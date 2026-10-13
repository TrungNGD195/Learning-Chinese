import asyncio

import pytest

from app.ai.vector_storage import repository
from app.ai.vector_storage.schemas import NearestVectorResult
from app.ai.vector_storage.service import VectorStorageService
from app.core.errors import ApplicationError
from app.database.models import KnowledgeVersion
from app.database.session import SessionFactory
from step62_test_support import step62_state


def test_nearest_vectors_uses_exact_cosine_and_filters_active_rows(step62_state):
    async def run():
        profile = await step62_state.create_profile(status="ACTIVE")
        inactive_profile = await step62_state.create_profile(status="INACTIVE")
        active_source = await step62_state.create_source()
        active_version, active_chunks = await step62_state.create_version(
            active_source, status="ACTIVE",
            profile_vectors={
                profile: [[1., 0., 0.], [0., 1., 0.]],
                inactive_profile: [[1., 0., 0.], [0., 0., 1.]],
            },
        )
        processing_source = await step62_state.create_source()
        await step62_state.create_version(
            processing_source, status="PROCESSING",
            profile_vectors={profile: [[1., 0., 0.], [0., 0., 1.]]},
        )
        failed_source = await step62_state.create_source()
        _, failed_chunks = await step62_state.create_version(
            failed_source, status="FAILED",
            profile_vectors={profile: [[1., 0., 0.], [0., 0., 1.]]},
        )
        superseded_source = await step62_state.create_source()
        _, superseded_chunks = await step62_state.create_version(
            superseded_source, status="SUPERSEDED",
            profile_vectors={profile: [[1., 0., 0.], [0., 0., 1.]]},
        )
        async with SessionFactory() as session:
            results = await repository.nearest_vectors(session, [1., 0., 0.], profile, 10)
            inactive_results = await repository.nearest_vectors(
                session, [1., 0., 0.], inactive_profile, 10
            )
            assert len(results) == 2
            assert all(isinstance(item, NearestVectorResult) for item in results)
            assert [item.chunk_id for item in results] == active_chunks
            assert inactive_results == []
            assert not set(failed_chunks + superseded_chunks).intersection(
                item.chunk_id for item in results
            )
            assert results[0].distance == 0.0
            assert results[1].distance == 1.0
            assert not hasattr(results[0], "content")
            assert (await session.get(KnowledgeVersion, active_version)).status == "ACTIVE"

    asyncio.run(run())


def test_nearest_vectors_breaks_equal_distance_ties_by_chunk_id(step62_state):
    async def run():
        profile = await step62_state.create_profile(status="ACTIVE")
        source = await step62_state.create_source()
        _, chunk_ids = await step62_state.create_version(
            source, status="ACTIVE",
            profile_vectors={profile: [[0., 1., 0.], [0., -1., 0.]]},
        )
        async with SessionFactory() as session:
            results = await repository.nearest_vectors(session, [1., 0., 0.], profile, 2)
        assert [row.chunk_id for row in results] == sorted(chunk_ids)
        assert [row.distance for row in results] == [1.0, 1.0]

    asyncio.run(run())


def test_nearest_service_requires_global_active_profile_and_matching_dimensions(step62_state):
    async def run():
        active = await step62_state.create_profile(status="ACTIVE")
        inactive = await step62_state.create_profile(status="INACTIVE")
        source = await step62_state.create_source()
        await step62_state.create_version(source, status="ACTIVE", profile_vectors={
            active: [[1., 0., 0.], [0., 1., 0.]],
            inactive: [[1., 0., 0.], [0., 1., 0.]],
        })
        async with SessionFactory() as session:
            service = VectorStorageService(session)
            results = await service.nearest_vectors([1., 0., 0.], active, 1)
            assert len(results) == 1 and results[0].distance == 0.0
            with pytest.raises(ApplicationError) as wrong_profile:
                await service.nearest_vectors([1., 0., 0.], inactive, 1)
            assert wrong_profile.value.code == "EMBEDDING_PROFILE_NOT_READY"
            with pytest.raises(ApplicationError) as wrong_dimensions:
                await service.nearest_vectors([1., 0.], active, 1)
            assert wrong_dimensions.value.code == "VECTOR_DIMENSION_MISMATCH"
            with pytest.raises(ValueError):
                await service.nearest_vectors([1., 0., 0.], active, 0)

    asyncio.run(run())


def test_active_profile_resolver_returns_frozen_missing_profile_error(step62_state):
    async def run():
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await VectorStorageService(session).resolve_active_profile()
        assert error.value.code == "ACTIVE_EMBEDDING_PROFILE_NOT_FOUND"

    asyncio.run(run())
