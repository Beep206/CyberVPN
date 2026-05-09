"""S1-PAY-009 refund/dispute process role and provider-mode checks."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.api.shared.stage1_payment_mapping import Stage1PaymentProvider
from src.presentation.api.shared.stage1_refund_dispute_process import (
    STAGE1_REFUND_DISPUTE_PROVIDER_MODES,
    Stage1RefundProviderMode,
    build_stage1_refund_dispute_runbook,
    can_intake_stage1_refund_dispute,
    can_review_stage1_refund_dispute,
    require_stage1_refund_dispute_reviewer,
    stage1_refund_provider_mode,
)


def _admin(role: AdminRole, *, totp_enabled: bool = True) -> AdminUserModel:
    role_slug = role.value.replace("/", "-")
    return AdminUserModel(
        login=f"s1-pay-009-{role_slug}",
        email=f"{role_slug}@example.test",
        role=role.value,
        is_active=True,
        totp_enabled=totp_enabled,
    )


@pytest.mark.parametrize(
    "role",
    [
        AdminRole.FINANCE,
        AdminRole.ADMIN,
        AdminRole.SUPER_ADMIN,
        AdminRole.OWNER_SUPER_ADMIN,
    ],
)
def test_stage1_finance_and_admin_roles_can_review_refund_dispute_state(role: AdminRole) -> None:
    assert can_review_stage1_refund_dispute(role) is True
    assert can_intake_stage1_refund_dispute(role) is True


@pytest.mark.parametrize(
    "role",
    [
        AdminRole.SUPPORT,
        AdminRole.OPERATOR,
        AdminRole.VIEWER,
    ],
)
def test_stage1_support_operator_viewer_cannot_change_refund_dispute_state(role: AdminRole) -> None:
    assert can_review_stage1_refund_dispute(role) is False


def test_stage1_support_can_intake_but_not_finance_review_refund_dispute_cases() -> None:
    assert can_intake_stage1_refund_dispute(AdminRole.SUPPORT) is True
    assert can_review_stage1_refund_dispute(AdminRole.SUPPORT) is False


@pytest.mark.asyncio
async def test_stage1_refund_dispute_reviewer_dependency_is_explicit(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.presentation.api.shared.stage1_refund_dispute_process.settings.admin_2fa_required",
        True,
    )

    assert await require_stage1_refund_dispute_reviewer(_admin(AdminRole.FINANCE))
    assert await require_stage1_refund_dispute_reviewer(_admin(AdminRole.ADMIN))

    with pytest.raises(HTTPException) as support_error:
        await require_stage1_refund_dispute_reviewer(_admin(AdminRole.SUPPORT))
    assert support_error.value.status_code == 403
    assert "finance or admin" in str(support_error.value.detail)

    with pytest.raises(HTTPException) as operator_error:
        await require_stage1_refund_dispute_reviewer(_admin(AdminRole.OPERATOR))
    assert operator_error.value.status_code == 403

    with pytest.raises(HTTPException) as totp_error:
        await require_stage1_refund_dispute_reviewer(_admin(AdminRole.FINANCE, totp_enabled=False))
    assert totp_error.value.status_code == 403
    assert "2FA" in str(totp_error.value.detail)


def test_stage1_refund_provider_modes_cover_owner_approved_provider_set() -> None:
    assert set(STAGE1_REFUND_DISPUTE_PROVIDER_MODES) == set(Stage1PaymentProvider)
    assert stage1_refund_provider_mode(Stage1PaymentProvider.TELEGRAM_STARS) == (
        Stage1RefundProviderMode.TELEGRAM_STARS_API_AFTER_EVIDENCE
    )
    assert stage1_refund_provider_mode(Stage1PaymentProvider.YOOKASSA) == (
        Stage1RefundProviderMode.PROVIDER_API_AFTER_EVIDENCE
    )
    assert stage1_refund_provider_mode(Stage1PaymentProvider.PAYRAM) == (
        Stage1RefundProviderMode.PROVIDER_SUPPORT_OR_MANUAL_PAYOUT
    )


def test_stage1_refund_dispute_runbook_is_safe_to_expose_in_evidence() -> None:
    runbook = build_stage1_refund_dispute_runbook()
    serialized = str(runbook).lower()

    assert "finance" in runbook["review_roles"]
    assert "support" in runbook["support_intake_roles"]
    assert "payment_url" in runbook["forbidden_output_fields"]
    assert "raw_provider_payload" in runbook["forbidden_output_fields"]
    assert "vpn_config_url" in runbook["forbidden_output_fields"]
    assert "secret-value" not in serialized
    assert "private-key" not in serialized
