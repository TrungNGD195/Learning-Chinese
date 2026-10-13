import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import Settings, get_settings
from app.core.errors import ApplicationError

password_hasher = PasswordHasher()
_DUMMY_HASH = password_hasher.hash("step35-dummy-credential-never-used")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_password(password: str) -> None:
    if not 8 <= len(password) <= 128:
        raise ApplicationError("INVALID_PASSWORD", "Password must contain 8 to 128 characters", status_code=422)


def hash_password(password: str) -> str:
    validate_password(password)
    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def dummy_password_verify(password: str) -> None:
    verify_password(_DUMMY_HASH, password)


def create_access_token(user_id: UUID, role: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    now = datetime.now(UTC)
    return jwt.encode(
        {"sub": str(user_id), "role": role, "iat": now, "exp": now + timedelta(minutes=settings.access_token_expire_minutes)},
        settings.secret_key.get_secret_value(), algorithm="HS256",
    )


def decode_access_token(token: str, settings: Settings | None = None) -> tuple[UUID, str]:
    settings = settings or get_settings()
    try:
        claims = jwt.decode(token, settings.secret_key.get_secret_value(), algorithms=["HS256"], options={"require": ["sub", "role", "iat", "exp"]})
        return UUID(claims["sub"]), claims["role"]
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise ApplicationError("AUTHENTICATION_REQUIRED", "Authentication is required", status_code=401) from None


def generate_opaque_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, hashlib.sha256(raw.encode("utf-8")).hexdigest()


def token_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
