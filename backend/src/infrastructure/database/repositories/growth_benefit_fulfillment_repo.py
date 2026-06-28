from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.gifts.service import IssueGiftCodeUseCase
from src.application.use_cases.growth_benefits.fulfill import (
    BenefitFulfillmentRecord,
    DuplicateBenefitFulfillmentError,
    DuplicateInviteBatchError,
    GrantAddonBenefitConfig,
    GrowthBenefitConfigurationError,
    InviteBatchRecord,
    InviteCodeRecord,
    IssueGiftBenefitConfig,
    NewBenefitFulfillment,
    NewInviteBatch,
    NewInviteCode,
)
from src.domain.enums import WalletTxReason
from src.infrastructure.database.models.growth_benefit_model import (
    GrowthBenefitFulfillmentModel,
    InviteBatchModel,
)
from src.infrastructure.database.models.growth_code_model import (
    GiftCodePolicyModel,
    GrowthCodeIssuanceModel,
    GrowthCodeModel,
)
from src.infrastructure.database.models.growth_reward_allocation_model import GrowthRewardAllocationModel
from src.infrastructure.database.models.invite_code_model import InviteCodeModel
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.models.plan_addon_model import PlanAddonModel, SubscriptionAddonModel
from src.infrastructure.database.models.wallet_model import WalletTransactionModel
from src.infrastructure.database.repositories.service_access_repo import ServiceAccessRepository
from src.infrastructure.database.repositories.wallet_repo import WalletRepository


