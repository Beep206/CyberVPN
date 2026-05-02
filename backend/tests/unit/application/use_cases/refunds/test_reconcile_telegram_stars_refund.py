from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.use_cases.refunds.reconcile_telegram_stars_refund import (
    ReconcileTelegramStarsRefundUseCase,
)
from src.domain.enums import PaymentProvider


@pytest.mark.asyncio
async def test_reconcile_creates_and_marks_refund_succeeded() -> None:
    order_id = uuid4()
    payment_id = uuid4()
    payment_attempt_id = uuid4()
    user_id = uuid4()
    payment = SimpleNamespace(
        id=payment_id,
        provider=PaymentProvider.TELEGRAM_STARS.value,
        user_uuid=user_id,
        currency="XTR",
        amount=Decimal("250.00"),
    )
    mobile_user = SimpleNamespace(id=user_id, telegram_id=123456789)
    payment_attempt = SimpleNamespace(id=payment_attempt_id, order_id=order_id)
    order = SimpleNamespace(id=order_id)
    created_refund = SimpleNamespace(
        id=uuid4(),
        order_id=order_id,
        payment_id=payment_id,
        refund_status="requested",
        external_reference="tg-charge-1",
    )
    updated_refund = SimpleNamespace(
        id=created_refund.id,
        refund_status="succeeded",
    )

    session = AsyncMock()
    use_case = ReconcileTelegramStarsRefundUseCase(session)
    use_case._payments = MagicMock()
    use_case._payments.get_telegram_stars_by_charge_id = AsyncMock(return_value=payment)
    use_case._mobile_users = MagicMock()
    use_case._mobile_users.get_by_id = AsyncMock(return_value=mobile_user)
    use_case._payment_attempts = MagicMock()
    use_case._payment_attempts.get_by_payment_id = AsyncMock(return_value=payment_attempt)
    use_case._orders = MagicMock()
    use_case._orders.get_by_id = AsyncMock(return_value=order)
    use_case._refunds = MagicMock()
    use_case._refunds.list_for_order = AsyncMock(return_value=[])
    use_case._refunds.get_by_order_and_idempotency_key = AsyncMock(return_value=None)
    use_case._refunds.create = AsyncMock(return_value=created_refund)
    use_case._update_refund = MagicMock()
    use_case._update_refund.execute = AsyncMock(return_value=updated_refund)

    result = await use_case.execute(
        telegram_id=123456789,
        telegram_payment_charge_id="tg-charge-1",
        amount=250,
        transaction_id="tg-charge-1",
        refunded_at=datetime.now(UTC),
        invoice_payload="stars:payment:user",
        raw_transaction={"id": "tg-charge-1"},
    )

    use_case._refunds.create.assert_awaited_once()
    use_case._update_refund.execute.assert_awaited_once()
    assert result.action == "created_and_reconciled"
    assert result.payment_id == payment_id
    assert result.refund_id == created_refund.id
    assert result.refund_status == "succeeded"
    assert result.already_reconciled is False


@pytest.mark.asyncio
async def test_reconcile_returns_payment_not_found_when_charge_missing() -> None:
    session = AsyncMock()
    use_case = ReconcileTelegramStarsRefundUseCase(session)
    use_case._payments = MagicMock()
    use_case._payments.get_telegram_stars_by_charge_id = AsyncMock(return_value=None)

    result = await use_case.execute(
        telegram_id=123456789,
        telegram_payment_charge_id="missing-charge",
        amount=250,
        transaction_id="missing-charge",
    )

    assert result.action == "payment_not_found"
    assert result.payment_id is None
    assert result.refund_id is None
