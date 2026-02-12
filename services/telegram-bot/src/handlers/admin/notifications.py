from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.types import CallbackQuery


if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from src.services.api_client import CyberVPNAPIClient

logger = structlog.get_logger(__name__)

router = Router(name="admin_notifications")


@router.callback_query(F.data == "admin:notifications:settings")
async def notifications_settings_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Show notification settings."""
    try:
        # Get notification settings
        settings = await api_client.get_notification_settings()

        settings_text = i18n.get("admin-notifications-title") + "\n\n"

        # Payment notifications
        payment_enabled = settings.get("payment_notifications_enabled", True)
        settings_text += f"💳 {i18n.get('admin-notifications-payment')}: "
        settings_text += "✅" if payment_enabled else "❌"
        settings_text += "\n"

        # Subscription expiry warnings
        expiry_enabled = settings.get("expiry_warnings_enabled", True)
        expiry_days = settings.get("expiry_warning_days", 3)
        settings_text += f"⏰ {i18n.get('admin-notifications-expiry')}: "
        settings_text += f"✅ ({expiry_days} {i18n.get('days')})" if expiry_enabled else "❌"
        settings_text += "\n"

        # Referral notifications
        referral_enabled = settings.get("referral_notifications_enabled", True)
        settings_text += f"👥 {i18n.get('admin-notifications-referral')}: "
        settings_text += "✅" if referral_enabled else "❌"
        settings_text += "\n"

        # Trial notifications
        trial_enabled = settings.get("trial_notifications_enabled", True)
        settings_text += f"🆓 {i18n.get('admin-notifications-trial')}: "
        settings_text += "✅" if trial_enabled else "❌"
        settings_text += "\n"

        # Create action buttons
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()

        builder.row(
            InlineKeyboardButton(
                text="💳 " + i18n.get("admin-notifications-toggle-payment"),
                callback_data="admin:notifications:toggle:payment",
                style="primary",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="⏰ " + i18n.get("admin-notifications-toggle-expiry"),
                callback_data="admin:notifications:toggle:expiry",
                style="primary",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="👥 " + i18n.get("admin-notifications-toggle-referral"),
                callback_data="admin:notifications:toggle:referral",
                style="primary",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🆓 " + i18n.get("admin-notifications-toggle-trial"),
                callback_data="admin:notifications:toggle:trial",
                style="primary",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔙 " + i18n.get("button-back"),
                callback_data="admin:settings",
                style="primary",
            )
        )

        await callback.message.edit_text(
            text=settings_text,
            reply_markup=builder.as_markup(),
        )

        logger.info("admin_notifications_settings_viewed", admin_id=callback.from_user.id)

    except Exception as e:
        logger.error("admin_notifications_settings_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data.startswith("admin:notifications:toggle:"))
async def notification_toggle_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Toggle notification type."""
    notification_type = callback.data.split(":")[3]

    try:
        # Toggle notification setting
        result = await api_client.toggle_notification_setting(notification_type)
        is_enabled = result.get("is_enabled", False)

        if is_enabled:
            await callback.answer(
                i18n.get("admin-notifications-enabled", type=notification_type),
                show_alert=True,
            )
        else:
            await callback.answer(
                i18n.get("admin-notifications-disabled", type=notification_type),
                show_alert=True,
            )

        # Refresh settings view
        await notifications_settings_handler(callback, i18n, api_client)

        logger.info(
            "admin_notification_toggled",
            admin_id=callback.from_user.id,
            notification_type=notification_type,
            is_enabled=is_enabled,
        )

    except Exception as e:
        logger.error(
            "admin_notification_toggle_error",
            admin_id=callback.from_user.id,
            notification_type=notification_type,
            error=str(e),
        )
        await callback.answer(i18n.get("error-generic"), show_alert=True)
