"""Durable consumer for Remnawave 3.4 Redis Stream exports.

The module deliberately owns no CyberVPN database schema. Callers provide an
idempotent :class:`RemnawaveStreamSink` whose ``persist`` method returns only
after its transaction is durable. A stream entry is acknowledged only after
that return. If the worker crashes between durable commit and ``XACK``, the
same idempotency key is delivered again and the sink must return a duplicate
no-op result safely.

Permanent contract failures are moved to a redacted DLQ and acknowledged in
one Redis transaction. Transient failures remain in the PEL even after the
alert threshold, preserving the raw event until the durable sink recovers.
After the durable projection or terminal DLQ receipt commits,
``subscription_requests`` is atomically acknowledged and deleted from the
source stream because its wire entry contains raw request IP and User-Agent.
The DLQ contains a payload digest and safe error taxonomy, never request IP,
User-Agent, traffic records, connection IPs, or subscription data.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, Protocol

import structlog
from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress, TypeAdapter, ValidationError, field_validator
from redis.asyncio import Redis
from redis.exceptions import ResponseError

from src.metrics import (
    REMNAWAVE_STREAM_DEAD_LETTERS_TOTAL,
    REMNAWAVE_STREAM_LAST_CONSUMED_UNIXTIME,
    REMNAWAVE_STREAM_MESSAGE_LAG,
    REMNAWAVE_STREAM_MESSAGES_TOTAL,
    REMNAWAVE_STREAM_PARSE_FAILURES_TOTAL,
    REMNAWAVE_STREAM_PENDING_CURRENT,
    REMNAWAVE_STREAM_PROCESS_DURATION,
    REMNAWAVE_STREAM_RECLAIMED_TOTAL,
    REMNAWAVE_STREAM_RETENTION_PURGED_TOTAL,
    REMNAWAVE_STREAM_RETRIES_TOTAL,
)
from src.services.backend_api_client import (
    BackendAPIClient,
    BackendAPIRemnawaveMaintenancePermanentError,
    BackendAPIRemnawaveMaintenanceTransientError,
    BackendAPIStreamPermanentError,
    BackendAPIStreamTransientError,
)

logger = structlog.get_logger(__name__)

USER_USAGE_STREAM = "ioraw:export:user_usage"
SUBSCRIPTION_REQUESTS_STREAM = "ioraw:export:subscription_requests"
NODE_CONNECTIONS_STREAM = "ioraw:export:node_connections"
REMNAWAVE_STREAMS = (USER_USAGE_STREAM, SUBSCRIPTION_REQUESTS_STREAM, NODE_CONNECTIONS_STREAM)
REMNAWAVE_STREAM_CONSUMER_GROUP = "cybervpn-remnawave-v1"
SUPPORTED_SCHEMA_VERSION = "1"
STREAM_API_NAMES = {
    USER_USAGE_STREAM: "user_usage",
    SUBSCRIPTION_REQUESTS_STREAM: "subscription_requests",
    NODE_CONNECTIONS_STREAM: "node_connections",
}


class _WireModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


def _validate_decimal(value: str) -> str:
    if not value or not value.isascii() or not value.isdecimal():
        raise ValueError("expected an unsigned decimal string")
    return value


def _validate_positive_decimal(value: str) -> str:
    normalized = _validate_decimal(value)
    if int(normalized) <= 0:
        raise ValueError("expected a positive decimal string")
    return normalized


def _validate_aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return value.astimezone(UTC)


class _UserUsageWire(_WireModel):
    version: Literal["1"] = Field(alias="v")
    node_id: str = Field(alias="nodeId")
    timestamp: datetime = Field(alias="ts")
    records: str

    _node_id_is_decimal = field_validator("node_id")(_validate_positive_decimal)
    _timestamp_is_aware = field_validator("timestamp")(_validate_aware_datetime)


class _SubscriptionRequestWire(_WireModel):
    version: Literal["1"] = Field(alias="v")
    user_id: str = Field(alias="userId")
    requested_at: datetime = Field(alias="requestAt")
    request_ip: IPvAnyAddress | None = Field(default=None, alias="requestIp")
    user_agent: str | None = Field(default=None, max_length=1024, alias="userAgent")
    srr_rule_name: str | None = Field(default=None, max_length=160, alias="srrRuleName")
    srr_response_type: str = Field(min_length=1, max_length=80, alias="srrResponseType")

    _user_id_is_decimal = field_validator("user_id")(_validate_positive_decimal)
    _requested_at_is_aware = field_validator("requested_at")(_validate_aware_datetime)


class _NodeConnectionIpWire(_WireModel):
    ip: IPvAnyAddress
    last_seen: datetime = Field(alias="lastSeen")

    _last_seen_is_aware = field_validator("last_seen")(_validate_aware_datetime)


class _NodeConnectionUserWire(_WireModel):
    user_id: str = Field(alias="userId")
    ips: list[_NodeConnectionIpWire]

    _user_id_is_decimal = field_validator("user_id")(_validate_positive_decimal)


class _NodeConnectionsWire(_WireModel):
    version: Literal["1"] = Field(alias="v")
    node_id: str = Field(alias="nodeId")
    timestamp: datetime = Field(alias="ts")
    users: str

    _node_id_is_decimal = field_validator("node_id")(_validate_positive_decimal)
    _timestamp_is_aware = field_validator("timestamp")(_validate_aware_datetime)


_NODE_CONNECTION_USERS_ADAPTER = TypeAdapter(list[_NodeConnectionUserWire])


@dataclass(frozen=True, slots=True)
class UserUsageRecord:
    user_id: int
    total_bytes: int


@dataclass(frozen=True, slots=True)
class UserUsageEvent:
    schema_version: Literal["1"]
    node_id: int
    observed_at: datetime
    records: tuple[UserUsageRecord, ...]


@dataclass(frozen=True, slots=True)
class SubscriptionRequestEvent:
    schema_version: Literal["1"]
    user_id: int
    requested_at: datetime
    request_ip: str | None
    user_agent: str | None
    srr_rule_name: str | None
    srr_response_type: str


@dataclass(frozen=True, slots=True)
class NodeConnectionIp:
    ip: str
    last_seen: datetime


@dataclass(frozen=True, slots=True)
class NodeConnectionUser:
    user_id: int
    ips: tuple[NodeConnectionIp, ...]


@dataclass(frozen=True, slots=True)
class NodeConnectionsEvent:
    schema_version: Literal["1"]
    node_id: int
    observed_at: datetime
    users: tuple[NodeConnectionUser, ...]


type RemnawaveStreamEvent = UserUsageEvent | SubscriptionRequestEvent | NodeConnectionsEvent
type StreamFieldMapping = Mapping[str, str] | Mapping[bytes, bytes] | Mapping[str | bytes, str | bytes]
type RedisFieldValue = bytes | bytearray | memoryview[int] | str | int | float


class StreamContractError(ValueError):
    """A permanent stream contract error safe to classify without payload text."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class TransientSinkError(RuntimeError):
    """The sink did not commit and the message can be retried safely."""


