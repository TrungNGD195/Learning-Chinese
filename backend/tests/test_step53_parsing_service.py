import asyncio
import hashlib
import json
import shutil
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import delete, select

from app.core.errors import ApplicationError
from app.database.models import Document, HSKLevel, Lesson, ParsingRun, User
from app.database.session import SessionFactory
from app.ingestion.parsing_service import parse_raw_artifact
from app.ingestion import repository
from app.ingestion.schemas import ParsedArtifactRef, RawArtifactRef
from app.ingestion.storage import LocalFileStorage


@pytest.fixture
def storage_root():
    path = Path(__file__).resolve().parents[1] / f".step53-storage-{uuid4().hex}"
    path.mkdir()
    yield path
    shutil.rmtree(path, ignore_errors=True)


def test_parse_persists_specific_deterministic_artifact_and_document_status(storage_root) -> None:
    async def run_test() -> None:
        user_id, document_id = uuid4(), uuid4()
        raw = b"Stored words\n\nChinese: \xe4\xbd\xa0\xe5\xa5\xbd"
        digest = hashlib.sha256(raw).hexdigest()
        storage = LocalFileStorage(storage_root)
        storage.write_bytes("documents/test/raw.txt", raw)
        async with SessionFactory.begin() as session:
            session.add(User(id=user_id, email=f"step53-{user_id}@example.invalid", password_hash="unused", full_name="Test", role="ADMIN"))
            await session.flush()
            session.add(Document(
                id=document_id, original_filename="raw.txt", file_type="TXT", storage_reference="documents/test/raw.txt",
                mime_type="text/plain", file_size_bytes=len(raw), content_hash=digest,
                processing_status="UPLOADED", review_status="PENDING", uploaded_by=user_id,
            ))
        ref = None
        try:
            async with SessionFactory() as session:
                ref = await parse_raw_artifact(RawArtifactRef(
                    source_type="DOCUMENT", source_id=document_id, storage_key="documents/test/raw.txt",
                    file_format="TXT", mime_type="text/plain", file_size_bytes=len(raw), content_hash=digest,
                ), session=session, storage=storage)
            with storage.open(ref.storage_key) as handle:
                artifact_bytes = handle.read()
            async with SessionFactory() as session:
                repeated = await parse_raw_artifact(RawArtifactRef(
                    source_type="DOCUMENT", source_id=document_id, storage_key="documents/test/raw.txt",
                    file_format="TXT", mime_type="text/plain", file_size_bytes=len(raw), content_hash=digest,
                ), session=session, storage=storage)
            with storage.open(repeated.storage_key) as handle:
                assert handle.read() == artifact_bytes
            assert repeated.parsing_run_id != ref.parsing_run_id
            artifact = json.loads(artifact_bytes)
            assert artifact["schema_version"] == "parsed_cleaned_artifact/v1"
            assert ref.schema_version == "parsed_cleaned_artifact/v1"
            assert [unit["order"] for unit in artifact["units"]] == [0, 1]
            async with SessionFactory() as session:
                run = await session.get(ParsingRun, ref.parsing_run_id)
                document = await session.get(Document, document_id)
                assert run.status == "SUCCEEDED" and run.parsed_storage_reference == ref.storage_key
                assert run.parser_name == "txt_utf8" and run.parser_version == "v1"
                assert document.processing_status == "PROCESSING"
            async with SessionFactory.begin() as session:
                await session.execute(delete(ParsingRun).where(ParsingRun.document_id == document_id))
                await session.delete(await session.get(Document, document_id))
                await session.delete(await session.get(User, user_id))
        except Exception:
            async with SessionFactory.begin() as session:
                await session.execute(delete(ParsingRun).where(ParsingRun.document_id == document_id))
                await session.execute(delete(Document).where(Document.id == document_id))
                await session.execute(delete(User).where(User.id == user_id))
            raise
        assert ref is not None
    asyncio.run(run_test())


def test_parsed_artifact_ref_rejects_old_schema_identity() -> None:
    with pytest.raises(ValidationError):
        ParsedArtifactRef(
            parsing_run_id=uuid4(), source_type="DOCUMENT", source_id=uuid4(),
            storage_key="parsed/documents/source/run/parsed_cleaned.json",
            schema_version="ParsedCleanedArtifact/v1",
        )


