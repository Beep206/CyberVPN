from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import WebSocketException
from redis.exceptions import RedisError

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("REMNAWAVE_TOKEN", "local-remnawave-token")
os.environ.setdefault("CRYPTOBOT_TOKEN", "local-cryptobot-token")
os.environ.setdefault("JWT_SECRET", "0123456789abcdef0123456789abcdef")

from src.application.services.ws_ticket_service import MESSAGING_REALTIME_TICKET_SCOPE, TicketData
from src.infrastructure.messaging import nats_messaging_runtime
from src.infrastructure.messaging.presence import MessagingPresenceIdentity, MessagingPresenceRegistry
from src.infrastructure.messaging.sse_manager import SSEManager
from src.presentation.api.v1.messaging import routes as messaging_routes


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, tuple[str, int | None]] = {}
        self.sets: dict[str, set[str]] = {}
        self.expirations: dict[str, int] = {}

    async def set(self, key: str, value: str, *, ex: int | None = None) -> bool:
        self.values[key] = (value, ex)
        return True

    async def sadd(self, key: str, member: str) -> int:
        self.sets.setdefault(key, set()).add(member)
        return 1

    async def expire(self, key: str, ttl: int) -> bool:
        self.expirations[key] = ttl
        return True

    async def delete(self, key: str) -> int:
        return 1 if self.values.pop(key, None) is not None else 0

    async def srem(self, key: str, *members: str) -> int:
        existing = self.sets.setdefault(key, set())
        before = len(existing)
        existing.difference_update(members)
        return before - len(existing)

    async def smembers(self, key: str) -> set[str]:
        return set(self.sets.get(key, set()))

    async def exists(self, key: str) -> int:
        return int(key in self.values)


class _FailingRedis(_FakeRedis):
    async def set(self, key: str, value: str, *, ex: int | None = None) -> bool:
        raise RedisError("redis unavailable")


@pytest.mark.asyncio
async def test_presence_registry_uses_ttl_and_connection_index() -> None:
    redis = _FakeRedis()
    registry = MessagingPresenceRegistry(redis, ttl_seconds=45)  # type: ignore[arg-type]
    identity = MessagingPresenceIdentity(
        participant_type="customer",
        participant_id="customer-1",
        connection_id="connection-1",
        transport="websocket",
    )

    assert await registry.register(identity) is True

    assert redis.values["messaging:presence:customer:customer-1:connection-1"][1] == 45
    assert redis.sets["messaging:presence:index:customer:customer-1"] == {"connection-1"}
    assert redis.expirations["messaging:presence:index:customer:customer-1"] == 45
    assert await registry.connection_count(participant_type="customer", participant_id="customer-1") == 1

    assert await registry.disconnect(identity) is True
    assert redis.sets["messaging:presence:index:customer:customer-1"] == set()


@pytest.mark.asyncio
async def test_presence_registry_degrades_without_rejecting_connection() -> None:
    registry = MessagingPresenceRegistry(_FailingRedis(), ttl_seconds=45)  # type: ignore[arg-type]
    identity = MessagingPresenceIdentity(
        participant_type="admin",
        participant_id="admin-1",
        connection_id="connection-1",
        transport="sse",
    )

    assert await registry.register(identity) is False


@pytest.mark.asyncio
async def test_sse_manager_streams_event_and_heartbeat() -> None:
    manager = SSEManager()
    stream = manager.create_stream("messaging:customer:customer-1", heartbeat_interval_seconds=0.01)

    first_chunk = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)
    await manager.broadcast_event("messaging:customer:customer-1", "message.created", {"event_id": "evt-1"})
    assert await first_chunk == 'event: message.created\ndata: {"event_id":"evt-1"}\n\n'
    assert await anext(stream) == "event: ping\ndata: {}\n\n"

    await stream.aclose()


