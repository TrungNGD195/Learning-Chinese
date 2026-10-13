import asyncio
from io import BytesIO
import json
from uuid import uuid4

import pytest
from sqlalchemy import delete, event, select

from app.core.errors import ApplicationError
from app.database.models import (
    Chunk, Document, KnowledgeSource, KnowledgeVersion, ParsingRun,
    TransformationRun, User,
)
from app.database.session import SessionFactory
from app.ingestion.orchestrator import IngestionOrchestrator
from app.ingestion.transformation.models import TransformedDocument


class _MemoryBuffer(BytesIO):
    def close(self):
        self.saved_bytes = self.getvalue()
        super().close()


class MemoryStorage:
    def __init__(self):
        self.objects = {}
        self.temporary = {}

    def write_bytes(self, key, data):
        self.objects[key] = data

    def create_temp(self):
        key = f"tmp/{uuid4().hex}"
        handle = _MemoryBuffer()
        self.temporary[key] = handle
        return key, handle

    def write(self, handle, data):
        handle.write(data)

    def finalize(self, temp_key, storage_key):
        self.objects[storage_key] = self.temporary.pop(temp_key).saved_bytes
        return storage_key

    def discard(self, temp_key):
        self.temporary.pop(temp_key, None)

    def delete(self, storage_key):
        self.objects.pop(storage_key, None)

    def open(self, storage_key):
        return BytesIO(self.objects[storage_key])

    def open_temp(self, temp_key):
        return BytesIO(self.temporary[temp_key].getvalue())


@pytest.fixture
def document_context():
    user_id, document_id = uuid4(), uuid4()
    storage = MemoryStorage()
    raw_key = f"documents/{document_id}/raw.txt"
    raw = b"Chinese learning begins with clear, structured examples."
    storage.write_bytes(raw_key, raw)

    async def setup():
        async with SessionFactory.begin() as session:
            session.add(User(id=user_id, email=f"step56-doc-{user_id}@example.invalid",
                             password_hash="test-only", full_name="Step 5.6 Admin", role="ADMIN"))
            await session.flush()
            session.add(Document(
                id=document_id, original_filename="lesson.txt", file_type="TXT",
                storage_reference=raw_key, mime_type="text/plain", file_size_bytes=len(raw),
                content_hash=__import__("hashlib").sha256(raw).hexdigest(),
                title="Chinese basics", source_category="CURRICULUM_MATERIAL",
                source_origin="Test source", source_language="en", usage_rights_note="Test only",
                processing_status="UPLOADED", review_status="PENDING", uploaded_by=user_id,
            ))
    asyncio.run(setup())
    context = {"user_id": user_id, "document_id": document_id, "storage": storage}
    yield context

    async def cleanup():
        async with SessionFactory.begin() as session:
            source_ids = select(KnowledgeSource.id).where(KnowledgeSource.document_id == document_id)
            version_ids = select(KnowledgeVersion.id).where(KnowledgeVersion.knowledge_source_id.in_(source_ids))
            await session.execute(delete(Chunk).where(Chunk.knowledge_version_id.in_(version_ids)))
            await session.execute(delete(KnowledgeVersion).where(KnowledgeVersion.knowledge_source_id.in_(source_ids)))
            await session.execute(delete(KnowledgeSource).where(KnowledgeSource.document_id == document_id))
            await session.execute(delete(TransformationRun).where(TransformationRun.document_id == document_id))
            await session.execute(delete(ParsingRun).where(ParsingRun.document_id == document_id))
            await session.execute(delete(Document).where(Document.id == document_id))
            await session.execute(delete(User).where(User.id == user_id))
    asyncio.run(cleanup())


