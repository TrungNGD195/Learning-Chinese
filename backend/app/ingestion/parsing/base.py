from dataclasses import dataclass
from typing import Any, Protocol


class ParsingFailure(Exception):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class ParsedUnit:
    order: int
    text: str
    source_locator: dict[str, Any]


class DocumentParser(Protocol):
    name: str
    version: str

    def parse(self, raw: bytes) -> list[ParsedUnit]: ...
