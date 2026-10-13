from pathlib import Path
from shutil import rmtree
from uuid import uuid4
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
import hashlib
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy import select
from types import SimpleNamespace

from app.core.config import get_settings
from app.database.models import Document
from app.database.session import SessionFactory
from app.auth.current_user import get_current_user
from app.ingestion.service import document_raw_artifact_ref
from app.main import app


def test_admin_upload_persists_exact_pdf_and_hides_storage_reference(
    persisted_admin_override, monkeypatch,
) -> None:
    root = Path(__file__).resolve().parents[2] / "tmp" / f"step52-upload-{uuid4().hex}"
    root.mkdir(parents=True)
    storage_root = root / "raw"
    monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(storage_root))
    get_settings.cache_clear()
    body = b"%PDF-1.7\nraw fixture bytes\n%%EOF"
    form = {"title": "PDF source", "source_category": "INTERNAL_AUTHORED",
            "source_origin": "Test source", "source_language": "en",
            "domain_allowed": "true"}
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/admin/documents",
            files={"file": ("..\\..\\attacker.pdf", body, "application/pdf")},
            data=form,
        )
        duplicate = client.post(
            "/api/v1/admin/documents",
            files={"file": ("source.pdf", body, "application/pdf")},
            data=form,
        )
    get_settings.cache_clear()
    assert response.status_code == 201, response.text
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DUPLICATE_DOCUMENT"
    payload = response.json()
    assert payload["original_filename"] == "attacker.pdf"
    assert payload["processing_status"] == "UPLOADED"
    assert payload["review_status"] == "PENDING"
    assert payload["file_size_bytes"] == len(body)
    assert payload["content_hash"] == hashlib.sha256(body).hexdigest()
    assert payload["mime_type"] == "application/pdf"
    assert payload["title"] == "PDF source"
    assert payload["source_category"] == "INTERNAL_AUTHORED"
    assert "storage_reference" not in payload
    assert "storage" not in payload
    artifact = storage_root / "documents" / payload["id"] / "raw.pdf"
    assert artifact.read_bytes() == body

    import asyncio
    from uuid import UUID
    async def inspect_ref():
        async with SessionFactory() as session:
            document = await session.get(Document, UUID(payload["id"]))
            assert document.review_transformation_run_id is None
            from app.database.models import KnowledgeSource, ParsingRun, TransformationRun
            assert await session.scalar(select(ParsingRun.id).where(
                ParsingRun.document_id == document.id)) is None
            assert await session.scalar(select(TransformationRun.id).where(
                TransformationRun.document_id == document.id)) is None
            assert await session.scalar(select(KnowledgeSource.id).where(
                KnowledgeSource.document_id == document.id)) is None
            ref = document_raw_artifact_ref(document)
            assert ref.source_type == "DOCUMENT"
            assert ref.content_hash == payload["content_hash"]
            assert ref.storage_key == f"documents/{payload['id']}/raw.pdf"
    async def cleanup() -> None:
        async with SessionFactory.begin() as session:
            await session.execute(delete(Document).where(Document.id == UUID(payload["id"])))
    asyncio.run(inspect_ref())
    asyncio.run(cleanup())
    rmtree(root)


def test_upload_rejects_domain_false_and_unsupported_extension(
    persisted_admin_override, monkeypatch,
) -> None:
    root = Path(__file__).resolve().parents[2] / "tmp" / f"step52-upload-{uuid4().hex}"
    root.mkdir(parents=True)
    monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(root / "raw"))
    get_settings.cache_clear()
    data = {"title": "source", "source_category": "INTERNAL_AUTHORED",
            "source_origin": "origin", "source_language": "en", "domain_allowed": "false"}
    with TestClient(app) as client:
        rejected = client.post("/api/v1/admin/documents", files={"file": ("a.pdf", b"%PDF-1.0", "application/pdf")}, data=data)
        unsupported = client.post("/api/v1/admin/documents", files={"file": ("a.html", b"<p>x</p>", "text/html")}, data={**data, "domain_allowed": "true"})
        missing_attestation = client.post("/api/v1/admin/documents", files={"file": ("a.pdf", b"%PDF-1.0", "application/pdf")}, data={key: value for key, value in data.items() if key != "domain_allowed"})
    get_settings.cache_clear()
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "INVALID_REQUEST"
    assert unsupported.status_code == 422
    assert unsupported.json()["error"]["code"] == "UNSUPPORTED_DOCUMENT_TYPE"
    assert missing_attestation.status_code == 422
    assert missing_attestation.json()["error"]["code"] == "INVALID_REQUEST"
    rmtree(root)


def _docx_bytes() -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
    return output.getvalue()


@pytest.mark.parametrize(("filename", "body", "mime"), [
    ("lesson.docx", _docx_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ("lesson.txt", "你好\n".encode("utf-8"), "text/plain"),
    ("lesson.md", b"# Chinese lesson\n", "text/markdown"),
])
def test_other_frozen_formats_preserve_exact_bytes(
    persisted_admin_override, monkeypatch, filename: str, body: bytes, mime: str,
) -> None:
    root = Path(__file__).resolve().parents[2] / "tmp" / f"step52-format-{uuid4().hex}"
    root.mkdir(parents=True)
    storage_root = root / "raw"
    monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(storage_root))
    get_settings.cache_clear()
    data = {"title": "source", "source_category": "INTERNAL_AUTHORED",
            "source_origin": "origin", "source_language": "zh", "domain_allowed": "true"}
    with TestClient(app) as client:
        response = client.post("/api/v1/admin/documents", files={"file": (filename, body, mime)}, data=data)
    get_settings.cache_clear()
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["file_size_bytes"] == len(body)
    assert payload["mime_type"] == mime
    artifact = storage_root / "documents" / payload["id"] / f"raw{Path(filename).suffix}"
    assert artifact.read_bytes() == body
    import asyncio
    from uuid import UUID
    async def cleanup() -> None:
        async with SessionFactory.begin() as session:
            await session.execute(delete(Document).where(Document.id == UUID(payload["id"])))
    asyncio.run(cleanup())
    rmtree(root)


