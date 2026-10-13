import asyncio
import json
import shutil
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.errors import ApplicationError
from app.database.models import (
    Document, HSKLevel, Lesson, ParsingRun, TransformationRun, User,
)
from app.database.session import SessionFactory
from app.ingestion.schemas import ParsedArtifactRef, TransformedArtifactRef
from app.ingestion.storage import LocalFileStorage
from app.ingestion.transformation import document_transformer
from app.ingestion.transformation import service as transformation_service
from app.ingestion.transformation.service import (
    load_transformed_artifact,
    transform_parsed_artifact,
)


@pytest.fixture
def storage_root():
    path = Path(__file__).resolve().parents[2] / "tmp" / f"step54-tests-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    yield path
    shutil.rmtree(path, ignore_errors=True)


async def _seed_source(storage: LocalFileStorage, source_type: str, *, metadata=True):
    user_id, level_id, lesson_id, source_id, parsing_id = [uuid4() for _ in range(5)]
    source_id = source_id if source_type == "DOCUMENT" else lesson_id
    parsed_key = f"parsed/{source_type.lower()}/{source_id}/parsed_cleaned_artifact.json"
    storage.write_bytes("raw/source", b"preserved raw artifact")
    units = ([{"order": 0, "text": "A long paragraph. A long paragraph.", "source_locator": {"kind": "TEXT_BLOCK", "block_index": 0}}]
             if source_type == "DOCUMENT" else [
                 {"order": 0, "text": "Persisted lesson title", "source_locator": {
                     "kind": "LESSON_FIELD", "section": "LESSON", "entity_id": str(lesson_id), "field": "title"}},
                 {"order": 1, "text": "hello", "source_locator": {
                     "kind": "LESSON_FIELD", "section": "VOCABULARY", "entity_id": str(uuid4()),
                     "field": "hanzi", "order_index": 0}},
             ])
    artifact = {
        "schema_version": "parsed_cleaned_artifact/v1", "source_type": source_type,
        "source_id": str(source_id), "raw_content_hash": "d" * 64,
        "parser_name": "test", "parser_version": "v1", "cleaning_strategy": "test",
        "cleaning_version": "v1", "units": units,
    }
    storage.write_bytes(parsed_key, json.dumps(artifact, ensure_ascii=False).encode("utf-8"))
    async with SessionFactory.begin() as session:
        session.add(User(id=user_id, email=f"step54-{user_id}@example.invalid", password_hash="unused",
                         full_name="Step 5.4", role="ADMIN"))
        await session.flush()
        session.add(HSKLevel(id=level_id, level_number=3_000_000 + level_id.int % 1_000_000,
                             order_index=3_000_000 + level_id.int % 1_000_000))
        await session.flush()
        session.add(Lesson(id=lesson_id, hsk_level_id=level_id, lesson_number=1,
                           title="Live lesson title", status="PUBLISHED"))
        if source_type == "DOCUMENT":
            session.add(Document(
                id=source_id, original_filename="original.txt", file_type="TXT", storage_reference="raw/source",
                mime_type="text/plain", file_size_bytes=12, content_hash=uuid4().hex,
                processing_status="UPLOADED", review_status="PENDING", uploaded_by=user_id,
                title="Snapshot document title" if metadata else None,
                source_category="INTERNAL_AUTHORED" if metadata else None,
                source_origin="Seeded source" if metadata else None,
                source_language="zh" if metadata else None,
                usage_rights_note="Private study" if metadata else None,
            ))
        await session.flush()
        session.add(ParsingRun(
            id=parsing_id, source_type=source_type,
            document_id=source_id if source_type == "DOCUMENT" else None,
            lesson_id=source_id if source_type == "LESSON" else None,
            raw_storage_reference="raw/source", raw_content_hash="d" * 64,
            parser_name="test", parser_version="v1", cleaning_strategy="test", cleaning_version="v1",
            status="SUCCEEDED", parsed_storage_reference=parsed_key,
        ))
    return {
        "user_id": user_id, "level_id": level_id, "lesson_id": lesson_id,
        "source_id": source_id, "parsing_id": parsing_id,
        "ref": ParsedArtifactRef(parsing_run_id=parsing_id, source_type=source_type,
                                 source_id=source_id, storage_key=parsed_key,
                                 schema_version="parsed_cleaned_artifact/v1"),
    }


