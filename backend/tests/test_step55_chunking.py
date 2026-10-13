import hashlib
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.errors import ApplicationError
from app.ingestion.chunking.config import DEFAULT_CHUNKING_CONFIG
from app.ingestion.chunking.models import ChunkMetadata, ChunkSourceRange, TableRowProvenance
from app.ingestion.chunking.strategy import build_chunk_plan, content_hash
from app.ingestion.chunking.text_splitter import split_oversized_text
from app.ingestion.transformation.formatters import GRAMMAR_FIELDS
from app.ingestion.transformation.models import TransformedDocument


def _document(blocks, *, source_type="DOCUMENT", source_id=None):
    source_id = source_id or uuid4()
    return TransformedDocument.model_validate({
        "schema_version": "transformed_document/v1", "source_type": source_type, "source_id": source_id,
        "title": "Test source", "source_language": "zh" if source_type == "DOCUMENT" else None,
        "source_category": "CURRICULUM_MATERIAL" if source_type == "DOCUMENT" else None,
        "transformation_strategy": "canonical_document", "transformation_version": "v1",
        "provenance": {"source_origin": "unit test"} if source_type == "DOCUMENT" else {}, "blocks": blocks,
    })


def _paragraph(order, text, *, section=None, page=None):
    locator = {"kind": "PDF_PAGE", "page_number": page} if page is not None else {"kind": "TEXT_BLOCK", "block_index": order}
    return {"order": order, "content_type": "DOCUMENT_TEXT", "block_kind": "PARAGRAPH", "text": text,
            "section_path": section or [], "source_locator": locator, "structured_data": {}, "metadata": {}}


def _lesson_general(order, text, lesson_id, field="description"):
    return {"order": order, "content_type": "LESSON_GENERAL", "block_kind": "LESSON_GENERAL", "text": text,
            "section_path": ["Lesson"], "source_locator": {"kind": "LESSON_ENTITY", "section": "LESSON",
            "entity_id": str(lesson_id), "fields": [{"kind": "LESSON_FIELD", "section": "LESSON",
            "entity_id": str(lesson_id), "field": field}]}, "structured_data": {}, "metadata": {}}


def _vocabulary(order, lesson_id, vocabulary_id, text):
    return {"order": order, "content_type": "VOCABULARY", "block_kind": "VOCABULARY_ITEM", "text": text,
            "section_path": ["Vocabulary"], "source_locator": {"kind": "LESSON_ENTITY", "section": "VOCABULARY",
            "entity_id": str(vocabulary_id), "order_index": order, "fields": [{"kind": "LESSON_FIELD",
            "section": "VOCABULARY", "entity_id": str(vocabulary_id), "field": "hanzi", "order_index": order}]},
            "structured_data": {"lesson_id": str(lesson_id), "vocabulary_id": str(vocabulary_id), "hanzi": text}, "metadata": {}}


def _grammar(order, lesson_id, grammar_id, values):
    field_names = [name for name, _label in GRAMMAR_FIELDS if name in values]
    text = "\n".join(f"{label}: {values[name]}" for name, label in GRAMMAR_FIELDS if name in values)
    return {"order": order, "content_type": "GRAMMAR", "block_kind": "GRAMMAR_SECTION", "text": text,
            "section_path": ["Grammar", values["name"]], "source_locator": {"kind": "LESSON_ENTITY",
            "section": "GRAMMAR", "entity_id": str(grammar_id), "order_index": order,
            "fields": [{"kind": "LESSON_FIELD", "section": "GRAMMAR", "entity_id": str(grammar_id),
                        "field": name, "order_index": order} for name in field_names]},
            "structured_data": {"lesson_id": str(lesson_id), "grammar_id": str(grammar_id), **values}, "metadata": {}}


def _table(order, rows):
    return {"order": order, "content_type": "DOCUMENT_TEXT", "block_kind": "TABLE",
            "text": "\n".join(row["text"] for row in rows), "section_path": [],
            "source_locator": {"kind": "DOCX_TABLE", "table_index": 0, "rows": [
                {"kind": "DOCX_TABLE_ROW", "table_index": 0, "row_index": row["row_index"], "block_index": order}
                for row in rows]}, "structured_data": {"table_index": 0, "rows": rows}, "metadata": {}}


def _list(order, items):
    return {"order": order, "content_type": "DOCUMENT_TEXT", "block_kind": "LIST", "text": "\n".join(items),
            "section_path": [], "source_locator": {"kind": "MARKDOWN_LIST", "list_kind": "unordered",
            "members": [{"kind": "MARKDOWN_BLOCK", "block_index": index, "block_kind": "LIST_ITEM",
                         "list_kind": "unordered"} for index in range(len(items))]},
            "structured_data": {"list_kind": "unordered", "items": items}, "metadata": {}}


