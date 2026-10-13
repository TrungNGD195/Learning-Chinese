import asyncio

import pytest
from sqlalchemy import select
from uuid import uuid4

from app.ai.vector_storage import repository
from app.ai.vector_storage.service import VectorStorageService
from app.core.errors import ApplicationError
from app.database.models import Embedding, EmbeddingProfile, KnowledgeSource, KnowledgeVersion
from app.database.session import SessionFactory
from step62_test_support import step62_state


def test_bootstrap_activates_the_entire_locked_source_snapshot_atomically(step62_state):
    async def run():
        target = await step62_state.create_profile()
        sources = [await step62_state.create_source(), await step62_state.create_source()]
        versions = []
        for source in sources:
            version, _ = await step62_state.create_version(
                source, profile_vectors={target: [[1., 0., 0.], [0., 1., 0.]]}
            )
            versions.append(version)
        async with SessionFactory() as session:
            await VectorStorageService(session).bootstrap_profile(target)
        async with SessionFactory() as session:
            profile = await session.get(EmbeddingProfile, target)
            activated = [await session.get(KnowledgeVersion, version) for version in versions]
        assert profile.status == "ACTIVE"
        assert all(version.status == "ACTIVE" for version in activated)
        assert len({version.activated_at for version in activated}) == 1

    asyncio.run(run())


def test_bootstrap_fails_all_or_nothing_when_one_source_is_unready(step62_state):
    async def run():
        target = await step62_state.create_profile()
        ready_source, incomplete_source = await step62_state.create_source(), await step62_state.create_source()
        ready, _ = await step62_state.create_version(
            ready_source, profile_vectors={target: [[1., 0., 0.], [0., 1., 0.]]}
        )
        incomplete, _ = await step62_state.create_version(
            incomplete_source, profile_vectors={target: [[1., 0., 0.]]}
        )
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await VectorStorageService(session).bootstrap_profile(target)
        assert error.value.code == "KNOWLEDGE_VERSION_NOT_VECTOR_READY"
        async with SessionFactory() as session:
            assert (await session.get(EmbeddingProfile, target)).status == "INACTIVE"
            assert (await session.get(KnowledgeVersion, ready)).status == "PROCESSING"
            assert (await session.get(KnowledgeVersion, incomplete)).status == "PROCESSING"

    asyncio.run(run())


def test_bootstrap_rejects_a_nonempty_source_cohort_without_processing_candidate(step62_state):
    async def run():
        target = await step62_state.create_profile()
        source = await step62_state.create_source()
        failed, _ = await step62_state.create_version(source, status="FAILED")
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await VectorStorageService(session).bootstrap_profile(target)
        assert error.value.code == "KNOWLEDGE_VERSION_NOT_PROCESSING"
        async with SessionFactory() as session:
            assert (await session.get(EmbeddingProfile, target)).status == "INACTIVE"
            assert (await session.get(KnowledgeVersion, failed)).status == "FAILED"

    asyncio.run(run())


def test_bootstrap_rejects_empty_cohort_and_active_version_candidates(step62_state):
    async def run():
        empty_target = await step62_state.create_profile()
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as empty_error:
                await VectorStorageService(session).bootstrap_profile(empty_target)
        assert empty_error.value.code == "ACTIVATION_CONFLICT"
        active_target = await step62_state.create_profile()
        active_source = await step62_state.create_source()
        active_version, _ = await step62_state.create_version(active_source, status="ACTIVE")
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as active_error:
                await VectorStorageService(session).bootstrap_profile(active_target)
        assert active_error.value.code == "ACTIVATION_CONFLICT"
        async with SessionFactory() as session:
            assert (await session.get(EmbeddingProfile, active_target)).status == "INACTIVE"
            assert (await session.get(KnowledgeVersion, active_version)).status == "ACTIVE"

    asyncio.run(run())


@pytest.mark.parametrize("status", ["FAILED", "SUPERSEDED"])
def test_normal_activation_rejects_ineligible_version_states(step62_state, status):
    async def run():
        profile = await step62_state.create_profile(status="ACTIVE")
        source = await step62_state.create_source()
        version, _ = await step62_state.create_version(source, status=status)
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await VectorStorageService(session).activate_version(version)
        assert error.value.code == "KNOWLEDGE_VERSION_NOT_PROCESSING"
        async with SessionFactory() as session:
            assert (await session.get(KnowledgeVersion, version)).status == status
            assert (await session.get(EmbeddingProfile, profile)).status == "ACTIVE"

    asyncio.run(run())


