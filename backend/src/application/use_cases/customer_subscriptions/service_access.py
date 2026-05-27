from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.entitlements_service import EntitlementsService
from src.application.use_cases.customer_subscriptions.list_customer_subscriptions import (
    CustomerSubscriptionSummary,
    ListCustomerSubscriptionsUseCase,
)
from src.application.use_cases.service_access.access_delivery_channels import (
    CreateAccessDeliveryChannelUseCase,
    TouchAccessDeliveryChannelUseCase,
    _default_channel_subject_ref,
    _default_provisioning_profile_key,
    _default_target_channel,
)
from src.application.use_cases.service_access.provisioning_profiles import CreateProvisioningProfileUseCase
from src.application.use_cases.service_access.service_identities import CreateServiceIdentityUseCase
from src.application.use_cases.subscriptions.generate_config import GenerateConfigUseCase
from src.application.use_cases.subscriptions.stage1_paid_provisioning import STAGE1_PAID_TRAFFIC_LIMIT_STRATEGY
from src.application.use_cases.trial.stage1_trial_policy import (
    STAGE1_TRIAL_DEVICE_LIMIT,
    STAGE1_TRIAL_TRAFFIC_LIMIT_BYTES,
    STAGE1_TRIAL_TRAFFIC_LIMIT_STRATEGY,
)
from src.infrastructure.database.models.access_delivery_channel_model import AccessDeliveryChannelModel
from src.infrastructure.database.models.entitlement_grant_model import EntitlementGrantModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.provisioning_profile_model import ProvisioningProfileModel
from src.infrastructure.database.models.service_identity_model import ServiceIdentityModel
from src.infrastructure.database.repositories.service_access_repo import ServiceAccessRepository
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.stage1_ru_bundle import resolve_stage1_ru_bundle_external_squad_uuid
from src.infrastructure.remnawave.subscription_urls import normalize_public_subscription_url
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway


@dataclass(frozen=True)
class SelectedCustomerSubscriptionServiceState:
    subscription: CustomerSubscriptionSummary
    entitlement_snapshot: dict[str, Any]
    active_entitlement_grant: EntitlementGrantModel | None
    service_identity: ServiceIdentityModel | None
    provisioning_profile: ProvisioningProfileModel | None
    access_delivery_channel: AccessDeliveryChannelModel | None
    resolved_provisioning_profile_key: str | None
    resolved_channel_subject_ref: str | None


