from typing import Annotated, Any, Literal, Union
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StrictInt, StrictStr, model_validator


SourceType = Literal["DOCUMENT", "LESSON"]
ContentType = Literal["DOCUMENT_TEXT", "VOCABULARY", "GRAMMAR", "LESSON_GENERAL"]
BlockKind = Literal[
    "HEADING", "PARAGRAPH", "LIST", "CODE_BLOCK", "TABLE",
    "VOCABULARY_ITEM", "GRAMMAR_SECTION", "LESSON_GENERAL",
]
NonNegativeInt = Annotated[StrictInt, Field(ge=0)]
PositiveInt = Annotated[StrictInt, Field(ge=1)]


def _canonical_uuid(value):
    if not isinstance(value, (UUID, str)):
        raise ValueError("UUID identity must be a UUID or UUID string")
    return value


CanonicalUUID = Annotated[UUID, BeforeValidator(_canonical_uuid)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceMetadataSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: SourceType
    source_id: UUID
    title: str | None = None
    source_language: Literal["vi", "zh", "en"] | None = None
    source_category: Literal["CURRICULUM_MATERIAL", "INTERNAL_AUTHORED"] | None = None
    source_origin: str | None = None
    usage_rights_note: str | None = None
    original_filename: str | None = None


class ParsedUnitInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order: int = Field(ge=0)
    text: str
    source_locator: dict[str, Any]


class ParsedCleanedArtifactInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["parsed_cleaned_artifact/v1"]
    source_type: SourceType
    source_id: UUID
    raw_content_hash: str
    parser_name: str
    parser_version: str
    cleaning_strategy: str
    cleaning_version: str
    units: list[ParsedUnitInput]

    @model_validator(mode="after")
    def ordered_units(self):
        if [unit.order for unit in self.units] != list(range(len(self.units))):
            raise ValueError("parsed unit order must be consecutive")
        return self


class PDFPageLocator(StrictModel):
    kind: Literal["PDF_PAGE"]
    page_number: PositiveInt


class DOCXParagraphLocator(StrictModel):
    kind: Literal["DOCX_PARAGRAPH"]
    block_index: NonNegativeInt


class TextBlockLocator(StrictModel):
    kind: Literal["TEXT_BLOCK"]
    block_index: NonNegativeInt


class MarkdownBlockLocator(StrictModel):
    kind: Literal["MARKDOWN_BLOCK"]
    block_index: NonNegativeInt
    block_kind: Literal["HEADING", "PARAGRAPH", "CODE_BLOCK", "LIST_ITEM"]
    heading_level: Annotated[StrictInt, Field(ge=1, le=6)] | None = None
    list_kind: Literal["ordered", "unordered"] | None = None

    @model_validator(mode="after")
    def fields_match_block_kind(self):
        if (self.block_kind == "HEADING") != (self.heading_level is not None):
            raise ValueError("heading_level is required only for Markdown headings")
        if (self.block_kind == "LIST_ITEM") != (self.list_kind is not None):
            raise ValueError("list_kind is required only for Markdown list items")
        return self


class MarkdownListLocator(StrictModel):
    kind: Literal["MARKDOWN_LIST"]
    list_kind: Literal["ordered", "unordered"]
    members: list[MarkdownBlockLocator] = Field(min_length=1)

    @model_validator(mode="after")
    def contiguous_members(self):
        if any(member.block_kind != "LIST_ITEM" or member.list_kind != self.list_kind for member in self.members):
            raise ValueError("Markdown list members must match the grouped list kind")
        indexes = [member.block_index for member in self.members]
        if indexes != list(range(indexes[0], indexes[0] + len(indexes))):
            raise ValueError("Markdown list members must be contiguous and ordered")
        return self


class DOCXTableRowLocator(StrictModel):
    kind: Literal["DOCX_TABLE_ROW"]
    table_index: NonNegativeInt
    row_index: NonNegativeInt
    block_index: NonNegativeInt


class DOCXTableLocator(StrictModel):
    kind: Literal["DOCX_TABLE"]
    table_index: NonNegativeInt
    rows: list[DOCXTableRowLocator] = Field(min_length=1)

    @model_validator(mode="after")
    def retained_rows_match_table(self):
        row_indexes = [row.row_index for row in self.rows]
        if any(row.table_index != self.table_index for row in self.rows):
            raise ValueError("DOCX row lineage must match its table")
        if row_indexes != sorted(set(row_indexes)):
            raise ValueError("DOCX table rows must preserve unique ascending row indexes")
        return self


LessonSection = Literal["LESSON", "VOCABULARY", "GRAMMAR"]
LessonField = Literal[
    "title", "description", "hanzi", "pinyin", "vietnamese_meaning", "part_of_speech",
    "example", "note", "name", "structure", "explanation", "usage",
]


class LessonFieldLocator(StrictModel):
    kind: Literal["LESSON_FIELD"]
    section: LessonSection
    entity_id: CanonicalUUID
    field: LessonField
    order_index: NonNegativeInt | None = None

    @model_validator(mode="after")
    def field_matches_section(self):
        allowed = {
            "LESSON": {"title", "description"},
            "VOCABULARY": {"hanzi", "pinyin", "vietnamese_meaning", "part_of_speech", "example", "note"},
            "GRAMMAR": {"name", "structure", "explanation", "usage", "example", "note"},
        }
        if self.field not in allowed[self.section]:
            raise ValueError("Lesson field is not valid for its section")
        if (self.section == "LESSON") != (self.order_index is None):
            raise ValueError("order_index is required for Vocabulary and Grammar fields only")
        return self


class LessonEntityLocator(StrictModel):
    kind: Literal["LESSON_ENTITY"]
    section: LessonSection
    entity_id: CanonicalUUID
    order_index: NonNegativeInt | None = None
    fields: list[LessonFieldLocator] = Field(min_length=1)

    @model_validator(mode="after")
    def field_lineage_matches_entity(self):
        field_names = [field.field for field in self.fields]
        if len(field_names) != len(set(field_names)):
            raise ValueError("Lesson field lineage cannot duplicate fields")
        if any(field.section != self.section or field.entity_id != self.entity_id for field in self.fields):
            raise ValueError("Lesson field lineage must match entity section and identity")
        if self.section == "LESSON":
            if self.order_index is not None or any(field.order_index is not None for field in self.fields):
                raise ValueError("Lesson-level locators do not use order_index")
        elif self.order_index is None or any(field.order_index != self.order_index for field in self.fields):
            raise ValueError("Vocabulary and Grammar locators require matching order_index")
        return self


CanonicalSourceLocator = Annotated[
    Union[
        PDFPageLocator, DOCXParagraphLocator, TextBlockLocator, MarkdownBlockLocator,
        MarkdownListLocator, DOCXTableLocator, LessonEntityLocator,
    ],
    Field(discriminator="kind"),
]


class EmptyStructuredData(StrictModel):
    pass


class TableRow(StrictModel):
    row_index: NonNegativeInt
    text: StrictStr


class TableStructuredData(StrictModel):
    table_index: NonNegativeInt
    rows: list[TableRow] = Field(min_length=1)

    @model_validator(mode="after")
    def ordered_rows(self):
        indexes = [row.row_index for row in self.rows]
        if indexes != sorted(set(indexes)):
            raise ValueError("TABLE rows must have unique ascending row indexes")
        return self


class ListStructuredData(StrictModel):
    list_kind: Literal["ordered", "unordered"]
    items: list[StrictStr] = Field(min_length=1)


class VocabularyStructuredData(StrictModel):
    lesson_id: CanonicalUUID
    vocabulary_id: CanonicalUUID
    hanzi: StrictStr | None = None
    pinyin: StrictStr | None = None
    vietnamese_meaning: StrictStr | None = None
    part_of_speech: StrictStr | None = None
    example: StrictStr | None = None
    note: StrictStr | None = None


class GrammarStructuredData(StrictModel):
    lesson_id: CanonicalUUID
    grammar_id: CanonicalUUID
    name: StrictStr | None = None
    structure: StrictStr | None = None
    explanation: StrictStr | None = None
    usage: StrictStr | None = None
    example: StrictStr | None = None
    note: StrictStr | None = None


CanonicalStructuredData = Union[
    EmptyStructuredData, TableStructuredData, ListStructuredData,
    VocabularyStructuredData, GrammarStructuredData,
]


class EmptyMetadata(StrictModel):
    pass


class DocumentProvenance(StrictModel):
    source_origin: StrictStr
    usage_rights_note: StrictStr | None = None
    original_filename: StrictStr | None = None

    @model_validator(mode="after")
    def required_origin_is_non_blank(self):
        if not self.source_origin.strip():
            raise ValueError("Document provenance source_origin must not be blank")
        return self


class LessonProvenance(StrictModel):
    pass


class CanonicalBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order: NonNegativeInt
    content_type: ContentType
    block_kind: BlockKind
    text: str
    section_path: list[str]
    source_locator: CanonicalSourceLocator
    structured_data: CanonicalStructuredData = Field(default_factory=EmptyStructuredData)
    metadata: EmptyMetadata = Field(default_factory=EmptyMetadata)

    @model_validator(mode="before")
    @classmethod
    def parse_structured_variant(cls, value):
        if not isinstance(value, dict):
            return value
        block_kind = value.get("block_kind")
        data = value.get("structured_data", {})
        if isinstance(data, BaseModel):
            return value
        data_models = {
            "TABLE": TableStructuredData,
            "LIST": ListStructuredData,
            "VOCABULARY_ITEM": VocabularyStructuredData,
            "GRAMMAR_SECTION": GrammarStructuredData,
        }
        if block_kind in data_models:
            value = {**value, "structured_data": data_models[block_kind].model_validate(data)}
        else:
            value = {**value, "structured_data": EmptyStructuredData.model_validate(data)}
        return value

    @model_validator(mode="after")
    def compatible_fields(self):
        compatibility = {
            "DOCUMENT_TEXT": {"HEADING", "PARAGRAPH", "LIST", "CODE_BLOCK", "TABLE"},
            "VOCABULARY": {"VOCABULARY_ITEM"},
            "GRAMMAR": {"GRAMMAR_SECTION"},
            "LESSON_GENERAL": {"LESSON_GENERAL"},
        }
        if self.block_kind not in compatibility[self.content_type]:
            raise ValueError("content type and block kind are incompatible")
        expected_structured = {
            "TABLE": TableStructuredData,
            "LIST": ListStructuredData,
            "VOCABULARY_ITEM": VocabularyStructuredData,
            "GRAMMAR_SECTION": GrammarStructuredData,
        }.get(self.block_kind, EmptyStructuredData)
        if not isinstance(self.structured_data, expected_structured):
            raise ValueError("structured_data does not match block_kind")
        if self.block_kind == "TABLE":
            if not isinstance(self.source_locator, DOCXTableLocator):
                raise ValueError("TABLE requires DOCX_TABLE source lineage")
            if self.source_locator.table_index != self.structured_data.table_index:
                raise ValueError("TABLE locator and structured table index must match")
            if [row.row_index for row in self.source_locator.rows] != [row.row_index for row in self.structured_data.rows]:
                raise ValueError("TABLE locator and structured rows must match")
        elif self.block_kind == "LIST":
            if not isinstance(self.source_locator, MarkdownListLocator):
                raise ValueError("LIST requires grouped Markdown list source lineage")
        elif self.block_kind in {"VOCABULARY_ITEM", "GRAMMAR_SECTION", "LESSON_GENERAL"}:
            if not isinstance(self.source_locator, LessonEntityLocator):
                raise ValueError("Lesson blocks require LESSON_ENTITY source lineage")
            if self.block_kind == "VOCABULARY_ITEM":
                data = self.structured_data
                if (self.source_locator.section != "VOCABULARY"
                        or str(data.vocabulary_id) != str(self.source_locator.entity_id)
                        or any(field.section != "VOCABULARY" for field in self.source_locator.fields)):
                    raise ValueError("Vocabulary structured identity must match its source locator")
                if any(field.entity_id != data.vocabulary_id for field in self.source_locator.fields):
                    raise ValueError("Vocabulary field lineage must match structured identity")
                expected_fields = {
                    key for key in ("hanzi", "pinyin", "vietnamese_meaning", "part_of_speech", "example", "note")
                    if getattr(data, key) is not None
                }
                if {field.field for field in self.source_locator.fields} != expected_fields:
                    raise ValueError("Vocabulary fields must match retained parsed field lineage")
                if self.section_path != ["Vocabulary"]:
                    raise ValueError("Vocabulary section path is fixed")
            if self.block_kind == "GRAMMAR_SECTION":
                data = self.structured_data
                if (self.source_locator.section != "GRAMMAR"
                        or str(data.grammar_id) != str(self.source_locator.entity_id)
                        or any(field.section != "GRAMMAR" or field.entity_id != data.grammar_id for field in self.source_locator.fields)):
                    raise ValueError("Grammar structured identity must match its source locator")
                expected_fields = {
                    key for key in ("name", "structure", "explanation", "usage", "example", "note")
                    if getattr(data, key) is not None
                }
                if {field.field for field in self.source_locator.fields} != expected_fields:
                    raise ValueError("Grammar fields must match retained parsed field lineage")
                if not data.name or not data.name.strip() or self.section_path != ["Grammar", data.name]:
                    raise ValueError("Grammar name and section path are required canonical structure")
            if self.block_kind == "LESSON_GENERAL":
                if (self.source_locator.section != "LESSON" or self.section_path != ["Lesson"]
                        or [field.field for field in self.source_locator.fields] != ["description"]):
                    raise ValueError("Lesson general blocks require description field lineage")
        elif self.block_kind in {"HEADING", "CODE_BLOCK"}:
            expected_kind = "HEADING" if self.block_kind == "HEADING" else "CODE_BLOCK"
            if not isinstance(self.source_locator, MarkdownBlockLocator) or self.source_locator.block_kind != expected_kind:
                raise ValueError(f"{self.block_kind} requires matching Markdown source lineage")
        elif self.block_kind == "PARAGRAPH":
            markdown_paragraph = (isinstance(self.source_locator, MarkdownBlockLocator)
                                  and self.source_locator.block_kind == "PARAGRAPH")
            if not isinstance(self.source_locator, (PDFPageLocator, DOCXParagraphLocator, TextBlockLocator)) and not markdown_paragraph:
                raise ValueError("PARAGRAPH requires PDF, DOCX, text or Markdown paragraph source lineage")
        if not self.text and isinstance(self.structured_data, EmptyStructuredData):
            raise ValueError("empty block")
        return self


class TransformedDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["transformed_document/v1"]
    source_type: SourceType
    source_id: UUID
    title: str = Field(min_length=1)
    source_language: Literal["vi", "zh", "en"] | None
    source_category: Literal["CURRICULUM_MATERIAL", "INTERNAL_AUTHORED"] | None
    transformation_strategy: Literal["canonical_document"]
    transformation_version: Literal["v1"]
    provenance: DocumentProvenance | LessonProvenance
    blocks: list[CanonicalBlock]

    @model_validator(mode="before")
    @classmethod
    def parse_provenance_variant(cls, value):
        if not isinstance(value, dict) or isinstance(value.get("provenance"), BaseModel):
            return value
        model = DocumentProvenance if value.get("source_type") == "DOCUMENT" else LessonProvenance
        return {**value, "provenance": model.model_validate(value.get("provenance", {}))}

    @model_validator(mode="after")
    def source_metadata_and_order(self):
        if not self.title.strip():
            raise ValueError("canonical title must not be blank")
        if self.source_type == "DOCUMENT":
            if self.source_language is None or self.source_category is None:
                raise ValueError("DOCUMENT requires source language and category")
            if not isinstance(self.provenance, DocumentProvenance):
                raise ValueError("DOCUMENT requires document provenance")
        else:
            if self.source_language is not None or self.source_category is not None:
                raise ValueError("LESSON source language and category must be null")
            if not isinstance(self.provenance, LessonProvenance):
                raise ValueError("LESSON requires lesson provenance")
        if [block.order for block in self.blocks] != list(range(len(self.blocks))):
            raise ValueError("block order must be consecutive")
        for block in self.blocks:
            if self.source_type == "DOCUMENT" and isinstance(block.source_locator, LessonEntityLocator):
                raise ValueError("DOCUMENT blocks cannot use Lesson source locators")
            if self.source_type == "LESSON" and not isinstance(block.source_locator, LessonEntityLocator):
                raise ValueError("LESSON blocks require Lesson source locators")
            if isinstance(block.source_locator, LessonEntityLocator):
                if block.source_locator.section == "LESSON" and block.source_locator.entity_id != self.source_id:
                    raise ValueError("Lesson-level locator must match source identity")
                if block.block_kind in {"VOCABULARY_ITEM", "GRAMMAR_SECTION"}:
                    structured = block.structured_data
                    if str(structured.lesson_id) != str(self.source_id):
                        raise ValueError("Lesson entity structured data must match source identity")
        return self