class PermanentSinkError(RuntimeError):
    """The sink rejected this event permanently; it must be dead-lettered."""


class StreamConsumerGroupInvariantError(RuntimeError):
    """The privacy-sensitive source has an unsupported consumer group."""


@dataclass(frozen=True, slots=True)
class StreamPayloadLimits:
    max_message_bytes: int = 1_048_576
    max_usage_records: int = 10_000
    max_connection_users: int = 10_000
    max_ips_per_user: int = 256

    def __post_init__(self) -> None:
        for name, value in (
            ("max_message_bytes", self.max_message_bytes),
            ("max_usage_records", self.max_usage_records),
            ("max_connection_users", self.max_connection_users),
            ("max_ips_per_user", self.max_ips_per_user),
        ):
            if value <= 0:
                raise ValueError(f"{name} must be positive")


@dataclass(frozen=True, slots=True)
class StreamMessage:
    stream: str
    message_id: str
    fields: Mapping[str, str]
    delivery_count: int = 1
    contract_error: str | None = None
    payload_hmac_sha256: str | None = None


@dataclass(frozen=True, slots=True)
class ReclaimBatch:
    messages: tuple[StreamMessage, ...]
    deleted_message_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StreamRuntimeState:
    observed_stream_identity: str
    stream_exists: bool
    group_exists: bool
    first_message_id: str | None
    last_message_id: str | None
    group_last_delivered_id: str | None
    group_pending_count: int
    group_pending_min_id: str | None
    group_pending_max_id: str | None
    group_lag: int | None = None


@dataclass(frozen=True, slots=True)
class RedactedDeadLetter:
    stream: str
    message_id: str
    schema_version: str
    reason: str
    error_type: str
    payload_hmac_sha256: str
    delivery_count: int
    failed_at: datetime

    def fields(self) -> dict[str, str]:
        return {
            "stream": self.stream,
            "messageId": self.message_id,
            "schemaVersion": self.schema_version,
            "reason": self.reason,
            "errorType": self.error_type,
            "payloadHmacSha256": self.payload_hmac_sha256,
            "deliveryCount": str(self.delivery_count),
            "failedAt": self.failed_at.astimezone(UTC).isoformat(),
        }


class RemnawaveStreamSink(Protocol):
    """Backend-owned durable sink port.

    Implementations must commit idempotently on ``idempotency_key`` and return
    only after the transaction is durable. Repeated calls with the same key
    must be safe and must not duplicate traffic, request, or connection state.
    """

    async def persist(self, event: RemnawaveStreamEvent, *, idempotency_key: str) -> None: ...

    async def persist_dead_letter(self, dead_letter: RedactedDeadLetter) -> None: ...

    async def record_gap(
        self,
        stream: str,
        missing_message_ids: Sequence[str],
        *,
        detected_at: datetime,
    ) -> None: ...

    async def observe_runtime(
        self,
        stream: str,
        state: StreamRuntimeState,
        *,
        observed_at: datetime,
    ) -> None: ...


class BackendRemnawaveStreamSink:
    """HTTP sink adapter for the backend-owned transactional ingestion API."""

    def __init__(self, backend: BackendAPIClient) -> None:
        self._backend = backend

    async def persist(self, event: RemnawaveStreamEvent, *, idempotency_key: str) -> None:
        try:
            await self._backend.persist_remnawave_stream_event(
                _serialize_event(event),
                idempotency_key=idempotency_key,
            )
        except BackendAPIStreamPermanentError as exc:
            raise PermanentSinkError("backend rejected stream event permanently") from exc
        except BackendAPIStreamTransientError as exc:
            raise TransientSinkError("backend stream ingestion is temporarily unavailable") from exc

    async def persist_dead_letter(self, dead_letter: RedactedDeadLetter) -> None:
        try:
            stream_name = STREAM_API_NAMES[dead_letter.stream]
            await self._backend.persist_remnawave_dead_letter(
                {
                    "stream_name": stream_name,
                    "message_id": dead_letter.message_id,
                    "schema_version": dead_letter.schema_version or None,
                    "error_type": dead_letter.error_type,
                    "redacted_reason": dead_letter.reason,
                    "payload_fingerprint": dead_letter.payload_hmac_sha256,
                    "attempts": dead_letter.delivery_count,
                }
            )
        except KeyError as exc:
            raise PermanentSinkError("unsupported dead-letter stream") from exc
        except (
            BackendAPIRemnawaveMaintenancePermanentError,
            BackendAPIRemnawaveMaintenanceTransientError,
        ) as exc:
            # Never XACK without the durable PostgreSQL metadata receipt. Even a
            # deterministic 4xx here is an operator-visible contract incident,
            # not permission to discard the source entry.
            raise TransientSinkError("backend dead-letter persistence is unavailable") from exc

    async def record_gap(
        self,
        stream: str,
        missing_message_ids: Sequence[str],
        *,
        detected_at: datetime,
    ) -> None:
        try:
            gap = await self._backend.create_remnawave_stream_gap(
                stream_name=STREAM_API_NAMES[stream],
                missing_message_ids=tuple(missing_message_ids),
                detected_at=detected_at,
            )
            if gap.reconciliation_status not in {"reconciled", "partial"}:
                gap = await self._backend.reconcile_remnawave_stream_gap(
                    gap_id=gap.gap_id,
                    stream_name=gap.stream_name,
                )
            if gap.reconciliation_status not in {"reconciled", "partial"}:
                raise TransientSinkError("backend stream-gap reconciliation is not terminal")
        except KeyError as exc:
            raise PermanentSinkError("unsupported gap stream") from exc
        except (
            BackendAPIRemnawaveMaintenancePermanentError,
            BackendAPIRemnawaveMaintenanceTransientError,
        ) as exc:
            # Exact trimmed ids have already disappeared from the PEL. Keep
            # the in-memory report pending and halt processing until the
            # durable backend acknowledges the idempotent gap fingerprint.
            raise TransientSinkError("backend stream-gap persistence is unavailable") from exc

    async def observe_runtime(
        self,
        stream: str,
        state: StreamRuntimeState,
        *,
        observed_at: datetime,
    ) -> None:
        try:
            observation = await self._backend.observe_remnawave_stream_checkpoint(
                stream_name=STREAM_API_NAMES[stream],
                observed_stream_identity=state.observed_stream_identity,
                stream_exists=state.stream_exists,
                group_exists=state.group_exists,
                first_message_id=state.first_message_id,
                last_message_id=state.last_message_id,
                group_last_delivered_id=state.group_last_delivered_id,
                group_pending_count=state.group_pending_count,
                group_pending_min_id=state.group_pending_min_id,
                group_pending_max_id=state.group_pending_max_id,
                observed_at=observed_at,
                group_lag=state.group_lag,
            )
            if (
                observation.loss_detected
                and observation.reconciliation_status in {"pending", "running"}
                and observation.gap_id is not None
            ):
                reconciled_gap = await self._backend.reconcile_remnawave_stream_gap(
                    gap_id=observation.gap_id,
                    stream_name=STREAM_API_NAMES[stream],
                )
                observation = replace(
                    observation,
                    reconciliation_status=reconciled_gap.reconciliation_status,
                )
            if observation.loss_detected and observation.reconciliation_status not in {
                "reconciled",
                "partial",
            }:
                raise TransientSinkError(
                    "durable stream loss requires authoritative reconciliation before group repair"
                )
        except KeyError as exc:
            raise PermanentSinkError("unsupported checkpoint stream") from exc
        except TransientSinkError:
            raise
        except (
            BackendAPIRemnawaveMaintenancePermanentError,
            BackendAPIRemnawaveMaintenanceTransientError,
        ) as exc:
            raise TransientSinkError("backend stream checkpoint is unavailable") from exc


