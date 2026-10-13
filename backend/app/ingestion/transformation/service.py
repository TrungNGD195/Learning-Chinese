import json
import logging
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError
from app.ingestion import repository
from app.ingestion.parsing.base import ParsingFailure
from app.ingestion.schemas import ParsedArtifactRef, TransformedArtifactRef
from app.ingestion.storage import FileStorage
from app.ingestion.transformation import document_transformer, lesson_transformer
from app.ingestion.transformation.models import ParsedCleanedArtifactInput, SourceMetadataSnapshot, TransformedDocument

logger = logging.getLogger(__name__)
TRANSFORMATION_STRATEGY = "canonical_document"
TRANSFORMATION_VERSION = "v1"
TRANSFORMED_SCHEMA = "transformed_document/v1"


def _error_code(exc: Exception) -> str:
    if isinstance(exc, ParsingFailure) and exc.code in {
        "TRANSFORMATION_FAILED", "INVALID_TRANSFORMED_DOCUMENT", "UNSUPPORTED_CONTENT_TYPE", "INVALID_SOURCE_LOCATOR",
    }:
        return exc.code
    return "TRANSFORMATION_FAILED"


async def _persist_failed(session: AsyncSession, run_id, *, code: str, detail: str, document_id=None) -> None:
    try:
        await session.rollback()
        async with session.begin():
            run = await repository.get_transformation_run(session, run_id)
            if run is not None:
                run.status = "FAILED"
                run.transformed_storage_reference = None
                run.error_code = code
                run.error_detail = detail[:300]
            if document_id is not None:
                document = await repository.get_document(session, document_id)
                if document is not None:
                    document.processing_status = "FAILED"
                    document.review_transformation_run_id = None
    except Exception:
        await session.rollback()
        logger.warning("Failed to persist transformation failure state", exc_info=False)


def _snapshot_values(artifact: ParsedCleanedArtifactInput, source) -> dict:
    if artifact.source_type == "DOCUMENT":
        return {
            "source_type": "DOCUMENT", "source_id": str(artifact.source_id),
            "title": getattr(source, "title", None),
            "source_language": getattr(source, "source_language", None),
            "source_category": getattr(source, "source_category", None),
            "source_origin": getattr(source, "source_origin", None),
            "usage_rights_note": getattr(source, "usage_rights_note", None),
            "original_filename": getattr(source, "original_filename", None),
        }
    title = next((unit.text for unit in artifact.units if unit.source_locator.get("kind") == "LESSON_FIELD"
                  and unit.source_locator.get("section") == "LESSON"
                  and unit.source_locator.get("entity_id") == str(artifact.source_id)
                  and unit.source_locator.get("field") == "title"), None)
    return {
        "source_type": "LESSON", "source_id": str(artifact.source_id), "title": title,
        "source_language": None, "source_category": None,
    }


async def _finalize(storage: FileStorage, key: str, data: bytes) -> None:
    temp_key, handle = storage.create_temp()
    try:
        with handle:
            storage.write(handle, data)
        storage.finalize(temp_key, key)
    except Exception:
        try:
            storage.discard(temp_key)
        except Exception:
            logger.warning("Failed to discard temporary transformed artifact", exc_info=False)
        raise


