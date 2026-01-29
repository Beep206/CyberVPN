"""CyberVPN Telegram Bot — Support handler.

Displays support contact information to users.
"""

from __future__ import annotations

from typing import Any, Callable

from aiogram import F, Router
from aiogram.types import CallbackQuery

router = Router(name="support")


@router.callback_query(F.data == "menu:support")
async def support_menu(
    callback: CallbackQuery,
    i18n: Callable[..., str],
    settings: Any,
) -> None:
    """Show support contact information.

    Args:
        callback: Callback query from support menu button.
        i18n: Translator function.
        settings: Bot settings with support username.
    """
    await callback.answer()
    await callback.message.edit_text(
        i18n("support-message", username=settings.support_username),
    )
