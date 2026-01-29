from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from states.subscription import SubscriptionState

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from clients.api_client import APIClient
    from config.settings import Settings

logger = structlog.get_logger(__name__)

router = Router(name="payment")


@router.callback_query(SubscriptionState.selecting_payment, F.data.startswith("payment:"))
async def payment_method_selected_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
    state: FSMContext,
) -> None:
    """Handle payment method selection and create payment."""
    payment_method = callback.data.split(":")[1]
    user_id = callback.from_user.id

    # Get stored data
    data = await state.get_data()
    plan_id = data.get("plan_id")
    duration_months = data.get("duration_months")
    total_price = data.get("total_price")

    if not all([plan_id, duration_months, total_price]):
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        await state.clear()
        return

    try:
        # Create payment via API
        payment_data = {
            "user_id": user_id,
            "plan_id": plan_id,
            "duration_months": duration_months,
            "amount": total_price,
            "payment_method": payment_method,
        }

        payment = await api_client.create_payment(payment_data)
        payment_id = payment.get("id")
        payment_url = payment.get("payment_url")

        # Store payment ID
        await state.update_data(payment_id=payment_id)

        if payment_method == "stars":
            # Telegram Stars payment
            from aiogram.types import LabeledPrice

            prices = [LabeledPrice(label=i18n.get("subscription-payment"), amount=int(total_price * 100))]

            await callback.message.answer_invoice(
                title=i18n.get("subscription-payment-title"),
                description=i18n.get("subscription-payment-description"),
                payload=f"payment_{payment_id}",
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
            amount=total_price,
        )

    except Exception as e:
        logger.error("payment_creation_error", user_id=user_id, error=str(e))
        await callback.answer(i18n.get("error-payment-creation-failed"), show_alert=True)
        await state.clear()

    await callback.answer()


@router.callback_query(F.data.startswith("payment:check:"))
async def check_payment_status_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
    state: FSMContext,
) -> None:
    """Check payment status."""
    payment_id = callback.data.split(":")[2]
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

            from keyboards.config import config_delivery_keyboard

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


@router.message(SubscriptionState.processing_payment, F.successful_payment)
async def successful_payment_handler(
    message: Message,
    i18n: I18nContext,
    api_client: APIClient,
    state: FSMContext,
) -> None:
    """Handle successful Telegram Stars payment."""
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
        payment_id = payment_info.invoice_payload[8:]

        try:
            # Confirm payment via API
            await api_client.confirm_payment(payment_id, payment_info.telegram_payment_charge_id)

            await message.answer(i18n.get("payment-success"))

            # Clear state and show config delivery options
            await state.clear()

            from keyboards.config import config_delivery_keyboard

            await message.answer(
                text=i18n.get("config-delivery-prompt"),
                reply_markup=config_delivery_keyboard(i18n),
            )

        except Exception as e:
            logger.error("payment_confirmation_error", user_id=user_id, payment_id=payment_id, error=str(e))
            await message.answer(i18n.get("error-payment-confirmation-failed"))
