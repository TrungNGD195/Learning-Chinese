import re

from app.ingestion.cleaning import clean_text
from app.ingestion.parsing.base import ParsedUnit, ParsingFailure


class TxtParser:
    name = "txt_utf8"
    version = "v1"

    def parse(self, raw: bytes) -> list[ParsedUnit]:
        try:
            text = raw.decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError as exc:
            raise ParsingFailure("TEXT_DECODING_FAILED", "Text input is not valid UTF-8.") from exc
        text = clean_text(text)
        blocks = re.split(r"\n\s*\n", text)
        units = []
        for source_index, block in enumerate(blocks):
            if block.strip():
                units.append(ParsedUnit(len(units), clean_text(block), {"kind": "TEXT_BLOCK", "block_index": source_index}))
        return units
