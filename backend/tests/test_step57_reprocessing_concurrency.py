import asyncio
from hashlib import sha256

import pytest
from sqlalchemy import select

from app.core.errors import ApplicationError
from app.database.models import Document, KnowledgeVersion, Lesson
from app.database.session import SessionFactory
from app.ingestion.reprocessing import ReprocessingService


def test_document_re_review_claim_allows_only_one_processor(step57_document, monkeypatch):
    ctx = step57_document
    asyncio.run(ctx["prepare_approved"]())
    changed = ctx["storage"].objects[ctx["raw_key"]] + b" re-review"
    ctx["storage"].write_bytes(ctx["raw_key"], changed)

    async def change_hash():
        async with SessionFactory.begin() as session:
            document = await session.get(Document, ctx["source_id"])
            document.content_hash = sha256(changed).hexdigest()
            document.file_size_bytes = len(changed)
    asyncio.run(change_hash())

    from app.ingestion import orchestrator
    original_parse = orchestrator.parse_raw_artifact
    entered, release = asyncio.Event(), asyncio.Event()
    async def slow_parse(*args, **kwargs):
        entered.set()
        await release.wait()
        return await original_parse(*args, **kwargs)
    monkeypatch.setattr(orchestrator, "parse_raw_artifact", slow_parse)

    async def run_race():
        async with SessionFactory() as first_session, SessionFactory() as second_session:
            first = asyncio.create_task(ReprocessingService(
                first_session, ctx["storage"]).reprocess_source("DOCUMENT", ctx["source_id"]))
            await asyncio.wait_for(entered.wait(), timeout=10)
            document_state = await second_session.get(Document, ctx["source_id"])
            assert document_state.processing_status == "PROCESSING"
            with pytest.raises(ApplicationError) as raised:
                await ReprocessingService(second_session, ctx["storage"]).reprocess_source(
                    "DOCUMENT", ctx["source_id"])
            assert raised.value.code == "PROCESSING_ALREADY_IN_PROGRESS"
            release.set()
            result = await asyncio.wait_for(first, timeout=20)
            assert result["processing_status"] == "PREVIEW_READY"
    asyncio.run(run_race())


def test_lesson_rebuild_claim_blocks_second_concurrent_build(step57_lesson, monkeypatch):
    ctx = step57_lesson
    baseline = asyncio.run(ctx["prepare_active"]())

    async def make_stale():
        async with SessionFactory.begin() as session:
            lesson = await session.get(Lesson, ctx["source_id"])
            lesson.title = "Concurrent maintenance target"
    asyncio.run(make_stale())

    from app.ingestion import orchestrator
    original_build = orchestrator.build_chunks
    entered, release = asyncio.Event(), asyncio.Event()
    async def slow_build(*args, **kwargs):
        entered.set()
        await release.wait()
        return await original_build(*args, **kwargs)
    monkeypatch.setattr(orchestrator, "build_chunks", slow_build)

    async def run_race():
        async with SessionFactory() as first_session, SessionFactory() as second_session:
            first = asyncio.create_task(ReprocessingService(
                first_session, ctx["storage"]).reprocess_source("LESSON", ctx["source_id"]))
            await asyncio.wait_for(entered.wait(), timeout=10)
            from app.database.models import KnowledgeSource
            lesson_source_id = select(KnowledgeSource.id).where(
                KnowledgeSource.lesson_id == ctx["source_id"]
            ).scalar_subquery()
            processing = (await second_session.execute(select(KnowledgeVersion).where(
                KnowledgeVersion.knowledge_source_id == lesson_source_id,
                KnowledgeVersion.status == "PROCESSING"))).scalars().all()
            assert len(processing) == 1
            with pytest.raises(ApplicationError) as raised:
                await ReprocessingService(second_session, ctx["storage"]).reprocess_source(
                    "LESSON", ctx["source_id"])
            assert raised.value.code == "PROCESSING_ALREADY_IN_PROGRESS"
            release.set()
            result = await asyncio.wait_for(first, timeout=20)
            assert result["knowledge_version_id"] != baseline["knowledge_version_id"]
            old = await first_session.get(KnowledgeVersion, baseline["knowledge_version_id"])
            assert old.status == "ACTIVE"
    asyncio.run(run_race())
