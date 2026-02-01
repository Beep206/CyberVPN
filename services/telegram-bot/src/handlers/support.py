"""CyberVPN Telegram Bot — Support handler.

Displays support contact information to users.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from aiogram import F, Router
from aiogram.types import CallbackQuery

router = Router(name="support")

if TYPE_CHECKING:
    from src.config import BotSettings


@router.callback_query(F.data == "menu:support")
async def support_menu(
    callback: CallbackQuery,
    i18n: Callable[..., str],
    settings: BotSettings,
) -> None:
    """Show support contact information.

    Args:
        callback: Callback query from support menu button.
        i18n: Translator function.
        settings: Bot settings with support username.
    """
    contact = settings.support_username
    contact = contact if contact.startswith("@") else f"@{contact}"

    await callback.answer()
    await callback.message.edit_text(
        i18n("support-message", contact=contact),
    )
