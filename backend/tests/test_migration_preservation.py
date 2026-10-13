import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.database.models import Base


def _load_revision(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _apply_revision(connection, revision) -> None:
    with Operations.context(MigrationContext.configure(connection, opts={"target_metadata": Base.metadata})):
        revision.upgrade()


def _revert_revision(connection, revision) -> None:
    with Operations.context(MigrationContext.configure(connection, opts={"target_metadata": Base.metadata})):
        revision.downgrade()


def test_upgrade_0001_to_0002_preserves_existing_step34_data() -> None:
    settings = get_settings()
    assert settings.app_env == "test"
    schema = f"step35_migration_{uuid4().hex}"
    user_id, level_id, lesson_id, assessment_id, attempt_id = [uuid4() for _ in range(5)]
    engine = create_engine(settings.effective_database_url)
    migrations = Path(__file__).resolve().parents[1] / "migrations" / "versions"
    initial = _load_revision(migrations / "0001_initial_schema.py")
    auth_tokens = _load_revision(migrations / "0002_auth_token_tables.py")

    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))

        with engine.connect() as connection:
            connection.exec_driver_sql(f'SET search_path TO "{schema}", public')
            connection.commit()

            with connection.begin():
                _apply_revision(connection, initial)
                connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"))
                connection.execute(text("INSERT INTO alembic_version(version_num) VALUES ('0001_initial_schema')"))

            with connection.begin():
                connection.execute(text(
                    "INSERT INTO users(id, email, password_hash, full_name, role) "
                    "VALUES (:id, :email, 'representative-hash', 'Existing Learner', 'LEARNER')"
                ), {"id": user_id, "email": f"migration-{user_id}@example.invalid"})
                connection.execute(text(
                    "INSERT INTO hsk_levels(id, level_number, order_index) VALUES (:id, 1, 1)"
                ), {"id": level_id})
                connection.execute(text(
                    "INSERT INTO lessons(id, hsk_level_id, lesson_number, title, status) "
                    "VALUES (:id, :level_id, 1, 'Existing lesson', 'PUBLISHED')"
                ), {"id": lesson_id, "level_id": level_id})
                connection.execute(text(
                    "INSERT INTO assessments(id, type, lesson_id, title, status) "
                    "VALUES (:id, 'LESSON_EXERCISE', :lesson_id, 'Existing assessment', 'PUBLISHED')"
                ), {"id": assessment_id, "lesson_id": lesson_id})
                connection.execute(text(
                    "INSERT INTO assessment_attempts(id, user_id, assessment_id, attempt_number, status) "
                    "VALUES (:id, :user_id, :assessment_id, 1, 'IN_PROGRESS')"
                ), {"id": attempt_id, "user_id": user_id, "assessment_id": assessment_id})

            with connection.begin():
                _apply_revision(connection, auth_tokens)
                connection.execute(text(
                    "UPDATE alembic_version SET version_num='0002_auth_token_tables' "
                    "WHERE version_num='0001_initial_schema'"
                ))

            with connection.begin():
                assert connection.execute(text(
                    "SELECT email, full_name FROM users WHERE id=:id"
                ), {"id": user_id}).one() == (f"migration-{user_id}@example.invalid", "Existing Learner")
                assert connection.execute(text(
                    "SELECT title FROM lessons WHERE id=:id"
                ), {"id": lesson_id}).scalar_one() == "Existing lesson"
                assert connection.execute(text(
                    "SELECT status FROM assessment_attempts WHERE id=:id"
                ), {"id": attempt_id}).scalar_one() == "IN_PROGRESS"
                assert connection.execute(text(
                    "SELECT version_num FROM alembic_version"
                )).scalar_one() == "0002_auth_token_tables"
                tables = set(connection.execute(text(
                    "SELECT tablename FROM pg_tables WHERE schemaname=:schema"
                ), {"schema": schema}).scalars())
                assert {"refresh_tokens", "password_reset_tokens"} <= tables
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()


