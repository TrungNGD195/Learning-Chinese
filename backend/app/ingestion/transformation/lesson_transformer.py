from collections import OrderedDict
from typing import Any
from uuid import UUID

from app.ingestion.parsing.base import ParsingFailure
from app.ingestion.transformation.formatters import GRAMMAR_FIELDS, VOCABULARY_FIELDS, labeled_text
from app.ingestion.transformation.models import CanonicalBlock, ParsedCleanedArtifactInput, SourceMetadataSnapshot, TransformedDocument


VOCABULARY_SOURCE_FIELDS = {"hanzi", "pinyin", "vietnamese_meaning", "part_of_speech", "example", "note"}
GRAMMAR_SOURCE_FIELDS = {"name", "structure", "explanation", "usage", "example", "note"}


def _group_units(artifact: ParsedCleanedArtifactInput, section: str) -> list[dict[str, Any]]:
    groups: OrderedDict[tuple[str, int], dict[str, Any]] = OrderedDict()
    allowed_fields = VOCABULARY_SOURCE_FIELDS if section == "VOCABULARY" else GRAMMAR_SOURCE_FIELDS
    for unit in artifact.units:
        locator = unit.source_locator
        if locator.get("section") != section:
            continue
        entity_id = locator.get("entity_id")
        field = locator.get("field")
        order_index = locator.get("order_index")
        try:
            normalized_entity_id = str(UUID(entity_id))
        except (ValueError, TypeError, AttributeError):
            normalized_entity_id = None
        if (locator.get("kind") != "LESSON_FIELD" or normalized_entity_id is None
                or field not in allowed_fields or not isinstance(order_index, int) or order_index < 0):
            raise ParsingFailure("INVALID_SOURCE_LOCATOR", f"Stored {section.lower()} field locator is invalid.")
        key = (normalized_entity_id, order_index)
        group = groups.setdefault(key, {
            "entity_id": normalized_entity_id, "order_index": order_index, "source_order": unit.order,
            "fields": {}, "locators": [],
        })
        group["source_order"] = min(group["source_order"], unit.order)
        if field in group["fields"]:
            raise ParsingFailure("INVALID_SOURCE_LOCATOR", f"Stored {section.lower()} field is duplicated.")
        group["fields"][field] = unit.text
        group["locators"].append(locator)
    return sorted(groups.values(), key=lambda group: (group["order_index"], group["locators"][0]["field"]))


def transform_lesson(artifact: ParsedCleanedArtifactInput, snapshot: SourceMetadataSnapshot) -> TransformedDocument:
    if artifact.source_type != "LESSON" or snapshot.source_type != "LESSON" or artifact.source_id != snapshot.source_id:
        raise ParsingFailure("INVALID_SOURCE_LOCATOR", "Parsed Lesson identity does not match its metadata snapshot.")
    lesson_title: str | None = None
    general_units = []
    for unit in artifact.units:
        locator = unit.source_locator
        section = locator.get("section")
        if section not in {"LESSON", "VOCABULARY", "GRAMMAR"}:
            raise ParsingFailure("UNSUPPORTED_CONTENT_TYPE", "Stored Lesson section is unsupported.")
        if section != "LESSON":
            continue
        if locator.get("kind") != "LESSON_FIELD" or locator.get("entity_id") != str(artifact.source_id):
            raise ParsingFailure("INVALID_SOURCE_LOCATOR", "Stored Lesson field locator is invalid.")
        field = locator.get("field")
        if not isinstance(field, str) or not field:
            raise ParsingFailure("INVALID_SOURCE_LOCATOR", "Stored Lesson general field locator is invalid.")
        if field == "title":
            if lesson_title is not None:
                raise ParsingFailure("INVALID_SOURCE_LOCATOR", "Stored Lesson title field is duplicated.")
            lesson_title = unit.text
        else:
            general_units.append(unit)
    title = lesson_title
    if not title or not title.strip():
        raise ParsingFailure("TRANSFORMATION_FAILED", "Persisted Lesson title is unavailable.")
    if snapshot.title and snapshot.title != title:
        raise ParsingFailure("TRANSFORMATION_FAILED", "Lesson metadata snapshot does not match parsed title.")

    ordered_blocks: list[tuple[int, CanonicalBlock]] = []
    for group in _group_units(artifact, "VOCABULARY"):
        data: dict[str, Any] = {"lesson_id": str(artifact.source_id), "vocabulary_id": group["entity_id"]}
        data.update(group["fields"])
        text = labeled_text(data, VOCABULARY_FIELDS)
        locator = {
            "kind": "LESSON_ENTITY", "section": "VOCABULARY", "entity_id": group["entity_id"],
            "order_index": group["order_index"], "fields": group["locators"],
        }
        block = CanonicalBlock(
            order=0, content_type="VOCABULARY", block_kind="VOCABULARY_ITEM", text=text,
            section_path=["Vocabulary"], source_locator=locator, structured_data=data, metadata={},
        )
        ordered_blocks.append((group["source_order"], block))
    for group in _group_units(artifact, "GRAMMAR"):
        data = {"lesson_id": str(artifact.source_id), "grammar_id": group["entity_id"]}
        data.update(group["fields"])
        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ParsingFailure("INVALID_TRANSFORMED_DOCUMENT", "Grammar name is required for its canonical section path.")
        text = labeled_text(data, GRAMMAR_FIELDS)
        locator = {
            "kind": "LESSON_ENTITY", "section": "GRAMMAR", "entity_id": group["entity_id"],
            "order_index": group["order_index"], "fields": group["locators"],
        }
        block = CanonicalBlock(
            order=0, content_type="GRAMMAR", block_kind="GRAMMAR_SECTION", text=text,
            section_path=["Grammar", name], source_locator=locator, structured_data=data, metadata={},
        )
        ordered_blocks.append((group["source_order"], block))
    for unit in general_units:
        if not unit.text:
            continue
        block = CanonicalBlock(
            order=0, content_type="LESSON_GENERAL", block_kind="LESSON_GENERAL",
            text=unit.text, section_path=["Lesson"],
            source_locator={"kind": "LESSON_ENTITY", "section": "LESSON", "entity_id": str(artifact.source_id),
                            "fields": [unit.source_locator]},
            structured_data={}, metadata={},
        )
        ordered_blocks.append((unit.order, block))
    blocks = [block.model_copy(update={"order": order})
              for order, (_, block) in enumerate(sorted(ordered_blocks, key=lambda item: item[0]))]
    return TransformedDocument(
        schema_version="transformed_document/v1", source_type="LESSON", source_id=artifact.source_id,
        title=title, source_language=None, source_category=None,
        transformation_strategy="canonical_document", transformation_version="v1",
        provenance={}, blocks=blocks,
    )
