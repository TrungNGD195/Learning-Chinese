import asyncio
from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.ai.embeddings.schemas import EmbeddingProviderIdentity
from app.ai.embeddings.service import EmbeddingService
from app.ai.embeddings.schemas import EmbeddingProfileIdentity
from app.ai.embeddings import repository as embedding_repository
from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.database.models import Chunk, Document, Embedding, EmbeddingProfile, KnowledgeVersion, TransformationRun
from app.database.session import SessionFactory
from app.ingestion.chunking.strategy import content_hash as chunk_content_hash


def _prepare(context):
    result = asyncio.run(context["prepare_approved"]())
    async def set_processing():
        async with SessionFactory.begin() as session:
            version = await session.get(KnowledgeVersion, result["knowledge_version_id"])
            version.status = "PROCESSING"
    asyncio.run(set_processing())
    return result


class _FakeProvider:
    identity = EmbeddingProviderIdentity(
        "LOCAL", "sentence-transformers/6.1.0", "BAAI/bge-m3",
        "5617a9f61b028005a4858fdac845db406aefb181", 1024, "v1", True,
    )
    device = "cpu"

    def __init__(self, session=None, *, fail_on_call=None):
        self.session = session
        self.calls = []
        self.fail_on_call = fail_on_call

    async def embed_documents(self, texts, *, batch_size):
        assert self.session is None or not self.session.in_transaction()
        self.calls.append((texts, batch_size))
        if self.fail_on_call == len(self.calls):
            raise ApplicationError("EMBEDDING_PROVIDER_FAILED", "safe", status_code=500)
        return [[1.0] + [0.0] * 1023 for _ in texts]

    async def embed_query(self, text):
        return [1.0] + [0.0] * 1023


def test_build_persists_complete_embeddings_and_keeps_lifecycle(step57_document):
    result = _prepare(step57_document)
    version_id = result["knowledge_version_id"]

    async def run():
        async with SessionFactory() as session:
            provider = _FakeProvider(session)
            built = await EmbeddingService(session, provider=provider).embed_processing_version(version_id)
            assert built.required_count > 0
            assert built.embedded_count == built.required_count
            assert built.embedded_this_run == built.required_count
            assert built.knowledge_version_status == "PROCESSING"
            assert provider.calls
        async with SessionFactory() as session:
            version = await session.get(KnowledgeVersion, version_id)
            assert version.status == "PROCESSING"
            profiles = list((await session.scalars(select(EmbeddingProfile))).all())
            profile = next(profile for profile in profiles if profile.model_name == "BAAI/bge-m3")
            assert profile.status == "INACTIVE"
            embeddings = (await session.scalars(select(Embedding).join(Chunk).where(Chunk.knowledge_version_id == version_id))).all()
            assert len(embeddings) == built.required_count
            embedding_ids = [row.id for row in embeddings]
            await session.rollback()
            async with session.begin():
                await session.execute(delete(Embedding).where(Embedding.id.in_(embedding_ids)))
    asyncio.run(run())


def test_build_failure_marks_failed_without_deleting_prior_batches(step57_document):
    result = _prepare(step57_document)
    version_id = result["knowledge_version_id"]

    async def run():
        async with SessionFactory.begin() as session:
            originals = (await session.scalars(select(Chunk).where(Chunk.knowledge_version_id == version_id).order_by(Chunk.chunk_index))).all()
            original = originals[0]
            content = original.content + " second test chunk"
            session.add(Chunk(
                knowledge_version_id=version_id, content=content, content_type=original.content_type,
                chunk_index=len(originals), token_count=None, page_number=original.page_number,
                section=original.section, lesson_id=original.lesson_id,
                metadata_json=original.metadata_json, content_hash=chunk_content_hash(content, original.content_type),
            ))
        async with SessionFactory() as session:
            provider = _FakeProvider(fail_on_call=2)
            with pytest.raises(ApplicationError) as error:
                await EmbeddingService(session, provider=provider, settings=get_settings().model_copy(update={"embedding_batch_size": 1})).embed_processing_version(version_id)
            assert error.value.code == "EMBEDDING_PROVIDER_FAILED"
        async with SessionFactory() as session:
            version = await session.get(KnowledgeVersion, version_id)
            assert version.status == "FAILED"
            count = await session.scalar(select(Embedding.id).join(Chunk).where(Chunk.knowledge_version_id == version_id).limit(1))
            assert count is not None
            await session.rollback()
            async with session.begin():
                ids = select(Chunk.id).where(Chunk.knowledge_version_id == version_id)
                await session.execute(delete(Embedding).where(Embedding.chunk_id.in_(ids)))
                target = await session.get(KnowledgeVersion, version_id)
                target.status = "PROCESSING"
    asyncio.run(run())