class StreamTransport(Protocol):
    async def runtime_state(self, stream: str, group: str) -> StreamRuntimeState: ...

    async def ensure_group(self, stream: str, group: str, start_id: str) -> None: ...

    async def read_new(
        self,
        streams: Sequence[str],
        group: str,
        consumer: str,
        *,
        count: int,
        block_ms: int,
    ) -> tuple[StreamMessage, ...]: ...

    async def reclaim(
        self,
        stream: str,
        group: str,
        consumer: str,
        *,
        min_idle_ms: int,
        count: int,
    ) -> ReclaimBatch: ...

    async def ack(self, stream: str, group: str, message_id: str) -> None: ...

    async def ack_and_delete(self, stream: str, group: str, message_id: str) -> None: ...

    async def dead_letter_and_ack(
        self,
        stream: str,
        group: str,
        message_id: str,
        dead_letter: RedactedDeadLetter,
        *,
        maxlen: int,
    ) -> None: ...

    async def pending_count(self, stream: str, group: str) -> int: ...

    async def purge_dead_letters(self, stream: str, *, expires_before: datetime, count: int) -> int: ...


class StreamConsumerObserver(Protocol):
    def message(self, stream: str, outcome: str, duration_seconds: float) -> None: ...

    def retry(self, stream: str) -> None: ...

    def dead_letter(self, stream: str, reason: str) -> None: ...

    def reclaimed(self, stream: str, outcome: str, count: int = 1) -> None: ...

    def pending(self, stream: str, count: int) -> None: ...

    def lag(self, stream: str, seconds: float) -> None: ...

    def retention_purged(self, stream: str, store: str, count: int) -> None: ...


class PrometheusStreamConsumerObserver:
    def message(self, stream: str, outcome: str, duration_seconds: float) -> None:
        REMNAWAVE_STREAM_MESSAGES_TOTAL.labels(stream=stream, outcome=outcome).inc()
        REMNAWAVE_STREAM_PROCESS_DURATION.labels(stream=stream, outcome=outcome).observe(duration_seconds)
        if outcome in {"persisted", "dead_lettered"}:
            REMNAWAVE_STREAM_LAST_CONSUMED_UNIXTIME.labels(stream=stream).set(time.time())

    def retry(self, stream: str) -> None:
        REMNAWAVE_STREAM_RETRIES_TOTAL.labels(stream=stream).inc()

    def dead_letter(self, stream: str, reason: str) -> None:
        REMNAWAVE_STREAM_DEAD_LETTERS_TOTAL.labels(stream=stream, reason=reason).inc()
        if reason in {
            "invalid_payload",
            "invalid_utf8",
            "payload_too_large",
            "unsupported_schema_version",
        }:
            REMNAWAVE_STREAM_PARSE_FAILURES_TOTAL.labels(stream=stream, reason=reason).inc()

    def reclaimed(self, stream: str, outcome: str, count: int = 1) -> None:
        REMNAWAVE_STREAM_RECLAIMED_TOTAL.labels(stream=stream, outcome=outcome).inc(count)

    def pending(self, stream: str, count: int) -> None:
        REMNAWAVE_STREAM_PENDING_CURRENT.labels(stream=stream).set(count)

    def lag(self, stream: str, seconds: float) -> None:
        REMNAWAVE_STREAM_MESSAGE_LAG.labels(stream=stream).observe(max(0.0, seconds))

    def retention_purged(self, stream: str, store: str, count: int) -> None:
        if count > 0:
            REMNAWAVE_STREAM_RETENTION_PURGED_TOTAL.labels(stream=stream, store=store).inc(count)


@dataclass(frozen=True, slots=True)
class RemnawaveStreamConsumerConfig:
    consumer_name: str
    payload_fingerprint_hmac_key: bytes = field(repr=False)
    group_name: str = REMNAWAVE_STREAM_CONSUMER_GROUP
    start_id: str = "0-0"
    read_count: int = 50
    block_ms: int = 5_000
    reclaim_count: int = 50
    reclaim_min_idle_ms: int = 30_000
    max_delivery_attempts: int = 5
    dlq_maxlen: int = 3_000
    dlq_retention_days: int = 14
    receipt_retention_days: int = 14
    dlq_purge_count: int = 100
    checkpoint_observe_interval_seconds: float = 30.0
    redis_retry_base_seconds: float = 0.25
    redis_retry_max_seconds: float = 5.0
    limits: StreamPayloadLimits = StreamPayloadLimits()

    def __post_init__(self) -> None:
        if not self.consumer_name.strip():
            raise ValueError("consumer_name must not be empty")
        if self.group_name != REMNAWAVE_STREAM_CONSUMER_GROUP:
            raise ValueError(f"group_name must be exactly {REMNAWAVE_STREAM_CONSUMER_GROUP}")
        if len(self.payload_fingerprint_hmac_key) < 32:
            raise ValueError("payload_fingerprint_hmac_key must contain at least 32 bytes")
        for name, value in (
            ("read_count", self.read_count),
            ("block_ms", self.block_ms),
            ("reclaim_count", self.reclaim_count),
            ("reclaim_min_idle_ms", self.reclaim_min_idle_ms),
            ("max_delivery_attempts", self.max_delivery_attempts),
            ("dlq_maxlen", self.dlq_maxlen),
            ("dlq_retention_days", self.dlq_retention_days),
            ("receipt_retention_days", self.receipt_retention_days),
            ("dlq_purge_count", self.dlq_purge_count),
        ):
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if self.redis_retry_base_seconds <= 0 or self.redis_retry_max_seconds < self.redis_retry_base_seconds:
            raise ValueError("Redis retry bounds are invalid")
        if self.checkpoint_observe_interval_seconds <= 0:
            raise ValueError("checkpoint_observe_interval_seconds must be positive")