def _canonical_bytes(document: TransformedDocument) -> bytes:
    return json.dumps(document.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


async def transform_parsed_artifact(
    parsed_artifact: ParsedArtifactRef, *, session: AsyncSession, storage: FileStorage,
) -> TransformedArtifactRef:
    """Transform one specific successful parsed run and persist a canonical artifact."""
    await session.rollback()
    try:
        ref = ParsedArtifactRef.model_validate(parsed_artifact)
        with storage.open(ref.storage_key) as handle:
            parsed_bytes = handle.read()
        parsed = ParsedCleanedArtifactInput.model_validate_json(parsed_bytes)
        if parsed.source_type != ref.source_type or parsed.source_id != ref.source_id:
            raise ParsingFailure("INVALID_SOURCE_LOCATOR", "Parsed artifact source does not match its reference.")
        async with session.begin():
            parsing_run = await repository.get_parsing_run_for_transformation(session, ref.parsing_run_id)
            if (parsing_run is None or parsing_run.status != "SUCCEEDED"
                    or parsing_run.parsed_storage_reference != ref.storage_key
                    or parsing_run.source_type != ref.source_type
                    or (parsing_run.document_id if ref.source_type == "DOCUMENT" else parsing_run.lesson_id) != ref.source_id):
                raise ParsingFailure("TRANSFORMATION_FAILED", "Parsed artifact reference is not a successful matching parsing run.")
            source = await repository.get_document(session, ref.source_id) if ref.source_type == "DOCUMENT" else None
            snapshot = _snapshot_values(parsed, source)
            run_id = uuid4()
            document_id = ref.source_id if ref.source_type == "DOCUMENT" else None
            await repository.add_transformation_run(session, {
                "id": run_id,
                "source_type": ref.source_type,
                "document_id": document_id,
                "lesson_id": ref.source_id if ref.source_type == "LESSON" else None,
                "parsing_run_id": ref.parsing_run_id,
                "parsed_storage_reference": ref.storage_key,
                "transformation_strategy": TRANSFORMATION_STRATEGY,
                "transformation_version": TRANSFORMATION_VERSION,
                "status": "PENDING",
                "source_metadata_snapshot": snapshot,
            })
        try:
            async with session.begin():
                run = await repository.get_transformation_run(session, run_id)
                run.status = "PROCESSING"
                if document_id is not None:
                    current_document = await repository.get_document(session, document_id)
                    if current_document is None:
                        raise ParsingFailure("TRANSFORMATION_FAILED", "Document source metadata is unavailable.")
                    current_document.processing_status = "PROCESSING"

            metadata = SourceMetadataSnapshot.model_validate(snapshot)
            if ref.source_type == "DOCUMENT" and source is None:
                raise ParsingFailure("TRANSFORMATION_FAILED", "Document source metadata is unavailable.")
            if ref.source_type == "DOCUMENT":
                result = document_transformer.transform_document(parsed, metadata)
            else:
                result = lesson_transformer.transform_lesson(parsed, metadata)
            canonical = TransformedDocument.model_validate(result)
            if canonical.source_id != ref.source_id or canonical.source_type != ref.source_type:
                raise ParsingFailure("INVALID_TRANSFORMED_DOCUMENT", "Canonical artifact identity is invalid.")
            canonical_bytes = _canonical_bytes(canonical)
            # Round-trip validation ensures persisted bytes satisfy the canonical contract.
            TransformedDocument.model_validate_json(canonical_bytes)
            artifact_key = f"transformed/{ref.source_type.lower()}s/{ref.source_id}/{run_id}/transformed_document.json"
            try:
                await _finalize(storage, artifact_key, canonical_bytes)
            except Exception:
                try:
                    storage.delete(artifact_key)
                except Exception:
                    logger.warning("Failed to remove partially finalized transformed artifact", exc_info=False)
                raise
            try:
                async with session.begin():
                    run = await repository.get_transformation_run(session, run_id)
                    run.status = "SUCCEEDED"
                    run.transformed_storage_reference = artifact_key
                    run.error_code = None
                    run.error_detail = None
                    if document_id is not None:
                        current_document = await repository.get_document(session, document_id)
                        if current_document is None:
                            raise RuntimeError("source row unavailable")
                        current_document.processing_status = "PREVIEW_READY"
                        current_document.review_transformation_run_id = run_id
            except Exception as exc:
                await session.rollback()
                try:
                    storage.delete(artifact_key)
                except Exception:
                    logger.warning("Failed to remove orphan transformed artifact", exc_info=False)
                await _persist_failed(session, run_id, code="TRANSFORMATION_FAILED",
                                      detail="Transformed artifact could not be recorded.", document_id=document_id)
                raise ApplicationError("TRANSFORMATION_FAILED", "Transformation could not be completed.", status_code=500) from exc
            return TransformedArtifactRef(
                transformation_run_id=run_id, source_type=ref.source_type, source_id=ref.source_id,
                storage_key=artifact_key, schema_version=TRANSFORMED_SCHEMA,
            )
        except ApplicationError:
            raise
        except Exception as exc:
            code = _error_code(exc)
            if isinstance(exc, ValidationError):
                code = "INVALID_TRANSFORMED_DOCUMENT"
                detail = "Canonical transformed document failed validation."
            elif isinstance(exc, ParsingFailure):
                detail = exc.detail
            else:
                detail = "Parsed content could not be transformed."
            await _persist_failed(session, run_id, code=code, detail=detail, document_id=document_id)
            raise ApplicationError(code, detail, status_code=422) from exc
    except ApplicationError:
        raise
    except ParsingFailure as exc:
        raise ApplicationError(exc.code, exc.detail, status_code=422) from exc
    except ValidationError as exc:
        raise ApplicationError("TRANSFORMATION_FAILED", "Transformation input is invalid.", status_code=422) from exc
    except Exception as exc:
        raise ApplicationError("TRANSFORMATION_FAILED", "Transformation input could not be loaded.", status_code=422) from exc


def load_transformed_artifact(ref: TransformedArtifactRef, *, storage: FileStorage) -> TransformedDocument:
    """Load and validate the exact persisted artifact without rerunning transformation."""
    try:
        typed_ref = TransformedArtifactRef.model_validate(ref)
        with storage.open(typed_ref.storage_key) as handle:
            document = TransformedDocument.model_validate_json(handle.read())
        if document.source_type != typed_ref.source_type or document.source_id != typed_ref.source_id:
            raise ValueError("artifact identity mismatch")
        return document
    except Exception as exc:
        raise ApplicationError("INVALID_TRANSFORMED_DOCUMENT", "Transformed artifact is invalid.", status_code=422) from exc