def test_two_services_converge_on_chunk_profile_uniqueness(step57_document):
    result = _prepare(step57_document)
    version_id = result["knowledge_version_id"]

    async def run():
        async def one():
            async with SessionFactory() as session:
                return await EmbeddingService(session, provider=_FakeProvider()).embed_processing_version(version_id)
        built = await asyncio.gather(one(), one())
        assert all(item.embedded_count == item.required_count for item in built)
        async with SessionFactory() as session:
            rows = (await session.scalars(select(Embedding).join(Chunk).where(Chunk.knowledge_version_id == version_id))).all()
            assert len(rows) == built[0].required_count
            embedding_ids = [row.id for row in rows]
            await session.rollback()
            async with session.begin():
                await session.execute(delete(Embedding).where(Embedding.id.in_(embedding_ids)))
    asyncio.run(run())


def test_zero_chunk_processing_version_fails_with_d2_contract(step57_document):
    result = _prepare(step57_document)
    version_id = result["knowledge_version_id"]

    async def run():
        async with SessionFactory.begin() as session:
            await session.execute(delete(Chunk).where(Chunk.knowledge_version_id == version_id))
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await EmbeddingService(session, provider=_FakeProvider()).embed_processing_version(version_id)
            assert error.value.code == "EMBEDDING_BUILD_FAILED"
            assert error.value.details == {"reason": "ZERO_REQUIRED_CHUNKS"}
        async with SessionFactory() as session:
            version = await session.get(KnowledgeVersion, version_id)
            assert version.status == "FAILED"
    asyncio.run(run())


class _Planner:
    def __init__(self, action=None, reason=None): self.calls = []; self.action = action; self.reason = reason
    async def plan_source(self, source_type, source_id, **flags):
        from types import SimpleNamespace
        from app.ingestion.reprocessing import ReprocessingAction, ReprocessingReason
        self.calls.append((source_type, source_id, flags))
        return SimpleNamespace(action=self.action or ReprocessingAction.FROM_EMBED,
                               reason=self.reason or ReprocessingReason.EMBEDDING_PROFILE_CHANGED)


async def _insert_profile_evidence(
    session, version_id, *, input_version="v1", provider="LOCAL",
    provider_version="sentence-transformers/6.1.0", model_name="BAAI/bge-m3",
    model_version="5617a9f61b028005a4858fdac845db406aefb181", dimensions=1024,
    normalize_embeddings=True,
):
    if input_version != "v1":
        input_version = f"{input_version}-{uuid4()}"
    if model_name != "BAAI/bge-m3":
        model_name = f"{model_name}-{uuid4()}"
    profile = await embedding_repository.get_or_create_embedding_profile(session, EmbeddingProfileIdentity(
        provider=provider, provider_version=provider_version, model_name=model_name,
        model_version=model_version, dimensions=dimensions, embedding_input_version=input_version,
        normalize_embeddings=normalize_embeddings,
    ))
    chunk = await session.scalar(select(Chunk).where(
        Chunk.knowledge_version_id == version_id
    ).order_by(Chunk.chunk_index))
    session.add(Embedding(chunk_id=chunk.id, embedding_profile_id=profile.id, vector=[1.0] + [0.0] * 1023))
    return profile


