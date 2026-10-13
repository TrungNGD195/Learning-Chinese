from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.schemas import EmbeddingChunkContext, EmbeddingProfileIdentity
from app.database.models import (
    Chunk, Document, Embedding, EmbeddingProfile, HSKLevel, KnowledgeSource,
    KnowledgeVersion, Lesson,
)


def _identity_filter(identity: EmbeddingProfileIdentity):
    return (
        (EmbeddingProfile.provider == identity.provider)
        & (EmbeddingProfile.provider_version == identity.provider_version)
        & (EmbeddingProfile.model_name == identity.model_name)
        & (EmbeddingProfile.model_version == identity.model_version)
        & (EmbeddingProfile.dimensions == identity.dimensions)
        & (EmbeddingProfile.embedding_input_version == identity.embedding_input_version)
        & (EmbeddingProfile.normalize_embeddings == identity.normalize_embeddings)
    )


async def get_embedding_profile_by_identity(session: AsyncSession, identity: EmbeddingProfileIdentity):
    return await session.scalar(select(EmbeddingProfile).where(_identity_filter(identity)))


async def get_or_create_embedding_profile(session: AsyncSession, identity: EmbeddingProfileIdentity):
    existing = await get_embedding_profile_by_identity(session, identity)
    if existing is not None:
        return existing
    profile = EmbeddingProfile(
        provider=identity.provider, provider_version=identity.provider_version,
        model_name=identity.model_name, model_version=identity.model_version,
        dimensions=identity.dimensions, embedding_input_version=identity.embedding_input_version,
        normalize_embeddings=identity.normalize_embeddings, status="INACTIVE",
    )
    try:
        async with session.begin_nested():
            session.add(profile)
            await session.flush()
    except IntegrityError:
        existing = await get_embedding_profile_by_identity(session, identity)
        if existing is None:
            raise
        return existing
    return profile


async def get_version_and_source(session: AsyncSession, version_id):
    row = (await session.execute(
        select(KnowledgeVersion, KnowledgeSource)
        .join(KnowledgeSource, KnowledgeSource.id == KnowledgeVersion.knowledge_source_id)
        .where(KnowledgeVersion.id == version_id)
    )).one_or_none()
    return row


async def lock_version(session: AsyncSession, version_id):
    return await session.scalar(select(KnowledgeVersion).where(KnowledgeVersion.id == version_id)
                                .with_for_update().execution_options(populate_existing=True))


async def lock_source(session: AsyncSession, source_id):
    return await session.scalar(select(KnowledgeSource).where(KnowledgeSource.id == source_id).with_for_update())


async def find_processing_version(session: AsyncSession, source_id):
    return await session.scalar(select(KnowledgeVersion).where(
        KnowledgeVersion.knowledge_source_id == source_id,
        KnowledgeVersion.status == "PROCESSING",
    ))


async def count_required_chunks(session: AsyncSession, version_id) -> int:
    return int(await session.scalar(select(func.count()).select_from(Chunk).where(Chunk.knowledge_version_id == version_id)) or 0)


def _context_query():
    return (
        select(
            Chunk.id, Chunk.chunk_index, Chunk.content, Chunk.content_type, Chunk.section,
            KnowledgeSource.source_type, KnowledgeSource.document_id.label("source_document_id"),
            KnowledgeSource.lesson_id.label("source_lesson_id"), Chunk.lesson_id.label("chunk_lesson_id"),
            Document.title.label("document_title"), Lesson.id.label("lesson_id"),
            Lesson.title.label("lesson_title"), HSKLevel.level_number.label("hsk_level_number"),
        )
        .join(KnowledgeVersion, KnowledgeVersion.id == Chunk.knowledge_version_id)
        .join(KnowledgeSource, KnowledgeSource.id == KnowledgeVersion.knowledge_source_id)
        .outerjoin(Document, Document.id == KnowledgeSource.document_id)
        .outerjoin(Lesson, Lesson.id == KnowledgeSource.lesson_id)
        .outerjoin(HSKLevel, HSKLevel.id == Lesson.hsk_level_id)
    )


def _as_context(row) -> EmbeddingChunkContext:
    return EmbeddingChunkContext(
        chunk_id=row.id, chunk_index=row.chunk_index, content=row.content,
        content_type=row.content_type, section=row.section,
        document_title=row.document_title, lesson_id=row.lesson_id,
        lesson_title=row.lesson_title, hsk_level_number=row.hsk_level_number,
        source_type=row.source_type, source_document_id=row.source_document_id,
        source_lesson_id=row.source_lesson_id, chunk_lesson_id=row.chunk_lesson_id,
    )


async def list_chunk_contexts_for_version(session: AsyncSession, version_id):
    rows = (await session.execute(_context_query().where(
        Chunk.knowledge_version_id == version_id
    ).order_by(Chunk.chunk_index.asc()))).all()
    return [_as_context(row) for row in rows]


async def list_missing_chunk_contexts_for_profile(session: AsyncSession, version_id, profile_id, limit: int):
    rows = (await session.execute(
        _context_query()
        .outerjoin(Embedding, (Embedding.chunk_id == Chunk.id) & (Embedding.embedding_profile_id == profile_id))
        .where(Chunk.knowledge_version_id == version_id, Embedding.id.is_(None))
        .order_by(Chunk.chunk_index.asc())
        .limit(limit)
    )).all()
    return [_as_context(row) for row in rows]


async def list_existing_embedding_profile_ids_for_version(session: AsyncSession, version_id):
    return set((await session.scalars(
        select(Embedding.embedding_profile_id).join(Chunk, Chunk.id == Embedding.chunk_id)
        .where(Chunk.knowledge_version_id == version_id).distinct()
    )).all())


async def list_existing_embedding_chunk_ids(session: AsyncSession, profile_id, chunk_ids):
    if not chunk_ids:
        return set()
    return set((await session.scalars(select(Embedding.chunk_id).where(
        Embedding.embedding_profile_id == profile_id, Embedding.chunk_id.in_(chunk_ids)
    ))).all())


async def insert_embeddings_conflict_safe(session: AsyncSession, rows: list[dict]) -> int:
    if not rows:
        return 0
    statement = insert(Embedding).values(rows).on_conflict_do_nothing(
        constraint="uq_embeddings_chunk_id_embedding_profile_id"
    ).returning(Embedding.id)
    return len((await session.scalars(statement)).all())


async def count_embeddings_for_version_profile(session: AsyncSession, version_id, profile_id) -> int:
    value = await session.scalar(
        select(func.count()).select_from(Embedding)
        .join(Chunk, Chunk.id == Embedding.chunk_id)
        .where(Chunk.knowledge_version_id == version_id, Embedding.embedding_profile_id == profile_id)
    )
    return int(value or 0)


async def mark_version_failed(session: AsyncSession, version_id) -> bool:
    version = await lock_version(session, version_id)
    if version is None or version.status != "PROCESSING":
        return False
    version.status = "FAILED"
    await session.flush()
    return True


async def get_profile(session: AsyncSession, profile_id):
    return await session.get(EmbeddingProfile, profile_id)


async def get_version_source_for_update(session: AsyncSession, version_id):
    row = await get_version_and_source(session, version_id)
    if row is None:
        return None
    version, source = row
    locked_source = await lock_source(session, source.id)
    locked_version = await lock_version(session, version.id)
    return (locked_version, locked_source) if locked_version is not None and locked_source is not None else None
