from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from src.keyboards.admin_main import admin_main_keyboard

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

logger = structlog.get_logger(__name__)

router = Router(name="admin_main")


@router.message(Command("admin"))
async def admin_panel_handler(
    message: Message,
    i18n: I18nContext,
) -> None:
    """Show admin panel main menu."""
    await message.answer(
        text=i18n.get("admin-panel-title"),
        reply_markup=admin_main_keyboard(i18n),
    )

    logger.info("admin_panel_opened", admin_id=message.from_user.id)


@router.callback_query(F.data == "admin:menu")
async def admin_menu_callback_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
) -> None:
    """Handle admin menu callback."""
    await callback.message.edit_text(
        text=i18n.get("admin-panel-title"),
        reply_markup=admin_main_keyboard(i18n),
    )

    await callback.answer()


@router.callback_query(F.data == "admin:settings")
async def admin_settings_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
) -> None:
    """Show admin settings menu."""
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text=i18n.get("admin-settings-access"),
            callback_data="admin:access:settings",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=i18n.get("admin-settings-gateways"),
            callback_data="admin:gateways:settings",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=i18n.get("admin-settings-referral"),
            callback_data="admin:referral:settings",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=i18n.get("admin-settings-notifications"),
            callback_data="admin:notifications:settings",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 " + i18n.get("button-back"),
            callback_data="admin:menu",
        )
    )

    await callback.message.edit_text(
        text=i18n.get("admin-settings-title"),
        reply_markup=builder.as_markup(),
    )

    await callback.answer()
