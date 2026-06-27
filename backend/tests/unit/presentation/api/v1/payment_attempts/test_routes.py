from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.application.use_cases.auth_realms import RealmResolution
from src.presentation.api.v1.payment_attempts import routes


def _realm(realm_id):
    return RealmResolution(auth_realm=SimpleNamespace(id=realm_id), source="test")


def _order(*, user_id, auth_realm_id):
    return SimpleNamespace(id=uuid4(), user_id=user_id, auth_realm_id=auth_realm_id)


def _attempt(**overrides):
    base = {
        "id": uuid4(),
        "order_id": uuid4(),
        "payment_id": uuid4(),
        "supersedes_attempt_id": None,
        "attempt_number": 1,
        "provider": "internal_zero",
        "sale_channel": "web",
        "currency_code": "USD",
        "status": "succeeded",
        "displayed_amount": 0,
        "wallet_amount": 0,
        "gateway_amount": 0,
        "external_reference": f"internal_zero:{uuid4()}",
        "idempotency_key": "raw-customer-idempotency-key",
        "provider_snapshot": {
            "invoice_id": "inv-private",
            "payment_url": "https://pay.example.test/private",
            "status": "pending",
            "amount": 10,
            "currency": "USD",
            "expires_at": datetime.now(UTC) + timedelta(minutes=15),
            "internal_order_id": str(uuid4()),
        },
        "request_snapshot": {"checkout_session_id": str(uuid4()), "private_context": "secret"},
        "terminal_at": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_customer_payment_attempt_read_serializer_redacts_sensitive_fields() -> None:
    response = routes._serialize_payment_attempt(_attempt())
    payload = response.model_dump()

    assert payload["external_reference"] is None
    assert payload["idempotency_key"].startswith("sha256:")
    assert "raw-customer-idempotency-key" not in str(payload)
    assert "payment_url" not in payload["provider_snapshot"]
    assert "internal_order_id" not in payload["provider_snapshot"]
    assert payload["request_snapshot"] == {}
    assert payload["invoice"] is not None
    assert payload["invoice"]["payment_url"] == ""
    assert "https://pay.example.test/private" not in str(payload)


@pytest.mark.asyncio
async def test_customer_payment_attempt_list_denies_cross_realm_order(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = uuid4()
    request_realm_id = uuid4()
    order_realm_id = uuid4()

    monkeypatch.setattr(
        routes,
        "GetOrderUseCase",
        lambda _db: SimpleNamespace(
            execute=AsyncMock(return_value=_order(user_id=user_id, auth_realm_id=order_realm_id))
        ),
    )
    monkeypatch.setattr(
        routes,
        "ListPaymentAttemptsUseCase",
        lambda _db: SimpleNamespace(execute=AsyncMock(return_value=[_attempt()])),
    )

    with pytest.raises(HTTPException) as exc_info:
        await routes.list_payment_attempts(
            order_id=uuid4(),
            db=object(),
            user_id=user_id,
            current_realm=_realm(request_realm_id),
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_customer_payment_attempt_detail_denies_cross_realm_order(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = uuid4()
    request_realm_id = uuid4()
    order_realm_id = uuid4()
    attempt = _attempt()

    monkeypatch.setattr(
        routes,
        "GetPaymentAttemptUseCase",
        lambda _db: SimpleNamespace(execute=AsyncMock(return_value=attempt)),
    )
    monkeypatch.setattr(
        routes,
        "GetOrderUseCase",
        lambda _db: SimpleNamespace(
            execute=AsyncMock(return_value=_order(user_id=user_id, auth_realm_id=order_realm_id))
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        await routes.get_payment_attempt(
            payment_attempt_id=attempt.id,
            db=object(),
            user_id=user_id,
            current_realm=_realm(request_realm_id),
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_customer_payment_attempt_list_allows_same_realm_and_redacts(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = uuid4()
    realm_id = uuid4()
    attempt = _attempt()

    monkeypatch.setattr(
        routes,
        "GetOrderUseCase",
        lambda _db: SimpleNamespace(execute=AsyncMock(return_value=_order(user_id=user_id, auth_realm_id=realm_id))),
    )
    monkeypatch.setattr(
        routes,
        "ListPaymentAttemptsUseCase",
        lambda _db: SimpleNamespace(execute=AsyncMock(return_value=[attempt])),
    )

    response = await routes.list_payment_attempts(
        order_id=attempt.order_id,
        db=object(),
        user_id=user_id,
        current_realm=_realm(realm_id),
    )

    assert len(response) == 1
    payload = response[0].model_dump()
    assert payload["idempotency_key"].startswith("sha256:")
    assert payload["request_snapshot"] == {}
    assert "payment_url" not in payload["provider_snapshot"]
