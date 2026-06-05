"""HTTP-only cookie helpers for auth token delivery (SEC-01)."""

from urllib.parse import urlsplit

from fastapi import Request, Response

from src.config.settings import settings

LEGACY_ACCESS_COOKIE = "access_token"
LEGACY_REFRESH_COOKIE = "refresh_token"
ACCESS_COOKIE_PATH = "/api"
REFRESH_COOKIE_PATH = "/api"
LEGACY_REFRESH_COOKIE_PATH = "/api/v1/auth/refresh"
LOCAL_HTTP_COOKIE_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "test", "testserver"})
INTERNAL_API_COOKIE_HOSTS = frozenset({"cybervpn-backend", "localhost", "127.0.0.1", "::1", "test", "testserver"})
CUSTOMER_LOCAL_HTTP_COOKIE_PORTS = frozenset({3000, 13000})


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


def _request_host(request: Request) -> str:
    return (request.url.hostname or "").lower()


def _request_scheme(request: Request) -> str:
    return request.url.scheme.lower()


def _origin_is_customer_local_http(origin: str | None) -> bool:
    if not origin:
        return False

    candidate = origin.strip()
    if not candidate:
        return False

    try:
        parsed = urlsplit(candidate)
        if parsed.scheme.lower() != "http" or candidate != f"{parsed.scheme}://{parsed.netloc}":
            return False
        if parsed.username is not None or parsed.password is not None:
            return False
        host = (parsed.hostname or "").lower()
        port = parsed.port
    except ValueError:
        return False
    return host in LOCAL_HTTP_COOKIE_HOSTS and port in CUSTOMER_LOCAL_HTTP_COOKIE_PORTS


def _uses_customer_local_http_cookie_policy(request: Request | None, cookie_namespace: str | None) -> bool:
    if request is None or cookie_namespace != "customer":
        return False
    if _request_scheme(request) != "http":
        return False
    if not _origin_is_customer_local_http(request.headers.get("origin")):
        return False

    return _request_host(request) in INTERNAL_API_COOKIE_HOSTS


def _resolve_cookie_domain(request: Request | None, cookie_namespace: str | None) -> str | None:
    if _uses_customer_local_http_cookie_policy(request, cookie_namespace):
        return None
    return settings.cookie_domain or None


def _resolve_cookie_secure(request: Request | None, cookie_namespace: str | None) -> bool:
    if _uses_customer_local_http_cookie_policy(request, cookie_namespace):
        return False

    if settings.environment.lower() == "production":
        return True

    secure = settings.cookie_secure
    if not secure or request is None:
        return secure

    return not (_request_scheme(request) == "http" and _request_host(request) in LOCAL_HTTP_COOKIE_HOSTS)


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
    request: Request | None = None,
    cookie_namespace: str | None = None,
    access_max_age: int | None = None,
    refresh_max_age: int | None = None,
) -> None:
    """Attach httpOnly auth cookies to the response."""
    if access_max_age is None:
        access_max_age = settings.access_token_expire_minutes * 60
    if refresh_max_age is None:
        refresh_max_age = settings.refresh_token_expire_days * 86400

    access_cookie = resolve_access_cookie_name(cookie_namespace)
    refresh_cookie = resolve_refresh_cookie_name(cookie_namespace)
    domain = _resolve_cookie_domain(request, cookie_namespace)
    secure = _resolve_cookie_secure(request, cookie_namespace)

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


def set_pending_2fa_cookie(
    response: Response,
    pending_token: str,
    *,
    request: Request | None = None,
    cookie_namespace: str | None = None,
    max_age: int | None = None,
) -> None:
    """Attach the pending 2FA token as an httpOnly web access cookie."""
    if max_age is None:
        max_age = settings.access_token_expire_minutes * 60

    access_cookie = resolve_access_cookie_name(cookie_namespace)
    refresh_cookie = resolve_refresh_cookie_name(cookie_namespace)
    domain = _resolve_cookie_domain(request, cookie_namespace)
    secure = _resolve_cookie_secure(request, cookie_namespace)

    response.set_cookie(
        key=access_cookie,
        value=pending_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        path=ACCESS_COOKIE_PATH,
        max_age=max_age,
        domain=domain,
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


def clear_auth_cookies(
    response: Response,
    *,
    request: Request | None = None,
    cookie_namespace: str | None = None,
) -> None:
    """Clear auth cookies by setting max_age=0."""
    access_cookie = resolve_access_cookie_name(cookie_namespace)
    refresh_cookie = resolve_refresh_cookie_name(cookie_namespace)
    domain = _resolve_cookie_domain(request, cookie_namespace)
    secure = _resolve_cookie_secure(request, cookie_namespace)

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