def test_step56_migration_covers_d064_existing_downgrade_reupgrade_and_fresh_base() -> None:
    settings = get_settings()
    assert settings.app_env == "test"
    engine = create_engine(settings.effective_database_url)
    migrations = Path(__file__).resolve().parents[1] / "migrations" / "versions"
    filenames = (
        "0001_initial_schema.py", "0002_auth_token_tables.py",
        "0003_conversation_message_flow.py", "0004_document_source_policy.py",
        "0005_raw_document_metadata.py", "0006_parsing_runs.py",
        "0007_transformation_runs.py", "0008_chunking_contract.py",
        "0009_pipeline_orchestration_contract.py",
    )
    revisions = [_load_revision(migrations / name) for name in filenames]
    legacy_schema = f"step56_existing_{uuid4().hex}"
    fresh_schema = f"step56_fresh_{uuid4().hex}"
    user_id, document_id = uuid4(), uuid4()

    def create_schema(connection, schema: str) -> None:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        connection.commit()
        connection.exec_driver_sql(f'SET search_path TO "{schema}", public')
        connection.commit()

    def apply_to_head(connection, schema: str) -> None:
        connection.exec_driver_sql(f'SET search_path TO "{schema}", public')
        connection.commit()
        for index, revision in enumerate(revisions):
            with connection.begin():
                _apply_revision(connection, revision)
                if index == 0:
                    connection.execute(text(
                        "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
                    ))
                    connection.execute(text(
                        "INSERT INTO alembic_version(version_num) VALUES (:revision)"
                    ), {"revision": revision.revision})
                else:
                    connection.execute(text("UPDATE alembic_version SET version_num=:revision"),
                                       {"revision": revision.revision})

    def width(connection) -> int:
        column = next(item for item in inspect(connection).get_columns("alembic_version")
                      if item["name"] == "version_num")
        return column["type"].length

    def assert_step56_present(connection) -> None:
        assert "review_transformation_run_id" in {
            item["name"] for item in inspect(connection).get_columns("documents")
        }
        assert "uq_knowledge_sources_document_id" in {
            item["name"] for item in inspect(connection).get_unique_constraints("knowledge_sources")
        }
        assert "uq_knowledge_versions_one_processing_per_source" in {
            item["name"] for item in inspect(connection).get_indexes("knowledge_versions")
        }

    def assert_step56_absent(connection) -> None:
        assert "review_transformation_run_id" not in {
            item["name"] for item in inspect(connection).get_columns("documents")
        }
        assert "uq_knowledge_sources_document_id" not in {
            item["name"] for item in inspect(connection).get_unique_constraints("knowledge_sources")
        }
        assert "uq_knowledge_versions_one_processing_per_source" not in {
            item["name"] for item in inspect(connection).get_indexes("knowledge_versions")
        }

    try:
        with engine.connect() as connection:
            # CASE 1: an accepted 0008/VARCHAR(32) database upgrades without preparation.
            create_schema(connection, legacy_schema)
            for index, revision in enumerate(revisions[:8]):
                with connection.begin():
                    _apply_revision(connection, revision)
                    if index == 0:
                        connection.execute(text(
                            "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
                        ))
                        connection.execute(text(
                            "INSERT INTO alembic_version(version_num) VALUES (:revision)"
                        ), {"revision": revision.revision})
                    else:
                        connection.execute(text("UPDATE alembic_version SET version_num=:revision"),
                                           {"revision": revision.revision})
            assert width(connection) == 32
            connection.commit()
            with connection.begin():
                connection.execute(text(
                    "INSERT INTO users(id,email,password_hash,full_name,role) "
                    "VALUES (:id,:email,'legacy','Legacy','ADMIN')"
                ), {"id": user_id, "email": f"step56-{user_id}@example.invalid"})
                connection.execute(text(
                    "INSERT INTO documents(id,original_filename,file_type,storage_reference,"
                    "processing_status,review_status,uploaded_by) "
                    "VALUES (:id,'legacy.txt','TXT','legacy/raw','UPLOADED','PENDING',:user_id)"
                ), {"id": document_id, "user_id": user_id})
            with connection.begin():
                _apply_revision(connection, revisions[8])
                connection.execute(text("UPDATE alembic_version SET version_num=:revision"),
                                   {"revision": revisions[8].revision})
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == revisions[8].revision
            assert width(connection) == 64
            assert_step56_present(connection)
            assert connection.execute(text("SELECT original_filename FROM documents WHERE id=:id"),
                                      {"id": document_id}).scalar_one() == "legacy.txt"
            connection.commit()

            # CASE 2: application schema rolls back but the Alembic control width stays wide.
            with connection.begin():
                _revert_revision(connection, revisions[8])
                connection.execute(text("UPDATE alembic_version SET version_num=:revision"),
                                   {"revision": revisions[7].revision})
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == revisions[7].revision
            assert_step56_absent(connection)
            assert width(connection) == 64
            assert connection.execute(text("SELECT original_filename FROM documents WHERE id=:id"),
                                      {"id": document_id}).scalar_one() == "legacy.txt"
            connection.commit()

            # CASE 3: re-upgrade detects VARCHAR(64) and safely skips a second alter.
            with connection.begin():
                _apply_revision(connection, revisions[8])
                connection.execute(text("UPDATE alembic_version SET version_num=:revision"),
                                   {"revision": revisions[8].revision})
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == revisions[8].revision
            assert width(connection) == 64
            assert_step56_present(connection)
            connection.commit()

            # CASE 4: a fresh base-to-head chain needs no out-of-band preparation.
            create_schema(connection, fresh_schema)
            apply_to_head(connection, fresh_schema)
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == revisions[8].revision
            assert width(connection) == 64
            assert_step56_present(connection)
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{legacy_schema}" CASCADE'))
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{fresh_schema}" CASCADE'))
        engine.dispose()


