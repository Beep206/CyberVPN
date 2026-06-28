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
    db = SimpleNamespace(commit=AsyncMock())
    update_payment = AsyncMock(return_value=payment)
    append_event = AsyncMock(return_value=SimpleNamespace(id=uuid4()))
    post_payment_execute = AsyncMock(return_value={"cash_rewards_deferred": True})
    settlement_execute = AsyncMock(
        return_value=SimpleNamespace(
            status="legacy_non_order",
            legacy_post_payment_required=True,
        )
    )

    class _PaymentRepository:
        def __init__(self, _db) -> None:
            pass

        async def update(self, updated_payment):
            return await update_payment(updated_payment)

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

    class _Settlement:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, **kwargs):
            return await settlement_execute(**kwargs)

    monkeypatch.setattr(telegram_routes.settings, "telegram_bot_internal_secret", SecretStr("telegram-test-secret"))
    monkeypatch.setattr(
        telegram_routes,
        "_validate_telegram_stars_payment",
        AsyncMock(return_value=(payment, mobile_user)),
    )
    monkeypatch.setattr(telegram_routes, "PaymentRepository", _PaymentRepository)
    monkeypatch.setattr(telegram_routes, "EventOutboxService", _Outbox)
    monkeypatch.setattr(telegram_routes, "SettleCompletedPaymentAttemptUseCase", _Settlement)
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
    settlement_execute.assert_awaited_once_with(
        payment_id=payment_id,
        provider="telegram_stars",
        source="telegram_stars_confirm",
    )
    post_payment_execute.assert_awaited_once_with(payment_id, process_cash_rewards=False)
    append_event.assert_awaited_once()
    append_kwargs = append_event.await_args.kwargs
    assert append_kwargs["event_name"] == "payment.completed"
    assert append_kwargs["event_key"] == f"payment.completed:{payment_id}"
    assert append_kwargs["event_payload"]["payment_id"] == str(payment_id)
    assert append_kwargs["event_payload"]["payment_attempt_id"] is None
    assert append_kwargs["event_payload"]["order_id"] is None
    assert append_kwargs["source_context"]["source"] == "telegram_stars_confirm"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_telegram_stars_confirmation_uses_order_settlement_without_legacy_post_payment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    payment_id = uuid4()
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
    db = SimpleNamespace(commit=AsyncMock())
    update_payment = AsyncMock(return_value=payment)
    settlement_execute = AsyncMock(
        return_value=SimpleNamespace(
            status="finalized",
            legacy_post_payment_required=False,
        )
    )
    post_payment_execute = AsyncMock()
    append_event = AsyncMock()

    class _PaymentRepository:
        def __init__(self, _db) -> None:
            pass

        async def update(self, updated_payment):
            return await update_payment(updated_payment)

    class _Settlement:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, **kwargs):
            return await settlement_execute(**kwargs)

    class _PostPayment:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, requested_payment_id, *, process_cash_rewards: bool = False):
            return await post_payment_execute(
                requested_payment_id,
                process_cash_rewards=process_cash_rewards,
            )

    class _Outbox:
        def __init__(self, _db) -> None:
            pass

        async def append_event(self, **kwargs):
            return await append_event(**kwargs)

    monkeypatch.setattr(telegram_routes.settings, "telegram_bot_internal_secret", SecretStr("telegram-test-secret"))
    monkeypatch.setattr(
        telegram_routes,
        "_validate_telegram_stars_payment",
        AsyncMock(return_value=(payment, mobile_user)),
    )
    monkeypatch.setattr(telegram_routes, "PaymentRepository", _PaymentRepository)
    monkeypatch.setattr(telegram_routes, "SettleCompletedPaymentAttemptUseCase", _Settlement)
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
            telegram_payment_charge_id="tg-stars-charge-2",
            provider_payment_charge_id="provider-charge-2",
        ),
        telegram_bot_secret="telegram-test-secret",
        db=db,
    )

    assert response.payment_id == payment_id
    assert response.status == "completed"
    update_payment.assert_awaited_once_with(payment)
    settlement_execute.assert_awaited_once_with(
        payment_id=payment_id,
        provider="telegram_stars",
        source="telegram_stars_confirm",
    )
    post_payment_execute.assert_not_awaited()
    append_event.assert_not_awaited()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_telegram_stars_order_attempt_missing_does_not_run_legacy_post_payment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    payment_id = uuid4()
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
            "checkout_mode": "order_payment_attempt",
            "order_id": str(uuid4()),
        },
        created_at=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        updated_at=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
    )
    mobile_user = SimpleNamespace(id=user_id)
    db = SimpleNamespace(commit=AsyncMock())
    update_payment = AsyncMock(return_value=payment)
    settlement_execute = AsyncMock(
        return_value=SimpleNamespace(
            status="order_attempt_missing",
            legacy_post_payment_required=False,
        )
    )
    post_payment_execute = AsyncMock()
    append_event = AsyncMock()

    class _PaymentRepository:
        def __init__(self, _db) -> None:
            pass

        async def update(self, updated_payment):
            return await update_payment(updated_payment)

    class _Settlement:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, **kwargs):
            return await settlement_execute(**kwargs)

    class _PostPayment:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, requested_payment_id, *, process_cash_rewards: bool = False):
            return await post_payment_execute(
                requested_payment_id,
                process_cash_rewards=process_cash_rewards,
            )

    class _Outbox:
        def __init__(self, _db) -> None:
            pass

        async def append_event(self, **kwargs):
            return await append_event(**kwargs)

    monkeypatch.setattr(telegram_routes.settings, "telegram_bot_internal_secret", SecretStr("telegram-test-secret"))
    monkeypatch.setattr(
        telegram_routes,
        "_validate_telegram_stars_payment",
        AsyncMock(return_value=(payment, mobile_user)),
    )
    monkeypatch.setattr(telegram_routes, "PaymentRepository", _PaymentRepository)
    monkeypatch.setattr(telegram_routes, "SettleCompletedPaymentAttemptUseCase", _Settlement)
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
            telegram_payment_charge_id="tg-stars-charge-missing-attempt",
            provider_payment_charge_id="provider-charge-missing-attempt",
        ),
        telegram_bot_secret="telegram-test-secret",
        db=db,
    )

    assert response.payment_id == payment_id
    assert response.status == "completed"
    update_payment.assert_awaited_once_with(payment)
    settlement_execute.assert_awaited_once_with(
        payment_id=payment_id,
        provider="telegram_stars",
        source="telegram_stars_confirm",
    )
    post_payment_execute.assert_not_awaited()
    append_event.assert_not_awaited()
    db.commit.assert_awaited_once()
