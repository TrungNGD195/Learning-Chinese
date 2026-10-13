import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.citations.parser import parse_citations
from app.conversation import repository
from app.conversation.ai_chat import AIChatProcessingError, AIChatService, ChatRequest
from app.ai.rag.errors import DUPLICATE_RAG_GENERATION, rag_error
from app.ai.rag.schemas import NO_EVIDENCE_CONTENT, RagRunResult, RagRunStatus, RagTierUsed
from app.ai.citations.schemas import CitationValidationResult
from app.conversation.citation_finalization import fail_assistant_without_citations, finalize_validated_assistant
from app.conversation.processing_lock import assistant_processing_lock
from app.core.errors import ApplicationError
from app.database.models import Conversation, Message
from app.database.session import SessionFactory
from app.exercise import service as exercise_service
from app.progress import service as progress_service

logger = logging.getLogger("app.conversation")


def _not_found() -> ApplicationError:
    return ApplicationError("CONVERSATION_NOT_FOUND", "Conversation was not found", status_code=404)


def _deleted() -> ApplicationError:
    return ApplicationError("CONVERSATION_DELETED", "Conversation has been deleted", status_code=410)


def _retry_invalid() -> ApplicationError:
    return ApplicationError("INVALID_MESSAGE_RETRY", "Message retry is not valid", status_code=409)


def _chat_disabled() -> ApplicationError:
    return ApplicationError(
        "AI_CHAT_DISABLED_DURING_TEST",
        "AI chat is disabled during an active periodic test",
        status_code=409,
    )


def _ai_failed(details: dict[str, str]) -> ApplicationError:
    return ApplicationError("AI_RESPONSE_FAILED", "AI response processing failed", details, status_code=502)


def _conversation_payload(conversation: Conversation) -> dict:
    return {
        "id": conversation.id,
        "scope": "LESSON",
        "lesson_id": conversation.lesson_id,
        "title": conversation.title,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
    }


def _message_payload(message: Message, citations: list[dict] | None = None) -> dict:
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "sequence_number": message.sequence_number,
        "role": message.role,
        "content": message.content,
        "status": message.status,
        "reply_to_message_id": message.reply_to_message_id,
        "created_at": message.created_at,
        "citations": citations or [],
    }


def _citation_payloads(message: Message, rows: list) -> list[dict]:
    if message.role != "ASSISTANT" or message.status != "COMPLETED" or not rows:
        return []
    order: dict[str, int] = {}
    if message.content:
        try:
            order = {
                label: index
                for index, label in enumerate(dict.fromkeys(
                    item.label for item in parse_citations(message.content).occurrences
                ))
            }
        except Exception:
            # Persisted snapshots stay readable if legacy content has malformed markers.
            order = {}
    result = []
    for row in sorted(rows, key=lambda item: order.get(item.source_label, len(order))):
        locator = row.locator if isinstance(row.locator, dict) else {}
        result.append({
            "label": row.source_label,
            "source_kind": row.source_kind,
            "title": row.title,
            "source_type": row.source_type,
            "section": locator.get("section") if isinstance(locator.get("section"), str) else None,
            "page_number": locator.get("page_number") if type(locator.get("page_number")) is int else None,
            "url": row.url,
            "domain": row.domain,
        })
    return result


async def create_conversation(session: AsyncSession, user_id: UUID, lesson_id: UUID) -> dict:
    try:
        await progress_service.require_lesson_access(session, user_id, lesson_id)
        conversation = Conversation(user_id=user_id, lesson_id=lesson_id)
        await repository.add_conversation(session, conversation)
        await session.commit()
        return _conversation_payload(conversation)
    except Exception:
        await session.rollback()
        raise


async def list_conversations(
    session: AsyncSession,
    user_id: UUID,
    *,
    page: int,
    page_size: int,
    lesson_id: UUID | None = None,
) -> dict:
    try:
        total, rows = await repository.list_conversations(session, user_id, page, page_size, lesson_id)
        payload = [_conversation_payload(row) for row in rows]
        await session.rollback()
        return {"items": payload, "page": page, "page_size": page_size, "total": total}
    except Exception:
        await session.rollback()
        raise


