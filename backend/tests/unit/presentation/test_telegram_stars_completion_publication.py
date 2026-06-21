from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import SecretStr

from src.presentation.api.v1.telegram import routes as telegram_routes
from src.presentation.api.v1.telegram.schemas import TelegramStarsConfirmRequest


@pytest.mark.asyncio
async def test_telegram_stars_confirmation_defers_cash_rewards_and_publishes_payment_completed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    payment_id = uuid4()
    attempt_id = uuid4()
    order_id = uuid4()
    invoice_payload = telegram_routes._build_telegram_stars_invoice_payload(
        payment_id=payment_id,
        telegram_id=123456789,
    )
    payment = SimpleNamespace(
        id=payment_id,
        user_uuid=user_id,
        status="pending",
        provider="telegram_stars",
        external_id=None,
        amount=500,
        currency="XTR",
        metadata_={
            "invoice_payload": invoice_payload,
            "telegram_stars_amount": 500,
            "commission_base_amount": "999.00",
        },
        created_at=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        updated_at=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
    )
    mobile_user = SimpleNamespace(id=user_id)
    payment_attempt = SimpleNamespace(id=attempt_id, order_id=order_id, status="succeeded")
    db = SimpleNamespace(commit=AsyncMock())
    update_payment = AsyncMock(return_value=payment)
    append_event = AsyncMock(return_value=SimpleNamespace(id=uuid4()))
    post_payment_execute = AsyncMock(return_value={"cash_rewards_deferred": True})

    class _PaymentRepository:
        def __init__(self, _db) -> None:
            pass

        async def update(self, updated_payment):
            return await update_payment(updated_payment)

    class _PaymentAttemptRepository:
        def __init__(self, _db) -> None:
            pass

        async def get_by_payment_id(self, requested_payment_id):
            assert requested_payment_id == payment_id
            return payment_attempt

    class _Outbox:
        def __init__(self, _db) -> None:
            pass

        async def append_event(self, **kwargs):
            return await append_event(**kwargs)

    class _PostPayment:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, requested_payment_id, *, process_cash_rewards: bool = False):
            return await post_payment_execute(
                requested_payment_id,
                process_cash_rewards=process_cash_rewards,
            )

    monkeypatch.setattr(telegram_routes.settings, "telegram_bot_internal_secret", SecretStr("telegram-test-secret"))
    monkeypatch.setattr(
        telegram_routes,
        "_validate_telegram_stars_payment",
        AsyncMock(return_value=(payment, mobile_user)),
    )
    monkeypatch.setattr(telegram_routes, "PaymentRepository", _PaymentRepository)
    monkeypatch.setattr(telegram_routes, "PaymentAttemptRepository", _PaymentAttemptRepository)
    monkeypatch.setattr(telegram_routes, "EventOutboxService", _Outbox)
    monkeypatch.setattr(
        "src.application.use_cases.payments.post_payment.PostPaymentProcessingUseCase",
        _PostPayment,
    )

    response = await telegram_routes.confirm_telegram_stars_payment(
        payment_id=payment_id,
        body=TelegramStarsConfirmRequest(
            telegram_id=123456789,
            currency="XTR",
            total_amount=500,
            invoice_payload=invoice_payload,
            telegram_payment_charge_id="tg-stars-charge-1",
            provider_payment_charge_id="provider-charge-1",
        ),
        telegram_bot_secret="telegram-test-secret",
        db=db,
    )

    assert response.payment_id == payment_id
    assert response.status == "completed"
    assert response.external_id == "tg-stars-charge-1"
    assert response.already_processed is False
    assert payment.metadata_["telegram_payment_charge_id"] == "tg-stars-charge-1"
    update_payment.assert_awaited_once_with(payment)
    post_payment_execute.assert_awaited_once_with(payment_id, process_cash_rewards=False)
    append_event.assert_awaited_once()
    append_kwargs = append_event.await_args.kwargs
    assert append_kwargs["event_name"] == "payment.completed"
    assert append_kwargs["event_key"] == f"payment.completed:{payment_id}"
    assert append_kwargs["event_payload"]["payment_id"] == str(payment_id)
    assert append_kwargs["event_payload"]["payment_attempt_id"] == str(attempt_id)
    assert append_kwargs["event_payload"]["order_id"] == str(order_id)
    assert append_kwargs["source_context"]["source"] == "telegram_stars_confirm"
    db.commit.assert_awaited_once()