def test_step57_migration_backfill_fk_delete_and_downgrade_contract() -> None:
    settings = get_settings()
    assert settings.app_env == "test"
    schema = f"step57_migration_{uuid4().hex}"
    engine = create_engine(settings.effective_database_url)
    migration_dir = Path(__file__).resolve().parents[1] / "migrations" / "versions"
    names = (
        "0001_initial_schema.py", "0002_auth_token_tables.py",
        "0003_conversation_message_flow.py", "0004_document_source_policy.py",
        "0005_raw_document_metadata.py", "0006_parsing_runs.py",
        "0007_transformation_runs.py", "0008_chunking_contract.py",
        "0009_pipeline_orchestration_contract.py",
        "0010_incremental_reprocessing_contract.py",
    )
    revisions = [_load_revision(migration_dir / name) for name in names]
    user_id, level_id, lesson_id = uuid4(), uuid4(), uuid4()
    doc_ids = [uuid4() for _ in range(9)]
    parse_ids = [uuid4() for _ in range(9)]
    run_ids = [uuid4() for _ in range(9)]
    version_id, source_id = uuid4(), uuid4()

    def setup_0009(connection) -> None:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        connection.commit()
        connection.exec_driver_sql(f'SET search_path TO "{schema}", public')
        connection.commit()
        for index, revision in enumerate(revisions[:9]):
            with connection.begin():
                _apply_revision(connection, revision)
                if index == 0:
                    connection.execute(text(
                        "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
                    ))
                    connection.execute(text("INSERT INTO alembic_version VALUES (:revision)"),
                                       {"revision": revision.revision})
                else:
                    connection.execute(text("UPDATE alembic_version SET version_num=:revision"),
                                       {"revision": revision.revision})

    try:
        with engine.connect() as connection:
            setup_0009(connection)
            with connection.begin():
                connection.execute(text(
                    "INSERT INTO users(id,email,password_hash,full_name,role) "
                    "VALUES (:id,:email,'legacy','Migration Admin','ADMIN')"
                ), {"id": user_id, "email": f"step57-{user_id}@example.invalid"})
                connection.execute(text(
                    "INSERT INTO hsk_levels(id,level_number,order_index) VALUES (:id,1,1)"
                ), {"id": level_id})
                connection.execute(text(
                    "INSERT INTO lessons(id,hsk_level_id,lesson_number,title,status) "
                    "VALUES (:id,:hsk,1,'Migration lesson','PUBLISHED')"
                ), {"id": lesson_id, "hsk": level_id})
                for index, document_id in enumerate(doc_ids):
                    review_status = "APPROVED" if index == 0 or index >= 3 else ("PENDING" if index == 1 else "REJECTED")
                    pointers = [run_ids[0], run_ids[1], run_ids[2], run_ids[0], run_ids[4],
                                run_ids[5], run_ids[6], run_ids[7], None]
                    pointer = pointers[index]
                    processing = "PREVIEW_READY" if review_status == "APPROVED" else ("FAILED" if review_status == "PENDING" else "PREVIEW_READY")
                    connection.execute(text(
                        "INSERT INTO documents(id,original_filename,file_type,storage_reference,content_hash,"
                        "processing_status,review_status,uploaded_by,approved_by,approved_at,review_transformation_run_id) "
                        "VALUES (:id,'migration.txt','TXT','raw/key',:hash,:processing,:review,:user,:approved_by,:approved_at,NULL)"
                    ), {"id": document_id, "hash": f"{index + 1:064x}", "processing": processing,
                        "review": review_status, "user": user_id,
                        "approved_by": user_id if review_status == "APPROVED" else None,
                        "approved_at": "2026-01-01T00:00:00+00:00" if review_status == "APPROVED" else None,
                        "run": None})
                for index, parsing_id in enumerate(parse_ids):
                    target_doc = doc_ids[index]
                    lesson_parse = index in {2, 4}
                    connection.execute(text(
                        "INSERT INTO parsing_runs(id,source_type,document_id,lesson_id,raw_storage_reference,raw_content_hash,"
                        "parser_name,parser_version,cleaning_strategy,cleaning_version,status,parsed_storage_reference) "
                        "VALUES (:id,:type,:doc,:lesson,'raw/key',:hash,'txt_utf8','v1','basic_text_cleaning','v1','SUCCEEDED','parsed/key')"
                    ), {"id": parsing_id, "type": "LESSON" if lesson_parse else "DOCUMENT",
                        "doc": None if lesson_parse else target_doc, "lesson": lesson_id if lesson_parse else None,
                        "hash": f"{index + 1:064x}"})
                # Deterministically valid run A belongs to approved Document 0.
                for index, run_id in enumerate(run_ids):
                    if index in {2, 4}:
                        source_type, document_id, lesson_target = "LESSON", None, lesson_id
                    else:
                        source_type = "DOCUMENT"
                        document_id = doc_ids[index]
                        lesson_target = None
                    status = "PROCESSING" if index in {5, 6, 7} else "SUCCEEDED"
                    transformed_key = None if index in {5, 6, 7} else "transformed/key"
                    error_code = "TRANSFORMATION_FAILED" if index == 7 else None
                    connection.execute(text(
                        "INSERT INTO transformation_runs(id,source_type,document_id,lesson_id,parsing_run_id,"
                        "parsed_storage_reference,transformation_strategy,transformation_version,status,"
                        "transformed_storage_reference,error_code,source_metadata_snapshot) "
                        "VALUES (:id,:type,:doc,:lesson,:parsing,'parsed/key','canonical_document','v1',:status,:transformed,:error,'{}')"
                    ), {"id": run_id, "type": source_type, "doc": document_id, "lesson": lesson_target,
                        "parsing": parse_ids[index], "status": status, "transformed": transformed_key,
                        "error": error_code})
                # The accepted 0009 schema has a cyclic document/run reference.
                # Seed the rows first, then attach the pre-existing review refs.
                for index, document_id in enumerate(doc_ids):
                    pointer = [run_ids[0], run_ids[1], run_ids[2], run_ids[0], run_ids[4],
                               run_ids[5], run_ids[6], run_ids[7], None][index]
                    connection.execute(text(
                        "UPDATE documents SET review_transformation_run_id=:run WHERE id=:id"
                    ), {"run": pointer, "id": document_id})

            # Case E: a pre-0010 KnowledgeVersion is intentionally unlineaged.
            with connection.begin():
                connection.execute(text(
                    "INSERT INTO knowledge_sources(id,source_type,document_id) VALUES (:id,'DOCUMENT',:doc)"
                ), {"id": source_id, "doc": doc_ids[0]})
                connection.execute(text(
                    "INSERT INTO knowledge_versions(id,knowledge_source_id,version_number,status) "
                    "VALUES (:id,:source,1,'ACTIVE')"
                ), {"id": version_id, "source": source_id})

            with connection.begin():
                _apply_revision(connection, revisions[9])
                connection.execute(text("UPDATE alembic_version SET version_num=:revision"),
                                   {"revision": revisions[9].revision})
                assert connection.execute(text(
                    "SELECT approved_transformation_run_id FROM documents WHERE id=:id"
                ), {"id": doc_ids[0]}).scalar_one() == run_ids[0]
                for document_id in doc_ids[1:]:
                    assert connection.execute(text(
                        "SELECT approved_transformation_run_id FROM documents WHERE id=:id"
                    ), {"id": document_id}).scalar_one() is None
                assert connection.execute(text(
                    "SELECT transformation_run_id FROM knowledge_versions WHERE id=:id"
                ), {"id": version_id}).scalar_one() is None
                assert revisions[9].revision == "0010_incremental_reprocessing_contract"
                assert revisions[9].down_revision == "0009_pipeline_orchestration_contract"

            # approved pointer uses SET NULL; lineage pointer uses RESTRICT.
            with connection.begin():
                connection.execute(text(
                    "DELETE FROM transformation_runs WHERE id=:id"
                ), {"id": run_ids[0]})
                assert connection.execute(text(
                    "SELECT approved_transformation_run_id FROM documents WHERE id=:id"
                ), {"id": doc_ids[0]}).scalar_one() is None
            with connection.begin():
                connection.execute(text(
                    "UPDATE knowledge_versions SET transformation_run_id=:run WHERE id=:id"
                ), {"run": run_ids[5], "id": version_id})
            with connection.begin():
                with pytest.raises(IntegrityError):
                    with connection.begin_nested():
                        connection.execute(text(
                            "DELETE FROM transformation_runs WHERE id=:id"
                        ), {"id": run_ids[5]})
                assert connection.execute(text(
                    "SELECT transformation_run_id FROM knowledge_versions WHERE id=:id"
                ), {"id": version_id}).scalar_one() == run_ids[5]

            with connection.begin():
                _revert_revision(connection, revisions[9])
                connection.execute(text("UPDATE alembic_version SET version_num=:revision"),
                                   {"revision": revisions[8].revision})
                assert "approved_transformation_run_id" not in {
                    column["name"] for column in inspect(connection).get_columns("documents")
                }
                assert "transformation_run_id" not in {
                    column["name"] for column in inspect(connection).get_columns("knowledge_versions")
                }
                assert connection.execute(text(
                    "SELECT title FROM lessons WHERE id=:id"
                ), {"id": lesson_id}).scalar_one() == "Migration lesson"
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()


