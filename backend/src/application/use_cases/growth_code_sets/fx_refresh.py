"""FX provider refresh use case for Growth Codes v6.2."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.growth_risk_fx_model import (
    FxProviderConfigModel,
    FxProviderRefreshRunModel,
    FxRateSnapshotModel,
)

FxRefreshTrigger = Literal["scheduled", "admin", "manual", "system_retry"]

_REDACTED_REASON_VALUE = "[REDACTED]"
_CHANGE_REASON_SECRET_PATTERNS = (
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{10,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"(?i)\b(?:vless|trojan|ss)://\S+"),
    re.compile(r"(?i)\b(?:secret|token|password|api[_-]?key|provider[_-]?secret)\s*[:=]\s*\S+"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b[A-Z0-9]{6,}(?:-[A-Z0-9]{3,})+\b"),
)


class FxRefreshError(ValueError):
    """Stable, public-safe FX refresh error."""

    def __init__(self, code: str, *, context: Mapping[str, Any] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.context = dict(context or {})


@dataclass(frozen=True)
class RefreshFxProviderRatesCommand:
    provider_key: str | None = None
    base_currency: str | None = None
    quote_currency: str | None = None
    idempotency_key: str | None = None
    trigger_type: FxRefreshTrigger = "admin"
    requested_by_admin_id: UUID | None = None
    change_reason: str | None = None
    requested_at: datetime | None = None


@dataclass(frozen=True)
class RefreshFxProviderRatesResult:
    runs: list[FxProviderRefreshRunModel]
    created_snapshots: list[FxRateSnapshotModel]


@dataclass(frozen=True)
class _RatePayload:
    base_currency: str
    quote_currency: str
    rate: Decimal
    inverse_rate: Decimal
    source_type: str
    provider_rate_id: str | None
    observed_at: datetime
    fetched_at: datetime
    valid_until: datetime
    raw_payload: dict[str, Any]


class RefreshFxProviderRatesUseCase:
    """Create immutable provider FX snapshots from enabled provider configs.

    The provider adapter is intentionally repository-controlled: each provider
    config can expose rates in metadata (`provider_rates`, `rate_snapshots`, or
    `rates`) or directly on supported pairs. If no rate payload is configured,
    the run is persisted as failed instead of fabricating external provider data.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def execute(self, command: RefreshFxProviderRatesCommand) -> RefreshFxProviderRatesResult:
        now = _normalize_utc(command.requested_at or datetime.now(UTC))
        configs = await self._enabled_configs(command.provider_key)
        if not configs:
            raise FxRefreshError(
                "FX_PROVIDER_CONFIG_NOT_FOUND",
                context={"provider_key": command.provider_key},
            )

        runs: list[FxProviderRefreshRunModel] = []
        snapshots: list[FxRateSnapshotModel] = []
        for config in configs:
            run_key = _run_key(config.provider_key, command, now)
            existing = await self._existing_run(run_key)
            if existing is not None:
                runs.append(existing)
                continue
            try:
                async with self._db.begin_nested():
                    run, created = await self._refresh_config(config=config, command=command, now=now, run_key=run_key)
            except IntegrityError:
                existing = await self._existing_run(run_key)
                if existing is None:
                    raise
                runs.append(existing)
                continue
            runs.append(run)
            snapshots.extend(created)
        await self._db.flush()
        return RefreshFxProviderRatesResult(runs=runs, created_snapshots=snapshots)

    async def _enabled_configs(self, provider_key: str | None) -> list[FxProviderConfigModel]:
        statement = select(FxProviderConfigModel).where(FxProviderConfigModel.enabled.is_(True))
        if provider_key:
            statement = statement.where(FxProviderConfigModel.provider_key == provider_key.strip())
        statement = statement.order_by(FxProviderConfigModel.priority.asc(), FxProviderConfigModel.provider_key.asc())
        result = await self._db.execute(statement)
        return list(result.scalars().all())

    async def _existing_run(self, run_key: str) -> FxProviderRefreshRunModel | None:
        result = await self._db.execute(
            select(FxProviderRefreshRunModel).where(FxProviderRefreshRunModel.run_key == run_key)
        )
        return result.scalar_one_or_none()

    async def _refresh_config(
        self,
        *,
        config: FxProviderConfigModel,
        command: RefreshFxProviderRatesCommand,
        now: datetime,
        run_key: str,
    ) -> tuple[FxProviderRefreshRunModel, list[FxRateSnapshotModel]]:
        requested_pairs = _requested_pairs(config, command)
        run = FxProviderRefreshRunModel(
            provider_config_id=config.id,
            provider_key=config.provider_key,
            run_key=run_key,
            status="running",
            trigger_type=command.trigger_type,
            requested_by_admin_id=command.requested_by_admin_id,
            started_at=now,
            pairs_requested=[_pair_public_payload(pair) for pair in requested_pairs],
            pairs_succeeded=[],
            pairs_failed=[],
            created_snapshot_ids=[],
            metadata_={
                "change_reason": _safe_change_reason(command.change_reason),
                "source": "growth_v62_fx_refresh",
            },
        )
        self._db.add(run)
        await self._db.flush()

        succeeded: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []
        snapshots: list[FxRateSnapshotModel] = []
        for pair in requested_pairs:
            try:
                rate_payload = _rate_payload_from_config(config, pair, now)
            except FxRefreshError as exc:
                failed.append({**_pair_public_payload(pair), "reason": exc.code})
                continue
            existing_snapshot = await self._existing_snapshot(config=config, payload=rate_payload)
            if existing_snapshot is not None:
                succeeded.append(
                    {
                        **_pair_public_payload(pair),
                        "duplicate": True,
                        "snapshot_id": str(existing_snapshot.id),
                    }
                )
                continue
            snapshot = _snapshot_from_payload(
                config=config,
                run=run,
                payload=rate_payload,
                requested_by_admin_id=command.requested_by_admin_id,
                change_reason=command.change_reason,
                now=now,
            )
            self._db.add(snapshot)
            snapshots.append(snapshot)
            succeeded.append(_pair_public_payload(pair))

        await self._db.flush()
        run.pairs_succeeded = succeeded
        run.pairs_failed = failed
        run.created_snapshot_ids = [str(snapshot.id) for snapshot in snapshots]
        run.provider_payload_hash = _sha256_json(
            {
                "provider_key": config.provider_key,
                "pairs_succeeded": succeeded,
                "pairs_failed": failed,
                "snapshot_ids": run.created_snapshot_ids,
            }
        )
        run.finished_at = now
        if succeeded and failed:
            run.status = "partial"
        elif succeeded:
            run.status = "succeeded"
        else:
            run.status = "failed"
            run.error_code = "FX_PROVIDER_RATE_UNAVAILABLE"
            run.error_message = "No configured provider rate payload matched the requested pairs."
        return run, snapshots

    async def _existing_snapshot(
        self,
        *,
        config: FxProviderConfigModel,
        payload: _RatePayload,
    ) -> FxRateSnapshotModel | None:
        result = await self._db.execute(
            select(FxRateSnapshotModel).where(
                FxRateSnapshotModel.base_currency == payload.base_currency,
                FxRateSnapshotModel.quote_currency == payload.quote_currency,
                FxRateSnapshotModel.source_type == payload.source_type,
                FxRateSnapshotModel.provider_key == config.provider_key,
                FxRateSnapshotModel.observed_at == payload.observed_at,
            )
        )
        return result.scalar_one_or_none()


