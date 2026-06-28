"""Remnawave gateway for Stage 1 manual subscription grants/extensions."""

from __future__ import annotations

from uuid import UUID

from src.application.use_cases.subscriptions.stage1_manual_subscription import (
    Stage1ManualSubscriptionError,
    Stage1ManualSubscriptionRequest,
    Stage1ManualSubscriptionResult,
)
from src.domain.enums import UserStatus
from src.infrastructure.remnawave.smart_ru_bundle import (
    SmartRuConfigurationError,
    resolve_smart_ru_external_squad_uuid,
    resolve_smart_ru_internal_squad_uuids,
)
from src.infrastructure.remnawave.stage1_ru_bundle import resolve_stage1_ru_bundle_external_squad_uuid
from src.infrastructure.remnawave.subscription_urls import normalize_public_subscription_url
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
        try:
            smart_ru_external_squad_uuid = resolve_smart_ru_external_squad_uuid(request.plan_code)
            smart_ru_internal_squad_uuids = resolve_smart_ru_internal_squad_uuids(request.plan_code)
        except SmartRuConfigurationError as exc:
            raise Stage1ManualSubscriptionError(str(exc)) from exc
        external_squad_uuid = smart_ru_external_squad_uuid or resolve_stage1_ru_bundle_external_squad_uuid(
            request.plan_code
        )
        if external_squad_uuid:
            payload["external_squad_uuid"] = external_squad_uuid
        if smart_ru_internal_squad_uuids:
            payload["active_internal_squads"] = smart_ru_internal_squad_uuids
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

        subscription_url = normalize_public_subscription_url(user.subscription_url)
        subscription_url_changed = bool(subscription_url and subscription_url != request.previous_subscription_url)
        return Stage1ManualSubscriptionResult(
            customer_account_id=request.customer_account_id,
            remnawave_uuid=str(user.uuid),
            profile_id=request.profile_id,
            status=user.status.value.lower() if hasattr(user.status, "value") else str(user.status).lower(),
            operation=request.operation,
            duration_days=request.duration_days,
            previous_expires_at=request.current_access_expires_at,
            expires_at=user.expires_at or request.access_expires_at,
            subscription_url=subscription_url,
            subscription_url_changed=subscription_url_changed,
            created=created,
        )
