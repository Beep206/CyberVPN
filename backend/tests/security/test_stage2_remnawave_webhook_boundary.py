import hashlib
import hmac
import json
from contextlib import nullcontext
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from src.application.use_cases.webhooks import remnawave_webhook as remnawave_webhook_use_case
from src.application.use_cases.webhooks.webhook_log_redaction import webhook_log_fingerprint
from src.config.settings import settings
from src.presentation.api.v1.webhooks.routes import remnawave_webhook

_WEBHOOK_LOG_FINGERPRINT_SECRET = "webhook-fingerprint-key-8f1c7d9a2e6b4f03"


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class _Request:
    def __init__(self, body: bytes, headers: dict[str, str]) -> None:
        self._body = body
        self.headers = headers

    async def body(self) -> bytes:
        return self._body


class _Session:
    def __init__(self) -> None:
        self.logs: list[object] = []

    def add(self, log: object) -> None:
        self.logs.append(log)


class _DuplicateSession(_Session):
    @property
    def no_autoflush(self):
        return nullcontext()

    async def execute(self, statement):
        self.statement = statement
        return SimpleNamespace(scalar_one_or_none=lambda: object())


class _BroadcastSpy:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def broadcast(self, channel: str, data: dict[str, object]) -> None:
        self.calls.append((channel, data))


@pytest.mark.parametrize(
    ("headers_factory", "environment"),
    [
        (lambda signature: {"X-Remnawave-Signature": signature}, "development"),
        (lambda signature: {"X-Webhook-Signature": signature}, "production"),
    ],
)
async def test_remnawave_webhook_rejects_timestamp_free_signatures(
    monkeypatch: pytest.MonkeyPatch,
    headers_factory,
    environment: str,
) -> None:
    secret = "test-remnawave-webhook-secret"
    body = json.dumps({"event": "user.created", "data": {"uuid": "user-1"}}).encode()
    signature = _sign(secret, body)
    session = _Session()
    broadcast_spy = _BroadcastSpy()

    monkeypatch.setattr(settings, "environment", environment)
    monkeypatch.setattr(settings, "remnawave_webhook_secret", SecretStr(secret))
    monkeypatch.setattr(settings, "remnawave_webhook_max_age_seconds", 300)
    monkeypatch.setattr(settings, "remnawave_webhook_future_skew_seconds", 60)
    monkeypatch.setattr(remnawave_webhook_use_case, "ws_manager", broadcast_spy)

    response = await remnawave_webhook(
        request=_Request(body, headers_factory(signature)),
        db=session,
    )

    assert response == {"status": "invalid_timestamp"}
    assert len(session.logs) == 1
    assert session.logs[0].is_valid is False
    assert session.logs[0].error_message == "missing_timestamp"
    assert broadcast_spy.calls == []


