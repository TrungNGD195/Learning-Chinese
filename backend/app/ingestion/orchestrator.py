"""Coordinate accepted ingestion stages with short, durable state changes."""
from __future__ import annotations

import logging
import hashlib
from time import perf_counter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError
from app.database.models import (
    Document, KnowledgeSource, KnowledgeVersion, Lesson, TransformationRun,
)
from app.ingestion import repository, service as raw_service
from app.ingestion.service import create_lesson_snapshot, lesson_snapshot_bytes
from app.ingestion.chunking.service import build_chunks
from app.ingestion.parsing_service import parse_raw_artifact
from app.ingestion.schemas import ParsedArtifactRef, RawArtifactRef, TransformedArtifactRef
from app.ingestion.storage import FileStorage
from app.ingestion.transformation.models import TransformedDocument
from app.ingestion.transformation.service import (
    load_transformed_artifact, transform_parsed_artifact,
)

logger = logging.getLogger(__name__)


def _error(code: str, message: str, status: int = 409, details=None) -> ApplicationError:
    return ApplicationError(code, message, details=details, status_code=status)


def _log(source_id, source_type: str, stage: str, status: str, started: float,
         *, version_id=None, error_code=None) -> None:
    logger.info(
        "ingestion_stage",
        extra={
            "source_id": str(source_id), "source_type": source_type,
            "stage": stage, "status": status,
            "knowledge_version_id": str(version_id) if version_id else None,
            "error_code": error_code,
            "duration_ms": round((perf_counter() - started) * 1000, 2),
        },
    )


async def _stage(awaitable, *, source_id, source_type: str, stage: str, version_id=None):
    started = perf_counter()
    try:
        result = await awaitable
    except Exception as exc:
        code = exc.code if isinstance(exc, ApplicationError) else "INGESTION_PROCESSING_FAILED"
        _log(source_id, source_type, stage, "FAILED", started,
             version_id=version_id, error_code=code)
        raise
    _log(source_id, source_type, stage, "SUCCEEDED", started, version_id=version_id)
    return result


def _valid_run(run: TransformationRun | None, *, source_type: str, source_id) -> bool:
    if run is None:
        return False
    target_id = run.document_id if source_type == "DOCUMENT" else run.lesson_id
    return (
        run.status == "SUCCEEDED"
        and run.source_type == source_type
        and target_id == source_id
        and run.transformed_storage_reference is not None
    )


def _ref_from_run(run: TransformationRun) -> TransformedArtifactRef:
    source_id = run.document_id if run.source_type == "DOCUMENT" else run.lesson_id
    return TransformedArtifactRef(
        transformation_run_id=run.id,
        source_type=run.source_type,
        source_id=source_id,
        storage_key=run.transformed_storage_reference,
        schema_version="transformed_document/v1",
    )


async def resolve_document_knowledge_retry_artifact(
    session: AsyncSession,
    document: Document,
) -> TransformedArtifactRef | None:
    """Resolve the exact approved artifact accepted by knowledge retry."""
    if document.approved_transformation_run_id is None:
        return None
    run = await session.get(TransformationRun, document.approved_transformation_run_id)
    if not _valid_run(run, source_type="DOCUMENT", source_id=document.id):
        return None
    return _ref_from_run(run)


def _validate_source(source: KnowledgeSource, source_type: str, source_id) -> None:
    valid = source.source_type == source_type
    if source_type == "DOCUMENT":
        valid = valid and source.document_id == source_id and source.lesson_id is None
    else:
        valid = valid and source.lesson_id == source_id and source.document_id is None
    if not valid:
        raise _error("INVALID_SOURCE_STATE", "Knowledge source identity is invalid.")


def _constraint_name(exc: IntegrityError) -> str | None:
    diagnostic = getattr(getattr(exc, "orig", None), "diag", None)
    return getattr(diagnostic, "constraint_name", None)


async def _get_or_create_source(session: AsyncSession, source_type: str, source_id) -> KnowledgeSource:
    source = await repository.get_knowledge_source(
        session, source_type=source_type, source_id=source_id
    )
    if source is not None:
        _validate_source(source, source_type, source_id)
        return source

    try:
        async with session.begin_nested():
            source = await repository.add_knowledge_source(
                session, source_type=source_type, source_id=source_id
            )
        return source
    except IntegrityError as exc:
        expected = (
            "uq_knowledge_sources_document_id" if source_type == "DOCUMENT"
            else "uq_knowledge_sources_lesson_id"
        )
        if _constraint_name(exc) != expected:
            raise
        source = await repository.get_knowledge_source(
            session, source_type=source_type, source_id=source_id
        )
        if source is None:
            raise
        _validate_source(source, source_type, source_id)
        return source


