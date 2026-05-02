from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.growth_code_repo import GrowthCodeRepository
from src.infrastructure.database.repositories.growth_reward_allocation_repo import (
    GrowthRewardAllocationRepository,
)
from src.infrastructure.database.repositories.outbox_repo import OutboxRepository


@dataclass(frozen=True)
class AdminGrowthSignalsOverview:
    total_codes: int
    active_codes: int
    total_redemptions: int
    active_reservations: int
    blocked_reward_count: int
    available_referral_credit_usd: float
    code_status_breakdown: list[dict[str, Any]]
    resolution_result_breakdown: list[dict[str, Any]]
    rejection_reason_breakdown: list[dict[str, Any]]
    redemption_breakdown: list[dict[str, Any]]
    reward_status_breakdown: list[dict[str, Any]]
    reward_type_breakdown: list[dict[str, Any]]
    recent_lifecycle_events: list[dict[str, Any]]


@dataclass(frozen=True)
class AdminGrowthAbuseSignal:
    signal_key: str
    signal_type: str
    severity: str
    code_type: str | None
    reason_code: str
    count: int
    unique_users: int
    latest_event_at: datetime
    review_hint: str
    growth_code_id: str | None = None
    reward_allocation_id: str | None = None
    beneficiary_user_id: str | None = None
    source_redemption_id: str | None = None


class GetAdminGrowthSignalsOverviewUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._codes = GrowthCodeRepository(session)
        self._rewards = GrowthRewardAllocationRepository(session)
        self._outbox = OutboxRepository(session)

    async def execute(self) -> AdminGrowthSignalsOverview:
        code_status_breakdown = await self._codes.summarize_codes_by_type_status()
        resolution_result_breakdown = await self._codes.summarize_resolution_results()
        rejection_reason_breakdown = await self._codes.summarize_resolution_rejections()
        redemption_breakdown = await self._codes.summarize_redemptions_by_code_type()
        reward_status_breakdown = await self._rewards.summarize_by_status()
        reward_type_breakdown = await self._rewards.summarize_by_type()
        recent_events = await self._load_recent_lifecycle_events()

        total_codes = sum(int(item["count"]) for item in code_status_breakdown)
        active_codes = sum(
            int(item["count"])
            for item in code_status_breakdown
            if str(item["status"]) in {"active", "reserved"}
        )
        total_redemptions = sum(int(item["count"]) for item in redemption_breakdown)
        active_reservations = await self._codes.count_active_reservations()
        blocked_reward_count = sum(
            int(item["count"])
            for item in reward_status_breakdown
            if str(item["allocation_status"]) == "blocked_by_risk"
        )

        return AdminGrowthSignalsOverview(
            total_codes=total_codes,
            active_codes=active_codes,
            total_redemptions=total_redemptions,
            active_reservations=active_reservations,
            blocked_reward_count=blocked_reward_count,
            available_referral_credit_usd=await self._rewards.get_available_referral_credit_total(),
            code_status_breakdown=code_status_breakdown,
            resolution_result_breakdown=resolution_result_breakdown,
            rejection_reason_breakdown=rejection_reason_breakdown,
            redemption_breakdown=redemption_breakdown,
            reward_status_breakdown=reward_status_breakdown,
            reward_type_breakdown=reward_type_breakdown,
            recent_lifecycle_events=recent_events,
        )

    async def _load_recent_lifecycle_events(self) -> list[dict[str, Any]]:
        event_families = ("growth_code", "invite", "referral", "promo", "gift", "growth_reward")
        items = []
        for family in event_families:
            items.extend(await self._outbox.list_events(event_family=family, limit=10))
        items.sort(key=lambda item: item.occurred_at, reverse=True)
        recent = items[:12]
        return [
            {
                "id": str(item.id),
                "event_name": item.event_name,
                "event_family": item.event_family,
                "aggregate_type": item.aggregate_type,
                "aggregate_id": item.aggregate_id,
                "occurred_at": item.occurred_at,
                "event_status": item.event_status,
            }
            for item in recent
        ]


class ListAdminGrowthAbuseSignalsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._codes = GrowthCodeRepository(session)
        self._rewards = GrowthRewardAllocationRepository(session)

    async def execute(self, *, limit: int = 25) -> list[AdminGrowthAbuseSignal]:
        signals: list[AdminGrowthAbuseSignal] = []
        for row in await self._codes.list_resolution_abuse_signals(limit=limit, min_attempts=3):
            reject_reason = str(row["reject_reason"] or "unknown")
            signal_type = (
                "invite_self_redemption"
                if reject_reason == "invite_self_redemption_blocked"
                else "repeated_resolution_rejection"
            )
            severity = (
                "danger"
                if reject_reason in {"invite_self_redemption_blocked", "code_blocked_by_risk"}
                else "warning"
            )
            signals.append(
                AdminGrowthAbuseSignal(
                    signal_key=f"resolution:{row['raw_code_hash']}:{reject_reason}",
                    signal_type=signal_type,
                    severity=severity,
                    code_type=row.get("code_type"),
                    reason_code=reject_reason,
                    count=int(row["attempt_count"]),
                    unique_users=int(row["unique_users"]),
                    latest_event_at=row["latest_event_at"],
                    review_hint="Use Growth Code Lookup, then escalate to Security if the cluster looks intentional.",
                )
            )

        blocked_rewards = await self._rewards.list_blocked_by_risk(limit=limit)
        for reward in blocked_rewards:
            signals.append(
                AdminGrowthAbuseSignal(
                    signal_key=f"reward:{reward.id}",
                    signal_type="blocked_reward",
                    severity="danger",
                    code_type=None,
                    reason_code="blocked_by_risk",
                    count=1,
                    unique_users=1,
                    latest_event_at=reward.allocated_at,
                    review_hint=(
                        "Inspect the linked reward and open a formal risk review "
                        "when manual action is required."
                    ),
                    reward_allocation_id=str(reward.id),
                    beneficiary_user_id=str(reward.beneficiary_user_id),
                    source_redemption_id=str(reward.source_redemption_id) if reward.source_redemption_id else None,
                )
            )

        signals.sort(key=lambda item: item.latest_event_at, reverse=True)
        return signals[:limit]
