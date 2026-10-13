from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID

from app.ai.retrieval.errors import retrieval_error


@dataclass(frozen=True, slots=True)
class RetrievalFilter:
    """Immutable V0 eligibility constraints applied before vector Top-K."""

    lesson_ids: frozenset[UUID] | None = None
    hsk_levels: frozenset[int] | None = None
    content_types: frozenset[str] | None = None
    source_types: frozenset[str] | None = None
    source_categories: frozenset[str] | None = None
    source_languages: frozenset[str] | None = None

    _CANONICAL: ClassVar[dict[str, frozenset[str]]] = {
        "content_types": frozenset({"DOCUMENT_TEXT", "VOCABULARY", "GRAMMAR", "LESSON_GENERAL"}),
        "source_types": frozenset({"DOCUMENT", "LESSON"}),
        "source_categories": frozenset({"CURRICULUM_MATERIAL", "INTERNAL_AUTHORED"}),
        "source_languages": frozenset({"vi", "zh", "en"}),
    }
    _COLLECTION_FIELDS: ClassVar[tuple[str, ...]] = (
        "lesson_ids", "hsk_levels", "content_types", "source_types",
        "source_categories", "source_languages",
    )

    def __post_init__(self) -> None:
        self.validate(normalize=True)

    def validate(self, *, normalize: bool = False) -> None:
        for field_name in self._COLLECTION_FIELDS:
            values = getattr(self, field_name)
            if values is None:
                continue
            if isinstance(values, (str, bytes, dict)) or not isinstance(
                values, (set, frozenset, list, tuple)
            ):
                raise retrieval_error(
                    "INVALID_RETRIEVAL_FILTER",
                    "Retrieval filter dimensions must be collections.",
                    422,
                )
            if not values:
                raise retrieval_error(
                    "INVALID_RETRIEVAL_FILTER",
                    "An explicit empty retrieval filter is not allowed.",
                    422,
                )
            try:
                normalized = frozenset(values)
            except TypeError:
                raise retrieval_error(
                    "INVALID_RETRIEVAL_FILTER_VALUE",
                    "Retrieval filter contains an invalid value.",
                    422,
                ) from None
            if field_name == "lesson_ids":
                valid = all(isinstance(value, UUID) for value in normalized)
            elif field_name == "hsk_levels":
                valid = all(type(value) is int for value in normalized)
            else:
                valid = all(
                    isinstance(value, str) and value in self._CANONICAL[field_name]
                    for value in normalized
                )
            if not valid:
                raise retrieval_error(
                    "INVALID_RETRIEVAL_FILTER_VALUE",
                    "Retrieval filter contains a non-canonical value.",
                    422,
                )
            if normalize and not isinstance(values, frozenset):
                object.__setattr__(self, field_name, normalized)

        if self.source_types == frozenset({"DOCUMENT"}) and self.lesson_ids is not None:
            raise retrieval_error(
                "INVALID_RETRIEVAL_FILTER_COMBINATION",
                "Document-only retrieval cannot be combined with Lesson IDs.",
                422,
            )
