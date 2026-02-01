from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.states.promocode import PromoCodeState

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from src.services.api_client import CyberVPNAPIClient

logger = structlog.get_logger(__name__)

router = Router(name="promocode")


@router.callback_query(F.data == "promocode:enter")
async def enter_promocode_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    state: FSMContext,
) -> None:
    """Start promo code entry flow."""
    await callback.message.edit_text(
        text=i18n.get("promocode-enter-prompt"),
    )

    await state.set_state(PromoCodeState.entering_code)
    logger.info("promocode_entry_started", user_id=callback.from_user.id)

    await callback.answer()


@router.message(PromoCodeState.entering_code, F.text)
async def promocode_entered_handler(
    message: Message,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext,
) -> None:
    """Handle promo code input and activation."""
    if message.from_user is None or message.text is None:
        await state.clear()
        return

    user_id = message.from_user.id
    promo_code = message.text.strip().upper()

    try:
        # Validate and activate promo code
        result = await api_client.activate_promocode(user_id, promo_code)

        discount_type = result.get("discount_type", "percentage")
        discount_value = result.get("discount_value", 0)
        discount_currency = result.get("currency") or result.get("currency_code") or i18n.get("currency")

        if discount_type == "percentage":
            discount_text = f"{discount_value}%"
        else:
            discount_text = f"{discount_value} {discount_currency}"

        await message.answer(
            text=i18n.get(
                "promocode-activated",
                code=promo_code,
                discount=discount_text,
            ),
        )

        # Clear state
        await state.clear()

        logger.info(
            "promocode_activated",
            user_id=user_id,
            code=promo_code,
            discount_type=discount_type,
            discount_value=discount_value,
        )

    except Exception as e:
        error_msg = str(e)
        logger.error("promocode_activation_error", user_id=user_id, code=promo_code, error=error_msg)

        # Determine error type
        if "not found" in error_msg.lower():
            await message.answer(i18n.get("promocode-not-found"))
        elif "expired" in error_msg.lower():
            await message.answer(i18n.get("promocode-expired"))
        elif "already used" in error_msg.lower():
            await message.answer(i18n.get("promocode-already-used"))
        elif "usage limit" in error_msg.lower():
            await message.answer(i18n.get("promocode-usage-limit"))
        else:
            await message.answer(i18n.get("error-generic"))

        # Clear state
        await state.clear()


@router.callback_query(F.data == "promocode:cancel")
async def cancel_promocode_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    state: FSMContext,
) -> None:
    """Cancel promo code entry."""
    await state.clear()

    from src.keyboards.menu import main_menu_keyboard

    await callback.message.edit_text(
        text=i18n.get("promocode-cancelled"),
        reply_markup=main_menu_keyboard(i18n),
    )

    logger.info("promocode_entry_cancelled", user_id=callback.from_user.id)
    await callback.answer()
