from datetime import datetime
from pathlib import PurePosixPath, PureWindowsPath
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RawArtifactRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_type: Literal["DOCUMENT", "LESSON"]
    source_id: UUID
    storage_key: str
    file_format: str
    mime_type: str
    file_size_bytes: int
    content_hash: str


class ParsedArtifactRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    parsing_run_id: UUID
    source_type: Literal["DOCUMENT", "LESSON"]
    source_id: UUID
    storage_key: str
    schema_version: Literal["parsed_cleaned_artifact/v1"]


class TransformedArtifactRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    transformation_run_id: UUID
    source_type: Literal["DOCUMENT", "LESSON"]
    source_id: UUID
    storage_key: str
    schema_version: Literal["transformed_document/v1"]


class DocumentRawIngestionResponse(BaseModel):
    id: UUID
    original_filename: str
    file_type: str
    mime_type: str
    file_size_bytes: int
    content_hash: str
    title: str
    source_category: str
    source_origin: str
    source_language: str
    usage_rights_note: str | None
    processing_status: str
    review_status: str
    created_at: datetime


DocumentProcessingStatus = Literal["UPLOADED", "PROCESSING", "PREVIEW_READY", "FAILED"]
DocumentReviewStatus = Literal["PENDING", "APPROVED", "REJECTED"]
DocumentSourceCategoryValue = Literal["CURRICULUM_MATERIAL", "INTERNAL_AUTHORED"]
DocumentSourceLanguageValue = Literal["vi", "zh", "en"]


class DocumentAdminListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    file_type: str
    mime_type: str | None
    file_size_bytes: int | None
    title: str | None
    source_category: DocumentSourceCategoryValue | None
    source_origin: str | None
    source_language: DocumentSourceLanguageValue | None
    usage_rights_note: str | None
    processing_status: DocumentProcessingStatus
    review_status: DocumentReviewStatus
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None


class DocumentAdminDetailResponse(DocumentAdminListItemResponse):
    knowledge_retry_available: bool


class DocumentAdminPageResponse(BaseModel):
    items: list[DocumentAdminListItemResponse]
    page: int
    page_size: int
    total: int


def validate_storage_key(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value or "\\" in value or path.is_absolute()
        or PureWindowsPath(value).drive
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise ValueError("Invalid storage key")
    if len(value) > 512:
        raise ValueError("Invalid storage key")
    return value


RawArtifactRef.model_rebuild()
