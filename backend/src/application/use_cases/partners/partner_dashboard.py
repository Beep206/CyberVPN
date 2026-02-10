"""Use case for building the partner dashboard summary."""

import logging
from typing import Any
from uuid import UUID

from src.application.services.config_service import ConfigService
from src.infrastructure.database.repositories.partner_repo import PartnerRepository

logger = logging.getLogger(__name__)


class PartnerDashboardUseCase:
    """Aggregate partner statistics for the dashboard view.

    Returns client count, total earnings, active codes, tier information,
    and the partner's current tier based on client count.
    """

    def __init__(
        self,
        partner_repo: PartnerRepository,
        config_service: ConfigService,
    ) -> None:
        self._partner_repo = partner_repo
        self._config = config_service

    async def execute(self, partner_user_id: UUID) -> dict[str, Any]:
        """Build and return dashboard data for *partner_user_id*."""
        total_clients = await self._partner_repo.count_clients(partner_user_id)
        total_earned = await self._partner_repo.get_total_earnings(partner_user_id)
        codes = await self._partner_repo.get_codes_by_partner(partner_user_id)
        tiers = await self._config.get_partner_tiers()

        current_tier = self._resolve_tier(total_clients, tiers)

        logger.info(
            "partner_dashboard_loaded",
            extra={
                "partner_user_id": str(partner_user_id),
                "total_clients": total_clients,
                "total_earned": str(total_earned),
                "current_tier_commission_pct": current_tier.get("commission_pct") if current_tier else None,
            },
        )

        return {
            "total_clients": total_clients,
            "total_earned": float(total_earned),
            "codes": codes,
            "tiers": tiers,
            "current_tier": current_tier,
        }

    @staticmethod
    def _resolve_tier(client_count: int, tiers: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Find the highest tier the partner qualifies for based on client count.

        Tiers are expected to have ``min_clients`` and ``commission_pct`` keys,
        sorted ascending by ``min_clients``.
        """
        if not tiers:
            return None

        sorted_tiers = sorted(tiers, key=lambda t: t.get("min_clients", 0))
        resolved: dict[str, Any] | None = None

        for tier in sorted_tiers:
            if client_count >= tier.get("min_clients", 0):
                resolved = tier

        return resolved
