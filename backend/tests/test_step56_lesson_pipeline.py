import asyncio
from io import BytesIO
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.core.errors import ApplicationError
from app.database.models import (
    Chunk, Grammar, HSKLevel, KnowledgeSource, KnowledgeVersion, Lesson,
    LessonGrammar, LessonVocabulary, ParsingRun, TransformationRun, Vocabulary,
)
from app.database.session import SessionFactory
from app.ingestion.orchestrator import IngestionOrchestrator


class MemoryStorage:
    def __init__(self):
        self.objects = {}
        self.pending = {}

    def write_bytes(self, key, data):
        self.objects[key] = data

    def create_temp(self):
        key = f"tmp/{uuid4().hex}"
        handle = _SavedBuffer()
        self.pending[key] = handle
        return key, handle

    def write(self, handle, data):
        handle.write(data)

    def finalize(self, temp_key, storage_key):
        self.objects[storage_key] = self.pending.pop(temp_key).saved
        return storage_key

    def discard(self, key):
        self.pending.pop(key, None)

    def delete(self, key):
        self.objects.pop(key, None)

    def open(self, key):
        return BytesIO(self.objects[key])

    def open_temp(self, key):
        return BytesIO(self.pending[key].getvalue())


class _SavedBuffer(BytesIO):
    def close(self):
        self.saved = self.getvalue()
        super().close()


@pytest.fixture
def lesson_context():
    level_id, lesson_id, vocab_id, lesson_vocab_id = (uuid4() for _ in range(4))
    storage = MemoryStorage()
    level_number = 4_000_000 + level_id.int % 1_000_000

    async def setup():
        async with SessionFactory.begin() as session:
            session.add(HSKLevel(id=level_id, level_number=level_number, order_index=level_number))
            await session.flush()
            session.add(Lesson(
                id=lesson_id, hsk_level_id=level_id, lesson_number=1,
                title="Chinese greetings", description="First lesson", status="PUBLISHED",
            ))
            await session.flush()
            session.add(Vocabulary(id=vocab_id, hanzi="你好", pinyin="nǐ hǎo",
                                   vietnamese_meaning="xin chào"))
            await session.flush()
            session.add(LessonVocabulary(
                id=lesson_vocab_id, lesson_id=lesson_id, vocabulary_id=vocab_id, order_index=1,
                example="你好！",
            ))
    asyncio.run(setup())
    ctx = {"level_id": level_id, "lesson_id": lesson_id, "vocab_id": vocab_id,
           "lesson_vocab_id": lesson_vocab_id, "storage": storage}
    yield ctx

    async def cleanup():
        async with SessionFactory.begin() as session:
            source_ids = select(KnowledgeSource.id).where(KnowledgeSource.lesson_id == lesson_id)
            version_ids = select(KnowledgeVersion.id).where(KnowledgeVersion.knowledge_source_id.in_(source_ids))
            await session.execute(delete(Chunk).where(Chunk.knowledge_version_id.in_(version_ids)))
            await session.execute(delete(KnowledgeVersion).where(KnowledgeVersion.knowledge_source_id.in_(source_ids)))
            await session.execute(delete(KnowledgeSource).where(KnowledgeSource.lesson_id == lesson_id))
            await session.execute(delete(TransformationRun).where(TransformationRun.lesson_id == lesson_id))
            await session.execute(delete(ParsingRun).where(ParsingRun.lesson_id == lesson_id))
            await session.execute(delete(LessonVocabulary).where(LessonVocabulary.lesson_id == lesson_id))
            await session.execute(delete(LessonGrammar).where(LessonGrammar.lesson_id == lesson_id))
            await session.execute(delete(Vocabulary).where(Vocabulary.id == vocab_id))
            await session.execute(delete(Lesson).where(Lesson.id == lesson_id))
            await session.execute(delete(HSKLevel).where(HSKLevel.id == level_id))
    asyncio.run(cleanup())


