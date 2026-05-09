"""S1-PAY-005 payment webhook signature verification checks."""

from __future__ import annotations

import hashlib
import hmac
import json
from collections import Counter
from typing import Any

import pytest
from fastapi import FastAPI, HTTPException, Request, status
from httpx import ASGITransport, AsyncClient

from src.presentation.api.shared import Stage1WebhookSignatureStatus, verify_stage1_webhook_signature
from src.presentation.api.shared.stage1_payment_mapping import Stage1PaymentProvider
from src.presentation.api.shared.stage1_webhook_idempotency import (
    Stage1InMemoryWebhookIdempotencyGuard,
    extract_stage1_webhook_identity,
)


def _cryptobot_signature(token: str, body: bytes) -> str:
    hmac_secret = hashlib.sha256(token.encode("utf-8")).digest()
    return hmac.new(hmac_secret, body, hashlib.sha256).hexdigest()


def _nowpayments_signature(secret: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps(_sort_json(payload), ensure_ascii=False, separators=(",", ":"))
    return hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha512).hexdigest()


def _digiseller_signature(secret: str, payload: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "signature"}
    material = "".join(f"{key}:{unsigned[key]};" for key in sorted(unsigned))
    return hmac.new(secret.encode("utf-8"), material.encode("utf-8"), hashlib.sha256).hexdigest()


def _sort_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sort_json(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_sort_json(item) for item in value]
    return value


def test_stage1_cryptobot_signature_accepts_official_hmac_contract() -> None:
    token = "test-cryptobot-token"
    body = b'{"update_id":777,"update_type":"invoice_paid","payload":{"invoice_id":999999,"status":"paid"}}'
    signature = _cryptobot_signature(token, body)

    decision = verify_stage1_webhook_signature(
        Stage1PaymentProvider.CRYPTOBOT,
        body=body,
        headers={"crypto-pay-api-signature": signature},
        secret=token,
    )

    assert decision.accepted is True
    assert decision.status == Stage1WebhookSignatureStatus.VALID
    assert decision.to_safe_dict()["signature_present"] is True


def test_stage1_cryptobot_signature_rejects_mutated_body_and_missing_header() -> None:
    token = "test-cryptobot-token"
    body = b'{"update_id":777,"update_type":"invoice_paid","payload":{"invoice_id":999999,"status":"paid"}}'
    signature = _cryptobot_signature(token, body)

    mutated = verify_stage1_webhook_signature(
        Stage1PaymentProvider.CRYPTOBOT,
        body=body.replace(b"paid", b"active"),
        headers={"crypto-pay-api-signature": signature},
        secret=token,
    )
    missing = verify_stage1_webhook_signature(Stage1PaymentProvider.CRYPTOBOT, body=body, headers={}, secret=token)

    assert mutated.accepted is False
    assert mutated.status == Stage1WebhookSignatureStatus.INVALID
    assert missing.accepted is False
    assert missing.status == Stage1WebhookSignatureStatus.MISSING_SIGNATURE


def test_stage1_nowpayments_signature_uses_sorted_json_hmac_sha512() -> None:
    secret = "test-nowpayments-ipn-secret"
    payload = {
        "payment_status": "finished",
        "payment_id": 123456,
        "nested": {"z": 1, "a": "first"},
    }
    unsorted_body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    signature = _nowpayments_signature(secret, payload)

    decision = verify_stage1_webhook_signature(
        "nowpayments",
        body=unsorted_body,
        headers={"x-nowpayments-sig": signature},
        secret=secret,
    )
    invalid = verify_stage1_webhook_signature(
        "nowpayments",
        body=unsorted_body,
        headers={"x-nowpayments-sig": "00" * 64},
        secret=secret,
    )

    assert decision.accepted is True
    assert invalid.accepted is False
    assert invalid.status == Stage1WebhookSignatureStatus.INVALID


def test_stage1_payram_webhook_requires_project_api_key_header() -> None:
    secret = "payram-project-api-key"

    valid = verify_stage1_webhook_signature(
        Stage1PaymentProvider.PAYRAM,
        headers={"API-Key": secret},
        secret=secret,
    )
    invalid = verify_stage1_webhook_signature(
        Stage1PaymentProvider.PAYRAM,
        headers={"API-Key": "wrong"},
        secret=secret,
    )

    assert valid.accepted is True
    assert invalid.accepted is False
    assert invalid.status == Stage1WebhookSignatureStatus.INVALID


