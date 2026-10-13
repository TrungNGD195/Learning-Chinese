import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, inspect, select, text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.errors import ApplicationError
from app.database.engine import engine
from app.database.models import (Base, Document, HSKLevel, KnowledgeSource, KnowledgeVersion,
                                Lesson, ParsingRun, TransformationRun, User)
from app.database.readiness import check_database_readiness
from app.database.seeds.required import seed_required_data
from app.database.session import SessionFactory, get_db_session


EXPECTED_TABLES = {
    "users", "hsk_levels", "lessons", "curriculum_units", "pronunciation_sections",
    "pronunciation_progress", "vocabulary", "lesson_vocabulary", "grammar", "lesson_grammar",
    "assessments", "assessment_lessons", "assessment_vocabulary", "assessment_grammar",
    "questions", "question_options", "assessment_attempts", "attempt_answers",
    "learner_lesson_progress", "learner_hsk_progress", "learner_vocabulary_progress",
    "learner_grammar_progress", "conversations", "messages", "message_citations", "documents",
    "knowledge_sources", "knowledge_versions", "chunks", "embedding_profiles", "embeddings",
    "message_retrievals", "refresh_tokens", "password_reset_tokens", "parsing_runs", "transformation_runs",
}


def test_metadata_covers_exact_phase2_table_set() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES
    for name in ("assessment_lessons", "assessment_vocabulary", "assessment_grammar"):
        assert "id" not in Base.metadata.tables[name].c
        assert not Base.metadata.tables[name].primary_key.columns


