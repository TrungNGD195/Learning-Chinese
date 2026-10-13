from uuid import uuid4

import pytest

from app.ai.retrieval.scopes import RetrievalScope, build_scope_filter
from app.core.errors import ApplicationError


def test_current_lesson_scope_requires_trusted_lesson_id():
    with pytest.raises(ApplicationError) as error:
        build_scope_filter(RetrievalScope.CURRENT_LESSON)
    assert error.value.code == "INVALID_RETRIEVAL_SCOPE"
    assert error.value.status_code == 422


def test_current_lesson_scope_uses_canonical_source_ownership():
    lesson_id = uuid4()
    retrieval_filter = build_scope_filter(
        RetrievalScope.CURRENT_LESSON, trusted_lesson_id=lesson_id
    )
    assert retrieval_filter.lesson_ids == frozenset({lesson_id})
    assert retrieval_filter.source_types == frozenset({"LESSON"})
    assert retrieval_filter.content_types is None


def test_internal_kb_scope_is_all_active_internal_knowledge_without_filter():
    assert build_scope_filter(RetrievalScope.INTERNAL_KB) is None


def test_unknown_scope_fails_closed():
    with pytest.raises(ApplicationError) as error:
        build_scope_filter("EXTERNAL")
    assert error.value.code == "INVALID_RETRIEVAL_SCOPE"


def test_retrieval_scope_has_only_the_two_frozen_values():
    assert {scope.value for scope in RetrievalScope} == {"CURRENT_LESSON", "INTERNAL_KB"}
