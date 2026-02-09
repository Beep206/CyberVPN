"""Rate limiting dependencies for Telegram auth endpoints.

Per-IP rate limiting:
- POST /auth/telegram/miniapp: 10 req/min per IP
- POST /auth/telegram/bot-link: 10 req/min per IP
- POST /auth/telegram/generate-login-link: 5 req/min per user (admin-only)
"""

import logging
import time
from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends, HTTPException, Request, status

from src.config.settings import settings
from src.infrastructure.cache.redis_client import get_redis_pool

logger = logging.getLogger("cybervpn")

TELEGRAM_AUTH_LIMIT = 10  # per minute per IP
GENERATE_LINK_LIMIT = 5  # per minute per user
WINDOW_SECONDS = 60


def _get_client_ip(request: Request) -> str:
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


async def _check_rate_limit(key: str, limit: int) -> bool:
    """Check rate limit using Redis sorted set sliding window.

    Returns True if allowed, False if rate limited.
    On Redis error, fail-open (allow the request).
    """
    pool = None
    client = None
    try:
        pool = get_redis_pool()
        client = redis.Redis(connection_pool=pool)
        now = time.time()

        pipe = client.pipeline()
        pipe.zremrangebyscore(key, 0, now - WINDOW_SECONDS)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, WINDOW_SECONDS)
        results = await pipe.execute()

        return results[2] <= limit
    except Exception as exc:
        logger.warning("Telegram rate limit check failed: %s", exc)
        return True  # Fail-open for these endpoints
    finally:
        if client is not None:
            await client.aclose()


async def check_telegram_miniapp_rate_limit(request: Request) -> None:
    """Rate limit POST /auth/telegram/miniapp: 10/min per IP."""
    client_ip = _get_client_ip(request)
    key = f"cybervpn:tg_auth:miniapp:ip:{client_ip}"

    if not await _check_rate_limit(key, TELEGRAM_AUTH_LIMIT):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(WINDOW_SECONDS)},
        )


async def check_telegram_bot_link_rate_limit(request: Request) -> None:
    """Rate limit POST /auth/telegram/bot-link: 10/min per IP."""
    client_ip = _get_client_ip(request)
    key = f"cybervpn:tg_auth:bot_link:ip:{client_ip}"

    if not await _check_rate_limit(key, TELEGRAM_AUTH_LIMIT):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(WINDOW_SECONDS)},
        )


async def check_generate_link_rate_limit(request: Request) -> None:
    """Rate limit POST /auth/telegram/generate-login-link: 5/min per IP."""
    client_ip = _get_client_ip(request)
    key = f"cybervpn:tg_auth:gen_link:ip:{client_ip}"

    if not await _check_rate_limit(key, GENERATE_LINK_LIMIT):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(WINDOW_SECONDS)},
        )


# Type aliases for FastAPI Depends
TelegramMiniAppRateLimit = Annotated[None, Depends(check_telegram_miniapp_rate_limit)]
TelegramBotLinkRateLimit = Annotated[None, Depends(check_telegram_bot_link_rate_limit)]
GenerateLinkRateLimit = Annotated[None, Depends(check_generate_link_rate_limit)]
