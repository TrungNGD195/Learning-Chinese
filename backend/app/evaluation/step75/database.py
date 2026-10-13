from __future__ import annotations

from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.database.models import Conversation, Message, MessageCitation, MessageRetrieval, User
from app.evaluation.step73.fixtures import assert_evaluation_database, load_fixture_pack


async def create_isolated_conversation(session: AsyncSession, *, settings: Settings,
                                       actual_database: str, lesson_id, case: dict,
                                       run_id: str, execution_id: str) -> dict:
    """Create test-only learner/history in guarded test DB; caller supplies fixture Lesson ID."""
    database_guard = assert_evaluation_database(settings, actual_database)
    user_id, conversation_id = uuid4(), uuid4()
    user = User(id=user_id, email=f"{run_id}-{execution_id}@evaluation.invalid",
                password_hash="disabled-evaluation-only", full_name="Step 7.5 Evaluation",
                role="LEARNER", is_active=True)
    conversation = Conversation(id=conversation_id, user_id=user_id, lesson_id=lesson_id,
                                title="Step 7.5 isolated evaluation")
    session.add_all([user, conversation])
    sequence = 1
    history_pairings = []
    for turn in case.get("conversation_context") or []:
        user_message = Message(conversation_id=conversation_id, role="USER",
                               content=turn["user_text"], status="COMPLETED",
                               sequence_number=sequence)
        session.add(user_message)
        await session.flush()
        assistant_message = Message(conversation_id=conversation_id, role="ASSISTANT",
                                    content=turn["assistant_text"], status="COMPLETED",
                                    sequence_number=sequence + 1,
                                    reply_to_message_id=user_message.id)
        session.add(assistant_message)
        await session.flush()
        history_pairings.append({"user_message_id": user_message.id,
                                 "assistant_message_id": assistant_message.id,
                                 "reply_to_message_id": assistant_message.reply_to_message_id,
                                 "user_sequence_number": sequence,
                                 "assistant_sequence_number": sequence + 1})
        sequence += 2
    await session.commit()
    return {"user_id": user_id, "conversation_id": conversation_id,
            "lesson_id": lesson_id, "database_isolation": database_guard,
            "current_sequence_number": sequence, "history_pairings": history_pairings}


async def delete_isolated_conversation(session: AsyncSession, *, settings: Settings,
                                       actual_database: str, conversation_id,
                                       user_id) -> None:
    """Remove only a generated evaluation conversation after revalidating DB identity."""
    assert_evaluation_database(settings, actual_database)
    message_ids = list((await session.scalars(select(Message.id).where(
        Message.conversation_id == conversation_id))).all())
    if message_ids:
        await session.execute(delete(MessageCitation).where(MessageCitation.message_id.in_(message_ids)))
        await session.execute(delete(MessageRetrieval).where(MessageRetrieval.message_id.in_(message_ids)))
        await session.execute(delete(Message).where(Message.id.in_(message_ids)))
    await session.execute(delete(Conversation).where(
        Conversation.id == conversation_id, Conversation.user_id == user_id))
    await session.execute(delete(User).where(User.id == user_id))
    await session.commit()


def fixture_metadata_by_chunk_id(bootstrap: dict) -> dict[str, dict]:
    """Resolve fixture locators by actual runtime chunk identity from Step 7.3 bootstrap."""
    _, blocks, _ = load_fixture_pack()
    by_locator = {row["stable_locator"]: row for row in blocks}
    result: dict[str, dict] = {}
    for locator, chunk_ids in bootstrap.get("runtime_map", {}).items():
        block = by_locator.get(locator)
        if block is None:
            raise ValueError("E2E_FIXTURE_RUNTIME_MAP_HAS_UNKNOWN_LOCATOR")
        for chunk_id in chunk_ids:
            row = result.setdefault(str(chunk_id), {"stable_locators": [],
                "source_kind": block.get("source_kind"), "source_id": block.get("source_id"),
                "lesson_locator": block.get("lesson_locator"), "title": block.get("source_title"),
                "content_type": block.get("content_type"), "content": block.get("content")})
            if locator not in row["stable_locators"]:
                row["stable_locators"].append(locator)
    return result
