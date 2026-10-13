import asyncio
import inspect
from uuid import uuid4

import pytest

from app.ai.retrieval.filters import RetrievalFilter
from app.ai.retrieval.scopes import RetrievalScope, build_scope_filter
from app.ai.retrieval.service import SemanticRetrievalService
from app.core.errors import ApplicationError
from app.database.session import SessionFactory
from step63_test_support import FakeProvider, make_identity, settings_with_candidate_k
from step64_test_support import step64_corpus


def test_current_lesson_scope_reaches_sql_filter_before_candidate_k(step64_corpus):
    async def setup():
        l2 = await step64_corpus.create_lesson(vector=[1., 0., 0.])
        l1 = await step64_corpus.create_lesson(vector=[0.8, 0.6, 0.])
        document = await step64_corpus.create_document(vector=[0., 1., 0.])
        return l1, l2, document

    lesson_1, lesson_2, document = asyncio.run(setup())
    retrieval_filter = build_scope_filter(
        RetrievalScope.CURRENT_LESSON, trusted_lesson_id=lesson_1["lesson_id"]
    )

    async def run():
        async with SessionFactory() as session:
            provider = FakeProvider(step64_corpus.identity, vector=[1., 0., 0.])
            service = SemanticRetrievalService(
                session, provider=provider, settings=settings_with_candidate_k(1)
            )
            candidates = await service.retrieve("用法", retrieval_filter=retrieval_filter)
        assert provider.queries == ["用法"]
        return candidates

    candidates = asyncio.run(run())
    assert len(candidates) == 1
    assert candidates[0].chunk_id == lesson_1["chunk_id"]
    assert candidates[0].rank == 1
    assert candidates[0].source_lesson_id == lesson_1["lesson_id"]
    assert lesson_2["chunk_id"] != candidates[0].chunk_id
    assert document["chunk_id"] != candidates[0].chunk_id


def test_internal_kb_scope_includes_active_lessons_and_documents(step64_corpus):
    async def setup():
        lesson = await step64_corpus.create_lesson(vector=[1., 0., 0.])
        document = await step64_corpus.create_document(
            vector=[0., 1., 0.], category="INTERNAL_AUTHORED", language="en"
        )
        return lesson, document

    lesson, document = asyncio.run(setup())
    retrieval_filter = build_scope_filter(RetrievalScope.INTERNAL_KB)
    assert retrieval_filter is None

    async def run():
        async with SessionFactory() as session:
            candidates = await SemanticRetrievalService(
                session,
                provider=FakeProvider(step64_corpus.identity),
                settings=settings_with_candidate_k(20),
            ).retrieve("query", retrieval_filter=retrieval_filter)
        return candidates

    candidates = asyncio.run(run())
    assert {item.chunk_id for item in candidates} == {lesson["chunk_id"], document["chunk_id"]}
    assert {item.source_type for item in candidates} == {"LESSON", "DOCUMENT"}


def test_invalid_filter_fails_before_provider_and_database_work(step64_corpus):
    retrieval_filter = RetrievalFilter(content_types={"GRAMMAR"})
    object.__setattr__(retrieval_filter, "content_types", frozenset())
    provider = FakeProvider(step64_corpus.identity)

    async def run():
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await SemanticRetrievalService(session, provider=provider).retrieve(
                    "query", retrieval_filter=retrieval_filter
                )
        assert error.value.code == "INVALID_RETRIEVAL_FILTER"
        assert provider.queries == []

    asyncio.run(run())


def test_non_filter_input_is_rejected_without_falling_back_to_unfiltered(step64_corpus):
    provider = FakeProvider(step64_corpus.identity)

    async def run():
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await SemanticRetrievalService(session, provider=provider).retrieve(
                    "query", retrieval_filter={"lesson_ids": [str(uuid4())]}
                )
        assert error.value.code == "INVALID_RETRIEVAL_FILTER"
        assert provider.queries == []

    asyncio.run(run())


def test_missing_current_lesson_trusted_id_fails_before_provider_call():
    provider = FakeProvider(make_identity())
    with pytest.raises(ApplicationError) as error:
        retrieval_filter = build_scope_filter(RetrievalScope.CURRENT_LESSON)
        asyncio.run(_retrieve_without_scope(retrieval_filter, provider))
    assert error.value.code == "INVALID_RETRIEVAL_SCOPE"
    assert provider.queries == []


async def _retrieve_without_scope(retrieval_filter, provider):
    async with SessionFactory() as session:
        await SemanticRetrievalService(session, provider=provider).retrieve(
            "query", retrieval_filter=retrieval_filter
        )


def test_unknown_lesson_id_is_valid_empty_result_without_extra_scope_lookup(step64_corpus):
    retrieval_filter = RetrievalFilter(lesson_ids={uuid4()}, source_types={"LESSON"})

    async def run():
        async with SessionFactory() as session:
            provider = FakeProvider(step64_corpus.identity)
            results = await SemanticRetrievalService(
                session, provider=provider
            ).retrieve("query", retrieval_filter=retrieval_filter)
        assert provider.queries == ["query"]
        assert results == []

    asyncio.run(run())


def test_filter_logging_uses_counts_and_enum_shapes_without_ids_or_content():
    retrieval_filter = RetrievalFilter(
        lesson_ids={uuid4()}, content_types={"GRAMMAR", "VOCABULARY"},
        source_types={"LESSON"},
    )
    fields = SemanticRetrievalService._filter_log_fields(retrieval_filter)
    assert fields["lesson_filter_count"] == 1
    assert fields["hsk_filter_count"] == 0
    assert fields["content_types"] == ["GRAMMAR", "VOCABULARY"]
    assert fields["source_types"] == ["LESSON"]
    assert str(next(iter(retrieval_filter.lesson_ids))) not in repr(fields)
    assert "retrieval_filter" not in repr(fields)


def test_retrieve_filter_is_keyword_only_and_candidate_k_is_not_overridable():
    signature = inspect.signature(SemanticRetrievalService.retrieve)
    assert list(signature.parameters) == ["self", "query_text", "retrieval_filter"]
    assert signature.parameters["retrieval_filter"].kind is inspect.Parameter.KEYWORD_ONLY
    assert "candidate_k" not in signature.parameters
