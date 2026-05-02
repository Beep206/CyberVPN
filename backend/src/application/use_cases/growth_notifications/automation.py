"""Automatic repair and closure flows for customer growth notification deliveries."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.customer_growth_notification_delivery_model import (
    CustomerGrowthNotificationDeliveryModel,
)
from src.infrastructure.database.repositories.customer_growth_notification_delivery_repository import (
    CustomerGrowthNotificationDeliveryRepository,
)
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.monitoring.instrumentation.growth_codes import (
    CUSTOMER_ACCOUNT_SURFACE,
    log_growth_code_event,
)

from .admin_controls import ManageCustomerGrowthNotificationDeliveryUseCase
from .catalog import admin_manual_notification_key, category_for_growth_notification_kind
from .fanout import PlanCustomerGrowthNotificationFanoutUseCase
from .preferences import build_customer_growth_notification_preferences, growth_notification_pref_enabled


@dataclass(slots=True)
class GrowthNotificationRepairAutomationResult:
    recovered_deliveries: list[CustomerGrowthNotificationDeliveryModel] = field(default_factory=list)
    closure_deliveries: list[CustomerGrowthNotificationDeliveryModel] = field(default_factory=list)


class AutomateCustomerGrowthNotificationRepairUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._deliveries = CustomerGrowthNotificationDeliveryRepository(session)
        self._mobile_users = MobileUserRepository(session)
        self._manage = ManageCustomerGrowthNotificationDeliveryUseCase(session)
        self._fanout = PlanCustomerGrowthNotificationFanoutUseCase(session)

    async def execute(
        self,
        *,
        mobile_user_id: UUID,
        repair_trigger: str,
        surface: str = CUSTOMER_ACCOUNT_SURFACE,
        admin_user_id: UUID | None = None,
    ) -> GrowthNotificationRepairAutomationResult:
        user = await self._mobile_users.get_by_id(mobile_user_id)
        if user is None:
            raise ValueError("customer_not_found")

        prefs = build_customer_growth_notification_preferences(user.notification_prefs)
        candidates = await self._deliveries.list_deliveries(
            mobile_user_id=mobile_user_id,
            limit=200,
            offset=0,
        )
        recovered: list[CustomerGrowthNotificationDeliveryModel] = []
        for delivery in candidates:
            if not self._should_attempt_repair(
                delivery=delivery,
                repair_trigger=repair_trigger,
                prefs=prefs,
                user=user,
            ):
                continue
            try:
                context = await self._manage.recover_after_repair(
                    delivery_id=delivery.id,
                    repair_trigger=repair_trigger,
                    surface=surface,
                    admin_user_id=admin_user_id,
                    reason_code=repair_trigger,
                    event_note="Customer account repair re-armed the blocked delivery.",
                )
            except ValueError:
                continue
            recovered.append(context.delivery)

        closure_deliveries: list[CustomerGrowthNotificationDeliveryModel] = []
        if recovered:
            closure_deliveries = await self._send_repair_closure_notification(
                mobile_user_id=mobile_user_id,
                repair_trigger=repair_trigger,
                recovered=recovered,
                admin_user_id=admin_user_id,
            )
            log_growth_code_event(
                "growth_notification.repair_automation_completed",
                surface=surface,
                action_context="growth_notification_repair_automation",
                result="accepted",
                reward_type="growth_notification",
                repair_trigger=repair_trigger,
                recovered_count=len(recovered),
            )

        return GrowthNotificationRepairAutomationResult(
            recovered_deliveries=recovered,
            closure_deliveries=closure_deliveries,
        )

    def _should_attempt_repair(
        self,
        *,
        delivery: CustomerGrowthNotificationDeliveryModel,
        repair_trigger: str,
        prefs: dict[str, bool],
        user,
    ) -> bool:
        if delivery.source_kind == "growth_notification_closure":
            return False
        status_reason = str(delivery.status_reason or "")
        if repair_trigger == "preferences_reenabled":
            if status_reason != "preference_disabled":
                return False
            return growth_notification_pref_enabled(
                prefs,
                category=category_for_growth_notification_kind(delivery.notification_kind),
                channel=delivery.delivery_channel,
            )
        if repair_trigger == "telegram_linked":
            return status_reason == "telegram_unlinked" and getattr(user, "telegram_id", None) is not None
        if repair_trigger == "contact_data_corrected":
            email = str(getattr(user, "email", "") or "").strip()
            return status_reason == "email_unavailable" and bool(email)
        return False

    async def _send_repair_closure_notification(
        self,
        *,
        mobile_user_id: UUID,
        repair_trigger: str,
        recovered: list[CustomerGrowthNotificationDeliveryModel],
        admin_user_id: UUID | None,
    ) -> list[CustomerGrowthNotificationDeliveryModel]:
        route_slug = str((recovered[0].delivery_payload or {}).get("route_slug") or "/referral")
        locale = str((recovered[0].delivery_payload or {}).get("locale") or "en-EN")
        channels = sorted({delivery.delivery_channel for delivery in recovered})
        channel_summary = ", ".join(channel.replace("_", " ") for channel in channels)
        recovered_count = len(recovered)

        if repair_trigger == "telegram_linked":
            title = "Telegram delivery restored"
            message = "Telegram growth updates can be delivered again."
        elif repair_trigger == "contact_data_corrected":
            title = "Email delivery restored"
            message = "Email growth updates can be delivered again."
        else:
            title = "Delivery channel restored"
            message = "Growth notification delivery resumed after you updated your notification settings."

        notes = [
            f"Recovered deliveries: {recovered_count}.",
            f"Channels: {channel_summary}.",
        ]
        return await self._fanout.execute(
            mobile_user_id=mobile_user_id,
            notification_key=admin_manual_notification_key(uuid4()),
            notification_kind="admin_manual_update",
            title=title,
            message=message,
            route_slug=route_slug,
            notes=notes,
            source_kind="growth_notification_closure",
            source_id=str(recovered[0].id),
            created_by_admin_user_id=admin_user_id,
            locale=locale,
            allowed_channels={"in_app"},
            ignore_preferences=False,
        )
