import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.conversation import service
from app.conversation.ai_chat import AIChatProcessingError, ChatRequest
from app.ai.rag.schemas import NO_EVIDENCE_CONTENT, RagInternalTier, RagRunResult, RagRunStatus, RagTierUsed
from app.core.errors import ApplicationError
from app.database.models import Assessment, AssessmentAttempt, Conversation, Message
from app.database.session import SessionFactory
from tests import conversation_test_support as support


def no_evidence(request: ChatRequest) -> RagRunResult:
    return RagRunResult(
        assistant_message_id=request.assistant_message_id, status=RagRunStatus.NO_EVIDENCE,
        assistant_content=NO_EVIDENCE_CONTENT,
        tiers_attempted=(RagTierUsed.CURRENT_LESSON, RagTierUsed.INTERNAL_KB, RagTierUsed.TRUSTED_EXTERNAL),
        tier_used=RagTierUsed.NONE, current_lesson_candidate_count=0,
        current_lesson_scored_count=0, internal_kb_candidate_count=0,
        internal_kb_scored_count=0, selected_context_count=0,
        memory_selected_turn_count=0, retrieval_trace=(), validated_citations=(),
    )


class ImmediateAI:
    async def generate_reply(self, request: ChatRequest) -> RagRunResult:
        return no_evidence(request)


class FailingAI:
    async def generate_reply(self, request: ChatRequest) -> RagRunResult:
        raise AIChatProcessingError("internal test-only failure")


class BlockingAI:
    def __init__(self, *, expected_calls: int = 1):
        self.expected_calls = expected_calls
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.calls = 0
        self.transaction_states: list[bool] = []
        self.responses: list[ChatRequest] = []
        self.sessions: dict = {}

    async def generate_reply(self, request: ChatRequest) -> RagRunResult:
        self.calls += 1
        self.responses.append(request)
        session = self.sessions.get(request.conversation_id)
        self.transaction_states.append(session.in_transaction() if session is not None else False)
        if self.calls >= self.expected_calls:
            self.started.set()
        await asyncio.wait_for(self.release.wait(), timeout=5)
        return no_evidence(request)



async def create_conversation(user_id, lesson_id):
    async with SessionFactory.begin() as session:
        conversation = Conversation(user_id=user_id, lesson_id=lesson_id)
        session.add(conversation)
        await session.flush()
        return conversation.id


async def create_pending_turn(user_id, lesson_id):
    async with SessionFactory.begin() as session:
        conversation = Conversation(user_id=user_id, lesson_id=lesson_id)
        session.add(conversation)
        await session.flush()
        user_message = Message(
            conversation_id=conversation.id, sequence_number=1, role="USER",
            content="failure lock test", status="COMPLETED",
        )
        session.add(user_message)
        await session.flush()
        assistant = Message(
            conversation_id=conversation.id, sequence_number=2, role="ASSISTANT",
            content=None, status="PENDING", reply_to_message_id=user_message.id,
        )
        session.add(assistant)
        await session.flush()
        return conversation.id, user_message.id, assistant.id


async def message_state(conversation_id):
    async with SessionFactory() as session:
        return list((await session.scalars(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.sequence_number)
        )).all())


@pytest.mark.parametrize("send_count", [2])
def test_postgres_same_conversation_concurrent_sends_get_unique_sequences(send_count):
    user_id, lesson_id = asyncio.run(support.seed_user_lesson())
    conversation_id = asyncio.run(create_conversation(user_id, lesson_id))

    async def run():
        async def send(index):
            async with SessionFactory() as session:
                return await service.send_message(session, user_id, conversation_id, f"question {index}", ImmediateAI())
        return await asyncio.gather(*(send(index) for index in range(send_count)))

    try:
        results = asyncio.run(run())
        rows = asyncio.run(message_state(conversation_id))
        assert len(results) == send_count and len(rows) == send_count * 2
        assert [row.sequence_number for row in rows] == list(range(1, send_count * 2 + 1))
        assert [row.role for row in rows] == ["USER", "ASSISTANT"] * send_count
        assert all(rows[index + 1].reply_to_message_id == rows[index].id for index in range(0, len(rows), 2))
    finally:
        support.scenario_cleanup(user_id, lesson_id)


def test_postgres_concurrent_retries_create_exactly_one_new_attempt():
    user_id, lesson_id = asyncio.run(support.seed_user_lesson())
    conversation_id = asyncio.run(create_conversation(user_id, lesson_id))

    async def run():
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as failed:
                await service.send_message(session, user_id, conversation_id, "retry me", FailingAI())
        failed_assistant_id = UUID(failed.value.details["assistant_message_id"])
        ai = BlockingAI(expected_calls=1)
        async def retry():
            async with SessionFactory() as session:
                try:
                    return await service.retry_message(session, user_id, failed_assistant_id, ai)
                except ApplicationError as error:
                    return error
        first = asyncio.create_task(retry())
        await asyncio.wait_for(ai.started.wait(), timeout=5)
        second_result = await retry()
        assert isinstance(second_result, ApplicationError)
        assert second_result.code == "INVALID_MESSAGE_RETRY"
        ai.release.set()
        first_result = await first
        assert isinstance(first_result, dict)
        return failed_assistant_id

    try:
        failed_id = asyncio.run(run())
        rows = asyncio.run(message_state(conversation_id))
        assert len(rows) == 3
        assert rows[0].role == "USER"
        assert rows[1].id == failed_id and rows[1].status == "FAILED"
        assert rows[2].role == "ASSISTANT" and rows[2].status == "COMPLETED"
        assert rows[2].reply_to_message_id == rows[0].id
    finally:
        support.scenario_cleanup(user_id, lesson_id)