def test_normal_activation_supersedes_old_version_after_readiness_and_is_idempotent(step62_state):
    async def run():
        profile = await step62_state.create_profile(status="ACTIVE")
        source = await step62_state.create_source()
        old, _ = await step62_state.create_version(source, status="ACTIVE", version_number=1,
            profile_vectors={profile: [[1., 0., 0.], [0., 1., 0.]]})
        candidate, _ = await step62_state.create_version(source, status="PROCESSING", version_number=2,
            profile_vectors={profile: [[1., 0., 0.], [0., 1., 0.]]})
        async with SessionFactory() as session:
            await VectorStorageService(session).activate_version(candidate)
        async with SessionFactory() as session:
            old_after = await session.get(KnowledgeVersion, old)
            target_after = await session.get(KnowledgeVersion, candidate)
            activation_time = target_after.activated_at
        assert old_after.status == "SUPERSEDED"
        assert target_after.status == "ACTIVE"
        async with SessionFactory() as session:
            await VectorStorageService(session).activate_version(candidate)
        async with SessionFactory() as session:
            assert (await session.get(KnowledgeVersion, candidate)).activated_at == activation_time

    asyncio.run(run())


def test_unready_replacement_keeps_old_active_version_untouched(step62_state):
    async def run():
        profile = await step62_state.create_profile(status="ACTIVE")
        source = await step62_state.create_source()
        old, _ = await step62_state.create_version(source, status="ACTIVE", version_number=1,
            profile_vectors={profile: [[1., 0., 0.], [0., 1., 0.]]})
        candidate, _ = await step62_state.create_version(source, status="PROCESSING", version_number=2)
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await VectorStorageService(session).activate_version(candidate)
        assert error.value.code == "KNOWLEDGE_VERSION_NOT_VECTOR_READY"
        async with SessionFactory() as session:
            assert (await session.get(KnowledgeVersion, old)).status == "ACTIVE"
            assert (await session.get(KnowledgeVersion, candidate)).status == "PROCESSING"

    asyncio.run(run())


def test_profile_migration_rejects_incomplete_target_cohort_without_partial_change(step62_state):
    async def run():
        p1 = await step62_state.create_profile(status="ACTIVE")
        p2 = await step62_state.create_profile()
        source_a, source_b = await step62_state.create_source(), await step62_state.create_source()
        version_a, _ = await step62_state.create_version(source_a, status="ACTIVE", profile_vectors={
            p1: [[1., 0., 0.], [0., 1., 0.]], p2: [[1., 0., 0.], [0., 1., 0.]]})
        version_b, _ = await step62_state.create_version(source_b, status="ACTIVE", profile_vectors={
            p1: [[1., 0., 0.], [0., 1., 0.]], p2: [[1., 0., 0.]]})
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await VectorStorageService(session).migrate_active_profile(p2)
        assert error.value.code == "KNOWLEDGE_VERSION_NOT_VECTOR_READY"
        async with SessionFactory() as session:
            assert (await session.get(EmbeddingProfile, p1)).status == "ACTIVE"
            assert (await session.get(EmbeddingProfile, p2)).status == "INACTIVE"
            assert (await session.get(KnowledgeVersion, version_a)).status == "ACTIVE"
            assert (await session.get(KnowledgeVersion, version_b)).status == "ACTIVE"

    asyncio.run(run())


def test_profile_migration_changes_only_profiles_and_is_idempotent(step62_state):
    async def run():
        p1 = await step62_state.create_profile(status="ACTIVE")
        p2 = await step62_state.create_profile()
        source = await step62_state.create_source()
        version, _ = await step62_state.create_version(source, status="ACTIVE", profile_vectors={
            p1: [[1., 0., 0.], [0., 1., 0.]], p2: [[1., 0., 0.], [0., 1., 0.]]})
        async with SessionFactory() as session:
            before = (await session.get(KnowledgeVersion, version)).activated_at
        async with SessionFactory() as session:
            await VectorStorageService(session).migrate_active_profile(p2)
        async with SessionFactory() as session:
            assert (await session.get(EmbeddingProfile, p1)).status == "INACTIVE"
            assert (await session.get(EmbeddingProfile, p2)).status == "ACTIVE"
            current = await session.get(KnowledgeVersion, version)
            assert current.status == "ACTIVE"
            assert current.activated_at == before
        async with SessionFactory() as session:
            await VectorStorageService(session).migrate_active_profile(p2)

    asyncio.run(run())