def test_upgrade_0003_to_0004_preserves_legacy_document_and_enforces_source_policy() -> None:
    settings = get_settings()
    assert settings.app_env == "test"
    schema = f"step51_migration_{uuid4().hex}"
    user_id, document_id = uuid4(), uuid4()
    engine = create_engine(settings.effective_database_url)
    migrations = Path(__file__).resolve().parents[1] / "migrations" / "versions"
    initial = _load_revision(migrations / "0001_initial_schema.py")
    auth_tokens = _load_revision(migrations / "0002_auth_token_tables.py")
    conversation_flow = _load_revision(migrations / "0003_conversation_message_flow.py")
    source_policy = _load_revision(migrations / "0004_document_source_policy.py")

    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))

        with engine.connect() as connection:
            connection.exec_driver_sql(f'SET search_path TO "{schema}", public')
            connection.commit()

            with connection.begin():
                _apply_revision(connection, initial)
                connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"))
                connection.execute(text("INSERT INTO alembic_version(version_num) VALUES ('0001_initial_schema')"))

            with connection.begin():
                _apply_revision(connection, auth_tokens)
                connection.execute(text("UPDATE alembic_version SET version_num='0002_auth_token_tables'"))

            with connection.begin():
                _apply_revision(connection, conversation_flow)
                connection.execute(text("UPDATE alembic_version SET version_num='0003_conversation_message_flow'"))

            with connection.begin():
                connection.execute(text(
                    "INSERT INTO users(id, email, password_hash, full_name, role) "
                    "VALUES (:id, :email, 'legacy-hash', 'Legacy Uploader', 'ADMIN')"
                ), {"id": user_id, "email": f"step51-{user_id}@example.invalid"})
                connection.execute(text(
                    "INSERT INTO documents(id, original_filename, file_type, storage_reference, "
                    "processing_status, review_status, uploaded_by) "
                    "VALUES (:id, 'legacy.txt', 'TXT', 'legacy/storage', 'UPLOADED', 'PENDING', :user_id)"
                ), {"id": document_id, "user_id": user_id})

            with connection.begin():
                _apply_revision(connection, source_policy)
                connection.execute(text("UPDATE alembic_version SET version_num='0004_document_source_policy'"))

            with connection.begin():
                legacy = connection.execute(text(
                    "SELECT original_filename, file_type, storage_reference, processing_status, review_status, "
                    "title, source_category, source_origin, source_language, usage_rights_note "
                    "FROM documents WHERE id=:id"
                ), {"id": document_id}).one()
                assert legacy == (
                    "legacy.txt", "TXT", "legacy/storage", "UPLOADED", "PENDING", None, None, None, None, None
                )
                assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0004_document_source_policy"
                physical_check_names = set(connection.execute(text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'documents'::regclass AND contype = 'c'"
                )).scalars())
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
                    name for name in physical_check_names
                    if any(name.endswith(suffix) for suffix in source_check_suffixes)
                }
                assert actual_source_check_names == expected_source_check_names

                invalid_metadata = (
                    ("source_category", "REFERENCE"),
                    ("source_language", "fr"),
                    ("title", "   "),
                    ("source_origin", "   "),
                )
                for field, value in invalid_metadata:
                    with pytest.raises(IntegrityError):
                        with connection.begin_nested():
                            connection.execute(text(
                                f"INSERT INTO documents(id, original_filename, file_type, storage_reference, "
                                f"processing_status, review_status, uploaded_by, {field}) "
                                "VALUES (:id, 'invalid.txt', 'TXT', 'invalid/storage', 'UPLOADED', 'PENDING', :user_id, :value)"
                            ), {"id": uuid4(), "user_id": user_id, "value": value})
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()


