from datetime import UTC, datetime
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.ai.citations.schemas import ValidatedCitation
from app.database.models import Conversation, Message, MessageCitation, MessageRetrieval


@dataclass(frozen=True)
class MemoryTurnRow:
    user_message_id: UUID
    assistant_message_id: UUID
    user_text: str | None
    assistant_text: str | None
    user_sequence_number: int
    assistant_sequence_number: int
    conversation_id: UUID


async def get_owned_conversation(
    session: AsyncSession,
    conversation_id: UUID,
    user_id: UUID,
    *,
    for_update: bool = False,
) -> Conversation | None:
    query = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == user_id,
    )
    if for_update:
        query = query.with_for_update()
    return await session.scalar(query)


async def add_conversation(session: AsyncSession, conversation: Conversation) -> Conversation:
    session.add(conversation)
    await session.flush()
    return conversation


async def list_conversations(
    session: AsyncSession,
    user_id: UUID,
    page: int,
    page_size: int,
    lesson_id: UUID | None = None,
) -> tuple[int, list[Conversation]]:
    filters = [Conversation.user_id == user_id, Conversation.deleted_at.is_(None)]
    if lesson_id is not None:
        filters.append(Conversation.lesson_id == lesson_id)
    total = await session.scalar(select(func.count()).select_from(Conversation).where(*filters))
    rows = await session.scalars(
        select(Conversation)
        .where(*filters)
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return int(total or 0), list(rows)


async def rename_conversation(session: AsyncSession, conversation: Conversation, title: str | None) -> None:
    conversation.title = title
    conversation.updated_at = datetime.now(UTC)
    await session.flush()


async def touch_conversation(session: AsyncSession, conversation: Conversation) -> None:
    conversation.updated_at = datetime.now(UTC)
    await session.flush()


async def soft_delete_conversation(session: AsyncSession, conversation: Conversation) -> None:
    if conversation.deleted_at is None:
        conversation.deleted_at = datetime.now(UTC)
        await session.flush()


async def next_sequence_number(session: AsyncSession, conversation_id: UUID) -> int:
    maximum = await session.scalar(
        select(func.max(Message.sequence_number)).where(Message.conversation_id == conversation_id)
    )
    return int(maximum or 0) + 1


async def add_message(session: AsyncSession, message: Message) -> Message:
    session.add(message)
    await session.flush()
    return message


async def get_owned_message(
    session: AsyncSession,
    message_id: UUID,
    user_id: UUID,
    *,
    for_update: bool = False,
) -> tuple[Message, Conversation] | None:
    query = (
        select(Message, Conversation)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Message.id == message_id, Conversation.user_id == user_id)
    )
    if for_update:
        query = query.with_for_update(of=Message)
    row = (await session.execute(query)).one_or_none()
    return row if row is not None else None


async def get_message(session: AsyncSession, message_id: UUID, *, for_update: bool = False) -> Message | None:
    query = select(Message).where(Message.id == message_id)
    if for_update:
        query = query.with_for_update()
    return await session.scalar(query)


async def get_original_user_message(
    session: AsyncSession,
    conversation_id: UUID,
    user_message_id: UUID,
) -> Message | None:
    return await session.scalar(
        select(Message).where(
            Message.id == user_message_id,
            Message.conversation_id == conversation_id,
            Message.role == "USER",
        )
    )


async def latest_assistant_attempt(session: AsyncSession, user_message_id: UUID) -> Message | None:
    return await session.scalar(
        select(Message)
        .where(Message.reply_to_message_id == user_message_id, Message.role == "ASSISTANT")
        .order_by(Message.sequence_number.desc())
        .limit(1)
    )


async def message_page(
    session: AsyncSession,
    conversation_id: UUID,
    page: int,
    page_size: int,
) -> tuple[int, list[Message]]:
    total = await session.scalar(
        select(func.count()).select_from(Message).where(Message.conversation_id == conversation_id)
    )
    rows = await session.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.sequence_number.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return int(total or 0), list(reversed(list(rows)))


async def list_recent_completed_turn_pairs_for_memory(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    before_sequence_number: int,
    limit: int,
) -> tuple[MemoryTurnRow, ...]:
    """Load only the bounded, completed USER/ASSISTANT pairs before the current USER."""
    user = aliased(Message, name="memory_user")
    assistant = aliased(Message, name="memory_assistant")
    rows = await session.execute(
        select(user, assistant)
        .join(assistant, assistant.reply_to_message_id == user.id)
        .where(
            user.conversation_id == conversation_id,
            user.role == "USER",
            user.status == "COMPLETED",
            user.sequence_number < before_sequence_number,
            assistant.conversation_id == conversation_id,
            assistant.role == "ASSISTANT",
            assistant.status == "COMPLETED",
            assistant.sequence_number < before_sequence_number,
        )
        .order_by(user.sequence_number.desc(), assistant.sequence_number.desc())
        .limit(limit)
    )
    return tuple(
        MemoryTurnRow(
            user_message_id=user_row.id,
            assistant_message_id=assistant_row.id,
            user_text=user_row.content,
            assistant_text=assistant_row.content,
            user_sequence_number=user_row.sequence_number,
            assistant_sequence_number=assistant_row.sequence_number,
            conversation_id=user_row.conversation_id,
        )
        for user_row, assistant_row in rows
    )


async def finalize_message(
    session: AsyncSession,
    message: Message,
    *,
    status: str,
    content: str | None,
) -> None:
    message.status = status
    message.content = content
    await session.flush()


async def add_message_citations(
    session: AsyncSession,
    message_id: UUID,
    citations: tuple[ValidatedCitation, ...],
) -> None:
    """Insert unique validated snapshots; transaction ownership stays with the caller."""
    session.add_all([
        MessageCitation(
            message_id=message_id,
            source_label=item.label,
            source_kind=item.source_kind,
            chunk_id=item.chunk_id,
            title=item.title,
            url=item.url,
            domain=item.domain,
            source_type=item.source_type,
            locator=dict(item.locator) if item.locator is not None else None,
            metadata=dict(item.metadata) if item.metadata is not None else None,
        )
        for item in citations
    ])
    await session.flush()


async def add_message_retrievals(session: AsyncSession, message_id: UUID, traces) -> None:
    """Stage selected-tier runtime traces in the caller's Transaction B."""
    session.add_all([
        MessageRetrieval(
            message_id=message_id,
            chunk_id=item.chunk_id,
            rank=item.rank,
            retrieval_score=item.retrieval_score,
            rerank_score=item.rerank_score,
        )
        for item in traces
    ])
    await session.flush()


async def list_message_citations(
    session: AsyncSession,
    message_ids: tuple[UUID, ...] | list[UUID],
) -> dict[UUID, list[MessageCitation]]:
    if not message_ids:
        return {}
    rows = await session.scalars(
        select(MessageCitation)
        .where(MessageCitation.message_id.in_(message_ids))
        .order_by(MessageCitation.created_at, MessageCitation.id)
    )
    result: dict[UUID, list[MessageCitation]] = {message_id: [] for message_id in message_ids}
    for row in rows:
        result.setdefault(row.message_id, []).append(row)
    return result
