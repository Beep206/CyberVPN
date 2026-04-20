from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService, OutboxActorContext
from src.application.services.entitlements_service import EntitlementsService
from src.infrastructure.database.models.entitlement_grant_model import EntitlementGrantModel
from src.infrastructure.database.models.growth_reward_allocation_model import GrowthRewardAllocationModel
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.models.renewal_order_model import RenewalOrderModel
from src.infrastructure.database.repositories.service_access_repo import ServiceAccessRepository


@dataclass(frozen=True)
class CreateEntitlementGrantResult:
    created: bool
    entitlement_grant: EntitlementGrantModel


class CreateEntitlementGrantUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ServiceAccessRepository(session)

    async def execute(
        self,
        *,
        service_identity_id: UUID,
        source_order_id: UUID | None = None,
        source_growth_reward_allocation_id: UUID | None = None,
        source_renewal_order_id: UUID | None = None,
        manual_source_key: str | None = None,
        grant_snapshot: dict[str, Any] | None = None,
        expires_at: datetime | None = None,
        created_by_admin_user_id: UUID | None = None,
    ) -> CreateEntitlementGrantResult:
        service_identity = await self._repo.get_service_identity_by_id(service_identity_id)
        if service_identity is None:
            raise ValueError("Service identity not found")

        source_names = [
            name
            for name, value in (
                ("order", source_order_id),
                ("growth_reward", source_growth_reward_allocation_id),
                ("renewal", source_renewal_order_id),
                ("manual", manual_source_key),
            )
            if value is not None
        ]
        if len(source_names) != 1:
            raise ValueError("Exactly one entitlement provenance source is required")

        existing = await self._get_existing_by_source(
            source_order_id=source_order_id,
            source_growth_reward_allocation_id=source_growth_reward_allocation_id,
            source_renewal_order_id=source_renewal_order_id,
            manual_source_key=manual_source_key,
        )
        if existing is not None:
            return CreateEntitlementGrantResult(created=False, entitlement_grant=existing)

        source_type = source_names[0]
        resolved_snapshot = dict(grant_snapshot or {})
        source_snapshot: dict[str, Any] = {"source_type": source_type}
        origin_storefront_id = service_identity.origin_storefront_id

        if source_order_id is not None:
            order = await self._session.get(OrderModel, source_order_id)
            if order is None:
                raise ValueError("Source order not found")
            if order.user_id != service_identity.customer_account_id:
                raise ValueError("Source order does not belong to service identity customer")
            if order.auth_realm_id != service_identity.auth_realm_id:
                raise ValueError("Source order does not belong to service identity realm")
            origin_storefront_id = order.storefront_id
            source_snapshot.update(
                {
                    "order_id": str(order.id),
                    "order_status": order.order_status,
                    "settlement_status": order.settlement_status,
                }
            )
            if not resolved_snapshot:
                resolved_snapshot = dict(order.entitlements_snapshot or {})
        elif source_growth_reward_allocation_id is not None:
            allocation = await self._session.get(GrowthRewardAllocationModel, source_growth_reward_allocation_id)
            if allocation is None:
                raise ValueError("Source growth reward allocation not found")
            if allocation.beneficiary_user_id != service_identity.customer_account_id:
                raise ValueError("Growth reward allocation does not belong to service identity customer")
            if allocation.auth_realm_id != service_identity.auth_realm_id:
                raise ValueError("Growth reward allocation does not belong to service identity realm")
            origin_storefront_id = allocation.storefront_id or origin_storefront_id
            source_snapshot.update(
                {
                    "growth_reward_allocation_id": str(allocation.id),
                    "reward_type": allocation.reward_type,
                    "allocation_status": allocation.allocation_status,
                }
            )
            if not resolved_snapshot:
                resolved_snapshot = dict(allocation.reward_payload.get("entitlements_snapshot") or {})
        elif source_renewal_order_id is not None:
            renewal_order = await self._session.get(RenewalOrderModel, source_renewal_order_id)
            if renewal_order is None:
                raise ValueError("Source renewal order not found")
            if renewal_order.user_id != service_identity.customer_account_id:
                raise ValueError("Renewal order does not belong to service identity customer")
            if renewal_order.auth_realm_id != service_identity.auth_realm_id:
                raise ValueError("Renewal order does not belong to service identity realm")
            source_order = await self._session.get(OrderModel, renewal_order.order_id)
            origin_storefront_id = renewal_order.storefront_id
            source_snapshot.update(
                {
                    "renewal_order_id": str(renewal_order.id),
                    "renewal_mode": renewal_order.renewal_mode,
                    "renewal_sequence_number": renewal_order.renewal_sequence_number,
                }
            )
            if source_order is not None:
                source_snapshot["renewal_order_settlement_status"] = source_order.settlement_status
                if not resolved_snapshot:
                    resolved_snapshot = dict(source_order.entitlements_snapshot or {})
        else:
            source_snapshot["manual_source_key"] = manual_source_key

        if not resolved_snapshot:
            raise ValueError("Entitlement grant snapshot is required for this source")

        model = EntitlementGrantModel(
            id=uuid.uuid4(),
            grant_key=f"ent_{uuid.uuid4().hex}",
            service_identity_id=service_identity_id,
            customer_account_id=service_identity.customer_account_id,
            auth_realm_id=service_identity.auth_realm_id,
            origin_storefront_id=origin_storefront_id,
            source_type=source_type,
            source_order_id=source_order_id,
            source_growth_reward_allocation_id=source_growth_reward_allocation_id,
            source_renewal_order_id=source_renewal_order_id,
            manual_source_key=manual_source_key,
            grant_status="pending",
            grant_snapshot=resolved_snapshot,
            source_snapshot=source_snapshot,
            expires_at=expires_at,
            created_by_admin_user_id=created_by_admin_user_id,
        )
        created = await self._repo.create_entitlement_grant(model)
        return CreateEntitlementGrantResult(created=True, entitlement_grant=created)

    async def _get_existing_by_source(
        self,
        *,
        source_order_id: UUID | None,
        source_growth_reward_allocation_id: UUID | None,
        source_renewal_order_id: UUID | None,
        manual_source_key: str | None,
    ) -> EntitlementGrantModel | None:
        if source_order_id is not None:
            return await self._repo.get_entitlement_grant_by_source_order_id(source_order_id=source_order_id)
        if source_growth_reward_allocation_id is not None:
            return await self._repo.get_entitlement_grant_by_source_growth_reward_allocation_id(
                source_growth_reward_allocation_id=source_growth_reward_allocation_id
            )
        if source_renewal_order_id is not None:
            return await self._repo.get_entitlement_grant_by_source_renewal_order_id(
                source_renewal_order_id=source_renewal_order_id
            )
        if manual_source_key is not None:
            return await self._repo.get_entitlement_grant_by_manual_source_key(
                manual_source_key=manual_source_key
            )
        return None


class GetEntitlementGrantUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ServiceAccessRepository(session)

    async def execute(self, *, entitlement_grant_id: UUID) -> EntitlementGrantModel | None:
        return await self._repo.get_entitlement_grant_by_id(entitlement_grant_id)


class GetCurrentEntitlementStateUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._entitlements = EntitlementsService(session)

    async def execute(
        self,
        *,
        customer_account_id: UUID,
        auth_realm_id: UUID | None = None,
    ) -> dict[str, Any]:
        return await self._entitlements.get_current_snapshot(
            customer_account_id,
            auth_realm_id=auth_realm_id,
        )


class ListEntitlementGrantsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ServiceAccessRepository(session)

    async def execute(
        self,
        *,
        service_identity_id: UUID | None = None,
        customer_account_id: UUID | None = None,
        auth_realm_id: UUID | None = None,
        source_type: str | None = None,
        grant_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EntitlementGrantModel]:
        return await self._repo.list_entitlement_grants(
            service_identity_id=service_identity_id,
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            source_type=source_type,
            grant_status=grant_status,
            limit=limit,
            offset=offset,
        )


class _TransitionEntitlementGrantUseCase:
    terminal_statuses = frozenset({"revoked", "expired"})

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ServiceAccessRepository(session)
        self._outbox = EventOutboxService(session)

    async def _get_grant(self, entitlement_grant_id: UUID) -> EntitlementGrantModel:
        item = await self._repo.get_entitlement_grant_by_id(entitlement_grant_id)
        if item is None:
            raise ValueError("Entitlement grant not found")
        return item

    async def _validate_source_for_activation(self, item: EntitlementGrantModel) -> None:
        if item.source_order_id is not None:
            order = await self._session.get(OrderModel, item.source_order_id)
            if order is None:
                raise ValueError("Source order not found")
            if order.settlement_status != "paid":
                raise ValueError("Source order is not payout-settled")
            return
        if item.source_renewal_order_id is not None:
            renewal_order = await self._session.get(RenewalOrderModel, item.source_renewal_order_id)
            if renewal_order is None:
                raise ValueError("Source renewal order not found")
            order = await self._session.get(OrderModel, renewal_order.order_id)
            if order is None:
                raise ValueError("Linked renewal order record not found")
            if order.settlement_status != "paid":
                raise ValueError("Source renewal order is not payout-settled")
            return
        if item.source_growth_reward_allocation_id is not None:
            allocation = await self._session.get(
                GrowthRewardAllocationModel,
                item.source_growth_reward_allocation_id,
            )
            if allocation is None:
                raise ValueError("Source growth reward allocation not found")
            if allocation.allocation_status != "allocated":
                raise ValueError("Source growth reward allocation is not active")


