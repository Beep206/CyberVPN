from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.types import LabeledPrice

from src.states.subscription import SubscriptionState

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message, PreCheckoutQuery
    from aiogram_i18n import I18nContext

    from src.services.api_client import CyberVPNAPIClient

logger = structlog.get_logger(__name__)

router = Router(name="payment")


def _parse_telegram_stars_invoice_payload(invoice_payload: str) -> tuple[str, int] | None:
    parts = invoice_payload.split(":")
    if len(parts) != 3 or parts[0] != "stars":
        return None

    payment_id = parts[1].strip()
    if not payment_id:
        return None

    try:
        telegram_id = int(parts[2])
    except (TypeError, ValueError):
        return None

    return payment_id, telegram_id


def _stars_checkout_error_message(detail: str | None = None) -> str:
    if detail:
        normalized = detail.strip()
        if normalized:
            return normalized[:120]
    return "Payment validation failed. Please try again."


def _format_telegram_stars_amount(total_amount: int, currency: str) -> str:
    normalized_currency = str(currency or "").upper()
    if normalized_currency == "XTR":
        return f"{int(total_amount)} XTR"
    return f"{int(total_amount)} {normalized_currency}".strip()


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
        if payment_method == "telegram_stars":
            telegram_stars_amount = int(checkout_payload.get("telegram_stars_amount") or 0)
            if telegram_stars_amount <= 0:
                await callback.answer(i18n.get("error-payment-creation-failed"), show_alert=True)
                await state.clear()
                return

            checkout_payload["currency"] = "XTR"
            invoice = await api_client.create_stars_invoice(
                telegram_id=user_id,
                plan_id=str(checkout_payload.get("plan_id") or ""),
                duration_days=int(data.get("duration_days") or 0),
                amount=telegram_stars_amount,
                addons=list(checkout_payload.get("addons") or []),
                promo_code=checkout_payload.get("promo_code"),
                use_wallet=float(checkout_payload.get("use_wallet", 0) or 0),
            )
            payment_id = str(invoice.get("payment_id") or "")
            invoice_payload = str(invoice.get("invoice_payload") or "")

            if not payment_id or not invoice_payload:
                await callback.answer(i18n.get("error-payment-creation-failed"), show_alert=True)
                await state.clear()
                return

            await state.update_data(
                payment_id=payment_id,
                checkout_payload=checkout_payload,
                invoice_payload=invoice_payload,
            )
            await state.set_state(SubscriptionState.processing_payment)

            await callback.message.answer_invoice(
                title=str(invoice.get("title") or data.get("plan_name") or "CyberVPN subscription"),
                description=str(invoice.get("description") or "Telegram Stars payment"),
                payload=invoice_payload,
                currency=str(invoice.get("currency") or "XTR"),
                prices=[
                    LabeledPrice(
                        label=str(data.get("plan_name") or "CyberVPN subscription"),
                        amount=int(invoice.get("amount") or telegram_stars_amount),
                    )
                ],
                provider_token="",
            )
            logger.info(
                "telegram_stars_invoice_sent",
                user_id=user_id,
                payment_id=payment_id,
                total_amount=telegram_stars_amount,
            )
            await callback.answer()
            return

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
async def pre_checkout_handler(
    pre_checkout_query: PreCheckoutQuery,
    api_client: CyberVPNAPIClient,
) -> None:
    parsed_payload = _parse_telegram_stars_invoice_payload(pre_checkout_query.invoice_payload)
    if parsed_payload is None:
        await pre_checkout_query.answer(ok=False, error_message=_stars_checkout_error_message())
        return

    payment_id, telegram_id = parsed_payload
    if telegram_id != pre_checkout_query.from_user.id:
        await pre_checkout_query.answer(ok=False, error_message=_stars_checkout_error_message())
        return

    try:
        result = await api_client.validate_stars_pre_checkout(
            payment_id=payment_id,
            telegram_id=telegram_id,
            currency=pre_checkout_query.currency,
            total_amount=pre_checkout_query.total_amount,
            invoice_payload=pre_checkout_query.invoice_payload,
        )
        ok = bool(result.get("ok"))
        await pre_checkout_query.answer(
            ok=ok,
            error_message=None if ok else _stars_checkout_error_message(result.get("error_message")),
        )
    except Exception as exc:
        logger.error(
            "telegram_stars_pre_checkout_failed",
            payment_id=payment_id,
            telegram_id=telegram_id,
            error=str(exc),
        )
        await pre_checkout_query.answer(ok=False, error_message=_stars_checkout_error_message(str(exc)))


@router.message(F.successful_payment)
async def successful_payment_handler(
    message: Message,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext,
) -> None:
    if message.successful_payment is None:
        return

    successful_payment = message.successful_payment
    parsed_payload = _parse_telegram_stars_invoice_payload(successful_payment.invoice_payload)
    if parsed_payload is None or message.from_user is None:
        logger.warning("unexpected_successful_payment_received", payload=successful_payment.invoice_payload)
        await message.answer(i18n.get("payment-status-unknown"))
        return

    payment_id, telegram_id = parsed_payload
    if telegram_id != message.from_user.id:
        logger.warning(
            "successful_payment_user_mismatch",
            payment_id=payment_id,
            expected_telegram_id=telegram_id,
            actual_telegram_id=message.from_user.id,
        )
        await message.answer(i18n.get("payment-status-unknown"))
        return

    try:
        result = await api_client.confirm_stars_payment(
            payment_id=payment_id,
            telegram_id=telegram_id,
            currency=successful_payment.currency,
            total_amount=successful_payment.total_amount,
            invoice_payload=successful_payment.invoice_payload,
            telegram_payment_charge_id=successful_payment.telegram_payment_charge_id,
            provider_payment_charge_id=successful_payment.provider_payment_charge_id,
        )
        logger.info(
            "telegram_stars_payment_confirmed",
            payment_id=payment_id,
            telegram_id=telegram_id,
            already_processed=bool(result.get("already_processed")),
        )
    except Exception as exc:
        logger.error("telegram_stars_payment_confirm_failed", payment_id=payment_id, error=str(exc))
        await message.answer(i18n.get("payment-status-unknown"))
        return

    await state.clear()
    await message.answer(i18n.get("payment-success"))

    from src.keyboards.config import config_delivery_keyboard

    await message.answer(
        text=i18n.get("config-delivery-prompt"),
        reply_markup=config_delivery_keyboard(i18n),
    )


@router.message(F.refunded_payment)
async def refunded_payment_handler(
    message: Message,
    i18n: I18nContext,
) -> None:
    if message.refunded_payment is None:
        return

    refunded_payment = message.refunded_payment
    amount = _format_telegram_stars_amount(refunded_payment.total_amount, refunded_payment.currency)
    logger.info(
        "telegram_stars_payment_refunded",
        telegram_payment_charge_id=refunded_payment.telegram_payment_charge_id,
        provider_payment_charge_id=refunded_payment.provider_payment_charge_id,
        amount=refunded_payment.total_amount,
        currency=refunded_payment.currency,
    )
    await message.answer(i18n.get("notify-payment-refunded", amount=amount))
