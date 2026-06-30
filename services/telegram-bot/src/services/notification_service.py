from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram_i18n import I18nContext

    from src.services.api_client import CyberVPNAPIClient

logger = structlog.get_logger(__name__)


class NotificationService:
    """Service for sending notifications to users via Telegram bot."""

    def __init__(self, bot: Bot, api_client: CyberVPNAPIClient) -> None:
        """Initialize notification service.

        Args:
            bot: Telegram bot instance
            api_client: API client for fetching user data
        """
        self.bot = bot
        self.api_client = api_client

    async def send_payment_confirmation(
        self,
        user_id: int,
        payment_data: dict[str, Any],
        i18n: I18nContext,
    ) -> None:
        """Send payment confirmation notification.

        Args:
            user_id: Telegram user ID
            payment_data: Payment information
            i18n: I18n context for translations
        """
        try:
            amount = payment_data.get("amount", 0)
            payment_id = payment_data.get("id")
            plan_name = payment_data.get("plan_name", "N/A")

            message = i18n.get(
                "notification-payment-success",
                amount=amount,
                plan=plan_name,
                payment_id=payment_id,
            )

            await self.bot.send_message(
                chat_id=user_id,
                text=message,
            )

            logger.info("payment_confirmation_sent", user_id=user_id, payment_id=payment_id)

        except Exception as e:
            logger.error("payment_confirmation_error", user_id=user_id, error=str(e))

    async def send_subscription_expiry_warning(
        self,
        user_id: int,
        subscription_data: dict[str, Any],
        days_remaining: int,
        i18n: I18nContext,
    ) -> None:
        """Send subscription expiry warning.

        Args:
            user_id: Telegram user ID
            subscription_data: Subscription information
            days_remaining: Days until expiry
            i18n: I18n context for translations
        """
        try:
            plan_name = subscription_data.get("plan_name", "N/A")
            expires_at = subscription_data.get("expires_at", "N/A")

            message = i18n.get(
                "notification-subscription-expiring",
                plan=plan_name,
                days=days_remaining,
                expires_at=expires_at,
            )

            from aiogram.types import InlineKeyboardButton
            from aiogram.utils.keyboard import InlineKeyboardBuilder

            builder = InlineKeyboardBuilder()
            builder.row(
                InlineKeyboardButton(
                    text=i18n.get("notification-renew-subscription"),
                    callback_data="subscription:buy",
                )
            )

            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                reply_markup=builder.as_markup(),
            )

            logger.info(
                "expiry_warning_sent",
                user_id=user_id,
                days_remaining=days_remaining,
            )

        except Exception as e:
            logger.error("expiry_warning_error", user_id=user_id, error=str(e))

    async def send_subscription_expired(
        self,
        user_id: int,
        subscription_data: dict[str, Any],
        i18n: I18nContext,
    ) -> None:
        """Send subscription expired notification.

        Args:
            user_id: Telegram user ID
            subscription_data: Subscription information
            i18n: I18n context for translations
        """
        try:
            plan_name = subscription_data.get("plan_name", "N/A")

            message = i18n.get(
                "notification-subscription-expired",
                plan=plan_name,
            )

            from aiogram.types import InlineKeyboardButton
            from aiogram.utils.keyboard import InlineKeyboardBuilder

            builder = InlineKeyboardBuilder()
            builder.row(
                InlineKeyboardButton(
                    text=i18n.get("notification-renew-subscription"),
                    callback_data="subscription:buy",
                )
            )

            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                reply_markup=builder.as_markup(),
            )

            logger.info("expiry_notification_sent", user_id=user_id)

        except Exception as e:
            logger.error("expiry_notification_error", user_id=user_id, error=str(e))

    async def send_referral_bonus(
        self,
        user_id: int,
        bonus_data: dict[str, Any],
        i18n: I18nContext,
    ) -> None:
        """Send referral bonus notification.

        Args:
            user_id: Telegram user ID
            bonus_data: Referral bonus information
            i18n: I18n context for translations
        """
        try:
            bonus_amount = bonus_data.get("bonus_amount", 0)
            referred_user = bonus_data.get("referred_username", "N/A")

            message = i18n.get(
                "notification-referral-bonus",
                amount=bonus_amount,
                referred_user=referred_user,
            )

            await self.bot.send_message(
                chat_id=user_id,
                text=message,
            )

            logger.info("referral_bonus_notification_sent", user_id=user_id, bonus=bonus_amount)

        except Exception as e:
            logger.error("referral_bonus_notification_error", user_id=user_id, error=str(e))

    async def send_trial_activated(
        self,
        user_id: int,
        trial_data: dict[str, Any],
        i18n: I18nContext,
    ) -> None:
        """Send trial activation notification.

        Args:
            user_id: Telegram user ID
            trial_data: Trial information
            i18n: I18n context for translations
        """
        try:
            duration_days = trial_data.get("duration_days", 3)
            expires_at = trial_data.get("expires_at", "N/A")

            message = i18n.get(
                "notification-trial-activated",
                duration=duration_days,
                expires_at=expires_at,
            )

            from aiogram.types import InlineKeyboardButton
            from aiogram.utils.keyboard import InlineKeyboardBuilder

            builder = InlineKeyboardBuilder()
            builder.row(
                InlineKeyboardButton(
                    text=i18n.get("notification-get-config"),
                    callback_data="config:qr",
                )
            )

            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                reply_markup=builder.as_markup(),
            )

            logger.info("trial_activation_notification_sent", user_id=user_id)

        except Exception as e:
            logger.error("trial_activation_notification_error", user_id=user_id, error=str(e))

    async def send_subscription_activated(
        self,
        user_id: int,
        subscription_data: dict[str, Any],
        i18n: I18nContext,
    ) -> None:
        """Send subscription activation notification.

        Args:
            user_id: Telegram user ID
            subscription_data: Subscription information
            i18n: I18n context for translations
        """
        try:
            plan_name = subscription_data.get("plan_name", "N/A")
            expires_at = subscription_data.get("expires_at", "N/A")

            message = i18n.get(
                "notification-subscription-activated",
                plan=plan_name,
                expires_at=expires_at,
            )

            from aiogram.types import InlineKeyboardButton
            from aiogram.utils.keyboard import InlineKeyboardBuilder

            builder = InlineKeyboardBuilder()
            builder.row(
                InlineKeyboardButton(
                    text=i18n.get("notification-get-config"),
                    callback_data="config:qr",
                )
            )

            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                reply_markup=builder.as_markup(),
            )

            logger.info("subscription_activation_notification_sent", user_id=user_id)

        except Exception as e:
            logger.error("subscription_activation_notification_error", user_id=user_id, error=str(e))

    async def send_admin_alert(
        self,
        admin_ids: list[int],
        alert_message: str,
    ) -> None:
        """Send alert to admin users.

        Args:
            admin_ids: List of admin Telegram user IDs
            alert_message: Alert message text
        """
        for admin_id in admin_ids:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=f"🚨 ADMIN ALERT\n\n{alert_message}",
                )

                logger.info("admin_alert_sent", admin_id=admin_id)

            except Exception as e:
                logger.error("admin_alert_error", admin_id=admin_id, error=str(e))
