from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.retrieval.filters import RetrievalFilter
from app.ai.vector_storage.schemas import NearestVectorResult
from app.database.models import (
    Chunk, Document, Embedding, EmbeddingProfile, HSKLevel, KnowledgeSource,
    KnowledgeVersion, Lesson,
)


async def count_required_chunks(session: AsyncSession, version_id):
    return int(await session.scalar(select(func.count()).select_from(Chunk).where(
        Chunk.knowledge_version_id == version_id
    )) or 0)


async def count_embeddings_for_version_profile(session: AsyncSession, version_id, profile_id):
    return int(await session.scalar(
        select(func.count()).select_from(Embedding)
        .join(Chunk, Chunk.id == Embedding.chunk_id)
        .where(Chunk.knowledge_version_id == version_id, Embedding.embedding_profile_id == profile_id)
    ) or 0)


async def count_invalid_vector_dimensions(session: AsyncSession, version_id, profile_id, expected_dimensions: int):
    return int(await session.scalar(
        select(func.count()).select_from(Embedding)
        .join(Chunk, Chunk.id == Embedding.chunk_id)
        .where(
            Chunk.knowledge_version_id == version_id,
            Embedding.embedding_profile_id == profile_id,
            func.vector_dims(Embedding.vector) != expected_dimensions,
        )
    ) or 0)


async def select_probe_embedding(session: AsyncSession, version_id, profile_id):
    return (await session.execute(
        select(Embedding.vector, Embedding.id, Chunk.id.label("chunk_id"))
        .join(Chunk, Chunk.id == Embedding.chunk_id)
        .where(Chunk.knowledge_version_id == version_id,
               Embedding.embedding_profile_id == profile_id)
        .order_by(Chunk.chunk_index.asc(), Embedding.id.asc())
        .limit(1)
    )).one_or_none()


async def run_candidate_probe(session: AsyncSession, version_id, profile_id, probe_vector):
    distance = Embedding.vector.cosine_distance(probe_vector)
    return (await session.execute(
        select(Embedding.id, Embedding.embedding_profile_id, Chunk.id.label("chunk_id"),
               Chunk.knowledge_version_id.label("knowledge_version_id"),
               distance.label("distance"), Embedding.vector)
        .join(Chunk, Chunk.id == Embedding.chunk_id)
        .where(Chunk.knowledge_version_id == version_id,
               Embedding.embedding_profile_id == profile_id)
        .order_by(distance.asc(), Chunk.id.asc())
        .limit(1)
    )).one_or_none()


async def get_profile(session: AsyncSession, profile_id):
    return await session.get(EmbeddingProfile, profile_id)


async def list_profiles(session: AsyncSession):
    return list((await session.scalars(
        select(EmbeddingProfile).order_by(EmbeddingProfile.id.asc())
    )).all())


async def lock_all_profiles(session: AsyncSession):
    return list((await session.scalars(
        select(EmbeddingProfile).order_by(EmbeddingProfile.id.asc()).with_for_update()
        .execution_options(populate_existing=True)
    )).all())


async def get_version_source_id(session: AsyncSession, version_id):
    return await session.scalar(select(KnowledgeVersion.knowledge_source_id).where(
        KnowledgeVersion.id == version_id
    ))


async def get_version(session: AsyncSession, version_id):
    return await session.get(KnowledgeVersion, version_id)


async def lock_source(session: AsyncSession, source_id):
    return await session.scalar(
        select(KnowledgeSource).where(KnowledgeSource.id == source_id).with_for_update()
        .execution_options(populate_existing=True)
    )


async def lock_sources(session: AsyncSession):
    return list((await session.scalars(
        select(KnowledgeSource).order_by(KnowledgeSource.id.asc()).with_for_update()
        .execution_options(populate_existing=True)
    )).all())


