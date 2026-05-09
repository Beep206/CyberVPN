"""S1-PROD-005 product-level grace period behavior checks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.application.use_cases.subscriptions.stage1_expiry_grace_disable import (
    STAGE1_EXPIRY_GRACE_JOB_NAME,
    STAGE1_PAID_GRACE_PERIOD_HOURS,
    Stage1ExpiryAccessKind,
    Stage1ExpiryGraceAccessRecord,
    Stage1ExpiryGraceDecisionState,
    Stage1ExpiryGraceDisableResult,
    Stage1ExpiryGraceWorker,
    evaluate_stage1_expiry_grace,
)
from src.domain.enums import UserStatus
from src.presentation.api.shared.stage1_contract import (
    Stage1AccessState,
    Stage1ProvisioningState,
    Stage1SupportState,
)
from src.presentation.api.shared.stage1_support_templates import (
    Stage1SupportTemplateId,
    get_stage1_support_template,
)


class RecordingExpiryGateway:
    def __init__(self) -> None:
        self.disabled: list[tuple[Stage1ExpiryGraceAccessRecord, datetime]] = []

    async def disable_expired_access(
        self,
        record: Stage1ExpiryGraceAccessRecord,
        *,
        disabled_at: datetime,
    ) -> Stage1ExpiryGraceDisableResult:
        self.disabled.append((record, disabled_at))
        assert record.remnawave_uuid is not None
        return Stage1ExpiryGraceDisableResult(
            customer_account_id=record.customer_account_id,
            remnawave_uuid=record.remnawave_uuid,
            status=UserStatus.DISABLED,
            disabled_at=disabled_at,
        )


def test_s1_prod_005_paid_grace_period_is_owner_approved_72_hours() -> None:
    assert STAGE1_PAID_GRACE_PERIOD_HOURS == 72


def test_s1_prod_005_grace_state_is_self_service_renewal_without_disable_or_secret_leak() -> None:
    expires_at = datetime(2026, 5, 1, 9, 30, tzinfo=UTC)
    now = expires_at + timedelta(hours=1)
    decision = evaluate_stage1_expiry_grace(_paid_record(access_expires_at=expires_at), now=now)

    flow = decision.to_flow_status()

    assert decision.state == Stage1ExpiryGraceDecisionState.GRACE
    assert flow.access_state == Stage1AccessState.GRACE
    assert flow.provisioning_state == Stage1ProvisioningState.READY
    assert flow.support_state == Stage1SupportState.SELF_SERVICE
    assert flow.support_escalation is False
    assert flow.details["job_name"] == STAGE1_EXPIRY_GRACE_JOB_NAME
    assert flow.details["grace_ends_at"] == (expires_at + timedelta(hours=72)).isoformat()
    assert flow.details["disable_required"] is False
    assert "renew" in (flow.user_action or "").lower()
    _assert_no_runtime_secret_leak(flow.model_dump())


@pytest.mark.asyncio
async def test_s1_prod_005_paid_access_disables_only_at_72h_boundary() -> None:
    expires_at = datetime(2026, 5, 1, 9, 30, tzinfo=UTC)
    before_boundary = expires_at + timedelta(hours=STAGE1_PAID_GRACE_PERIOD_HOURS, seconds=-1)
    at_boundary = expires_at + timedelta(hours=STAGE1_PAID_GRACE_PERIOD_HOURS)
    record = _paid_record(access_expires_at=expires_at)
    gateway = RecordingExpiryGateway()

    grace = await Stage1ExpiryGraceWorker(gateway=gateway, now=lambda: before_boundary).process_record(record)
    disabled = await Stage1ExpiryGraceWorker(gateway=gateway, now=lambda: at_boundary).process_record(record)

    assert grace.state == Stage1ExpiryGraceDecisionState.GRACE
    assert grace.disable_required is False
    assert disabled.state == Stage1ExpiryGraceDecisionState.DISABLED
    assert disabled.access_state == Stage1AccessState.EXPIRED
    assert disabled.provisioning_state == Stage1ProvisioningState.SUSPENDED
    assert disabled.disabled is True
    assert gateway.disabled == [(record, at_boundary)]


@pytest.mark.asyncio
async def test_s1_prod_005_trial_has_no_paid_grace() -> None:
    expires_at = datetime(2026, 5, 1, 9, 30, tzinfo=UTC)
    record = Stage1ExpiryGraceAccessRecord(
        customer_account_id=uuid4(),
        access_kind=Stage1ExpiryAccessKind.TRIAL,
        access_expires_at=expires_at,
        remnawave_uuid=str(uuid4()),
    )
    gateway = RecordingExpiryGateway()

    decision = await Stage1ExpiryGraceWorker(gateway=gateway, now=lambda: expires_at).process_record(record)

    assert decision.state == Stage1ExpiryGraceDecisionState.DISABLED
    assert decision.grace_started_at == expires_at
    assert decision.grace_ends_at == expires_at
    assert gateway.disabled == [(record, expires_at)]


def test_s1_prod_005_missing_remnawave_uuid_after_grace_escalates_to_support_review() -> None:
    expires_at = datetime(2026, 5, 1, 9, 30, tzinfo=UTC)
    now = expires_at + timedelta(hours=73)
    decision = evaluate_stage1_expiry_grace(
        _paid_record(access_expires_at=expires_at, remnawave_uuid=None),
        now=now,
    )

    flow = decision.to_flow_status()

    assert decision.state == Stage1ExpiryGraceDecisionState.RECONCILIATION_REQUIRED
    assert flow.access_state == Stage1AccessState.EXPIRED
    assert flow.provisioning_state == Stage1ProvisioningState.RECONCILIATION_REQUIRED
    assert flow.support_state == Stage1SupportState.SUPPORT_REVIEW
    assert flow.support_escalation is True
    assert decision.error_code == "missing_remnawave_uuid"
    _assert_no_runtime_secret_leak(flow.model_dump())


def test_s1_prod_005_expired_support_template_matches_manual_renewal_policy() -> None:
    template = get_stage1_support_template(Stage1SupportTemplateId.EXPIRED_SUBSCRIPTION)
    message = template.customer_message_ru.lower()

    assert "grace period" in message
    assert "telegram mini app" in message
    assert "payment_id_or_invoice_id_if_paid" in template.safe_data_to_request
    assert "raw_subscription_url" in template.forbidden_data
    assert "password" in template.forbidden_data
    assert "renews automatically" not in message
    assert "guaranteed refund" not in message


def _paid_record(
    *,
    access_expires_at: datetime,
    remnawave_uuid: str | None = "33333333-3333-4333-8333-333333333333",
) -> Stage1ExpiryGraceAccessRecord:
    return Stage1ExpiryGraceAccessRecord(
        customer_account_id=uuid4(),
        access_kind=Stage1ExpiryAccessKind.PAID_SUBSCRIPTION,
        access_expires_at=access_expires_at,
        remnawave_uuid=remnawave_uuid,
    )


def _assert_no_runtime_secret_leak(payload: object) -> None:
    serialized = str(payload).lower()
    for forbidden in ("https://", "http://", "token", "secret", "password", "subscription_url", "config_file"):
        assert forbidden not in serialized