def test_document_process_pins_exact_preview_approval_artifact_and_builds_chunks(document_context):
    ctx = document_context
    pinned_ids = []

    async def verify():
        async with SessionFactory() as session:
            orchestration = IngestionOrchestrator(session, ctx["storage"])
            await orchestration.process_document(ctx["document_id"])
            first_preview = await orchestration.preview_document(ctx["document_id"])
            document = await session.get(Document, ctx["document_id"])
            pinned = document.review_transformation_run_id
            assert document.approved_transformation_run_id is None
            assert document.processing_status == "PREVIEW_READY"
            run = await session.get(TransformationRun, pinned)
            assert run.status == "SUCCEEDED"
            assert run.transformed_storage_reference

            # A later successful run exists, but is not the review artifact.
            alternate = first_preview.model_copy(update={"title": "Unpinned newer artifact"})
            alternate_key = f"transformed/documents/{ctx['document_id']}/newer.json"
            ctx["storage"].write_bytes(
                alternate_key,
                json.dumps(alternate.model_dump(mode="json"), ensure_ascii=False).encode(),
            )
            parse_id = (await session.execute(select(ParsingRun.id).where(
                ParsingRun.document_id == ctx["document_id"], ParsingRun.status == "SUCCEEDED"
            ))).scalar_one()
            await session.rollback()
            async with session.begin():
                session.add(TransformationRun(
                    source_type="DOCUMENT", document_id=ctx["document_id"], parsing_run_id=parse_id,
                    parsed_storage_reference="parsed/unrelated-but-valid.json",
                    transformation_strategy="canonical_document", transformation_version="v1",
                    status="SUCCEEDED", transformed_storage_reference=alternate_key,
                    source_metadata_snapshot={"source_type": "DOCUMENT"},
                ))
            preview = await orchestration.preview_document(ctx["document_id"])
            assert preview.title == first_preview.title

            from app.ingestion import orchestrator as module
            original = module.build_chunks
            async def capture(ref, version_id, **kwargs):
                pinned_ids.append(ref.transformation_run_id)
                return await original(ref, version_id, **kwargs)
            module.build_chunks = capture
            try:
                result = await orchestration.approve_document(ctx["document_id"], ctx["user_id"])
            finally:
                module.build_chunks = original
            assert result["review_status"] == "APPROVED"
            assert pinned_ids == [pinned]
            document = await session.get(Document, ctx["document_id"])
            version = await session.get(KnowledgeVersion, result["knowledge_version_id"])
            chunks = (await session.execute(select(Chunk).where(
                Chunk.knowledge_version_id == version.id))).scalars().all()
            assert document.review_transformation_run_id == pinned
            assert document.approved_transformation_run_id == pinned
            assert document.review_status == "APPROVED"
            assert version.status == "PROCESSING"
            assert version.transformation_run_id == pinned
            assert chunks
            assert chunks[0].content in "\n".join(block.text for block in preview.blocks)
            with pytest.raises(ApplicationError) as duplicate:
                await orchestration.approve_document(ctx["document_id"], ctx["user_id"])
            assert duplicate.value.code == "DOCUMENT_ALREADY_APPROVED"

    asyncio.run(verify())