def test_profile_migration_serializes_against_concurrent_version_activation(step62_state):
    async def run():
        p1 = await step62_state.create_profile(status="ACTIVE")
        p2 = await step62_state.create_profile()
        source = await step62_state.create_source()
        old, _ = await step62_state.create_version(source, status="ACTIVE", version_number=1, profile_vectors={
            p1: [[1., 0., 0.], [0., 1., 0.]], p2: [[1., 0., 0.], [0., 1., 0.]]})
        candidate, _ = await step62_state.create_version(source, status="PROCESSING", version_number=2, profile_vectors={
            p1: [[1., 0., 0.], [0., 1., 0.]], p2: [[1., 0., 0.], [0., 1., 0.]]})

        async def activate():
            async with SessionFactory() as session:
                await VectorStorageService(session).activate_version(candidate)

        async def migrate():
            async with SessionFactory() as session:
                await VectorStorageService(session).migrate_active_profile(p2)

        await asyncio.gather(activate(), migrate())
        async with SessionFactory() as session:
            profiles = list((await session.scalars(select(EmbeddingProfile).where(
                EmbeddingProfile.id.in_([p1, p2])
            ))).all())
            versions = [await session.get(KnowledgeVersion, version) for version in (old, candidate)]
        assert sum(profile.status == "ACTIVE" for profile in profiles) == 1
        assert next(profile for profile in profiles if profile.status == "ACTIVE").id == p2
        assert [version.status for version in versions] == ["SUPERSEDED", "ACTIVE"]

    asyncio.run(run())


def test_lifecycle_logs_structured_success_and_safe_failure(step62_state, caplog):
    async def run():
        caplog.set_level("INFO", logger="app.ai.vector_storage.service")
        profile = await step62_state.create_profile(status="ACTIVE")
        source = await step62_state.create_source()
        good, _ = await step62_state.create_version(source, profile_vectors={
            profile: [[1., 0., 0.], [0., 1., 0.]]
        })
        bad_source = await step62_state.create_source()
        bad, _ = await step62_state.create_version(bad_source)
        async with SessionFactory() as session:
            await VectorStorageService(session).activate_version(good)
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError):
                await VectorStorageService(session).activate_version(bad)
        success = next(record for record in caplog.records
                       if record.msg == "knowledge_version_activation_completed")
        assert success.embedding_profile_id == str(profile)
        assert success.knowledge_version_id == str(good)
        assert success.activation_action == "activate_version"
        assert success.distance_metric == "cosine"
        assert success.status == "SUCCEEDED"
        failure = next(record for record in caplog.records
                       if record.msg == "vector_storage_operation_failed")
        assert failure.embedding_profile_id == str(profile)
        assert failure.knowledge_version_id == str(bad)
        assert failure.error_code == "KNOWLEDGE_VERSION_NOT_VECTOR_READY"
        assert failure.status == "FAILED"

    asyncio.run(run())


def test_bootstrap_rejects_an_existing_active_profile(step62_state):
    async def run():
        active = await step62_state.create_profile(status="ACTIVE")
        target = await step62_state.create_profile()
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await VectorStorageService(session).bootstrap_profile(target)
        assert error.value.code == "ACTIVATION_CONFLICT"
        async with SessionFactory() as session:
            assert (await session.get(EmbeddingProfile, active)).status == "ACTIVE"
            assert (await session.get(EmbeddingProfile, target)).status == "INACTIVE"

    asyncio.run(run())


def test_bootstrap_rejects_otherwise_ready_active_knowledge_version(step62_state):
    async def run():
        target = await step62_state.create_profile()
        source = await step62_state.create_source()
        active, _ = await step62_state.create_version(
            source, status="ACTIVE", profile_vectors={target: [[1., 0., 0.], [0., 1., 0.]]}
        )
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await VectorStorageService(session).bootstrap_profile(target)
        assert error.value.code == "ACTIVATION_CONFLICT"
        async with SessionFactory() as session:
            assert (await session.get(EmbeddingProfile, target)).status == "INACTIVE"
            assert (await session.get(KnowledgeVersion, active)).status == "ACTIVE"

    asyncio.run(run())


