from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery

from src.states.subscription import SubscriptionState

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from src.services.api_client import CyberVPNAPIClient

logger = structlog.get_logger(__name__)

router = Router(name="payment")

STARS_PRICING: dict[int, int] = {
    30: 100,
    90: 250,
    365: 800,
}


def _stars_amount_for_duration(duration_days: int) -> int:
    if duration_days in STARS_PRICING:
        return STARS_PRICING[duration_days]
    if duration_days > 0:
        return max(1, int(duration_days / 30 * 100))
    return 100


@router.callback_query(SubscriptionState.selecting_payment, F.data.startswith("pay:"))
async def payment_method_selected_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext,
) -> None:
    """Handle payment method selection and create payment."""
    if callback.data is None:
        await state.clear()
        return

    if not isinstance(callback.message, Message):
        await state.clear()
        return

    payment_method = callback.data.split(":")[1]
    user_id = callback.from_user.id

    # Get stored data
    data = await state.get_data()
    plan_id = data.get("plan_id")
    duration_days = data.get("duration_days")
    amount = data.get("amount")
    currency = data.get("currency")

    if not all([plan_id, duration_days, amount]):
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        await state.clear()
        return

    if duration_days is None:
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        await state.clear()
        return

    try:
        # Create payment via API
        payment_data = {
            "telegram_id": user_id,
            "plan_id": plan_id,
            "duration_days": duration_days,
            "amount": amount,
            "currency": currency,
            "payment_method": payment_method,
        }

        payment = await api_client.create_payment(payment_data)
        payment_id = payment.get("id")
        payment_url = payment.get("payment_url")

        if not payment_id:
            await callback.answer(i18n.get("error-payment-creation-failed"), show_alert=True)
            await state.clear()
            return

        # Store payment ID
        await state.update_data(payment_id=payment_id)

        if payment_method in {"stars", "telegram_stars"}:
            # Telegram Stars payment
            from aiogram.types import LabeledPrice

            duration_days_value = int(duration_days) if isinstance(duration_days, (int, str)) else 0
            stars_amount = _stars_amount_for_duration(duration_days_value)
            prices = [LabeledPrice(label=i18n.get("subscription-payment"), amount=stars_amount)]

            await callback.message.answer_invoice(
                title=i18n.get("subscription-payment-title"),
                description=i18n.get("subscription-payment-description"),
                payload=f"payment_{payment_id}:{duration_days_value}",
                provider_token="",  # Empty for Telegram Stars
                currency="XTR",
                prices=prices,
            )

        else:
            # External payment (Cryptomus, YooKassa, Stripe)
            if payment_url:
                from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
                from aiogram.utils.keyboard import InlineKeyboardBuilder

                builder = InlineKeyboardBuilder()
                builder.row(
                    InlineKeyboardButton(
                        text=i18n.get("payment-open-link"),
                        url=payment_url,
                    )
                )
                builder.row(
                    InlineKeyboardButton(
                        text=i18n.get("payment-check-status"),
                        callback_data=f"payment:check:{payment_id}",
                        style="primary",
                    )
                )

                await callback.message.edit_text(
                    text=i18n.get("payment-external-instructions"),
                    reply_markup=builder.as_markup(),
                )
            else:
                await callback.answer(i18n.get("error-payment-creation-failed"), show_alert=True)
                await state.clear()
                return

        await state.set_state(SubscriptionState.processing_payment)
        logger.info(
            "payment_created",
            user_id=user_id,
            payment_id=payment_id,
            payment_method=payment_method,
            amount=amount,
        )

    except Exception as e:
        logger.error("payment_creation_error", user_id=user_id, error=str(e))
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
    """Check payment status."""
    if callback.data is None:
        await state.clear()
        return

    if not isinstance(callback.message, Message):
        await state.clear()
        return

    parts = callback.data.split(":")
    payment_id = parts[2] if len(parts) > 2 else None
    if not payment_id:
        data = await state.get_data()
        payment_id = data.get("payment_id")
    if not payment_id:
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        await state.clear()
        return
    user_id = callback.from_user.id

    try:
        # Check payment status via API
        payment = await api_client.get_payment_status(payment_id)
        status = payment.get("status")

        if status == "completed":
            await callback.message.edit_text(
                text=i18n.get("payment-success"),
            )

            # Clear state and show config delivery options
            await state.clear()

            from src.keyboards.config import config_delivery_keyboard

            await callback.message.answer(
                text=i18n.get("config-delivery-prompt"),
                reply_markup=config_delivery_keyboard(i18n),
            )

            logger.info("payment_completed", user_id=user_id, payment_id=payment_id)

        elif status == "pending":
            await callback.answer(i18n.get("payment-pending"), show_alert=True)

        elif status == "failed":
            await callback.message.edit_text(
                text=i18n.get("payment-failed"),
            )
            await state.clear()
            logger.warning("payment_failed", user_id=user_id, payment_id=payment_id)

        else:
            await callback.answer(i18n.get("payment-status-unknown"), show_alert=True)

    except Exception as e:
        logger.error("payment_status_check_error", user_id=user_id, payment_id=payment_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery) -> None:
    """Answer pre-checkout query for Telegram Stars payments."""
    payload = pre_checkout_query.invoice_payload or ""
    if payload.startswith("payment_"):
        await pre_checkout_query.answer(ok=True)
        return

    await pre_checkout_query.answer(ok=False, error_message="Invalid payment payload")


@router.message(SubscriptionState.processing_payment, F.successful_payment)
async def successful_payment_handler(
    message: Message,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext,
) -> None:
    """Handle successful Telegram Stars payment."""
    if message.from_user is None or message.successful_payment is None:
        return

    user_id = message.from_user.id
    payment_info = message.successful_payment

    logger.info(
        "telegram_stars_payment_received",
        user_id=user_id,
        amount=payment_info.total_amount,
        currency=payment_info.currency,
        payload=payment_info.invoice_payload,
    )

    # Extract payment ID from payload
    if payment_info.invoice_payload.startswith("payment_"):
        payload = payment_info.invoice_payload[8:]
        payment_id = payload.split(":")[0]

        try:
            # Confirm payment via API
            await api_client.confirm_payment(payment_id, payment_info.telegram_payment_charge_id)

            await message.answer(i18n.get("payment-success"))

            # Clear state and show config delivery options
            await state.clear()

            from src.keyboards.config import config_delivery_keyboard

            await message.answer(
                text=i18n.get("config-delivery-prompt"),
                reply_markup=config_delivery_keyboard(i18n),
            )

        except Exception as e:
            logger.error("payment_confirmation_error", user_id=user_id, payment_id=payment_id, error=str(e))
            await message.answer(i18n.get("error-payment-confirmation-failed"))
