from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext


def access_settings_keyboard(
    i18n: I18nContext,
    settings: dict,
) -> InlineKeyboardMarkup:
    """Create access settings keyboard."""
    builder = InlineKeyboardBuilder()

    # Access mode toggle
    access_mode = settings.get("access_mode", "open")
    mode_status = "🔒" if access_mode == "private" else "🔓"
    builder.row(
        InlineKeyboardButton(
            text=f"{mode_status} {i18n.get('admin-access-mode')}: {access_mode.upper()}",
            callback_data="admin:access:toggle_mode",
            style="primary",
        )
    )

    # Channel requirement
    channel_required = settings.get("channel_required", False)
    channel_status = "✅" if channel_required else "❌"
    builder.row(
        InlineKeyboardButton(
            text=f"{channel_status} {i18n.get('admin-access-channel-required')}",
            callback_data="admin:access:toggle_channel",
            style="primary",
        )
    )

    # Set channel
    if channel_required:
        builder.row(
            InlineKeyboardButton(
                text="📢 " + i18n.get("admin-access-set-channel"),
                callback_data="admin:access:set_channel",
                style="primary",
            )
        )

    # Access rules
    rules_enabled = settings.get("rules_enabled", False)
    rules_status = "✅" if rules_enabled else "❌"
    builder.row(
        InlineKeyboardButton(
            text=f"{rules_status} {i18n.get('admin-access-rules-enabled')}",
            callback_data="admin:access:toggle_rules",
            style="primary",
        )
    )

    # Edit rules
    if rules_enabled:
        builder.row(
            InlineKeyboardButton(
                text="📝 " + i18n.get("admin-access-edit-rules"),
                callback_data="admin:access:edit_rules",
                style="primary",
            )
        )

    # Whitelist/Blacklist
    builder.row(
        InlineKeyboardButton(
            text="✅ " + i18n.get("admin-access-whitelist"),
            callback_data="admin:access:whitelist",
            style="primary",
        ),
        InlineKeyboardButton(
            text="🚫 " + i18n.get("admin-access-blacklist"),
            callback_data="admin:access:blacklist",
            style="danger",
        ),
    )

    # Back button
    builder.row(
        InlineKeyboardButton(
            text="🔙 " + i18n.get("button-back"),
            callback_data="admin:settings",
            style="primary",
        )
    )

    return builder.as_markup()
