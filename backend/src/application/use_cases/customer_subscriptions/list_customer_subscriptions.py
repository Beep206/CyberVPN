from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.entitlements_service import EntitlementsService
from src.infrastructure.database.models.entitlement_grant_model import EntitlementGrantModel
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.service_access_repo import ServiceAccessRepository
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository

CustomerSubscriptionKind = Literal["entitlement_grant", "trial", "legacy_payment"]
CustomerSubscriptionManagementScope = Literal["subscription_entitlement", "account_vpn_identity"]


@dataclass(frozen=True)
class CustomerSubscriptionSummary:
    subscription_key: str
    kind: CustomerSubscriptionKind
    status: str
    display_name: str | None
    plan_uuid: str | None
    plan_code: str | None
    source_type: str | None
    source_order_id: UUID | None
    entitlement_grant_id: UUID | None
    service_identity_id: UUID | None
    provider_name: str | None
    expires_at: str | None
    created_at: datetime | None
    effective_entitlements: dict[str, Any]
    invite_bundle: dict[str, int]
    is_trial: bool
    addons: list[dict[str, Any]]
    can_manage: bool
    can_deliver_config: bool
    management_scope: CustomerSubscriptionManagementScope


@dataclass(frozen=True)
class CustomerSubscriptionListResult:
    customer_account_id: UUID
    auth_realm_id: UUID
    selected_subscription_key: str | None
    default_subscription_key: str | None
    items: list[CustomerSubscriptionSummary]
    limitations: list[str] = field(default_factory=list)


