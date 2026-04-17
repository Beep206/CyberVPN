"""Pricing entitlements calculation for plans, add-ons, and trial."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.plan_addon_repo import PlanAddonRepository, SubscriptionAddonRepository
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository


class EntitlementsService:
    TRIAL_PERIOD_DAYS = 7

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._payments = PaymentRepository(session)
        self._plans = SubscriptionPlanRepository(session)
        self._addons = PlanAddonRepository(session)
        self._subscription_addons = SubscriptionAddonRepository(session)
        self._users = MobileUserRepository(session)

    @staticmethod
    def build_snapshot(
        *,
        plan,
        addon_lines: list[dict] | None = None,
        expires_at: datetime | None = None,
        is_trial: bool = False,
        status: str | None = None,
    ) -> dict:
        addon_lines = addon_lines or []
        device_limit = int(plan.device_limit)
        dedicated_ip_count = int((plan.dedicated_ip or {}).get("included", 0))

        for line in addon_lines:
            qty = int(line.get("qty", 1))
            delta = line.get("delta_entitlements") or {}
            device_limit += int(delta.get("device_limit", 0)) * qty
            dedicated_ip_count += int(delta.get("dedicated_ip_count", 0)) * qty

        traffic_policy = plan.traffic_policy or {"mode": "fair_use", "display_label": "Unlimited"}
        return {
            "status": status or ("trial" if is_trial else "active"),
            "plan_uuid": str(plan.id),
            "plan_code": plan.plan_code,
            "display_name": plan.display_name or plan.name,
            "period_days": plan.duration_days,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "effective_entitlements": {
                "device_limit": device_limit,
                "traffic_policy": traffic_policy.get("mode", "fair_use"),
                "display_traffic_label": traffic_policy.get("display_label", "Unlimited"),
                "connection_modes": plan.connection_modes or [],
                "server_pool": plan.server_pool or [],
                "support_sla": plan.support_sla,
                "dedicated_ip_count": dedicated_ip_count,
            },
            "invite_bundle": plan.invite_bundle or {"count": 0, "friend_days": 0, "expiry_days": 0},
            "is_trial": is_trial,
            "addons": [
                {
                    "code": line.get("code"),
                    "qty": int(line.get("qty", 1)),
                    "location_code": line.get("location_code"),
                }
                for line in addon_lines
            ],
        }

    def build_trial_snapshot(self, *, expires_at: datetime | None = None) -> dict:
        return {
            "status": "trial",
            "plan_uuid": None,
            "plan_code": "trial",
            "display_name": "Trial",
            "period_days": self.TRIAL_PERIOD_DAYS,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "effective_entitlements": {
                "device_limit": 1,
                "traffic_policy": "fair_use",
                "display_traffic_label": "Unlimited",
                "connection_modes": ["standard"],
                "server_pool": ["shared"],
                "support_sla": "standard",
                "dedicated_ip_count": 0,
            },
            "invite_bundle": {"count": 0, "friend_days": 0, "expiry_days": 0},
            "is_trial": True,
            "addons": [],
        }

    @staticmethod
    def build_empty_snapshot() -> dict:
        return {
            "status": "none",
            "plan_uuid": None,
            "plan_code": None,
            "display_name": None,
            "period_days": None,
            "expires_at": None,
            "effective_entitlements": {
                "device_limit": 0,
                "traffic_policy": "none",
                "display_traffic_label": "None",
                "connection_modes": [],
                "server_pool": [],
                "support_sla": "none",
                "dedicated_ip_count": 0,
            },
            "invite_bundle": {"count": 0, "friend_days": 0, "expiry_days": 0},
            "is_trial": False,
            "addons": [],
        }

    async def list_active_addon_lines(self, user_id: UUID) -> list[dict]:
        active_addons = await self._subscription_addons.list_active_for_user(user_id)
        addon_catalog = {
            str(addon.id): addon
            for addon in await self._addons.get_by_ids([addon.plan_addon_id for addon in active_addons])
        }

        addon_lines: list[dict] = []
        for active_addon in active_addons:
            addon = addon_catalog.get(str(active_addon.plan_addon_id))
            if addon is None:
                continue
            addon_lines.append(
                {
                    "code": addon.code,
                    "qty": active_addon.quantity,
                    "location_code": active_addon.location_code,
                    "delta_entitlements": addon.delta_entitlements or {},
                }
            )
        return addon_lines

    async def get_current_snapshot(self, user_id: UUID) -> dict:
        payment = await self._payments.get_latest_active_plan_payment(user_id)
        if payment and payment.plan_id:
            plan = await self._plans.get_by_id(payment.plan_id)
            if plan is not None:
                addon_lines = await self.list_active_addon_lines(user_id)
                expires_at = (
                    payment.created_at + timedelta(days=payment.subscription_days)
                    if payment.subscription_days > 0
                    else None
                )
                return self.build_snapshot(plan=plan, addon_lines=addon_lines, expires_at=expires_at)

        user = await self._users.get_by_id(user_id)
        now = datetime.now(UTC)
        if user and user.trial_expires_at and user.trial_expires_at > now:
            return self.build_trial_snapshot(expires_at=user.trial_expires_at)

        return self.build_empty_snapshot()
