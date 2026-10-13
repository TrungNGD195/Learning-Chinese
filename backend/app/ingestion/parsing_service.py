import json
import logging
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError
from app.database.models import Document
from app.ingestion import repository
from app.ingestion.cleaning import CLEANING_STRATEGY, CLEANING_VERSION
from app.ingestion.parsing.base import ParsingFailure
from app.ingestion.parsing.docx import DocxParser
from app.ingestion.parsing.lesson import LessonSnapshotParser
from app.ingestion.parsing.markdown import MarkdownParser
from app.ingestion.parsing.pdf import PdfParser
from app.ingestion.parsing.text import TxtParser
from app.ingestion.schemas import ParsedArtifactRef, RawArtifactRef
from app.ingestion.storage import FileStorage
from app.ingestion.transformation.models import ParsedCleanedArtifactInput

logger = logging.getLogger(__name__)
ARTIFACT_SCHEMA = "parsed_cleaned_artifact/v1"


async def load_parsed_artifact(
    ref: ParsedArtifactRef, *, session: AsyncSession, storage: FileStorage,
    expected_source_fingerprint: str,
) -> ParsedCleanedArtifactInput:
    """Load one exact, successful parsed artifact and validate persisted lineage."""
    try:
        typed_ref = ParsedArtifactRef.model_validate(ref)
    except Exception as exc:
        raise ApplicationError("ARTIFACT_INVALID", "Parsed artifact reference is invalid.", status_code=409) from exc
    try:
        with storage.open(typed_ref.storage_key) as handle:
            data = handle.read()
    except FileNotFoundError as exc:
        raise ApplicationError("ARTIFACT_MISSING", "Parsed artifact is unavailable.", status_code=409) from exc
    except Exception as exc:
        raise ApplicationError("ARTIFACT_INVALID", "Parsed artifact could not be read.", status_code=409) from exc
    try:
        artifact = ParsedCleanedArtifactInput.model_validate_json(data)
    except Exception as exc:
        raise ApplicationError("ARTIFACT_INVALID", "Parsed artifact is invalid.", status_code=409) from exc

    await session.rollback()
    run = await repository.get_parsing_run(session, typed_ref.parsing_run_id)
    source_id = None
    if run is not None:
        source_id = run.document_id if typed_ref.source_type == "DOCUMENT" else run.lesson_id
    if (
        run is None
        or run.status != "SUCCEEDED"
        or run.error_code is not None
        or run.parsed_storage_reference != typed_ref.storage_key
        or run.source_type != typed_ref.source_type
        or source_id != typed_ref.source_id
        or artifact.source_type != typed_ref.source_type
        or artifact.source_id != typed_ref.source_id
        or artifact.schema_version != typed_ref.schema_version
        or artifact.raw_content_hash != expected_source_fingerprint
        or run.raw_content_hash != expected_source_fingerprint
        or artifact.raw_content_hash != run.raw_content_hash
        or artifact.parser_name != run.parser_name
        or artifact.parser_version != run.parser_version
        or artifact.cleaning_strategy != run.cleaning_strategy
        or artifact.cleaning_version != run.cleaning_version
    ):
        await session.rollback()
        raise ApplicationError("ARTIFACT_INVALID", "Parsed artifact lineage is invalid.", status_code=409)
    await session.rollback()
    return artifact


def _select_parser(source: RawArtifactRef):
    if source.source_type == "LESSON" and source.file_format.upper() == "JSON":
        return LessonSnapshotParser()
    if source.source_type == "DOCUMENT":
        parsers = {"PDF": PdfParser, "DOCX": DocxParser, "TXT": TxtParser, "MD": MarkdownParser}
        parser = parsers.get(source.file_format.upper())
        if parser is not None:
            return parser()
    raise ParsingFailure("UNSUPPORTED_PARSER", "No parser is available for this source format.")


async def _persist_failure(session: AsyncSession, run_id, code: str, detail: str, *, document_id=None) -> None:
    try:
        await session.rollback()
        async with session.begin():
            run = await repository.get_parsing_run(session, run_id)
            if run is not None:
                run.status = "FAILED"
                run.parsed_storage_reference = None
                run.error_code = code
                run.error_detail = detail[:300]
            if document_id is not None:
                document = await session.get(Document, document_id)
                if document is not None:
                    document.processing_status = "FAILED"
    except Exception:
        await session.rollback()
        logger.warning("Failed to persist parsing failure state", exc_info=False)


async def _store(storage: FileStorage, key: str, data: bytes) -> None:
    writer = getattr(storage, "write_bytes", None)
    if writer is not None:
        writer(key, data)
        return
    temp_key, handle = storage.create_temp()
    try:
        with handle:
            storage.write(handle, data)
        storage.finalize(temp_key, key)
    except Exception:
        try:
            storage.discard(temp_key)
        except Exception:
            logger.warning("Failed to discard temporary parsed artifact", exc_info=False)
        raise