@pytest.mark.asyncio
async def test_messaging_ws_auth_rejects_missing_or_wrong_principal_ticket(monkeypatch: pytest.MonkeyPatch) -> None:
    class _TicketService:
        def __init__(self, _redis) -> None:
            pass

        async def validate_and_consume(self, ticket: str, _client_ip: str | None):
            if ticket == "admin-ticket":
                return TicketData(
                    user_id="admin-1",
                    role="admin",
                    login="admin",
                    created_at=messaging_routes.datetime.now(messaging_routes.UTC),
                    principal_type="admin",
                    scope=MESSAGING_REALTIME_TICKET_SCOPE,
                )
            return None

    monkeypatch.setattr(messaging_routes, "WebSocketTicketService", _TicketService)
    websocket = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))

    with pytest.raises(WebSocketException):
        await messaging_routes._authenticate_messaging_ws_ticket(
            websocket=websocket,  # type: ignore[arg-type]
            ticket=None,
            expected_principal_type="customer",
            redis_client=AsyncMock(),
        )

    with pytest.raises(WebSocketException):
        await messaging_routes._authenticate_messaging_ws_ticket(
            websocket=websocket,  # type: ignore[arg-type]
            ticket="admin-ticket",
            expected_principal_type="customer",
            redis_client=AsyncMock(),
        )


@pytest.mark.asyncio
async def test_messaging_ws_auth_rejects_generic_admin_ticket_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    class _TicketService:
        def __init__(self, _redis) -> None:
            pass

        async def validate_and_consume(self, ticket: str, _client_ip: str | None):
            return TicketData(
                user_id="admin-1",
                role="admin",
                login="admin",
                created_at=messaging_routes.datetime.now(messaging_routes.UTC),
                principal_type="admin",
            )

    monkeypatch.setattr(messaging_routes, "WebSocketTicketService", _TicketService)
    websocket = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))

    with pytest.raises(WebSocketException):
        await messaging_routes._authenticate_messaging_ws_ticket(
            websocket=websocket,  # type: ignore[arg-type]
            ticket="generic-admin-ticket",
            expected_principal_type="admin",
            redis_client=AsyncMock(),
        )


@pytest.mark.asyncio
async def test_messaging_ws_subscribe_rejects_cross_principal_channel() -> None:
    websocket = SimpleNamespace(sent=[])

    async def send_json(payload):
        websocket.sent.append(payload)

    websocket.send_json = send_json
    principal = messaging_routes.MessagingRealtimePrincipal(principal_type="customer", principal_id="customer-1")

    await messaging_routes._handle_realtime_ws_message(
        websocket=websocket,  # type: ignore[arg-type]
        principal=principal,
        raw_message='{"type":"subscribe","channels":["messaging:admin:admin-1","self"]}',
    )

    assert websocket.sent == [
        {
            "type": "error",
            "code": "UNAUTHORIZED_CHANNEL",
            "channel": "messaging:admin:admin-1",
        },
        {"type": "subscribed", "channel": "self"},
    ]


@pytest.mark.asyncio
async def test_dispatcher_deduplicates_recipients_and_sanitizes_customer_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeWSManager:
        def __init__(self) -> None:
            self.sent: list[tuple[str, dict]] = []

        async def broadcast(self, channel: str, data: dict) -> None:
            self.sent.append((channel, data))

    class _FakeSSEManager:
        def __init__(self) -> None:
            self.sent: list[tuple[str, str, dict]] = []

        async def broadcast_event(self, channel: str, event: str, data: dict) -> None:
            self.sent.append((channel, event, data))

    ws = _FakeWSManager()
    sse = _FakeSSEManager()
    monkeypatch.setattr(nats_messaging_runtime, "ws_manager", ws)
    monkeypatch.setattr(nats_messaging_runtime, "sse_manager", sse)

    payload = {
        "event_id": "evt-1",
        "event_type": "messaging.message.created",
        "occurred_at": "2026-05-31T00:00:00Z",
        "aggregate_type": "messaging_message",
        "aggregate_id": "message-1",
        "payload": {
            "conversation_id": "conversation-1",
            "customer_account_id": "customer-1",
            "sender_id": "admin-1",
            "assigned_admin_id": "admin-1",
            "recipient_refs": [
                {"type": "customer", "id": "customer-1"},
                {"type": "customer", "id": "customer-1"},
                {"type": "admin", "id": "admin-1"},
            ],
        },
    }

    count = await nats_messaging_runtime.MessagingRealtimeDispatcher().dispatch(payload)

    assert count == 2
    customer_message = ws.sent[0][1]
    assert ws.sent[0][0] == "messaging:customer:customer-1"
    assert "recipient_refs" not in customer_message["payload"]
    assert "sender_id" not in customer_message["payload"]
    assert "assigned_admin_id" not in customer_message["payload"]
    assert "customer_account_id" not in customer_message["payload"]
    assert ws.sent[1][0] == "messaging:admin:admin-1"
    assert sse.sent[0][1] == "messaging.message.created"
