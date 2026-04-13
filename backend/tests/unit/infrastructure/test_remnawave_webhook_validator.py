import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

from src.infrastructure.remnawave.webhook_validator import RemnawaveWebhookValidator


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_validate_request_accepts_current_headers_with_epoch_timestamp() -> None:
    fixed_now = datetime(2026, 4, 11, 12, 0, tzinfo=UTC)
    secret = "test-remnawave-webhook-secret"
    body = json.dumps({"event": "node.updated"}).encode()
    signature = _sign(secret, body)
    timestamp = str(int((fixed_now - timedelta(seconds=30)).timestamp()))

    validator = RemnawaveWebhookValidator(secret, now_provider=lambda: fixed_now)

    result = validator.validate_request(body, signature, timestamp)

    assert result.is_valid is True
    assert result.reason is None


def test_validate_request_accepts_iso8601_timestamp() -> None:
    fixed_now = datetime(2026, 4, 11, 12, 0, tzinfo=UTC)
    secret = "test-remnawave-webhook-secret"
    body = json.dumps({"event": "user.created"}).encode()
    signature = _sign(secret, body)
    timestamp = (fixed_now - timedelta(seconds=10)).isoformat().replace("+00:00", "Z")

    validator = RemnawaveWebhookValidator(secret, now_provider=lambda: fixed_now)

    result = validator.validate_request(body, signature, timestamp)

    assert result.is_valid is True
    assert result.reason is None


def test_validate_request_rejects_missing_signature() -> None:
    fixed_now = datetime(2026, 4, 11, 12, 0, tzinfo=UTC)
    body = b'{"event":"node.updated"}'
    validator = RemnawaveWebhookValidator("test-secret", now_provider=lambda: fixed_now)

    result = validator.validate_request(body, None, str(int(fixed_now.timestamp())))

    assert result.is_valid is False
    assert result.reason == "missing_signature"


def test_validate_request_rejects_invalid_signature() -> None:
    fixed_now = datetime(2026, 4, 11, 12, 0, tzinfo=UTC)
    body = b'{"event":"node.updated"}'
    validator = RemnawaveWebhookValidator("test-secret", now_provider=lambda: fixed_now)

    result = validator.validate_request(body, "deadbeef", str(int(fixed_now.timestamp())))

    assert result.is_valid is False
    assert result.reason == "invalid_signature"


def test_validate_request_rejects_missing_timestamp_for_current_headers() -> None:
    fixed_now = datetime(2026, 4, 11, 12, 0, tzinfo=UTC)
    secret = "test-remnawave-webhook-secret"
    body = b'{"event":"node.updated"}'
    signature = _sign(secret, body)
    validator = RemnawaveWebhookValidator(secret, now_provider=lambda: fixed_now)

    result = validator.validate_request(body, signature, None)

    assert result.is_valid is False
    assert result.reason == "missing_timestamp"


def test_validate_request_allows_missing_timestamp_for_legacy_mode() -> None:
    fixed_now = datetime(2026, 4, 11, 12, 0, tzinfo=UTC)
    secret = "test-remnawave-webhook-secret"
    body = b'{"event":"node.updated"}'
    signature = _sign(secret, body)
    validator = RemnawaveWebhookValidator(secret, now_provider=lambda: fixed_now)

    result = validator.validate_request(body, signature, None, allow_missing_timestamp=True)

    assert result.is_valid is True
    assert result.reason is None


def test_validate_request_rejects_invalid_timestamp() -> None:
    fixed_now = datetime(2026, 4, 11, 12, 0, tzinfo=UTC)
    secret = "test-remnawave-webhook-secret"
    body = b'{"event":"node.updated"}'
    signature = _sign(secret, body)
    validator = RemnawaveWebhookValidator(secret, now_provider=lambda: fixed_now)

    result = validator.validate_request(body, signature, "not-a-real-timestamp")

    assert result.is_valid is False
    assert result.reason == "invalid_timestamp"


def test_validate_request_rejects_stale_timestamp() -> None:
    fixed_now = datetime(2026, 4, 11, 12, 0, tzinfo=UTC)
    secret = "test-remnawave-webhook-secret"
    body = b'{"event":"node.updated"}'
    signature = _sign(secret, body)
    stale_timestamp = str(int((fixed_now - timedelta(minutes=10)).timestamp()))
    validator = RemnawaveWebhookValidator(secret, max_age_seconds=300, now_provider=lambda: fixed_now)

    result = validator.validate_request(body, signature, stale_timestamp)

    assert result.is_valid is False
    assert result.reason == "stale_timestamp"


def test_validate_request_rejects_future_timestamp_beyond_skew() -> None:
    fixed_now = datetime(2026, 4, 11, 12, 0, tzinfo=UTC)
    secret = "test-remnawave-webhook-secret"
    body = b'{"event":"node.updated"}'
    signature = _sign(secret, body)
    future_timestamp = str(int((fixed_now + timedelta(minutes=2)).timestamp()))
    validator = RemnawaveWebhookValidator(
        secret,
        max_age_seconds=300,
        future_skew_seconds=30,
        now_provider=lambda: fixed_now,
    )

    result = validator.validate_request(body, signature, future_timestamp)

    assert result.is_valid is False
    assert result.reason == "future_timestamp"
