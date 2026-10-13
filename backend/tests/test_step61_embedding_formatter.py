from uuid import uuid4

import pytest

from app.ai.embeddings.formatter import EmbeddingInputFormatter
from app.ai.embeddings.schemas import EmbeddingChunkContext
from app.core.errors import ApplicationError


def test_document_format_is_deterministic_and_preserves_content_exactly() -> None:
    content = "  exact canonical text\n"
    chunk = EmbeddingChunkContext(uuid4(), 0, content, "DOCUMENT_TEXT", "  Chapter 1  ", "  Title  ", source_type="DOCUMENT", source_document_id=uuid4())
    result = EmbeddingInputFormatter().format(chunk)
    assert result == "Title: Title\nSection: Chapter 1\n\n  exact canonical text\n"
    assert chunk.content == content


def test_document_without_section_and_lesson_context() -> None:
    document = EmbeddingChunkContext(uuid4(), 0, "body", "DOCUMENT_TEXT", document_title="Doc", source_type="DOCUMENT", source_document_id=uuid4())
    lesson_id = uuid4()
    lesson = EmbeddingChunkContext(uuid4(), 0, "vocabulary", "VOCABULARY", lesson_id=lesson_id,
                                   lesson_title="  Greetings  ", hsk_level_number=2,
                                   source_type="LESSON", source_lesson_id=lesson_id, chunk_lesson_id=lesson_id)
    formatter = EmbeddingInputFormatter()
    assert formatter.format(document) == "Title: Doc\n\nbody"
    assert formatter.format(lesson) == "HSK: 2\nLesson: Greetings\nType: VOCABULARY\n\nvocabulary"


def test_missing_or_mismatched_semantic_context_fails_safely() -> None:
    item = EmbeddingChunkContext(uuid4(), 0, "body", "LESSON_GENERAL", lesson_title="Lesson", hsk_level_number=1,
                                 source_type="LESSON", source_lesson_id=uuid4(), chunk_lesson_id=uuid4())
    with pytest.raises(ApplicationError, match="inconsistent"):
        EmbeddingInputFormatter().format(item)


@pytest.mark.parametrize(
    ("content_type", "expected_type"),
    [("GRAMMAR", "GRAMMAR"), ("LESSON_GENERAL", "LESSON_GENERAL")],
)
def test_lesson_formatter_exact_grammar_and_general_serialization(content_type, expected_type):
    chunk_id, lesson_id, source_lesson_id = uuid4(), uuid4(), uuid4()
    content = "  canonical lesson text"
    item = EmbeddingChunkContext(
        chunk_id=chunk_id, chunk_index=17, content=content, content_type=content_type,
        section="must not appear", lesson_id=lesson_id, lesson_title="  Greetings  ",
        hsk_level_number=3, source_type="LESSON", source_lesson_id=source_lesson_id,
        chunk_lesson_id=source_lesson_id,
    )
    result = EmbeddingInputFormatter().format(item)
    assert result == f"HSK: 3\nLesson: Greetings\nType: {expected_type}\n\n  canonical lesson text"
    assert not result.endswith("\n")
    assert item.content == content
    assert str(chunk_id) not in result
    assert str(lesson_id) not in result
    assert "must not appear" not in result
    assert "storage" not in result.lower()


@pytest.mark.parametrize("title", [None, "", " \t "])
def test_document_formatter_rejects_missing_null_or_blank_title_without_fallback(title):
    item = EmbeddingChunkContext(
        chunk_id=uuid4(), chunk_index=0, content="body", content_type="DOCUMENT_TEXT",
        document_title=title, source_type="DOCUMENT", source_document_id=uuid4(),
    )
    with pytest.raises(ApplicationError) as error:
        EmbeddingInputFormatter().format(item)
    assert error.value.code == "EMBEDDING_BUILD_FAILED"
    assert error.value.message == "Required Document context is unavailable."
    assert error.value.details is None
    assert "filename" not in error.value.message.lower()
    assert "storage" not in error.value.message.lower()
