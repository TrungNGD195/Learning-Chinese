from collections.abc import Iterable

from app.ingestion.transformation.models import (
    CanonicalBlock, CanonicalSourceLocator, DOCXTableLocator, LessonEntityLocator,
    MarkdownListLocator, PDFPageLocator,
)
from app.ingestion.chunking.config import METADATA_SCHEMA_VERSION
from app.ingestion.chunking.models import ChunkMetadata, ChunkSourceRange


def source_ranges(blocks: Iterable[CanonicalBlock], *, split: tuple[int, int] | None = None,
                  source_locators: list[CanonicalSourceLocator] | None = None) -> list[ChunkSourceRange]:
    blocks = list(blocks)
    locators = ([block.source_locator for block in blocks]
                if source_locators is None else source_locators)
    if len(locators) != len(blocks):
        raise ValueError("source locator count must match represented blocks")
    if split is None:
        return [ChunkSourceRange(block_order=block.order, source_locator=locator)
                for block, locator in zip(blocks, locators, strict=True)]
    if len(blocks) != 1:
        raise ValueError("a forced split range must refer to exactly one canonical block")
    return [ChunkSourceRange(block_order=blocks[0].order, source_locator=locators[0], char_start=split[0], char_end=split[1])]


def make_metadata(blocks: list[CanonicalBlock], *, extra: dict | None = None, split: tuple[int, int] | None = None,
                  source_locators: list[CanonicalSourceLocator] | None = None) -> ChunkMetadata:
    if not blocks:
        raise ValueError("chunk provenance requires at least one source block")
    paths = {tuple(block.section_path) for block in blocks}
    # Atomic structured units own their own path; a merged generic candidate is validated before this point.
    section_path = list(blocks[0].section_path) if len(paths) == 1 else []
    pages = [block.source_locator.page_number for block in blocks if isinstance(block.source_locator, PDFPageLocator)]
    values = {
        "schema_version": METADATA_SCHEMA_VERSION,
        "section_path": section_path,
        "block_start_order": blocks[0].order,
        "block_end_order": blocks[-1].order,
        "source_ranges": source_ranges(blocks, split=split, source_locators=source_locators),
        "page_start": min(pages) if pages else None,
        "page_end": max(pages) if pages else None,
        **(extra or {}),
    }
    return ChunkMetadata.model_validate(values)


def narrow_table_locator(block: CanonicalBlock, row_indexes: list[int]) -> DOCXTableLocator:
    locator = block.source_locator
    if not isinstance(locator, DOCXTableLocator):
        raise ValueError("table block must use DOCX table locator")
    selected = [row for row in locator.rows if row.row_index in set(row_indexes)]
    return DOCXTableLocator.model_validate({
        "kind": locator.kind, "table_index": locator.table_index,
        "rows": [row.model_dump(mode="json") for row in selected],
    })


def narrow_list_locator(block: CanonicalBlock, item_start: int, item_end: int) -> MarkdownListLocator:
    locator = block.source_locator
    if not isinstance(locator, MarkdownListLocator):
        raise ValueError("list block must use Markdown list locator")
    if item_start < 0 or item_end < item_start or item_end >= len(locator.members):
        raise ValueError("list item range is outside its source locator")
    return MarkdownListLocator.model_validate({
        "kind": locator.kind, "list_kind": locator.list_kind,
        "members": [member.model_dump(mode="json") for member in locator.members[item_start:item_end + 1]],
    })


def narrow_grammar_locator(block: CanonicalBlock, field_names: list[str]) -> LessonEntityLocator:
    locator = block.source_locator
    if not isinstance(locator, LessonEntityLocator) or locator.section != "GRAMMAR":
        raise ValueError("Grammar block must use Lesson grammar entity locator")
    fields_by_name = {field.field: field for field in locator.fields}
    if len(set(field_names)) != len(field_names) or any(name not in fields_by_name for name in field_names):
        raise ValueError("Grammar field lineage is outside its source locator")
    selected = [fields_by_name[name] for name in field_names]
    return LessonEntityLocator.model_validate({
        "kind": locator.kind, "section": locator.section, "entity_id": locator.entity_id,
        "order_index": locator.order_index,
        "fields": [field.model_dump(mode="json", exclude_none=True) for field in selected],
    })