def test_profile_repository_identity_reuse_and_concurrent_creation():
    identity = EmbeddingProfileIdentity("LOCAL", "sentence-transformers/6.1.0", f"profile-test-{uuid4()}",
        "5617a9f61b028005a4858fdac845db406aefb181", 1024, "v1", True)
    owned_profile_ids = set()
    async def run():
        async def create():
            async with SessionFactory.begin() as session:
                profile = await embedding_repository.get_or_create_embedding_profile(session, identity)
                owned_profile_ids.add(profile.id)
                return profile.id, profile.status
        try:
            first, second = await asyncio.gather(create(), create())
            assert first[0] == second[0]
            assert first[1] == second[1] == "INACTIVE"
            async with SessionFactory.begin() as session:
                profile = await embedding_repository.get_embedding_profile_by_identity(session, identity)
                assert profile is not None
                profile.status = "ACTIVE"
            async with SessionFactory.begin() as session:
                reused = await embedding_repository.get_or_create_embedding_profile(session, identity)
                assert reused.id == first[0] and reused.status == "ACTIVE"
                other_input = await embedding_repository.get_or_create_embedding_profile(
                    session, replace(identity, embedding_input_version="v2")
                )
                other_norm = await embedding_repository.get_or_create_embedding_profile(
                    session, replace(identity, normalize_embeddings=False)
                )
                owned_profile_ids.update((other_input.id, other_norm.id))
                assert other_input.id != reused.id and other_norm.id != reused.id
                legacy = EmbeddingProfile(provider="LOCAL", provider_version=None, model_name=f"legacy-{uuid4()}",
                    model_version=None, dimensions=384, embedding_input_version=None,
                    normalize_embeddings=None, status="INACTIVE")
                session.add(legacy)
                await session.flush()
                owned_profile_ids.add(legacy.id)
                incomplete_target = replace(identity, model_name=legacy.model_name, dimensions=384)
                assert await embedding_repository.get_embedding_profile_by_identity(session, incomplete_target) is None
                assert await session.get(EmbeddingProfile, legacy.id) is not None
        finally:
            if owned_profile_ids:
                async with SessionFactory.begin() as session:
                    await session.execute(delete(Embedding).where(
                        Embedding.embedding_profile_id.in_(owned_profile_ids)
                    ))
                    await session.execute(delete(EmbeddingProfile).where(
                        EmbeddingProfile.id.in_(owned_profile_ids)
                    ))
                async with SessionFactory() as session:
                    remaining = await session.scalar(select(EmbeddingProfile.id).where(
                        EmbeddingProfile.id.in_(owned_profile_ids)
                    ).limit(1))
                    assert remaining is None, "test-owned embedding profiles leaked after cleanup"
    asyncio.run(run())


@pytest.mark.parametrize("vectors", [
    [], [[1.0, 0.0]], [[float("nan")] + [0.0] * 1023],
    [[float("inf")] + [0.0] * 1023], [[0.5] + [0.0] * 1023],
])
def test_output_validation_rejects_count_dimension_nonfinite_and_nonunit_vectors(vectors):
    with pytest.raises(ApplicationError) as error:
        EmbeddingService._validate_vectors(vectors, 1, 1024)
    assert error.value.code == "INVALID_EMBEDDING_OUTPUT"


def test_failed_retry_without_profile_evidence_hands_off_conservatively(step57_document):
    result = _prepare(step57_document)
    version_id = result["knowledge_version_id"]
    async def run():
        async with SessionFactory.begin() as session:
            version = await session.get(KnowledgeVersion, version_id)
            version.status = "FAILED"
        planner = _Planner()
        provider = _FakeProvider()
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await EmbeddingService(session, provider=provider).retry_failed_version(version_id, reprocessing_planner=planner)
            assert error.value.code == "EMBEDDING_FINGERPRINT_MISMATCH"
            assert error.value.details == {
                "reprocessing_action": "FROM_EMBED", "reprocessing_reason": "EMBEDDING_PROFILE_CHANGED",
            }
        assert planner.calls[0][2] == {"embedding_profile_changed": True, "embedding_input_changed": False}
        assert provider.calls == []
        async with SessionFactory() as session:
            assert (await session.get(KnowledgeVersion, version_id)).status == "FAILED"
    asyncio.run(run())


