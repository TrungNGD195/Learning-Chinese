import asyncio
import inspect
import logging
import math
from dataclasses import replace
from uuid import uuid4

import pytest
import psycopg
from sqlalchemy import func, select

from app.ai.embeddings.errors import embedding_error
from app.ai.retrieval import repository
from app.ai.retrieval.schemas import CandidateMetadata
from app.ai.retrieval.service import SemanticRetrievalService
from app.ai.vector_storage.service import VectorStorageService
from app.core.errors import ApplicationError
from app.core.config import get_settings
from app.database.models import Embedding, EmbeddingProfile, Message, MessageRetrieval
from app.database.session import SessionFactory
from step62_test_support import step62_state
from step63_test_support import (
    FakeProvider,
    create_profile,
    make_identity,
    settings_with_candidate_k,
)


def test_retrieve_uses_normalized_query_once_and_does_not_write(step62_state, caplog):
    async def run():
        identity = make_identity()
        profile_id = await create_profile(step62_state, identity)
        source_id = await step62_state.create_source()
        _, chunk_ids = await step62_state.create_version(
            source_id, status="ACTIVE",
            profile_vectors={profile_id: [[1., 0., 0.], [0., 1., 0.]]},
        )
        async with SessionFactory.begin() as session:
            from app.database.models import Chunk
            chunk = await session.get(Chunk, chunk_ids[0])
            chunk.content = "no-logging-content-sentinel"
        async with SessionFactory() as session:
            before = (
                await session.scalar(select(func.count()).select_from(Embedding)),
                await session.scalar(select(func.count()).select_from(MessageRetrieval)),
                await session.scalar(select(func.count()).select_from(Message)),
            )
            await session.rollback()
            provider = FakeProvider(identity)
            service = SemanticRetrievalService(
                session, provider=provider, settings=settings_with_candidate_k(20)
            )
            with caplog.at_level(logging.INFO):
                candidates = await service.retrieve("  private-query-sentinel\t使用 了？  ")
            after = (
                await session.scalar(select(func.count()).select_from(Embedding)),
                await session.scalar(select(func.count()).select_from(MessageRetrieval)),
                await session.scalar(select(func.count()).select_from(Message)),
            )
        assert provider.queries == ["private-query-sentinel 使用 了？"]
        assert provider.documents_calls == 0
        assert [item.chunk_id for item in candidates] == chunk_ids
        assert [item.rank for item in candidates] == [1, 2]
        assert [item.distance for item in candidates] == [0.0, 1.0]
        assert [item.retrieval_score for item in candidates] == [1.0, 0.0]
        assert before == after
        assert not hasattr(candidates[0], "vector")
        assert "private-query-sentinel" not in caplog.text
        assert "no-logging-content-sentinel" not in caplog.text
        assert "1.0, 0.0, 0.0" not in caplog.text

    asyncio.run(run())


@pytest.mark.parametrize(
    "field,wrong_value",
    [
        ("provider", "OTHER"),
        ("provider_version", "other-provider-version"),
        ("model_name", "other-model"),
        ("model_version", "other-model-version"),
        ("dimensions", 4),
        ("embedding_input_version", "other-input"),
        ("normalize_embeddings", False),
    ],
)
def test_provider_profile_identity_mismatch_stops_before_embedding(
    step62_state, monkeypatch, field, wrong_value
):
    async def run():
        identity = make_identity()
        await create_profile(step62_state, identity)
        provider = FakeProvider(replace(identity, **{field: wrong_value}))

        async def must_not_search(*args, **kwargs):
            raise AssertionError("vector search must not run after an identity mismatch")

        monkeypatch.setattr(VectorStorageService, "nearest_vectors", must_not_search)
        async with SessionFactory() as session:
            service = SemanticRetrievalService(session, provider=provider)
            with pytest.raises(ApplicationError) as error:
                await service.retrieve("query")
        assert error.value.code == "QUERY_EMBEDDING_FAILED"
        assert provider.queries == []

    asyncio.run(run())


def test_missing_active_profile_uses_step62_error_and_does_not_embed(step62_state):
    async def run():
        identity = make_identity()
        provider = FakeProvider(identity)
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await SemanticRetrievalService(session, provider=provider).retrieve("query")
        assert error.value.code == "ACTIVE_EMBEDDING_PROFILE_NOT_FOUND"
        assert error.value.status_code == 409
        assert provider.queries == []

    asyncio.run(run())