async def _cleanup(source):
    async with SessionFactory.begin() as session:
        await session.execute(
            TransformationRun.__table__.delete().where(
                (TransformationRun.document_id == source["source_id"])
                | (TransformationRun.lesson_id == source["source_id"])
            )
        )
        await session.execute(ParsingRun.__table__.delete().where(ParsingRun.id == source["parsing_id"]))
        if source.get("source_type") == "DOCUMENT":
            await session.execute(Document.__table__.delete().where(Document.id == source["source_id"]))
        await session.execute(Lesson.__table__.delete().where(Lesson.id == source["lesson_id"]))
        await session.execute(HSKLevel.__table__.delete().where(HSKLevel.id == source["level_id"]))
        await session.execute(User.__table__.delete().where(User.id == source["user_id"]))


def _with_type(source, source_type):
    source["source_type"] = source_type
    return source


def test_document_runs_are_new_each_invocation_deterministic_and_load_without_rerun(storage_root: Path, monkeypatch):
    async def verify():
        storage = LocalFileStorage(storage_root / "storage")
        source = _with_type(await _seed_source(storage, "DOCUMENT"), "DOCUMENT")
        try:
            async with SessionFactory() as session:
                first = await transform_parsed_artifact(source["ref"], session=session, storage=storage)
            async with SessionFactory() as session:
                second = await transform_parsed_artifact(source["ref"], session=session, storage=storage)
            assert first.transformation_run_id != second.transformation_run_id
            with storage.open(first.storage_key) as handle:
                first_bytes = handle.read()
            with storage.open(second.storage_key) as handle:
                second_bytes = handle.read()
            assert first_bytes == second_bytes
            assert first_bytes == json.dumps(json.loads(first_bytes), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            loaded = load_transformed_artifact(first, storage=storage)
            assert b"transformation_run_id" not in first_bytes
            assert b"created_at" not in first_bytes and b"updated_at" not in first_bytes
            assert first.storage_key != second.storage_key
            assert loaded.title == "Snapshot document title"
            assert loaded.source_language == "zh"
            assert loaded.source_category == "INTERNAL_AUTHORED"
            assert loaded.provenance.model_dump(mode="json", exclude_none=True) == {
                "source_origin": "Seeded source", "usage_rights_note": "Private study",
                "original_filename": "original.txt",
            }
            assert loaded.blocks[0].text == "A long paragraph. A long paragraph."
            assert len(loaded.blocks) == 1
            async with SessionFactory() as session:
                runs = list((await session.scalars(
                    select(TransformationRun).where(TransformationRun.document_id == source["source_id"])
                )).all())
                document = await session.get(Document, source["source_id"])
                assert len(runs) == 2
                assert all(run.status == "SUCCEEDED" and run.error_code is None for run in runs)
                assert all(run.parsing_run_id == source["parsing_id"] for run in runs)
                assert all(run.source_metadata_snapshot["title"] == "Snapshot document title" for run in runs)
                assert document.processing_status == "PREVIEW_READY"
            monkeypatch.setattr(document_transformer, "transform_document", lambda *_: pytest.fail("load reran transformation"))
            assert load_transformed_artifact(first, storage=storage).title == "Snapshot document title"
        finally:
            await _cleanup(source)
    asyncio.run(verify())


def test_lesson_uses_persisted_parsed_snapshot_and_has_no_document_lifecycle(storage_root: Path):
    async def verify():
        storage = LocalFileStorage(storage_root / "storage")
        source = _with_type(await _seed_source(storage, "LESSON"), "LESSON")
        try:
            async with SessionFactory() as session:
                ref = await transform_parsed_artifact(source["ref"], session=session, storage=storage)
            result = load_transformed_artifact(ref, storage=storage)
            assert result.title == "Persisted lesson title"
            assert result.source_language is result.source_category is None
            assert result.blocks[0].text == "Từ: hello"
            async with SessionFactory() as session:
                run = await session.get(TransformationRun, ref.transformation_run_id)
                assert run.status == "SUCCEEDED"
                assert run.lesson_id == source["source_id"] and run.document_id is None
                assert run.source_metadata_snapshot["title"] == "Persisted lesson title"
                assert await session.get(Document, source["source_id"]) is None
        finally:
            await _cleanup(source)
    asyncio.run(verify())


def test_missing_document_metadata_fails_without_fallback(storage_root: Path):
    async def verify():
        storage = LocalFileStorage(storage_root / "storage")
        source = _with_type(await _seed_source(storage, "DOCUMENT", metadata=False), "DOCUMENT")
        try:
            async with SessionFactory() as session:
                with pytest.raises(ApplicationError) as raised:
                    await transform_parsed_artifact(source["ref"], session=session, storage=storage)
            assert raised.value.code == "TRANSFORMATION_FAILED"
            async with SessionFactory() as session:
                runs = list((await session.scalars(
                    select(TransformationRun).where(TransformationRun.document_id == source["source_id"])
                )).all())
                document = await session.get(Document, source["source_id"])
                assert len(runs) == 1 and runs[0].status == "FAILED"
                assert runs[0].transformed_storage_reference is None and runs[0].error_code == "TRANSFORMATION_FAILED"
                assert document.processing_status == "FAILED"
        finally:
            await _cleanup(source)
    asyncio.run(verify())


def test_invalid_canonical_output_marks_run_failed(storage_root: Path, monkeypatch):
    async def verify():
        storage = LocalFileStorage(storage_root / "storage")
        source = _with_type(await _seed_source(storage, "DOCUMENT"), "DOCUMENT")
        monkeypatch.setattr(document_transformer, "transform_document", lambda *_: {"blocks": "not a canonical array"})
        try:
            async with SessionFactory() as session:
                with pytest.raises(ApplicationError) as raised:
                    await transform_parsed_artifact(source["ref"], session=session, storage=storage)
            assert raised.value.code == "INVALID_TRANSFORMED_DOCUMENT"
            async with SessionFactory() as session:
                run = await session.scalar(select(TransformationRun).where(
                    TransformationRun.document_id == source["source_id"]))
                document = await session.get(Document, source["source_id"])
                assert run.status == "FAILED" and run.error_code == "INVALID_TRANSFORMED_DOCUMENT"
                assert document.processing_status == "FAILED"
            with storage.open(source["ref"].storage_key) as handle:
                assert handle.read()
            with storage.open("raw/source") as handle:
                assert handle.read() == b"preserved raw artifact"
        finally:
            await _cleanup(source)
    asyncio.run(verify())


def test_storage_finalization_failure_marks_run_failed(storage_root: Path):
    class FinalizeFailsStorage(LocalFileStorage):
        def finalize(self, temp_key, storage_key):
            if storage_key.startswith("transformed/"):
                finalized = super().finalize(temp_key, storage_key)
                assert finalized == storage_key
                raise OSError("simulated finalization failure")
            return super().finalize(temp_key, storage_key)

    async def verify():
        storage = FinalizeFailsStorage(storage_root / "storage")
        source = _with_type(await _seed_source(storage, "DOCUMENT"), "DOCUMENT")
        try:
            async with SessionFactory() as session:
                with pytest.raises(ApplicationError) as raised:
                    await transform_parsed_artifact(source["ref"], session=session, storage=storage)
            assert raised.value.code == "TRANSFORMATION_FAILED"
            async with SessionFactory() as session:
                run = await session.scalar(select(TransformationRun).where(
                    TransformationRun.document_id == source["source_id"]))
                document = await session.get(Document, source["source_id"])
                assert run.status == "FAILED" and run.transformed_storage_reference is None
                assert document.processing_status == "FAILED"
            assert not list((storage_root / "storage" / "transformed").rglob("*.json"))
            with storage.open(source["ref"].storage_key) as handle:
                assert handle.read()
            with storage.open("raw/source") as handle:
                assert handle.read() == b"preserved raw artifact"
        finally:
            await _cleanup(source)
    asyncio.run(verify())


def test_database_success_state_failure_removes_orphan_artifact(storage_root: Path, monkeypatch):
    from app.ingestion import repository

    original = repository.get_transformation_run
    calls = 0

    async def fail_success_lookup(session, run_id):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated database persistence failure")
        return await original(session, run_id)

    async def verify():
        storage = LocalFileStorage(storage_root / "storage")
        source = _with_type(await _seed_source(storage, "DOCUMENT"), "DOCUMENT")
        monkeypatch.setattr(repository, "get_transformation_run", fail_success_lookup)
        try:
            async with SessionFactory() as session:
                with pytest.raises(ApplicationError) as raised:
                    await transform_parsed_artifact(source["ref"], session=session, storage=storage)
            assert raised.value.code == "TRANSFORMATION_FAILED"
            async with SessionFactory() as session:
                run = await session.scalar(select(TransformationRun).where(
                    TransformationRun.document_id == source["source_id"]))
                document = await session.get(Document, source["source_id"])
                assert run.status == "FAILED" and run.transformed_storage_reference is None
                assert document.processing_status == "FAILED"
            assert not list((storage_root / "storage" / "transformed").rglob("*.json"))
            with storage.open(source["ref"].storage_key) as handle:
                assert handle.read()
            with storage.open("raw/source") as handle:
                assert handle.read() == b"preserved raw artifact"
        finally:
            monkeypatch.setattr(repository, "get_transformation_run", original)
            await _cleanup(source)
    asyncio.run(verify())


def test_reference_must_match_the_exact_successful_parsing_run(storage_root: Path):
    async def verify():
        storage = LocalFileStorage(storage_root / "storage")
        source = _with_type(await _seed_source(storage, "DOCUMENT"), "DOCUMENT")
        invalid = source["ref"].model_copy(update={"parsing_run_id": uuid4()})
        try:
            async with SessionFactory() as session:
                with pytest.raises(ApplicationError) as raised:
                    await transform_parsed_artifact(invalid, session=session, storage=storage)
            assert raised.value.code == "TRANSFORMATION_FAILED"
            async with SessionFactory() as session:
                assert await session.scalar(select(TransformationRun).where(
                    TransformationRun.document_id == source["source_id"])) is None
        finally:
            await _cleanup(source)
    asyncio.run(verify())


def test_parsed_payload_source_must_match_supplied_reference(storage_root: Path):
    async def verify():
        storage = LocalFileStorage(storage_root / "storage")
        source = _with_type(await _seed_source(storage, "DOCUMENT"), "DOCUMENT")
        mismatched = source["ref"].model_copy(update={"source_id": uuid4()})
        try:
            async with SessionFactory() as session:
                with pytest.raises(ApplicationError) as raised:
                    await transform_parsed_artifact(mismatched, session=session, storage=storage)
            assert raised.value.code == "INVALID_SOURCE_LOCATOR"
            async with SessionFactory() as session:
                assert await session.scalar(select(TransformationRun).where(
                    TransformationRun.document_id == source["source_id"])) is None
        finally:
            await _cleanup(source)
    asyncio.run(verify())


@pytest.mark.parametrize("mismatch", ["status", "storage_reference", "source_type", "document_target", "lesson_target"])
def test_service_rejects_parsing_run_lineage_mismatches(storage_root: Path, mismatch: str):
    async def verify():
        storage = LocalFileStorage(storage_root / "storage")
        source_type = "LESSON" if mismatch == "lesson_target" else "DOCUMENT"
        source = _with_type(await _seed_source(storage, source_type), source_type)
        try:
            async with SessionFactory.begin() as session:
                parsing = await session.get(ParsingRun, source["parsing_id"])
                if mismatch == "status":
                    parsing.status = "PROCESSING"
                elif mismatch == "storage_reference":
                    parsing.parsed_storage_reference = "parsed/a-different-artifact.json"
                elif mismatch == "source_type":
                    parsing.source_type = "LESSON"
                    parsing.document_id = None
                    parsing.lesson_id = source["lesson_id"]
                elif mismatch == "document_target":
                    alternate_id = uuid4()
                    session.add(Document(
                        id=alternate_id, original_filename="alternate.txt", file_type="TXT",
                        storage_reference="raw/alternate", mime_type="text/plain", file_size_bytes=10,
                        content_hash=uuid4().hex, processing_status="UPLOADED", review_status="PENDING",
                        uploaded_by=source["user_id"], title="Alternate", source_category="INTERNAL_AUTHORED",
                        source_origin="Alternate", source_language="zh",
                    ))
                    await session.flush()
                    parsing.document_id = alternate_id
                    source["alternate_id"] = alternate_id
                elif mismatch == "lesson_target":
                    alternate_lesson = uuid4()
                    session.add(Lesson(
                        id=alternate_lesson, hsk_level_id=source["level_id"], lesson_number=2,
                        title="Alternate lesson", status="PUBLISHED",
                    ))
                    await session.flush()
                    parsing.lesson_id = alternate_lesson
                    source["alternate_id"] = alternate_lesson

            async with SessionFactory() as session:
                with pytest.raises(ApplicationError) as raised:
                    await transform_parsed_artifact(source["ref"], session=session, storage=storage)
            assert raised.value.code == "TRANSFORMATION_FAILED"
            async with SessionFactory() as session:
                assert await session.scalar(select(TransformationRun).where(
                    (TransformationRun.document_id == source["source_id"])
                    | (TransformationRun.lesson_id == source["source_id"]))) is None
        finally:
            if source.get("alternate_id"):
                async with SessionFactory.begin() as session:
                    if mismatch == "document_target":
                        await session.execute(Document.__table__.delete().where(Document.id == source["alternate_id"]))
                    else:
                        await session.execute(Lesson.__table__.delete().where(Lesson.id == source["alternate_id"]))
            await _cleanup(source)
    asyncio.run(verify())


def test_persisted_malformed_transformed_json_is_rejected_by_actual_loader(storage_root: Path):
    storage = LocalFileStorage(storage_root / "storage")
    source_id = uuid4()
    key = "transformed/documents/malformed.json"
    malformed = {
        "schema_version": "transformed_document/v1", "source_type": "DOCUMENT", "source_id": str(source_id),
        "title": "Malformed", "source_language": "zh", "source_category": "INTERNAL_AUTHORED",
        "transformation_strategy": "canonical_document", "transformation_version": "v1",
        "provenance": {"source_origin": "test"},
        "blocks": [{"order": 0, "content_type": "DOCUMENT_TEXT", "block_kind": "PARAGRAPH",
                    "text": "x", "section_path": [], "source_locator": {"anything": "goes"},
                    "structured_data": {}, "metadata": {}}],
    }
    storage.write_bytes(key, json.dumps(malformed).encode("utf-8"))
    ref = TransformedArtifactRef(
        transformation_run_id=uuid4(), source_type="DOCUMENT", source_id=source_id,
        storage_key=key, schema_version="transformed_document/v1",
    )
    with pytest.raises(ApplicationError) as raised:
        load_transformed_artifact(ref, storage=storage)
    assert raised.value.code == "INVALID_TRANSFORMED_DOCUMENT"
    assert raised.value.details is None
    assert "ValidationError" not in raised.value.message


def test_source_metadata_is_snapshotted_before_live_document_changes(storage_root: Path, monkeypatch):
    from app.ingestion import repository

    async def verify():
        storage = LocalFileStorage(storage_root / "storage")
        source = _with_type(await _seed_source(storage, "DOCUMENT"), "DOCUMENT")
        original = transformation_service._snapshot_values
        original_get_run = repository.get_transformation_run

        def snapshot_then_mutate(parsed, live_source):
            values = original(parsed, live_source)
            live_source.title = "Changed after invocation snapshot"
            live_source.source_origin = "Changed source"
            return values

        async def assert_processing_state(session, run_id):
            run = await original_get_run(session, run_id)
            if run.status == "PROCESSING":
                document = await repository.get_document(session, source["source_id"])
                assert document.processing_status == "PROCESSING"
            return run

        monkeypatch.setattr(transformation_service, "_snapshot_values", snapshot_then_mutate)
        monkeypatch.setattr(repository, "get_transformation_run", assert_processing_state)
        try:
            async with SessionFactory() as session:
                ref = await transform_parsed_artifact(source["ref"], session=session, storage=storage)
            transformed = load_transformed_artifact(ref, storage=storage)
            assert transformed.title == "Snapshot document title"
            assert transformed.provenance.source_origin == "Seeded source"
            async with SessionFactory() as session:
                run = await session.get(TransformationRun, ref.transformation_run_id)
                live_document = await session.get(Document, source["source_id"])
                assert run.source_metadata_snapshot["title"] == "Snapshot document title"
                assert live_document.title == "Changed after invocation snapshot"
        finally:
            monkeypatch.setattr(repository, "get_transformation_run", original_get_run)
            await _cleanup(source)
    asyncio.run(verify())
