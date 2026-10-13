import asyncio
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.auth.security import hash_password
from app.ai.rag.schemas import NO_EVIDENCE_CONTENT, RagInternalTier, RagRunResult, RagRunStatus, RagTierUsed
from app.conversation.ai_chat import AIChatProcessingError, ChatRequest, get_ai_chat_service
from app.database.models import Conversation, Message, User
from app.database.session import SessionFactory
from app.main import app
from tests import conversation_test_support as support


class RecordingAI:
    def __init__(self, *, fail: bool = False, content: str | None = None):
        self.fail = fail
        self.content = content
        self.requests: list[ChatRequest] = []

    async def generate_reply(self, request: ChatRequest) -> RagRunResult:
        self.requests.append(request)
        if self.fail:
            raise AIChatProcessingError("private deterministic failure detail")
        return RagRunResult(
            assistant_message_id=request.assistant_message_id,
            status=RagRunStatus.NO_EVIDENCE,
            assistant_content=NO_EVIDENCE_CONTENT,
            tiers_attempted=(RagTierUsed.CURRENT_LESSON, RagTierUsed.INTERNAL_KB, RagTierUsed.TRUSTED_EXTERNAL),
            tier_used=RagTierUsed.NONE,
            current_lesson_candidate_count=0,
            current_lesson_scored_count=0,
            internal_kb_candidate_count=0,
            internal_kb_scored_count=0,
            selected_context_count=0,
            memory_selected_turn_count=0,
            retrieval_trace=(),
            validated_citations=(),
        )


def test_auth_strict_conversation_contract_and_owned_crud():
    user_id, lesson_id = asyncio.run(support.seed_user_lesson())
    other_user_id = asyncio.run(support.seed_user_for_lesson(lesson_id))
    try:
        from fastapi.testclient import TestClient
        with TestClient(app, raise_server_exceptions=False) as anonymous:
            assert anonymous.get("/api/v1/me/conversations").status_code == 401
            assert anonymous.post("/api/v1/conversations", json={"lesson_id": str(lesson_id)}).status_code == 401
        with support.authenticated_client(user_id) as client:
            assert client.post("/api/v1/conversations", json={"lesson_id": str(lesson_id), "user_id": str(user_id)}).status_code == 422
            assert client.post("/api/v1/conversations", json={"lesson_id": str(lesson_id), "scope": "LESSON"}).status_code == 422
            created = client.post("/api/v1/conversations", json={"lesson_id": str(lesson_id)})
            assert created.status_code == 201, created.text
            first = created.json()
            assert set(first) == {"id", "scope", "lesson_id", "title", "created_at", "updated_at"}
            assert first["scope"] == "LESSON" and "user_id" not in first
            second = client.post("/api/v1/conversations", json={"lesson_id": str(lesson_id)})
            assert second.status_code == 201 and second.json()["id"] != first["id"]

            empty_patch = client.patch(f"/api/v1/conversations/{first['id']}", json={})
            assert empty_patch.status_code == 422
            bad_title = client.patch(f"/api/v1/conversations/{first['id']}", json={"title": "   "})
            assert bad_title.status_code == 422
            too_long = client.patch(f"/api/v1/conversations/{first['id']}", json={"title": "x" * 201})
            assert too_long.status_code == 422
            max_title = client.patch(f"/api/v1/conversations/{first['id']}", json={"title": "x" * 200})
            assert max_title.status_code == 200 and len(max_title.json()["title"]) == 200
            renamed = client.patch(f"/api/v1/conversations/{first['id']}", json={"title": "  My lesson chat  "})
            assert renamed.status_code == 200 and renamed.json()["title"] == "My lesson chat"
            cleared = client.patch(f"/api/v1/conversations/{first['id']}", json={"title": None})
            assert cleared.status_code == 200 and cleared.json()["title"] is None

            listing = client.get("/api/v1/me/conversations", params={"scope": "LESSON", "lesson_id": str(lesson_id)})
            assert listing.status_code == 200 and listing.json()["total"] == 2
            assert client.get("/api/v1/me/conversations", params={"scope": "GLOBAL"}).status_code == 422
            assert client.get("/api/v1/me/conversations", params={"page_size": 101}).status_code == 422
            assert client.get(f"/api/v1/conversations/{uuid4()}").json()["error"]["code"] == "CONVERSATION_NOT_FOUND"

            with support.authenticated_client(other_user_id) as other_client:
                private = other_client.get(f"/api/v1/conversations/{first['id']}")
                assert private.status_code == 404 and private.json()["error"]["code"] == "CONVERSATION_NOT_FOUND"
                assert other_client.get(f"/api/v1/conversations/{first['id']}/messages").status_code == 404
                assert other_client.delete(f"/api/v1/conversations/{first['id']}").status_code == 404

            deleted = client.delete(f"/api/v1/conversations/{first['id']}")
            assert deleted.status_code == 204
            assert client.delete(f"/api/v1/conversations/{first['id']}").status_code == 204
            for response in (
                client.get(f"/api/v1/conversations/{first['id']}"),
                client.patch(f"/api/v1/conversations/{first['id']}", json={"title": "later"}),
                client.get(f"/api/v1/conversations/{first['id']}/messages"),
                client.post(f"/api/v1/conversations/{first['id']}/messages", json={"content": "hello"}),
            ):
                assert response.status_code == 410 and response.json()["error"]["code"] == "CONVERSATION_DELETED"
            remaining = client.get("/api/v1/me/conversations").json()
            assert remaining["total"] == 1 and remaining["items"][0]["id"] == second.json()["id"]

        async def verify_persisted_soft_delete() -> None:
            async with SessionFactory() as session:
                row = await session.get(Conversation, UUID(first["id"]))
                assert row is not None and row.deleted_at is not None
        asyncio.run(verify_persisted_soft_delete())
    finally:
        support.scenario_cleanup(user_id, lesson_id)
        asyncio.run(support.cleanup_user_only(other_user_id))


