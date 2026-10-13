from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.current_user import get_current_user
from app.conversation import service
from app.conversation.ai_chat import AIChatService, get_ai_chat_service
from app.conversation.schemas import (
    ConversationCreateRequest,
    ConversationPage,
    ConversationPatchRequest,
    ConversationResponse,
    MessageCreateRequest,
    MessagePage,
    MessageResponse,
    SendMessageResponse,
)
from app.database.models import User
from app.database.session import get_db_session

router = APIRouter(tags=["conversations"])


@router.post("/conversations", status_code=201, response_model=ConversationResponse)
async def create_conversation(
    payload: ConversationCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    return await service.create_conversation(session, current_user.id, payload.lesson_id)


@router.get("/me/conversations", response_model=ConversationPage)
async def list_conversations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    lesson_id: UUID | None = None,
    scope: Literal["LESSON"] | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    del scope  # LESSON is the only V0 scope; it is an API filter, not persisted.
    return await service.list_conversations(
        session,
        current_user.id,
        page=page,
        page_size=page_size,
        lesson_id=lesson_id,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    return await service.get_conversation(session, current_user.id, conversation_id)


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def rename_conversation(
    conversation_id: UUID,
    payload: ConversationPatchRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    return await service.rename_conversation(session, current_user.id, conversation_id, payload.title)


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    await service.delete_conversation(session, current_user.id, conversation_id)
    return Response(status_code=204)


@router.get("/conversations/{conversation_id}/messages", response_model=MessagePage)
async def message_history(
    conversation_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    return await service.message_history(
        session,
        current_user.id,
        conversation_id,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    status_code=201,
    response_model=SendMessageResponse,
)
async def send_message(
    conversation_id: UUID,
    payload: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    ai_chat_service: AIChatService = Depends(get_ai_chat_service),
):
    return await service.send_message(
        session,
        current_user.id,
        conversation_id,
        payload.content,
        ai_chat_service,
    )


@router.post(
    "/messages/{assistant_message_id}/retry",
    status_code=201,
    response_model=MessageResponse,
)
async def retry_message(
    assistant_message_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    ai_chat_service: AIChatService = Depends(get_ai_chat_service),
):
    return await service.retry_message(session, current_user.id, assistant_message_id, ai_chat_service)
