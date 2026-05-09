"""Stage 1 manual subscription operations for admin-controlled grants."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol
from uuid import UUID

from src.application.use_cases.auth.permissions import Permission, has_permission
from src.domain.enums import AdminRole
from src.presentation.api.shared.stage1_vpn_protocols import (
    STAGE1_DEFAULT_VPN_PROFILE_ID,
    get_stage1_vpn_profile,
)

STAGE1_MANUAL_SUBSCRIPTION_ACTION = "customer_subscription_manual_granted"
STAGE1_MANUAL_SUBSCRIPTION_TRAFFIC_LIMIT_STRATEGY = "NO_RESET"
STAGE1_MANUAL_SUBSCRIPTION_MAX_DAYS = 365
STAGE1_MANUAL_SUBSCRIPTION_MAX_DEVICE_LIMIT = 10


class Stage1ManualSubscriptionError(RuntimeError):
    """Raised when a manual S1 subscription operation is unsafe or invalid."""


@dataclass(frozen=True, slots=True)
class Stage1ManualSubscriptionRequest:
    """Provider-neutral manual subscription grant/extension request."""

    customer_account_id: UUID
    actor_admin_id: UUID
    email: str
    username: str | None
    telegram_id: int | None
    reason: str
    duration_days: int
    requested_at: datetime
    access_starts_at: datetime
    access_expires_at: datetime
    operation: Literal["grant", "extend"]
    traffic_limit_bytes: int | None
    device_limit: int
    profile_id: str = STAGE1_DEFAULT_VPN_PROFILE_ID
    existing_remnawave_uuid: str | None = None
    current_access_expires_at: datetime | None = None
    previous_subscription_url: str | None = None
    traffic_limit_strategy: str = STAGE1_MANUAL_SUBSCRIPTION_TRAFFIC_LIMIT_STRATEGY

    @property
    def remnawave_username(self) -> str:
        """Return a deterministic non-PII username for manual S1 grants."""

        return f"cvpn_manual_{self.customer_account_id.hex}"


@dataclass(frozen=True, slots=True)
class Stage1ManualSubscriptionResult:
    """Safe result of a manual S1 subscription grant/extension."""

    customer_account_id: UUID
    remnawave_uuid: str
    profile_id: str
    status: str
    operation: Literal["grant", "extend"]
    duration_days: int
    previous_expires_at: datetime | None
    expires_at: datetime
    subscription_url: str | None = None
    subscription_url_changed: bool = False
    created: bool = False
    provider_name: str = "remnawave"

    def to_safe_dict(self) -> dict[str, str | int | bool | None]:
        """Serialize metadata without leaking config links or provider secrets."""

        return {
            "customer_account_id": str(self.customer_account_id),
            "remnawave_uuid": self.remnawave_uuid,
            "profile_id": self.profile_id,
            "status": self.status,
            "operation": self.operation,
            "duration_days": self.duration_days,
            "previous_expires_at": self.previous_expires_at.isoformat()
            if self.previous_expires_at
            else None,
            "expires_at": self.expires_at.isoformat(),
            "subscription_url_changed": self.subscription_url_changed,
            "created": self.created,
            "provider_name": self.provider_name,
        }

    def to_audit_details(self, *, reason: str) -> dict[str, str | int | bool | None]:
        """Return audit metadata with reason length only and no raw config links."""

        return {
            **self.to_safe_dict(),
            "reason_length": len(reason.strip()),
            "audit_action": STAGE1_MANUAL_SUBSCRIPTION_ACTION,
            "config_delivery_required": True,
        }


class Stage1ManualSubscriptionGateway(Protocol):
    """Gateway implemented by Remnawave adapters or tests."""

    async def apply_manual_subscription(
        self,
        request: Stage1ManualSubscriptionRequest,
    ) -> Stage1ManualSubscriptionResult:
        """Create or update upstream VPN access for a manual admin operation."""


def can_apply_stage1_manual_subscription(role: AdminRole) -> bool:
    """Return whether an admin role may manually grant or extend S1 access."""

    return has_permission(role, Permission.SUBSCRIPTION_CREATE)


def build_stage1_manual_subscription_request(
    *,
    customer_account_id: UUID,
    actor_admin_id: UUID,
    email: str,
    username: str | None,
    telegram_id: int | None,
    reason: str,
    duration_days: int,
    requested_at: datetime | None = None,
    current_access_expires_at: datetime | None = None,
    traffic_limit_bytes: int | None = None,
    device_limit: int = 1,
    existing_remnawave_uuid: str | None = None,
    previous_subscription_url: str | None = None,
    profile_id: str = STAGE1_DEFAULT_VPN_PROFILE_ID,
) -> Stage1ManualSubscriptionRequest:
    """Build and validate a manual S1 subscription grant/extension request."""

    reason = reason.strip()
    if len(reason) < 3:
        raise Stage1ManualSubscriptionError("Manual subscription operation requires an operator reason")
    if len(reason) > 1000:
        raise Stage1ManualSubscriptionError("Manual subscription operation reason is too long")
    if duration_days <= 0 or duration_days > STAGE1_MANUAL_SUBSCRIPTION_MAX_DAYS:
        raise Stage1ManualSubscriptionError("Manual subscription duration must be between 1 and 365 days")
    if device_limit <= 0 or device_limit > STAGE1_MANUAL_SUBSCRIPTION_MAX_DEVICE_LIMIT:
        raise Stage1ManualSubscriptionError("Manual subscription device limit must be between 1 and 10")
    if traffic_limit_bytes is not None and traffic_limit_bytes <= 0:
        raise Stage1ManualSubscriptionError("Manual subscription traffic limit must be positive or unlimited")

    profile = get_stage1_vpn_profile(profile_id)
    if not profile.enabled or not profile.required_for_s1:
        raise Stage1ManualSubscriptionError("Manual subscription profile is not enabled for S1")

    requested_at_utc = _ensure_aware_utc(requested_at or datetime.now(UTC))
    current_expires_at = (
        _ensure_aware_utc(current_access_expires_at)
        if current_access_expires_at is not None
        else None
    )
    access_starts_at = (
        current_expires_at
        if current_expires_at is not None and current_expires_at > requested_at_utc
        else requested_at_utc
    )
    operation: Literal["grant", "extend"] = (
        "extend"
        if current_expires_at is not None and current_expires_at > requested_at_utc
        else "grant"
    )

    return Stage1ManualSubscriptionRequest(
        customer_account_id=customer_account_id,
        actor_admin_id=actor_admin_id,
        email=email.strip().lower(),
        username=username,
        telegram_id=telegram_id,
        reason=reason,
        duration_days=duration_days,
        requested_at=requested_at_utc,
        access_starts_at=access_starts_at,
        access_expires_at=access_starts_at + timedelta(days=duration_days),
        operation=operation,
        traffic_limit_bytes=traffic_limit_bytes,
        device_limit=device_limit,
        profile_id=profile.profile_id,
        existing_remnawave_uuid=existing_remnawave_uuid,
        current_access_expires_at=current_expires_at,
        previous_subscription_url=previous_subscription_url,
    )


class Stage1ManualSubscriptionService:
    """Coordinates S1 manual grant/extension through an injected gateway."""

    def __init__(self, gateway: Stage1ManualSubscriptionGateway) -> None:
        self._gateway = gateway

    async def apply(
        self,
        request: Stage1ManualSubscriptionRequest,
    ) -> Stage1ManualSubscriptionResult:
        """Apply the manual subscription operation and validate safe results."""

        result = await self._gateway.apply_manual_subscription(request)
        if result.customer_account_id != request.customer_account_id:
            raise Stage1ManualSubscriptionError("Manual subscription gateway returned an unexpected customer")
        if result.profile_id != request.profile_id:
            raise Stage1ManualSubscriptionError("Manual subscription gateway returned an unexpected S1 profile")
        expires_delta_seconds = abs((result.expires_at - request.access_expires_at).total_seconds())
        if expires_delta_seconds > 1:
            raise Stage1ManualSubscriptionError("Manual subscription gateway returned an unexpected expiry")
        if not result.remnawave_uuid:
            raise Stage1ManualSubscriptionError("Manual subscription gateway returned no Remnawave user UUID")
        return result


def _ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