def test_locked_and_completed_lesson_access_and_conversation_list_order():
    locked_user, locked_lesson = asyncio.run(support.seed_user_lesson(accessible=False))
    completed_user, completed_lesson = asyncio.run(support.seed_user_lesson(completed=True))
    try:
        with support.authenticated_client(locked_user) as client:
            response = client.post("/api/v1/conversations", json={"lesson_id": str(locked_lesson)})
            assert response.status_code == 403 and response.json()["error"]["code"] == "LESSON_LOCKED"
        with support.authenticated_client(completed_user) as client:
            created = client.post("/api/v1/conversations", json={"lesson_id": str(completed_lesson)})
            assert created.status_code == 201
            first_id = created.json()["id"]
            second = client.post("/api/v1/conversations", json={"lesson_id": str(completed_lesson)}).json()
            assert second["id"] != first_id
            client.patch(f"/api/v1/conversations/{first_id}", json={"title": "touch activity"})
            ordered = client.get("/api/v1/me/conversations", params={"lesson_id": str(completed_lesson), "page": 1, "page_size": 1}).json()
            assert ordered["total"] == 2 and ordered["items"][0]["id"] == first_id
    finally:
        support.scenario_cleanup(locked_user, locked_lesson)
        support.scenario_cleanup(completed_user, completed_lesson)


