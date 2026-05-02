"""Admin controls for customer growth notification deliveries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from html import escape
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.customer_growth_notification_delivery_model import (
    CustomerGrowthNotificationDeliveryModel,
)
from src.infrastructure.database.models.notification_queue_model import NotificationQueue
from src.infrastructure.database.repositories.customer_growth_notification_delivery_repository import (
    CustomerGrowthNotificationDeliveryRepository,
)
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.monitoring.instrumentation.growth_codes import (
    ADMIN_GROWTH_SURFACE,
    log_growth_code_event,
    observe_growth_notification_delivery_recovered,
    observe_growth_notification_repair_completed,
    observe_growth_notification_support_resolution,
)

from .catalog import admin_manual_notification_key
from .fanout import PlanCustomerGrowthNotificationFanoutUseCase


@dataclass(slots=True)
class CustomerGrowthNotificationDeliveryContext:
    delivery: CustomerGrowthNotificationDeliveryModel
    telegram_queue: NotificationQueue | None
    closure_deliveries: list[CustomerGrowthNotificationDeliveryModel] = field(default_factory=list)


class CreateAdminManualGrowthNotificationUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._mobile_users = MobileUserRepository(session)
        self._fanout = PlanCustomerGrowthNotificationFanoutUseCase(session)

    async def execute(
        self,
        *,
        mobile_user_id: UUID,
        title: str,
        message: str,
        route_slug: str,
        channels: set[str],
        created_by_admin_user_id: UUID,
        locale: str = "en-EN",
        notes: list[str] | None = None,
    ) -> list[CustomerGrowthNotificationDeliveryModel]:
        if not channels:
            raise ValueError("channels_required")
        user = await self._mobile_users.get_by_id(mobile_user_id)
        if user is None:
            raise ValueError("customer_not_found")

        notification_id = uuid4()
        return await self._fanout.execute(
            mobile_user_id=mobile_user_id,
            notification_key=admin_manual_notification_key(notification_id),
            notification_kind="admin_manual_update",
            title=title,
            message=message,
            route_slug=route_slug,
            notes=notes,
            source_kind="admin_manual_notification",
            source_id=str(notification_id),
            created_by_admin_user_id=created_by_admin_user_id,
            locale=locale,
            allowed_channels=channels,
        )


class ManageCustomerGrowthNotificationDeliveryUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._deliveries = CustomerGrowthNotificationDeliveryRepository(session)
        self._fanout = PlanCustomerGrowthNotificationFanoutUseCase(session)
        self._mobile_users = MobileUserRepository(session)

    async def resend(
        self,
        *,
        delivery_id: UUID,
        admin_user_id: UUID | None = None,
        reason_code: str | None = None,
        event_type: str = "admin_resend_requested",
        event_note: str | None = None,
    ) -> CustomerGrowthNotificationDeliveryContext:
        delivery, queue_entry, user = await self._load_context(delivery_id)
        now = datetime.now(UTC)
        previous_status = delivery.delivery_status

        if delivery.delivery_channel == "in_app":
            raise ValueError("in_app_not_resendable")

        self._refresh_delivery_payload_from_user(delivery=delivery, user=user)
        delivery.status_reason = reason_code or None
        delivery.planned_at = now
        delivery.delivered_at = None

        if delivery.delivery_channel == "email":
            recipient_email = str((delivery.delivery_payload or {}).get("recipient_email") or "").strip()
            if not recipient_email:
                raise ValueError("email_unavailable")
            delivery.delivery_status = "planned"
            await self._deliveries.create_event(
                delivery=delivery,
                event_type=event_type,
                reason_code=delivery.status_reason,
                event_payload={
                    "channel": delivery.delivery_channel,
                    "previous_status": previous_status,
                    "next_status": delivery.delivery_status,
                },
                event_note=event_note,
                created_by_admin_user_id=admin_user_id,
                occurred_at=now,
            )
            return CustomerGrowthNotificationDeliveryContext(delivery=delivery, telegram_queue=queue_entry)

        telegram_id = int((delivery.delivery_payload or {}).get("telegram_id") or 0)
        if telegram_id <= 0:
            raise ValueError("telegram_unlinked")

        new_queue_entry = NotificationQueue(
            telegram_id=telegram_id,
            message=_telegram_message_from_delivery(delivery),
            notification_type=f"growth:{delivery.notification_kind}",
            status="pending",
            scheduled_at=now,
        )
        self._session.add(new_queue_entry)
        await self._session.flush()

        delivery.delivery_status = "queued"
        delivery.notification_queue_id = new_queue_entry.id
        await self._deliveries.create_event(
            delivery=delivery,
            event_type=event_type,
            reason_code=delivery.status_reason,
            event_payload={
                "channel": delivery.delivery_channel,
                "previous_status": previous_status,
                "next_status": delivery.delivery_status,
                "queue_recreated": True,
            },
            notification_queue_id=new_queue_entry.id,
            event_note=event_note,
            created_by_admin_user_id=admin_user_id,
            occurred_at=now,
        )
        return CustomerGrowthNotificationDeliveryContext(delivery=delivery, telegram_queue=new_queue_entry)

    async def recover_after_repair(
        self,
        *,
        delivery_id: UUID,
        repair_trigger: str,
        surface: str,
        admin_user_id: UUID | None = None,
        reason_code: str | None = None,
        event_note: str | None = None,
    ) -> CustomerGrowthNotificationDeliveryContext:
        delivery, queue_entry, user = await self._load_context(delivery_id)
        if delivery.delivery_status == "delivered":
            raise ValueError("already_delivered")

        await self._deliveries.create_event(
            delivery=delivery,
            event_type="repair_completed",
            reason_code=reason_code or repair_trigger,
            event_payload={
                "channel": delivery.delivery_channel,
                "repair_trigger": repair_trigger,
                "previous_status": delivery.delivery_status,
            },
            event_note=event_note,
            created_by_admin_user_id=admin_user_id,
            occurred_at=datetime.now(UTC),
        )
        observe_growth_notification_repair_completed(
            delivery_channel=delivery.delivery_channel,
            repair_trigger=repair_trigger,
            surface=surface,
            result="accepted",
        )
        log_growth_code_event(
            "growth_notification.repair_completed",
            surface=surface,
            action_context="growth_notification_repair",
            result="accepted",
            reward_type="growth_notification",
            delivery_channel=delivery.delivery_channel,
            repair_trigger=repair_trigger,
            delivery_id=str(delivery.id),
        )

        if delivery.delivery_channel == "in_app":
            now = datetime.now(UTC)
            delivery.delivery_status = "delivered"
            delivery.status_reason = None
            delivery.delivered_at = now
            delivery.planned_at = now
            await self._deliveries.create_event(
                delivery=delivery,
                event_type="delivery_recovered",
                reason_code=reason_code or repair_trigger,
                event_payload={
                    "channel": delivery.delivery_channel,
                    "recovery_kind": "delivered",
                    "repair_trigger": repair_trigger,
                },
                event_note="In-app delivery became visible again after repair.",
                created_by_admin_user_id=admin_user_id,
                occurred_at=now,
            )
            observe_growth_notification_delivery_recovered(
                delivery_channel=delivery.delivery_channel,
                recovery_kind="delivered",
                surface=surface,
                result="accepted",
            )
            log_growth_code_event(
                "growth_notification.delivery_recovered",
                surface=surface,
                action_context="growth_notification_repair",
                result="accepted",
                reward_type="growth_notification",
                delivery_channel=delivery.delivery_channel,
                recovery_kind="delivered",
                delivery_id=str(delivery.id),
            )
            return CustomerGrowthNotificationDeliveryContext(delivery=delivery, telegram_queue=queue_entry)

        context = await self.resend(
            delivery_id=delivery.id,
            admin_user_id=admin_user_id,
            reason_code=reason_code or repair_trigger,
            event_type="delivery_recovered",
            event_note=event_note or "Delivery was re-armed after a completed repair action.",
        )
        observe_growth_notification_delivery_recovered(
            delivery_channel=context.delivery.delivery_channel,
            recovery_kind=context.delivery.delivery_status,
            surface=surface,
            result="accepted",
        )
        log_growth_code_event(
            "growth_notification.delivery_recovered",
            surface=surface,
            action_context="growth_notification_repair",
            result="accepted",
            reward_type="growth_notification",
            delivery_channel=context.delivery.delivery_channel,
            recovery_kind=context.delivery.delivery_status,
            delivery_id=str(context.delivery.id),
        )
        return context

    async def resolve(
        self,
        *,
        delivery_id: UUID,
        admin_user_id: UUID | None = None,
        reason_code: str | None = None,
    ) -> CustomerGrowthNotificationDeliveryContext:
        delivery, queue_entry, _ = await self._load_context(delivery_id)
        if delivery.delivery_status == "delivered":
            raise ValueError("delivery_already_delivered")

        resolved_reason = reason_code or "support_resolved"
        await self._deliveries.create_event(
            delivery=delivery,
            event_type="support_resolved",
            reason_code=resolved_reason,
            event_payload={
                "channel": delivery.delivery_channel,
                "previous_status": delivery.delivery_status,
            },
            event_note="Support resolved the delivery escalation and requested recovery.",
            created_by_admin_user_id=admin_user_id,
            occurred_at=datetime.now(UTC),
        )
        observe_growth_notification_support_resolution(
            delivery_channel=delivery.delivery_channel,
            reason_code=resolved_reason,
            surface=ADMIN_GROWTH_SURFACE,
            result="accepted",
        )
        log_growth_code_event(
            "growth_notification.support_resolved",
            surface=ADMIN_GROWTH_SURFACE,
            action_context="growth_notification_support_resolution",
            result="accepted",
            reward_type="growth_notification",
            delivery_channel=delivery.delivery_channel,
            delivery_id=str(delivery.id),
        )

        context = await self.recover_after_repair(
            delivery_id=delivery.id,
            repair_trigger="support_resolved",
            surface=ADMIN_GROWTH_SURFACE,
            admin_user_id=admin_user_id,
            reason_code=resolved_reason,
            event_note="Support resolved the delivery issue and re-armed the blocked channel.",
        )
        context.closure_deliveries = await self._send_customer_closure_notification(
            delivery=context.delivery,
            admin_user_id=admin_user_id,
            closure_kind="support_resolved",
        )
        return context

    async def pause(
        self,
        *,
        delivery_id: UUID,
        admin_user_id: UUID | None = None,
        reason_code: str | None = None,
    ) -> CustomerGrowthNotificationDeliveryContext:
        delivery, queue_entry, _ = await self._load_context(delivery_id)
        if delivery.delivery_status == "delivered":
            raise ValueError("delivery_already_delivered")

        delivery.delivery_status = "paused"
        delivery.status_reason = reason_code or "paused_by_admin"
        if queue_entry is not None and queue_entry.status in {"pending", "processing"}:
            queue_entry.status = "cancelled"
            queue_entry.error_message = delivery.status_reason
        await self._deliveries.create_event(
            delivery=delivery,
            event_type="admin_paused",
            reason_code=delivery.status_reason,
            event_payload={"channel": delivery.delivery_channel},
            created_by_admin_user_id=admin_user_id,
        )
        return CustomerGrowthNotificationDeliveryContext(delivery=delivery, telegram_queue=queue_entry)

    async def revoke(
        self,
        *,
        delivery_id: UUID,
        admin_user_id: UUID | None = None,
        reason_code: str | None = None,
    ) -> CustomerGrowthNotificationDeliveryContext:
        delivery, queue_entry, _ = await self._load_context(delivery_id)
        if delivery.delivery_status == "delivered":
            raise ValueError("delivery_already_delivered")

        delivery.delivery_status = "revoked"
        delivery.status_reason = reason_code or "revoked_by_admin"
        if queue_entry is not None and queue_entry.status in {"pending", "processing"}:
            queue_entry.status = "cancelled"
            queue_entry.error_message = delivery.status_reason
        await self._deliveries.create_event(
            delivery=delivery,
            event_type="admin_revoked",
            reason_code=delivery.status_reason,
            event_payload={"channel": delivery.delivery_channel},
            created_by_admin_user_id=admin_user_id,
        )
        return CustomerGrowthNotificationDeliveryContext(delivery=delivery, telegram_queue=queue_entry)

    async def _load_context(
        self,
        delivery_id: UUID,
    ) -> tuple[CustomerGrowthNotificationDeliveryModel, NotificationQueue | None, object]:
        delivery = await self._deliveries.get_by_id(delivery_id)
        if delivery is None:
            raise ValueError("delivery_not_found")
        queue_entry = None
        if delivery.notification_queue_id is not None:
            queue_entry = await self._session.get(NotificationQueue, delivery.notification_queue_id)
        user = await self._mobile_users.get_by_id(delivery.mobile_user_id)
        if user is None:
            raise ValueError("customer_not_found")
        return delivery, queue_entry, user

    def _refresh_delivery_payload_from_user(self, *, delivery, user) -> None:
        payload = dict(delivery.delivery_payload or {})
        payload["channel"] = delivery.delivery_channel
        if delivery.delivery_channel == "email":
            payload["recipient_email"] = str(getattr(user, "email", "") or "").strip()
        if delivery.delivery_channel == "telegram":
            payload["telegram_id"] = getattr(user, "telegram_id", None)
        delivery.delivery_payload = payload

    async def _send_customer_closure_notification(
        self,
        *,
        delivery: CustomerGrowthNotificationDeliveryModel,
        admin_user_id: UUID | None,
        closure_kind: str,
    ) -> list[CustomerGrowthNotificationDeliveryModel]:
        route_slug = str((delivery.delivery_payload or {}).get("route_slug") or "/referral")
        channel_label = delivery.delivery_channel.replace("_", " ").title()
        if closure_kind == "support_resolved":
            title = "Delivery issue resolved"
            message = (
                f"Support restored {channel_label.lower()} delivery for "
                f"\"{delivery.title}\"."
            )
            notes = [
                f"Channel: {channel_label}.",
                "Future growth updates can now continue on this route.",
            ]
        else:
            title = "Delivery channel restored"
            message = (
                f"{channel_label} delivery for \"{delivery.title}\" is available again."
            )
            notes = [f"Channel: {channel_label}."]

        locale = str((delivery.delivery_payload or {}).get("locale") or "en-EN")
        return await self._fanout.execute(
            mobile_user_id=delivery.mobile_user_id,
            notification_key=admin_manual_notification_key(uuid4()),
            notification_kind="admin_manual_update",
            title=title,
            message=message,
            route_slug=route_slug,
            notes=notes,
            source_kind="growth_notification_closure",
            source_id=str(delivery.id),
            created_by_admin_user_id=admin_user_id,
            locale=locale,
            allowed_channels={"in_app"},
            ignore_preferences=False,
        )


def _telegram_message_from_delivery(delivery: CustomerGrowthNotificationDeliveryModel) -> str:
    route_slug = str((delivery.delivery_payload or {}).get("route_slug") or "").strip()
    message = f"<b>{escape(delivery.title)}</b>\n{escape(delivery.message)}"
    if route_slug:
        return f"{message}\nOpen: {escape(route_slug)}"
    return message
