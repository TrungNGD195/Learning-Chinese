import asyncio

from app.conversation import repository
from app.database.models import Conversation, Message
from app.database.session import SessionFactory
from conversation_test_support import cleanup_scenario, seed_user_lesson


def test_repository_returns_only_bounded_completed_pairs_before_current_message():
    async def scenario():
        user_id, lesson_id = await seed_user_lesson(accessible=False)
        try:
            conversation_id = None
            async with SessionFactory.begin() as session:
                conversation = Conversation(user_id=user_id, lesson_id=lesson_id)
                session.add(conversation)
                await session.flush()
                conversation_id = conversation.id
                first = Message(conversation_id=conversation.id, sequence_number=1, role="USER", content="first", status="COMPLETED")
                session.add(first)
                await session.flush()
                session.add(Message(conversation_id=conversation.id, sequence_number=2, role="ASSISTANT", content=None, status="FAILED", reply_to_message_id=first.id))
                session.add(Message(conversation_id=conversation.id, sequence_number=3, role="ASSISTANT", content="final first", status="COMPLETED", reply_to_message_id=first.id))
                second = Message(conversation_id=conversation.id, sequence_number=4, role="USER", content="second", status="COMPLETED")
                session.add(second)
                await session.flush()
                session.add(Message(conversation_id=conversation.id, sequence_number=5, role="ASSISTANT", content=None, status="PENDING", reply_to_message_id=second.id))
                session.add(Message(conversation_id=conversation.id, sequence_number=6, role="ASSISTANT", content="final second", status="COMPLETED", reply_to_message_id=second.id))
                session.add(Message(conversation_id=conversation.id, sequence_number=7, role="USER", content="current", status="COMPLETED"))

                other_conversation = Conversation(user_id=user_id, lesson_id=lesson_id)
                session.add(other_conversation)
                await session.flush()
                other_user = Message(conversation_id=other_conversation.id, sequence_number=1, role="USER", content="other conversation", status="COMPLETED")
                session.add(other_user)
                await session.flush()
                session.add(Message(conversation_id=other_conversation.id, sequence_number=2, role="ASSISTANT", content="other answer", status="COMPLETED", reply_to_message_id=other_user.id))

                pairs = await repository.list_recent_completed_turn_pairs_for_memory(
                    session, conversation_id=conversation.id, before_sequence_number=7, limit=2,
                )
                assert [pair.user_sequence_number for pair in pairs] == [4, 1]
                assert [pair.assistant_text for pair in pairs] == ["final second", "final first"]
                assert all(pair.conversation_id == conversation.id for pair in pairs)
                assert len(await repository.list_recent_completed_turn_pairs_for_memory(
                    session, conversation_id=conversation.id, before_sequence_number=7, limit=1,
                )) == 1
        finally:
            await cleanup_scenario(user_id, lesson_id)

    asyncio.run(scenario())
