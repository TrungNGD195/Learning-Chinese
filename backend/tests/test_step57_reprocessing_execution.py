import asyncio
from hashlib import sha256
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select

from app.core.errors import ApplicationError
from app.database.models import (
    Chunk, Document, HSKLevel, KnowledgeSource, KnowledgeVersion, Lesson,
    LessonVocabulary, ParsingRun, TransformationRun, Vocabulary,
)
from app.database.session import SessionFactory
from app.ingestion.reprocessing import (
    ReprocessingAction, ReprocessingPlanner, ReprocessingReason, ReprocessingService,
)


async def _count(model, source_id, source_type):
    async with SessionFactory() as session:
        if model is ParsingRun:
            field = ParsingRun.document_id if source_type == "DOCUMENT" else ParsingRun.lesson_id
        else:
            field = TransformationRun.document_id if source_type == "DOCUMENT" else TransformationRun.lesson_id
        return await session.scalar(select(func.count()).select_from(model).where(field == source_id))


def _approved_run_id(source_id):
    async def run():
        async with SessionFactory() as session:
            document = await session.get(Document, source_id)
            return document.approved_transformation_run_id
    return asyncio.run(run())


def _install_second_valid_approved_run(ctx):
    async def create():
        async with SessionFactory.begin() as session:
            document = await session.get(Document, ctx["source_id"])
            approved = await session.get(TransformationRun, document.approved_transformation_run_id)
            artifact_bytes = ctx["storage"].objects[approved.transformed_storage_reference]
            second_id = uuid4()
            key = f"step57/documents/{ctx['source_id']}/{second_id}/approved.json"
            ctx["storage"].write_bytes(key, artifact_bytes)
            session.add(TransformationRun(
                id=second_id, source_type="DOCUMENT", document_id=ctx["source_id"],
                parsing_run_id=approved.parsing_run_id,
                parsed_storage_reference=approved.parsed_storage_reference,
                transformation_strategy=approved.transformation_strategy,
                transformation_version=approved.transformation_version,
                status="SUCCEEDED", transformed_storage_reference=key,
                source_metadata_snapshot=approved.source_metadata_snapshot,
            ))
            await session.flush()
            document.approved_transformation_run_id = second_id
            document.review_transformation_run_id = second_id
            return approved.id, second_id
    return asyncio.run(create())


def test_document_from_parse_re_review_keeps_approved_and_active_lineage(step57_document):
    ctx = step57_document
    approved = asyncio.run(ctx["prepare_approved"]())
    approved_run_id = _approved_run_id(ctx["source_id"])
    original_raw = ctx["storage"].objects[ctx["raw_key"]]
    changed_raw = original_raw + b" Updated source content."
    ctx["storage"].write_bytes(ctx["raw_key"], changed_raw)
    changed_hash = sha256(changed_raw).hexdigest()

    async def execute():
        async with SessionFactory.begin() as session:
            document = await session.get(Document, ctx["source_id"])
            document.content_hash = changed_hash
            document.file_size_bytes = len(changed_raw)
        parses_before = await _count(ParsingRun, ctx["source_id"], "DOCUMENT")
        transforms_before = await _count(TransformationRun, ctx["source_id"], "DOCUMENT")
        async with SessionFactory() as session:
            service = ReprocessingService(session, ctx["storage"])
            plan = await service.plan_source("DOCUMENT", ctx["source_id"])
            assert (plan.action, plan.reason) == (
                ReprocessingAction.FROM_PARSE, ReprocessingReason.SOURCE_CHANGED)
            result = await service.reprocess_source("DOCUMENT", ctx["source_id"])
            assert result["review_status"] == "PENDING"
            assert result["processing_status"] == "PREVIEW_READY"
            assert result["approved_transformation_run_id"] == approved_run_id
            assert await _count(ParsingRun, ctx["source_id"], "DOCUMENT") == parses_before + 1
            assert await _count(TransformationRun, ctx["source_id"], "DOCUMENT") == transforms_before + 1
        async with SessionFactory() as session:
            document = await session.get(Document, ctx["source_id"])
            approved_id = document.approved_transformation_run_id
            assert approved_id is not None
            assert document.review_transformation_run_id != approved_id
            assert (document.review_status, document.processing_status) == ("PENDING", "PREVIEW_READY")
            source = await session.scalar(select(KnowledgeSource).where(
                KnowledgeSource.document_id == ctx["source_id"]))
            versions = (await session.execute(select(KnowledgeVersion).where(
                KnowledgeVersion.knowledge_source_id == source.id))).scalars().all()
            assert len(versions) == 1
            assert versions[0].id == approved["knowledge_version_id"]
            assert versions[0].status == "ACTIVE"
    asyncio.run(execute())


