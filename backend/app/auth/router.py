from fastapi import APIRouter, Cookie, Depends, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service
from app.auth.cookies import clear_auth_cookies, set_auth_cookies
from app.auth.current_user import get_current_user
from app.auth.email import EmailService, get_email_service
from app.auth.schemas import (ChangePasswordRequest, LoginRequest, PasswordResetConfirmRequest,
    PasswordResetRequest, RegisterRequest, UserProfileResponse)
from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.database.models import User
from app.database.session import get_db_session

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201, response_model=UserProfileResponse)
async def register(payload: RegisterRequest, response: Response, session: AsyncSession = Depends(get_db_session)):
    issued = await service.register(session, payload.email, payload.password, payload.full_name)
    set_auth_cookies(response, issued.access_token, issued.refresh_token)
    return issued.user


@router.post("/login", response_model=UserProfileResponse)
async def login(payload: LoginRequest, response: Response, session: AsyncSession = Depends(get_db_session)):
    issued = await service.login(session, payload.email, payload.password)
    set_auth_cookies(response, issued.access_token, issued.refresh_token)
    return issued.user


@router.get("/me", response_model=UserProfileResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/refresh", status_code=204)
async def refresh(response: Response, refresh_token: str | None = Cookie(default=None), session: AsyncSession = Depends(get_db_session)):
    try:
        issued = await service.refresh(session, refresh_token)
    except ApplicationError as exc:
        if exc.code in {"INVALID_REFRESH_TOKEN", "ACCOUNT_DISABLED"}:
            error_response = JSONResponse(status_code=exc.status_code, content={"error": {
                "code": exc.code, "message": exc.message, "details": exc.details,
            }})
            clear_auth_cookies(error_response)
            return error_response
        raise
    set_auth_cookies(response, issued.access_token, issued.refresh_token)
    response.status_code = 204
    return response


@router.post("/logout", status_code=204)
async def logout(response: Response, refresh_token: str | None = Cookie(default=None), session: AsyncSession = Depends(get_db_session)):
    await service.logout(session, refresh_token)
    clear_auth_cookies(response)
    response.status_code = 204
    return response


@router.post("/logout-all", status_code=204)
async def logout_all(response: Response, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)):
    await service.logout_all(session, current_user.id)
    clear_auth_cookies(response)
    response.status_code = 204
    return response


@router.post("/change-password", status_code=204)
async def change_password(payload: ChangePasswordRequest, response: Response, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)):
    await service.change_password(session, current_user, payload.current_password, payload.new_password)
    clear_auth_cookies(response)
    response.status_code = 204
    return response


@router.post("/password-reset/request", status_code=202)
async def password_reset_request(payload: PasswordResetRequest, session: AsyncSession = Depends(get_db_session), email_service: EmailService = Depends(get_email_service)):
    await service.request_password_reset(session, payload.email, email_service)
    return Response(status_code=202)


@router.post("/password-reset/confirm", status_code=204)
async def password_reset_confirm(payload: PasswordResetConfirmRequest, response: Response, session: AsyncSession = Depends(get_db_session)):
    await service.confirm_password_reset(session, payload.token, payload.new_password)
    clear_auth_cookies(response)
    response.status_code = 204
    return response
