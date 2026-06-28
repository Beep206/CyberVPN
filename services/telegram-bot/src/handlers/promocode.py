from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router

from src.states.promocode import PromoCodeState

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message
    from aiogram_i18n import I18nContext

    from src.config import BotSettings
    from src.services.api_client import CyberVPNAPIClient
    from src.services.cache_service import CacheService

logger = structlog.get_logger(__name__)

router = Router(name="promocode")


@router.callback_query(F.data.in_({"promocode:enter", "growth:code"}))
async def enter_promocode_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    state: FSMContext,
    settings: BotSettings | None = None,
) -> None:
    """Start promo code entry flow."""
    from src.handlers.connection import _callback_message, _private_gate, telegram_user_fingerprint

    if not await _private_gate(callback, i18n, settings):
        return

    message = _callback_message(callback)
    if message is None:
        await callback.answer(i18n.get("bot-onboarding-connection-private-chat-required"), show_alert=True)
        return

    await message.edit_text(
        text=i18n.get("code-enter-prompt"),
    )

    await state.set_state(PromoCodeState.entering_code)
    logger.info(
        "code_entry_started",
        telegram_user_fingerprint=telegram_user_fingerprint(callback.from_user.id),
        callback_data=callback.data,
    )

    await callback.answer()


@router.message(PromoCodeState.entering_code, F.text)
async def promocode_entered_handler(
    message: Message,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext,
    cache: CacheService | None = None,
    settings: BotSettings | None = None,
) -> None:
    """Handle universal growth-code input and open the shared connection flow."""
    if message.from_user is None or message.text is None:
        await state.clear()
        return
    if cache is None:
        await message.answer(i18n.get("error-generic"))
        await state.clear()
        return

    user_id = message.from_user.id
    code = message.text.strip()
    from src.handlers.connection import apply_code_and_open_connection, code_fingerprint, telegram_user_fingerprint

    await apply_code_and_open_connection(
        message,
        i18n,
        api_client,
        cache,
        settings,
        code=code,
    )
    await state.clear()
    logger.info(
        "onboarding_code_text_submitted",
        telegram_user_fingerprint=telegram_user_fingerprint(user_id),
        code_fingerprint=code_fingerprint(code),
    )


@router.callback_query(F.data == "promocode:cancel")
async def cancel_promocode_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    state: FSMContext,
) -> None:
    """Cancel promo code entry."""
    await state.clear()

    from src.handlers.connection import _callback_message, telegram_user_fingerprint
    from src.keyboards.menu import main_menu_keyboard

    message = _callback_message(callback)
    if message is not None:
        await message.edit_text(
            text=i18n.get("code-cancelled"),
            reply_markup=main_menu_keyboard(i18n),
        )

    logger.info("promocode_entry_cancelled", telegram_user_fingerprint=telegram_user_fingerprint(callback.from_user.id))
    await callback.answer()
