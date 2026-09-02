"""Webhook log storage redaction checks."""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import logging
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import SecretStr

from src.application.use_cases.payments.payment_webhook import ProcessPaymentWebhookUseCase
from src.application.use_cases.webhooks.remnawave_webhook import ProcessRemnawaveWebhookUseCase
from src.application.use_cases.webhooks.webhook_log_redaction import (
    build_cryptobot_webhook_log_payload,
    build_remnawave_webhook_log_payload,
    signature_fingerprint,
    webhook_log_fingerprint,
)
from src.config.settings import settings
from src.infrastructure.payments.cryptobot.webhook_handler import CryptoBotWebhookHandler
from src.infrastructure.remnawave.webhook_validator import RemnawaveWebhookValidator

_WEBHOOK_LOG_FINGERPRINT_SECRET = "webhook-fingerprint-key-8f1c7d9a2e6b4f03"
_WEBHOOK_LOG_FINGERPRINT_DOMAIN = b"cybervpn/webhook-log-fingerprint/v2"


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, instance: Any) -> None:
        self.added.append(instance)


@pytest.fixture(autouse=True)
def _configure_webhook_log_fingerprint_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        settings,
        "webhook_log_fingerprint_secret",
        SecretStr(_WEBHOOK_LOG_FINGERPRINT_SECRET),
    )


