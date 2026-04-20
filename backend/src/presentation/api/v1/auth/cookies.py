"""HTTP-only cookie helpers for auth token delivery (SEC-01)."""

from fastapi import Response

from src.config.settings import settings

LEGACY_ACCESS_COOKIE = "access_token"
LEGACY_REFRESH_COOKIE = "refresh_token"
ACCESS_COOKIE_PATH = "/api"
REFRESH_COOKIE_PATH = "/api"
LEGACY_REFRESH_COOKIE_PATH = "/api/v1/auth/refresh"


def resolve_access_cookie_name(cookie_namespace: str | None = None) -> str:
    if not cookie_namespace or cookie_namespace == "admin":
        return LEGACY_ACCESS_COOKIE
    return f"{cookie_namespace}_access_token"


def resolve_refresh_cookie_name(cookie_namespace: str | None = None) -> str:
    if not cookie_namespace or cookie_namespace == "admin":
        return LEGACY_REFRESH_COOKIE
    return f"{cookie_namespace}_refresh_token"


def get_access_token_cookie(cookie_source, cookie_namespace: str | None = None) -> str | None:
    return cookie_source.get(resolve_access_cookie_name(cookie_namespace))


def get_refresh_token_cookie(cookie_source, cookie_namespace: str | None = None) -> str | None:
    return cookie_source.get(resolve_refresh_cookie_name(cookie_namespace))


def _clear_cookie(
    response: Response,
    *,
    key: str,
    path: str,
    domain: str | None,
    secure: bool,
) -> None:
    response.set_cookie(
        key=key,
        value="",
        httponly=True,
        secure=secure,
        samesite="lax",
        path=path,
        max_age=0,
        domain=domain,
    )


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    *,
    cookie_namespace: str | None = None,
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

    access_cookie = resolve_access_cookie_name(cookie_namespace)
    refresh_cookie = resolve_refresh_cookie_name(cookie_namespace)

    response.set_cookie(
        key=access_cookie,
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        path=ACCESS_COOKIE_PATH,
        max_age=access_max_age,
        domain=domain,
    )
    response.set_cookie(
        key=refresh_cookie,
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
        max_age=refresh_max_age,
        domain=domain,
    )
    _clear_cookie(
        response,
        key=LEGACY_REFRESH_COOKIE,
        path=LEGACY_REFRESH_COOKIE_PATH,
        domain=domain,
        secure=secure,
    )

    if cookie_namespace and cookie_namespace != "admin":
        _clear_cookie(
            response,
            key=LEGACY_ACCESS_COOKIE,
            path=ACCESS_COOKIE_PATH,
            domain=domain,
            secure=secure,
        )
        _clear_cookie(
            response,
            key=LEGACY_REFRESH_COOKIE,
            path=REFRESH_COOKIE_PATH,
            domain=domain,
            secure=secure,
        )


def clear_auth_cookies(response: Response, *, cookie_namespace: str | None = None) -> None:
    """Clear auth cookies by setting max_age=0."""
    domain = settings.cookie_domain or None
    secure = settings.cookie_secure
    access_cookie = resolve_access_cookie_name(cookie_namespace)
    refresh_cookie = resolve_refresh_cookie_name(cookie_namespace)

    _clear_cookie(
        response,
        key=access_cookie,
        path=ACCESS_COOKIE_PATH,
        domain=domain,
        secure=secure,
    )
    _clear_cookie(
        response,
        key=refresh_cookie,
        path=REFRESH_COOKIE_PATH,
        domain=domain,
        secure=secure,
    )
    _clear_cookie(
        response,
        key=LEGACY_REFRESH_COOKIE,
        path=LEGACY_REFRESH_COOKIE_PATH,
        domain=domain,
        secure=secure,
    )

    if cookie_namespace and cookie_namespace != "admin":
        _clear_cookie(
            response,
            key=LEGACY_ACCESS_COOKIE,
            path=ACCESS_COOKIE_PATH,
            domain=domain,
            secure=secure,
        )
        _clear_cookie(
            response,
            key=LEGACY_REFRESH_COOKIE,
            path=REFRESH_COOKIE_PATH,
            domain=domain,
            secure=secure,
        )
