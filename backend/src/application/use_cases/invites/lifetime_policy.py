"""Invite entitlement duration and expiry helpers for v7+ campaigns."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

INVITE_DURATION_FIXED_DAYS = "fixed_days"
INVITE_DURATION_LIFETIME = "lifetime"
INVITE_DURATION_MODES = {INVITE_DURATION_FIXED_DAYS, INVITE_DURATION_LIFETIME}

INVITE_EXPIRY_RELATIVE = "relative"
INVITE_EXPIRY_ABSOLUTE = "absolute"
INVITE_EXPIRY_NONE = "none"
INVITE_EXPIRY_CAMPAIGN_DEFAULT = "campaign_default"
INVITE_EXPIRY_MODES = {INVITE_EXPIRY_RELATIVE, INVITE_EXPIRY_ABSOLUTE, INVITE_EXPIRY_NONE}


@dataclass(frozen=True, slots=True)
class InviteGrantResolution:
    snapshot: dict[str, Any]
    expires_at: datetime | None
    display_days: int
    duration_mode: str
    device_limit_override: int | None


@dataclass(frozen=True, slots=True)
class InviteExpiryResolution:
    expiry_mode: str
    expiry_days: int | None
    expires_at: datetime | None


def normalize_invite_duration_mode(value: str | None) -> str:
    mode = str(value or INVITE_DURATION_FIXED_DAYS).strip().lower()
    if mode not in INVITE_DURATION_MODES:
        raise ValueError("Unsupported invite duration mode")
    return mode


def normalize_invite_expiry_mode(value: str | None) -> str:
    mode = str(value or INVITE_EXPIRY_RELATIVE).strip().lower()
    if mode not in INVITE_EXPIRY_MODES:
        raise ValueError("Unsupported invite expiry mode")
    return mode


def is_lifetime_duration(value: str | None) -> bool:
    return normalize_invite_duration_mode(value) == INVITE_DURATION_LIFETIME


def positive_int_or_none(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = int(value)
        except ValueError:
            return None
    else:
        return None
    return parsed if parsed > 0 else None


def display_days_for_duration(duration_mode: str | None, duration_days: object) -> int:
    if is_lifetime_duration(duration_mode):
        return 0
    return positive_int_or_none(duration_days) or 1


def resolve_invite_grant(
    *,
    snapshot: dict[str, Any],
    duration_mode: str | None,
    duration_days: object,
    granted_at: datetime,
    device_limit_override: object | None = None,
) -> InviteGrantResolution:
    mode = normalize_invite_duration_mode(duration_mode)
    display_days = display_days_for_duration(mode, duration_days)
    expires_at = None if mode == INVITE_DURATION_LIFETIME else _coerce_utc(granted_at) + timedelta(days=display_days)
    override = positive_int_or_none(device_limit_override)
    return InviteGrantResolution(
        snapshot=apply_invite_entitlement_overrides(
            snapshot=snapshot,
            duration_mode=mode,
            duration_days=None if mode == INVITE_DURATION_LIFETIME else display_days,
            expires_at=expires_at,
            device_limit_override=override,
        ),
        expires_at=expires_at,
        display_days=display_days,
        duration_mode=mode,
        device_limit_override=override,
    )


def apply_invite_entitlement_overrides(
    *,
    snapshot: dict[str, Any],
    duration_mode: str | None,
    duration_days: int | None,
    expires_at: datetime | None,
    device_limit_override: int | None,
) -> dict[str, Any]:
    """Return a detached entitlement snapshot with invite-specific overrides."""

    mode = normalize_invite_duration_mode(duration_mode)
    copied = deepcopy(dict(snapshot or {}))
    effective = dict(copied.get("effective_entitlements") or {})
    invite_bundle = dict(copied.get("invite_bundle") or {})

    copied["status"] = "active"
    copied["duration_mode"] = mode
    copied["lifetime"] = mode == INVITE_DURATION_LIFETIME
    copied["period_days"] = None if mode == INVITE_DURATION_LIFETIME else duration_days
    copied["expires_at"] = _iso_or_none(expires_at)
    copied["device_limit_override"] = device_limit_override

    if device_limit_override is not None:
        effective["device_limit"] = int(device_limit_override)
        effective["device_limit_override"] = int(device_limit_override)
    else:
        effective.pop("device_limit_override", None)

    invite_bundle["grant_duration_mode"] = mode
    invite_bundle["grant_duration_days"] = None if mode == INVITE_DURATION_LIFETIME else duration_days
    invite_bundle["grant_device_limit_override"] = device_limit_override
    copied["effective_entitlements"] = effective
    copied["invite_bundle"] = invite_bundle
    return copied


def resolve_invite_expiry(
    *,
    expiry_mode: str | None,
    expiry_days: object,
    expires_at: datetime | None,
    now: datetime,
) -> InviteExpiryResolution:
    mode = normalize_invite_expiry_mode(expiry_mode)
    if mode == INVITE_EXPIRY_NONE:
        return InviteExpiryResolution(expiry_mode=mode, expiry_days=None, expires_at=None)
    if mode == INVITE_EXPIRY_ABSOLUTE:
        if expires_at is None:
            raise ValueError("expires_at is required for absolute invite expiry")
        absolute = _coerce_utc(expires_at)
        return InviteExpiryResolution(expiry_mode=mode, expiry_days=None, expires_at=absolute)
    relative_days = positive_int_or_none(expiry_days)
    if relative_days is None:
        raise ValueError("expiry_days is required for relative invite expiry")
    return InviteExpiryResolution(
        expiry_mode=INVITE_EXPIRY_RELATIVE,
        expiry_days=relative_days,
        expires_at=_coerce_utc(now) + timedelta(days=relative_days),
    )


def remnawave_lifetime_payload(
    *,
    mode: str,
    sentinel_expire_at: str | None,
) -> dict[str, Any]:
    normalized_mode = str(mode or "sentinel").strip().lower()
    if normalized_mode == "none":
        return {
            "allow_missing_expire_at": True,
            "lifetime_expiry_mode": "none",
            "upstream_expiry_mode": "none",
            "upstream_expires_at": None,
        }
    sentinel = (sentinel_expire_at or "").strip() or "2099-12-31T23:59:59Z"
    return {
        "expire_at": sentinel,
        "lifetime_expiry_mode": "sentinel",
        "lifetime_expire_at": sentinel,
        "upstream_expiry_mode": "sentinel",
        "upstream_expires_at": sentinel,
    }


def _iso_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _coerce_utc(value).isoformat().replace("+00:00", "Z")


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
