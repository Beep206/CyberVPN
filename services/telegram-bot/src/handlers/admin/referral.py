from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.types import CallbackQuery

from src.keyboards.admin_referral import referral_settings_keyboard

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from src.services.api_client import CyberVPNAPIClient

logger = structlog.get_logger(__name__)

router = Router(name="admin_referral")


@router.callback_query(F.data == "admin:referral:settings")
async def referral_settings_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Show referral system settings."""
    try:
        settings = await api_client.get_referral_settings()

        await callback.message.edit_text(
            text=i18n.get("admin-referral-settings-title"),
            reply_markup=referral_settings_keyboard(i18n, settings),
        )

        logger.info("admin_referral_settings_viewed", admin_id=callback.from_user.id)

    except Exception as e:
        logger.error("admin_referral_settings_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "admin:referral:toggle_enabled")
async def toggle_referral_system_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Toggle referral system."""
    try:
        settings = await api_client.get_referral_settings()
        current = settings.get("referral_enabled", False)

        await api_client.update_referral_settings({"referral_enabled": not current})

        action = "disabled" if current else "enabled"
        await callback.answer(i18n.get(f"admin-referral-system-{action}"), show_alert=True)

        # Refresh settings
        await referral_settings_handler(callback, i18n, api_client)

        logger.info("admin_referral_system_toggled", admin_id=callback.from_user.id, enabled=not current)

    except Exception as e:
        logger.error("admin_referral_toggle_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)


@router.callback_query(F.data == "admin:referral:toggle_type")
async def toggle_reward_type_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Toggle reward type (percentage/fixed)."""
    try:
        settings = await api_client.get_referral_settings()
        current = settings.get("referral_reward_type", "fixed")
        new_type = "percentage" if current == "fixed" else "fixed"

        await api_client.update_referral_settings({"referral_reward_type": new_type})

        await callback.answer(i18n.get(f"admin-referral-type-{new_type}"), show_alert=True)

        # Refresh settings
        await referral_settings_handler(callback, i18n, api_client)

        logger.info("admin_referral_type_toggled", admin_id=callback.from_user.id, new_type=new_type)

    except Exception as e:
        logger.error("admin_referral_type_toggle_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)


@router.callback_query(F.data == "admin:referral:toggle_first_purchase")
async def toggle_first_purchase_bonus_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Toggle first purchase bonus."""
    try:
        settings = await api_client.get_referral_settings()
        current = settings.get("first_purchase_bonus", False)

        await api_client.update_referral_settings({"first_purchase_bonus": not current})

        action = "disabled" if current else "enabled"
        await callback.answer(i18n.get(f"admin-referral-first-purchase-{action}"), show_alert=True)

        # Refresh settings
        await referral_settings_handler(callback, i18n, api_client)

        logger.info("admin_referral_first_purchase_toggled", admin_id=callback.from_user.id, enabled=not current)

    except Exception as e:
        logger.error("admin_referral_first_purchase_toggle_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)


@router.callback_query(F.data == "admin:referral:toggle_lifetime")
async def toggle_lifetime_referrals_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Toggle lifetime referrals."""
    try:
        settings = await api_client.get_referral_settings()
        current = settings.get("lifetime_referrals", False)

        await api_client.update_referral_settings({"lifetime_referrals": not current})

        action = "disabled" if current else "enabled"
        await callback.answer(i18n.get(f"admin-referral-lifetime-{action}"), show_alert=True)

        # Refresh settings
        await referral_settings_handler(callback, i18n, api_client)

        logger.info("admin_referral_lifetime_toggled", admin_id=callback.from_user.id, enabled=not current)

    except Exception as e:
        logger.error("admin_referral_lifetime_toggle_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)


@router.callback_query(F.data == "admin:referral:stats")
async def referral_stats_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Show referral statistics."""
    try:
        stats = await api_client.get_referral_system_stats()

        total_referrals = stats.get("total_referrals", 0)
        active_referrers = stats.get("active_referrers", 0)
        total_bonus_paid = stats.get("total_bonus_paid", 0)
        pending_bonus = stats.get("pending_bonus", 0)

        stats_text = i18n.get(
            "admin-referral-stats-details",
            total=total_referrals,
            active=active_referrers,
            paid=total_bonus_paid,
            pending=pending_bonus,
        )

        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="🔙 " + i18n.get("button-back"),
                callback_data="admin:referral:settings",
                style="primary",
            )
        )

        await callback.message.edit_text(
            text=stats_text,
            reply_markup=builder.as_markup(),
        )

        logger.info("admin_referral_stats_viewed", admin_id=callback.from_user.id)

    except Exception as e:
        logger.error("admin_referral_stats_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()
