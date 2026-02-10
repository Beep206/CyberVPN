"""HTTP-only cookie helpers for auth token delivery (SEC-01)."""

from fastapi import Response

from src.config.settings import settings

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    access_max_age: int | None = None,
    refresh_max_age: int | None = None,
) -> None:
    """Attach httpOnly auth cookies to the response."""
    if access_max_age is None:
        access_max_age = settings.access_token_expire_minutes * 60
    if refresh_max_age is None:
        refresh_max_age = settings.refresh_token_expire_days * 86400

    domain = settings.cookie_domain or None
    secure = settings.cookie_secure

    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/api",
        max_age=access_max_age,
        domain=domain,
    )
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/api/v1/auth/refresh",
        max_age=refresh_max_age,
        domain=domain,
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear auth cookies by setting max_age=0."""
    domain = settings.cookie_domain or None
    secure = settings.cookie_secure

    response.set_cookie(
        key=ACCESS_COOKIE,
        value="",
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/api",
        max_age=0,
        domain=domain,
    )
    response.set_cookie(
        key=REFRESH_COOKIE,
        value="",
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/api/v1/auth/refresh",
        max_age=0,
        domain=domain,
    )