def _requested_pairs(
    config: FxProviderConfigModel,
    command: RefreshFxProviderRatesCommand,
) -> list[dict[str, Any]]:
    metadata = _metadata(config)
    configured_pairs = _list_of_mappings(config.supported_pairs) or _metadata_rate_payloads(metadata)
    pairs: list[dict[str, Any]] = []
    for item in configured_pairs:
        try:
            base_currency = _currency(_first(item, "source_currency", "base_currency", "source", "base"))
            quote_currency = _currency(_first(item, "target_currency", "quote_currency", "target", "quote"))
        except FxRefreshError:
            continue
        if command.base_currency and base_currency != _currency(command.base_currency):
            continue
        if command.quote_currency and quote_currency != _currency(command.quote_currency):
            continue
        pair = dict(item)
        pair["base_currency"] = base_currency
        pair["quote_currency"] = quote_currency
        pairs.append(pair)
    return _dedupe_pairs(pairs)


def _rate_payload_from_config(
    config: FxProviderConfigModel,
    pair: Mapping[str, Any],
    now: datetime,
) -> _RatePayload:
    metadata = _metadata(config)
    payload = _matching_rate_payload(metadata, pair) or (dict(pair) if pair.get("rate") is not None else None)
    if payload is None:
        raise FxRefreshError("FX_PROVIDER_RATE_NOT_CONFIGURED")
    base_currency = _currency(
        _first(payload, "source_currency", "base_currency", "source", "base") or pair["base_currency"]
    )
    quote_currency = _currency(
        _first(payload, "target_currency", "quote_currency", "target", "quote") or pair["quote_currency"]
    )
    rate = _positive_decimal(_first(payload, "rate", "provider_rate", "value"))
    observed_at = _datetime_or_now(_first(payload, "observed_at", "fetched_at"), now)
    fetched_at = _datetime_or_now(payload.get("fetched_at"), now)
    ttl_seconds = _positive_int(payload.get("rate_ttl_seconds") or config.rate_ttl_seconds, default=3600)
    valid_until = _datetime_or_none(_first(payload, "valid_until", "expires_at")) or fetched_at + timedelta(
        seconds=ttl_seconds
    )
    source_type = str(payload.get("source_type") or "provider").strip().lower() or "provider"
    return _RatePayload(
        base_currency=base_currency,
        quote_currency=quote_currency,
        rate=rate,
        inverse_rate=Decimal("1") / rate,
        source_type=source_type,
        provider_rate_id=_string_or_none(payload.get("provider_rate_id") or payload.get("id")),
        observed_at=observed_at,
        fetched_at=fetched_at,
        valid_until=valid_until,
        raw_payload=_json_safe_payload(payload),
    )


