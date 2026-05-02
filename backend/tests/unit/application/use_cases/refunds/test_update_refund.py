from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.use_cases.refunds.update_refund import (
    RefundProviderExecutionError,
    UpdateRefundUseCase,
)
from src.domain.enums import PaymentProvider
from src.infrastructure.payments.telegram_stars.client import TelegramStarsRefundError


@pytest.mark.asyncio
async def test_execute_succeeded_telegram_stars_refund_calls_provider_once() -> None:
    refund_id = uuid4()
    order_id = uuid4()
    payment_id = uuid4()
    user_id = uuid4()
    refund = SimpleNamespace(
        id=refund_id,
        order_id=order_id,
        payment_id=payment_id,
        refund_status="requested",
        completed_at=None,
        external_reference=None,
        provider_snapshot={},
        provider=PaymentProvider.TELEGRAM_STARS.value,
        amount=Decimal("15.00"),
        currency_code="XTR",
        reason_code="customer_request",
    )
    order = SimpleNamespace(id=order_id, displayed_price=Decimal("15.00"), settlement_status="paid")
    payment = SimpleNamespace(
        id=payment_id,
        user_uuid=user_id,
        provider=PaymentProvider.TELEGRAM_STARS.value,
        external_id="tg-charge-1",
        metadata_={"provider_payment_charge_id": "provider-charge-1"},
        status="completed",
    )
    mobile_user = SimpleNamespace(id=user_id, telegram_id=123456789)

    session = AsyncMock()
    telegram_stars_client = MagicMock()
    telegram_stars_client.refund_payment = AsyncMock(
        return_value=SimpleNamespace(
            external_reference="tg-charge-1",
            provider_snapshot={
                "provider": "telegram_stars",
                "provider_result": "refunded",
            },
        )
    )
    use_case = UpdateRefundUseCase(session, telegram_stars_client=telegram_stars_client)
    use_case._refunds = MagicMock()
    use_case._refunds.get_by_id = AsyncMock(side_effect=[refund, refund])
    use_case._refunds.sum_for_order_by_statuses = AsyncMock(return_value=Decimal("15.00"))
    use_case._orders = MagicMock()
    use_case._orders.get_by_id = AsyncMock(return_value=order)
    use_case._payments = MagicMock()
    use_case._payments.get_by_id = AsyncMock(return_value=payment)
    use_case._payments.update = AsyncMock(return_value=payment)
    use_case._mobile_users = MagicMock()
    use_case._mobile_users.get_by_id = AsyncMock(return_value=mobile_user)
    use_case._settlement_effects = MagicMock()
    use_case._settlement_effects.execute = AsyncMock()
    use_case._reverse_referral_rewards = MagicMock()
    use_case._reverse_referral_rewards.execute = AsyncMock()
    use_case._outbox = MagicMock()
    use_case._outbox.append_event = AsyncMock()

    updated = await use_case.execute(refund_id=refund_id, refund_status="succeeded")

    telegram_stars_client.refund_payment.assert_awaited_once_with(
        user_id=123456789,
        telegram_payment_charge_id="tg-charge-1",
        provider_payment_charge_id="provider-charge-1",
    )
    use_case._settlement_effects.execute.assert_awaited_once_with(refund_id=refund_id)
    use_case._reverse_referral_rewards.execute.assert_awaited_once_with(
        order_id=order_id,
        reversal_reason="refund_succeeded",
        commit=False,
    )
    use_case._outbox.append_event.assert_awaited_once()
    use_case._payments.update.assert_awaited_once()
    session.commit.assert_awaited_once()
    assert refund.external_reference == "tg-charge-1"
    assert refund.provider_snapshot["provider_result"] == "refunded"
    assert refund.completed_at is not None
    assert payment.status == "refunded"
    assert updated is refund


@pytest.mark.asyncio
async def test_execute_same_succeeded_refund_is_idempotent() -> None:
    refund_id = uuid4()
    order_id = uuid4()
    completed_at = datetime.now(UTC)
    refund = SimpleNamespace(
        id=refund_id,
        order_id=order_id,
        payment_id=None,
        refund_status="succeeded",
        completed_at=completed_at,
        external_reference="existing-ref",
        provider_snapshot={"provider_result": "refunded"},
        provider=None,
        amount=Decimal("5.00"),
        currency_code="USD",
        reason_code="customer_request",
    )
    order = SimpleNamespace(id=order_id, displayed_price=Decimal("10.00"), settlement_status="partially_refunded")

    session = AsyncMock()
    telegram_stars_client = MagicMock()
    telegram_stars_client.refund_payment = AsyncMock()
    use_case = UpdateRefundUseCase(session, telegram_stars_client=telegram_stars_client)
    use_case._refunds = MagicMock()
    use_case._refunds.get_by_id = AsyncMock(side_effect=[refund, refund])
    use_case._refunds.sum_for_order_by_statuses = AsyncMock(return_value=Decimal("5.00"))
    use_case._orders = MagicMock()
    use_case._orders.get_by_id = AsyncMock(return_value=order)
    use_case._payments = MagicMock()
    use_case._payments.get_by_id = AsyncMock(return_value=None)
    use_case._payments.update = AsyncMock()
    use_case._mobile_users = MagicMock()
    use_case._mobile_users.get_by_id = AsyncMock()
    use_case._settlement_effects = MagicMock()
    use_case._settlement_effects.execute = AsyncMock()
    use_case._reverse_referral_rewards = MagicMock()
    use_case._reverse_referral_rewards.execute = AsyncMock()
    use_case._outbox = MagicMock()
    use_case._outbox.append_event = AsyncMock()

    updated = await use_case.execute(refund_id=refund_id, refund_status="succeeded")

    telegram_stars_client.refund_payment.assert_not_awaited()
    use_case._settlement_effects.execute.assert_not_awaited()
    use_case._reverse_referral_rewards.execute.assert_not_awaited()
    use_case._outbox.append_event.assert_not_awaited()
    assert refund.completed_at == completed_at
    assert updated is refund


