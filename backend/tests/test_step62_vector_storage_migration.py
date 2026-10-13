import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings

FK_NAME = "fk_embeddings_chunk_id_chunks"


def _migration():
    path = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "0012_vector_storage_readiness.py"
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "0012_vector_storage_readiness"
    assert module.down_revision == "0011_embedding_profile_identity"
    return module


def _assert_fk(connection, expected_ondelete):
    constraints = inspect(connection).get_foreign_keys("embeddings")
    matching = [constraint for constraint in constraints if constraint["name"] == FK_NAME]
    assert len(matching) == 1
    assert matching[0]["constrained_columns"] == ["chunk_id"]
    assert matching[0]["referred_table"] == "chunks"
    assert matching[0]["referred_columns"] == ["id"]
    assert matching[0]["options"].get("ondelete") == expected_ondelete


def _create_0011_schema(connection, schema, active_count):
    connection.exec_driver_sql(f'SET search_path TO "{schema}", public')
    connection.commit()
    with connection.begin():
        connection.execute(text("CREATE TABLE chunks (id uuid PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE embedding_profiles (id uuid PRIMARY KEY, status varchar NOT NULL)"))
        connection.execute(text(f"""
            CREATE TABLE embeddings (
              id uuid PRIMARY KEY,
              chunk_id uuid NOT NULL,
              embedding_profile_id uuid NOT NULL,
              CONSTRAINT {FK_NAME} FOREIGN KEY(chunk_id) REFERENCES chunks(id),
              CONSTRAINT fk_embeddings_embedding_profile_id_embedding_profiles
                FOREIGN KEY(embedding_profile_id) REFERENCES embedding_profiles(id),
              CONSTRAINT uq_embeddings_chunk_id_embedding_profile_id UNIQUE(chunk_id, embedding_profile_id)
            )
        """))
        for _ in range(active_count):
            connection.execute(text("INSERT INTO embedding_profiles(id,status) VALUES (:id,'ACTIVE')"), {"id": uuid4()})
    with connection.begin():
        _assert_fk(connection, None)


@pytest.mark.parametrize("active_count", [0, 1])
def test_0012_valid_0011_state_upgrade_downgrade_reupgrade(active_count):
    settings = get_settings()
    assert settings.app_env == "test"
    schema = f"step62_valid_{uuid4().hex}"
    engine = create_engine(settings.effective_database_url)
    migration = _migration()
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        with engine.connect() as connection:
            _create_0011_schema(connection, schema, active_count)
            with connection.begin():
                with Operations.context(MigrationContext.configure(connection)):
                    migration.upgrade()
                _assert_fk(connection, "CASCADE")
                emb_indexes = {item["name"] for item in inspect(connection).get_indexes("embeddings")}
                profile_indexes = {item["name"] for item in inspect(connection).get_indexes("embedding_profiles")}
                assert "ix_embeddings_embedding_profile_id" in emb_indexes
                assert "uq_embedding_profiles_one_active" in profile_indexes
                active_index = next(item for item in inspect(connection).get_indexes("embedding_profiles")
                                    if item["name"] == "uq_embedding_profiles_one_active")
                assert active_index["unique"] is True
                predicate = active_index["dialect_options"]["postgresql_where"]
                assert "status" in predicate and "ACTIVE" in predicate
                index_method = connection.execute(text("""
                    SELECT am.amname
                    FROM pg_class idx
                    JOIN pg_namespace n ON n.oid=idx.relnamespace
                    JOIN pg_index i ON i.indexrelid=idx.oid
                    JOIN pg_am am ON am.oid=idx.relam
                    WHERE n.nspname=:schema AND idx.relname='ix_embeddings_embedding_profile_id'
                """), {"schema": schema}).scalar_one()
                assert index_method == "btree"
                ann_indexes = connection.execute(text("""
                    SELECT count(*) FROM pg_indexes
                    WHERE schemaname=:schema AND (indexdef ILIKE '%hnsw%' OR indexdef ILIKE '%ivfflat%')
                """), {"schema": schema}).scalar_one()
                assert ann_indexes == 0
                active_count_now = connection.execute(text(
                    "SELECT count(*) FROM embedding_profiles WHERE status='ACTIVE'"
                )).scalar_one()
                assert active_count_now == active_count
                profile_id = uuid4()
                chunk_id = uuid4()
                embedding_id = uuid4()
                connection.execute(text("INSERT INTO embedding_profiles(id,status) VALUES (:id,'INACTIVE')"),
                                   {"id": profile_id})
                connection.execute(text("INSERT INTO chunks(id) VALUES (:id)"), {"id": chunk_id})
                connection.execute(text("INSERT INTO embeddings(id,chunk_id,embedding_profile_id) VALUES (:e,:c,:p)"),
                                   {"e": embedding_id, "c": chunk_id, "p": profile_id})
                with pytest.raises(IntegrityError):
                    with connection.begin_nested():
                        connection.execute(text("DELETE FROM embedding_profiles WHERE id=:id"), {"id": profile_id})
                connection.execute(text("DELETE FROM chunks WHERE id=:id"), {"id": chunk_id})
                assert connection.execute(text("SELECT count(*) FROM embeddings WHERE id=:id"),
                                          {"id": embedding_id}).scalar_one() == 0
                if active_count == 0:
                    connection.execute(text("INSERT INTO embedding_profiles(id,status) VALUES (:id,'ACTIVE')"), {"id": uuid4()})
                with pytest.raises(IntegrityError):
                    with connection.begin_nested():
                        connection.execute(text("INSERT INTO embedding_profiles(id,status) VALUES (:id,'ACTIVE')"), {"id": uuid4()})
            with connection.begin():
                with Operations.context(MigrationContext.configure(connection)):
                    migration.downgrade()
                _assert_fk(connection, None)
                assert "ix_embeddings_embedding_profile_id" not in {
                    item["name"] for item in inspect(connection).get_indexes("embeddings")
                }
                assert "uq_embedding_profiles_one_active" not in {
                    item["name"] for item in inspect(connection).get_indexes("embedding_profiles")
                }
            with connection.begin():
                with Operations.context(MigrationContext.configure(connection)):
                    migration.upgrade()
                _assert_fk(connection, "CASCADE")
                assert "ix_embeddings_embedding_profile_id" in {
                    item["name"] for item in inspect(connection).get_indexes("embeddings")
                }
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()