def test_send_failure_durability_retry_and_newest_window_pagination():
    user_id, lesson_id = asyncio.run(support.seed_user_lesson())
    failure = RecordingAI(fail=True)
    app.dependency_overrides[get_ai_chat_service] = lambda: failure
    try:
        with support.authenticated_client(user_id) as client:
            conversation = client.post("/api/v1/conversations", json={"lesson_id": str(lesson_id)}).json()
            conversation_id = conversation["id"]
            invalid = client.post(f"/api/v1/conversations/{conversation_id}/messages", json={"content": " \n "})
            assert invalid.status_code == 422
            spoof = client.post(f"/api/v1/conversations/{conversation_id}/messages", json={"content": "hello", "role": "ASSISTANT"})
            assert spoof.status_code == 422
            failed = client.post(f"/api/v1/conversations/{conversation_id}/messages", json={"content": "  first question  "})
            assert failed.status_code == 502
            error = failed.json()["error"]
            assert error["code"] == "AI_RESPONSE_FAILED"
            assert set(error["details"]) == {"user_message_id", "assistant_message_id"}
            assert "private deterministic failure detail" not in failed.text
            user_message_id = error["details"]["user_message_id"]
            failed_assistant_id = error["details"]["assistant_message_id"]

            other_user_id = asyncio.run(support.seed_user_for_lesson(lesson_id))
            try:
                with support.authenticated_client(other_user_id) as other_client:
                    private_retry = other_client.post(f"/api/v1/messages/{failed_assistant_id}/retry")
                    assert private_retry.status_code == 404
                    assert private_retry.json()["error"]["code"] == "CONVERSATION_NOT_FOUND"
            finally:
                asyncio.run(support.cleanup_user_only(other_user_id))

            async def inspect_failure() -> None:
                async with SessionFactory() as session:
                    rows = list((await session.scalars(select(Message).where(Message.conversation_id == UUID(conversation_id)).order_by(Message.sequence_number))).all())
                assert len(rows) == 2
                assert rows[0].id == UUID(user_message_id) and rows[0].content == "first question" and rows[0].status == "COMPLETED"
                assert rows[1].id == UUID(failed_assistant_id) and rows[1].status == "FAILED" and rows[1].content is None
                assert rows[1].reply_to_message_id == rows[0].id and [row.sequence_number for row in rows] == [1, 2]
            asyncio.run(inspect_failure())

            retry_failure = RecordingAI(fail=True)
            app.dependency_overrides[get_ai_chat_service] = lambda: retry_failure
            failed_retry = client.post(f"/api/v1/messages/{failed_assistant_id}/retry")
            assert failed_retry.status_code == 502
            next_failed_id = failed_retry.json()["error"]["details"]["assistant_message_id"]
            assert client.post(f"/api/v1/messages/{failed_assistant_id}/retry").status_code == 409

            success = RecordingAI(content="  recovered  ")
            app.dependency_overrides[get_ai_chat_service] = lambda: success
            retried = client.post(f"/api/v1/messages/{next_failed_id}/retry")
            assert retried.status_code == 201
            retry_response = retried.json()
            assert set(retry_response) == {"id", "conversation_id", "sequence_number", "role", "content", "status", "reply_to_message_id", "created_at", "citations"}
            assert retry_response["citations"] == []
            assert retry_response["role"] == "ASSISTANT" and retry_response["status"] == "COMPLETED"
            assert retry_response["content"] == NO_EVIDENCE_CONTENT and retry_response["reply_to_message_id"] == user_message_id
            assert success.requests[0].content == "first question"
            assert client.post(f"/api/v1/messages/{next_failed_id}/retry").status_code == 409

            # Seed one more turn and verify page 1 is the newest sequence window.
            sent = client.post(f"/api/v1/conversations/{conversation_id}/messages", json={"content": "second question"})
            assert sent.status_code == 201
            assert set(sent.json()) == {"user_message", "assistant_message"}
            assert sent.json()["user_message"]["sequence_number"] == 5
            assert sent.json()["assistant_message"]["sequence_number"] == 6
            page1 = client.get(f"/api/v1/conversations/{conversation_id}/messages", params={"page_size": 3}).json()
            page2 = client.get(f"/api/v1/conversations/{conversation_id}/messages", params={"page": 2, "page_size": 3}).json()
            assert page1["total"] == 6
            assert [item["sequence_number"] for item in page1["items"]] == [4, 5, 6]
            assert [item["sequence_number"] for item in page2["items"]] == [1, 2, 3]
            assert "user_id" not in page1["items"][0]
    finally:
        app.dependency_overrides.pop(get_ai_chat_service, None)
        support.scenario_cleanup(user_id, lesson_id)


def test_active_periodic_test_blocks_chat_but_lesson_exercise_does_not():
    user_id, lesson_id = asyncio.run(support.seed_user_lesson())
    assessment_ids = []
    try:
        lesson_exercise_id, _ = asyncio.run(support.add_assessment_attempt(user_id, lesson_id, assessment_type="LESSON_EXERCISE"))
        assessment_ids.append(lesson_exercise_id)
        ai = RecordingAI()
        app.dependency_overrides[get_ai_chat_service] = lambda: ai
        with support.authenticated_client(user_id) as client:
            conversation = client.post("/api/v1/conversations", json={"lesson_id": str(lesson_id)}).json()
            conversation_id = conversation["id"]
            allowed = client.post(f"/api/v1/conversations/{conversation_id}/messages", json={"content": "exercise active"})
            assert allowed.status_code == 201
            failure = RecordingAI(fail=True)
            app.dependency_overrides[get_ai_chat_service] = lambda: failure
            failed_send = client.post(f"/api/v1/conversations/{conversation_id}/messages", json={"content": "create retry candidate"})
            assert failed_send.status_code == 502
            retry_id = failed_send.json()["error"]["details"]["assistant_message_id"]

        periodic_id, periodic_attempt_id = asyncio.run(support.add_assessment_attempt(user_id, lesson_id, assessment_type="PERIODIC_TEST"))
        assessment_ids.append(periodic_id)
        with support.authenticated_client(user_id) as client:
            conversation_id = client.get("/api/v1/me/conversations").json()["items"][0]["id"]
            before = client.get(f"/api/v1/conversations/{conversation_id}/messages").json()["total"]
            blocked = client.post(f"/api/v1/conversations/{conversation_id}/messages", json={"content": "must be blocked"})
            assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "AI_CHAT_DISABLED_DURING_TEST"
            retry_blocked = client.post(f"/api/v1/messages/{retry_id}/retry")
            assert retry_blocked.status_code == 409 and retry_blocked.json()["error"]["code"] == "AI_CHAT_DISABLED_DURING_TEST"
            after = client.get(f"/api/v1/conversations/{conversation_id}/messages").json()["total"]
            assert before == after

        async def terminalize_attempt():
            from app.database.models import AssessmentAttempt
            async with SessionFactory.begin() as session:
                attempt = await session.get(AssessmentAttempt, periodic_attempt_id)
                attempt.status = "GRADED"
        asyncio.run(terminalize_attempt())
        app.dependency_overrides[get_ai_chat_service] = lambda: RecordingAI()
        with support.authenticated_client(user_id) as client:
            conversations = client.get("/api/v1/me/conversations").json()["items"]
            first_conversation_id = next(item["id"] for item in conversations if item["id"] == conversation_id)
            assert client.post(f"/api/v1/conversations/{first_conversation_id}/messages", json={"content": "test ended"}).status_code == 201
    finally:
        app.dependency_overrides.pop(get_ai_chat_service, None)
        support.scenario_cleanup(user_id, lesson_id, assessment_ids)


