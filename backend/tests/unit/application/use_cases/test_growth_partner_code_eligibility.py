from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.growth_codes.resolve_code import ResolveGrowthCodeUseCase
from src.domain.enums import GrowthCodeActionContext, GrowthCodeRejectReason, GrowthCodeResolutionStatus


def _partner_code(**overrides):
    base = {
        "id": uuid.uuid4(),
        "partner_account_id": uuid.uuid4(),
        "partner_user_id": uuid.uuid4(),
        "markup_pct": Decimal("7"),
        "is_active": True,
        "lifecycle_status": "active",
        "approval_status": "approved",
        "active_from": None,
        "expires_at": None,
        "owner_type": "affiliate",
        "code_kind": "starter_code",
        "lane_key": "creator_affiliate",
        "attribution_model": "last_eligible_touch",
        "attribution_window_seconds": 30 * 24 * 60 * 60,
        "policy_version_id": None,
        "commission_contract_id": None,
        "allowed_channels": ["web"],
        "allowed_storefront_ids": ["*"],
        "allowed_geographies": ["*"],
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_growth_partner_code_checkout_rejects_surface_ineligible_code_with_policy_snapshot() -> None:
    use_case = ResolveGrowthCodeUseCase(SimpleNamespace())
    use_case._partners = SimpleNamespace(get_account_by_id=AsyncMock(return_value=SimpleNamespace(status="active")))
    partner_code = _partner_code(allowed_channels=["partner_blog"])

    result = await use_case._resolve_partner_code(
        partner_code=partner_code,
        action_context=GrowthCodeActionContext.CHECKOUT,
        user_id=None,
        existing_promo_present=False,
        sale_channel="web",
        storefront_id=uuid.uuid4(),
    )

    assert result.accepted is False
    assert result.result == GrowthCodeResolutionStatus.REJECTED
    assert result.reject_reason == GrowthCodeRejectReason.CODE_NOT_ELIGIBLE_FOR_SURFACE
    assert result.partner_code_id == partner_code.id
    assert result.policy_snapshot is not None
    assert result.policy_snapshot["allowed"] is False
    assert result.policy_snapshot["reason_codes"] == ["sale_channel_not_allowed"]
