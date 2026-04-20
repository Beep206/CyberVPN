from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.models.service_identity_model import ServiceIdentityModel
from src.infrastructure.database.repositories.service_access_repo import ServiceAccessRepository


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
        service_context: dict[str, Any] | None = None,
    ) -> CreateServiceIdentityResult:
        customer = await self._session.get(MobileUserModel, customer_account_id)
        if customer is None:
            raise ValueError("Customer account not found")

        realm = await self._session.get(AuthRealmModel, auth_realm_id)
        if realm is None:
            raise ValueError("Auth realm not found")

        if customer.auth_realm_id and customer.auth_realm_id != auth_realm_id:
            raise ValueError("Customer account does not belong to auth realm")

        existing = await self._repo.get_service_identity_by_customer_realm_provider(
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            provider_name=provider_name,
        )
        if existing is not None:
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

        model = ServiceIdentityModel(
            id=uuid.uuid4(),
            service_key=f"svc_{uuid.uuid4().hex}",
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            source_order_id=source_order_id,
            origin_storefront_id=resolved_origin_storefront_id,
            provider_name=provider_name,
            provider_subject_ref=provider_subject_ref or customer.remnawave_uuid,
            identity_status="active",
            service_context=merged_context,
        )
        created = await self._repo.create_service_identity(model)
        return CreateServiceIdentityResult(created=True, service_identity=created)


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
        identity_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ServiceIdentityModel]:
        return await self._repo.list_service_identities(
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            source_order_id=source_order_id,
            provider_name=provider_name,
            identity_status=identity_status,
            limit=limit,
            offset=offset,
        )