class RemnawaveStreamConsumer:
    def __init__(
        self,
        transport: StreamTransport,
        sink: RemnawaveStreamSink,
        config: RemnawaveStreamConsumerConfig,
        *,
        observer: StreamConsumerObserver | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._transport = transport
        self._sink = sink
        self._config = config
        self._observer = observer or PrometheusStreamConsumerObserver()
        self._monotonic = monotonic
        self._now = now
        self._stop_event = asyncio.Event()
        self._initialized = False
        self._next_runtime_observation_at = 0.0
        self._pending_gap_reports: list[tuple[str, tuple[str, ...], datetime]] = []

    async def initialize(self) -> None:
        # Observe all live stream/group state against the durable backend
        # checkpoint before MKSTREAM can hide a flush or group recreation.
        await self._observe_runtime_and_repair_groups()
        self._next_runtime_observation_at = self._monotonic() + self._config.checkpoint_observe_interval_seconds
        self._initialized = True

    async def _observe_runtime_and_repair_groups(self) -> None:
        observed_at = self._now()
        states: dict[str, StreamRuntimeState] = {}
        for stream in REMNAWAVE_STREAMS:
            states[stream] = await self._transport.runtime_state(stream, self._config.group_name)
        # Commit every observation before mutating Redis. If the backend is
        # unavailable, fail closed and preserve the missing/regressed state.
        for stream, state in states.items():
            await self._sink.observe_runtime(stream, state, observed_at=observed_at)
        for stream in states:
            # Always issue the idempotent create after observation so a group
            # deleted in the observation/create race is repaired as well.
            await self._transport.ensure_group(stream, self._config.group_name, self._config.start_id)

    async def _observe_runtime_if_due(self) -> None:
        if self._monotonic() < self._next_runtime_observation_at:
            return
        await self._observe_runtime_and_repair_groups()
        self._next_runtime_observation_at = self._monotonic() + self._config.checkpoint_observe_interval_seconds

    def stop(self) -> None:
        self._stop_event.set()

    async def run(self) -> None:
        if not self._initialized:
            await self.initialize()
        consecutive_redis_failures = 0
        while not self._stop_event.is_set():
            try:
                await self.consume_new_once()
                if self._stop_event.is_set():
                    break
                await self.reclaim_once()
                consecutive_redis_failures = 0
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                consecutive_redis_failures += 1
                logger.error(
                    "remnawave_stream_redis_error",
                    error_type=type(exc).__name__,
                    consecutive_failures=consecutive_redis_failures,
                )
                exponent = min(consecutive_redis_failures - 1, 10)
                delay = min(
                    self._config.redis_retry_base_seconds * (2**exponent),
                    self._config.redis_retry_max_seconds,
                )
                await self._wait_for_stop(delay)

    async def consume_new_once(self) -> int:
        if self._initialized:
            await self._observe_runtime_if_due()
        try:
            messages = await self._transport.read_new(
                REMNAWAVE_STREAMS,
                self._config.group_name,
                self._config.consumer_name,
                count=self._config.read_count,
                block_ms=self._config.block_ms,
            )
        except ResponseError as exc:
            if "NOGROUP" not in str(exc).upper():
                raise
            # A live Valkey flush can occur between periodic observations. Do
            # not blindly recreate the group: persist the missing state first.
            await self._observe_runtime_and_repair_groups()
            self._next_runtime_observation_at = self._monotonic() + self._config.checkpoint_observe_interval_seconds
            return 0
        for message in messages:
            await self._process(message)
        await self._observe_pending()
        await self._purge_dead_letters()
        return len(messages)

    async def reclaim_once(self) -> int:
        reclaimed = 0
        await self._flush_pending_gap_reports()
        for stream in REMNAWAVE_STREAMS:
            batch = await self._transport.reclaim(
                stream,
                self._config.group_name,
                self._config.consumer_name,
                min_idle_ms=self._config.reclaim_min_idle_ms,
                count=self._config.reclaim_count,
            )
            if batch.deleted_message_ids:
                self._pending_gap_reports.append((stream, batch.deleted_message_ids, self._now()))
                await self._flush_pending_gap_reports()
                self._observer.reclaimed(stream, "trimmed", len(batch.deleted_message_ids))
            for message in batch.messages:
                self._observer.reclaimed(stream, "claimed")
                await self._process(message, pending_reclaim=True)
                reclaimed += 1
        await self._observe_pending()
        return reclaimed

    async def _flush_pending_gap_reports(self) -> None:
        while self._pending_gap_reports:
            stream, missing_message_ids, detected_at = self._pending_gap_reports[0]
            await self._sink.record_gap(
                stream,
                missing_message_ids,
                detected_at=detected_at,
            )
            self._pending_gap_reports.pop(0)

    async def _process(self, message: StreamMessage, *, pending_reclaim: bool = False) -> None:
        started = self._monotonic()
        digest = message.payload_hmac_sha256 or _payload_hmac_sha256(
            message.fields,
            self._config.payload_fingerprint_hmac_key,
        )
        outcome = "failed"
        try:
            if pending_reclaim and _receipt_retention_elapsed(
                message.message_id,
                now=self._now(),
                retention_days=self._config.receipt_retention_days,
            ):
                # A commit followed by an XACK failure can leave an entry in
                # the PEL beyond the PostgreSQL receipt lifetime. Replaying it
                # after receipt cleanup would double-apply additive usage or
                # connection counts. Treat the old entry as an exact gap,
                # require the backend's authoritative reconciliation, and
                # finalize the source only after that durable handoff succeeds.
                await self._sink.record_gap(
                    message.stream,
                    (message.message_id,),
                    detected_at=self._now(),
                )
                try:
                    await self._ack_finalized_message(message)
                except asyncio.CancelledError:
                    outcome = "cancelled"
                    raise
                except Exception:
                    outcome = "ack_failed"
                    raise
                outcome = "stale_reconciled"
                logger.warning(
                    "remnawave_stream_stale_pending_reconciled",
                    stream=message.stream,
                    message_id=message.message_id,
                    delivery_count=message.delivery_count,
                )
                return
            if message.contract_error is not None:
                raise StreamContractError(message.contract_error)
            event = parse_stream_event(message.stream, message.fields, self._config.limits)
            event_time = _event_time(event)
            self._observer.lag(message.stream, (self._now() - event_time).total_seconds())
            await self._sink.persist(
                event,
                idempotency_key=f"remnawave:{_event_type(event)}:{message.message_id}",
            )
        except StreamContractError as exc:
            await self._dead_letter(message, digest, exc.code, type(exc).__name__)
            outcome = "dead_lettered"
        except PermanentSinkError as exc:
            await self._dead_letter(message, digest, "permanent_sink_error", type(exc).__name__)
            outcome = "dead_lettered"
        except TransientSinkError as exc:
            outcome = await self._retry_or_dead_letter(message, digest, type(exc).__name__)
        except Exception as exc:
            # Unknown sink errors are treated as transient. This avoids data
            # loss while still bounding redelivery through the PEL count.
            outcome = await self._retry_or_dead_letter(message, digest, type(exc).__name__)
        else:
            # Keep Redis transport failures outside sink retry classification.
            # A durable sink commit followed by an XACK failure must be replayed
            # with the same idempotency key, never moved to DLQ as a sink error.
            try:
                await self._ack_finalized_message(message)
            except asyncio.CancelledError:
                outcome = "cancelled"
                raise
            except Exception:
                outcome = "ack_failed"
                raise
            outcome = "persisted"
            logger.info(
                "remnawave_stream_message_persisted",
                stream=message.stream,
                message_id=message.message_id,
                delivery_count=message.delivery_count,
            )
        finally:
            self._observer.message(message.stream, outcome, max(0.0, self._monotonic() - started))

    async def _ack_finalized_message(self, message: StreamMessage) -> None:
        if message.stream == SUBSCRIPTION_REQUESTS_STREAM:
            await self._transport.ack_and_delete(
                message.stream,
                self._config.group_name,
                message.message_id,
            )
            return
        await self._transport.ack(
            message.stream,
            self._config.group_name,
            message.message_id,
        )

    async def _retry_or_dead_letter(self, message: StreamMessage, digest: str, error_type: str) -> str:
        _ = digest
        if message.delivery_count >= self._config.max_delivery_attempts:
            # A transient backend outage is not evidence that the event itself
            # is invalid. Keep the raw entry in the PEL indefinitely (with
            # bounded reclaim cadence) instead of reducing it to redacted DLQ
            # metadata and irreversibly acknowledging usage/presence data.
            self._observer.retry(message.stream)
            logger.error(
                "remnawave_stream_retry_budget_exhausted_pending",
                stream=message.stream,
                message_id=message.message_id,
                delivery_count=message.delivery_count,
                error_type=error_type,
            )
            return "retry_exhausted_pending"

        self._observer.retry(message.stream)
        logger.warning(
            "remnawave_stream_message_retry_scheduled",
            stream=message.stream,
            message_id=message.message_id,
            delivery_count=message.delivery_count,
            error_type=error_type,
        )
        return "retry_pending"

    async def _dead_letter(self, message: StreamMessage, digest: str, reason: str, error_type: str) -> None:
        # Never mirror an untrusted wire value into the redacted DLQ.  The
        # schema field is part of the upstream payload and may itself contain
        # secrets when a producer is malformed or hostile.
        schema_version = message.fields.get("v")
        if schema_version != SUPPORTED_SCHEMA_VERSION:
            schema_version = "invalid"
        dead_letter = RedactedDeadLetter(
            stream=message.stream,
            message_id=message.message_id,
            schema_version=schema_version,
            reason=reason,
            error_type=error_type,
            payload_hmac_sha256=digest,
            delivery_count=message.delivery_count,
            failed_at=self._now(),
        )
        await self._sink.persist_dead_letter(dead_letter)
        await self._transport.dead_letter_and_ack(
            message.stream,
            self._config.group_name,
            message.message_id,
            dead_letter,
            maxlen=self._config.dlq_maxlen,
        )
        self._observer.dead_letter(message.stream, reason)
        logger.warning(
            "remnawave_stream_message_dead_lettered",
            stream=message.stream,
            message_id=message.message_id,
            reason=reason,
            delivery_count=message.delivery_count,
        )

    async def _observe_pending(self) -> None:
        for stream in REMNAWAVE_STREAMS:
            count = await self._transport.pending_count(stream, self._config.group_name)
            self._observer.pending(stream, count)

    async def _purge_dead_letters(self) -> None:
        cutoff = self._now() - timedelta(days=self._config.dlq_retention_days)
        for stream in REMNAWAVE_STREAMS:
            purged = await self._transport.purge_dead_letters(
                stream,
                expires_before=cutoff,
                count=self._config.dlq_purge_count,
            )
            self._observer.retention_purged(stream, "redis_dlq", purged)

    async def _wait_for_stop(self, delay_seconds: float) -> None:
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=delay_seconds)
        except TimeoutError:
            return