def test_migrated_schema_has_vector_constraints_indexes_and_fk_actions() -> None:
    async def inspect_schema() -> None:
        async with engine.connect() as connection:
            table_names, indexes, constraints, citation_fks, vector_extension, vector_type, chunking_columns = await connection.run_sync(
                lambda sync: (
                    set(inspect(sync).get_table_names()),
                    {(table, item["name"]): item for table in EXPECTED_TABLES for item in inspect(sync).get_indexes(table)},
                    {table: {item["name"]: item["sqltext"] for item in inspect(sync).get_check_constraints(table)} for table in EXPECTED_TABLES},
                    inspect(sync).get_foreign_keys("message_citations"),
                    sync.execute(text("select exists(select 1 from pg_extension where extname='vector')")).scalar_one(),
                    sync.execute(text("select format_type(a.atttypid,a.atttypmod) from pg_attribute a where a.attrelid='embeddings'::regclass and a.attname='vector'")).scalar_one(),
                    {table: {item["name"]: item for item in inspect(sync).get_columns(table)}
                     for table in ("knowledge_versions", "chunks")},
                )
            )
            assert EXPECTED_TABLES | {"alembic_version"} == table_names
            assert vector_extension is True
            assert vector_type == "vector"
            assert {"chunking_version", "chunk_max_chars"} <= set(chunking_columns["knowledge_versions"])
            assert chunking_columns["knowledge_versions"]["chunking_version"]["nullable"] is True
            assert chunking_columns["knowledge_versions"]["chunk_max_chars"]["nullable"] is True
            assert chunking_columns["chunks"]["content_hash"]["nullable"] is True
            assert "content_hash" in Base.metadata.tables["chunks"].c
            required_indexes = {
                ("lessons", "ix_lessons_hsk_level_id"),
                ("curriculum_units", "ix_curriculum_units_hsk_level_id_order_index"),
                ("assessment_attempts", "ix_assessment_attempts_user_id_assessment_id"),
                ("conversations", "ix_conversations_user_id_updated_at"),
                ("messages", "ix_messages_conversation_id_created_at"),
                ("documents", "ix_documents_processing_status"),
                ("documents", "ix_documents_review_status"),
                ("knowledge_versions", "uq_knowledge_versions_one_active_per_source"),
            }
            assert required_indexes <= set(indexes)
            active_idx = indexes[("knowledge_versions", "uq_knowledge_versions_one_active_per_source")]
            assert active_idx["unique"] is True
            active_filter = active_idx["dialect_options"]["postgresql_where"]
            assert "status" in active_filter and "'ACTIVE'" in active_filter
            for table, check_excerpts in {
                "curriculum_units": {"ck_curriculum_units_target_invariant": ["unit_type = 'LESSON'", "assessment_id IS NULL"]},
                "assessments": {"ck_assessments_lesson_target": ["LESSON_EXERCISE", "lesson_id IS NULL"]},
                "messages": {"ck_messages_completed_content": ["COMPLETED", "content IS NOT NULL", "btrim"]},
                "documents": {"ck_documents_approval_invariant": ["APPROVED", "PREVIEW_READY", "approved_by IS NOT NULL", "approved_at IS NOT NULL"]},
                "knowledge_sources": {"ck_knowledge_sources_target_invariant": ["DOCUMENT", "LESSON", "document_id IS NULL"]},
            }.items():
                for name, excerpts in check_excerpts.items():
                    check_sql = constraints[table][name].replace("::text", "")
                    assert all(excerpt in check_sql for excerpt in excerpts), (table, name, check_sql)
            assert {item["options"].get("ondelete") for item in citation_fks if item["constrained_columns"] == ["message_id"]} == {"CASCADE"}
            assert {item["options"].get("ondelete") for item in citation_fks if item["constrained_columns"] == ["chunk_id"]} == {"SET NULL"}
            citation_schema = await connection.run_sync(lambda sync: (
                inspect(sync).get_columns("message_citations"),
                inspect(sync).get_unique_constraints("message_citations"),
                inspect(sync).get_check_constraints("message_citations"),
            ))
            citation_columns, citation_unique, citation_checks = citation_schema
            citation_column_map = {item["name"]: item for item in citation_columns}
            assert set(citation_column_map) == {
                "id", "message_id", "source_label", "source_kind", "chunk_id", "title",
                "url", "domain", "source_type", "locator", "metadata", "created_at",
            }
            assert citation_column_map["message_id"]["nullable"] is False
            assert citation_column_map["chunk_id"]["nullable"] is True
            assert {tuple(item["column_names"]) for item in citation_unique} >= {("message_id", "source_label")}
            source_kind_check = next(item for item in citation_checks if item["name"] == "ck_message_citations_source_kind_values")
            assert "INTERNAL_CHUNK" in source_kind_check["sqltext"] and "EXTERNAL_URL" in source_kind_check["sqltext"]

    asyncio.run(inspect_schema())


def test_auth_token_schema_matches_d013_and_migration_head() -> None:
    async def inspect_auth_schema() -> None:
        async with engine.connect() as connection:
            details = await connection.run_sync(lambda sync: (
                {table: inspect(sync).get_columns(table) for table in ("refresh_tokens", "password_reset_tokens")},
                {table: inspect(sync).get_indexes(table) for table in ("refresh_tokens", "password_reset_tokens")},
                {table: inspect(sync).get_foreign_keys(table) for table in ("refresh_tokens", "password_reset_tokens")},
                sync.execute(text("select version_num from alembic_version")).scalar_one(),
            ))
        raw_columns, indexes, foreign_keys, revision = details
        columns = {table: {item["name"]: item for item in values} for table, values in raw_columns.items()}
        assert revision == "0012_vector_storage_readiness"
        assert set(columns["refresh_tokens"]) == {"id", "user_id", "token_hash", "expires_at", "revoked_at", "created_at"}
        assert set(columns["password_reset_tokens"]) == {"id", "user_id", "token_hash", "expires_at", "used_at", "created_at"}
        assert {item["name"] for item in indexes["refresh_tokens"]} == {"ix_refresh_tokens_user_id", "ix_refresh_tokens_expires_at", "uq_refresh_tokens_token_hash"}
        assert {item["name"] for item in indexes["password_reset_tokens"]} == {"ix_password_reset_tokens_user_id", "ix_password_reset_tokens_expires_at", "uq_password_reset_tokens_token_hash"}
        assert next(item for item in indexes["refresh_tokens"] if item["name"] == "uq_refresh_tokens_token_hash")["unique"]
        assert next(item for item in indexes["password_reset_tokens"] if item["name"] == "uq_password_reset_tokens_token_hash")["unique"]
        for table in ("refresh_tokens", "password_reset_tokens"):
            assert {fk["options"].get("ondelete") for fk in foreign_keys[table]} == {"CASCADE"}
            assert columns[table]["token_hash"]["type"].__class__.__name__ == "TEXT"
    asyncio.run(inspect_auth_schema())


