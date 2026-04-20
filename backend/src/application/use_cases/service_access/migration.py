from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.entitlements_service import EntitlementsService
from src.application.use_cases.service_access.access_delivery_channels import (
    CreateAccessDeliveryChannelUseCase,
    _default_channel_subject_ref,
    _default_provisioning_profile_key,
)
from src.application.use_cases.service_access.provisioning_profiles import (
    CreateProvisioningProfileUseCase,
)
from src.application.use_cases.service_access.service_identities import CreateServiceIdentityUseCase
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.service_access_repo import ServiceAccessRepository

SUBSCRIPTION_URL_PROFILE_KEY = _default_provisioning_profile_key("subscription_url")
SUBSCRIPTION_URL_TARGET_CHANNEL = "subscription_url"
SUBSCRIPTION_URL_DELIVERY_METHOD = "subscription_url"


@dataclass(frozen=True)
class LegacyServiceAccessShadowResult:
    customer_account_id: UUID
    auth_realm_id: UUID
    provider_name: str
    legacy_provider_subject_ref: str | None
    legacy_subscription_url: str | None
    legacy_entitlement_snapshot: dict[str, Any]
    canonical_entitlement_snapshot: dict[str, Any]
    service_identity: Any | None
    provisioning_profile: Any | None
    access_delivery_channel: Any | None
    mismatch_codes: list[str]


@dataclass(frozen=True)
class MigrateLegacyServiceAccessResult:
    service_identity_created: bool
    provisioning_profile_created: bool
    access_delivery_channel_created: bool
    service_identity: Any
    provisioning_profile: Any | None
    access_delivery_channel: Any | None
    shadow_before: LegacyServiceAccessShadowResult
    shadow_after: LegacyServiceAccessShadowResult


class GetLegacyServiceAccessShadowUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ServiceAccessRepository(session)
        self._entitlements = EntitlementsService(session)

    async def execute(
        self,
        *,
        customer_account_id: UUID,
        auth_realm_id: UUID,
        provider_name: str,
    ) -> LegacyServiceAccessShadowResult:
        customer = await self._session.get(MobileUserModel, customer_account_id)
        if customer is None:
            raise ValueError("Customer account not found")
        if customer.auth_realm_id and customer.auth_realm_id != auth_realm_id:
            raise ValueError("Customer account does not belong to auth realm")

        legacy_provider_subject_ref = customer.remnawave_uuid
        legacy_subscription_url = customer.subscription_url
        legacy_entitlement_snapshot = await self._entitlements.get_legacy_snapshot(customer_account_id)
        canonical_entitlement_snapshot = await self._entitlements.get_current_snapshot(
            customer_account_id,
            auth_realm_id=auth_realm_id,
        )

        service_identity = await self._repo.get_service_identity_by_customer_realm_provider(
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            provider_name=provider_name,
        )

        provisioning_profile = None
        access_delivery_channel = None
        if service_identity is not None:
            provisioning_profile = await self._repo.get_provisioning_profile_by_service_identity_and_key(
                service_identity_id=service_identity.id,
                profile_key=SUBSCRIPTION_URL_PROFILE_KEY,
            )
            access_delivery_channel = await self._repo.get_access_delivery_channel_by_service_identity_type_subject(
                service_identity_id=service_identity.id,
                channel_type="subscription_url",
                channel_subject_ref=_default_channel_subject_ref(
                    channel_type="subscription_url",
                    provided_subject_ref=None,
                    credential_subject_key=None,
                    service_identity_key=service_identity.service_key,
                ),
            )

        mismatch_codes: list[str] = []
        if legacy_provider_subject_ref and service_identity is None:
            mismatch_codes.append("missing_canonical_service_identity")
        if service_identity is not None and legacy_provider_subject_ref is None:
            mismatch_codes.append("legacy_provider_subject_missing")
        if (
            service_identity is not None
            and legacy_provider_subject_ref is not None
            and service_identity.provider_subject_ref != legacy_provider_subject_ref
        ):
            mismatch_codes.append("provider_subject_mismatch")

        if legacy_subscription_url:
            if provisioning_profile is None:
                mismatch_codes.append("missing_canonical_subscription_profile")
            if access_delivery_channel is None:
                mismatch_codes.append("missing_canonical_subscription_channel")
            elif (access_delivery_channel.delivery_payload or {}).get("subscription_url") != legacy_subscription_url:
                mismatch_codes.append("subscription_url_payload_mismatch")

        if canonical_entitlement_snapshot.get("status") != legacy_entitlement_snapshot.get("status"):
            mismatch_codes.append("entitlement_status_mismatch")
        if canonical_entitlement_snapshot.get("plan_code") != legacy_entitlement_snapshot.get("plan_code"):
            mismatch_codes.append("entitlement_plan_code_mismatch")

        return LegacyServiceAccessShadowResult(
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            provider_name=provider_name,
            legacy_provider_subject_ref=legacy_provider_subject_ref,
            legacy_subscription_url=legacy_subscription_url,
            legacy_entitlement_snapshot=legacy_entitlement_snapshot,
            canonical_entitlement_snapshot=canonical_entitlement_snapshot,
            service_identity=service_identity,
            provisioning_profile=provisioning_profile,
            access_delivery_channel=access_delivery_channel,
            mismatch_codes=mismatch_codes,
        )


class MigrateLegacyServiceAccessUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._shadow = GetLegacyServiceAccessShadowUseCase(session)

    async def execute(
        self,
        *,
        customer_account_id: UUID,
        auth_realm_id: UUID,
        provider_name: str,
    ) -> MigrateLegacyServiceAccessResult:
        shadow_before = await self._shadow.execute(
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            provider_name=provider_name,
        )
        customer = await self._session.get(MobileUserModel, customer_account_id)
        if customer is None:
            raise ValueError("Customer account not found")
        if not customer.remnawave_uuid:
            raise ValueError("Legacy provider subject reference is required for migration")

        service_identity_result = await CreateServiceIdentityUseCase(self._session).execute(
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            provider_name=provider_name,
            provider_subject_ref=customer.remnawave_uuid,
            service_context={
                "bridge_origin": "phase5_legacy_migration",
                "legacy_subscription_url_present": bool(customer.subscription_url),
            },
        )
        service_identity = service_identity_result.service_identity

        provisioning_profile_result = None
        access_delivery_channel_result = None
        if customer.subscription_url:
            provisioning_profile_result = await CreateProvisioningProfileUseCase(self._session).execute(
                service_identity_id=service_identity.id,
                profile_key=SUBSCRIPTION_URL_PROFILE_KEY,
                target_channel=SUBSCRIPTION_URL_TARGET_CHANNEL,
                delivery_method=SUBSCRIPTION_URL_DELIVERY_METHOD,
                provisioning_payload={
                    "bridge_origin": "phase5_legacy_migration",
                    "legacy_subscription_url": customer.subscription_url,
                },
            )
            access_delivery_channel_result = await CreateAccessDeliveryChannelUseCase(self._session).execute(
                service_identity_id=service_identity.id,
                provisioning_profile_id=provisioning_profile_result.provisioning_profile.id,
                channel_type="subscription_url",
                channel_subject_ref=_default_channel_subject_ref(
                    channel_type="subscription_url",
                    provided_subject_ref=None,
                    credential_subject_key=None,
                    service_identity_key=service_identity.service_key,
                ),
                delivery_context={
                    "bridge_origin": "phase5_legacy_migration",
                },
                delivery_payload={
                    "subscription_url": customer.subscription_url,
                    "legacy_subscription_url": customer.subscription_url,
                    "provider_name": provider_name,
                },
            )

        shadow_after = await self._shadow.execute(
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            provider_name=provider_name,
        )
        return MigrateLegacyServiceAccessResult(
            service_identity_created=service_identity_result.created,
            provisioning_profile_created=(
                provisioning_profile_result.created if provisioning_profile_result is not None else False
            ),
            access_delivery_channel_created=(
                access_delivery_channel_result.created if access_delivery_channel_result is not None else False
            ),
            service_identity=service_identity,
            provisioning_profile=(
                provisioning_profile_result.provisioning_profile
                if provisioning_profile_result is not None
                else None
            ),
            access_delivery_channel=(
                access_delivery_channel_result.access_delivery_channel
                if access_delivery_channel_result is not None
                else None
            ),
            shadow_before=shadow_before,
            shadow_after=shadow_after,
        )
