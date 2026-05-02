"""Plan customer growth notification fanout across in-app, email, and Telegram."""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.notification_queue_model import NotificationQueue
from src.infrastructure.database.repositories.customer_growth_notification_delivery_repository import (
    CustomerGrowthNotificationDeliveryRepository,
)
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository

from .catalog import category_for_growth_notification_kind, normalize_growth_notification_key
from .preferences import (
    GROWTH_NOTIFICATION_CHANNEL_EMAIL,
    GROWTH_NOTIFICATION_CHANNEL_IN_APP,
    GROWTH_NOTIFICATION_CHANNEL_TELEGRAM,
    build_customer_growth_notification_preferences,
    growth_notification_pref_enabled,
)


class PlanCustomerGrowthNotificationFanoutUseCase:
    """Persist delivery intent for customer growth notifications."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._deliveries = CustomerGrowthNotificationDeliveryRepository(session)
        self._mobile_users = MobileUserRepository(session)

    async def execute(
        self,
        *,
        mobile_user_id: UUID,
        notification_key: str,
        notification_kind: str,
        title: str,
        message: str,
        route_slug: str = "/referral",
        notes: list[str] | None = None,
        source_kind: str | None = None,
        source_id: str | None = None,
        created_by_admin_user_id: UUID | None = None,
        locale: str = "en-EN",
        allowed_channels: set[str] | None = None,
        ignore_preferences: bool = False,
    ) -> list:
        user = await self._mobile_users.get_by_id(mobile_user_id)
        if user is None:
            return []

        now = datetime.now(UTC)
        category = category_for_growth_notification_kind(notification_kind)
        prefs = build_customer_growth_notification_preferences(user.notification_prefs)
        normalized_key = normalize_growth_notification_key(notification_key)
        notes_payload = list(notes or [])

        created_items = []
        async def _persist(
            *,
            channel: str,
            delivery_status: str,
            event_type: str,
            payload: dict,
            status_reason: str | None = None,
            notification_queue_id: UUID | None = None,
            delivered_at: datetime | None = None,
        ):
            delivery = await self._deliveries.upsert_delivery(
                mobile_user_id=mobile_user_id,
                notification_key=normalized_key,
                notification_kind=notification_kind,
                delivery_channel=channel,
                delivery_status=delivery_status,
                status_reason=status_reason,
                title=title,
                message=message,
                delivery_payload=payload,
                source_kind=source_kind,
                source_id=source_id,
                notification_queue_id=notification_queue_id,
                created_by_admin_user_id=created_by_admin_user_id,
                planned_at=now,
                delivered_at=delivered_at,
            )
            await self._deliveries.create_event(
                delivery=delivery,
                event_type=event_type,
                reason_code=status_reason,
                event_payload={
                    "channel": channel,
                    "route_slug": payload.get("route_slug"),
                    "category": payload.get("category"),
                    "fanout_stage": event_type,
                },
                notification_queue_id=notification_queue_id,
                created_by_admin_user_id=created_by_admin_user_id,
                occurred_at=now,
            )
            created_items.append(delivery)

        for channel in (
            GROWTH_NOTIFICATION_CHANNEL_IN_APP,
            GROWTH_NOTIFICATION_CHANNEL_EMAIL,
            GROWTH_NOTIFICATION_CHANNEL_TELEGRAM,
        ):
            if allowed_channels is not None and channel not in allowed_channels:
                continue
            payload = {
                "route_slug": route_slug,
                "notes": notes_payload,
                "category": category,
                "channel": channel,
                "locale": locale,
            }
            pref_enabled = True
            if not ignore_preferences:
                pref_enabled = growth_notification_pref_enabled(
                    prefs,
                    category=category,
                    channel=channel,
                )
            if not pref_enabled:
                await _persist(
                    channel=channel,
                    delivery_status="skipped",
                    event_type="fanout_skipped",
                    payload=payload,
                    status_reason="preference_disabled",
                )
                continue

            if channel == GROWTH_NOTIFICATION_CHANNEL_IN_APP:
                await _persist(
                    channel=channel,
                    delivery_status="delivered",
                    event_type="fanout_delivered",
                    payload=payload,
                    delivered_at=now,
                )
                continue

            if channel == GROWTH_NOTIFICATION_CHANNEL_EMAIL:
                recipient_email = user.email.strip() if user.email else ""
                payload["recipient_email"] = recipient_email
                await _persist(
                    channel=channel,
                    delivery_status="planned" if recipient_email else "skipped",
                    event_type="fanout_planned" if recipient_email else "fanout_skipped",
                    payload=payload,
                    status_reason=None if recipient_email else "email_unavailable",
                )
                continue

            telegram_id = int(user.telegram_id) if user.telegram_id is not None else None
            payload["telegram_id"] = telegram_id
            existing = await self._deliveries.get_by_user_key_channel(
                mobile_user_id=mobile_user_id,
                notification_key=normalized_key,
                delivery_channel=channel,
            )
            queue_id = existing.notification_queue_id if existing is not None else None
            if telegram_id is None:
                await _persist(
                    channel=channel,
                    delivery_status="skipped",
                    event_type="fanout_skipped",
                    payload=payload,
                    status_reason="telegram_unlinked",
                )
                continue

            if queue_id is None:
                queue_entry = NotificationQueue(
                    telegram_id=telegram_id,
                    message=_render_telegram_message(title=title, message=message, route_slug=route_slug),
                    notification_type=f"growth:{notification_kind}",
                    scheduled_at=now,
                )
                self._session.add(queue_entry)
                await self._session.flush()
                queue_id = queue_entry.id

            await _persist(
                channel=channel,
                delivery_status="queued",
                event_type="fanout_queued",
                payload=payload,
                notification_queue_id=queue_id,
            )

        return created_items


def _render_telegram_message(*, title: str, message: str, route_slug: str) -> str:
    safe_title = escape(title)
    safe_message = escape(message)
    safe_route_slug = escape(route_slug)
    base = f"<b>{safe_title}</b>\n{safe_message}"
    if route_slug:
        return f"{base}\nOpen: {safe_route_slug}"
    return base