def test_step51_document_source_columns_are_nullable_and_constrained() -> None:
    async def inspect_source_policy_schema() -> None:
        async with engine.connect() as connection:
            details = await connection.run_sync(lambda sync: (
                inspect(sync).get_columns("documents"),
                inspect(sync).get_check_constraints("documents"),
            ))
        columns, checks = details
        column_map = {column["name"]: column for column in columns}
        source_columns = {"title", "source_category", "source_origin", "source_language", "usage_rights_note"}
        assert source_columns <= set(column_map)
        assert all(column_map[name]["nullable"] for name in source_columns)
        check_map = {check["name"]: check["sqltext"] for check in checks}
        expected_source_check_names = {
            "ck_documents_source_category_values",
            "ck_documents_source_language_values",
            "ck_documents_title_non_blank",
            "ck_documents_source_origin_non_blank",
        }
        source_check_suffixes = {
            "source_category_values",
            "source_language_values",
            "title_non_blank",
            "source_origin_non_blank",
        }
        actual_source_check_names = {
            name for name in check_map
            if any(name.endswith(suffix) for suffix in source_check_suffixes)
        }
        assert actual_source_check_names == expected_source_check_names

    asyncio.run(inspect_source_policy_schema())


def test_step52_document_raw_metadata_is_nullable_unique_and_positive() -> None:
    async def inspect_raw_schema() -> None:
        async with engine.connect() as connection:
            details = await connection.run_sync(lambda sync: (
                inspect(sync).get_columns("documents"),
                inspect(sync).get_unique_constraints("documents"),
                inspect(sync).get_check_constraints("documents"),
            ))
        columns, unique_constraints, checks = details
        column_map = {column["name"]: column for column in columns}
        for name in ("mime_type", "file_size_bytes", "content_hash"):
            assert name in column_map and column_map[name]["nullable"]
        assert {item["name"] for item in unique_constraints} >= {"uq_documents_content_hash"}
        file_size = next(item for item in checks if item["name"] == "ck_documents_file_size_positive")
        assert "file_size_bytes > 0" in file_size["sqltext"]
    asyncio.run(inspect_raw_schema())


def test_step53_parsing_run_schema_has_frozen_constraints_and_indexes() -> None:
    async def inspect_parsing_schema() -> None:
        async with engine.connect() as connection:
            details = await connection.run_sync(lambda sync: (
                inspect(sync).get_columns("parsing_runs"),
                inspect(sync).get_check_constraints("parsing_runs"),
                inspect(sync).get_foreign_keys("parsing_runs"),
                inspect(sync).get_indexes("parsing_runs"),
                sync.execute(text("select version_num from alembic_version")).scalar_one(),
            ))
        columns, checks, foreign_keys, indexes, revision = details
        assert revision == "0012_vector_storage_readiness"
        assert {column["name"] for column in columns} == {
            "id", "source_type", "document_id", "lesson_id", "raw_storage_reference", "raw_content_hash",
            "parser_name", "parser_version", "cleaning_strategy", "cleaning_version", "status",
            "parsed_storage_reference", "error_code", "error_detail", "created_at", "updated_at",
        }
        check_map = {item["name"]: item["sqltext"] for item in checks}
        assert set(check_map) == {
            "ck_parsing_runs_source_type_values", "ck_parsing_runs_status_values",
            "ck_parsing_runs_source_target_invariant", "ck_parsing_runs_success_invariant",
            "ck_parsing_runs_failure_invariant",
        }
        assert "DOCUMENT" in check_map["ck_parsing_runs_source_target_invariant"]
        assert "LESSON" in check_map["ck_parsing_runs_source_target_invariant"]
        assert {item["referred_table"] for item in foreign_keys} == {"documents", "lessons"}
        assert {item["name"] for item in indexes} == {
            "ix_parsing_runs_document_id", "ix_parsing_runs_lesson_id", "ix_parsing_runs_status",
        }
    asyncio.run(inspect_parsing_schema())


