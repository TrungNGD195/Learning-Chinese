import re

from app.ingestion.cleaning import clean_text
from app.ingestion.parsing.base import ParsedUnit


_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_LIST = re.compile(r"^(\s*)([-+*]|\d+[.)])\s+(.*)$")
_FENCE = re.compile(r"^\s*(```+|~~~+)")


class MarkdownParser:
    name = "markdown_blocks"
    version = "v1"

    def parse(self, raw: bytes) -> list[ParsedUnit]:
        try:
            text = raw.decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError as exc:
            from app.ingestion.parsing.base import ParsingFailure
            raise ParsingFailure("TEXT_DECODING_FAILED", "Text input is not valid UTF-8.") from exc
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        units: list[ParsedUnit] = []
        block_index = 0
        i = 0
        while i < len(lines):
            line = lines[i]
            if not line.strip():
                i += 1
                continue
            fence = _FENCE.match(line)
            if fence:
                marker = fence.group(1)
                code = []
                i += 1
                while i < len(lines) and not lines[i].lstrip().startswith(marker[:3]):
                    code.append(lines[i])
                    i += 1
                if i < len(lines):
                    i += 1
                value = clean_text("\n".join(code), preserve_spaces=True)
                kind = "CODE_BLOCK"
                locator = {"kind": "MARKDOWN_BLOCK", "block_index": block_index, "block_kind": kind}
            elif heading := _HEADING.match(line):
                value = clean_text(heading.group(2))
                kind = "HEADING"
                locator = {"kind": "MARKDOWN_BLOCK", "block_index": block_index, "block_kind": kind, "heading_level": len(heading.group(1))}
                i += 1
            elif match := _LIST.match(line):
                marker, first = match.group(2), match.group(3)
                values = [first]
                i += 1
                while i < len(lines) and lines[i].strip() and lines[i][:1].isspace() and not _LIST.match(lines[i]):
                    values.append(lines[i].strip())
                    i += 1
                value = clean_text("\n".join(values))
                kind = "LIST_ITEM"
                locator = {"kind": "MARKDOWN_BLOCK", "block_index": block_index, "block_kind": kind,
                           "list_kind": "ordered" if marker[0].isdigit() else "unordered"}
            else:
                values = [line.strip()]
                i += 1
                while i < len(lines) and lines[i].strip() and not _HEADING.match(lines[i]) and not _LIST.match(lines[i]) and not _FENCE.match(lines[i]):
                    values.append(lines[i].strip())
                    i += 1
                value = clean_text("\n".join(values))
                kind = "PARAGRAPH"
                locator = {"kind": "MARKDOWN_BLOCK", "block_index": block_index, "block_kind": kind}
            if value:
                units.append(ParsedUnit(len(units), value, locator))
                block_index += 1
        return units
