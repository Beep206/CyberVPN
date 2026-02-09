"""Redis helpers for one-time Telegram bot login link tokens."""

import json
import logging
import secrets
import time

import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Key prefix and TTL
_KEY_PREFIX = "tg_login_link:"
_TOKEN_TTL_SECONDS = 300  # 5 minutes


async def generate_bot_link_token(
    redis_client: redis.Redis,
    telegram_id: int,
    ip: str = "",
) -> str:
    """Generate a one-time login token for a Telegram user.

    Args:
        redis_client: Async Redis client.
        telegram_id: Telegram user ID.
        ip: Originating IP address (for audit).

    Returns:
        The generated token string (256-bit entropy).
    """
    token = secrets.token_urlsafe(32)
    key = f"{_KEY_PREFIX}{token}"
    value = json.dumps({
        "telegram_id": telegram_id,
        "created_at": int(time.time()),
        "ip": ip,
    })

    await redis_client.set(key, value, ex=_TOKEN_TTL_SECONDS)

    logger.info(
        "Generated bot link token",
        extra={"telegram_id": telegram_id, "ttl": _TOKEN_TTL_SECONDS},
    )
    return token


async def consume_bot_link_token(
    redis_client: redis.Redis,
    token: str,
) -> int | None:
    """Atomically retrieve and delete a one-time login token.

    Uses GETDEL for atomic one-time-use semantics.

    Args:
        redis_client: Async Redis client.
        token: The token string to consume.

    Returns:
        telegram_id if token is valid and not expired, None otherwise.
    """
    key = f"{_KEY_PREFIX}{token}"

    # GETDEL: atomic get + delete (Redis 6.2+)
    raw = await redis_client.getdel(key)
    if raw is None:
        return None

    try:
        data = json.loads(raw)
        telegram_id = data.get("telegram_id")
        if telegram_id is not None:
            return int(telegram_id)
    except (json.JSONDecodeError, ValueError, TypeError):
        logger.warning("Invalid bot link token data", extra={"token_prefix": token[:8]})

    return None
