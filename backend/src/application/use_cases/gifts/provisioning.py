"""Provider-neutral provisioning contract for redeemed gift access."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from src.presentation.api.shared.stage1_vpn_protocols import (
    STAGE1_DEFAULT_VPN_PROFILE_ID,
    get_stage1_vpn_profile,
)

GIFT_TRAFFIC_LIMIT_STRATEGY = "NO_RESET"


class GiftProvisioningError(RuntimeError):
    """A redeemed gift could not be provisioned without weakening identity safety."""


@dataclass(frozen=True, slots=True)
class GiftProvisioningRequest:
    customer_account_id: UUID
    gift_code_id: UUID
    email: str
    username: str | None
    telegram_id: int | None
    plan_code: str | None
    access_expires_at: datetime
    traffic_limit_bytes: int | None
    device_limit: int
    profile_id: str = STAGE1_DEFAULT_VPN_PROFILE_ID
    existing_remnawave_uuid: str | None = None
    existing_remnawave_user_id: int | None = None
    traffic_limit_strategy: str = GIFT_TRAFFIC_LIMIT_STRATEGY

    @property
    def remnawave_username(self) -> str:
        return f"cvpn_g_{self.customer_account_id.hex[:28]}"


@dataclass(frozen=True, slots=True)
class GiftProvisioningResult:
    customer_account_id: UUID
    gift_code_id: UUID
    remnawave_uuid: str | None
    remnawave_user_id: int | None
    profile_id: str
    status: str
    expires_at: datetime
    subscription_url: str | None = None
    created: bool = False
    provider_name: str = "remnawave"

    def require_remnawave_user_id(self) -> int:
        value = self.remnawave_user_id
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise GiftProvisioningError("Gift provisioning gateway returned an incomplete Remnawave identity")
        return value


class GiftProvisioningGateway(Protocol):
    async def provision_gift_access(self, request: GiftProvisioningRequest) -> GiftProvisioningResult:
        """Create or update the exact recipient's Remnawave access."""


def build_gift_provisioning_request(
    *,
    customer_account_id: UUID,
    gift_code_id: UUID,
    email: str,
    username: str | None,
    telegram_id: int | None,
    plan_code: str | None,
    access_expires_at: datetime,
    traffic_limit_bytes: int | None,
    device_limit: int,
    existing_remnawave_uuid: str | None,
    existing_remnawave_user_id: int | None,
    profile_id: str = STAGE1_DEFAULT_VPN_PROFILE_ID,
) -> GiftProvisioningRequest:
    if isinstance(device_limit, bool) or not isinstance(device_limit, int) or device_limit <= 0:
        raise GiftProvisioningError("Gift provisioning requires a positive device limit")
    if traffic_limit_bytes is not None and (
        isinstance(traffic_limit_bytes, bool) or not isinstance(traffic_limit_bytes, int) or traffic_limit_bytes <= 0
    ):
        raise GiftProvisioningError("Gift provisioning traffic limit must be positive or unlimited")
    if existing_remnawave_user_id is not None and (
        isinstance(existing_remnawave_user_id, bool)
        or not isinstance(existing_remnawave_user_id, int)
        or existing_remnawave_user_id <= 0
    ):
        raise GiftProvisioningError("Existing gift recipient numeric identity is invalid")

    profile = get_stage1_vpn_profile(profile_id)
    if not profile.enabled or not profile.required_for_s1:
        raise GiftProvisioningError("Gift provisioning profile is not enabled")

    return GiftProvisioningRequest(
        customer_account_id=customer_account_id,
        gift_code_id=gift_code_id,
        email=email.strip().lower(),
        username=username,
        telegram_id=telegram_id,
        plan_code=plan_code.strip().lower() if plan_code else None,
        access_expires_at=_ensure_aware_utc(access_expires_at),
        traffic_limit_bytes=traffic_limit_bytes,
        device_limit=device_limit,
        profile_id=profile.profile_id,
        existing_remnawave_uuid=existing_remnawave_uuid,
        existing_remnawave_user_id=existing_remnawave_user_id,
    )


class GiftProvisioningService:
    def __init__(self, gateway: GiftProvisioningGateway) -> None:
        self._gateway = gateway

    async def provision(self, request: GiftProvisioningRequest) -> GiftProvisioningResult:
        result = await self._gateway.provision_gift_access(request)
        if result.customer_account_id != request.customer_account_id or result.gift_code_id != request.gift_code_id:
            raise GiftProvisioningError("Gift provisioning gateway returned an unexpected target")
        if result.profile_id != request.profile_id:
            raise GiftProvisioningError("Gift provisioning gateway returned an unexpected profile")
        if result.provider_name != "remnawave" or result.status.strip().lower() != "active":
            raise GiftProvisioningError("Gift provisioning gateway did not return active Remnawave access")
        if abs((_ensure_aware_utc(result.expires_at) - request.access_expires_at).total_seconds()) > 1:
            raise GiftProvisioningError("Gift provisioning gateway returned an unexpected expiry")
        result.require_remnawave_user_id()
        if result.remnawave_uuid is not None:
            try:
                UUID(result.remnawave_uuid)
            except ValueError as exc:
                raise GiftProvisioningError("Gift provisioning gateway returned an invalid rollback reference") from exc
        return result


def _ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
