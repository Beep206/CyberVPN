from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.use_cases.payment_attempts import settle_completed_attempt as settle_module
from src.application.use_cases.payment_attempts.settle_completed_attempt import SettleCompletedPaymentAttemptUseCase
from src.domain.enums import PaymentAttemptStatus


@pytest.mark.asyncio
async def test_completed_order_payment_attempt_finalizes_order_once(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = uuid4()
    payment_id = uuid4()
    attempt_id = uuid4()
    order_id = uuid4()
    payment = SimpleNamespace(
        id=payment_id,
        user_uuid=user_id,
        status="completed",
        provider="cryptobot",
        external_id="invoice-123",
        currency="USD",
        amount=Decimal("20.00"),
        metadata_={},
    )
    attempt = SimpleNamespace(
        id=attempt_id,
        order_id=order_id,
        payment_id=payment_id,
        status=PaymentAttemptStatus.PENDING.value,
        terminal_at=None,
        external_reference="invoice-123",
    )
    order = SimpleNamespace(
        id=order_id,
        user_id=user_id,
        settlement_status="pending_payment",
        gateway_amount=Decimal("20.00"),
        wallet_amount=Decimal("0"),
        displayed_price=Decimal("20.00"),
        discount_amount=Decimal("0"),
        currency_code="USD",
        pricing_snapshot={"quote": {"gateway_amount": "20.00", "duration_days": 30}},
    )
    finalize_execute = AsyncMock(return_value=[])

    class _PaymentRepository:
        def __init__(self, _session) -> None:
            pass

        async def get_by_id_for_update(self, requested_payment_id):
            assert requested_payment_id == payment_id
            return payment

    class _PaymentAttemptRepository:
        def __init__(self, _session) -> None:
            pass

        async def get_by_payment_id_for_update(self, requested_payment_id):
            assert requested_payment_id == payment_id
            return attempt

    class _OrderRepository:
        def __init__(self, _session) -> None:
            pass

        async def get_by_id_for_update(self, requested_order_id):
            assert requested_order_id == order_id
            return order

    class _Finalizer:
        def __init__(self, _session) -> None:
            pass

        async def execute(self, **kwargs):
            return await finalize_execute(**kwargs)

    monkeypatch.setattr(settle_module, "PaymentRepository", _PaymentRepository)
    monkeypatch.setattr(settle_module, "PaymentAttemptRepository", _PaymentAttemptRepository)
    monkeypatch.setattr(settle_module, "OrderRepository", _OrderRepository)
    monkeypatch.setattr(settle_module, "FinalizeCompletedPaymentUseCase", _Finalizer)

    session = SimpleNamespace(flush=AsyncMock())
    result = await SettleCompletedPaymentAttemptUseCase(session).execute(
        payment_id=payment_id,
        external_reference="invoice-123",
        provider="cryptobot",
        source="payment_webhook",
    )

    assert result.status == "finalized"
    assert result.payment_id == payment_id
    assert result.payment_attempt_id == attempt_id
    assert result.order_id == order_id
    assert attempt.status == PaymentAttemptStatus.SUCCEEDED.value
    assert attempt.terminal_at is not None
    finalize_execute.assert_awaited_once()
    kwargs = finalize_execute.await_args.kwargs
    assert kwargs["order"] is order
    assert kwargs["payment"] is payment
    assert kwargs["payment_attempt"] is attempt
    assert kwargs["quote_snapshot"]["gateway_amount"] == "20.00"
    assert kwargs["source"] == "payment_webhook"


@pytest.mark.asyncio
async def test_completed_non_order_payment_records_safe_unlinked_event_and_legacy_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    payment_id = uuid4()
    append_event = AsyncMock(return_value=SimpleNamespace(id=uuid4()))
    payment = SimpleNamespace(
        id=payment_id,
        user_uuid=user_id,
        status="completed",
        provider="cryptobot",
        external_id="raw-invoice-id",
        metadata_={},
    )

    class _PaymentRepository:
        def __init__(self, _session) -> None:
            pass

        async def get_by_id_for_update(self, requested_payment_id):
            assert requested_payment_id == payment_id
            return payment

    class _PaymentAttemptRepository:
        def __init__(self, _session) -> None:
            pass

        async def get_by_payment_id_for_update(self, requested_payment_id):
            assert requested_payment_id == payment_id
            return None

    class _Outbox:
        def __init__(self, _session) -> None:
            pass

        async def append_event(self, **kwargs):
            return await append_event(**kwargs)

    monkeypatch.setattr(settle_module, "PaymentRepository", _PaymentRepository)
    monkeypatch.setattr(settle_module, "PaymentAttemptRepository", _PaymentAttemptRepository)
    monkeypatch.setattr(settle_module, "EventOutboxService", _Outbox)

    result = await SettleCompletedPaymentAttemptUseCase(SimpleNamespace(flush=AsyncMock())).execute(
        payment_id=payment_id,
        external_reference="raw-invoice-id",
        provider="cryptobot",
        source="payment_webhook",
    )

    assert result.status == "legacy_non_order"
    assert result.legacy_post_payment_required is True
    append_event.assert_awaited_once()
    kwargs = append_event.await_args.kwargs
    assert kwargs["event_name"] == "payment.settlement.unlinked"
    assert kwargs["event_key"] == f"payment.settlement.unlinked:{payment_id}:payment_attempt_not_found"
    assert kwargs["event_payload"]["payment_id"] == str(payment_id)
    assert kwargs["event_payload"]["reason"] == "payment_attempt_not_found"
    assert kwargs["event_payload"]["external_reference_fingerprint"]
    assert "raw-invoice-id" not in str(kwargs)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "metadata",
    (
        {"checkout_mode": "order_payment_attempt", "order_id": "8e07f951-0fb2-47bc-a92c-6c1e8d7fb18f"},
        {"checkout_mode": "zero_gateway_order_payment_attempt"},
        {"order_id": "8e07f951-0fb2-47bc-a92c-6c1e8d7fb18f"},
    ),
)
async def test_completed_order_payment_with_missing_attempt_is_not_legacy(
    monkeypatch: pytest.MonkeyPatch,
    metadata: dict[str, str],
) -> None:
    user_id = uuid4()
    payment_id = uuid4()
    append_event = AsyncMock(return_value=SimpleNamespace(id=uuid4()))
    payment = SimpleNamespace(
        id=payment_id,
        user_uuid=user_id,
        status="completed",
        provider="cryptobot",
        external_id="order-invoice-id",
        metadata_=metadata,
    )

    class _PaymentRepository:
        def __init__(self, _session) -> None:
            pass

        async def get_by_id_for_update(self, requested_payment_id):
            assert requested_payment_id == payment_id
            return payment

    class _PaymentAttemptRepository:
        def __init__(self, _session) -> None:
            pass

        async def get_by_payment_id_for_update(self, requested_payment_id):
            assert requested_payment_id == payment_id
            return None

    class _Outbox:
        def __init__(self, _session) -> None:
            pass

        async def append_event(self, **kwargs):
            return await append_event(**kwargs)

    monkeypatch.setattr(settle_module, "PaymentRepository", _PaymentRepository)
    monkeypatch.setattr(settle_module, "PaymentAttemptRepository", _PaymentAttemptRepository)
    monkeypatch.setattr(settle_module, "EventOutboxService", _Outbox)

    result = await SettleCompletedPaymentAttemptUseCase(SimpleNamespace(flush=AsyncMock())).execute(
        payment_id=payment_id,
        external_reference="order-invoice-id",
        provider="cryptobot",
        source="payment_webhook",
    )

    assert result.status == "order_attempt_missing"
    assert result.legacy_post_payment_required is False
    assert result.payment_attempt_id is None
    assert result.reason == "order_payment_attempt_not_found"
    append_event.assert_awaited_once()
    kwargs = append_event.await_args.kwargs
    assert kwargs["event_name"] == "payment.settlement.unlinked"
    assert kwargs["event_key"] == f"payment.settlement.unlinked:{payment_id}:order_payment_attempt_not_found"
    assert kwargs["event_payload"]["payment_id"] == str(payment_id)
    assert kwargs["event_payload"]["reason"] == "order_payment_attempt_not_found"
    assert "order-invoice-id" not in str(kwargs)


