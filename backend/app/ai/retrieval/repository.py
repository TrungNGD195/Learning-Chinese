from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.retrieval.schemas import CandidateMetadata
from app.database.models import Chunk, Document, HSKLevel, KnowledgeSource, KnowledgeVersion, Lesson


async def load_candidate_metadata(
    session: AsyncSession, chunk_ids: Sequence[UUID]
) -> list[CandidateMetadata]:
    if not chunk_ids:
        return []
    statement = (
        select(
            Chunk.id.label("chunk_id"),
            Chunk.chunk_index,
            Chunk.content,
            Chunk.content_type,
            Chunk.knowledge_version_id,
            KnowledgeSource.id.label("knowledge_source_id"),
            KnowledgeSource.source_type,
            KnowledgeSource.document_id.label("source_document_id"),
            KnowledgeSource.lesson_id.label("source_lesson_id"),
            Chunk.lesson_id.label("chunk_lesson_id"),
            Document.title.label("document_title"),
            Lesson.title.label("lesson_title"),
            HSKLevel.level_number.label("hsk_level_number"),
            Chunk.page_number,
            Chunk.section,
            Chunk.metadata_json.label("locator_metadata"),
        )
        .join(KnowledgeVersion, KnowledgeVersion.id == Chunk.knowledge_version_id)
        .join(KnowledgeSource, KnowledgeSource.id == KnowledgeVersion.knowledge_source_id)
        .outerjoin(Document, Document.id == KnowledgeSource.document_id)
        .outerjoin(Lesson, Lesson.id == KnowledgeSource.lesson_id)
        .outerjoin(HSKLevel, HSKLevel.id == Lesson.hsk_level_id)
        .where(Chunk.id.in_(chunk_ids))
    )
    rows = (await session.execute(statement)).mappings().all()
    return [CandidateMetadata(**dict(row)) for row in rows]