def test_document_from_chunk_uses_exact_approved_run_and_new_version(step57_document, monkeypatch):
    ctx = step57_document
    approved = asyncio.run(ctx["prepare_approved"]())
    source_id = ctx["source_id"]

    async def setup_stale_config():
        async with SessionFactory.begin() as session:
            version = await session.get(KnowledgeVersion, approved["knowledge_version_id"])
            version.chunking_version = "old-version"
    asyncio.run(setup_stale_config())
    parses_before = asyncio.run(_count(ParsingRun, source_id, "DOCUMENT"))
    transforms_before = asyncio.run(_count(TransformationRun, source_id, "DOCUMENT"))

    async def verify():
        async with SessionFactory() as session:
            service = ReprocessingService(session, ctx["storage"])
            plan = await service.plan_source("DOCUMENT", source_id)
            assert plan.action is ReprocessingAction.FROM_CHUNK
            assert plan.reusable_transformed_ref.transformation_run_id == plan.approved_artifact_run_id
            result = await service.reprocess_source("DOCUMENT", source_id)
            assert result["transformation_run_id"] == plan.approved_artifact_run_id
            assert await _count(ParsingRun, source_id, "DOCUMENT") == parses_before
            assert await _count(TransformationRun, source_id, "DOCUMENT") == transforms_before
            created = await session.get(KnowledgeVersion, result["knowledge_version_id"])
            assert created.transformation_run_id == plan.approved_artifact_run_id
            assert created.status == "PROCESSING"
            source = await session.scalar(select(KnowledgeSource).where(
                KnowledgeSource.document_id == source_id))
            versions = (await session.execute(select(KnowledgeVersion).where(
                KnowledgeVersion.knowledge_source_id == source.id))).scalars().all()
            assert sum(version.status == "ACTIVE" for version in versions) == 1
            assert sum(version.status == "PROCESSING" for version in versions) == 1
    asyncio.run(verify())


def test_legacy_document_active_null_lineage_rebuilds_from_approved_run(step57_document):
    ctx = step57_document
    approved = asyncio.run(ctx["prepare_approved"]())
    approved_run_id = _approved_run_id(ctx["source_id"])
    async def legacy_lineage_and_chunks():
        async with SessionFactory.begin() as session:
            active = await session.get(KnowledgeVersion, approved["knowledge_version_id"])
            active.transformation_run_id = None
        async with SessionFactory() as session:
            old_chunks = (await session.execute(select(
                Chunk.chunk_index, Chunk.content, Chunk.content_hash
            ).where(Chunk.knowledge_version_id == approved["knowledge_version_id"]).order_by(
                Chunk.chunk_index))).all()
            return old_chunks
    old_chunks = asyncio.run(legacy_lineage_and_chunks())
    parses_before = asyncio.run(_count(ParsingRun, ctx["source_id"], "DOCUMENT"))
    transforms_before = asyncio.run(_count(TransformationRun, ctx["source_id"], "DOCUMENT"))

    async def execute():
        async with SessionFactory() as session:
            service = ReprocessingService(session, ctx["storage"])
            plan = await service.plan_source("DOCUMENT", ctx["source_id"])
            assert (plan.action, plan.reason) == (
                ReprocessingAction.FROM_CHUNK, ReprocessingReason.ARTIFACT_INVALID)
            assert plan.reusable_transformed_ref.transformation_run_id == approved_run_id
            result = await service.reprocess_source("DOCUMENT", ctx["source_id"])
            assert result["transformation_run_id"] == approved_run_id
            created = await session.get(KnowledgeVersion, result["knowledge_version_id"])
            assert created.status == "PROCESSING"
            assert created.transformation_run_id == approved_run_id
            assert await _count(ParsingRun, ctx["source_id"], "DOCUMENT") == parses_before
            assert await _count(TransformationRun, ctx["source_id"], "DOCUMENT") == transforms_before
            old_active = await session.get(KnowledgeVersion, approved["knowledge_version_id"])
            assert old_active.status == "ACTIVE" and old_active.transformation_run_id is None
            after_chunks = (await session.execute(select(
                Chunk.chunk_index, Chunk.content, Chunk.content_hash
            ).where(Chunk.knowledge_version_id == old_active.id).order_by(Chunk.chunk_index))).all()
            assert after_chunks == old_chunks
            assert (await session.execute(select(Chunk).where(
                Chunk.knowledge_version_id == created.id))).scalars().all()
    asyncio.run(execute())


