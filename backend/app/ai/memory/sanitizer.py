import re

_HISTORICAL_CITATION = re.compile(r"\[S[1-9][0-9]*\]")


def sanitize_historical_assistant_text(text: str) -> str:
    return _HISTORICAL_CITATION.sub("", text)
