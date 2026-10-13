import asyncio
from uuid import uuid4
from types import SimpleNamespace

import pytest

from app.ai.vector_storage import repository
from app.ai.vector_storage.service import VectorStorageService
from app.core.errors import ApplicationError
from app.database.models import EmbeddingProfile, KnowledgeVersion
from app.database.session import SessionFactory
from step62_test_support import step62_state


def test_pair_readiness_is_version_status_agnostic_and_runs_persisted_cosine_probe(step62_state):
    async def run():
        profile = await step62_state.create_profile()
        results_to_check = []
        for status in ("PROCESSING", "ACTIVE"):
            source = await step62_state.create_source()
            version, _ = await step62_state.create_version(
                source, status=status,
                profile_vectors={profile: [[1., 0., 0.], [0., 1., 0.]]},
            )
            results_to_check.append(version)
        async with SessionFactory() as session:
            service = VectorStorageService(session)
            results = [await service.check_vector_pair_readiness(version, profile)
                       for version in results_to_check]
        for result in results:
            assert result.ready
            assert result.required_chunk_count == result.embedding_count == 2
            assert result.expected_dimensions == 3
            assert result.invalid_dimension_count == 0
            assert result.failure_code is None
            assert result.probe_distance is not None and abs(result.probe_distance) <= 1e-6

    asyncio.run(run())


def test_readiness_reports_incomplete_embeddings_and_dimension_mismatch(step62_state):
    async def run():
        profile = await step62_state.create_profile(dimensions=3)
        source = await step62_state.create_source()
        incomplete, _ = await step62_state.create_version(
            source, profile_vectors={profile: [[1., 0., 0.]]}
        )
        wrong_profile = await step62_state.create_profile(dimensions=2)
        mismatch_source = await step62_state.create_source()
        mismatch, _ = await step62_state.create_version(
            mismatch_source, profile_vectors={wrong_profile: [[1., 0., 0.], [0., 1., 0.]]}
        )
        async with SessionFactory() as session:
            service = VectorStorageService(session)
            incomplete_result = await service.check_vector_pair_readiness(incomplete, profile)
            mismatch_result = await service.check_vector_pair_readiness(mismatch, wrong_profile)
        assert incomplete_result.failure_code == "KNOWLEDGE_VERSION_NOT_VECTOR_READY"
        assert incomplete_result.required_chunk_count == 2 and incomplete_result.embedding_count == 1
        assert mismatch_result.failure_code == "VECTOR_DIMENSION_MISMATCH"
        assert mismatch_result.invalid_dimension_count == 2

    asyncio.run(run())


def test_readiness_rejects_missing_or_incomplete_profile(step62_state):
    async def run():
        source = await step62_state.create_source()
        version, _ = await step62_state.create_version(source)
        incomplete_id = uuid4()
        async with SessionFactory.begin() as session:
            session.add(EmbeddingProfile(
                id=incomplete_id, provider="LOCAL", provider_version=None,
                model_name=f"legacy-{incomplete_id}", model_version=None, dimensions=3,
                embedding_input_version=None, normalize_embeddings=None, status="INACTIVE",
            ))
        step62_state.profile_ids.add(incomplete_id)
        async with SessionFactory() as session:
            service = VectorStorageService(session)
            missing = await service.check_vector_pair_readiness(version, uuid4())
            incomplete = await service.check_vector_pair_readiness(version, incomplete_id)
        assert missing.failure_code == "EMBEDDING_PROFILE_NOT_READY"
        assert incomplete.failure_code == "EMBEDDING_PROFILE_NOT_READY"

    asyncio.run(run())


def test_readiness_requires_at_least_one_required_chunk(step62_state):
    async def run():
        profile = await step62_state.create_profile()
        source = await step62_state.create_source()
        version, _ = await step62_state.create_version(source, vectors=[])
        async with SessionFactory() as session:
            result = await VectorStorageService(session).check_vector_pair_readiness(version, profile)
        assert result.ready is False
        assert result.required_chunk_count == 0
        assert result.failure_code == "KNOWLEDGE_VERSION_NOT_VECTOR_READY"

    asyncio.run(run())