async def get_conversation(session: AsyncSession, user_id: UUID, conversation_id: UUID) -> dict:
    try:
        conversation = await repository.get_owned_conversation(session, conversation_id, user_id)
        if conversation is None:
            raise _not_found()
        if conversation.deleted_at is not None:
            raise _deleted()
        payload = _conversation_payload(conversation)
        await session.rollback()
        return payload
    except Exception:
        await session.rollback()
        raise


async def rename_conversation(
    session: AsyncSession,
    user_id: UUID,
    conversation_id: UUID,
    title: str | None,
) -> dict:
    try:
        conversation = await repository.get_owned_conversation(session, conversation_id, user_id, for_update=True)
        if conversation is None:
            raise _not_found()
        if conversation.deleted_at is not None:
            raise _deleted()
        await repository.rename_conversation(session, conversation, title)
        await session.commit()
        return _conversation_payload(conversation)
    except Exception:
        await session.rollback()
        raise


async def delete_conversation(session: AsyncSession, user_id: UUID, conversation_id: UUID) -> None:
    try:
        conversation = await repository.get_owned_conversation(session, conversation_id, user_id, for_update=True)
        if conversation is None:
            raise _not_found()
        await repository.soft_delete_conversation(session, conversation)
        await session.commit()
    except Exception:
        await session.rollback()
        raise


async def message_history(
    session: AsyncSession,
    user_id: UUID,
    conversation_id: UUID,
    *,
    page: int,
    page_size: int,
) -> dict:
    try:
        conversation = await repository.get_owned_conversation(session, conversation_id, user_id)
        if conversation is None:
            raise _not_found()
        if conversation.deleted_at is not None:
            raise _deleted()
        total, rows = await repository.message_page(session, conversation_id, page, page_size)
        citation_map = await repository.list_message_citations(session, [row.id for row in rows])
        payload = [_message_payload(row, _citation_payloads(row, citation_map.get(row.id, []))) for row in rows]
        await session.rollback()
        return {"items": payload, "page": page, "page_size": page_size, "total": total}
    except Exception:
        await session.rollback()
        raise


async def _lock_active_conversation(
    session: AsyncSession,
    user_id: UUID,
    conversation_id: UUID,
) -> Conversation:
    conversation = await repository.get_owned_conversation(session, conversation_id, user_id, for_update=True)
    if conversation is None:
        raise _not_found()
    if conversation.deleted_at is not None:
        raise _deleted()
    return conversation


async def _finalize_rag_result(
    session: AsyncSession,
    request: ChatRequest,
    result: RagRunResult,
) -> dict:
    try:
        assistant = await repository.get_message(session, request.assistant_message_id, for_update=True)
        if (
            assistant is None or assistant.role != "ASSISTANT" or assistant.status != "PENDING"
            or assistant.conversation_id != request.conversation_id
            or assistant.reply_to_message_id != request.user_message_id
            or result.assistant_message_id != request.assistant_message_id
        ):
            raise rag_error(DUPLICATE_RAG_GENERATION)
        if result.status is RagRunStatus.NO_EVIDENCE:
            if (
                result.assistant_content != NO_EVIDENCE_CONTENT
                or result.tier_used is not RagTierUsed.NONE
                or result.retrieval_trace or result.validated_citations
            ):
                raise AIChatProcessingError("Invalid no-evidence runtime result")
            await repository.finalize_message(
                session, assistant, status="COMPLETED", content=NO_EVIDENCE_CONTENT
            )
        else:
            if result.status is not RagRunStatus.GROUNDED_ANSWER or not result.validated_citations:
                raise AIChatProcessingError("Invalid grounded runtime result")
            if result.tier_used is RagTierUsed.TRUSTED_EXTERNAL:
                if result.retrieval_trace or any(item.source_kind != "EXTERNAL_URL" for item in result.validated_citations):
                    raise AIChatProcessingError("Invalid external grounded runtime result")
            else:
                if not result.retrieval_trace:
                    raise AIChatProcessingError("Invalid internal grounded runtime result")
                await repository.add_message_retrievals(session, assistant.id, result.retrieval_trace)
            await repository.add_message_citations(session, assistant.id, result.validated_citations)
            await repository.finalize_message(
                session, assistant, status="COMPLETED", content=result.assistant_content
            )
        citation_rows = await repository.list_message_citations(session, [assistant.id])
        payload = _message_payload(
            assistant,
            _citation_payloads(assistant, citation_rows.get(assistant.id, [])),
        )
        await session.commit()
        logger.info("assistant_message_finalized", extra={
            "assistant_message_id": str(request.assistant_message_id),
            "citation_row_count": len(payload["citations"]),
            "finalization_status": "COMPLETED",
            "error_code": None,
        })
        return payload
    except Exception:
        await session.rollback()
        raise


