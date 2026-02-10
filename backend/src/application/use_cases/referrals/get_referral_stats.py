"""Use case: retrieve referral statistics for a user."""

from decimal import Decimal
from typing import Any
from uuid import UUID

from src.application.services.config_service import ConfigService
from src.infrastructure.database.repositories.referral_commission_repo import (
    ReferralCommissionRepository,
)


class GetReferralStatsUseCase:
    def __init__(
        self,
        commission_repo: ReferralCommissionRepository,
        config_service: ConfigService,
    ) -> None:
        self._commission_repo = commission_repo
        self._config_service = config_service

    async def execute(self, user_id: UUID) -> dict[str, Any]:
        """Return aggregated referral statistics for *user_id*.

        Returns a dict with:
        - total_referrals: number of commission records
        - total_earned: sum of commission amounts (Decimal)
        - commission_rate: current configured rate (float)
        - recent_commissions: last 10 commission records
        """
        total_referrals = await self._commission_repo.count_by_referrer(user_id)
        total_earned: Decimal = await self._commission_repo.get_total_by_referrer(user_id)
        commission_rate: float = await self._config_service.get_referral_commission_rate()
        recent = await self._commission_repo.get_by_referrer(user_id, offset=0, limit=10)

        return {
            "total_referrals": total_referrals,
            "total_earned": total_earned,
            "commission_rate": commission_rate,
            "recent_commissions": recent,
        }