def test_lesson_parse_uses_snapshot_without_document_lifecycle(storage_root) -> None:
    async def run_test() -> None:
        user_id, level_id, lesson_id = uuid4(), uuid4(), uuid4()
        level_number = 1000 + level_id.int % 1_000_000
        lesson_snapshot = {
            "schema_version": "raw_lesson_snapshot/v1",
            "lesson": {"id": str(lesson_id), "hsk": {"id": str(level_id), "level_number": level_number, "title": "HSK"},
                       "lesson_number": 1, "title": "Snapshot title", "description": None, "status": "PUBLISHED"},
            "vocabulary": [], "grammar": [],
        }
        raw = json.dumps(lesson_snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(raw).hexdigest()
        storage = LocalFileStorage(storage_root)
        storage.write_bytes("lessons/source/raw.json", raw)
        async with SessionFactory.begin() as session:
            session.add(User(id=user_id, email=f"step53-{user_id}@example.invalid", password_hash="unused", full_name="Test", role="ADMIN"))
            await session.flush()
            session.add(HSKLevel(id=level_id, level_number=level_number, title="Live HSK", order_index=1))
            await session.flush()
            session.add(Lesson(id=lesson_id, hsk_level_id=level_id, lesson_number=1, title="Live title", status="DRAFT"))
        try:
            async with SessionFactory() as session:
                ref = await parse_raw_artifact(RawArtifactRef(
                    source_type="LESSON", source_id=lesson_id, storage_key="lessons/source/raw.json",
                    file_format="JSON", mime_type="application/json", file_size_bytes=len(raw), content_hash=digest,
                ), session=session, storage=storage)
            with storage.open(ref.storage_key) as handle:
                artifact = json.loads(handle.read())
            assert artifact["units"][0]["text"] == "Snapshot title"
            async with SessionFactory() as session:
                run = await session.get(ParsingRun, ref.parsing_run_id)
                assert run.lesson_id == lesson_id and run.document_id is None and run.status == "SUCCEEDED"
            async with SessionFactory.begin() as session:
                await session.execute(delete(ParsingRun).where(ParsingRun.lesson_id == lesson_id))
                await session.delete(await session.get(Lesson, lesson_id))
                await session.delete(await session.get(HSKLevel, level_id))
                await session.delete(await session.get(User, user_id))
        except Exception:
            async with SessionFactory.begin() as session:
                await session.execute(delete(ParsingRun).where(ParsingRun.lesson_id == lesson_id))
                await session.execute(delete(Lesson).where(Lesson.id == lesson_id))
                await session.execute(delete(HSKLevel).where(HSKLevel.id == level_id))
                await session.execute(delete(User).where(User.id == user_id))
            raise
    asyncio.run(run_test())


def test_final_success_state_failure_deletes_orphan_parsed_artifact(storage_root, monkeypatch) -> None:
    async def run_test() -> None:
        user_id, document_id = uuid4(), uuid4()
        raw = b"valid input"
        digest = hashlib.sha256(raw).hexdigest()
        storage = LocalFileStorage(storage_root)
        storage.write_bytes("documents/test/raw.txt", raw)
        async with SessionFactory.begin() as session:
            session.add(User(id=user_id, email=f"step53-{user_id}@example.invalid", password_hash="unused", full_name="Test", role="ADMIN"))
            await session.flush()
            session.add(Document(id=document_id, original_filename="raw.txt", file_type="TXT", storage_reference="documents/test/raw.txt",
                                 mime_type="text/plain", file_size_bytes=len(raw), content_hash=digest,
                                 processing_status="UPLOADED", review_status="PENDING", uploaded_by=user_id))
        original_get = repository.get_parsing_run
        calls = 0

        async def fail_success_lookup(session, run_id):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("simulated final state failure")
            return await original_get(session, run_id)

        monkeypatch.setattr(repository, "get_parsing_run", fail_success_lookup)
        try:
            async with SessionFactory() as session:
                with pytest.raises(ApplicationError) as error:
                    await parse_raw_artifact(RawArtifactRef(
                        source_type="DOCUMENT", source_id=document_id, storage_key="documents/test/raw.txt",
                        file_format="TXT", mime_type="text/plain", file_size_bytes=len(raw), content_hash=digest,
                    ), session=session, storage=storage)
            assert error.value.code == "PARSING_FAILED"
            assert storage.open("documents/test/raw.txt").read() == raw
            assert list(storage_root.rglob("parsed_cleaned.json")) == []
            async with SessionFactory() as session:
                run = await session.scalar(select(ParsingRun).where(ParsingRun.document_id == document_id))
                assert run.status == "FAILED" and run.error_code == "PARSING_FAILED"
                assert run.parsed_storage_reference is None
            async with SessionFactory.begin() as session:
                await session.execute(delete(ParsingRun).where(ParsingRun.document_id == document_id))
                await session.execute(delete(Document).where(Document.id == document_id))
                await session.execute(delete(User).where(User.id == user_id))
        except Exception:
            async with SessionFactory.begin() as session:
                await session.execute(delete(ParsingRun).where(ParsingRun.document_id == document_id))
                await session.execute(delete(Document).where(Document.id == document_id))
                await session.execute(delete(User).where(User.id == user_id))
            raise
    asyncio.run(run_test())


def test_parse_failure_keeps_raw_and_marks_document_failed(storage_root) -> None:
    async def run_test() -> None:
        user_id, document_id = uuid4(), uuid4()
        raw = b"not utf-8: \xff"
        digest = hashlib.sha256(raw).hexdigest()
        storage = LocalFileStorage(storage_root)
        storage.write_bytes("documents/test/raw.txt", raw)
        async with SessionFactory.begin() as session:
            session.add(User(id=user_id, email=f"step53-{user_id}@example.invalid", password_hash="unused", full_name="Test", role="ADMIN"))
            await session.flush()
            session.add(Document(id=document_id, original_filename="raw.txt", file_type="TXT", storage_reference="documents/test/raw.txt",
                                 mime_type="text/plain", file_size_bytes=len(raw), content_hash=digest,
                                 processing_status="UPLOADED", review_status="PENDING", uploaded_by=user_id))
        try:
            async with SessionFactory() as session:
                with pytest.raises(ApplicationError) as error:
                    await parse_raw_artifact(RawArtifactRef(source_type="DOCUMENT", source_id=document_id,
                        storage_key="documents/test/raw.txt", file_format="TXT", mime_type="text/plain",
                        file_size_bytes=len(raw), content_hash=digest), session=session, storage=storage)
                assert error.value.code == "TEXT_DECODING_FAILED"
            assert storage.open("documents/test/raw.txt").read() == raw
            async with SessionFactory() as session:
                run = await session.scalar(select(ParsingRun).where(ParsingRun.document_id == document_id))
                doc = await session.get(Document, document_id)
                assert run.status == "FAILED" and run.error_code == "TEXT_DECODING_FAILED"
                assert run.parsed_storage_reference is None and doc.processing_status == "FAILED"
            async with SessionFactory.begin() as session:
                await session.execute(delete(ParsingRun).where(ParsingRun.document_id == document_id))
                await session.execute(delete(Document).where(Document.id == document_id))
                await session.execute(delete(User).where(User.id == user_id))
        except Exception:
            async with SessionFactory.begin() as session:
                await session.execute(delete(ParsingRun).where(ParsingRun.document_id == document_id))
                await session.execute(delete(Document).where(Document.id == document_id))
                await session.execute(delete(User).where(User.id == user_id))
            raise
    asyncio.run(run_test())


def test_unsupported_document_format_is_recorded_as_stable_failure(storage_root) -> None:
    async def run_test() -> None:
        user_id, document_id = uuid4(), uuid4()
        raw = b"unsupported format bytes"
        digest = hashlib.sha256(raw).hexdigest()
        storage = LocalFileStorage(storage_root)
        storage.write_bytes("documents/test/raw.csv", raw)
        async with SessionFactory.begin() as session:
            session.add(User(id=user_id, email=f"step53-{user_id}@example.invalid", password_hash="unused", full_name="Test", role="ADMIN"))
            await session.flush()
            session.add(Document(id=document_id, original_filename="raw.csv", file_type="CSV", storage_reference="documents/test/raw.csv",
                                 mime_type="text/csv", file_size_bytes=len(raw), content_hash=digest,
                                 processing_status="UPLOADED", review_status="PENDING", uploaded_by=user_id))
        try:
            async with SessionFactory() as session:
                with pytest.raises(ApplicationError) as error:
                    await parse_raw_artifact(RawArtifactRef(source_type="DOCUMENT", source_id=document_id,
                        storage_key="documents/test/raw.csv", file_format="CSV", mime_type="text/csv",
                        file_size_bytes=len(raw), content_hash=digest), session=session, storage=storage)
            assert error.value.code == "UNSUPPORTED_PARSER"
            assert storage.open("documents/test/raw.csv").read() == raw
            async with SessionFactory() as session:
                run = await session.scalar(select(ParsingRun).where(ParsingRun.document_id == document_id))
                doc = await session.get(Document, document_id)
                assert run.status == "FAILED" and run.error_code == "UNSUPPORTED_PARSER"
                assert doc.processing_status == "FAILED" and run.parsed_storage_reference is None
            async with SessionFactory.begin() as session:
                await session.execute(delete(ParsingRun).where(ParsingRun.document_id == document_id))
                await session.execute(delete(Document).where(Document.id == document_id))
                await session.execute(delete(User).where(User.id == user_id))
        except Exception:
            async with SessionFactory.begin() as session:
                await session.execute(delete(ParsingRun).where(ParsingRun.document_id == document_id))
                await session.execute(delete(Document).where(Document.id == document_id))
                await session.execute(delete(User).where(User.id == user_id))
            raise
    asyncio.run(run_test())


def test_parsed_artifact_finalization_failure_cleans_temp_and_preserves_raw(storage_root) -> None:
    class FinalizeFailureStorage(LocalFileStorage):
        def finalize(self, temp_key: str, storage_key: str) -> str:
            if storage_key.startswith("parsed/"):
                raise OSError("injected finalization failure")
            return super().finalize(temp_key, storage_key)

    async def run_test() -> None:
        user_id, document_id = uuid4(), uuid4()
        raw = b"Finalization failure fixture"
        digest = hashlib.sha256(raw).hexdigest()
        storage = FinalizeFailureStorage(storage_root)
        storage.write_bytes("documents/test/raw.txt", raw)
        async with SessionFactory.begin() as session:
            session.add(User(id=user_id, email=f"step53-{user_id}@example.invalid", password_hash="unused", full_name="Test", role="ADMIN"))
            await session.flush()
            session.add(Document(id=document_id, original_filename="raw.txt", file_type="TXT", storage_reference="documents/test/raw.txt",
                                 mime_type="text/plain", file_size_bytes=len(raw), content_hash=digest,
                                 processing_status="UPLOADED", review_status="PENDING", uploaded_by=user_id))
        try:
            async with SessionFactory() as session:
                with pytest.raises(ApplicationError) as error:
                    await parse_raw_artifact(RawArtifactRef(source_type="DOCUMENT", source_id=document_id,
                        storage_key="documents/test/raw.txt", file_format="TXT", mime_type="text/plain",
                        file_size_bytes=len(raw), content_hash=digest), session=session, storage=storage)
            assert error.value.code == "PARSING_FAILED"
            assert storage.open("documents/test/raw.txt").read() == raw
            assert list(storage.temp_root.iterdir()) == []
            assert list((storage.root / "parsed").rglob("parsed_cleaned.json")) == []
            async with SessionFactory() as session:
                run = await session.scalar(select(ParsingRun).where(ParsingRun.document_id == document_id))
                doc = await session.get(Document, document_id)
                assert run.status == "FAILED" and run.error_code == "PARSING_FAILED"
                assert run.parsed_storage_reference is None and doc.processing_status == "FAILED"
            async with SessionFactory.begin() as session:
                await session.execute(delete(ParsingRun).where(ParsingRun.document_id == document_id))
                await session.execute(delete(Document).where(Document.id == document_id))
                await session.execute(delete(User).where(User.id == user_id))
        except Exception:
            async with SessionFactory.begin() as session:
                await session.execute(delete(ParsingRun).where(ParsingRun.document_id == document_id))
                await session.execute(delete(Document).where(Document.id == document_id))
                await session.execute(delete(User).where(User.id == user_id))
            raise
    asyncio.run(run_test())
