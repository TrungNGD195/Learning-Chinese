from __future__ import annotations

import asyncio

from app.ai.retrieval.scopes import RetrievalScope, build_scope_filter
from app.ai.retrieval.service import SemanticRetrievalService
from app.evaluation.step73.runner import _candidate_in_scope, _retrieval_filter_for_tier
from app.database.session import SessionFactory
from step63_test_support import FakeProvider, settings_with_candidate_k
from step64_test_support import step64_corpus


def test_step73_internal_kb_attempt_retrieves_lesson_and_approved_document(step64_corpus):
    async def arrange():
        lesson = await step64_corpus.create_lesson(
            vector=[1.0, 0.0, 0.0], content="Published Lesson knowledge",
        )
        document = await step64_corpus.create_document(
            vector=[0.0, 1.0, 0.0], category="INTERNAL_AUTHORED",
            content="Approved internal Document knowledge",
        )
        return lesson, document

    lesson, document = asyncio.run(arrange())
    scope_filter = _retrieval_filter_for_tier("INTERNAL_KB", lesson_id=None)

    # Keep evaluator scope selection coupled to the frozen Step 6.8-A policy.
    assert scope_filter is build_scope_filter(RetrievalScope.INTERNAL_KB)
    assert scope_filter is None

    async def retrieve():
        async with SessionFactory() as session:
            provider = FakeProvider(step64_corpus.identity)
            candidates = await SemanticRetrievalService(
                session,
                provider=provider,
                settings=settings_with_candidate_k(20),
            ).retrieve("internal knowledge", retrieval_filter=scope_filter)
            return candidates, provider

    candidates, provider = asyncio.run(retrieve())
    found = {candidate.chunk_id: candidate for candidate in candidates}
    assert lesson["chunk_id"] in found
    assert document["chunk_id"] in found
    assert {found[lesson["chunk_id"]].source_type, found[document["chunk_id"]].source_type} == {
        "LESSON", "DOCUMENT",
    }
    assert _candidate_in_scope(found[lesson["chunk_id"]], "INTERNAL_KB", lesson_id=None)
    assert _candidate_in_scope(found[document["chunk_id"]], "INTERNAL_KB", lesson_id=None)
    assert provider.queries == ["internal knowledge"]