async def test_remnawave_webhook_broadcast_excludes_provider_secrets_and_customer_pii(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "test-remnawave-webhook-secret"
    broadcast_spy = _BroadcastSpy()
    session = _Session()
    body = json.dumps(
        {
            "event": "user.updated",
            "data": {
                "uuid": "user-1",
                "status": "active",
                "subscriptionUrl": "https://subscription.example/secret",
                "token": "provider-token",
                "email": "customer@example.com",
                "telegramId": 123456,
                "profile": {"subscriptionUrl": "nested-secret"},
            },
        }
    ).encode()
    signature = _sign(secret, body)
    timestamp = str(int(datetime.now(UTC).timestamp()))

    monkeypatch.setattr(settings, "remnawave_webhook_secret", SecretStr(secret))
    monkeypatch.setattr(settings, "remnawave_webhook_max_age_seconds", 300)
    monkeypatch.setattr(settings, "remnawave_webhook_future_skew_seconds", 60)
    monkeypatch.setattr(remnawave_webhook_use_case, "ws_manager", broadcast_spy)

    response = await remnawave_webhook(
        request=_Request(
            body,
            {
                "X-Remnawave-Signature": signature,
                "X-Remnawave-Timestamp": timestamp,
            },
        ),
        db=session,
    )

    assert response == {"status": "processed", "event": "user.updated"}
    assert broadcast_spy.calls == [
        (
            "events",
            {
                "event": "user.updated",
                "data": {
                    "uuid": "user-1",
                    "status": "active",
                },
            },
        )
    ]


async def test_remnawave_webhook_accepts_torrent_blocker_report_as_safe_admin_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "test-remnawave-webhook-secret"
    broadcast_spy = _BroadcastSpy()
    session = _Session()
    body = json.dumps(
        {
            "event": "torrent_blocker.report",
            "data": {
                "userUuid": "user-1",
                "nodeUuid": "node-1",
                "nodeName": "DE Frankfurt",
                "blocked": True,
                "blockDuration": 86400,
                "ip": "203.0.113.10",
                "email": "customer@example.com",
                "token": "provider-token",
            },
        }
    ).encode()
    signature = _sign(secret, body)
    timestamp = str(int(datetime.now(UTC).timestamp()))

    monkeypatch.setattr(settings, "remnawave_webhook_secret", SecretStr(secret))
    monkeypatch.setattr(settings, "remnawave_webhook_max_age_seconds", 300)
    monkeypatch.setattr(settings, "remnawave_webhook_future_skew_seconds", 60)
    monkeypatch.setattr(remnawave_webhook_use_case, "ws_manager", broadcast_spy)

    response = await remnawave_webhook(
        request=_Request(
            body,
            {
                "X-Remnawave-Signature": signature,
                "X-Remnawave-Timestamp": timestamp,
            },
        ),
        db=session,
    )

    assert response == {"status": "processed", "event": "torrent_blocker.report"}
    assert len(session.logs) == 1
    assert session.logs[0].event_type == "torrent_blocker.report"
    assert session.logs[0].is_valid is True
    assert broadcast_spy.calls == [
        (
            "events",
            {
                "event": "torrent_blocker.report",
                "data": {
                    "userUuid": "user-1",
                    "nodeUuid": "node-1",
                    "nodeName": "DE Frankfurt",
                    "blocked": True,
                    "blockDuration": 86400,
                },
                "abuse_type": "torrent",
                "admin_notification": True,
            },
        )
    ]
    serialized = f"{session.logs[0].payload} {broadcast_spy.calls}".lower()
    assert "203.0.113.10" not in serialized
    assert "customer@example.com" not in serialized
    assert "provider-token" not in serialized


async def test_remnawave_webhook_rejects_oversized_body_before_broadcast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broadcast_spy = _BroadcastSpy()
    session = _Session()
    body = json.dumps({"event": "user.updated", "data": {"uuid": "user-1", "status": "active"}}).encode()

    monkeypatch.setattr(settings, "remnawave_webhook_max_body_bytes", 12)
    monkeypatch.setattr(remnawave_webhook_use_case, "ws_manager", broadcast_spy)

    response = await remnawave_webhook(
        request=_Request(body, {"X-Remnawave-Signature": "ignored-for-oversized-body"}),
        db=session,
    )

    assert response == {"status": "invalid_payload"}
    assert len(session.logs) == 1
    assert session.logs[0].is_valid is False
    assert session.logs[0].error_message == "body_too_large"
    assert broadcast_spy.calls == []


async def test_remnawave_webhook_rejects_duplicate_body_before_broadcast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "test-remnawave-webhook-secret"
    broadcast_spy = _BroadcastSpy()
    session = _DuplicateSession()
    body = json.dumps({"event": "user.updated", "data": {"uuid": "user-1", "status": "active"}}).encode()
    signature = _sign(secret, body)
    timestamp = str(int(datetime.now(UTC).timestamp()))

    monkeypatch.setattr(settings, "remnawave_webhook_secret", SecretStr(secret))
    monkeypatch.setattr(settings, "remnawave_webhook_max_age_seconds", 300)
    monkeypatch.setattr(settings, "remnawave_webhook_future_skew_seconds", 60)
    monkeypatch.setattr(settings, "remnawave_webhook_max_body_bytes", 65536)
    monkeypatch.setattr(
        settings,
        "webhook_log_fingerprint_secret",
        SecretStr(_WEBHOOK_LOG_FINGERPRINT_SECRET),
    )
    monkeypatch.setattr(remnawave_webhook_use_case, "ws_manager", broadcast_spy)

    response = await remnawave_webhook(
        request=_Request(
            body,
            {
                "X-Remnawave-Signature": signature,
                "X-Remnawave-Timestamp": timestamp,
            },
        ),
        db=session,
    )

    assert response == {"status": "duplicate", "event": "user.updated"}
    assert len(session.logs) == 1
    assert session.logs[0].is_valid is True
    assert session.logs[0].error_message == "duplicate_webhook"
    assert session.logs[0].payload["body_fingerprint"] == webhook_log_fingerprint(
        body,
        namespace="remnawave_body",
    )
    assert session.logs[0].payload["body_fingerprint"] != hashlib.sha256(body).hexdigest()
    compiled_statement = str(session.statement.compile(compile_kwargs={"literal_binds": True}))
    assert "body_fingerprint" in compiled_statement
    assert "body_sha256" not in compiled_statement
    assert broadcast_spy.calls == []


async def test_missing_fingerprint_secret_omits_body_fingerprint_and_skips_duplicate_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "test-remnawave-webhook-secret"
    broadcast_spy = _BroadcastSpy()
    session = _DuplicateSession()
    body = json.dumps({"event": "user.updated", "data": {"uuid": "user-1"}}).encode()
    signature = _sign(secret, body)
    timestamp = str(int(datetime.now(UTC).timestamp()))

    monkeypatch.setattr(settings, "remnawave_webhook_secret", SecretStr(secret))
    monkeypatch.setattr(settings, "webhook_log_fingerprint_secret", SecretStr(""))
    monkeypatch.setattr(settings, "remnawave_webhook_max_age_seconds", 300)
    monkeypatch.setattr(settings, "remnawave_webhook_future_skew_seconds", 60)
    monkeypatch.setattr(settings, "remnawave_webhook_max_body_bytes", 65536)
    monkeypatch.setattr(remnawave_webhook_use_case, "ws_manager", broadcast_spy)

    response = await remnawave_webhook(
        request=_Request(
            body,
            {
                "X-Remnawave-Signature": signature,
                "X-Remnawave-Timestamp": timestamp,
            },
        ),
        db=session,
    )

    assert response == {"status": "processed", "event": "user.updated"}
    assert "body_fingerprint" not in session.logs[0].payload
    assert "body_sha256" not in session.logs[0].payload
    assert not hasattr(session, "statement")
    assert len(broadcast_spy.calls) == 1


async def test_remnawave_webhook_drops_oversized_websocket_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "test-remnawave-webhook-secret"
    broadcast_spy = _BroadcastSpy()
    session = _Session()
    body = json.dumps(
        {
            "event": "torrent_blocker.report",
            "data": {
                "userUuid": "u" * 240,
                "nodeName": "n" * 240,
                "blocked": True,
                "blockDuration": 10**20,
                "nodeUuid": "node-1",
            },
        }
    ).encode()
    signature = _sign(secret, body)
    timestamp = str(int(datetime.now(UTC).timestamp()))

    monkeypatch.setattr(settings, "remnawave_webhook_secret", SecretStr(secret))
    monkeypatch.setattr(settings, "remnawave_webhook_max_age_seconds", 300)
    monkeypatch.setattr(settings, "remnawave_webhook_future_skew_seconds", 60)
    monkeypatch.setattr(settings, "remnawave_webhook_max_body_bytes", 65536)
    monkeypatch.setattr(remnawave_webhook_use_case, "ws_manager", broadcast_spy)

    response = await remnawave_webhook(
        request=_Request(
            body,
            {
                "X-Remnawave-Signature": signature,
                "X-Remnawave-Timestamp": timestamp,
            },
        ),
        db=session,
    )

    assert response == {"status": "processed", "event": "torrent_blocker.report"}
    payload = broadcast_spy.calls[0][1]
    assert payload["data"] == {"blocked": True, "nodeUuid": "node-1"}
