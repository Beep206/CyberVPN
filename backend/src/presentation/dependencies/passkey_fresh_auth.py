"""Passkey fresh-auth request guard helpers."""

from __future__ import annotations

import logging

import redis.asyncio as redis
from fastapi import HTTPException, Request, status

from src.infrastructure.cache.passkey_fresh_auth import PasskeyFreshAuthGrantError, PasskeyFreshAuthGrantStore

FRESH_AUTH_GRANT_ID_HEADER = "X-Fresh-Auth-Grant-Id"
FRESH_AUTH_REQUIRED_DETAIL = "Fresh passkey reauthentication required"

logger = logging.getLogger(__name__)


async def enforce_passkey_fresh_auth(
    *,
    request: Request,
    redis_client: redis.Redis,
    principal_subject: str,
    principal_class: str,
    auth_realm_id: str,
    realm_key: str,
    action: str,
) -> None:
    grant_id = request.headers.get(FRESH_AUTH_GRANT_ID_HEADER)
    if grant_id is None or not grant_id.strip():
        raise _fresh_auth_required()

    try:
        await PasskeyFreshAuthGrantStore(redis_client).consume(
            grant_id,
            expected_principal_subject=principal_subject,
            expected_principal_class=principal_class,
            expected_auth_realm_id=auth_realm_id,
            expected_realm_key=realm_key,
            expected_action=action,
        )
    except PasskeyFreshAuthGrantError as exc:
        logger.info("Passkey fresh-auth grant rejected", extra={"reason": str(exc)})
        raise _fresh_auth_required() from exc


def _fresh_auth_required() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=FRESH_AUTH_REQUIRED_DETAIL)
