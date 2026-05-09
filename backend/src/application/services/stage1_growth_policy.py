"""Stage 1 public growth-flow kill switch policy."""

from __future__ import annotations

from dataclasses import dataclass

S1_GROWTH_POLICY_ID = "stage1_beta_growth_flows_disabled_by_default_v1"
S1_GROWTH_DISABLED_MESSAGE = (
    "Public promo, gift, referral, and checkout code flows are disabled for S1 beta"
)


class Stage1GrowthPolicyError(ValueError):
    """Raised when a public growth flow is disabled by S1 beta policy."""


@dataclass(frozen=True, slots=True)
class Stage1GrowthPolicy:
    """Canonical S1 beta public growth-flow policy."""

    policy_id: str = S1_GROWTH_POLICY_ID
    referral_enabled_by_default: bool = False
    promo_codes_enabled_by_default: bool = False
    gift_codes_enabled_by_default: bool = False
    checkout_code_discounts_enabled_by_default: bool = False


def get_stage1_growth_policy() -> Stage1GrowthPolicy:
    """Return the immutable S1 beta growth-flow policy."""

    return Stage1GrowthPolicy()


def assert_stage1_referral_enabled(*, enabled: bool) -> None:
    """Reject public referral actions unless S1 explicitly enables referrals."""

    if not enabled:
        raise Stage1GrowthPolicyError("Referral flows are disabled for S1 beta")


def assert_stage1_promo_codes_enabled(*, enabled: bool) -> None:
    """Reject public promo-code actions unless S1 explicitly enables promo codes."""

    if not enabled:
        raise Stage1GrowthPolicyError("Promo code flows are disabled for S1 beta")


def assert_stage1_gift_codes_enabled(*, enabled: bool) -> None:
    """Reject public gift-code actions unless S1 explicitly enables gift codes."""

    if not enabled:
        raise Stage1GrowthPolicyError("Gift code flows are disabled for S1 beta")


def assert_stage1_checkout_codes_enabled(
    *,
    code_input: str | None,
    promo_code: str | None = None,
    enabled: bool,
) -> None:
    """Reject public checkout code discounts unless S1 explicitly enables them."""

    has_code = bool((code_input or "").strip()) or bool((promo_code or "").strip())
    if has_code and not enabled:
        raise Stage1GrowthPolicyError("Checkout code discounts are disabled for S1 beta")