def _receipt_retention_elapsed(
    message_id: str,
    *,
    now: datetime,
    retention_days: int,
) -> bool:
    """Return whether a Redis entry can outlive its durable dedupe receipt."""

    try:
        milliseconds_text, _sequence_text = message_id.split("-", 1)
        message_milliseconds = int(milliseconds_text)
    except (ValueError, TypeError):
        return False
    cutoff_milliseconds = int((now - timedelta(days=retention_days)).timestamp() * 1_000)
    return message_milliseconds <= cutoff_milliseconds


class RedisStreamTransport:
    """redis-py adapter implementing consumer groups and atomic finalization."""

    def __init__(self, redis: Redis, *, payload_fingerprint_hmac_key: bytes) -> None:
        if len(payload_fingerprint_hmac_key) < 32:
            raise ValueError("payload_fingerprint_hmac_key must contain at least 32 bytes")
        self._redis = redis
        self._payload_fingerprint_hmac_key = payload_fingerprint_hmac_key

    async def runtime_state(self, stream: str, group: str) -> StreamRuntimeState:
        server_info = await self._redis.info(section="server")
        raw_identity = _mapping_value(server_info, "run_id")
        if raw_identity is None:
            raise RuntimeError("Redis server identity is unavailable")
        observed_stream_identity = _decode_scalar(raw_identity)
        if not observed_stream_identity or len(observed_stream_identity) > 128:
            raise RuntimeError("Redis server identity is invalid")

        stream_exists = bool(await self._redis.exists(stream))
        if not stream_exists:
            return StreamRuntimeState(
                observed_stream_identity=observed_stream_identity,
                stream_exists=False,
                group_exists=False,
                first_message_id=None,
                last_message_id=None,
                group_last_delivered_id=None,
                group_pending_count=0,
                group_pending_min_id=None,
                group_pending_max_id=None,
            )

        try:
            stream_info = await self._redis.xinfo_stream(stream)
            groups = await self._redis.xinfo_groups(stream)
        except ResponseError as exc:
            if "NO SUCH KEY" not in str(exc).upper():
                raise
            return StreamRuntimeState(
                observed_stream_identity=observed_stream_identity,
                stream_exists=False,
                group_exists=False,
                first_message_id=None,
                last_message_id=None,
                group_last_delivered_id=None,
                group_pending_count=0,
                group_pending_min_id=None,
                group_pending_max_id=None,
            )

        first_message_id = _entry_message_id(_mapping_value(stream_info, "first-entry"))
        last_message_id = _entry_message_id(_mapping_value(stream_info, "last-entry"))
        last_generated_id = _optional_decoded_scalar(_mapping_value(stream_info, "last-generated-id"))
        group_names = {
            decoded_name
            for candidate in groups
            if isinstance(candidate, Mapping)
            and (decoded_name := _decoded_mapping_value(candidate, "name")) is not None
        }
        if stream == SUBSCRIPTION_REQUESTS_STREAM and group_names - {group}:
            # Source entries contain raw IP and User-Agent. XDEL after the
            # canonical group's durable projection is safe only while no
            # second group can still depend on the same source entry. Never
            # include untrusted group names in the exception or logs.
            raise StreamConsumerGroupInvariantError(
                "subscription_requests requires exactly one canonical consumer group"
            )
        selected_group: Mapping[Any, Any] | None = None
        for candidate in groups:
            if isinstance(candidate, Mapping) and _decoded_mapping_value(candidate, "name") == group:
                selected_group = candidate
                break
        if selected_group is None:
            return StreamRuntimeState(
                observed_stream_identity=observed_stream_identity,
                stream_exists=True,
                group_exists=False,
                first_message_id=first_message_id,
                last_message_id=last_message_id,
                group_last_delivered_id=None,
                group_pending_count=0,
                group_pending_min_id=None,
                group_pending_max_id=None,
            )

        group_last_delivered_id = _decoded_mapping_value(selected_group, "last-delivered-id")
        raw_group_lag = _mapping_value(selected_group, "lag")
        group_lag = int(raw_group_lag) if raw_group_lag is not None else None
        if group_lag is not None and group_lag < 0:
            raise RuntimeError("Redis consumer group lag is invalid")
        pending_summary = await self._redis.xpending(stream, group)
        if isinstance(pending_summary, Mapping):
            group_pending_count = int(_mapping_value(pending_summary, "pending") or 0)
            group_pending_min_id = _optional_decoded_scalar(_mapping_value(pending_summary, "min"))
            group_pending_max_id = _optional_decoded_scalar(_mapping_value(pending_summary, "max"))
        elif isinstance(pending_summary, Sequence) and pending_summary:
            group_pending_count = int(pending_summary[0])
            group_pending_min_id = _optional_decoded_scalar(pending_summary[1] if len(pending_summary) > 1 else None)
            group_pending_max_id = _optional_decoded_scalar(pending_summary[2] if len(pending_summary) > 2 else None)
        else:
            group_pending_count = 0
            group_pending_min_id = None
            group_pending_max_id = None
        if group_pending_count == 0:
            group_pending_min_id = None
            group_pending_max_id = None
        if (
            stream == SUBSCRIPTION_REQUESTS_STREAM
            and last_message_id is None
            and group_pending_count == 0
            and group_last_delivered_id is not None
            and last_generated_id == group_last_delivered_id
        ):
            # XDEL intentionally leaves an empty stream after the sole group
            # has durably projected and acknowledged its latest entry. Report
            # that finalized id as the logical stream tail so checkpoint
            # monitoring does not misclassify privacy deletion as data loss.
            # A deleted pending entry, an undelivered generated id, or a new
            # Valkey epoch does not satisfy these conditions and still trips
            # the normal reconciliation boundary.
            last_message_id = last_generated_id

        return StreamRuntimeState(
            observed_stream_identity=observed_stream_identity,
            stream_exists=True,
            group_exists=True,
            first_message_id=first_message_id,
            last_message_id=last_message_id,
            group_last_delivered_id=group_last_delivered_id,
            group_pending_count=group_pending_count,
            group_pending_min_id=group_pending_min_id,
            group_pending_max_id=group_pending_max_id,
            group_lag=group_lag,
        )

    async def ensure_group(self, stream: str, group: str, start_id: str) -> None:
        try:
            await self._redis.xgroup_create(stream, group, id=start_id, mkstream=True)
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc).upper():
                raise

    async def read_new(
        self,
        streams: Sequence[str],
        group: str,
        consumer: str,
        *,
        count: int,
        block_ms: int,
    ) -> tuple[StreamMessage, ...]:
        response = await self._redis.xreadgroup(
            group,
            consumer,
            streams={stream: ">" for stream in streams},
            count=count,
            block=block_ms,
        )
        return _decode_read_response(
            response,
            delivery_count=1,
            payload_fingerprint_hmac_key=self._payload_fingerprint_hmac_key,
        )

    async def reclaim(
        self,
        stream: str,
        group: str,
        consumer: str,
        *,
        min_idle_ms: int,
        count: int,
    ) -> ReclaimBatch:
        response = await self._redis.xautoclaim(
            stream,
            group,
            consumer,
            min_idle_time=min_idle_ms,
            start_id="0-0",
            count=count,
        )
        entries = response[1] if len(response) > 1 else []
        deleted_ids = response[2] if len(response) > 2 else []
        messages: list[StreamMessage] = []
        for message_id, fields in entries:
            decoded_id = _decode_scalar(message_id)
            delivery_count = await self._delivery_count(stream, group, decoded_id)
            messages.append(
                _decode_stream_message(
                    stream,
                    decoded_id,
                    fields,
                    delivery_count=max(1, delivery_count),
                    payload_fingerprint_hmac_key=self._payload_fingerprint_hmac_key,
                )
            )
        return ReclaimBatch(
            messages=tuple(messages),
            deleted_message_ids=tuple(_decode_scalar(message_id) for message_id in deleted_ids),
        )

    async def ack(self, stream: str, group: str, message_id: str) -> None:
        await self._redis.xack(stream, group, message_id)

    async def ack_and_delete(self, stream: str, group: str, message_id: str) -> None:
        if stream != SUBSCRIPTION_REQUESTS_STREAM:
            raise ValueError("ack_and_delete is reserved for subscription_requests")
        pipeline = self._redis.pipeline(transaction=True)
        pipeline.xack(stream, group, message_id)
        pipeline.xdel(stream, message_id)
        await pipeline.execute()

    async def dead_letter_and_ack(
        self,
        stream: str,
        group: str,
        message_id: str,
        dead_letter: RedactedDeadLetter,
        *,
        maxlen: int,
    ) -> None:
        pipeline = self._redis.pipeline(transaction=True)
        redis_fields: dict[RedisFieldValue, RedisFieldValue] = {
            key: value for key, value in dead_letter.fields().items()
        }
        dlq_stream = f"{stream}:dlq"
        # The DLQ entry deliberately receives a Redis-generated id.  Reusing
        # the source stream id makes an older reclaimed source entry fail with
        # ERR equal or smaller than the DLQ top id after a newer entry has
        # already been quarantined. XADD, XACK, and the privacy-required XDEL
        # remain in one transaction, while messageId in the redacted fields
        # preserves source identity.
        pipeline.xadd(
            dlq_stream,
            redis_fields,
            maxlen=maxlen,
            approximate=True,
        )
        pipeline.xack(stream, group, message_id)
        if stream == SUBSCRIPTION_REQUESTS_STREAM:
            pipeline.xdel(stream, message_id)
        await pipeline.execute()

    async def pending_count(self, stream: str, group: str) -> int:
        summary = await self._redis.xpending(stream, group)
        if isinstance(summary, Mapping):
            return int(summary.get("pending", 0))
        if isinstance(summary, Sequence) and summary:
            return int(summary[0])
        return 0

    async def purge_dead_letters(self, stream: str, *, expires_before: datetime, count: int) -> int:
        if count <= 0:
            raise ValueError("count must be positive")
        cutoff = expires_before.replace(tzinfo=UTC) if expires_before.tzinfo is None else expires_before.astimezone(UTC)
        dlq_stream = f"{stream}:dlq"
        # Redis-generated DLQ ids encode the server-side insertion time.  This
        # avoids a second expiry index and keeps retention reliable even when
        # the worker clock or an untrusted producer timestamp is skewed.
        cutoff_milliseconds = int(cutoff.timestamp() * 1_000)
        raw_entries = (
            await self._redis.xrange(
                dlq_stream,
                min="-",
                max=f"{cutoff_milliseconds}-{(1 << 64) - 1}",
                count=count,
            )
            or []
        )
        message_ids: list[str] = []
        for message_id, _fields in raw_entries:
            if not isinstance(message_id, (str, bytes)):
                raise TypeError("Redis DLQ returned an invalid message id")
            message_ids.append(_decode_scalar(message_id))
        if not message_ids:
            return 0
        await self._redis.xdel(dlq_stream, *message_ids)
        return len(message_ids)

    async def _delivery_count(self, stream: str, group: str, message_id: str) -> int:
        entries = await self._redis.xpending_range(stream, group, message_id, message_id, 1)
        if not entries:
            return 1
        entry = entries[0]
        if isinstance(entry, Mapping):
            value = entry.get("times_delivered", entry.get("delivery_count", 1))
            return int(value)
        return 1


