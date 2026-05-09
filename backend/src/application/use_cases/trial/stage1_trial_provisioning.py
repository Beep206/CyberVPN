"""Stage 1 trial provisioning contract for Remnawave-backed VPN access."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.presentation.api.shared.stage1_vpn_protocols import (
    STAGE1_DEFAULT_VPN_PROFILE_ID,
    get_stage1_vpn_profile,
)

from . import stage1_trial_policy as _trial_policy

STAGE1_TRIAL_DURATION_DAYS = _trial_policy.STAGE1_TRIAL_DURATION_DAYS
STAGE1_TRIAL_TRAFFIC_LIMIT_BYTES = _trial_policy.STAGE1_TRIAL_TRAFFIC_LIMIT_BYTES
STAGE1_TRIAL_DEVICE_LIMIT = _trial_policy.STAGE1_TRIAL_DEVICE_LIMIT
STAGE1_TRIAL_TRAFFIC_LIMIT_STRATEGY = _trial_policy.STAGE1_TRIAL_TRAFFIC_LIMIT_STRATEGY


class Stage1TrialProvisioningError(RuntimeError):
    """Raised when S1 trial VPN access cannot be provisioned."""


@dataclass(frozen=True, slots=True)
class Stage1TrialProvisioningRequest:
    """Provider-neutral request for S1 trial VPN access."""

    customer_account_id: UUID
    email: str
    username: str | None
    telegram_id: int | None
    trial_expires_at: datetime
    profile_id: str = STAGE1_DEFAULT_VPN_PROFILE_ID
    existing_remnawave_uuid: str | None = None
    traffic_limit_bytes: int = STAGE1_TRIAL_TRAFFIC_LIMIT_BYTES
    device_limit: int = STAGE1_TRIAL_DEVICE_LIMIT
    traffic_limit_strategy: str = STAGE1_TRIAL_TRAFFIC_LIMIT_STRATEGY

    @property
    def remnawave_username(self) -> str:
        """Return a deterministic non-PII username for Remnawave."""

        return f"cvpn_trial_{self.customer_account_id.hex}"


@dataclass(frozen=True, slots=True)
class Stage1TrialProvisioningResult:
    """Safe result of S1 trial VPN provisioning."""

    customer_account_id: UUID
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
            "remnawave_uuid": self.remnawave_uuid,
            "profile_id": self.profile_id,
            "status": self.status,
            "expires_at": self.expires_at.isoformat(),
            "created": self.created,
            "provider_name": self.provider_name,
        }


class Stage1TrialProvisioningGateway(Protocol):
    """Gateway implemented by Remnawave adapters or tests."""

    async def provision_trial_access(
        self,
        request: Stage1TrialProvisioningRequest,
    ) -> Stage1TrialProvisioningResult:
        """Create or update upstream VPN access for a trial."""


def build_stage1_trial_provisioning_request(
    *,
    customer_account_id: UUID,
    email: str,
    username: str | None,
    telegram_id: int | None,
    trial_expires_at: datetime,
    existing_remnawave_uuid: str | None = None,
    profile_id: str = STAGE1_DEFAULT_VPN_PROFILE_ID,
) -> Stage1TrialProvisioningRequest:
    """Build and validate the S1 trial provisioning request."""

    profile = get_stage1_vpn_profile(profile_id)
    if not profile.enabled or not profile.required_for_s1:
        raise Stage1TrialProvisioningError("Trial provisioning profile is not enabled for S1")

    return Stage1TrialProvisioningRequest(
        customer_account_id=customer_account_id,
        email=email,
        username=username,
        telegram_id=telegram_id,
        trial_expires_at=trial_expires_at,
        profile_id=profile.profile_id,
        existing_remnawave_uuid=existing_remnawave_uuid,
    )


class Stage1TrialProvisioningService:
    """Coordinates trial VPN access creation through an injected gateway."""

    def __init__(self, gateway: Stage1TrialProvisioningGateway) -> None:
        self._gateway = gateway

    async def provision(
        self,
        *,
        customer_account_id: UUID,
        email: str,
        username: str | None,
        telegram_id: int | None,
        trial_expires_at: datetime,
        existing_remnawave_uuid: str | None = None,
        profile_id: str = STAGE1_DEFAULT_VPN_PROFILE_ID,
    ) -> Stage1TrialProvisioningResult:
        request = build_stage1_trial_provisioning_request(
            customer_account_id=customer_account_id,
            email=email,
            username=username,
            telegram_id=telegram_id,
            trial_expires_at=trial_expires_at,
            existing_remnawave_uuid=existing_remnawave_uuid,
            profile_id=profile_id,
        )
        result = await self._gateway.provision_trial_access(request)
        if result.profile_id != request.profile_id:
            raise Stage1TrialProvisioningError("Provisioning gateway returned an unexpected S1 profile")
        expires_delta_seconds = abs((result.expires_at - request.trial_expires_at).total_seconds())
        if expires_delta_seconds > 1:
            raise Stage1TrialProvisioningError("Provisioning gateway returned an unexpected trial expiry")
        if not result.remnawave_uuid:
            raise Stage1TrialProvisioningError("Provisioning gateway returned no Remnawave user UUID")
        return result
