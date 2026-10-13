import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.core.config import get_settings


# The Step 3.1 app is imported during test collection, so select its safe test
# configuration before any test module imports app.main.
os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "false"
os.environ["APP_NAME"] = "Trung Chinese Learning API"
os.environ["API_V1_PREFIX"] = "/api/v1"
os.environ["CORS_ORIGINS"] = "http://test-origin.invalid"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["EMBEDDING_PROVIDER"] = "local"
os.environ["EMBEDDING_MODEL_NAME"] = "BAAI/bge-m3"
os.environ["EMBEDDING_MODEL_REVISION"] = "5617a9f61b028005a4858fdac845db406aefb181"
os.environ["EMBEDDING_DEVICE"] = "auto"
os.environ["EMBEDDING_BATCH_SIZE"] = "32"
os.environ["EMBEDDING_INPUT_VERSION"] = "v1"
os.environ["EMBEDDING_NORMALIZE"] = "true"
os.environ["SECRET_KEY"] = "test-only-signing-key-not-a-deployment-secret-0123456789"

# Integration tests are allowed to use only the explicitly dedicated database.
# Settings reads backend/.env without exposing the configured DSN.
_test_settings = get_settings()
from sqlalchemy.engine import make_url

if _test_settings.app_env != "test":
    raise RuntimeError("Database tests require APP_ENV=test")
if make_url(_test_settings.effective_database_url).database != "chinese_learning_test":
    raise RuntimeError("Database tests require the dedicated chinese_learning_test database")
if _test_settings.database_url and (
    make_url(_test_settings.database_url).database
    == make_url(_test_settings.effective_database_url).database
):
    raise RuntimeError("Test database must differ from DATABASE_URL")
get_settings.cache_clear()

from app.auth.current_user import get_current_user
from app.database.models import (
    Chunk, Document, Embedding, HSKLevel, KnowledgeSource, KnowledgeVersion, Lesson,
    ParsingRun, TransformationRun, User,
)
from app.database.session import SessionFactory
from app.main import app


class _Step57Buffer(__import__("io").BytesIO):
    def close(self):
        self.saved_bytes = self.getvalue()
        super().close()


class _Step57MemoryStorage:
    def __init__(self):
        self.objects = {}
        self.temporary = {}

    def write_bytes(self, key, data):
        self.objects[key] = data

    def create_temp(self):
        from uuid import uuid4
        key = f"tmp/{uuid4().hex}"
        handle = _Step57Buffer()
        self.temporary[key] = handle
        return key, handle

    def write(self, handle, data): handle.write(data)
    def finalize(self, temp_key, storage_key):
        self.objects[storage_key] = self.temporary.pop(temp_key).saved_bytes
        return storage_key
    def discard(self, temp_key): self.temporary.pop(temp_key, None)
    def delete(self, storage_key): self.objects.pop(storage_key, None)

    def open(self, storage_key):
        from io import BytesIO
        try:
            return BytesIO(self.objects[storage_key])
        except KeyError as exc:
            raise FileNotFoundError(storage_key) from exc

    def open_temp(self, temp_key):
        from io import BytesIO
        return BytesIO(self.temporary[temp_key].getvalue())


@pytest.fixture
def step57_document():
    from hashlib import sha256
    from uuid import uuid4

    user_id, document_id = uuid4(), uuid4()
    storage = _Step57MemoryStorage()
    raw_key = f"step57/documents/{document_id}/raw.txt"
    raw = b"Step 5.7 incremental reprocessing baseline with a stable paragraph."
    content_hash = sha256(raw).hexdigest()
    storage.write_bytes(raw_key, raw)

    async def setup():
        async with SessionFactory.begin() as session:
            session.add(User(id=user_id, email=f"step57-{user_id}@example.invalid",
                             password_hash="test-only", full_name="Step 5.7 Admin", role="ADMIN"))
            await session.flush()
            session.add(Document(
                id=document_id, original_filename="source.txt", file_type="TXT",
                storage_reference=raw_key, mime_type="text/plain", file_size_bytes=len(raw),
                content_hash=content_hash, title="Step 5.7 source",
                source_category="CURRICULUM_MATERIAL", source_origin="test fixture",
                source_language="en", usage_rights_note="test only",
                processing_status="UPLOADED", review_status="PENDING", uploaded_by=user_id,
            ))
    asyncio.run(setup())

    async def prepare_approved():
        from app.ingestion.orchestrator import IngestionOrchestrator
        async with SessionFactory() as session:
            orchestration = IngestionOrchestrator(session, storage)
            await orchestration.process_document(document_id)
            result = await orchestration.approve_document(document_id, user_id)
        async with SessionFactory.begin() as session:
            version = await session.get(KnowledgeVersion, result["knowledge_version_id"])
            version.status = "ACTIVE"
        return result

    context = {"user_id": user_id, "source_id": document_id, "storage": storage,
               "content_hash": content_hash, "raw_key": raw_key,
               "prepare_approved": prepare_approved}
    yield context

    async def cleanup():
        async with SessionFactory.begin() as session:
            source_ids = select(KnowledgeSource.id).where(KnowledgeSource.document_id == document_id)
            version_ids = select(KnowledgeVersion.id).where(KnowledgeVersion.knowledge_source_id.in_(source_ids))
            chunk_ids = select(Chunk.id).where(Chunk.knowledge_version_id.in_(version_ids))
            await session.execute(delete(Embedding).where(Embedding.chunk_id.in_(chunk_ids)))
            await session.execute(delete(Chunk).where(Chunk.knowledge_version_id.in_(version_ids)))
            await session.execute(delete(KnowledgeVersion).where(KnowledgeVersion.knowledge_source_id.in_(source_ids)))
            await session.execute(delete(KnowledgeSource).where(KnowledgeSource.document_id == document_id))
            await session.execute(delete(TransformationRun).where(TransformationRun.document_id == document_id))
            await session.execute(delete(ParsingRun).where(ParsingRun.document_id == document_id))
            await session.execute(delete(Document).where(Document.id == document_id))
            await session.execute(delete(User).where(User.id == user_id))
    asyncio.run(cleanup())