async def lock_versions_for_sources(session: AsyncSession, source_ids, statuses):
    if not source_ids:
        return []
    return list((await session.scalars(
        select(KnowledgeVersion)
        .where(KnowledgeVersion.knowledge_source_id.in_(source_ids), KnowledgeVersion.status.in_(statuses))
        .order_by(KnowledgeVersion.id.asc()).with_for_update()
        .execution_options(populate_existing=True)
    )).all())


async def lock_active_sources_and_versions(session: AsyncSession):
    active_source_ids = select(KnowledgeVersion.knowledge_source_id).where(
        KnowledgeVersion.status == "ACTIVE"
    ).distinct()
    sources = list((await session.scalars(
        select(KnowledgeSource).where(KnowledgeSource.id.in_(active_source_ids))
        .order_by(KnowledgeSource.id.asc()).with_for_update()
        .execution_options(populate_existing=True)
    )).all())
    versions = list((await session.scalars(
        select(KnowledgeVersion).where(KnowledgeVersion.status == "ACTIVE")
        .order_by(KnowledgeVersion.id.asc()).with_for_update()
        .execution_options(populate_existing=True)
    )).all())
    return sources, versions


async def nearest_vectors(
    session: AsyncSession,
    query_vector,
    profile_id,
    limit: int,
    *,
    retrieval_filter: RetrievalFilter | None = None,
):
    distance = Embedding.vector.cosine_distance(query_vector)
    statement = (
        select(Chunk.id, distance.label("distance"))
        .join(Embedding, Embedding.chunk_id == Chunk.id)
        .join(KnowledgeVersion, KnowledgeVersion.id == Chunk.knowledge_version_id)
        .join(EmbeddingProfile, EmbeddingProfile.id == Embedding.embedding_profile_id)
        .where(
            Embedding.embedding_profile_id == profile_id,
            EmbeddingProfile.id == profile_id,
            EmbeddingProfile.status == "ACTIVE",
            KnowledgeVersion.status == "ACTIVE",
        )
    )

    if retrieval_filter is not None:
        retrieval_filter.validate()
        needs_source = any((
            retrieval_filter.lesson_ids is not None,
            retrieval_filter.hsk_levels is not None,
            retrieval_filter.source_types is not None,
            retrieval_filter.source_categories is not None,
            retrieval_filter.source_languages is not None,
        ))
        if needs_source:
            statement = statement.join(
                KnowledgeSource,
                KnowledgeSource.id == KnowledgeVersion.knowledge_source_id,
            )
        if retrieval_filter.hsk_levels is not None:
            statement = statement.join(Lesson, Lesson.id == KnowledgeSource.lesson_id).join(
                HSKLevel, HSKLevel.id == Lesson.hsk_level_id
            )
        if (
            retrieval_filter.source_categories is not None
            or retrieval_filter.source_languages is not None
        ):
            statement = statement.join(Document, Document.id == KnowledgeSource.document_id)

        predicates = []
        if retrieval_filter.lesson_ids is not None:
            predicates.append(KnowledgeSource.lesson_id.in_(sorted(retrieval_filter.lesson_ids, key=str)))
        if retrieval_filter.hsk_levels is not None:
            predicates.append(HSKLevel.level_number.in_(sorted(retrieval_filter.hsk_levels)))
        if retrieval_filter.content_types is not None:
            predicates.append(Chunk.content_type.in_(sorted(retrieval_filter.content_types)))
        if retrieval_filter.source_types is not None:
            predicates.append(KnowledgeSource.source_type.in_(sorted(retrieval_filter.source_types)))
        if retrieval_filter.source_categories is not None:
            predicates.append(Document.source_category.in_(sorted(retrieval_filter.source_categories)))
        if retrieval_filter.source_languages is not None:
            predicates.append(Document.source_language.in_(sorted(retrieval_filter.source_languages)))
        if predicates:
            statement = statement.where(*predicates)

    statement = statement.order_by(distance.asc(), Chunk.id.asc()).limit(limit)
    rows = (await session.execute(statement)).all()
    return [NearestVectorResult(chunk_id=row.id, distance=float(row.distance)) for row in rows]
