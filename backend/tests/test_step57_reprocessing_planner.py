import asyncio
from dataclasses import replace
import hashlib
import pytest
from uuid import uuid4
from sqlalchemy import delete, func, select

from app.database.models import Chunk, Document, KnowledgeSource, KnowledgeVersion, ParsingRun, TransformationRun
from app.database.session import SessionFactory
from app.ingestion.chunking.config import DEFAULT_CHUNKING_CONFIG
from app.ingestion.reprocessing import (
    ReprocessingAction, ReprocessingPlan, ReprocessingPlanner, ReprocessingReason,
    ReprocessingService, derive_chunk_fingerprint, derive_parse_fingerprint,
    derive_transformation_fingerprint,
)


def _install_second_valid_approved_run(ctx):
    from app.database.models import Document
    from app.database.session import SessionFactory

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


def test_derived_fingerprints_are_canonical_and_sensitive_to_processor_config():
    parsed, transformed = b'{"units":[]}', b'{"blocks":[]}'
    one = derive_parse_fingerprint("a" * 64, "txt_utf8", "v1", "basic_text_cleaning", "v1")
    assert one == derive_parse_fingerprint("a" * 64, "txt_utf8", "v1", "basic_text_cleaning", "v1")
    assert one != derive_parse_fingerprint("a" * 64, "txt_utf8", "v2", "basic_text_cleaning", "v1")
    assert derive_transformation_fingerprint(parsed, "canonical_document", "v1") == derive_transformation_fingerprint(parsed, "canonical_document", "v1")
    assert derive_transformation_fingerprint(parsed, "canonical_document", "v1") != derive_transformation_fingerprint(parsed, "canonical_document", "v2")
    assert derive_chunk_fingerprint(transformed, "structure_aware", "v1", 1200, 1800, 150) == derive_chunk_fingerprint(transformed, "structure_aware", "v1", 1200, 1800, 150)


def test_document_noop_is_idempotent_and_filename_is_not_source_identity(step57_document):
    ctx = step57_document
    asyncio.run(ctx["prepare_approved"]())

    async def verify():
        async with SessionFactory() as session:
            planner = ReprocessingPlanner(session, ctx["storage"])
            first = await planner.plan_source("DOCUMENT", ctx["source_id"])
            assert first.action is ReprocessingAction.NO_OP, (first.action, first.reason)
            assert first.source_fingerprint == ctx["content_hash"]
            assert first.baseline_transformation_run_id == first.approved_artifact_run_id
            assert first.reusable_parsed_ref is not None
            assert first.reusable_transformed_ref is not None
        async with SessionFactory.begin() as session:
            document = await session.get(Document, ctx["source_id"])
            document.original_filename = "renamed-source.txt"
        async with SessionFactory() as session:
            service = ReprocessingService(session, ctx["storage"])
            models = (ParsingRun, TransformationRun, KnowledgeVersion)
            before = []
            for model in models:
                before.append(await session.scalar(select(func.count()).select_from(model)))
            result = await service.reprocess_source("DOCUMENT", ctx["source_id"])
            after = []
            for model in models:
                after.append(await session.scalar(select(func.count()).select_from(model)))
            assert isinstance(result, ReprocessingPlan)
            assert result.action is ReprocessingAction.NO_OP
            assert result.source_fingerprint == ctx["content_hash"]
            assert before == after
    asyncio.run(verify())


def test_document_active_null_transform_lineage_requires_exact_approved_chunk_rebuild(step57_document):
    ctx = step57_document
    asyncio.run(ctx["prepare_approved"]())
    async def get_approved_id():
        async with SessionFactory() as session:
            document = await session.get(Document, ctx["source_id"])
            return document.approved_transformation_run_id
    approved_id = asyncio.run(get_approved_id())

    async def remove_active_lineage():
        async with SessionFactory.begin() as session:
            source = await session.scalar(select(KnowledgeSource).where(
                KnowledgeSource.document_id == ctx["source_id"]))
            active = await session.scalar(select(KnowledgeVersion).where(
                KnowledgeVersion.knowledge_source_id == source.id,
                KnowledgeVersion.status == "ACTIVE"))
            active.transformation_run_id = None
    asyncio.run(remove_active_lineage())

    async def verify():
        async with SessionFactory() as session:
            plan = await ReprocessingPlanner(session, ctx["storage"]).plan_source(
                "DOCUMENT", ctx["source_id"])
            assert (plan.action, plan.reason) == (
                ReprocessingAction.FROM_CHUNK, ReprocessingReason.ARTIFACT_INVALID)
            assert plan.reusable_transformed_ref.transformation_run_id == approved_id
    asyncio.run(verify())