def test_empty_invalid_and_oversized_uploads_are_rejected_and_clean_temporary_files(
    persisted_admin_override, monkeypatch,
) -> None:
    root = Path(__file__).resolve().parents[2] / "tmp" / f"step52-invalid-{uuid4().hex}"
    root.mkdir(parents=True)
    storage_root = root / "raw"
    monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(storage_root))
    monkeypatch.setenv("DOCUMENT_MAX_UPLOAD_MB", "1")
    get_settings.cache_clear()
    data = {"title": "source", "source_category": "INTERNAL_AUTHORED",
            "source_origin": "origin", "source_language": "en", "domain_allowed": "true"}
    with TestClient(app) as client:
        empty = client.post("/api/v1/admin/documents", files={"file": ("empty.txt", b"", "text/plain")}, data=data)
        invalid = client.post("/api/v1/admin/documents", files={"file": ("bad.txt", b"\xff", "text/plain")}, data=data)
        too_large = client.post("/api/v1/admin/documents", files={"file": ("large.txt", b"a" * (1024 * 1024 + 1), "text/plain")}, data=data)
    get_settings.cache_clear()
    assert (empty.status_code, empty.json()["error"]["code"]) == (422, "EMPTY_DOCUMENT")
    assert (invalid.status_code, invalid.json()["error"]["code"]) == (422, "INVALID_DOCUMENT_FILE")
    assert (too_large.status_code, too_large.json()["error"]["code"]) == (413, "DOCUMENT_TOO_LARGE")
    assert not list((storage_root / "tmp").glob("*.part"))
    rmtree(root)


def test_missing_auth_and_learner_cannot_upload() -> None:
    with TestClient(app) as client:
        unauthenticated = client.post("/api/v1/admin/documents")
        assert unauthenticated.status_code == 401

    async def learner():
        return SimpleNamespace(id=uuid4(), role="LEARNER", is_active=True)
    app.dependency_overrides[get_current_user] = learner
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/admin/documents",
                files={"file": ("source.pdf", b"%PDF-1.0", "application/pdf")},
                data={"title": "source", "source_category": "INTERNAL_AUTHORED",
                      "source_origin": "origin", "source_language": "en", "domain_allowed": "true"},
            )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_duplicate_unique_race_rolls_back_and_removes_finalized_artifact(
    persisted_admin_override, monkeypatch,
) -> None:
    root = Path(__file__).resolve().parents[2] / "tmp" / f"step52-race-{uuid4().hex}"
    root.mkdir(parents=True)
    storage_root = root / "raw"
    monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(storage_root))
    get_settings.cache_clear()

    async def not_found(session, content_hash):
        return None
    async def race_insert(session, values):
        origin = SimpleNamespace(diag=SimpleNamespace(constraint_name="uq_documents_content_hash"))
        raise IntegrityError("insert", {}, origin)

    monkeypatch.setattr("app.ingestion.service.repository.get_by_content_hash", not_found)
    monkeypatch.setattr("app.ingestion.service.repository.add_document", race_insert)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/admin/documents",
            files={"file": ("race.txt", b"race content", "text/plain")},
            data={"title": "source", "source_category": "INTERNAL_AUTHORED",
                  "source_origin": "origin", "source_language": "en", "domain_allowed": "true"},
        )
    get_settings.cache_clear()
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_DOCUMENT"
    assert not [path for path in storage_root.rglob("*") if path.is_file()]
    rmtree(root)


def test_generic_database_failure_rolls_back_and_removes_finalized_artifact(
    persisted_admin_override, monkeypatch,
) -> None:
    root = Path(__file__).resolve().parents[2] / "tmp" / f"step52-db-failure-{uuid4().hex}"
    root.mkdir(parents=True)
    storage_root = root / "raw"
    monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(storage_root))
    get_settings.cache_clear()
    persistence_attempt: dict[str, object] = {}

    from app.ingestion import repository
    add_document = repository.add_document

    async def fail_after_staging(session, values):
        final_path = storage_root / values["storage_reference"]
        assert final_path.is_file(), "the raw artifact must be finalized before DB persistence"
        persistence_attempt["document_id"] = values["id"]
        persistence_attempt["final_path"] = final_path
        await add_document(session, values)
        raise OperationalError("INSERT documents", {}, RuntimeError("injected non-duplicate DB failure"))

    monkeypatch.setattr(repository, "add_document", fail_after_staging)
    body = b"non-duplicate persistence failure fixture"
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/admin/documents",
            files={"file": ("failure.txt", body, "text/plain")},
            data={"title": "failure source", "source_category": "INTERNAL_AUTHORED",
                  "source_origin": "injected database failure", "source_language": "en",
                  "domain_allowed": "true"},
        )
    get_settings.cache_clear()

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "RAW_STORAGE_FAILED"
    assert response.json()["error"]["code"] != "DUPLICATE_DOCUMENT"
    assert persistence_attempt
    assert not persistence_attempt["final_path"].exists()
    assert not [path for path in storage_root.rglob("*") if path.is_file()]

    import asyncio
    async def verify_rollback() -> None:
        async with SessionFactory() as session:
            persisted = await session.scalar(
                select(Document).where(Document.id == persistence_attempt["document_id"])
            )
            assert persisted is None
    asyncio.run(verify_rollback())
    rmtree(root)
