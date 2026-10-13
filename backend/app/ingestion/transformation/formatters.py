from collections.abc import Mapping, Sequence
from typing import Any


VOCABULARY_FIELDS = (
    ("hanzi", "Từ"),
    ("pinyin", "Pinyin"),
    ("vietnamese_meaning", "Nghĩa"),
    ("part_of_speech", "Từ loại"),
    ("example", "Ví dụ"),
    ("note", "Ghi chú"),
)
GRAMMAR_FIELDS = (
    ("name", "Ngữ pháp"),
    ("structure", "Cấu trúc"),
    ("explanation", "Giải thích"),
    ("usage", "Cách dùng"),
    ("example", "Ví dụ"),
    ("note", "Ghi chú"),
)


def labeled_text(data: Mapping[str, Any], fields: Sequence[tuple[str, str]]) -> str:
    return "\n".join(f"{label}: {data[key]}" for key, label in fields if isinstance(data.get(key), str) and data[key])