def _snapshot_from_payload(
    *,
    config: FxProviderConfigModel,
    run: FxProviderRefreshRunModel,
    payload: _RatePayload,
    requested_by_admin_id: UUID | None,
    change_reason: str | None,
    now: datetime,
) -> FxRateSnapshotModel:
    approval_required = bool(config.requires_admin_approval)
    status = "pending_approval" if approval_required else "active"
    approval_state = "pending" if approval_required else "approved"
    checksum_payload = {
        "base_currency": payload.base_currency,
        "quote_currency": payload.quote_currency,
        "rate": payload.rate,
        "inverse_rate": payload.inverse_rate,
        "source_type": payload.source_type,
        "provider_key": config.provider_key,
        "provider_rate_id": payload.provider_rate_id,
        "observed_at": payload.observed_at,
        "fetched_at": payload.fetched_at,
        "valid_until": payload.valid_until,
        "status": status,
    }
    return FxRateSnapshotModel(
        provider_config_id=config.id,
        base_currency=payload.base_currency,
        quote_currency=payload.quote_currency,
        rate=payload.rate,
        inverse_rate=payload.inverse_rate,
        source_type=payload.source_type,
        provider_key=config.provider_key,
        provider_priority=config.priority,
        provider_rate_id=payload.provider_rate_id,
        observed_at=payload.observed_at,
        fetched_at=payload.fetched_at,
        valid_until=payload.valid_until,
        status=status,
        approval_state=approval_state,
        approved_by_admin_id=None,
        approved_at=now if approval_state == "approved" else None,
        checksum=_sha256_json(checksum_payload),
        raw_provider_payload_hash=_sha256_json(payload.raw_payload),
        metadata_={
            "provider_priority": config.priority,
            "fx_refresh_run_id": str(run.id),
            "requested_by_admin_user_id": str(requested_by_admin_id) if requested_by_admin_id else None,
            "change_reason": _safe_change_reason(change_reason),
            "auto_approved": approval_state == "approved",
            "source": "growth_v62_fx_refresh",
        },
    )


