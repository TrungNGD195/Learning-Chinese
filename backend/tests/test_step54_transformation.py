from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.ingestion.parsing.base import ParsingFailure
from app.ingestion.transformation.document_transformer import transform_document
from app.ingestion.transformation.lesson_transformer import transform_lesson
from app.ingestion.transformation.models import (
    CanonicalBlock,
    ParsedCleanedArtifactInput,
    SourceMetadataSnapshot,
    TransformedDocument,
)


def document(units, *, source_id=None):
    source_id = source_id or uuid4()
    return ParsedCleanedArtifactInput(
        schema_version="parsed_cleaned_artifact/v1", source_type="DOCUMENT", source_id=source_id,
        raw_content_hash="a" * 64, parser_name="test", parser_version="v1",
        cleaning_strategy="test", cleaning_version="v1", units=units,
    )


def metadata(source_id):
    return SourceMetadataSnapshot(
        source_type="DOCUMENT", source_id=source_id, title="Snapshot title",
        source_language="zh", source_category="CURRICULUM_MATERIAL", source_origin="Imported",
        usage_rights_note="Use for internal study", original_filename="source.md",
    )


def test_document_formats_map_to_ordered_canonical_blocks_without_loss_or_splitting():
    artifact = document([
        {"order": 0, "text": "PDF page", "source_locator": {"kind": "PDF_PAGE", "page_number": 1}},
        {"order": 1, "text": "DOCX para", "source_locator": {"kind": "DOCX_PARAGRAPH", "block_index": 0}},
        {"order": 2, "text": "TXT text", "source_locator": {"kind": "TEXT_BLOCK", "block_index": 0}},
        {"order": 3, "text": "Heading", "source_locator": {"kind": "MARKDOWN_BLOCK", "block_index": 0, "block_kind": "HEADING", "heading_level": 1}},
        {"order": 4, "text": "Child", "source_locator": {"kind": "MARKDOWN_BLOCK", "block_index": 1, "block_kind": "HEADING", "heading_level": 2}},
        {"order": 5, "text": "Paragraph", "source_locator": {"kind": "MARKDOWN_BLOCK", "block_index": 2, "block_kind": "PARAGRAPH"}},
        {"order": 6, "text": "first", "source_locator": {"kind": "MARKDOWN_BLOCK", "block_index": 3, "block_kind": "LIST_ITEM", "list_kind": "unordered"}},
        {"order": 7, "text": "second", "source_locator": {"kind": "MARKDOWN_BLOCK", "block_index": 4, "block_kind": "LIST_ITEM", "list_kind": "unordered"}},
        {"order": 8, "text": "print('x')", "source_locator": {"kind": "MARKDOWN_BLOCK", "block_index": 5, "block_kind": "CODE_BLOCK"}},
    ])
    result = transform_document(artifact, metadata(artifact.source_id))
    assert [block.block_kind for block in result.blocks] == [
        "PARAGRAPH", "PARAGRAPH", "PARAGRAPH", "HEADING", "HEADING", "PARAGRAPH", "LIST", "CODE_BLOCK",
    ]
    assert result.blocks[4].section_path == ["Heading", "Child"]
    assert result.blocks[5].section_path == ["Heading", "Child"]
    assert result.blocks[0].section_path == []
    assert result.blocks[1].section_path == []
    assert result.blocks[2].section_path == []
    assert result.blocks[6].structured_data.model_dump(mode="json") == {"list_kind": "unordered", "items": ["first", "second"]}
    assert [block.order for block in result.blocks] == list(range(len(result.blocks)))
    assert result.provenance.model_dump(mode="json", exclude_none=True) == {
        "source_origin": "Imported", "usage_rights_note": "Use for internal study", "original_filename": "source.md",
    }


