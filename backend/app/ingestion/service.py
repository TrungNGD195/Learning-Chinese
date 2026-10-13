import codecs
import hashlib
import logging
import zipfile
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ApplicationError
from app.database.models import (
    Document, Grammar, HSKLevel, Lesson, LessonGrammar, LessonVocabulary, Vocabulary,
)
from app.ingestion import repository
from app.ingestion.schemas import RawArtifactRef
from app.ingestion.schemas import (
    DocumentAdminDetailResponse,
    DocumentAdminListItemResponse,
    DocumentAdminPageResponse,
)
from app.ingestion.source_policy import (
    DocumentSourceMetadata, is_document_ingestion_eligible,
    is_published_lesson_eligible,
)
from app.ingestion.storage import FileStorage, LocalFileStorage
from sqlalchemy import select

logger = logging.getLogger(__name__)
CHUNK_SIZE = 64 * 1024

MIME_TYPES = {
    ".pdf": {"application/pdf"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
    },
    ".txt": {"text/plain"},
    ".md": {"text/markdown", "text/plain"},
}


async def list_admin_documents(
    session: AsyncSession, *, page: int, page_size: int,
) -> DocumentAdminPageResponse:
    documents, total = await repository.list_documents(
        session, page=page, page_size=page_size
    )
    return DocumentAdminPageResponse(
        items=[DocumentAdminListItemResponse.model_validate(document) for document in documents],
        page=page,
        page_size=page_size,
        total=total,
    )


async def get_admin_document_detail(
    session: AsyncSession, document_id: UUID,
) -> DocumentAdminDetailResponse:
    document = await repository.get_document(session, document_id)
    if document is None:
        raise _error("NOT_FOUND", "Document was not found", 404)

    # Imported here to keep the existing orchestrator -> ingestion service
    # dependency one-way while sharing the mutation's artifact predicate.
    from app.ingestion.orchestrator import resolve_document_knowledge_retry_artifact

    artifact = await resolve_document_knowledge_retry_artifact(session, document)
    processing_version = None
    if artifact is not None:
        source = await repository.get_knowledge_source(
            session, source_type="DOCUMENT", source_id=document.id
        )
        if source is not None:
            processing_version = await repository.find_processing_version(
                session, source.id
            )
    item = DocumentAdminListItemResponse.model_validate(document)
    return DocumentAdminDetailResponse.model_validate({
        **item.model_dump(),
        "knowledge_retry_available": artifact is not None and processing_version is None,
    })


def _error(code: str, message: str, status: int) -> ApplicationError:
    return ApplicationError(code, message, status_code=status)


def document_raw_artifact_ref(document: Document) -> RawArtifactRef:
    """Build the internal Step-5.3 handoff from a persisted raw Document."""
    return RawArtifactRef(
        source_type="DOCUMENT", source_id=document.id,
        storage_key=document.storage_reference, file_format=document.file_type,
        mime_type=document.mime_type, file_size_bytes=document.file_size_bytes,
        content_hash=document.content_hash,
    )


def _validate_signature(storage: FileStorage, temp_key: str, extension: str, declared_mime: str) -> None:
    if declared_mime not in MIME_TYPES.get(extension, set()):
        raise _error("INVALID_DOCUMENT_FILE", "Declared MIME type does not match the file type", 422)
    with storage.open_temp(temp_key) as raw:
        first = raw.read(8)
        raw.seek(0)
        if extension == ".pdf" and not first.startswith(b"%PDF-"):
            raise _error("INVALID_DOCUMENT_FILE", "File signature is invalid", 422)
        if extension == ".docx":
            if first[:4] != b"PK\x03\x04":
                raise _error("INVALID_DOCUMENT_FILE", "File signature is invalid", 422)
            try:
                with zipfile.ZipFile(raw) as archive:
                    names = set(archive.namelist())
                    if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                        raise ValueError("not a DOCX package")
            except (zipfile.BadZipFile, OSError, ValueError) as exc:
                raise _error("INVALID_DOCUMENT_FILE", "DOCX package is invalid", 422) from exc
        if extension in {".txt", ".md"}:
            decoder = codecs.getincrementaldecoder("utf-8")("strict")
            try:
                while data := raw.read(CHUNK_SIZE):
                    decoder.decode(data)
                decoder.decode(b"", final=True)
            except UnicodeDecodeError as exc:
                raise _error("INVALID_DOCUMENT_FILE", "Text file is not valid UTF-8", 422) from exc