class ListCustomerSubscriptionsUseCase:
    """Build a customer-safe subscription read model.

    The existing VPN service identity contract is still account/provider-level
    for most production users. This read model exposes subscription-level
    entitlements now while making that limitation explicit for the frontend.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._entitlements = EntitlementsService(session)
        self._service_access = ServiceAccessRepository(session)
        self._payments = PaymentRepository(session)
        self._plans = SubscriptionPlanRepository(session)
        self._users = MobileUserRepository(session)

    async def execute(
        self,
        *,
        customer_account_id: UUID,
        auth_realm_id: UUID,
        selected_subscription_key: str | None = None,
    ) -> CustomerSubscriptionListResult:
        now = datetime.now(UTC)
        items: list[CustomerSubscriptionSummary] = []
        limitations: list[str] = []

        grants = await self._service_access.list_entitlement_grants(
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            limit=100,
            offset=0,
        )
        for grant in grants:
            items.append(await self._summary_from_grant(grant, now=now))

        if not items:
            legacy = await self._summary_from_legacy_payment(customer_account_id, now=now)
            if legacy is not None:
                items.append(legacy)

        trial = await self._summary_from_trial(customer_account_id, now=now)
        if trial is not None and not any(item.kind == "trial" for item in items):
            items.append(trial)

        if any(item.management_scope == "account_vpn_identity" for item in items):
            limitations.append(
                "VPN service identity is currently account-scoped. Per-subscription VPN identities require MSUB-08."
            )

        default_key = self._default_subscription_key(items)
        available_keys = {item.subscription_key for item in items}
        selected_key = selected_subscription_key if selected_subscription_key in available_keys else default_key

        return CustomerSubscriptionListResult(
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            selected_subscription_key=selected_key,
            default_subscription_key=default_key,
            items=items,
            limitations=limitations,
        )

    async def get_by_key(
        self,
        *,
        customer_account_id: UUID,
        auth_realm_id: UUID,
        subscription_key: str,
    ) -> CustomerSubscriptionSummary | None:
        result = await self.execute(
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            selected_subscription_key=subscription_key,
        )
        for item in result.items:
            if item.subscription_key == subscription_key:
                return item
        return None

    async def _summary_from_grant(
        self,
        grant: EntitlementGrantModel,
        *,
        now: datetime,
    ) -> CustomerSubscriptionSummary:
        service_identity = await self._service_access.get_service_identity_by_id(grant.service_identity_id)
        snapshot = self._entitlements.normalize_grant_snapshot(
            grant_snapshot=dict(grant.grant_snapshot or {}),
            expires_at=grant.expires_at,
        )
        status = str(grant.grant_status)
        if status == "active" and grant.expires_at is not None:
            expires_at = self._entitlements._to_utc_datetime(grant.expires_at)
            if expires_at is not None and expires_at <= now:
                status = "expired"

        can_deliver = (
            status == "active"
            and service_identity is not None
            and service_identity.identity_status == "active"
        )
        return CustomerSubscriptionSummary(
            subscription_key=f"grant:{grant.id}",
            kind="entitlement_grant",
            status=status,
            display_name=snapshot.get("display_name"),
            plan_uuid=snapshot.get("plan_uuid"),
            plan_code=snapshot.get("plan_code"),
            source_type=grant.source_type,
            source_order_id=grant.source_order_id,
            entitlement_grant_id=grant.id,
            service_identity_id=grant.service_identity_id,
            provider_name=service_identity.provider_name if service_identity is not None else None,
            expires_at=snapshot.get("expires_at"),
            created_at=grant.created_at,
            effective_entitlements=dict(snapshot.get("effective_entitlements") or {}),
            invite_bundle=dict(snapshot.get("invite_bundle") or {}),
            is_trial=bool(snapshot.get("is_trial", False)),
            addons=list(snapshot.get("addons") or []),
            can_manage=status not in {"revoked"},
            can_deliver_config=can_deliver,
            management_scope="account_vpn_identity",
        )

    async def _summary_from_legacy_payment(
        self,
        customer_account_id: UUID,
        *,
        now: datetime,
    ) -> CustomerSubscriptionSummary | None:
        payment = await self._payments.get_latest_active_plan_payment(customer_account_id, at=now)
        if payment is None or payment.plan_id is None:
            return None

        plan = await self._plans.get_by_id(payment.plan_id)
        if plan is None:
            return None

        addon_lines = await self._entitlements.list_active_addon_lines(customer_account_id)
        expires_at = self._entitlements._to_utc_datetime(payment.created_at)
        if expires_at is not None and payment.subscription_days > 0:
            expires_at = expires_at + timedelta(days=payment.subscription_days)
        elif payment.subscription_days <= 0:
            expires_at = None
        snapshot = self._entitlements.build_snapshot(plan=plan, addon_lines=addon_lines, expires_at=expires_at)
        status = "active" if expires_at is None or expires_at > now else "expired"

        return CustomerSubscriptionSummary(
            subscription_key=f"legacy-payment:{payment.id}",
            kind="legacy_payment",
            status=status,
            display_name=snapshot.get("display_name"),
            plan_uuid=snapshot.get("plan_uuid"),
            plan_code=snapshot.get("plan_code"),
            source_type="legacy_payment",
            source_order_id=None,
            entitlement_grant_id=None,
            service_identity_id=None,
            provider_name=None,
            expires_at=snapshot.get("expires_at"),
            created_at=payment.created_at,
            effective_entitlements=dict(snapshot.get("effective_entitlements") or {}),
            invite_bundle=dict(snapshot.get("invite_bundle") or {}),
            is_trial=False,
            addons=list(snapshot.get("addons") or []),
            can_manage=status == "active",
            can_deliver_config=False,
            management_scope="subscription_entitlement",
        )

    async def _summary_from_trial(
        self,
        customer_account_id: UUID,
        *,
        now: datetime,
    ) -> CustomerSubscriptionSummary | None:
        user = await self._users.get_by_id(customer_account_id)
        trial_expires_at = self._entitlements._to_utc_datetime(user.trial_expires_at) if user else None
        if user is None or trial_expires_at is None or trial_expires_at <= now:
            return None

        snapshot = self._entitlements.build_trial_snapshot(expires_at=trial_expires_at)
        return CustomerSubscriptionSummary(
            subscription_key=f"trial:{customer_account_id}",
            kind="trial",
            status="trial",
            display_name=snapshot.get("display_name"),
            plan_uuid=snapshot.get("plan_uuid"),
            plan_code=snapshot.get("plan_code"),
            source_type="trial",
            source_order_id=None,
            entitlement_grant_id=None,
            service_identity_id=None,
            provider_name=None,
            expires_at=snapshot.get("expires_at"),
            created_at=user.created_at,
            effective_entitlements=dict(snapshot.get("effective_entitlements") or {}),
            invite_bundle=dict(snapshot.get("invite_bundle") or {}),
            is_trial=True,
            addons=[],
            can_manage=True,
            can_deliver_config=False,
            management_scope="subscription_entitlement",
        )

    @staticmethod
    def _default_subscription_key(items: list[CustomerSubscriptionSummary]) -> str | None:
        active_items = [item for item in items if item.status in {"active", "trial"}]
        if active_items:
            return active_items[0].subscription_key
        return items[0].subscription_key if items else None


class GetCustomerSubscriptionEntitlementsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._subscriptions = ListCustomerSubscriptionsUseCase(session)

    async def execute(
        self,
        *,
        customer_account_id: UUID,
        auth_realm_id: UUID,
        subscription_key: str,
    ) -> dict[str, Any] | None:
        item = await self._subscriptions.get_by_key(
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            subscription_key=subscription_key,
        )
        if item is None:
            return None
        return {
            "status": item.status,
            "plan_uuid": item.plan_uuid,
            "plan_code": item.plan_code,
            "display_name": item.display_name,
            "period_days": None,
            "expires_at": item.expires_at,
            "effective_entitlements": item.effective_entitlements,
            "invite_bundle": item.invite_bundle,
            "is_trial": item.is_trial,
            "addons": item.addons,
        }