@pytest.mark.parametrize(
    ("profile_kwargs", "expected_flags", "expected_reason"),
    [
        ({"input_version": "previous-input"}, {"embedding_profile_changed": False, "embedding_input_changed": True}, "EMBEDDING_INPUT_CHANGED"),
        ({"model_name": "previous-model"}, {"embedding_profile_changed": True, "embedding_input_changed": False}, "EMBEDDING_PROFILE_CHANGED"),
    ],
    ids=["input-version-only", "known-profile-mismatch"],
)
def test_failed_retry_classifies_current_lineage_profile_evidence(
    step57_document, profile_kwargs, expected_flags, expected_reason,
):
    result = _prepare(step57_document)
    version_id = result["knowledge_version_id"]

    async def run():
        async with SessionFactory.begin() as session:
            version = await session.get(KnowledgeVersion, version_id)
            version.status = "FAILED"
            profile = await _insert_profile_evidence(session, version_id, **profile_kwargs)
        from app.ingestion.reprocessing import ReprocessingAction, ReprocessingReason
        planner = _Planner(ReprocessingAction.FROM_EMBED, ReprocessingReason(expected_reason))
        provider = _FakeProvider()
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await EmbeddingService(session, provider=provider).retry_failed_version(
                    version_id, reprocessing_planner=planner)
            assert error.value.code == "EMBEDDING_FINGERPRINT_MISMATCH"
            assert error.value.details == {
                "reprocessing_action": "FROM_EMBED", "reprocessing_reason": expected_reason,
            }
        assert planner.calls[0][2] == expected_flags
        assert provider.calls == []
        async with SessionFactory.begin() as session:
            assert (await session.get(KnowledgeVersion, version_id)).status == "FAILED"
            await session.execute(delete(Embedding).where(Embedding.embedding_profile_id == profile.id))
    asyncio.run(run())


def test_upstream_mismatch_precedes_empty_profile_evidence_and_returns_planner_reason(step57_document):
    result = _prepare(step57_document)
    version_id = result["knowledge_version_id"]

    async def run():
        async with SessionFactory.begin() as session:
            version = await session.get(KnowledgeVersion, version_id)
            version.status = "FAILED"
            from app.database.models import Document
            document = await session.get(Document, step57_document["source_id"])
            document.content_hash = "0" * 64
        from app.ingestion.reprocessing import ReprocessingAction, ReprocessingReason
        planner = _Planner(ReprocessingAction.FROM_PARSE, ReprocessingReason.SOURCE_CHANGED)
        provider = _FakeProvider()
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await EmbeddingService(session, provider=provider).retry_failed_version(
                    version_id, reprocessing_planner=planner)
            assert error.value.code == "EMBEDDING_FINGERPRINT_MISMATCH"
            assert error.value.details == {
                "reprocessing_action": "FROM_PARSE", "reprocessing_reason": "SOURCE_CHANGED",
            }
        assert planner.calls[0][2] == {"embedding_profile_changed": False, "embedding_input_changed": False}
        assert provider.calls == []
        async with SessionFactory.begin() as session:
            assert (await session.get(KnowledgeVersion, version_id)).status == "FAILED"
    asyncio.run(run())


def test_upstream_mismatch_precedes_stale_profile_evidence(step57_document):
    result = _prepare(step57_document)
    version_id = result["knowledge_version_id"]

    async def run():
        async with SessionFactory.begin() as session:
            version = await session.get(KnowledgeVersion, version_id)
            version.status = "FAILED"
            profile = await _insert_profile_evidence(session, version_id, model_name="stale-model")
            from app.database.models import Document
            document = await session.get(Document, step57_document["source_id"])
            document.content_hash = "f" * 64
        from app.ingestion.reprocessing import ReprocessingAction, ReprocessingReason
        planner = _Planner(ReprocessingAction.FROM_PARSE, ReprocessingReason.SOURCE_CHANGED)
        provider = _FakeProvider()
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await EmbeddingService(session, provider=provider).retry_failed_version(
                    version_id, reprocessing_planner=planner)
            assert error.value.details == {
                "reprocessing_action": "FROM_PARSE", "reprocessing_reason": "SOURCE_CHANGED",
            }
        assert planner.calls[0][2] == {"embedding_profile_changed": False, "embedding_input_changed": False}
        assert provider.calls == []
        async with SessionFactory.begin() as session:
            assert (await session.get(KnowledgeVersion, version_id)).status == "FAILED"
            await session.execute(delete(Embedding).where(Embedding.embedding_profile_id == profile.id))
    asyncio.run(run())