class ActivateEntitlementGrantUseCase(_TransitionEntitlementGrantUseCase):
    async def execute(
        self,
        *,
        entitlement_grant_id: UUID,
        activated_by_admin_user_id: UUID | None,
    ) -> EntitlementGrantModel:
        item = await self._get_grant(entitlement_grant_id)
        if item.grant_status == "active":
            return item
        if item.grant_status in self.terminal_statuses:
            raise ValueError("Terminal entitlement grants cannot be reactivated")

        await self._validate_source_for_activation(item)
        now = datetime.now(UTC)
        item.grant_status = "active"
        item.effective_from = item.effective_from or now
        item.activated_at = now
        item.activated_by_admin_user_id = activated_by_admin_user_id
        item.suspended_at = None
        item.suspended_by_admin_user_id = None
        item.suspension_reason_code = None
        await self._outbox.append_event(
            event_name="entitlement.grant.activated",
            aggregate_type="entitlement_grant",
            aggregate_id=str(item.id),
            partition_key=str(item.customer_account_id),
            event_payload={
                "entitlement_grant_id": str(item.id),
                "service_identity_id": str(item.service_identity_id),
                "customer_account_id": str(item.customer_account_id),
                "auth_realm_id": str(item.auth_realm_id),
                "source_type": item.source_type,
                "grant_status": item.grant_status,
            },
            actor_context=OutboxActorContext(
                principal_type="admin" if activated_by_admin_user_id is not None else None,
                principal_id=str(activated_by_admin_user_id) if activated_by_admin_user_id is not None else None,
                auth_realm_id=str(item.auth_realm_id),
            ),
            source_context={"source_use_case": "ActivateEntitlementGrantUseCase"},
        )
        await self._session.flush()
        return item


class SuspendEntitlementGrantUseCase(_TransitionEntitlementGrantUseCase):
    async def execute(
        self,
        *,
        entitlement_grant_id: UUID,
        suspended_by_admin_user_id: UUID | None,
        reason_code: str | None,
    ) -> EntitlementGrantModel:
        item = await self._get_grant(entitlement_grant_id)
        if item.grant_status == "suspended":
            return item
        if item.grant_status in self.terminal_statuses:
            raise ValueError("Terminal entitlement grants cannot be suspended")

        item.grant_status = "suspended"
        item.suspended_at = datetime.now(UTC)
        item.suspended_by_admin_user_id = suspended_by_admin_user_id
        item.suspension_reason_code = reason_code
        await self._session.flush()
        return item


class RevokeEntitlementGrantUseCase(_TransitionEntitlementGrantUseCase):
    async def execute(
        self,
        *,
        entitlement_grant_id: UUID,
        revoked_by_admin_user_id: UUID | None,
        reason_code: str | None,
    ) -> EntitlementGrantModel:
        item = await self._get_grant(entitlement_grant_id)
        if item.grant_status == "revoked":
            return item
        if item.grant_status == "expired":
            raise ValueError("Expired entitlement grants cannot be revoked")

        item.grant_status = "revoked"
        item.revoked_at = datetime.now(UTC)
        item.revoked_by_admin_user_id = revoked_by_admin_user_id
        item.revoke_reason_code = reason_code
        await self._outbox.append_event(
            event_name="entitlement.grant.revoked",
            aggregate_type="entitlement_grant",
            aggregate_id=str(item.id),
            partition_key=str(item.customer_account_id),
            event_payload={
                "entitlement_grant_id": str(item.id),
                "service_identity_id": str(item.service_identity_id),
                "customer_account_id": str(item.customer_account_id),
                "auth_realm_id": str(item.auth_realm_id),
                "source_type": item.source_type,
                "grant_status": item.grant_status,
                "reason_code": reason_code,
            },
            actor_context=OutboxActorContext(
                principal_type="admin" if revoked_by_admin_user_id is not None else None,
                principal_id=str(revoked_by_admin_user_id) if revoked_by_admin_user_id is not None else None,
                auth_realm_id=str(item.auth_realm_id),
            ),
            source_context={"source_use_case": "RevokeEntitlementGrantUseCase"},
        )
        await self._session.flush()
        return item


class ExpireEntitlementGrantUseCase(_TransitionEntitlementGrantUseCase):
    async def execute(
        self,
        *,
        entitlement_grant_id: UUID,
        expired_by_admin_user_id: UUID | None,
        reason_code: str | None,
    ) -> EntitlementGrantModel:
        item = await self._get_grant(entitlement_grant_id)
        if item.grant_status == "expired":
            return item
        if item.grant_status == "revoked":
            raise ValueError("Revoked entitlement grants cannot be expired")

        now = datetime.now(UTC)
        item.grant_status = "expired"
        item.expired_at = now
        item.expired_by_admin_user_id = expired_by_admin_user_id
        item.expiry_reason_code = reason_code
        if item.expires_at is None:
            item.expires_at = now
        await self._session.flush()
        return item