def test_step53_postgresql_rejects_invalid_parsing_run_invariants() -> None:
    async def verify_constraints() -> None:
        user_id, document_id, level_id, lesson_id = uuid4(), uuid4(), uuid4(), uuid4()
        async with SessionFactory.begin() as session:
            session.add(User(id=user_id, email=f"parsing-invariants-{user_id}@example.invalid",
                             password_hash="unused", full_name="Constraint Test", role="ADMIN"))
            await session.flush()
            session.add(HSKLevel(id=level_id, level_number=1_000_000 + level_id.int % 1_000_000, order_index=1))
            await session.flush()
            session.add(Lesson(id=lesson_id, hsk_level_id=level_id, lesson_number=1,
                               title="Constraint test", status="PUBLISHED"))
            session.add(Document(
                id=document_id, original_filename="constraint.txt", file_type="TXT", storage_reference="test/raw",
                mime_type="text/plain", file_size_bytes=4, content_hash=uuid4().hex,
                processing_status="UPLOADED", review_status="PENDING", uploaded_by=user_id,
            ))
            await session.flush()

            common = {
                "raw_storage_reference": "test/raw", "raw_content_hash": "a" * 64,
                "parser_name": "txt_utf8", "parser_version": "v1",
                "cleaning_strategy": "basic_text_cleaning", "cleaning_version": "v1",
            }

            def row(source_type="DOCUMENT", status="PENDING", **overrides):
                values = {
                    **common, "id": uuid4(), "source_type": source_type,
                    "document_id": document_id if source_type == "DOCUMENT" else None,
                    "lesson_id": lesson_id if source_type == "LESSON" else None,
                    "status": status,
                }
                values.update(overrides)
                return ParsingRun(**values)

            # Valid target/status combinations remain insertable.
            session.add_all([row("DOCUMENT", "PENDING"), row("LESSON", "PROCESSING")])
            await session.flush()

            invalid = [
                row(status="NOT_A_STATUS"),
                row(source_type="DOCUMENT", lesson_id=lesson_id),
                row(source_type="DOCUMENT", document_id=None),
                row(source_type="LESSON", document_id=document_id),
                row(source_type="LESSON", lesson_id=None),
                row(status="SUCCEEDED"),
                row(status="SUCCEEDED", parsed_storage_reference="parsed/item.json", error_code="PARSING_FAILED"),
                row(status="FAILED", parsed_storage_reference="parsed/item.json", error_code="PARSING_FAILED"),
                row(status="FAILED", error_code=None),
            ]
            for invalid_run in invalid:
                with pytest.raises(IntegrityError):
                    async with session.begin_nested():
                        session.add(invalid_run)
                        await session.flush()

        async with SessionFactory.begin() as session:
            await session.execute(delete(ParsingRun).where(
                (ParsingRun.document_id == document_id) | (ParsingRun.lesson_id == lesson_id)
            ))
            await session.execute(delete(Document).where(Document.id == document_id))
            await session.execute(delete(Lesson).where(Lesson.id == lesson_id))
            await session.execute(delete(HSKLevel).where(HSKLevel.id == level_id))
            await session.execute(delete(User).where(User.id == user_id))

    asyncio.run(verify_constraints())


