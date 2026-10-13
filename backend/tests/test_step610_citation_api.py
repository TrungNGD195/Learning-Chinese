import asyncio
from uuid import UUID

from sqlalchemy import event, select

from app.conversation.ai_chat import get_ai_chat_service
from app.ai.rag.schemas import NO_EVIDENCE_CONTENT, RagInternalTier, RagRunResult, RagRunStatus, RagTierUsed
from app.database.engine import engine
from app.database.models import Conversation, Message, MessageCitation
from app.database.session import SessionFactory
from app.main import app
from tests import conversation_test_support as support


class CitationTestAI:
    def __init__(self, content="A plain answer"):
        self.content = content

    async def generate_reply(self, request):
        return RagRunResult(
            assistant_message_id=request.assistant_message_id, status=RagRunStatus.NO_EVIDENCE,
            assistant_content=NO_EVIDENCE_CONTENT,
            tiers_attempted=(RagTierUsed.CURRENT_LESSON, RagTierUsed.INTERNAL_KB, RagTierUsed.TRUSTED_EXTERNAL),
            tier_used=RagTierUsed.NONE, current_lesson_candidate_count=0,
            current_lesson_scored_count=0, internal_kb_candidate_count=0,
            internal_kb_scored_count=0, selected_context_count=0,
            memory_selected_turn_count=0, retrieval_trace=(), validated_citations=(),
        )


def test_message_api_always_returns_safe_batched_citation_snapshots():
    user_id, lesson_id = asyncio.run(support.seed_user_lesson())
    app.dependency_overrides[get_ai_chat_service] = lambda: CitationTestAI()
    try:
        with support.authenticated_client(user_id) as client:
            conversation = client.post("/api/v1/conversations", json={"lesson_id": str(lesson_id)}).json()
            conversation_id = conversation["id"]
            sent = client.post(f"/api/v1/conversations/{conversation_id}/messages", json={"content": "question"})
            assert sent.status_code == 201, sent.text
            user_message = sent.json()["user_message"]
            assistant_message = sent.json()["assistant_message"]
            assert user_message["citations"] == []
            assert assistant_message["citations"] == []

            async def add_snapshot():
                async with SessionFactory.begin() as session:
                    assistant = await session.get(Message, UUID(assistant_message["id"]))
                    assistant.content = "Rule [S3]\n`[S1]`\n[S1](https://evil.example)\nMore [S1]"
                    session.add(MessageCitation(
                        message_id=UUID(assistant_message["id"]),
                        source_label="S1", source_kind="INTERNAL_CHUNK", chunk_id=None,
                        title="Stored S1", source_type="LESSON",
                        locator={"page_number": 7, "section": "Stored section"},
                    ))
                    session.add(MessageCitation(
                        message_id=UUID(assistant_message["id"]),
                        source_label="S3", source_kind="INTERNAL_CHUNK", chunk_id=None,
                        title="Stored S3", source_type="DOCUMENT",
                        locator={"page_number": 3, "section": "Earlier section"},
                    ))
            asyncio.run(add_snapshot())

            citation_selects = []
            def observe(_conn, _cursor, statement, _parameters, _context, _many):
                if "FROM message_citations" in statement:
                    citation_selects.append(statement)
            event.listen(engine.sync_engine, "before_cursor_execute", observe)
            try:
                history = client.get(f"/api/v1/conversations/{conversation_id}/messages")
            finally:
                event.remove(engine.sync_engine, "before_cursor_execute", observe)
            assert history.status_code == 200
            assert len(citation_selects) == 1
            messages = history.json()["items"]
            assert messages[0]["citations"] == []
            citations = messages[1]["citations"]
            assert [citation["label"] for citation in citations] == ["S3", "S1"]
            assert citations[0] == {
                "label": "S3", "source_kind": "INTERNAL_CHUNK", "title": "Stored S3",
                "source_type": "DOCUMENT", "section": "Earlier section", "page_number": 3,
                "url": None, "domain": None,
            }
            assert citations[1] == {
                "label": "S1", "source_kind": "INTERNAL_CHUNK", "title": "Stored S1",
                "source_type": "LESSON", "section": "Stored section", "page_number": 7,
                "url": None, "domain": None,
            }
            citation = citations[0]
            assert "id" not in citation and "chunk_id" not in citation and "metadata" not in citation
    finally:
        app.dependency_overrides.pop(get_ai_chat_service, None)
        support.scenario_cleanup(user_id, lesson_id)


def test_model_markdown_url_never_becomes_a_citation_api_object():
    user_id, lesson_id = asyncio.run(support.seed_user_lesson())
    app.dependency_overrides[get_ai_chat_service] = lambda: CitationTestAI("Claim [S1](https://evil.example)")
    try:
        with support.authenticated_client(user_id) as client:
            conversation = client.post("/api/v1/conversations", json={"lesson_id": str(lesson_id)}).json()
            conversation_id = conversation["id"]
            sent = client.post(f"/api/v1/conversations/{conversation_id}/messages", json={"content": "question"})
            assert sent.status_code == 201
            assistant = sent.json()["assistant_message"]
            assert assistant["citations"] == []
            assert assistant["content"] == NO_EVIDENCE_CONTENT

            async def inject_legacy_markdown_content():
                async with SessionFactory.begin() as session:
                    row = await session.get(Message, UUID(assistant["id"]))
                    row.content = "Claim [S1](https://evil.example)"
            asyncio.run(inject_legacy_markdown_content())

            async def persisted_rows():
                async with SessionFactory() as session:
                    return list((await session.scalars(select(MessageCitation).where(
                        MessageCitation.message_id == UUID(assistant["id"]),
                    ))).all())
            assert asyncio.run(persisted_rows()) == []
            history = client.get(f"/api/v1/conversations/{conversation_id}/messages").json()
            assistant_history = next(item for item in history["items"] if item["id"] == assistant["id"])
            assert assistant_history["citations"] == []
            assert "https://evil.example" not in str(assistant_history["citations"])
    finally:
        app.dependency_overrides.pop(get_ai_chat_service, None)
        support.scenario_cleanup(user_id, lesson_id)