def test_empty_query_fails_before_profile_or_provider_access(step62_state):
    async def run():
        provider = FakeProvider(make_identity())
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await SemanticRetrievalService(session, provider=provider).retrieve(" \t ")
        assert error.value.code == "EMPTY_RETRIEVAL_QUERY"
        assert provider.queries == []

    asyncio.run(run())


def test_multiple_active_profile_resolver_error_is_preserved(monkeypatch):
    async def multiple(self):
        raise ApplicationError(
            "MULTIPLE_ACTIVE_EMBEDDING_PROFILES", "Multiple profiles.", status_code=500
        )

    monkeypatch.setattr(VectorStorageService, "resolve_active_profile", multiple)

    async def run():
        provider = FakeProvider(make_identity())
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await SemanticRetrievalService(session, provider=provider).retrieve("query")
        assert error.value.code == "MULTIPLE_ACTIVE_EMBEDDING_PROFILES"
        assert provider.queries == []

    asyncio.run(run())


@pytest.mark.parametrize(
    "vector",
    [None, [1.0, 0.0], [1.0, math.nan, 0.0], [1.0, math.inf, 0.0], [0.0, 0.0, 0.0]],
)
def test_invalid_query_vectors_never_reach_search(step62_state, monkeypatch, vector):
    async def run():
        identity = make_identity()
        await create_profile(step62_state, identity)
        provider = FakeProvider(identity, vector=vector)

        async def must_not_search(*args, **kwargs):
            raise AssertionError("invalid query vector must not reach vector search")

        monkeypatch.setattr(VectorStorageService, "nearest_vectors", must_not_search)
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await SemanticRetrievalService(session, provider=provider).retrieve("query")
        assert error.value.code == "INVALID_QUERY_EMBEDDING"

    asyncio.run(run())


def test_provider_oversized_query_maps_to_422_without_raw_detail(step62_state, caplog):
    async def run():
        identity = make_identity()
        await create_profile(step62_state, identity)
        provider = FakeProvider(
            identity,
            error=embedding_error(
                "EMBEDDING_INPUT_TOO_LONG", "raw-provider-sentinel", 422
            ),
        )
        with caplog.at_level(logging.WARNING):
            async with SessionFactory() as session:
                with pytest.raises(ApplicationError) as error:
                    await SemanticRetrievalService(session, provider=provider).retrieve("private query")
        assert error.value.code == "RETRIEVAL_QUERY_TOO_LONG"
        assert error.value.status_code == 422
        assert "raw-provider-sentinel" not in caplog.text
        assert "private query" not in caplog.text

    asyncio.run(run())


def test_generic_provider_failure_is_normalized_and_not_logged(step62_state, caplog):
    async def run():
        identity = make_identity()
        await create_profile(step62_state, identity)
        provider = FakeProvider(identity, error=RuntimeError("provider-secret-sentinel"))
        with caplog.at_level(logging.WARNING):
            async with SessionFactory() as session:
                with pytest.raises(ApplicationError) as error:
                    await SemanticRetrievalService(session, provider=provider).retrieve(
                        "private query sentinel"
                    )
        assert error.value.code == "QUERY_EMBEDDING_FAILED"
        assert "provider-secret-sentinel" not in caplog.text
        assert "private query sentinel" not in caplog.text

    asyncio.run(run())


def test_provider_runs_outside_database_transaction(step62_state):
    async def run():
        identity = make_identity()
        profile_id = await create_profile(step62_state, identity)
        source_id = await step62_state.create_source()
        await step62_state.create_version(
            source_id, status="ACTIVE", profile_vectors={profile_id: [[1., 0., 0.], [0., 1., 0.]]}
        )
        holder = {}

        def check_transaction():
            assert not holder["session"].in_transaction()

        provider = FakeProvider(identity, on_embed=check_transaction)
        async with SessionFactory() as session:
            holder["session"] = session
            await SemanticRetrievalService(session, provider=provider).retrieve("query")
        assert provider.queries == ["query"]

    asyncio.run(run())