def test_published_lesson_claim_precedes_snapshot_and_completed_pipeline_reuses_stages(lesson_context):
    ctx = lesson_context
    async def verify():
        async with SessionFactory() as session:
            orchestration = IngestionOrchestrator(session, ctx["storage"])
            result = await orchestration.process_published_lesson(ctx["lesson_id"])
            version_id = result["knowledge_version_id"]
            lesson = await session.get(Lesson, ctx["lesson_id"])
            version = await session.get(KnowledgeVersion, version_id)
            rows = (await session.execute(select(Chunk).where(
                Chunk.knowledge_version_id == version_id))).scalars().all()
            assert lesson.status == "PUBLISHED"
            assert version.status == "PROCESSING"
            assert rows and any(row.content_type == "VOCABULARY" for row in rows)
            assert (await session.execute(select(KnowledgeSource.id).where(
                KnowledgeSource.lesson_id == ctx["lesson_id"]))).scalar_one()
    asyncio.run(verify())


@pytest.mark.parametrize("failed_stage", ["raw", "parse", "transform", "chunk"])
def test_lesson_stage_failure_marks_claim_failed_and_fails_fast(lesson_context, monkeypatch, failed_stage):
    ctx = lesson_context
    source_id, active_id = uuid4(), uuid4()
    async def seed_active():
        async with SessionFactory.begin() as session:
            session.add(KnowledgeSource(id=source_id, source_type="LESSON", lesson_id=ctx["lesson_id"]))
            await session.flush()
            session.add(KnowledgeVersion(id=active_id, knowledge_source_id=source_id,
                                         version_number=1, status="ACTIVE"))
            await session.flush()
            session.add(Chunk(knowledge_version_id=active_id, content="old active lesson chunk",
                              content_type="LESSON_GENERAL", chunk_index=0, metadata_json={}))
    asyncio.run(seed_active())
    from app.ingestion import orchestrator as module
    calls = {name: 0 for name in ("raw", "parse", "transform", "chunk")}
    names = {
        "raw": "create_lesson_snapshot", "parse": "parse_raw_artifact",
        "transform": "transform_parsed_artifact", "chunk": "build_chunks",
    }
    for stage in ("raw", "parse", "transform", "chunk"):
        original = getattr(module, names[stage])
        async def replacement(*args, _stage=stage, _original=original, **kwargs):
            calls[_stage] += 1
            if _stage == failed_stage:
                raise ApplicationError("STAGE_TEST_FAILURE", "private stage text", status_code=500)
            return await _original(*args, **kwargs)
        monkeypatch.setattr(module, names[stage], replacement)

    async def verify():
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as raised:
                await IngestionOrchestrator(session, ctx["storage"]).process_published_lesson(ctx["lesson_id"])
            assert (raised.value.code, raised.value.status_code) == ("KNOWLEDGE_BUILD_FAILED", 500)
            assert "private stage text" not in str(raised.value)
            assert calls[failed_stage] == 1
            assert all(calls[name] == 0 for name in ("raw", "parse", "transform", "chunk")
                       if ("raw", "parse", "transform", "chunk").index(name) >
                       ("raw", "parse", "transform", "chunk").index(failed_stage))
            lesson = await session.get(Lesson, ctx["lesson_id"])
            versions = (await session.execute(select(KnowledgeVersion).where(
                KnowledgeVersion.knowledge_source_id == source_id).order_by(
                    KnowledgeVersion.version_number))).scalars().all()
            assert lesson.status == "PUBLISHED"
            assert [version.status for version in versions] == ["ACTIVE", "FAILED"]
            chunks = (await session.execute(select(Chunk.content).where(
                Chunk.knowledge_version_id == active_id))).scalars().all()
            assert chunks == ["old active lesson chunk"]
    asyncio.run(verify())


