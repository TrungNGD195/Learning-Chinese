from __future__ import annotations

import re

from app.ai.citations.errors import CITATION_FORMAT_INVALID, citation_error
from app.ai.citations.schemas import CitationOccurrence, CitationParseResult

_LABEL = re.compile(r"S[1-9][0-9]*\Z")
_CITATION_LIKE = re.compile(r"(?:\s*S|\s*\^)", re.IGNORECASE)


def _fenced_ranges(text: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    offset = 0
    opened: tuple[str, int, int] | None = None
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        if opened is None:
            match = re.match(r" {0,3}(`{3,}|~{3,})", content)
            if match:
                fence = match.group(1)
                opened = (fence[0], len(fence), offset)
        else:
            char, length, start = opened
            match = re.match(rf" {{0,3}}{re.escape(char)}{{{length},}}\s*$", content)
            if match:
                ranges.append((start, offset + len(line)))
                opened = None
        offset += len(line)
    if opened is not None:
        ranges.append((opened[2], len(text)))
    return ranges


def _inside(index: int, ranges: list[tuple[int, int]], range_index: int) -> tuple[bool, int]:
    while range_index < len(ranges) and ranges[range_index][1] <= index:
        range_index += 1
    return (
        range_index < len(ranges) and ranges[range_index][0] <= index < ranges[range_index][1],
        range_index,
    )


def _closing_inline_code(text: str, start: int, delimiter_length: int) -> int | None:
    i = start
    while i < len(text):
        if text[i] == "`":
            end = i
            while end < len(text) and text[end] == "`":
                end += 1
            if end - i == delimiter_length:
                return end
            i = end
        else:
            i += 1
    return None


def _link_end(text: str, label_close: int) -> int | None:
    if label_close + 1 >= len(text) or text[label_close + 1] != "(":
        return None
    depth = 1
    i = label_close + 2
    escaped = False
    while i < len(text):
        char = text[i]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(text)


def parse_citations(text: str) -> CitationParseResult:
    """Find citation tokens in eligible prose, retaining offsets into original text."""
    if not isinstance(text, str):
        raise citation_error(CITATION_FORMAT_INVALID)
    fences = _fenced_ranges(text)
    fence_index = 0
    found: list[CitationOccurrence] = []
    i = 0
    while i < len(text):
        excluded, fence_index = _inside(i, fences, fence_index)
        if excluded:
            i = fences[fence_index][1]
            continue
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == "`":
            end = i
            while end < len(text) and text[end] == "`":
                end += 1
            close = _closing_inline_code(text, end, end - i)
            if close is not None:
                i = close
                continue
            i = end
            continue
        if text[i] != "[":
            i += 1
            continue
        close = text.find("]", i + 1)
        if close < 0:
            candidate = text[i + 1 : i + 32]
            if _CITATION_LIKE.match(candidate):
                raise citation_error(CITATION_FORMAT_INVALID)
            i += 1
            continue
        link_end = _link_end(text, close)
        if link_end is not None:
            i = link_end
            continue
        token = text[i + 1 : close]
        if _LABEL.fullmatch(token):
            found.append(CitationOccurrence(label=token, start=i, end=close + 1))
        elif _CITATION_LIKE.match(token):
            raise citation_error(CITATION_FORMAT_INVALID)
        i = close + 1
    occurrences = tuple(found)
    return CitationParseResult(occurrences=occurrences, occurrence_count=len(occurrences))