def test_upgrade_0004_to_0005_preserves_legacy_document_and_adds_raw_constraints() -> None:
    settings = get_settings()
    assert settings.app_env == "test"
    schema = f"step52_migration_{uuid4().hex}"
    user_id, document_id = uuid4(), uuid4()
    engine = create_engine(settings.effective_database_url)
    migrations = Path(__file__).resolve().parents[1] / "migrations" / "versions"
    revision_modules = [
        _load_revision(migrations / filename)
        for filename in (
            "0001_initial_schema.py", "0002_auth_token_tables.py",
            "0003_conversation_message_flow.py", "0004_document_source_policy.py",
            "0005_raw_document_metadata.py",
        )
    ]
    pre_0005_columns: set[str] | None = None
    pre_0005_constraints: set[str] | None = None
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        with engine.connect() as connection:
            connection.exec_driver_sql(f'SET search_path TO "{schema}", public')
            connection.commit()
            revision_ids = (
                "0001_initial_schema", "0002_auth_token_tables",
                "0003_conversation_message_flow", "0004_document_source_policy",
                "0005_raw_document_metadata",
            )
            with connection.begin():
                _apply_revision(connection, revision_modules[0])
                connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"))
                connection.execute(text("INSERT INTO alembic_version VALUES (:revision)"), {"revision": revision_ids[0]})
            for index, revision in enumerate(revision_modules[1:], start=1):
                with connection.begin():
                    if index == 4:
                        connection.execute(text(
                            "INSERT INTO users(id, email, password_hash, full_name, role) "
                            "VALUES (:id, :email, 'legacy-hash', 'Legacy Uploader', 'ADMIN')"
                        ), {"id": user_id, "email": f"step52-{user_id}@example.invalid"})
                        connection.execute(text(
                            "INSERT INTO documents(id, original_filename, file_type, storage_reference, "
                            "processing_status, review_status, uploaded_by, title, source_category, "
                            "source_origin, source_language) "
                            "VALUES (:id, 'legacy.txt', 'TXT', 'legacy/storage', 'UPLOADED', 'PENDING', "
                            ":user_id, 'Legacy title', 'INTERNAL_AUTHORED', 'Legacy source', 'en')"
                        ), {"id": document_id, "user_id": user_id})
                        pre_0005_columns = set(connection.execute(text(
                            "SELECT column_name FROM information_schema.columns "
                            "WHERE table_schema=:schema AND table_name='documents'"
                        ), {"schema": schema}).scalars())
                        pre_0005_constraints = set(connection.execute(text(
                            "SELECT conname FROM pg_constraint WHERE conrelid='documents'::regclass"
                        )).scalars())
                    _apply_revision(connection, revision)
                    connection.execute(text("UPDATE alembic_version SET version_num=:revision"), {"revision": revision_ids[index]})
            with connection.begin():
                row = connection.execute(text(
                    "SELECT mime_type, file_size_bytes, content_hash FROM documents WHERE id=:id"
                ), {"id": document_id}).one()
                assert row == (None, None, None)
                constraints = set(connection.execute(text(
                    "SELECT conname FROM pg_constraint WHERE conrelid='documents'::regclass"
                )).scalars())
                assert "uq_documents_content_hash" in constraints
                assert "ck_documents_file_size_positive" in constraints
                connection.execute(text(
                    "INSERT INTO documents(id, original_filename, file_type, storage_reference, "
                    "processing_status, review_status, uploaded_by) "
                    "VALUES (:id, 'legacy-2.txt', 'TXT', 'legacy/storage-2', 'UPLOADED', 'PENDING', :user_id)"
                ), {"id": uuid4(), "user_id": user_id})
                duplicate_hash = "a" * 64
                connection.execute(text(
                    "UPDATE documents SET content_hash=:hash WHERE id=:id"
                ), {"hash": duplicate_hash, "id": document_id})
                with pytest.raises(IntegrityError):
                    with connection.begin_nested():
                        connection.execute(text(
                            "INSERT INTO documents(id, original_filename, file_type, storage_reference, "
                            "processing_status, review_status, uploaded_by, content_hash) "
                            "VALUES (:id, 'duplicate.txt', 'TXT', 'legacy/duplicate', 'UPLOADED', 'PENDING', :user_id, :hash)"
                        ), {"id": uuid4(), "user_id": user_id, "hash": duplicate_hash})
                with pytest.raises(IntegrityError):
                    with connection.begin_nested():
                        connection.execute(text(
                            "UPDATE documents SET file_size_bytes=0 WHERE id=:id"
                        ), {"id": document_id})
                assert revision_modules[4].revision == "0005_raw_document_metadata"
                assert revision_modules[4].down_revision == "0004_document_source_policy"

            with connection.begin():
                _revert_revision(connection, revision_modules[4])
                connection.execute(text(
                    "UPDATE alembic_version SET version_num='0004_document_source_policy' "
                    "WHERE version_num='0005_raw_document_metadata'"
                ))

            with connection.begin():
                post_downgrade_columns = set(connection.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema=:schema AND table_name='documents'"
                ), {"schema": schema}).scalars())
                post_downgrade_constraints = set(connection.execute(text(
                    "SELECT conname FROM pg_constraint WHERE conrelid='documents'::regclass"
                )).scalars())
                assert pre_0005_columns is not None
                assert pre_0005_constraints is not None
                assert post_downgrade_columns == pre_0005_columns
                assert not {"mime_type", "file_size_bytes", "content_hash"} & post_downgrade_columns
                assert post_downgrade_constraints == pre_0005_constraints
                assert "uq_documents_content_hash" not in post_downgrade_constraints
                assert "ck_documents_file_size_positive" not in post_downgrade_constraints
                legacy = connection.execute(text(
                    "SELECT original_filename, title, source_category, source_origin, source_language "
                    "FROM documents WHERE id=:id"
                ), {"id": document_id}).one()
                assert legacy == (
                    "legacy.txt", "Legacy title", "INTERNAL_AUTHORED", "Legacy source", "en"
                )
                connection.execute(text(
                    "INSERT INTO documents(id, original_filename, file_type, storage_reference, "
                    "processing_status, review_status, uploaded_by, title, source_category, "
                    "source_origin, source_language) VALUES (:id, 'post-downgrade.txt', 'TXT', "
                    "'legacy/post-downgrade', 'UPLOADED', 'PENDING', :user_id, 'Still valid', "
                    "'INTERNAL_AUTHORED', 'Imported source', 'vi')"
                ), {"id": uuid4(), "user_id": user_id})
                assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0004_document_source_policy"
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()