def parse_stream_event(
    stream: str,
    fields: StreamFieldMapping,
    limits: StreamPayloadLimits | None = None,
) -> RemnawaveStreamEvent:
    active_limits = limits or StreamPayloadLimits()
    decoded = _decode_fields(fields)
    if _payload_size(decoded) > active_limits.max_message_bytes:
        raise StreamContractError("payload_too_large")
    if decoded.get("v") != SUPPORTED_SCHEMA_VERSION:
        raise StreamContractError("unsupported_schema_version")

    try:
        if stream == USER_USAGE_STREAM:
            return _parse_user_usage(decoded, active_limits)
        if stream == SUBSCRIPTION_REQUESTS_STREAM:
            return _parse_subscription_request(decoded)
        if stream == NODE_CONNECTIONS_STREAM:
            return _parse_node_connections(decoded, active_limits)
    except (ValidationError, ValueError, TypeError) as exc:
        raise StreamContractError("invalid_payload") from exc

    raise StreamContractError("unknown_stream")


def _parse_user_usage(fields: Mapping[str, str], limits: StreamPayloadLimits) -> UserUsageEvent:
    wire = _UserUsageWire.model_validate(fields)
    pairs = wire.records.split(";")
    if not pairs or len(pairs) > limits.max_usage_records:
        raise ValueError("usage record count outside bounds")
    records: list[UserUsageRecord] = []
    for pair in pairs:
        parts = pair.split(":")
        if len(parts) != 2:
            raise ValueError("invalid usage record")
        user_id = _validate_positive_decimal(parts[0])
        total_bytes = _validate_decimal(parts[1])
        records.append(UserUsageRecord(user_id=int(user_id), total_bytes=int(total_bytes)))
    return UserUsageEvent(
        schema_version=wire.version,
        node_id=int(wire.node_id),
        observed_at=wire.timestamp,
        records=tuple(records),
    )