def test_lesson_retry_creates_new_version_after_failed_claim(lesson_context, monkeypatch):
    ctx = lesson_context
    from app.ingestion import orchestrator as module
    original = module.create_lesson_snapshot
    calls = 0
    async def fail_once(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ApplicationError("RAW_STORAGE_FAILED", "private storage text", status_code=500)
        return await original(*args, **kwargs)
    monkeypatch.setattr(module, "create_lesson_snapshot", fail_once)

    async def verify():
        async with SessionFactory() as session:
            orchestration = IngestionOrchestrator(session, ctx["storage"])
            with pytest.raises(ApplicationError):
                await orchestration.process_published_lesson(ctx["lesson_id"])
            first = (await session.execute(select(KnowledgeVersion).join(KnowledgeSource).where(
                KnowledgeSource.lesson_id == ctx["lesson_id"]))).scalar_one()
            first_id = first.id
            assert first.status == "FAILED"
            result = await orchestration.retry_lesson_knowledge(ctx["lesson_id"])
            assert result["knowledge_version_id"] != first_id
            versions = (await session.execute(select(KnowledgeVersion).join(KnowledgeSource).where(
                KnowledgeSource.lesson_id == ctx["lesson_id"]).order_by(KnowledgeVersion.version_number))).scalars().all()
            assert [item.status for item in versions] == ["FAILED", "PROCESSING"]
            assert [item.version_number for item in versions] == [1, 2]
    asyncio.run(verify())


def test_lesson_draft_cannot_claim_a_knowledge_build(lesson_context):
    ctx = lesson_context
    async def verify():
        async with SessionFactory.begin() as session:
            lesson = await session.get(Lesson, ctx["lesson_id"])
            lesson.status = "DRAFT"
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as raised:
                await IngestionOrchestrator(session, ctx["storage"]).process_published_lesson(ctx["lesson_id"])
            assert (raised.value.code, raised.value.status_code) == ("INVALID_SOURCE_STATE", 409)
            assert (await session.execute(select(KnowledgeSource.id).where(
                KnowledgeSource.lesson_id == ctx["lesson_id"]))).scalar_one_or_none() is None
    asyncio.run(verify())


def test_concurrent_lesson_trigger_sees_durable_claim_before_snapshot(lesson_context, monkeypatch):
    ctx = lesson_context
    from app.ingestion import orchestrator as module
    original = module.create_lesson_snapshot
    entered, release = asyncio.Event(), asyncio.Event()
    snapshot_calls = 0
    async def pause_snapshot(session, lesson_id, storage):
        nonlocal snapshot_calls
        snapshot_calls += 1
        async with SessionFactory() as check:
            version = (await check.execute(select(KnowledgeVersion).join(KnowledgeSource).where(
                KnowledgeSource.lesson_id == lesson_id,
                KnowledgeVersion.status == "PROCESSING",
            ))).scalar_one()
            assert version.id
        entered.set()
        await release.wait()
        return await original(session, lesson_id, storage)
    monkeypatch.setattr(module, "create_lesson_snapshot", pause_snapshot)

    async def verify():
        first_session, second_session = SessionFactory(), SessionFactory()
        try:
            first = asyncio.create_task(IngestionOrchestrator(
                first_session, ctx["storage"]
            ).process_published_lesson(ctx["lesson_id"]))
            await entered.wait()
            with pytest.raises(ApplicationError) as raised:
                await IngestionOrchestrator(second_session, ctx["storage"]).process_published_lesson(ctx["lesson_id"])
            assert (raised.value.code, raised.value.status_code) == ("PROCESSING_ALREADY_IN_PROGRESS", 409)
            assert snapshot_calls == 1
            release.set()
            await first
        finally:
            release.set()
            await first_session.close()
            await second_session.close()
    asyncio.run(verify())


def test_lesson_publish_commits_before_ingestion_and_repeat_does_not_trigger_again(lesson_context, monkeypatch):
    ctx = lesson_context
    from app.admin import service as admin_service
    from app.ingestion import orchestrator as module
    monkeypatch.setattr("app.ingestion.storage.LocalFileStorage", lambda _root: ctx["storage"])
    async def set_draft():
        async with SessionFactory.begin() as session:
            lesson = await session.get(Lesson, ctx["lesson_id"])
            lesson.status = "DRAFT"
            lesson.published_at = None
    asyncio.run(set_draft())
    trigger_calls = 0
    async def verify_committed(session, lesson_id, storage):
        nonlocal trigger_calls
        trigger_calls += 1
        async with SessionFactory() as check:
            published = await check.get(Lesson, lesson_id)
            assert published.status == "PUBLISHED"
            assert published.published_at is not None
        return {"lesson_id": lesson_id}
    monkeypatch.setattr(module, "process_published_lesson", verify_committed)

    async def verify():
        async with SessionFactory() as session:
            result = await admin_service.lesson_transition(session, ctx["lesson_id"], "publish")
            assert result["status"] == "PUBLISHED"
            with pytest.raises(ApplicationError) as repeated:
                await admin_service.lesson_transition(session, ctx["lesson_id"], "publish")
            assert repeated.value.code == "INVALID_LIFECYCLE_TRANSITION"
            assert trigger_calls == 1
    asyncio.run(verify())
