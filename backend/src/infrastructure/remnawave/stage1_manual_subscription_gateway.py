"""Remnawave gateway for Stage 1 manual subscription grants/extensions."""

from __future__ import annotations

from uuid import UUID

from src.application.use_cases.subscriptions.stage1_manual_subscription import (
    Stage1ManualSubscriptionError,
    Stage1ManualSubscriptionRequest,
    Stage1ManualSubscriptionResult,
)
from src.domain.enums import UserStatus
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway


class RemnawaveStage1ManualSubscriptionGateway:
    """Create or update Remnawave users for S1 manual admin operations."""

    def __init__(self, user_gateway: RemnawaveUserGateway) -> None:
        self._user_gateway = user_gateway

    async def apply_manual_subscription(
        self,
        request: Stage1ManualSubscriptionRequest,
    ) -> Stage1ManualSubscriptionResult:
        payload = {
            "email": request.email,
            "telegram_id": request.telegram_id,
            "expire_at": request.access_expires_at,
            "traffic_limit_bytes": request.traffic_limit_bytes,
            "trafficLimitStrategy": request.traffic_limit_strategy,
            "hwid_device_limit": request.device_limit,
            "status": UserStatus.ACTIVE,
        }
        payload = {key: value for key, value in payload.items() if value is not None or key == "traffic_limit_bytes"}

        if request.existing_remnawave_uuid:
            try:
                user = await self._user_gateway.update(UUID(request.existing_remnawave_uuid), **payload)
            except ValueError as exc:
                raise Stage1ManualSubscriptionError("Existing Remnawave UUID is invalid") from exc
            created = False
        else:
            user = await self._user_gateway.create(
                username=request.remnawave_username,
                **payload,
            )
            created = True

        subscription_url_changed = bool(
            user.subscription_url and user.subscription_url != request.previous_subscription_url
        )
        return Stage1ManualSubscriptionResult(
            customer_account_id=request.customer_account_id,
            remnawave_uuid=str(user.uuid),
            profile_id=request.profile_id,
            status=user.status.value.lower() if hasattr(user.status, "value") else str(user.status).lower(),
            operation=request.operation,
            duration_days=request.duration_days,
            previous_expires_at=request.current_access_expires_at,
            expires_at=user.expires_at or request.access_expires_at,
            subscription_url=user.subscription_url,
            subscription_url_changed=subscription_url_changed,
            created=created,
        )