def test_step54_transformation_run_schema_has_frozen_constraints_and_indexes() -> None:
    async def inspect_schema() -> None:
        async with engine.connect() as connection:
            columns, checks, foreign_keys, indexes, revision = await connection.run_sync(lambda sync: (
                inspect(sync).get_columns("transformation_runs"),
                inspect(sync).get_check_constraints("transformation_runs"),
                inspect(sync).get_foreign_keys("transformation_runs"),
                inspect(sync).get_indexes("transformation_runs"),
                sync.execute(text("select version_num from alembic_version")).scalar_one(),
            ))
        assert revision == "0012_vector_storage_readiness"
        assert {column["name"] for column in columns} == {
            "id", "source_type", "document_id", "lesson_id", "parsing_run_id", "parsed_storage_reference",
            "transformation_strategy", "transformation_version", "status", "transformed_storage_reference",
            "error_code", "error_detail", "source_metadata_snapshot", "created_at", "updated_at",
        }
        assert {item["name"] for item in checks} == {
            "ck_transformation_runs_source_type_values", "ck_transformation_runs_status_values",
            "ck_transformation_runs_source_target_invariant", "ck_transformation_runs_success_invariant",
            "ck_transformation_runs_failure_invariant",
        }
        assert {item["referred_table"] for item in foreign_keys} == {"documents", "lessons", "parsing_runs"}
        assert {item["name"] for item in indexes} == {
            "ix_transformation_runs_document_id", "ix_transformation_runs_lesson_id",
            "ix_transformation_runs_parsing_run_id", "ix_transformation_runs_status",
        }
    asyncio.run(inspect_schema())


def test_step54_postgresql_rejects_invalid_transformation_run_invariants() -> None:
    async def verify_constraints() -> None:
        user_id, document_id, level_id, lesson_id = uuid4(), uuid4(), uuid4(), uuid4()
        parsing_id, lesson_parsing_id = uuid4(), uuid4()
        async with SessionFactory.begin() as session:
            session.add(User(id=user_id, email=f"transformation-invariants-{user_id}@example.invalid",
                             password_hash="unused", full_name="Constraint Test", role="ADMIN"))
            await session.flush()
            session.add(HSKLevel(id=level_id, level_number=2_000_000 + level_id.int % 1_000_000, order_index=1))
            await session.flush()
            session.add(Lesson(id=lesson_id, hsk_level_id=level_id, lesson_number=1,
                               title="Constraint test", status="PUBLISHED"))
            session.add(Document(
                id=document_id, original_filename="constraint.txt", file_type="TXT", storage_reference="test/raw",
                mime_type="text/plain", file_size_bytes=4, content_hash=uuid4().hex,
                processing_status="UPLOADED", review_status="PENDING", uploaded_by=user_id,
            ))
            await session.flush()
            session.add(ParsingRun(
                id=parsing_id, source_type="DOCUMENT", document_id=document_id, raw_storage_reference="raw",
                raw_content_hash="a" * 64, parser_name="test", parser_version="v1",
                cleaning_strategy="test", cleaning_version="v1", status="SUCCEEDED",
                parsed_storage_reference="parsed/key",
            ))
            await session.flush()
            session.add(ParsingRun(
                id=lesson_parsing_id, source_type="LESSON", lesson_id=lesson_id, raw_storage_reference="raw/lesson",
                raw_content_hash="b" * 64, parser_name="test", parser_version="v1",
                cleaning_strategy="test", cleaning_version="v1", status="SUCCEEDED",
                parsed_storage_reference="parsed/lesson/key",
            ))
            await session.flush()

            def row(source_type="DOCUMENT", status="PENDING", **overrides):
                values = {
                    "id": uuid4(), "source_type": source_type,
                    "document_id": document_id if source_type == "DOCUMENT" else None,
                    "lesson_id": lesson_id if source_type == "LESSON" else None,
                    "parsing_run_id": parsing_id if source_type == "DOCUMENT" else lesson_parsing_id,
                    "parsed_storage_reference": "parsed/key" if source_type == "DOCUMENT" else "parsed/lesson/key",
                    "transformation_strategy": "canonical_document", "transformation_version": "v1",
                    "status": status, "source_metadata_snapshot": {"source_type": source_type},
                }
                values.update(overrides)
                return TransformationRun(**values)

            session.add_all([row(status="PENDING"), row(source_type="LESSON", status="PROCESSING")])
            await session.flush()
            invalid = [
                row(status="NOT_A_STATUS"),
                row(source_type="DOCUMENT", lesson_id=lesson_id),
                row(source_type="DOCUMENT", document_id=None),
                row(source_type="LESSON", document_id=document_id),
                row(source_type="LESSON", lesson_id=None),
                row(status="SUCCEEDED"),
                row(status="SUCCEEDED", transformed_storage_reference="transformed/key", error_code="FAILED"),
                row(status="FAILED", transformed_storage_reference="transformed/key", error_code="FAILED"),
                row(status="FAILED", error_code=None),
            ]
            for invalid_run in invalid:
                with pytest.raises(IntegrityError):
                    async with session.begin_nested():
                        session.add(invalid_run)
                        await session.flush()

        async with SessionFactory.begin() as session:
            await session.execute(delete(TransformationRun).where(
                (TransformationRun.document_id == document_id) | (TransformationRun.lesson_id == lesson_id)
            ))
            await session.execute(delete(ParsingRun).where(ParsingRun.id.in_([parsing_id, lesson_parsing_id])))
            await session.execute(delete(Document).where(Document.id == document_id))
            await session.execute(delete(Lesson).where(Lesson.id == lesson_id))
            await session.execute(delete(HSKLevel).where(HSKLevel.id == level_id))
            await session.execute(delete(User).where(User.id == user_id))
    asyncio.run(verify_constraints())


