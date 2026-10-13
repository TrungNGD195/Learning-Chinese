from dataclasses import replace
from uuid import uuid4

import pytest

from app.ai.reranking.errors import reranking_error
from app.ai.reranking.formatter import RerankPassageFormatter
from app.ai.retrieval.schemas import RetrievalCandidate


def document_candidate(**overrides) -> RetrievalCandidate:
    values = dict(
        rank=1,
        chunk_id=uuid4(),
        chunk_index=2,
        content="  Source-derived text.  ",
        content_type="DOCUMENT_TEXT",
        knowledge_version_id=uuid4(),
        knowledge_source_id=uuid4(),
        source_type="DOCUMENT",
        source_document_id=uuid4(),
        source_lesson_id=None,
        chunk_lesson_id=None,
        document_title="Chinese Basics",
        lesson_title=None,
        hsk_level_number=None,
        page_number=8,
        section="Chapter 2 / Greetings",
        locator_metadata={"storage_key": "private/path.pdf"},
        distance=0.2,
        retrieval_score=0.8,
    )
    values.update(overrides)
    return RetrievalCandidate(**values)


def lesson_candidate(**overrides) -> RetrievalCandidate:
    candidate = document_candidate(
        content_type="VOCABULARY",
        source_type="LESSON",
        source_document_id=None,
        source_lesson_id=uuid4(),
        document_title=None,
        lesson_title="First Words",
        hsk_level_number=1,
        page_number=None,
        section=None,
    )
    return replace(candidate, **overrides)


def test_document_passage_is_deterministic_and_omits_absent_section_and_metadata():
    candidate = document_candidate(section=None)

    expected = "Title: Chinese Basics\n\n  Source-derived text.  "
    assert RerankPassageFormatter.format(candidate) == expected
    assert RerankPassageFormatter.format(candidate) == expected
    assert "Section:" not in expected
    assert "8" not in expected
    assert str(candidate.chunk_id) not in expected
    assert "0.8" not in expected
    assert "private/path.pdf" not in expected


def test_document_passage_includes_title_optional_section_and_original_content():
    candidate = document_candidate()

    assert RerankPassageFormatter.format(candidate) == (
        "Title: Chinese Basics\nSection: Chapter 2 / Greetings\n\n"
        "  Source-derived text.  "
    )
    assert candidate.content == "  Source-derived text.  "


def test_lesson_passage_contains_only_frozen_semantic_fields():
    candidate = lesson_candidate()

    assert RerankPassageFormatter.format(candidate) == (
        "HSK: 1\nLesson: First Words\nType: VOCABULARY\n\n"
        "  Source-derived text.  "
    )
    assert str(candidate.chunk_id) not in RerankPassageFormatter.format(candidate)


@pytest.mark.parametrize(
    "candidate",
    [
        document_candidate(content="  "),
        document_candidate(document_title=None),
        document_candidate(section="  "),
        lesson_candidate(lesson_title=None),
        lesson_candidate(hsk_level_number=None),
        document_candidate(source_type="OTHER"),
    ],
)
def test_malformed_candidate_fails_without_silently_dropping_it(candidate):
    with pytest.raises(Exception) as caught:
        RerankPassageFormatter.format(candidate)

    assert getattr(caught.value, "code", None) == "INVALID_RERANK_INPUT"
