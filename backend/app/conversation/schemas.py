from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConversationCreateRequest(StrictRequest):
    lesson_id: UUID


class ConversationPatchRequest(StrictRequest):
    title: str | None

    @field_validator("title")
    @classmethod
    def trim_and_validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not 1 <= len(value) <= 200:
            raise ValueError("title must contain between 1 and 200 characters")
        return value


class ConversationResponse(BaseModel):
    id: UUID
    scope: Literal["LESSON"] = "LESSON"
    lesson_id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class ConversationPage(BaseModel):
    items: list[ConversationResponse]
    page: int
    page_size: int
    total: int


class MessageCreateRequest(StrictRequest):
    content: str

    @field_validator("content")
    @classmethod
    def trim_and_validate_content(cls, value: str) -> str:
        value = value.strip()
        if not 1 <= len(value) <= 4000:
            raise ValueError("content must contain between 1 and 4000 characters")
        return value


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    sequence_number: int
    role: Literal["USER", "ASSISTANT"]
    content: str | None
    status: Literal["PENDING", "COMPLETED", "FAILED"]
    reply_to_message_id: UUID | None
    created_at: datetime
    citations: list["CitationResponse"]


class CitationResponse(BaseModel):
    label: str
    source_kind: Literal["INTERNAL_CHUNK", "EXTERNAL_URL"]
    title: str
    source_type: Literal["DOCUMENT", "LESSON"] | None = Field(...)
    section: str | None = Field(...)
    page_number: int | None = Field(..., gt=0)
    url: str | None = Field(...)
    domain: str | None = Field(...)


class MessagePage(BaseModel):
    items: list[MessageResponse]
    page: int
    page_size: int
    total: int


class SendMessageResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