def test_step56_schema_has_pinned_review_fk_and_source_processing_uniqueness() -> None:
    async def inspect_step56_schema() -> None:
        async with engine.connect() as connection:
            details = await connection.run_sync(lambda sync: (
                inspect(sync).get_columns("documents"),
                inspect(sync).get_foreign_keys("documents"),
                inspect(sync).get_unique_constraints("knowledge_sources"),
                inspect(sync).get_indexes("knowledge_versions"),
                sync.execute(text("select version_num from alembic_version")).scalar_one(),
            ))
        columns, foreign_keys, uniques, indexes, revision = details
        review = next(column for column in columns if column["name"] == "review_transformation_run_id")
        assert review["nullable"] is True
        review_fk = next(item for item in foreign_keys if item["constrained_columns"] == ["review_transformation_run_id"])
        assert review_fk["referred_table"] == "transformation_runs"
        assert review_fk["options"].get("ondelete") == "SET NULL"
        assert any(item["name"] == "uq_knowledge_sources_document_id" for item in uniques)
        processing = next(item for item in indexes if item["name"] == "uq_knowledge_versions_one_processing_per_source")
        assert processing["unique"] is True
        assert "PROCESSING" in processing["dialect_options"]["postgresql_where"]
        assert revision == "0012_vector_storage_readiness"

    asyncio.run(inspect_step56_schema())


def test_step57_schema_has_nullable_exact_lineage_foreign_keys() -> None:
    async def inspect_step57_schema() -> None:
        async with engine.connect() as connection:
            details = await connection.run_sync(lambda sync: (
                {table: inspect(sync).get_columns(table) for table in ("documents", "knowledge_versions")},
                {table: inspect(sync).get_foreign_keys(table) for table in ("documents", "knowledge_versions")},
                sync.execute(text("select version_num from alembic_version")).scalar_one(),
            ))
        columns, foreign_keys, revision = details
        document_columns = {column["name"]: column for column in columns["documents"]}
        version_columns = {column["name"]: column for column in columns["knowledge_versions"]}
        assert document_columns["approved_transformation_run_id"]["nullable"] is True
        assert version_columns["transformation_run_id"]["nullable"] is True
        approved_fk = next(item for item in foreign_keys["documents"]
                           if item["constrained_columns"] == ["approved_transformation_run_id"])
        version_fk = next(item for item in foreign_keys["knowledge_versions"]
                          if item["constrained_columns"] == ["transformation_run_id"])
        assert approved_fk["referred_table"] == "transformation_runs"
        assert approved_fk["options"].get("ondelete") == "SET NULL"
        assert version_fk["referred_table"] == "transformation_runs"
        assert version_fk["options"].get("ondelete") == "RESTRICT"
        assert revision == "0012_vector_storage_readiness"
    asyncio.run(inspect_step57_schema())


