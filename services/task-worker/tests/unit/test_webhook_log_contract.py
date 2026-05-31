"""Webhook log model contract checks."""

from src.models.webhook_log import WebhookLogModel


def test_webhook_log_model_uses_signature_fingerprint_semantics() -> None:
    fingerprint = "a" * 64

    log = WebhookLogModel(
        source="cryptobot",
        event_type="invoice_paid",
        payload={"schema": "webhook_log.redacted.v1"},
        signature_fingerprint=fingerprint,
        is_valid=True,
    )

    assert log.signature_fingerprint == fingerprint
    assert WebhookLogModel.__table__.columns["signature"].type.length == 64
    assert "signature_fingerprint" not in WebhookLogModel.__table__.columns