def test_config_hash_is_exact_canonical_payload_and_excludes_provenance():
    doc = _document([_paragraph(0, "same", section=["A"]), _paragraph(1, "same", section=["B"])])
    result = build_chunk_plan(doc, uuid4())
    assert len(result.chunks) == 2
    assert result.chunks[0].content_hash == result.chunks[1].content_hash
    assert result.chunks[0].content_hash == content_hash("same", "DOCUMENT_TEXT")
    expected = hashlib.sha256(json.dumps(
        {"content": "same", "content_type": "DOCUMENT_TEXT"}, ensure_ascii=False,
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    assert result.chunks[0].content_hash == expected
    assert [chunk.chunk_index for chunk in result.chunks] == [0, 1]
    assert result.chunks[0].metadata.section_path == ["A"]
    assert result.chunks[1].metadata.section_path == ["B"]
    assert result.chunks[0].token_count is None
    assert result.knowledge_version_id


def test_adjacent_document_blocks_merge_but_page_changes_do_not_split_and_pages_aggregate():
    plan = build_chunk_plan(_document([_paragraph(0, "first", page=2), _paragraph(1, "second", page=3)]), uuid4())
    assert len(plan.chunks) == 1
    chunk = plan.chunks[0]
    assert chunk.content == "first\n\nsecond"
    assert chunk.page_number is None
    assert (chunk.metadata.page_start, chunk.metadata.page_end) == (2, 3)
    assert [item.char_start for item in chunk.metadata.source_ranges] == [None, None]


def test_section_change_flushes_and_section_projection_is_hierarchical():
    plan = build_chunk_plan(_document([
        _paragraph(0, "one", section=["A", "B"]), _paragraph(1, "two", section=["A", "C"]),
    ]), uuid4())
    assert [chunk.content for chunk in plan.chunks] == ["one", "two"]
    assert [chunk.section for chunk in plan.chunks] == ["A > B", "A > C"]
    assert [chunk.metadata.section_path for chunk in plan.chunks] == [["A", "B"], ["A", "C"]]


def test_heading_starts_a_forward_candidate_and_stays_in_canonical_content():
    lesson = uuid4()
    heading = {"order": 0, "content_type": "DOCUMENT_TEXT", "block_kind": "HEADING", "text": "Title",
               "section_path": ["Title"], "source_locator": {"kind": "MARKDOWN_BLOCK", "block_index": 0,
               "block_kind": "HEADING", "heading_level": 1}, "structured_data": {}, "metadata": {}}
    paragraph = {"order": 1, "content_type": "DOCUMENT_TEXT", "block_kind": "PARAGRAPH", "text": "Body",
                 "section_path": ["Title"], "source_locator": {"kind": "MARKDOWN_BLOCK", "block_index": 1,
                 "block_kind": "PARAGRAPH"}, "structured_data": {}, "metadata": {}}
    chunk = build_chunk_plan(_document([heading, paragraph]), uuid4()).chunks[0]
    assert chunk.content == "Title\n\nBody"
    assert chunk.metadata.block_start_order == 0 and chunk.metadata.block_end_order == 1
    assert lesson


def test_short_lesson_general_blocks_merge_without_a_global_minimum():
    lesson = uuid4()
    chunks = build_chunk_plan(_document([
        _lesson_general(0, "short one", lesson), _lesson_general(1, "short two", lesson),
    ], source_type="LESSON", source_id=lesson), uuid4()).chunks
    assert len(chunks) == 1
    assert chunks[0].content == "short one\n\nshort two"
    assert chunks[0].lesson_id == lesson


def test_vocabulary_is_atomic_short_and_keeps_entity_identity():
    lesson, first, second = uuid4(), uuid4(), uuid4()
    plan = build_chunk_plan(_document([
        _vocabulary(0, lesson, first, "字"), _vocabulary(1, lesson, second, "字"),
    ], source_type="LESSON", source_id=lesson), uuid4())
    assert [chunk.content for chunk in plan.chunks] == ["字", "字"]
    assert [chunk.metadata.vocabulary_id for chunk in plan.chunks] == [first, second]
    assert all(chunk.lesson_id == lesson for chunk in plan.chunks)


def test_grammar_is_atomic_until_max_then_splits_at_field_boundaries_and_records_lineage():
    lesson, grammar_id = uuid4(), uuid4()
    short = _grammar(0, lesson, grammar_id, {"name": "A", "explanation": "x" * 1250})
    normal = build_chunk_plan(_document([short], source_type="LESSON", source_id=lesson), uuid4())
    assert len(normal.chunks) == 1
    assert normal.chunks[0].metadata.grammar_id == grammar_id
    huge = _grammar(0, lesson, grammar_id, {"name": "A", "explanation": "x" * 1900, "usage": "use"})
    result = build_chunk_plan(_document([huge], source_type="LESSON", source_id=lesson), uuid4())
    assert len(result.chunks) > 1
    assert all(len(chunk.content) <= DEFAULT_CHUNKING_CONFIG.max_chars for chunk in result.chunks)
    assert all(chunk.metadata.grammar_id == grammar_id for chunk in result.chunks)
    assert all(chunk.metadata.semantic_part_index is not None for chunk in result.chunks)
    assert all(chunk.metadata.field_lineage for chunk in result.chunks)
    forced = [chunk for chunk in result.chunks if chunk.metadata.source_ranges[0].char_start is not None]
    assert forced
    assert all(chunk.metadata.source_ranges[0].char_end > chunk.metadata.source_ranges[0].char_start for chunk in forced)


def test_oversized_grammar_packs_complete_fields_before_forced_splitting():
    lesson, grammar_id = uuid4(), uuid4()
    block = _grammar(0, lesson, grammar_id, {"name": "A" * 650, "structure": "B" * 650, "usage": "C" * 650})
    chunks = build_chunk_plan(_document([block], source_type="LESSON", source_id=lesson), uuid4()).chunks
    assert len(chunks) == 2
    assert all(chunk.metadata.source_ranges[0].char_start is None for chunk in chunks)
    assert [chunk.metadata.field_lineage for chunk in chunks] == [["name", "structure"], ["usage"]]
    assert [[field.field for field in chunk.metadata.source_ranges[0].source_locator.fields]
            for chunk in chunks] == [["name", "structure"], ["usage"]]


def test_small_table_is_one_chunk_and_large_table_splits_only_between_retained_rows():
    rows = [{"row_index": 0, "text": "head"}, {"row_index": 1, "text": "body"}]
    one = build_chunk_plan(_document([_table(0, rows)]), uuid4()).chunks
    assert len(one) == 1 and one[0].content == "head\nbody"
    large_rows = [{"row_index": index, "text": str(index) * 1000} for index in range(3)]
    chunks = build_chunk_plan(_document([_table(0, large_rows)]), uuid4()).chunks
    assert [chunk.content for chunk in chunks] == [str(i) * 1000 for i in range(3)]
    assert [chunk.metadata.table_rows[0].row_index for chunk in chunks] == [0, 1, 2]
    assert [[row.row_index for row in chunk.metadata.source_ranges[0].source_locator.rows]
            for chunk in chunks] == [[0], [1], [2]]
    assert all("Table:" not in chunk.content and "Header:" not in chunk.content for chunk in chunks)
    assert all(len(chunk.content) <= 1800 for chunk in chunks)


def test_table_row_over_max_fails_without_splitting_row():
    with pytest.raises(ApplicationError) as raised:
        build_chunk_plan(_document([_table(0, [{"row_index": 0, "text": "x" * 1801}])]), uuid4())
    assert raised.value.code == "CHUNK_TOO_LARGE"


def test_list_packs_complete_items_then_splits_only_one_oversized_item_with_exact_ranges():
    items = ["small", "a" * 1900, "tail"]
    chunks = build_chunk_plan(_document([_list(0, items)]), uuid4()).chunks
    assert chunks[0].content == "small"
    middle = [chunk for chunk in chunks if chunk.metadata.item_start_index == 1]
    assert middle and all(chunk.metadata.item_part_count == len(middle) for chunk in middle)
    assert all(chunk.metadata.list_kind == "unordered" for chunk in chunks)
    assert [member.block_index for member in chunks[0].metadata.source_ranges[0].source_locator.members] == [0]
    assert all([member.block_index for member in chunk.metadata.source_ranges[0].source_locator.members] == [1]
               for chunk in middle)
    assert [member.block_index for member in chunks[-1].metadata.source_ranges[0].source_locator.members] == [2]
    for chunk in middle:
        source_range = chunk.metadata.source_ranges[0]
        assert source_range.char_start is not None and source_range.char_end is not None
        start = source_range.char_start - len("small\n")
        end = source_range.char_end - len("small\n")
        assert chunk.content == items[1][start:end]
    assert chunks[-1].content == "tail"


def test_normal_list_is_one_atomic_chunk():
    chunks = build_chunk_plan(_document([_list(0, ["one", "two", "three"])]), uuid4()).chunks
    assert len(chunks) == 1
    assert chunks[0].content == "one\ntwo\nthree"
    assert chunks[0].metadata.item_start_index == 0
    assert chunks[0].metadata.item_end_index == 2


def test_forced_split_prefers_paragraph_boundary_and_overlap_is_local_to_one_source_unit():
    source = "a" * 1100 + "\n\n" + "b" * 1050
    parts = split_oversized_text(source)
    assert len(parts) > 1
    assert parts[0].char_end == 1102
    assert parts[1].char_start < parts[0].char_end
    assert all(part.char_end - part.char_start <= DEFAULT_CHUNKING_CONFIG.max_chars for part in parts)
    assert parts[0].text == source[parts[0].char_start:parts[0].char_end]


def test_forced_split_falls_back_to_sentence_separator_before_whitespace():
    sentence = split_oversized_text("a" * 1190 + "." + "b" * 1000)
    whitespace = split_oversized_text("a" * 1190 + " " + "b" * 1000)
    assert sentence[0].char_end == 1191
    assert whitespace[0].char_end == 1191


def test_splitter_prefers_paragraph_over_line_boundary():
    text = "a" * 900 + "\n\n" + "b" * 300 + "\n" + "c" * 1000
    assert split_oversized_text(text)[0].char_end == 902


def test_splitter_prefers_line_over_sentence_boundary():
    text = "a" * 900 + "\n" + "b" * 200 + "\u3002" + "c" * 1000
    assert split_oversized_text(text)[0].char_end == 901


@pytest.mark.parametrize("punctuation", ["\u3002", "\uff01", "\uff1f", "\uff1b", ".", "!", "?", ";"])
def test_splitter_prefers_chinese_and_latin_sentence_punctuation_over_whitespace(punctuation):
    text = "a" * 900 + punctuation + "b" * 200 + " " + "c" * 1000
    assert split_oversized_text(text)[0].char_end == 901


def test_splitter_prefers_whitespace_over_hard_boundary():
    text = "a" * 900 + " " + "b" * 1000
    assert split_oversized_text(text)[0].char_end == 901


def test_splitter_uses_hard_boundary_when_no_separator_exists():
    parts = split_oversized_text("a" * 2500)
    assert parts[0].char_end == 1200
    assert parts[1].char_start == 1050
    assert parts[0].char_end - parts[1].char_start == DEFAULT_CHUNKING_CONFIG.overlap_chars


def test_generic_forced_text_provenance_uses_exact_character_range():
    block = _paragraph(0, "x" * 2500)
    chunks = build_chunk_plan(_document([block]), uuid4()).chunks
    assert chunks[0].metadata.source_ranges[0].source_locator.block_index == 0
    assert (chunks[0].metadata.source_ranges[0].char_start,
            chunks[0].metadata.source_ranges[0].char_end) == (0, 1200)
    assert chunks[1].metadata.source_ranges[0].source_locator.block_index == 0
    assert chunks[1].metadata.source_ranges[0].char_start == 1050


def test_text_types_never_merge_and_hash_does_not_define_identity():
    lesson = uuid4()
    plan = build_chunk_plan(_document([
        _lesson_general(0, "same", lesson), _vocabulary(1, lesson, uuid4(), "same"),
    ], source_type="LESSON", source_id=lesson), uuid4())
    assert [chunk.content_type for chunk in plan.chunks] == ["LESSON_GENERAL", "VOCABULARY"]
    assert plan.chunks[0].content_hash != plan.chunks[1].content_hash


def test_malformed_typed_source_locator_and_table_provenance_are_rejected():
    with pytest.raises(ValidationError):
        ChunkSourceRange(block_order=0, source_locator={"kind": "UNKNOWN", "anything": "x"})
    with pytest.raises(ValidationError):
        ChunkSourceRange(block_order=True, source_locator={"kind": "TEXT_BLOCK", "block_index": 0})
    with pytest.raises(ValidationError):
        TableRowProvenance(row_index=0, text="row", cells=["invented"])
    with pytest.raises(ValidationError):
        ChunkMetadata(
            section_path=[], block_start_order=0, block_end_order=0,
            source_ranges=[{"block_order": 0, "source_locator": {"kind": "DOCX_TABLE", "table_index": 0,
                "rows": [{"kind": "DOCX_TABLE_ROW", "table_index": 0, "row_index": 0, "block_index": 0}]}}],
            table_index=0, table_rows=[{"row_index": 1, "text": "wrong row"}],
        )

