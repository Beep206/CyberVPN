"""CyberVPN Telegram Bot — Bot instance and Dispatcher factory.

Provides factory functions for creating the aiogram Bot and Dispatcher
with Redis FSM storage, middleware stack, and router registration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

if TYPE_CHECKING:
    from src.config import BotSettings


def create_bot(settings: BotSettings) -> Bot:
    """Create and configure the aiogram Bot instance.

    Args:
        settings: Application settings containing bot token and configuration.

    Returns:
        Configured Bot instance with HTML parse mode and link preview disabled.
    """
    return Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            link_preview_is_disabled=True,
        ),
    )


def create_redis_storage(settings: BotSettings) -> RedisStorage:
    """Create Redis-backed FSM storage for the Dispatcher.

    Args:
        settings: Application settings with Redis connection details.

    Returns:
        RedisStorage connected to the configured Redis instance.
    """
    redis = Redis.from_url(
        settings.redis.dsn,
        password=(
            settings.redis.password.get_secret_value()
            if settings.redis.password
            else None
        ),
        decode_responses=True,
    )
    return RedisStorage(
        redis=redis,
        key_builder_prefix=settings.redis.key_prefix,
    )


def create_dispatcher(settings: BotSettings) -> Dispatcher:
    """Create and configure the Dispatcher with storage, middleware, and routers.

    The dispatcher is the root router that orchestrates all update processing.

    Middleware is registered in a specific order to ensure correct execution:
    1. Logging — captures every incoming update
    2. Metrics — collects Prometheus counters
    3. Throttling — rate-limits users before expensive operations
    4. Auth — identifies/registers user, injects data['user']
    5. Access Control — checks maintenance, rules, channel subscription
    6. i18n — sets locale for downstream handlers

    Routers are included after middleware registration:
    - Admin router (with IsAdmin filter)
    - User-facing routers (start, menu, subscription, payment, etc.)

    Args:
        settings: Application settings for storage and middleware configuration.

    Returns:
        Fully configured Dispatcher ready for polling or webhook startup.
    """
    storage = create_redis_storage(settings)
    dp = Dispatcher(storage=storage)

    # Store settings in dispatcher context for access in handlers/middleware
    dp["settings"] = settings

    # Register middleware stack
    from src.middlewares import register_middlewares

    register_middlewares(dp, settings)

    # Register all handler routers
    from src.handlers import register_routers

    register_routers(dp)

    return dp
