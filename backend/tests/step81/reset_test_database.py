"""Reset only the dedicated Step 8.1 PostgreSQL test database.

This intentionally requires an explicit command-line confirmation and rechecks
the resolved database identity immediately before truncating application data.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.database.base import Base
from app.database import models as _models  # noqa: F401 - populate metadata
from app.database.seeds.required import seed_required_data

EXPECTED_DB = "chinese_learning_test"
LOOPBACK = {"localhost", "127.0.0.1", "::1"}


def _migration_heads() -> set[str]:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    return set(ScriptDirectory.from_config(config).get_heads())


def _identity(url: str) -> tuple[str, int, str | None]:
    parsed = make_url(url)
    return (parsed.host or "").lower(), parsed.port or 5432, parsed.database


async def _reset() -> None:
    settings = get_settings()
    if settings.app_env != "test":
        raise RuntimeError("APP_ENV must be test")
    if not settings.test_database_url:
        raise RuntimeError("TEST_DATABASE_URL is required")
    target = make_url(settings.test_database_url)
    if target.drivername != "postgresql+psycopg":
        raise RuntimeError("TEST_DATABASE_URL must use PostgreSQL with psycopg")
    if target.database != EXPECTED_DB or target.host not in LOOPBACK:
        raise RuntimeError("TEST_DATABASE_URL must target the local dedicated test database")
    if settings.database_url and _identity(settings.database_url) == _identity(settings.test_database_url):
        raise RuntimeError("TEST_DATABASE_URL must differ from DATABASE_URL")

    engine = create_async_engine(settings.effective_database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("""
                select current_database(),
                    (select extversion from pg_extension where extname='vector')
            """))
            db, vector = result.one()
            actual_heads = set((await connection.execute(
                text("select version_num from alembic_version")
            )).scalars().all())
            if db != EXPECTED_DB or not vector or actual_heads != _migration_heads():
                raise RuntimeError("Test DB identity, pgvector, or migration-head check failed")
            table_names = sorted(
                table.name for table in Base.metadata.sorted_tables
                if table.name != "alembic_version"
            )
            quoted = ", ".join(f'"{name}"' for name in table_names)
            await connection.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))
            await connection.commit()
    finally:
        await engine.dispose()

    await seed_required_data()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm-test-database-reset", action="store_true",
        help="confirm that application rows in chinese_learning_test may be cleared",
    )
    args = parser.parse_args()
    if not args.confirm_test_database_reset:
        parser.error("pass --confirm-test-database-reset to proceed")
    try:
        asyncio.run(_reset())
    except Exception as exc:
        # Do not echo connection strings or driver exception text.
        print(f"RESET=FAIL ({type(exc).__name__})", file=sys.stderr)
        raise SystemExit(1) from None
    print("RESET=PASS")
    print("DATABASE=localhost:5432/chinese_learning_test")
    print("SEEDED=3 required HSK levels; 3 required pronunciation sections")


if __name__ == "__main__":
    main()