def test_upgrade_0005_to_0006_adds_parsing_runs_and_downgrade_preserves_source_data() -> None:
    settings = get_settings()
    assert settings.app_env == "test"
    schema = f"step53_migration_{uuid4().hex}"
    user_id, level_id, lesson_id, document_id = [uuid4() for _ in range(4)]
    engine = create_engine(settings.effective_database_url)
    migration_dir = Path(__file__).resolve().parents[1] / "migrations" / "versions"
    files = (
        "0001_initial_schema.py", "0002_auth_token_tables.py", "0003_conversation_message_flow.py",
        "0004_document_source_policy.py", "0005_raw_document_metadata.py", "0006_parsing_runs.py",
    )
    revisions = [_load_revision(migration_dir / name) for name in files]
    revision_ids = [item.revision for item in revisions]
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        with engine.connect() as connection:
            connection.exec_driver_sql(f'SET search_path TO "{schema}", public')
            connection.commit()
            with connection.begin():
                _apply_revision(connection, revisions[0])
                connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"))
                connection.execute(text("INSERT INTO alembic_version VALUES (:revision)"), {"revision": revision_ids[0]})
            for index, revision in enumerate(revisions[1:], start=1):
                with connection.begin():
                    if index == 1:
                        connection.execute(text(
                            "INSERT INTO users(id,email,password_hash,full_name,role) "
                            "VALUES (:id,:email,'legacy','Existing User','ADMIN')"
                        ), {"id": user_id, "email": f"step53-{user_id}@example.invalid"})
                        connection.execute(text("INSERT INTO hsk_levels(id,level_number,order_index) VALUES (:id,1,1)"), {"id": level_id})
                        connection.execute(text(
                            "INSERT INTO lessons(id,hsk_level_id,lesson_number,title,status) "
                            "VALUES (:id,:level,1,'Existing lesson','PUBLISHED')"
                        ), {"id": lesson_id, "level": level_id})
                        connection.execute(text(
                            "INSERT INTO documents(id,original_filename,file_type,storage_reference,processing_status,review_status,uploaded_by) "
                            "VALUES (:id,'existing.txt','TXT','raw/key','UPLOADED','PENDING',:user)"
                        ), {"id": document_id, "user": user_id})
                    _apply_revision(connection, revision)
                    connection.execute(text("UPDATE alembic_version SET version_num=:revision"), {"revision": revision_ids[index]})
            with connection.begin():
                assert connection.execute(text("SELECT title FROM lessons WHERE id=:id"), {"id": lesson_id}).scalar_one() == "Existing lesson"
                assert connection.execute(text("SELECT storage_reference FROM documents WHERE id=:id"), {"id": document_id}).scalar_one() == "raw/key"
                assert "parsing_runs" in inspect(connection).get_table_names(schema=schema)
                assert revisions[5].revision == "0006_parsing_runs"
                assert revisions[5].down_revision == "0005_raw_document_metadata"
            with connection.begin():
                _revert_revision(connection, revisions[5])
                connection.execute(text("UPDATE alembic_version SET version_num='0005_raw_document_metadata'"))
            with connection.begin():
                assert "parsing_runs" not in inspect(connection).get_table_names(schema=schema)
                assert connection.execute(text("SELECT title FROM lessons WHERE id=:id"), {"id": lesson_id}).scalar_one() == "Existing lesson"
                assert connection.execute(text("SELECT storage_reference FROM documents WHERE id=:id"), {"id": document_id}).scalar_one() == "raw/key"
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()


