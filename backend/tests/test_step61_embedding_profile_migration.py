import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings


def test_0011_adds_nullable_identity_fields_preserves_legacy_and_downgrades() -> None:
    settings = get_settings()
    assert settings.app_env == "test"
    schema = f"step61_migration_{uuid4().hex}"
    migration_path = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "0011_embedding_profile_identity.py"
    spec = importlib.util.spec_from_file_location(migration_path.stem, migration_path)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.revision == "0011_embedding_profile_identity"
    assert migration.down_revision == "0010_incremental_reprocessing_contract"
    engine = create_engine(settings.effective_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        with engine.connect() as connection:
            connection.exec_driver_sql(f'SET search_path TO "{schema}", public')
            connection.commit()
            with connection.begin():
                connection.execute(text("CREATE TABLE embedding_profiles (id uuid PRIMARY KEY, provider text NOT NULL, model_name text NOT NULL, model_version text, dimensions integer NOT NULL, status varchar NOT NULL, created_at timestamptz NOT NULL DEFAULT now())"))
                legacy_id = uuid4()
                connection.execute(text("INSERT INTO embedding_profiles(id,provider,model_name,dimensions,status) VALUES (:id,'LOCAL','legacy',384,'INACTIVE')"), {"id": legacy_id})
            with connection.begin():
                with Operations.context(MigrationContext.configure(connection)):
                    migration.upgrade()
                columns = {column["name"]: column for column in inspect(connection).get_columns("embedding_profiles")}
                assert {"provider_version", "embedding_input_version", "normalize_embeddings"} <= set(columns)
                assert all(columns[name]["nullable"] for name in ("provider_version", "embedding_input_version", "normalize_embeddings"))
                assert connection.execute(text("SELECT model_name FROM embedding_profiles WHERE id=:id"), {"id": legacy_id}).scalar_one() == "legacy"
                assert connection.execute(text("SELECT provider_version,embedding_input_version,normalize_embeddings FROM embedding_profiles WHERE id=:id"), {"id": legacy_id}).one() == (None, None, None)
                connection.execute(text("INSERT INTO embedding_profiles(id,provider,provider_version,model_name,model_version,dimensions,embedding_input_version,normalize_embeddings,status) VALUES (:id,'LOCAL','sentence-transformers/6.1.0','BAAI/bge-m3','rev',1024,'v1',true,'INACTIVE')"), {"id": uuid4()})
                with pytest.raises(IntegrityError):
                    with connection.begin_nested():
                        connection.execute(text("INSERT INTO embedding_profiles(id,provider,provider_version,model_name,model_version,dimensions,embedding_input_version,normalize_embeddings,status) VALUES (:id,'LOCAL','sentence-transformers/6.1.0','BAAI/bge-m3','rev',1024,'v1',true,'ACTIVE')"), {"id": uuid4()})
                connection.execute(text("INSERT INTO embedding_profiles(id,provider,provider_version,model_name,model_version,dimensions,embedding_input_version,normalize_embeddings,status) VALUES (:id,'LOCAL','sentence-transformers/6.1.0','BAAI/bge-m3','rev',1024,'v2',true,'INACTIVE')"), {"id": uuid4()})
                connection.execute(text("INSERT INTO embedding_profiles(id,provider,provider_version,model_name,model_version,dimensions,embedding_input_version,normalize_embeddings,status) VALUES (:id,'LOCAL','sentence-transformers/6.1.0','BAAI/bge-m3','rev',1024,'v1',false,'INACTIVE')"), {"id": uuid4()})
            with connection.begin():
                with Operations.context(MigrationContext.configure(connection)):
                    migration.downgrade()
                assert {column["name"] for column in inspect(connection).get_columns("embedding_profiles")} == {
                    "id", "provider", "model_name", "model_version", "dimensions", "status", "created_at"
                }
                assert connection.execute(text("SELECT count(*) FROM embedding_profiles")).scalar_one() == 4
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()
