from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.remnawave_identity_access import (
    RemnawaveIdentityAccessConflict,
    persist_runtime_mapped_service_identity,
    resolve_exact_mapped_remnawave_ref,
)
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.models.service_identity_model import ServiceIdentityModel
from src.infrastructure.database.repositories.service_access_repo import ServiceAccessRepository

_REMNAWAVE_BINDING_STATE_KEY = "remnawave_binding_state"
_REMNAWAVE_BINDING_PENDING = "pending_provider_create"
_REMNAWAVE_BINDING_MAPPED = "mapped"


@dataclass(frozen=True)
class CreateServiceIdentityResult:
    created: bool
    service_identity: ServiceIdentityModel


class CreateServiceIdentityUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ServiceAccessRepository(session)

    async def execute(
        self,
        *,
        customer_account_id: UUID,
        auth_realm_id: UUID,
        provider_name: str,
        source_order_id: UUID | None = None,
        origin_storefront_id: UUID | None = None,
        provider_subject_ref: str | None = None,
        provider_numeric_subject_id: int | None = None,
        identity_scope: str = "account",
        subscription_key: str | None = None,
        service_context: dict[str, Any] | None = None,
        allow_pending_remnawave_binding: bool = False,
    ) -> CreateServiceIdentityResult:
        normalized_provider_name = provider_name.strip().lower()
        if not normalized_provider_name:
            raise ValueError("Provider name is required")

        customer = await self._session.get(MobileUserModel, customer_account_id)
        if customer is None:
            raise ValueError("Customer account not found")

        realm = await self._session.get(AuthRealmModel, auth_realm_id)
        if realm is None:
            raise ValueError("Auth realm not found")

        if customer.auth_realm_id and customer.auth_realm_id != auth_realm_id:
            raise ValueError("Customer account does not belong to auth realm")

        if identity_scope not in {"account", "subscription"}:
            raise ValueError("Unsupported service identity scope")
        if identity_scope == "subscription" and not subscription_key:
            raise ValueError("Subscription-scoped service identity requires subscription_key")
        if allow_pending_remnawave_binding and (
            normalized_provider_name != "remnawave"
            or identity_scope != "account"
            or provider_subject_ref is not None
            or provider_numeric_subject_id is not None
        ):
            raise ValueError("Pending Remnawave binding is only valid for an unbound account identity")

        resolved_provider_subject_ref = provider_subject_ref
        resolved_provider_numeric_subject_id = provider_numeric_subject_id
        resolved_remnawave_ref: RemnawaveUserRef | None = None
        if normalized_provider_name == "remnawave":
            resolved_remnawave_ref = await self._resolve_runtime_remnawave_identity(
                customer=customer,
                provider_subject_ref=provider_subject_ref,
                provider_numeric_subject_id=provider_numeric_subject_id,
                require_customer_binding=(
                    identity_scope == "account"
                    or (provider_subject_ref is None and provider_numeric_subject_id is None)
                ),
                allow_missing_customer_binding=allow_pending_remnawave_binding,
            )
            if resolved_remnawave_ref is not None:
                resolved_provider_subject_ref = (
                    str(resolved_remnawave_ref.legacy_uuid) if resolved_remnawave_ref.legacy_uuid is not None else None
                )
                resolved_provider_numeric_subject_id = resolved_remnawave_ref.require_numeric_id()

        if identity_scope == "subscription":
            existing = await self._repo.get_service_identity_by_subscription_key(
                customer_account_id=customer_account_id,
                auth_realm_id=auth_realm_id,
                provider_name=normalized_provider_name,
                subscription_key=subscription_key or "",
            )
        else:
            existing = await self._repo.get_service_identity_by_customer_realm_provider(
                customer_account_id=customer_account_id,
                auth_realm_id=auth_realm_id,
                provider_name=normalized_provider_name,
            )
        if existing is not None:
            if resolved_remnawave_ref is not None:
                try:
                    await persist_runtime_mapped_service_identity(
                        self._session,
                        service_identity=existing,
                        remnawave_user_id=resolved_remnawave_ref.require_numeric_id(),
                        remnawave_uuid=resolved_remnawave_ref.legacy_uuid,
                        source="service_identity_existing",
                    )
                except RemnawaveIdentityAccessConflict as exc:
                    raise ValueError("Existing service identity does not match reconciled identity") from exc
                await self._activate_pending_identity_after_exact_mapping(existing)
            elif normalized_provider_name == "remnawave":
                self._require_safe_pending_identity(existing)
            return CreateServiceIdentityResult(created=False, service_identity=existing)

        resolved_origin_storefront_id = origin_storefront_id
        if source_order_id is not None:
            source_order = await self._session.get(OrderModel, source_order_id)
            if source_order is None:
                raise ValueError("Source order not found")
            if source_order.user_id != customer_account_id:
                raise ValueError("Source order does not belong to customer account")
            if source_order.auth_realm_id != auth_realm_id:
                raise ValueError("Source order does not belong to auth realm")
            if resolved_origin_storefront_id and resolved_origin_storefront_id != source_order.storefront_id:
                raise ValueError("Origin storefront does not match source order")
            resolved_origin_storefront_id = source_order.storefront_id

        merged_context = dict(service_context or {})
        if customer.subscription_url and "legacy_subscription_url" not in merged_context:
            merged_context["legacy_subscription_url"] = customer.subscription_url
        pending_remnawave_binding = normalized_provider_name == "remnawave" and resolved_remnawave_ref is None
        if pending_remnawave_binding:
            merged_context[_REMNAWAVE_BINDING_STATE_KEY] = _REMNAWAVE_BINDING_PENDING

        model = ServiceIdentityModel(
            id=uuid.uuid4(),
            service_key=f"svc_{uuid.uuid4().hex}",
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            source_order_id=source_order_id,
            origin_storefront_id=resolved_origin_storefront_id,
            provider_name=normalized_provider_name,
            identity_scope=identity_scope,
            subscription_key=subscription_key,
            provider_subject_ref=(
                resolved_provider_subject_ref
                if normalized_provider_name == "remnawave"
                else resolved_provider_subject_ref or customer.remnawave_uuid
            ),
            provider_numeric_subject_id=(
                resolved_provider_numeric_subject_id
                if resolved_provider_numeric_subject_id is not None
                else getattr(customer, "remnawave_user_id", None)
            ),
            identity_status="suspended" if pending_remnawave_binding else "active",
            service_context=merged_context,
        )
        created = await self._repo.create_service_identity(model)
        if resolved_remnawave_ref is not None:
            try:
                await persist_runtime_mapped_service_identity(
                    self._session,
                    service_identity=created,
                    remnawave_user_id=resolved_remnawave_ref.require_numeric_id(),
                    remnawave_uuid=resolved_remnawave_ref.legacy_uuid,
                    source="service_identity_create",
                )
            except RemnawaveIdentityAccessConflict as exc:
                raise ValueError("Service identity could not be reconciled") from exc
        return CreateServiceIdentityResult(created=True, service_identity=created)

    async def _resolve_runtime_remnawave_identity(
        self,
        *,
        customer: MobileUserModel,
        provider_subject_ref: str | None,
        provider_numeric_subject_id: int | None,
        require_customer_binding: bool,
        allow_missing_customer_binding: bool,
    ) -> RemnawaveUserRef | None:
        if require_customer_binding:
            try:
                customer_ref = await resolve_exact_mapped_remnawave_ref(
                    self._session,
                    subject_type="mobile_user",
                    subject_id=customer.id,
                    numeric_user_id=customer.remnawave_user_id,
                    legacy_uuid_raw=customer.remnawave_uuid,
                )
            except RemnawaveIdentityAccessConflict as exc:
                raise ValueError("Customer Remnawave identity is not exactly reconciled") from exc
            if customer_ref is None:
                if allow_missing_customer_binding:
                    return None
                raise ValueError("Customer account has no canonical Remnawave identity")
            if provider_subject_ref is not None:
                if customer_ref.legacy_uuid is None or provider_subject_ref != str(customer_ref.legacy_uuid):
                    raise ValueError("Provider subject reference does not belong to customer account")
            if provider_numeric_subject_id is not None and (
                isinstance(provider_numeric_subject_id, bool)
                or provider_numeric_subject_id != customer_ref.require_numeric_id()
            ):
                raise ValueError("Provider numeric subject id does not belong to customer account")
            return customer_ref

        if (
            isinstance(provider_numeric_subject_id, bool)
            or not isinstance(provider_numeric_subject_id, int)
            or provider_numeric_subject_id <= 0
        ):
            raise ValueError("Remnawave service identity requires a positive numeric id")
        legacy_uuid = None
        if provider_subject_ref is not None:
            try:
                legacy_uuid = UUID(provider_subject_ref)
            except ValueError as exc:
                raise ValueError("Remnawave service identity requires a valid rollback reference") from exc
        return RemnawaveUserRef(id=provider_numeric_subject_id, legacy_uuid=legacy_uuid)

    @staticmethod
    def _require_safe_pending_identity(service_identity: ServiceIdentityModel) -> None:
        if (
            service_identity.identity_status != "suspended"
            or service_identity.provider_numeric_subject_id is not None
            or service_identity.provider_subject_ref not in {None, ""}
            or dict(service_identity.service_context or {}).get(_REMNAWAVE_BINDING_STATE_KEY)
            != _REMNAWAVE_BINDING_PENDING
        ):
            raise ValueError("Existing Remnawave service identity is not safely pending provider binding")

    async def _activate_pending_identity_after_exact_mapping(
        self,
        service_identity: ServiceIdentityModel,
    ) -> None:
        context = dict(service_identity.service_context or {})
        if context.get(_REMNAWAVE_BINDING_STATE_KEY) != _REMNAWAVE_BINDING_PENDING:
            return
        if service_identity.identity_status != "suspended":
            raise ValueError("Pending Remnawave service identity has an invalid status")
        service_identity.identity_status = "active"
        context[_REMNAWAVE_BINDING_STATE_KEY] = _REMNAWAVE_BINDING_MAPPED
        service_identity.service_context = context
        await self._session.flush()