@pytest.mark.asyncio
async def test_completed_attempt_rejects_cross_user_order(monkeypatch: pytest.MonkeyPatch) -> None:
    payment_id = uuid4()
    order_id = uuid4()
    payment = SimpleNamespace(
        id=payment_id,
        user_uuid=uuid4(),
        status="completed",
        provider="cryptobot",
        external_id="invoice-123",
    )
    attempt = SimpleNamespace(
        id=uuid4(),
        order_id=order_id,
        payment_id=payment_id,
        status=PaymentAttemptStatus.PENDING.value,
        terminal_at=None,
        external_reference="invoice-123",
    )
    order = SimpleNamespace(
        id=order_id,
        user_id=uuid4(),
        settlement_status="pending_payment",
    )
    finalize_execute = AsyncMock(return_value=[])

    class _PaymentRepository:
        def __init__(self, _session) -> None:
            pass

        async def get_by_id_for_update(self, _payment_id):
            return payment

    class _PaymentAttemptRepository:
        def __init__(self, _session) -> None:
            pass

        async def get_by_payment_id_for_update(self, _payment_id):
            return attempt

    class _OrderRepository:
        def __init__(self, _session) -> None:
            pass

        async def get_by_id_for_update(self, _order_id):
            return order

    class _Finalizer:
        def __init__(self, _session) -> None:
            pass

        async def execute(self, **kwargs):
            return await finalize_execute(**kwargs)

    monkeypatch.setattr(settle_module, "PaymentRepository", _PaymentRepository)
    monkeypatch.setattr(settle_module, "PaymentAttemptRepository", _PaymentAttemptRepository)
    monkeypatch.setattr(settle_module, "OrderRepository", _OrderRepository)
    monkeypatch.setattr(settle_module, "FinalizeCompletedPaymentUseCase", _Finalizer)

    with pytest.raises(ValueError, match="Payment user does not belong to order"):
        await SettleCompletedPaymentAttemptUseCase(SimpleNamespace(flush=AsyncMock())).execute(
            payment_id=payment_id,
            provider="cryptobot",
            source="payment_webhook",
        )

    assert attempt.status == PaymentAttemptStatus.PENDING.value
    finalize_execute.assert_not_awaited()
