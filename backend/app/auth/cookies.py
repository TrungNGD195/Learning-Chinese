from fastapi import Response

from app.core.config import Settings, get_settings

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
ACCESS_PATH = "/"
REFRESH_PATH = "/api/v1/auth"


def set_auth_cookies(response: Response, access_token: str, refresh_token: str, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    common = {"httponly": True, "secure": settings.cookie_secure, "samesite": settings.cookie_samesite, "domain": None}
    # Keep browser credentials for the browser session only. JWT and refresh-token
    # server-side expiration remain enforced independently by the auth services.
    response.set_cookie(ACCESS_COOKIE, access_token, path=ACCESS_PATH, **common)
    response.set_cookie(REFRESH_COOKIE, refresh_token, path=REFRESH_PATH, **common)


def clear_auth_cookies(response: Response, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    response.delete_cookie(ACCESS_COOKIE, path=ACCESS_PATH, secure=settings.cookie_secure, httponly=True, samesite=settings.cookie_samesite)
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH, secure=settings.cookie_secure, httponly=True, samesite=settings.cookie_samesite)
