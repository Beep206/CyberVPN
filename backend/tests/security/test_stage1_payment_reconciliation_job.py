"""S1-PAY-012 payment reconciliation job checks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.application.use_cases.payments.stage1_reconciliation import (
    REPORT_VERSION,
    build_stage1_payment_reconciliation_report,
    reconcile_stage1_payment_attempt_snapshot,
    reconcile_stage1_payment_without_attempt,
)
from src.presentation.api.v1.payments import routes as payment_routes

NOW = datetime(2026, 5, 5, 12, 0, tzinfo=UTC)


def _attempt(**overrides: Any) -> SimpleNamespace:
    values = {
        "id": uuid4(),
        "order_id": uuid4(),
        "payment_id": None,
        "provider": "cryptobot",
        "status": "pending",
        "external_reference": "raw-provider-attempt-reference",
        "idempotency_key": "raw-idempotency-key",
        "provider_snapshot": {"payment_url": "https://provider.example/pay/raw"},
        "request_snapshot": {"raw": True},
        "created_at": NOW - timedelta(minutes=5),
        "updated_at": NOW - timedelta(minutes=5),
        "terminal_at": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _order(**overrides: Any) -> SimpleNamespace:
    values = {
        "id": uuid4(),
        "user_id": uuid4(),
        "order_status": "committed",
        "settlement_status": "pending_payment",
        "created_at": NOW - timedelta(minutes=5),
        "updated_at": NOW - timedelta(minutes=5),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _payment(**overrides: Any) -> SimpleNamespace:
    values = {
        "id": uuid4(),
        "user_uuid": uuid4(),
        "external_id": "raw-provider-payment-id",
        "provider": "cryptobot",
        "status": "completed",
        "created_at": NOW - timedelta(minutes=5),
        "updated_at": NOW - timedelta(minutes=5),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_stage1_reconciliation_detects_stale_active_attempt() -> None:
    items = reconcile_stage1_payment_attempt_snapshot(
        attempt=_attempt(status="processing", updated_at=NOW - timedelta(minutes=65)),
        order=_order(),
        payment=None,
        observed_at=NOW,
    )

    assert [item.code.value for item in items] == ["stale_active_attempt"]
    assert items[0].severity.value == "p1_escalation"
    assert "reconcile_provider_dashboard" in items[0].actions


def test_stage1_reconciliation_detects_succeeded_attempt_without_payment_and_redacts_ids() -> None:
    items = reconcile_stage1_payment_attempt_snapshot(
        attempt=_attempt(
            status="succeeded",
            terminal_at=NOW - timedelta(hours=25),
            updated_at=NOW - timedelta(hours=25),
        ),
        order=_order(),
        payment=None,
        observed_at=NOW,
    )

    payload = items[0].to_api_dict()
    serialized = str(payload)
    assert payload["code"] == "succeeded_attempt_without_payment"
    assert payload["severity"] == "p0_blocker"
    assert payload["launch_blocker"] is True
    assert payload["safe_reference"].startswith("s1:payment-review:")
    assert "raw-provider-attempt-reference" not in serialized
    assert "raw-idempotency-key" not in serialized
    assert "provider.example" not in serialized


def test_stage1_reconciliation_detects_linked_status_and_settlement_mismatches() -> None:
    user_id = uuid4()
    attempt = _attempt(status="succeeded", payment_id=uuid4(), terminal_at=NOW - timedelta(minutes=20))
    order = _order(user_id=user_id, settlement_status="pending_payment")
    payment = _payment(user_uuid=user_id, status="completed", updated_at=NOW - timedelta(minutes=20))

    items = reconcile_stage1_payment_attempt_snapshot(
        attempt=attempt,
        order=order,
        payment=payment,
        observed_at=NOW,
    )

    assert [item.code.value for item in items] == ["order_settlement_mismatch"]
    assert items[0].severity.value == "alert_15m"
    assert "run_post_payment_processing_or_repair" in items[0].actions


def test_stage1_reconciliation_detects_completed_payment_without_attempt() -> None:
    items = reconcile_stage1_payment_without_attempt(
        payment=_payment(updated_at=NOW - timedelta(minutes=30)),
        observed_at=NOW,
    )

    payload = items[0].to_api_dict()
    serialized = str(payload)
    assert payload["code"] == "canonical_payment_without_attempt"
    assert payload["payment_state"] == "orphan_review_required"
    assert "raw-provider-payment-id" not in serialized


def test_stage1_reconciliation_handles_unknown_provider_without_crashing() -> None:
    items = reconcile_stage1_payment_without_attempt(
        payment=_payment(provider="wallet", updated_at=NOW - timedelta(minutes=30)),
        observed_at=NOW,
    )

    payload = items[0].to_api_dict()
    assert payload["provider"] == "wallet"
    assert payload["payment_state"] == "orphan_review_required"
    assert "do_not_create_account_silently" in payload["actions"]


def test_stage1_reconciliation_report_summary_is_actionable() -> None:
    item = reconcile_stage1_payment_without_attempt(
        payment=_payment(updated_at=NOW - timedelta(hours=25)),
        observed_at=NOW,
    )[0]

    report = build_stage1_payment_reconciliation_report(
        items=[item],
        inspected_attempts=2,
        inspected_payments_without_attempt=1,
        generated_at=NOW,
    )
    body = report.to_api_dict()

    assert body["report_version"] == REPORT_VERSION
    assert body["summary"]["total_items"] == 1
    assert body["summary"]["p0_blocker_items"] == 1
    assert body["summary"]["launch_blocked"] is True
    assert body["summary"]["mismatch_counts"] == {"canonical_payment_without_attempt": 1}


@pytest.mark.asyncio
async def test_stage1_reconciliation_internal_route_returns_safe_report(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(payment_routes.router, prefix="/api/v1")

    async def fake_db():
        yield object()

    class FakeUseCase:
        def __init__(self, _db: object) -> None:
            pass

        async def execute(self, *, limit: int = 250) -> Any:
            item = reconcile_stage1_payment_attempt_snapshot(
                attempt=_attempt(status="processing", updated_at=NOW - timedelta(minutes=20)),
                order=_order(),
                payment=None,
                observed_at=NOW,
            )[0]
            return build_stage1_payment_reconciliation_report(
                items=[item],
                inspected_attempts=1,
                inspected_payments_without_attempt=0,
                generated_at=NOW,
            )

    app.dependency_overrides[payment_routes.get_db] = fake_db
    monkeypatch.setattr(payment_routes, "_require_telegram_bot_secret", lambda _secret: None)
    monkeypatch.setattr(payment_routes, "Stage1PaymentReconciliationUseCase", FakeUseCase)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://backend") as client:
        response = await client.post(
            "/api/v1/payments/internal/reconciliation/run",
            params={"limit": 10},
            headers={"X-Telegram-Bot-Secret": "test-secret"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total_items"] == 1
    assert body["items"][0]["safe_reference"].startswith("s1:payment-reconciliation:")
    assert "raw-provider" not in str(body)
