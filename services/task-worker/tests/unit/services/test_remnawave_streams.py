"""Deterministic contract and delivery tests for Remnawave Redis exports."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import UUID

import fakeredis.aioredis
import pytest
from redis.exceptions import ResponseError

from src.services.backend_api_client import (
    BackendAPIStreamPermanentError,
    BackendAPIStreamTransientError,
    BackendRemnawaveStreamGap,
    BackendRemnawaveStreamObservation,
)
from src.services.remnawave_streams import (
    NODE_CONNECTIONS_STREAM,
    REMNAWAVE_STREAMS,
    SUBSCRIPTION_REQUESTS_STREAM,
    USER_USAGE_STREAM,
    BackendRemnawaveStreamSink,
    NodeConnectionsEvent,
    PermanentSinkError,
    ReclaimBatch,
    RedactedDeadLetter,
    RedisStreamTransport,
    RemnawaveStreamConsumer,
    RemnawaveStreamConsumerConfig,
    RemnawaveStreamEvent,
    StreamConsumerGroupInvariantError,
    StreamContractError,
    StreamMessage,
    StreamPayloadLimits,
    StreamRuntimeState,
    SubscriptionRequestEvent,
    TransientSinkError,
    UserUsageEvent,
    parse_stream_event,
)

FIXED_NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
TEST_HMAC_KEY = b"task-worker-stream-hmac-key-for-tests-0001"
OTHER_HMAC_KEY = b"task-worker-stream-hmac-key-for-tests-0002"


def _usage_fields(*, version: str = "1") -> dict[str, str]:
    return {
        "v": version,
        "nodeId": "17",
        "ts": "2026-08-30T11:59:00.000Z",
        "records": "42:1024;43:0",
    }


def _subscription_request_fields(*, version: str = "1") -> dict[str, str]:
    return {
        "v": version,
        "userId": "42",
        "requestAt": "2026-08-30T11:59:30.000Z",
        "requestIp": "198.51.100.42",
        "userAgent": "CyberVPN-Private-UA/1",
        "srrResponseType": "ALLOW",
    }


class _FakeSink:
    def __init__(self, order: list[str] | None = None) -> None:
        self.persisted: list[tuple[RemnawaveStreamEvent, str]] = []
        self.persisted_dead_letters: list[RedactedDeadLetter] = []
        self.error: Exception | None = None
        self.dead_letter_error: Exception | None = None
        self.gap_error: Exception | None = None
        self.runtime_error: Exception | None = None
        self.recorded_gaps: list[tuple[str, tuple[str, ...], datetime]] = []
        self.runtime_observations: list[tuple[str, StreamRuntimeState, datetime]] = []
        self.order = order

    async def persist(self, event: RemnawaveStreamEvent, *, idempotency_key: str) -> None:
        if self.order is not None:
            self.order.append("persist")
        if self.error is not None:
            raise self.error
        self.persisted.append((event, idempotency_key))

    async def persist_dead_letter(self, dead_letter: RedactedDeadLetter) -> None:
        if self.order is not None:
            self.order.append("postgres_dlq")
        if self.dead_letter_error is not None:
            raise self.dead_letter_error
        self.persisted_dead_letters.append(dead_letter)

    async def record_gap(
        self,
        stream: str,
        missing_message_ids: Sequence[str],
        *,
        detected_at: datetime,
    ) -> None:
        if self.order is not None:
            self.order.append("postgres_gap")
        if self.gap_error is not None:
            raise self.gap_error
        self.recorded_gaps.append((stream, tuple(missing_message_ids), detected_at))

    async def observe_runtime(
        self,
        stream: str,
        state: StreamRuntimeState,
        *,
        observed_at: datetime,
    ) -> None:
        if self.runtime_error is not None:
            raise self.runtime_error
        self.runtime_observations.append((stream, state, observed_at))


class _FakeTransport:
    def __init__(self, order: list[str] | None = None) -> None:
        self.new_messages: tuple[StreamMessage, ...] = ()
        self.reclaim_batches: dict[str, ReclaimBatch] = {}
        self.groups: list[tuple[str, str, str]] = []
        self.acked: list[tuple[str, str, str]] = []
        self.deleted: list[tuple[str, str]] = []
        self.dead_letters: list[tuple[RedactedDeadLetter, int]] = []
        self.ack_error: Exception | None = None
        self.purge_requests: list[tuple[str, datetime, int]] = []
        self.order = order
        self.runtime_states: dict[str, StreamRuntimeState] = {}
        self.read_error: Exception | None = None

    async def runtime_state(self, stream: str, group: str) -> StreamRuntimeState:
        del group
        return self.runtime_states.get(
            stream,
            StreamRuntimeState(
                observed_stream_identity="test-run-id",
                stream_exists=True,
                group_exists=True,
                first_message_id=None,
                last_message_id=None,
                group_last_delivered_id=None,
                group_pending_count=0,
                group_pending_min_id=None,
                group_pending_max_id=None,
            ),
        )

    async def ensure_group(self, stream: str, group: str, start_id: str) -> None:
        self.groups.append((stream, group, start_id))

    async def read_new(
        self,
        streams: Sequence[str],
        group: str,
        consumer: str,
        *,
        count: int,
        block_ms: int,
    ) -> tuple[StreamMessage, ...]:
        del streams, group, consumer, count, block_ms
        if self.read_error is not None:
            raise self.read_error
        messages, self.new_messages = self.new_messages, ()
        return messages

    async def reclaim(
        self,
        stream: str,
        group: str,
        consumer: str,
        *,
        min_idle_ms: int,
        count: int,
    ) -> ReclaimBatch:
        del group, consumer, min_idle_ms, count
        return self.reclaim_batches.pop(stream, ReclaimBatch(()))

    async def ack(self, stream: str, group: str, message_id: str) -> None:
        if self.order is not None:
            self.order.append("ack")
        if self.ack_error is not None:
            raise self.ack_error
        self.acked.append((stream, group, message_id))

    async def ack_and_delete(self, stream: str, group: str, message_id: str) -> None:
        if self.order is not None:
            self.order.append("ack_delete")
        if self.ack_error is not None:
            raise self.ack_error
        self.acked.append((stream, group, message_id))
        self.deleted.append((stream, message_id))

    async def dead_letter_and_ack(
        self,
        stream: str,
        group: str,
        message_id: str,
        dead_letter: RedactedDeadLetter,
        *,
        maxlen: int,
    ) -> None:
        if self.order is not None:
            self.order.append("redis_dlq_ack")
        self.dead_letters.append((dead_letter, maxlen))
        self.acked.append((stream, group, message_id))
        if stream == SUBSCRIPTION_REQUESTS_STREAM:
            self.deleted.append((stream, message_id))

    async def pending_count(self, stream: str, group: str) -> int:
        del stream, group
        return 0

    async def purge_dead_letters(self, stream: str, *, expires_before: datetime, count: int) -> int:
        self.purge_requests.append((stream, expires_before, count))
        return 0


class _FakeObserver:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str, float]] = []
        self.retries: list[str] = []
        self.dead_letters: list[tuple[str, str]] = []
        self.reclaimed_messages: list[tuple[str, str, int]] = []
        self.pending_counts: list[tuple[str, int]] = []
        self.lags: list[tuple[str, float]] = []
        self.retention_purges: list[tuple[str, str, int]] = []

    def message(self, stream: str, outcome: str, duration_seconds: float) -> None:
        self.messages.append((stream, outcome, duration_seconds))

    def retry(self, stream: str) -> None:
        self.retries.append(stream)

    def dead_letter(self, stream: str, reason: str) -> None:
        self.dead_letters.append((stream, reason))

    def reclaimed(self, stream: str, outcome: str, count: int = 1) -> None:
        self.reclaimed_messages.append((stream, outcome, count))

    def pending(self, stream: str, count: int) -> None:
        self.pending_counts.append((stream, count))

    def lag(self, stream: str, seconds: float) -> None:
        self.lags.append((stream, seconds))

    def retention_purged(self, stream: str, store: str, count: int) -> None:
        self.retention_purges.append((stream, store, count))


def _consumer(
    transport: _FakeTransport,
    sink: _FakeSink,
    observer: _FakeObserver,
    *,
    max_delivery_attempts: int = 5,
    receipt_retention_days: int = 50_000,
    hmac_key: bytes = TEST_HMAC_KEY,
) -> RemnawaveStreamConsumer:
    monotonic_values = iter((10.0, 10.25, *([10.25] * 100)))
    return RemnawaveStreamConsumer(
        transport,
        sink,
        RemnawaveStreamConsumerConfig(
            consumer_name="worker-test-1",
            payload_fingerprint_hmac_key=hmac_key,
            max_delivery_attempts=max_delivery_attempts,
            receipt_retention_days=receipt_retention_days,
        ),
        observer=observer,
        monotonic=monotonic_values.__next__,
        now=lambda: FIXED_NOW,
    )


def test_parse_all_remnawave_3_4_stream_contracts() -> None:
    usage = parse_stream_event(USER_USAGE_STREAM, _usage_fields())
    assert isinstance(usage, UserUsageEvent)
    assert usage.node_id == 17
    assert [(record.user_id, record.total_bytes) for record in usage.records] == [(42, 1024), (43, 0)]

    request = parse_stream_event(
        SUBSCRIPTION_REQUESTS_STREAM,
        {
            "v": "1",
            "userId": "42",
            "requestAt": "2026-08-30T11:59:30.000Z",
            "requestIp": "198.51.100.42",
            "userAgent": "CyberVPN-Test/1",
            "srrRuleName": "allow-paid",
            "srrResponseType": "ALLOW",
        },
    )
    assert isinstance(request, SubscriptionRequestEvent)
    assert request.user_id == 42
    assert request.srr_response_type == "ALLOW"

    connections = parse_stream_event(
        NODE_CONNECTIONS_STREAM,
        {
            "v": "1",
            "nodeId": "17",
            "ts": "2026-08-30T11:59:45.000Z",
            "users": ('[{"userId":"42","ips":[{"ip":"2001:db8::42","lastSeen":"2026-08-30T11:59:40.000Z"}]}]'),
        },
    )
    assert isinstance(connections, NodeConnectionsEvent)
    assert connections.node_id == 17
    assert connections.users[0].user_id == 42
    assert connections.users[0].ips[0].ip == "2001:db8::42"


def test_subscription_request_accepts_3_4_1_producer_typo_alias() -> None:
    event = parse_stream_event(
        SUBSCRIPTION_REQUESTS_STREAM,
        {
            "v": "1",
            "userId": "42",
            "requestAt": "2026-08-30T11:59:30.000Z",
            "ssrResponseType": "BLOCK",
        },
    )

    assert isinstance(event, SubscriptionRequestEvent)
    assert event.srr_response_type == "BLOCK"


def test_subscription_request_rejects_conflicting_contract_and_producer_keys() -> None:
    with pytest.raises(StreamContractError) as exc_info:
        parse_stream_event(
            SUBSCRIPTION_REQUESTS_STREAM,
            {
                "v": "1",
                "userId": "42",
                "requestAt": "2026-08-30T11:59:30.000Z",
                "srrResponseType": "ALLOW",
                "ssrResponseType": "BLOCK",
            },
        )

    assert exc_info.value.code == "invalid_payload"


@pytest.mark.parametrize(
    ("stream", "fields", "expected_code"),
    [
        (USER_USAGE_STREAM, _usage_fields(version="2"), "unsupported_schema_version"),
        (USER_USAGE_STREAM, {**_usage_fields(), "records": "42:not-a-number"}, "invalid_payload"),
        (
            NODE_CONNECTIONS_STREAM,
            {
                "v": "1",
                "nodeId": "17",
                "ts": "2026-08-30T11:59:45.000Z",
                "users": ('[{"userId":"42","ips":[{"ip":"not-an-ip","lastSeen":"2026-08-30T11:59:40.000Z"}]}]'),
            },
            "invalid_payload",
        ),
    ],
)
def test_parse_rejects_unknown_versions_and_malformed_payloads(
    stream: str,
    fields: dict[str, str],
    expected_code: str,
) -> None:
    with pytest.raises(StreamContractError) as exc_info:
        parse_stream_event(stream, fields)

    assert exc_info.value.code == expected_code


def test_parse_enforces_bounded_record_and_message_sizes() -> None:
    with pytest.raises(StreamContractError) as record_error:
        parse_stream_event(
            USER_USAGE_STREAM,
            _usage_fields(),
            StreamPayloadLimits(max_usage_records=1),
        )
    assert record_error.value.code == "invalid_payload"

    with pytest.raises(StreamContractError) as size_error:
        parse_stream_event(
            USER_USAGE_STREAM,
            _usage_fields(),
            StreamPayloadLimits(max_message_bytes=8),
        )
    assert size_error.value.code == "payload_too_large"


@pytest.mark.asyncio
async def test_consumer_acks_only_after_durable_sink_returns() -> None:
    order: list[str] = []
    transport = _FakeTransport(order)
    transport.new_messages = (StreamMessage(USER_USAGE_STREAM, "1000-1", _usage_fields()),)
    sink = _FakeSink(order)
    observer = _FakeObserver()

    processed = await _consumer(transport, sink, observer).consume_new_once()

    assert processed == 1
    assert order == ["persist", "ack"]
    assert sink.persisted[0][1] == "remnawave:user_usage:1000-1"
    assert transport.acked == [(USER_USAGE_STREAM, "cybervpn-remnawave-v1", "1000-1")]
    assert observer.messages == [(USER_USAGE_STREAM, "persisted", 0.25)]
    assert observer.pending_counts == [(stream, 0) for stream in REMNAWAVE_STREAMS]
    assert transport.purge_requests == [(stream, FIXED_NOW - timedelta(days=14), 100) for stream in REMNAWAVE_STREAMS]


@pytest.mark.asyncio
async def test_subscription_request_is_atomically_acked_and_deleted_only_after_durable_sink_returns() -> None:
    order: list[str] = []
    transport = _FakeTransport(order)
    transport.new_messages = (StreamMessage(SUBSCRIPTION_REQUESTS_STREAM, "1000-11", _subscription_request_fields()),)
    sink = _FakeSink(order)

    await _consumer(transport, sink, _FakeObserver()).consume_new_once()

    assert order == ["persist", "ack_delete"]
    assert sink.persisted[0][1] == "remnawave:subscription_requests:1000-11"
    assert transport.acked == [(SUBSCRIPTION_REQUESTS_STREAM, "cybervpn-remnawave-v1", "1000-11")]
    assert transport.deleted == [(SUBSCRIPTION_REQUESTS_STREAM, "1000-11")]


@pytest.mark.asyncio
async def test_transient_sink_failure_stays_pending_before_retry_budget_is_exhausted() -> None:
    transport = _FakeTransport()
    transport.new_messages = (StreamMessage(USER_USAGE_STREAM, "1000-2", _usage_fields(), delivery_count=2),)
    sink = _FakeSink()
    sink.error = TransientSinkError("database temporarily unavailable")
    observer = _FakeObserver()

    await _consumer(transport, sink, observer, max_delivery_attempts=3).consume_new_once()

    assert transport.acked == []
    assert transport.dead_letters == []
    assert observer.retries == [USER_USAGE_STREAM]
    assert observer.messages[0][1] == "retry_pending"


@pytest.mark.asyncio
async def test_transient_outage_past_retry_budget_never_discards_raw_event() -> None:
    sensitive_value = "198.51.100.42 private-user-agent"
    fields = {
        "v": "1",
        "userId": "42",
        "requestAt": "2026-08-30T11:59:30.000Z",
        "requestIp": "198.51.100.42",
        "userAgent": sensitive_value,
        "srrResponseType": "ALLOW",
    }
    order: list[str] = []
    transport = _FakeTransport(order)
    transport.new_messages = (StreamMessage(SUBSCRIPTION_REQUESTS_STREAM, "1000-3", fields, delivery_count=3),)
    sink = _FakeSink(order)
    sink.error = TransientSinkError("database temporarily unavailable")
    observer = _FakeObserver()

    await _consumer(transport, sink, observer, max_delivery_attempts=3).consume_new_once()

    assert sensitive_value not in str(observer.messages)
    assert transport.dead_letters == []
    assert transport.acked == []
    assert transport.deleted == []
    assert sink.persisted_dead_letters == []
    assert order == ["persist"]
    assert observer.retries == [SUBSCRIPTION_REQUESTS_STREAM]
    assert observer.messages[0][1] == "retry_exhausted_pending"


@pytest.mark.asyncio
async def test_untrusted_schema_value_is_never_copied_to_dead_letter() -> None:
    untrusted_schema = "malformed-value-that-must-not-be-reflected"
    transport = _FakeTransport()
    transport.new_messages = (
        StreamMessage(
            USER_USAGE_STREAM,
            "1000-31",
            _usage_fields(version=untrusted_schema),
            delivery_count=1,
        ),
    )
    sink = _FakeSink()

    await _consumer(transport, sink, _FakeObserver()).consume_new_once()

    dead_letter = transport.dead_letters[0][0]
    assert dead_letter.schema_version == "invalid"
    assert untrusted_schema not in json.dumps(dead_letter.fields(), sort_keys=True)


@pytest.mark.asyncio
async def test_subscription_terminal_dlq_commits_redacted_receipt_before_atomic_source_removal() -> None:
    order: list[str] = []
    transport = _FakeTransport(order)
    transport.new_messages = (
        StreamMessage(
            SUBSCRIPTION_REQUESTS_STREAM,
            "1000-33",
            _subscription_request_fields(version="2"),
            delivery_count=1,
        ),
    )
    sink = _FakeSink(order)

    await _consumer(transport, sink, _FakeObserver()).consume_new_once()

    assert order == ["postgres_dlq", "redis_dlq_ack"]
    assert transport.deleted == [(SUBSCRIPTION_REQUESTS_STREAM, "1000-33")]
    redacted_wire = json.dumps(transport.dead_letters[0][0].fields(), sort_keys=True)
    for raw_value in ("requestIp", "198.51.100.42", "userAgent", "CyberVPN-Private-UA/1"):
        assert raw_value not in redacted_wire


@pytest.mark.asyncio
async def test_dead_letter_backend_failure_leaves_source_pending_and_skips_redis_dlq() -> None:
    transport = _FakeTransport()
    transport.new_messages = (
        StreamMessage(USER_USAGE_STREAM, "1000-30", _usage_fields(version="2"), delivery_count=3),
    )
    sink = _FakeSink()
    sink.dead_letter_error = TransientSinkError("postgres unavailable")

    with pytest.raises(TransientSinkError):
        await _consumer(transport, sink, _FakeObserver(), max_delivery_attempts=3).consume_new_once()

    assert transport.dead_letters == []
    assert transport.acked == []


@pytest.mark.asyncio
async def test_subscription_parse_failure_keeps_raw_source_when_durable_dlq_write_must_retry() -> None:
    transport = _FakeTransport()
    transport.new_messages = (
        StreamMessage(
            SUBSCRIPTION_REQUESTS_STREAM,
            "1000-32",
            _subscription_request_fields(version="2"),
            delivery_count=3,
        ),
    )
    sink = _FakeSink()
    sink.dead_letter_error = TransientSinkError("postgres unavailable")

    with pytest.raises(TransientSinkError):
        await _consumer(transport, sink, _FakeObserver(), max_delivery_attempts=3).consume_new_once()

    assert transport.dead_letters == []
    assert transport.acked == []
    assert transport.deleted == []


@pytest.mark.asyncio
async def test_permanent_sink_failure_is_dead_lettered_without_retry() -> None:
    transport = _FakeTransport()
    transport.new_messages = (StreamMessage(USER_USAGE_STREAM, "1000-4", _usage_fields()),)
    sink = _FakeSink()
    sink.error = PermanentSinkError("authoritative sink rejected event")
    observer = _FakeObserver()

    await _consumer(transport, sink, observer).consume_new_once()

    assert transport.dead_letters[0][0].reason == "permanent_sink_error"
    assert observer.retries == []


@pytest.mark.asyncio
async def test_ack_failure_after_commit_is_replayed_and_never_dead_lettered() -> None:
    order: list[str] = []
    transport = _FakeTransport(order)
    transport.new_messages = (StreamMessage(USER_USAGE_STREAM, "1000-5", _usage_fields(), delivery_count=5),)
    transport.ack_error = ConnectionError("Redis unavailable")
    sink = _FakeSink(order)
    observer = _FakeObserver()

    with pytest.raises(ConnectionError, match="Redis unavailable"):
        await _consumer(transport, sink, observer, max_delivery_attempts=5).consume_new_once()

    assert order == ["persist", "ack"]
    assert len(sink.persisted) == 1
    assert transport.dead_letters == []
    assert observer.messages[0][1] == "ack_failed"


@pytest.mark.asyncio
async def test_replay_after_commit_uses_the_same_sink_idempotency_key() -> None:
    class _IdempotentSink(_FakeSink):
        def __init__(self) -> None:
            super().__init__()
            self.calls: list[str] = []
            self.committed_keys: set[str] = set()

        async def persist(self, event: RemnawaveStreamEvent, *, idempotency_key: str) -> None:
            self.calls.append(idempotency_key)
            if idempotency_key in self.committed_keys:
                return
            self.committed_keys.add(idempotency_key)
            self.persisted.append((event, idempotency_key))

    transport = _FakeTransport()
    message = StreamMessage(USER_USAGE_STREAM, "1000-7", _usage_fields())
    transport.new_messages = (message,)
    transport.ack_error = ConnectionError("crash boundary")
    sink = _IdempotentSink()

    with pytest.raises(ConnectionError):
        await _consumer(transport, sink, _FakeObserver()).consume_new_once()

    transport.ack_error = None
    transport.new_messages = (StreamMessage(USER_USAGE_STREAM, "1000-7", _usage_fields(), delivery_count=2),)
    await _consumer(transport, sink, _FakeObserver()).consume_new_once()

    expected_key = "remnawave:user_usage:1000-7"
    assert sink.calls == [expected_key, expected_key]
    assert len(sink.persisted) == 1
    assert transport.acked == [(USER_USAGE_STREAM, "cybervpn-remnawave-v1", "1000-7")]


@pytest.mark.asyncio
async def test_reclaim_processes_idle_pending_message_with_delivery_count() -> None:
    transport = _FakeTransport()
    transport.reclaim_batches[USER_USAGE_STREAM] = ReclaimBatch(
        (StreamMessage(USER_USAGE_STREAM, "1000-6", _usage_fields(), delivery_count=4),),
        ("999-1",),
    )
    sink = _FakeSink()
    observer = _FakeObserver()

    reclaimed = await _consumer(transport, sink, observer).reclaim_once()

    assert reclaimed == 1
    assert len(sink.persisted) == 1
    assert (USER_USAGE_STREAM, "claimed", 1) in observer.reclaimed_messages
    assert (USER_USAGE_STREAM, "trimmed", 1) in observer.reclaimed_messages
    assert sink.recorded_gaps == [(USER_USAGE_STREAM, ("999-1",), FIXED_NOW)]


@pytest.mark.asyncio
async def test_reclaim_reconciles_stale_pending_before_receipt_replay() -> None:
    stale_milliseconds = int((FIXED_NOW - timedelta(days=15)).timestamp() * 1_000)
    message_id = f"{stale_milliseconds}-7"
    order: list[str] = []
    transport = _FakeTransport(order)
    transport.reclaim_batches[USER_USAGE_STREAM] = ReclaimBatch(
        (StreamMessage(USER_USAGE_STREAM, message_id, _usage_fields(), delivery_count=8),),
    )
    sink = _FakeSink(order)
    observer = _FakeObserver()

    reclaimed = await _consumer(
        transport,
        sink,
        observer,
        receipt_retention_days=14,
    ).reclaim_once()

    assert reclaimed == 1
    assert sink.persisted == []
    assert sink.recorded_gaps == [(USER_USAGE_STREAM, (message_id,), FIXED_NOW)]
    assert transport.acked == [(USER_USAGE_STREAM, "cybervpn-remnawave-v1", message_id)]
    assert order == ["postgres_gap", "ack"]
    assert observer.messages[0][1] == "stale_reconciled"


@pytest.mark.asyncio
async def test_stale_pending_gap_failure_never_acks_or_reapplies() -> None:
    stale_milliseconds = int((FIXED_NOW - timedelta(days=15)).timestamp() * 1_000)
    message_id = f"{stale_milliseconds}-8"
    transport = _FakeTransport()
    transport.reclaim_batches[USER_USAGE_STREAM] = ReclaimBatch(
        (StreamMessage(USER_USAGE_STREAM, message_id, _usage_fields(), delivery_count=8),),
    )
    sink = _FakeSink()
    sink.gap_error = TransientSinkError("authoritative reconciliation unavailable")

    observer = _FakeObserver()
    await _consumer(
        transport,
        sink,
        observer,
        receipt_retention_days=14,
    ).reclaim_once()

    assert sink.persisted == []
    assert transport.acked == []
    assert observer.retries == [USER_USAGE_STREAM]
    assert observer.messages[0][1] == "retry_exhausted_pending"


@pytest.mark.asyncio
async def test_reclaim_halts_before_processing_when_durable_gap_write_fails() -> None:
    transport = _FakeTransport()
    transport.reclaim_batches[USER_USAGE_STREAM] = ReclaimBatch(
        (StreamMessage(USER_USAGE_STREAM, "1000-6", _usage_fields(), delivery_count=4),),
        ("999-1",),
    )
    sink = _FakeSink()
    sink.gap_error = TransientSinkError("backend unavailable")
    consumer = _consumer(transport, sink, _FakeObserver())

    with pytest.raises(TransientSinkError, match="backend unavailable"):
        await consumer.reclaim_once()

    assert sink.persisted == []
    sink.gap_error = None
    await consumer.reclaim_once()
    assert sink.recorded_gaps == [(USER_USAGE_STREAM, ("999-1",), FIXED_NOW)]


@pytest.mark.asyncio
async def test_initialize_observes_missing_streams_before_idempotent_group_repair() -> None:
    transport = _FakeTransport()
    missing_state = StreamRuntimeState(
        observed_stream_identity="new-valkey-run",
        stream_exists=False,
        group_exists=False,
        first_message_id=None,
        last_message_id=None,
        group_last_delivered_id=None,
        group_pending_count=0,
        group_pending_min_id=None,
        group_pending_max_id=None,
    )
    transport.runtime_states = {stream: missing_state for stream in REMNAWAVE_STREAMS}
    sink = _FakeSink()

    await _consumer(transport, sink, _FakeObserver()).initialize()

    assert [item[0] for item in sink.runtime_observations] == list(REMNAWAVE_STREAMS)
    assert transport.groups == [(stream, "cybervpn-remnawave-v1", "0-0") for stream in REMNAWAVE_STREAMS]


@pytest.mark.asyncio
async def test_initialize_never_repairs_group_before_checkpoint_commit() -> None:
    transport = _FakeTransport()
    sink = _FakeSink()
    sink.runtime_error = TransientSinkError("checkpoint unavailable")

    with pytest.raises(TransientSinkError, match="checkpoint unavailable"):
        await _consumer(transport, sink, _FakeObserver()).initialize()

    assert transport.groups == []


@pytest.mark.asyncio
async def test_runtime_nogroup_is_observed_and_repaired_without_permanent_stall() -> None:
    transport = _FakeTransport()
    sink = _FakeSink()
    consumer = _consumer(transport, sink, _FakeObserver())
    await consumer.initialize()
    initial_observations = len(sink.runtime_observations)
    missing_state = StreamRuntimeState(
        observed_stream_identity="post-flush-run",
        stream_exists=False,
        group_exists=False,
        first_message_id=None,
        last_message_id=None,
        group_last_delivered_id=None,
        group_pending_count=0,
        group_pending_min_id=None,
        group_pending_max_id=None,
    )
    transport.runtime_states = {stream: missing_state for stream in REMNAWAVE_STREAMS}
    transport.read_error = ResponseError("NOGROUP No such key or consumer group")

    assert await consumer.consume_new_once() == 0
    assert len(sink.runtime_observations) == initial_observations + len(REMNAWAVE_STREAMS)
    assert transport.groups[-3:] == [(stream, "cybervpn-remnawave-v1", "0-0") for stream in REMNAWAVE_STREAMS]


@pytest.mark.asyncio
async def test_initialize_is_idempotent_at_transport_boundary() -> None:
    transport = _FakeTransport()
    consumer = _consumer(transport, _FakeSink(), _FakeObserver())

    await consumer.initialize()
    await consumer.initialize()

    expected = [(stream, "cybervpn-remnawave-v1", "0-0") for stream in (*REMNAWAVE_STREAMS, *REMNAWAVE_STREAMS)]
    assert transport.groups == expected


@pytest.mark.asyncio
async def test_backend_sink_serializes_all_typed_event_dtos() -> None:
    backend = AsyncMock()
    sink = BackendRemnawaveStreamSink(backend)
    usage = parse_stream_event(USER_USAGE_STREAM, _usage_fields())
    subscription = parse_stream_event(
        SUBSCRIPTION_REQUESTS_STREAM,
        {
            "v": "1",
            "userId": "42",
            "requestAt": "2026-08-30T11:59:30.000Z",
            "requestIp": "198.51.100.42",
            "userAgent": "CyberVPN-Test/1",
            "srrResponseType": "ALLOW",
        },
    )
    connections = parse_stream_event(
        NODE_CONNECTIONS_STREAM,
        {
            "v": "1",
            "nodeId": "17",
            "ts": "2026-08-30T11:59:45.000Z",
            "users": ('[{"userId":"42","ips":[{"ip":"2001:db8::42","lastSeen":"2026-08-30T11:59:40.000Z"}]}]'),
        },
    )

    await sink.persist(usage, idempotency_key="remnawave:user_usage:1000-10")
    await sink.persist(
        subscription,
        idempotency_key="remnawave:subscription_requests:1000-11",
    )
    await sink.persist(
        connections,
        idempotency_key="remnawave:node_connections:1000-12",
    )

    payloads = [call.args[0] for call in backend.persist_remnawave_stream_event.await_args_list]
    assert payloads[0] == {
        "event_type": "user_usage",
        "schema_version": "1",
        "node_id": 17,
        "observed_at": "2026-08-30T11:59:00+00:00",
        "records": [
            {"user_id": 42, "total_bytes": 1024},
            {"user_id": 43, "total_bytes": 0},
        ],
    }
    assert payloads[1]["event_type"] == "subscription_requests"
    assert payloads[1]["request_ip"] == "198.51.100.42"
    assert payloads[2]["event_type"] == "node_connections"
    assert payloads[2]["users"][0]["ips"][0]["ip"] == "2001:db8::42"


@pytest.mark.asyncio
async def test_backend_sink_persists_only_redacted_dead_letter_metadata() -> None:
    backend = AsyncMock()
    sink = BackendRemnawaveStreamSink(backend)
    dead_letter = RedactedDeadLetter(
        stream=SUBSCRIPTION_REQUESTS_STREAM,
        message_id="1000-14",
        schema_version="1",
        reason="invalid_payload",
        error_type="StreamContractError",
        payload_hmac_sha256="a" * 64,
        delivery_count=4,
        failed_at=FIXED_NOW,
    )

    await sink.persist_dead_letter(dead_letter)

    backend.persist_remnawave_dead_letter.assert_awaited_once_with(
        {
            "stream_name": "subscription_requests",
            "message_id": "1000-14",
            "schema_version": "1",
            "error_type": "StreamContractError",
            "redacted_reason": "invalid_payload",
            "payload_fingerprint": "a" * 64,
            "attempts": 4,
        }
    )


@pytest.mark.asyncio
async def test_backend_sink_reconciles_exact_gap_before_returning() -> None:
    backend = AsyncMock()
    gap_id = UUID("11111111-1111-4111-8111-111111111111")
    backend.create_remnawave_stream_gap.return_value = BackendRemnawaveStreamGap(
        gap_id=gap_id,
        stream_name="user_usage",
        reconciliation_status="pending",
    )
    backend.reconcile_remnawave_stream_gap.return_value = BackendRemnawaveStreamGap(
        gap_id=gap_id,
        stream_name="user_usage",
        reconciliation_status="partial",
    )
    sink = BackendRemnawaveStreamSink(backend)

    await sink.record_gap(USER_USAGE_STREAM, ("1000-99",), detected_at=FIXED_NOW)

    backend.create_remnawave_stream_gap.assert_awaited_once()
    backend.reconcile_remnawave_stream_gap.assert_awaited_once_with(
        gap_id=gap_id,
        stream_name="user_usage",
    )


@pytest.mark.asyncio
async def test_backend_sink_reconciles_latched_checkpoint_before_group_repair() -> None:
    backend = AsyncMock()
    gap_id = UUID("22222222-2222-4222-8222-222222222222")
    backend.observe_remnawave_stream_checkpoint.return_value = BackendRemnawaveStreamObservation(
        loss_detected=True,
        loss_reason="gap_pending_reconciliation",
        gap_id=gap_id,
        reconciliation_status="running",
    )
    backend.reconcile_remnawave_stream_gap.return_value = BackendRemnawaveStreamGap(
        gap_id=gap_id,
        stream_name="node_connections",
        reconciliation_status="partial",
    )
    sink = BackendRemnawaveStreamSink(backend)
    state = StreamRuntimeState(
        observed_stream_identity="new-valkey-run",
        stream_exists=False,
        group_exists=False,
        first_message_id=None,
        last_message_id=None,
        group_last_delivered_id=None,
        group_pending_count=0,
        group_pending_min_id=None,
        group_pending_max_id=None,
    )

    await sink.observe_runtime(NODE_CONNECTIONS_STREAM, state, observed_at=FIXED_NOW)

    backend.reconcile_remnawave_stream_gap.assert_awaited_once_with(
        gap_id=gap_id,
        stream_name="node_connections",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("backend_error", "sink_error"),
    [
        (BackendAPIStreamPermanentError("conflict"), PermanentSinkError),
        (BackendAPIStreamTransientError("disabled"), TransientSinkError),
    ],
)
async def test_backend_sink_maps_http_failure_classes(
    backend_error: Exception,
    sink_error: type[Exception],
) -> None:
    backend = AsyncMock()
    backend.persist_remnawave_stream_event.side_effect = backend_error
    sink = BackendRemnawaveStreamSink(backend)
    event = parse_stream_event(USER_USAGE_STREAM, _usage_fields())

    with pytest.raises(sink_error):
        await sink.persist(event, idempotency_key="remnawave:user_usage:1000-13")


@pytest.mark.asyncio
async def test_redis_transport_creates_group_reads_and_atomically_dead_letters() -> None:
    redis = fakeredis.aioredis.FakeRedis(decode_responses=False)
    transport = RedisStreamTransport(redis, payload_fingerprint_hmac_key=TEST_HMAC_KEY)
    group = "contract-test-group"
    await transport.ensure_group(USER_USAGE_STREAM, group, "0-0")
    message_id = await redis.xadd(USER_USAGE_STREAM, _usage_fields())

    messages = await transport.read_new(
        (USER_USAGE_STREAM,),
        group,
        "consumer-a",
        count=1,
        block_ms=1,
    )
    assert len(messages) == 1
    assert messages[0].message_id == message_id.decode()
    assert await transport.pending_count(USER_USAGE_STREAM, group) == 1

    dead_letter = RedactedDeadLetter(
        stream=USER_USAGE_STREAM,
        message_id=messages[0].message_id,
        schema_version="1",
        reason="invalid_payload",
        error_type="StreamContractError",
        payload_hmac_sha256="a" * 64,
        delivery_count=1,
        failed_at=FIXED_NOW,
    )
    await transport.dead_letter_and_ack(
        USER_USAGE_STREAM,
        group,
        messages[0].message_id,
        dead_letter,
        maxlen=100,
    )

    assert await transport.pending_count(USER_USAGE_STREAM, group) == 0
    assert await redis.xlen(USER_USAGE_STREAM) == 1
    dlq_entries = await redis.xrange(f"{USER_USAGE_STREAM}:dlq")
    assert len(dlq_entries) == 1
    assert b"requestIp" not in dlq_entries[0][1]
    await redis.aclose()


@pytest.mark.asyncio
async def test_redis_transport_atomically_acks_and_deletes_persisted_subscription_request() -> None:
    redis = fakeredis.aioredis.FakeRedis(decode_responses=False)
    transport = RedisStreamTransport(redis, payload_fingerprint_hmac_key=TEST_HMAC_KEY)
    group = "subscription-success-group"
    await transport.ensure_group(SUBSCRIPTION_REQUESTS_STREAM, group, "0-0")
    message_id = await redis.xadd(SUBSCRIPTION_REQUESTS_STREAM, _subscription_request_fields())

    messages = await transport.read_new(
        (SUBSCRIPTION_REQUESTS_STREAM,),
        group,
        "consumer-a",
        count=1,
        block_ms=1,
    )
    assert messages[0].message_id == message_id.decode()
    assert await transport.pending_count(SUBSCRIPTION_REQUESTS_STREAM, group) == 1

    await transport.ack_and_delete(SUBSCRIPTION_REQUESTS_STREAM, group, messages[0].message_id)

    assert await transport.pending_count(SUBSCRIPTION_REQUESTS_STREAM, group) == 0
    assert await redis.xlen(SUBSCRIPTION_REQUESTS_STREAM) == 0
    await redis.aclose()


@pytest.mark.asyncio
async def test_redis_transport_rejects_source_deletion_for_non_subscription_streams() -> None:
    redis = fakeredis.aioredis.FakeRedis(decode_responses=False)
    transport = RedisStreamTransport(redis, payload_fingerprint_hmac_key=TEST_HMAC_KEY)

    with pytest.raises(ValueError, match="reserved for subscription_requests"):
        await transport.ack_and_delete(USER_USAGE_STREAM, "group-a", "1000-1")

    await redis.aclose()


@pytest.mark.asyncio
async def test_redis_subscription_dlq_removes_raw_source_and_contains_only_redacted_metadata() -> None:
    redis = fakeredis.aioredis.FakeRedis(decode_responses=False)
    transport = RedisStreamTransport(redis, payload_fingerprint_hmac_key=TEST_HMAC_KEY)
    group = "subscription-dlq-group"
    await transport.ensure_group(SUBSCRIPTION_REQUESTS_STREAM, group, "0-0")
    await redis.xadd(SUBSCRIPTION_REQUESTS_STREAM, _subscription_request_fields(version="2"))
    messages = await transport.read_new(
        (SUBSCRIPTION_REQUESTS_STREAM,),
        group,
        "consumer-a",
        count=1,
        block_ms=1,
    )
    dead_letter = RedactedDeadLetter(
        stream=SUBSCRIPTION_REQUESTS_STREAM,
        message_id=messages[0].message_id,
        schema_version="invalid",
        reason="unsupported_schema_version",
        error_type="StreamContractError",
        payload_hmac_sha256="a" * 64,
        delivery_count=1,
        failed_at=FIXED_NOW,
    )

    await transport.dead_letter_and_ack(
        SUBSCRIPTION_REQUESTS_STREAM,
        group,
        messages[0].message_id,
        dead_letter,
        maxlen=100,
    )

    assert await transport.pending_count(SUBSCRIPTION_REQUESTS_STREAM, group) == 0
    assert await redis.xlen(SUBSCRIPTION_REQUESTS_STREAM) == 0
    dlq_entries = await redis.xrange(f"{SUBSCRIPTION_REQUESTS_STREAM}:dlq")
    assert len(dlq_entries) == 1
    dlq_wire = repr(dlq_entries[0][1])
    for raw_value in ("requestIp", "198.51.100.42", "userAgent", "CyberVPN-Private-UA/1"):
        assert raw_value not in dlq_wire
    await redis.aclose()


@pytest.mark.asyncio
async def test_redis_runtime_state_captures_epoch_range_group_and_pel() -> None:
    redis = AsyncMock()
    redis.info.return_value = {b"run_id": b"valkey-run-123"}
    redis.exists.return_value = 1
    redis.xinfo_stream.return_value = {
        b"first-entry": (b"1000-1", {b"v": b"1"}),
        b"last-entry": (b"1000-5", {b"v": b"1"}),
    }
    redis.xinfo_groups.return_value = [
        {
            b"name": b"cybervpn-remnawave-v1",
            b"last-delivered-id": b"1000-5",
            b"lag": 3,
        }
    ]
    redis.xpending.return_value = {
        b"pending": 2,
        b"min": b"1000-3",
        b"max": b"1000-4",
    }
    transport = RedisStreamTransport(redis, payload_fingerprint_hmac_key=TEST_HMAC_KEY)

    state = await transport.runtime_state(USER_USAGE_STREAM, "cybervpn-remnawave-v1")

    assert state == StreamRuntimeState(
        observed_stream_identity="valkey-run-123",
        stream_exists=True,
        group_exists=True,
        first_message_id="1000-1",
        last_message_id="1000-5",
        group_last_delivered_id="1000-5",
        group_pending_count=2,
        group_pending_min_id="1000-3",
        group_pending_max_id="1000-4",
        group_lag=3,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("pending_count", "expected_last_message_id"),
    [(0, "1000-5"), (1, None)],
)
async def test_subscription_runtime_state_distinguishes_finalized_privacy_deletion_from_pending_loss(
    pending_count: int,
    expected_last_message_id: str | None,
) -> None:
    redis = AsyncMock()
    redis.info.return_value = {b"run_id": b"valkey-run-123"}
    redis.exists.return_value = 1
    redis.xinfo_stream.return_value = {
        b"first-entry": None,
        b"last-entry": None,
        b"last-generated-id": b"1000-5",
    }
    redis.xinfo_groups.return_value = [
        {
            b"name": b"cybervpn-remnawave-v1",
            b"last-delivered-id": b"1000-5",
        }
    ]
    redis.xpending.return_value = {
        b"pending": pending_count,
        b"min": b"1000-5" if pending_count else None,
        b"max": b"1000-5" if pending_count else None,
    }
    transport = RedisStreamTransport(redis, payload_fingerprint_hmac_key=TEST_HMAC_KEY)

    state = await transport.runtime_state(SUBSCRIPTION_REQUESTS_STREAM, "cybervpn-remnawave-v1")

    assert state.last_message_id == expected_last_message_id
    assert state.group_pending_count == pending_count


@pytest.mark.asyncio
async def test_subscription_runtime_state_rejects_any_additional_consumer_group() -> None:
    redis = AsyncMock()
    redis.info.return_value = {b"run_id": b"valkey-run-123"}
    redis.exists.return_value = 1
    redis.xinfo_stream.return_value = {
        b"first-entry": (b"1000-1", {b"v": b"1"}),
        b"last-entry": (b"1000-1", {b"v": b"1"}),
        b"last-generated-id": b"1000-1",
    }
    redis.xinfo_groups.return_value = [
        {b"name": b"cybervpn-remnawave-v1", b"last-delivered-id": b"1000-1"},
        {b"name": b"unexpected-copy", b"last-delivered-id": b"0-0"},
    ]
    transport = RedisStreamTransport(redis, payload_fingerprint_hmac_key=TEST_HMAC_KEY)

    with pytest.raises(
        StreamConsumerGroupInvariantError,
        match="requires exactly one canonical consumer group",
    ):
        await transport.runtime_state(
            SUBSCRIPTION_REQUESTS_STREAM,
            "cybervpn-remnawave-v1",
        )

    redis.xpending.assert_not_awaited()


@pytest.mark.asyncio
async def test_redis_transport_turns_invalid_utf8_into_redacted_terminal_message() -> None:
    redis = fakeredis.aioredis.FakeRedis(decode_responses=False)
    transport = RedisStreamTransport(redis, payload_fingerprint_hmac_key=TEST_HMAC_KEY)
    group = "cybervpn-remnawave-v1"
    await transport.ensure_group(USER_USAGE_STREAM, group, "0-0")
    await redis.xadd(
        USER_USAGE_STREAM,
        {
            b"v": b"1",
            b"nodeId": b"17",
            b"ts": b"2026-08-30T11:59:00.000Z",
            b"records": b"42:\xff",
        },
    )
    messages = await transport.read_new(
        (USER_USAGE_STREAM,),
        group,
        "consumer-a",
        count=1,
        block_ms=1,
    )
    assert messages[0].contract_error == "invalid_utf8"
    assert messages[0].fields == {}

    observer = _FakeObserver()
    consumer = RemnawaveStreamConsumer(
        transport,
        _FakeSink(),
        RemnawaveStreamConsumerConfig(
            consumer_name="consumer-a",
            payload_fingerprint_hmac_key=TEST_HMAC_KEY,
            group_name=group,
        ),
        observer=observer,
        now=lambda: FIXED_NOW,
    )
    await consumer._process(messages[0])

    assert await transport.pending_count(USER_USAGE_STREAM, group) == 0
    dlq_entries = await redis.xrange(f"{USER_USAGE_STREAM}:dlq")
    dlq_fields = dlq_entries[0][1]
    assert dlq_fields[b"reason"] == b"invalid_utf8"
    assert b"records" not in dlq_fields
    await redis.aclose()


@pytest.mark.asyncio
async def test_redis_dlq_retention_purges_before_and_at_boundary_only() -> None:
    redis = fakeredis.aioredis.FakeRedis(decode_responses=False)
    transport = RedisStreamTransport(redis, payload_fingerprint_hmac_key=TEST_HMAC_KEY)
    cutoff = FIXED_NOW - timedelta(days=14)
    failed_times = (cutoff - timedelta(seconds=1), cutoff, cutoff + timedelta(seconds=1))
    for index, failed_at in enumerate(failed_times, start=1):
        dead_letter = RedactedDeadLetter(
            stream=USER_USAGE_STREAM,
            message_id=f"source-{index}",
            schema_version="1",
            reason="invalid_payload",
            error_type="StreamContractError",
            payload_hmac_sha256="a" * 64,
            delivery_count=1,
            failed_at=failed_at,
        )
        redis_id = f"{int(failed_at.timestamp() * 1_000)}-{index}"
        await redis.xadd(f"{USER_USAGE_STREAM}:dlq", dead_letter.fields(), id=redis_id)

    purged = await transport.purge_dead_letters(
        USER_USAGE_STREAM,
        expires_before=cutoff,
        count=100,
    )

    assert purged == 2
    remaining = await redis.xrange(f"{USER_USAGE_STREAM}:dlq")
    assert len(remaining) == 1
    assert remaining[0][1][b"messageId"] == b"source-3"
    assert (
        await transport.purge_dead_letters(
            USER_USAGE_STREAM,
            expires_before=cutoff,
            count=100,
        )
        == 0
    )
    await redis.aclose()


@pytest.mark.asyncio
async def test_redis_dlq_accepts_reclaimed_source_ids_out_of_order() -> None:
    redis = fakeredis.aioredis.FakeRedis(decode_responses=False)
    transport = RedisStreamTransport(redis, payload_fingerprint_hmac_key=TEST_HMAC_KEY)
    group = "out-of-order-dlq-group"
    await transport.ensure_group(USER_USAGE_STREAM, group, "0-0")
    for message_id in ("1000-1", "1000-2"):
        await redis.xadd(USER_USAGE_STREAM, _usage_fields(), id=message_id)
    messages = await transport.read_new(
        (USER_USAGE_STREAM,),
        group,
        "consumer-a",
        count=2,
        block_ms=1,
    )

    for message in reversed(messages):
        await transport.dead_letter_and_ack(
            USER_USAGE_STREAM,
            group,
            message.message_id,
            RedactedDeadLetter(
                stream=USER_USAGE_STREAM,
                message_id=message.message_id,
                schema_version="1",
                reason="invalid_payload",
                error_type="StreamContractError",
                payload_hmac_sha256="a" * 64,
                delivery_count=1,
                failed_at=FIXED_NOW,
            ),
            maxlen=100,
        )

    assert await transport.pending_count(USER_USAGE_STREAM, group) == 0
    dlq_entries = await redis.xrange(f"{USER_USAGE_STREAM}:dlq")
    assert {fields[b"messageId"] for _entry_id, fields in dlq_entries} == {b"1000-1", b"1000-2"}
    await redis.aclose()