@pytest.mark.asyncio
async def test_execute_telegram_stars_refund_raises_when_provider_fails() -> None:
    refund_id = uuid4()
    order_id = uuid4()
    payment_id = uuid4()
    user_id = uuid4()
    refund = SimpleNamespace(
        id=refund_id,
        order_id=order_id,
        payment_id=payment_id,
        refund_status="requested",
        completed_at=None,
        external_reference=None,
        provider_snapshot={},
        provider=PaymentProvider.TELEGRAM_STARS.value,
        amount=Decimal("15.00"),
        currency_code="XTR",
        reason_code="customer_request",
    )
    payment = SimpleNamespace(
        id=payment_id,
        user_uuid=user_id,
        provider=PaymentProvider.TELEGRAM_STARS.value,
        external_id="tg-charge-1",
        metadata_={},
        status="completed",
    )
    mobile_user = SimpleNamespace(id=user_id, telegram_id=123456789)

    session = AsyncMock()
    telegram_stars_client = MagicMock()
    telegram_stars_client.refund_payment = AsyncMock(side_effect=TelegramStarsRefundError("provider down"))
    use_case = UpdateRefundUseCase(session, telegram_stars_client=telegram_stars_client)
    use_case._refunds = MagicMock()
    use_case._refunds.get_by_id = AsyncMock(return_value=refund)
    use_case._orders = MagicMock()
    use_case._orders.get_by_id = AsyncMock(return_value=SimpleNamespace(id=order_id, displayed_price=Decimal("15.00")))
    use_case._payments = MagicMock()
    use_case._payments.get_by_id = AsyncMock(return_value=payment)
    use_case._mobile_users = MagicMock()
    use_case._mobile_users.get_by_id = AsyncMock(return_value=mobile_user)
    use_case._settlement_effects = MagicMock()
    use_case._settlement_effects.execute = AsyncMock()
    use_case._reverse_referral_rewards = MagicMock()
    use_case._reverse_referral_rewards.execute = AsyncMock()
    use_case._outbox = MagicMock()
    use_case._outbox.append_event = AsyncMock()

    with pytest.raises(RefundProviderExecutionError, match="provider down"):
        await use_case.execute(refund_id=refund_id, refund_status="succeeded")


@pytest.mark.asyncio
async def test_execute_reconciled_refund_uses_system_actor_without_provider_call() -> None:
    refund_id = uuid4()
    order_id = uuid4()
    payment_id = uuid4()
    refund = SimpleNamespace(
        id=refund_id,
        order_id=order_id,
        payment_id=payment_id,
        refund_status="requested",
        completed_at=None,
        external_reference=None,
        provider_snapshot={},
        provider=PaymentProvider.TELEGRAM_STARS.value,
        amount=Decimal("15.00"),
        currency_code="XTR",
        reason_code="provider_reconciled",
    )
    order = SimpleNamespace(id=order_id, displayed_price=Decimal("15.00"), settlement_status="paid")
    payment = SimpleNamespace(id=payment_id, status="completed")

    session = AsyncMock()
    telegram_stars_client = MagicMock()
    telegram_stars_client.refund_payment = AsyncMock()
    use_case = UpdateRefundUseCase(session, telegram_stars_client=telegram_stars_client)
    use_case._refunds = MagicMock()
    use_case._refunds.get_by_id = AsyncMock(side_effect=[refund, refund])
    use_case._refunds.sum_for_order_by_statuses = AsyncMock(return_value=Decimal("15.00"))
    use_case._orders = MagicMock()
    use_case._orders.get_by_id = AsyncMock(return_value=order)
    use_case._payments = MagicMock()
    use_case._payments.get_by_id = AsyncMock(return_value=payment)
    use_case._payments.update = AsyncMock(return_value=payment)
    use_case._settlement_effects = MagicMock()
    use_case._settlement_effects.execute = AsyncMock()
    use_case._reverse_referral_rewards = MagicMock()
    use_case._reverse_referral_rewards.execute = AsyncMock()
    use_case._outbox = MagicMock()
    use_case._outbox.append_event = AsyncMock()

    updated = await use_case.execute(
        refund_id=refund_id,
        refund_status="succeeded",
        external_reference="tg-charge-1",
        provider_snapshot={"provider_result": "reconciled_from_get_star_transactions"},
        skip_provider_execution=True,
        source_context={"provider_sync": "getStarTransactions"},
    )

    telegram_stars_client.refund_payment.assert_not_awaited()
    use_case._settlement_effects.execute.assert_awaited_once_with(refund_id=refund_id)
    use_case._reverse_referral_rewards.execute.assert_awaited_once()
    use_case._outbox.append_event.assert_awaited_once()
    assert updated is refund