def test_openapi_conversation_contract_paths_and_message_fields():
    schema = app.openapi()
    paths = schema["paths"]
    assert "/api/v1/conversations" in paths
    assert "/api/v1/messages/{assistant_message_id}/retry" in paths
    message = schema["components"]["schemas"]["MessageResponse"]["properties"]
    assert set(message) == {"id", "conversation_id", "sequence_number", "role", "content", "status", "reply_to_message_id", "created_at", "citations"}
    assert message["citations"]["type"] == "array"
    assert schema["components"]["schemas"]["CitationResponse"]["properties"]["label"]["type"] == "string"
    create_request = schema["components"]["schemas"]["ConversationCreateRequest"]["properties"]
    assert set(create_request) == {"lesson_id"}
    message_request = schema["components"]["schemas"]["MessageCreateRequest"]["properties"]
    assert set(message_request) == {"content"}


def test_message_content_bounds_are_applied_after_trimming():
    user_id, lesson_id = asyncio.run(support.seed_user_lesson())
    app.dependency_overrides[get_ai_chat_service] = lambda: RecordingAI()
    try:
        with support.authenticated_client(user_id) as client:
            conversation = client.post("/api/v1/conversations", json={"lesson_id": str(lesson_id)}).json()
            conversation_id = conversation["id"]
            accepted = client.post(
                f"/api/v1/conversations/{conversation_id}/messages",
                json={"content": "x" * 4000},
            )
            assert accepted.status_code == 201
            assert len(accepted.json()["user_message"]["content"]) == 4000
            rejected = client.post(
                f"/api/v1/conversations/{conversation_id}/messages",
                json={"content": "x" * 4001},
            )
            assert rejected.status_code == 422
    finally:
        app.dependency_overrides.pop(get_ai_chat_service, None)
        support.scenario_cleanup(user_id, lesson_id)


def test_deleted_conversation_rejects_retry_but_keeps_message_history():
    user_id, lesson_id = asyncio.run(support.seed_user_lesson())
    app.dependency_overrides[get_ai_chat_service] = lambda: RecordingAI(fail=True)
    try:
        with support.authenticated_client(user_id) as client:
            conversation = client.post("/api/v1/conversations", json={"lesson_id": str(lesson_id)}).json()
            conversation_id = conversation["id"]
            failed = client.post(f"/api/v1/conversations/{conversation_id}/messages", json={"content": "persist history"})
            assert failed.status_code == 502
            assistant_id = failed.json()["error"]["details"]["assistant_message_id"]
            assert client.delete(f"/api/v1/conversations/{conversation_id}").status_code == 204
            retry = client.post(f"/api/v1/messages/{assistant_id}/retry")
            assert retry.status_code == 410 and retry.json()["error"]["code"] == "CONVERSATION_DELETED"
        async def history_is_retained():
            async with SessionFactory() as session:
                count = await session.scalar(select(func.count()).select_from(Message).where(Message.conversation_id == UUID(conversation_id)))
                return count
        assert asyncio.run(history_is_retained()) == 2
    finally:
        app.dependency_overrides.pop(get_ai_chat_service, None)
        support.scenario_cleanup(user_id, lesson_id)
