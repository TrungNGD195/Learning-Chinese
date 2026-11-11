from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

RequiredText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30000)]


class ReadingCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    order_index: int = Field(ge=1)
    title: RequiredText
    content: RequiredText
    pinyin: str | None = Field(default=None, max_length=30000)
    vietnamese_translation: str | None = Field(default=None, max_length=30000)
    source_reference: str | None = Field(default=None, max_length=1000)


class ReadingResponse(BaseModel):
    id: UUID
    order_index: int
    title: str
    content: str
    pinyin: str | None
    vietnamese_translation: str | None
    source_reference: str | None
    version: int


class ReadingCompleteRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: int = Field(ge=1)


class ReadingProgressResponse(BaseModel):
    id: UUID
    completed: bool
    completed_at: datetime | None


class ReadingCompleteResponse(BaseModel):
    completed_at: datetime
    theory_completed_at: datetime | None
