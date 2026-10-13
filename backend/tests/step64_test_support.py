from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import delete

from step62_test_support import Step62State
from app.database.models import (
    Chunk, Document, Embedding, HSKLevel, KnowledgeSource, KnowledgeVersion, Lesson, User,
)
from app.database.session import SessionFactory
from step63_test_support import create_profile, make_identity


class Step64Corpus:
    def __init__(self, state):
        self.state = state
        self.profile_id = None
        self.identity = make_identity()
        self.documents = []
        self.users = []

    async def setup(self):
        self.profile_id = await create_profile(self.state, self.identity)
        return self

    async def create_lesson(
        self,
        *,
        vector,
        content="Lesson content",
        content_type="LESSON_GENERAL",
        chunk_lesson_id="source",
        version_status="ACTIVE",
        embedding_profile_id=None,
        hsk_level_number=None,
        hsk_level_id=None,
    ):
        source_id = await self.state.create_source()
        lesson_id = self.state.source_lessons[source_id]
        async with SessionFactory() as session:
            lesson_row = await session.get(Lesson, lesson_id)
            level_id = lesson_row.hsk_level_id
        profile_id = embedding_profile_id or self.profile_id
        version_id, chunk_ids = await self.state.create_version(
            source_id,
            status=version_status,
            vectors=[vector],
            profile_vectors={profile_id: [vector]},
        )
        chunk_id = chunk_ids[0]
        async with SessionFactory.begin() as session:
            chunk = await session.get(Chunk, chunk_id)
            chunk.content = content
            chunk.content_type = content_type
            chunk.lesson_id = lesson_id if chunk_lesson_id == "source" else chunk_lesson_id
            lesson_row = await session.get(Lesson, lesson_id)
            if hsk_level_id is not None:
                lesson_row.hsk_level_id = hsk_level_id
                level_id = hsk_level_id
            if hsk_level_number is not None:
                level = await session.get(HSKLevel, level_id)
                level.level_number = hsk_level_number
        return {
            "chunk_id": chunk_id,
            "source_id": source_id,
            "lesson_id": lesson_id,
            "level_id": level_id,
            "hsk_level_number": hsk_level_number,
            "version_id": version_id,
        }

    async def create_document(
        self,
        *,
        vector,
        category="CURRICULUM_MATERIAL",
        language="zh",
        content="Document knowledge",
        content_type="DOCUMENT_TEXT",
        version_status="ACTIVE",
        embedding_profile_id=None,
    ):
        user_id, document_id, source_id = uuid4(), uuid4(), uuid4()
        version_id, chunk_id = uuid4(), uuid4()
        profile_id = embedding_profile_id or self.profile_id
        now = datetime.now(timezone.utc)
        async with SessionFactory.begin() as session:
            session.add(User(
                id=user_id, email=f"step64-{user_id}@example.invalid",
                password_hash="test-only", full_name="Step 6.4 Admin", role="ADMIN",
            ))
            await session.flush()
            session.add(Document(
                id=document_id, original_filename=f"{document_id}.txt", file_type="TXT",
                storage_reference=f"step64/{document_id}", mime_type="text/plain",
                file_size_bytes=32, processing_status="PREVIEW_READY", review_status="APPROVED",
                uploaded_by=user_id, approved_by=user_id, approved_at=now,
                title=f"Step 6.4 document {document_id}", source_category=category,
                source_language=language,
            ))
            await session.flush()
            session.add(KnowledgeSource(
                id=source_id, source_type="DOCUMENT", document_id=document_id,
            ))
            await session.flush()
            session.add(KnowledgeVersion(
                id=version_id, knowledge_source_id=source_id, version_number=1,
                status=version_status,
            ))
            await session.flush()
            session.add(Chunk(
                id=chunk_id, knowledge_version_id=version_id, content=content,
                content_type=content_type, chunk_index=0, token_count=4,
                content_hash=f"step64-{chunk_id}",
            ))
            from app.database.models import Embedding
            await session.flush()
            session.add(Embedding(
                chunk_id=chunk_id, embedding_profile_id=profile_id, vector=vector,
            ))
        self.state.source_ids.add(source_id)
        self.state.version_ids.add(version_id)
        self.state.chunk_ids.add(chunk_id)
        self.documents.append(document_id)
        self.users.append(user_id)
        return {
            "chunk_id": chunk_id, "source_id": source_id, "document_id": document_id,
            "version_id": version_id,
        }

    async def add_profile_vector(self, chunk_id, profile_id, vector):
        async with SessionFactory.begin() as session:
            session.add(Embedding(
                chunk_id=chunk_id, embedding_profile_id=profile_id, vector=vector,
            ))

    async def cleanup_documents(self):
        # Remove the shared Step-6.2 fixture data first so Document foreign keys
        # are released; its own fixture teardown remains safely idempotent.
        await self.state.cleanup()
        async with SessionFactory.begin() as session:
            if self.documents:
                await session.execute(delete(Document).where(Document.id.in_(self.documents)))
            if self.users:
                await session.execute(delete(User).where(User.id.in_(self.users)))


@pytest.fixture
def step64_corpus():
    corpus = Step64Corpus(Step62State())
    import asyncio
    asyncio.run(corpus.setup())
    yield corpus
    import asyncio
    asyncio.run(corpus.cleanup_documents())
