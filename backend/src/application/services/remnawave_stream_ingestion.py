"""Transactional, idempotent persistence for Remnawave 3.4 Redis Stream events."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from ipaddress import ip_address

from sqlalchemy import and_, case, delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.infrastructure.database.models.remnawave_upgrade_model import (
    RemnawaveNodeConnectionsHourlyModel,
    RemnawaveNodePresenceModel,
    RemnawaveStreamCheckpointModel,
    RemnawaveStreamDeadLetterModel,
    RemnawaveStreamReceiptModel,
    RemnawaveSubscriptionRequestEventModel,
    RemnawaveUserUsageHourlyModel,
)

_IDEMPOTENCY_KEY_RE = re.compile(r"^remnawave:(user_usage|subscription_requests|node_connections):([0-9]+-[0-9]+)$")
_FINGERPRINT_RE = re.compile(r"^[a-f0-9]{64}$")
_REDACTED_CODE_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,120}$")
_MAX_PRODUCER_CLOCK_SKEW = timedelta(minutes=5)


class RemnawaveStreamIngestionError(ValueError):
    pass


class RemnawaveStreamIdempotencyConflict(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class UsageRecord:
    user_id: int
    total_bytes: int


@dataclass(frozen=True, slots=True)
class ConnectionIp:
    ip: str
    last_seen: datetime


@dataclass(frozen=True, slots=True)
class ConnectionUser:
    user_id: int
    ips: tuple[ConnectionIp, ...]


class RemnawaveStreamIngestionService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._clock = clock or (lambda: datetime.now(UTC))

    async def persist_user_usage(
        self,
        *,
        idempotency_key: str,
        payload_sha256: str,
        schema_version: str,
        node_id: int,
        observed_at: datetime,
        records: Iterable[UsageRecord],
    ) -> bool:
        received_at = self._validate_producer_timestamp(observed_at, field_name="observed_at")
        stream_name, message_id = self._parse_key(idempotency_key, expected_stream="user_usage")
        if await self._already_committed(stream_name, message_id, payload_sha256):
            return False
        bucket_at = _hour_bucket(observed_at)
        expires_at = received_at + timedelta(days=settings.remnawave_user_usage_retention_days)
        for record in records:
            # Remnawave 3.4 emits bytes consumed in this export batch, not a
            # cumulative counter.  The receipt makes each message idempotent;
            # the PostgreSQL upsert makes concurrent consumer replicas add the
            # per-message deltas without a read/modify/write race.
            statement = insert(RemnawaveUserUsageHourlyModel).values(
                id=uuid.uuid4(),
                bucket_at=bucket_at,
                node_id=node_id,
                user_id=record.user_id,
                total_bytes=record.total_bytes,
                expires_at=expires_at,
                updated_at=received_at,
            )
            statement = statement.on_conflict_do_update(
                constraint="uq_remnawave_user_usage_hour",
                set_={
                    "total_bytes": RemnawaveUserUsageHourlyModel.total_bytes + statement.excluded.total_bytes,
                    "expires_at": func.greatest(
                        RemnawaveUserUsageHourlyModel.expires_at,
                        statement.excluded.expires_at,
                    ),
                    "updated_at": statement.excluded.updated_at,
                },
            )
            await self._session.execute(statement)
        self._add_receipt(stream_name, message_id, schema_version, payload_sha256)
        await self._record_committed_checkpoint(stream_name, message_id)
        await self._session.flush()
        return True

    async def persist_subscription_request(
        self,
        *,
        idempotency_key: str,
        payload_sha256: str,
        schema_version: str,
        user_id: int,
        requested_at: datetime,
        request_ip: str | None,
        user_agent: str | None,
        srr_rule_name: str | None,
        srr_response_type: str,
    ) -> bool:
        received_at = self._validate_producer_timestamp(requested_at, field_name="requested_at")
        stream_name, message_id = self._parse_key(idempotency_key, expected_stream="subscription_requests")
        if await self._already_committed(stream_name, message_id, payload_sha256):
            return False
        self._session.add(
            RemnawaveSubscriptionRequestEventModel(
                id=uuid.uuid4(),
                stream_message_id=message_id,
                user_id=user_id,
                requested_at=requested_at,
                response_type=srr_response_type,
                response_rule_name=srr_rule_name,
                request_ip_hmac=_hmac_ip(request_ip) if request_ip else None,
                user_agent_family=_user_agent_family(user_agent),
                expires_at=received_at + timedelta(days=settings.remnawave_subscription_request_retention_days),
            )
        )
        self._add_receipt(stream_name, message_id, schema_version, payload_sha256)
        await self._record_committed_checkpoint(stream_name, message_id)
        await self._session.flush()
        return True

    async def persist_node_connections(
        self,
        *,
        idempotency_key: str,
        payload_sha256: str,
        schema_version: str,
        node_id: int,
        observed_at: datetime,
        users: Iterable[ConnectionUser],
    ) -> bool:
        received_at = self._validate_producer_timestamp(observed_at, field_name="observed_at")
        snapshot_at = _as_aware_utc(observed_at)
        stream_name, message_id = self._parse_key(idempotency_key, expected_stream="node_connections")
        if await self._already_committed(stream_name, message_id, payload_sha256):
            return False

        # Serialize snapshots per node across consumer replicas.  The advisory
        # transaction lock avoids a stale DELETE racing with a newer snapshot,
        # while still allowing different nodes to ingest concurrently.
        await self._session.execute(select(func.pg_advisory_xact_lock(node_id)))
        latest_snapshot_at = (
            await self._session.execute(
                select(func.max(RemnawaveNodePresenceModel.snapshot_at)).where(
                    RemnawaveNodePresenceModel.node_id == node_id
                )
            )
        ).scalar_one_or_none()
        replace_presence = latest_snapshot_at is None or snapshot_at >= _as_aware_utc(latest_snapshot_at)
        if replace_presence:
            await self._session.execute(
                delete(RemnawaveNodePresenceModel).where(RemnawaveNodePresenceModel.node_id == node_id)
            )

        bucket_at = _hour_bucket(snapshot_at)
        expires_at = received_at + timedelta(days=settings.remnawave_node_connections_retention_days)
        for user in users:
            connection_count = 0
            seen_hashes: set[str] = set()
            for item in user.ips:
                self._validate_timestamp_against_received_at(
                    item.last_seen,
                    received_at=received_at,
                    field_name="last_seen",
                )
                canonical_ip = str(ip_address(item.ip))
                ip_hmac = _hmac_ip(canonical_ip)
                if ip_hmac in seen_hashes:
                    continue
                seen_hashes.add(ip_hmac)
                connection_count += 1
                if replace_presence:
                    self._session.add(
                        RemnawaveNodePresenceModel(
                            id=uuid.uuid4(),
                            node_id=node_id,
                            user_id=user.user_id,
                            ip_hmac=ip_hmac,
                            last_seen_at=_as_aware_utc(item.last_seen),
                            snapshot_at=snapshot_at,
                            expires_at=expires_at,
                        )
                    )

            hourly_statement = insert(RemnawaveNodeConnectionsHourlyModel).values(
                id=uuid.uuid4(),
                bucket_at=bucket_at,
                node_id=node_id,
                user_id=user.user_id,
                connection_count=connection_count,
                expires_at=expires_at,
            )
            hourly_statement = hourly_statement.on_conflict_do_update(
                constraint="uq_remnawave_node_connections_hour",
                set_={
                    "connection_count": RemnawaveNodeConnectionsHourlyModel.connection_count
                    + hourly_statement.excluded.connection_count,
                    "expires_at": func.greatest(
                        RemnawaveNodeConnectionsHourlyModel.expires_at,
                        hourly_statement.excluded.expires_at,
                    ),
                },
            )
            await self._session.execute(hourly_statement)
        self._add_receipt(stream_name, message_id, schema_version, payload_sha256)
        await self._record_committed_checkpoint(stream_name, message_id)
        await self._session.flush()
        return True

    async def reconcile_current_node_presence(
        self,
        *,
        node_id: int,
        observed_at: datetime,
        users: Iterable[ConnectionUser],
    ) -> bool:
        """Replace only recoverable current presence from an authoritative REST snapshot.

        Lost hourly connection counts are intentionally not fabricated.  The
        owning stream gap therefore remains ``partial`` after this succeeds.
        """

        if isinstance(node_id, bool) or not isinstance(node_id, int) or node_id <= 0:
            raise RemnawaveStreamIngestionError("Invalid Remnawave numeric node id")
        received_at = self._validate_producer_timestamp(observed_at, field_name="observed_at")
        snapshot_at = _as_aware_utc(observed_at)
        await self._session.execute(select(func.pg_advisory_xact_lock(node_id)))
        latest_snapshot_at = (
            await self._session.execute(
                select(func.max(RemnawaveNodePresenceModel.snapshot_at)).where(
                    RemnawaveNodePresenceModel.node_id == node_id
                )
            )
        ).scalar_one_or_none()
        if latest_snapshot_at is not None and snapshot_at < _as_aware_utc(latest_snapshot_at):
            return False

        await self._session.execute(
            delete(RemnawaveNodePresenceModel).where(RemnawaveNodePresenceModel.node_id == node_id)
        )
        expires_at = received_at + timedelta(days=settings.remnawave_node_connections_retention_days)
        seen_presence: set[tuple[int, str]] = set()
        for user in users:
            if isinstance(user.user_id, bool) or user.user_id <= 0:
                raise RemnawaveStreamIngestionError("Invalid Remnawave numeric user id")
            for item in user.ips:
                self._validate_timestamp_against_received_at(
                    item.last_seen,
                    received_at=received_at,
                    field_name="last_seen",
                )
                ip_hmac = _hmac_ip(str(ip_address(item.ip)))
                presence_key = (user.user_id, ip_hmac)
                if presence_key in seen_presence:
                    continue
                seen_presence.add(presence_key)
                self._session.add(
                    RemnawaveNodePresenceModel(
                        id=uuid.uuid4(),
                        node_id=node_id,
                        user_id=user.user_id,
                        ip_hmac=ip_hmac,
                        last_seen_at=_as_aware_utc(item.last_seen),
                        snapshot_at=snapshot_at,
                        expires_at=expires_at,
                    )
                )
        await self._session.flush()
        return True

    def _validate_producer_timestamp(self, value: datetime, *, field_name: str) -> datetime:
        received_at = _as_aware_utc(self._clock())
        self._validate_timestamp_against_received_at(
            value,
            received_at=received_at,
            field_name=field_name,
        )
        return received_at

    @staticmethod
    def _validate_timestamp_against_received_at(
        value: datetime,
        *,
        received_at: datetime,
        field_name: str,
    ) -> None:
        producer_at = _as_aware_utc(value)
        if producer_at > received_at + _MAX_PRODUCER_CLOCK_SKEW:
            raise RemnawaveStreamIngestionError(
                f"Remnawave stream {field_name} exceeds the allowed producer clock skew"
            )

    async def upsert_dead_letter(
        self,
        *,
        stream_name: str,
        message_id: str,
        schema_version: str | None,
        error_type: str,
        redacted_reason: str,
        source_fingerprint: str,
        attempts: int,
    ) -> None:
        """Persist only bounded, re-keyed DLQ metadata; never a raw payload."""

        self._parse_key(f"remnawave:{stream_name}:{message_id}", expected_stream=stream_name)
        if schema_version is not None and not 1 <= len(schema_version) <= 12:
            raise RemnawaveStreamIngestionError("Invalid DLQ schema version")
        if not _REDACTED_CODE_RE.fullmatch(error_type) or not _REDACTED_CODE_RE.fullmatch(redacted_reason):
            raise RemnawaveStreamIngestionError("Invalid redacted DLQ error metadata")
        if not _FINGERPRINT_RE.fullmatch(source_fingerprint):
            raise RemnawaveStreamIngestionError("Invalid DLQ source fingerprint")
        if isinstance(attempts, bool) or not 1 <= attempts <= 10_000:
            raise RemnawaveStreamIngestionError("Invalid DLQ attempts")
        now = datetime.now(UTC)
        fingerprint_material = json.dumps(
            {
                "stream_name": stream_name,
                "message_id": message_id,
                "schema_version": schema_version,
                "error_type": error_type,
                "source_fingerprint": source_fingerprint,
            },
            separators=(",", ":"),
            sort_keys=True,
        )
        stored_fingerprint = payload_fingerprint(f"cybervpn/remnawave-stream-dlq/v1\0{fingerprint_material}")
        statement = insert(RemnawaveStreamDeadLetterModel).values(
            id=uuid.uuid4(),
            stream_name=stream_name,
            message_id=message_id,
            schema_version=schema_version,
            payload_sha256=stored_fingerprint,
            attempts=attempts,
            error_code=error_type,
            redacted_error=redacted_reason,
            expires_at=now + timedelta(days=settings.remnawave_stream_receipt_retention_days),
            created_at=now,
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_remnawave_stream_dlq",
            set_={
                "schema_version": statement.excluded.schema_version,
                "payload_sha256": statement.excluded.payload_sha256,
                "attempts": func.greatest(
                    RemnawaveStreamDeadLetterModel.attempts,
                    statement.excluded.attempts,
                ),
                "error_code": statement.excluded.error_code,
                "redacted_error": statement.excluded.redacted_error,
                "expires_at": func.greatest(
                    RemnawaveStreamDeadLetterModel.expires_at,
                    statement.excluded.expires_at,
                ),
            },
        )
        await self._session.execute(statement)
        await self._session.flush()

    async def _already_committed(self, stream_name: str, message_id: str, payload_sha256: str) -> bool:
        receipt = (
            await self._session.execute(
                select(RemnawaveStreamReceiptModel).where(
                    RemnawaveStreamReceiptModel.stream_name == stream_name,
                    RemnawaveStreamReceiptModel.message_id == message_id,
                )
            )
        ).scalar_one_or_none()
        if receipt is None:
            return False
        if not hmac.compare_digest(receipt.payload_sha256, payload_sha256):
            raise RemnawaveStreamIdempotencyConflict("Idempotency key was reused with a different payload")
        return receipt.processing_status == "committed"

    @staticmethod
    def _parse_key(idempotency_key: str, *, expected_stream: str) -> tuple[str, str]:
        match = _IDEMPOTENCY_KEY_RE.fullmatch(idempotency_key.strip())
        if match is None or match.group(1) != expected_stream:
            raise RemnawaveStreamIngestionError("Invalid Remnawave stream idempotency key")
        return match.group(1), match.group(2)

    def _add_receipt(self, stream_name: str, message_id: str, schema_version: str, payload_sha256: str) -> None:
        now = datetime.now(UTC)
        self._session.add(
            RemnawaveStreamReceiptModel(
                id=uuid.uuid4(),
                stream_name=stream_name,
                message_id=message_id,
                schema_version=schema_version,
                payload_sha256=payload_sha256,
                processing_status="committed",
                attempts=1,
                processed_at=now,
                expires_at=now + timedelta(days=settings.remnawave_stream_receipt_retention_days),
                created_at=now,
            )
        )

    async def _record_committed_checkpoint(self, stream_name: str, message_id: str) -> None:
        message_ms, message_sequence = (int(part) for part in message_id.split("-", 1))
        statement = insert(RemnawaveStreamCheckpointModel).values(
            id=uuid.uuid4(),
            stream_name=stream_name,
            last_committed_message_id=message_id,
            last_committed_ms=message_ms,
            last_committed_sequence=message_sequence,
            stream_exists=False,
            group_exists=False,
            updated_at=_as_aware_utc(self._clock()),
        )
        newer = or_(
            RemnawaveStreamCheckpointModel.last_committed_ms.is_(None),
            statement.excluded.last_committed_ms > RemnawaveStreamCheckpointModel.last_committed_ms,
            and_(
                statement.excluded.last_committed_ms == RemnawaveStreamCheckpointModel.last_committed_ms,
                statement.excluded.last_committed_sequence > RemnawaveStreamCheckpointModel.last_committed_sequence,
            ),
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_remnawave_stream_checkpoint",
            set_={
                "last_committed_message_id": case(
                    (newer, statement.excluded.last_committed_message_id),
                    else_=RemnawaveStreamCheckpointModel.last_committed_message_id,
                ),
                "last_committed_ms": case(
                    (newer, statement.excluded.last_committed_ms),
                    else_=RemnawaveStreamCheckpointModel.last_committed_ms,
                ),
                "last_committed_sequence": case(
                    (newer, statement.excluded.last_committed_sequence),
                    else_=RemnawaveStreamCheckpointModel.last_committed_sequence,
                ),
                "updated_at": statement.excluded.updated_at,
            },
        )
        await self._session.execute(statement)


def payload_fingerprint(canonical_json: str) -> str:
    """Return a non-reversible, domain-separated receipt fingerprint."""

    secret = settings.remnawave_stream_ip_hmac_secret.get_secret_value().strip()
    if len(secret) < 32:
        raise RemnawaveStreamIngestionError("Remnawave stream payload hashing is not configured")
    material = b"cybervpn/remnawave-stream-receipt/v1\0" + canonical_json.encode("utf-8")
    return hmac.new(secret.encode("utf-8"), material, hashlib.sha256).hexdigest()


def _hour_bucket(value: datetime) -> datetime:
    aware = _as_aware_utc(value)
    return aware.replace(minute=0, second=0, microsecond=0)


def _as_aware_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _hmac_ip(value: str) -> str:
    secret = settings.remnawave_stream_ip_hmac_secret.get_secret_value().strip()
    if len(secret) < 32:
        raise RemnawaveStreamIngestionError("Remnawave stream IP hashing is not configured")
    canonical = str(ip_address(value))
    return hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()


def _user_agent_family(value: str | None) -> str | None:
    if not value:
        return None
    lowered = value.lower()
    families = (
        ("mihomo", ("mihomo", "clash.meta")),
        ("clash", ("clash",)),
        ("sing-box", ("sing-box",)),
        ("v2rayn", ("v2rayn",)),
        ("hiddify", ("hiddify",)),
        ("nekobox", ("nekobox",)),
        ("shadowrocket", ("shadowrocket",)),
        ("streisand", ("streisand",)),
        ("okhttp", ("okhttp",)),
        ("curl", ("curl",)),
        ("firefox", ("firefox",)),
        ("chrome", ("chrome", "chromium")),
        ("safari", ("safari",)),
        ("telegram", ("telegram",)),
    )
    for family, markers in families:
        if any(marker in lowered for marker in markers):
            return family
    return "other"