async def _finalize_assistant(
    session: AsyncSession,
    assistant_message_id: UUID,
    *,
    status: str,
    content: str | None,
    citation_result: CitationValidationResult | None = None,
) -> dict:
    """Retain the accepted Step-6.10 short finalizer for focused callers/tests."""
    try:
        assistant = await repository.get_message(session, assistant_message_id, for_update=True)
        if assistant is None or assistant.role != "ASSISTANT" or assistant.status != "PENDING":
            raise _ai_failed({"assistant_message_id": str(assistant_message_id)})
        if status == "COMPLETED" and citation_result is not None:
            await finalize_validated_assistant(
                session, assistant_message=assistant, content=content or "", validation=citation_result,
            )
        elif status == "FAILED":
            await fail_assistant_without_citations(session, assistant_message=assistant)
        else:
            await repository.finalize_message(session, assistant, status=status, content=content)
        citation_rows = await repository.list_message_citations(session, [assistant.id])
        payload = _message_payload(assistant, _citation_payloads(assistant, citation_rows.get(assistant.id, [])))
        await session.commit()
        logger.info("assistant_message_finalized", extra={
            "assistant_message_id": str(assistant_message_id),
            "citation_row_count": len(payload["citations"]),
            "finalization_status": status,
            "error_code": None,
        })
        return payload
    except Exception:
        await session.rollback()
        raise


async def _process_ai_turn(
    session: AsyncSession,
    ai_chat_service: AIChatService,
    request: ChatRequest,
    *,
    user_message_id: UUID | None,
    assistant_message_id: UUID,
) -> tuple[dict | None, ApplicationError | None]:
    try:
        async with assistant_processing_lock(assistant_message_id):
            try:
                async with SessionFactory() as check_session:
                    async with check_session.begin():
                        assistant = await repository.get_message(check_session, assistant_message_id)
                        if (
                            assistant is None or assistant.id != request.assistant_message_id
                            or assistant.conversation_id != request.conversation_id
                            or assistant.role != "ASSISTANT"
                            or assistant.reply_to_message_id != request.user_message_id
                            or assistant.status != "PENDING"
                        ):
                            raise rag_error(DUPLICATE_RAG_GENERATION)
                result = await ai_chat_service.generate_reply(request)
                if not isinstance(result, RagRunResult):
                    raise AIChatProcessingError("AI result must be a RAG runtime result")
                return await _finalize_rag_result(session, request, result), None
            except ApplicationError as exc:
                if exc.code == DUPLICATE_RAG_GENERATION:
                    raise
                logger.warning("assistant_message_processing_failed", extra={
                    "assistant_message_id": str(assistant_message_id),
                    "status": "FAILED", "error_code": exc.code,
                })
                await _mark_assistant_failed(session, assistant_message_id)
                details = {"assistant_message_id": str(assistant_message_id)}
                if user_message_id is not None:
                    details = {"user_message_id": str(user_message_id), **details}
                return None, _ai_failed(details)
            except Exception:
                logger.warning("assistant_message_processing_failed", extra={
                    "assistant_message_id": str(assistant_message_id),
                    "status": "FAILED", "error_code": "AI_RESPONSE_FAILED",
                })
                await _mark_assistant_failed(session, assistant_message_id)
                details = {"assistant_message_id": str(assistant_message_id)}
                if user_message_id is not None:
                    details = {"user_message_id": str(user_message_id), **details}
                return None, _ai_failed(details)
    except ApplicationError as exc:
        if exc.code == DUPLICATE_RAG_GENERATION:
            logger.info("assistant_message_duplicate_processing", extra={
                "assistant_message_id": str(assistant_message_id),
                "lock_acquired": False,
                "duplicate_processing": True,
                "error_code": DUPLICATE_RAG_GENERATION,
            })
            return None, exc
        logger.warning("assistant_message_processing_failed", extra={
            "assistant_message_id": str(assistant_message_id),
            "status": "FAILED", "error_code": exc.code,
        })
        details = {"assistant_message_id": str(assistant_message_id)}
        if user_message_id is not None:
            details = {"user_message_id": str(user_message_id), **details}
        return None, _ai_failed(details)
    except Exception:
        logger.warning("assistant_message_processing_failed", extra={
            "assistant_message_id": str(assistant_message_id),
            "status": "FAILED", "error_code": "AI_RESPONSE_FAILED",
        })
        details = {"assistant_message_id": str(assistant_message_id)}
        if user_message_id is not None:
            details = {"user_message_id": str(user_message_id), **details}
        return None, _ai_failed(details)


