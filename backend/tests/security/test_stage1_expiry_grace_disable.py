"""S1-VPN-007 expiry/grace disable checks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

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
from src.domain.entities.user import User
from src.domain.enums import UserStatus
from src.infrastructure.remnawave.stage1_expiry_grace_gateway import RemnawaveStage1ExpiryGraceGateway
from src.presentation.api.shared.stage1_contract import (
    Stage1AccessState,
    Stage1ProvisioningState,
    Stage1SupportState,
)


class RecordingExpiryGateway:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.disabled: list[tuple[Stage1ExpiryGraceAccessRecord, datetime]] = []

    async def disable_expired_access(
        self,
        record: Stage1ExpiryGraceAccessRecord,
        *,
        disabled_at: datetime,
    ) -> Stage1ExpiryGraceDisableResult:
        self.disabled.append((record, disabled_at))
        if self.fail:
            raise TimeoutError("remnawave timeout token=should-not-leak")
        assert record.remnawave_uuid is not None
        return Stage1ExpiryGraceDisableResult(
            customer_account_id=record.customer_account_id,
            remnawave_uuid=record.remnawave_uuid,
            status=UserStatus.DISABLED,
            disabled_at=disabled_at,
        )


class FakeRemnawaveUserGateway:
    def __init__(self, user: User) -> None:
        self.user = user
        self.updated: list[tuple[UUID, dict]] = []

    async def update(self, uuid: UUID, **kwargs) -> User:
        self.updated.append((uuid, kwargs))
        return self.user


def test_paid_access_before_expiry_is_not_disabled() -> None:
    now = datetime(2026, 5, 4, 9, 30, tzinfo=UTC)
    record = _paid_record(access_expires_at=now + timedelta(minutes=1))

    decision = evaluate_stage1_expiry_grace(record, now=now)

    assert decision.state == Stage1ExpiryGraceDecisionState.ACTIVE
    assert decision.access_state == Stage1AccessState.ACTIVE
    assert decision.provisioning_state == Stage1ProvisioningState.READY
    assert decision.disable_required is False


def test_paid_access_in_72h_grace_is_not_disabled() -> None:
    expires_at = datetime(2026, 5, 1, 9, 30, tzinfo=UTC)
    now = expires_at + timedelta(hours=STAGE1_PAID_GRACE_PERIOD_HOURS, seconds=-1)
    record = _paid_record(access_expires_at=expires_at)

    decision = evaluate_stage1_expiry_grace(record, now=now)

    assert decision.state == Stage1ExpiryGraceDecisionState.GRACE
    assert decision.access_state == Stage1AccessState.GRACE
    assert decision.support_state == Stage1SupportState.SELF_SERVICE
    assert decision.grace_started_at == expires_at
    assert decision.grace_ends_at == expires_at + timedelta(hours=72)
    assert decision.disable_required is False


@pytest.mark.asyncio
async def test_paid_access_disables_at_grace_boundary_only() -> None:
    expires_at = datetime(2026, 5, 1, 9, 30, tzinfo=UTC)
    now = expires_at + timedelta(hours=STAGE1_PAID_GRACE_PERIOD_HOURS)
    record = _paid_record(access_expires_at=expires_at)
    gateway = RecordingExpiryGateway()

    decision = await Stage1ExpiryGraceWorker(gateway=gateway, now=lambda: now).process_record(record)

    assert decision.state == Stage1ExpiryGraceDecisionState.DISABLED
    assert decision.access_state == Stage1AccessState.EXPIRED
    assert decision.provisioning_state == Stage1ProvisioningState.SUSPENDED
    assert decision.disable_required is True
    assert decision.disabled is True
    assert gateway.disabled == [(record, now)]


@pytest.mark.asyncio
async def test_trial_access_has_no_paid_grace_and_disables_at_expiry() -> None:
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
    assert decision.grace_ends_at == expires_at
    assert gateway.disabled == [(record, expires_at)]


@pytest.mark.asyncio
async def test_already_disabled_access_is_not_disabled_again() -> None:
    expires_at = datetime(2026, 5, 1, 9, 30, tzinfo=UTC)
    now = expires_at + timedelta(days=10)
    record = _paid_record(access_expires_at=expires_at, current_user_status=UserStatus.DISABLED)
    gateway = RecordingExpiryGateway()

    decision = await Stage1ExpiryGraceWorker(gateway=gateway, now=lambda: now).process_record(record)

    assert decision.state == Stage1ExpiryGraceDecisionState.ALREADY_DISABLED
    assert decision.disabled is False
    assert gateway.disabled == []


def test_missing_remnawave_uuid_after_grace_requires_reconciliation() -> None:
    expires_at = datetime(2026, 5, 1, 9, 30, tzinfo=UTC)
    now = expires_at + timedelta(hours=73)
    record = _paid_record(access_expires_at=expires_at, remnawave_uuid=None)

    decision = evaluate_stage1_expiry_grace(record, now=now)

    assert decision.state == Stage1ExpiryGraceDecisionState.RECONCILIATION_REQUIRED
    assert decision.provisioning_state == Stage1ProvisioningState.RECONCILIATION_REQUIRED
    assert decision.support_state == Stage1SupportState.SUPPORT_REVIEW
    assert decision.disable_required is False
    assert decision.error_code == "missing_remnawave_uuid"


@pytest.mark.asyncio
async def test_worker_failure_preserves_due_state_and_sanitizes_result() -> None:
    expires_at = datetime(2026, 5, 1, 9, 30, tzinfo=UTC)
    now = expires_at + timedelta(hours=73)
    record = _paid_record(access_expires_at=expires_at)

    decision = await Stage1ExpiryGraceWorker(
        gateway=RecordingExpiryGateway(fail=True),
        now=lambda: now,
    ).process_record(record)

    assert decision.state == Stage1ExpiryGraceDecisionState.RECONCILIATION_REQUIRED
    assert decision.provisioning_state == Stage1ProvisioningState.RECONCILIATION_REQUIRED
    assert decision.support_state == Stage1SupportState.OPS_ESCALATION
    assert decision.disable_required is True
    assert decision.disabled is False
    serialized = str(decision.to_safe_dict()).lower()
    assert "should-not-leak" not in serialized
    assert "token=" not in serialized


@pytest.mark.asyncio
async def test_batch_worker_disables_only_records_past_policy() -> None:
    base = datetime(2026, 5, 4, 9, 30, tzinfo=UTC)
    records = [
        _paid_record(access_expires_at=base + timedelta(hours=1)),
        _paid_record(access_expires_at=base - timedelta(hours=12)),
        _paid_record(access_expires_at=base - timedelta(hours=72)),
    ]
    gateway = RecordingExpiryGateway()

    results = await Stage1ExpiryGraceWorker(gateway=gateway, now=lambda: base).process_batch(records)

    assert [result.state for result in results] == [
        Stage1ExpiryGraceDecisionState.ACTIVE,
        Stage1ExpiryGraceDecisionState.GRACE,
        Stage1ExpiryGraceDecisionState.DISABLED,
    ]
    assert gateway.disabled == [(records[2], base)]


def test_flow_status_uses_grace_and_disable_details_without_secrets() -> None:
    expires_at = datetime(2026, 5, 1, 9, 30, tzinfo=UTC)
    now = expires_at + timedelta(hours=1)
    decision = evaluate_stage1_expiry_grace(_paid_record(access_expires_at=expires_at), now=now)

    flow = decision.to_flow_status()

    assert flow.access_state == Stage1AccessState.GRACE
    assert flow.details["job_name"] == STAGE1_EXPIRY_GRACE_JOB_NAME
    assert flow.details["disable_required"] is False
    assert "renew" in (flow.user_action or "").lower()
    assert "https://" not in str(flow.details).lower()
    assert "token" not in str(flow.details).lower()


@pytest.mark.asyncio
async def test_remnawave_expiry_gateway_updates_user_to_disabled() -> None:
    remnawave_uuid = uuid4()
    disabled_at = datetime(2026, 5, 4, 9, 30, tzinfo=UTC)
    record = _paid_record(access_expires_at=disabled_at - timedelta(hours=73), remnawave_uuid=str(remnawave_uuid))
    user_gateway = FakeRemnawaveUserGateway(
        User(
            uuid=remnawave_uuid,
            username="cvpn_paid_user",
            status=UserStatus.DISABLED,
            short_uuid="redacted",
            created_at=datetime(2026, 5, 1, 9, 30, tzinfo=UTC),
            updated_at=disabled_at,
        )
    )

    result = await RemnawaveStage1ExpiryGraceGateway(user_gateway).disable_expired_access(
        record,
        disabled_at=disabled_at,
    )

    assert result.status == UserStatus.DISABLED
    assert user_gateway.updated == [(remnawave_uuid, {"status": UserStatus.DISABLED})]


def _paid_record(
    *,
    access_expires_at: datetime,
    remnawave_uuid: str | None = "33333333-3333-4333-8333-333333333333",
    current_user_status: UserStatus = UserStatus.ACTIVE,
) -> Stage1ExpiryGraceAccessRecord:
    return Stage1ExpiryGraceAccessRecord(
        customer_account_id=uuid4(),
        access_kind=Stage1ExpiryAccessKind.PAID_SUBSCRIPTION,
        access_expires_at=access_expires_at,
        remnawave_uuid=remnawave_uuid,
        current_user_status=current_user_status,
    )