def test_approved_b_active_a_rebuilds_exact_b_and_preserves_a(step57_document, monkeypatch):
    ctx = step57_document
    approved = asyncio.run(ctx["prepare_approved"]())
    active_a, approved_b = _install_second_valid_approved_run(ctx)
    parses_before = asyncio.run(_count(ParsingRun, ctx["source_id"], "DOCUMENT"))
    transforms_before = asyncio.run(_count(TransformationRun, ctx["source_id"], "DOCUMENT"))
    from app.ingestion import orchestrator
    original_build = orchestrator.build_chunks
    built_run_ids = []
    async def capture(ref, version_id, **kwargs):
        built_run_ids.append(ref.transformation_run_id)
        return await original_build(ref, version_id, **kwargs)
    monkeypatch.setattr(orchestrator, "build_chunks", capture)

    async def execute():
        async with SessionFactory() as session:
            service = ReprocessingService(session, ctx["storage"])
            plan = await service.plan_source("DOCUMENT", ctx["source_id"])
            assert (plan.action, plan.reason) == (
                ReprocessingAction.FROM_CHUNK, ReprocessingReason.ARTIFACT_INVALID)
            assert plan.reusable_transformed_ref.transformation_run_id == approved_b
            result = await service.reprocess_source("DOCUMENT", ctx["source_id"])
            assert result["transformation_run_id"] == approved_b
            assert built_run_ids == [approved_b]
            created = await session.get(KnowledgeVersion, result["knowledge_version_id"])
            assert created.status == "PROCESSING" and created.transformation_run_id == approved_b
            old_active = await session.get(KnowledgeVersion, approved["knowledge_version_id"])
            assert old_active.status == "ACTIVE" and old_active.transformation_run_id == active_a
            assert await _count(ParsingRun, ctx["source_id"], "DOCUMENT") == parses_before
            assert await _count(TransformationRun, ctx["source_id"], "DOCUMENT") == transforms_before
    asyncio.run(execute())


