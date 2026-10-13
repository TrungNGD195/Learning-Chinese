from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError
from app.database.models import KnowledgeSource
from app.ingestion import repository
from app.ingestion.chunking.config import DEFAULT_CHUNKING_CONFIG
from app.ingestion.chunking.models import ChunkBuildResult
from app.ingestion.chunking.strategy import build_chunk_plan
from app.ingestion.schemas import TransformedArtifactRef
from app.ingestion.storage import FileStorage
from app.ingestion.transformation.models import TransformedDocument
from app.ingestion.transformation.service import load_transformed_artifact


def _source_matches(source: KnowledgeSource, ref: TransformedArtifactRef) -> bool:
    return (
        source.source_type == ref.source_type
        and (source.document_id if ref.source_type == "DOCUMENT" else source.lesson_id) == ref.source_id
        and (source.lesson_id is None if ref.source_type == "DOCUMENT" else source.document_id is None)
    )


async def _validate_version_source(session: AsyncSession, version_id: UUID, ref: TransformedArtifactRef,
                                   *, locked: bool = False):
    if locked:
        version = await repository.lock_knowledge_version(session, version_id)
        source = await session.get(KnowledgeSource, version.knowledge_source_id) if version else None
    else:
        pair = await repository.get_knowledge_version_source(session, version_id)
        version, source = pair if pair is not None else (None, None)
    if version is None or source is None:
        raise ApplicationError("INVALID_CHUNKING_INPUT", "Knowledge version source is unavailable.", status_code=422)
    if version.status != "PROCESSING":
        raise ApplicationError("KNOWLEDGE_VERSION_NOT_PROCESSING", "Knowledge version is not available for chunking.", status_code=409)
    if not _source_matches(source, ref):
        raise ApplicationError("INVALID_CHUNKING_INPUT", "Knowledge version does not match the transformed source.", status_code=422)
    return version, source


async def _validate_transformation_lineage(session: AsyncSession, ref: TransformedArtifactRef) -> None:
    run = await repository.get_transformation_run(session, ref.transformation_run_id)
    source_id = None
    if run is not None:
        source_id = run.document_id if ref.source_type == "DOCUMENT" else run.lesson_id
    if (
        run is None
        or run.status != "SUCCEEDED"
        or run.transformed_storage_reference != ref.storage_key
        or run.source_type != ref.source_type
        or source_id != ref.source_id
        or ref.schema_version != "transformed_document/v1"
    ):
        raise ApplicationError("INVALID_CHUNKING_INPUT", "Transformed artifact lineage is not a successful exact match.", status_code=422)


async def build_chunks(
    transformed_artifact: TransformedArtifactRef,
    knowledge_version_id: UUID,
    *,
    session: AsyncSession,
    storage: FileStorage,
) -> ChunkBuildResult:
    """Plan from one exact persisted artifact, then atomically replace a PROCESSING version's Chunks."""
    try:
        ref = TransformedArtifactRef.model_validate(transformed_artifact)
    except (ValidationError, TypeError, ValueError) as exc:
        raise ApplicationError("INVALID_CHUNKING_INPUT", "Transformed artifact reference is invalid.", status_code=422) from exc

    # The initial read and artifact planning stay outside the replacement transaction.
    await session.rollback()
    try:
        async with session.begin():
            await _validate_transformation_lineage(session, ref)
            await _validate_version_source(session, knowledge_version_id, ref)
    except ApplicationError:
        raise
    except Exception as exc:
        raise ApplicationError("CHUNKING_FAILED", "Chunking input could not be validated.", status_code=500) from exc

    try:
        document = load_transformed_artifact(ref, storage=storage)
        typed_document = TransformedDocument.model_validate(document)
        if typed_document.schema_version != ref.schema_version:
            raise ApplicationError("INVALID_CHUNKING_INPUT", "Transformed artifact schema does not match its reference.", status_code=422)
        if typed_document.source_type != ref.source_type or typed_document.source_id != ref.source_id:
            raise ApplicationError("INVALID_CHUNKING_INPUT", "Transformed artifact identity does not match its reference.", status_code=422)
        plan = build_chunk_plan(typed_document, knowledge_version_id)
    except ApplicationError as exc:
        if exc.code == "INVALID_TRANSFORMED_DOCUMENT":
            raise ApplicationError("INVALID_CHUNKING_INPUT", "Persisted transformed artifact is invalid.", status_code=422) from exc
        raise
    except ValidationError as exc:
        raise ApplicationError("INVALID_CHUNKING_INPUT", "Transformed artifact is invalid for chunking.", status_code=422) from exc
    except Exception as exc:
        raise ApplicationError("CHUNKING_FAILED", "Chunk planning failed.", status_code=500) from exc

    await session.rollback()
    try:
        async with session.begin():
            version, _source = await _validate_version_source(session, knowledge_version_id, ref, locked=True)
            # Recheck the exact run while the version row is locked so stale or changed lineage cannot replace rows.
            await _validate_transformation_lineage(session, ref)
            if version.transformation_run_id not in (None, ref.transformation_run_id):
                raise ApplicationError(
                    "INVALID_CHUNKING_INPUT",
                    "Knowledge version is pinned to a different transformation.",
                    status_code=422,
                )
            await repository.delete_chunks_for_version(session, knowledge_version_id)
            values = [
                {
                    "content": chunk.content,
                    "content_type": chunk.content_type,
                    "chunk_index": chunk.chunk_index,
                    "token_count": None,
                    "page_number": chunk.page_number,
                    "section": chunk.section,
                    "lesson_id": chunk.lesson_id,
                    "metadata_json": chunk.metadata.model_dump(mode="json"),
                    "content_hash": chunk.content_hash,
                }
                for chunk in plan.chunks
            ]
            await repository.add_chunks(session, knowledge_version_id, values)
            version.transformation_run_id = ref.transformation_run_id
            version.chunking_strategy = DEFAULT_CHUNKING_CONFIG.strategy
            version.chunking_version = DEFAULT_CHUNKING_CONFIG.version
            version.chunk_size = DEFAULT_CHUNKING_CONFIG.target_chars
            version.chunk_max_chars = DEFAULT_CHUNKING_CONFIG.max_chars
            version.chunk_overlap = DEFAULT_CHUNKING_CONFIG.overlap_chars
            await session.flush()
    except ApplicationError:
        await session.rollback()
        raise
    except Exception as exc:
        await session.rollback()
        raise ApplicationError("CHUNKING_FAILED", "Chunk replacement could not be committed.", status_code=500) from exc

    return plan