async def _new_processing_version(
    session: AsyncSession, source_id, *, transformation_run_id=None,
) -> UUID:
    source = await repository.get_knowledge_source_for_update(session, source_id)
    if source is None:
        raise _error("INVALID_SOURCE_STATE", "Knowledge source was not found.")
    if await repository.find_processing_version(session, source_id) is not None:
        raise _error(
            "PROCESSING_ALREADY_IN_PROGRESS", "A knowledge build is already processing."
        )
    version_number = await repository.next_knowledge_version_number(session, source_id)
    version = await repository.add_processing_version(
        session, source_id=source_id, version_number=version_number,
        transformation_run_id=transformation_run_id,
    )
    return version.id


async def _allocate_document_version(
    session: AsyncSession, document_id, *, transformation_run_id=None,
    expected_source_fingerprint: str | None = None,
) -> UUID:
    await session.rollback()
    async with session.begin():
        document = await repository.get_document_for_update(session, document_id)
        if document is None:
            raise _error("NOT_FOUND", "Document was not found.", status=404)
        if document.processing_status == "PROCESSING":
            raise _error("PROCESSING_ALREADY_IN_PROGRESS", "Document processing is already in progress.")
        if (expected_source_fingerprint is not None
                and document.content_hash != expected_source_fingerprint):
            raise _error("REPROCESSING_STATE_CHANGED", "Document source changed during planning.")
        if (transformation_run_id is not None
                and document.approved_transformation_run_id != transformation_run_id):
            raise _error("INVALID_SOURCE_STATE", "Approved Document artifact changed during build claim.")
        if (transformation_run_id is not None
                and document.review_status not in {"APPROVED", "PENDING"}):
            raise _error("INVALID_SOURCE_STATE", "Document has no approved artifact for a build.")
        source = await _get_or_create_source(session, "DOCUMENT", document_id)
        return await _new_processing_version(
            session, source.id, transformation_run_id=transformation_run_id
        )


async def _allocate_lesson_version(
    session: AsyncSession, lesson_id, *, expected_source_fingerprint: str | None = None,
    expected_active_version_id=None, expected_transformation_run_id=None,
    revalidate_baseline: bool = False, transformation_run_id=None,
) -> UUID:
    await session.rollback()
    async with session.begin():
        lesson = await session.scalar(
            select(Lesson).where(Lesson.id == lesson_id).with_for_update()
        )
        if lesson is None or lesson.status != "PUBLISHED":
            raise _error("INVALID_SOURCE_STATE", "Only a published Lesson can be ingested.")
        if expected_source_fingerprint is not None:
            current_snapshot = await lesson_snapshot_bytes(session, lesson_id)
            current_fingerprint = hashlib.sha256(current_snapshot).hexdigest()
            if current_fingerprint != expected_source_fingerprint:
                raise _error("REPROCESSING_STATE_CHANGED", "Lesson content changed during planning.")
        source = await _get_or_create_source(session, "LESSON", lesson_id)
        # The source row serializes retries and concurrent publish-triggered builds.
        await repository.get_knowledge_source_for_update(session, source.id)
        if revalidate_baseline:
            active = await session.scalar(select(KnowledgeVersion).where(
                KnowledgeVersion.knowledge_source_id == source.id,
                KnowledgeVersion.status == "ACTIVE",
            ))
            if ((active.id if active else None) != expected_active_version_id
                    or (active.transformation_run_id if active else None) != expected_transformation_run_id):
                raise _error("REPROCESSING_STATE_CHANGED", "Lesson knowledge baseline changed during planning.")
        return await _new_processing_version(
            session, source.id, transformation_run_id=transformation_run_id,
        )


async def _mark_document_failed(session: AsyncSession, document_id) -> None:
    try:
        await session.rollback()
        async with session.begin():
            document = await repository.get_document_for_update(session, document_id)
            if document is not None and document.processing_status == "PROCESSING":
                document.processing_status = "FAILED"
                document.review_transformation_run_id = None
    except Exception:
        await session.rollback()
        logger.warning("document_failure_state_persist_failed", extra={
            "source_id": str(document_id), "source_type": "DOCUMENT",
            "stage": "failure", "status": "FAILED",
            "knowledge_version_id": None, "error_code": "STATE_PERSIST_FAILED",
            "duration_ms": 0,
        })