def _parse_subscription_request(fields: Mapping[str, str]) -> SubscriptionRequestEvent:
    normalized = dict(fields)
    # Remnawave backend 3.4.3's producer currently emits `ssrResponseType`
    # although its published contract calls the field `srrResponseType`.
    contract_value = normalized.get("srrResponseType")
    producer_value = normalized.get("ssrResponseType")
    if contract_value is not None and producer_value is not None and contract_value != producer_value:
        raise ValueError("conflicting SRR response type fields")
    if contract_value is None and producer_value is not None:
        normalized["srrResponseType"] = producer_value
    wire = _SubscriptionRequestWire.model_validate(normalized)
    return SubscriptionRequestEvent(
        schema_version=wire.version,
        user_id=int(wire.user_id),
        requested_at=wire.requested_at,
        request_ip=str(wire.request_ip) if wire.request_ip is not None else None,
        user_agent=wire.user_agent,
        srr_rule_name=wire.srr_rule_name,
        srr_response_type=wire.srr_response_type,
    )


def _parse_node_connections(fields: Mapping[str, str], limits: StreamPayloadLimits) -> NodeConnectionsEvent:
    wire = _NodeConnectionsWire.model_validate(fields)
    raw_users = json.loads(wire.users)
    users = _NODE_CONNECTION_USERS_ADAPTER.validate_python(raw_users)
    if len(users) > limits.max_connection_users:
        raise ValueError("connection user count outside bounds")
    normalized_users: list[NodeConnectionUser] = []
    for user in users:
        if len(user.ips) > limits.max_ips_per_user:
            raise ValueError("connection IP count outside bounds")
        normalized_users.append(
            NodeConnectionUser(
                user_id=int(user.user_id),
                ips=tuple(NodeConnectionIp(ip=str(item.ip), last_seen=item.last_seen) for item in user.ips),
            )
        )
    return NodeConnectionsEvent(
        schema_version=wire.version,
        node_id=int(wire.node_id),
        observed_at=wire.timestamp,
        users=tuple(normalized_users),
    )


