import hashlib
import json
from typing import Any
from uuid import UUID

from app.core.errors import ApplicationError
from app.ingestion.chunking.config import (
    BLOCK_SEPARATOR, DEFAULT_CHUNKING_CONFIG, LIST_ITEM_SEPARATOR, TABLE_ROW_SEPARATOR,
)
from app.ingestion.chunking.locator import (
    make_metadata, narrow_grammar_locator, narrow_list_locator, narrow_table_locator,
)
from app.ingestion.chunking.models import ChunkBuildResult, ChunkMetadata, ChunkPlan, TableRowProvenance
from app.ingestion.chunking.text_splitter import split_oversized_text
from app.ingestion.transformation.formatters import GRAMMAR_FIELDS
from app.ingestion.transformation.models import (
    CanonicalBlock, CanonicalSourceLocator, GrammarStructuredData, ListStructuredData, TableStructuredData,
    TransformedDocument, VocabularyStructuredData,
)


def content_hash(content: str, content_type: str) -> str:
    canonical = json.dumps(
        {"content": content, "content_type": content_type},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _app_error(code: str, message: str, status: int = 422) -> ApplicationError:
    return ApplicationError(code, message, status_code=status)


def _section(block: CanonicalBlock) -> str | None:
    return " > ".join(block.section_path) if block.section_path else None


def _page_number(metadata: ChunkMetadata) -> int | None:
    if metadata.page_start is not None and metadata.page_start == metadata.page_end:
        return metadata.page_start
    return None


def _make_plan(content: str, blocks: list[CanonicalBlock], *, extra: dict[str, Any] | None = None,
               split: tuple[int, int] | None = None, lesson_id: UUID | None = None,
               vocabulary_id: UUID | None = None, grammar_id: UUID | None = None,
               source_locators: list[CanonicalSourceLocator] | None = None,
               semantic_part_index: int | None = None, semantic_part_count: int | None = None,
               field_lineage: list[str] | None = None) -> ChunkPlan:
    first = blocks[0]
    metadata_values: dict[str, Any] = {}
    if extra:
        metadata_values.update(extra)
    if vocabulary_id is not None:
        metadata_values["vocabulary_id"] = vocabulary_id
    if grammar_id is not None:
        metadata_values["grammar_id"] = grammar_id
    if semantic_part_index is not None:
        metadata_values["semantic_part_index"] = semantic_part_index
        metadata_values["semantic_part_count"] = semantic_part_count
    if field_lineage is not None:
        metadata_values["field_lineage"] = field_lineage
    metadata = make_metadata(blocks, extra=metadata_values, split=split, source_locators=source_locators)
    if not content.strip():
        raise _app_error("INVALID_CHUNK", "Chunk content must not be empty.")
    return ChunkPlan(
        content=content, content_type=first.content_type, chunk_index=0, token_count=None,
        page_number=_page_number(metadata), section=_section(first), lesson_id=lesson_id,
        metadata=metadata, content_hash=content_hash(content, first.content_type),
    )


def _generic_block_split(block: CanonicalBlock, lesson_id: UUID | None) -> list[ChunkPlan]:
    parts = split_oversized_text(block.text)
    count = len(parts)
    return [
        _make_plan(part.text, [block], split=(part.char_start, part.char_end), lesson_id=lesson_id,
                   semantic_part_index=i, semantic_part_count=count)
        for i, part in enumerate(parts)
    ]


def _generic_text(blocks: list[CanonicalBlock], lesson_id: UUID | None) -> list[ChunkPlan]:
    output: list[ChunkPlan] = []
    current: list[CanonicalBlock] = []
    current_text = ""

    def flush() -> None:
        nonlocal current, current_text
        if current:
            output.append(_make_plan(current_text, current, lesson_id=lesson_id))
        current, current_text = [], ""

    for block in blocks:
        if block.block_kind == "TABLE":
            flush()
            output.extend(_table_chunks(block, lesson_id))
            continue
        if block.block_kind == "LIST":
            flush()
            output.extend(_list_chunks(block, lesson_id))
            continue
        if not block.text.strip():
            raise _app_error("INVALID_CHUNK", "Canonical text block is empty.")
        if len(block.text) > DEFAULT_CHUNKING_CONFIG.max_chars:
            flush()
            output.extend(_generic_block_split(block, lesson_id))
            continue
        if block.block_kind == "HEADING" and current:
            flush()
        if not current:
            current = [block]
            current_text = block.text
            continue

        previous = current[-1]
        compatible = (
            previous.order + 1 == block.order
            and previous.content_type == block.content_type
            and previous.section_path == block.section_path
        )
        is_heading_candidate = len(current) == 1 and current[0].block_kind == "HEADING"
        if not compatible or (len(current_text) >= DEFAULT_CHUNKING_CONFIG.target_chars and not is_heading_candidate):
            flush()
            current = [block]
            current_text = block.text
            continue
        candidate = current_text + BLOCK_SEPARATOR + block.text
        if len(candidate) <= DEFAULT_CHUNKING_CONFIG.max_chars:
            current.append(block)
            current_text = candidate
        else:
            flush()
            current = [block]
            current_text = block.text
    flush()
    return output


def _table_chunks(block: CanonicalBlock, lesson_id: UUID | None) -> list[ChunkPlan]:
    data = block.structured_data
    if not isinstance(data, TableStructuredData):
        raise _app_error("INVALID_CHUNKING_INPUT", "Canonical table structure is invalid.")
    if block.text != TABLE_ROW_SEPARATOR.join(row.text for row in data.rows):
        raise _app_error("INVALID_CHUNKING_INPUT", "Canonical table text does not match retained rows.")
    maximum = DEFAULT_CHUNKING_CONFIG.max_chars
    if any(len(row.text) > maximum for row in data.rows):
        raise _app_error("CHUNK_TOO_LARGE", "A retained table row exceeds the maximum chunk size.")
    groups: list[list[Any]] = []
    current: list[Any] = []
    current_len = 0
    for row in data.rows:
        needed = len(row.text) + (len(TABLE_ROW_SEPARATOR) if current else 0)
        if current and current_len + needed > maximum:
            groups.append(current)
            current, current_len = [], 0
            needed = len(row.text)
        current.append(row)
        current_len += needed
    if current:
        groups.append(current)
    return [
        _make_plan(
            TABLE_ROW_SEPARATOR.join(row.text for row in group), [block], lesson_id=lesson_id,
            extra={"table_index": data.table_index,
                   "table_rows": [TableRowProvenance(row_index=row.row_index, text=row.text) for row in group]},
            source_locators=[narrow_table_locator(block, [row.row_index for row in group])],
        )
        for group in groups
    ]


def _list_chunks(block: CanonicalBlock, lesson_id: UUID | None) -> list[ChunkPlan]:
    data = block.structured_data
    if not isinstance(data, ListStructuredData):
        raise _app_error("INVALID_CHUNKING_INPUT", "Canonical list structure is invalid.")
    if block.text != LIST_ITEM_SEPARATOR.join(data.items):
        raise _app_error("INVALID_CHUNKING_INPUT", "Canonical list text does not match retained items.")
    max_chars = DEFAULT_CHUNKING_CONFIG.max_chars
    offsets: list[tuple[int, int]] = []
    cursor = 0
    for item in data.items:
        offsets.append((cursor, cursor + len(item)))
        cursor += len(item) + len(LIST_ITEM_SEPARATOR)

    output: list[ChunkPlan] = []
    groups: list[tuple[list[int], str]] = []
    indexes: list[int] = []
    texts: list[str] = []
    length = 0

    def flush_group() -> None:
        nonlocal indexes, texts, length
        if indexes:
            groups.append((indexes, LIST_ITEM_SEPARATOR.join(texts)))
        indexes, texts, length = [], [], 0

    oversized: list[int] = []
    for index, item in enumerate(data.items):
        if len(item) > max_chars:
            flush_group()
            oversized.append(index)
            continue
        needed = len(item) + (len(LIST_ITEM_SEPARATOR) if texts else 0)
        if texts and length + needed > max_chars:
            flush_group()
            needed = len(item)
        indexes.append(index)
        texts.append(item)
        length += needed
    flush_group()

    for item_indexes, text in groups:
        start_index, end_index = item_indexes[0], item_indexes[-1]
        output.append(_make_plan(
            text, [block], lesson_id=lesson_id,
            extra={"list_kind": data.list_kind, "item_start_index": start_index, "item_end_index": end_index},
            source_locators=[narrow_list_locator(block, start_index, end_index)],
        ))

    for item_index in oversized:
        item = data.items[item_index]
        parts = split_oversized_text(item)
        item_part_count = len(parts)
        base_start = offsets[item_index][0]
        for part_index, part in enumerate(parts):
            output.append(_make_plan(
                part.text, [block], split=(base_start + part.char_start, base_start + part.char_end),
                lesson_id=lesson_id,
                extra={"list_kind": data.list_kind, "item_start_index": item_index, "item_end_index": item_index,
                       "item_part_index": part_index, "item_part_count": item_part_count},
                source_locators=[narrow_list_locator(block, item_index, item_index)],
                semantic_part_index=part_index, semantic_part_count=item_part_count,
            ))
    # Items were partitioned in order; interleave grouped runs and oversized-item parts by source position.
    output.sort(key=lambda plan: (plan.metadata.item_start_index if plan.metadata.item_start_index is not None else -1,
                                 plan.metadata.item_part_index if plan.metadata.item_part_index is not None else -1))
    return output


def _grammar_fields(block: CanonicalBlock) -> list[tuple[str, str, int, int]]:
    data = block.structured_data
    if not isinstance(data, GrammarStructuredData):
        raise _app_error("INVALID_CHUNKING_INPUT", "Canonical grammar structure is invalid.")
    rendered: list[tuple[str, str, int, int]] = []
    cursor = 0
    for key, label in GRAMMAR_FIELDS:
        value = getattr(data, key)
        if not isinstance(value, str) or not value:
            continue
        field_text = f"{label}: {value}"
        start = block.text.find(field_text, cursor)
        if start < 0:
            raise _app_error("INVALID_CHUNKING_INPUT", "Grammar fields do not match canonical text.")
        end = start + len(field_text)
        rendered.append((key, field_text, start, end))
        cursor = end
    if "\n".join(item[1] for item in rendered) != block.text:
        raise _app_error("INVALID_CHUNKING_INPUT", "Grammar fields do not match canonical text.")
    return rendered


def _grammar_chunks(block: CanonicalBlock, lesson_id: UUID | None) -> list[ChunkPlan]:
    data = block.structured_data
    if not isinstance(data, GrammarStructuredData):
        raise _app_error("INVALID_CHUNKING_INPUT", "Canonical grammar structure is invalid.")
    grammar_id = data.grammar_id
    if len(block.text) <= DEFAULT_CHUNKING_CONFIG.max_chars:
        return [_make_plan(block.text, [block], lesson_id=lesson_id, grammar_id=grammar_id)]

    fields = _grammar_fields(block)
    segments: list[tuple[str, list[str], tuple[int, int] | None]] = []
    current_texts: list[str] = []
    current_names: list[str] = []
    current_length = 0

    def flush_fields() -> None:
        nonlocal current_texts, current_names, current_length
        if current_texts:
            segments.append(("\n".join(current_texts), list(current_names), None))
        current_texts, current_names, current_length = [], [], 0

    for name, text, start, end in fields:
        field_length = len(text)
        needed = field_length + (1 if current_texts else 0)
        if field_length > DEFAULT_CHUNKING_CONFIG.max_chars:
            flush_fields()
            parts = split_oversized_text(text)
            segments.extend((part.text, [name], (start + part.char_start, start + part.char_end)) for part in parts)
            continue
        if current_texts and current_length + needed > DEFAULT_CHUNKING_CONFIG.max_chars:
            flush_fields()
            needed = field_length
        current_texts.append(text)
        current_names.append(name)
        current_length += needed
    flush_fields()
    count = len(segments)
    return [
        _make_plan(
            text, [block], lesson_id=lesson_id, grammar_id=grammar_id,
            split=split, field_lineage=names, semantic_part_index=index, semantic_part_count=count,
            source_locators=[narrow_grammar_locator(block, names)],
        )
        for index, (text, names, split) in enumerate(segments)
    ]


def build_chunk_plan(document: TransformedDocument, knowledge_version_id: UUID) -> ChunkBuildResult:
    typed = TransformedDocument.model_validate(document)
    lesson_id = typed.source_id if typed.source_type == "LESSON" else None
    plans: list[ChunkPlan] = []
    document_blocks: list[CanonicalBlock] = []

    def flush_document_blocks() -> None:
        nonlocal document_blocks
        if document_blocks:
            plans.extend(_generic_text(document_blocks, lesson_id))
            document_blocks = []

    for block in typed.blocks:
        if block.content_type in {"DOCUMENT_TEXT", "LESSON_GENERAL"}:
            document_blocks.append(block)
            continue
        flush_document_blocks()
        if block.content_type == "VOCABULARY":
            data = block.structured_data
            if not isinstance(data, VocabularyStructuredData):
                raise _app_error("INVALID_CHUNKING_INPUT", "Canonical vocabulary structure is invalid.")
            plans.append(_make_plan(block.text, [block], lesson_id=data.lesson_id, vocabulary_id=data.vocabulary_id))
        elif block.content_type == "GRAMMAR":
            plans.extend(_grammar_chunks(block, lesson_id))
        else:
            raise _app_error("INVALID_CHUNKING_INPUT", "Canonical content type is unsupported.")
    flush_document_blocks()
    for plan in plans:
        if plan.content_type in {"DOCUMENT_TEXT", "LESSON_GENERAL"} and len(plan.content) > DEFAULT_CHUNKING_CONFIG.max_chars:
            raise _app_error("INVALID_CHUNK", "Generic text chunk exceeds the maximum character size.")
    indexed = [plan.model_copy(update={"chunk_index": index}) for index, plan in enumerate(plans)]
    return ChunkBuildResult(
        knowledge_version_id=knowledge_version_id, source_type=typed.source_type, source_id=typed.source_id,
        chunks=indexed,
    )