def test_document_approval_commits_before_build_failure_and_retry_uses_pinned_ref(document_context, monkeypatch):
    ctx = document_context

    async def verify():
        async with SessionFactory() as session:
            orchestration = IngestionOrchestrator(session, ctx["storage"])
            await orchestration.process_document(ctx["document_id"])
            document = await session.get(Document, ctx["document_id"])
            pinned = document.review_transformation_run_id
            source = KnowledgeSource(source_type="DOCUMENT", document_id=ctx["document_id"])
            session.add(source)
            await session.flush()
            active = KnowledgeVersion(knowledge_source_id=source.id, version_number=1, status="ACTIVE")
            session.add(active)
            await session.flush()
            active_id = active.id
            session.add(Chunk(
                knowledge_version_id=active.id, content="old active chunk", content_type="DOCUMENT_TEXT",
                chunk_index=0, metadata_json={},
            ))
            await session.commit()

            from app.ingestion import orchestrator as module
            original = module.build_chunks
            calls = 0
            async def fail_first(ref, version_id, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 1:
                    assert ref.transformation_run_id == pinned
                    raise ApplicationError("CHUNKING_FAILED", "private detail", status_code=500)
                return await original(ref, version_id, **kwargs)
            monkeypatch.setattr(module, "build_chunks", fail_first)
            with pytest.raises(ApplicationError) as failed:
                await orchestration.approve_document(ctx["document_id"], ctx["user_id"])
            assert (failed.value.code, failed.value.status_code) == ("KNOWLEDGE_BUILD_FAILED", 500)
            assert "private detail" not in str(failed.value)
            document = await session.get(Document, ctx["document_id"])
            assert document.review_status == "APPROVED"
            assert document.approved_transformation_run_id == pinned
            assert document.approved_by == ctx["user_id"] and document.approved_at is not None
            versions = (await session.execute(select(KnowledgeVersion).where(
                KnowledgeVersion.knowledge_source_id == source.id).order_by(KnowledgeVersion.version_number))).scalars().all()
            assert [version.status for version in versions] == ["ACTIVE", "FAILED"]
            failed_id = versions[-1].id
            old_chunks = (await session.execute(select(Chunk.content).where(
                Chunk.knowledge_version_id == active_id))).scalars().all()
            assert old_chunks == ["old active chunk"]

            async def unexpected(*_args, **_kwargs):
                raise AssertionError("knowledge retry must not parse or transform")
            monkeypatch.setattr(module, "parse_raw_artifact", unexpected)
            monkeypatch.setattr(module, "transform_parsed_artifact", unexpected)
            retried = await orchestration.retry_document_knowledge(ctx["document_id"])
            assert retried["knowledge_version_id"] != failed_id
            retried_version = await session.get(KnowledgeVersion, retried["knowledge_version_id"])
            assert retried_version.version_number == 3
            assert retried_version.status == "PROCESSING"
            assert retried_version.transformation_run_id == pinned
            assert await session.get(KnowledgeVersion, active_id) is not None

    asyncio.run(verify())


def test_document_parse_failure_is_fail_fast_and_failed_document_can_retry(document_context, monkeypatch):
    ctx = document_context
    from app.ingestion import orchestrator as module
    original_parse = module.parse_raw_artifact
    original_transform = module.transform_parsed_artifact
    transformed_called = False

    async def fail_parse(*_args, **_kwargs):
        raise ApplicationError("PARSING_FAILED", "private parser detail", status_code=422)
    async def transform(*_args, **_kwargs):
        nonlocal transformed_called
        transformed_called = True
    monkeypatch.setattr(module, "parse_raw_artifact", fail_parse)
    monkeypatch.setattr(module, "transform_parsed_artifact", transform)

    async def fail_then_recover():
        async with SessionFactory() as session:
            orchestration = IngestionOrchestrator(session, ctx["storage"])
            with pytest.raises(ApplicationError) as raised:
                await orchestration.process_document(ctx["document_id"])
            assert (raised.value.code, raised.value.status_code) == ("INGESTION_PROCESSING_FAILED", 500)
            assert "private parser detail" not in str(raised.value)
            document = await session.get(Document, ctx["document_id"])
            assert (document.processing_status, document.review_transformation_run_id) == ("FAILED", None)
            assert transformed_called is False
            monkeypatch.setattr(module, "parse_raw_artifact", original_parse)
            monkeypatch.setattr(module, "transform_parsed_artifact", original_transform)
            await orchestration.process_document(ctx["document_id"])
            retried = await session.get(Document, ctx["document_id"])
            assert retried.processing_status == "PREVIEW_READY"
            assert retried.review_transformation_run_id is not None

    asyncio.run(fail_then_recover())


def test_legacy_raw_metadata_failure_is_safe_and_persists_failed_claim(
    document_context, monkeypatch, caplog,
):
    ctx = document_context
    from app.ingestion import orchestrator as module
    stage_calls = {"parse": 0, "transform": 0, "chunk": 0}

    async def record_parse(*_args, **_kwargs):
        stage_calls["parse"] += 1

    async def record_transform(*_args, **_kwargs):
        stage_calls["transform"] += 1

    async def record_chunk(*_args, **_kwargs):
        stage_calls["chunk"] += 1

    monkeypatch.setattr(module, "parse_raw_artifact", record_parse)
    monkeypatch.setattr(module, "transform_parsed_artifact", record_transform)
    monkeypatch.setattr(module, "build_chunks", record_chunk)
    caplog.set_level("INFO", logger="app.ingestion.orchestrator")

    async def verify():
        async with SessionFactory.begin() as session:
            document = await session.get(Document, ctx["document_id"])
            document.mime_type = None
            document.file_size_bytes = None
            document.content_hash = None

        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as raised:
                await IngestionOrchestrator(session, ctx["storage"]).process_document(
                    ctx["document_id"]
                )
            assert (raised.value.code, raised.value.status_code) == (
                "INGESTION_PROCESSING_FAILED", 500
            )
            client_error = str(raised.value)
            assert all(field not in client_error for field in (
                "mime_type", "file_size_bytes", "content_hash", "ValidationError",
            ))

        # Read through a separate session after the use case has failed.
        async with SessionFactory() as independent_session:
            persisted = await independent_session.get(Document, ctx["document_id"])
            assert persisted.processing_status == "FAILED"
            assert persisted.review_transformation_run_id is None

    asyncio.run(verify())
    assert stage_calls == {"parse": 0, "transform": 0, "chunk": 0}
    failure_records = [
        record for record in caplog.records
        if getattr(record, "source_id", None) == str(ctx["document_id"])
        and getattr(record, "stage", None) == "raw"
        and getattr(record, "status", None) == "FAILED"
    ]
    assert len(failure_records) == 1
    record = failure_records[0]
    assert record.source_type == "DOCUMENT"
    assert record.error_code == "INGESTION_PROCESSING_FAILED"
    assert isinstance(record.duration_ms, (int, float))
    assert all(field not in record.getMessage() for field in (
        "mime_type", "file_size_bytes", "content_hash", "ValidationError",
    ))


def test_document_preview_ready_and_review_pointer_commit_atomically(document_context):
    ctx = document_context
    def reject_successful_pointer(mapper, connection, document):
        if document.processing_status == "PREVIEW_READY" and document.review_transformation_run_id is not None:
            raise RuntimeError("injected final persistence failure")
    event.listen(Document, "before_update", reject_successful_pointer)
    async def verify():
        async with SessionFactory() as session:
            orchestration = IngestionOrchestrator(session, ctx["storage"])
            with pytest.raises(ApplicationError) as failed:
                await orchestration.process_document(ctx["document_id"])
            assert failed.value.code == "INGESTION_PROCESSING_FAILED"
            document = await session.get(Document, ctx["document_id"])
            assert document.processing_status == "FAILED"
            assert document.review_transformation_run_id is None
            runs = (await session.execute(select(TransformationRun).where(
                TransformationRun.document_id == ctx["document_id"]))).scalars().all()
            assert runs and all(run.status != "SUCCEEDED" for run in runs)
    try:
        asyncio.run(verify())
    finally:
        event.remove(Document, "before_update", reject_successful_pointer)


def test_document_rejection_is_terminal_and_creates_no_knowledge_source(document_context):
    ctx = document_context
    async def verify():
        async with SessionFactory() as session:
            orchestration = IngestionOrchestrator(session, ctx["storage"])
            await orchestration.process_document(ctx["document_id"])
            pointer = (await session.get(Document, ctx["document_id"])).review_transformation_run_id
            await orchestration.reject_document(ctx["document_id"])
            document = await session.get(Document, ctx["document_id"])
            assert document.review_status == "REJECTED"
            assert document.review_transformation_run_id == pointer
            assert (await session.execute(select(KnowledgeSource.id).where(
                KnowledgeSource.document_id == ctx["document_id"]))).scalar_one_or_none() is None
            with pytest.raises(ApplicationError) as repeated:
                await orchestration.reject_document(ctx["document_id"])
            assert repeated.value.code == "INVALID_SOURCE_STATE"
    asyncio.run(verify())


def test_document_transform_failure_keeps_parsed_artifact_and_stops_before_chunking(document_context):
    ctx = document_context
    async def verify():
        async with SessionFactory.begin() as session:
            document = await session.get(Document, ctx["document_id"])
            document.source_origin = None
        from app.ingestion import orchestrator as module
        async def unexpected(*_args, **_kwargs):
            raise AssertionError("Document processing must not chunk before approval")
        original = module.build_chunks
        module.build_chunks = unexpected
        try:
            async with SessionFactory() as session:
                orchestration = IngestionOrchestrator(session, ctx["storage"])
                with pytest.raises(ApplicationError) as failed:
                    await orchestration.process_document(ctx["document_id"])
                assert failed.value.code == "INGESTION_PROCESSING_FAILED"
                document = await session.get(Document, ctx["document_id"])
                assert (document.processing_status, document.review_transformation_run_id) == ("FAILED", None)
                parse_run = (await session.execute(select(ParsingRun).where(
                    ParsingRun.document_id == ctx["document_id"]))).scalar_one()
                transform_run = (await session.execute(select(TransformationRun).where(
                    TransformationRun.document_id == ctx["document_id"]))).scalar_one()
                assert parse_run.status == "SUCCEEDED"
                assert transform_run.status == "FAILED"
        finally:
            module.build_chunks = original
    asyncio.run(verify())


def test_document_preview_requires_a_ready_pinned_run(document_context):
    ctx = document_context
    async def verify():
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as raised:
                await IngestionOrchestrator(session, ctx["storage"]).preview_document(ctx["document_id"])
            assert (raised.value.code, raised.value.status_code) == ("DOCUMENT_NOT_PREVIEW_READY", 409)
    asyncio.run(verify())
