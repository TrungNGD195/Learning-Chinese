"""Source metadata and eligibility rules for future ingestion workflows."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator


class DocumentSourceCategory(StrEnum):
    CURRICULUM_MATERIAL = "CURRICULUM_MATERIAL"
    INTERNAL_AUTHORED = "INTERNAL_AUTHORED"


class DocumentSourceLanguage(StrEnum):
    VI = "vi"
    ZH = "zh"
    EN = "en"


SUPPORTED_DOCUMENT_FORMATS = frozenset({"PDF", "DOCX", "TXT", "MD"})


class DocumentSourceMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    source_category: DocumentSourceCategory
    source_origin: str
    source_language: DocumentSourceLanguage
    usage_rights_note: str | None = None

    @field_validator("title", "source_origin")
    @classmethod
    def require_non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


def is_document_ingestion_eligible(
    metadata: DocumentSourceMetadata,
    *,
    input_format: str,
    domain_allowed: bool,
) -> bool:
    """Return whether validated source metadata may enter raw ingestion."""
    if not isinstance(metadata, DocumentSourceMetadata):
        return False
    normalized_format = input_format.strip().upper()
    return domain_allowed and normalized_format in SUPPORTED_DOCUMENT_FORMATS


def is_published_lesson_eligible(lesson_status: str) -> bool:
    """Only published Lessons may enter the internal Lesson knowledge flow."""
    return lesson_status == "PUBLISHED"


def is_document_approved_for_knowledge(review_status: str) -> bool:
    """Check the existing human-review boundary without activating knowledge."""
    return review_status == "APPROVED"