def test_stage1_telegram_stars_webhook_requires_telegram_secret_token_header() -> None:
    secret = "tg_secret-token_1"

    valid = verify_stage1_webhook_signature(
        Stage1PaymentProvider.TELEGRAM_STARS,
        headers={"X-Telegram-Bot-Api-Secret-Token": secret},
        secret=secret,
    )
    missing_secret = verify_stage1_webhook_signature(
        Stage1PaymentProvider.TELEGRAM_STARS,
        headers={"X-Telegram-Bot-Api-Secret-Token": secret},
        secret="",
    )

    assert valid.accepted is True
    assert missing_secret.accepted is False
    assert missing_secret.status == Stage1WebhookSignatureStatus.MISSING_SECRET


def test_stage1_digiseller_signature_uses_sorted_hmac_fields() -> None:
    secret = "digiseller-secret"
    payload = {
        "invoice_id": "12345",
        "amount": "10.00",
        "currency": "USD",
        "status": "paid",
    }
    signed_payload = {**payload, "signature": _digiseller_signature(secret, payload)}

    valid = verify_stage1_webhook_signature(
        Stage1PaymentProvider.DIGISELLER,
        payload=signed_payload,
        secret=secret,
    )
    invalid = verify_stage1_webhook_signature(
        Stage1PaymentProvider.DIGISELLER,
        payload={**signed_payload, "status": "wait"},
        secret=secret,
    )

    assert valid.accepted is True
    assert invalid.accepted is False
    assert invalid.status == Stage1WebhookSignatureStatus.INVALID


def test_stage1_yookassa_webhook_requires_provider_recheck_before_processing() -> None:
    pending = verify_stage1_webhook_signature(Stage1PaymentProvider.YOOKASSA)
    confirmed = verify_stage1_webhook_signature(
        Stage1PaymentProvider.YOOKASSA,
        provider_recheck_confirmed=True,
    )

    assert pending.accepted is False
    assert pending.status == Stage1WebhookSignatureStatus.REQUIRES_PROVIDER_RECHECK
    assert pending.to_safe_dict()["provider_recheck_required"] is True
    assert confirmed.accepted is True
    assert confirmed.to_safe_dict()["provider_recheck_confirmed"] is True


def test_stage1_signature_decision_safe_output_never_echoes_secret_or_signature() -> None:
    token = "test-cryptobot-token"
    body = b'{"update_id":777,"update_type":"invoice_paid","payload":{"invoice_id":999999,"status":"paid"}}'
    signature = _cryptobot_signature(token, body)

    decision = verify_stage1_webhook_signature(
        Stage1PaymentProvider.CRYPTOBOT,
        body=body,
        headers={"crypto-pay-api-signature": signature},
        secret=token,
    )
    serialized = str(decision.to_safe_dict())

    assert token not in serialized
    assert signature not in serialized
    assert "999999" not in serialized


@pytest.mark.asyncio
async def test_stage1_invalid_signature_is_rejected_before_webhook_side_effects() -> None:
    token = "test-cryptobot-token"
    body = b'{"update_id":777,"update_type":"invoice_paid","payload":{"invoice_id":999999,"status":"paid"}}'
    signature = _cryptobot_signature(token, body)
    app = FastAPI()
    guard = Stage1InMemoryWebhookIdempotencyGuard()
    counters: Counter[str] = Counter()

    @app.post("/s1/webhooks/cryptobot")
    async def cryptobot_webhook(request: Request) -> dict[str, Any]:
        request_body = await request.body()
        signature_decision = verify_stage1_webhook_signature(
            Stage1PaymentProvider.CRYPTOBOT,
            body=request_body,
            headers=request.headers,
            secret=token,
        )
        if not signature_decision.accepted:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

        payload = json.loads(request_body)
        identity = extract_stage1_webhook_identity(Stage1PaymentProvider.CRYPTOBOT, payload)
        idempotency_decision = guard.record(identity)
        for side_effect in idempotency_decision.side_effects_allowed:
            counters[side_effect.value] += 1

        return {
            "signature": signature_decision.to_safe_dict(),
            "idempotency": idempotency_decision.to_api_dict(),
            "counters": dict(counters),
        }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://backend") as client:
        invalid = await client.post(
            "/s1/webhooks/cryptobot",
            content=body,
            headers={"content-type": "application/json", "crypto-pay-api-signature": "00" * 32},
        )
        assert invalid.status_code == 401
        assert counters == {}

        valid = await client.post(
            "/s1/webhooks/cryptobot",
            content=body,
            headers={"content-type": "application/json", "crypto-pay-api-signature": signature},
        )

    assert valid.status_code == 200
    assert valid.json()["signature"]["accepted"] is True
    assert valid.json()["idempotency"]["result"] == "accepted_new"
    assert valid.json()["counters"]["provisioning_job"] == 1


def test_stage1_shared_package_exports_signature_contract() -> None:
    assert verify_stage1_webhook_signature(Stage1PaymentProvider.YOOKASSA).to_safe_dict()["provider"] == "yookassa"
