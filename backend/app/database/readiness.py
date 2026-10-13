from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.errors import ApplicationError
from app.database.engine import engine


async def check_database_readiness() -> None:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise ApplicationError(
            code="DATABASE_NOT_READY",
            message="Database dependency is not ready",
            details=None,
            status_code=503,
        ) from exc
