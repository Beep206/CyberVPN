"""Stage 1 paid plan catalog policy."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

S1_PAID_PLAN_POLICY_ID = "stage1_beta_paid_plans_v1"
S1_ADDON_POLICY_ID = "stage1_beta_addons_disabled_by_default_v1"
S1_PAID_PLAN_CODES = ("basic", "plus", "pro", "max")
S1_PRIVATE_PLAN_CODES = ("start", "ru_start", "ru_basic", "test", "development")
S1_PAID_PLAN_DURATIONS = (30, 90, 180, 365)
S1_PUBLIC_PAID_SALE_CHANNELS = ("web", "miniapp", "telegram_bot")
S1_PUBLIC_ADDON_CODES = ("extra_device", "dedicated_ip")
S1_PUBLIC_ADDON_SALE_CHANNELS = ("web", "miniapp", "telegram_bot")


class Stage1PlanPolicyError(ValueError):
    """Raised when a plan is outside the S1 beta paid catalog."""


class Stage1AddonPolicyError(ValueError):
    """Raised when an add-on is outside the S1 beta add-on policy."""


@dataclass(frozen=True, slots=True)
class Stage1PaidPlanPolicy:
    """Canonical paid-plan policy for S1 controlled public beta."""

    policy_id: str = S1_PAID_PLAN_POLICY_ID
    plan_codes: tuple[str, ...] = S1_PAID_PLAN_CODES
    private_plan_codes: tuple[str, ...] = S1_PRIVATE_PLAN_CODES
    durations_days: tuple[int, ...] = S1_PAID_PLAN_DURATIONS
    public_sale_channels: tuple[str, ...] = S1_PUBLIC_PAID_SALE_CHANNELS


@dataclass(frozen=True, slots=True)
class Stage1AddonPolicy:
    """Canonical add-on policy for S1 controlled public beta."""

    policy_id: str = S1_ADDON_POLICY_ID
    addon_codes: tuple[str, ...] = S1_PUBLIC_ADDON_CODES
    public_sale_channels: tuple[str, ...] = S1_PUBLIC_ADDON_SALE_CHANNELS
    enabled_by_default: bool = False


def get_stage1_paid_plan_policy() -> Stage1PaidPlanPolicy:
    """Return the immutable S1 beta paid-plan policy."""

    return Stage1PaidPlanPolicy()


def get_stage1_addon_policy() -> Stage1AddonPolicy:
    """Return the immutable S1 beta add-on policy."""

    return Stage1AddonPolicy()


def is_stage1_public_paid_plan(plan: Any, *, sale_channel: str | None = None) -> bool:
    """Return True when a plan belongs to the public S1 beta paid catalog."""

    plan_code = str(getattr(plan, "plan_code", "") or "")
    duration_days = int(getattr(plan, "duration_days", 0) or 0)
    catalog_visibility = str(getattr(plan, "catalog_visibility", "") or "")
    sale_channels = set(getattr(plan, "sale_channels", []) or [])
    price_usd = Decimal(str(getattr(plan, "price_usd", "0") or "0"))
    device_limit = int(getattr(plan, "device_limit", 0) or 0)

    if not bool(getattr(plan, "is_active", False)):
        return False
    if catalog_visibility != "public":
        return False
    if plan_code not in S1_PAID_PLAN_CODES:
        return False
    if duration_days not in S1_PAID_PLAN_DURATIONS:
        return False
    if price_usd <= 0:
        return False
    if device_limit <= 0:
        return False
    if sale_channel is not None:
        if sale_channel not in S1_PUBLIC_PAID_SALE_CHANNELS:
            return False
        if sale_channels and sale_channel not in sale_channels:
            return False
    return True


def filter_stage1_public_paid_plans(plans: list[Any], *, sale_channel: str | None = None) -> list[Any]:
    """Filter arbitrary plan rows down to the public S1 beta paid catalog."""

    return [plan for plan in plans if is_stage1_public_paid_plan(plan, sale_channel=sale_channel)]


def is_stage1_public_addon(addon: Any, *, sale_channel: str | None = None, enabled: bool = False) -> bool:
    """Return True when an add-on may be publicly sold in S1."""

    if not enabled:
        return False

    code = str(getattr(addon, "code", "") or "")
    sale_channels = set(getattr(addon, "sale_channels", []) or [])
    price_usd = Decimal(str(getattr(addon, "price_usd", "0") or "0"))

    if not bool(getattr(addon, "is_active", False)):
        return False
    if code not in S1_PUBLIC_ADDON_CODES:
        return False
    if price_usd <= 0:
        return False
    if sale_channel is not None:
        if sale_channel not in S1_PUBLIC_ADDON_SALE_CHANNELS:
            return False
        if sale_channels and sale_channel not in sale_channels:
            return False
    return True


def filter_stage1_public_addons(
    addons: list[Any],
    *,
    sale_channel: str | None = None,
    enabled: bool = False,
) -> list[Any]:
    """Filter arbitrary add-on rows down to the S1 public add-on policy."""

    return [
        addon
        for addon in addons
        if is_stage1_public_addon(addon, sale_channel=sale_channel, enabled=enabled)
    ]


def assert_stage1_paid_plan_purchasable(plan: Any, *, sale_channel: str) -> None:
    """Reject out-of-policy paid plans on public checkout channels."""

    if sale_channel == "admin":
        return
    if not is_stage1_public_paid_plan(plan, sale_channel=sale_channel):
        raise Stage1PlanPolicyError("Plan is not available in the S1 beta paid catalog")


def assert_stage1_addons_enabled(*, addon_count: int, enabled: bool) -> None:
    """Reject public add-on checkout paths unless S1 explicitly enables add-ons."""

    if addon_count > 0 and not enabled:
        raise Stage1AddonPolicyError("Add-ons are disabled for S1 beta")