def test_vector_order_is_preserved_when_hydration_rows_arrive_reversed(step62_state, monkeypatch):
    async def run():
        identity = make_identity()
        profile_id = await create_profile(step62_state, identity)
        source_id = await step62_state.create_source()
        _, chunk_ids = await step62_state.create_version(
            source_id, status="ACTIVE",
            profile_vectors={profile_id: [[1., 0., 0.], [0., 1., 0.]]},
        )
        original = repository.load_candidate_metadata

        async def reversed_metadata(session, ids):
            return list(reversed(await original(session, ids)))

        monkeypatch.setattr(repository, "load_candidate_metadata", reversed_metadata)
        async with SessionFactory() as session:
            candidates = await SemanticRetrievalService(
                session, provider=FakeProvider(identity)
            ).retrieve("query")
        assert [item.chunk_id for item in candidates] == chunk_ids
        assert [item.rank for item in candidates] == [1, 2]

    asyncio.run(run())


def test_hydration_missing_result_fails_instead_of_dropping_candidate(step62_state, monkeypatch):
    async def run():
        identity = make_identity()
        profile_id = await create_profile(step62_state, identity)
        source_id = await step62_state.create_source()
        await step62_state.create_version(
            source_id, status="ACTIVE", profile_vectors={profile_id: [[1., 0., 0.], [0., 1., 0.]]}
        )

        async def missing(session, ids):
            return []

        monkeypatch.setattr(repository, "load_candidate_metadata", missing)
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await SemanticRetrievalService(
                    session, provider=FakeProvider(identity)
                ).retrieve("query")
        assert error.value.code == "SEMANTIC_RETRIEVAL_FAILED"

    asyncio.run(run())


def test_hydration_database_failure_is_semantic_failure(step62_state, monkeypatch):
    async def run():
        identity = make_identity()
        profile_id = await create_profile(step62_state, identity)
        source_id = await step62_state.create_source()
        await step62_state.create_version(
            source_id, status="ACTIVE", profile_vectors={profile_id: [[1., 0., 0.], [0., 1., 0.]]}
        )

        async def broken(session, ids):
            raise RuntimeError("raw-sql-sentinel")

        monkeypatch.setattr(repository, "load_candidate_metadata", broken)
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await SemanticRetrievalService(
                    session, provider=FakeProvider(identity)
                ).retrieve("query")
        assert error.value.code == "SEMANTIC_RETRIEVAL_FAILED"
        assert "raw-sql-sentinel" not in str(error.value)

    asyncio.run(run())


def test_successful_empty_search_returns_empty_list(step62_state):
    async def run():
        identity = make_identity()
        await create_profile(step62_state, identity)
        async with SessionFactory() as session:
            candidates = await SemanticRetrievalService(
                session, provider=FakeProvider(identity)
            ).retrieve("query")
        assert candidates == []

    asyncio.run(run())


def test_vector_failure_does_not_become_empty_result(step62_state, monkeypatch):
    async def run():
        identity = make_identity()
        await create_profile(step62_state, identity)

        async def broken(*args, **kwargs):
            raise ApplicationError("VECTOR_QUERY_FAILED", "raw-vector-driver-detail", 500)

        monkeypatch.setattr(VectorStorageService, "nearest_vectors", broken)
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await SemanticRetrievalService(
                    session, provider=FakeProvider(identity)
                ).retrieve("query")
        assert error.value.code == "VECTOR_RETRIEVAL_FAILED"
        assert "raw-vector-driver-detail" not in str(error.value)

    asyncio.run(run())


def test_active_gates_exclude_non_active_versions_and_profile(step62_state):
    async def run():
        identity = make_identity()
        active_profile = await create_profile(step62_state, identity)
        inactive_identity = make_identity()
        inactive_profile = await create_profile(
            step62_state, inactive_identity, status="INACTIVE"
        )
        active_source = await step62_state.create_source()
        _, active_chunks = await step62_state.create_version(
            active_source, status="ACTIVE",
            profile_vectors={
                active_profile: [[1., 0., 0.], [0., 1., 0.]],
                inactive_profile: [[1., 0., 0.], [0., 1., 0.]],
            },
        )
        excluded = set()
        for status in ("PROCESSING", "FAILED", "SUPERSEDED"):
            source_id = await step62_state.create_source()
            _, ids = await step62_state.create_version(
                source_id, status=status,
                profile_vectors={active_profile: [[1., 0., 0.], [0., 1., 0.]]},
            )
            excluded.update(ids)
        async with SessionFactory() as session:
            candidates = await SemanticRetrievalService(
                session, provider=FakeProvider(identity)
            ).retrieve("query")
        assert [item.chunk_id for item in candidates] == active_chunks
        assert not excluded.intersection(item.chunk_id for item in candidates)

    asyncio.run(run())