async def ingest_document(
    *, session: AsyncSession, settings: Settings, storage: FileStorage,
    admin_id: UUID, upload, title: str, source_category: str, source_origin: str,
    source_language: str, usage_rights_note: str | None, domain_allowed: bool,
) -> dict:
    filename = (upload.filename or "source").replace("\\", "/").rsplit("/", 1)[-1]
    extension = Path(filename).suffix.lower()
    if extension not in MIME_TYPES:
        raise _error("UNSUPPORTED_DOCUMENT_TYPE", "Supported formats are PDF, DOCX, TXT and MD", 422)
    try:
        metadata = DocumentSourceMetadata.model_validate({
            "title": title, "source_category": source_category,
            "source_origin": source_origin, "source_language": source_language,
            "usage_rights_note": usage_rights_note,
        })
    except ValidationError as exc:
        raise _error("INVALID_REQUEST", "Request validation failed", 422) from exc
    if not is_document_ingestion_eligible(
        metadata, input_format=extension[1:].upper(), domain_allowed=domain_allowed
    ):
        raise _error("INVALID_REQUEST", "Document source is not eligible for ingestion", 422)

    mime_type = (upload.content_type or "").split(";", 1)[0].strip().lower()
    max_bytes = settings.document_max_upload_mb * 1024 * 1024
    document_id = uuid4()
    temp_key = None
    final_key = f"documents/{document_id}/raw{extension}"
    finalized = False
    digest = hashlib.sha256()
    total = 0
    try:
        # The Admin dependency may have queried through this same request session.
        # Release that read transaction before waiting on the client upload stream.
        await session.rollback()
        temp_key, handle = storage.create_temp()
        with handle:
            while chunk := await upload.read(CHUNK_SIZE):
                total += len(chunk)
                if total > max_bytes:
                    raise _error("DOCUMENT_TOO_LARGE", "Document exceeds the configured upload limit", 413)
                digest.update(chunk)
                storage.write(handle, chunk)
        if total == 0:
            raise _error("EMPTY_DOCUMENT", "Document is empty", 422)
        _validate_signature(storage, temp_key, extension, mime_type)
        content_hash = digest.hexdigest()
        if await repository.get_by_content_hash(session, content_hash):
            raise _error("DUPLICATE_DOCUMENT", "An identical document already exists", 409)
        # The duplicate pre-check is only an optimization. End its read transaction
        # before finalization; the unique constraint remains authoritative at insert.
        await session.rollback()
        storage.finalize(temp_key, final_key)
        finalized = True
        async with session.begin():
            document = await repository.add_document(session, {
                "id": document_id,
                "original_filename": filename,
                "file_type": extension[1:].upper(),
                "storage_reference": final_key,
                "mime_type": mime_type,
                "file_size_bytes": total,
                "content_hash": content_hash,
                "title": metadata.title,
                "source_category": metadata.source_category.value,
                "source_origin": metadata.source_origin,
                "source_language": metadata.source_language.value,
                "usage_rights_note": metadata.usage_rights_note,
                "processing_status": "UPLOADED",
                "review_status": "PENDING",
                "uploaded_by": admin_id,
            })
        return {name: getattr(document, name) for name in (
            "id", "original_filename", "file_type", "mime_type", "file_size_bytes",
            "content_hash", "title", "source_category", "source_origin",
            "source_language", "usage_rights_note", "processing_status", "review_status", "created_at",
        )}
    except ApplicationError:
        await _cleanup(session, storage, temp_key, final_key if finalized else None)
        raise
    except IntegrityError as exc:
        await session.rollback()
        await _cleanup(session, storage, temp_key, final_key if finalized else None)
        if _is_content_hash_conflict(exc):
            raise _error("DUPLICATE_DOCUMENT", "An identical document already exists", 409) from exc
        raise _error("RAW_STORAGE_FAILED", "Document ingestion could not be completed", 500) from exc
    except Exception as exc:
        await session.rollback()
        await _cleanup(session, storage, temp_key, final_key if finalized else None)
        raise _error("RAW_STORAGE_FAILED", "Document ingestion could not be completed", 500) from exc
    finally:
        await upload.close()