async def _mark_version_failed(session: AsyncSession, version_id, *, source_id, source_type: str) -> None:
    try:
        await session.rollback()
        async with session.begin():
            await repository.mark_knowledge_version_failed(session, version_id)
    except Exception:
        await session.rollback()
        logger.warning("knowledge_version_failure_state_persist_failed", extra={
            "source_id": str(source_id), "source_type": source_type,
            "stage": "failure", "status": "FAILED",
            "knowledge_version_id": str(version_id), "error_code": "STATE_PERSIST_FAILED",
            "duration_ms": 0,
        })


async def _build_knowledge(session: AsyncSession, storage: FileStorage, *, source_id,
                           source_type: str, version_id, artifact: TransformedArtifactRef) -> None:
    try:
        await _stage(
            build_chunks(artifact, version_id, session=session, storage=storage),
            source_id=source_id, source_type=source_type, stage="chunk", version_id=version_id,
        )
    except Exception as exc:
        await _mark_version_failed(
            session, version_id, source_id=source_id, source_type=source_type
        )
        logger.warning("knowledge_build_failed", extra={
            "source_id": str(source_id), "source_type": source_type,
            "stage": "chunk", "status": "FAILED",
            "knowledge_version_id": str(version_id),
            "error_code": exc.code if isinstance(exc, ApplicationError) else "KNOWLEDGE_BUILD_FAILED",
            "duration_ms": 0,
        })
        if source_type == "DOCUMENT":
            details = {"document_id": str(source_id), "review_status": "APPROVED",
                       "knowledge_version_id": str(version_id)}
        else:
            details = {"lesson_id": str(source_id), "lesson_status": "PUBLISHED",
                       "knowledge_version_id": str(version_id)}
        raise _error(
            "KNOWLEDGE_BUILD_FAILED", "Knowledge build could not be completed.",
            status=500, details=details,
        ) from exc


