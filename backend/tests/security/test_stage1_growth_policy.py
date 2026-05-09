from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.application.services.config_service import ConfigService
from src.application.services.stage1_growth_policy import (
    Stage1GrowthPolicyError,
    assert_stage1_checkout_codes_enabled,
    assert_stage1_gift_codes_enabled,
    assert_stage1_promo_codes_enabled,
    assert_stage1_referral_enabled,
)
from src.config.settings import settings
from src.domain.enums import GrowthCodeActionContext
from src.presentation.api.v1.codes.routes import resolve_growth_code
from src.presentation.api.v1.codes.schemas import ResolveGrowthCodeRequest
from src.presentation.api.v1.gifts.routes import redeem_gift
from src.presentation.api.v1.gifts.schemas import GiftRedeemRequest
from src.presentation.api.v1.promo_codes.routes import validate_promo
from src.presentation.api.v1.promo_codes.schemas import ValidatePromoRequest
from src.presentation.api.v1.referral.routes import get_referral_code, get_referral_status


class FailingConfigRepository:
    async def get_value(self, *_args, **_kwargs):
        raise AssertionError("S1 global referral kill switch must fail closed before DB config")


class StaticConfigRepository:
    def __init__(self, values: dict[str, dict[str, object]]) -> None:
        self._values = values

    async def get_value(self, key: str, default):
        return self._values.get(key, default)


def test_stage1_growth_policy_defaults_are_disabled() -> None:
    with pytest.raises(Stage1GrowthPolicyError, match="Referral flows"):
        assert_stage1_referral_enabled(enabled=False)
    with pytest.raises(Stage1GrowthPolicyError, match="Promo code flows"):
        assert_stage1_promo_codes_enabled(enabled=False)
    with pytest.raises(Stage1GrowthPolicyError, match="Gift code flows"):
        assert_stage1_gift_codes_enabled(enabled=False)
    with pytest.raises(Stage1GrowthPolicyError, match="Checkout code discounts"):
        assert_stage1_checkout_codes_enabled(code_input="SAVE20", enabled=False)

    assert_stage1_checkout_codes_enabled(code_input=None, promo_code=None, enabled=False)


def test_referral_config_fails_closed_before_system_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "referral_enabled", False)

    result = asyncio.run(ConfigService(FailingConfigRepository()).is_referral_enabled())

    assert result is False


def test_referral_config_respects_database_default_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "referral_enabled", True)

    result = asyncio.run(
        ConfigService(
            StaticConfigRepository({"referral.enabled": {"enabled": False}})
        ).is_referral_enabled()
    )

    assert result is False


def test_public_referral_status_is_disabled_without_generating_codes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "referral_enabled", False)

    status = asyncio.run(get_referral_status(user_id=uuid4(), db=object()))

    assert status.enabled is False
    assert status.commission_rate == 0
    assert status.friend_discount_pct == 0
    assert status.reward_hold_days == 0


@pytest.mark.parametrize(
    ("call", "expected_detail"),
    [
        (
            lambda: get_referral_code(user_id=uuid4(), db=object()),
            "Referral flows are disabled for S1 beta",
        ),
        (
            lambda: validate_promo(
                body=ValidatePromoRequest(code="SAVE20", plan_id=uuid4(), amount=79),
                db=object(),
                user_id=uuid4(),
            ),
            "Promo code flows are disabled for S1 beta",
        ),
        (
            lambda: resolve_growth_code(
                payload=ResolveGrowthCodeRequest(
                    code="SAVE20",
                    action_context=GrowthCodeActionContext.CHECKOUT,
                    plan_id=uuid4(),
                    amount=79,
                    channel="web",
                ),
                request=SimpleNamespace(headers={}),
                db=object(),
                user_id=uuid4(),
            ),
            "Checkout code discounts are disabled for S1 beta",
        ),
        (
            lambda: redeem_gift(
                payload=GiftRedeemRequest(code="GIFT-123"),
                db=object(),
                user_id=uuid4(),
                current_realm=SimpleNamespace(),
            ),
            "Gift code flows are disabled for S1 beta",
        ),
    ],
)
def test_public_growth_routes_return_403_when_stage1_disabled(
    monkeypatch: pytest.MonkeyPatch,
    call,
    expected_detail: str,
) -> None:
    monkeypatch.setattr(settings, "referral_enabled", False)
    monkeypatch.setattr(settings, "promo_codes_enabled", False)
    monkeypatch.setattr(settings, "gift_codes_enabled", False)
    monkeypatch.setattr(settings, "checkout_code_discounts_enabled", False)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(call())

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == expected_detail