@pytest.mark.parametrize(
    ("mismatch", "expected_action", "expected_reason"),
    [
        ("transformation", "FROM_TRANSFORM", "TRANSFORMATION_CHANGED"),
        ("chunking", "FROM_CHUNK", "CHUNKING_CHANGED"),
        ("chunk_order", "FROM_CHUNK", "ARTIFACT_INVALID"),
        ("chunk_hash", "FROM_CHUNK", "ARTIFACT_INVALID"),
    ],
    ids=["transformation-lineage", "chunking-config", "chunk-order", "chunk-content-hash"],
)
def test_failed_retry_rejects_each_stale_upstream_lineage_branch(
    step57_document, mismatch, expected_action, expected_reason,
):
    result = _prepare(step57_document)
    version_id = result["knowledge_version_id"]

    async def run():
        async with SessionFactory.begin() as session:
            version = await session.get(KnowledgeVersion, version_id)
            version.status = "FAILED"
            if mismatch == "transformation":
                transformation = await session.get(TransformationRun, version.transformation_run_id)
                transformation.transformation_version = "obsolete-transform-version"
            elif mismatch == "chunking":
                version.chunking_version = "obsolete-chunking-version"
            else:
                chunks = list((await session.scalars(select(Chunk).where(
                    Chunk.knowledge_version_id == version_id
                ).order_by(Chunk.chunk_index))).all())
                if mismatch == "chunk_order":
                    chunks[0].chunk_index = max(chunk.chunk_index for chunk in chunks) + 2
                else:
                    chunks[0].content_hash = "f" * 64

        from app.ingestion.reprocessing import ReprocessingAction, ReprocessingReason
        planner = _Planner(ReprocessingAction(expected_action), ReprocessingReason(expected_reason))
        provider = _FakeProvider()
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await EmbeddingService(session, provider=provider).retry_failed_version(
                    version_id, reprocessing_planner=planner)
            assert error.value.code == "EMBEDDING_FINGERPRINT_MISMATCH"
            assert error.value.details == {
                "reprocessing_action": expected_action, "reprocessing_reason": expected_reason,
            }
        assert planner.calls[0][2] == {
            "embedding_profile_changed": False, "embedding_input_changed": False,
        }
        assert provider.calls == []
        async with SessionFactory() as session:
            assert (await session.get(KnowledgeVersion, version_id)).status == "FAILED"
    asyncio.run(run())


@pytest.mark.parametrize(
    "profile_kwargs",
    [
        {"provider": "REMOTE"},
        {"provider_version": "sentence-transformers/other"},
        {"model_version": "not-the-frozen-revision"},
        {"dimensions": 1025},
        {"normalize_embeddings": False},
    ],
    ids=["provider", "provider-version", "model-version", "dimensions", "normalization"],
)
def test_failed_retry_classifies_each_remaining_semantic_profile_mismatch(step57_document, profile_kwargs):
    result = _prepare(step57_document)
    version_id = result["knowledge_version_id"]

    async def run():
        async with SessionFactory.begin() as session:
            version = await session.get(KnowledgeVersion, version_id)
            version.status = "FAILED"
            profile = await _insert_profile_evidence(session, version_id, **profile_kwargs)
        from app.ingestion.reprocessing import ReprocessingAction, ReprocessingReason
        planner = _Planner(ReprocessingAction.FROM_EMBED, ReprocessingReason.EMBEDDING_PROFILE_CHANGED)
        provider = _FakeProvider()
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await EmbeddingService(session, provider=provider).retry_failed_version(
                    version_id, reprocessing_planner=planner)
            assert error.value.code == "EMBEDDING_FINGERPRINT_MISMATCH"
            assert error.value.details == {
                "reprocessing_action": "FROM_EMBED",
                "reprocessing_reason": "EMBEDDING_PROFILE_CHANGED",
            }
        assert planner.calls[0][2] == {
            "embedding_profile_changed": True, "embedding_input_changed": False,
        }
        assert provider.calls == []
        async with SessionFactory.begin() as session:
            assert (await session.get(KnowledgeVersion, version_id)).status == "FAILED"
            await session.execute(delete(Embedding).where(Embedding.embedding_profile_id == profile.id))
    asyncio.run(run())


