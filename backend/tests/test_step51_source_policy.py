from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.ingestion.source_policy import (
    SUPPORTED_DOCUMENT_FORMATS,
    DocumentSourceCategory,
    DocumentSourceMetadata,
    is_document_approved_for_knowledge,
    is_document_ingestion_eligible,
    is_published_lesson_eligible,
)


def metadata(**overrides) -> DocumentSourceMetadata:
    values = {
        "title": "HSK vocabulary notes",
        "source_category": "CURRICULUM_MATERIAL",
        "source_origin": "HSK1 textbook, unit 1",
        "source_language": "zh",
    }
    values.update(overrides)
    return DocumentSourceMetadata.model_validate(values)


@pytest.mark.parametrize(
    "category",
    [DocumentSourceCategory.CURRICULUM_MATERIAL, DocumentSourceCategory.INTERNAL_AUTHORED],
)
def test_frozen_source_categories_are_accepted(category: DocumentSourceCategory) -> None:
    assert metadata(source_category=category).source_category is category


def test_unsupported_source_category_is_rejected() -> None:
    with pytest.raises(ValidationError):
        metadata(source_category="REFERENCE")


@pytest.mark.parametrize("language", ["vi", "zh", "en"])
def test_frozen_source_languages_are_accepted(language: str) -> None:
    assert metadata(source_language=language).source_language.value == language


def test_unsupported_source_language_is_rejected() -> None:
    with pytest.raises(ValidationError):
        metadata(source_language="fr")


@pytest.mark.parametrize("field", ["title", "source_origin"])
@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_required_metadata_must_not_be_blank(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        metadata(**{field: value})


@pytest.mark.parametrize("field", ["title", "source_origin"])
def test_required_metadata_cannot_be_omitted(field: str) -> None:
    values = {
        "title": "HSK vocabulary notes",
        "source_category": "INTERNAL_AUTHORED",
        "source_origin": "Team-authored note",
        "source_language": "vi",
    }
    del values[field]
    with pytest.raises(ValidationError):
        DocumentSourceMetadata.model_validate(values)


def test_usage_rights_note_is_optional_and_no_extra_provenance_is_defined() -> None:
    contract = metadata()
    assert contract.usage_rights_note is None
    assert set(DocumentSourceMetadata.model_fields) == {
        "title", "source_category", "source_origin", "source_language", "usage_rights_note"
    }
    with pytest.raises(ValidationError):
        metadata(trust_score=1)


def test_only_supported_v0_document_formats_are_eligible() -> None:
    assert SUPPORTED_DOCUMENT_FORMATS == {"PDF", "DOCX", "TXT", "MD"}
    source = metadata()
    for input_format in SUPPORTED_DOCUMENT_FORMATS:
        assert is_document_ingestion_eligible(source, input_format=input_format, domain_allowed=True)
    assert not is_document_ingestion_eligible(source, input_format="HTML", domain_allowed=True)
    assert not is_document_ingestion_eligible(source, input_format="URL", domain_allowed=True)


def test_domain_decision_is_explicit_and_never_classified_here() -> None:
    source = metadata()
    assert not is_document_ingestion_eligible(source, input_format="PDF", domain_allowed=False)
    assert not hasattr(__import__("app.ingestion.source_policy", fromlist=["*"]), "classify_domain")


def test_non_source_runtime_objects_cannot_enter_document_policy() -> None:
    runtime_record = SimpleNamespace(status="COMPLETED", content="learner answer")
    assert not is_document_ingestion_eligible(runtime_record, input_format="TXT", domain_allowed=True)  # type: ignore[arg-type]


@pytest.mark.parametrize("status", ["DRAFT", "ARCHIVED"])
def test_only_published_lesson_is_eligible(status: str) -> None:
    assert not is_published_lesson_eligible(status)


def test_published_lesson_is_eligible() -> None:
    assert is_published_lesson_eligible("PUBLISHED")


@pytest.mark.parametrize("review_status", ["PENDING", "REJECTED"])
def test_pending_or_rejected_document_is_not_approved(review_status: str) -> None:
    assert not is_document_approved_for_knowledge(review_status)


def test_approval_helper_only_checks_human_review_boundary() -> None:
    review_state = SimpleNamespace(review_status="APPROVED")
    assert is_document_approved_for_knowledge(review_state.review_status)
    assert review_state.review_status == "APPROVED"
