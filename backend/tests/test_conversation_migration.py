import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text

from app.core.config import get_settings


def _revision(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _upgrade(connection, module) -> None:
    with Operations.context(MigrationContext.configure(connection)):
        module.upgrade()


def test_migration_0002_to_0003_preserves_and_orders_historical_messages():
    settings = get_settings()
    assert settings.app_env == "test"
    schema = f"step36_backfill_{uuid4().hex}"
    user_id, hsk_id, lesson_id, conversation_id = uuid4(), uuid4(), uuid4(), uuid4()
    message_ids = [UUID("00000000-0000-0000-0000-000000000001"), UUID("00000000-0000-0000-0000-000000000002"), uuid4()]
    created = datetime(2024, 1, 1, tzinfo=UTC)
    engine = create_engine(settings.effective_database_url)
    versions = Path(__file__).resolve().parents[1] / "migrations" / "versions"
    initial = _revision(versions / "0001_initial_schema.py")
    auth = _revision(versions / "0002_auth_token_tables.py")
    conversation = _revision(versions / "0003_conversation_message_flow.py")

    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        with engine.connect() as connection:
            connection.exec_driver_sql(f'SET search_path TO "{schema}", public')
            connection.commit()
            with connection.begin():
                _upgrade(connection, initial)
            with connection.begin():
                _upgrade(connection, auth)
                connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"))
                connection.execute(text("INSERT INTO alembic_version(version_num) VALUES ('0002_auth_token_tables')"))
            with connection.begin():
                connection.execute(text(
                    "INSERT INTO users(id,email,password_hash,full_name,role) VALUES (:id,:email,'hash','History','LEARNER')"
                ), {"id": user_id, "email": f"history-{user_id}@example.invalid"})
                connection.execute(text("INSERT INTO hsk_levels(id,level_number,order_index) VALUES (:id,1,1)"), {"id": hsk_id})
                connection.execute(text(
                    "INSERT INTO lessons(id,hsk_level_id,lesson_number,title,status) VALUES (:id,:hsk,1,'History','PUBLISHED')"
                ), {"id": lesson_id, "hsk": hsk_id})
                connection.execute(text(
                    "INSERT INTO conversations(id,user_id,lesson_id,title) VALUES (:id,:user,:lesson,'Historical')"
                ), {"id": conversation_id, "user": user_id, "lesson": lesson_id})
                rows = [
                    {"id": message_ids[0], "conversation": conversation_id, "role": "USER", "content": "first", "status": "COMPLETED", "created": created},
                    {"id": message_ids[1], "conversation": conversation_id, "role": "ASSISTANT", "content": "answer", "status": "COMPLETED", "created": created},
                    {"id": message_ids[2], "conversation": conversation_id, "role": "USER", "content": "later", "status": "COMPLETED", "created": created + timedelta(seconds=1)},
                ]
                connection.execute(text(
                    "INSERT INTO messages(id,conversation_id,role,content,status,created_at) "
                    "VALUES (:id,:conversation,:role,:content,:status,:created)"
                ), rows)
            with connection.begin():
                _upgrade(connection, conversation)
                connection.execute(text(
                    "UPDATE alembic_version SET version_num='0003_conversation_message_flow' "
                    "WHERE version_num='0002_auth_token_tables'"
                ))
            with connection.begin():
                rows = connection.execute(text(
                    "SELECT id,sequence_number,reply_to_message_id FROM messages WHERE conversation_id=:id "
                    "ORDER BY sequence_number"
                ), {"id": conversation_id}).all()
                assert [(row.id, row.sequence_number, row.reply_to_message_id) for row in rows] == [
                    (message_ids[0], 1, None),
                    (message_ids[1], 2, None),
                    (message_ids[2], 3, None),
                ]
                assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0003_conversation_message_flow"
                assert connection.execute(text(
                    "SELECT deleted_at FROM conversations WHERE id=:id"
                ), {"id": conversation_id}).scalar_one() is None
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()
