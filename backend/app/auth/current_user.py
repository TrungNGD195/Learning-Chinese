from uuid import UUID

from fastapi import Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import decode_access_token
from app.core.errors import ApplicationError
from app.database.models import User
from app.database.session import get_db_session
from app.auth import repository


async def get_current_user(access_token: str | None = Cookie(default=None), session: AsyncSession = Depends(get_db_session)) -> User:
    if not access_token:
        raise ApplicationError("AUTHENTICATION_REQUIRED", "Authentication is required", status_code=401)
    user_id, _token_role = decode_access_token(access_token)
    user = await repository.get_user_by_id(session, user_id)
    if user is None:
        raise ApplicationError("AUTHENTICATION_REQUIRED", "Authentication is required", status_code=401)
    if not user.is_active:
        raise ApplicationError("ACCOUNT_DISABLED", "Account is disabled", status_code=403)
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "ADMIN":
        raise ApplicationError("ADMIN_REQUIRED", "Admin access is required", status_code=403)
    return current_user
