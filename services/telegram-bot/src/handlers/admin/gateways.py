from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.types import CallbackQuery


if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from src.services.api_client import CyberVPNAPIClient

logger = structlog.get_logger(__name__)

router = Router(name="admin_gateways")


@router.callback_query(F.data == "admin:gateways:settings")
async def gateways_settings_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Show payment gateways settings."""
    try:
        # Get gateway settings
        gateways = await api_client.get_payment_gateways()

        gateway_text = i18n.get("admin-gateways-title") + "\n\n"

        for gateway in gateways:
            gateway_name = gateway.get("name")
            is_enabled = gateway.get("is_enabled", False)
            status_emoji = "✅" if is_enabled else "❌"

            gateway_text += f"{status_emoji} {gateway_name}\n"

        # Create action buttons
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()

        for gateway in gateways:
            gateway_id = gateway.get("id")
            gateway_name = gateway.get("name")

            builder.row(
                InlineKeyboardButton(
                    text=f"⚙️ {gateway_name}",
                    callback_data=f"admin:gateway:view:{gateway_id}",
                )
            )

        builder.row(
            InlineKeyboardButton(
                text="🔙 " + i18n.get("button-back"),
                callback_data="admin:settings",
            )
        )

        await callback.message.edit_text(
            text=gateway_text,
            reply_markup=builder.as_markup(),
        )

        logger.info("admin_gateways_settings_viewed", admin_id=callback.from_user.id)

    except Exception as e:
        logger.error("admin_gateways_settings_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data.startswith("admin:gateway:view:"))
async def gateway_view_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """View gateway details."""
    gateway_id = callback.data.split(":")[3]

    try:
        # Get gateway details
        gateway = await api_client.get_payment_gateway(gateway_id)

        gateway_text = i18n.get(
            "admin-gateway-details",
            name=gateway.get("name", "N/A"),
            type=gateway.get("type", "N/A"),
            is_enabled=i18n.get("yes") if gateway.get("is_enabled") else i18n.get("no"),
            commission=gateway.get("commission_percent", 0),
        )

        # Create action buttons
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()

        toggle_text = (
            i18n.get("admin-gateway-disable") if gateway.get("is_enabled") else i18n.get("admin-gateway-enable")
        )

        builder.row(
            InlineKeyboardButton(
                text=toggle_text,
                callback_data=f"admin:gateway:toggle:{gateway_id}",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔙 " + i18n.get("button-back"),
                callback_data="admin:gateways:settings",
            )
        )

        await callback.message.edit_text(
            text=gateway_text,
            reply_markup=builder.as_markup(),
        )

        logger.info("admin_gateway_viewed", admin_id=callback.from_user.id, gateway_id=gateway_id)

    except Exception as e:
        logger.error("admin_gateway_view_error", admin_id=callback.from_user.id, gateway_id=gateway_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data.startswith("admin:gateway:toggle:"))
async def gateway_toggle_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
) -> None:
    """Toggle gateway enabled status."""
    gateway_id = callback.data.split(":")[3]

    try:
        # Toggle gateway status
        result = await api_client.toggle_payment_gateway(gateway_id)
        is_enabled = result.get("is_enabled", False)

        if is_enabled:
            await callback.answer(i18n.get("admin-gateway-enabled"), show_alert=True)
        else:
            await callback.answer(i18n.get("admin-gateway-disabled"), show_alert=True)

        # Refresh gateway view
        await gateway_view_handler(callback, i18n, api_client)

        logger.info(
            "admin_gateway_toggled", admin_id=callback.from_user.id, gateway_id=gateway_id, is_enabled=is_enabled
        )

    except Exception as e:
        logger.error("admin_gateway_toggle_error", admin_id=callback.from_user.id, gateway_id=gateway_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)