def test_upgrade_0006_to_0007_preserves_source_and_parsing_data_on_downgrade() -> None:
    settings = get_settings()
    assert settings.app_env == "test"
    schema = f"step54_migration_{uuid4().hex}"
    user_id, level_id, lesson_id, document_id, parsing_id = [uuid4() for _ in range(5)]
    engine = create_engine(settings.effective_database_url)
    migration_dir = Path(__file__).resolve().parents[1] / "migrations" / "versions"
    files = (
        "0001_initial_schema.py", "0002_auth_token_tables.py", "0003_conversation_message_flow.py",
        "0004_document_source_policy.py", "0005_raw_document_metadata.py", "0006_parsing_runs.py",
        "0007_transformation_runs.py",
    )
    revisions = [_load_revision(migration_dir / filename) for filename in files]
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        with engine.connect() as connection:
            connection.exec_driver_sql(f'SET search_path TO "{schema}", public')
            connection.commit()
            with connection.begin():
                _apply_revision(connection, revisions[0])
                connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"))
                connection.execute(text("INSERT INTO alembic_version VALUES (:revision)"), {"revision": revisions[0].revision})
            for revision in revisions[1:]:
                with connection.begin():
                    if revision.revision == "0002_auth_token_tables":
                        connection.execute(text(
                            "INSERT INTO users(id,email,password_hash,full_name,role) "
                            "VALUES (:id,:email,'migration-hash','Existing Admin','ADMIN')"
                        ), {"id": user_id, "email": f"step54-{user_id}@example.invalid"})
                        connection.execute(text("INSERT INTO hsk_levels(id,level_number,order_index) VALUES (:id,1,1)"), {"id": level_id})
                        connection.execute(text(
                            "INSERT INTO lessons(id,hsk_level_id,lesson_number,title,status) "
                            "VALUES (:id,:level,1,'Existing lesson','PUBLISHED')"
                        ), {"id": lesson_id, "level": level_id})
                        
                    if revision.revision == "0006_parsing_runs":
                        connection.execute(text(
                            "INSERT INTO documents(id,original_filename,file_type,storage_reference,"
                            "processing_status,review_status,uploaded_by,title,source_category,source_origin,source_language) "
                            "VALUES (:id,'existing.txt','TXT','raw/key','UPLOADED','PENDING',:user,'Existing document',"
                            "'INTERNAL_AUTHORED','Existing source','en')"
                        ), {"id": document_id, "user": user_id})
                    if revision.revision == "0007_transformation_runs":
                        connection.execute(text(
                            "INSERT INTO parsing_runs(id,source_type,document_id,raw_storage_reference,raw_content_hash,"
                            "parser_name,parser_version,cleaning_strategy,cleaning_version,status,parsed_storage_reference) "
                            "VALUES (:id,'DOCUMENT',:document,'raw/key',:hash,'test','v1','test','v1','SUCCEEDED','parsed/key')"
                        ), {"id": parsing_id, "document": document_id, "hash": "a" * 64})
                    _apply_revision(connection, revision)
                    connection.execute(text("UPDATE alembic_version SET version_num=:revision"), {"revision": revision.revision})
            with connection.begin():
                assert revisions[-1].revision == "0007_transformation_runs"
                assert revisions[-1].down_revision == "0006_parsing_runs"
                assert "transformation_runs" in inspect(connection).get_table_names(schema=schema)
                assert connection.execute(text("SELECT title FROM documents WHERE id=:id"), {"id": document_id}).scalar_one() == "Existing document"
                assert connection.execute(text("SELECT status FROM parsing_runs WHERE id=:id"), {"id": parsing_id}).scalar_one() == "SUCCEEDED"
                columns = {column["name"] for column in inspect(connection).get_columns("transformation_runs", schema=schema)}
                assert "source_metadata_snapshot" in columns
                connection.execute(text(
                    "INSERT INTO transformation_runs(id,source_type,document_id,parsing_run_id,parsed_storage_reference,"
                    "transformation_strategy,transformation_version,status,source_metadata_snapshot) "
                    "VALUES (:id,'DOCUMENT',:document,:parsing,'parsed/key','canonical_document','v1','PENDING',:snapshot)"
                ), {"id": uuid4(), "document": document_id, "parsing": parsing_id, "snapshot": '{"title":"Existing document"}'})
                with pytest.raises(IntegrityError):
                    with connection.begin_nested():
                        connection.execute(text(
                            "INSERT INTO transformation_runs(id,source_type,document_id,lesson_id,parsing_run_id,"
                            "parsed_storage_reference,transformation_strategy,transformation_version,status,source_metadata_snapshot) "
                            "VALUES (:id,'DOCUMENT',:document,:lesson,:parsing,'parsed/key','canonical_document','v1','PENDING','{}')"
                        ), {"id": uuid4(), "document": document_id, "lesson": lesson_id, "parsing": parsing_id})
            with connection.begin():
                _revert_revision(connection, revisions[-1])
                connection.execute(text("UPDATE alembic_version SET version_num='0006_parsing_runs'"))
            with connection.begin():
                assert "transformation_runs" not in inspect(connection).get_table_names(schema=schema)
                assert connection.execute(text("SELECT title FROM documents WHERE id=:id"), {"id": document_id}).scalar_one() == "Existing document"
                assert connection.execute(text("SELECT status FROM parsing_runs WHERE id=:id"), {"id": parsing_id}).scalar_one() == "SUCCEEDED"
                assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0006_parsing_runs"
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()


