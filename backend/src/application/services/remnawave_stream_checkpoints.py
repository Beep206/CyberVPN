"""Durable startup comparison for detecting full Remnawave stream loss."""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.remnawave_stream_gaps import (
    RemnawaveStreamGapResult,
    RemnawaveStreamGapService,
    RemnawaveStreamName,
)
from src.application.services.remnawave_stream_ingestion import payload_fingerprint
from src.infrastructure.database.models.remnawave_upgrade_model import RemnawaveStreamCheckpointModel

_STREAM_ID_RE = re.compile(r"^[0-9]+-[0-9]+$")
_IDENTITY_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_MAX_OBSERVED_CLOCK_SKEW = timedelta(minutes=5)


class RemnawaveStreamCheckpointError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RemnawaveStreamObservationResult:
    stream_name: RemnawaveStreamName
    last_committed_message_id: str | None
    stream_exists: bool
    group_exists: bool
    loss_detected: bool
    loss_reason: str | None
    gap: RemnawaveStreamGapResult | None
    observed_at: datetime


class RemnawaveStreamCheckpointService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._clock = clock or (lambda: datetime.now(UTC))

    async def observe_startup(
        self,
        *,
        stream_name: RemnawaveStreamName,
        observed_stream_identity: str,
        stream_exists: bool,
        group_exists: bool,
        first_message_id: str | None,
        last_message_id: str | None,
        group_last_delivered_id: str | None,
        group_pending_count: int,
        group_pending_min_id: str | None,
        group_pending_max_id: str | None,
        observed_at: datetime,
        group_lag: int | None = None,
    ) -> RemnawaveStreamObservationResult:
        if stream_name not in {"user_usage", "subscription_requests", "node_connections"}:
            raise RemnawaveStreamCheckpointError("Invalid Remnawave stream name")
        identity = observed_stream_identity.strip()
        if not _IDENTITY_RE.fullmatch(identity):
            raise RemnawaveStreamCheckpointError("Invalid observed stream identity")
        first_message_id = _optional_stream_id(first_message_id)
        last_message_id = _optional_stream_id(last_message_id)
        group_last_delivered_id = _optional_stream_id(group_last_delivered_id)
        group_pending_min_id = _optional_stream_id(group_pending_min_id)
        group_pending_max_id = _optional_stream_id(group_pending_max_id)
        now = _aware_utc(self._clock())
        observed_at = _aware_utc(observed_at)
        if observed_at > now + _MAX_OBSERVED_CLOCK_SKEW:
            raise RemnawaveStreamCheckpointError("Stream observation timestamp exceeds allowed clock skew")
        if not stream_exists and any(
            value is not None for value in (first_message_id, last_message_id, group_last_delivered_id)
        ):
            raise RemnawaveStreamCheckpointError("Missing stream cannot report message ids")
        if not stream_exists and group_exists:
            raise RemnawaveStreamCheckpointError("Consumer group cannot exist without its stream")
        if not group_exists and group_last_delivered_id is not None:
            raise RemnawaveStreamCheckpointError("Missing consumer group cannot report a delivered id")
        if isinstance(group_pending_count, bool) or not 0 <= group_pending_count <= 100_000:
            raise RemnawaveStreamCheckpointError("Invalid consumer group pending count")
        if not group_exists and (
            group_pending_count != 0 or group_pending_min_id is not None or group_pending_max_id is not None
        ):
            raise RemnawaveStreamCheckpointError("Missing consumer group cannot report pending entries")
        if group_pending_count == 0 and (group_pending_min_id is not None or group_pending_max_id is not None):
            raise RemnawaveStreamCheckpointError("Empty PEL cannot report pending message ids")
        if group_pending_count > 0 and (group_pending_min_id is None or group_pending_max_id is None):
            raise RemnawaveStreamCheckpointError("Non-empty PEL requires a bounded pending range")
        if group_lag is not None and (isinstance(group_lag, bool) or not 0 <= group_lag <= 10_000_000):
            raise RemnawaveStreamCheckpointError("Invalid consumer group lag")
        if not group_exists and group_lag is not None:
            raise RemnawaveStreamCheckpointError("Missing consumer group cannot report lag")

        identity_hmac = payload_fingerprint(f"cybervpn/remnawave-stream-epoch/v1\0{identity}")
        row = (
            await self._session.execute(
                select(RemnawaveStreamCheckpointModel)
                .where(RemnawaveStreamCheckpointModel.stream_name == stream_name)
                .with_for_update()
            )
        ).scalar_one_or_none()
        is_new_checkpoint = row is None
        if row is None:
            row = RemnawaveStreamCheckpointModel(
                id=uuid.uuid4(),
                stream_name=stream_name,
                last_committed_message_id=None,
                last_committed_ms=None,
                last_committed_sequence=None,
                observed_identity_hmac=identity_hmac,
                observed_first_message_id=first_message_id,
                observed_last_message_id=last_message_id,
                observed_group_last_delivered_id=group_last_delivered_id,
                observed_group_pending_count=group_pending_count,
                observed_group_pending_min_id=group_pending_min_id,
                observed_group_pending_max_id=group_pending_max_id,
                observed_group_lag=group_lag,
                stream_exists=stream_exists,
                group_exists=group_exists,
                observed_at=observed_at,
                updated_at=now,
            )
            self._session.add(row)
            await self._session.flush()

        active_gap = await RemnawaveStreamGapService(self._session, clock=self._clock).get_active(stream_name)
        if active_gap is not None:
            _apply_observation(
                row,
                identity_hmac=identity_hmac,
                first_message_id=first_message_id,
                last_message_id=last_message_id,
                group_last_delivered_id=group_last_delivered_id,
                group_pending_count=group_pending_count,
                group_pending_min_id=group_pending_min_id,
                group_pending_max_id=group_pending_max_id,
                group_lag=group_lag,
                stream_exists=stream_exists,
                group_exists=group_exists,
                observed_at=observed_at,
                updated_at=now,
            )
            await self._session.flush()
            return RemnawaveStreamObservationResult(
                stream_name=stream_name,
                last_committed_message_id=row.last_committed_message_id,
                stream_exists=stream_exists,
                group_exists=group_exists,
                loss_detected=True,
                loss_reason="gap_pending_reconciliation",
                gap=active_gap,
                observed_at=observed_at,
            )
        if is_new_checkpoint:
            return RemnawaveStreamObservationResult(
                stream_name=stream_name,
                last_committed_message_id=None,
                stream_exists=stream_exists,
                group_exists=group_exists,
                loss_detected=False,
                loss_reason=None,
                gap=None,
                observed_at=observed_at,
            )

        loss_reason = _detect_loss(
            row=row,
            identity_hmac=identity_hmac,
            stream_exists=stream_exists,
            group_exists=group_exists,
            first_message_id=first_message_id,
            last_message_id=last_message_id,
            group_last_delivered_id=group_last_delivered_id,
            group_pending_count=group_pending_count,
            group_pending_min_id=group_pending_min_id,
        )
        gap = None
        if loss_reason is not None:
            gap = await RemnawaveStreamGapService(self._session, clock=self._clock).register_unknown_loss(
                stream_name=stream_name,
                checkpoint_message_id=row.last_committed_message_id,
                observed_first_message_id=first_message_id,
                observed_last_message_id=last_message_id,
                observed_identity_hmac=identity_hmac,
                detected_at=observed_at,
                reason_code=loss_reason,
            )

        _apply_observation(
            row,
            identity_hmac=identity_hmac,
            first_message_id=first_message_id,
            last_message_id=last_message_id,
            group_last_delivered_id=group_last_delivered_id,
            group_pending_count=group_pending_count,
            group_pending_min_id=group_pending_min_id,
            group_pending_max_id=group_pending_max_id,
            group_lag=group_lag,
            stream_exists=stream_exists,
            group_exists=group_exists,
            observed_at=observed_at,
            updated_at=now,
        )
        await self._session.flush()
        return RemnawaveStreamObservationResult(
            stream_name=stream_name,
            last_committed_message_id=row.last_committed_message_id,
            stream_exists=stream_exists,
            group_exists=group_exists,
            loss_detected=loss_reason is not None,
            loss_reason=loss_reason,
            gap=gap,
            observed_at=observed_at,
        )