async def _mark_assistant_failed(session: AsyncSession, assistant_message_id: UUID) -> None:
    try:
        assistant = await repository.get_message(session, assistant_message_id, for_update=True)
        if assistant is not None and assistant.role == "ASSISTANT" and assistant.status == "PENDING":
            await repository.finalize_message(session, assistant, status="FAILED", content=None)
            await session.commit()
        else:
            await session.rollback()
    except Exception:
        await session.rollback()
        raise


async def send_message(
    session: AsyncSession,
    user_id: UUID,
    conversation_id: UUID,
    content: str,
    ai_chat_service: AIChatService,
) -> dict:
    try:
        conversation = await _lock_active_conversation(session, user_id, conversation_id)
        if await exercise_service.has_active_periodic_test(session, user_id):
            raise _chat_disabled()

        next_sequence = await repository.next_sequence_number(session, conversation.id)
        user_message = await repository.add_message(
            session,
            Message(
                conversation_id=conversation.id,
                sequence_number=next_sequence,
                role="USER",
                content=content,
                status="COMPLETED",
            ),
        )
        assistant = await repository.add_message(
            session,
            Message(
                conversation_id=conversation.id,
                sequence_number=next_sequence + 1,
                role="ASSISTANT",
                content=None,
                status="PENDING",
                reply_to_message_id=user_message.id,
            ),
        )
        await repository.touch_conversation(session, conversation)
        request = ChatRequest(
            user_id=user_id,
            conversation_id=conversation.id,
            lesson_id=conversation.lesson_id,
            user_message_id=user_message.id,
            assistant_message_id=assistant.id,
            content=content,
        )
        user_payload = _message_payload(user_message)
        assistant_id = assistant.id
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    assistant_payload, error = await _process_ai_turn(
        session,
        ai_chat_service,
        request,
        user_message_id=user_message.id,
        assistant_message_id=assistant_id,
    )
    if error is not None:
        raise error
    return {"user_message": user_payload, "assistant_message": assistant_payload}


async def retry_message(
    session: AsyncSession,
    user_id: UUID,
    assistant_message_id: UUID,
    ai_chat_service: AIChatService,
) -> dict:
    try:
        resolved = await repository.get_owned_message(session, assistant_message_id, user_id)
        if resolved is None:
            raise _not_found()
        conversation_id = resolved[1].id
        await session.rollback()

        conversation = await _lock_active_conversation(session, user_id, conversation_id)
        target = await repository.get_message(session, assistant_message_id, for_update=True)
        if target is None or target.conversation_id != conversation.id:
            raise _retry_invalid()
        if target.role != "ASSISTANT" or target.status != "FAILED" or target.reply_to_message_id is None:
            raise _retry_invalid()

        original = await repository.get_original_user_message(
            session,
            conversation.id,
            target.reply_to_message_id,
        )
        if original is None:
            raise _retry_invalid()
        latest = await repository.latest_assistant_attempt(session, original.id)
        if latest is None or latest.id != target.id:
            raise _retry_invalid()
        if await exercise_service.has_active_periodic_test(session, user_id):
            raise _chat_disabled()

        next_sequence = await repository.next_sequence_number(session, conversation.id)
        assistant = await repository.add_message(
            session,
            Message(
                conversation_id=conversation.id,
                sequence_number=next_sequence,
                role="ASSISTANT",
                content=None,
                status="PENDING",
                reply_to_message_id=original.id,
            ),
        )
        await repository.touch_conversation(session, conversation)
        request = ChatRequest(
            user_id=user_id,
            conversation_id=conversation.id,
            lesson_id=conversation.lesson_id,
            user_message_id=original.id,
            assistant_message_id=assistant.id,
            content=original.content,
        )
        new_assistant_id = assistant.id
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    response, error = await _process_ai_turn(
        session,
        ai_chat_service,
        request,
        user_message_id=None,
        assistant_message_id=new_assistant_id,
    )
    if error is not None:
        raise error
    return response
