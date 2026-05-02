"""Customer-safe troubleshooting and recovery surface for growth notifications."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.notification_queue_model import NotificationQueue
from src.infrastructure.database.repositories.customer_growth_notification_delivery_repository import (
    CustomerGrowthNotificationDeliveryRepository,
)
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.monitoring.instrumentation.growth_codes import (
    CUSTOMER_REDEEM_SURFACE,
    log_growth_code_event,
    observe_growth_notification_customer_recovery_request,
    observe_growth_notification_support_escalation,
)

from .admin_controls import ManageCustomerGrowthNotificationDeliveryUseCase
from .catalog import category_for_growth_notification_kind, normalize_growth_notification_key
from .preferences import (
    build_customer_growth_notification_preferences,
    growth_notification_pref_enabled,
)


@dataclass(frozen=True)
class CustomerGrowthNotificationDeliveryEventView:
    event_type: str
    occurred_at: datetime | None
    summary: str


@dataclass(frozen=True)
class CustomerGrowthNotificationRepairTarget:
    kind: str
    summary: str


@dataclass(frozen=True)
class CustomerGrowthNotificationDeliveryView:
    delivery: Any
    queue_snapshot: NotificationQueue | None
    troubleshooting_state: str
    customer_message_key: str
    customer_summary: str
    recovery_allowed: bool
    support_required: bool
    recovery_block_reason: str | None
    repair_target: CustomerGrowthNotificationRepairTarget | None
    events: list[CustomerGrowthNotificationDeliveryEventView]


@dataclass(frozen=True)
class CustomerGrowthNotificationSupportHandoff:
    reference_code: str
    troubleshooting_summary: str
    copy_text: str
    suggested_escalation_channel: str
    contact_subject: str
    contact_body: str


@dataclass(frozen=True)
class CustomerGrowthNotificationSurfaceDetail:
    deliveries: list[CustomerGrowthNotificationDeliveryView]
    support_handoff: CustomerGrowthNotificationSupportHandoff


class GetCustomerGrowthNotificationSurfaceDetailUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._deliveries = CustomerGrowthNotificationDeliveryRepository(session)
        self._mobile_users = MobileUserRepository(session)

    async def execute(
        self,
        *,
        mobile_user_id: UUID,
        notification_key: str,
        title: str,
        route_slug: str,
    ) -> CustomerGrowthNotificationSurfaceDetail:
        notification_key = normalize_growth_notification_key(notification_key)
        user = await self._mobile_users.get_by_id(mobile_user_id)
        if user is None:
            raise ValueError("customer_not_found")

        deliveries = await self._deliveries.list_by_user_notification_key(
            mobile_user_id=mobile_user_id,
            notification_key=notification_key,
        )
        delivery_events = await self._deliveries.list_events_for_delivery_ids([delivery.id for delivery in deliveries])
        events_by_delivery_id: dict[UUID, list[Any]] = {}
        for item in delivery_events:
            events_by_delivery_id.setdefault(item.delivery_id, []).append(item)

        prefs = build_customer_growth_notification_preferences(user.notification_prefs)
        delivery_views: list[CustomerGrowthNotificationDeliveryView] = []
        for delivery in sorted(deliveries, key=_delivery_sort_key):
            queue_snapshot = None
            if delivery.notification_queue_id is not None:
                queue_snapshot = await self._session.get(NotificationQueue, delivery.notification_queue_id)

            channel_events = events_by_delivery_id.get(delivery.id, [])
            state = _build_customer_delivery_state(
                delivery=delivery,
                queue_snapshot=queue_snapshot,
                pref_enabled=growth_notification_pref_enabled(
                    prefs,
                    category=category_for_growth_notification_kind(delivery.notification_kind),
                    channel=delivery.delivery_channel,
                ),
                channel_available=_channel_available(user=user, channel=delivery.delivery_channel),
            )
            delivery_views.append(
                CustomerGrowthNotificationDeliveryView(
                    delivery=delivery,
                    queue_snapshot=queue_snapshot,
                    troubleshooting_state=state["troubleshooting_state"],
                    customer_message_key=state["customer_message_key"],
                    customer_summary=state["customer_summary"],
                    recovery_allowed=bool(state["recovery_allowed"]),
                    support_required=bool(state["support_required"]),
                    recovery_block_reason=state["recovery_block_reason"],
                    repair_target=_build_repair_target(state=state),
                    events=[
                        CustomerGrowthNotificationDeliveryEventView(
                            event_type=event.event_type,
                            occurred_at=event.occurred_at,
                            summary=_event_summary(event_type=event.event_type, channel=delivery.delivery_channel),
                        )
                        for event in channel_events
                    ],
                )
            )

        return CustomerGrowthNotificationSurfaceDetail(
            deliveries=delivery_views,
            support_handoff=_build_support_handoff(
                notification_key=notification_key,
                title=title,
                route_slug=route_slug,
                deliveries=delivery_views,
            ),
        )


class RequestCustomerGrowthNotificationRecoveryUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._deliveries = CustomerGrowthNotificationDeliveryRepository(session)
        self._mobile_users = MobileUserRepository(session)
        self._manage = ManageCustomerGrowthNotificationDeliveryUseCase(session)

    async def execute(
        self,
        *,
        mobile_user_id: UUID,
        notification_key: str,
        delivery_channel: str,
    ) -> Any:
        notification_key = normalize_growth_notification_key(notification_key)
        user = await self._mobile_users.get_by_id(mobile_user_id)
        if user is None:
            raise ValueError("customer_not_found")

        delivery = await self._deliveries.get_by_user_key_channel(
            mobile_user_id=mobile_user_id,
            notification_key=notification_key,
            delivery_channel=delivery_channel,
        )
        if delivery is None:
            raise ValueError("delivery_not_found")

        queue_snapshot = None
        if delivery.notification_queue_id is not None:
            queue_snapshot = await self._session.get(NotificationQueue, delivery.notification_queue_id)

        prefs = build_customer_growth_notification_preferences(user.notification_prefs)
        state = _build_customer_delivery_state(
            delivery=delivery,
            queue_snapshot=queue_snapshot,
            pref_enabled=growth_notification_pref_enabled(
                prefs,
                category=category_for_growth_notification_kind(delivery.notification_kind),
                channel=delivery.delivery_channel,
            ),
            channel_available=_channel_available(user=user, channel=delivery.delivery_channel),
        )
        if not bool(state["recovery_allowed"]):
            raise ValueError(str(state["recovery_block_reason"] or "delivery_not_recoverable"))

        context = await self._manage.resend(
            delivery_id=delivery.id,
            reason_code="customer_recovery_requested",
            event_type="customer_recovery_requested",
            event_note="Customer requested another delivery attempt from the rewards surface.",
        )
        observe_growth_notification_customer_recovery_request(
            delivery_channel=delivery.delivery_channel,
            troubleshooting_state=str(state["troubleshooting_state"]),
            surface=CUSTOMER_REDEEM_SURFACE,
            result="accepted",
        )
        log_growth_code_event(
            "growth_notification.customer_recovery_requested",
            surface=CUSTOMER_REDEEM_SURFACE,
            action_context="growth_notification_recovery",
            result="accepted",
            reward_type="growth_notification",
            delivery_channel=delivery.delivery_channel,
            notification_key=notification_key,
            troubleshooting_state=str(state["troubleshooting_state"]),
        )
        return context.delivery


class EscalateCustomerGrowthNotificationSupportUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._deliveries = CustomerGrowthNotificationDeliveryRepository(session)
        self._mobile_users = MobileUserRepository(session)

    async def execute(
        self,
        *,
        mobile_user_id: UUID,
        notification_key: str,
        delivery_channel: str | None,
        escalation_channel: str,
    ) -> list[Any]:
        notification_key = normalize_growth_notification_key(notification_key)
        user = await self._mobile_users.get_by_id(mobile_user_id)
        if user is None:
            raise ValueError("customer_not_found")

        deliveries = await self._deliveries.list_by_user_notification_key(
            mobile_user_id=mobile_user_id,
            notification_key=notification_key,
        )
        if delivery_channel is not None:
            deliveries = [item for item in deliveries if item.delivery_channel == delivery_channel]
        if not deliveries:
            raise ValueError("delivery_not_found")

        prefs = build_customer_growth_notification_preferences(user.notification_prefs)
        escalated: list[Any] = []
        for delivery in deliveries:
            queue_snapshot = None
            if delivery.notification_queue_id is not None:
                queue_snapshot = await self._session.get(NotificationQueue, delivery.notification_queue_id)
            state = _build_customer_delivery_state(
                delivery=delivery,
                queue_snapshot=queue_snapshot,
                pref_enabled=growth_notification_pref_enabled(
                    prefs,
                    category=category_for_growth_notification_kind(delivery.notification_kind),
                    channel=delivery.delivery_channel,
                ),
                channel_available=_channel_available(user=user, channel=delivery.delivery_channel),
            )
            if not bool(state["support_required"]):
                continue

            await self._deliveries.create_event(
                delivery=delivery,
                event_type="customer_support_escalation_requested",
                reason_code=state["recovery_block_reason"],
                event_payload={
                    "channel": delivery.delivery_channel,
                    "escalation_channel": escalation_channel,
                    "troubleshooting_state": state["troubleshooting_state"],
                },
                event_note="Customer requested guided support escalation from the rewards surface.",
            )
            observe_growth_notification_support_escalation(
                delivery_channel=delivery.delivery_channel,
                troubleshooting_state=str(state["troubleshooting_state"]),
                escalation_channel=escalation_channel,
                surface=CUSTOMER_REDEEM_SURFACE,
                result="accepted",
            )
            log_growth_code_event(
                "growth_notification.support_escalation_requested",
                surface=CUSTOMER_REDEEM_SURFACE,
                action_context="growth_notification_support_escalation",
                result="accepted",
                reward_type="growth_notification",
                delivery_channel=delivery.delivery_channel,
                escalation_channel=escalation_channel,
                notification_key=notification_key,
                troubleshooting_state=str(state["troubleshooting_state"]),
            )
            escalated.append(delivery)

        if not escalated:
            raise ValueError("support_escalation_not_required")
        return escalated


def _delivery_sort_key(delivery: Any) -> tuple[int, datetime]:
    order = {
        "in_app": 0,
        "email": 1,
        "telegram": 2,
    }
    return (
        order.get(str(getattr(delivery, "delivery_channel", "")), 99),
        getattr(delivery, "planned_at", getattr(delivery, "created_at", datetime.min)),
    )


def _channel_label(channel: str) -> str:
    labels = {
        "in_app": "In-app",
        "email": "Email",
        "telegram": "Telegram",
    }
    return labels.get(channel, channel.replace("_", " ").title())


def _channel_available(*, user: Any, channel: str) -> bool:
    if channel == "email":
        return bool(getattr(user, "email", "").strip())
    if channel == "telegram":
        return getattr(user, "telegram_id", None) is not None
    return True


def _event_summary(*, event_type: str, channel: str) -> str:
    channel_label = _channel_label(channel)
    summaries = {
        "fanout_delivered": f"{channel_label} delivery completed.",
        "fanout_planned": f"{channel_label} delivery prepared.",
        "fanout_queued": f"{channel_label} delivery queued.",
        "fanout_skipped": f"{channel_label} delivery skipped.",
        "email_processing_started": "Email delivery started.",
        "email_delivered": "Email delivered.",
        "email_failed": "Email delivery failed.",
        "telegram_processing_started": "Telegram delivery started.",
        "telegram_delivered": "Telegram delivered.",
        "telegram_retry_scheduled": "Telegram retry scheduled.",
        "telegram_failed": "Telegram delivery failed.",
        "admin_paused": "Support paused this delivery.",
        "admin_revoked": "Support revoked this delivery.",
        "admin_resend_requested": "Support requested another send.",
        "repair_completed": "A repair action completed for this delivery.",
        "support_resolved": "Support resolved the delivery issue.",
        "delivery_recovered": "Delivery was re-armed after repair.",
        "customer_recovery_requested": "You requested another send.",
        "customer_support_escalation_requested": "You opened a guided support escalation.",
    }
    return summaries.get(event_type, f"{channel_label} delivery updated.")


def _build_repair_target(*, state: dict[str, Any]) -> CustomerGrowthNotificationRepairTarget | None:
    reason = str(state.get("recovery_block_reason") or "")
    troubleshooting_state = str(state.get("troubleshooting_state") or "")

    if reason == "preference_disabled":
        return CustomerGrowthNotificationRepairTarget(
            kind="notification_preferences",
            summary="Turn this delivery channel back on in notification preferences.",
        )
    if reason == "telegram_unlinked":
        return CustomerGrowthNotificationRepairTarget(
            kind="telegram_link",
            summary="Link Telegram to this account before requesting another Telegram send.",
        )
    if reason == "email_unavailable":
        return CustomerGrowthNotificationRepairTarget(
            kind="profile_review",
            summary="Review your account profile and support routing before trying email delivery again.",
        )
    if troubleshooting_state in {"paused_admin", "revoked_admin", "unknown"} or bool(
        state.get("support_required")
    ):
        return CustomerGrowthNotificationRepairTarget(
            kind="support_contact",
            summary="Open official support with the structured reference below.",
        )
    return None


def _build_customer_delivery_state(
    *,
    delivery: Any,
    queue_snapshot: NotificationQueue | None,
    pref_enabled: bool,
    channel_available: bool,
) -> dict[str, Any]:
    delivery_status = str(getattr(delivery, "delivery_status", "unknown"))
    status_reason = str(getattr(delivery, "status_reason", "") or "")
    delivery_channel = str(getattr(delivery, "delivery_channel", ""))
    channel_label = _channel_label(delivery_channel)
    queue_error = queue_snapshot.error_message if queue_snapshot is not None else None

    if delivery_status == "delivered":
        return {
            "troubleshooting_state": "delivered",
            "customer_message_key": "growth_notifications.delivery.delivered",
            "customer_summary": f"{channel_label} delivery completed successfully.",
            "recovery_allowed": False,
            "support_required": False,
            "recovery_block_reason": "already_delivered",
            "support_summary": "Delivery completed successfully on the selected channel.",
        }
    if delivery_status in {"queued", "processing", "planned"}:
        return {
            "troubleshooting_state": "in_progress",
            "customer_message_key": "growth_notifications.delivery.pending",
            "customer_summary": f"{channel_label} delivery is still in progress.",
            "recovery_allowed": False,
            "support_required": False,
            "recovery_block_reason": "already_in_progress",
            "support_summary": "Delivery is still queued or being processed.",
        }
    if delivery_status == "revoked":
        return {
            "troubleshooting_state": "revoked_admin",
            "customer_message_key": "growth_notifications.delivery.revoked",
            "customer_summary": f"{channel_label} delivery was revoked during review.",
            "recovery_allowed": False,
            "support_required": True,
            "recovery_block_reason": "revoked_by_admin",
            "support_summary": status_reason or "Delivery was revoked by an operator before customer receipt.",
        }
    if delivery_status == "paused":
        return {
            "troubleshooting_state": "paused_admin",
            "customer_message_key": "growth_notifications.delivery.paused",
            "customer_summary": f"{channel_label} delivery is paused while support reviews it.",
            "recovery_allowed": False,
            "support_required": True,
            "recovery_block_reason": "paused_by_admin",
            "support_summary": status_reason or "Delivery is paused pending operator review.",
        }
    if delivery_status == "skipped":
        if status_reason == "preference_disabled":
            return {
                "troubleshooting_state": "suppressed",
                "customer_message_key": "growth_notifications.delivery.unavailable",
                "customer_summary": (
                    f"{channel_label} delivery was skipped because this channel is turned off in your preferences."
                ),
                "recovery_allowed": bool(pref_enabled and channel_available and delivery_channel != "in_app"),
                "support_required": False,
                "recovery_block_reason": (
                    None
                    if pref_enabled and channel_available and delivery_channel != "in_app"
                    else "preference_disabled"
                ),
                "support_summary": "Delivery was intentionally skipped because the channel was disabled.",
            }
        if status_reason == "telegram_unlinked":
            return {
                "troubleshooting_state": "suppressed",
                "customer_message_key": "growth_notifications.delivery.unavailable",
                "customer_summary": "Telegram delivery is unavailable until Telegram is linked to this account.",
                "recovery_allowed": False,
                "support_required": True,
                "recovery_block_reason": "telegram_unlinked",
                "support_summary": "Delivery was skipped because Telegram is not linked for this customer.",
            }
        if status_reason == "email_unavailable":
            return {
                "troubleshooting_state": "suppressed",
                "customer_message_key": "growth_notifications.delivery.unavailable",
                "customer_summary": "Email delivery is unavailable for this account right now.",
                "recovery_allowed": False,
                "support_required": True,
                "recovery_block_reason": "email_unavailable",
                "support_summary": "Delivery was skipped because email is unavailable for this customer.",
            }
        return {
            "troubleshooting_state": "suppressed",
            "customer_message_key": "growth_notifications.delivery.unavailable",
            "customer_summary": f"{channel_label} delivery is currently unavailable.",
            "recovery_allowed": False,
            "support_required": True,
            "recovery_block_reason": "delivery_unavailable",
            "support_summary": status_reason
            or "Delivery was intentionally skipped because the channel was unavailable or disabled.",
        }
    if delivery_status == "failed":
        return {
            "troubleshooting_state": "actionable_retry",
            "customer_message_key": "growth_notifications.delivery.retry_available",
            "customer_summary": (
                f"{channel_label} delivery failed. You can request another send."
                if pref_enabled and channel_available and delivery_channel != "in_app"
                else f"{channel_label} delivery failed and needs support review."
            ),
            "recovery_allowed": bool(pref_enabled and channel_available and delivery_channel != "in_app"),
            "support_required": not bool(pref_enabled and channel_available and delivery_channel != "in_app"),
            "recovery_block_reason": (
                None
                if pref_enabled and channel_available and delivery_channel != "in_app"
                else "delivery_not_recoverable"
            ),
            "support_summary": queue_error
            or status_reason
            or "Channel delivery failed and can be retried after review.",
        }

    return {
        "troubleshooting_state": "unknown",
        "customer_message_key": "growth_notifications.delivery.unknown",
        "customer_summary": f"{channel_label} delivery needs support review.",
        "recovery_allowed": False,
        "support_required": True,
        "recovery_block_reason": "unknown_delivery_state",
        "support_summary": status_reason or "Delivery state requires manual inspection.",
    }


def _build_support_handoff(
    *,
    notification_key: str,
    title: str,
    route_slug: str,
    deliveries: list[CustomerGrowthNotificationDeliveryView],
) -> CustomerGrowthNotificationSupportHandoff:
    reference_code = f"GROWTH::{notification_key}"
    if deliveries:
        troubleshooting_summary = " | ".join(
            f"{_channel_label(item.delivery.delivery_channel)}: {item.troubleshooting_state}" for item in deliveries
        )
    else:
        troubleshooting_summary = "No external delivery records are attached to this growth notice."

    copy_lines = [
        f"Reference: {reference_code}",
        f"Title: {title}",
        f"Route: {route_slug}",
        f"Summary: {troubleshooting_summary}",
    ]
    if deliveries:
        copy_lines.append("Channel states:")
        copy_lines.extend(
            f"- {_channel_label(item.delivery.delivery_channel)}: {item.customer_summary}" for item in deliveries
        )

    suggested_escalation_channel = _suggested_escalation_channel(deliveries)
    contact_subject = f"[{reference_code}] Growth delivery issue"
    contact_body = "\n".join(
        [
            "Hello CyberVPN support,",
            "",
            "I need help with a growth notification delivery.",
            "",
            *copy_lines,
        ]
    )

    return CustomerGrowthNotificationSupportHandoff(
        reference_code=reference_code,
        troubleshooting_summary=troubleshooting_summary,
        copy_text="\n".join(copy_lines),
        suggested_escalation_channel=suggested_escalation_channel,
        contact_subject=contact_subject,
        contact_body=contact_body,
    )


def _suggested_escalation_channel(deliveries: list[CustomerGrowthNotificationDeliveryView]) -> str:
    if any(item.troubleshooting_state in {"paused_admin", "revoked_admin"} for item in deliveries):
        return "contact_form"
    if any(
        item.recovery_block_reason in {"email_unavailable", "delivery_unavailable", "unknown_delivery_state"}
        for item in deliveries
    ):
        return "support_email"
    return "telegram_support"