def test_0012_rejects_two_active_legacy_profiles_without_choosing_or_deactivating():
    settings = get_settings()
    assert settings.app_env == "test"
    schema = f"step62_invalid_{uuid4().hex}"
    engine = create_engine(settings.effective_database_url)
    migration = _migration()
    profile_ids = [uuid4(), uuid4()]
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        with engine.connect() as connection:
            _create_0011_schema(connection, schema, 0)
            with connection.begin():
                connection.execute(text("INSERT INTO embedding_profiles(id,status) VALUES (:a,'ACTIVE'),(:b,'ACTIVE')"),
                                   {"a": profile_ids[0], "b": profile_ids[1]})
            with pytest.raises(IntegrityError):
                with connection.begin():
                    with Operations.context(MigrationContext.configure(connection)):
                        migration.upgrade()
            with connection.begin():
                rows = connection.execute(text("SELECT id,status FROM embedding_profiles ORDER BY id")).all()
                assert [(row.id, row.status) for row in rows] == sorted(
                    [(profile_ids[0], "ACTIVE"), (profile_ids[1], "ACTIVE")], key=lambda item: item[0]
                )
                _assert_fk(connection, None)
                assert "ix_embeddings_embedding_profile_id" not in {
                    item["name"] for item in inspect(connection).get_indexes("embeddings")
                }
                assert "uq_embedding_profiles_one_active" not in {
                    item["name"] for item in inspect(connection).get_indexes("embedding_profiles")
                }
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()


def test_orm_metadata_matches_step62_schema():
    from app.database.models import Embedding, EmbeddingProfile
    assert "ix_embeddings_embedding_profile_id" in {index.name for index in Embedding.__table__.indexes}
    assert "uq_embedding_profiles_one_active" in {index.name for index in EmbeddingProfile.__table__.indexes}
    chunk_fk = next(fk for fk in Embedding.__table__.foreign_keys if fk.parent.name == "chunk_id")
    assert chunk_fk.ondelete == "CASCADE"
    assert Embedding.__table__.c.vector.nullable is False
    assert Embedding.__table__.c.vector.type.dim is None
    assert "embedding_profile_id" not in EmbeddingProfile.__table__.c