@pytest.fixture
def step57_lesson():
    from uuid import uuid4

    level_id, lesson_id = uuid4(), uuid4()
    hsk_number = 3_000_000 + level_id.int % 1_000_000
    storage = _Step57MemoryStorage()

    async def setup():
        async with SessionFactory.begin() as session:
            session.add(HSKLevel(id=level_id, level_number=hsk_number, order_index=hsk_number))
            await session.flush()
            session.add(Lesson(
                id=lesson_id, hsk_level_id=level_id, lesson_number=900000 + lesson_id.int % 100000,
                title="Step 5.7 Lesson", description="A stable description for chunk planning.",
                status="PUBLISHED",
            ))
    asyncio.run(setup())

    async def prepare_active():
        from app.ingestion.orchestrator import IngestionOrchestrator
        async with SessionFactory() as session:
            result = await IngestionOrchestrator(session, storage).process_published_lesson(lesson_id)
        async with SessionFactory.begin() as session:
            version = await session.get(KnowledgeVersion, result["knowledge_version_id"])
            version.status = "ACTIVE"
        return result

    context = {"source_id": lesson_id, "level_id": level_id, "storage": storage,
               "prepare_active": prepare_active}
    yield context

    async def cleanup():
        async with SessionFactory.begin() as session:
            source_ids = select(KnowledgeSource.id).where(KnowledgeSource.lesson_id == lesson_id)
            version_ids = select(KnowledgeVersion.id).where(KnowledgeVersion.knowledge_source_id.in_(source_ids))
            chunk_ids = select(Chunk.id).where(Chunk.knowledge_version_id.in_(version_ids))
            await session.execute(delete(Embedding).where(Embedding.chunk_id.in_(chunk_ids)))
            await session.execute(delete(Chunk).where(Chunk.knowledge_version_id.in_(version_ids)))
            await session.execute(delete(KnowledgeVersion).where(KnowledgeVersion.knowledge_source_id.in_(source_ids)))
            await session.execute(delete(KnowledgeSource).where(KnowledgeSource.lesson_id == lesson_id))
            await session.execute(delete(TransformationRun).where(TransformationRun.lesson_id == lesson_id))
            await session.execute(delete(ParsingRun).where(ParsingRun.lesson_id == lesson_id))
            await session.execute(delete(Lesson).where(Lesson.id == lesson_id))
            await session.execute(delete(HSKLevel).where(HSKLevel.id == level_id))
    asyncio.run(cleanup())


@pytest.fixture(autouse=True)
def clear_cached_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def persisted_admin_override():
    user_id = uuid4()
    email = f"test-admin-{user_id}@example.invalid"
    async def setup():
        async with SessionFactory.begin() as session:
            session.add(User(id=user_id, email=email, password_hash="test-only", full_name="Test Admin", role="ADMIN"))
    asyncio.run(setup())
    async def current_user():
        async with SessionFactory() as session:
            return await session.get(User, user_id)
    app.dependency_overrides[get_current_user] = current_user
    yield user_id
    app.dependency_overrides.pop(get_current_user, None)
    async def cleanup():
        async with SessionFactory.begin() as session:
            await session.execute(delete(User).where(User.id == user_id))
    asyncio.run(cleanup())
