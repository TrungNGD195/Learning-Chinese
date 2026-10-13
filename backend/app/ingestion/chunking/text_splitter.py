from dataclasses import dataclass

from app.ingestion.chunking.config import DEFAULT_CHUNKING_CONFIG


@dataclass(frozen=True, slots=True)
class TextPart:
    text: str
    char_start: int
    char_end: int


_SEPARATOR_GROUPS = (
    ("paragraph", ("\r\n\r\n", "\n\n")),
    ("line", ("\r\n", "\n", "\r")),
    ("sentence", ("。", "！", "？", ".", "!", "?", "；", ";")),
    ("whitespace", (" ", "\t")),
)


def _preferred_end(text: str, start: int, hard_end: int, target: int) -> int:
    target_end = min(start + target, hard_end)
    # Search close to the target first, preserving the specified separator-class priority.
    low = max(start + 1, target_end - max(80, target // 3))
    for _name, separators in _SEPARATOR_GROUPS:
        candidates: list[int] = []
        for separator in separators:
            cursor = low
            while True:
                found = text.find(separator, cursor, hard_end)
                if found < 0:
                    break
                end = found + len(separator)
                if end > start and end <= hard_end:
                    candidates.append(end)
                cursor = found + 1
        if candidates:
            return min(candidates, key=lambda point: (abs(point - target_end), point))
    if target_end > start:
        return target_end
    return hard_end


def split_oversized_text(text: str, *, max_chars: int | None = None, target_chars: int | None = None,
                         overlap_chars: int | None = None) -> list[TextPart]:
    """Split one canonical textual unit only, recording zero-based [start,end) ranges."""
    maximum = max_chars or DEFAULT_CHUNKING_CONFIG.max_chars
    target = target_chars or DEFAULT_CHUNKING_CONFIG.target_chars
    overlap = DEFAULT_CHUNKING_CONFIG.overlap_chars if overlap_chars is None else overlap_chars
    if maximum <= 0 or target <= 0 or overlap < 0 or overlap >= maximum:
        raise ValueError("invalid deterministic splitter configuration")
    if len(text) <= maximum:
        return [TextPart(text=text, char_start=0, char_end=len(text))]
    parts: list[TextPart] = []
    start = 0
    while start < len(text):
        hard_end = min(start + maximum, len(text))
        end = len(text) if hard_end == len(text) else _preferred_end(text, start, hard_end, target)
        if end <= start:
            raise ValueError("deterministic splitter failed to advance")
        parts.append(TextPart(text=text[start:end], char_start=start, char_end=end))
        if end == len(text):
            break
        next_start = max(start + 1, end - overlap)
        start = next_start
    return parts
