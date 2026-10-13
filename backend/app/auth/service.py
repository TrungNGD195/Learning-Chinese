import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import repository
from app.auth.email import EmailService
from app.auth.security import (
    create_access_token,
    dummy_password_verify,
    generate_opaque_token,
    hash_password,
    normalize_email,
    token_hash,
    validate_password,
    verify_password,
)
from app.core.config import Settings, get_settings
from app.core.errors import ApplicationError
from app.database.models import PasswordResetToken, RefreshToken, User

logger = logging.getLogger("app.auth")


@dataclass(frozen=True)
class IssuedSession:
    user: User
    access_token: str
    refresh_token: str


def _registered_error() -> ApplicationError:
    return ApplicationError("EMAIL_ALREADY_REGISTERED", "Email is already registered", status_code=409)


def _invalid_refresh() -> ApplicationError:
    return ApplicationError("INVALID_REFRESH_TOKEN", "Refresh token is invalid", status_code=401)


def _invalid_reset() -> ApplicationError:
    return ApplicationError("INVALID_RESET_TOKEN", "Reset token is invalid", status_code=400)


async def _commit_auth_operation(session: AsyncSession) -> None:
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        logger.error("Authentication state change failed")
        raise ApplicationError("AUTH_OPERATION_FAILED", "Authentication operation failed", status_code=500) from None


async def register(
    session: AsyncSession,
    email: str,
    password: str,
    full_name: str,
    settings: Settings | None = None,
) -> IssuedSession:
    settings = settings or get_settings()
    normalized = normalize_email(email)
    validate_password(password)
    password_digest = hash_password(password)
    try:
        if await repository.get_user_by_email(session, normalized):
            raise _registered_error()
        user = User(
            email=normalized,
            password_hash=password_digest,
            full_name=full_name.strip(),
            role="LEARNER",
            is_active=True,
        )
        raw_refresh, refresh_digest = generate_opaque_token()
        await repository.add_user(session, user)
        await repository.add_refresh_token(
            session,
            RefreshToken(
                user_id=user.id,
                token_hash=refresh_digest,
                expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
            ),
        )
        await _commit_auth_operation(session)
        return IssuedSession(user, create_access_token(user.id, user.role, settings), raw_refresh)
    except IntegrityError as exc:
        await session.rollback()
        if getattr(getattr(exc.orig, "diag", None), "constraint_name", None) in {"uq_users_email", "users_email_key"}:
            raise _registered_error() from None
        raise ApplicationError("AUTH_OPERATION_FAILED", "Authentication operation failed", status_code=500) from None
    except Exception:
        if session.in_transaction():
            await session.rollback()
        raise


async def login(
    session: AsyncSession,
    email: str,
    password: str,
    settings: Settings | None = None,
) -> IssuedSession:
    settings = settings or get_settings()
    user = await repository.get_user_by_email(session, normalize_email(email))
    if user is None:
        dummy_password_verify(password)
        await session.rollback()
        raise ApplicationError("INVALID_CREDENTIALS", "Email or password is incorrect", status_code=401)

    verified_hash = user.password_hash
    verified = verify_password(verified_hash, password)
    user_id = user.id
    if not verified:
        logger.info("Authentication attempt failed")
        await session.rollback()
        raise ApplicationError("INVALID_CREDENTIALS", "Email or password is incorrect", status_code=401)
    if not user.is_active:
        await session.rollback()
        raise ApplicationError("ACCOUNT_DISABLED", "Account is disabled", status_code=403)

    # Password verification stays outside the write transaction. Re-read under
    # the User lock so a concurrent password change cannot issue a stale session.
    await session.rollback()
    current = await repository.lock_user_by_id(session, user_id)
    if current is None or current.password_hash != verified_hash:
        await session.rollback()
        raise ApplicationError("INVALID_CREDENTIALS", "Email or password is incorrect", status_code=401)
    if not current.is_active:
        await session.rollback()
        raise ApplicationError("ACCOUNT_DISABLED", "Account is disabled", status_code=403)

    raw_refresh, refresh_digest = generate_opaque_token()
    await repository.add_refresh_token(
        session,
        RefreshToken(
            user_id=current.id,
            token_hash=refresh_digest,
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
        ),
    )
    await _commit_auth_operation(session)
    return IssuedSession(current, create_access_token(current.id, current.role, settings), raw_refresh)


async def refresh(
    session: AsyncSession,
    raw_refresh: str | None,
    settings: Settings | None = None,
) -> IssuedSession:
    settings = settings or get_settings()
    if not raw_refresh:
        raise _invalid_refresh()

    hashed = token_hash(raw_refresh)
    user_id = await repository.get_refresh_user_id_by_hash(session, hashed)
    if user_id is None:
        await session.rollback()
        raise _invalid_refresh()
    await session.rollback()

    # Security-sensitive session writes use the common lock order: User, then
    # credential row. Revalidation happens only after both locks are held.
    user = await repository.lock_user_by_id(session, user_id)
    row = await repository.get_refresh_by_hash(session, hashed, for_update=True)
    now = datetime.now(UTC)
    if row is None or row.user_id != user_id or row.revoked_at is not None or row.expires_at <= now:
        await session.rollback()
        raise _invalid_refresh()
    if user is None or not user.is_active:
        await session.rollback()
        raise ApplicationError("ACCOUNT_DISABLED", "Account is disabled", status_code=403)

    raw_new, digest_new = generate_opaque_token()
    await repository.revoke_refresh_token(session, row)
    await repository.add_refresh_token(
        session,
        RefreshToken(
            user_id=user.id,
            token_hash=digest_new,
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        ),
    )
    await _commit_auth_operation(session)
    return IssuedSession(user, create_access_token(user.id, user.role, settings), raw_new)


