import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, func, select

from app.core.errors import ApplicationError
from app.database.models import Document, KnowledgeSource, KnowledgeVersion, TransformationRun
from app.database.session import SessionFactory
from app.ingestion.orchestrator import IngestionOrchestrator
from app.main import app


def _client_get(path: str):
    with TestClient(app) as client:
        return client.get(path)


def test_document_list_defaults_pagination_order_and_public_fields(
    persisted_admin_override,
):
    user_id = persisted_admin_override
    document_ids = [uuid4(), uuid4(), uuid4()]
    created_at = datetime(2100, 1, 1, tzinfo=timezone.utc)

    async def seed():
        async with SessionFactory.begin() as session:
            for index, document_id in enumerate(document_ids):
                session.add(Document(
                    id=document_id,
                    original_filename=f"read-contract-{index}.txt",
                    file_type="TXT",
                    storage_reference=f"test-only/{document_id}.txt",
                    mime_type=None,
                    file_size_bytes=None,
                    content_hash=None,
                    title=None,
                    source_category=None,
                    source_origin=None,
                    source_language=None,
                    usage_rights_note=None,
                    processing_status="UPLOADED",
                    review_status="PENDING",
                    uploaded_by=user_id,
                    created_at=created_at,
                    updated_at=created_at,
                ))

    asyncio.run(seed())
    try:
        default = _client_get("/api/v1/admin/documents")
        assert default.status_code == 200
        body = default.json()
        assert {key: body[key] for key in ("page", "page_size")} == {
            "page": 1, "page_size": 20,
        }
        assert {"items", "page", "page_size", "total"} <= body.keys()
        ordered = sorted((str(item) for item in document_ids), reverse=True)
        assert [item["id"] for item in body["items"][:3]] == ordered
        assert body["total"] >= 3
        first = _client_get("/api/v1/admin/documents?page=1&page_size=1").json()
        second = _client_get("/api/v1/admin/documents?page=2&page_size=1").json()
        assert first["page"] == 1 and first["page_size"] == 1
        assert second["page"] == 2 and second["page_size"] == 1
        assert first["total"] == second["total"]
        assert [first["items"][0]["id"], second["items"][0]["id"]] == ordered[:2]
        assert _client_get("/api/v1/admin/documents?page=0").status_code == 422
        assert _client_get("/api/v1/admin/documents?page_size=101").status_code == 422

        item = next(item for item in body["items"] if item["id"] in ordered)
        for field in (
            "mime_type", "file_size_bytes", "title", "source_category",
            "source_origin", "source_language", "usage_rights_note", "approved_at",
        ):
            assert item[field] is None
        assert item["processing_status"] == "UPLOADED"
        assert item["review_status"] == "PENDING"
        forbidden = {
            "storage_reference", "content_hash", "uploaded_by", "approved_by",
            "review_transformation_run_id", "approved_transformation_run_id",
            "parsing_run_id", "transformation_run_id", "knowledge_source_id",
            "knowledge_version_id", "chunk_id", "vector_id",
        }
        assert forbidden.isdisjoint(item)
    finally:
        async def cleanup():
            async with SessionFactory.begin() as session:
                await session.execute(delete(Document).where(Document.id.in_(document_ids)))
        asyncio.run(cleanup())