def test_upgrade_0007_to_0008_preserves_legacy_knowledge_and_downgrade_removes_only_new_columns() -> None:
    settings = get_settings()
    assert settings.app_env == "test"
    schema = f"step55_migration_{uuid4().hex}"
    user_id, level_id, lesson_id, source_id, version_id, chunk_id = [uuid4() for _ in range(6)]
    engine = create_engine(settings.effective_database_url)
    migration_dir = Path(__file__).resolve().parents[1] / "migrations" / "versions"
    filenames = (
        "0001_initial_schema.py", "0002_auth_token_tables.py", "0003_conversation_message_flow.py",
        "0004_document_source_policy.py", "0005_raw_document_metadata.py", "0006_parsing_runs.py",
        "0007_transformation_runs.py", "0008_chunking_contract.py",
    )
    revisions = [_load_revision(migration_dir / filename) for filename in filenames]
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        with engine.connect() as connection:
            connection.exec_driver_sql(f'SET search_path TO "{schema}", public')
            connection.commit()
            with connection.begin():
                _apply_revision(connection, revisions[0])
                connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"))
                connection.execute(text("INSERT INTO alembic_version VALUES (:revision)"), {"revision": revisions[0].revision})
            for revision in revisions[1:7]:
                with connection.begin():
                    _apply_revision(connection, revision)
                    connection.execute(text("UPDATE alembic_version SET version_num=:revision"), {"revision": revision.revision})
            with connection.begin():
                connection.execute(text(
                    "INSERT INTO users(id,email,password_hash,full_name,role) "
                    "VALUES (:id,:email,'legacy','Migration user','ADMIN')"
                ), {"id": user_id, "email": f"step55-{user_id}@example.invalid"})
                connection.execute(text("INSERT INTO hsk_levels(id,level_number,order_index) VALUES (:id,1,1)"), {"id": level_id})
                connection.execute(text(
                    "INSERT INTO lessons(id,hsk_level_id,lesson_number,title,status) "
                    "VALUES (:id,:level,1,'Legacy lesson','PUBLISHED')"
                ), {"id": lesson_id, "level": level_id})
                connection.execute(text(
                    "INSERT INTO knowledge_sources(id,source_type,lesson_id) VALUES (:id,'LESSON',:lesson)"
                ), {"id": source_id, "lesson": lesson_id})
                connection.execute(text(
                    "INSERT INTO knowledge_versions(id,knowledge_source_id,version_number,status) "
                    "VALUES (:id,:source,1,'PROCESSING')"
                ), {"id": version_id, "source": source_id})
                connection.execute(text(
                    "INSERT INTO chunks(id,knowledge_version_id,content,content_type,chunk_index,lesson_id,metadata) "
                    "VALUES (:id,:version,'legacy chunk','LESSON_GENERAL',0,:lesson,'{}')"
                ), {"id": chunk_id, "version": version_id, "lesson": lesson_id})
            with connection.begin():
                _apply_revision(connection, revisions[7])
                connection.execute(text("UPDATE alembic_version SET version_num=:revision"), {"revision": revisions[7].revision})
                assert revisions[7].revision == "0008_chunking_contract"
                assert revisions[7].down_revision == "0007_transformation_runs"
                columns = {
                    table: {item["name"]: item for item in inspect(connection).get_columns(table, schema=schema)}
                    for table in ("knowledge_versions", "chunks")
                }
                assert columns["knowledge_versions"]["chunking_version"]["nullable"] is True
                assert columns["knowledge_versions"]["chunk_max_chars"]["nullable"] is True
                assert columns["chunks"]["content_hash"]["nullable"] is True
                assert connection.execute(text(
                    "SELECT content FROM chunks WHERE id=:id"
                ), {"id": chunk_id}).scalar_one() == "legacy chunk"
                assert connection.execute(text(
                    "SELECT chunking_version,chunk_max_chars FROM knowledge_versions WHERE id=:id"
                ), {"id": version_id}).one() == (None, None)
                connection.execute(text(
                    "UPDATE knowledge_versions SET chunking_strategy='structure_aware',chunking_version='v1',"
                    "chunk_size=1200,chunk_max_chars=1800,chunk_overlap=150 WHERE id=:id"
                ), {"id": version_id})
                connection.execute(text("UPDATE chunks SET content_hash=:hash WHERE id=:id"), {"id": chunk_id, "hash": "b" * 64})
                assert connection.execute(text("SELECT content_hash FROM chunks WHERE id=:id"), {"id": chunk_id}).scalar_one() == "b" * 64
            with connection.begin():
                _revert_revision(connection, revisions[7])
                connection.execute(text("UPDATE alembic_version SET version_num='0007_transformation_runs'"))
            with connection.begin():
                version_columns = {item["name"] for item in inspect(connection).get_columns("knowledge_versions", schema=schema)}
                chunk_columns = {item["name"] for item in inspect(connection).get_columns("chunks", schema=schema)}
                assert not {"chunking_version", "chunk_max_chars"} & version_columns
                assert "content_hash" not in chunk_columns
                assert connection.execute(text("SELECT content FROM chunks WHERE id=:id"), {"id": chunk_id}).scalar_one() == "legacy chunk"
                assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0007_transformation_runs"
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()