def _matching_rate_payload(metadata: Mapping[str, Any], pair: Mapping[str, Any]) -> Mapping[str, Any] | None:
    base_currency = str(pair["base_currency"])
    quote_currency = str(pair["quote_currency"])
    for payload in _metadata_rate_payloads(metadata):
        try:
            payload_base = _currency(_first(payload, "source_currency", "base_currency", "source", "base"))
            payload_quote = _currency(_first(payload, "target_currency", "quote_currency", "target", "quote"))
        except FxRefreshError:
            continue
        if payload_base == base_currency and payload_quote == quote_currency:
            return payload
    return None


def _metadata_rate_payloads(metadata: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    for key in ("provider_rates", "rate_snapshots", "rates"):
        items = _list_of_mappings(metadata.get(key))
        if items:
            return items
    return []


def _metadata(config: FxProviderConfigModel) -> dict[str, Any]:
    return dict(config.metadata_ or {})


def _list_of_mappings(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _dedupe_pairs(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, Any]] = []
    for pair in pairs:
        key = (str(pair["base_currency"]), str(pair["quote_currency"]))
        if key in seen:
            continue
        seen.add(key)
        result.append(pair)
    return result


def _run_key(provider_key: str, command: RefreshFxProviderRatesCommand, now: datetime) -> str:
    if command.idempotency_key:
        key_material = command.idempotency_key.strip()
    else:
        implicit_window = now.replace(second=0, microsecond=0).isoformat()
        key_material = f"implicit:{implicit_window}"
    scope = {
        "provider_key": provider_key,
        "base_currency": _optional_currency(command.base_currency),
        "quote_currency": _optional_currency(command.quote_currency),
        "trigger_type": command.trigger_type,
        "requested_by_admin_id": str(command.requested_by_admin_id) if command.requested_by_admin_id else None,
        "idempotency_key": key_material,
        "requested_at": None,
    }
    return f"fx-refresh:{provider_key}:{_sha256_json(scope)[:32]}"


def _safe_change_reason(value: str | None) -> str | None:
    if value is None:
        return None
    sanitized = value.strip()
    for pattern in _CHANGE_REASON_SECRET_PATTERNS:
        sanitized = pattern.sub(_REDACTED_REASON_VALUE, sanitized)
    return sanitized[:2000]


def _pair_public_payload(pair: Mapping[str, Any]) -> dict[str, str]:
    return {
        "base_currency": str(pair["base_currency"]),
        "quote_currency": str(pair["quote_currency"]),
    }


def _first(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return None


def _currency(value: Any) -> str:
    if not isinstance(value, str):
        raise FxRefreshError("FX_CURRENCY_INVALID")
    normalized = value.strip().upper()
    if len(normalized) < 3 or len(normalized) > 12:
        raise FxRefreshError("FX_CURRENCY_INVALID")
    return normalized


def _optional_currency(value: str | None) -> str | None:
    return _currency(value) if value else None


def _positive_decimal(value: Any) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise FxRefreshError("FX_PROVIDER_RATE_INVALID") from exc
    if parsed <= 0:
        raise FxRefreshError("FX_PROVIDER_RATE_INVALID")
    return parsed


def _positive_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _datetime_or_now(value: Any, now: datetime) -> datetime:
    return _datetime_or_none(value) or now


def _datetime_or_none(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return _normalize_utc(value)
    if value in (None, ""):
        return None
    try:
        return _normalize_utc(datetime.fromisoformat(str(value).replace("Z", "+00:00")))
    except ValueError as exc:
        raise FxRefreshError("FX_PROVIDER_TIMESTAMP_INVALID") from exc


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _string_or_none(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _json_safe_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): _json_safe(value) for key, value in payload.items()}


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return _normalize_utc(value).isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_json_safe(item) for item in value]
    return value


def _sha256_json(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        {str(key): _json_safe(value) for key, value in sorted(payload.items())},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
