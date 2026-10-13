"""Verify a local Step 8.2 PostgreSQL database and its current migration head."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings

EXPECTED_DATABASES = {
    "development": "chinese_learning",
    "test": "chinese_learning_test",
}
LOOPBACK = {"localhost", "127.0.0.1", "::1"}


def _migration_heads() -> set[str]:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    return set(ScriptDirectory.from_config(config).get_heads())


async def _verify(expected_environment: str) -> None:
    settings = get_settings()
    if settings.app_env != expected_environment:
        raise RuntimeError("APP_ENV does not match the requested database role")
    url = make_url(settings.effective_database_url)
    expected_database = EXPECTED_DATABASES[expected_environment]
    if url.drivername != "postgresql+psycopg" or url.database != expected_database:
        raise RuntimeError("Effective database identity does not match the requested role")
    if url.host not in LOOPBACK:
        raise RuntimeError("Local Step 8.2 databases must use a loopback host")
    if settings.database_url and settings.test_database_url:
        normal = make_url(settings.database_url)
        test = make_url(settings.test_database_url)
        normal_identity = ((normal.host or "").lower(), normal.port or 5432, normal.database)
        test_identity = ((test.host or "").lower(), test.port or 5432, test.database)
        if normal_identity == test_identity:
            raise RuntimeError("DATABASE_URL and TEST_DATABASE_URL must be distinct")

    engine = create_async_engine(settings.effective_database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            row = (await connection.execute(text("""
                select current_database(),
                    current_setting('server_version_num'),
                    (select extversion from pg_extension where extname = 'vector')
            """))).one()
            database, postgres_version_num, pgvector_version = row
            versions = set((await connection.execute(
                text("select version_num from alembic_version")
            )).scalars().all())
    finally:
        await engine.dispose()

    expected_heads = _migration_heads()
    if (
        database != expected_database
        or int(postgres_version_num) // 10_000 != 17
        or not pgvector_version
    ):
        raise RuntimeError("Database identity, PostgreSQL 17, or pgvector verification failed")
    if versions != expected_heads:
        raise RuntimeError("Database Alembic revision does not match the current repository head")
    print(f"DATABASE=PASS role={expected_environment} name={database}")
    print(f"POSTGRES=PASS major=17 version_num={postgres_version_num}")
    print(f"PGVECTOR=PASS version={pgvector_version}")
    print(f"ALEMBIC_HEAD=PASS revision={','.join(sorted(versions))}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", choices=EXPECTED_DATABASES, required=True)
    args = parser.parse_args()
    try:
        asyncio.run(_verify(args.environment))
    except Exception as exc:
        # Driver exceptions can contain connection details; emit only a safe category.
        print(f"DATABASE_VERIFY=FAIL error={type(exc).__name__}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
