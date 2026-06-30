from __future__ import annotations

import pytest

from src.application.use_cases.invites.campaigns import (
    InviteCampaignValidationError,
    _validate_lifetime_campaign_policy,
    _validate_multi_use_campaign_policy,
)


def _valid_risk_policy() -> dict[str, object]:
    return {
        "per_user_redeem_cap": 1,
        "max_redemptions_per_device": 1,
        "max_redemptions_per_ip_window": 3,
        "velocity_window_hours": 24,
        "deny_disposable_email": True,
        "deny_known_abuse_subject": True,
        "high_risk_context": True,
    }


def test_multi_use_policy_acknowledgement_error_has_public_detail() -> None:
    with pytest.raises(InviteCampaignValidationError) as exc_info:
        _validate_multi_use_campaign_policy(
            risk_policy=_valid_risk_policy(),
            caps={"global_issue_cap": 1000},
            max_generation_depth=5,
            acknowledgement=False,
            policy={},
        )

    assert exc_info.value.to_detail() == {
        "code": "INVITE_CAMPAIGN_MULTI_USE_ACK_REQUIRED",
        "message_key": "invite_campaign.multi_use_ack_required",
        "message": "Multi-use acknowledgement is required.",
    }


def test_lifetime_global_issue_cap_error_has_public_detail() -> None:
    with pytest.raises(InviteCampaignValidationError) as exc_info:
        _validate_lifetime_campaign_policy(
            grant_duration_mode="lifetime",
            child_grant_duration_mode="lifetime",
            child_invite_count=12,
            max_generation_depth=5,
            require_no_active_access=True,
            block_self_redemption=True,
            root_invite_expiry_mode="none",
            child_invite_expiry_mode="none",
            campaign_expires_at=None,
            caps={},
            risk_policy=_valid_risk_policy(),
            lifetime_campaign_acknowledgement=True,
        )

    assert exc_info.value.to_detail() == {
        "code": "INVITE_CAMPAIGN_GLOBAL_ISSUE_CAP_REQUIRED",
        "message_key": "invite_campaign.global_issue_cap_required",
        "message": "Lifetime campaigns with 10 or more child invites require global_issue_cap.",
    }


def test_lifetime_acknowledgement_error_has_public_detail() -> None:
    with pytest.raises(InviteCampaignValidationError) as exc_info:
        _validate_lifetime_campaign_policy(
            grant_duration_mode="lifetime",
            child_grant_duration_mode="lifetime",
            child_invite_count=12,
            max_generation_depth=5,
            require_no_active_access=True,
            block_self_redemption=True,
            root_invite_expiry_mode="none",
            child_invite_expiry_mode="none",
            campaign_expires_at=None,
            caps={"global_issue_cap": 1500000},
            risk_policy=_valid_risk_policy(),
            lifetime_campaign_acknowledgement=False,
        )

    assert exc_info.value.to_detail() == {
        "code": "INVITE_CAMPAIGN_LIFETIME_ACK_REQUIRED",
        "message_key": "invite_campaign.lifetime_ack_required",
        "message": "Lifetime campaign acknowledgement is required.",
    }