def test_readiness_normalizes_pgvector_errors_without_exposing_driver_text(step62_state, monkeypatch, caplog):
    async def run():
        profile = await step62_state.create_profile()
        source = await step62_state.create_source()
        version, _ = await step62_state.create_version(
            source, profile_vectors={profile: [[1., 0., 0.], [0., 1., 0.]]}
        )
        async def fail(*args, **kwargs):
            raise RuntimeError("SECRET_SQL_DRIVER_DETAIL vector=[777.125, -888.25, 999.5]")
        monkeypatch.setattr(repository, "run_candidate_probe", fail)
        caplog.set_level("ERROR", logger="app.ai.vector_storage.service")
        async with SessionFactory() as session:
            result = await VectorStorageService(session).check_vector_pair_readiness(version, profile)
        assert result.ready is False
        assert result.failure_code == "VECTOR_QUERY_FAILED"
        records = [record for record in caplog.records
                   if record.msg == "vector_pair_readiness_query_failed"]
        assert len(records) == 1
        record = records[0]
        payload = "[777.125, -888.25, 999.5]"
        message = getattr(record, "message", record.getMessage())
        assert "SECRET_SQL_DRIVER_DETAIL" not in message
        assert "SECRET_SQL_DRIVER_DETAIL" not in record.getMessage()
        assert record.exc_text is None
        assert record.exc_info is None
        assert "SECRET_SQL_DRIVER_DETAIL" not in caplog.text
        assert payload not in caplog.text
        assert record.error_code == "VECTOR_QUERY_FAILED"

    asyncio.run(run())


@pytest.mark.parametrize("probe_kind", ["missing", "non_finite", "nonzero_self_distance"])
def test_readiness_rejects_invalid_technical_probe_without_mutating_lifecycle(
    step62_state, monkeypatch, probe_kind
):
    async def run():
        profile = await step62_state.create_profile(status="INACTIVE")
        source = await step62_state.create_source()
        version, _ = await step62_state.create_version(
            source, status="SUPERSEDED",
            profile_vectors={profile: [[1., 0., 0.], [0., 1., 0.]]},
        )

        async def probe(*args, **kwargs):
            if probe_kind == "missing":
                return None
            distance = float("inf") if probe_kind == "non_finite" else 1.000001e-6
            return SimpleNamespace(
                embedding_profile_id=profile,
                knowledge_version_id=version,
                vector=[1., 0., 0.],
                distance=distance,
            )

        monkeypatch.setattr(repository, "run_candidate_probe", probe)

        def unexpected_provider_call(*args, **kwargs):
            raise AssertionError("Vector readiness must not invoke an embedding provider or model.")

        import app.ai.embeddings.provider as embedding_provider
        from app.ai.embeddings.sentence_transformer_provider import SentenceTransformerEmbeddingProvider
        monkeypatch.setattr(embedding_provider, "get_embedding_provider", unexpected_provider_call)
        monkeypatch.setattr(SentenceTransformerEmbeddingProvider, "_load_model", unexpected_provider_call)

        async with SessionFactory() as session:
            result = await VectorStorageService(session).check_vector_pair_readiness(version, profile)
        assert result.ready is False
        assert result.failure_code == "KNOWLEDGE_VERSION_NOT_VECTOR_READY"
        async with SessionFactory() as session:
            stored_version = await session.get(KnowledgeVersion, version)
            stored_profile = await session.get(EmbeddingProfile, profile)
        assert stored_version.status == "SUPERSEDED"
        assert stored_profile.status == "INACTIVE"

    asyncio.run(run())


def test_active_profile_resolver_defends_against_multiple_active_rows():
    profiles = [SimpleNamespace(status="ACTIVE"), SimpleNamespace(status="ACTIVE")]
    with pytest.raises(ApplicationError) as error:
        VectorStorageService._active_profile(profiles)
    assert error.value.code == "MULTIPLE_ACTIVE_EMBEDDING_PROFILES"