def test_failed_retry_claim_is_exclusive_under_concurrency(monkeypatch, step57_document):
    result = _prepare(step57_document)
    version_id = result["knowledge_version_id"]
    entered_build, release_build = asyncio.Event(), asyncio.Event()
    original_build = EmbeddingService.embed_processing_version

    async def gated_build(self, target_version_id):
        entered_build.set()
        await release_build.wait()
        return await original_build(self, target_version_id)

    monkeypatch.setattr(EmbeddingService, "embed_processing_version", gated_build)

    async def first_retry():
        async with SessionFactory() as session:
            return await EmbeddingService(session, provider=_FakeProvider()).retry_failed_version(
                version_id, reprocessing_planner=_Planner())

    async def run():
        async with SessionFactory.begin() as session:
            version = await session.get(KnowledgeVersion, version_id)
            version.status = "FAILED"
            await _insert_profile_evidence(session, version_id)

        first = asyncio.create_task(first_retry())
        await asyncio.wait_for(entered_build.wait(), timeout=15)
        try:
            async with SessionFactory() as session:
                with pytest.raises(ApplicationError) as error:
                    await EmbeddingService(session, provider=_FakeProvider()).retry_failed_version(
                        version_id, reprocessing_planner=_Planner())
                assert error.value.code == "PROCESSING_ALREADY_IN_PROGRESS"
        finally:
            release_build.set()
        built = await first
        assert built.embedded_count == built.required_count
        async with SessionFactory.begin() as session:
            claimed = await session.get(KnowledgeVersion, version_id)
            assert claimed.status == "PROCESSING"
            source_versions = list((await session.scalars(select(KnowledgeVersion).where(
                KnowledgeVersion.knowledge_source_id == claimed.knowledge_source_id
            ))).all())
            assert len(source_versions) == 1 and source_versions[0].id == version_id
            ids = select(Chunk.id).where(Chunk.knowledge_version_id == version_id)
            await session.execute(delete(Embedding).where(Embedding.chunk_id.in_(ids)))
    asyncio.run(run())


def test_repository_conflict_clause_deterministically_discards_duplicate_insert(step57_document):
    result = _prepare(step57_document)
    version_id = result["knowledge_version_id"]
    identity = EmbeddingProfileIdentity("LOCAL", "sentence-transformers/6.1.0", f"race-{uuid4()}",
        "5617a9f61b028005a4858fdac845db406aefb181", 1024, "v1", True)

    async def run():
        async with SessionFactory.begin() as session:
            version = await session.get(KnowledgeVersion, version_id)
            version.status = "PROCESSING"
            profile = await embedding_repository.get_or_create_embedding_profile(session, identity)
            chunk = await session.scalar(select(Chunk).where(
                Chunk.knowledge_version_id == version_id).order_by(Chunk.chunk_index))
            chunk_id, profile_id = chunk.id, profile.id

        ready = asyncio.Event()
        arrived = 0
        async def attempt():
            nonlocal arrived
            async with SessionFactory() as session:
                assert await embedding_repository.list_existing_embedding_chunk_ids(
                    session, profile_id, [chunk_id]) == set()
                await session.rollback()
                arrived += 1
                if arrived == 2:
                    ready.set()
                await asyncio.wait_for(ready.wait(), timeout=10)
                async with session.begin():
                    return await embedding_repository.insert_embeddings_conflict_safe(session, [{
                        "chunk_id": chunk_id, "embedding_profile_id": profile_id,
                        "vector": [1.0] + [0.0] * 1023,
                    }])

        inserted = await asyncio.gather(attempt(), attempt())
        assert sorted(inserted) == [0, 1]
        async with SessionFactory() as session:
            rows = (await session.scalars(select(Embedding).where(
                Embedding.chunk_id == chunk_id, Embedding.embedding_profile_id == profile_id))).all()
            assert len(rows) == 1
            embedding_id = rows[0].id
            assert (await session.get(KnowledgeVersion, version_id)).status == "PROCESSING"
            await session.rollback()
            async with session.begin():
                await session.execute(delete(Embedding).where(Embedding.id == embedding_id))
    asyncio.run(run())