def test_different_conversations_are_not_serialized_and_ai_has_no_open_transaction():
    user_id, lesson_id = asyncio.run(support.seed_user_lesson())
    first_id, second_id = asyncio.run(create_conversation(user_id, lesson_id)), asyncio.run(create_conversation(user_id, lesson_id))
    ai = BlockingAI(expected_calls=2)

    async def run():
        async def send(conversation_id, content):
            async with SessionFactory() as session:
                ai.sessions[conversation_id] = session
                return await service.send_message(session, user_id, conversation_id, content, ai)
        tasks = [asyncio.create_task(send(first_id, "first")), asyncio.create_task(send(second_id, "second"))]
        await asyncio.wait_for(ai.started.wait(), timeout=5)
        assert ai.calls == 2
        assert ai.transaction_states == [False, False]
        ai.release.set()
        return await asyncio.gather(*tasks)

    try:
        assert len(asyncio.run(run())) == 2
    finally:
        ai.sessions.clear()
        support.scenario_cleanup(user_id, lesson_id)


@pytest.mark.parametrize("change_after_transaction_a", ["periodic_test", "soft_delete"])
def test_d026_later_state_changes_do_not_cancel_started_ai_turn(change_after_transaction_a):
    user_id, lesson_id = asyncio.run(support.seed_user_lesson())
    conversation_id = asyncio.run(create_conversation(user_id, lesson_id))
    ai = BlockingAI()

    async def run():
        async def send():
            async with SessionFactory() as session:
                ai.sessions[conversation_id] = session
                return await service.send_message(session, user_id, conversation_id, "started turn", ai)
        task = asyncio.create_task(send())
        await asyncio.wait_for(ai.started.wait(), timeout=5)
        assert ai.transaction_states == [False]
        assessment_id = None
        if change_after_transaction_a == "periodic_test":
            assessment_id, _ = await support.add_assessment_attempt(
                user_id,
                lesson_id,
                assessment_type="PERIODIC_TEST",
            )
        else:
            async with SessionFactory() as session:
                await service.delete_conversation(session, user_id, conversation_id)
        ai.release.set()
        result = await task
        return result, assessment_id

    try:
        _, assessment_id = asyncio.run(run())
        rows = asyncio.run(message_state(conversation_id))
        assert len(rows) == 2 and rows[1].status == "COMPLETED"
        async def check_deleted():
            async with SessionFactory() as session:
                conversation = await session.get(Conversation, conversation_id)
                return conversation.deleted_at is not None
        deleted = asyncio.run(check_deleted())
        assert deleted is (change_after_transaction_a == "soft_delete")
        if assessment_id is not None:
            async def cleanup_assessment():
                async with SessionFactory.begin() as session:
                    await session.execute(AssessmentAttempt.__table__.delete().where(AssessmentAttempt.user_id == user_id))
                    await session.execute(Assessment.__table__.delete().where(Assessment.id == assessment_id))
            asyncio.run(cleanup_assessment())
    finally:
        ai.sessions.clear()
        support.scenario_cleanup(user_id, lesson_id)


@pytest.mark.parametrize("change_after_transaction_a", ["periodic_test", "soft_delete"])
def test_d026_later_state_changes_do_not_cancel_started_retry(change_after_transaction_a):
    user_id, lesson_id = asyncio.run(support.seed_user_lesson())
    conversation_id = asyncio.run(create_conversation(user_id, lesson_id))
    ai = BlockingAI()

    async def run():
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as failed:
                await service.send_message(session, user_id, conversation_id, "retry snapshot", FailingAI())
        failed_id = UUID(failed.value.details["assistant_message_id"])

        async def retry():
            async with SessionFactory() as session:
                ai.sessions[conversation_id] = session
                return await service.retry_message(session, user_id, failed_id, ai)

        task = asyncio.create_task(retry())
        await asyncio.wait_for(ai.started.wait(), timeout=5)
        assert ai.transaction_states == [False]
        assessment_id = None
        if change_after_transaction_a == "periodic_test":
            assessment_id, _ = await support.add_assessment_attempt(
                user_id,
                lesson_id,
                assessment_type="PERIODIC_TEST",
            )
        else:
            async with SessionFactory() as session:
                await service.delete_conversation(session, user_id, conversation_id)
        ai.release.set()
        response = await task
        return failed_id, response, assessment_id

    try:
        failed_id, response, assessment_id = asyncio.run(run())
        assert response["status"] == "COMPLETED"
        rows = asyncio.run(message_state(conversation_id))
        assert len(rows) == 3
        assert rows[1].id == failed_id and rows[1].status == "FAILED"
        assert rows[2].status == "COMPLETED" and rows[2].reply_to_message_id == rows[0].id
        async def check_deleted():
            async with SessionFactory() as session:
                conversation = await session.get(Conversation, conversation_id)
                return conversation.deleted_at is not None
        assert asyncio.run(check_deleted()) is (change_after_transaction_a == "soft_delete")
        if assessment_id is not None:
            async def clean_periodic():
                async with SessionFactory.begin() as session:
                    await session.execute(AssessmentAttempt.__table__.delete().where(AssessmentAttempt.user_id == user_id))
                    await session.execute(Assessment.__table__.delete().where(Assessment.id == assessment_id))
            asyncio.run(clean_periodic())
    finally:
        ai.sessions.clear()
        support.scenario_cleanup(user_id, lesson_id)