def test_document_approved_b_active_a_chunk_lineage_requires_b(step57_document):
    ctx = step57_document
    asyncio.run(ctx["prepare_approved"]())
    _active_a, approved_b = _install_second_valid_approved_run(ctx)

    async def verify():
        async with SessionFactory() as session:
            plan = await ReprocessingPlanner(session, ctx["storage"]).plan_source(
                "DOCUMENT", ctx["source_id"])
            assert (plan.action, plan.reason) == (
                ReprocessingAction.FROM_CHUNK, ReprocessingReason.ARTIFACT_INVALID)
            assert plan.reusable_transformed_ref.transformation_run_id == approved_b
    asyncio.run(verify())


def test_matching_pending_candidate_is_review_pending_noop(step57_document):
    ctx = step57_document

    async def verify():
        from app.ingestion.orchestrator import IngestionOrchestrator
        async with SessionFactory() as session:
            await IngestionOrchestrator(session, ctx["storage"]).process_document(ctx["source_id"])
        async with SessionFactory() as session:
            plan = await ReprocessingPlanner(session, ctx["storage"]).plan_source("DOCUMENT", ctx["source_id"])
            assert plan.action is ReprocessingAction.NO_OP
            assert plan.reason is ReprocessingReason.REVIEW_PENDING
            assert plan.review_candidate_run_id is not None
    asyncio.run(verify())


@pytest.mark.parametrize(("mutation", "action", "reason"), [
    ("source", ReprocessingAction.FROM_PARSE, ReprocessingReason.SOURCE_CHANGED),
    ("parser", ReprocessingAction.FROM_PARSE, ReprocessingReason.PARSER_CHANGED),
    ("cleaning", ReprocessingAction.FROM_PARSE, ReprocessingReason.CLEANING_CHANGED),
    ("transformation", ReprocessingAction.FROM_TRANSFORM, ReprocessingReason.TRANSFORMATION_CHANGED),
])
def test_earliest_stale_stage_precedence(step57_document, monkeypatch, mutation, action, reason):
    ctx = step57_document
    asyncio.run(ctx["prepare_approved"]())
    from app.ingestion import reprocessing as module
    if mutation == "parser":
        from app.ingestion.parsing.text import TxtParser
        monkeypatch.setattr(TxtParser, "version", "v2")
    elif mutation == "cleaning":
        monkeypatch.setattr(module, "CLEANING_VERSION", "v2")
    elif mutation == "transformation":
        monkeypatch.setattr(module, "TRANSFORMATION_VERSION", "v2")

    async def verify():
        if mutation == "source":
            async with SessionFactory.begin() as session:
                run = (await session.execute(select(ParsingRun).where(
                    ParsingRun.document_id == ctx["source_id"]
                ))).scalar_one()
                run.raw_content_hash = "f" * 64
        async with SessionFactory() as session:
            plan = await ReprocessingPlanner(session, ctx["storage"]).plan_source("DOCUMENT", ctx["source_id"])
            assert (plan.action, plan.reason) == (action, reason)
            if action is ReprocessingAction.FROM_TRANSFORM:
                assert plan.reusable_parsed_ref is not None
                assert plan.reusable_transformed_ref is None
    asyncio.run(verify())


@pytest.mark.parametrize(("artifact", "reason"), [
    ("parsed-missing", ReprocessingReason.ARTIFACT_MISSING),
    ("parsed-invalid", ReprocessingReason.ARTIFACT_INVALID),
])
def test_parsed_artifact_integrity_selects_from_parse(step57_document, artifact, reason):
    ctx = step57_document
    asyncio.run(ctx["prepare_approved"]())

    async def verify():
        async with SessionFactory() as session:
            parsing = (await session.execute(select(ParsingRun).where(
                ParsingRun.document_id == ctx["source_id"]
            ))).scalar_one()
            key = parsing.parsed_storage_reference
        if artifact == "parsed-missing":
            ctx["storage"].delete(key)
        else:
            ctx["storage"].write_bytes(key, b"not-json")
        async with SessionFactory() as session:
            plan = await ReprocessingPlanner(session, ctx["storage"]).plan_source("DOCUMENT", ctx["source_id"])
            assert (plan.action, plan.reason) == (ReprocessingAction.FROM_PARSE, reason)
    asyncio.run(verify())


@pytest.mark.parametrize(("artifact", "reason"), [
    ("missing", ReprocessingReason.ARTIFACT_MISSING),
    ("invalid", ReprocessingReason.ARTIFACT_INVALID),
])
def test_transformed_artifact_integrity_selects_from_transform(step57_document, artifact, reason):
    ctx = step57_document
    asyncio.run(ctx["prepare_approved"]())

    async def verify():
        async with SessionFactory() as session:
            run = (await session.execute(select(TransformationRun).where(
                TransformationRun.document_id == ctx["source_id"]
            ))).scalar_one()
            key = run.transformed_storage_reference
        if artifact == "missing":
            ctx["storage"].delete(key)
        else:
            ctx["storage"].write_bytes(key, b"{}")
        async with SessionFactory() as session:
            plan = await ReprocessingPlanner(session, ctx["storage"]).plan_source("DOCUMENT", ctx["source_id"])
            assert (plan.action, plan.reason) == (ReprocessingAction.FROM_TRANSFORM, reason)
            assert plan.reusable_parsed_ref is not None
    asyncio.run(verify())


