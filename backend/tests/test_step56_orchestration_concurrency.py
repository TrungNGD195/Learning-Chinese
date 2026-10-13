import asyncio
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, event, select

from app import main
from app.core.errors import ApplicationError
from app.database.models import (
    Document, KnowledgeSource, KnowledgeVersion, ParsingRun, TransformationRun, User,
)
from app.database.session import SessionFactory
from app.ingestion.orchestrator import IngestionOrchestrator, _allocate_document_version


class _MemoryBuffer(BytesIO):
    def close(self):
        self.saved = self.getvalue()
        super().close()


class MemoryStorage:
    def __init__(self):
        self.objects = {}
        self.temporary = {}
    def write_bytes(self, key, value): self.objects[key] = value
    def open(self, key):
        from io import BytesIO
        return BytesIO(self.objects[key])
    def open_temp(self, key): return self.open(key)
    def create_temp(self):
        key = f"tmp/{uuid4().hex}"
        buffer = _MemoryBuffer()
        self.temporary[key] = buffer
        return key, buffer
    def write(self, handle, value): handle.write(value)
    def finalize(self, temp, target):
        self.objects[target] = self.temporary.pop(temp).saved
        return target
    def discard(self, temp): self.temporary.pop(temp, None)
    def delete(self, key): self.objects.pop(key, None)


async def _create_document(*, processing="UPLOADED"):
    user_id, document_id = uuid4(), uuid4()
    async with SessionFactory.begin() as session:
        session.add(User(id=user_id, email=f"step56-lock-{user_id}@example.invalid",
                         password_hash="unused", full_name="Step 5.6", role="ADMIN"))
        await session.flush()
        session.add(Document(
            id=document_id, original_filename="claim.txt", file_type="TXT", storage_reference="raw/claim.txt",
            mime_type="text/plain", file_size_bytes=5, content_hash=uuid4().hex,
            title="Claim fixture", source_category="INTERNAL_AUTHORED", source_origin="Test source",
            source_language="en",
            processing_status=processing, review_status="PENDING", uploaded_by=user_id,
        ))
    return user_id, document_id


async def _cleanup_document(user_id, document_id):
    async with SessionFactory.begin() as session:
        source_ids = select(KnowledgeSource.id).where(KnowledgeSource.document_id == document_id)
        await session.execute(delete(KnowledgeVersion).where(KnowledgeVersion.knowledge_source_id.in_(source_ids)))
        await session.execute(delete(KnowledgeSource).where(KnowledgeSource.document_id == document_id))
        await session.execute(delete(TransformationRun).where(TransformationRun.document_id == document_id))
        await session.execute(delete(ParsingRun).where(ParsingRun.document_id == document_id))
        await session.execute(delete(Document).where(Document.id == document_id))
        await session.execute(delete(User).where(User.id == user_id))


def test_document_process_claim_is_committed_before_parse_and_rejects_concurrent_trigger(monkeypatch, caplog):
    from app.ingestion import orchestrator as module
    user_id, document_id = asyncio.run(_create_document())
    storage = MemoryStorage()
    caplog.set_level("INFO", logger="app.ingestion.orchestrator")
    storage.write_bytes("raw/claim.txt", b"Visible during claim")
    entered, release = asyncio.Event(), asyncio.Event()
    original = module.parse_raw_artifact
    original_raw_ref = module.raw_service.document_raw_artifact_ref
    first_session = None
    claim_committed = False

    def record_commit(_session):
        nonlocal claim_committed
        claim_committed = True

    def verify_claim_before_raw_ref(document):
        assert claim_committed, "PROCESSING claim must commit before RawArtifactRef construction"
        assert document.processing_status == "PROCESSING"
        assert document.review_transformation_run_id is None
        return original_raw_ref(document)

    monkeypatch.setattr(
        module.raw_service, "document_raw_artifact_ref", verify_claim_before_raw_ref
    )

    async def pause_after_claim(raw_ref, **kwargs):
        async with SessionFactory() as check:
            document = await check.get(Document, document_id)
            assert document.processing_status == "PROCESSING"
            assert document.review_transformation_run_id is None
        entered.set()
        await release.wait()
        return await original(raw_ref, **kwargs)
    monkeypatch.setattr(module, "parse_raw_artifact", pause_after_claim)

    async def verify():
        nonlocal first_session
        first_session = SessionFactory()
        second_session = SessionFactory()
        event.listen(first_session.sync_session, "after_commit", record_commit)
        try:
            first = asyncio.create_task(IngestionOrchestrator(first_session, storage).process_document(document_id))
            await entered.wait()
            with pytest.raises(ApplicationError) as raised:
                await IngestionOrchestrator(second_session, storage).process_document(document_id)
            assert (raised.value.code, raised.value.status_code) == ("PROCESSING_ALREADY_IN_PROGRESS", 409)
            release.set()
            await first
        finally:
            release.set()
            event.remove(first_session.sync_session, "after_commit", record_commit)
            await first_session.close()
            await second_session.close()
    try:
        asyncio.run(verify())
        records = [record for record in caplog.records if getattr(record, "stage", None) in {"parse", "transform"}]
        assert records
        assert all(hasattr(records[0], name) for name in (
            "source_id", "source_type", "stage", "status", "duration_ms",
        ))
    finally:
        asyncio.run(_cleanup_document(user_id, document_id))


