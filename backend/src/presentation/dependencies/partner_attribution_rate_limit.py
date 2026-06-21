"""Redis-backed rate limits for public partner attribution routes."""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from uuid import uuid4

import redis.asyncio as redis
from fastapi import HTTPException, Request, status

from src.application.use_cases.partner_attribution.utils import PARTNER_ATTRIBUTION_BROWSER_ACTIVE_SESSION_LIMIT
from src.config.settings import settings
from src.infrastructure.monitoring.partner_runtime_metrics import partner_attribution_rate_limited_total
from src.presentation.api.v1.partner_attribution.schemas import PartnerAttributionCaptureRequest
from src.presentation.dependencies.client_ip import resolve_client_ip

logger = logging.getLogger(__name__)

WINDOW_SECONDS = 10 * 60
CAPTURE_IP_LIMIT = 30
CAPTURE_SLUG_LIMIT = 100
TRANSFER_IP_LIMIT = 10
CLAIM_USER_LIMIT = 10
BROWSER_ACTIVE_SESSION_LIMIT = PARTNER_ATTRIBUTION_BROWSER_ACTIVE_SESSION_LIMIT


@dataclass(frozen=True)
class _RateLimitRule:
    scope: str
    key: str
    limit: int
    window_seconds: int = WINDOW_SECONDS
    member: str | None = None


async def check_partner_attribution_capture_rate_limit(
    *,
    request: Request,
    payload: PartnerAttributionCaptureRequest,
    redis_client: redis.Redis,
) -> None:
    client_ip = resolve_client_ip(request).ip
    token_hash = _hash_key_part(payload.public_token)
    rules = [
        _RateLimitRule(
            scope="capture_ip",
            key=f"cybervpn:partner_attribution:rate:capture:ip:{_hash_key_part(client_ip)}",
            limit=CAPTURE_IP_LIMIT,
        ),
        _RateLimitRule(
            scope="capture_slug",
            key=f"cybervpn:partner_attribution:rate:capture:slug:{token_hash}",
            limit=CAPTURE_SLUG_LIMIT,
        ),
    ]
    await _check_rules(redis_client, rules)


async def check_partner_attribution_transfer_rate_limit(
    *,
    request: Request,
    redis_client: redis.Redis,
) -> None:
    client_ip = resolve_client_ip(request).ip
    await _check_rules(
        redis_client,
        [
            _RateLimitRule(
                scope="transfer_ip",
                key=f"cybervpn:partner_attribution:rate:transfer:ip:{_hash_key_part(client_ip)}",
                limit=TRANSFER_IP_LIMIT,
            )
        ],
    )


async def check_partner_attribution_claim_rate_limit(
    *,
    user_id: object,
    redis_client: redis.Redis,
) -> None:
    await _check_rules(
        redis_client,
        [
            _RateLimitRule(
                scope="claim_user",
                key=f"cybervpn:partner_attribution:rate:claim:user:{_hash_key_part(str(user_id))}",
                limit=CLAIM_USER_LIMIT,
            )
        ],
    )


async def _check_rules(redis_client: redis.Redis, rules: list[_RateLimitRule]) -> None:
    now = time.time()
    try:
        for rule in rules:
            count = await _record_and_count(redis_client, rule, now)
            if count > rule.limit:
                _observe_limited(rule.scope)
                logger.warning(
                    "partner_attribution_rate_limited",
                    extra={"scope": rule.scope, "limit": rule.limit, "count": count},
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "code": "PARTNER_ATTRIBUTION_RATE_LIMITED",
                        "message": "Too many partner attribution attempts. Please try again later.",
                        "scope": rule.scope,
                    },
                    headers={"Retry-After": str(rule.window_seconds)},
                )
    except HTTPException:
        raise
    except redis.RedisError as exc:
        await _handle_redis_unavailable(exc)


async def _record_and_count(redis_client: redis.Redis, rule: _RateLimitRule, now: float) -> int:
    member = rule.member or f"{now:.9f}:{uuid4().hex}"
    async with redis_client.pipeline(transaction=True) as pipe:
        pipe.zremrangebyscore(rule.key, 0, now - rule.window_seconds)
        pipe.zadd(rule.key, {member: now})
        pipe.zcard(rule.key)
        pipe.expire(rule.key, rule.window_seconds)
        results = await pipe.execute()
    return int(results[2])


async def _handle_redis_unavailable(exc: Exception) -> None:
    fail_open = bool(getattr(settings, "rate_limit_fail_open", False)) or settings.environment != "production"
    logger.error(
        "partner_attribution_rate_limit_redis_unavailable",
        extra={"fail_open": fail_open, "error": str(exc)},
    )
    if fail_open:
        return
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "PARTNER_ATTRIBUTION_RATE_LIMIT_UNAVAILABLE",
            "message": "Partner attribution is temporarily unavailable. Please try again later.",
        },
        headers={"Retry-After": "30"},
    ) from exc


def _observe_limited(scope: str) -> None:
    partner_attribution_rate_limited_total.labels(scope=scope).inc()


def _hash_key_part(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
