from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.use_cases.payment_attempts import create_payment_attempt as create_attempt_module
from src.application.use_cases.payment_attempts.create_payment_attempt import CreatePaymentAttemptUseCase
from src.domain.enums import PaymentAttemptStatus


@pytest.mark.asyncio
async def test_completed_order_payment_attempt_publishes_payment_completed_after_attempt_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    realm_id = uuid4()
    order_id = uuid4()
    checkout_session_id = uuid4()
    payment_id = uuid4()
    attempt_id = uuid4()
    payment = SimpleNamespace(
        id=payment_id,
        user_uuid=user_id,
        status="completed",
        provider="wallet",
        currency="USD",
        amount=Decimal("75.00"),
        external_id=None,
        metadata_={"order_id": str(order_id)},
    )
    order = SimpleNamespace(
        id=order_id,
        user_id=user_id,
        auth_realm_id=realm_id,
        settlement_status="pending_payment",
        checkout_session_id=checkout_session_id,
        subscription_plan_id=uuid4(),
        sale_channel="web",
        currency_code="USD",
        displayed_price=Decimal("75.00"),
        wallet_amount=Decimal("0"),
        gateway_amount=Decimal("75.00"),
        pricing_snapshot={"quote": {"plan_name": "Wallet Plan", "duration_days": 30}},
    )
    created_attempt = SimpleNamespace(
        id=attempt_id,
        order_id=order_id,
        payment_id=payment_id,
        status=PaymentAttemptStatus.SUCCEEDED.value,
    )
    quote_result = SimpleNamespace(duration_days=30)
    append_event = AsyncMock(return_value=SimpleNamespace(id=uuid4()))

    class _CommitCheckout:
        def __init__(self, _session, _crypto_client) -> None:
            pass

        async def execute(self, **kwargs):
            assert kwargs["publish_completed_payment_event"] is False
            return SimpleNamespace(payment=payment, status="completed", invoice=None)

    monkeypatch.setattr(
        create_attempt_module,
        "build_checkout_result_from_order",
        lambda _order: quote_result,
    )
    monkeypatch.setattr(create_attempt_module, "CommitCheckoutUseCase", _CommitCheckout)

    use_case = CreatePaymentAttemptUseCase.__new__(CreatePaymentAttemptUseCase)
    use_case._session = SimpleNamespace(commit=AsyncMock())
    use_case._crypto_client = object()
    use_case._orders = SimpleNamespace(get_by_id=AsyncMock(return_value=order))
    use_case._attempts = SimpleNamespace(
        get_by_order_and_idempotency_key=AsyncMock(return_value=None),
        get_active_for_order=AsyncMock(return_value=None),
        get_latest_for_order=AsyncMock(return_value=None),
        create=AsyncMock(return_value=created_attempt),
        get_by_id=AsyncMock(return_value=created_attempt),
    )
    use_case._outbox = SimpleNamespace(append_event=append_event)

    result = await use_case.execute(
        order_id=order_id,
        user_id=user_id,
        current_realm=SimpleNamespace(realm_id=str(realm_id)),
        idempotency_key="zero-gateway-order-attempt",
    )

    assert result.payment_attempt is created_attempt
    assert result.created is True
    assert order.settlement_status == "paid"
    append_event.assert_awaited_once()
    append_kwargs = append_event.await_args.kwargs
    assert append_kwargs["event_name"] == "payment.completed"
    assert append_kwargs["event_key"] == f"payment.completed:{payment_id}"
    assert append_kwargs["event_payload"]["payment_id"] == str(payment_id)
    assert append_kwargs["event_payload"]["payment_attempt_id"] == str(attempt_id)
    assert append_kwargs["event_payload"]["order_id"] == str(order_id)
    assert append_kwargs["source_context"]["source"] == "zero_gateway_order_payment_attempt"
    use_case._session.commit.assert_awaited_once()
