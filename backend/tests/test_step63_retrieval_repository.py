import asyncio
from uuid import uuid4

from sqlalchemy import delete

from app.ai.retrieval.repository import load_candidate_metadata
from app.database.models import (
    Chunk, Document, KnowledgeSource, KnowledgeVersion, User,
)
from app.database.session import SessionFactory
from step62_test_support import step62_state


def test_candidate_hydration_joins_lesson_and_hsk_provenance(step62_state):
    async def run():
        source_id = await step62_state.create_source()
        version_id, chunk_ids = await step62_state.create_version(source_id)
        async with SessionFactory.begin() as session:
            chunk = await session.get(Chunk, chunk_ids[0])
            chunk.page_number = 3
            chunk.section = "Grammar"
            chunk.metadata_json = {"offset": 42}
        async with SessionFactory() as session:
            rows = await load_candidate_metadata(session, [chunk_ids[0]])
        assert len(rows) == 1
        row = rows[0]
        assert row.chunk_id == chunk_ids[0]
        assert row.knowledge_version_id == version_id
        assert row.knowledge_source_id == source_id
        assert row.source_type == "LESSON"
        assert row.source_lesson_id == step62_state.source_lessons[source_id]
        assert row.chunk_lesson_id == step62_state.source_lessons[source_id]
        assert row.document_title is None
        assert row.lesson_title == "Step 6.2 vector test"
        assert row.hsk_level_number is not None
        assert row.page_number == 3
        assert row.section == "Grammar"
        assert row.locator_metadata == {"offset": 42}

    asyncio.run(run())


def test_candidate_hydration_resolves_document_provenance():
    async def run():
        user_id, document_id, source_id = uuid4(), uuid4(), uuid4()
        version_id, chunk_id = uuid4(), uuid4()
        async with SessionFactory.begin() as session:
            session.add(User(
                id=user_id, email=f"step63-{user_id}@example.invalid",
                password_hash="test-only", full_name="Step 6.3 test", role="ADMIN",
            ))
            await session.flush()
            session.add(Document(
                id=document_id, original_filename="lesson.txt", file_type="TXT",
                storage_reference=f"step63/{document_id}", mime_type="text/plain",
                file_size_bytes=12, processing_status="UPLOADED", review_status="PENDING",
                uploaded_by=user_id, title="Document provenance title",
            ))
            await session.flush()
            session.add(KnowledgeSource(
                id=source_id, source_type="DOCUMENT", document_id=document_id,
            ))
            await session.flush()
            session.add(KnowledgeVersion(
                id=version_id, knowledge_source_id=source_id, version_number=1,
                status="ACTIVE",
            ))
            await session.flush()
            session.add(Chunk(
                id=chunk_id, knowledge_version_id=version_id,
                content="Document content", content_type="DOCUMENT_TEXT",
                chunk_index=7, token_count=3, content_hash=f"step63-{chunk_id}",
            ))
        try:
            async with SessionFactory() as session:
                rows = await load_candidate_metadata(session, [chunk_id])
            assert len(rows) == 1
            row = rows[0]
            assert row.source_type == "DOCUMENT"
            assert row.source_document_id == document_id
            assert row.source_lesson_id is None
            assert row.chunk_index == 7
            assert row.document_title == "Document provenance title"
            assert row.lesson_title is None
            assert row.hsk_level_number is None
        finally:
            async with SessionFactory.begin() as session:
                await session.execute(delete(Chunk).where(Chunk.id == chunk_id))
                await session.execute(delete(KnowledgeVersion).where(KnowledgeVersion.id == version_id))
                await session.execute(delete(KnowledgeSource).where(KnowledgeSource.id == source_id))
                await session.execute(delete(Document).where(Document.id == document_id))
                await session.execute(delete(User).where(User.id == user_id))

    asyncio.run(run())


def test_candidate_hydration_empty_ids_performs_no_rows():
    async def run():
        async with SessionFactory() as session:
            assert await load_candidate_metadata(session, []) == []

    asyncio.run(run())
