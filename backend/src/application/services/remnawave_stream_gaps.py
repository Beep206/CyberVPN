"""Durable, redacted tracking for gaps detected in ephemeral Remnawave streams."""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, cast

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.remnawave_stream_ingestion import payload_fingerprint
from src.config.settings import settings
from src.infrastructure.database.models.remnawave_upgrade_model import RemnawaveStreamGapModel

RemnawaveStreamName = Literal["user_usage", "subscription_requests", "node_connections"]
RemnawaveGapStatus = Literal["pending", "running", "reconciled", "partial", "failed"]
RemnawaveGapLossKind = Literal["exact_ids", "unknown_range"]

_MESSAGE_ID_RE = re.compile(r"^[0-9]+-[0-9]+$")
_REDACTED_DETAIL_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,120}$")
_MAX_DETECTION_CLOCK_SKEW = timedelta(minutes=5)
_MAX_MISSING_MESSAGE_IDS = 1_000


class RemnawaveStreamGapError(ValueError):
    pass


class RemnawaveStreamGapNotFoundError(RemnawaveStreamGapError):
    pass


class RemnawaveStreamGapTransitionError(RemnawaveStreamGapError):
    pass


@dataclass(frozen=True, slots=True)
class RemnawaveStreamGapResult:
    gap_id: uuid.UUID
    stream_name: RemnawaveStreamName
    loss_kind: RemnawaveGapLossKind
    missing_message_ids: tuple[str, ...]
    missing_count: int
    from_message_id: str | None
    to_message_id: str | None
    reconciliation_status: RemnawaveGapStatus
    detected_at: datetime
    reused: bool