def test_document_from_transform_reuses_exact_parsed_artifact_and_waits_for_review(step57_document):
    ctx = step57_document
    asyncio.run(ctx["prepare_approved"]())
    approved_run_id = _approved_run_id(ctx["source_id"])
    async def stale_transform_identity():
        async with SessionFactory.begin() as session:
            run = await session.get(TransformationRun, approved_run_id)
            run.transformation_version = "legacy-version"
    asyncio.run(stale_transform_identity())
    parses_before = asyncio.run(_count(ParsingRun, ctx["source_id"], "DOCUMENT"))
    transforms_before = asyncio.run(_count(TransformationRun, ctx["source_id"], "DOCUMENT"))

    async def verify():
        async with SessionFactory() as session:
            service = ReprocessingService(session, ctx["storage"])
            plan = await service.plan_source("DOCUMENT", ctx["source_id"])
            assert plan.action is ReprocessingAction.FROM_TRANSFORM
            assert plan.reusable_parsed_ref.parsing_run_id is not None
            result = await service.reprocess_source("DOCUMENT", ctx["source_id"])
            assert result["action"] == "FROM_TRANSFORM"
            assert result["review_candidate_run_id"] != approved_run_id
            assert await _count(ParsingRun, ctx["source_id"], "DOCUMENT") == parses_before
            assert await _count(TransformationRun, ctx["source_id"], "DOCUMENT") == transforms_before + 1
            source = await session.scalar(select(KnowledgeSource).where(
                KnowledgeSource.document_id == ctx["source_id"]))
            assert await session.scalar(select(func.count()).select_from(KnowledgeVersion).where(
                KnowledgeVersion.knowledge_source_id == source.id)) == 1
    asyncio.run(verify())


def test_lesson_edit_requires_explicit_maintenance_and_builds_new_lineage(step57_lesson):
    ctx = step57_lesson
    original = asyncio.run(ctx["prepare_active"]())
    parses_before = asyncio.run(_count(ParsingRun, ctx["source_id"], "LESSON"))
    transforms_before = asyncio.run(_count(TransformationRun, ctx["source_id"], "LESSON"))

    async def edit_and_check():
        async with SessionFactory.begin() as session:
            lesson = await session.get(Lesson, ctx["source_id"])
            lesson.title = "Edited title"
        async with SessionFactory() as session:
            planner = ReprocessingPlanner(session, ctx["storage"])
            plan = await planner.plan_source("LESSON", ctx["source_id"])
            assert plan.action is ReprocessingAction.FROM_PARSE
            assert await _count(ParsingRun, ctx["source_id"], "LESSON") == parses_before
            assert await _count(TransformationRun, ctx["source_id"], "LESSON") == transforms_before
        async with SessionFactory() as session:
            result = await ReprocessingService(session, ctx["storage"]).reprocess_source(
                "LESSON", ctx["source_id"])
            assert result["action"] == "FROM_PARSE"
            created = await session.get(KnowledgeVersion, result["knowledge_version_id"])
            assert created.transformation_run_id == result["transformation_run_id"]
            assert created.status == "PROCESSING"
            assert created.id != original["knowledge_version_id"]
            assert await _count(ParsingRun, ctx["source_id"], "LESSON") == parses_before + 1
            assert await _count(TransformationRun, ctx["source_id"], "LESSON") == transforms_before + 1
            old = await session.get(KnowledgeVersion, original["knowledge_version_id"])
            lesson = await session.get(Lesson, ctx["source_id"])
            assert old.status == "ACTIVE"
            assert lesson.status == "PUBLISHED"
    asyncio.run(edit_and_check())