def test_step56_postgresql_enforces_document_source_and_processing_identity() -> None:
    async def verify_constraints() -> None:
        user_id, document_id, level_id, lesson_id = (uuid4() for _ in range(4))
        document_source_id, lesson_source_id = uuid4(), uuid4()
        async with SessionFactory.begin() as session:
            session.add(User(id=user_id, email=f"step56-unique-{user_id}@example.invalid",
                             password_hash="unused", full_name="Step 5.6", role="ADMIN"))
            await session.flush()
            session.add(HSKLevel(id=level_id, level_number=3_000_000 + level_id.int % 1_000_000, order_index=1))
            await session.flush()
            session.add(Lesson(id=lesson_id, hsk_level_id=level_id, lesson_number=1,
                               title="Step 5.6", status="PUBLISHED"))
            session.add(Document(
                id=document_id, original_filename="step56.txt", file_type="TXT",
                storage_reference="test/step56.txt", mime_type="text/plain", file_size_bytes=4,
                content_hash=uuid4().hex, processing_status="UPLOADED", review_status="PENDING",
                uploaded_by=user_id,
            ))
            await session.flush()
            session.add_all([
                KnowledgeSource(id=document_source_id, source_type="DOCUMENT", document_id=document_id),
                KnowledgeSource(id=lesson_source_id, source_type="LESSON", lesson_id=lesson_id),
            ])
            await session.flush()
            session.add_all([
                KnowledgeVersion(knowledge_source_id=document_source_id, version_number=1, status="PROCESSING"),
                KnowledgeVersion(knowledge_source_id=lesson_source_id, version_number=1, status="ACTIVE"),
                KnowledgeVersion(knowledge_source_id=lesson_source_id, version_number=2, status="PROCESSING"),
            ])
            await session.flush()
            for duplicate in (
                KnowledgeSource(source_type="DOCUMENT", document_id=document_id),
                KnowledgeVersion(knowledge_source_id=document_source_id, version_number=2, status="PROCESSING"),
            ):
                with pytest.raises(IntegrityError):
                    async with session.begin_nested():
                        session.add(duplicate)
                        await session.flush()
            # ACTIVE + PROCESSING is allowed for the same source; the partial
            # unique index applies only to PROCESSING rows.
        async with SessionFactory.begin() as session:
            await session.execute(delete(KnowledgeVersion).where(KnowledgeVersion.knowledge_source_id.in_([document_source_id, lesson_source_id])))
            await session.execute(delete(KnowledgeSource).where(KnowledgeSource.id.in_([document_source_id, lesson_source_id])))
            await session.execute(delete(Document).where(Document.id == document_id))
            await session.execute(delete(Lesson).where(Lesson.id == lesson_id))
            await session.execute(delete(HSKLevel).where(HSKLevel.id == level_id))
            await session.execute(delete(User).where(User.id == user_id))

    asyncio.run(verify_constraints())


