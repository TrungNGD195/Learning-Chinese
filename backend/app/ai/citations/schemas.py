from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal, Mapping, TypeAlias
from uuid import UUID


@dataclass(frozen=True)
class CitationOccurrence:
    label: str
    start: int
    end: int


@dataclass(frozen=True)
class CitationParseResult:
    occurrences: tuple[CitationOccurrence, ...]
    occurrence_count: int


@dataclass(frozen=True)
class InternalCitationSource:
    label: str
    chunk_id: UUID
    source_type: Literal["DOCUMENT", "LESSON"]
    title: str
    page_number: int | None = None
    section: str | None = None


@dataclass(frozen=True)
class ExternalCitationSource:
    label: str
    title: str
    url: str


CitationSource: TypeAlias = InternalCitationSource | ExternalCitationSource


@dataclass(frozen=True)
class ValidatedCitation:
    label: str
    source_kind: Literal["INTERNAL_CHUNK", "EXTERNAL_URL"]
    title: str
    chunk_id: UUID | None = None
    url: str | None = None
    domain: str | None = None
    source_type: str | None = None
    locator: Mapping[str, object] | None = None
    metadata: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        if self.locator is not None:
            object.__setattr__(self, "locator", MappingProxyType(dict(self.locator)))
        if self.metadata is not None:
            object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True)
class CitationValidationResult:
    text: str
    cited_labels: tuple[str, ...]
    citations: tuple[ValidatedCitation, ...]
    citation_count: int
    occurrence_count: int
    status: Literal["VALID"] = "VALID"