def test_shared_vocabulary_edit_stales_only_linked_published_lessons(step57_lesson):
    ctx = step57_lesson
    other_lesson_id, unaffected_lesson_id, vocabulary_id = uuid4(), uuid4(), uuid4()
    async def setup_shared_content():
        async with SessionFactory.begin() as session:
            session.add_all([
                Lesson(id=other_lesson_id, hsk_level_id=ctx["level_id"],
                       lesson_number=920001, title="Shared lesson",
                       description="Shared content baseline.", status="PUBLISHED"),
                Lesson(id=unaffected_lesson_id, hsk_level_id=ctx["level_id"],
                       lesson_number=920002, title="Unaffected lesson",
                       description="Independent content baseline.", status="PUBLISHED"),
                Vocabulary(id=vocabulary_id, hanzi="学", pinyin="xué",
                           vietnamese_meaning="học", part_of_speech="verb"),
            ])
            await session.flush()
            session.add_all([
                LessonVocabulary(lesson_id=ctx["source_id"], vocabulary_id=vocabulary_id, order_index=1),
                LessonVocabulary(lesson_id=other_lesson_id, vocabulary_id=vocabulary_id, order_index=1),
            ])
    asyncio.run(setup_shared_content())
    from app.ingestion.orchestrator import IngestionOrchestrator
    async def build_other(lesson_id):
        async with SessionFactory() as session:
            result = await IngestionOrchestrator(session, ctx["storage"]).process_published_lesson(lesson_id)
        async with SessionFactory.begin() as session:
            version = await session.get(KnowledgeVersion, result["knowledge_version_id"])
            version.status = "ACTIVE"
        return result
    asyncio.run(ctx["prepare_active"]())
    other_active = asyncio.run(build_other(other_lesson_id))
    unaffected_active = asyncio.run(build_other(unaffected_lesson_id))
    async def prior_hashes():
        async with SessionFactory() as session:
            hashes = {}
            for lesson_id in (ctx["source_id"], other_lesson_id, unaffected_lesson_id):
                source = await session.scalar(select(KnowledgeSource).where(
                    KnowledgeSource.lesson_id == lesson_id))
                active = await session.scalar(select(KnowledgeVersion).where(
                    KnowledgeVersion.knowledge_source_id == source.id,
                    KnowledgeVersion.status == "ACTIVE"))
                run = await session.get(TransformationRun, active.transformation_run_id)
                parsing = await session.get(ParsingRun, run.parsing_run_id)
                hashes[lesson_id] = parsing.raw_content_hash
            return hashes
    async def update_and_plan():
        async with SessionFactory.begin() as session:
            vocabulary = await session.get(Vocabulary, vocabulary_id)
            vocabulary.vietnamese_meaning = "học tập"
        async with SessionFactory() as session:
            planner = ReprocessingPlanner(session, ctx["storage"])
            linked_a = await planner.plan_source("LESSON", ctx["source_id"])
            linked_b = await planner.plan_source("LESSON", other_lesson_id)
            unaffected = await planner.plan_source("LESSON", unaffected_lesson_id)
            assert linked_a.action is ReprocessingAction.FROM_PARSE
            assert linked_b.action is ReprocessingAction.FROM_PARSE
            assert unaffected.action is ReprocessingAction.NO_OP, (unaffected.action, unaffected.reason)
            assert linked_a.source_fingerprint != old_hashes[ctx["source_id"]]
            assert linked_b.source_fingerprint != old_hashes[other_lesson_id]
            assert unaffected.source_fingerprint == old_hashes[unaffected_lesson_id]
            assert unaffected.source_fingerprint
        async with SessionFactory() as session:
            assert (await session.get(KnowledgeVersion, other_active["knowledge_version_id"])).status == "ACTIVE"
            assert (await session.get(KnowledgeVersion, unaffected_active["knowledge_version_id"])).status == "ACTIVE"
    try:
        old_hashes = asyncio.run(prior_hashes())
        asyncio.run(update_and_plan())
    finally:
        async def cleanup_added_lessons():
            async with SessionFactory.begin() as session:
                lesson_ids = [ctx["source_id"], other_lesson_id, unaffected_lesson_id]
                source_ids = select(KnowledgeSource.id).where(KnowledgeSource.lesson_id.in_(lesson_ids))
                version_ids = select(KnowledgeVersion.id).where(KnowledgeVersion.knowledge_source_id.in_(source_ids))
                await session.execute(delete(Chunk).where(Chunk.knowledge_version_id.in_(version_ids)))
                await session.execute(delete(KnowledgeVersion).where(KnowledgeVersion.knowledge_source_id.in_(source_ids)))
                await session.execute(delete(KnowledgeSource).where(KnowledgeSource.lesson_id.in_(lesson_ids)))
                await session.execute(delete(TransformationRun).where(TransformationRun.lesson_id.in_(lesson_ids)))
                await session.execute(delete(ParsingRun).where(ParsingRun.lesson_id.in_(lesson_ids)))
                await session.execute(delete(LessonVocabulary).where(LessonVocabulary.lesson_id.in_(lesson_ids)))
                await session.execute(delete(Vocabulary).where(Vocabulary.id == vocabulary_id))
                await session.execute(delete(Lesson).where(Lesson.id.in_(lesson_ids)))
        asyncio.run(cleanup_added_lessons())


