from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from src.infrastructure.messaging import nats_messaging_runtime as runtime_module
from src.infrastructure.messaging.nats_messaging_runtime import (
    MessagingOutboxEnvelope,
    NatsMessagingRuntime,
    _build_subject,
)


def test_build_subject_uses_documented_consumer_scoped_subject_exception() -> None:
    subject = _build_subject(
        consumer_key="messaging_realtime_projection",
        event_name="messaging.message.created",
        schema_version=2,
    )

    assert subject == "messaging.messaging_realtime_projection.messaging.message.created.v2"


@pytest.mark.asyncio
async def test_publish_envelope_uses_messaging_stream_and_nats_msg_id() -> None:
    class FakeAck:
        stream = "MESSAGING_EVENTS"
        sequence = 42
        duplicate = False

    class FakeJetStream:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        async def publish(self, subject, payload, **kwargs):
            self.calls.append({"subject": subject, "payload": payload, **kwargs})
            return FakeAck()

    runtime = NatsMessagingRuntime()
    fake_jetstream = FakeJetStream()
    runtime._jetstream = fake_jetstream
    envelope = MessagingOutboxEnvelope(
        consumer_key="messaging_realtime_projection",
        event_key="messaging.message.created:msg-001",
        event_name="messaging.message.created",
        event_family="messaging",
        aggregate_type="messaging_message",
        aggregate_id="msg-001",
        schema_version=1,
        subject="messaging.messaging_realtime_projection.messaging.message.created.v1",
        occurred_at=datetime(2026, 5, 31, 12, 0, tzinfo=UTC),
        actor_context={},
        source_context={"bounded_context": "messaging"},
        event_payload={"recipient_refs": [{"type": "customer", "id": "customer-001"}]},
    )

    ack = await runtime._publish_envelope(envelope)

    assert fake_jetstream.calls[0]["subject"] == envelope.subject
    assert fake_jetstream.calls[0]["stream"] == "MESSAGING_EVENTS"
    assert fake_jetstream.calls[0]["headers"] == {
        "Nats-Msg-Id": "messaging_realtime_projection:messaging.message.created:msg-001"
    }
    assert ack["broker_sequence"] == 42
    assert ack["idempotency_key"] == "messaging_realtime_projection:messaging.message.created:msg-001"


@pytest.mark.asyncio
async def test_process_message_suppresses_duplicate_consumer_receipt(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeRepo:
        created = False

        async def get_receipt(self, *, consumer_key: str, event_key: str):
            return object()

        async def create_receipt(self, **kwargs):
            self.created = True

    class FakeDispatcher:
        called = False

        async def dispatch(self, payload):
            self.called = True
            return 1

    payload = {
        "event_id": "evt-1",
        "event_type": "messaging.message.created",
        "subject": "messaging.messaging_realtime_projection.messaging.message.created.v1",
        "payload": {"recipient_refs": [{"type": "customer", "id": "customer-001"}]},
    }
    repo = FakeRepo()
    dispatcher = FakeDispatcher()
    monkeypatch.setattr(runtime_module, "OutboxConsumerReceiptRepository", lambda _session: repo)

    session_commits = 0

    async def commit():
        nonlocal session_commits
        session_commits += 1

    monkeypatch.setattr(runtime_module, "AsyncSessionLocal", lambda: _AsyncContext(SimpleNamespace(commit=commit)))

    runtime = NatsMessagingRuntime(realtime_dispatcher=dispatcher)
    raw_message = SimpleNamespace(data=json.dumps(payload).encode("utf-8"))

    await runtime._process_message(consumer_key="messaging_realtime_projection", raw_message=raw_message)

    assert dispatcher.called is False
    assert repo.created is False
    assert session_commits == 1


@pytest.mark.asyncio
async def test_process_message_records_receipt_after_realtime_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeRepo:
        def __init__(self) -> None:
            self.receipt: dict[str, object] | None = None

        async def get_receipt(self, *, consumer_key: str, event_key: str):
            return None

        async def create_receipt(self, **kwargs):
            self.receipt = kwargs

    class FakeDispatcher:
        async def dispatch(self, payload):
            return 2

    payload = {
        "event_id": "evt-2",
        "event_type": "messaging.message.created",
        "subject": "messaging.messaging_realtime_projection.messaging.message.created.v1",
        "payload": {"recipient_refs": [{"type": "customer", "id": "customer-001"}]},
    }
    repo = FakeRepo()
    session = SimpleNamespace(commit=_noop_async)
    monkeypatch.setattr(runtime_module, "AsyncSessionLocal", lambda: _AsyncContext(session))
    monkeypatch.setattr(runtime_module, "OutboxConsumerReceiptRepository", lambda _session: repo)

    runtime = NatsMessagingRuntime(realtime_dispatcher=FakeDispatcher())
    raw_message = SimpleNamespace(data=json.dumps(payload).encode("utf-8"))

    await runtime._process_message(consumer_key="messaging_realtime_projection", raw_message=raw_message)

    assert repo.receipt is not None
    assert repo.receipt["consumer_key"] == "messaging_realtime_projection"
    assert repo.receipt["event_key"] == "evt-2"
    assert repo.receipt["metadata_payload"] == {"status": "processed", "dispatch_count": 2}


@pytest.mark.asyncio
async def test_mark_publication_failure_moves_to_dead_letter(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeRepo:
        failed = False
        dead_letter = False

        async def mark_publication_failed(self, **kwargs):
            self.failed = True

        async def mark_publication_dead_letter(self, **kwargs):
            self.dead_letter = True

    repo = FakeRepo()
    publication = SimpleNamespace(
        attempts=3,
        consumer_key="messaging_realtime_projection",
        outbox_event=SimpleNamespace(
            event_name="messaging.message.created",
            occurred_at=datetime(2026, 5, 31, 12, 0, tzinfo=UTC),
        ),
    )
    monkeypatch.setattr(runtime_module.settings, "outbox_dispatch_dead_letter_after_attempts", 3)

    result = await NatsMessagingRuntime()._mark_publication_failure(
        repo=repo,
        publication=publication,
        lease_owner="lease-1",
        exc=RuntimeError("nats unavailable"),
    )

    assert result == "dead_letter"
    assert repo.dead_letter is True
    assert repo.failed is False


class _AsyncContext:
    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, exc_type, exc, tb):
        return None


async def _noop_async() -> None:
    return None
