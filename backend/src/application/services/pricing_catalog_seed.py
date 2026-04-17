"""Canonical pricing catalog bootstrap data for the Phase 1 rollout.

The seed is intentionally backend-owned and editable: it provides a stable
starting catalog for local/staging environments and a safe re-apply path for
production admin teams.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import CatalogVisibility, PlanCode, SaleChannel, SupportSLA
from src.infrastructure.database.models.plan_addon_model import PlanAddonModel
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
from src.infrastructure.database.repositories.plan_addon_repo import PlanAddonRepository
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository

PUBLIC_CHANNELS = [
    SaleChannel.WEB.value,
    SaleChannel.MINIAPP.value,
    SaleChannel.TELEGRAM_BOT.value,
    SaleChannel.ADMIN.value,
]
ADMIN_ONLY_CHANNELS = [SaleChannel.ADMIN.value]
STANDARD_DURATIONS = [30, 90, 180, 365]


@dataclass(frozen=True)
class PlanSeedSpec:
    name: str
    plan_code: str
    display_name: str
    catalog_visibility: str
    duration_days: int
    device_limit: int
    price_usd: Decimal
    price_rub: Decimal | None
    sale_channels: list[str]
    traffic_policy: dict[str, Any]
    connection_modes: list[str]
    server_pool: list[str]
    support_sla: str
    dedicated_ip: dict[str, Any]
    invite_bundle: dict[str, int]
    trial_eligible: bool
    features: dict[str, Any]
    is_active: bool
    sort_order: int
    traffic_limit_bytes: int | None = None


@dataclass(frozen=True)
class AddonSeedSpec:
    code: str
    display_name: str
    duration_mode: str
    is_stackable: bool
    quantity_step: int
    price_usd: Decimal
    price_rub: Decimal | None
    max_quantity_by_plan: dict[str, int]
    delta_entitlements: dict[str, Any]
    requires_location: bool
    sale_channels: list[str]
    is_active: bool


PLAN_PRICE_USD: dict[str, dict[int, Decimal]] = {
    # Bootstrap commercial baseline. These values remain editable in admin.
    PlanCode.START.value: {
        30: Decimal("4.99"),
        90: Decimal("11.99"),
        180: Decimal("21.99"),
        365: Decimal("39.99"),
    },
    PlanCode.BASIC.value: {
        30: Decimal("5.99"),
        90: Decimal("14.99"),
        180: Decimal("27.99"),
        365: Decimal("49.99"),
    },
    PlanCode.PLUS.value: {
        30: Decimal("8.99"),
        90: Decimal("22.99"),
        180: Decimal("39.99"),
        365: Decimal("79.00"),
    },
    PlanCode.PRO.value: {
        30: Decimal("11.99"),
        90: Decimal("29.99"),
        180: Decimal("49.99"),
        365: Decimal("89.00"),
    },
    PlanCode.MAX.value: {
        30: Decimal("14.99"),
        90: Decimal("36.99"),
        180: Decimal("59.99"),
        365: Decimal("99.00"),
    },
    PlanCode.TEST.value: {
        30: Decimal("14.99"),
        90: Decimal("36.99"),
        180: Decimal("59.99"),
        365: Decimal("99.00"),
    },
    PlanCode.DEVELOPMENT.value: {
        30: Decimal("0.00"),
        90: Decimal("0.00"),
        180: Decimal("0.00"),
        365: Decimal("0.00"),
    },
}


PLAN_FAMILY_CONFIG: dict[str, dict[str, Any]] = {
    PlanCode.START.value: {
        "display_name": "Start",
        "catalog_visibility": CatalogVisibility.HIDDEN.value,
        "device_limit": 1,
        "sale_channels": ADMIN_ONLY_CHANNELS,
        "traffic_policy": {
            "mode": "fair_use",
            "display_label": "Unlimited",
            "enforcement_profile": "consumer_entry",
        },
        "connection_modes": ["standard"],
        "server_pool": ["shared"],
        "support_sla": SupportSLA.STANDARD.value,
        "dedicated_ip": {"included": 0, "eligible": True},
        "features": {
            "internal_notes": "Hidden entry plan for direct/admin distribution.",
            "public_badge": None,
        },
        "trial_eligible": False,
        "is_active": True,
    },
    PlanCode.BASIC.value: {
        "display_name": "Basic",
        "catalog_visibility": CatalogVisibility.PUBLIC.value,
        "device_limit": 2,
        "sale_channels": PUBLIC_CHANNELS,
        "traffic_policy": {
            "mode": "fair_use",
            "display_label": "Unlimited",
            "enforcement_profile": "consumer_entry",
        },
        "connection_modes": ["standard"],
        "server_pool": ["shared"],
        "support_sla": SupportSLA.STANDARD.value,
        "dedicated_ip": {"included": 0, "eligible": True},
        "features": {
            "marketing_badge": "Starter",
            "audience": "single_user",
        },
        "trial_eligible": False,
        "is_active": True,
    },
    PlanCode.PLUS.value: {
        "display_name": "Plus",
        "catalog_visibility": CatalogVisibility.PUBLIC.value,
        "device_limit": 5,
        "sale_channels": PUBLIC_CHANNELS,
        "traffic_policy": {
            "mode": "fair_use",
            "display_label": "Unlimited",
            "enforcement_profile": "mainstream",
        },
        "connection_modes": ["standard", "stealth"],
        "server_pool": ["shared_plus"],
        "support_sla": SupportSLA.STANDARD.value,
        "dedicated_ip": {"included": 0, "eligible": True},
        "features": {
            "marketing_badge": "Most Popular",
            "audience": "mass_market",
        },
        "trial_eligible": False,
        "is_active": True,
    },
    PlanCode.PRO.value: {
        "display_name": "Pro",
        "catalog_visibility": CatalogVisibility.PUBLIC.value,
        "device_limit": 10,
        "sale_channels": PUBLIC_CHANNELS,
        "traffic_policy": {
            "mode": "fair_use",
            "display_label": "Unlimited",
            "enforcement_profile": "power_user",
        },
        "connection_modes": ["standard", "stealth", "manual_config"],
        "server_pool": ["premium_shared"],
        "support_sla": SupportSLA.PRIORITY.value,
        "dedicated_ip": {"included": 0, "eligible": True},
        "features": {
            "marketing_badge": "Best Balance",
            "audience": "power_user",
        },
        "trial_eligible": False,
        "is_active": True,
    },
    PlanCode.MAX.value: {
        "display_name": "Max",
        "catalog_visibility": CatalogVisibility.PUBLIC.value,
        "device_limit": 15,
        "sale_channels": PUBLIC_CHANNELS,
        "traffic_policy": {
            "mode": "fair_use",
            "display_label": "Unlimited",
            "enforcement_profile": "premium_consumer",
        },
        "connection_modes": ["standard", "stealth", "manual_config", "dedicated_ip"],
        "server_pool": ["premium", "exclusive"],
        "support_sla": SupportSLA.VIP.value,
        "dedicated_ip": {"included": 1, "eligible": True},
        "features": {
            "marketing_badge": "Most Complete",
            "audience": "family_premium",
        },
        "trial_eligible": False,
        "is_active": True,
    },
    PlanCode.TEST.value: {
        "display_name": "Test",
        "catalog_visibility": CatalogVisibility.HIDDEN.value,
        "device_limit": 15,
        "sale_channels": ADMIN_ONLY_CHANNELS,
        "traffic_policy": {
            "mode": "fair_use",
            "display_label": "Unlimited",
            "enforcement_profile": "beta",
        },
        "connection_modes": ["standard", "stealth", "manual_config", "dedicated_ip", "experimental"],
        "server_pool": ["premium", "exclusive", "beta"],
        "support_sla": SupportSLA.VIP.value,
        "dedicated_ip": {"included": 1, "eligible": True},
        "features": {
            "internal_notes": "Experimental premium catalog entry.",
            "experimental_protocols": True,
        },
        "trial_eligible": False,
        "is_active": True,
    },
    PlanCode.DEVELOPMENT.value: {
        "display_name": "Development",
        "catalog_visibility": CatalogVisibility.HIDDEN.value,
        "device_limit": 999,
        "sale_channels": ADMIN_ONLY_CHANNELS,
        "traffic_policy": {
            "mode": "internal_unlimited",
            "display_label": "Unlimited",
            "enforcement_profile": "internal",
        },
        "connection_modes": [
            "standard",
            "stealth",
            "manual_config",
            "dedicated_ip",
            "experimental",
            "internal",
        ],
        "server_pool": ["shared", "premium", "exclusive", "beta", "internal"],
        "support_sla": SupportSLA.INTERNAL.value,
        "dedicated_ip": {"included": 999, "eligible": True},
        "features": {
            "internal_only": True,
            "internal_notes": "Unrestricted internal development catalog entry.",
        },
        "trial_eligible": False,
        "is_active": True,
    },
}


def _invite_bundle(plan_code: str, duration_days: int) -> dict[str, int]:
    bundles: dict[tuple[str, int], dict[str, int]] = {
        (PlanCode.START.value, 365): {"count": 1, "friend_days": 7, "expiry_days": 30},
        (PlanCode.BASIC.value, 365): {"count": 1, "friend_days": 7, "expiry_days": 30},
        (PlanCode.PLUS.value, 180): {"count": 1, "friend_days": 7, "expiry_days": 30},
        (PlanCode.PLUS.value, 365): {"count": 2, "friend_days": 14, "expiry_days": 60},
        (PlanCode.PRO.value, 180): {"count": 1, "friend_days": 14, "expiry_days": 60},
        (PlanCode.PRO.value, 365): {"count": 2, "friend_days": 14, "expiry_days": 60},
        (PlanCode.MAX.value, 180): {"count": 1, "friend_days": 14, "expiry_days": 60},
        (PlanCode.MAX.value, 365): {"count": 3, "friend_days": 14, "expiry_days": 60},
        (PlanCode.TEST.value, 365): {"count": 3, "friend_days": 14, "expiry_days": 60},
    }
    return bundles.get((plan_code, duration_days), {"count": 0, "friend_days": 0, "expiry_days": 0})


def build_plan_seed_specs() -> list[PlanSeedSpec]:
    """Return the canonical `plan_code + duration` seed matrix."""
    specs: list[PlanSeedSpec] = []
    family_order = {
        PlanCode.START.value: 10,
        PlanCode.BASIC.value: 20,
        PlanCode.PLUS.value: 30,
        PlanCode.PRO.value: 40,
        PlanCode.MAX.value: 50,
        PlanCode.TEST.value: 60,
        PlanCode.DEVELOPMENT.value: 70,
    }

    for plan_code, config in PLAN_FAMILY_CONFIG.items():
        for duration_index, duration_days in enumerate(STANDARD_DURATIONS, start=1):
            specs.append(
                PlanSeedSpec(
                    name=f"{plan_code}_{duration_days}",
                    plan_code=plan_code,
                    display_name=str(config["display_name"]),
                    catalog_visibility=str(config["catalog_visibility"]),
                    duration_days=duration_days,
                    device_limit=int(config["device_limit"]),
                    price_usd=PLAN_PRICE_USD[plan_code][duration_days],
                    price_rub=None,
                    sale_channels=list(config["sale_channels"]),
                    traffic_policy=dict(config["traffic_policy"]),
                    connection_modes=list(config["connection_modes"]),
                    server_pool=list(config["server_pool"]),
                    support_sla=str(config["support_sla"]),
                    dedicated_ip=dict(config["dedicated_ip"]),
                    invite_bundle=_invite_bundle(plan_code, duration_days),
                    trial_eligible=bool(config["trial_eligible"]),
                    features={
                        **dict(config["features"]),
                        "bootstrap_seed_version": "phase1_v1",
                        "period_days": duration_days,
                    },
                    is_active=bool(config["is_active"]),
                    sort_order=family_order[plan_code] + duration_index,
                )
            )
    return specs


def build_addon_seed_specs() -> list[AddonSeedSpec]:
    """Return the canonical add-on seed matrix."""
    return [
        AddonSeedSpec(
            code="extra_device",
            display_name="+1 device",
            duration_mode="inherits_subscription",
            is_stackable=True,
            quantity_step=1,
            price_usd=Decimal("6.00"),
            price_rub=None,
            max_quantity_by_plan={
                PlanCode.START.value: 1,
                PlanCode.BASIC.value: 2,
                PlanCode.PLUS.value: 3,
                PlanCode.PRO.value: 5,
                PlanCode.MAX.value: 10,
                PlanCode.TEST.value: 10,
                PlanCode.DEVELOPMENT.value: 0,
            },
            delta_entitlements={"device_limit": 1},
            requires_location=False,
            sale_channels=PUBLIC_CHANNELS,
            is_active=True,
        ),
        AddonSeedSpec(
            code="dedicated_ip",
            display_name="Dedicated IP",
            duration_mode="inherits_subscription",
            is_stackable=True,
            quantity_step=1,
            price_usd=Decimal("24.00"),
            price_rub=None,
            max_quantity_by_plan={},
            delta_entitlements={"dedicated_ip_count": 1},
            requires_location=True,
            sale_channels=PUBLIC_CHANNELS,
            is_active=True,
        ),
    ]


def _apply_plan_spec(model: SubscriptionPlanModel, spec: PlanSeedSpec) -> bool:
    changed = False
    assignments = {
        "name": spec.name,
        "plan_code": spec.plan_code,
        "display_name": spec.display_name,
        "catalog_visibility": spec.catalog_visibility,
        "duration_days": spec.duration_days,
        "traffic_limit_bytes": spec.traffic_limit_bytes,
        "device_limit": spec.device_limit,
        "price_usd": spec.price_usd,
        "price_rub": spec.price_rub,
        "sale_channels": spec.sale_channels,
        "traffic_policy": spec.traffic_policy,
        "connection_modes": spec.connection_modes,
        "server_pool": spec.server_pool,
        "support_sla": spec.support_sla,
        "dedicated_ip": spec.dedicated_ip,
        "invite_bundle": spec.invite_bundle,
        "trial_eligible": spec.trial_eligible,
        "features": spec.features,
        "is_active": spec.is_active,
        "sort_order": spec.sort_order,
        "tier": None,
    }
    for field_name, value in assignments.items():
        if getattr(model, field_name) != value:
            setattr(model, field_name, value)
            changed = True
    return changed


def _apply_addon_spec(model: PlanAddonModel, spec: AddonSeedSpec) -> bool:
    changed = False
    assignments = {
        "code": spec.code,
        "display_name": spec.display_name,
        "duration_mode": spec.duration_mode,
        "is_stackable": spec.is_stackable,
        "quantity_step": spec.quantity_step,
        "price_usd": spec.price_usd,
        "price_rub": spec.price_rub,
        "max_quantity_by_plan": spec.max_quantity_by_plan,
        "delta_entitlements": spec.delta_entitlements,
        "requires_location": spec.requires_location,
        "sale_channels": spec.sale_channels,
        "is_active": spec.is_active,
    }
    for field_name, value in assignments.items():
        if getattr(model, field_name) != value:
            setattr(model, field_name, value)
            changed = True
    return changed


async def seed_pricing_catalog(session: AsyncSession) -> dict[str, int]:
    """Upsert the canonical Phase 1 pricing catalog into the database."""
    plan_repo = SubscriptionPlanRepository(session)
    addon_repo = PlanAddonRepository(session)

    summary = {
        "plans_created": 0,
        "plans_updated": 0,
        "addons_created": 0,
        "addons_updated": 0,
    }

    for spec in build_plan_seed_specs():
        existing = await plan_repo.get_by_name(spec.name)
        if existing is None:
            model = SubscriptionPlanModel(
                name=spec.name,
                tier=None,
                plan_code=spec.plan_code,
                display_name=spec.display_name,
                catalog_visibility=spec.catalog_visibility,
                duration_days=spec.duration_days,
                traffic_limit_bytes=spec.traffic_limit_bytes,
                device_limit=spec.device_limit,
                price_usd=spec.price_usd,
                price_rub=spec.price_rub,
                sale_channels=spec.sale_channels,
                traffic_policy=spec.traffic_policy,
                connection_modes=spec.connection_modes,
                server_pool=spec.server_pool,
                support_sla=spec.support_sla,
                dedicated_ip=spec.dedicated_ip,
                invite_bundle=spec.invite_bundle,
                trial_eligible=spec.trial_eligible,
                features=spec.features,
                is_active=spec.is_active,
                sort_order=spec.sort_order,
            )
            await plan_repo.create(model)
            summary["plans_created"] += 1
            continue

        if _apply_plan_spec(existing, spec):
            await plan_repo.update(existing)
            summary["plans_updated"] += 1

    for spec in build_addon_seed_specs():
        existing = await addon_repo.get_by_code(spec.code)
        if existing is None:
            model = PlanAddonModel(
                code=spec.code,
                display_name=spec.display_name,
                duration_mode=spec.duration_mode,
                is_stackable=spec.is_stackable,
                quantity_step=spec.quantity_step,
                price_usd=spec.price_usd,
                price_rub=spec.price_rub,
                max_quantity_by_plan=spec.max_quantity_by_plan,
                delta_entitlements=spec.delta_entitlements,
                requires_location=spec.requires_location,
                sale_channels=spec.sale_channels,
                is_active=spec.is_active,
            )
            await addon_repo.create(model)
            summary["addons_created"] += 1
            continue

        if _apply_addon_spec(existing, spec):
            await addon_repo.update(existing)
            summary["addons_updated"] += 1

    await session.flush()
    return summary