def test_baseline_retrieval_returns_candidates_across_lessons(step62_state):
    async def run():
        identity = make_identity()
        profile_id = await create_profile(step62_state, identity)
        source_ids = [await step62_state.create_source() for _ in range(2)]
        expected = []
        for index, source_id in enumerate(source_ids):
            _, ids = await step62_state.create_version(
                source_id, status="ACTIVE",
                profile_vectors={profile_id: [[1., 0., 0.], [0., 1., 0.]]},
            )
            expected.extend(ids)
        async with SessionFactory() as session:
            candidates = await SemanticRetrievalService(
                session, provider=FakeProvider(identity)
            ).retrieve("query")
        assert {item.chunk_id for item in candidates} == set(expected)
        assert {item.source_lesson_id for item in candidates} == {
            step62_state.source_lessons[source_id] for source_id in source_ids
        }

    asyncio.run(run())


def test_profile_switch_during_embedding_fails_safely_without_cross_space_search(
    step62_state, monkeypatch
):
    async def run():
        p1_identity = make_identity()
        p2_identity = make_identity()
        p1 = await create_profile(step62_state, p1_identity)
        p2 = await create_profile(step62_state, p2_identity, status="INACTIVE")
        source_id = await step62_state.create_source()
        await step62_state.create_version(
            source_id, status="ACTIVE",
            profile_vectors={p1: [[1., 0., 0.], [0., 1., 0.]], p2: [[1., 0., 0.], [0., 1., 0.]]},
        )

        def switch_profile():
            dsn = get_settings().effective_database_url.replace(
                "postgresql+psycopg://", "postgresql://", 1
            )
            with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE embedding_profiles SET status = 'INACTIVE' WHERE id = %s", (p1,)
                )
                cursor.execute(
                    "UPDATE embedding_profiles SET status = 'ACTIVE' WHERE id = %s", (p2,)
                )

        async def must_not_search(*args, **kwargs):
            raise AssertionError("P1 vectors must never be searched in P2 space")

        from app.ai.vector_storage import repository as vector_repository
        monkeypatch.setattr(vector_repository, "nearest_vectors", must_not_search)
        async with SessionFactory() as session:
            provider = FakeProvider(p1_identity, on_embed=switch_profile)
            with pytest.raises(ApplicationError) as error:
                await SemanticRetrievalService(session, provider=provider).retrieve("query")
        assert error.value.code == "VECTOR_RETRIEVAL_FAILED"

    asyncio.run(run())


@pytest.mark.parametrize("distance,score", [(0.0, 1.0), (0.2, 0.8), (1.3, -0.3)])
def test_candidate_score_is_one_minus_distance_without_clamping(distance, score):
    metadata = CandidateMetadata(
        chunk_id=uuid4(), chunk_index=0, content="x", content_type="DOCUMENT_TEXT",
        knowledge_version_id=uuid4(), knowledge_source_id=uuid4(), source_type="DOCUMENT",
        source_document_id=uuid4(), source_lesson_id=None, chunk_lesson_id=None,
        document_title="title", lesson_title=None, hsk_level_number=None,
        page_number=None, section=None, locator_metadata=None,
    )
    candidate = SemanticRetrievalService._candidate(1, metadata, distance)
    assert candidate.distance == distance
    assert candidate.retrieval_score == pytest.approx(score)


def test_normal_retrieve_interface_has_filter_only_and_no_candidate_k_override():
    signature = inspect.signature(SemanticRetrievalService.retrieve)
    assert list(signature.parameters) == ["self", "query_text", "retrieval_filter"]
    assert signature.parameters["retrieval_filter"].kind is inspect.Parameter.KEYWORD_ONLY
    assert "candidate_k" not in signature.parameters
