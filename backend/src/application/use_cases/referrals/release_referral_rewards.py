from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService, OutboxActorContext
from src.application.use_cases.growth_notifications.catalog import referral_available_notification_key
from src.application.use_cases.growth_notifications.fanout import PlanCustomerGrowthNotificationFanoutUseCase
from src.domain.enums import GrowthRewardAllocationStatus, GrowthRewardType
from src.infrastructure.database.repositories.growth_reward_allocation_repo import (
    GrowthRewardAllocationRepository,
)
from src.infrastructure.monitoring.instrumentation.growth_codes import (
    GROWTH_WORKER_SURFACE,
    log_growth_code_event,
    observe_growth_reward_created,
)


class ReleaseReferralRewardsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._allocations = GrowthRewardAllocationRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        as_of: datetime | None = None,
        limit: int = 100,
        commit: bool = True,
    ) -> list:
        resolved_as_of = _coerce_utc(as_of)
        released = await self._allocations.list_releasable_referral_rewards(as_of=resolved_as_of, limit=limit)
        for allocation in released:
            allocation.allocation_status = GrowthRewardAllocationStatus.AVAILABLE.value
            allocation.available_at = resolved_as_of
            allocation.hold_until = None
            await self._session.flush()
            await self._outbox.append_event(
                event_name="growth_reward.allocation.available",
                aggregate_type="growth_reward_allocation",
                aggregate_id=str(allocation.id),
                partition_key=str(allocation.beneficiary_user_id),
                event_payload={
                    "growth_reward_allocation_id": str(allocation.id),
                    "beneficiary_user_id": str(allocation.beneficiary_user_id),
                    "reward_type": allocation.reward_type,
                    "allocation_status": allocation.allocation_status,
                    "available_at": allocation.available_at.isoformat() if allocation.available_at else None,
                },
                actor_context=OutboxActorContext(
                    principal_type="system",
                    auth_realm_id=str(allocation.auth_realm_id),
                ),
                source_context={"source_use_case": "ReleaseReferralRewardsUseCase.execute"},
            )
            await self._outbox.append_event(
                event_name="referral.reward_available",
                aggregate_type="growth_reward_allocation",
                aggregate_id=str(allocation.id),
                partition_key=str(allocation.beneficiary_user_id),
                event_payload={
                    "growth_reward_allocation_id": str(allocation.id),
                    "beneficiary_user_id": str(allocation.beneficiary_user_id),
                    "quantity": str(allocation.quantity),
                    "currency_code": allocation.currency_code,
                },
                actor_context=OutboxActorContext(
                    principal_type="system",
                    auth_realm_id=str(allocation.auth_realm_id),
                ),
                source_context={"source_use_case": "ReleaseReferralRewardsUseCase.execute"},
            )
            observe_growth_reward_created(
                reward_type=GrowthRewardType.REFERRAL_CREDIT.value,
                reward_status=GrowthRewardAllocationStatus.AVAILABLE.value,
                surface=GROWTH_WORKER_SURFACE,
                quantity=float(allocation.quantity),
                currency_code=allocation.currency_code,
            )
            log_growth_code_event(
                "referral.reward_available",
                surface=GROWTH_WORKER_SURFACE,
                result="success",
                reward_type=allocation.reward_type,
                growth_reward_allocation_id=str(allocation.id),
                beneficiary_user_id=str(allocation.beneficiary_user_id),
                allocation_status=allocation.allocation_status,
            )
            await PlanCustomerGrowthNotificationFanoutUseCase(self._session).execute(
                mobile_user_id=allocation.beneficiary_user_id,
                notification_key=referral_available_notification_key(allocation.id),
                notification_kind="referral_reward_available",
                title="Referral reward available",
                message=f"A referral reward of ${float(allocation.quantity):.2f} is now available on your account.",
                route_slug="/referral",
                source_kind="growth_reward",
                source_id=str(allocation.id),
            )

        if commit:
            await self._session.commit()
            for allocation in released:
                await self._session.refresh(allocation)
        return released


def _coerce_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