class GrowthBenefitFulfillmentRepository:
    """SQLAlchemy adapter for Growth Codes v6 benefit fulfillment state.

    The caller owns the surrounding transaction. Methods flush so the caller can
    observe generated identifiers and database constraints before committing.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_fulfillment_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> BenefitFulfillmentRecord | None:
        result = await self._session.execute(
            select(GrowthBenefitFulfillmentModel).where(
                GrowthBenefitFulfillmentModel.idempotency_key == idempotency_key
            )
        )
        model = result.scalars().first()
        return _fulfillment_record(model) if model is not None else None

    async def create_fulfillment(self, data: NewBenefitFulfillment) -> BenefitFulfillmentRecord:
        model = GrowthBenefitFulfillmentModel(
            benefit_id=data.benefit_id,
            growth_code_id=data.growth_code_id,
            user_id=data.user_id,
            order_id=data.order_id,
            payment_id=data.payment_id,
            idempotency_key=data.idempotency_key,
            status=data.status,
            attempt_count=data.attempt_count,
            config_snapshot=dict(data.config_snapshot),
            result_payload=dict(data.result_payload),
            started_at=data.started_at,
        )
        try:
            async with self._session.begin_nested():
                self._session.add(model)
                await self._session.flush()
        except IntegrityError as exc:
            if _is_idempotency_violation(exc):
                raise DuplicateBenefitFulfillmentError(data.idempotency_key) from exc
            raise
        await self._session.refresh(model)
        return _fulfillment_record(model)

    async def set_fulfillment_result(
        self,
        *,
        fulfillment_id: UUID,
        status: str,
        result_payload: dict[str, Any],
        completed_at: datetime | None,
    ) -> BenefitFulfillmentRecord:
        model = await self._session.get(GrowthBenefitFulfillmentModel, fulfillment_id)
        if model is None:
            raise ValueError("growth benefit fulfillment was not found")
        model.status = status
        model.result_payload = dict(result_payload)
        model.completed_at = completed_at
        model.error_code = None
        model.error_message = None
        await self._session.flush()
        await self._session.refresh(model)
        return _fulfillment_record(model)

    async def get_invite_batch_by_idempotency_key(self, idempotency_key: str) -> InviteBatchRecord | None:
        result = await self._session.execute(
            select(InviteBatchModel).where(InviteBatchModel.idempotency_key == idempotency_key)
        )
        model = result.scalars().first()
        return _invite_batch_record(model) if model is not None else None

    async def create_invite_batch(self, data: NewInviteBatch) -> InviteBatchRecord:
        model = InviteBatchModel(
            owner_user_id=data.owner_user_id,
            campaign_id=data.campaign_id,
            source_growth_code_id=data.source_growth_code_id,
            source_benefit_id=data.source_benefit_id,
            source_order_id=data.source_order_id,
            source_payment_id=data.source_payment_id,
            source_type=data.source_type,
            requested_count=data.requested_count,
            issued_count=data.issued_count,
            friend_days=data.friend_days,
            expiry_mode=data.expiry_mode,
            expiry_days=data.expiry_days,
            expires_at=data.expires_at,
            entitlement_mode=data.entitlement_mode,
            entitlement_profile_key=data.entitlement_profile_key,
            plan_id=data.plan_id,
            entitlement_snapshot=dict(data.entitlement_snapshot),
            status=data.status,
            idempotency_key=data.idempotency_key,
        )
        try:
            async with self._session.begin_nested():
                self._session.add(model)
                await self._session.flush()
        except IntegrityError as exc:
            if _is_idempotency_violation(exc):
                raise DuplicateInviteBatchError(data.idempotency_key) from exc
            raise
        await self._session.refresh(model)
        return _invite_batch_record(model)

    async def set_invite_batch_issued(
        self,
        *,
        batch_id: UUID,
        issued_count: int,
        status: str,
    ) -> InviteBatchRecord:
        model = await self._session.get(InviteBatchModel, batch_id)
        if model is None:
            raise ValueError("growth invite batch was not found")
        model.issued_count = issued_count
        model.status = status
        await self._session.flush()
        await self._session.refresh(model)
        return _invite_batch_record(model)

    async def list_invite_codes_for_batch(self, batch_id: UUID) -> tuple[InviteCodeRecord, ...]:
        result = await self._session.execute(
            select(InviteCodeModel).where(InviteCodeModel.batch_id == batch_id).order_by(InviteCodeModel.id.asc())
        )
        return tuple(_invite_code_record(model) for model in result.scalars().all())

    async def create_invite_codes(self, data: tuple[NewInviteCode, ...]) -> tuple[InviteCodeRecord, ...]:
        models = [
            InviteCodeModel(
                code=item.code,
                owner_user_id=item.owner_user_id,
                free_days=item.free_days,
                plan_id=item.plan_id,
                batch_id=item.batch_id,
                source_growth_code_id=item.source_growth_code_id,
                source_benefit_id=item.source_benefit_id,
                source_payment_id=item.source_payment_id,
                expires_at=item.expires_at,
                code_hash=item.code_hash,
                code_prefix=item.code_prefix,
                entitlement_mode=item.entitlement_mode,
                entitlement_profile_key=item.entitlement_profile_key,
                entitlement_snapshot=dict(item.entitlement_snapshot),
                source="growth_benefit",
                status="issued",
            )
            for item in data
        ]
        self._session.add_all(models)
        await self._session.flush()
        for model in models:
            await self._session.refresh(model)
        return tuple(_invite_code_record(model) for model in models)

    async def apply_wallet_credit_benefit(
        self,
        *,
        user_id: UUID,
        fulfillment_id: UUID,
        amount: Decimal,
        currency: str,
        description_key: str,
    ) -> dict[str, Any]:
        if currency != "USD":
            raise ValueError("wallet_credit benefit supports USD wallet only")
        existing = await self._session.execute(
            select(WalletTransactionModel).where(
                WalletTransactionModel.reference_type == "growth_benefit_fulfillment",
                WalletTransactionModel.reference_id == fulfillment_id,
            )
        )
        existing_tx = existing.scalars().first()
        if existing_tx is not None:
            return {
                "wallet_transaction_id": str(existing_tx.id),
                "amount": str(existing_tx.amount),
                "currency": existing_tx.currency,
                "balance_after": str(existing_tx.balance_after),
                "duplicate": True,
            }

        tx = await WalletRepository(self._session).credit(
            user_id=user_id,
            amount=amount,
            reason=WalletTxReason.ADJUSTMENT,
            description=description_key,
            reference_type="growth_benefit_fulfillment",
            reference_id=fulfillment_id,
        )
        return {
            "wallet_transaction_id": str(tx.id),
            "amount": str(tx.amount),
            "currency": tx.currency,
            "balance_after": str(tx.balance_after),
            "duplicate": False,
        }

    async def apply_bonus_days_benefit(
        self,
        *,
        user_id: UUID,
        order_id: UUID,
        payment_id: UUID,
        fulfillment_id: UUID,
        benefit_id: UUID,
        growth_code_id: UUID,
        days: int,
        grant_mode: str,
        entitlement_profile_key: str | None,
        reversal_mode: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        order = await self._require_order(order_id=order_id, user_id=user_id)
        source_key = _bonus_days_source_key(benefit_id=benefit_id, payment_id=payment_id)
        existing = await self._get_reward_allocation_by_source_key(source_key)
        if existing is not None:
            return {
                **_reward_allocation_payload(existing),
                "side_effect_mode": dict(existing.reward_payload or {}).get("side_effect_mode", "reward_allocation"),
                "duplicate": True,
            }

        current_grant = None
        if grant_mode == "extend_current_subscription":
            current_grant = await ServiceAccessRepository(self._session).get_current_active_entitlement_grant(
                customer_account_id=user_id,
                auth_realm_id=order.auth_realm_id,
                now=occurred_at,
            )

        side_effect_mode = "reward_allocation"
        allocation_status = "allocated"
        previous_expires_at = None
        new_expires_at = None
        target_entitlement_grant_id = None
        if grant_mode == "extend_current_subscription":
            if current_grant is None:
                side_effect_mode = "pending_reward_allocation"
                allocation_status = "pending"
            else:
                side_effect_mode = "entitlement_extension"
                target_entitlement_grant_id = current_grant.id
                previous_expires_at = current_grant.expires_at
                if previous_expires_at is not None:
                    normalized_previous = _to_utc(previous_expires_at)
                    base = max(normalized_previous, occurred_at)
                    new_expires_at = base + timedelta(days=days)
                    current_grant.expires_at = new_expires_at
                    current_grant.grant_snapshot = {
                        **dict(current_grant.grant_snapshot or {}),
                        "expires_at": new_expires_at.isoformat(),
                    }

        allocation = GrowthRewardAllocationModel(
            reward_type="bonus_days",
            allocation_status=allocation_status,
            beneficiary_user_id=user_id,
            auth_realm_id=order.auth_realm_id,
            storefront_id=order.storefront_id,
            source_code_id=growth_code_id,
            order_id=order_id,
            source_key=source_key,
            quantity=days,
            unit="days",
            reward_payload={
                "source": "growth_benefit_fulfillment",
                "fulfillment_id": str(fulfillment_id),
                "benefit_id": str(benefit_id),
                "payment_id": str(payment_id),
                "side_effect_mode": side_effect_mode,
                "grant_mode": grant_mode,
                "entitlement_profile_key": entitlement_profile_key,
                "reversal_mode": reversal_mode,
                "target_entitlement_grant_id": str(target_entitlement_grant_id)
                if target_entitlement_grant_id
                else None,
                "previous_expires_at": _iso_or_none(previous_expires_at),
                "new_expires_at": _iso_or_none(new_expires_at),
            },
            available_at=occurred_at if allocation_status == "allocated" else None,
        )
        self._session.add(allocation)
        await self._session.flush()
        await self._session.refresh(allocation)
        return {
            **_reward_allocation_payload(allocation),
            "side_effect_mode": side_effect_mode,
            "target_entitlement_grant_id": str(target_entitlement_grant_id) if target_entitlement_grant_id else None,
            "previous_expires_at": _iso_or_none(previous_expires_at),
            "new_expires_at": _iso_or_none(new_expires_at),
            "duplicate": False,
        }

    async def issue_gift_benefit(
        self,
        *,
        user_id: UUID,
        order_id: UUID,
        payment_id: UUID,
        fulfillment_id: UUID,
        benefit_id: UUID,
        growth_code_id: UUID,
        config: IssueGiftBenefitConfig,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        order = await self._require_order(order_id=order_id, user_id=user_id)
        plan_id = config.plan_id or order.subscription_plan_id
        if plan_id is None:
            raise ValueError("issue_gift benefit requires plan_id or an order subscription plan")

        batch_id = _deterministic_uuid(f"growth-gift:{benefit_id}:payment:{payment_id}:fulfillment:{fulfillment_id}")
        existing = await self._list_gift_codes_for_batch(batch_id)
        duplicate = len(existing) >= config.count
        if len(existing) < config.count:
            issuer = IssueGiftCodeUseCase(self._session)
            for _ in range(config.count - len(existing)):
                await issuer.execute(
                    owner_user_id=user_id,
                    plan_id=plan_id,
                    issuer_type="system",
                    issuance_type="growth_benefit",
                    source_payment_id=payment_id,
                    source_order_id=order_id,
                    storefront_id=order.storefront_id,
                    auth_realm_id=order.auth_realm_id,
                    batch_id=batch_id,
                    reason_code="growth_benefit",
                    admin_note=f"growth_benefit_fulfillment:{fulfillment_id}",
                )
            existing = await self._list_gift_codes_for_batch(batch_id)

        selected = tuple(existing[: config.count])
        return {
            "gift_batch_id": str(batch_id),
            "issued_count": len(selected),
            "requested_count": config.count,
            "plan_id": str(plan_id),
            "issued_at": occurred_at.isoformat(),
            "entitlement_mode": config.entitlement_mode,
            "entitlement_profile_key": config.entitlement_profile_key,
            "gift_code_ids": [str(item["growth_code_id"]) for item in selected],
            "gift_code_refs": [
                {
                    "id": str(item["growth_code_id"]),
                    "code_hash": item["code_hash"],
                    "code_prefix": item["code_prefix"],
                    "status": item["status"],
                    "policy_id": str(item["policy_id"]),
                    "issuance_id": str(item["issuance_id"]),
                }
                for item in selected
            ],
            "duplicate": duplicate,
        }

    async def grant_addon_benefit(
        self,
        *,
        user_id: UUID,
        order_id: UUID,
        payment_id: UUID,
        fulfillment_id: UUID,
        benefit_id: UUID,
        growth_code_id: UUID,
        config: GrantAddonBenefitConfig,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        order = await self._require_order(order_id=order_id, user_id=user_id)
        addon = await self._get_active_addon(config.addon_code)
        if addon.requires_location and not config.location_code:
            raise ValueError("grant_addon benefit requires location_code for this add-on")

        source_key = _addon_source_key(benefit_id=benefit_id, payment_id=payment_id)
        existing_addon = await self._get_subscription_addon_by_source_key(source_key, payment_id=payment_id)
        if existing_addon is not None:
            return {
                "side_effect_mode": "subscription_addon_grant",
                "subscription_addon_id": str(existing_addon.id),
                "plan_addon_id": str(existing_addon.plan_addon_id),
                "starts_at": existing_addon.starts_at.isoformat(),
                "expires_at": _iso_or_none(existing_addon.expires_at),
                "duplicate": True,
            }

        service_access = ServiceAccessRepository(self._session)
        current_grant = await service_access.get_current_active_entitlement_grant(
            customer_account_id=user_id,
            auth_realm_id=order.auth_realm_id,
            now=occurred_at,
        )
        if current_grant is not None:
            _validate_addon_quantity_for_grant(
                addon=addon,
                grant_snapshot=dict(current_grant.grant_snapshot or {}),
                config=config,
            )
            if config.duration_mode == "match_plan":
                expires_at = _to_utc(current_grant.expires_at) if current_grant.expires_at is not None else None
            else:
                expires_at = occurred_at + timedelta(days=int(config.duration_days or 0))
            subscription_addon = SubscriptionAddonModel(
                user_id=user_id,
                plan_addon_id=addon.id,
                payment_id=payment_id,
                quantity=config.quantity,
                location_code=config.location_code,
                status="active",
                starts_at=occurred_at,
                expires_at=expires_at,
                metadata_={
                    "source": "growth_benefit_fulfillment",
                    "source_key": source_key,
                    "fulfillment_id": str(fulfillment_id),
                    "benefit_id": str(benefit_id),
                    "growth_code_id": str(growth_code_id),
                    "order_id": str(order_id),
                    "reversal_mode": config.reversal_mode,
                },
            )
            self._session.add(subscription_addon)
            await self._session.flush()
            await self._session.refresh(subscription_addon)
            return {
                "side_effect_mode": "subscription_addon_grant",
                "subscription_addon_id": str(subscription_addon.id),
                "plan_addon_id": str(addon.id),
                "target_entitlement_grant_id": str(current_grant.id),
                "starts_at": subscription_addon.starts_at.isoformat(),
                "expires_at": _iso_or_none(subscription_addon.expires_at),
                "duplicate": False,
            }

        allocation = await self._get_reward_allocation_by_source_key(source_key)
        if allocation is None:
            allocation = GrowthRewardAllocationModel(
                reward_type="grant_addon",
                allocation_status="pending",
                beneficiary_user_id=user_id,
                auth_realm_id=order.auth_realm_id,
                storefront_id=order.storefront_id,
                source_code_id=growth_code_id,
                order_id=order_id,
                source_key=source_key,
                quantity=config.quantity,
                unit="addon",
                reward_payload={
                    "source": "growth_benefit_fulfillment",
                    "fulfillment_id": str(fulfillment_id),
                    "benefit_id": str(benefit_id),
                    "payment_id": str(payment_id),
                    "side_effect_mode": "pending_reward_allocation",
                    "addon_code": addon.code,
                    "plan_addon_id": str(addon.id),
                    "quantity": config.quantity,
                    "duration_mode": config.duration_mode,
                    "duration_days": config.duration_days,
                    "location_code": config.location_code,
                    "reversal_mode": config.reversal_mode,
                },
            )
            self._session.add(allocation)
            await self._session.flush()
            await self._session.refresh(allocation)
            duplicate = False
        else:
            duplicate = True
        return {
            **_reward_allocation_payload(allocation),
            "side_effect_mode": "pending_reward_allocation",
            "plan_addon_id": str(addon.id),
            "duplicate": duplicate,
        }

    async def _require_order(self, *, order_id: UUID, user_id: UUID) -> OrderModel:
        order = await self._session.get(OrderModel, order_id)
        if order is None or order.user_id != user_id:
            raise ValueError("Order not found for growth benefit fulfillment")
        return order

    async def _get_reward_allocation_by_source_key(self, source_key: str) -> GrowthRewardAllocationModel | None:
        result = await self._session.execute(
            select(GrowthRewardAllocationModel).where(GrowthRewardAllocationModel.source_key == source_key)
        )
        return result.scalars().first()

    async def _list_gift_codes_for_batch(self, batch_id: UUID) -> tuple[dict[str, Any], ...]:
        result = await self._session.execute(
            select(GrowthCodeModel, GiftCodePolicyModel, GrowthCodeIssuanceModel)
            .join(GiftCodePolicyModel, GiftCodePolicyModel.growth_code_id == GrowthCodeModel.id)
            .join(GrowthCodeIssuanceModel, GrowthCodeIssuanceModel.growth_code_id == GrowthCodeModel.id)
            .where(
                GrowthCodeModel.code_type == "gift",
                GrowthCodeModel.batch_id == batch_id,
                GrowthCodeIssuanceModel.issuance_type == "growth_benefit",
            )
            .order_by(GrowthCodeModel.created_at.asc(), GrowthCodeModel.id.asc())
        )
        rows = result.all()
        return tuple(
            {
                "growth_code_id": code.id,
                "code_hash": code.code_hash,
                "code_prefix": code.code_prefix,
                "status": code.status,
                "policy_id": policy.id,
                "issuance_id": issuance.id,
            }
            for code, policy, issuance in rows
        )

    async def _get_active_addon(self, addon_code: str) -> PlanAddonModel:
        result = await self._session.execute(select(PlanAddonModel).where(PlanAddonModel.code == addon_code))
        addon = result.scalar_one_or_none()
        if addon is None or not addon.is_active:
            raise ValueError("grant_addon benefit references inactive or missing add-on")
        return addon

    async def _get_subscription_addon_by_source_key(
        self,
        source_key: str,
        *,
        payment_id: UUID,
    ) -> SubscriptionAddonModel | None:
        result = await self._session.execute(
            select(SubscriptionAddonModel).where(
                SubscriptionAddonModel.status == "active",
                SubscriptionAddonModel.payment_id == payment_id,
            )
        )
        for model in result.scalars().all():
            if dict(model.metadata_ or {}).get("source_key") == source_key:
                return model
        return None


def _fulfillment_record(model: GrowthBenefitFulfillmentModel) -> BenefitFulfillmentRecord:
    return BenefitFulfillmentRecord(
        id=model.id,
        benefit_id=model.benefit_id,
        growth_code_id=model.growth_code_id,
        user_id=model.user_id,
        order_id=model.order_id,
        payment_id=model.payment_id,
        idempotency_key=model.idempotency_key,
        status=model.status,
        attempt_count=model.attempt_count,
        config_snapshot=dict(model.config_snapshot or {}),
        result_payload=dict(model.result_payload or {}),
        error_code=model.error_code,
        error_message=model.error_message,
        started_at=model.started_at,
        completed_at=model.completed_at,
        next_retry_at=model.next_retry_at,
    )


def _invite_batch_record(model: InviteBatchModel) -> InviteBatchRecord:
    return InviteBatchRecord(
        id=model.id,
        owner_user_id=model.owner_user_id,
        campaign_id=model.campaign_id,
        source_growth_code_id=model.source_growth_code_id,
        source_benefit_id=model.source_benefit_id,
        source_order_id=model.source_order_id,
        source_payment_id=model.source_payment_id,
        source_type=model.source_type,
        requested_count=model.requested_count,
        issued_count=model.issued_count,
        friend_days=model.friend_days,
        expiry_mode=model.expiry_mode,
        expiry_days=model.expiry_days,
        expires_at=model.expires_at,
        entitlement_mode=model.entitlement_mode,
        entitlement_profile_key=model.entitlement_profile_key,
        plan_id=model.plan_id,
        entitlement_snapshot=dict(model.entitlement_snapshot or {}),
        status=model.status,
        idempotency_key=model.idempotency_key,
    )


def _invite_code_record(model: InviteCodeModel) -> InviteCodeRecord:
    if model.batch_id is None or model.source_growth_code_id is None or model.source_benefit_id is None:
        raise ValueError("growth invite code is missing source references")
    if model.source_payment_id is None:
        raise ValueError("growth invite code is missing source payment")
    return InviteCodeRecord(
        id=model.id,
        owner_user_id=model.owner_user_id,
        batch_id=model.batch_id,
        source_growth_code_id=model.source_growth_code_id,
        source_benefit_id=model.source_benefit_id,
        source_payment_id=model.source_payment_id,
        free_days=model.free_days,
        expires_at=model.expires_at,
        code_hash=str(model.code_hash or ""),
        code_prefix=str(model.code_prefix or ""),
        status=model.status,
    )


def _bonus_days_source_key(*, benefit_id: UUID, payment_id: UUID) -> str:
    return f"growth-bonus-days:{benefit_id}:pay:{payment_id}"


def _addon_source_key(*, benefit_id: UUID, payment_id: UUID) -> str:
    return f"growth-addon:{benefit_id}:pay:{payment_id}"


def _deterministic_uuid(value: str) -> UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, value)


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _iso_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _to_utc(value).isoformat()


def _reward_allocation_payload(model: GrowthRewardAllocationModel) -> dict[str, Any]:
    return {
        "growth_reward_allocation_id": str(model.id),
        "reward_type": model.reward_type,
        "allocation_status": model.allocation_status,
        "source_key": model.source_key,
        "quantity": str(model.quantity),
        "unit": model.unit,
    }


def _validate_addon_quantity_for_grant(
    *,
    addon: PlanAddonModel,
    grant_snapshot: dict[str, Any],
    config: GrantAddonBenefitConfig,
) -> None:
    max_quantity_by_plan = dict(addon.max_quantity_by_plan or {})
    if not max_quantity_by_plan:
        return
    plan_code = str(grant_snapshot.get("plan_code") or "")
    if not plan_code:
        raise GrowthBenefitConfigurationError("grant_addon benefit requires plan_code compatibility snapshot")
    raw_limit = max_quantity_by_plan.get(plan_code)
    if raw_limit is None:
        raise GrowthBenefitConfigurationError("grant_addon benefit is not compatible with current plan")
    if config.quantity > int(raw_limit):
        raise GrowthBenefitConfigurationError("grant_addon benefit exceeds plan add-on quantity limit")


def _is_idempotency_violation(exc: IntegrityError) -> bool:
    message = str(exc).lower()
    is_unique_violation = "unique" in message or "duplicate" in message or "23505" in message
    return is_unique_violation and "idempotency" in message
