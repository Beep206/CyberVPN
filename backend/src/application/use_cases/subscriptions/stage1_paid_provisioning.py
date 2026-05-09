"""Stage 1 paid provisioning contract for Remnawave-backed VPN access."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from src.presentation.api.shared.stage1_vpn_protocols import (
    STAGE1_DEFAULT_VPN_PROFILE_ID,
    get_stage1_vpn_profile,
)

STAGE1_PAID_ORDER_STATUS = "committed"
STAGE1_PAID_SETTLEMENT_STATUS = "paid"
STAGE1_PAID_TRAFFIC_LIMIT_STRATEGY = "NO_RESET"


class Stage1PaidProvisioningError(RuntimeError):
    """Raised when S1 paid VPN access cannot be provisioned."""


@dataclass(frozen=True, slots=True)
class Stage1PaidProvisioningRequest:
    """Provider-neutral request for S1 paid VPN access."""

    customer_account_id: UUID
    order_id: UUID
    email: str
    username: str | None
    telegram_id: int | None
    plan_duration_days: int
    paid_at: datetime
    access_starts_at: datetime
    access_expires_at: datetime
    traffic_limit_bytes: int | None
    device_limit: int
    profile_id: str = STAGE1_DEFAULT_VPN_PROFILE_ID
    existing_remnawave_uuid: str | None = None
    source_provider: str | None = None
    source_payment_id: str | None = None
    traffic_limit_strategy: str = STAGE1_PAID_TRAFFIC_LIMIT_STRATEGY

    @property
    def remnawave_username(self) -> str:
        """Return a deterministic non-PII username for Remnawave."""

        return f"cvpn_paid_{self.customer_account_id.hex}"


@dataclass(frozen=True, slots=True)
class Stage1PaidProvisioningResult:
    """Safe result of S1 paid VPN provisioning."""

    customer_account_id: UUID
    order_id: UUID
    remnawave_uuid: str
    profile_id: str
    status: str
    expires_at: datetime
    subscription_url: str | None = None
    created: bool = False
    provider_name: str = "remnawave"

    def to_safe_dict(self) -> dict[str, str | bool]:
        """Serialize metadata without leaking config links or provider secrets."""

        return {
            "customer_account_id": str(self.customer_account_id),
            "order_id": str(self.order_id),
            "remnawave_uuid": self.remnawave_uuid,
            "profile_id": self.profile_id,
            "status": self.status,
            "expires_at": self.expires_at.isoformat(),
            "created": self.created,
            "provider_name": self.provider_name,
        }


class Stage1PaidProvisioningGateway(Protocol):
    """Gateway implemented by Remnawave adapters or tests."""

    async def provision_paid_access(
        self,
        request: Stage1PaidProvisioningRequest,
    ) -> Stage1PaidProvisioningResult:
        """Create or update upstream VPN access for a paid order."""


def build_stage1_paid_provisioning_request(
    *,
    customer_account_id: UUID,
    order_id: UUID,
    email: str,
    username: str | None,
    telegram_id: int | None,
    order_status: str,
    settlement_status: str,
    plan_duration_days: int,
    paid_at: datetime,
    current_access_expires_at: datetime | None = None,
    provisioning_requested_at: datetime | None = None,
    traffic_limit_bytes: int | None,
    device_limit: int,
    existing_remnawave_uuid: str | None = None,
    source_provider: str | None = None,
    source_payment_id: str | None = None,
    profile_id: str = STAGE1_DEFAULT_VPN_PROFILE_ID,
) -> Stage1PaidProvisioningRequest:
    """Build and validate the S1 paid provisioning request."""

    if _normalize_status(order_status) != STAGE1_PAID_ORDER_STATUS:
        raise Stage1PaidProvisioningError("Paid provisioning requires a committed order")
    if _normalize_status(settlement_status) != STAGE1_PAID_SETTLEMENT_STATUS:
        raise Stage1PaidProvisioningError("Paid provisioning requires final paid settlement")
    if plan_duration_days <= 0:
        raise Stage1PaidProvisioningError("Paid provisioning requires a positive plan duration")
    if device_limit <= 0:
        raise Stage1PaidProvisioningError("Paid provisioning requires a positive device limit")
    if traffic_limit_bytes is not None and traffic_limit_bytes <= 0:
        raise Stage1PaidProvisioningError("Paid provisioning traffic limit must be positive or unlimited")

    profile = get_stage1_vpn_profile(profile_id)
    if not profile.enabled or not profile.required_for_s1:
        raise Stage1PaidProvisioningError("Paid provisioning profile is not enabled for S1")

    requested_at = _ensure_aware_utc(provisioning_requested_at or datetime.now(UTC))
    paid_at_utc = _ensure_aware_utc(paid_at)
    current_expires_at = _ensure_aware_utc(current_access_expires_at) if current_access_expires_at else None
    access_starts_at = current_expires_at if current_expires_at and current_expires_at > requested_at else requested_at
    access_expires_at = access_starts_at + timedelta(days=plan_duration_days)

    return Stage1PaidProvisioningRequest(
        customer_account_id=customer_account_id,
        order_id=order_id,
        email=email,
        username=username,
        telegram_id=telegram_id,
        plan_duration_days=plan_duration_days,
        paid_at=paid_at_utc,
        access_starts_at=access_starts_at,
        access_expires_at=access_expires_at,
        traffic_limit_bytes=traffic_limit_bytes,
        device_limit=device_limit,
        profile_id=profile.profile_id,
        existing_remnawave_uuid=existing_remnawave_uuid,
        source_provider=source_provider,
        source_payment_id=source_payment_id,
    )


class Stage1PaidProvisioningService:
    """Coordinates paid VPN access creation or extension through an injected gateway."""

    def __init__(self, gateway: Stage1PaidProvisioningGateway) -> None:
        self._gateway = gateway

    async def provision(
        self,
        *,
        customer_account_id: UUID,
        order_id: UUID,
        email: str,
        username: str | None,
        telegram_id: int | None,
        order_status: str,
        settlement_status: str,
        plan_duration_days: int,
        paid_at: datetime,
        current_access_expires_at: datetime | None = None,
        provisioning_requested_at: datetime | None = None,
        traffic_limit_bytes: int | None,
        device_limit: int,
        existing_remnawave_uuid: str | None = None,
        source_provider: str | None = None,
        source_payment_id: str | None = None,
        profile_id: str = STAGE1_DEFAULT_VPN_PROFILE_ID,
    ) -> Stage1PaidProvisioningResult:
        request = build_stage1_paid_provisioning_request(
            customer_account_id=customer_account_id,
            order_id=order_id,
            email=email,
            username=username,
            telegram_id=telegram_id,
            order_status=order_status,
            settlement_status=settlement_status,
            plan_duration_days=plan_duration_days,
            paid_at=paid_at,
            current_access_expires_at=current_access_expires_at,
            provisioning_requested_at=provisioning_requested_at,
            traffic_limit_bytes=traffic_limit_bytes,
            device_limit=device_limit,
            existing_remnawave_uuid=existing_remnawave_uuid,
            source_provider=source_provider,
            source_payment_id=source_payment_id,
            profile_id=profile_id,
        )
        result = await self._gateway.provision_paid_access(request)
        if result.profile_id != request.profile_id:
            raise Stage1PaidProvisioningError("Provisioning gateway returned an unexpected S1 profile")
        expires_delta_seconds = abs((result.expires_at - request.access_expires_at).total_seconds())
        if expires_delta_seconds > 1:
            raise Stage1PaidProvisioningError("Provisioning gateway returned an unexpected paid expiry")
        if not result.remnawave_uuid:
            raise Stage1PaidProvisioningError("Provisioning gateway returned no Remnawave user UUID")
        return result


def _normalize_status(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def _ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