async def parse_raw_artifact(
    raw_artifact: RawArtifactRef, *, session: AsyncSession, storage: FileStorage,
) -> ParsedArtifactRef:
    """Run one isolated parsing attempt over immutable bytes and return its exact artifact ref."""
    await session.rollback()
    run_id = uuid4()
    parser = None
    artifact_key = None
    document_id = raw_artifact.source_id if raw_artifact.source_type == "DOCUMENT" else None
    try:
        try:
            parser = _select_parser(raw_artifact)
            parser_name, parser_version = parser.name, parser.version
        except ParsingFailure:
            parser_name, parser_version = "unsupported", "v1"
        async with session.begin():
            await repository.add_parsing_run(session, {
                "id": run_id,
                "source_type": raw_artifact.source_type,
                "document_id": document_id,
                "lesson_id": raw_artifact.source_id if raw_artifact.source_type == "LESSON" else None,
                "raw_storage_reference": raw_artifact.storage_key,
                "raw_content_hash": raw_artifact.content_hash,
                "parser_name": parser_name,
                "parser_version": parser_version,
                "cleaning_strategy": CLEANING_STRATEGY,
                "cleaning_version": CLEANING_VERSION,
                "status": "PENDING",
            })
            if document_id is not None:
                document = await session.get(Document, document_id)
                if document is None:
                    raise ParsingFailure("PARSING_FAILED", "Document source record was not found.")
                document.processing_status = "PROCESSING"
        if parser is None:
            raise ParsingFailure("UNSUPPORTED_PARSER", "No parser is available for this source format.")
        async with session.begin():
            run = await repository.get_parsing_run(session, run_id)
            run.status = "PROCESSING"

        with storage.open(raw_artifact.storage_key) as handle:
            raw = handle.read()
        units = parser.parse(raw)
        if raw_artifact.source_type == "LESSON":
            try:
                if json.loads(raw.decode("utf-8"))["lesson"]["id"] != str(raw_artifact.source_id):
                    raise ValueError
            except Exception as exc:
                raise ParsingFailure("INVALID_LESSON_SNAPSHOT", "Stored lesson snapshot identity does not match its reference.") from exc
        artifact = {
            "schema_version": ARTIFACT_SCHEMA,
            "source_type": raw_artifact.source_type,
            "source_id": str(raw_artifact.source_id),
            "raw_content_hash": raw_artifact.content_hash,
            "parser_name": parser.name,
            "parser_version": parser.version,
            "cleaning_strategy": CLEANING_STRATEGY,
            "cleaning_version": CLEANING_VERSION,
            "units": [{"order": unit.order, "text": unit.text, "source_locator": unit.source_locator} for unit in units],
        }
        data = json.dumps(artifact, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        artifact_key = f"parsed/{raw_artifact.source_type.lower()}s/{raw_artifact.source_id}/{run_id}/parsed_cleaned.json"
        await _store(storage, artifact_key, data)
        try:
            async with session.begin():
                run = await repository.get_parsing_run(session, run_id)
                run.status = "SUCCEEDED"
                run.parsed_storage_reference = artifact_key
                run.error_code = None
                run.error_detail = None
        except Exception:
            await session.rollback()
            try:
                storage.delete(artifact_key)
            except Exception:
                logger.warning("Failed to remove orphan parsed artifact", exc_info=False)
            await _persist_failure(session, run_id, "PARSING_FAILED", "Parsed artifact could not be recorded.", document_id=document_id)
            raise ApplicationError("PARSING_FAILED", "Parsing could not be completed.", status_code=500)
        return ParsedArtifactRef(
            parsing_run_id=run_id, source_type=raw_artifact.source_type,
            source_id=raw_artifact.source_id, storage_key=artifact_key, schema_version=ARTIFACT_SCHEMA,
        )
    except ApplicationError:
        raise
    except ParsingFailure as exc:
        if artifact_key:
            try:
                storage.delete(artifact_key)
            except Exception:
                logger.warning("Failed to remove incomplete parsed artifact", exc_info=False)
        await _persist_failure(session, run_id, exc.code, exc.detail, document_id=document_id)
        raise ApplicationError(exc.code, exc.detail, status_code=422)
    except Exception as exc:
        if artifact_key:
            try:
                storage.delete(artifact_key)
            except Exception:
                logger.warning("Failed to remove incomplete parsed artifact", exc_info=False)
        await _persist_failure(session, run_id, "PARSING_FAILED", "Raw content could not be parsed.", document_id=document_id)
        raise ApplicationError("PARSING_FAILED", "Parsing could not be completed.", status_code=422) from exc
