"""Pricing entitlements calculation for plans, add-ons, and trial."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.plan_addon_repo import PlanAddonRepository, SubscriptionAddonRepository
from src.infrastructure.database.repositories.service_access_repo import ServiceAccessRepository
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
        self._service_access = ServiceAccessRepository(session)

    @staticmethod
    def _to_utc_datetime(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

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

    def _normalize_grant_snapshot(self, *, grant_snapshot: dict, expires_at: datetime | None) -> dict:
        snapshot = self.build_empty_snapshot()
        provided = dict(grant_snapshot or {})
        effective_entitlements = dict(snapshot["effective_entitlements"])
        effective_entitlements.update(dict(provided.get("effective_entitlements") or {}))
        invite_bundle = dict(snapshot["invite_bundle"])
        invite_bundle.update(dict(provided.get("invite_bundle") or {}))

        snapshot.update(
            {
                key: value
                for key, value in provided.items()
                if key not in {"effective_entitlements", "invite_bundle", "addons", "status", "expires_at"}
            }
        )
        snapshot["effective_entitlements"] = effective_entitlements
        snapshot["invite_bundle"] = invite_bundle
        snapshot["addons"] = list(provided.get("addons") or [])
        snapshot["status"] = "active"
        snapshot["is_trial"] = bool(provided.get("is_trial", False))
        snapshot["expires_at"] = expires_at.isoformat() if expires_at else provided.get("expires_at")
        return snapshot

    async def get_current_snapshot(self, user_id: UUID, *, auth_realm_id: UUID | None = None) -> dict:
        now = datetime.now(UTC)

        if auth_realm_id is not None:
            has_canonical_grants = await self._service_access.has_any_entitlement_grants_for_customer_realm(
                customer_account_id=user_id,
                auth_realm_id=auth_realm_id,
            )
            if has_canonical_grants:
                current_grant = await self._service_access.get_current_active_entitlement_grant(
                    customer_account_id=user_id,
                    auth_realm_id=auth_realm_id,
                    now=now,
                )
                if current_grant is not None:
                    return self._normalize_grant_snapshot(
                        grant_snapshot=dict(current_grant.grant_snapshot or {}),
                        expires_at=current_grant.expires_at,
                    )
                return self.build_empty_snapshot()

        payment = await self._payments.get_latest_active_plan_payment(user_id)
        if payment and payment.plan_id:
            plan = await self._plans.get_by_id(payment.plan_id)
            if plan is not None:
                addon_lines = await self.list_active_addon_lines(user_id)
                expires_at = self._to_utc_datetime(payment.created_at)
                if expires_at is not None and payment.subscription_days > 0:
                    expires_at = expires_at + timedelta(days=payment.subscription_days)
                elif payment.subscription_days <= 0:
                    expires_at = None
                return self.build_snapshot(plan=plan, addon_lines=addon_lines, expires_at=expires_at)

        user = await self._users.get_by_id(user_id)
        trial_expires_at = self._to_utc_datetime(user.trial_expires_at) if user else None
        if user and trial_expires_at and trial_expires_at > now:
            return self.build_trial_snapshot(expires_at=trial_expires_at)

        return self.build_empty_snapshot()

    async def get_legacy_snapshot(self, user_id: UUID) -> dict:
        return await self.get_current_snapshot(user_id, auth_realm_id=None)