def _decode_read_response(
    response: Any,
    *,
    delivery_count: int,
    payload_fingerprint_hmac_key: bytes,
) -> tuple[StreamMessage, ...]:
    messages: list[StreamMessage] = []
    for stream, entries in response or []:
        decoded_stream = _decode_scalar(stream)
        for message_id, fields in entries:
            messages.append(
                _decode_stream_message(
                    decoded_stream,
                    _decode_scalar(message_id),
                    fields,
                    delivery_count=delivery_count,
                    payload_fingerprint_hmac_key=payload_fingerprint_hmac_key,
                )
            )
    return tuple(messages)


def _decode_stream_message(
    stream: str,
    message_id: str,
    fields: StreamFieldMapping,
    *,
    delivery_count: int,
    payload_fingerprint_hmac_key: bytes,
) -> StreamMessage:
    payload_hmac_sha256 = _payload_hmac_sha256(fields, payload_fingerprint_hmac_key)
    try:
        decoded_fields = _decode_fields(fields)
    except StreamContractError as exc:
        return StreamMessage(
            stream=stream,
            message_id=message_id,
            fields={},
            delivery_count=delivery_count,
            contract_error=exc.code,
            payload_hmac_sha256=payload_hmac_sha256,
        )
    return StreamMessage(
        stream=stream,
        message_id=message_id,
        fields=decoded_fields,
        delivery_count=delivery_count,
        payload_hmac_sha256=payload_hmac_sha256,
    )


def _decode_fields(fields: StreamFieldMapping) -> dict[str, str]:
    if len(fields) > 32:
        raise StreamContractError("too_many_fields")
    try:
        return {_decode_scalar(key): _decode_scalar(value) for key, value in fields.items()}
    except UnicodeDecodeError as exc:
        raise StreamContractError("invalid_utf8") from exc


def _mapping_value(mapping: Mapping[Any, Any], key: str) -> Any:
    if key in mapping:
        return mapping[key]
    return mapping.get(key.encode("utf-8"))


def _decoded_mapping_value(mapping: Mapping[Any, Any], key: str) -> str | None:
    return _optional_decoded_scalar(_mapping_value(mapping, key))


def _optional_decoded_scalar(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, (str, bytes)):
        raise TypeError("Redis returned an invalid scalar")
    return _decode_scalar(value)


def _entry_message_id(entry: Any) -> str | None:
    if entry is None:
        return None
    if not isinstance(entry, Sequence) or isinstance(entry, (str, bytes)) or not entry:
        raise TypeError("Redis stream info returned an invalid entry")
    return _optional_decoded_scalar(entry[0])


def _decode_scalar(value: str | bytes) -> str:
    return value.decode("utf-8", errors="strict") if isinstance(value, bytes) else str(value)


def _payload_size(fields: Mapping[str, str]) -> int:
    return sum(len(key.encode("utf-8")) + len(value.encode("utf-8")) for key, value in fields.items())


def _payload_hmac_sha256(fields: StreamFieldMapping, key: bytes) -> str:
    digest = hmac.new(key, digestmod=hashlib.sha256)
    digest.update(b"cybervpn/remnawave-stream-payload/v1\0")
    encoded_fields = sorted((_scalar_bytes(key), _scalar_bytes(value)) for key, value in fields.items())
    for key, value in encoded_fields:
        digest.update(key)
        digest.update(b"\0")
        digest.update(value)
        digest.update(b"\0")
    return digest.hexdigest()


def _scalar_bytes(value: str | bytes) -> bytes:
    return value if isinstance(value, bytes) else value.encode("utf-8")


def _event_time(event: RemnawaveStreamEvent) -> datetime:
    if isinstance(event, SubscriptionRequestEvent):
        return event.requested_at
    return event.observed_at


def _event_type(event: RemnawaveStreamEvent) -> str:
    if isinstance(event, UserUsageEvent):
        return "user_usage"
    if isinstance(event, SubscriptionRequestEvent):
        return "subscription_requests"
    return "node_connections"


def _serialize_event(event: RemnawaveStreamEvent) -> dict[str, Any]:
    if isinstance(event, UserUsageEvent):
        return {
            "event_type": "user_usage",
            "schema_version": event.schema_version,
            "node_id": event.node_id,
            "observed_at": event.observed_at.isoformat(),
            "records": [{"user_id": record.user_id, "total_bytes": record.total_bytes} for record in event.records],
        }
    if isinstance(event, SubscriptionRequestEvent):
        return {
            "event_type": "subscription_requests",
            "schema_version": event.schema_version,
            "user_id": event.user_id,
            "requested_at": event.requested_at.isoformat(),
            "request_ip": event.request_ip,
            "user_agent": event.user_agent,
            "srr_rule_name": event.srr_rule_name,
            "srr_response_type": event.srr_response_type,
        }
    return {
        "event_type": "node_connections",
        "schema_version": event.schema_version,
        "node_id": event.node_id,
        "observed_at": event.observed_at.isoformat(),
        "users": [
            {
                "user_id": user.user_id,
                "ips": [{"ip": item.ip, "last_seen": item.last_seen.isoformat()} for item in user.ips],
            }
            for user in event.users
        ],
    }