def test_unexpected_database_integrity_error_marks_build_failed(monkeypatch, step57_document):
    result = _prepare(step57_document)
    version_id = result["knowledge_version_id"]

    async def fail_insert(*_args, **_kwargs):
        raise IntegrityError("unexpected constraint", {}, RuntimeError("not the embedding unique constraint"))

    monkeypatch.setattr(embedding_repository, "insert_embeddings_conflict_safe", fail_insert)
    async def run():
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await EmbeddingService(session, provider=_FakeProvider()).embed_processing_version(version_id)
            assert error.value.code == "EMBEDDING_BUILD_FAILED"
        async with SessionFactory() as session:
            assert (await session.get(KnowledgeVersion, version_id)).status == "FAILED"
    asyncio.run(run())


def test_normal_embedding_rejects_missing_knowledge_version_without_side_effects():
    version_id = uuid4()
    provider = _FakeProvider()
    target_identity = EmbeddingProfileIdentity(
        "LOCAL", "sentence-transformers/6.1.0", "BAAI/bge-m3",
        "5617a9f61b028005a4858fdac845db406aefb181", 1024, "v1", True,
    )

    async def run():
        async with SessionFactory() as session:
            profile_before = await embedding_repository.get_embedding_profile_by_identity(session, target_identity)
            profile_before_id = profile_before.id if profile_before else None
            await session.rollback()
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await EmbeddingService(session, provider=provider).embed_processing_version(version_id)
            assert error.value.code == "KNOWLEDGE_VERSION_NOT_PROCESSING"
        async with SessionFactory() as session:
            assert await session.get(KnowledgeVersion, version_id) is None
            profile_after = await embedding_repository.get_embedding_profile_by_identity(session, target_identity)
            profile_after_id = profile_after.id if profile_after else None
            assert profile_after_id == profile_before_id
        assert provider.calls == []
    asyncio.run(run())


@pytest.mark.parametrize("status", ["FAILED", "ACTIVE", "SUPERSEDED"])
def test_normal_embedding_rejects_non_processing_versions_without_side_effects(step57_document, status):
    result = _prepare(step57_document)
    version_id = result["knowledge_version_id"]
    provider = _FakeProvider()
    target_identity = EmbeddingProfileIdentity(
        "LOCAL", "sentence-transformers/6.1.0", "BAAI/bge-m3",
        "5617a9f61b028005a4858fdac845db406aefb181", 1024, "v1", True,
    )

    async def run():
        async with SessionFactory.begin() as session:
            (await session.get(KnowledgeVersion, version_id)).status = status
        async with SessionFactory() as session:
            profile_before = await embedding_repository.get_embedding_profile_by_identity(session, target_identity)
            profile_before_id = profile_before.id if profile_before else None
            await session.rollback()
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await EmbeddingService(session, provider=provider).embed_processing_version(version_id)
            assert error.value.code == "KNOWLEDGE_VERSION_NOT_PROCESSING"
        async with SessionFactory() as session:
            assert (await session.get(KnowledgeVersion, version_id)).status == status
            profile_after = await embedding_repository.get_embedding_profile_by_identity(session, target_identity)
            profile_after_id = profile_after.id if profile_after else None
            assert profile_after_id == profile_before_id
        assert provider.calls == []
    asyncio.run(run())


