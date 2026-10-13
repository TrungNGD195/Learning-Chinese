import re
import unicodedata

from app.ai.retrieval.errors import retrieval_error

_WHITESPACE = re.compile(r"\s+")


class QueryPreprocessor:
    """Apply deterministic, meaning-preserving query normalization."""

    @staticmethod
    def preprocess(query_text: str) -> str:
        if not isinstance(query_text, str):
            raise retrieval_error("EMPTY_RETRIEVAL_QUERY", "A non-empty query is required.", 422)
        normalized = unicodedata.normalize("NFC", query_text.strip())
        normalized = _WHITESPACE.sub(" ", normalized)
        if not normalized:
            raise retrieval_error("EMPTY_RETRIEVAL_QUERY", "A non-empty query is required.", 422)
        return normalized
