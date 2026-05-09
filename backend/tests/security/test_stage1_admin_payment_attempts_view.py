"""S1-ADM-005 admin-safe payment attempts view checks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from src.domain.enums import AdminRole, PaymentAttemptStatus
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.models.payment_attempt_model import PaymentAttemptModel
from src.presentation.api.v1.admin.payment_attempts import (
    _require_stage1_payment_attempt_support_viewer,
    _serialize_admin_payment_attempt,
    router,
)
from src.presentation.api.v1.router import API_V1_PREFIX
from src.presentation.dependencies.auth import get_current_active_user


def _admin(role: AdminRole, *, totp_enabled: bool = True) -> AdminUserModel:
    role_slug = role.value.replace("/", "-")
    return AdminUserModel(
        login=f"s1-adm-005-{role_slug}",
        email=f"{role_slug}@example.test",
        role=role.value,
        is_active=True,
        totp_enabled=totp_enabled,
    )


def _order(*, user_id: UUID | None = None) -> OrderModel:
    return OrderModel(
        id=uuid4(),
        checkout_session_id=uuid4(),
        user_id=user_id or uuid4(),
        auth_realm_id=uuid4(),
        storefront_id=uuid4(),
        sale_channel="web",
        currency_code="USD",
        order_status="committed",
        settlement_status="pending_payment",
        base_price=Decimal("10.00"),
        displayed_price=Decimal("10.00"),
        created_at=datetime(2026, 5, 4, 10, 0, tzinfo=UTC),
        updated_at=datetime(2026, 5, 4, 10, 0, tzinfo=UTC),
    )


def _attempt(
    *,
    order_id: UUID,
    status: str = PaymentAttemptStatus.SUCCEEDED.value,
    payment_id: UUID | None = None,
    terminal_at: datetime | None = None,
) -> PaymentAttemptModel:
    return PaymentAttemptModel(
        id=uuid4(),
        order_id=order_id,
        payment_id=payment_id,
        attempt_number=1,
        provider="cryptobot",
        sale_channel="telegram_bot",
        currency_code="USD",
        status=status,
        displayed_amount=Decimal("10.00"),
        wallet_amount=Decimal("2.00"),
        gateway_amount=Decimal("8.00"),
        external_reference="provider-charge-secret-123",
        idempotency_key="raw-idempotency-key-secret",
        provider_snapshot={
            "invoice_id": "invoice-secret-123",
            "payment_url": "https://pay.example.test/raw-token",
            "status": "paid",
            "expires_at": "2026-05-04T11:00:00Z",
            "provider_payment_id": "raw-provider-payment-id",
        },
        request_snapshot={
            "authorization": "Bearer raw-secret",
            "client_ip": "198.51.100.10",
        },
        terminal_at=terminal_at,
        created_at=datetime(2026, 5, 4, 9, 0, tzinfo=UTC),
        updated_at=datetime(2026, 5, 4, 9, 5, tzinfo=UTC),
    )


def test_stage1_support_payment_attempt_view_redacts_provider_and_finance_fields() -> None:
    order = _order()
    attempt = _attempt(order_id=order.id, terminal_at=datetime(2026, 5, 4, 9, 5, tzinfo=UTC))

    response = _serialize_admin_payment_attempt(
        attempt,
        order,
        visibility="support",
        observed_at=datetime(2026, 5, 4, 9, 20, tzinfo=UTC),
    )
    payload = response.model_dump(mode="json")
    serialized = str(payload)

    assert payload["visibility"] == "support"
    assert payload["payment_id"] is None
    assert payload["wallet_amount"] is None
    assert payload["gateway_amount"] is None
    assert payload["provider_status"] == "paid"
    assert payload["external_reference_fingerprint"]
    assert payload["idempotency_key_present"] is True
    assert payload["invoice_present"] is True
    assert payload["review_state"] == "alert_15m"
    assert payload["review_reason"] == "paid_without_canonical_payment"
    assert payload["manual_review_required"] is True

    assert "provider-charge-secret-123" not in serialized
    assert "raw-idempotency-key-secret" not in serialized
    assert "https://pay.example.test/raw-token" not in serialized
    assert "raw-provider-payment-id" not in serialized
    assert "Bearer raw-secret" not in serialized


def test_stage1_finance_payment_attempt_view_keeps_safe_internal_breakdown_only() -> None:
    order = _order()
    payment_id = uuid4()
    attempt = _attempt(order_id=order.id, payment_id=payment_id)

    response = _serialize_admin_payment_attempt(attempt, order, visibility="finance")
    payload = response.model_dump(mode="json")
    serialized = str(payload)

    assert payload["visibility"] == "finance"
    assert payload["payment_id"] == str(payment_id)
    assert payload["wallet_amount"] == 2.0
    assert payload["gateway_amount"] == 8.0
    assert payload["payment_record_present"] is True
    assert payload["manual_review_required"] is False
    assert "raw-idempotency-key-secret" not in serialized
    assert "raw-provider-payment-id" not in serialized
    assert "https://pay.example.test/raw-token" not in serialized


@pytest.mark.asyncio
async def test_stage1_support_payment_attempt_role_gate_is_explicit() -> None:
    gate = _require_stage1_payment_attempt_support_viewer

    assert await gate(_admin(AdminRole.SUPPORT))
    assert await gate(_admin(AdminRole.FINANCE))
    assert await gate(_admin(AdminRole.ADMIN))

    with pytest.raises(HTTPException) as operator_error:
        await gate(_admin(AdminRole.OPERATOR))
    assert operator_error.value.status_code == 403
    assert "support, finance or admin" in str(operator_error.value.detail)

    with pytest.raises(HTTPException) as viewer_error:
        await gate(_admin(AdminRole.VIEWER))
    assert viewer_error.value.status_code == 403


@pytest.mark.asyncio
async def test_stage1_support_payment_attempt_route_hides_raw_payment_attempt_fields(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(router, prefix=API_V1_PREFIX)
    order = _order()
    attempt = _attempt(
        order_id=order.id,
        terminal_at=datetime(2026, 5, 4, 9, 0, tzinfo=UTC) - timedelta(hours=2),
    )

    async def fake_current_user() -> AdminUserModel:
        return _admin(AdminRole.SUPPORT)

    async def fake_list_payment_attempt_rows(*args, **kwargs):  # noqa: ARG001
        return [(attempt, order)]

    app.dependency_overrides[get_current_active_user] = fake_current_user
    monkeypatch.setattr(
        "src.presentation.api.v1.admin.payment_attempts._list_payment_attempt_rows",
        fake_list_payment_attempt_rows,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://admin.cyber-vpn.net") as client:
        response = await client.get(f"{API_V1_PREFIX}/admin/mobile-users/{order.user_id}/payment-attempts")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["visibility"] == "support"
    assert payload["items"][0]["payment_id"] is None
    serialized = str(payload)
    assert "raw-idempotency-key-secret" not in serialized
    assert "raw-provider-payment-id" not in serialized
    assert "https://pay.example.test/raw-token" not in serialized