def _expected_fingerprint(value: str | bytes, *, namespace: str) -> str:
    normalized = value if isinstance(value, bytes) else value.strip().encode("utf-8")
    message = b"\x00".join(
        (
            _WEBHOOK_LOG_FINGERPRINT_DOMAIN,
            namespace.encode("ascii"),
            normalized,
        )
    )
    return hmac.new(
        _WEBHOOK_LOG_FINGERPRINT_SECRET.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()


def _cryptobot_signed_body(token: str, payload: dict[str, Any]) -> tuple[bytes, str]:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    secret = hashlib.sha256(token.encode("utf-8")).digest()
    signature = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return body, signature


def _remnawave_signature(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _serialized(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _assert_sensitive_values_absent(serialized: str) -> None:
    sensitive_values = [
        "raw-signature-value",
        "https://vpn.example.invalid/subscription/config",
        "https://vpn.example.invalid/config/vless",
        "provider-token-secret",
        "tgWebAppData=user%3Dsecret",
        "alice@example.invalid",
        "raw-invalid-body-secret",
        "node-raw-uuid",
        "123456789",
    ]
    for value in sensitive_values:
        assert value not in serialized


def _load_redaction_migration() -> Any:
    migration_path = (
        Path(__file__).resolve().parents[2] / "alembic" / "versions" / "20260531_redact_webhook_log_storage.py"
    )
    spec = importlib.util.spec_from_file_location("redact_webhook_log_storage", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_cryptobot_webhook_log_stores_allowlisted_metadata_only() -> None:
    token = "test-webhook-token"
    body, signature = _cryptobot_signed_body(
        token,
        {
            "update_id": "raw-signature-value",
            "update_type": "unknown_event",
            "payload": {
                "invoice_id": "123456789",
                "status": "paid",
                "subscription_url": "https://vpn.example.invalid/subscription/config",
                "initData": "tgWebAppData=user%3Dsecret",
                "email": "alice@example.invalid",
            },
        },
    )
    session = _FakeSession()
    use_case = ProcessPaymentWebhookUseCase(  # type: ignore[arg-type]
        session=session,
        webhook_handler=CryptoBotWebhookHandler(token),
    )

    result = await use_case.execute(provider="cryptobot", body=body, signature=signature)

    assert result == {"status": "ignored", "update_type": "unknown_event"}
    assert len(session.added) == 1
    log = session.added[0]
    assert log.event_type == "unknown_event"
    assert log.is_valid is True
    assert log.signature_fingerprint == _expected_fingerprint(signature, namespace="signature")
    assert log.payload["schema"] == "webhook_log.redacted.v2"
    assert log.payload["status"] == "paid"
    assert "invoice_id_fingerprint" in log.payload
    assert "event_id_fingerprint" in log.payload
    _assert_sensitive_values_absent(_serialized(log.payload))


@pytest.mark.asyncio
async def test_cryptobot_invalid_signature_log_never_stores_raw_signature_or_payload() -> None:
    token = "test-webhook-token"
    body = json.dumps(
        {
            "update_type": "invoice_paid",
            "payload": {
                "invoice_id": "123456789",
                "status": "paid",
                "subscription_url": "https://vpn.example.invalid/subscription/config",
                "provider_token": "provider-token-secret",
            },
        },
        separators=(",", ":"),
    ).encode("utf-8")
    session = _FakeSession()
    use_case = ProcessPaymentWebhookUseCase(  # type: ignore[arg-type]
        session=session,
        webhook_handler=CryptoBotWebhookHandler(token),
    )

    result = await use_case.execute(provider="cryptobot", body=body, signature="raw-signature-value")

    assert result == {"status": "invalid_signature"}
    log = session.added[0]
    assert log.is_valid is False
    assert log.signature_fingerprint == _expected_fingerprint("raw-signature-value", namespace="signature")
    _assert_sensitive_values_absent(_serialized(log.payload))


@pytest.mark.asyncio
async def test_payment_webhook_application_logs_redact_provider_external_ids(caplog, monkeypatch) -> None:
    raw_external_id = "raw-provider-invoice-424242"
    expected_fingerprint = _expected_fingerprint(
        raw_external_id,
        namespace="payment_provider_reference",
    )
    caplog.set_level(logging.INFO, logger="src.application.use_cases.payments.payment_webhook")

    missing_repo = SimpleNamespace(
        get_by_external_id_for_update=AsyncMock(return_value=None),
        update=AsyncMock(),
    )
    monkeypatch.setattr(
        "src.application.use_cases.payments.payment_webhook.PaymentRepository",
        lambda _session: missing_repo,
    )
    missing_use_case = ProcessPaymentWebhookUseCase(  # type: ignore[arg-type]
        session=_FakeSession(),
        webhook_handler=object(),
    )

    missing_result = await missing_use_case._handle_invoice_paid(raw_external_id)

    assert missing_result["warning"] == "payment_not_found"
    assert raw_external_id not in caplog.text
    assert any(getattr(record, "external_id_fingerprint", None) == expected_fingerprint for record in caplog.records)
    assert all(record.__dict__.get("external_id") != raw_external_id for record in caplog.records)

    caplog.clear()
    payment = SimpleNamespace(
        id=uuid4(),
        user_uuid=uuid4(),
        status="pending",
        provider="cryptobot",
        currency="USD",
        amount=Decimal("12.34"),
        metadata_={},
        wallet_amount_used=Decimal("0"),
    )
    paid_repo = SimpleNamespace(
        get_by_external_id_for_update=AsyncMock(return_value=payment),
        get_by_external_id=AsyncMock(return_value=payment),
        update=AsyncMock(return_value=payment),
    )
    monkeypatch.setattr(
        "src.application.use_cases.payments.payment_webhook.PaymentRepository",
        lambda _session: paid_repo,
    )
    paid_use_case = ProcessPaymentWebhookUseCase(  # type: ignore[arg-type]
        session=SimpleNamespace(commit=AsyncMock()),
        webhook_handler=object(),
    )
    paid_use_case._attempts = SimpleNamespace(get_by_payment_id=AsyncMock(return_value=None))  # type: ignore[assignment]
    paid_use_case._outbox = SimpleNamespace(append_event=AsyncMock())  # type: ignore[assignment]

    class _PostPaymentProcessing:
        async def execute(self, _payment_id, *, process_cash_rewards: bool) -> dict[str, Any]:
            assert process_cash_rewards is False
            return {"cash_rewards_deferred": True}

    class _Settlement:
        async def execute(self, **_kwargs) -> SimpleNamespace:
            return SimpleNamespace(status="legacy_non_order", legacy_post_payment_required=True)

    monkeypatch.setattr(
        "src.application.use_cases.payments.payment_webhook.SettleCompletedPaymentAttemptUseCase",
        lambda _session: _Settlement(),
    )
    monkeypatch.setattr(
        "src.application.use_cases.payments.post_payment.PostPaymentProcessingUseCase",
        lambda _session: _PostPaymentProcessing(),
    )

    paid_result = await paid_use_case._handle_invoice_paid(raw_external_id)

    assert paid_result["status"] == "processed"
    assert raw_external_id not in caplog.text
    assert any(getattr(record, "external_id_fingerprint", None) == expected_fingerprint for record in caplog.records)
    assert all(record.__dict__.get("external_id") != raw_external_id for record in caplog.records)

    caplog.clear()
    payment.status = "pending"
    payment.wallet_amount_used = Decimal("3.21")
    payment.metadata_ = {"wallet_frozen": True}
    unfreeze_error_use_case = ProcessPaymentWebhookUseCase(  # type: ignore[arg-type]
        session=SimpleNamespace(commit=AsyncMock()),
        webhook_handler=object(),
    )
    unfreeze_error_use_case._attempts = SimpleNamespace(  # type: ignore[assignment]
        get_by_payment_id=AsyncMock(return_value=None)
    )
    unfreeze_error_use_case._wallet = SimpleNamespace(  # type: ignore[assignment]
        unfreeze=AsyncMock(side_effect=RuntimeError("wallet backend down"))
    )

    unfreeze_error_result = await unfreeze_error_use_case._handle_invoice_failed(raw_external_id, "invoice_failed")

    assert unfreeze_error_result["status"] == "processed"
    assert raw_external_id not in caplog.text
    assert any(getattr(record, "external_id_fingerprint", None) == expected_fingerprint for record in caplog.records)
    assert all(record.__dict__.get("external_id") != raw_external_id for record in caplog.records)

    caplog.clear()
    payment.status = "pending"
    failed_use_case = ProcessPaymentWebhookUseCase(  # type: ignore[arg-type]
        session=SimpleNamespace(commit=AsyncMock()),
        webhook_handler=object(),
    )
    failed_use_case._attempts = SimpleNamespace(get_by_payment_id=AsyncMock(return_value=None))  # type: ignore[assignment]

    failed_result = await failed_use_case._handle_invoice_failed(raw_external_id, "invoice_failed")

    assert failed_result["status"] == "processed"
    assert raw_external_id not in caplog.text
    assert any(getattr(record, "external_id_fingerprint", None) == expected_fingerprint for record in caplog.records)
    assert all(record.__dict__.get("external_id") != raw_external_id for record in caplog.records)


@pytest.mark.asyncio
async def test_payment_webhook_does_not_run_legacy_post_payment_for_missing_order_attempt(monkeypatch) -> None:
    raw_external_id = "order-provider-invoice-777"
    payment = SimpleNamespace(
        id=uuid4(),
        user_uuid=uuid4(),
        status="pending",
        provider="cryptobot",
        currency="USD",
        amount=Decimal("12.34"),
        metadata_={"checkout_mode": "order_payment_attempt", "order_id": str(uuid4())},
        wallet_amount_used=Decimal("0"),
    )
    paid_repo = SimpleNamespace(
        get_by_external_id_for_update=AsyncMock(return_value=payment),
        get_by_external_id=AsyncMock(return_value=payment),
        update=AsyncMock(return_value=payment),
    )
    post_payment_execute = AsyncMock()
    append_event = AsyncMock()

    class _Settlement:
        async def execute(self, **_kwargs) -> SimpleNamespace:
            return SimpleNamespace(
                status="order_attempt_missing",
                legacy_post_payment_required=False,
                payment_id=payment.id,
                payment_attempt_id=None,
                order_id=None,
                benefit_results=(),
                reason="order_payment_attempt_not_found",
            )

    class _PostPaymentProcessing:
        async def execute(self, _payment_id, *, process_cash_rewards: bool) -> dict[str, Any]:
            return await post_payment_execute(_payment_id, process_cash_rewards=process_cash_rewards)

    monkeypatch.setattr(
        "src.application.use_cases.payments.payment_webhook.PaymentRepository",
        lambda _session: paid_repo,
    )
    monkeypatch.setattr(
        "src.application.use_cases.payments.payment_webhook.SettleCompletedPaymentAttemptUseCase",
        lambda _session: _Settlement(),
    )
    monkeypatch.setattr(
        "src.application.use_cases.payments.post_payment.PostPaymentProcessingUseCase",
        lambda _session: _PostPaymentProcessing(),
    )
    session = SimpleNamespace(commit=AsyncMock())
    use_case = ProcessPaymentWebhookUseCase(  # type: ignore[arg-type]
        session=session,
        webhook_handler=object(),
    )
    use_case._attempts = SimpleNamespace(get_by_payment_id=AsyncMock(return_value=None))  # type: ignore[assignment]
    use_case._outbox = SimpleNamespace(append_event=append_event)  # type: ignore[assignment]

    result = await use_case._handle_invoice_paid(raw_external_id)

    assert result["status"] == "processed"
    assert result["post_payment"]["settlement"]["status"] == "order_attempt_missing"
    paid_repo.update.assert_awaited_once_with(payment)
    post_payment_execute.assert_not_awaited()
    append_event.assert_not_awaited()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_remnawave_webhook_log_stores_allowlisted_metadata_only() -> None:
    secret = "test-remnawave-secret"
    body = json.dumps(
        {
            "event": "node.updated",
            "data": {
                "uuid": "node-raw-uuid",
                "status": "online",
                "subscription_url": "https://vpn.example.invalid/subscription/config",
                "config_url": "https://vpn.example.invalid/config/vless",
                "provider_token": "provider-token-secret",
                "initData": "tgWebAppData=user%3Dsecret",
                "email": "alice@example.invalid",
            },
        },
        separators=(",", ":"),
    ).encode("utf-8")
    signature = _remnawave_signature(secret, body)
    timestamp = str(int(datetime.now(UTC).timestamp()))
    session = _FakeSession()
    use_case = ProcessRemnawaveWebhookUseCase(  # type: ignore[arg-type]
        session=session,
        validator=RemnawaveWebhookValidator(secret),
    )

    result = await use_case.execute(body=body, signature=signature, timestamp=timestamp)

    assert result == {"status": "processed", "event": "node.updated"}
    log = session.added[0]
    assert log.event_type == "node.updated"
    assert log.is_valid is True
    assert log.signature_fingerprint == _expected_fingerprint(signature, namespace="signature")
    assert log.payload["status"] == "online"
    assert "subject_fingerprint" in log.payload
    _assert_sensitive_values_absent(_serialized(log.payload))


@pytest.mark.asyncio
async def test_remnawave_invalid_json_log_never_stores_raw_body() -> None:
    secret = "test-remnawave-secret"
    body = (
        b'{"event":"node.updated","data":{"subscription_url":'
        b'"https://vpn.example.invalid/subscription/config",'
        b'"secret":"raw-invalid-body-secret"'
    )
    session = _FakeSession()
    use_case = ProcessRemnawaveWebhookUseCase(  # type: ignore[arg-type]
        session=session,
        validator=RemnawaveWebhookValidator(secret),
    )

    result = await use_case.execute(body=body, signature="raw-signature-value", timestamp=None)

    assert result == {"status": "invalid_payload"}
    log = session.added[0]
    assert log.event_type is None
    assert log.is_valid is False
    assert log.payload["body_parse_status"] == "invalid_json"
    assert log.payload["body_size_bytes"] == len(body)
    assert "raw_body" not in log.payload
    assert log.signature_fingerprint == _expected_fingerprint("raw-signature-value", namespace="signature")
    _assert_sensitive_values_absent(_serialized(log.payload))


def test_webhook_log_fingerprints_are_keyed_and_domain_separated() -> None:
    raw_low_entropy_id = "123456789"

    event_fingerprint = webhook_log_fingerprint(
        raw_low_entropy_id,
        namespace="cryptobot_event_id",
    )
    invoice_fingerprint = webhook_log_fingerprint(
        raw_low_entropy_id,
        namespace="cryptobot_invoice_id",
    )

    assert event_fingerprint == _expected_fingerprint(
        raw_low_entropy_id,
        namespace="cryptobot_event_id",
    )
    assert invoice_fingerprint == _expected_fingerprint(
        raw_low_entropy_id,
        namespace="cryptobot_invoice_id",
    )
    assert event_fingerprint != invoice_fingerprint
    assert event_fingerprint != hashlib.sha256(raw_low_entropy_id.encode("utf-8")).hexdigest()

    raw_body = b'{"event":"user.updated","data":{"userId":42}}'
    assert webhook_log_fingerprint(raw_body, namespace="remnawave_body") == _expected_fingerprint(
        raw_body,
        namespace="remnawave_body",
    )
    assert webhook_log_fingerprint(raw_body, namespace="remnawave_body") != hashlib.sha256(raw_body).hexdigest()


def test_missing_webhook_log_fingerprint_secret_omits_all_fingerprints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "webhook_log_fingerprint_secret", SecretStr(""))

    cryptobot_payload = build_cryptobot_webhook_log_payload(
        {
            "update_id": "123",
            "update_type": "invoice_paid",
            "payload": {"invoice_id": "456", "status": "paid"},
        },
        signature="signature-value",
        is_valid=True,
    )
    remnawave_payload = build_remnawave_webhook_log_payload(
        {
            "id": "event-1",
            "event": "user.updated",
            "data": {"userId": 42, "status": "active"},
        },
        signature="signature-value",
        is_valid=True,
        validation_reason=None,
    )

    assert signature_fingerprint("signature-value") is None
    assert "event_id_fingerprint" not in cryptobot_payload
    assert "invoice_id_fingerprint" not in cryptobot_payload
    assert "event_id_fingerprint" not in remnawave_payload
    assert "subject_fingerprint" not in remnawave_payload
    assert cryptobot_payload["schema"] == "webhook_log.redacted.v2"
    assert remnawave_payload["schema"] == "webhook_log.redacted.v2"


def test_legacy_webhook_log_migration_sanitizes_existing_raw_rows() -> None:
    migration = _load_redaction_migration()

    cryptobot_payload = migration._sanitize_legacy_payload(
        {
            "source": "cryptobot",
            "event_type": "invoice_paid",
            "payload": {
                "update_id": "raw-signature-value",
                "update_type": "invoice_paid",
                "payload": {
                    "invoice_id": "123456789",
                    "status": "paid",
                    "subscription_url": "https://vpn.example.invalid/subscription/config",
                    "initData": "tgWebAppData=user%3Dsecret",
                    "email": "alice@example.invalid",
                },
            },
            "signature": "raw-signature-value",
            "is_valid": True,
            "error_message": None,
        }
    )
    remnawave_payload = migration._sanitize_legacy_payload(
        {
            "source": "remnawave",
            "event_type": "node.updated",
            "payload": {
                "event": "node.updated",
                "data": {
                    "uuid": "node-raw-uuid",
                    "status": "online",
                    "subscription_url": "https://vpn.example.invalid/subscription/config",
                    "config_url": "https://vpn.example.invalid/config/vless",
                    "provider_token": "provider-token-secret",
                    "initData": "tgWebAppData=user%3Dsecret",
                    "email": "alice@example.invalid",
                },
            },
            "signature": "raw-signature-value",
            "is_valid": True,
            "error_message": None,
        }
    )

    assert cryptobot_payload["schema"] == "webhook_log.redacted.v1"
    assert cryptobot_payload["event_type"] == "invoice_paid"
    assert cryptobot_payload["status"] == "paid"
    assert "event_id_fingerprint" in cryptobot_payload
    assert "invoice_id_fingerprint" in cryptobot_payload
    assert remnawave_payload["event_type"] == "node.updated"
    assert remnawave_payload["status"] == "online"
    assert "subject_fingerprint" in remnawave_payload
    _assert_sensitive_values_absent(_serialized(cryptobot_payload))
    _assert_sensitive_values_absent(_serialized(remnawave_payload))


def test_legacy_webhook_log_migration_does_not_trust_spoofed_redacted_schema() -> None:
    migration = _load_redaction_migration()

    payload = migration._sanitize_redacted_payload(
        {
            "source": "remnawave",
            "event_type": "node.updated",
            "payload": {
                "schema": "webhook_log.redacted.v1",
                "source": "remnawave",
                "event_type": "node.updated",
                "event_id_fingerprint": hashlib.sha256(b"event-1").hexdigest(),
                "signature_present": True,
                "validation_status": "valid",
                "data": {
                    "uuid": "node-raw-uuid",
                    "status": "online",
                    "subscription_url": "https://vpn.example.invalid/subscription/config",
                    "config_url": "https://vpn.example.invalid/config/vless",
                    "provider_token": "provider-token-secret",
                    "initData": "tgWebAppData=user%3Dsecret",
                    "email": "alice@example.invalid",
                },
                "raw_body": "raw-invalid-body-secret",
            },
            "signature": "raw-signature-value",
            "is_valid": True,
            "error_message": None,
        },
        {
            "schema": "webhook_log.redacted.v1",
            "source": "remnawave",
            "event_type": "node.updated",
            "event_id_fingerprint": hashlib.sha256(b"event-1").hexdigest(),
            "signature_present": True,
            "validation_status": "valid",
            "data": {
                "uuid": "node-raw-uuid",
                "status": "online",
                "subscription_url": "https://vpn.example.invalid/subscription/config",
                "config_url": "https://vpn.example.invalid/config/vless",
                "provider_token": "provider-token-secret",
                "initData": "tgWebAppData=user%3Dsecret",
                "email": "alice@example.invalid",
            },
            "raw_body": "raw-invalid-body-secret",
        },
    )

    assert payload["schema"] == "webhook_log.redacted.v1"
    assert payload["event_type"] == "node.updated"
    assert payload["status"] == "online"
    assert "event_id_fingerprint" in payload
    assert "subject_fingerprint" in payload
    assert "data" not in payload
    assert "raw_body" not in payload
    _assert_sensitive_values_absent(_serialized(payload))