def test_concurrent_document_source_create_and_version_claim_has_one_winner():
    user_id, document_id = asyncio.run(_create_document())
    async def verify():
        sessions = [SessionFactory(), SessionFactory()]
        try:
            results = await asyncio.gather(*(
                _allocate_document_version(session, document_id) for session in sessions
            ), return_exceptions=True)
            winners = [value for value in results if isinstance(value, type(uuid4()))]
            failures = [value for value in results if isinstance(value, ApplicationError)]
            assert len(winners) == 1
            assert len(failures) == 1
            assert failures[0].code == "PROCESSING_ALREADY_IN_PROGRESS"
            async with SessionFactory() as check:
                sources = (await check.execute(select(KnowledgeSource).where(
                    KnowledgeSource.document_id == document_id))).scalars().all()
                versions = (await check.execute(select(KnowledgeVersion).where(
                    KnowledgeVersion.knowledge_source_id == sources[0].id))).scalars().all()
                assert len(sources) == len(versions) == 1
                assert versions[0].status == "PROCESSING"
        finally:
            for session in sessions:
                await session.close()
    try:
        asyncio.run(verify())
    finally:
        asyncio.run(_cleanup_document(user_id, document_id))


def test_version_allocation_uses_source_lock_and_next_historical_number():
    user_id, document_id = asyncio.run(_create_document())
    source_id = uuid4()
    async def setup_history():
        async with SessionFactory.begin() as session:
            session.add(KnowledgeSource(id=source_id, source_type="DOCUMENT", document_id=document_id))
            await session.flush()
            session.add_all([
                KnowledgeVersion(knowledge_source_id=source_id, version_number=1, status="ACTIVE"),
                KnowledgeVersion(knowledge_source_id=source_id, version_number=2, status="FAILED"),
                KnowledgeVersion(knowledge_source_id=source_id, version_number=3, status="SUPERSEDED"),
            ])
    asyncio.run(setup_history())
    try:
        async def verify():
            async with SessionFactory() as session:
                version_id = await _allocate_document_version(session, document_id)
                version = await session.get(KnowledgeVersion, version_id)
                assert (version.version_number, version.status) == (4, "PROCESSING")
                history = (await session.execute(select(KnowledgeVersion.version_number, KnowledgeVersion.status)
                    .where(KnowledgeVersion.knowledge_source_id == source_id)
                    .order_by(KnowledgeVersion.version_number))).all()
                assert history == [(1, "ACTIVE"), (2, "FAILED"), (3, "SUPERSEDED"), (4, "PROCESSING")]
        asyncio.run(verify())
    finally:
        asyncio.run(_cleanup_document(user_id, document_id))


def test_admin_routes_remain_protected_and_no_stage_endpoints_are_exposed():
    schema = main.app.openapi()
    assert "/api/v1/admin/documents/{document_id}/process" in schema["paths"]
    assert "/api/v1/admin/documents/{document_id}/preview" in schema["paths"]
    assert "/api/v1/admin/documents/{document_id}/knowledge/retry" in schema["paths"]
    assert "/api/v1/admin/lessons/{lesson_id}/knowledge/retry" in schema["paths"]
    assert not any(path.endswith("/parse") or path.endswith("/transform") or path.endswith("/chunk")
                   for path in schema["paths"])
    with TestClient(main.app) as client:
        response = client.post(f"/api/v1/admin/documents/{uuid4()}/process")
        assert response.status_code == 401
