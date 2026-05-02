from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.config_service import ConfigService
from src.application.use_cases.growth_codes.registry import GrowthCodeRegistryService
from src.application.use_cases.growth_rewards import CreateGrowthRewardAllocationUseCase
from src.domain.enums import GrowthRewardAllocationStatus, GrowthRewardType
from src.infrastructure.database.models.growth_reward_allocation_model import GrowthRewardAllocationModel
from src.infrastructure.database.repositories.growth_code_repo import GrowthCodeRepository
from src.infrastructure.database.repositories.growth_reward_allocation_repo import (
    GrowthRewardAllocationRepository,
)
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository


@dataclass(frozen=True)
class ReferralRewardDecision:
    reward_amount: Decimal
    reward_was_capped: bool
    source_code_id: UUID
    hold_days: int
    status: str


class ProcessReferralRewardUseCase:
    def __init__(
        self,
        session: AsyncSession,
        *,
        config_service: ConfigService | None = None,
    ) -> None:
        self._session = session
        self._config_service = config_service
        self._users = MobileUserRepository(session)
        self._codes = GrowthCodeRepository(session)
        self._registry = GrowthCodeRegistryService(session)
        self._allocations = GrowthRewardAllocationRepository(session)
        self._growth_rewards = CreateGrowthRewardAllocationUseCase(session)

    async def execute(
        self,
        *,
        referrer_user_id: UUID,
        referred_user_id: UUID,
        payment_id: UUID,
        base_amount: Decimal,
        duration_days: int | None,
        order_id: UUID | None = None,
        storefront_id: UUID | None = None,
    ) -> GrowthRewardAllocationModel | None:
        if self._config_service is not None and not await self._config_service.is_referral_enabled():
            return None

        referrer = await self._users.get_by_id(referrer_user_id)
        referred = await self._users.get_by_id(referred_user_id)
        if referrer is None or referred is None:
            raise ValueError("Referral participants not found")
        if referrer.id == referred.id:
            return None
        if referrer.auth_realm_id is None or referrer.auth_realm_id != referred.auth_realm_id:
            raise ValueError("Referral participants must belong to the same auth realm")

        referral_code = await self._registry.ensure_shadow_referral(referrer)
        referral_policy = await self._codes.get_referral_policy(referral_code.id)
        if referral_policy is None:
            raise ValueError("Referral policy not found")

        reward_decision = await self._resolve_reward_decision(
            beneficiary_user_id=referrer.id,
            base_amount=base_amount,
            duration_days=duration_days,
            source_code_id=referral_code.id,
            hold_days=int(referral_policy.hold_days or 0),
            reward_value=Decimal(str(referral_policy.reward_value or 0)),
            monthly_cap=(
                Decimal(str(referral_policy.monthly_cap or 0))
                if referral_policy.monthly_cap is not None
                else None
            ),
            lifetime_cap=Decimal(str(referral_policy.lifetime_cap or 0))
            if referral_policy.lifetime_cap is not None
            else None,
            policy_snapshot=dict(referral_policy.policy_snapshot or {}),
        )
        if reward_decision is None:
            return None

        now = datetime.now(UTC)
        allocation = await self._growth_rewards.execute(
            reward_type=GrowthRewardType.REFERRAL_CREDIT.value,
            beneficiary_user_id=referrer.id,
            allocation_status=reward_decision.status,
            quantity=reward_decision.reward_amount,
            unit="credit",
            currency_code="USD",
            storefront_id=storefront_id,
            source_code_id=reward_decision.source_code_id,
            order_id=order_id,
            source_key=f"referral_reward:payment:{payment_id}",
            reward_payload={
                "payment_id": str(payment_id),
                "referred_user_id": str(referred_user_id),
                "base_amount": str(base_amount),
                "duration_days": duration_days,
                "reward_was_capped": reward_decision.reward_was_capped,
                "hold_days": reward_decision.hold_days,
                "friend_discount_value": float(referral_policy.friend_discount_value or 0),
                "reward_schedule": dict((referral_policy.policy_snapshot or {}).get("duration_reward_schedule") or {}),
            },
            hold_until=(
                now + timedelta(days=reward_decision.hold_days)
                if reward_decision.status == GrowthRewardAllocationStatus.PENDING.value
                else None
            ),
            available_at=(
                None
                if reward_decision.status == GrowthRewardAllocationStatus.PENDING.value
                else now
            ),
            commit=False,
        )
        return allocation

    async def _resolve_reward_decision(
        self,
        *,
        beneficiary_user_id: UUID,
        base_amount: Decimal,
        duration_days: int | None,
        source_code_id: UUID,
        hold_days: int,
        reward_value: Decimal,
        monthly_cap: Decimal | None,
        lifetime_cap: Decimal | None,
        policy_snapshot: dict,
    ) -> ReferralRewardDecision | None:
        reward_amount = _resolve_reward_amount(
            duration_days=duration_days,
            reward_value=reward_value,
            policy_snapshot=policy_snapshot,
            base_amount=base_amount,
            fallback_rate=Decimal("0.10"),
        )
        if reward_amount <= Decimal("0"):
            return None

        reward_was_capped = False
        if monthly_cap is not None:
            month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_used = Decimal(
                str(
                    await self._allocations.sum_quantity_for_beneficiary(
                        beneficiary_user_id=beneficiary_user_id,
                        reward_type=GrowthRewardType.REFERRAL_CREDIT.value,
                        statuses=("pending", "available"),
                        allocated_from=month_start,
                    )
                )
            )
            remaining_monthly = monthly_cap - monthly_used
            if remaining_monthly <= Decimal("0"):
                return None
            if reward_amount > remaining_monthly:
                reward_amount = remaining_monthly
                reward_was_capped = True

        if lifetime_cap is not None:
            lifetime_used = Decimal(
                str(
                    await self._allocations.sum_quantity_for_beneficiary(
                        beneficiary_user_id=beneficiary_user_id,
                        reward_type=GrowthRewardType.REFERRAL_CREDIT.value,
                        statuses=("pending", "available"),
                    )
                )
            )
            remaining_lifetime = lifetime_cap - lifetime_used
            if remaining_lifetime <= Decimal("0"):
                return None
            if reward_amount > remaining_lifetime:
                reward_amount = remaining_lifetime
                reward_was_capped = True

        if reward_amount <= Decimal("0"):
            return None

        return ReferralRewardDecision(
            reward_amount=reward_amount.quantize(Decimal("0.01")),
            reward_was_capped=reward_was_capped,
            source_code_id=source_code_id,
            hold_days=hold_days,
            status=(
                GrowthRewardAllocationStatus.PENDING.value
                if hold_days > 0
                else GrowthRewardAllocationStatus.AVAILABLE.value
            ),
        )


def _resolve_reward_amount(
    *,
    duration_days: int | None,
    reward_value: Decimal,
    policy_snapshot: dict,
    base_amount: Decimal,
    fallback_rate: Decimal,
) -> Decimal:
    if duration_days is not None:
        reward_schedule = dict(policy_snapshot.get("duration_reward_schedule") or {})
        scheduled_reward = reward_schedule.get(str(duration_days)) or reward_schedule.get(duration_days)
        if scheduled_reward is not None:
            return Decimal(str(scheduled_reward))

    if reward_value > Decimal("0"):
        return reward_value

    return (base_amount * fallback_rate).quantize(Decimal("0.01"))
