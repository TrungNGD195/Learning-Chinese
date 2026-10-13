from dataclasses import FrozenInstanceError, fields
from uuid import uuid4

import pytest

from app.ai.retrieval.filters import RetrievalFilter
from app.core.errors import ApplicationError


def test_none_dimensions_are_unrestricted_and_dimensions_are_exactly_v0():
    retrieval_filter = RetrievalFilter()
    assert all(getattr(retrieval_filter, item.name) is None for item in fields(retrieval_filter))
    assert {item.name for item in fields(retrieval_filter)} == {
        "lesson_ids", "hsk_levels", "content_types", "source_types",
        "source_categories", "source_languages",
    }


@pytest.mark.parametrize(
    "field",
    ["lesson_ids", "hsk_levels", "content_types", "source_types", "source_categories", "source_languages"],
)
def test_every_explicit_empty_dimension_is_invalid(field):
    with pytest.raises(ApplicationError) as error:
        RetrievalFilter(**{field: set()})
    assert error.value.code == "INVALID_RETRIEVAL_FILTER"
    assert error.value.status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [
        ("content_types", {"ESSAY"}),
        ("source_types", {"OTHER"}),
        ("source_categories", {"UNTRUSTED"}),
        ("source_languages", {"fr"}),
        ("hsk_levels", {"HSK 2"}),
        ("lesson_ids", {"not-a-uuid"}),
    ],
)
def test_noncanonical_values_are_rejected(field, value):
    with pytest.raises(ApplicationError) as error:
        RetrievalFilter(**{field: value})
    assert error.value.code == "INVALID_RETRIEVAL_FILTER_VALUE"


def test_document_only_and_lesson_ids_contradiction_is_rejected():
    with pytest.raises(ApplicationError) as error:
        RetrievalFilter(source_types={"DOCUMENT"}, lesson_ids={uuid4()})
    assert error.value.code == "INVALID_RETRIEVAL_FILTER_COMBINATION"


def test_supported_multi_values_are_normalized_to_immutable_frozensets():
    lesson_a, lesson_b = uuid4(), uuid4()
    retrieval_filter = RetrievalFilter(
        lesson_ids={lesson_a, lesson_b}, hsk_levels={2, 3},
        content_types={"GRAMMAR", "VOCABULARY"},
        source_types={"LESSON", "DOCUMENT"},
        source_categories={"CURRICULUM_MATERIAL", "INTERNAL_AUTHORED"},
        source_languages={"zh", "vi", "en"},
    )
    assert retrieval_filter.lesson_ids == frozenset({lesson_a, lesson_b})
    assert retrieval_filter.hsk_levels == frozenset({2, 3})
    assert retrieval_filter.content_types == frozenset({"GRAMMAR", "VOCABULARY"})
    with pytest.raises(FrozenInstanceError):
        retrieval_filter.lesson_ids = frozenset()