def test_chunking_drift_missing_and_invalid_chunks_are_from_chunk(step57_document, monkeypatch):
    ctx = step57_document
    asyncio.run(ctx["prepare_approved"]())
    from app.ingestion import reprocessing as module
    monkeypatch.setattr(module, "DEFAULT_CHUNKING_CONFIG", replace(DEFAULT_CHUNKING_CONFIG, target_chars=1100))

    async def verify():
        async with SessionFactory() as session:
            changed = await ReprocessingPlanner(session, ctx["storage"]).plan_source("DOCUMENT", ctx["source_id"])
            assert (changed.action, changed.reason) == (ReprocessingAction.FROM_CHUNK, ReprocessingReason.CHUNKING_CHANGED)
        monkeypatch.setattr(module, "DEFAULT_CHUNKING_CONFIG", DEFAULT_CHUNKING_CONFIG)
        async with SessionFactory.begin() as session:
            source = (await session.execute(select(KnowledgeSource).where(
                KnowledgeSource.document_id == ctx["source_id"]
            ))).scalar_one()
            version = (await session.execute(select(KnowledgeVersion).where(
                KnowledgeVersion.knowledge_source_id == source.id,
                KnowledgeVersion.status == "ACTIVE",
            ))).scalar_one()
            chunk = (await session.execute(select(Chunk).where(
                Chunk.knowledge_version_id == version.id
            ))).scalars().first()
            chunk.content_hash = "0" * 64
        async with SessionFactory() as session:
            invalid = await ReprocessingPlanner(session, ctx["storage"]).plan_source("DOCUMENT", ctx["source_id"])
            assert (invalid.action, invalid.reason) == (ReprocessingAction.FROM_CHUNK, ReprocessingReason.ARTIFACT_INVALID)
        async with SessionFactory.begin() as session:
            source = (await session.execute(select(KnowledgeSource).where(
                KnowledgeSource.document_id == ctx["source_id"]
            ))).scalar_one()
            version = (await session.execute(select(KnowledgeVersion).where(
                KnowledgeVersion.knowledge_source_id == source.id,
                KnowledgeVersion.status == "ACTIVE",
            ))).scalar_one()
            await session.execute(delete(Chunk).where(
                Chunk.knowledge_version_id == version.id
            ))
        async with SessionFactory() as session:
            missing = await ReprocessingPlanner(session, ctx["storage"]).plan_source("DOCUMENT", ctx["source_id"])
            assert (missing.action, missing.reason) == (ReprocessingAction.FROM_CHUNK, ReprocessingReason.ARTIFACT_MISSING)
    asyncio.run(verify())


@pytest.mark.parametrize(("change", "reason"), [
    ("profile", ReprocessingReason.EMBEDDING_PROFILE_CHANGED),
    ("input", ReprocessingReason.EMBEDDING_INPUT_CHANGED),
])
def test_embedding_changes_are_policy_only(step57_document, change, reason):
    ctx = step57_document
    asyncio.run(ctx["prepare_approved"]())
    async def verify():
        async with SessionFactory() as session:
            planner = ReprocessingPlanner(session, ctx["storage"])
            plan = await planner.plan_source(
                "DOCUMENT", ctx["source_id"],
                embedding_profile_changed=change == "profile",
                embedding_input_changed=change == "input",
            )
            assert (plan.action, plan.reason) == (ReprocessingAction.FROM_EMBED, reason)
    asyncio.run(verify())


def test_legacy_lesson_version_without_lineage_plans_conservative_from_parse(step57_lesson):
    ctx = step57_lesson
    asyncio.run(ctx["prepare_active"]())

    async def verify():
        async with SessionFactory.begin() as session:
            source = (await session.execute(select(KnowledgeSource).where(
                KnowledgeSource.lesson_id == ctx["source_id"]
            ))).scalar_one()
            version = (await session.execute(select(KnowledgeVersion).where(
                KnowledgeVersion.knowledge_source_id == source.id,
                KnowledgeVersion.status == "ACTIVE"
            ))).scalar_one()
            version.transformation_run_id = None
        async with SessionFactory() as session:
            plan = await ReprocessingPlanner(session, ctx["storage"]).plan_source("LESSON", ctx["source_id"])
            assert plan.action is ReprocessingAction.FROM_PARSE
            assert plan.reason is ReprocessingReason.ARTIFACT_MISSING
    asyncio.run(verify())