def test_empty_text_is_dropped_but_short_duplicate_and_long_units_are_kept():
    repeated = "same"
    long_text = "long content " * 400
    artifact = document([
        {"order": 0, "text": "", "source_locator": {"kind": "TEXT_BLOCK", "block_index": 0}},
        {"order": 1, "text": "x", "source_locator": {"kind": "TEXT_BLOCK", "block_index": 1}},
        {"order": 2, "text": repeated, "source_locator": {"kind": "TEXT_BLOCK", "block_index": 2}},
        {"order": 3, "text": repeated, "source_locator": {"kind": "TEXT_BLOCK", "block_index": 3}},
        {"order": 4, "text": long_text, "source_locator": {"kind": "TEXT_BLOCK", "block_index": 4}},
    ])
    result = transform_document(artifact, metadata(artifact.source_id))
    assert [block.text for block in result.blocks] == ["x", repeated, repeated, long_text]
    assert [block.order for block in result.blocks] == [0, 1, 2, 3]
    assert all(block.content_type != block.block_kind for block in result.blocks)


def test_markdown_list_groups_break_for_incompatible_kind_and_interruption():
    artifact = document([
        {"order": 0, "text": "one", "source_locator": {"kind": "MARKDOWN_BLOCK", "block_index": 0, "block_kind": "LIST_ITEM", "list_kind": "unordered"}},
        {"order": 1, "text": "two", "source_locator": {"kind": "MARKDOWN_BLOCK", "block_index": 1, "block_kind": "LIST_ITEM", "list_kind": "unordered"}},
        {"order": 2, "text": "three", "source_locator": {"kind": "MARKDOWN_BLOCK", "block_index": 2, "block_kind": "LIST_ITEM", "list_kind": "ordered"}},
        {"order": 3, "text": "between", "source_locator": {"kind": "MARKDOWN_BLOCK", "block_index": 3, "block_kind": "PARAGRAPH"}},
        {"order": 4, "text": "four", "source_locator": {"kind": "MARKDOWN_BLOCK", "block_index": 4, "block_kind": "LIST_ITEM", "list_kind": "ordered"}},
    ])
    result = transform_document(artifact, metadata(artifact.source_id))
    assert [block.block_kind for block in result.blocks] == ["LIST", "LIST", "PARAGRAPH", "LIST"]
    assert [block.structured_data.items for block in result.blocks if block.block_kind == "LIST"] == [
        ["one", "two"], ["three"], ["four"],
    ]


def test_docx_rows_remain_truthful_grouped_rows_and_do_not_split_tabs():
    artifact = document([
        {"order": 0, "text": "甲\tfirst\tgloss", "source_locator": {"kind": "DOCX_TABLE_ROW", "block_index": 4, "table_index": 2, "row_index": 0}},
        {"order": 1, "text": "乙\tsecond", "source_locator": {"kind": "DOCX_TABLE_ROW", "block_index": 4, "table_index": 2, "row_index": 1}},
    ])
    block = transform_document(artifact, metadata(artifact.source_id)).blocks[0]
    assert block.block_kind == "TABLE"
    assert block.structured_data.model_dump(mode="json") == {"table_index": 2, "rows": [
        {"row_index": 0, "text": "甲\tfirst\tgloss"}, {"row_index": 1, "text": "乙\tsecond"},
    ]}
    assert "cells" not in str(block.model_dump(mode="json"))
    assert block.text == "甲\tfirst\tgloss\n乙\tsecond"


@pytest.mark.parametrize("locator", [
    {"kind": "PDF_PAGE", "page_number": 0},
    {"kind": "PDF_PAGE", "page_number": "1"},
    {"kind": "DOCX_TABLE_ROW", "table_index": -1, "row_index": 0},
    {"kind": "MARKDOWN_BLOCK", "block_index": 0, "block_kind": "HEADING", "heading_level": 7},
])
def test_invalid_source_locators_fail_explicitly(locator):
    artifact = document([{"order": 0, "text": "x", "source_locator": locator}])
    with pytest.raises(ParsingFailure) as raised:
        transform_document(artifact, metadata(artifact.source_id))
    assert raised.value.code == "INVALID_SOURCE_LOCATOR"


def test_unknown_document_content_type_is_rejected():
    artifact = document([{"order": 0, "text": "x", "source_locator": {"kind": "OCR_PAGE"}}])
    with pytest.raises(ParsingFailure) as raised:
        transform_document(artifact, metadata(artifact.source_id))
    assert raised.value.code == "INVALID_SOURCE_LOCATOR"
    markdown = document([{"order": 0, "text": "x", "source_locator": {"kind": "MARKDOWN_BLOCK", "block_index": 0, "block_kind": "HTML"}}])
    with pytest.raises(ParsingFailure) as raised:
        transform_document(markdown, metadata(markdown.source_id))
    assert raised.value.code == "UNSUPPORTED_CONTENT_TYPE"