def test_historical_profile_embeddings_do_not_satisfy_target_completeness(step57_document):
    result = _prepare(step57_document)
    version_id = result["knowledge_version_id"]
    historical_identity = EmbeddingProfileIdentity(
        "LOCAL", "sentence-transformers/6.1.0", "BAAI/bge-m3",
        f"historical-{uuid4()}", 1024, "v1", True,
    )

    async def run():
        async with SessionFactory.begin() as session:
            historical_profile = await embedding_repository.get_or_create_embedding_profile(
                session, historical_identity)
            chunks = list((await session.scalars(select(Chunk).where(
                Chunk.knowledge_version_id == version_id).order_by(Chunk.chunk_index))).all())
            session.add_all([
                Embedding(chunk_id=chunk.id, embedding_profile_id=historical_profile.id,
                          vector=[1.0] + [0.0] * 1023)
                for chunk in chunks
            ])
            await session.flush()
            required_count = len(chunks)
            assert await embedding_repository.count_embeddings_for_version_profile(
                session, version_id, historical_profile.id) == required_count
            target_identity = EmbeddingProfileIdentity(
                "LOCAL", "sentence-transformers/6.1.0", "BAAI/bge-m3",
                "5617a9f61b028005a4858fdac845db406aefb181", 1024, "v1", True,
            )
            target_profile = await embedding_repository.get_embedding_profile_by_identity(session, target_identity)
            assert await embedding_repository.count_embeddings_for_version_profile(
                session, version_id, target_profile.id if target_profile else uuid4()) == 0

        provider = _FakeProvider()
        async with SessionFactory() as session:
            built = await EmbeddingService(session, provider=provider).embed_processing_version(version_id)
        assert built.required_count == required_count
        assert built.embedded_count == required_count
        assert built.embedded_this_run == required_count
        async with SessionFactory() as session:
            assert await embedding_repository.count_embeddings_for_version_profile(
                session, version_id, built.embedding_profile_id) == required_count
            assert await embedding_repository.count_embeddings_for_version_profile(
                session, version_id, historical_profile.id) == required_count
            assert (await session.get(KnowledgeVersion, version_id)).status == "PROCESSING"
    asyncio.run(run())


def test_compatible_failed_retry_skips_existing_embedding(step57_document):
    result = _prepare(step57_document)
    version_id = result["knowledge_version_id"]
    identity = EmbeddingProfileIdentity("LOCAL", "sentence-transformers/6.1.0", "BAAI/bge-m3",
        "5617a9f61b028005a4858fdac845db406aefb181", 1024, "v1", True)

    async def run():
        async with SessionFactory.begin() as session:
            version = await session.get(KnowledgeVersion, version_id)
            version.status = "FAILED"
            profile = await session.scalar(select(EmbeddingProfile).where(
                EmbeddingProfile.provider == identity.provider,
                EmbeddingProfile.provider_version == identity.provider_version,
                EmbeddingProfile.model_name == identity.model_name,
                EmbeddingProfile.model_version == identity.model_version,
                EmbeddingProfile.dimensions == identity.dimensions,
                EmbeddingProfile.embedding_input_version == identity.embedding_input_version,
                EmbeddingProfile.normalize_embeddings == identity.normalize_embeddings,
            ))
            if profile is None:
                profile = EmbeddingProfile(provider=identity.provider, provider_version=identity.provider_version,
                    model_name=identity.model_name, model_version=identity.model_version, dimensions=identity.dimensions,
                    embedding_input_version=identity.embedding_input_version,
                    normalize_embeddings=identity.normalize_embeddings, status="INACTIVE")
                session.add(profile)
                await session.flush()
            chunk = await session.scalar(select(Chunk).where(Chunk.knowledge_version_id == version_id).order_by(Chunk.chunk_index))
            session.add(Embedding(chunk_id=chunk.id, embedding_profile_id=profile.id, vector=[1.0] + [0.0] * 1023))
        async with SessionFactory() as session:
            built = await EmbeddingService(session, provider=_FakeProvider()).retry_failed_version(
                version_id, reprocessing_planner=_Planner())
            assert built.skipped_count >= 1
            assert built.embedded_count == built.required_count
        async with SessionFactory() as session:
            assert (await session.get(KnowledgeVersion, version_id)).status == "PROCESSING"
            await session.rollback()
            async with session.begin():
                ids = select(Chunk.id).where(Chunk.knowledge_version_id == version_id)
                await session.execute(delete(Embedding).where(Embedding.chunk_id.in_(ids)))
    asyncio.run(run())
