from importlib.metadata import version
from io import BytesIO

from docx import Document as open_document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.ingestion.cleaning import clean_text
from app.ingestion.parsing.base import ParsedUnit, ParsingFailure


class DocxParser:
    name = "python-docx"
    version = version("python-docx")

    def parse(self, raw: bytes) -> list[ParsedUnit]:
        try:
            document = open_document(BytesIO(raw))
            units: list[ParsedUnit] = []
            table_index = 0
            for block_index, child in enumerate(document.element.body.iterchildren()):
                if isinstance(child, CT_P):
                    text = clean_text(Paragraph(child, document).text)
                    if text:
                        units.append(ParsedUnit(len(units), text, {"kind": "DOCX_PARAGRAPH", "block_index": block_index}))
                elif isinstance(child, CT_Tbl):
                    table = Table(child, document)
                    for row_index, row in enumerate(table.rows):
                        text = clean_text("\t".join(clean_text(cell.text) for cell in row.cells), preserve_spaces=True)
                        units.append(ParsedUnit(len(units), text, {
                            "kind": "DOCX_TABLE_ROW", "block_index": block_index,
                            "table_index": table_index, "row_index": row_index,
                        }))
                    table_index += 1
            return units
        except ParsingFailure:
            raise
        except Exception as exc:
            raise ParsingFailure("PARSING_FAILED", "DOCX text could not be extracted.") from exc