def test_required_document_metadata_has_no_fallback():
    artifact = document([])
    incomplete = metadata(artifact.source_id).model_copy(update={"title": None, "source_origin": None})
    with pytest.raises(ParsingFailure) as raised:
        transform_document(artifact, incomplete)
    assert raised.value.code == "TRANSFORMATION_FAILED"


def test_lesson_groups_fields_in_source_order_with_frozen_labels_and_title_snapshot():
    lesson_id, vocab_id, grammar_id = uuid4(), uuid4(), uuid4()
    units = [
        {"order": 0, "text": "Tiếng Trung cơ bản", "source_locator": {"kind": "LESSON_FIELD", "section": "LESSON", "entity_id": str(lesson_id), "field": "title"}},
        {"order": 1, "text": "Giới thiệu", "source_locator": {"kind": "LESSON_FIELD", "section": "LESSON", "entity_id": str(lesson_id), "field": "description"}},
        {"order": 2, "text": "你好", "source_locator": {"kind": "LESSON_FIELD", "section": "VOCABULARY", "entity_id": str(vocab_id), "field": "hanzi", "order_index": 0}},
        {"order": 3, "text": "nǐ hǎo", "source_locator": {"kind": "LESSON_FIELD", "section": "VOCABULARY", "entity_id": str(vocab_id), "field": "pinyin", "order_index": 0}},
        {"order": 4, "text": "xin chào", "source_locator": {"kind": "LESSON_FIELD", "section": "VOCABULARY", "entity_id": str(vocab_id), "field": "vietnamese_meaning", "order_index": 0}},
        {"order": 5, "text": "Chào hỏi", "source_locator": {"kind": "LESSON_FIELD", "section": "GRAMMAR", "entity_id": str(grammar_id), "field": "name", "order_index": 0}},
        {"order": 6, "text": "A + B", "source_locator": {"kind": "LESSON_FIELD", "section": "GRAMMAR", "entity_id": str(grammar_id), "field": "structure", "order_index": 0}},
    ]
    artifact = ParsedCleanedArtifactInput(
        schema_version="parsed_cleaned_artifact/v1", source_type="LESSON", source_id=lesson_id,
        raw_content_hash="b" * 64, parser_name="raw_lesson_snapshot", parser_version="v1",
        cleaning_strategy="basic_text_cleaning", cleaning_version="v1", units=units,
    )
    snapshot = SourceMetadataSnapshot(source_type="LESSON", source_id=lesson_id, title="Tiếng Trung cơ bản")
    result = transform_lesson(artifact, snapshot)
    assert result.title == "Tiếng Trung cơ bản"
    assert result.source_language is result.source_category is None
    assert [block.block_kind for block in result.blocks] == ["LESSON_GENERAL", "VOCABULARY_ITEM", "GRAMMAR_SECTION"]
    assert result.blocks[0].text == "Giới thiệu"
    assert result.blocks[1].text == "Từ: 你好\nPinyin: nǐ hǎo\nNghĩa: xin chào"
    assert result.blocks[2].text == "Ngữ pháp: Chào hỏi\nCấu trúc: A + B"
    assert result.blocks[2].section_path == ["Grammar", "Chào hỏi"]
    assert result.blocks[0].source_locator.model_dump(mode="json", exclude_none=True)["fields"] == [units[1]["source_locator"]]


def test_lesson_duplicate_field_locator_is_rejected_and_no_empty_general_block():
    lesson_id = uuid4()
    loc = {"kind": "LESSON_FIELD", "section": "LESSON", "entity_id": str(lesson_id), "field": "title"}
    artifact = ParsedCleanedArtifactInput(
        schema_version="parsed_cleaned_artifact/v1", source_type="LESSON", source_id=lesson_id,
        raw_content_hash="c" * 64, parser_name="raw_lesson_snapshot", parser_version="v1",
        cleaning_strategy="basic_text_cleaning", cleaning_version="v1",
        units=[{"order": 0, "text": "Title", "source_locator": loc}],
    )
    snapshot = SourceMetadataSnapshot(source_type="LESSON", source_id=lesson_id, title="Title")
    assert transform_lesson(artifact, snapshot).blocks == []
    duplicate = artifact.model_copy(update={"units": [*artifact.units, artifact.units[0].model_copy(update={"order": 1})]})
    with pytest.raises(ParsingFailure) as raised:
        transform_lesson(duplicate, snapshot)
    assert raised.value.code == "INVALID_SOURCE_LOCATOR"


