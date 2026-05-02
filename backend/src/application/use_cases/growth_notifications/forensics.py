"""Support-grade detail and export context for growth notification deliveries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.notification_queue_model import NotificationQueue
from src.infrastructure.database.repositories.customer_growth_notification_delivery_repository import (
    CustomerGrowthNotificationDeliveryRepository,
)
from src.infrastructure.database.repositories.growth_code_repo import GrowthCodeRepository
from src.infrastructure.database.repositories.growth_reward_allocation_repo import (
    GrowthRewardAllocationRepository,
)
from src.infrastructure.database.repositories.invite_code_repo import InviteCodeRepository
from src.infrastructure.database.repositories.outbox_repo import OutboxRepository


@dataclass(frozen=True)
class CustomerGrowthNotificationDeliveryForensics:
    delivery: Any
    sibling_deliveries: list[Any]
    delivery_events: list[Any]
    queue_snapshot: NotificationQueue | None
    source_summary: dict[str, Any] | None
    lifecycle_events: list[Any]
    troubleshooting_state: str
    customer_message_key: str
    support_summary: str


class GetCustomerGrowthNotificationDeliveryForensicsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._deliveries = CustomerGrowthNotificationDeliveryRepository(session)
        self._invites = InviteCodeRepository(session)
        self._codes = GrowthCodeRepository(session)
        self._rewards = GrowthRewardAllocationRepository(session)
        self._outbox = OutboxRepository(session)

    async def execute(
        self,
        *,
        delivery_id: UUID,
    ) -> CustomerGrowthNotificationDeliveryForensics:
        delivery = await self._deliveries.get_by_id(delivery_id)
        if delivery is None:
            raise ValueError("delivery_not_found")

        sibling_deliveries = await self._deliveries.list_by_user_notification_key(
            mobile_user_id=delivery.mobile_user_id,
            notification_key=delivery.notification_key,
        )
        delivery_events = await self._deliveries.list_events_for_delivery(delivery_id=delivery.id)
        queue_snapshot = None
        if delivery.notification_queue_id is not None:
            queue_snapshot = await self._session.get(NotificationQueue, delivery.notification_queue_id)

        source_summary = await self._build_source_summary(
            source_kind=delivery.source_kind,
            source_id=delivery.source_id,
        )
        lifecycle_events = await self._load_lifecycle_events(
            source_kind=delivery.source_kind,
            source_id=delivery.source_id,
        )
        troubleshooting_state, customer_message_key, support_summary = _build_troubleshooting_state(
            delivery_status=delivery.delivery_status,
            status_reason=delivery.status_reason,
            queue_snapshot=queue_snapshot,
        )
        return CustomerGrowthNotificationDeliveryForensics(
            delivery=delivery,
            sibling_deliveries=sibling_deliveries,
            delivery_events=delivery_events,
            queue_snapshot=queue_snapshot,
            source_summary=source_summary,
            lifecycle_events=lifecycle_events,
            troubleshooting_state=troubleshooting_state,
            customer_message_key=customer_message_key,
            support_summary=support_summary,
        )

    async def _build_source_summary(
        self,
        *,
        source_kind: str | None,
        source_id: str | None,
    ) -> dict[str, Any] | None:
        if not source_kind:
            return None

        parsed_source_id = _parse_uuid_or_none(source_id)
        if source_kind == "invite_code" and parsed_source_id is not None:
            invite = await self._invites.get_by_id(parsed_source_id)
            if invite is None:
                return None
            return {
                "source_kind": source_kind,
                "source_id": str(invite.id),
                "source_label": invite.code,
                "source_status": _invite_status(invite),
                "owner_user_id": str(invite.owner_user_id) if invite.owner_user_id else None,
                "beneficiary_user_id": str(invite.used_by_user_id) if invite.used_by_user_id else None,
                "metadata": {
                    "free_days": invite.free_days,
                    "source": invite.source,
                    "expires_at": invite.expires_at.isoformat() if invite.expires_at else None,
                    "used_at": invite.used_at.isoformat() if invite.used_at else None,
                },
            }

        if source_kind == "growth_reward" and parsed_source_id is not None:
            reward = await self._rewards.get_by_id(parsed_source_id)
            if reward is None:
                return None
            return {
                "source_kind": source_kind,
                "source_id": str(reward.id),
                "source_label": reward.reward_type,
                "source_status": reward.allocation_status,
                "owner_user_id": None,
                "beneficiary_user_id": str(reward.beneficiary_user_id),
                "metadata": {
                    "order_id": str(reward.order_id) if reward.order_id else None,
                    "quantity": float(reward.quantity),
                    "unit": reward.unit,
                    "currency_code": reward.currency_code,
                    "hold_until": reward.hold_until.isoformat() if reward.hold_until else None,
                    "available_at": reward.available_at.isoformat() if reward.available_at else None,
                    "reversed_at": reward.reversed_at.isoformat() if reward.reversed_at else None,
                },
            }

        if source_kind == "gift_code" and parsed_source_id is not None:
            code = await self._codes.get_code_by_id(parsed_source_id)
            if code is None:
                return None
            policy = await self._codes.get_gift_policy(code.id)
            redemptions = await self._codes.list_redemptions(code.id)
            return {
                "source_kind": source_kind,
                "source_id": str(code.id),
                "source_label": f"{code.code_prefix}••••",
                "source_status": code.status,
                "owner_user_id": str(code.owner_user_id) if code.owner_user_id else None,
                "beneficiary_user_id": (
                    str(redemptions[0].beneficiary_user_id)
                    if redemptions
                    else None
                ),
                "metadata": {
                    "issuer_type": code.issuer_type,
                    "plan_family": policy.plan_family if policy is not None else None,
                    "duration_days": policy.duration_days if policy is not None else None,
                    "expires_at": code.expires_at.isoformat() if code.expires_at else None,
                    "redemption_count": len(redemptions),
                    "batch_id": str(code.batch_id) if code.batch_id else None,
                },
            }

        return {
            "source_kind": source_kind,
            "source_id": source_id,
            "source_label": source_kind.replace("_", " "),
            "source_status": None,
            "owner_user_id": None,
            "beneficiary_user_id": None,
            "metadata": {},
        }

    async def _load_lifecycle_events(
        self,
        *,
        source_kind: str | None,
        source_id: str | None,
    ) -> list[Any]:
        if source_kind == "gift_code" and source_id:
            return await self._outbox.list_events(
                event_family="gift",
                aggregate_type="growth_code",
                aggregate_id=source_id,
                limit=20,
            )
        if source_kind == "growth_reward" and source_id:
            return await self._outbox.list_events(
                aggregate_type="growth_reward_allocation",
                aggregate_id=source_id,
                limit=20,
            )
        return []


def _parse_uuid_or_none(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _invite_status(invite: Any) -> str:
    if bool(invite.is_used):
        return "used"
    if invite.expires_at is not None and invite.expires_at <= datetime.now(UTC):
        return "expired"
    return "active"


def _build_troubleshooting_state(
    *,
    delivery_status: str,
    status_reason: str | None,
    queue_snapshot: NotificationQueue | None,
) -> tuple[str, str, str]:
    queue_error = queue_snapshot.error_message if queue_snapshot is not None else None
    if delivery_status == "delivered":
        return (
            "delivered",
            "growth_notifications.delivery.delivered",
            "Delivery completed successfully on the selected channel.",
        )
    if delivery_status == "failed":
        return (
            "actionable_retry",
            "growth_notifications.delivery.retry_available",
            queue_error or status_reason or "Channel delivery failed and can be retried after review.",
        )
    if delivery_status == "revoked":
        return (
            "revoked_admin",
            "growth_notifications.delivery.revoked",
            status_reason or "Delivery was revoked by an operator before customer receipt.",
        )
    if delivery_status == "paused":
        return (
            "paused_admin",
            "growth_notifications.delivery.paused",
            status_reason or "Delivery is paused pending operator review.",
        )
    if delivery_status == "skipped":
        return (
            "suppressed",
            "growth_notifications.delivery.unavailable",
            status_reason or "Delivery was intentionally skipped because the channel was unavailable or disabled.",
        )
    if delivery_status in {"queued", "processing", "planned"}:
        return (
            "in_progress",
            "growth_notifications.delivery.pending",
            "Delivery is still queued or being processed.",
        )
    return (
        "unknown",
        "growth_notifications.delivery.unknown",
        status_reason or "Delivery state requires manual inspection.",
    )
