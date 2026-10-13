from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Chunk, Document, KnowledgeSource, KnowledgeVersion, ParsingRun, TransformationRun


async def add_document(session: AsyncSession, values: dict) -> Document:
    document = Document(**values)
    session.add(document)
    await session.flush()
    return document


async def get_by_content_hash(session: AsyncSession, content_hash: str) -> Document | None:
    return await session.scalar(select(Document).where(Document.content_hash == content_hash))


async def add_parsing_run(session: AsyncSession, values: dict) -> ParsingRun:
    run = ParsingRun(**values)
    session.add(run)
    await session.flush()
    return run


async def get_parsing_run(session: AsyncSession, run_id) -> ParsingRun | None:
    return await session.get(ParsingRun, run_id)


async def add_transformation_run(session: AsyncSession, values: dict) -> TransformationRun:
    run = TransformationRun(**values)
    session.add(run)
    await session.flush()
    return run


async def get_transformation_run(session: AsyncSession, run_id) -> TransformationRun | None:
    return await session.get(TransformationRun, run_id)


async def get_knowledge_version_source(session: AsyncSession, version_id):
    result = await session.execute(
        select(KnowledgeVersion, KnowledgeSource)
        .join(KnowledgeSource, KnowledgeSource.id == KnowledgeVersion.knowledge_source_id)
        .where(KnowledgeVersion.id == version_id)
    )
    return result.one_or_none()


async def lock_knowledge_version(session: AsyncSession, version_id) -> KnowledgeVersion | None:
    return await session.scalar(
        select(KnowledgeVersion).where(KnowledgeVersion.id == version_id).with_for_update()
    )


async def delete_chunks_for_version(session: AsyncSession, version_id) -> None:
    await session.execute(delete(Chunk).where(Chunk.knowledge_version_id == version_id))


async def add_chunks(session: AsyncSession, version_id, chunks: list[dict]) -> None:
    session.add_all(Chunk(knowledge_version_id=version_id, **chunk) for chunk in chunks)
    await session.flush()


async def get_document(session: AsyncSession, document_id) -> Document | None:
    return await session.get(Document, document_id)


async def list_documents(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
) -> tuple[list[Document], int]:
    total = await session.scalar(select(func.count()).select_from(Document))
    items = list((await session.scalars(
        select(Document)
        .order_by(Document.created_at.desc(), Document.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).all())
    return items, total or 0


async def get_document_for_update(session: AsyncSession, document_id):
    return await session.scalar(
        select(Document).where(Document.id == document_id).with_for_update()
    )


async def get_pinned_review_run(session: AsyncSession, document: Document):
    if document.review_transformation_run_id is None:
        return None
    return await session.get(TransformationRun, document.review_transformation_run_id)


async def get_knowledge_source(session: AsyncSession, *, source_type: str, source_id):
    column = KnowledgeSource.document_id if source_type == "DOCUMENT" else KnowledgeSource.lesson_id
    return await session.scalar(select(KnowledgeSource).where(column == source_id))


async def get_knowledge_source_for_update(session: AsyncSession, source_id):
    return await session.scalar(
        select(KnowledgeSource).where(KnowledgeSource.id == source_id).with_for_update()
    )


async def find_processing_version(session: AsyncSession, source_id):
    return await session.scalar(
        select(KnowledgeVersion).where(
            KnowledgeVersion.knowledge_source_id == source_id,
            KnowledgeVersion.status == "PROCESSING",
        )
    )


async def next_knowledge_version_number(session: AsyncSession, source_id) -> int:
    current = await session.scalar(
        select(func.max(KnowledgeVersion.version_number)).where(
            KnowledgeVersion.knowledge_source_id == source_id
        )
    )
    return (current or 0) + 1


async def add_knowledge_source(session: AsyncSession, *, source_type: str, source_id):
    source = KnowledgeSource(
        source_type=source_type,
        document_id=source_id if source_type == "DOCUMENT" else None,
        lesson_id=source_id if source_type == "LESSON" else None,
    )
    session.add(source)
    await session.flush()
    return source


async def add_processing_version(
    session: AsyncSession, *, source_id, version_number: int, transformation_run_id=None,
):
    version = KnowledgeVersion(
        knowledge_source_id=source_id,
        version_number=version_number,
        status="PROCESSING",
        transformation_run_id=transformation_run_id,
    )
    session.add(version)
    await session.flush()
    return version


async def set_knowledge_version_transformation_run(
    session: AsyncSession, version_id, transformation_run_id,
) -> None:
    version = await lock_knowledge_version(session, version_id)
    if version is None or version.status != "PROCESSING":
        raise ValueError("KnowledgeVersion is not available for lineage update")
    if version.transformation_run_id not in (None, transformation_run_id):
        raise ValueError("KnowledgeVersion transformation lineage is immutable")
    version.transformation_run_id = transformation_run_id
    await session.flush()


async def mark_knowledge_version_failed(session: AsyncSession, version_id) -> bool:
    version = await lock_knowledge_version(session, version_id)
    if version is None or version.status != "PROCESSING":
        return False
    version.status = "FAILED"
    await session.flush()
    return True


async def get_parsing_run_for_transformation(session: AsyncSession, parsing_run_id) -> ParsingRun | None:
    return await session.get(ParsingRun, parsing_run_id)