def test_lesson_unknown_section_is_not_silently_discarded():
    lesson_id = uuid4()
    artifact = ParsedCleanedArtifactInput(
        schema_version="parsed_cleaned_artifact/v1", source_type="LESSON", source_id=lesson_id,
        raw_content_hash="e" * 64, parser_name="raw_lesson_snapshot", parser_version="v1",
        cleaning_strategy="basic_text_cleaning", cleaning_version="v1",
        units=[{"order": 0, "text": "Title", "source_locator": {
            "kind": "LESSON_FIELD", "section": "LESSON", "entity_id": str(lesson_id), "field": "title"}},
            {"order": 1, "text": "x", "source_locator": {
                "kind": "LESSON_FIELD", "section": "UNSUPPORTED", "entity_id": str(uuid4()), "field": "text"}}],
    )
    snapshot = SourceMetadataSnapshot(source_type="LESSON", source_id=lesson_id, title="Title")
    with pytest.raises(ParsingFailure) as raised:
        transform_lesson(artifact, snapshot)
    assert raised.value.code == "UNSUPPORTED_CONTENT_TYPE"


def test_typed_canonical_model_rejects_mixed_source_metadata_and_noncanonical_order():
    with pytest.raises(ValidationError):
        TransformedDocument(
            schema_version="transformed_document/v1", source_type="DOCUMENT", source_id=uuid4(), title="x",
            source_language=None, source_category=None, transformation_strategy="canonical_document",
            transformation_version="v1", provenance={}, blocks=[],
        )


def _canonical_block(kind, locator, structured_data=None):
    content_type = {
        "TABLE": "DOCUMENT_TEXT", "LIST": "DOCUMENT_TEXT", "VOCABULARY_ITEM": "VOCABULARY",
        "GRAMMAR_SECTION": "GRAMMAR", "LESSON_GENERAL": "LESSON_GENERAL", "PARAGRAPH": "DOCUMENT_TEXT",
    }[kind]
    return {
        "order": 0, "content_type": content_type, "block_kind": kind,
        "text": "content", "section_path": [], "source_locator": locator,
        "structured_data": structured_data or {}, "metadata": {},
    }


@pytest.mark.parametrize("locator", [
    {"kind": "PDF_PAGE", "page_number": 0},
    {"kind": "PDF_PAGE", "page_number": 1, "nonsense": "accepted"},
    {"kind": "UNKNOWN", "anything": "goes"},
])
def test_canonical_pdf_and_unknown_locators_are_strict(locator):
    with pytest.raises(ValidationError):
        CanonicalBlock.model_validate(_canonical_block("PARAGRAPH", locator))


@pytest.mark.parametrize("rows", [
    [{"row_index": "bad", "text": "x"}],
    [{"row_index": 0, "text": 123}],
    [{"row_index": 0, "text": "x", "cells": ["fabricated"]}],
])
def test_canonical_table_rows_reject_wrong_types_and_extra_cells(rows):
    locator = {"kind": "DOCX_TABLE", "table_index": 0, "rows": [
        {"kind": "DOCX_TABLE_ROW", "table_index": 0, "row_index": 0, "block_index": 0},
    ]}
    with pytest.raises(ValidationError):
        CanonicalBlock.model_validate(_canonical_block("TABLE", locator, {"table_index": 0, "rows": rows}))


