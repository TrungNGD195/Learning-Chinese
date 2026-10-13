import asyncio
import json
from io import BytesIO
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.core.errors import ApplicationError
from app.database.models import (
    Chunk, Document, HSKLevel, KnowledgeSource, KnowledgeVersion, Lesson, ParsingRun, TransformationRun, User,
)
from app.database.session import SessionFactory
from app.ingestion import repository
from app.ingestion.chunking.service import _validate_version_source, build_chunks
from app.ingestion.schemas import TransformedArtifactRef
from app.ingestion.transformation.models import TransformedDocument


class MemoryStorage:
    def __init__(self, payload: bytes):
        self.payload = payload

    def open(self, key: str):
        assert key == "transformed/test/artifact.json"
        return BytesIO(self.payload)


def _artifact(lesson_id, text="Persisted transformed text") -> bytes:
    document = TransformedDocument.model_validate({
        "schema_version": "transformed_document/v1", "source_type": "LESSON", "source_id": lesson_id,
        "title": "Lesson snapshot", "source_language": None, "source_category": None,
        "transformation_strategy": "canonical_document", "transformation_version": "v1", "provenance": {},
        "blocks": [{"order": 0, "content_type": "LESSON_GENERAL", "block_kind": "LESSON_GENERAL",
                    "text": text, "section_path": ["Lesson"],
                    "source_locator": {"kind": "LESSON_ENTITY", "section": "LESSON", "entity_id": str(lesson_id),
                                       "fields": [{"kind": "LESSON_FIELD", "section": "LESSON",
                                                   "entity_id": str(lesson_id), "field": "description"}]},
                    "structured_data": {}, "metadata": {}}],
    })
    return json.dumps(document.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


@pytest.fixture
def chunking_context():
    ids = {key: uuid4() for key in (
        "lesson", "other_lesson", "level", "source", "version", "parsing", "transformation",
        "user", "document", "document_parsing", "document_transformation",
    )}
    ids["level_number"] = 1000000 + ids["level"].int % 1000000
    ref = TransformedArtifactRef(
        transformation_run_id=ids["transformation"], source_type="LESSON", source_id=ids["lesson"],
        storage_key="transformed/test/artifact.json", schema_version="transformed_document/v1",
    )

    async def create():
        async with SessionFactory.begin() as session:
            session.add(HSKLevel(id=ids["level"], level_number=ids["level_number"], order_index=ids["level_number"]))
            await session.flush()
            session.add(Lesson(id=ids["lesson"], hsk_level_id=ids["level"], lesson_number=1,
                               title="Lesson", status="PUBLISHED"))
            session.add(Lesson(id=ids["other_lesson"], hsk_level_id=ids["level"], lesson_number=2,
                               title="Other lesson", status="PUBLISHED"))
            await session.flush()
            session.add(KnowledgeSource(id=ids["source"], source_type="LESSON", lesson_id=ids["lesson"]))
            session.add(KnowledgeVersion(id=ids["version"], knowledge_source_id=ids["source"], version_number=1,
                                         status="PROCESSING"))
            await session.flush()
            session.add(ParsingRun(
                id=ids["parsing"], source_type="LESSON", lesson_id=ids["lesson"], raw_storage_reference="raw/key",
                raw_content_hash="a" * 64, parser_name="test", parser_version="v1", cleaning_strategy="test",
                cleaning_version="v1", status="SUCCEEDED", parsed_storage_reference="parsed/key",
            ))
            await session.flush()
            session.add(TransformationRun(
                id=ids["transformation"], source_type="LESSON", lesson_id=ids["lesson"],
                parsing_run_id=ids["parsing"], parsed_storage_reference="parsed/key",
                transformation_strategy="canonical_document", transformation_version="v1", status="SUCCEEDED",
                transformed_storage_reference=ref.storage_key, source_metadata_snapshot={},
            ))
            session.add(User(id=ids["user"], email=f"chunk-test-{ids['user']}@example.invalid",
                             password_hash="test-only", full_name="Chunk Test", role="ADMIN"))
            await session.flush()
            session.add(Document(
                id=ids["document"], original_filename="source.txt", file_type="TXT",
                storage_reference="raw/document.txt", processing_status="PREVIEW_READY",
                review_status="PENDING", uploaded_by=ids["user"],
            ))
            await session.flush()
            session.add(ParsingRun(
                id=ids["document_parsing"], source_type="DOCUMENT", document_id=ids["document"],
                raw_storage_reference="raw/document.txt", raw_content_hash="b" * 64,
                parser_name="test", parser_version="v1", cleaning_strategy="test", cleaning_version="v1",
                status="SUCCEEDED", parsed_storage_reference="parsed/document.json",
            ))
            await session.flush()
            session.add(TransformationRun(
                id=ids["document_transformation"], source_type="DOCUMENT", document_id=ids["document"],
                parsing_run_id=ids["document_parsing"], parsed_storage_reference="parsed/document.json",
                transformation_strategy="canonical_document", transformation_version="v1", status="SUCCEEDED",
                transformed_storage_reference="transformed/test/document.json", source_metadata_snapshot={},
            ))

    asyncio.run(create())
    context = {"ids": ids, "ref": ref, "storage": MemoryStorage(_artifact(ids["lesson"]))}
    yield context

    async def cleanup():
        async with SessionFactory.begin() as session:
            await session.execute(delete(Chunk).where(Chunk.knowledge_version_id == ids["version"]))
            await session.execute(delete(KnowledgeVersion).where(KnowledgeVersion.id == ids["version"]))
            await session.execute(delete(KnowledgeSource).where(KnowledgeSource.id == ids["source"]))
            await session.execute(delete(TransformationRun).where(TransformationRun.id == ids["transformation"]))
            await session.execute(delete(TransformationRun).where(
                TransformationRun.id == ids["document_transformation"]))
            await session.execute(delete(ParsingRun).where(ParsingRun.id == ids["parsing"]))
            await session.execute(delete(ParsingRun).where(ParsingRun.id == ids["document_parsing"]))
            await session.execute(delete(Lesson).where(Lesson.id == ids["lesson"]))
            await session.execute(delete(Lesson).where(Lesson.id == ids["other_lesson"]))
            await session.execute(delete(Document).where(Document.id == ids["document"]))
            await session.execute(delete(User).where(User.id == ids["user"]))
            await session.execute(delete(HSKLevel).where(HSKLevel.id == ids["level"]))
    asyncio.run(cleanup())


def test_step55_service_loads_exact_successful_artifact_and_persists_config(chunking_context):
    context = chunking_context
    async def build_and_check():
        async with SessionFactory() as session:
            result = await build_chunks(context["ref"], context["ids"]["version"], session=session, storage=context["storage"])
            assert result.chunks[0].content == "Persisted transformed text"
            version = await session.get(KnowledgeVersion, context["ids"]["version"])
            assert (version.status, version.chunking_strategy, version.chunking_version,
                    version.chunk_size, version.chunk_max_chars, version.chunk_overlap) == (
                "PROCESSING", "structure_aware", "v1", 1200, 1800, 150,
            )
            rows = (await session.execute(select(Chunk).where(Chunk.knowledge_version_id == context["ids"]["version"]))).scalars().all()
            assert len(rows) == 1
            assert rows[0].content_hash == result.chunks[0].content_hash
            assert rows[0].token_count is None
            assert rows[0].metadata_json["schema_version"] == "chunk_metadata/v1"
    asyncio.run(build_and_check())


def test_step55_rerun_replaces_the_same_version_chunk_set(chunking_context):
    context = chunking_context
    async def verify():
        async with SessionFactory() as session:
            first = await build_chunks(context["ref"], context["ids"]["version"], session=session, storage=context["storage"])
            second = await build_chunks(context["ref"], context["ids"]["version"], session=session, storage=context["storage"])
            rows = (await session.execute(select(Chunk).where(Chunk.knowledge_version_id == context["ids"]["version"]))).scalars().all()
            assert len(rows) == len(first.chunks) == len(second.chunks) == 1
            assert [row.chunk_index for row in rows] == [0]
            assert rows[0].content == first.chunks[0].content == second.chunks[0].content
    asyncio.run(verify())


def test_step55_replacement_failure_rolls_back_and_preserves_previous_complete_set(chunking_context, monkeypatch):
    context = chunking_context
    async def verify():
        async with SessionFactory() as session:
            await build_chunks(context["ref"], context["ids"]["version"], session=session, storage=context["storage"])
            old_content = (await session.execute(select(Chunk.content).where(
                Chunk.knowledge_version_id == context["ids"]["version"]))).scalar_one()

            original = repository.add_chunks
            async def fail_after_insert(session, version_id, values):
                await original(session, version_id, values)
                raise RuntimeError("private test-only persistence error")
            monkeypatch.setattr(repository, "add_chunks", fail_after_insert)
            with pytest.raises(ApplicationError) as raised:
                await build_chunks(context["ref"], context["ids"]["version"], session=session, storage=context["storage"])
            assert raised.value.code == "CHUNKING_FAILED"
            assert "private test-only" not in str(raised.value)
            rows = (await session.execute(select(Chunk).where(Chunk.knowledge_version_id == context["ids"]["version"]))).scalars().all()
            assert len(rows) == 1 and rows[0].content == old_content
    asyncio.run(verify())


def test_step55_final_flush_failure_rolls_back_replacement_and_preserves_config(chunking_context, monkeypatch):
    context = chunking_context
    async def verify():
        async with SessionFactory() as session:
            await build_chunks(context["ref"], context["ids"]["version"], session=session, storage=context["storage"])
        async with SessionFactory() as session:
            old_rows = (await session.execute(select(Chunk.id, Chunk.content, Chunk.content_hash).where(
                Chunk.knowledge_version_id == context["ids"]["version"]).order_by(Chunk.chunk_index))).all()
            version = await session.get(KnowledgeVersion, context["ids"]["version"])
            old_config = (version.status, version.chunking_strategy, version.chunking_version,
                          version.chunk_size, version.chunk_max_chars, version.chunk_overlap, version.activated_at)

            original_add = repository.add_chunks
            async def flush_then_fail_at_final_flush(active_session, version_id, values):
                await original_add(active_session, version_id, values)
                async def fail_final_flush():
                    raise RuntimeError("private test-only final flush error")
                monkeypatch.setattr(active_session, "flush", fail_final_flush)
            monkeypatch.setattr(repository, "add_chunks", flush_then_fail_at_final_flush)

            with pytest.raises(ApplicationError) as raised:
                await build_chunks(context["ref"], context["ids"]["version"], session=session,
                                   storage=context["storage"])
            assert raised.value.code == "CHUNKING_FAILED"
            assert raised.value.status_code == 500

        async with SessionFactory() as check_session:
            current_rows = (await check_session.execute(select(Chunk.id, Chunk.content, Chunk.content_hash).where(
                Chunk.knowledge_version_id == context["ids"]["version"]).order_by(Chunk.chunk_index))).all()
            current = await check_session.get(KnowledgeVersion, context["ids"]["version"])
            current_config = (current.status, current.chunking_strategy, current.chunking_version,
                              current.chunk_size, current.chunk_max_chars, current.chunk_overlap,
                              current.activated_at)
            assert current_rows == old_rows
            assert current_config == old_config
            assert current.status == "PROCESSING"
            assert current.activated_at is None
    asyncio.run(verify())


def test_step55_rejects_active_version_without_mutating_chunks(chunking_context):
    context = chunking_context
    async def verify():
        async with SessionFactory() as session:
            await build_chunks(context["ref"], context["ids"]["version"], session=session, storage=context["storage"])
            old_content = (await session.execute(select(Chunk.content).where(
                Chunk.knowledge_version_id == context["ids"]["version"]))).scalar_one()
            await session.rollback()
            async with session.begin():
                version = await session.get(KnowledgeVersion, context["ids"]["version"])
                version.status = "ACTIVE"
            with pytest.raises(ApplicationError) as raised:
                await build_chunks(context["ref"], context["ids"]["version"], session=session, storage=context["storage"])
            assert raised.value.code == "KNOWLEDGE_VERSION_NOT_PROCESSING"
            assert (await session.execute(select(Chunk.content).where(
                Chunk.knowledge_version_id == context["ids"]["version"]))).scalar_one() == old_content
    asyncio.run(verify())


def test_step55_rejects_wrong_exact_transformation_reference_before_storage_read(chunking_context):
    context = chunking_context
    wrong = context["ref"].model_copy(update={"storage_key": "transformed/test/other.json"})
    async def verify():
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as raised:
                await build_chunks(wrong, context["ids"]["version"], session=session, storage=context["storage"])
            assert raised.value.code == "INVALID_CHUNKING_INPUT"
            assert (await session.execute(select(Chunk.id).where(
                Chunk.knowledge_version_id == context["ids"]["version"]))).scalars().all() == []
    asyncio.run(verify())


def test_step55_rejects_lesson_target_mismatch(chunking_context):
    context = chunking_context
    wrong = context["ref"].model_copy(update={"source_id": uuid4()})
    async def verify():
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as raised:
                await build_chunks(wrong, context["ids"]["version"], session=session, storage=context["storage"])
            assert raised.value.code == "INVALID_CHUNKING_INPUT"
            assert (await session.execute(select(Chunk.id).where(
                Chunk.knowledge_version_id == context["ids"]["version"]))).scalars().all() == []
    asyncio.run(verify())


@pytest.mark.parametrize("status", ["PROCESSING", "FAILED"])
def test_step55_rejects_transformation_run_that_is_not_succeeded(chunking_context, status):
    context = chunking_context
    async def verify():
        async with SessionFactory.begin() as session:
            run = await session.get(TransformationRun, context["ids"]["transformation"])
            run.status = status
            if status == "FAILED":
                run.transformed_storage_reference = None
                run.error_code = "TEST_FAILURE"
                run.error_detail = "test-only"
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as raised:
                await build_chunks(context["ref"], context["ids"]["version"], session=session,
                                   storage=context["storage"])
            assert raised.value.code == "INVALID_CHUNKING_INPUT"
    asyncio.run(verify())


def test_step55_rejects_missing_transformation_run(chunking_context):
    context = chunking_context
    missing = context["ref"].model_copy(update={"transformation_run_id": uuid4()})
    async def verify():
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as raised:
                await build_chunks(missing, context["ids"]["version"], session=session, storage=context["storage"])
            assert raised.value.code == "INVALID_CHUNKING_INPUT"
    asyncio.run(verify())


def test_step55_rejects_transformation_source_type_mismatch(chunking_context):
    context = chunking_context
    wrong = context["ref"].model_copy(update={"source_type": "DOCUMENT"})
    async def verify():
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as raised:
                await build_chunks(wrong, context["ids"]["version"], session=session, storage=context["storage"])
            assert raised.value.code == "INVALID_CHUNKING_INPUT"
    asyncio.run(verify())


def test_step55_rejects_document_target_mismatch(chunking_context):
    context = chunking_context
    wrong = TransformedArtifactRef(
        transformation_run_id=context["ids"]["document_transformation"], source_type="DOCUMENT",
        source_id=uuid4(), storage_key="transformed/test/document.json", schema_version="transformed_document/v1",
    )
    async def verify():
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as raised:
                await build_chunks(wrong, context["ids"]["version"], session=session, storage=context["storage"])
            assert raised.value.code == "INVALID_CHUNKING_INPUT"
    asyncio.run(verify())


def test_step55_rejects_knowledge_source_that_does_not_match_transformed_lineage(chunking_context):
    context = chunking_context
    async def verify():
        async with SessionFactory.begin() as session:
            source = await session.get(KnowledgeSource, context["ids"]["source"])
            source.lesson_id = context["ids"]["other_lesson"]
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as raised:
                await build_chunks(context["ref"], context["ids"]["version"], session=session,
                                   storage=context["storage"])
            assert raised.value.code == "INVALID_CHUNKING_INPUT"
    asyncio.run(verify())


def test_step55_unexpected_planning_exception_is_internal_error(chunking_context, monkeypatch):
    context = chunking_context
    def fail_planning(*_args, **_kwargs):
        raise RuntimeError("private planner detail")
    monkeypatch.setattr("app.ingestion.chunking.service.build_chunk_plan", fail_planning)
    async def verify():
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as raised:
                await build_chunks(context["ref"], context["ids"]["version"], session=session,
                                   storage=context["storage"])
            assert raised.value.code == "CHUNKING_FAILED"
            assert raised.value.status_code == 500
            assert "private planner detail" not in str(raised.value)
        async with SessionFactory() as session:
            version = await session.get(KnowledgeVersion, context["ids"]["version"])
            assert version.status == "PROCESSING"
            assert (await session.execute(select(Chunk.id).where(
                Chunk.knowledge_version_id == context["ids"]["version"]))).scalars().all() == []
    asyncio.run(verify())


def test_step55_locked_state_recheck_rejects_stale_non_processing_version(chunking_context):
    context = chunking_context
    async def verify():
        async with SessionFactory.begin() as session:
            version = await session.get(KnowledgeVersion, context["ids"]["version"])
            version.status = "SUPERSEDED"
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as raised:
                async with session.begin():
                    await _validate_version_source(
                        session, context["ids"]["version"], context["ref"], locked=True,
                    )
            assert raised.value.code == "KNOWLEDGE_VERSION_NOT_PROCESSING"
    asyncio.run(verify())
