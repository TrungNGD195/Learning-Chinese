from uuid import uuid4
import logging

import pytest

from app.ai.citations.errors import (
    CITATION_EXTERNAL_URL_INVALID,
    CITATION_FORMAT_INVALID,
    CITATION_MISSING,
    CITATION_UNKNOWN_SOURCE,
)
from app.ai.citations.schemas import ExternalCitationSource, InternalCitationSource
from app.ai.citations.validator import CitationValidator, TrustedExternalDomains
from app.core.errors import ApplicationError


def internal(label="S1", *, page_number=4, section="Word order"):
    return InternalCitationSource(label, uuid4(), "DOCUMENT", "Grammar", page_number, section)


def test_internal_citations_use_trusted_typed_metadata_and_dedupe_occurrences():
    src3 = internal("S3")
    src1 = internal("S1", page_number=None, section=None)
    result = CitationValidator().validate(
        text="A [S3], B [S1], repeat [S3]",
        sources={"S3": src3, "S1": src1},
        citation_required=True,
    )
    assert result.text == "A [S3], B [S1], repeat [S3]"
    assert result.cited_labels == ("S3", "S1")
    assert result.occurrence_count == 3 and result.citation_count == 2
    assert result.citations[0].chunk_id == src3.chunk_id
    assert result.citations[0].locator == {"page_number": 4, "section": "Word order"}
    assert result.citations[1].locator is None


def test_lesson_and_external_source_snapshot_fields():
    lesson = InternalCitationSource("S1", uuid4(), "LESSON", "HSK lesson", 2, "Greetings")
    external = ExternalCitationSource("S2", "Reference", "https://example.edu/page")
    validator = CitationValidator(TrustedExternalDomains(frozenset({"example.edu"})))
    result = validator.validate(text="[S1] [S2]", sources={"S1": lesson, "S2": external}, citation_required=True)
    assert result.citations[0].source_type == "LESSON"
    assert result.citations[1].url == external.url and result.citations[1].domain == "example.edu"


@pytest.mark.parametrize(("text", "sources", "required", "code"), [
    ("no marker", {}, True, CITATION_MISSING),
    ("no marker", {}, False, None),
    ("bad [S0]", {}, False, CITATION_FORMAT_INVALID),
    ("[S9]", {"S1": internal()}, False, CITATION_UNKNOWN_SOURCE),
])
def test_requirement_format_and_unknown_error_semantics(text, sources, required, code):
    if code is None:
        result = CitationValidator().validate(text=text, sources=sources, citation_required=required)
        assert result.status == "VALID" and result.citations == ()
    else:
        with pytest.raises(ApplicationError) as error:
            CitationValidator().validate(text=text, sources=sources, citation_required=required)
        assert error.value.code == code


@pytest.mark.parametrize("url", ["http://example.edu", "javascript:alert(1)", "data:text/plain,x", "file:///secret", "https://evil.example"])
def test_external_citation_requires_https_and_exact_trusted_hostname(url):
    validator = CitationValidator(TrustedExternalDomains(frozenset({"example.edu"})))
    with pytest.raises(ApplicationError) as error:
        validator.validate(text="[S1]", sources={"S1": ExternalCitationSource("S1", "x", url)}, citation_required=True)
    assert error.value.code == CITATION_EXTERNAL_URL_INVALID


@pytest.mark.parametrize("url", ["https://example.edu", "https:///missing-host"])
def test_default_empty_trust_policy_rejects_external_sources(url):
    with pytest.raises(ApplicationError) as error:
        CitationValidator().validate(
            text="[S1]",
            sources={"S1": ExternalCitationSource("S1", "Reference", url)},
            citation_required=True,
        )
    assert error.value.code == CITATION_EXTERNAL_URL_INVALID


@pytest.mark.parametrize("source_map", [
    {"S1": InternalCitationSource("S2", uuid4(), "DOCUMENT", "Title")},
    {"S1": InternalCitationSource("S1", uuid4(), "DOCUMENT", "   ")},
    {"S1": InternalCitationSource("S1", uuid4(), "UNSUPPORTED", "Title")},
    {"S1": InternalCitationSource("S1", uuid4(), "DOCUMENT", "Title", 0)},
    {"S1": InternalCitationSource("S1", uuid4(), "DOCUMENT", "Title", section="  ")},
])
def test_malformed_trusted_source_mapping_fails_resolution(source_map):
    from app.ai.citations.errors import CITATION_SOURCE_RESOLUTION_FAILED

    with pytest.raises(ApplicationError) as error:
        CitationValidator().validate(text="[S1]", sources=source_map, citation_required=True)
    assert error.value.code == CITATION_SOURCE_RESOLUTION_FAILED


def test_model_markdown_url_is_not_a_validated_citation():
    result = CitationValidator().validate(
        text="[S1](https://evil.example)",
        sources={"S1": ExternalCitationSource("S1", "Application title", "https://example.edu/trusted")},
        citation_required=False,
    )
    assert result.occurrence_count == 0
    assert result.cited_labels == ()
    assert result.citations == ()
    with pytest.raises(ApplicationError) as error:
        CitationValidator().validate(
            text="[1]", sources={}, citation_required=True,
        )
    assert error.value.code == CITATION_MISSING


def test_validator_logs_only_safe_metadata(caplog):
    caplog.set_level(logging.INFO, logger="app.ai.citations")
    validator = CitationValidator(TrustedExternalDomains(frozenset({"example.edu"})))
    validator.validate(
        text="SENTINEL_GENERATED_ANSWER [S1]",
        sources={"S1": ExternalCitationSource(
            "S1", "SENTINEL_SOURCE_CONTENT", "https://example.edu/page?key=SENTINEL_URL_SECRET",
        )},
        citation_required=True,
    )
    assert "citation_validation_completed" in caplog.text
    for sentinel in ("SENTINEL_GENERATED_ANSWER", "SENTINEL_SOURCE_CONTENT", "SENTINEL_URL_SECRET", "SENTINEL_DB_EXCEPTION"):
        assert sentinel not in caplog.text


def test_prompt_source_map_adapter_copies_only_typed_citation_fields():
    from app.ai.citations.validator import sources_from_prompt_package
    from tests.step67_fixtures import prompt_package

    package = prompt_package()
    sources = sources_from_prompt_package(package)
    assert set(sources) == set(package.source_map)
    for label, source in sources.items():
        assert source.label == label
        assert not hasattr(source, "locator_metadata")
