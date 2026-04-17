from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router

from src.states.subscription import SubscriptionState

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message, PreCheckoutQuery
    from aiogram_i18n import I18nContext

    from src.services.api_client import CyberVPNAPIClient

logger = structlog.get_logger(__name__)

router = Router(name="payment")


@router.callback_query(SubscriptionState.selecting_payment, F.data.startswith("pay:"))
async def payment_method_selected_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext,
) -> None:
    if callback.data is None:
        await state.clear()
        return

    payment_method = callback.data.split(":")[1]
    user_id = callback.from_user.id
    data = await state.get_data()
    checkout_payload = dict(data.get("checkout_payload") or {})

    if not checkout_payload:
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        await state.clear()
        return

    checkout_payload["payment_method"] = payment_method

    try:
        payment = await api_client.commit_checkout(user_id, checkout_payload)
        payment_id = payment.get("payment_id")
        status = payment.get("status")
        invoice = payment.get("invoice") or {}

        await state.update_data(payment_id=payment_id, checkout_payload=checkout_payload)

        if status == "completed":
            await callback.message.edit_text(text=i18n.get("payment-success"))
            await state.clear()

            from src.keyboards.config import config_delivery_keyboard

            await callback.message.answer(
                text=i18n.get("config-delivery-prompt"),
                reply_markup=config_delivery_keyboard(i18n),
            )
            logger.info("payment_completed_zero_gateway", user_id=user_id, payment_id=payment_id)
            await callback.answer()
            return

        payment_url = invoice.get("payment_url")
        if payment_id and payment_url:
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=i18n.get("payment-open-link"), url=payment_url)],
                    [
                        InlineKeyboardButton(
                            text=i18n.get("payment-check-status"),
                            callback_data=f"payment:check:{payment_id}",
                        )
                    ],
                ]
            )
            await callback.message.edit_text(
                text=i18n.get("payment-external-instructions"),
                reply_markup=keyboard,
            )
            await state.set_state(SubscriptionState.processing_payment)
            logger.info(
                "payment_created",
                user_id=user_id,
                payment_id=payment_id,
                payment_method=payment_method,
            )
        else:
            await callback.answer(i18n.get("error-payment-creation-failed"), show_alert=True)
            await state.clear()
    except Exception as exc:
        logger.error("payment_creation_error", user_id=user_id, error=str(exc))
        await callback.answer(i18n.get("error-payment-creation-failed"), show_alert=True)
        await state.clear()

    await callback.answer()


@router.callback_query(F.data.startswith("payment:check"))
async def check_payment_status_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext,
) -> None:
    if callback.data is None:
        await state.clear()
        return

    parts = callback.data.split(":")
    payment_id = parts[2] if len(parts) > 2 else None
    if not payment_id:
        payment_id = (await state.get_data()).get("payment_id")
    if not payment_id:
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        await state.clear()
        return

    user_id = callback.from_user.id

    try:
        payment = await api_client.get_payment_status(user_id, payment_id)
        status = payment.get("status")

        if status == "completed":
            await callback.message.edit_text(text=i18n.get("payment-success"))
            await state.clear()

            from src.keyboards.config import config_delivery_keyboard

            await callback.message.answer(
                text=i18n.get("config-delivery-prompt"),
                reply_markup=config_delivery_keyboard(i18n),
            )
            logger.info("payment_completed", user_id=user_id, payment_id=payment_id)
        elif status == "pending":
            await callback.answer(i18n.get("payment-pending"), show_alert=True)
        elif status in {"failed", "cancelled", "expired"}:
            await callback.message.edit_text(text=i18n.get("payment-failed"))
            await state.clear()
            logger.warning("payment_failed", user_id=user_id, payment_id=payment_id, status=status)
        else:
            await callback.answer(i18n.get("payment-status-unknown"), show_alert=True)
    except Exception as exc:
        logger.error("payment_status_check_error", user_id=user_id, payment_id=payment_id, error=str(exc))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery) -> None:
    await pre_checkout_query.answer(ok=False, error_message="Telegram Stars are not enabled in this flow")


@router.message(SubscriptionState.processing_payment, F.successful_payment)
async def successful_payment_handler(
    message: Message,
    i18n: I18nContext,
) -> None:
    if message.successful_payment is None:
        return
    logger.warning("unexpected_successful_payment_received", payload=message.successful_payment.invoice_payload)
    await message.answer(i18n.get("payment-status-unknown"))
