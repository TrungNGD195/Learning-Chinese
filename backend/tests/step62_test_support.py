import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import delete

from app.database.models import (
    Chunk, Embedding, EmbeddingProfile, HSKLevel, KnowledgeSource,
    KnowledgeVersion, Lesson,
)
from app.database.session import SessionFactory


class Step62State:
    def __init__(self):
        self.profile_ids = set()
        self.source_ids = set()
        self.version_ids = set()
        self.chunk_ids = set()
        self.lesson_ids = set()
        self.level_ids = set()
        self.source_lessons = {}

    async def create_profile(self, *, status="INACTIVE", dimensions=3):
        profile_id = uuid4()
        async with SessionFactory.begin() as session:
            session.add(EmbeddingProfile(
                id=profile_id, provider="LOCAL", provider_version="step62-test-provider",
                model_name=f"step62-test-{uuid4()}", model_version="step62-test-model",
                dimensions=dimensions, embedding_input_version="test-input-v1",
                normalize_embeddings=True, status=status,
            ))
        self.profile_ids.add(profile_id)
        return profile_id

    async def create_source(self):
        level_id, lesson_id, source_id = uuid4(), uuid4(), uuid4()
        number = 20_000_000 + level_id.int % 1_000_000
        async with SessionFactory.begin() as session:
            session.add(HSKLevel(id=level_id, level_number=number, order_index=number))
            await session.flush()
            session.add(Lesson(
                id=lesson_id, hsk_level_id=level_id, lesson_number=lesson_id.int % 1_000_000,
                title="Step 6.2 vector test", description="Disposable vector storage test source",
                status="PUBLISHED",
            ))
            await session.flush()
            session.add(KnowledgeSource(id=source_id, source_type="LESSON", lesson_id=lesson_id))
        self.level_ids.add(level_id)
        self.lesson_ids.add(lesson_id)
        self.source_ids.add(source_id)
        self.source_lessons[source_id] = lesson_id
        return source_id

    async def create_version(self, source_id, *, status="PROCESSING", profile_vectors=None,
                             vectors=None, version_number=1):
        profile_vectors = profile_vectors or {}
        vectors = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]] if vectors is None else vectors
        version_id = uuid4()
        chunk_ids = [uuid4() for _ in vectors]
        async with SessionFactory.begin() as session:
            session.add(KnowledgeVersion(
                id=version_id, knowledge_source_id=source_id,
                version_number=version_number, status=status,
            ))
            await session.flush()
            session.add_all([
                Chunk(
                    id=chunk_id, knowledge_version_id=version_id,
                    content=f"Vector test chunk {index}", content_type="LESSON_GENERAL",
                    chunk_index=index, token_count=4, lesson_id=self.source_lessons[source_id],
                    content_hash=f"step62-{version_id}-{index}",
                )
                for index, chunk_id in enumerate(chunk_ids)
            ])
            await session.flush()
            for profile_id, vectors_for_profile in profile_vectors.items():
                session.add_all([
                    Embedding(chunk_id=chunk_id, embedding_profile_id=profile_id, vector=vector)
                    for chunk_id, vector in zip(chunk_ids, vectors_for_profile, strict=False)
                ])
        self.version_ids.add(version_id)
        self.chunk_ids.update(chunk_ids)
        return version_id, chunk_ids

    async def cleanup(self):
        async with SessionFactory.begin() as session:
            if self.chunk_ids:
                await session.execute(delete(Embedding).where(Embedding.chunk_id.in_(self.chunk_ids)))
                await session.execute(delete(Chunk).where(Chunk.id.in_(self.chunk_ids)))
            if self.version_ids:
                await session.execute(delete(KnowledgeVersion).where(KnowledgeVersion.id.in_(self.version_ids)))
            if self.source_ids:
                await session.execute(delete(KnowledgeSource).where(KnowledgeSource.id.in_(self.source_ids)))
            if self.lesson_ids:
                await session.execute(delete(Lesson).where(Lesson.id.in_(self.lesson_ids)))
            if self.level_ids:
                await session.execute(delete(HSKLevel).where(HSKLevel.id.in_(self.level_ids)))
            if self.profile_ids:
                await session.execute(delete(Embedding).where(Embedding.embedding_profile_id.in_(self.profile_ids)))
                await session.execute(delete(EmbeddingProfile).where(EmbeddingProfile.id.in_(self.profile_ids)))


@pytest.fixture
def step62_state():
    state = Step62State()
    yield state
    asyncio.run(state.cleanup())
