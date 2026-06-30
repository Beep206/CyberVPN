from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext


def import_keyboard(i18n: I18nContext) -> InlineKeyboardMarkup:
    """Create import/sync keyboard."""
    builder = InlineKeyboardBuilder()

    # Sync from Remnawave
    builder.row(
        InlineKeyboardButton(
            text="🔄 " + i18n.get("admin-import-sync-remnawave"),
            callback_data="admin:import:sync_remnawave",
        )
    )

    # Import users from CSV
    builder.row(
        InlineKeyboardButton(
            text="📥 " + i18n.get("admin-import-users-csv"),
            callback_data="admin:import:users_csv",
        )
    )

    # Import subscriptions from CSV
    builder.row(
        InlineKeyboardButton(
            text="📥 " + i18n.get("admin-import-subscriptions-csv"),
            callback_data="admin:import:subscriptions_csv",
        )
    )

    # Export users to CSV
    builder.row(
        InlineKeyboardButton(
            text="📤 " + i18n.get("admin-import-export-users"),
            callback_data="admin:import:export_users",
        )
    )

    # Export subscriptions to CSV
    builder.row(
        InlineKeyboardButton(
            text="📤 " + i18n.get("admin-import-export-subscriptions"),
            callback_data="admin:import:export_subscriptions",
        )
    )

    # Sync status
    builder.row(
        InlineKeyboardButton(
            text="📊 " + i18n.get("admin-import-sync-status"),
            callback_data="admin:import:sync_status",
        )
    )

    # Back button
    builder.row(
        InlineKeyboardButton(
            text="🔙 " + i18n.get("button-back"),
            callback_data="admin:menu",
        )
    )

    return builder.as_markup()
