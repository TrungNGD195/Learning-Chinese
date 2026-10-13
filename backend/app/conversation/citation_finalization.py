from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.citations.errors import CITATION_VALIDATION_FAILED, citation_error
from app.ai.citations.schemas import CitationValidationResult
from app.conversation import repository
from app.database.models import Message


async def finalize_validated_assistant(
    session: AsyncSession,
    *,
    assistant_message: Message,
    content: str,
    validation: CitationValidationResult,
) -> None:
    """Stage a validated Assistant result in the caller's transaction; never commit."""
    if (
        assistant_message.role != "ASSISTANT"
        or assistant_message.status != "PENDING"
        or not isinstance(content, str)
        or not content.strip()
        or validation.status != "VALID"
        or validation.text != content
    ):
        raise citation_error(CITATION_VALIDATION_FAILED)
    await repository.add_message_citations(session, assistant_message.id, validation.citations)
    await repository.finalize_message(session, assistant_message, status="COMPLETED", content=content)


async def fail_assistant_without_citations(
    session: AsyncSession,
    *,
    assistant_message: Message,
) -> None:
    """Stage failure in a caller-owned short transaction without persisting answer text."""
    if assistant_message.role != "ASSISTANT" or assistant_message.status != "PENDING":
        raise citation_error(CITATION_VALIDATION_FAILED)
    await repository.finalize_message(session, assistant_message, status="FAILED", content=None)
