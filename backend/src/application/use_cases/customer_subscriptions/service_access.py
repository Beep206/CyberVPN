from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.entitlements_service import EntitlementsService
from src.application.use_cases.customer_subscriptions.list_customer_subscriptions import (
    CustomerSubscriptionSummary,
    ListCustomerSubscriptionsUseCase,
)
from src.application.use_cases.invites.lifetime_policy import remnawave_lifetime_payload
from src.application.use_cases.service_access.access_delivery_channels import (
    CreateAccessDeliveryChannelUseCase,
    TouchAccessDeliveryChannelUseCase,
    _default_channel_subject_ref,
    _default_provisioning_profile_key,
    _default_target_channel,
)
from src.application.use_cases.service_access.device_credentials import (
    CreateDeviceCredentialUseCase,
    TouchDeviceCredentialUseCase,
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
from src.config.settings import settings
from src.infrastructure.database.models.access_delivery_channel_model import AccessDeliveryChannelModel
from src.infrastructure.database.models.device_credential_model import DeviceCredentialModel
from src.infrastructure.database.models.entitlement_grant_model import EntitlementGrantModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.provisioning_profile_model import ProvisioningProfileModel
from src.infrastructure.database.models.service_identity_model import ServiceIdentityModel
from src.infrastructure.database.repositories.service_access_repo import ServiceAccessRepository
from src.infrastructure.monitoring.instrumentation.growth_codes import observe_lifetime_remnawave_expiry_mode
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.smart_ru_bundle import (
    SmartRuConfigurationError,
    resolve_smart_ru_external_squad_uuid,
    resolve_smart_ru_internal_squad_uuids,
)
from src.infrastructure.remnawave.spb_de_exceptions_bundle import (
    SpbDeExceptionsConfigurationError,
    SpbDeExceptionsRoutingBundle,
    resolve_spb_de_exceptions_bundle,
)
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
    device_credential: DeviceCredentialModel | None
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
        credential_type: str | None = None,
        credential_subject_key: str | None = None,
        remnawave_client: RemnawaveClient | None = None,
        ensure_delivery: bool = True,
    ) -> SelectedCustomerSubscriptionServiceState:
        if bool(credential_type) ^ bool(credential_subject_key):
            raise ValueError("credential_type and credential_subject_key must be provided together")

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

        device_credential = None
        if service_identity is not None and credential_type and credential_subject_key:
            device_credential = await self._ensure_device_credential(
                service_identity=service_identity,
                provisioning_profile=provisioning_profile,
                credential_type=credential_type,
                credential_subject_key=credential_subject_key,
            )

        resolved_channel_subject_ref = None
        access_delivery_channel = None
        if ensure_delivery and service_identity is not None and channel_type is not None:
            resolved_channel_subject_ref = _default_channel_subject_ref(
                channel_type=channel_type,
                provided_subject_ref=channel_subject_ref,
                credential_subject_key=credential_subject_key,
                service_identity_key=service_identity.service_key,
            )
            access_delivery_channel = await self._ensure_access_delivery_channel(
                service_identity=service_identity,
                provisioning_profile=provisioning_profile,
                device_credential=device_credential,
                channel_type=channel_type,
                channel_subject_ref=resolved_channel_subject_ref,
                entitlement_snapshot=snapshot,
            )
            resolved_channel_subject_ref = access_delivery_channel.channel_subject_ref
            if device_credential is None and access_delivery_channel.device_credential_id is not None:
                device_credential = await self._repo.get_device_credential_by_id(
                    access_delivery_channel.device_credential_id
                )

        return SelectedCustomerSubscriptionServiceState(
            subscription=item,
            entitlement_snapshot=snapshot,
            active_entitlement_grant=grant if item.status in {"active", "trial"} else None,
            service_identity=service_identity,
            provisioning_profile=provisioning_profile,
            device_credential=device_credential,
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

        config = await GenerateConfigUseCase(remnawave_client).execute(
            service_identity.provider_subject_ref,
            plan_code=state.subscription.plan_code,
        )
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
        duration_mode = getattr(item, "duration_mode", None)
        lifetime = bool(getattr(item, "lifetime", False)) or duration_mode == "lifetime"
        return {
            "status": item.status,
            "plan_uuid": item.plan_uuid,
            "plan_code": item.plan_code,
            "display_name": item.display_name,
            "period_days": None,
            "duration_mode": duration_mode,
            "lifetime": lifetime,
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
        await _acquire_selected_subscription_provisioning_lock(
            self._session,
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            provider_name=provider_name,
            subscription_key=item.subscription_key,
        )
        existing = await self._repo.get_service_identity_by_subscription_key(
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            provider_name=provider_name,
            subscription_key=item.subscription_key,
        )
        if existing is not None and existing.provider_subject_ref:
            spb_de_exceptions_bundle = _resolve_spb_de_exceptions_bundle_or_http(item.plan_code)
            if spb_de_exceptions_bundle is not None and (remnawave_client is None or grant is None):
                _assert_spb_de_exceptions_context(existing, spb_de_exceptions_bundle)
            if grant is not None and grant.service_identity_id != existing.id:
                grant.service_identity_id = existing.id
                await self._session.flush()
            if grant is not None and remnawave_client is not None:
                return await self._ensure_grant_service_identity(
                    item=item,
                    grant=grant,
                    provider_name=provider_name,
                    remnawave_client=remnawave_client,
                    existing=existing,
                )
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
        spb_de_exceptions_bundle = _resolve_spb_de_exceptions_bundle_or_http(item.plan_code)

        if remnawave_client is None:
            if (
                existing is not None
                and existing.provider_subject_ref
                and existing.identity_scope == "subscription"
                and existing.subscription_key == item.subscription_key
            ):
                if spb_de_exceptions_bundle is not None:
                    _assert_spb_de_exceptions_context(existing, spb_de_exceptions_bundle)
                return existing
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Selected subscription VPN identity requires Remnawave provisioning",
            )

        customer = await self._session.get(MobileUserModel, grant.customer_account_id)
        if customer is None:
            raise ValueError("Customer account not found")

        snapshot = self._snapshot_from_summary(item)
        grant_snapshot = dict(getattr(grant, "grant_snapshot", None) or {})
        effective = dict(snapshot.get("effective_entitlements") or {})
        gateway = RemnawaveUserGateway(remnawave_client)
        expires_at = _parse_datetime(item.expires_at)
        duration_mode = str(grant_snapshot.get("duration_mode") or snapshot.get("duration_mode") or "").strip()
        lifetime_access = (
            bool(grant_snapshot.get("lifetime")) or bool(snapshot.get("lifetime")) or duration_mode == "lifetime"
        )
        payload = {
            "email": customer.email,
            "traffic_limit_bytes": _resolve_traffic_limit_bytes(effective),
            "trafficLimitStrategy": STAGE1_PAID_TRAFFIC_LIMIT_STRATEGY,
            "hwid_device_limit": max(1, int(effective.get("device_limit") or 1)),
        }
        if expires_at is not None:
            payload["expire_at"] = expires_at
        elif lifetime_access:
            payload.update(
                remnawave_lifetime_payload(
                    mode=settings.remnawave_lifetime_expiry_mode,
                    sentinel_expire_at=settings.remnawave_lifetime_expire_at,
                )
            )
        else:
            payload["expire_at"] = datetime.now(UTC) + timedelta(days=3650)
        spb_de_exceptions_context = (
            spb_de_exceptions_bundle.service_context() if spb_de_exceptions_bundle is not None else {}
        )
        if spb_de_exceptions_bundle is not None:
            external_squad_uuid = spb_de_exceptions_bundle.external_squad_uuid
            internal_squad_uuids = list(spb_de_exceptions_bundle.internal_squad_uuids)
        else:
            try:
                smart_ru_external_squad_uuid = resolve_smart_ru_external_squad_uuid(item.plan_code)
                smart_ru_internal_squad_uuids = resolve_smart_ru_internal_squad_uuids(item.plan_code)
            except SmartRuConfigurationError as exc:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Selected subscription VPN identity requires Premium Smart RU routing configuration",
                ) from exc
            external_squad_uuid = smart_ru_external_squad_uuid or resolve_stage1_ru_bundle_external_squad_uuid(
                item.plan_code
            )
            internal_squad_uuids = smart_ru_internal_squad_uuids
        if external_squad_uuid:
            payload["external_squad_uuid"] = external_squad_uuid
        if internal_squad_uuids:
            payload["active_internal_squads"] = internal_squad_uuids

        if (
            existing is not None
            and existing.provider_subject_ref
            and existing.identity_scope == "subscription"
            and existing.subscription_key == item.subscription_key
        ):
            existing_uuid = _parse_remnawave_uuid(existing.provider_subject_ref)
            existing_user = await gateway.get_by_uuid(existing_uuid) if existing_uuid is not None else None
            if existing_user is not None:
                if grant.service_identity_id != existing.id:
                    grant.service_identity_id = existing.id
                if spb_de_exceptions_bundle is not None and not _has_spb_de_exceptions_context(
                    existing,
                    spb_de_exceptions_bundle,
                ):
                    existing_user = await gateway.update(existing_user.uuid, **payload)
                if spb_de_exceptions_context:
                    existing.service_context = {
                        **_strip_bridge_context_keys(existing.service_context),
                        **spb_de_exceptions_context,
                    }
                subscription_url = normalize_public_subscription_url(existing_user.subscription_url)
                if subscription_url:
                    if customer.remnawave_uuid != str(existing_user.uuid):
                        customer.remnawave_uuid = str(existing_user.uuid)
                    if normalize_public_subscription_url(customer.subscription_url) != subscription_url:
                        customer.subscription_url = subscription_url
                    await self._store_subscription_url(
                        service_identity=existing,
                        subscription_url=subscription_url,
                    )
                if subscription_url or spb_de_exceptions_context:
                    await self._session.flush()
                return existing

        created_user = await gateway.create(
            username=f"cvpn_s_{grant.id.hex[:28]}",
            **payload,
        )
        if lifetime_access:
            observe_lifetime_remnawave_expiry_mode(
                mode=str(payload.get("lifetime_expiry_mode") or "sentinel"),
                result="success",
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
                    "duration_mode": duration_mode or None,
                    "subscription_url": subscription_url,
                    "provisioned_from": "msub08_selected_grant",
                    "lifetime": lifetime_access,
                    "remnawave_lifetime_expiry_mode": payload.get("lifetime_expiry_mode"),
                    "remnawave_lifetime_expire_at": payload.get("lifetime_expire_at"),
                    "upstream_expiry_mode": payload.get("upstream_expiry_mode"),
                    "upstream_expires_at": payload.get("upstream_expires_at"),
                    **spb_de_exceptions_context,
                },
            )
            service_identity = created.service_identity
        else:
            existing.provider_subject_ref = str(created_user.uuid)
            existing.identity_status = "active"
            existing.service_context = {
                **(
                    _strip_bridge_context_keys(existing.service_context)
                    if spb_de_exceptions_context
                    else dict(existing.service_context or {})
                ),
                "subscription_key": item.subscription_key,
                "entitlement_grant_id": str(grant.id),
                "plan_code": item.plan_code,
                "duration_mode": duration_mode or None,
                "subscription_url": subscription_url,
                "provisioned_from": "msub08_selected_grant",
                "lifetime": lifetime_access,
                "remnawave_lifetime_expiry_mode": payload.get("lifetime_expiry_mode"),
                "remnawave_lifetime_expire_at": payload.get("lifetime_expire_at"),
                "upstream_expiry_mode": payload.get("upstream_expiry_mode"),
                "upstream_expires_at": payload.get("upstream_expires_at"),
                **spb_de_exceptions_context,
            }
            service_identity = existing

        grant.service_identity_id = service_identity.id
        if customer.remnawave_uuid != str(created_user.uuid):
            customer.remnawave_uuid = str(created_user.uuid)
        if (
            subscription_url
            and normalize_public_subscription_url(getattr(customer, "subscription_url", None)) != subscription_url
        ):
            customer.subscription_url = subscription_url
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
        routing_payload = _provisioning_routing_payload(dict(service_identity.service_context or {}))
        if existing is not None:
            if routing_payload:
                existing_payload = _strip_bridge_context_keys(getattr(existing, "provisioning_payload", None))
                if existing_payload.get("remnawave_routing") != routing_payload:
                    existing.provisioning_payload = {
                        **existing_payload,
                        "remnawave_routing": routing_payload,
                    }
                    await self._session.flush()
            return existing
        provisioning_payload: dict[str, Any] = {
            "resolved_from": "selected_customer_subscription",
            "subscription_key": service_identity.subscription_key,
            "provider_name": service_identity.provider_name,
        }
        if routing_payload:
            provisioning_payload["remnawave_routing"] = routing_payload
        result = await CreateProvisioningProfileUseCase(self._session).execute(
            service_identity_id=service_identity.id,
            profile_key=profile_key,
            target_channel=_default_target_channel(channel_type),
            delivery_method=channel_type,
            provisioning_payload=provisioning_payload,
        )
        return result.provisioning_profile

    async def _ensure_device_credential(
        self,
        *,
        service_identity: ServiceIdentityModel,
        provisioning_profile: ProvisioningProfileModel | None,
        credential_type: str,
        credential_subject_key: str,
    ) -> DeviceCredentialModel:
        result = await CreateDeviceCredentialUseCase(self._session).execute(
            service_identity_id=service_identity.id,
            provisioning_profile_id=provisioning_profile.id if provisioning_profile is not None else None,
            credential_type=credential_type,
            subject_key=credential_subject_key,
            credential_context={
                "resolved_from": "selected_customer_subscription",
                "subscription_key": service_identity.subscription_key,
                "provider_name": service_identity.provider_name,
            },
        )
        credential = result.device_credential
        if credential.credential_status != "active":
            raise PermissionError("Selected subscription device credential is not active")
        await TouchDeviceCredentialUseCase(self._session).execute(device_credential_id=credential.id)
        return credential

    async def _ensure_access_delivery_channel(
        self,
        *,
        service_identity: ServiceIdentityModel,
        provisioning_profile: ProvisioningProfileModel | None,
        device_credential: DeviceCredentialModel | None,
        channel_type: str,
        channel_subject_ref: str,
        entitlement_snapshot: dict[str, Any],
    ) -> AccessDeliveryChannelModel:
        result = await CreateAccessDeliveryChannelUseCase(self._session).execute(
            service_identity_id=service_identity.id,
            provisioning_profile_id=provisioning_profile.id if provisioning_profile is not None else None,
            device_credential_id=device_credential.id if device_credential is not None else None,
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
        if provisioning_profile is not None and channel.provisioning_profile_id is None:
            channel.provisioning_profile_id = provisioning_profile.id
        if device_credential is not None and channel.device_credential_id is None:
            channel.device_credential_id = device_credential.id
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


async def _acquire_selected_subscription_provisioning_lock(
    session: Any,
    *,
    customer_account_id: UUID,
    auth_realm_id: UUID,
    provider_name: str,
    subscription_key: str,
) -> None:
    get_bind = getattr(session, "get_bind", None)
    bind = get_bind() if callable(get_bind) else None
    dialect_name = getattr(getattr(bind, "dialect", None), "name", "")
    if dialect_name != "postgresql":
        return

    execute = getattr(session, "execute", None)
    if not callable(execute):
        return

    scope = (
        f"selected-subscription-provisioning:{customer_account_id}:{auth_realm_id}:{provider_name}:{subscription_key}"
    )
    lock_id = int.from_bytes(hashlib.blake2b(scope.encode("utf-8"), digest_size=8).digest(), "big", signed=True)
    await execute(text("select pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id})


def _resolve_spb_de_exceptions_bundle_or_http(plan_code: str | None) -> SpbDeExceptionsRoutingBundle | None:
    try:
        return resolve_spb_de_exceptions_bundle(plan_code)
    except SpbDeExceptionsConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Selected subscription VPN identity requires Premium SPB/DE Exceptions routing configuration",
        ) from exc


def _has_spb_de_exceptions_context(
    service_identity: ServiceIdentityModel,
    bundle: SpbDeExceptionsRoutingBundle,
) -> bool:
    context = dict(service_identity.service_context or {})
    return all(context.get(key) == value for key, value in bundle.service_context().items())


def _assert_spb_de_exceptions_context(
    service_identity: ServiceIdentityModel,
    bundle: SpbDeExceptionsRoutingBundle,
) -> None:
    if _has_spb_de_exceptions_context(service_identity, bundle):
        return
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Selected subscription VPN identity requires Premium SPB/DE Exceptions routing configuration",
    )


def _provisioning_routing_payload(service_context: dict[str, Any]) -> dict[str, Any]:
    routing_keys = (
        "remnawave_routing_product",
        "remnawave_external_squad_uuid",
        "remnawave_internal_squad_uuids",
        "remnawave_config_profile",
        "remnawave_policy_version",
        "remnawave_fail_closed_for_matched_exceptions",
    )
    return {key: service_context[key] for key in routing_keys if key in service_context}


def _strip_bridge_context_keys(service_context: dict[str, Any] | None) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in dict(service_context or {}).items():
        if "bridge" in str(key).lower():
            continue
        if isinstance(value, dict):
            sanitized[key] = _strip_bridge_context_keys(value)
        elif isinstance(value, list):
            sanitized[key] = [_strip_bridge_context_keys(item) if isinstance(item, dict) else item for item in value]
        else:
            sanitized[key] = value
    return sanitized


def _parse_subscription_uuid(subscription_key: str, *, prefix: str) -> UUID:
    raw_prefix, _, raw_uuid = subscription_key.partition(":")
    if raw_prefix != prefix or not raw_uuid:
        raise LookupError("Unsupported subscription key")
    return UUID(raw_uuid)


def _parse_remnawave_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None


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
