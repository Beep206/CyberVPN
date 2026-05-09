"""S1 add-on policy and kill-switch checks."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.application.services.stage1_plan_policy import (
    S1_ADDON_POLICY_ID,
    Stage1AddonPolicyError,
    assert_stage1_addons_enabled,
    filter_stage1_public_addons,
    get_stage1_addon_policy,
)
from src.config.settings import Settings


def _addon(**overrides):
    base = {
        "code": "extra_device",
        "is_active": True,
        "price_usd": Decimal("6.00"),
        "sale_channels": ["web", "miniapp", "telegram_bot", "admin"],
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_stage1_addons_are_disabled_by_default_in_policy_and_settings() -> None:
    policy = get_stage1_addon_policy()
    settings = Settings(
        jwt_secret="xVanw-qakEZA0v_T5mJ9GSCJkTzoWYpHMJDX02lFg-B8",
        remnawave_token="valid_token_for_testing_purposes_32characters",
        cryptobot_token="valid_token_for_testing_purposes_32characters",
    )

    assert policy.policy_id == S1_ADDON_POLICY_ID
    assert policy.enabled_by_default is False
    assert settings.stage1_addons_enabled is False


def test_stage1_public_addon_filter_returns_empty_when_disabled() -> None:
    assert filter_stage1_public_addons([_addon()], sale_channel="web", enabled=False) == []


def test_stage1_public_addon_filter_allows_only_approved_enabled_public_addons() -> None:
    valid = _addon(code="extra_device")
    dedicated_ip = _addon(code="dedicated_ip")
    inactive = _addon(code="extra_device", is_active=False)
    unknown = _addon(code="priority_support")
    wrong_channel = _addon(code="extra_device", sale_channels=["telegram_bot"])
    free = _addon(code="extra_device", price_usd=Decimal("0.00"))

    assert filter_stage1_public_addons(
        [inactive, unknown, wrong_channel, free, valid, dedicated_ip],
        sale_channel="web",
        enabled=True,
    ) == [valid, dedicated_ip]


def test_stage1_addon_checkout_assertion_blocks_disabled_addons() -> None:
    with pytest.raises(Stage1AddonPolicyError, match="disabled for S1 beta"):
        assert_stage1_addons_enabled(addon_count=1, enabled=False)


def test_stage1_addon_checkout_assertion_allows_empty_or_enabled_addons() -> None:
    assert_stage1_addons_enabled(addon_count=0, enabled=False)
    assert_stage1_addons_enabled(addon_count=1, enabled=True)
