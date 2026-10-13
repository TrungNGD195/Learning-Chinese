from enum import StrEnum
from uuid import UUID

from app.ai.retrieval.errors import retrieval_error
from app.ai.retrieval.filters import RetrievalFilter


class RetrievalScope(StrEnum):
    CURRENT_LESSON = "CURRENT_LESSON"
    INTERNAL_KB = "INTERNAL_KB"


def build_scope_filter(
    scope: RetrievalScope,
    *,
    trusted_lesson_id: UUID | None = None,
) -> RetrievalFilter | None:
    try:
        resolved_scope = RetrievalScope(scope)
    except (TypeError, ValueError):
        raise retrieval_error("INVALID_RETRIEVAL_SCOPE", "Retrieval scope is invalid.", 422) from None

    if resolved_scope is RetrievalScope.INTERNAL_KB:
        return None
    if not isinstance(trusted_lesson_id, UUID):
        raise retrieval_error(
            "INVALID_RETRIEVAL_SCOPE",
            "CURRENT_LESSON requires a trusted Lesson ID.",
            422,
        )
    return RetrievalFilter(
        lesson_ids=frozenset({trusted_lesson_id}),
        source_types=frozenset({"LESSON"}),
    )
