from __future__ import annotations

import hashlib
import logging
import asyncio
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import text

from app.ai.rag.errors import DUPLICATE_RAG_GENERATION, rag_error
from app.database.engine import engine

logger = logging.getLogger("app.conversation")


def advisory_key(assistant_message_id: UUID) -> int:
    """Stable signed int64; collisions can only cause rare false contention."""
    digest = hashlib.sha256(assistant_message_id.bytes).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=True)


@asynccontextmanager
async def assistant_processing_lock(assistant_message_id: UUID):
    key = advisory_key(assistant_message_id)
    connection = await engine.connect()
    acquired = False
    acquisition_started = False
    acquisition_completed = False
    try:
        acquisition_started = True
        acquired = bool((await connection.execute(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": key}
        )).scalar_one())
        await connection.commit()  # session lock survives; release acquisition transaction
        acquisition_completed = True
        if not acquired:
            logger.info("assistant_processing_lock_duplicate", extra={
                "assistant_message_id": str(assistant_message_id),
                "lock_acquired": False,
                "duplicate_processing": True,
                "error_code": DUPLICATE_RAG_GENERATION,
            })
            raise rag_error(DUPLICATE_RAG_GENERATION)
        if connection.in_transaction():
            raise RuntimeError("advisory lock connection retained an acquisition transaction")
        logger.info("assistant_processing_lock_acquired", extra={
            "assistant_message_id": str(assistant_message_id),
            "lock_acquired": True,
            "duplicate_processing": False,
            "error_code": None,
        })
        yield connection
    finally:
        try:
            if acquisition_started and not acquisition_completed:
                # Acquisition outcome may be uncertain after driver/network failure.
                await asyncio.shield(connection.invalidate())
            elif acquired:
                try:
                    if connection.in_transaction():
                        await connection.rollback()
                    unlocked = bool((await connection.execute(
                        text("SELECT pg_advisory_unlock(:key)"), {"key": key}
                    )).scalar_one())
                    await connection.commit()
                    if not unlocked:
                        raise RuntimeError("advisory lock was not owned during release")
                    logger.info("assistant_processing_lock_released", extra={
                        "assistant_message_id": str(assistant_message_id),
                        "lock_acquired": True,
                        "lock_release_status": "RELEASED",
                        "error_code": None,
                    })
                except BaseException as exc:
                    logger.error("assistant_processing_lock_release_failed", extra={
                        "assistant_message_id": str(assistant_message_id),
                        "lock_acquired": True,
                        "lock_release_status": "INVALIDATED",
                        "error_code": "PROCESSING_LOCK_RELEASE_FAILED",
                    })
                    await asyncio.shield(connection.invalidate())
                    if isinstance(exc, asyncio.CancelledError):
                        raise
        finally:
            await asyncio.shield(connection.close())
