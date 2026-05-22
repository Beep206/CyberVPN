"""S2-STAGE-06 payment production hardening checks."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import pytest

from src.application.use_cases.payments.payment_webhook import ProcessPaymentWebhookUseCase
from src.infrastructure.payments.cryptobot.webhook_handler import CryptoBotWebhookHandler
from tests.helpers.realm_auth import FakeRedis


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, instance: Any) -> None:
        self.added.append(instance)


class _MarkSpyCryptoBotWebhookHandler(CryptoBotWebhookHandler):
    def __init__(self, api_token: str) -> None:
        super().__init__(api_token)
        self.marked: list[str] = []

    async def mark_invoice_processed(self, invoice_id: str) -> None:
        self.marked.append(invoice_id)


def _signed_body(token: str, payload: dict[str, Any]) -> tuple[bytes, str]:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    secret = hashlib.sha256(token.encode("utf-8")).digest()
    signature = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return body, signature


@pytest.mark.asyncio
async def test_s2_cryptobot_webhook_rejects_invalid_invoice_id_before_side_effects() -> None:
    token = "test-webhook-token"
    body, signature = _signed_body(
        token,
        {
            "update_type": "invoice_paid",
            "payload": {"invoice_id": "bad-invoice-id"},
        },
    )
    session = _FakeSession()
    use_case = ProcessPaymentWebhookUseCase(  # type: ignore[arg-type]
        session=session,
        webhook_handler=CryptoBotWebhookHandler(token),
    )

    result = await use_case.execute(provider="cryptobot", body=body, signature=signature)

    assert result == {
        "status": "invalid_payment",
        "invoice_id": "bad-invoice-id",
        "reason": "Invalid invoice ID format",
    }
    assert len(session.added) == 1
    assert session.added[0].is_valid is True


@pytest.mark.asyncio
async def test_s2_cryptobot_webhook_duplicate_invoice_returns_without_side_effects() -> None:
    token = "test-webhook-token"
    redis_client = FakeRedis()
    handler = CryptoBotWebhookHandler(token, redis_client=redis_client)  # type: ignore[arg-type]
    await handler.mark_invoice_processed("123456789")

    body, signature = _signed_body(
        token,
        {
            "update_type": "invoice_paid",
            "payload": {"invoice_id": "123456789"},
        },
    )
    use_case = ProcessPaymentWebhookUseCase(  # type: ignore[arg-type]
        session=_FakeSession(),
        webhook_handler=handler,
    )

    result = await use_case.execute(provider="cryptobot", body=body, signature=signature)

    assert result == {"status": "already_processed", "invoice_id": "123456789"}


@pytest.mark.asyncio
async def test_s2_payment_not_found_warning_does_not_close_orphan_invoice_idempotency() -> None:
    handler = _MarkSpyCryptoBotWebhookHandler("test-webhook-token")
    use_case = ProcessPaymentWebhookUseCase(  # type: ignore[arg-type]
        session=_FakeSession(),
        webhook_handler=handler,
    )

    await use_case._mark_invoice_paid_processed_after_result(
        "123456789",
        {"status": "processed", "warning": "payment_not_found"},
    )
    await use_case._mark_invoice_paid_processed_after_result("987654321", {"status": "processed"})

    assert handler.marked == ["987654321"]
