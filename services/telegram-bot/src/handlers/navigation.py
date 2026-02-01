from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from src.keyboards.menu import main_menu_keyboard

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from src.services.api_client import CyberVPNAPIClient

logger = structlog.get_logger(__name__)

router = Router(name="navigation")


@router.callback_query(F.data == "nav:menu")
@router.callback_query(F.data == "nav:back")
@router.callback_query(F.data == "nav:cancel")
async def navigation_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext,
) -> None:
    """Handle generic navigation callbacks."""
    if callback.message is None:
        await callback.answer()
        return

    await state.clear()

    user = None
    try:
        user = await api_client.get_user(callback.from_user.id)
    except Exception as e:
        logger.warning("navigation_user_fetch_failed", user_id=callback.from_user.id, error=str(e))

    await callback.message.edit_text(
        text=i18n.get("menu-main-title"),
        reply_markup=main_menu_keyboard(i18n, user),
    )
    await callback.answer()
