from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import PasswordResetToken, RefreshToken, User


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == email))


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.get(User, user_id)


async def lock_user_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    query = select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True)
    return await session.scalar(query)


async def add_user(session: AsyncSession, user: User) -> None:
    session.add(user)
    await session.flush()


async def update_password_hash(session: AsyncSession, user: User, password_hash: str) -> None:
    user.password_hash = password_hash


async def get_refresh_user_id_by_hash(session: AsyncSession, value: str) -> UUID | None:
    return await session.scalar(select(RefreshToken.user_id).where(RefreshToken.token_hash == value))


async def get_refresh_by_hash(
    session: AsyncSession, value: str, *, for_update: bool = False
) -> RefreshToken | None:
    query = select(RefreshToken).where(RefreshToken.token_hash == value)
    if for_update:
        query = query.with_for_update()
    return await session.scalar(query)


async def add_refresh_token(session: AsyncSession, token: RefreshToken) -> None:
    session.add(token)


async def revoke_refresh_token(session: AsyncSession, token: RefreshToken) -> None:
    token.revoked_at = datetime.now(UTC)


async def revoke_all_refresh_tokens(session: AsyncSession, user_id: UUID) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


async def get_reset_user_id_by_hash(session: AsyncSession, value: str) -> UUID | None:
    return await session.scalar(select(PasswordResetToken.user_id).where(PasswordResetToken.token_hash == value))


async def get_reset_by_hash(
    session: AsyncSession, value: str, *, for_update: bool = False
) -> PasswordResetToken | None:
    query = select(PasswordResetToken).where(PasswordResetToken.token_hash == value)
    if for_update:
        query = query.with_for_update()
    return await session.scalar(query)


async def add_reset_token(session: AsyncSession, token: PasswordResetToken) -> None:
    session.add(token)


async def invalidate_reset_tokens(
    session: AsyncSession, user_id: UUID, *, except_id: UUID | None = None
) -> None:
    query = update(PasswordResetToken).where(
        PasswordResetToken.user_id == user_id,
        PasswordResetToken.used_at.is_(None),
    )
    if except_id is not None:
        query = query.where(PasswordResetToken.id != except_id)
    await session.execute(query.values(used_at=datetime.now(UTC)))


async def mark_reset_token_used(session: AsyncSession, token: PasswordResetToken) -> None:
    token.used_at = datetime.now(UTC)