class CustomerSubscriptionServiceAccessUseCase:
    """Resolve VPN delivery state for one selected customer subscription."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ServiceAccessRepository(session)
        self._entitlements = EntitlementsService(session)
        self._subscriptions = ListCustomerSubscriptionsUseCase(session)

    async def get_service_state(
        self,
        *,
        customer_account_id: UUID,
        auth_realm_id: UUID,
        subscription_key: str,
        provider_name: str = "remnawave",
        channel_type: str | None = None,
        channel_subject_ref: str | None = None,
        provisioning_profile_key: str | None = None,
        remnawave_client: RemnawaveClient | None = None,
        ensure_delivery: bool = True,
    ) -> SelectedCustomerSubscriptionServiceState:
        item = await self._get_subscription(
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            subscription_key=subscription_key,
        )
        snapshot = self._snapshot_from_summary(item)
        grant = await self._get_selected_grant(item)
        service_identity = await self._ensure_subscription_service_identity(
            item=item,
            grant=grant,
            provider_name=provider_name,
            remnawave_client=remnawave_client,
        )

        resolved_profile_key = provisioning_profile_key or (
            _default_provisioning_profile_key(channel_type) if channel_type else None
        )
        provisioning_profile = None
        if service_identity is not None and resolved_profile_key is not None:
            provisioning_profile = await self._ensure_provisioning_profile(
                service_identity=service_identity,
                profile_key=resolved_profile_key,
                channel_type=channel_type or "shared_client",
            )

        resolved_channel_subject_ref = None
        access_delivery_channel = None
        if ensure_delivery and service_identity is not None and channel_type is not None:
            resolved_channel_subject_ref = _default_channel_subject_ref(
                channel_type=channel_type,
                provided_subject_ref=channel_subject_ref,
                credential_subject_key=None,
                service_identity_key=service_identity.service_key,
            )
            access_delivery_channel = await self._ensure_access_delivery_channel(
                service_identity=service_identity,
                provisioning_profile=provisioning_profile,
                channel_type=channel_type,
                channel_subject_ref=resolved_channel_subject_ref,
                entitlement_snapshot=snapshot,
            )

        return SelectedCustomerSubscriptionServiceState(
            subscription=item,
            entitlement_snapshot=snapshot,
            active_entitlement_grant=grant if item.status in {"active", "trial"} else None,
            service_identity=service_identity,
            provisioning_profile=provisioning_profile,
            access_delivery_channel=access_delivery_channel,
            resolved_provisioning_profile_key=resolved_profile_key,
            resolved_channel_subject_ref=resolved_channel_subject_ref,
        )

    async def get_config(
        self,
        *,
        customer_account_id: UUID,
        auth_realm_id: UUID,
        subscription_key: str,
        remnawave_client: RemnawaveClient,
    ) -> dict[str, Any]:
        state = await self.get_service_state(
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            subscription_key=subscription_key,
            provider_name="remnawave",
            channel_type="shared_client",
            provisioning_profile_key="shared_client-default",
            remnawave_client=remnawave_client,
            ensure_delivery=True,
        )
        service_identity = state.service_identity
        if service_identity is None or not service_identity.provider_subject_ref:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected subscription VPN identity is not provisioned",
            )

        config = await GenerateConfigUseCase(remnawave_client).execute(service_identity.provider_subject_ref)
        subscription_url = normalize_public_subscription_url(config.get("subscription_url"))
        if subscription_url:
            await self._store_subscription_url(
                service_identity=service_identity,
                subscription_url=subscription_url,
                channel=state.access_delivery_channel,
            )
        return config

    async def _get_subscription(
        self,
        *,
        customer_account_id: UUID,
        auth_realm_id: UUID,
        subscription_key: str,
    ) -> CustomerSubscriptionSummary:
        item = await self._subscriptions.get_by_key(
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            subscription_key=subscription_key,
        )
        if item is None:
            raise LookupError("Subscription not found")
        if item.status not in {"active", "trial"}:
            raise PermissionError("Selected subscription is not active")
        return item

    def _snapshot_from_summary(self, item: CustomerSubscriptionSummary) -> dict[str, Any]:
        return {
            "status": item.status,
            "plan_uuid": item.plan_uuid,
            "plan_code": item.plan_code,
            "display_name": item.display_name,
            "period_days": None,
            "expires_at": item.expires_at,
            "effective_entitlements": dict(item.effective_entitlements or {}),
            "invite_bundle": dict(item.invite_bundle or {}),
            "is_trial": item.is_trial,
            "addons": list(item.addons or []),
        }

    async def _get_selected_grant(
        self,
        item: CustomerSubscriptionSummary,
    ) -> EntitlementGrantModel | None:
        if item.entitlement_grant_id is None:
            return None
        grant = await self._repo.get_entitlement_grant_by_id(item.entitlement_grant_id)
        if grant is None:
            raise LookupError("Subscription grant not found")
        return grant

    async def _ensure_subscription_service_identity(
        self,
        *,
        item: CustomerSubscriptionSummary,
        grant: EntitlementGrantModel | None,
        provider_name: str,
        remnawave_client: RemnawaveClient | None,
    ) -> ServiceIdentityModel | None:
        customer_account_id = grant.customer_account_id if grant is not None else await self._customer_id(item)
        auth_realm_id = grant.auth_realm_id if grant is not None else await self._auth_realm_id(item)
        existing = await self._repo.get_service_identity_by_subscription_key(
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            provider_name=provider_name,
            subscription_key=item.subscription_key,
        )
        if existing is not None and existing.provider_subject_ref:
            if grant is not None and grant.service_identity_id != existing.id:
                grant.service_identity_id = existing.id
                await self._session.flush()
            return existing

        if item.kind == "trial":
            return await self._ensure_trial_service_identity(
                item=item,
                provider_name=provider_name,
                remnawave_client=remnawave_client,
                existing=existing,
            )
        if grant is None:
            return None
        return await self._ensure_grant_service_identity(
            item=item,
            grant=grant,
            provider_name=provider_name,
            remnawave_client=remnawave_client,
            existing=existing,
        )

    async def _ensure_grant_service_identity(
        self,
        *,
        item: CustomerSubscriptionSummary,
        grant: EntitlementGrantModel,
        provider_name: str,
        remnawave_client: RemnawaveClient | None,
        existing: ServiceIdentityModel | None,
    ) -> ServiceIdentityModel:
        if (
            existing is not None
            and existing.provider_subject_ref
            and existing.identity_scope == "subscription"
            and existing.subscription_key == item.subscription_key
        ):
            return existing

        if remnawave_client is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Selected subscription VPN identity requires Remnawave provisioning",
            )

        customer = await self._session.get(MobileUserModel, grant.customer_account_id)
        if customer is None:
            raise ValueError("Customer account not found")

        snapshot = self._snapshot_from_summary(item)
        effective = dict(snapshot.get("effective_entitlements") or {})
        gateway = RemnawaveUserGateway(remnawave_client)
        expires_at = _parse_datetime(item.expires_at) or datetime.now(UTC) + timedelta(days=3650)
        payload = {
            "email": customer.email,
            "expire_at": expires_at,
            "traffic_limit_bytes": _resolve_traffic_limit_bytes(effective),
            "trafficLimitStrategy": STAGE1_PAID_TRAFFIC_LIMIT_STRATEGY,
            "hwid_device_limit": max(1, int(effective.get("device_limit") or 1)),
        }
        if ru_bundle_squad_uuid := resolve_stage1_ru_bundle_external_squad_uuid(item.plan_code):
            payload["external_squad_uuid"] = ru_bundle_squad_uuid

        created_user = await gateway.create(
            username=f"cvpn_s_{grant.id.hex[:28]}",
            **payload,
        )
        subscription_url = normalize_public_subscription_url(created_user.subscription_url)

        if existing is None:
            created = await CreateServiceIdentityUseCase(self._session).execute(
                customer_account_id=grant.customer_account_id,
                auth_realm_id=grant.auth_realm_id,
                provider_name=provider_name,
                source_order_id=grant.source_order_id,
                origin_storefront_id=grant.origin_storefront_id,
                provider_subject_ref=str(created_user.uuid),
                identity_scope="subscription",
                subscription_key=item.subscription_key,
                service_context={
                    "subscription_key": item.subscription_key,
                    "entitlement_grant_id": str(grant.id),
                    "plan_code": item.plan_code,
                    "subscription_url": subscription_url,
                    "provisioned_from": "msub08_selected_grant",
                },
            )
            service_identity = created.service_identity
        else:
            existing.provider_subject_ref = str(created_user.uuid)
            existing.identity_status = "active"
            existing.service_context = {
                **dict(existing.service_context or {}),
                "subscription_key": item.subscription_key,
                "entitlement_grant_id": str(grant.id),
                "plan_code": item.plan_code,
                "subscription_url": subscription_url,
                "provisioned_from": "msub08_selected_grant",
            }
            service_identity = existing

        grant.service_identity_id = service_identity.id
        await self._ensure_provisioning_profile(
            service_identity=service_identity,
            profile_key="shared_client-default",
            channel_type="shared_client",
        )
        await self._store_subscription_url(service_identity=service_identity, subscription_url=subscription_url)
        await self._session.flush()
        return service_identity

    async def _ensure_trial_service_identity(
        self,
        *,
        item: CustomerSubscriptionSummary,
        provider_name: str,
        remnawave_client: RemnawaveClient | None,
        existing: ServiceIdentityModel | None,
    ) -> ServiceIdentityModel:
        customer_id = _parse_subscription_uuid(item.subscription_key, prefix="trial")
        customer = await self._session.get(MobileUserModel, customer_id)
        if customer is None:
            raise ValueError("Customer account not found")
        auth_realm_id = customer.auth_realm_id
        if auth_realm_id is None:
            raise ValueError("Customer account has no auth realm")

        provider_subject_ref = customer.remnawave_uuid
        subscription_url = normalize_public_subscription_url(customer.subscription_url)
        if not provider_subject_ref:
            if remnawave_client is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Selected trial VPN identity requires Remnawave provisioning",
                )
            gateway = RemnawaveUserGateway(remnawave_client)
            user = await gateway.create(
                username=f"cvpn_ts_{customer.id.hex[:27]}",
                email=customer.email,
                expire_at=_parse_datetime(item.expires_at) or datetime.now(UTC) + timedelta(days=3),
                traffic_limit_bytes=STAGE1_TRIAL_TRAFFIC_LIMIT_BYTES,
                trafficLimitStrategy=STAGE1_TRIAL_TRAFFIC_LIMIT_STRATEGY,
                hwid_device_limit=STAGE1_TRIAL_DEVICE_LIMIT,
            )
            provider_subject_ref = str(user.uuid)
            subscription_url = normalize_public_subscription_url(user.subscription_url)
            customer.remnawave_uuid = provider_subject_ref
            customer.subscription_url = subscription_url

        if existing is None:
            created = await CreateServiceIdentityUseCase(self._session).execute(
                customer_account_id=customer.id,
                auth_realm_id=auth_realm_id,
                provider_name=provider_name,
                provider_subject_ref=provider_subject_ref,
                identity_scope="subscription",
                subscription_key=item.subscription_key,
                service_context={
                    "subscription_key": item.subscription_key,
                    "subscription_url": subscription_url,
                    "provisioned_from": "msub08_selected_trial",
                },
            )
            service_identity = created.service_identity
        else:
            existing.provider_subject_ref = provider_subject_ref
            existing.identity_status = "active"
            existing.service_context = {
                **dict(existing.service_context or {}),
                "subscription_key": item.subscription_key,
                "subscription_url": subscription_url,
                "provisioned_from": "msub08_selected_trial",
            }
            service_identity = existing
        await self._store_subscription_url(service_identity=service_identity, subscription_url=subscription_url)
        await self._session.flush()
        return service_identity

    async def _ensure_provisioning_profile(
        self,
        *,
        service_identity: ServiceIdentityModel,
        profile_key: str,
        channel_type: str,
    ) -> ProvisioningProfileModel:
        existing = await self._repo.get_provisioning_profile_by_service_identity_and_key(
            service_identity_id=service_identity.id,
            profile_key=profile_key,
        )
        if existing is not None:
            return existing
        result = await CreateProvisioningProfileUseCase(self._session).execute(
            service_identity_id=service_identity.id,
            profile_key=profile_key,
            target_channel=_default_target_channel(channel_type),
            delivery_method=channel_type,
            provisioning_payload={
                "resolved_from": "selected_customer_subscription",
                "subscription_key": service_identity.subscription_key,
                "provider_name": service_identity.provider_name,
            },
        )
        return result.provisioning_profile

    async def _ensure_access_delivery_channel(
        self,
        *,
        service_identity: ServiceIdentityModel,
        provisioning_profile: ProvisioningProfileModel | None,
        channel_type: str,
        channel_subject_ref: str,
        entitlement_snapshot: dict[str, Any],
    ) -> AccessDeliveryChannelModel:
        result = await CreateAccessDeliveryChannelUseCase(self._session).execute(
            service_identity_id=service_identity.id,
            provisioning_profile_id=provisioning_profile.id if provisioning_profile is not None else None,
            channel_type=channel_type,
            channel_subject_ref=channel_subject_ref,
            delivery_context={
                "resolved_from": "selected_customer_subscription",
                "subscription_key": service_identity.subscription_key,
            },
            delivery_payload={
                "entitlement_status": entitlement_snapshot.get("status"),
                "provider_name": service_identity.provider_name,
                "subscription_key": service_identity.subscription_key,
                "subscription_url": (service_identity.service_context or {}).get("subscription_url"),
            },
        )
        channel = result.access_delivery_channel
        channel.delivery_payload = {
            **dict(channel.delivery_payload or {}),
            "entitlement_status": entitlement_snapshot.get("status"),
            "provider_name": service_identity.provider_name,
            "subscription_key": service_identity.subscription_key,
            "subscription_url": (service_identity.service_context or {}).get("subscription_url"),
        }
        await TouchAccessDeliveryChannelUseCase(self._session).execute(
            access_delivery_channel_id=channel.id,
            delivered=True,
        )
        return channel

    async def _store_subscription_url(
        self,
        *,
        service_identity: ServiceIdentityModel,
        subscription_url: str | None,
        channel: AccessDeliveryChannelModel | None = None,
    ) -> None:
        if not subscription_url:
            return
        service_identity.service_context = {
            **dict(service_identity.service_context or {}),
            "subscription_url": subscription_url,
        }
        if channel is None:
            channels = await self._repo.list_access_delivery_channels(
                service_identity_id=service_identity.id,
                channel_type="shared_client",
                limit=1,
            )
            channel = channels[0] if channels else None
        if channel is not None:
            channel.delivery_payload = {
                **dict(channel.delivery_payload or {}),
                "subscription_url": subscription_url,
                "subscription_key": service_identity.subscription_key,
            }
        await self._session.flush()

    async def _customer_id(self, item: CustomerSubscriptionSummary) -> UUID:
        if item.kind == "trial":
            return _parse_subscription_uuid(item.subscription_key, prefix="trial")
        if item.entitlement_grant_id is not None:
            grant = await self._repo.get_entitlement_grant_by_id(item.entitlement_grant_id)
            if grant is not None:
                return grant.customer_account_id
        raise LookupError("Cannot resolve subscription customer")

    async def _auth_realm_id(self, item: CustomerSubscriptionSummary) -> UUID:
        if item.kind == "trial":
            customer = await self._session.get(
                MobileUserModel,
                _parse_subscription_uuid(item.subscription_key, prefix="trial"),
            )
            if customer is not None and customer.auth_realm_id is not None:
                return customer.auth_realm_id
        if item.entitlement_grant_id is not None:
            grant = await self._repo.get_entitlement_grant_by_id(item.entitlement_grant_id)
            if grant is not None:
                return grant.auth_realm_id
        raise LookupError("Cannot resolve subscription auth realm")


def _parse_subscription_uuid(subscription_key: str, *, prefix: str) -> UUID:
    raw_prefix, _, raw_uuid = subscription_key.partition(":")
    if raw_prefix != prefix or not raw_uuid:
        raise LookupError("Unsupported subscription key")
    return UUID(raw_uuid)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _resolve_traffic_limit_bytes(effective_entitlements: dict[str, Any]) -> int | None:
    raw = effective_entitlements.get("traffic_limit_bytes")
    if isinstance(raw, int) and raw > 0:
        return raw
    label = str(effective_entitlements.get("display_traffic_label") or "")
    match = re.search(r"(\d+(?:\.\d+)?)\s*(gib|gb|mib|mb)", label, re.IGNORECASE)
    if match is None:
        return None
    amount = float(match.group(1))
    unit = match.group(2).lower()
    multiplier = 1024**3 if unit in {"gb", "gib"} else 1024**2
    return int(amount * multiplier)
