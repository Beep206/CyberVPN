"""Webhook log storage redaction checks."""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from src.application.use_cases.payments.payment_webhook import ProcessPaymentWebhookUseCase
from src.application.use_cases.webhooks.remnawave_webhook import ProcessRemnawaveWebhookUseCase
from src.infrastructure.payments.cryptobot.webhook_handler import CryptoBotWebhookHandler
from src.infrastructure.remnawave.webhook_validator import RemnawaveWebhookValidator


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, instance: Any) -> None:
        self.added.append(instance)


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
    assert log.signature_fingerprint == hashlib.sha256(signature.encode("utf-8")).hexdigest()
    assert log.payload["schema"] == "webhook_log.redacted.v1"
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
    assert log.signature_fingerprint == hashlib.sha256(b"raw-signature-value").hexdigest()
    _assert_sensitive_values_absent(_serialized(log.payload))


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
    assert log.signature_fingerprint == hashlib.sha256(signature.encode("utf-8")).hexdigest()
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
    assert log.signature_fingerprint == hashlib.sha256(b"raw-signature-value").hexdigest()
    _assert_sensitive_values_absent(_serialized(log.payload))


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