def test_delete_that_locks_first_prevents_later_send_transaction_a():
    user_id, lesson_id = asyncio.run(support.seed_user_lesson())
    conversation_id = asyncio.run(create_conversation(user_id, lesson_id))

    async def run():
        async with SessionFactory() as deleting_session:
            conversation = await service.repository.get_owned_conversation(
                deleting_session,
                conversation_id,
                user_id,
                for_update=True,
            )
            await service.repository.soft_delete_conversation(deleting_session, conversation)
            async def send():
                async with SessionFactory() as session:
                    try:
                        return await service.send_message(session, user_id, conversation_id, "too late", ImmediateAI())
                    except ApplicationError as error:
                        return error
            send_task = asyncio.create_task(send())
            await asyncio.sleep(0.05)
            await deleting_session.commit()
        result = await send_task
        assert isinstance(result, ApplicationError) and result.code == "CONVERSATION_DELETED"
        return await message_state(conversation_id)

    try:
        assert asyncio.run(run()) == []
    finally:
        support.scenario_cleanup(user_id, lesson_id)


def test_d090_processing_lock_is_held_until_failure_commit(monkeypatch):
    user_id, lesson_id = asyncio.run(support.seed_user_lesson())
    conversation_id, user_message_id, assistant_id = asyncio.run(
        create_pending_turn(user_id, lesson_id)
    )
    mark_started, allow_mark_commit = asyncio.Event(), asyncio.Event()
    original_mark_failed = service._mark_assistant_failed

    class CountingFailingAI:
        def __init__(self):
            self.calls = 0

        async def generate_reply(self, request):
            self.calls += 1
            raise AIChatProcessingError("internal test-only failure")

    ai = CountingFailingAI()
    request = ChatRequest(
        user_id=user_id, conversation_id=conversation_id, lesson_id=lesson_id,
        user_message_id=user_message_id, assistant_message_id=assistant_id,
        content="failure lock test",
    )

    async def block_before_failure_commit(session, message_id):
        mark_started.set()
        await asyncio.wait_for(allow_mark_commit.wait(), timeout=5)
        await original_mark_failed(session, message_id)

    monkeypatch.setattr(service, "_mark_assistant_failed", block_before_failure_commit)

    async def process_once(processor):
        async with SessionFactory() as session:
            return await service._process_ai_turn(
                session, processor, request,
                user_message_id=user_message_id,
                assistant_message_id=assistant_id,
            )

    async def inspect_status():
        async with SessionFactory() as session:
            message = await session.get(Message, assistant_id)
            return message.status

    async def run():
        first = asyncio.create_task(process_once(ai))
        await asyncio.wait_for(mark_started.wait(), timeout=5)

        # A is paused immediately before the FAILED commit. Its session lock
        # must still exclude processor B, which must not invoke AI or mutate.
        assert await inspect_status() == "PENDING"
        second = CountingFailingAI()
        duplicate_result = await process_once(second)
        assert duplicate_result[0] is None
        assert duplicate_result[1].code == "DUPLICATE_RAG_GENERATION"
        assert second.calls == 0
        assert await inspect_status() == "PENDING"

        allow_mark_commit.set()
        first_result = await asyncio.wait_for(first, timeout=5)
        assert first_result[0] is None
        assert first_result[1].code == "AI_RESPONSE_FAILED"
        assert ai.calls == 1
        assert await inspect_status() == "FAILED"

        # After commit and release, a later lock owner reaches the persisted
        # state check and is rejected without invoking AI.
        third = CountingFailingAI()
        later_result = await process_once(third)
        assert later_result[0] is None
        assert later_result[1].code == "DUPLICATE_RAG_GENERATION"
        assert third.calls == 0
        assert await inspect_status() == "FAILED"

    try:
        asyncio.run(run())
    finally:
        support.scenario_cleanup(user_id, lesson_id)