class RemnawaveStreamGapService:
    """Register exact deleted IDs and enforce a bounded reconciliation state machine."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._clock = clock or (lambda: datetime.now(UTC))

    async def get(self, gap_id: uuid.UUID) -> RemnawaveStreamGapResult:
        row = (
            await self._session.execute(select(RemnawaveStreamGapModel).where(RemnawaveStreamGapModel.id == gap_id))
        ).scalar_one_or_none()
        if row is None:
            raise RemnawaveStreamGapNotFoundError("Remnawave stream gap was not found")
        return _result_from_model(row, reused=True)

    async def get_active(self, stream_name: RemnawaveStreamName) -> RemnawaveStreamGapResult | None:
        row = (
            await self._session.execute(
                select(RemnawaveStreamGapModel)
                .where(
                    RemnawaveStreamGapModel.stream_name == stream_name,
                    RemnawaveStreamGapModel.reconciliation_status.in_(("pending", "running")),
                )
                .order_by(RemnawaveStreamGapModel.detected_at, RemnawaveStreamGapModel.id)
                .limit(1)
                .with_for_update()
            )
        ).scalar_one_or_none()
        return _result_from_model(row, reused=True) if row is not None else None

    async def register(
        self,
        *,
        stream_name: RemnawaveStreamName,
        missing_message_ids: Iterable[str],
        detected_at: datetime,
    ) -> RemnawaveStreamGapResult:
        if stream_name not in {"user_usage", "subscription_requests", "node_connections"}:
            raise RemnawaveStreamGapError("Invalid Remnawave stream name")
        now = _aware_utc(self._clock())
        detected_at = _aware_utc(detected_at)
        if detected_at > now + _MAX_DETECTION_CLOCK_SKEW:
            raise RemnawaveStreamGapError("Gap detection timestamp exceeds allowed clock skew")
        ordered_ids = _normalize_message_ids(missing_message_ids)
        fingerprint = payload_fingerprint(
            "cybervpn/remnawave-stream-gap/v1\0"
            + json.dumps(
                {"stream_name": stream_name, "missing_message_ids": ordered_ids},
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        gap_id = uuid.uuid4()
        is_unrecoverable_metadata = stream_name == "subscription_requests"
        initial_status: RemnawaveGapStatus = "partial" if is_unrecoverable_metadata else "pending"
        initial_detail = "metadata_not_reconstructable" if is_unrecoverable_metadata else None
        reconciled_at = now if is_unrecoverable_metadata else None
        expires_at = (
            now + timedelta(days=settings.remnawave_stream_receipt_retention_days)
            if is_unrecoverable_metadata
            else None
        )
        statement = (
            insert(RemnawaveStreamGapModel)
            .values(
                id=gap_id,
                gap_fingerprint=fingerprint,
                loss_kind="exact_ids",
                stream_name=stream_name,
                detected_at=detected_at,
                missing_message_ids=ordered_ids,
                missing_count=len(ordered_ids),
                from_message_id=ordered_ids[0],
                to_message_id=ordered_ids[-1],
                reconciliation_status=initial_status,
                reconciled_at=reconciled_at,
                redacted_detail=initial_detail,
                expires_at=expires_at,
            )
            .on_conflict_do_nothing(constraint="uq_remnawave_stream_gap_fingerprint")
            .returning(RemnawaveStreamGapModel.id)
        )
        inserted_id = (await self._session.execute(statement)).scalar_one_or_none()
        reused = inserted_id is None
        if reused:
            existing = (
                await self._session.execute(
                    select(RemnawaveStreamGapModel).where(RemnawaveStreamGapModel.gap_fingerprint == fingerprint)
                )
            ).scalar_one()
            result = _result_from_model(existing, reused=True)
        else:
            result = RemnawaveStreamGapResult(
                gap_id=gap_id,
                stream_name=stream_name,
                loss_kind="exact_ids",
                missing_message_ids=tuple(ordered_ids),
                missing_count=len(ordered_ids),
                from_message_id=ordered_ids[0],
                to_message_id=ordered_ids[-1],
                reconciliation_status=initial_status,
                detected_at=detected_at,
                reused=False,
            )
        await self._session.flush()
        return result

    async def register_unknown_loss(
        self,
        *,
        stream_name: RemnawaveStreamName,
        checkpoint_message_id: str | None,
        observed_first_message_id: str | None,
        observed_last_message_id: str | None,
        observed_identity_hmac: str,
        detected_at: datetime,
        reason_code: str,
    ) -> RemnawaveStreamGapResult:
        """Persist a flush/restart loss when Redis cannot enumerate deleted IDs."""

        if stream_name not in {"user_usage", "subscription_requests", "node_connections"}:
            raise RemnawaveStreamGapError("Invalid Remnawave stream name")
        if not re.fullmatch(r"[a-f0-9]{64}", observed_identity_hmac):
            raise RemnawaveStreamGapError("Invalid observed stream identity fingerprint")
        if reason_code not in {
            "stream_missing",
            "group_missing",
            "group_skipped_range",
            "stream_regressed",
            "epoch_regressed",
        }:
            raise RemnawaveStreamGapError("Invalid unknown stream loss reason")
        checkpoint_message_id = _optional_message_id(checkpoint_message_id)
        observed_first_message_id = _optional_message_id(observed_first_message_id)
        observed_last_message_id = _optional_message_id(observed_last_message_id)
        now = _aware_utc(self._clock())
        detected_at = _aware_utc(detected_at)
        if detected_at > now + _MAX_DETECTION_CLOCK_SKEW:
            raise RemnawaveStreamGapError("Gap detection timestamp exceeds allowed clock skew")
        material = {
            "stream_name": stream_name,
            "loss_kind": "unknown_range",
            "checkpoint_message_id": checkpoint_message_id,
            "observed_first_message_id": observed_first_message_id,
            "observed_last_message_id": observed_last_message_id,
            "observed_identity_hmac": observed_identity_hmac,
            "reason_code": reason_code,
        }
        fingerprint = payload_fingerprint(
            "cybervpn/remnawave-stream-gap/v1\0" + json.dumps(material, separators=(",", ":"), sort_keys=True)
        )
        gap_id = uuid.uuid4()
        is_unrecoverable_metadata = stream_name == "subscription_requests"
        initial_status: RemnawaveGapStatus = "partial" if is_unrecoverable_metadata else "pending"
        initial_detail = "metadata_not_reconstructable" if is_unrecoverable_metadata else reason_code
        statement = (
            insert(RemnawaveStreamGapModel)
            .values(
                id=gap_id,
                gap_fingerprint=fingerprint,
                loss_kind="unknown_range",
                stream_name=stream_name,
                detected_at=detected_at,
                missing_message_ids=[],
                missing_count=0,
                from_message_id=checkpoint_message_id,
                to_message_id=observed_first_message_id or observed_last_message_id,
                reconciliation_status=initial_status,
                reconciled_at=now if is_unrecoverable_metadata else None,
                redacted_detail=initial_detail,
                expires_at=(
                    now + timedelta(days=settings.remnawave_stream_receipt_retention_days)
                    if is_unrecoverable_metadata
                    else None
                ),
            )
            .on_conflict_do_nothing(constraint="uq_remnawave_stream_gap_fingerprint")
            .returning(RemnawaveStreamGapModel.id)
        )
        inserted_id = (await self._session.execute(statement)).scalar_one_or_none()
        if inserted_id is None:
            existing = (
                await self._session.execute(
                    select(RemnawaveStreamGapModel).where(RemnawaveStreamGapModel.gap_fingerprint == fingerprint)
                )
            ).scalar_one()
            result = _result_from_model(existing, reused=True)
        else:
            result = RemnawaveStreamGapResult(
                gap_id=gap_id,
                stream_name=stream_name,
                loss_kind="unknown_range",
                missing_message_ids=(),
                missing_count=0,
                from_message_id=checkpoint_message_id,
                to_message_id=observed_first_message_id or observed_last_message_id,
                reconciliation_status=initial_status,
                detected_at=detected_at,
                reused=False,
            )
        await self._session.flush()
        return result

    async def transition(
        self,
        *,
        gap_id: uuid.UUID,
        reconciliation_status: RemnawaveGapStatus,
        redacted_detail: str,
        authoritative_read_completed: bool,
    ) -> RemnawaveStreamGapResult:
        if not _REDACTED_DETAIL_RE.fullmatch(redacted_detail):
            raise RemnawaveStreamGapError("Invalid redacted reconciliation detail")
        row = (
            await self._session.execute(
                select(RemnawaveStreamGapModel).where(RemnawaveStreamGapModel.id == gap_id).with_for_update()
            )
        ).scalar_one_or_none()
        if row is None:
            raise RemnawaveStreamGapNotFoundError("Remnawave stream gap was not found")

        current_status = row.reconciliation_status
        if reconciliation_status == "running":
            if current_status not in {"pending", "running"}:
                raise RemnawaveStreamGapTransitionError("Terminal gap reconciliation cannot be restarted")
        elif reconciliation_status in {"reconciled", "partial"}:
            if row.stream_name == "subscription_requests":
                if reconciliation_status != "partial":
                    raise RemnawaveStreamGapTransitionError("Lost subscription metadata cannot be reconstructed")
            elif not authoritative_read_completed:
                raise RemnawaveStreamGapTransitionError(
                    "Usage and presence reconciliation requires an authoritative Remnawave read"
                )
            if current_status not in {"running", reconciliation_status}:
                raise RemnawaveStreamGapTransitionError("Gap reconciliation must be claimed before completion")
        elif reconciliation_status == "failed":
            if current_status not in {"pending", "running", "failed"}:
                raise RemnawaveStreamGapTransitionError("Terminal gap reconciliation cannot be overwritten")
        else:
            raise RemnawaveStreamGapTransitionError("Invalid gap reconciliation transition")

        row.reconciliation_status = reconciliation_status
        row.redacted_detail = redacted_detail
        now = _aware_utc(self._clock())
        is_terminal = reconciliation_status in {"reconciled", "partial", "failed"}
        if current_status != reconciliation_status:
            row.reconciled_at = now if is_terminal else None
            row.expires_at = (
                now + timedelta(days=settings.remnawave_stream_receipt_retention_days) if is_terminal else None
            )
        await self._session.flush()
        return _result_from_model(row, reused=current_status == reconciliation_status)


def _normalize_message_ids(values: Iterable[str]) -> list[str]:
    unique: set[str] = set()
    for value in values:
        normalized = value.strip()
        if not _MESSAGE_ID_RE.fullmatch(normalized) or len(normalized) > 64:
            raise RemnawaveStreamGapError("Invalid missing Remnawave stream message id")
        if normalized in unique:
            raise RemnawaveStreamGapError("Missing Remnawave stream message ids must be unique")
        unique.add(normalized)
        if len(unique) > _MAX_MISSING_MESSAGE_IDS:
            raise RemnawaveStreamGapError("Too many missing Remnawave stream message ids")
    if not unique:
        raise RemnawaveStreamGapError("At least one missing Remnawave stream message id is required")
    return sorted(unique, key=lambda value: tuple(int(part) for part in value.split("-", 1)))


def _optional_message_id(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not _MESSAGE_ID_RE.fullmatch(normalized) or len(normalized) > 64:
        raise RemnawaveStreamGapError("Invalid Remnawave stream message id")
    return normalized


def _result_from_model(model: RemnawaveStreamGapModel, *, reused: bool) -> RemnawaveStreamGapResult:
    return RemnawaveStreamGapResult(
        gap_id=model.id,
        stream_name=cast(RemnawaveStreamName, model.stream_name),
        loss_kind=cast(RemnawaveGapLossKind, model.loss_kind),
        missing_message_ids=tuple(model.missing_message_ids),
        missing_count=model.missing_count,
        from_message_id=model.from_message_id,
        to_message_id=model.to_message_id,
        reconciliation_status=cast(RemnawaveGapStatus, model.reconciliation_status),
        detected_at=model.detected_at,
        reused=reused,
    )


def _aware_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