def test_document_detail_success_not_found_and_server_derived_capability(
    persisted_admin_override, step57_document,
):
    document_id = step57_document["source_id"]
    storage = step57_document["storage"]

    async def set_legacy_nulls():
        async with SessionFactory.begin() as session:
            document = await session.get(Document, document_id)
            document.mime_type = None
            document.file_size_bytes = None
            document.title = None
            document.source_category = None
            document.source_origin = None
            document.source_language = None
            document.usage_rights_note = None

    asyncio.run(set_legacy_nulls())
    detail = _client_get(f"/api/v1/admin/documents/{document_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["id"] == str(document_id)
    assert body["knowledge_retry_available"] is False
    for field in (
        "mime_type", "file_size_bytes", "title", "source_category",
        "source_origin", "source_language", "usage_rights_note",
    ):
        assert body[field] is None
    assert "storage_reference" not in body
    assert "review_transformation_run_id" not in body
    assert "approved_transformation_run_id" not in body

    missing = _client_get(f"/api/v1/admin/documents/{uuid4()}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"

    async def restore_pipeline_metadata():
        async with SessionFactory.begin() as session:
            document = await session.get(Document, document_id)
            document.mime_type = "text/plain"
            document.file_size_bytes = len(storage.objects[step57_document["raw_key"]])
            document.title = "Step 5.7 source"
            document.source_category = "CURRICULUM_MATERIAL"
            document.source_origin = "test fixture"
            document.source_language = "en"
            document.usage_rights_note = "test only"

    asyncio.run(restore_pipeline_metadata())

    async def counts():
        async with SessionFactory() as session:
            source_count = await session.scalar(select(func.count()).select_from(KnowledgeSource))
            version_count = await session.scalar(select(func.count()).select_from(KnowledgeVersion))
            return source_count, version_count

    approved = asyncio.run(step57_document["prepare_approved"]())
    assert approved["review_status"] == "APPROVED"
    assert storage.objects
    before = asyncio.run(counts())
    ready = _client_get(f"/api/v1/admin/documents/{document_id}")
    assert ready.status_code == 200
    assert ready.json()["knowledge_retry_available"] is True
    after = asyncio.run(counts())
    assert after == before


def test_document_knowledge_retry_capability_respects_processing_version_and_d065(
    persisted_admin_override, step57_document,
):
    document_id = step57_document["source_id"]
    approved = asyncio.run(step57_document["prepare_approved"]())
    version_id = approved["knowledge_version_id"]

    async def mark_pending_review_and_ingestion_processing():
        async with SessionFactory.begin() as session:
            document = await session.get(Document, document_id)
            document.review_status = "PENDING"
            # This is a separate state machine; it must not substitute for a
            # KnowledgeVersion PROCESSING claim in capability evaluation.
            document.processing_status = "PROCESSING"
            version = await session.get(KnowledgeVersion, version_id)
            version.status = "ACTIVE"
            source = await session.get(KnowledgeSource, version.knowledge_source_id)
            session.add(KnowledgeVersion(
                knowledge_source_id=source.id,
                version_number=version.version_number + 1,
                status="FAILED",
            ))

    asyncio.run(mark_pending_review_and_ingestion_processing())
    pending_with_prior_artifact = _client_get(
        f"/api/v1/admin/documents/{document_id}"
    )
    assert pending_with_prior_artifact.status_code == 200
    assert pending_with_prior_artifact.json()["review_status"] == "PENDING"
    assert pending_with_prior_artifact.json()["processing_status"] == "PROCESSING"
    assert pending_with_prior_artifact.json()["knowledge_retry_available"] is True

    async def add_processing_claim():
        async with SessionFactory.begin() as session:
            document = await session.get(Document, document_id)
            document.processing_status = "PREVIEW_READY"
            versions = list((await session.scalars(
                select(KnowledgeVersion).join(
                    KnowledgeSource,
                    KnowledgeSource.id == KnowledgeVersion.knowledge_source_id,
                ).where(KnowledgeSource.document_id == document_id)
            )).all())
            source_id = versions[0].knowledge_source_id
            next_number = max(version.version_number for version in versions) + 1
            session.add(KnowledgeVersion(
                knowledge_source_id=source_id,
                version_number=next_number,
                status="PROCESSING",
            ))

    asyncio.run(add_processing_claim())
    unavailable = _client_get(f"/api/v1/admin/documents/{document_id}")
    assert unavailable.status_code == 200
    assert unavailable.json()["knowledge_retry_available"] is False

    async def retry_against_processing_claim():
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as error:
                await IngestionOrchestrator(
                    session, step57_document["storage"]
                ).retry_document_knowledge(document_id)
            return error.value.code

    assert asyncio.run(retry_against_processing_claim()) == "PROCESSING_ALREADY_IN_PROGRESS"


def test_invalid_approved_artifact_disables_knowledge_retry(
    persisted_admin_override, step57_document,
):
    document_id = step57_document["source_id"]
    approved = asyncio.run(step57_document["prepare_approved"]())

    async def invalidate_approved_run():
        async with SessionFactory.begin() as session:
            document = await session.get(Document, document_id)
            run = await session.get(TransformationRun, document.approved_transformation_run_id)
            run.status = "FAILED"
            run.transformed_storage_reference = None
            run.error_code = "TEST_INVALIDATED"
            run.error_detail = "test-only invalid approved artifact"

    asyncio.run(invalidate_approved_run())
    result = _client_get(f"/api/v1/admin/documents/{document_id}")
    assert result.status_code == 200
    assert result.json()["knowledge_retry_available"] is False
    assert approved["review_status"] == "APPROVED"


def test_document_read_routes_require_admin_and_openapi_preserves_routes():
    with TestClient(app) as client:
        unauthorized = client.get("/api/v1/admin/documents")
    assert unauthorized.status_code == 401
    assert unauthorized.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

    paths = app.openapi()["paths"]
    assert "get" in paths["/api/v1/admin/documents"]
    assert "get" in paths["/api/v1/admin/documents/{document_id}"]
    expected_existing = {
        ("post", "/api/v1/admin/documents"),
        ("post", "/api/v1/admin/documents/{document_id}/process"),
        ("get", "/api/v1/admin/documents/{document_id}/preview"),
        ("post", "/api/v1/admin/documents/{document_id}/approve"),
        ("post", "/api/v1/admin/documents/{document_id}/reject"),
        ("post", "/api/v1/admin/documents/{document_id}/knowledge/retry"),
    }
    for method, path in expected_existing:
        assert method in paths[path]
    schemas = app.openapi()["components"]["schemas"]
    assert set(schemas["DocumentAdminListItemResponse"]["properties"]["processing_status"]["enum"]) == {
        "UPLOADED", "PROCESSING", "PREVIEW_READY", "FAILED",
    }
    assert set(schemas["DocumentAdminListItemResponse"]["properties"]["review_status"]["enum"]) == {
        "PENDING", "APPROVED", "REJECTED",
    }

