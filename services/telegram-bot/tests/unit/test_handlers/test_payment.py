from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery, User

from src.handlers.payment import (
    _parse_telegram_stars_invoice_payload,
    payment_method_selected_handler,
    pre_checkout_handler,
    refunded_payment_handler,
    successful_payment_handler,
)
from src.states.subscription import SubscriptionState


class _I18nStub:
    def __call__(self, key: str, **kwargs: object) -> str:
        return self.get(key, **kwargs)

    def get(self, key: str, **kwargs: object) -> str:
        mapping = {
            "error-payment-creation-failed": "Payment creation failed",
            "payment-success": "Payment successful",
            "payment-status-unknown": "Payment status unknown",
            "config-delivery-prompt": "Choose config delivery",
        }
        if key == "notify-payment-refunded":
            return f"Refunded: {kwargs.get('amount')}"
        return mapping.get(key, key)


def _callback(user_id: int = 123456) -> CallbackQuery:
    callback = MagicMock(spec=CallbackQuery)
    callback.data = "pay:telegram_stars"
    callback.from_user = User(id=user_id, is_bot=False, first_name="Test")
    callback.message = MagicMock()
    callback.message.answer_invoice = AsyncMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    return callback


@pytest.mark.asyncio
async def test_payment_method_selected_handler_sends_stars_invoice() -> None:
    callback = _callback()
    state = MagicMock()
    state.get_data = AsyncMock(
        return_value={
            "duration_days": 30,
            "plan_name": "Pro Plan",
            "checkout_payload": {
                "plan_id": "plan-123",
                "addons": [],
                "promo_code": None,
                "use_wallet": 0,
                "telegram_stars_amount": 500,
            },
        }
    )
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    api_client = MagicMock()
    api_client.create_stars_invoice = AsyncMock(
        return_value={
            "payment_id": "payment-123",
            "title": "Pro Plan",
            "description": "CyberVPN access for 30 days",
            "invoice_payload": "stars:payment-123:123456",
            "amount": 500,
            "currency": "XTR",
        }
    )

    await payment_method_selected_handler(callback, _I18nStub(), api_client, state)

    api_client.create_stars_invoice.assert_awaited_once()
    callback.message.answer_invoice.assert_awaited_once()
    invoice_kwargs = callback.message.answer_invoice.await_args.kwargs
    assert invoice_kwargs["currency"] == "XTR"
    assert invoice_kwargs["provider_token"] == ""
    state.set_state.assert_awaited_once_with(SubscriptionState.processing_payment)


@pytest.mark.asyncio
async def test_pre_checkout_handler_validates_via_backend() -> None:
    pre_checkout = MagicMock(spec=PreCheckoutQuery)
    pre_checkout.from_user = User(id=123456, is_bot=False, first_name="Test")
    pre_checkout.currency = "XTR"
    pre_checkout.total_amount = 500
    pre_checkout.invoice_payload = "stars:payment-123:123456"
    pre_checkout.answer = AsyncMock()

    api_client = MagicMock()
    api_client.validate_stars_pre_checkout = AsyncMock(return_value={"ok": True})

    await pre_checkout_handler(pre_checkout, api_client)

    api_client.validate_stars_pre_checkout.assert_awaited_once_with(
        payment_id="payment-123",
        telegram_id=123456,
        currency="XTR",
        total_amount=500,
        invoice_payload="stars:payment-123:123456",
    )
    pre_checkout.answer.assert_awaited_once_with(ok=True, error_message=None)


@pytest.mark.asyncio
async def test_successful_payment_handler_confirms_and_prompts_config() -> None:
    successful_payment = SimpleNamespace(
        currency="XTR",
        total_amount=500,
        invoice_payload="stars:payment-123:123456",
        telegram_payment_charge_id="tg-charge-1",
        provider_payment_charge_id="provider-charge-1",
    )
    message = MagicMock(spec=Message)
    message.from_user = User(id=123456, is_bot=False, first_name="Test")
    message.successful_payment = successful_payment
    message.answer = AsyncMock()

    api_client = MagicMock()
    api_client.confirm_stars_payment = AsyncMock(return_value={"status": "completed", "already_processed": False})
    state = MagicMock()
    state.clear = AsyncMock()

    await successful_payment_handler(message, _I18nStub(), api_client, state)

    api_client.confirm_stars_payment.assert_awaited_once_with(
        payment_id="payment-123",
        telegram_id=123456,
        currency="XTR",
        total_amount=500,
        invoice_payload="stars:payment-123:123456",
        telegram_payment_charge_id="tg-charge-1",
        provider_payment_charge_id="provider-charge-1",
    )
    assert message.answer.await_count == 2
    state.clear.assert_awaited_once()


def test_parse_telegram_stars_invoice_payload() -> None:
    assert _parse_telegram_stars_invoice_payload("stars:payment-123:456") == ("payment-123", 456)
    assert _parse_telegram_stars_invoice_payload("invalid") is None


@pytest.mark.asyncio
async def test_refunded_payment_handler_notifies_user() -> None:
    refunded_payment = SimpleNamespace(
        currency="XTR",
        total_amount=500,
        invoice_payload="stars:payment-123:123456",
        telegram_payment_charge_id="tg-charge-1",
        provider_payment_charge_id="provider-charge-1",
    )
    message = MagicMock(spec=Message)
    message.refunded_payment = refunded_payment
    message.answer = AsyncMock()

    await refunded_payment_handler(message, _I18nStub())

    message.answer.assert_awaited_once_with("Refunded: 500 XTR")