def test_bootstrap_mutation_failure_rolls_back_profile_and_every_candidate(step62_state, monkeypatch):
    async def run():
        target = await step62_state.create_profile()
        candidates = []
        for _ in range(2):
            source = await step62_state.create_source()
            candidate, _ = await step62_state.create_version(
                source, profile_vectors={target: [[1., 0., 0.], [0., 1., 0.]]}
            )
            candidates.append(candidate)

        async with SessionFactory() as session:
            async def fail_mutation(*args, **kwargs):
                raise RuntimeError("injected bootstrap mutation failure")
            monkeypatch.setattr(session, "flush", fail_mutation)
            with pytest.raises(RuntimeError, match="injected bootstrap mutation failure"):
                await VectorStorageService(session).bootstrap_profile(target)

        async with SessionFactory() as session:
            assert (await session.get(EmbeddingProfile, target)).status == "INACTIVE"
            assert [
                (await session.get(KnowledgeVersion, candidate)).status for candidate in candidates
            ] == ["PROCESSING", "PROCESSING"]

    asyncio.run(run())


def test_bootstrap_uses_locked_source_snapshot_and_later_source_can_activate(
    step62_state, monkeypatch
):
    async def run():
        target = await step62_state.create_profile()
        snapshot_source = await step62_state.create_source()
        snapshot_candidate, _ = await step62_state.create_version(
            snapshot_source, profile_vectors={target: [[1., 0., 0.], [0., 1., 0.]]}
        )
        inserted = {}
        original_lock_sources = repository.lock_sources

        async def lock_then_insert_source(session):
            locked_snapshot = await original_lock_sources(session)
            assert [source.id for source in locked_snapshot] == [snapshot_source]
            later_source = await step62_state.create_source()
            later_candidate, later_chunks = await step62_state.create_version(later_source)
            inserted.update(source=later_source, version=later_candidate, chunks=later_chunks)
            return locked_snapshot

        monkeypatch.setattr(repository, "lock_sources", lock_then_insert_source)
        async with SessionFactory() as session:
            await VectorStorageService(session).bootstrap_profile(target)
        monkeypatch.setattr(repository, "lock_sources", original_lock_sources)

        async with SessionFactory() as session:
            assert (await session.get(KnowledgeVersion, snapshot_candidate)).status == "ACTIVE"
            assert (await session.get(KnowledgeVersion, inserted["version"])).status == "PROCESSING"
            later_source_row = await session.get(KnowledgeSource, inserted["source"])
            assert later_source_row is not None
        async with SessionFactory.begin() as session:
            session.add_all([
                Embedding(
                    chunk_id=chunk_id, embedding_profile_id=target,
                    vector=vector,
                )
                for chunk_id, vector in zip(
                    inserted["chunks"], [[1., 0., 0.], [0., 1., 0.]], strict=True
                )
            ])
        async with SessionFactory() as session:
            await VectorStorageService(session).activate_version(inserted["version"])
        async with SessionFactory() as session:
            assert (await session.get(KnowledgeVersion, inserted["version"])).status == "ACTIVE"

    asyncio.run(run())


def test_normal_activation_requires_a_global_active_profile(step62_state):
    async def run():
        profile = await step62_state.create_profile()
        source = await step62_state.create_source()
        version, _ = await step62_state.create_version(
            source, profile_vectors={profile: [[1., 0., 0.], [0., 1., 0.]]}
        )
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await VectorStorageService(session).activate_version(version)
        assert error.value.code == "ACTIVE_EMBEDDING_PROFILE_NOT_FOUND"
        async with SessionFactory() as session:
            assert (await session.get(KnowledgeVersion, version)).status == "PROCESSING"

    asyncio.run(run())


def test_normal_activation_rejects_vectors_only_under_another_inactive_profile(step62_state):
    async def run():
        active = await step62_state.create_profile(status="ACTIVE")
        inactive = await step62_state.create_profile()
        source = await step62_state.create_source()
        candidate, _ = await step62_state.create_version(
            source, profile_vectors={inactive: [[1., 0., 0.], [0., 1., 0.]]}
        )
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await VectorStorageService(session).activate_version(candidate)
        assert error.value.code == "KNOWLEDGE_VERSION_NOT_VECTOR_READY"
        async with SessionFactory() as session:
            assert (await session.get(EmbeddingProfile, active)).status == "ACTIVE"
            assert (await session.get(KnowledgeVersion, candidate)).status == "PROCESSING"

    asyncio.run(run())