async def logout(session: AsyncSession, raw_refresh: str | None) -> None:
    if raw_refresh:
        hashed = token_hash(raw_refresh)
        user_id = await repository.get_refresh_user_id_by_hash(session, hashed)
        if user_id is not None:
            await session.rollback()
            await repository.lock_user_by_id(session, user_id)
            row = await repository.get_refresh_by_hash(session, hashed, for_update=True)
            if row is not None and row.user_id == user_id and row.revoked_at is None:
                await repository.revoke_refresh_token(session, row)
    await _commit_auth_operation(session)


async def logout_all(session: AsyncSession, user_id: UUID) -> None:
    await repository.lock_user_by_id(session, user_id)
    await repository.revoke_all_refresh_tokens(session, user_id)
    await _commit_auth_operation(session)


async def change_password(
    session: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    validate_password(new_password)
    verified_hash = user.password_hash
    if not verify_password(verified_hash, current_password):
        logger.info("Password change verification failed")
        await session.rollback()
        raise ApplicationError("INVALID_CURRENT_PASSWORD", "Current password is incorrect", status_code=400)

    digest = hash_password(new_password)
    user_id = user.id
    await session.rollback()
    current = await repository.lock_user_by_id(session, user_id)
    if current is None or not current.is_active or current.password_hash != verified_hash:
        await session.rollback()
        raise ApplicationError("INVALID_CURRENT_PASSWORD", "Current password is incorrect", status_code=400)
    await repository.update_password_hash(session, current, digest)
    await repository.revoke_all_refresh_tokens(session, current.id)
    await _commit_auth_operation(session)


async def request_password_reset(
    session: AsyncSession,
    email: str,
    email_service: EmailService,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    normalized = normalize_email(email)
    user = await repository.get_user_by_email(session, normalized)
    if user is None:
        await session.rollback()
        return

    # Serializing on the authoritative User row makes each committed request
    # supersede every earlier currently useful reset credential.
    current = await repository.lock_user_by_id(session, user.id)
    if current is None or not current.is_active or current.email != normalized:
        await session.rollback()
        return
    raw, digest = generate_opaque_token()
    now = datetime.now(UTC)
    await repository.invalidate_reset_tokens(session, current.id)
    await repository.add_reset_token(
        session,
        PasswordResetToken(
            user_id=current.id,
            token_hash=digest,
            expires_at=now + timedelta(minutes=settings.password_reset_expire_minutes),
        ),
    )
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        logger.warning("Password reset request could not be persisted")
        return

    # Never hold a database transaction while an email adapter runs.
    try:
        await email_service.send_password_reset(normalized, raw)
    except Exception:
        logger.warning("Password reset email adapter failed")
        await session.rollback()
        token = await repository.get_reset_by_hash(session, digest)
        if token is not None and token.used_at is None:
            await repository.mark_reset_token_used(session, token)
        await session.commit()


async def confirm_password_reset(session: AsyncSession, raw_token: str, new_password: str) -> None:
    validate_password(new_password)
    digest = hash_password(new_password)
    hashed = token_hash(raw_token)
    user_id = await repository.get_reset_user_id_by_hash(session, hashed)
    if user_id is None:
        await session.rollback()
        raise _invalid_reset()

    # Reset confirmation follows the same User-before-token order as refresh,
    # reset issuance, logout-all, and password change.
    user = await repository.lock_user_by_id(session, user_id)
    row = await repository.get_reset_by_hash(session, hashed, for_update=True)
    now = datetime.now(UTC)
    if (
        user is None
        or row is None
        or row.user_id != user_id
        or not user.is_active
        or row.used_at is not None
        or row.expires_at <= now
    ):
        await session.rollback()
        raise _invalid_reset()

    await repository.update_password_hash(session, user, digest)
    await repository.mark_reset_token_used(session, row)
    await repository.invalidate_reset_tokens(session, user.id, except_id=row.id)
    await repository.revoke_all_refresh_tokens(session, user.id)
    await _commit_auth_operation(session)


async def create_admin(session: AsyncSession, email: str, password: str, full_name: str) -> User:
    normalized = normalize_email(email)
    full_name = full_name.strip()
    if not full_name:
        raise ApplicationError("INVALID_REQUEST", "Admin full name is required", status_code=422)
    validate_password(password)
    digest = hash_password(password)
    if await repository.get_user_by_email(session, normalized):
        await session.rollback()
        raise ApplicationError("ADMIN_ALREADY_EXISTS", "An account with that email already exists", status_code=409)
    user = User(email=normalized, password_hash=digest, full_name=full_name, role="ADMIN", is_active=True)
    await repository.add_user(session, user)
    try:
        await session.commit()
        return user
    except IntegrityError:
        await session.rollback()
        raise ApplicationError("ADMIN_ALREADY_EXISTS", "An account with that email already exists", status_code=409) from None
    except Exception:
        await session.rollback()
        raise ApplicationError("AUTH_OPERATION_FAILED", "Authentication operation failed", status_code=500) from None