@pytest.mark.parametrize("kind,locator,data", [
    ("VOCABULARY_ITEM", {"kind": "LESSON_ENTITY", "section": "VOCABULARY", "entity_id": str(uuid4()),
                          "order_index": 0, "fields": [{"kind": "LESSON_FIELD", "section": "VOCABULARY",
                          "entity_id": str(uuid4()), "field": "hanzi", "order_index": 0}]},
     {"lesson_id": None, "vocabulary_id": str(uuid4())}),
    ("VOCABULARY_ITEM", {"kind": "LESSON_ENTITY", "section": "VOCABULARY", "entity_id": str(uuid4()),
                          "order_index": 0, "fields": [{"kind": "LESSON_FIELD", "section": "VOCABULARY",
                          "entity_id": str(uuid4()), "field": "hanzi", "order_index": 0}]},
     {"lesson_id": str(uuid4()), "vocabulary_id": 123}),
    ("VOCABULARY_ITEM", {"kind": "LESSON_ENTITY", "section": "VOCABULARY", "entity_id": str(uuid4()),
                          "order_index": 0, "fields": [{"kind": "LESSON_FIELD", "section": "VOCABULARY",
                          "entity_id": str(uuid4()), "field": "hanzi", "order_index": 0}]},
     {"lesson_id": str(uuid4()), "vocabulary_id": str(uuid4()), "hanzi": {"arbitrary": "nested"}}),
    ("GRAMMAR_SECTION", {"kind": "LESSON_ENTITY", "section": "GRAMMAR", "entity_id": str(uuid4()),
                          "order_index": 0, "fields": [{"kind": "LESSON_FIELD", "section": "GRAMMAR",
                          "entity_id": str(uuid4()), "field": "name", "order_index": 0}]},
     {"lesson_id": None, "grammar_id": str(uuid4())}),
    ("GRAMMAR_SECTION", {"kind": "LESSON_ENTITY", "section": "GRAMMAR", "entity_id": str(uuid4()),
                          "order_index": 0, "fields": [{"kind": "LESSON_FIELD", "section": "GRAMMAR",
                          "entity_id": str(uuid4()), "field": "name", "order_index": 0}]},
     {"lesson_id": str(uuid4()), "grammar_id": 123}),
])
def test_lesson_structured_entity_identities_are_strict(kind, locator, data):
    with pytest.raises(ValidationError):
        CanonicalBlock.model_validate(_canonical_block(kind, locator, data))


@pytest.mark.parametrize("data", [
    {"list_kind": "sideways", "items": ["x"]},
    {"list_kind": "ordered", "items": ["x", 3]},
    {"list_kind": "ordered", "items": ["x"], "nested": {"arbitrary": True}},
])
def test_list_structured_data_rejects_invalid_literal_items_and_extras(data):
    locator = {"kind": "MARKDOWN_LIST", "list_kind": "ordered", "members": [
        {"kind": "MARKDOWN_BLOCK", "block_index": 0, "block_kind": "LIST_ITEM", "list_kind": "ordered"},
    ]}
    with pytest.raises(ValidationError):
        CanonicalBlock.model_validate(_canonical_block("LIST", locator, data))


def test_transformed_document_provenance_is_typed_and_rejects_unknown_fields():
    artifact = document([{"order": 0, "text": "body", "source_locator": {"kind": "PDF_PAGE", "page_number": 1}}])
    valid = transform_document(artifact, metadata(artifact.source_id)).model_dump(mode="json")
    valid["provenance"]["authority_score"] = 0.9
    with pytest.raises(ValidationError):
        TransformedDocument.model_validate(valid)


def test_canonical_block_metadata_is_explicitly_empty_and_rejects_arbitrary_data():
    with pytest.raises(ValidationError):
        CanonicalBlock.model_validate({
            **_canonical_block("PARAGRAPH", {"kind": "PDF_PAGE", "page_number": 1}),
            "metadata": {"unreviewed": {"anything": True}},
        })


def test_lesson_fields_and_grouped_locator_must_preserve_valid_lineage():
    bad = {
        "order": 0, "content_type": "LESSON_GENERAL", "block_kind": "LESSON_GENERAL", "text": "desc",
        "section_path": ["Lesson"], "structured_data": {}, "metadata": {},
        "source_locator": {"kind": "LESSON_ENTITY", "section": "LESSON", "entity_id": str(uuid4()),
                           "fields": [{"kind": "LESSON_FIELD", "section": "LESSON", "entity_id": str(uuid4()),
                                       "field": "invented"}]},
    }
    with pytest.raises(ValidationError):
        CanonicalBlock.model_validate(bad)
