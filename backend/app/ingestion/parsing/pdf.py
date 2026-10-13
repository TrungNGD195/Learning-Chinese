from importlib.metadata import version

import pymupdf as fitz

from app.ingestion.cleaning import clean_text
from app.ingestion.parsing.base import ParsedUnit, ParsingFailure


class PdfParser:
    name = "pymupdf"
    version = version("PyMuPDF")

    def parse(self, raw: bytes) -> list[ParsedUnit]:
        try:
            document = fitz.open(stream=raw, filetype="pdf")
            units = []
            for number, page in enumerate(document, start=1):
                text = clean_text(page.get_text("text"))
                if text.strip():
                    units.append(ParsedUnit(len(units), text, {"kind": "PDF_PAGE", "page_number": number}))
            document.close()
        except Exception as exc:
            raise ParsingFailure("PARSING_FAILED", "PDF text could not be extracted.") from exc
        if not units:
            raise ParsingFailure("NO_EXTRACTABLE_TEXT", "No extractable text was found in the PDF.")
        return units
