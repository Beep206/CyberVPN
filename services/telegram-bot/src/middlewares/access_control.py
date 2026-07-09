"""CyberVPN Telegram Bot — Access control middleware.

Enforces bot access conditions:
- Maintenance mode (block non-admins)
- Rules acceptance requirement
- Channel subscription requirement

Uses data['user'] from AuthMiddleware and data['settings'] from dispatcher.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message, TelegramObject

from src.services.api_client import APIError, CyberVPNAPIClient

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from src.config import BotSettings
    from src.services.cache_service import CacheService

logger = structlog.get_logger(__name__)


class AccessControlMiddleware(BaseMiddleware):
    """Access control middleware for bot conditions.

    Checks and enforces:
    - Maintenance mode (only admins allowed)
    - Rules acceptance requirement
    - Channel subscription requirement

    Requires:
    - data['user'] from AuthMiddleware
    - data['settings'] from dispatcher startup (bot config from API)

    Args:
        bot_settings: Bot configuration for admin checks.
        bot: Bot instance for checking channel membership.
    """

    def __init__(
        self,
        bot_settings: BotSettings,
        bot: Bot,
        api_client: CyberVPNAPIClient | None = None,
        cache: CacheService | None = None,
    ) -> None:
        self._bot_settings = bot_settings
        self._bot = bot
        self._api = api_client
        self._cache = cache

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Apply access control checks.

        Args:
            handler: Next handler in the chain.
            event: Telegram event (Message or CallbackQuery).
            data: Handler data dict.

        Returns:
            Result from the next handler, or None if access denied.
        """
        user_data = data.get("user")
        if user_data is None:
            logger.warning("access_control_no_user_data")
            return await handler(event, data)

        telegram_id = user_data.get("telegram_id")
        is_admin = self._bot_settings.is_admin(telegram_id)

        # Load bot access settings from cache/API
        settings_override = data.get("settings")
        if isinstance(settings_override, dict):
            bot_config = settings_override
        else:
            bot_config = await self._get_access_settings()
        access_mode = bot_config.get("access_mode") or bot_config.get("mode") or "open"
        rules_url = bot_config.get("rules_url") or bot_config.get("rules_link")
        channel_id = bot_config.get("channel_id") or bot_config.get("channel")

        # Check 1: Maintenance mode
        if access_mode == "maintenance" and not is_admin:
            logger.info(
                "access_denied_maintenance",
                telegram_id=telegram_id,
            )
            await self._send_maintenance_message(event)
            return None

        # Check 2: Rules acceptance (if enabled and not admin)
        if rules_url and not is_admin:
            has_accepted_rules = user_data.get("has_accepted_rules", False)
            if not has_accepted_rules:
                logger.info(
                    "access_denied_rules_not_accepted",
                    telegram_id=telegram_id,
                )
                await self._send_rules_required_message(event, rules_url)
                return None

        # Check 3: Channel subscription (if enabled and not admin)
        if channel_id and not is_admin:
            is_subscribed = await self._check_channel_subscription(
                telegram_id=telegram_id,
                channel_id=channel_id,
            )
            if not is_subscribed:
                logger.info(
                    "access_denied_not_subscribed",
                    telegram_id=telegram_id,
                    channel_id=channel_id,
                )
                await self._send_subscription_required_message(event, channel_id)
                return None

        # All checks passed
        return await handler(event, data)

    async def _get_access_settings(self) -> dict[str, Any]:
        if self._cache is not None:
            cached = await self._cache.get_bot_config()
            if isinstance(cached, dict) and cached:
                return cached

        if self._api is None:
            return {}

        try:
            settings = await self._api.get_access_settings()
        except APIError as exc:
            logger.error("access_settings_fetch_failed", error=str(exc))
            return {}

        if isinstance(settings, dict):
            if self._cache is not None:
                await self._cache.set_bot_config(settings)
            return settings

        return {}

    async def _check_channel_subscription(
        self,
        telegram_id: int,
        channel_id: str,
    ) -> bool:
        """Check if user is subscribed to required channel.

        Args:
            telegram_id: User's Telegram ID.
            channel_id: Channel username or ID (@channel or -100xxx).

        Returns:
            True if user is a member, False otherwise.
        """
        try:
            member = await self._bot.get_chat_member(
                chat_id=channel_id,
                user_id=telegram_id,
            )
            # Member status: creator, administrator, member, restricted, left, kicked
            return member.status in ("creator", "administrator", "member", "restricted")

        except Exception as exc:
            logger.error(
                "channel_subscription_check_failed",
                telegram_id=telegram_id,
                channel_id=channel_id,
                error=str(exc),
            )
            # Fail open: allow access if check fails
            return True

    @staticmethod
    async def _send_auth_required_message(event: TelegramObject) -> None:
        text = "⚠️ <b>Сервис временно недоступен</b>\n\nПопробуйте позже."  # noqa: RUF001

        if isinstance(event, Message):
            await event.answer(text, parse_mode="HTML")
        elif isinstance(event, CallbackQuery):
            await event.answer("Сервис временно недоступен", show_alert=True)

    @staticmethod
    async def _send_maintenance_message(event: TelegramObject) -> None:
        """Send maintenance mode message to user.

        Args:
            event: Telegram event to respond to.
        """
        text = "🔧 <b>Технические работы</b>\n\nБот временно недоступен. Попробуйте позже."  # noqa: RUF001

        if isinstance(event, Message):
            await event.answer(text, parse_mode="HTML")
        elif isinstance(event, CallbackQuery):
            await event.answer(
                "Бот на техническом обслуживании",
                show_alert=True,
            )

    @staticmethod
    async def _send_rules_required_message(
        event: TelegramObject,
        rules_url: str,
    ) -> None:
        """Send rules acceptance required message.

        Args:
            event: Telegram event to respond to.
            rules_url: URL to bot rules/terms.
        """
        text = (
            "📋 <b>Примите условия использования</b>\n\n"
            f"Для использования бота необходимо принять правила: {rules_url}\n\n"
            "После прочтения отправьте /accept_rules"
        )

        if isinstance(event, Message):
            await event.answer(text, parse_mode="HTML")
        elif isinstance(event, CallbackQuery):
            await event.answer(
                "Сначала примите правила бота",
                show_alert=True,
            )

    @staticmethod
    async def _send_subscription_required_message(
        event: TelegramObject,
        channel_id: str,
    ) -> None:
        """Send channel subscription required message.

        Args:
            event: Telegram event to respond to.
            channel_id: Channel username or ID.
        """
        # Format channel link
        channel_link = f"https://t.me/{channel_id[1:]}" if channel_id.startswith("@") else channel_id

        text = (
            "📢 <b>Подпишитесь на канал</b>\n\n"
            f"Для использования бота подпишитесь на наш канал: {channel_link}\n\n"
            "После подписки повторите команду."
        )

        if isinstance(event, Message):
            await event.answer(text, parse_mode="HTML", disable_web_page_preview=True)
        elif isinstance(event, CallbackQuery):
            await event.answer(
                "Сначала подпишитесь на канал",
                show_alert=True,
            )