def test_lesson_from_chunk_reuses_active_transform_without_parse_or_transform(step57_lesson):
    ctx = step57_lesson
    original = asyncio.run(ctx["prepare_active"]())
    async def setup_stale_config():
        async with SessionFactory.begin() as session:
            version = await session.get(KnowledgeVersion, original["knowledge_version_id"])
            version.chunking_version = "old-version"
    asyncio.run(setup_stale_config())
    parses_before = asyncio.run(_count(ParsingRun, ctx["source_id"], "LESSON"))
    transforms_before = asyncio.run(_count(TransformationRun, ctx["source_id"], "LESSON"))
    async def baseline_transform_id():
        async with SessionFactory() as session:
            version = await session.get(KnowledgeVersion, original["knowledge_version_id"])
            return version.transformation_run_id
    original_transform_id = asyncio.run(baseline_transform_id())

    async def verify():
        async with SessionFactory() as session:
            service = ReprocessingService(session, ctx["storage"])
            plan = await service.plan_source("LESSON", ctx["source_id"])
            assert plan.action is ReprocessingAction.FROM_CHUNK
            result = await service.reprocess_source("LESSON", ctx["source_id"])
            assert result["transformation_run_id"] == original_transform_id
            created = await session.get(KnowledgeVersion, result["knowledge_version_id"])
            assert created.transformation_run_id == original_transform_id
            assert created.status == "PROCESSING"
            assert await _count(ParsingRun, ctx["source_id"], "LESSON") == parses_before
            assert await _count(TransformationRun, ctx["source_id"], "LESSON") == transforms_before
            old = await session.get(KnowledgeVersion, original["knowledge_version_id"])
            assert old.status == "ACTIVE"
    asyncio.run(verify())


def test_lesson_from_transform_reuses_parsed_artifact_and_allocates_new_version(step57_lesson):
    ctx = step57_lesson
    original = asyncio.run(ctx["prepare_active"]())
    async def stale_transform_identity():
        async with SessionFactory.begin() as session:
            version = await session.get(KnowledgeVersion, original["knowledge_version_id"])
            run = await session.get(TransformationRun, version.transformation_run_id)
            run.transformation_version = "legacy-version"
    asyncio.run(stale_transform_identity())
    parses_before = asyncio.run(_count(ParsingRun, ctx["source_id"], "LESSON"))
    transforms_before = asyncio.run(_count(TransformationRun, ctx["source_id"], "LESSON"))

    async def verify():
        async with SessionFactory() as session:
            service = ReprocessingService(session, ctx["storage"])
            plan = await service.plan_source("LESSON", ctx["source_id"])
            assert plan.action is ReprocessingAction.FROM_TRANSFORM
            parsed_run_id = plan.reusable_parsed_ref.parsing_run_id
            result = await service.reprocess_source("LESSON", ctx["source_id"])
            created = await session.get(KnowledgeVersion, result["knowledge_version_id"])
            assert created.transformation_run_id == result["transformation_run_id"]
            new_run = await session.get(TransformationRun, result["transformation_run_id"])
            assert new_run.parsing_run_id == parsed_run_id
            assert await _count(ParsingRun, ctx["source_id"], "LESSON") == parses_before
            assert await _count(TransformationRun, ctx["source_id"], "LESSON") == transforms_before + 1
            assert (await session.get(KnowledgeVersion, original["knowledge_version_id"])).status == "ACTIVE"
    asyncio.run(verify())


