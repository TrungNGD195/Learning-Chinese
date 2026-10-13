from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator
from app.ingestion.transformation.models import (
    CanonicalSourceLocator, DOCXTableLocator, LessonEntityLocator, MarkdownListLocator,
)


ContentType = Literal["DOCUMENT_TEXT", "VOCABULARY", "GRAMMAR", "LESSON_GENERAL"]


class ChunkSourceRange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_order: StrictInt = Field(ge=0)
    source_locator: CanonicalSourceLocator
    char_start: StrictInt | None = Field(default=None, ge=0)
    char_end: StrictInt | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def complete_character_range(self):
        if (self.char_start is None) != (self.char_end is None):
            raise ValueError("source character range must provide both offsets or neither")
        if self.char_start is not None and self.char_end < self.char_start:
            raise ValueError("source character range end precedes its start")
        return self


class TableRowProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_index: StrictInt = Field(ge=0)
    text: StrictStr


class ChunkMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["chunk_metadata/v1"] = "chunk_metadata/v1"
    section_path: list[StrictStr]
    block_start_order: StrictInt = Field(ge=0)
    block_end_order: StrictInt = Field(ge=0)
    source_ranges: list[ChunkSourceRange] = Field(min_length=1)
    page_start: StrictInt | None = Field(default=None, ge=1)
    page_end: StrictInt | None = Field(default=None, ge=1)
    vocabulary_id: UUID | None = None
    grammar_id: UUID | None = None
    semantic_part_index: StrictInt | None = Field(default=None, ge=0)
    semantic_part_count: StrictInt | None = Field(default=None, ge=1)
    field_lineage: list[StrictStr] | None = None
    list_kind: Literal["ordered", "unordered"] | None = None
    item_start_index: StrictInt | None = Field(default=None, ge=0)
    item_end_index: StrictInt | None = Field(default=None, ge=0)
    item_part_index: StrictInt | None = Field(default=None, ge=0)
    item_part_count: StrictInt | None = Field(default=None, ge=1)
    table_index: StrictInt | None = Field(default=None, ge=0)
    table_rows: list[TableRowProvenance] | None = None

    @model_validator(mode="after")
    def ordered_source_trace(self):
        if self.block_end_order < self.block_start_order:
            raise ValueError("chunk block range is reversed")
        orders = [item.block_order for item in self.source_ranges]
        if orders != sorted(orders) or any(order < self.block_start_order or order > self.block_end_order for order in orders):
            raise ValueError("source ranges must follow the chunk block range")
        if self.page_start is not None and self.page_end is not None and self.page_end < self.page_start:
            raise ValueError("chunk page range is reversed")
        if self.semantic_part_index is not None and self.semantic_part_count is not None:
            if self.semantic_part_index >= self.semantic_part_count:
                raise ValueError("semantic part index must be below its part count")
        if self.table_index is not None or self.table_rows is not None:
            if self.table_index is None or not self.table_rows:
                raise ValueError("table provenance requires table identity and retained rows")
            if len(self.source_ranges) != 1 or not isinstance(self.source_ranges[0].source_locator, DOCXTableLocator):
                raise ValueError("table provenance requires one typed DOCX table locator")
            locator = self.source_ranges[0].source_locator
            row_indexes = [row.row_index for row in self.table_rows]
            if locator.table_index != self.table_index or [row.row_index for row in locator.rows] != row_indexes:
                raise ValueError("table row metadata and narrowed locator must match")
        if any(value is not None for value in (self.item_start_index, self.item_end_index, self.item_part_index,
                                               self.item_part_count, self.list_kind)):
            if self.list_kind is None or self.item_start_index is None or self.item_end_index is None:
                raise ValueError("list provenance requires kind and an item range")
            if self.item_end_index < self.item_start_index or len(self.source_ranges) != 1:
                raise ValueError("list item range or source locator is invalid")
            locator = self.source_ranges[0].source_locator
            if not isinstance(locator, MarkdownListLocator) or locator.list_kind != self.list_kind:
                raise ValueError("list provenance requires a matching typed Markdown list locator")
            split_item = self.source_ranges[0].char_start is not None
            if split_item:
                if (self.item_start_index != self.item_end_index or len(locator.members) != 1
                        or self.item_part_index is None or self.item_part_count is None
                        or self.item_part_index >= self.item_part_count):
                    raise ValueError("split list item provenance is inconsistent")
            elif (self.item_part_index is not None or self.item_part_count is not None
                  or len(locator.members) != self.item_end_index - self.item_start_index + 1):
                raise ValueError("grouped list provenance must match its retained members")
        if self.field_lineage is not None:
            if len(self.source_ranges) != 1 or not isinstance(self.source_ranges[0].source_locator, LessonEntityLocator):
                raise ValueError("Grammar field lineage requires one typed Lesson entity locator")
            locator = self.source_ranges[0].source_locator
            if locator.section != "GRAMMAR" or [field.field for field in locator.fields] != self.field_lineage:
                raise ValueError("Grammar field lineage and narrowed locator must match")
        return self


class ChunkPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: StrictStr = Field(min_length=1)
    content_type: ContentType
    chunk_index: StrictInt = Field(ge=0)
    token_count: None = None
    page_number: StrictInt | None = Field(default=None, ge=1)
    section: StrictStr | None = None
    lesson_id: UUID | None = None
    metadata: ChunkMetadata
    content_hash: StrictStr = Field(pattern=r"^[0-9a-f]{64}$")


class ChunkBuildResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    knowledge_version_id: UUID
    source_type: Literal["DOCUMENT", "LESSON"]
    source_id: UUID
    chunking_strategy: Literal["structure_aware"] = "structure_aware"
    chunking_version: Literal["v1"] = "v1"
    target_chars: StrictInt = 1200
    max_chars: StrictInt = 1800
    overlap_chars: StrictInt = 150
    chunks: list[ChunkPlan]

    @model_validator(mode="after")
    def canonical_chunk_order_and_config(self):
        if [chunk.chunk_index for chunk in self.chunks] != list(range(len(self.chunks))):
            raise ValueError("chunk indexes must be consecutive in canonical order")
        if (self.chunking_strategy, self.chunking_version, self.target_chars, self.max_chars, self.overlap_chars) != (
            "structure_aware", "v1", 1200, 1800, 150,
        ):
            raise ValueError("chunk config does not match the frozen v1 contract")
        return self