async def _cleanup(session: AsyncSession, storage: FileStorage, temp_key: str | None, final_key: str | None) -> None:
    try:
        await session.rollback()
    except Exception:
        logger.exception("Failed to roll back raw ingestion database work")
    for key, delete in ((temp_key, storage.discard), (final_key, storage.delete)):
        if key:
            try:
                delete(key)
            except Exception:
                logger.exception("Failed to clean up raw ingestion artifact")


def _is_content_hash_conflict(exc: IntegrityError) -> bool:
    original = getattr(exc, "orig", None)
    diagnostic = getattr(original, "diag", None)
    return getattr(diagnostic, "constraint_name", None) == "uq_documents_content_hash"


async def lesson_snapshot_bytes(session: AsyncSession, lesson_id: UUID) -> bytes:
    lesson = await session.get(Lesson, lesson_id)
    if lesson is None:
        raise _error("NOT_FOUND", "Lesson was not found", 404)
    if not is_published_lesson_eligible(lesson.status):
        raise _error("LESSON_NOT_PUBLISHED", "Only published Lessons can be snapshotted", 409)
    hsk = await session.get(HSKLevel, lesson.hsk_level_id)
    vocab_rows = (await session.execute(
        select(LessonVocabulary, Vocabulary)
        .join(Vocabulary, Vocabulary.id == LessonVocabulary.vocabulary_id)
        .where(LessonVocabulary.lesson_id == lesson_id)
        .order_by(LessonVocabulary.order_index.asc())
    )).all()
    grammar_rows = (await session.execute(
        select(LessonGrammar, Grammar)
        .join(Grammar, Grammar.id == LessonGrammar.grammar_id)
        .where(LessonGrammar.lesson_id == lesson_id)
        .order_by(LessonGrammar.order_index.asc())
    )).all()
    snapshot = {
        "schema_version": "raw_lesson_snapshot/v1",
        "lesson": {
            "id": str(lesson.id),
            "hsk": {"id": str(hsk.id), "level_number": hsk.level_number, "title": hsk.title},
            "lesson_number": lesson.lesson_number, "title": lesson.title,
            "description": lesson.description, "status": "PUBLISHED",
        },
        "vocabulary": [{
            "order_index": link.order_index, "lesson_vocabulary_id": str(link.id),
            "vocabulary_id": str(item.id), "hanzi": item.hanzi, "pinyin": item.pinyin,
            "vietnamese_meaning": item.vietnamese_meaning, "part_of_speech": item.part_of_speech,
            "note": link.note, "example": link.example,
        } for link, item in vocab_rows],
        "grammar": [{
            "order_index": link.order_index, "lesson_grammar_id": str(link.id),
            "grammar_id": str(item.id), "name": item.name, "structure": item.structure,
            "explanation": item.explanation, "usage": item.usage,
            "note": link.note, "example": link.example,
        } for link, item in grammar_rows],
    }
    import json
    return json.dumps(
        snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


async def create_lesson_snapshot(
    session: AsyncSession, lesson_id: UUID, storage: FileStorage,
) -> RawArtifactRef:
    data = await lesson_snapshot_bytes(session, lesson_id)
    content_hash = hashlib.sha256(data).hexdigest()
    storage_key = f"lessons/{lesson_id}/raw/{content_hash}.json"
    await session.rollback()
    writer = getattr(storage, "write_bytes", None)
    if writer is None:
        temp_key, handle = storage.create_temp()
        try:
            with handle:
                storage.write(handle, data)
            storage.finalize(temp_key, storage_key)
        except Exception:
            storage.discard(temp_key)
            raise _error("RAW_STORAGE_FAILED", "Lesson snapshot could not be stored", 500)
    else:
        try:
            writer(storage_key, data)
        except Exception as exc:
            raise _error("RAW_STORAGE_FAILED", "Lesson snapshot could not be stored", 500) from exc
    return RawArtifactRef(
        source_type="LESSON", source_id=lesson_id, storage_key=storage_key,
        file_format="JSON", mime_type="application/json", file_size_bytes=len(data),
        content_hash=content_hash,
    )