def test_from_embed_is_policy_only_and_creates_no_version(step57_lesson):
    ctx = step57_lesson
    asyncio.run(ctx["prepare_active"]())

    async def verify():
        async with SessionFactory() as session:
            service = ReprocessingService(session, ctx["storage"])
            plan = await service.planner.plan_source("LESSON", ctx["source_id"],
                                                       embedding_profile_changed=True)
            assert (plan.action, plan.reason) == (
                ReprocessingAction.FROM_EMBED, ReprocessingReason.EMBEDDING_PROFILE_CHANGED)
            assert await session.scalar(select(func.count()).select_from(KnowledgeVersion).where(
                KnowledgeVersion.knowledge_source_id == select(KnowledgeSource.id).where(
                    KnowledgeSource.lesson_id == ctx["source_id"]).scalar_subquery())) == 1
            assert await _count(ParsingRun, ctx["source_id"], "LESSON") == 1
            assert await _count(TransformationRun, ctx["source_id"], "LESSON") == 1
    asyncio.run(verify())


def test_failed_re_review_can_retry_and_preserves_approved_identity(step57_document, monkeypatch):
    ctx = step57_document
    approved = asyncio.run(ctx["prepare_approved"]())
    old_active_id = approved["knowledge_version_id"]
    approved_run_id = _approved_run_id(ctx["source_id"])
    raw = ctx["storage"].objects[ctx["raw_key"]] + b" newer source"
    ctx["storage"].write_bytes(ctx["raw_key"], raw)
    from app.ingestion import orchestrator

    async def alter_source_hash():
        async with SessionFactory.begin() as session:
            document = await session.get(Document, ctx["source_id"])
            document.content_hash = sha256(raw).hexdigest()
            document.file_size_bytes = len(raw)
    asyncio.run(alter_source_hash())
    original_transform = orchestrator.transform_parsed_artifact
    async def fail_transform(*_args, **_kwargs):
        raise ApplicationError("TRANSFORMATION_FAILED", "private failure", status_code=500)
    monkeypatch.setattr(orchestrator, "transform_parsed_artifact", fail_transform)

    async def fail_once():
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError):
                await ReprocessingService(session, ctx["storage"]).reprocess_source(
                    "DOCUMENT", ctx["source_id"])
        async with SessionFactory() as session:
            document = await session.get(Document, ctx["source_id"])
            assert (document.review_status, document.processing_status) == ("PENDING", "FAILED")
            assert document.review_transformation_run_id is None
            assert document.approved_transformation_run_id == approved_run_id
            assert document.approved_by == ctx["user_id"] and document.approved_at is not None
            assert (await session.get(KnowledgeVersion, old_active_id)).status == "ACTIVE"
    asyncio.run(fail_once())
    asyncio.run(fail_once())

    monkeypatch.setattr(orchestrator, "transform_parsed_artifact", original_transform)
    async def retry():
        async with SessionFactory() as session:
            result = await ReprocessingService(session, ctx["storage"]).reprocess_source(
                "DOCUMENT", ctx["source_id"])
            assert result["review_status"] == "PENDING"
            assert result["processing_status"] == "PREVIEW_READY"
            assert result["approved_transformation_run_id"] == approved_run_id
            assert result["review_candidate_run_id"] != approved_run_id
            document = await session.get(Document, ctx["source_id"])
            assert document.approved_by == ctx["user_id"] and document.approved_at is not None
            assert (await session.get(KnowledgeVersion, old_active_id)).status == "ACTIVE"
    asyncio.run(retry())


