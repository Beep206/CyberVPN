from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from src.application.use_cases.partner_attribution.eligibility import (
    EvaluatePartnerCodeEligibilityCommand,
    EvaluatePartnerCodeEligibilityUseCase,
)


def _code(**overrides):
    base = {
        "id": uuid.uuid4(),
        "partner_account_id": uuid.uuid4(),
        "partner_user_id": uuid.uuid4(),
        "code_kind": "starter_code",
        "owner_type": "affiliate",
        "lane_key": "creator_affiliate",
        "attribution_model": "last_eligible_touch",
        "attribution_window_seconds": 30 * 24 * 60 * 60,
        "policy_version_id": None,
        "commission_contract_id": None,
        "markup_pct": 7,
        "allowed_channels": ["content"],
        "allowed_storefront_ids": ["*"],
        "allowed_geographies": ["*"],
        "is_active": True,
        "lifecycle_status": "active",
        "approval_status": "approved",
        "active_from": None,
        "expires_at": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _account(**overrides):
    base = {"status": "active"}
    base.update(overrides)
    return SimpleNamespace(**base)


def test_partner_code_eligibility_allows_active_code_and_persists_decision_snapshot() -> None:
    storefront_id = uuid.uuid4()
    result = EvaluatePartnerCodeEligibilityUseCase().execute(
        EvaluatePartnerCodeEligibilityCommand(
            code_model=_code(allowed_storefront_ids=[str(storefront_id)]),
            account=_account(),
            sale_channel="content",
            storefront_id=storefront_id,
            geography="*",
            now=datetime(2026, 6, 21, tzinfo=UTC),
        )
    )

    assert result.allowed is True
    assert result.reason_codes == []
    assert result.policy_snapshot["allowed"] is True
    assert result.policy_snapshot["reason_codes"] == []
    assert result.policy_snapshot["evaluated_sale_channel"] == "content"
    assert result.policy_snapshot["evaluated_storefront_id"] == str(storefront_id)


def test_partner_code_eligibility_reports_lifecycle_account_and_scope_reasons() -> None:
    result = EvaluatePartnerCodeEligibilityUseCase().execute(
        EvaluatePartnerCodeEligibilityCommand(
            code_model=_code(
                lifecycle_status="paused",
                approval_status="rejected",
                allowed_channels=["partner_blog"],
                allowed_storefront_ids=[str(uuid.uuid4())],
            ),
            account=_account(status="suspended"),
            sale_channel="content",
            storefront_id=uuid.uuid4(),
            now=datetime(2026, 6, 21, tzinfo=UTC),
        )
    )

    assert result.allowed is False
    assert result.error_code == "PARTNER_CODE_NOT_ACTIVE"
    assert result.status_code == 409
    assert set(result.reason_codes) == {
        "code_lifecycle_not_active",
        "code_not_approved",
        "partner_account_not_active",
        "sale_channel_not_allowed",
        "storefront_not_allowed",
    }
    assert result.policy_snapshot["allowed"] is False
    assert result.policy_snapshot["reason_codes"] == sorted(result.reason_codes)


def test_partner_code_eligibility_maps_expired_link_to_link_error() -> None:
    link = SimpleNamespace(
        id=uuid.uuid4(),
        status="active",
        active_from=None,
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    result = EvaluatePartnerCodeEligibilityUseCase().execute(
        EvaluatePartnerCodeEligibilityCommand(
            code_model=_code(),
            account=_account(),
            link_model=link,
            sale_channel="content",
            now=datetime.now(UTC),
        )
    )

    assert result.allowed is False
    assert result.error_code == "PARTNER_CODE_LINK_EXPIRED"
    assert result.status_code == 410
    assert result.reason_codes == ["link_expired"]
    assert result.policy_snapshot["partner_code_link_id"] == str(link.id)
