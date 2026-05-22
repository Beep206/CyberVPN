"""Remnawave gateway for Stage 1 trial provisioning."""

from __future__ import annotations

from uuid import UUID

from src.application.use_cases.trial.stage1_trial_provisioning import (
    Stage1TrialProvisioningError,
    Stage1TrialProvisioningRequest,
    Stage1TrialProvisioningResult,
)
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway
from src.infrastructure.remnawave.subscription_urls import normalize_public_subscription_url


class RemnawaveStage1TrialProvisioningGateway:
    """Create or update Remnawave users for S1 trial access."""

    def __init__(self, user_gateway: RemnawaveUserGateway) -> None:
        self._user_gateway = user_gateway

    async def provision_trial_access(
        self,
        request: Stage1TrialProvisioningRequest,
    ) -> Stage1TrialProvisioningResult:
        payload = {
            "email": request.email,
            "telegram_id": request.telegram_id,
            "expire_at": request.trial_expires_at,
            "traffic_limit_bytes": request.traffic_limit_bytes,
            "trafficLimitStrategy": request.traffic_limit_strategy,
            "hwid_device_limit": request.device_limit,
        }
        payload = {key: value for key, value in payload.items() if value is not None}

        if request.existing_remnawave_uuid:
            try:
                user = await self._user_gateway.update(UUID(request.existing_remnawave_uuid), **payload)
            except ValueError as exc:
                raise Stage1TrialProvisioningError("Existing Remnawave UUID is invalid") from exc
            created = False
        else:
            user = await self._user_gateway.create(
                username=request.remnawave_username,
                **payload,
            )
            created = True

        return Stage1TrialProvisioningResult(
            customer_account_id=request.customer_account_id,
            remnawave_uuid=str(user.uuid),
            profile_id=request.profile_id,
            status=user.status.value.lower() if hasattr(user.status, "value") else str(user.status).lower(),
            expires_at=user.expires_at or request.trial_expires_at,
            subscription_url=normalize_public_subscription_url(user.subscription_url),
            created=created,
        )
