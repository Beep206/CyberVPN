from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService, OutboxActorContext
from src.application.use_cases.growth_notifications.catalog import referral_reversed_notification_key
from src.application.use_cases.growth_notifications.fanout import PlanCustomerGrowthNotificationFanoutUseCase
from src.domain.enums import GrowthRewardAllocationStatus
from src.infrastructure.database.repositories.growth_reward_allocation_repo import (
    GrowthRewardAllocationRepository,
)
from src.infrastructure.monitoring.instrumentation.growth_codes import (
    GROWTH_WORKER_SURFACE,
    log_growth_code_event,
    observe_growth_reward_reversed,
)


class ReverseReferralRewardsForOrderUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._allocations = GrowthRewardAllocationRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        order_id: UUID,
        reversal_reason: str,
        commit: bool = True,
    ) -> list:
        now = datetime.now(UTC)
        reversed_allocations = await self._allocations.list_reversible_referral_rewards_for_order(order_id=order_id)
        for allocation in reversed_allocations:
            allocation.allocation_status = GrowthRewardAllocationStatus.REVERSED.value
            allocation.reversal_reason = reversal_reason
            allocation.reversed_at = now
            allocation.available_at = None
            allocation.hold_until = None
            await self._session.flush()
            await self._outbox.append_event(
                event_name="growth_reward.allocation.reversed",
                aggregate_type="growth_reward_allocation",
                aggregate_id=str(allocation.id),
                partition_key=str(allocation.beneficiary_user_id),
                event_payload={
                    "growth_reward_allocation_id": str(allocation.id),
                    "beneficiary_user_id": str(allocation.beneficiary_user_id),
                    "reward_type": allocation.reward_type,
                    "allocation_status": allocation.allocation_status,
                    "reversal_reason": reversal_reason,
                    "order_id": str(order_id),
                },
                actor_context=OutboxActorContext(
                    principal_type="system",
                    auth_realm_id=str(allocation.auth_realm_id),
                ),
                source_context={"source_use_case": "ReverseReferralRewardsForOrderUseCase.execute"},
            )
            await self._outbox.append_event(
                event_name="referral.reward_reversed",
                aggregate_type="growth_reward_allocation",
                aggregate_id=str(allocation.id),
                partition_key=str(allocation.beneficiary_user_id),
                event_payload={
                    "growth_reward_allocation_id": str(allocation.id),
                    "beneficiary_user_id": str(allocation.beneficiary_user_id),
                    "quantity": str(allocation.quantity),
                    "currency_code": allocation.currency_code,
                    "reversal_reason": reversal_reason,
                    "order_id": str(order_id),
                },
                actor_context=OutboxActorContext(
                    principal_type="system",
                    auth_realm_id=str(allocation.auth_realm_id),
                ),
                source_context={"source_use_case": "ReverseReferralRewardsForOrderUseCase.execute"},
            )
            observe_growth_reward_reversed(
                reward_type=allocation.reward_type,
                surface=GROWTH_WORKER_SURFACE,
                reason_code=reversal_reason,
                quantity=float(allocation.quantity),
                currency_code=allocation.currency_code,
            )
            log_growth_code_event(
                "referral.reward_reversed",
                surface=GROWTH_WORKER_SURFACE,
                result="success",
                reward_type=allocation.reward_type,
                growth_reward_allocation_id=str(allocation.id),
                beneficiary_user_id=str(allocation.beneficiary_user_id),
                allocation_status=allocation.allocation_status,
                reversal_reason=reversal_reason,
                order_id=str(order_id),
            )
            await PlanCustomerGrowthNotificationFanoutUseCase(self._session).execute(
                mobile_user_id=allocation.beneficiary_user_id,
                notification_key=referral_reversed_notification_key(allocation.id),
                notification_kind="referral_reward_reversed",
                title="Referral reward reversed",
                message=f"A referral reward of ${float(allocation.quantity):.2f} was reversed.",
                route_slug="/referral",
                notes=[f"Reason: {reversal_reason}."],
                source_kind="growth_reward",
                source_id=str(allocation.id),
            )

        if commit:
            await self._session.commit()
            for allocation in reversed_allocations:
                await self._session.refresh(allocation)
        return reversed_allocations
