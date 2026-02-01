from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.types import CallbackQuery

from src.keyboards.menu import main_menu_keyboard, profile_kb
from src.keyboards.subscription import subscription_keyboard

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from src.config import BotSettings
    from src.services.api_client import CyberVPNAPIClient

logger = structlog.get_logger(__name__)

router = Router(name="menu")


@router.callback_query(F.data == "menu:main")
async def main_menu_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Handle main menu callback."""
    user = None
    try:
        user = await api_client.get_user(callback.from_user.id)
    except Exception as e:
        logger.warning("menu_user_fetch_failed", user_id=callback.from_user.id, error=str(e))

    await callback.message.edit_text(
        text=i18n.get("menu-main-title"),
        reply_markup=main_menu_keyboard(i18n, user),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:connect")
async def connect_menu_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Handle connect/subscription menu callback."""
    user_id = callback.from_user.id

    try:
        # Get active subscriptions
        subscriptions = await api_client.get_user_subscriptions(user_id)
        active_subs = [sub for sub in subscriptions if sub.get("status") == "active"]

        if active_subs:
            # Show subscription details
            sub = active_subs[0]
            text = i18n.get(
                "subscription-active",
                plan=sub.get("plan_name", "N/A"),
                expires=sub.get("expires_at", "N/A"),
            )
        else:
            text = i18n.get("subscription-none")

        await callback.message.edit_text(
            text=text,
            reply_markup=subscription_keyboard(i18n, has_active=bool(active_subs)),
        )
    except Exception as e:
        logger.error("connect_menu_error", user_id=user_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        return

    await callback.answer()


@router.callback_query(F.data == "menu:invite")
async def invite_menu_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    settings: BotSettings,
) -> None:
    """Handle invite/referral menu callback."""
    user_id = callback.from_user.id

    try:
        # Get referral stats
        stats = await api_client.get_referral_stats(user_id)
        referral_count = stats.get("total_referrals", 0)
        referral_bonus = stats.get("bonus_days", stats.get("total_bonus", 0))

        # Generate referral link
        bot_username = settings.bot_username or "CyberVPNBot"
        referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

        text = i18n.get(
            "referral-info",
            link=referral_link,
            count=referral_count,
            bonus_days=referral_bonus,
        )

        from src.keyboards.referral import referral_keyboard

        await callback.message.edit_text(
            text=text,
            reply_markup=referral_keyboard(i18n, stats),
        )
    except Exception as e:
        logger.error("invite_menu_error", user_id=user_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        return

    await callback.answer()


@router.callback_query(F.data == "menu:profile")
async def profile_menu_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Handle profile menu callback."""
    user_id = callback.from_user.id

    try:
        # Get user profile
        user = await api_client.get_user(user_id)
        username = user.get("username")
        username_display = f"@{username}" if username else "N/A"
        telegram_id = user.get("telegram_id", user_id)

        text = i18n.get(
            "profile-info",
            telegram_id=telegram_id,
            username=username_display,
            language=user.get("language_code", "en").upper(),
            registered=user.get("created_at", "N/A"),
        )

        await callback.message.edit_text(
            text=text,
            reply_markup=profile_kb(i18n),
        )
    except Exception as e:
        logger.error("profile_menu_error", user_id=user_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        return

    await callback.answer()


@router.callback_query(F.data == "menu:support")
async def support_menu_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    settings: BotSettings,
) -> None:
    """Handle support menu callback."""
    support_username = settings.support_username
    contact = support_username if support_username.startswith("@") else f"@{support_username}"
    support_text = i18n.get("support-message", contact=contact)

    await callback.message.edit_text(
        text=support_text,
    )
    await callback.answer()
