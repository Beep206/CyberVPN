import hashlib
import hmac
import json
from datetime import UTC, datetime

import pytest
from pydantic import SecretStr

from src.application.use_cases.webhooks import remnawave_webhook as remnawave_webhook_use_case
from src.config.settings import settings
from src.presentation.api.v1.webhooks.routes import remnawave_webhook


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
