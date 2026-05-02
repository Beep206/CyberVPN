"""Use case: retrieve referral statistics for a user."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from src.application.services.config_service import ConfigService
from src.infrastructure.database.repositories.growth_reward_allocation_repo import (
    GrowthRewardAllocationRepository,
)
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.database.repositories.referral_commission_repo import (
    ReferralCommissionRepository,
)


class GetReferralStatsUseCase:
    def __init__(
        self,
        commission_repo: ReferralCommissionRepository,
        growth_reward_repo: GrowthRewardAllocationRepository,
        mobile_user_repo: MobileUserRepository,
        config_service: ConfigService,
    ) -> None:
        self._commission_repo = commission_repo
        self._growth_reward_repo = growth_reward_repo
        self._mobile_users = mobile_user_repo
        self._config_service = config_service

    async def execute(self, user_id: UUID) -> dict[str, Any]:
        """Return aggregated referral statistics for *user_id*.

        The target-state primary truth is ``growth_reward_allocations``.
        Legacy ``referral_commissions`` remain included for historical continuity.
        """

        total_signups = await self._mobile_users.count_referred_users(user_id)
        legacy_distinct_referred_users = await self._commission_repo.count_distinct_referred_users(user_id)
        total_referrals = max(total_signups, legacy_distinct_referred_users)

        legacy_total_earned = await self._commission_repo.get_total_by_referrer(user_id)
        reward_totals = await self._growth_reward_repo.summarize_referral_credit_by_status(
            beneficiary_user_id=user_id,
        )

        pending_rewards_usd = Decimal(str(reward_totals.get("pending", 0)))
        available_rewards_usd = Decimal(str(reward_totals.get("available", 0)))
        reversed_rewards_usd = Decimal(str(reward_totals.get("reversed", 0)))
        blocked_rewards_usd = Decimal(str(reward_totals.get("blocked_by_risk", 0)))
        expired_rewards_usd = Decimal(str(reward_totals.get("expired", 0)))

        legacy_total_earned_decimal = Decimal(str(legacy_total_earned))
        total_earned = (
            legacy_total_earned_decimal
            + pending_rewards_usd
            + available_rewards_usd
            + blocked_rewards_usd
            + expired_rewards_usd
        )

        commission_rate: float = await self._config_service.get_referral_commission_rate()
        reward_stats_map = await self._growth_reward_repo.get_referral_reward_stats_map([user_id])
        qualifying_orders = int(
            reward_stats_map.get(user_id, {}).get("reward_count", 0) or 0
        )
        month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_cap_used = Decimal(
            str(
                await self._growth_reward_repo.sum_quantity_for_beneficiary(
                    beneficiary_user_id=user_id,
                    reward_type="referral_credit",
                    statuses=("pending", "available"),
                    allocated_from=month_start,
                )
            )
        )
        lifetime_cap_used = Decimal(
            str(
                await self._growth_reward_repo.sum_quantity_for_beneficiary(
                    beneficiary_user_id=user_id,
                    reward_type="referral_credit",
                    statuses=("pending", "available"),
                )
            )
        )

        return {
            "total_referrals": total_referrals,
            "total_earned": total_earned,
            "commission_rate": commission_rate,
            "pending_rewards_usd": pending_rewards_usd,
            "available_rewards_usd": available_rewards_usd,
            "reversed_rewards_usd": reversed_rewards_usd,
            "monthly_cap_used_usd": monthly_cap_used,
            "lifetime_cap_used_usd": lifetime_cap_used,
            "qualifying_orders": qualifying_orders,
        }
