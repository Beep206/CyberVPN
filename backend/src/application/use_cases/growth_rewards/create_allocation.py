from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService, OutboxActorContext
from src.domain.enums import GrowthRewardAllocationStatus, GrowthRewardType
from src.infrastructure.database.models.growth_reward_allocation_model import GrowthRewardAllocationModel
from src.infrastructure.database.repositories.growth_reward_allocation_repo import (
    GrowthRewardAllocationRepository,
)
from src.infrastructure.database.repositories.invite_code_repo import InviteCodeRepository
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.database.repositories.order_repo import OrderRepository
from src.infrastructure.database.repositories.referral_commission_repo import ReferralCommissionRepository
from src.infrastructure.monitoring.instrumentation.growth_codes import (
    GROWTH_WORKER_SURFACE,
    log_growth_code_event,
    observe_growth_reward_created,
    observe_invite_redeemed,
)


class CreateGrowthRewardAllocationUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._allocations = GrowthRewardAllocationRepository(session)
        self._users = MobileUserRepository(session)
        self._orders = OrderRepository(session)
        self._invites = InviteCodeRepository(session)
        self._referrals = ReferralCommissionRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        reward_type: str,
        beneficiary_user_id: UUID,
        allocation_status: str | None = None,
        quantity: Decimal | float | int | None = None,
        unit: str | None = None,
        currency_code: str | None = None,
        storefront_id: UUID | None = None,
        source_code_id: UUID | None = None,
        source_redemption_id: UUID | None = None,
        policy_version_id: UUID | None = None,
        order_id: UUID | None = None,
        invite_code_id: UUID | None = None,
        referral_commission_id: UUID | None = None,
        source_key: str | None = None,
        reward_payload: dict | None = None,
        hold_until: datetime | None = None,
        available_at: datetime | None = None,
        reversal_reason: str | None = None,
        wallet_transaction_id: UUID | None = None,
        created_by_admin_user_id: UUID | None = None,
        allocated_at: datetime | None = None,
        commit: bool = True,
    ) -> GrowthRewardAllocationModel:
        if reward_type not in {member.value for member in GrowthRewardType}:
            raise ValueError("Reward type is invalid")
        resolved_allocation_status = allocation_status or GrowthRewardAllocationStatus.ALLOCATED.value
        if resolved_allocation_status not in {member.value for member in GrowthRewardAllocationStatus}:
            raise ValueError("Allocation status is invalid")

        if source_key:
            existing = await self._allocations.get_by_source_key(source_key)
            if existing is not None:
                return existing

        beneficiary = await self._users.get_by_id(beneficiary_user_id)
        if beneficiary is None:
            raise ValueError("Beneficiary user not found")
        if beneficiary.auth_realm_id is None:
            raise ValueError("Beneficiary user must belong to an auth realm")

        resolved_storefront_id = storefront_id
        resolved_currency_code = currency_code
        resolved_payload = dict(reward_payload or {})

        if order_id is not None:
            order = await self._orders.get_by_id(order_id)
            if order is None:
                raise ValueError("Order not found")
            if order.auth_realm_id != beneficiary.auth_realm_id:
                raise ValueError("Order does not belong to the same auth realm as the beneficiary user")
            if resolved_storefront_id is not None and resolved_storefront_id != order.storefront_id:
                raise ValueError("storefront_id does not match the referenced order")
            resolved_storefront_id = order.storefront_id

        if invite_code_id is not None:
            invite_code = await self._invites.get_by_id(invite_code_id)
            if invite_code is None:
                raise ValueError("Invite code not found")
            resolved_payload.setdefault("invite_owner_user_id", str(invite_code.owner_user_id))
            resolved_payload.setdefault("invite_source", invite_code.source)

        if referral_commission_id is not None:
            referral_commission = await self._referrals.get_by_id(referral_commission_id)
            if referral_commission is None:
                raise ValueError("Referral commission not found")
            if referral_commission.referrer_user_id != beneficiary_user_id:
                raise ValueError("Referral commission beneficiary must be the referrer user")
            resolved_currency_code = resolved_currency_code or referral_commission.currency
            resolved_payload.setdefault("referred_user_id", str(referral_commission.referred_user_id))
            resolved_payload.setdefault("payment_id", str(referral_commission.payment_id))

        resolved_quantity, resolved_unit = _normalize_reward_shape(
            reward_type=reward_type,
            quantity=quantity,
            unit=unit,
        )
        if reward_type == GrowthRewardType.REFERRAL_CREDIT.value:
            resolved_currency_code = resolved_currency_code or "USD"

        model = GrowthRewardAllocationModel(
            reward_type=reward_type,
            allocation_status=resolved_allocation_status,
            beneficiary_user_id=beneficiary.id,
            auth_realm_id=beneficiary.auth_realm_id,
            storefront_id=resolved_storefront_id,
            source_code_id=source_code_id,
            source_redemption_id=source_redemption_id,
            policy_version_id=policy_version_id,
            order_id=order_id,
            invite_code_id=invite_code_id,
            referral_commission_id=referral_commission_id,
            source_key=source_key,
            quantity=float(resolved_quantity),
            unit=resolved_unit,
            currency_code=resolved_currency_code,
            reward_payload=resolved_payload,
            hold_until=_normalize_utc_optional(hold_until),
            available_at=_normalize_utc_optional(available_at),
            reversal_reason=reversal_reason,
            wallet_transaction_id=wallet_transaction_id,
            created_by_admin_user_id=created_by_admin_user_id,
            allocated_at=_normalize_utc(allocated_at),
        )
        created = await self._allocations.create(model)
        await self._outbox.append_event(
            event_name="growth_reward.allocation.created",
            aggregate_type="growth_reward_allocation",
            aggregate_id=str(created.id),
            partition_key=str(created.beneficiary_user_id),
            event_payload={
                "growth_reward_allocation_id": str(created.id),
                "reward_type": created.reward_type,
                "allocation_status": created.allocation_status,
                "beneficiary_user_id": str(created.beneficiary_user_id),
                "source_code_id": str(created.source_code_id) if created.source_code_id else None,
                "source_redemption_id": str(created.source_redemption_id) if created.source_redemption_id else None,
                "order_id": str(created.order_id) if created.order_id else None,
                "quantity": str(created.quantity),
                "unit": created.unit,
                "currency_code": created.currency_code,
            },
            actor_context=OutboxActorContext(
                principal_type="admin" if created_by_admin_user_id else "system",
                principal_id=str(created_by_admin_user_id) if created_by_admin_user_id else None,
                auth_realm_id=str(created.auth_realm_id),
            ),
            source_context={"source_use_case": "CreateGrowthRewardAllocationUseCase.execute"},
        )
        if created.reward_type == GrowthRewardType.REFERRAL_CREDIT.value:
            reward_event_name = {
                GrowthRewardAllocationStatus.PENDING.value: "referral.reward_pending",
                GrowthRewardAllocationStatus.AVAILABLE.value: "referral.reward_available",
                GrowthRewardAllocationStatus.REVERSED.value: "referral.reward_reversed",
            }.get(created.allocation_status)
            if reward_event_name is not None:
                await self._outbox.append_event(
                    event_name=reward_event_name,
                    aggregate_type="growth_reward_allocation",
                    aggregate_id=str(created.id),
                    partition_key=str(created.beneficiary_user_id),
                    event_payload={
                        "growth_reward_allocation_id": str(created.id),
                        "beneficiary_user_id": str(created.beneficiary_user_id),
                        "allocation_status": created.allocation_status,
                        "quantity": str(created.quantity),
                        "currency_code": created.currency_code,
                        "source_redemption_id": (
                            str(created.source_redemption_id) if created.source_redemption_id else None
                        ),
                    },
                    actor_context=OutboxActorContext(
                        principal_type="admin" if created_by_admin_user_id else "system",
                        principal_id=str(created_by_admin_user_id) if created_by_admin_user_id else None,
                        auth_realm_id=str(created.auth_realm_id),
                    ),
                    source_context={"source_use_case": "CreateGrowthRewardAllocationUseCase.execute"},
                )
        observe_growth_reward_created(
            reward_type=created.reward_type,
            reward_status=created.allocation_status,
            surface=GROWTH_WORKER_SURFACE,
            quantity=float(created.quantity),
            currency_code=created.currency_code,
        )
        if invite_code_id is not None:
            observe_invite_redeemed(
                source_type=resolved_payload.get("invite_source", "unknown"),
                surface=GROWTH_WORKER_SURFACE,
                result="success",
            )
        log_growth_code_event(
            "growth_reward.allocation.created",
            surface=GROWTH_WORKER_SURFACE,
            code_type=None,
            result="success",
            reward_type=created.reward_type,
            growth_reward_allocation_id=str(created.id),
            source_code_id=str(created.source_code_id) if created.source_code_id else None,
            beneficiary_user_id=str(created.beneficiary_user_id),
            allocation_status=created.allocation_status,
        )
        if commit:
            await self._session.commit()
            await self._session.refresh(created)
        return created


def _normalize_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _normalize_utc_optional(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _normalize_reward_shape(
    *,
    reward_type: str,
    quantity: Decimal | float | int | None,
    unit: str | None,
) -> tuple[Decimal, str]:
    normalized_unit = unit.strip().lower() if unit else None
    if reward_type == GrowthRewardType.BONUS_DAYS.value:
        resolved_quantity = Decimal(str(quantity if quantity is not None else 0))
        if resolved_quantity <= 0:
            raise ValueError("bonus_days allocation requires a positive quantity")
        return resolved_quantity, normalized_unit or "days"
    if reward_type == GrowthRewardType.REFERRAL_CREDIT.value:
        resolved_quantity = Decimal(str(quantity if quantity is not None else 0))
        if resolved_quantity <= 0:
            raise ValueError("referral_credit allocation requires a positive quantity")
        return resolved_quantity, normalized_unit or "credit"

    resolved_quantity = Decimal(str(quantity if quantity is not None else 1))
    if resolved_quantity <= 0:
        raise ValueError("Growth reward allocation quantity must be positive")
    return resolved_quantity, normalized_unit or "perk"
