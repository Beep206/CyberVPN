from __future__ import annotations

import hashlib
import hmac
import secrets
import time

from fastapi import Request, Response

from src.config.settings import settings

PRIVATE_CATALOG_ANONYMOUS_SESSION_COOKIE = "__Host-cvpn_private_catalog_session"
PRIVATE_CATALOG_ANONYMOUS_SESSION_MAX_AGE_SECONDS = 15 * 60
_FORMAT_VERSION = "v1"


def ensure_private_catalog_anonymous_session(request: Request, response: Response) -> str:
    token = request.cookies.get(PRIVATE_CATALOG_ANONYMOUS_SESSION_COOKIE)
    subject = private_catalog_anonymous_session_subject(token)
    if subject is not None:
        return subject

    raw_session_id = secrets.token_urlsafe(32)
    issued_at = int(time.time())
    token = _encode_token(raw_session_id, issued_at)
    response.set_cookie(
        key=PRIVATE_CATALOG_ANONYMOUS_SESSION_COOKIE,
        value=token,
        max_age=PRIVATE_CATALOG_ANONYMOUS_SESSION_MAX_AGE_SECONDS,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return _subject_ref(raw_session_id)


def private_catalog_anonymous_session_subject(token: str | None) -> str | None:
    if not token:
        return None
    parts = token.split(".")
    if len(parts) != 4:
        return None
    version, raw_session_id, issued_at_raw, signature = parts
    if version != _FORMAT_VERSION or not raw_session_id:
        return None
    try:
        issued_at = int(issued_at_raw)
    except ValueError:
        return None
    now = int(time.time())
    if issued_at > now + 60:
        return None
    if now - issued_at > PRIVATE_CATALOG_ANONYMOUS_SESSION_MAX_AGE_SECONDS:
        return None
    expected = _signature(raw_session_id, issued_at)
    if not hmac.compare_digest(signature, expected):
        return None
    return _subject_ref(raw_session_id)


def _encode_token(raw_session_id: str, issued_at: int) -> str:
    return f"{_FORMAT_VERSION}.{raw_session_id}.{issued_at}.{_signature(raw_session_id, issued_at)}"


def _signature(raw_session_id: str, issued_at: int) -> str:
    return hmac.new(
        _secret(),
        f"{_FORMAT_VERSION}.{raw_session_id}.{issued_at}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _subject_ref(raw_session_id: str) -> str:
    return hmac.new(
        _secret(),
        f"private-catalog-anonymous-session:{raw_session_id}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _secret() -> bytes:
    configured = settings.growth_code_hash_secret.get_secret_value().strip()
    secret = configured or settings.jwt_secret.get_secret_value().strip()
    return secret.encode("utf-8")