def test_normal_activation_rejects_active_but_incoherent_target(step62_state):
    async def run():
        profile = await step62_state.create_profile(status="ACTIVE")
        source = await step62_state.create_source()
        target, _ = await step62_state.create_version(source, status="ACTIVE")
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await VectorStorageService(session).activate_version(target)
        assert error.value.code == "ACTIVATION_CONFLICT"
        async with SessionFactory() as session:
            assert (await session.get(EmbeddingProfile, profile)).status == "ACTIVE"
            assert (await session.get(KnowledgeVersion, target)).status == "ACTIVE"

    asyncio.run(run())


def test_normal_activation_rejects_a_missing_target_version(step62_state):
    async def run():
        await step62_state.create_profile(status="ACTIVE")
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await VectorStorageService(session).activate_version(uuid4())
        assert error.value.code == "KNOWLEDGE_VERSION_NOT_PROCESSING"

    asyncio.run(run())


def test_normal_activation_mutation_failure_keeps_old_and_candidate_states(step62_state, monkeypatch):
    async def run():
        profile = await step62_state.create_profile(status="ACTIVE")
        source = await step62_state.create_source()
        old, _ = await step62_state.create_version(
            source, status="ACTIVE", version_number=1,
            profile_vectors={profile: [[1., 0., 0.], [0., 1., 0.]]},
        )
        candidate, _ = await step62_state.create_version(
            source, status="PROCESSING", version_number=2,
            profile_vectors={profile: [[1., 0., 0.], [0., 1., 0.]]},
        )

        async with SessionFactory() as session:
            original_flush = session.flush
            calls = 0

            async def fail_final_mutation(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise RuntimeError("injected activation mutation failure")
                return await original_flush(*args, **kwargs)

            monkeypatch.setattr(session, "flush", fail_final_mutation)
            with pytest.raises(RuntimeError, match="injected activation mutation failure"):
                await VectorStorageService(session).activate_version(candidate)

        async with SessionFactory() as session:
            assert (await session.get(KnowledgeVersion, old)).status == "ACTIVE"
            assert (await session.get(KnowledgeVersion, candidate)).status == "PROCESSING"

    asyncio.run(run())


def test_two_concurrent_activation_attempts_have_no_availability_gap(step62_state, monkeypatch):
    async def run():
        profile = await step62_state.create_profile(status="ACTIVE")
        source = await step62_state.create_source()
        old, _ = await step62_state.create_version(
            source, status="ACTIVE", version_number=1,
            profile_vectors={profile: [[1., 0., 0.], [0., 1., 0.]]},
        )
        candidate, _ = await step62_state.create_version(
            source, status="PROCESSING", version_number=2,
            profile_vectors={profile: [[1., 0., 0.], [0., 1., 0.]]},
        )
        first_flushed_old_state = asyncio.Event()
        release_first = asyncio.Event()
        second_started = asyncio.Event()

        async def first_attempt():
            async with SessionFactory() as session:
                original_flush = session.flush
                paused = False

                async def pause_after_supersede_flush(*args, **kwargs):
                    nonlocal paused
                    result = await original_flush(*args, **kwargs)
                    if not paused:
                        paused = True
                        first_flushed_old_state.set()
                        await release_first.wait()
                    return result

                monkeypatch.setattr(session, "flush", pause_after_supersede_flush)
                await VectorStorageService(session).activate_version(candidate)

        async def second_attempt():
            second_started.set()
            async with SessionFactory() as session:
                await VectorStorageService(session).activate_version(candidate)

        first = asyncio.create_task(first_attempt())
        await first_flushed_old_state.wait()
        async with SessionFactory() as observer:
            assert (await observer.get(KnowledgeVersion, old)).status == "ACTIVE"
            assert (await observer.get(KnowledgeVersion, candidate)).status == "PROCESSING"
        second = asyncio.create_task(second_attempt())
        await second_started.wait()
        await asyncio.sleep(0.05)
        release_first.set()
        await asyncio.gather(first, second)
        async with SessionFactory() as session:
            rows = [await session.get(KnowledgeVersion, item) for item in (old, candidate)]
        assert [row.status for row in rows] == ["SUPERSEDED", "ACTIVE"]
        assert sum(row.status == "ACTIVE" for row in rows) == 1

    asyncio.run(run())


def test_profile_migration_requires_current_active_profile(step62_state):
    async def run():
        target = await step62_state.create_profile()
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await VectorStorageService(session).migrate_active_profile(target)
        assert error.value.code == "ACTIVE_EMBEDDING_PROFILE_NOT_FOUND"

    asyncio.run(run())


def test_profile_migration_rejects_incomplete_target_profile(step62_state):
    async def run():
        await step62_state.create_profile(status="ACTIVE")
        target = uuid4()
        async with SessionFactory.begin() as session:
            session.add(EmbeddingProfile(
                id=target, provider="LOCAL", provider_version=None,
                model_name=f"legacy-{target}", model_version=None, dimensions=3,
                embedding_input_version=None, normalize_embeddings=None, status="INACTIVE",
            ))
        step62_state.profile_ids.add(target)
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await VectorStorageService(session).migrate_active_profile(target)
        assert error.value.code == "EMBEDDING_PROFILE_NOT_READY"

    asyncio.run(run())


def test_profile_migration_mutation_failure_rolls_back_profile_switch(step62_state, monkeypatch):
    async def run():
        p1 = await step62_state.create_profile(status="ACTIVE")
        p2 = await step62_state.create_profile()
        source = await step62_state.create_source()
        version, _ = await step62_state.create_version(source, status="ACTIVE", profile_vectors={
            p1: [[1., 0., 0.], [0., 1., 0.]], p2: [[1., 0., 0.], [0., 1., 0.]]
        })

        async with SessionFactory() as session:
            original_flush = session.flush
            calls = 0

            async def fail_second_profile_write(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise RuntimeError("injected profile-switch mutation failure")
                return await original_flush(*args, **kwargs)

            monkeypatch.setattr(session, "flush", fail_second_profile_write)
            with pytest.raises(RuntimeError, match="injected profile-switch mutation failure"):
                await VectorStorageService(session).migrate_active_profile(p2)

        async with SessionFactory() as session:
            assert (await session.get(EmbeddingProfile, p1)).status == "ACTIVE"
            assert (await session.get(EmbeddingProfile, p2)).status == "INACTIVE"
            assert (await session.get(KnowledgeVersion, version)).status == "ACTIVE"

    asyncio.run(run())


def test_concurrent_profile_migrations_serialize_under_sorted_profile_locks(
    step62_state, monkeypatch
):
    async def run():
        p1 = await step62_state.create_profile(status="ACTIVE")
        p2 = await step62_state.create_profile()
        p3 = await step62_state.create_profile()
        source = await step62_state.create_source()
        version, _ = await step62_state.create_version(source, status="ACTIVE", profile_vectors={
            p1: [[1., 0., 0.], [0., 1., 0.]],
            p2: [[1., 0., 0.], [0., 1., 0.]],
            p3: [[1., 0., 0.], [0., 1., 0.]],
        })
        original_lock = repository.lock_all_profiles
        observed_lock_orders = []

        async def record_sorted_profile_locks(session):
            profiles = await original_lock(session)
            observed_lock_orders.append([profile.id for profile in profiles])
            return profiles

        monkeypatch.setattr(repository, "lock_all_profiles", record_sorted_profile_locks)

        async def migrate(target):
            async with SessionFactory() as session:
                await VectorStorageService(session).migrate_active_profile(target)

        await asyncio.gather(migrate(p2), migrate(p3))
        assert len(observed_lock_orders) == 2
        assert all(order == sorted(order) for order in observed_lock_orders)
        async with SessionFactory() as session:
            profiles = list((await session.scalars(select(EmbeddingProfile).where(
                EmbeddingProfile.id.in_([p1, p2, p3])
            ))).all())
            final_version = await session.get(KnowledgeVersion, version)
        active = [profile for profile in profiles if profile.status == "ACTIVE"]
        assert len(active) == 1
        assert active[0].id in {p2, p3}
        assert final_version.status == "ACTIVE"

    asyncio.run(run())
