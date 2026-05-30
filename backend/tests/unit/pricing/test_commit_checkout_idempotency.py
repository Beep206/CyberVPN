from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.use_cases.payments.commit_checkout import (
    CheckoutIdempotencyConflictError,
    CommitCheckoutUseCase,
)
from src.infrastructure.database.models.payment_model import PaymentModel


class _Session:
    def get_bind(self):
        return None


def _quote(**overrides):
    base = {
        "base_price": Decimal("10.00"),
        "addon_amount": Decimal("0"),
        "displayed_price": Decimal("10.00"),
        "discount_amount": Decimal("0"),
        "wallet_amount": Decimal("0"),
        "gateway_amount": Decimal("10.00"),
        "partner_markup": Decimal("0"),
        "is_zero_gateway": False,
        "plan_id": uuid4(),
        "promo_code_id": None,
        "partner_code_id": None,
        "plan_name": "basic_30d",
        "duration_days": 30,
        "addons": [],
        "entitlements_snapshot": {},
        "commission_base_amount": Decimal("10.00"),
        "code_resolution": None,
        "reservation_id": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_commit_checkout_reuses_payment_for_same_idempotency_key() -> None:
    session = _Session()
    crypto_client = SimpleNamespace(
        create_invoice=AsyncMock(
            return_value={
                "invoice_id": "inv_idem_1",
                "pay_url": "https://pay.example.test/inv_idem_1",
                "status": "pending",
                "expiration_date": datetime.now(UTC).isoformat(),
            }
        )
    )
    use_case = CommitCheckoutUseCase(session, crypto_client)
    use_case._payments = SimpleNamespace(
        get_by_checkout_idempotency_key=AsyncMock(return_value=None),
        create=AsyncMock(side_effect=lambda model: model),
    )

    first = await use_case.execute(
        user_id=uuid4(),
        quote_result=_quote(),
        currency="USD",
        channel="web",
        description="CyberVPN basic",
        payload="payload-1",
        idempotency_key="retry-key-1",
    )
    use_case._payments.get_by_checkout_idempotency_key.return_value = first.payment

    second = await use_case.execute(
        user_id=first.payment.user_uuid,
        quote_result=_quote(plan_id=first.payment.plan_id),
        currency="USD",
        channel="web",
        description="CyberVPN basic",
        payload="payload-1",
        idempotency_key="retry-key-1",
    )

    assert second.payment.id == first.payment.id
    assert second.invoice is not None
    assert second.invoice.invoice_id == "inv_idem_1"
    assert crypto_client.create_invoice.await_count == 1
    assert use_case._payments.create.await_count == 1


@pytest.mark.asyncio
async def test_commit_checkout_rejects_idempotency_key_with_different_payload() -> None:
    session = _Session()
    crypto_client = SimpleNamespace(create_invoice=AsyncMock())
    use_case = CommitCheckoutUseCase(session, crypto_client)
    existing = PaymentModel(
        user_uuid=uuid4(),
        amount=10,
        currency="USD",
        status="pending",
        provider="cryptobot",
        subscription_days=30,
        metadata_={
            "checkout_mode": "new_purchase",
            "checkout_idempotency_key": "retry-key-2",
            "checkout_fingerprint": "different",
        },
    )
    use_case._payments = SimpleNamespace(
        get_by_checkout_idempotency_key=AsyncMock(return_value=existing),
        create=AsyncMock(),
    )

    with pytest.raises(CheckoutIdempotencyConflictError):
        await use_case.execute(
            user_id=existing.user_uuid,
            quote_result=_quote(),
            currency="USD",
            channel="web",
            description="CyberVPN basic",
            payload="payload-2",
            idempotency_key="retry-key-2",
        )

    crypto_client.create_invoice.assert_not_awaited()
    use_case._payments.create.assert_not_awaited()
