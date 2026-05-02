from __future__ import annotations

import secrets
import string
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from time import perf_counter
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService, OutboxActorContext
from src.application.services.entitlements_service import EntitlementsService
from src.application.use_cases.commerce_sessions.context_resolution import ResolveQuoteContextUseCase
from src.application.use_cases.growth_notifications.catalog import gift_issued_notification_key
from src.application.use_cases.growth_notifications.fanout import PlanCustomerGrowthNotificationFanoutUseCase
from src.application.use_cases.payments.checkout import CheckoutUseCase
from src.application.use_cases.service_access.entitlements import (
    ActivateEntitlementGrantUseCase,
    CreateEntitlementGrantUseCase,
    GetCurrentEntitlementStateUseCase,
)
from src.application.use_cases.service_access.service_identities import CreateServiceIdentityUseCase
from src.infrastructure.database.models.growth_code_model import (
    GiftCodePolicyModel,
    GrowthCodeIssuanceModel,
    GrowthCodeModel,
    GrowthCodeRedemptionModel,
)
from src.infrastructure.database.repositories.growth_code_repo import GrowthCodeRepository
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository
from src.infrastructure.monitoring.instrumentation.growth_codes import (
    ADMIN_GROWTH_SURFACE,
    CUSTOMER_REDEEM_SURFACE,
    GROWTH_WORKER_SURFACE,
    log_growth_code_event,
    observe_gift_redemption_failure,
    observe_growth_code_issue,
    observe_growth_code_redemption,
    observe_growth_code_redemption_duration,
)
from src.presentation.dependencies.auth_realms import RealmResolution

from ..growth_codes.hashing import build_growth_code_prefix, hash_growth_code

if TYPE_CHECKING:
    from src.application.use_cases.payments.commit_checkout import CommitCheckoutResult


@dataclass(frozen=True)
class IssuedGiftCode:
    growth_code: GrowthCodeModel
    policy: GiftCodePolicyModel
    issuance: GrowthCodeIssuanceModel
    raw_code: str


@dataclass(frozen=True)
class GiftPurchaseQuoteResult:
    resolved_context: object
    checkout_result: object


@dataclass(frozen=True)
class GiftPurchaseCommitResult:
    quote_result: object
    commit_result: CommitCheckoutResult
    issued_gift: IssuedGiftCode | None


@dataclass(frozen=True)
class IssuedGiftBatchResult:
    batch_id: UUID
    items: list[IssuedGiftCode]


@dataclass(frozen=True)
class RedeemedGiftCodeResult:
    growth_code: GrowthCodeModel
    policy: GiftCodePolicyModel
    redemption: GrowthCodeRedemptionModel
    entitlement_grant_id: UUID
    entitlement_snapshot: dict


class IssueGiftCodeUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._plans = SubscriptionPlanRepository(session)
        self._codes = GrowthCodeRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        owner_user_id: UUID | None = None,
        owner_partner_account_id: UUID | None = None,
        plan_id: UUID,
        issuer_type: str,
        issuance_type: str,
        recipient_hint: str | None = None,
        gift_message: str | None = None,
        source_payment_id: UUID | None = None,
        source_order_id: UUID | None = None,
        issued_by_admin_id: UUID | None = None,
        storefront_id: UUID | None = None,
        auth_realm_id: UUID | None = None,
        batch_id: UUID | None = None,
        reason_code: str | None = None,
        admin_note: str | None = None,
    ) -> IssuedGiftCode:
        if owner_user_id is None and owner_partner_account_id is None:
            raise ValueError("Gift issuance requires a user or partner owner")
        if owner_user_id is not None and owner_partner_account_id is not None:
            raise ValueError("Gift issuance cannot target both a user and a partner owner")

        existing = None
        if source_payment_id is not None:
            existing = await self._codes.find_code_by_source_payment_id(
                source_payment_id=source_payment_id,
                code_type="gift",
            )
        if existing is not None:
            policy = await self._codes.get_gift_policy(existing.id)
            issuance_items = await self._codes.list_issuances(existing.id)
            if policy is None or not issuance_items:
                raise ValueError("Existing gift code is missing canonical policy state")
            return IssuedGiftCode(
                growth_code=existing,
                policy=policy,
                issuance=issuance_items[0],
                raw_code=issuance_items[0].raw_code_encrypted or "",
            )

        plan = await self._plans.get_by_id(plan_id)
        if plan is None:
            raise ValueError("Gift plan not found")

        raw_code = await self._generate_unique_code()
        snapshot = EntitlementsService.build_snapshot(plan=plan, expires_at=None, status="active")
        now = datetime.now(UTC)

        growth_code = await self._codes.create_code(
            GrowthCodeModel(
                id=uuid.uuid4(),
                code_hash=hash_growth_code(raw_code),
                code_prefix=build_growth_code_prefix(raw_code),
                code_type="gift",
                status="active",
                issuer_type=issuer_type,
                issuer_admin_id=issued_by_admin_id,
                owner_user_id=owner_user_id,
                owner_partner_account_id=owner_partner_account_id,
                batch_id=batch_id,
                storefront_id=storefront_id,
                auth_realm_id=auth_realm_id,
                starts_at=now,
                expires_at=now + timedelta(days=365),
                max_uses=1,
            )
        )
        policy = await self._codes.create_gift_policy(
            GiftCodePolicyModel(
                growth_code_id=growth_code.id,
                grant_type="subscription_entitlement",
                plan_family=plan.plan_code,
                duration_days=plan.duration_days,
                entitlement_snapshot=snapshot,
                redemption_mode="redeem",
                transferable=True,
                batch_id=batch_id,
                policy_snapshot={
                    "recipient_hint": recipient_hint,
                    "gift_message": gift_message,
                    "plan_display_name": plan.display_name or plan.name,
                    "plan_name": plan.name,
                },
            )
        )
        issuance = await self._codes.create_issuance(
            GrowthCodeIssuanceModel(
                growth_code_id=growth_code.id,
                issuance_type=issuance_type,
                issued_to_user_id=owner_user_id,
                issued_to_partner_account_id=owner_partner_account_id,
                issued_by_admin_id=issued_by_admin_id,
                raw_code_encrypted=raw_code,
                source_order_id=source_order_id,
                source_payment_id=source_payment_id,
                source_plan_sku=f"{plan.plan_code}_{plan.duration_days}",
                source_bundle_snapshot={
                    "recipient_hint": recipient_hint,
                    "gift_message": gift_message,
                    "plan_display_name": plan.display_name or plan.name,
                    "duration_days": plan.duration_days,
                },
                reason_code=reason_code,
                admin_note=admin_note,
            )
        )
        await self._outbox.append_event(
            event_name="growth_code.issued",
            aggregate_type="growth_code",
            aggregate_id=str(growth_code.id),
            partition_key=str(growth_code.batch_id or growth_code.id),
            event_payload={
                "growth_code_id": str(growth_code.id),
                "batch_id": str(growth_code.batch_id) if growth_code.batch_id else None,
                "code_type": growth_code.code_type,
                "issuer_type": growth_code.issuer_type,
                "issuance_type": issuance.issuance_type,
                "owner_user_id": str(growth_code.owner_user_id) if growth_code.owner_user_id else None,
                "owner_partner_account_id": (
                    str(growth_code.owner_partner_account_id) if growth_code.owner_partner_account_id else None
                ),
            },
            actor_context=OutboxActorContext(
                principal_type="admin" if issued_by_admin_id else "customer" if owner_user_id else "partner",
                principal_id=(
                    str(issued_by_admin_id)
                    if issued_by_admin_id
                    else str(owner_user_id)
                    if owner_user_id
                    else str(owner_partner_account_id)
                    if owner_partner_account_id
                    else None
                ),
                auth_realm_id=str(auth_realm_id) if auth_realm_id else None,
            ),
            source_context={"source_use_case": "IssueGiftCodeUseCase.execute"},
        )
        await self._outbox.append_event(
            event_name="gift.issued",
            aggregate_type="growth_code",
            aggregate_id=str(growth_code.id),
            partition_key=str(growth_code.batch_id or growth_code.id),
            event_payload={
                "growth_code_id": str(growth_code.id),
                "issuance_type": issuance.issuance_type,
                "plan_family": policy.plan_family,
                "duration_days": policy.duration_days,
                "batch_id": str(growth_code.batch_id) if growth_code.batch_id else None,
            },
            actor_context=OutboxActorContext(
                principal_type="admin" if issued_by_admin_id else "customer" if owner_user_id else "partner",
                principal_id=(
                    str(issued_by_admin_id)
                    if issued_by_admin_id
                    else str(owner_user_id)
                    if owner_user_id
                    else str(owner_partner_account_id)
                    if owner_partner_account_id
                    else None
                ),
                auth_realm_id=str(auth_realm_id) if auth_realm_id else None,
            ),
            source_context={"source_use_case": "IssueGiftCodeUseCase.execute"},
        )
        observe_growth_code_issue(
            code_type=growth_code.code_type,
            issuer_type=growth_code.issuer_type,
            surface=ADMIN_GROWTH_SURFACE if issued_by_admin_id else GROWTH_WORKER_SURFACE,
            result="success",
            source_type=issuance.issuance_type,
        )
        log_growth_code_event(
            "gift.issued",
            surface=ADMIN_GROWTH_SURFACE if issued_by_admin_id else GROWTH_WORKER_SURFACE,
            code_type=growth_code.code_type,
            result="success",
            growth_code_id=str(growth_code.id),
            batch_id=str(growth_code.batch_id) if growth_code.batch_id else None,
            owner_user_id=str(growth_code.owner_user_id) if growth_code.owner_user_id else None,
        )
        if growth_code.owner_user_id is not None:
            notification_kind = (
                "gift_purchased"
                if issuance.issuance_type == "gift_purchase"
                else "gift_available"
            )
            notification_title = (
                "Gift purchase completed"
                if notification_kind == "gift_purchased"
                else "Gift code available"
            )
            notification_message = (
                f"Your {policy.plan_family} gift for {policy.duration_days} days is ready to share."
                if notification_kind == "gift_purchased"
                else f"A {policy.plan_family} gift for {policy.duration_days} days was issued to your account."
            )
            notification_notes = []
            if recipient_hint:
                notification_notes.append(f"Recipient: {recipient_hint}.")
            if growth_code.expires_at is not None:
                notification_notes.append(f"Expires {growth_code.expires_at.date().isoformat()}.")
            await PlanCustomerGrowthNotificationFanoutUseCase(self._session).execute(
                mobile_user_id=growth_code.owner_user_id,
                notification_key=gift_issued_notification_key(growth_code.id),
                notification_kind=notification_kind,
                title=notification_title,
                message=notification_message,
                route_slug="/referral",
                notes=notification_notes,
                source_kind="gift_code",
                source_id=str(growth_code.id),
                created_by_admin_user_id=issued_by_admin_id,
            )
        return IssuedGiftCode(growth_code=growth_code, policy=policy, issuance=issuance, raw_code=raw_code)

    async def execute_batch(
        self,
        *,
        owner_user_id: UUID | None = None,
        owner_partner_account_id: UUID | None = None,
        plan_id: UUID,
        count: int,
        issuer_type: str,
        issuance_type: str,
        recipient_hint: str | None = None,
        gift_message: str | None = None,
        issued_by_admin_id: UUID | None = None,
        storefront_id: UUID | None = None,
        auth_realm_id: UUID | None = None,
        reason_code: str | None = None,
        admin_note: str | None = None,
    ) -> IssuedGiftBatchResult:
        if count < 1:
            raise ValueError("Gift batch count must be at least 1")

        batch_id = uuid.uuid4()
        items: list[IssuedGiftCode] = []
        for _ in range(count):
            items.append(
                await self.execute(
                    owner_user_id=owner_user_id,
                    owner_partner_account_id=owner_partner_account_id,
                    plan_id=plan_id,
                    issuer_type=issuer_type,
                    issuance_type=issuance_type,
                    recipient_hint=recipient_hint,
                    gift_message=gift_message,
                    issued_by_admin_id=issued_by_admin_id,
                    storefront_id=storefront_id,
                    auth_realm_id=auth_realm_id,
                    batch_id=batch_id,
                    reason_code=reason_code,
                    admin_note=admin_note,
                )
            )
        return IssuedGiftBatchResult(batch_id=batch_id, items=items)

    async def _generate_unique_code(self) -> str:
        alphabet = string.ascii_uppercase + string.digits
        for _ in range(10):
            raw_code = "".join(secrets.choice(alphabet) for _ in range(12))
            existing = await self._codes.get_code_by_hash(hash_growth_code(raw_code), code_type="gift")
            if existing is None:
                return raw_code
        raise ValueError("Failed to allocate a unique gift code")


class QuoteGiftPurchaseUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._resolver = ResolveQuoteContextUseCase(session)
        self._checkout = CheckoutUseCase(session)

    async def execute(
        self,
        *,
        user_id: UUID,
        current_realm: RealmResolution,
        storefront_key: str | None,
        host: str | None,
        plan_id: UUID,
        use_wallet: Decimal,
        currency: str,
        channel: str,
    ) -> GiftPurchaseQuoteResult:
        resolved_context = await self._resolver.execute(
            current_realm=current_realm,
            storefront_key=storefront_key,
            host=host,
            subscription_plan_id=plan_id,
            pricebook_key=None,
            offer_key=None,
            currency_code=currency,
            sale_channel=channel,
        )
        if not resolved_context.offer.gift_eligible:
            raise ValueError("Selected plan is not gift eligible")
        checkout_result = await self._checkout.execute(
            user_id=user_id,
            plan_id=plan_id,
            use_wallet=use_wallet,
            storefront_id=resolved_context.storefront.id,
            sale_channel=channel,
            addons=[],
        )
        return GiftPurchaseQuoteResult(resolved_context=resolved_context, checkout_result=checkout_result)


class CommitGiftPurchaseUseCase:
    def __init__(self, session: AsyncSession, crypto_client) -> None:
        from src.application.use_cases.payments.commit_checkout import CommitCheckoutUseCase

        self._session = session
        self._commit = CommitCheckoutUseCase(session, crypto_client)
        self._issue = IssueGiftCodeUseCase(session)
        self._codes = GrowthCodeRepository(session)

    async def execute(
        self,
        *,
        user_id: UUID,
        plan_id: UUID,
        quote_result,
        currency: str,
        channel: str,
        recipient_hint: str | None,
        gift_message: str | None,
        storefront_id: UUID | None = None,
        auth_realm_id: UUID | None = None,
    ) -> GiftPurchaseCommitResult:
        commit_result = await self._commit.execute(
            user_id=user_id,
            quote_result=quote_result,
            currency=currency,
            channel=channel,
            description=f"CyberVPN gift - {quote_result.plan_name or 'plan'}",
            payload=f"gift:{user_id}:{plan_id}",
            checkout_mode="gift_purchase",
            payment_plan_id=plan_id,
            metadata_extra={
                "gift_recipient_hint": recipient_hint,
                "gift_message": gift_message,
                "gift_storefront_id": str(storefront_id) if storefront_id is not None else None,
                "gift_auth_realm_id": str(auth_realm_id) if auth_realm_id is not None else None,
            },
        )
        issued_gift = None
        if commit_result.status == "completed":
            gift_code = await self._codes.find_code_by_source_payment_id(
                source_payment_id=commit_result.payment.id,
                code_type="gift",
            )
            if gift_code is not None:
                policy = await self._codes.get_gift_policy(gift_code.id)
                issuance_items = await self._codes.list_issuances(gift_code.id)
                if policy is not None and issuance_items:
                    issued_gift = IssuedGiftCode(
                        growth_code=gift_code,
                        policy=policy,
                        issuance=issuance_items[0],
                        raw_code=issuance_items[0].raw_code_encrypted or "",
                    )
        return GiftPurchaseCommitResult(
            quote_result=quote_result,
            commit_result=commit_result,
            issued_gift=issued_gift,
        )


class ListGiftCodesUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._codes = GrowthCodeRepository(session)

    async def execute(
        self,
        *,
        owner_user_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[
        tuple[
            GrowthCodeModel,
            GiftCodePolicyModel | None,
            GrowthCodeIssuanceModel | None,
            GrowthCodeRedemptionModel | None,
        ]
    ]:
        codes = await self._codes.list_codes(
            code_type="gift",
            owner_user_id=owner_user_id,
            limit=limit,
            offset=offset,
        )
        items = []
        for code in codes:
            policy = await self._codes.get_gift_policy(code.id)
            issuances = await self._codes.list_issuances(code.id)
            redemptions = await self._codes.list_redemptions(code.id)
            issuance = issuances[0] if issuances else None
            redemption = redemptions[0] if redemptions else None
            items.append((code, policy, issuance, redemption))
        return items


class RedeemGiftCodeUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._codes = GrowthCodeRepository(session)
        self._service_identities = CreateServiceIdentityUseCase(session)
        self._entitlements = CreateEntitlementGrantUseCase(session)
        self._activate_entitlement = ActivateEntitlementGrantUseCase(session)
        self._current_entitlements = GetCurrentEntitlementStateUseCase(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        code: str,
        user_id: UUID,
        current_realm: RealmResolution,
    ) -> RedeemedGiftCodeResult:
        started_at = perf_counter()
        result_label = "failure"
        growth_code = await self._codes.get_code_by_hash(hash_growth_code(code), code_type="gift")
        if growth_code is None:
            observe_gift_redemption_failure(
                surface=CUSTOMER_REDEEM_SURFACE,
                reason_code="code_not_found",
            )
            observe_growth_code_redemption_duration(
                code_type="gift",
                surface=CUSTOMER_REDEEM_SURFACE,
                result=result_label,
                duration_seconds=perf_counter() - started_at,
            )
            raise ValueError("Gift code not found")
        policy = await self._codes.get_gift_policy(growth_code.id)
        if policy is None:
            observe_gift_redemption_failure(
                surface=CUSTOMER_REDEEM_SURFACE,
                reason_code="code_not_active",
            )
            observe_growth_code_redemption_duration(
                code_type="gift",
                surface=CUSTOMER_REDEEM_SURFACE,
                result=result_label,
                duration_seconds=perf_counter() - started_at,
            )
            raise ValueError("Gift code policy not found")
        if growth_code.status == "redeemed" or growth_code.uses_count >= int(growth_code.max_uses or 1):
            observe_gift_redemption_failure(
                surface=CUSTOMER_REDEEM_SURFACE,
                reason_code="gift_already_redeemed",
            )
            observe_growth_code_redemption_duration(
                code_type="gift",
                surface=CUSTOMER_REDEEM_SURFACE,
                result=result_label,
                duration_seconds=perf_counter() - started_at,
            )
            raise ValueError("Gift code already redeemed")
        if growth_code.expires_at is not None and _normalize_utc(growth_code.expires_at) <= datetime.now(UTC):
            observe_gift_redemption_failure(
                surface=CUSTOMER_REDEEM_SURFACE,
                reason_code="code_expired",
            )
            observe_growth_code_redemption_duration(
                code_type="gift",
                surface=CUSTOMER_REDEEM_SURFACE,
                result=result_label,
                duration_seconds=perf_counter() - started_at,
            )
            raise ValueError("Gift code expired")

        current_snapshot = await self._current_entitlements.execute(
            customer_account_id=user_id,
            auth_realm_id=UUID(current_realm.realm_id),
        )
        if current_snapshot.get("status") not in {None, "none"}:
            observe_gift_redemption_failure(
                surface=CUSTOMER_REDEEM_SURFACE,
                reason_code="code_not_eligible_for_surface",
            )
            observe_growth_code_redemption_duration(
                code_type="gift",
                surface=CUSTOMER_REDEEM_SURFACE,
                result=result_label,
                duration_seconds=perf_counter() - started_at,
            )
            raise ValueError("Gift redemption for accounts with active access is not supported yet")

        service_identity = await self._service_identities.execute(
            customer_account_id=user_id,
            auth_realm_id=UUID(current_realm.realm_id),
            provider_name="remnawave",
            origin_storefront_id=growth_code.storefront_id,
        )
        expires_at = datetime.now(UTC) + timedelta(days=int(policy.duration_days or 0))
        grant = await self._entitlements.execute(
            service_identity_id=service_identity.service_identity.id,
            manual_source_key=f"gift:{growth_code.id}:redeemer:{user_id}",
            grant_snapshot=dict(policy.entitlement_snapshot or {}),
            expires_at=expires_at,
        )
        activated = await self._activate_entitlement.execute(
            entitlement_grant_id=grant.entitlement_grant.id,
            activated_by_admin_user_id=None,
        )

        redemption = await self._codes.create_redemption(
            GrowthCodeRedemptionModel(
                growth_code_id=growth_code.id,
                code_type="gift",
                redeemer_user_id=user_id,
                beneficiary_user_id=user_id,
                entitlement_grant_id=activated.id,
                status="redeemed",
                redeemed_at=datetime.now(UTC),
                policy_version_id=growth_code.policy_version_id,
            )
        )
        growth_code.status = "redeemed"
        growth_code.uses_count = int(growth_code.uses_count or 0) + 1
        await self._session.flush()
        await self._outbox.append_event(
            event_name="growth_code.redeemed",
            aggregate_type="growth_code",
            aggregate_id=str(growth_code.id),
            partition_key=str(growth_code.id),
            event_payload={
                "growth_code_id": str(growth_code.id),
                "code_type": growth_code.code_type,
                "redeemer_user_id": str(user_id),
                "redemption_id": str(redemption.id),
                "entitlement_grant_id": str(activated.id),
            },
            actor_context=OutboxActorContext(
                principal_type="customer",
                principal_id=str(user_id),
                auth_realm_id=str(current_realm.realm_id),
            ),
            source_context={"source_use_case": "RedeemGiftCodeUseCase.execute"},
        )
        await self._outbox.append_event(
            event_name="gift.redeemed",
            aggregate_type="growth_code",
            aggregate_id=str(growth_code.id),
            partition_key=str(growth_code.id),
            event_payload={
                "growth_code_id": str(growth_code.id),
                "redemption_id": str(redemption.id),
                "entitlement_grant_id": str(activated.id),
                "plan_family": policy.plan_family,
                "duration_days": policy.duration_days,
            },
            actor_context=OutboxActorContext(
                principal_type="customer",
                principal_id=str(user_id),
                auth_realm_id=str(current_realm.realm_id),
            ),
            source_context={"source_use_case": "RedeemGiftCodeUseCase.execute"},
        )
        observe_growth_code_redemption(
            code_type="gift",
            surface=CUSTOMER_REDEEM_SURFACE,
            result="success",
        )
        observe_growth_code_redemption_duration(
            code_type="gift",
            surface=CUSTOMER_REDEEM_SURFACE,
            result="success",
            duration_seconds=perf_counter() - started_at,
        )
        log_growth_code_event(
            "gift.redeemed",
            surface=CUSTOMER_REDEEM_SURFACE,
            code_type="gift",
            action_context="redeem",
            result="success",
            growth_code_id=str(growth_code.id),
            redemption_id=str(redemption.id),
            entitlement_grant_id=str(activated.id),
        )
        return RedeemedGiftCodeResult(
            growth_code=growth_code,
            policy=policy,
            redemption=redemption,
            entitlement_grant_id=activated.id,
            entitlement_snapshot=dict(activated.grant_snapshot or {}),
        )


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
