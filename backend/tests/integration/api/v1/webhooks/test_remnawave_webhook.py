import hashlib
import hmac
import json
from datetime import UTC, datetime

import pytest
from pydantic import SecretStr
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.webhooks import remnawave_webhook as remnawave_webhook_use_case
from src.config.settings import settings
from src.infrastructure.database.models.webhook_log_model import WebhookLog


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class _BroadcastSpy:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def broadcast(self, channel: str, data: dict[str, object]) -> None:
        self.calls.append((channel, data))


@pytest.fixture(autouse=True)
async def _cleanup_remnawave_webhook_logs(db: AsyncSession):
    await db.execute(delete(WebhookLog).where(WebhookLog.source == "remnawave"))
    await db.commit()
    yield
    await db.execute(delete(WebhookLog).where(WebhookLog.source == "remnawave"))
    await db.commit()


class TestRemnawaveWebhookRoute:
    @pytest.mark.integration
    async def test_remnawave_webhook_accepts_current_headers(
        self,
        async_client,
        db: AsyncSession,
        monkeypatch,
    ):
        secret = "test-remnawave-webhook-secret"
        monkeypatch.setattr(settings, "remnawave_webhook_secret", SecretStr(secret))
        monkeypatch.setattr(settings, "remnawave_webhook_max_age_seconds", 300)
        monkeypatch.setattr(settings, "remnawave_webhook_future_skew_seconds", 60)

        body = json.dumps({"event": "node.updated", "data": {"uuid": "node-1"}}).encode()
        signature = _sign(secret, body)
        timestamp = str(int(datetime.now(UTC).timestamp()))

        response = await async_client.post(
            "/api/v1/webhooks/remnawave",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Remnawave-Signature": signature,
                "X-Remnawave-Timestamp": timestamp,
            },
        )

        assert response.status_code == 200
        assert response.json() == {"status": "processed", "event": "node.updated"}

        result = await db.execute(
            select(WebhookLog).where(WebhookLog.source == "remnawave").order_by(WebhookLog.created_at.desc())
        )
        log = result.scalar_one()
        assert log.is_valid is True
        assert log.error_message is None
        assert log.event_type == "node.updated"

    @pytest.mark.integration
    async def test_remnawave_webhook_rejects_legacy_signature_header_without_timestamp_in_production(
        self,
        async_client,
        db: AsyncSession,
        monkeypatch,
    ):
        secret = "test-remnawave-webhook-secret"
        monkeypatch.setattr(settings, "environment", "production")
        monkeypatch.setattr(settings, "remnawave_webhook_secret", SecretStr(secret))
        monkeypatch.setattr(settings, "remnawave_webhook_max_age_seconds", 300)
        monkeypatch.setattr(settings, "remnawave_webhook_future_skew_seconds", 60)

        body = json.dumps({"event": "user.created", "data": {"uuid": "user-1"}}).encode()
        signature = _sign(secret, body)

        response = await async_client.post(
            "/api/v1/webhooks/remnawave",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Signature": signature,
            },
        )

        assert response.status_code == 200
        assert response.json() == {"status": "invalid_timestamp"}

        result = await db.execute(
            select(WebhookLog).where(WebhookLog.source == "remnawave").order_by(WebhookLog.created_at.desc())
        )
        log = result.scalar_one()
        assert log.is_valid is False
        assert log.error_message == "missing_timestamp"
        assert log.event_type == "user.created"

    @pytest.mark.integration
    async def test_remnawave_webhook_broadcasts_only_allowlisted_payload(
        self,
        async_client,
        monkeypatch,
    ):
        secret = "test-remnawave-webhook-secret"
        broadcast_spy = _BroadcastSpy()
        monkeypatch.setattr(settings, "remnawave_webhook_secret", SecretStr(secret))
        monkeypatch.setattr(settings, "remnawave_webhook_max_age_seconds", 300)
        monkeypatch.setattr(settings, "remnawave_webhook_future_skew_seconds", 60)
        monkeypatch.setattr(remnawave_webhook_use_case, "ws_manager", broadcast_spy)

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

        response = await async_client.post(
            "/api/v1/webhooks/remnawave",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Remnawave-Signature": signature,
                "X-Remnawave-Timestamp": timestamp,
            },
        )

        assert response.status_code == 200
        assert response.json() == {"status": "processed", "event": "user.updated"}
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

    @pytest.mark.integration
    async def test_remnawave_webhook_rejects_missing_timestamp_for_current_headers(
        self,
        async_client,
        db: AsyncSession,
        monkeypatch,
    ):
        secret = "test-remnawave-webhook-secret"
        monkeypatch.setattr(settings, "remnawave_webhook_secret", SecretStr(secret))
        monkeypatch.setattr(settings, "remnawave_webhook_max_age_seconds", 300)
        monkeypatch.setattr(settings, "remnawave_webhook_future_skew_seconds", 60)

        body = json.dumps({"event": "node.updated", "data": {"uuid": "node-1"}}).encode()
        signature = _sign(secret, body)

        response = await async_client.post(
            "/api/v1/webhooks/remnawave",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Remnawave-Signature": signature,
            },
        )

        assert response.status_code == 200
        assert response.json() == {"status": "invalid_timestamp"}

        result = await db.execute(
            select(WebhookLog).where(WebhookLog.source == "remnawave").order_by(WebhookLog.created_at.desc())
        )
        log = result.scalar_one()
        assert log.is_valid is False
        assert log.error_message == "missing_timestamp"

    @pytest.mark.integration
    async def test_remnawave_webhook_rejects_invalid_signature(
        self,
        async_client,
        db: AsyncSession,
        monkeypatch,
    ):
        secret = "test-remnawave-webhook-secret"
        monkeypatch.setattr(settings, "remnawave_webhook_secret", SecretStr(secret))
        monkeypatch.setattr(settings, "remnawave_webhook_max_age_seconds", 300)
        monkeypatch.setattr(settings, "remnawave_webhook_future_skew_seconds", 60)

        body = json.dumps({"event": "node.updated", "data": {"uuid": "node-1"}}).encode()
        timestamp = str(int(datetime.now(UTC).timestamp()))

        response = await async_client.post(
            "/api/v1/webhooks/remnawave",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Remnawave-Signature": "deadbeef",
                "X-Remnawave-Timestamp": timestamp,
            },
        )

        assert response.status_code == 200
        assert response.json() == {"status": "invalid_signature"}

        result = await db.execute(
            select(WebhookLog).where(WebhookLog.source == "remnawave").order_by(WebhookLog.created_at.desc())
        )
        log = result.scalar_one()
        assert log.is_valid is False
        assert log.error_message == "invalid_signature"