def _detect_loss(
    *,
    row: RemnawaveStreamCheckpointModel,
    identity_hmac: str,
    stream_exists: bool,
    group_exists: bool,
    first_message_id: str | None,
    last_message_id: str | None,
    group_last_delivered_id: str | None,
    group_pending_count: int,
    group_pending_min_id: str | None,
) -> str | None:
    checkpoint = row.last_committed_message_id
    if checkpoint is None:
        return None
    if not stream_exists:
        return "stream_missing"
    if not group_exists:
        return "group_missing"
    if last_message_id is None or _stream_id_tuple(last_message_id) < _stream_id_tuple(checkpoint):
        return "stream_regressed"
    if (
        group_last_delivered_id is not None
        and _stream_id_tuple(group_last_delivered_id) > _stream_id_tuple(checkpoint)
        and (
            group_pending_count == 0
            or (
                group_pending_min_id is not None
                and _stream_id_tuple(group_pending_min_id) > _stream_id_tuple(checkpoint)
            )
        )
    ):
        return "group_skipped_range"
    if (
        row.observed_identity_hmac is not None
        and row.observed_identity_hmac != identity_hmac
        and (first_message_id is None or _stream_id_tuple(first_message_id) > _stream_id_tuple(checkpoint))
    ):
        return "epoch_regressed"
    return None


def _apply_observation(
    row: RemnawaveStreamCheckpointModel,
    *,
    identity_hmac: str,
    first_message_id: str | None,
    last_message_id: str | None,
    group_last_delivered_id: str | None,
    group_pending_count: int,
    group_pending_min_id: str | None,
    group_pending_max_id: str | None,
    group_lag: int | None,
    stream_exists: bool,
    group_exists: bool,
    observed_at: datetime,
    updated_at: datetime,
) -> None:
    row.observed_identity_hmac = identity_hmac
    row.observed_first_message_id = first_message_id
    row.observed_last_message_id = last_message_id
    row.observed_group_last_delivered_id = group_last_delivered_id
    row.observed_group_pending_count = group_pending_count
    row.observed_group_pending_min_id = group_pending_min_id
    row.observed_group_pending_max_id = group_pending_max_id
    row.observed_group_lag = group_lag
    row.stream_exists = stream_exists
    row.group_exists = group_exists
    row.observed_at = observed_at
    row.updated_at = updated_at


def _optional_stream_id(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if len(normalized) > 64 or not _STREAM_ID_RE.fullmatch(normalized):
        raise RemnawaveStreamCheckpointError("Invalid Redis stream message id")
    return normalized


def _stream_id_tuple(value: str) -> tuple[int, int]:
    milliseconds, sequence = value.split("-", 1)
    return int(milliseconds), int(sequence)


def _aware_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