def test_conversation_message_schema_matches_step36_metadata() -> None:
    async def inspect_conversation_schema() -> None:
        async with engine.connect() as connection:
            details = await connection.run_sync(lambda sync: (
                {table: inspect(sync).get_columns(table) for table in ("conversations", "messages")},
                inspect(sync).get_unique_constraints("messages"),
                inspect(sync).get_foreign_keys("messages"),
                inspect(sync).get_indexes("messages"),
            ))
        columns, unique, foreign_keys, indexes = details
        conversation_columns = {column["name"] for column in columns["conversations"]}
        message_columns = {column["name"]: column for column in columns["messages"]}
        assert "deleted_at" in conversation_columns
        assert "scope" not in conversation_columns
        assert message_columns["sequence_number"]["nullable"] is False
        assert {"reply_to_message_id", "sequence_number"} <= set(message_columns)
        assert any(
            item["name"] == "uq_messages_conversation_id_sequence_number"
            and item["column_names"] == ["conversation_id", "sequence_number"]
            for item in unique
        )
        reply_fk = next(item for item in foreign_keys if item["name"] == "fk_messages_reply_to_message_id_messages")
        assert reply_fk["referred_table"] == "messages"
        assert reply_fk["options"].get("ondelete") == "RESTRICT"
        assert any(item["name"] == "ix_messages_reply_to_message_id" for item in indexes)

    asyncio.run(inspect_conversation_schema())


def test_required_seed_is_idempotent_and_contains_only_system_rows() -> None:
    async def verify_seed() -> None:
        await seed_required_data()
        await seed_required_data()
        async with SessionFactory() as session:
            levels = (await session.execute(text("select level_number, order_index from hsk_levels order by order_index"))).all()
            sections = (await session.execute(text("select code, order_index from pronunciation_sections order by order_index"))).all()
            users = (await session.execute(text("select count(*) from users"))).scalar_one()
        assert levels == [(1, 1), (2, 2), (3, 3)]
        assert sections == [("TONES", 1), ("INITIALS", 2), ("FINALS", 3)]
        assert users == 0

    asyncio.run(verify_seed())


def test_session_lifecycle_does_not_implicitly_commit() -> None:
    async def verify_session() -> None:
        email = f"step33-{uuid4()}@example.invalid"
        dependency = get_db_session()
        session = await anext(dependency)
        second_dependency = get_db_session()
        second_session = await anext(second_dependency)
        assert session is not second_session
        await second_dependency.aclose()
        session.add(User(email=email, password_hash="test-only", full_name="Test", role="LEARNER"))
        await dependency.aclose()
        async with SessionFactory() as check:
            assert (await check.execute(select(User).where(User.email == email))).scalar_one_or_none() is None
        async with SessionFactory.begin() as explicit:
            explicit.add(User(email=email, password_hash="test-only", full_name="Test", role="LEARNER"))
        async with SessionFactory() as check:
            user = (await check.execute(select(User).where(User.email == email))).scalar_one()
            await check.delete(user)
            await check.commit()

    asyncio.run(verify_session())


def test_ready_endpoint_and_database_independent_health(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import main

    async def unavailable() -> None:
        raise ApplicationError("DATABASE_NOT_READY", "Database dependency is not ready", None, 503)

    with TestClient(main.create_app()) as client:
        assert client.get("/ready").status_code == 200
        assert client.get("/ready").json() == {"status": "ready"}
        monkeypatch.setattr(main, "check_database_readiness", unavailable)
        failed = client.get("/ready")
        assert failed.status_code == 503
        assert failed.json() == {"error": {"code": "DATABASE_NOT_READY", "message": "Database dependency is not ready", "details": None}}
        assert "test driver failure" not in failed.text
        assert client.get("/health").status_code == 200
        assert client.get("/health").json() == {"status": "ok"}


def test_live_readiness_probe_is_select_one_only() -> None:
    asyncio.run(check_database_readiness())


def test_readiness_converts_database_errors_without_leaking_driver_text(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.database import readiness

    class FailedConnection:
        async def __aenter__(self):
            raise OperationalError("SELECT 1", {}, RuntimeError("private connection detail"))

        async def __aexit__(self, *args):
            return False

    class FailedEngine:
        def connect(self):
            return FailedConnection()

    monkeypatch.setattr(readiness, "engine", FailedEngine())
    with pytest.raises(ApplicationError) as raised:
        asyncio.run(readiness.check_database_readiness())
    assert raised.value.code == "DATABASE_NOT_READY"
    assert raised.value.details is None
    assert "private connection detail" not in str(raised.value)

