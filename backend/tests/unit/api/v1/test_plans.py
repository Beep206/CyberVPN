"""Unit tests for public plan catalog endpoints."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.presentation.api.v1.plans import routes as plan_routes
from src.presentation.api.v1.plans.schemas import CreatePlanRequest, UpdatePlanRequest

TASK2_PLAN_CODE = "premium_spb_de_exceptions"


def _build_plan(**overrides):
    base = {
        "id": uuid4(),
        "name": "basic_30",
        "plan_code": "basic",
        "display_name": "Basic",
        "catalog_visibility": "public",
        "duration_days": 30,
        "traffic_limit_bytes": None,
        "device_limit": 2,
        "price_usd": Decimal("5.99"),
        "price_rub": None,
        "traffic_policy": {"mode": "fair_use", "display_label": "Unlimited"},
        "connection_modes": ["standard"],
        "server_pool": ["shared"],
        "support_sla": "standard",
        "dedicated_ip": {"included": 0, "eligible": True},
        "sale_channels": ["web", "miniapp", "telegram_bot", "admin"],
        "invite_bundle": {"count": 0, "friend_days": 0, "expiry_days": 0},
        "trial_eligible": False,
        "features": {},
        "is_active": True,
        "sort_order": 20,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_plan_request_schemas_accept_task2_plan_code() -> None:
    created = CreatePlanRequest(
        name="premium_spb_de_exceptions_30",
        plan_code=TASK2_PLAN_CODE,
        display_name="Premium SPB + DE Exceptions",
        duration_days=30,
        devices_included=5,
        price_usd=0,
    )
    updated = UpdatePlanRequest(plan_code=TASK2_PLAN_CODE)

    assert created.plan_code == TASK2_PLAN_CODE
    assert updated.plan_code == TASK2_PLAN_CODE


def test_plan_request_schemas_reject_plan_codes_above_database_limit() -> None:
    too_long = "p" * 41

    with pytest.raises(ValidationError, match="at most 40 characters"):
        UpdatePlanRequest(plan_code=too_long)


@pytest.mark.asyncio
async def test_public_plan_list_returns_only_stage1_beta_terms(monkeypatch: pytest.MonkeyPatch) -> None:
    valid = _build_plan(name="basic_30", duration_days=30)
    semiannual = _build_plan(name="basic_180", duration_days=180, sort_order=21)
    unsupported = _build_plan(name="basic_60", duration_days=60, sort_order=22)

    class FakePlanRepo:
        def __init__(self, _db) -> None:
            pass

        async def list_catalog(self, **kwargs):
            assert kwargs["sale_channel"] == "web"
            return [unsupported, semiannual, valid]

    monkeypatch.setattr(plan_routes, "SubscriptionPlanRepository", FakePlanRepo)

    response = await plan_routes.list_plans(channel="web", db=object())

    assert [plan.name for plan in response] == ["basic_180", "basic_30"]
    assert response[0].duration_days == 180
    assert response[1].duration_days == 30
