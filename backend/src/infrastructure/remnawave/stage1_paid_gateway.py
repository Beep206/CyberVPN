"""Remnawave gateway for Stage 1 paid provisioning."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.application.use_cases.subscriptions.stage1_paid_provisioning import (
    Stage1PaidProvisioningError,
    Stage1PaidProvisioningRequest,
    Stage1PaidProvisioningResult,
)
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.remnawave.smart_ru_bundle import (
    SmartRuConfigurationError,
    resolve_smart_ru_external_squad_uuid,
    resolve_smart_ru_internal_squad_uuids,
)
from src.infrastructure.remnawave.stage1_ru_bundle import resolve_stage1_ru_bundle_external_squad_uuid
from src.infrastructure.remnawave.subscription_urls import normalize_public_subscription_url
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway


class RemnawaveStage1PaidProvisioningGateway:
    """Create or update Remnawave users for S1 paid access."""

    def __init__(self, user_gateway: RemnawaveUserGateway) -> None:
        self._user_gateway = user_gateway

    async def provision_paid_access(
        self,
        request: Stage1PaidProvisioningRequest,
    ) -> Stage1PaidProvisioningResult:
        payload: dict[str, Any] = {
            "email": request.email,
            "telegram_id": request.telegram_id,
            "expire_at": request.access_expires_at,
            "traffic_limit_bytes": request.traffic_limit_bytes,
            "trafficLimitStrategy": request.traffic_limit_strategy,
            "hwid_device_limit": request.device_limit,
        }
        try:
            smart_ru_external_squad_uuid = resolve_smart_ru_external_squad_uuid(request.plan_code)
            smart_ru_internal_squad_uuids = resolve_smart_ru_internal_squad_uuids(request.plan_code)
        except SmartRuConfigurationError as exc:
            raise Stage1PaidProvisioningError(str(exc)) from exc
        external_squad_uuid = smart_ru_external_squad_uuid or resolve_stage1_ru_bundle_external_squad_uuid(
            request.plan_code
        )
        if external_squad_uuid:
            payload["external_squad_uuid"] = external_squad_uuid
        if smart_ru_internal_squad_uuids:
            payload["active_internal_squads"] = smart_ru_internal_squad_uuids
        payload = {key: value for key, value in payload.items() if value is not None or key == "traffic_limit_bytes"}

        if request.existing_remnawave_user_id is not None or request.existing_remnawave_uuid:
            try:
                legacy_uuid = UUID(request.existing_remnawave_uuid) if request.existing_remnawave_uuid else None
                if request.existing_remnawave_user_id is None:
                    raise Stage1PaidProvisioningError("Existing Remnawave numeric identity is not reconciled")
                existing_target = RemnawaveUserRef(
                    id=request.existing_remnawave_user_id,
                    legacy_uuid=legacy_uuid,
                )
                user = await self._user_gateway.update(existing_target, **payload)
            except ValueError as exc:
                raise Stage1PaidProvisioningError("Existing Remnawave identity is invalid") from exc
            created = False
        else:
            # A deterministic username cannot authorize a target-3.x rebind.
            # Duplicate or ambiguous creates fail closed for reconciliation.
            user = await self._user_gateway.create(
                username=request.remnawave_username,
                **payload,
            )
            created = True

        return Stage1PaidProvisioningResult(
            customer_account_id=request.customer_account_id,
            order_id=request.order_id,
            remnawave_uuid=str(user.uuid) if user.uuid is not None else request.existing_remnawave_uuid,
            profile_id=request.profile_id,
            status=user.status.value.lower() if hasattr(user.status, "value") else str(user.status).lower(),
            expires_at=user.expires_at or request.access_expires_at,
            subscription_url=normalize_public_subscription_url(user.subscription_url),
            created=created,
            remnawave_user_id=getattr(user, "remnawave_id", None),
        )