def test_document_candidate_rejection_restores_approved_artifact_and_active(step57_document):
    ctx = step57_document
    approved = asyncio.run(ctx["prepare_approved"]())
    approved_run_id = _approved_run_id(ctx["source_id"])
    raw = ctx["storage"].objects[ctx["raw_key"]] + b" replacement candidate"
    ctx["storage"].write_bytes(ctx["raw_key"], raw)

    async def execute():
        async with SessionFactory.begin() as session:
            document = await session.get(Document, ctx["source_id"])
            document.content_hash = sha256(raw).hexdigest()
            document.file_size_bytes = len(raw)
        async with SessionFactory() as session:
            service = ReprocessingService(session, ctx["storage"])
            await service.reprocess_source("DOCUMENT", ctx["source_id"])
            document = await session.get(Document, ctx["source_id"])
            candidate_id = document.review_transformation_run_id
            assert candidate_id != approved_run_id
            from app.ingestion.orchestrator import IngestionOrchestrator
            result = await IngestionOrchestrator(session, ctx["storage"]).reject_document(ctx["source_id"])
            assert result["review_status"] == "APPROVED"
            document = await session.get(Document, ctx["source_id"])
            assert document.review_transformation_run_id == approved_run_id
            assert document.approved_transformation_run_id == approved_run_id
            assert document.review_status == "APPROVED"
            assert (await session.get(KnowledgeVersion, approved["knowledge_version_id"])).status == "ACTIVE"
            assert await session.get(TransformationRun, candidate_id) is not None
    asyncio.run(execute())


def test_document_reapproval_switches_approved_pointer_only_after_candidate_review(step57_document):
    ctx = step57_document
    approved = asyncio.run(ctx["prepare_approved"]())
    old_run_id = _approved_run_id(ctx["source_id"])
    raw = ctx["storage"].objects[ctx["raw_key"]] + b" approved replacement"
    ctx["storage"].write_bytes(ctx["raw_key"], raw)

    async def execute():
        async with SessionFactory.begin() as session:
            document = await session.get(Document, ctx["source_id"])
            document.content_hash = sha256(raw).hexdigest()
            document.file_size_bytes = len(raw)
        async with SessionFactory() as session:
            service = ReprocessingService(session, ctx["storage"])
            await service.reprocess_source("DOCUMENT", ctx["source_id"])
            document = await session.get(Document, ctx["source_id"])
            candidate_id = document.review_transformation_run_id
            assert document.approved_transformation_run_id == old_run_id
            from app.ingestion.orchestrator import IngestionOrchestrator
            result = await IngestionOrchestrator(session, ctx["storage"]).approve_document(
                ctx["source_id"], ctx["user_id"])
            document = await session.get(Document, ctx["source_id"])
            version = await session.get(KnowledgeVersion, result["knowledge_version_id"])
            assert document.approved_transformation_run_id == candidate_id
            assert version.transformation_run_id == candidate_id
            assert version.status == "PROCESSING"
            assert (await session.get(KnowledgeVersion, approved["knowledge_version_id"])).status == "ACTIVE"
    asyncio.run(execute())


def test_chunk_build_failure_fails_new_version_and_preserves_active(step57_lesson, monkeypatch):
    ctx = step57_lesson
    original = asyncio.run(ctx["prepare_active"]())
    async def stale_config():
        async with SessionFactory.begin() as session:
            version = await session.get(KnowledgeVersion, original["knowledge_version_id"])
            version.chunking_version = "old-version"
    asyncio.run(stale_config())
    from app.ingestion import orchestrator as orchestration
    original_build = orchestration.build_chunks
    async def fail(*_args, **_kwargs):
        raise ApplicationError("CHUNKING_FAILED", "private chunk failure", status_code=500)
    monkeypatch.setattr(orchestration, "build_chunks", fail)

    async def execute():
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as raised:
                await ReprocessingService(session, ctx["storage"]).reprocess_source(
                    "LESSON", ctx["source_id"])
            assert raised.value.code == "KNOWLEDGE_BUILD_FAILED"
            source = await session.scalar(select(KnowledgeSource).where(
                KnowledgeSource.lesson_id == ctx["source_id"]))
            versions = (await session.execute(select(KnowledgeVersion).where(
                KnowledgeVersion.knowledge_source_id == source.id).order_by(
                    KnowledgeVersion.version_number))).scalars().all()
            assert [version.status for version in versions] == ["ACTIVE", "FAILED"]
            old_chunks = (await session.execute(select(Chunk.content).where(
                Chunk.knowledge_version_id == original["knowledge_version_id"]))).scalars().all()
            assert old_chunks
    asyncio.run(execute())
    monkeypatch.setattr(orchestration, "build_chunks", original_build)