class IngestionOrchestrator:
    """Run source lifecycle gates and delegate exact refs to accepted stages."""

    def __init__(self, session: AsyncSession, storage: FileStorage):
        self.session = session
        self.storage = storage

    async def process_document(self, document_id: UUID) -> dict:
        raw_started = perf_counter()
        await self.session.rollback()
        async with self.session.begin():
            document = await repository.get_document_for_update(self.session, document_id)
            if document is None:
                raise _error("NOT_FOUND", "Document was not found.", status=404)
            if document.review_status != "PENDING" or not (
                document.processing_status == "UPLOADED"
                or document.processing_status == "FAILED"
            ):
                if document.processing_status == "PROCESSING":
                    raise _error(
                        "PROCESSING_ALREADY_IN_PROGRESS", "Document processing is already in progress."
                    )
                raise _error("INVALID_SOURCE_STATE", "Document cannot be processed in its current state.")
            document.processing_status = "PROCESSING"
            document.review_transformation_run_id = None

        # The durable claim must finish before even validating the legacy raw
        # metadata. Some accepted pre-Step-5.2 rows have nullable raw fields.
        try:
            await self.session.refresh(document)
            raw_ref = raw_service.document_raw_artifact_ref(document)
        except Exception as exc:
            await _mark_document_failed(self.session, document_id)
            _log(
                document_id, "DOCUMENT", "raw", "FAILED", raw_started,
                error_code="INGESTION_PROCESSING_FAILED",
            )
            raise _error(
                "INGESTION_PROCESSING_FAILED",
                "Document processing could not be completed.",
                status=500,
            ) from exc

        _log(document_id, "DOCUMENT", "raw", "SUCCEEDED", raw_started)

        try:
            parsed = await _stage(
                parse_raw_artifact(raw_ref, session=self.session, storage=self.storage),
                source_id=document_id, source_type="DOCUMENT", stage="parse",
            )
            transformed = await _stage(
                transform_parsed_artifact(parsed, session=self.session, storage=self.storage),
                source_id=document_id, source_type="DOCUMENT", stage="transform",
            )
            await self.session.rollback()
            async with self.session.begin():
                current = await self.session.get(Document, document_id)
                if (current is None or current.processing_status != "PREVIEW_READY"
                        or current.review_transformation_run_id != transformed.transformation_run_id):
                    raise _error("INGESTION_PROCESSING_FAILED", "Document processing could not be completed.", status=500)
            logger.info("document_process_succeeded", extra={
                "source_id": str(document_id), "source_type": "DOCUMENT", "stage": "transform",
                "status": "SUCCEEDED", "knowledge_version_id": None, "error_code": None,
                "duration_ms": 0,
            })
            return {"id": document_id, "processing_status": "PREVIEW_READY"}
        except ApplicationError as exc:
            await _mark_document_failed(self.session, document_id)
            raise _error(
                "INGESTION_PROCESSING_FAILED", "Document processing could not be completed.", status=500
            ) from exc
        except Exception as exc:
            await _mark_document_failed(self.session, document_id)
            raise _error(
                "INGESTION_PROCESSING_FAILED", "Document processing could not be completed.", status=500
            ) from exc

    async def preview_document(self, document_id: UUID) -> TransformedDocument:
        await self.session.rollback()
        document = await repository.get_document(self.session, document_id)
        if (document is None or document.processing_status != "PREVIEW_READY"
                or document.review_transformation_run_id is None):
            raise _error(
                "DOCUMENT_NOT_PREVIEW_READY", "Document does not have a reviewable preview."
            )
        run = await repository.get_pinned_review_run(self.session, document)
        if not _valid_run(run, source_type="DOCUMENT", source_id=document_id):
            await self.session.rollback()
            raise _error(
                "DOCUMENT_NOT_PREVIEW_READY", "Document does not have a valid reviewable preview."
            )
        ref = _ref_from_run(run)
        await self.session.rollback()
        started = perf_counter()
        try:
            result = load_transformed_artifact(ref, storage=self.storage)
        except ApplicationError:
            _log(document_id, "DOCUMENT", "review", "FAILED", started,
                 error_code="DOCUMENT_NOT_PREVIEW_READY")
            raise _error(
                "DOCUMENT_NOT_PREVIEW_READY", "Document preview could not be loaded."
            ) from None
        _log(document_id, "DOCUMENT", "review", "SUCCEEDED", started)
        return result

    async def _approved_artifact(self, document_id: UUID) -> TransformedArtifactRef | None:
        await self.session.rollback()
        document = await repository.get_document(self.session, document_id)
        if document is None:
            raise _error("NOT_FOUND", "Document was not found.", status=404)
        ref = await resolve_document_knowledge_retry_artifact(self.session, document)
        await self.session.rollback()
        return ref

    async def approve_document(self, document_id: UUID, admin_id: UUID) -> dict:
        review_started = perf_counter()
        await self.session.rollback()
        async with self.session.begin():
            document = await repository.get_document_for_update(self.session, document_id)
            if document is None:
                raise _error("NOT_FOUND", "Document was not found.", status=404)
            if document.review_status == "APPROVED":
                raise _error("DOCUMENT_ALREADY_APPROVED", "Document has already been approved.")
            if document.review_status != "PENDING" or document.processing_status != "PREVIEW_READY":
                raise _error("INVALID_SOURCE_STATE", "Document is not ready for approval.")
            run = await repository.get_pinned_review_run(self.session, document)
            if not _valid_run(run, source_type="DOCUMENT", source_id=document_id):
                raise _error("INVALID_SOURCE_STATE", "Document review artifact is unavailable.")
            artifact = _ref_from_run(run)
            document.review_status = "APPROVED"
            document.approved_transformation_run_id = run.id
            document.approved_by = admin_id
            from datetime import UTC, datetime
            document.approved_at = datetime.now(UTC)
        _log(document_id, "DOCUMENT", "review", "SUCCEEDED", review_started)
        try:
            version_id = await _allocate_document_version(
                self.session, document_id,
                transformation_run_id=artifact.transformation_run_id,
            )
        except ApplicationError:
            raise
        except Exception as exc:
            raise _error(
                "KNOWLEDGE_BUILD_FAILED", "Knowledge build could not be started.", status=500,
                details={"document_id": str(document_id), "review_status": "APPROVED"},
            ) from exc
        await _build_knowledge(
            self.session, self.storage, source_id=document_id, source_type="DOCUMENT",
            version_id=version_id, artifact=artifact,
        )
        return {"id": document_id, "review_status": "APPROVED", "knowledge_version_id": version_id}

    async def reject_document(self, document_id: UUID) -> dict:
        review_started = perf_counter()
        await self.session.rollback()
        async with self.session.begin():
            document = await repository.get_document_for_update(self.session, document_id)
            if document is None:
                raise _error("NOT_FOUND", "Document was not found.", status=404)
            if document.review_status != "PENDING" or document.processing_status != "PREVIEW_READY":
                raise _error("INVALID_SOURCE_STATE", "Document is not ready for rejection.")
            run = await repository.get_pinned_review_run(self.session, document)
            if not _valid_run(run, source_type="DOCUMENT", source_id=document_id):
                raise _error("INVALID_SOURCE_STATE", "Document review artifact is unavailable.")
            if document.approved_transformation_run_id is not None:
                approved_run = await self.session.get(
                    TransformationRun, document.approved_transformation_run_id
                )
                if not _valid_run(approved_run, source_type="DOCUMENT", source_id=document_id):
                    raise _error("INVALID_SOURCE_STATE", "Approved Document artifact is unavailable.")
                document.review_status = "APPROVED"
                document.processing_status = "PREVIEW_READY"
                document.review_transformation_run_id = document.approved_transformation_run_id
                restored = True
            else:
                document.review_status = "REJECTED"
                restored = False
        _log(document_id, "DOCUMENT", "review", "SUCCEEDED", review_started)
        return {"id": document_id, "review_status": "APPROVED" if restored else "REJECTED"}

    async def retry_document_knowledge(self, document_id: UUID) -> dict:
        artifact = await self._approved_artifact(document_id)
        if artifact is None:
            raise _error("INVALID_SOURCE_STATE", "Only an approved Document can be rebuilt.")
        try:
            version_id = await _allocate_document_version(
                self.session, document_id,
                transformation_run_id=artifact.transformation_run_id,
            )
        except ApplicationError:
            raise
        except Exception as exc:
            raise _error(
                "KNOWLEDGE_BUILD_FAILED", "Knowledge build could not be started.", status=500,
                details={"document_id": str(document_id), "review_status": "APPROVED"},
            ) from exc
        await _build_knowledge(
            self.session, self.storage, source_id=document_id, source_type="DOCUMENT",
            version_id=version_id, artifact=artifact,
        )
        return {"id": document_id, "review_status": "APPROVED", "knowledge_version_id": version_id}

    async def process_published_lesson(self, lesson_id: UUID) -> dict:
        try:
            version_id = await _allocate_lesson_version(self.session, lesson_id)
        except ApplicationError:
            raise
        except Exception as exc:
            raise _error(
                "KNOWLEDGE_BUILD_FAILED", "Knowledge build could not be started.", status=500,
                details={"lesson_id": str(lesson_id), "lesson_status": "PUBLISHED"},
            ) from exc
        try:
            raw = await _stage(
                create_lesson_snapshot(self.session, lesson_id, self.storage),
                source_id=lesson_id, source_type="LESSON", stage="raw", version_id=version_id,
            )
            parsed = await _stage(
                parse_raw_artifact(raw, session=self.session, storage=self.storage),
                source_id=lesson_id, source_type="LESSON", stage="parse", version_id=version_id,
            )
            transformed = await _stage(
                transform_parsed_artifact(parsed, session=self.session, storage=self.storage),
                source_id=lesson_id, source_type="LESSON", stage="transform", version_id=version_id,
            )
            await self.session.rollback()
            async with self.session.begin():
                await repository.set_knowledge_version_transformation_run(
                    self.session, version_id, transformed.transformation_run_id
                )
            await _build_knowledge(
                self.session, self.storage, source_id=lesson_id, source_type="LESSON",
                version_id=version_id, artifact=transformed,
            )
            return {"lesson_id": lesson_id, "status": "PUBLISHED", "knowledge_version_id": version_id}
        except ApplicationError as exc:
            if exc.code == "KNOWLEDGE_BUILD_FAILED":
                raise _error(
                    "KNOWLEDGE_BUILD_FAILED", "Knowledge build could not be completed.", status=500,
                    details={"lesson_id": str(lesson_id), "lesson_status": "PUBLISHED",
                             "knowledge_version_id": str(version_id)},
                ) from exc
            await _mark_version_failed(
                self.session, version_id, source_id=lesson_id, source_type="LESSON"
            )
            raise _error(
                "KNOWLEDGE_BUILD_FAILED", "Knowledge build could not be completed.", status=500,
                details={"lesson_id": str(lesson_id), "lesson_status": "PUBLISHED",
                         "knowledge_version_id": str(version_id)},
            ) from exc
        except Exception as exc:
            await _mark_version_failed(
                self.session, version_id, source_id=lesson_id, source_type="LESSON"
            )
            raise _error(
                "KNOWLEDGE_BUILD_FAILED", "Knowledge build could not be completed.", status=500,
                details={"lesson_id": str(lesson_id), "lesson_status": "PUBLISHED",
                         "knowledge_version_id": str(version_id)},
            ) from exc

    async def retry_lesson_knowledge(self, lesson_id: UUID) -> dict:
        return await self.process_published_lesson(lesson_id)


async def process_published_lesson(session: AsyncSession, lesson_id: UUID,
                                   storage: FileStorage) -> dict:
    return await IngestionOrchestrator(session, storage).process_published_lesson(lesson_id)