class BindProvisionedRemnawaveServiceIdentityUseCase:
    """Bind a controlled pending placeholder only after an exact provider response."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ServiceAccessRepository(session)

    async def validate_target(
        self,
        *,
        service_identity_id: UUID,
        customer_account_id: UUID,
        auth_realm_id: UUID,
    ) -> ServiceIdentityModel:
        service_identity = await self._repo.get_service_identity_by_id(service_identity_id)
        if service_identity is None:
            raise ValueError("Provisioned service identity not found")
        if (
            service_identity.customer_account_id != customer_account_id
            or service_identity.auth_realm_id != auth_realm_id
            or service_identity.provider_name != "remnawave"
            or service_identity.identity_scope != "account"
        ):
            raise ValueError("Provisioned service identity does not belong to the redeemed access")

        context = dict(service_identity.service_context or {})
        if context.get(_REMNAWAVE_BINDING_STATE_KEY) == _REMNAWAVE_BINDING_PENDING:
            CreateServiceIdentityUseCase._require_safe_pending_identity(service_identity)
            return service_identity

        if service_identity.identity_status != "active":
            raise ValueError("Service identity is not provisionable")
        try:
            mapped_ref = await resolve_exact_mapped_remnawave_ref(
                self._session,
                subject_type="service_identity",
                subject_id=service_identity.id,
                numeric_user_id=service_identity.provider_numeric_subject_id,
                legacy_uuid_raw=service_identity.provider_subject_ref,
            )
        except RemnawaveIdentityAccessConflict as exc:
            raise ValueError("Service identity is not exactly reconciled") from exc
        if mapped_ref is None:
            raise ValueError("Active service identity cannot be unbound")
        return service_identity

    async def execute(
        self,
        *,
        service_identity_id: UUID,
        customer_account_id: UUID,
        auth_realm_id: UUID,
        remnawave_user_id: int,
        remnawave_uuid: str | None,
        mapping_source: str,
    ) -> ServiceIdentityModel:
        service_identity = await self.validate_target(
            service_identity_id=service_identity_id,
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
        )
        try:
            await persist_runtime_mapped_service_identity(
                self._session,
                service_identity=service_identity,
                remnawave_user_id=remnawave_user_id,
                remnawave_uuid=remnawave_uuid,
                source=mapping_source,
            )
        except RemnawaveIdentityAccessConflict as exc:
            raise ValueError("Service identity could not be reconciled") from exc

        context = dict(service_identity.service_context or {})
        context[_REMNAWAVE_BINDING_STATE_KEY] = _REMNAWAVE_BINDING_MAPPED
        service_identity.service_context = context
        service_identity.identity_status = "active"
        await self._session.flush()
        return service_identity


class GetServiceIdentityUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ServiceAccessRepository(session)

    async def execute(self, *, service_identity_id: UUID) -> ServiceIdentityModel | None:
        return await self._repo.get_service_identity_by_id(service_identity_id)


class ListServiceIdentitiesUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ServiceAccessRepository(session)

    async def execute(
        self,
        *,
        customer_account_id: UUID | None = None,
        auth_realm_id: UUID | None = None,
        source_order_id: UUID | None = None,
        provider_name: str | None = None,
        identity_scope: str | None = None,
        subscription_key: str | None = None,
        identity_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ServiceIdentityModel]:
        return await self._repo.list_service_identities(
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            source_order_id=source_order_id,
            provider_name=provider_name,
            identity_scope=identity_scope,
            subscription_key=subscription_key,
            identity_status=identity_status,
            limit=limit,
            offset=offset,
        )
