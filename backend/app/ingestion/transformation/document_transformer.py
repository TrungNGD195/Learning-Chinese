from typing import Any

from app.ingestion.parsing.base import ParsingFailure
from app.ingestion.transformation.models import (
    CanonicalBlock, ParsedCleanedArtifactInput, SourceMetadataSnapshot, TransformedDocument,
)


def _block(order: int, kind: str, text: str, locator: dict[str, Any], *, path=None, structured=None):
    return CanonicalBlock(
        order=order, content_type="DOCUMENT_TEXT", block_kind=kind, text=text,
        section_path=path or [], source_locator=locator,
        structured_data=structured or {}, metadata={},
    )


def transform_document(artifact: ParsedCleanedArtifactInput, snapshot: SourceMetadataSnapshot) -> TransformedDocument:
    if artifact.source_type != "DOCUMENT" or snapshot.source_type != "DOCUMENT" or artifact.source_id != snapshot.source_id:
        raise ParsingFailure("INVALID_SOURCE_LOCATOR", "Parsed document identity does not match its metadata snapshot.")
    if not snapshot.title or not snapshot.title.strip() or not snapshot.source_language or not snapshot.source_category or not snapshot.source_origin or not snapshot.source_origin.strip():
        raise ParsingFailure("TRANSFORMATION_FAILED", "Required Document source metadata is unavailable.")

    raw_blocks: list[CanonicalBlock] = []
    heading_stack: list[str] = []
    units = artifact.units
    index = 0
    while index < len(units):
        unit = units[index]
        locator = unit.source_locator
        kind = locator.get("kind")
        if not unit.text and kind != "DOCX_TABLE_ROW":
            index += 1
            continue
        if kind == "PDF_PAGE":
            if not isinstance(locator.get("page_number"), int) or locator["page_number"] < 1:
                raise ParsingFailure("INVALID_SOURCE_LOCATOR", "PDF page locator is invalid.")
            raw_blocks.append(_block(len(raw_blocks), "PARAGRAPH", unit.text, locator))
        elif kind == "DOCX_PARAGRAPH":
            if not isinstance(locator.get("block_index"), int) or locator["block_index"] < 0:
                raise ParsingFailure("INVALID_SOURCE_LOCATOR", "DOCX paragraph locator is invalid.")
            raw_blocks.append(_block(len(raw_blocks), "PARAGRAPH", unit.text, locator))
        elif kind == "TEXT_BLOCK":
            if not isinstance(locator.get("block_index"), int) or locator["block_index"] < 0:
                raise ParsingFailure("INVALID_SOURCE_LOCATOR", "Text block locator is invalid.")
            raw_blocks.append(_block(len(raw_blocks), "PARAGRAPH", unit.text, locator))
        elif kind == "DOCX_TABLE_ROW":
            table_index = locator.get("table_index")
            if not isinstance(table_index, int) or table_index < 0 or not isinstance(locator.get("row_index"), int):
                raise ParsingFailure("INVALID_SOURCE_LOCATOR", "DOCX table row locator is invalid.")
            rows = []
            locators = []
            while index < len(units):
                candidate = units[index]
                candidate_locator = candidate.source_locator
                if candidate_locator.get("kind") != "DOCX_TABLE_ROW" or candidate_locator.get("table_index") != table_index:
                    break
                if not isinstance(candidate_locator.get("row_index"), int) or (rows and candidate_locator["row_index"] <= rows[-1]["row_index"]):
                    raise ParsingFailure("INVALID_SOURCE_LOCATOR", "DOCX table row order is invalid.")
                rows.append({"row_index": candidate_locator["row_index"], "text": candidate.text})
                locators.append(candidate_locator)
                index += 1
            raw_blocks.append(_block(len(raw_blocks), "TABLE", "\n".join(row["text"] for row in rows),
                                     {"kind": "DOCX_TABLE", "table_index": table_index, "rows": locators},
                                     structured={"table_index": table_index, "rows": rows}))
            continue
        elif kind == "MARKDOWN_BLOCK":
            block_kind = locator.get("block_kind")
            block_index = locator.get("block_index")
            if not isinstance(block_index, int) or block_index < 0:
                raise ParsingFailure("INVALID_SOURCE_LOCATOR", "Markdown block locator is invalid.")
            if block_kind == "HEADING":
                level = locator.get("heading_level")
                if not isinstance(level, int) or not 1 <= level <= 6:
                    raise ParsingFailure("INVALID_SOURCE_LOCATOR", "Markdown heading locator is invalid.")
                heading_stack = heading_stack[:level - 1]
                heading_stack.append(unit.text)
                raw_blocks.append(_block(len(raw_blocks), "HEADING", unit.text, locator, path=list(heading_stack)))
            elif block_kind == "PARAGRAPH":
                raw_blocks.append(_block(len(raw_blocks), "PARAGRAPH", unit.text, locator, path=list(heading_stack)))
            elif block_kind == "CODE_BLOCK":
                raw_blocks.append(_block(len(raw_blocks), "CODE_BLOCK", unit.text, locator, path=list(heading_stack)))
            elif block_kind == "LIST_ITEM":
                list_kind = locator.get("list_kind")
                if list_kind not in {"ordered", "unordered"}:
                    raise ParsingFailure("INVALID_SOURCE_LOCATOR", "Markdown list locator is invalid.")
                members = []
                items = []
                while index < len(units):
                    candidate = units[index]
                    candidate_locator = candidate.source_locator
                    if (candidate_locator.get("kind") != "MARKDOWN_BLOCK"
                            or candidate_locator.get("block_kind") != "LIST_ITEM"
                            or candidate_locator.get("list_kind") != list_kind):
                        break
                    if candidate_locator.get("block_index") != block_index + len(items):
                        break
                    members.append(candidate_locator)
                    items.append(candidate.text)
                    index += 1
                raw_blocks.append(_block(len(raw_blocks), "LIST", "\n".join(items),
                    {"kind": "MARKDOWN_LIST", "list_kind": list_kind, "members": members},
                    path=list(heading_stack), structured={"list_kind": list_kind, "items": items}))
                continue
            else:
                raise ParsingFailure("UNSUPPORTED_CONTENT_TYPE", "Parsed Markdown block type is unsupported.")
        else:
            raise ParsingFailure("INVALID_SOURCE_LOCATOR", "Parsed Document source locator is unsupported.")
        index += 1

    blocks = [block for block in raw_blocks if block.text or block.structured_data]
    blocks = [block.model_copy(update={"order": order}) for order, block in enumerate(blocks)]
    provenance = {
        "source_origin": snapshot.source_origin,
        "usage_rights_note": snapshot.usage_rights_note,
        "original_filename": snapshot.original_filename,
    }
    return TransformedDocument(
        schema_version="transformed_document/v1", source_type="DOCUMENT", source_id=artifact.source_id,
        title=snapshot.title, source_language=snapshot.source_language, source_category=snapshot.source_category,
        transformation_strategy="canonical_document", transformation_version="v1",
        provenance=provenance, blocks=blocks,
    )
