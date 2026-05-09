"""Stage 1 expiry/grace worker contract for Remnawave-backed VPN access."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from src.domain.enums import UserStatus
from src.presentation.api.shared.stage1_contract import (
    JsonScalar,
    Stage1AccessState,
    Stage1FlowStatusResponse,
    Stage1ProvisioningState,
    Stage1SupportState,
)

STAGE1_PAID_GRACE_PERIOD_HOURS = 72
STAGE1_EXPIRY_GRACE_JOB_NAME = "stage1_expiry_grace_disable"


class Stage1ExpiryGraceError(RuntimeError):
    """Raised when the S1 expiry/grace worker cannot safely process access."""


class Stage1ExpiryAccessKind(StrEnum):
    """Access kinds handled by the S1 expiry worker."""

    PAID_SUBSCRIPTION = "paid_subscription"
    TRIAL = "trial"


class Stage1ExpiryGraceDecisionState(StrEnum):
    """Internal worker decision state."""

    ACTIVE = "active"
    GRACE = "grace"
    DISABLE_DUE = "disable_due"
    DISABLED = "disabled"
    ALREADY_DISABLED = "already_disabled"
    RECONCILIATION_REQUIRED = "reconciliation_required"


@dataclass(frozen=True, slots=True)
class Stage1ExpiryGraceAccessRecord:
    """Safe access record consumed by the S1 expiry/grace worker."""

    customer_account_id: UUID
    access_kind: Stage1ExpiryAccessKind
    access_expires_at: datetime
    remnawave_uuid: str | None
    current_user_status: UserStatus = UserStatus.ACTIVE
    provider_name: str = "remnawave"

    @property
    def grace_period(self) -> timedelta:
        if self.access_kind == Stage1ExpiryAccessKind.PAID_SUBSCRIPTION:
            return timedelta(hours=STAGE1_PAID_GRACE_PERIOD_HOURS)
        return timedelta()


@dataclass(frozen=True, slots=True)
class Stage1ExpiryGraceDisableResult:
    """Safe upstream disable acknowledgement."""

    customer_account_id: UUID
    remnawave_uuid: str
    status: UserStatus
    disabled_at: datetime
    provider_name: str = "remnawave"

    def to_safe_dict(self) -> dict[str, str]:
        return {
            "customer_account_id": str(self.customer_account_id),
            "remnawave_uuid": self.remnawave_uuid,
            "status": self.status.value,
            "disabled_at": self.disabled_at.isoformat(),
            "provider_name": self.provider_name,
        }


@dataclass(frozen=True, slots=True)
class Stage1ExpiryGraceDecision:
    """Worker decision for one access record."""

    customer_account_id: UUID
    access_kind: Stage1ExpiryAccessKind
    state: Stage1ExpiryGraceDecisionState
    access_state: Stage1AccessState
    provisioning_state: Stage1ProvisioningState
    support_state: Stage1SupportState
    access_expires_at: datetime
    grace_started_at: datetime
    grace_ends_at: datetime
    evaluated_at: datetime
    disable_required: bool = False
    disabled: bool = False
    remnawave_uuid_present: bool = False
    error_code: str | None = None

    def to_safe_dict(self) -> dict[str, JsonScalar]:
        return {
            "customer_account_id": str(self.customer_account_id),
            "access_kind": self.access_kind.value,
            "state": self.state.value,
            "access_state": self.access_state.value,
            "provisioning_state": self.provisioning_state.value,
            "support_state": self.support_state.value,
            "access_expires_at": self.access_expires_at.isoformat(),
            "grace_started_at": self.grace_started_at.isoformat(),
            "grace_ends_at": self.grace_ends_at.isoformat(),
            "evaluated_at": self.evaluated_at.isoformat(),
            "disable_required": self.disable_required,
            "disabled": self.disabled,
            "remnawave_uuid_present": self.remnawave_uuid_present,
            "error_code": self.error_code,
        }

    def to_flow_status(self) -> Stage1FlowStatusResponse:
        user_action = None
        if self.access_state == Stage1AccessState.GRACE:
            user_action = "Renew access before the grace period ends."
        elif self.access_state in {Stage1AccessState.EXPIRED, Stage1AccessState.NO_ACCESS}:
            user_action = "Renew access or contact support if payment was already made."

        return Stage1FlowStatusResponse(
            access_state=self.access_state,
            provisioning_state=self.provisioning_state,
            support_state=self.support_state,
            user_action=user_action,
            support_escalation=self.support_state
            in {Stage1SupportState.SUPPORT_REVIEW, Stage1SupportState.OPS_ESCALATION},
            details={
                "job_name": STAGE1_EXPIRY_GRACE_JOB_NAME,
                "state": self.state.value,
                "access_kind": self.access_kind.value,
                "grace_ends_at": self.grace_ends_at.isoformat(),
                "disable_required": self.disable_required,
            },
        )


class Stage1ExpiryGraceGateway(Protocol):
    """Gateway implemented by Remnawave adapters or tests."""

    async def disable_expired_access(
        self,
        record: Stage1ExpiryGraceAccessRecord,
        *,
        disabled_at: datetime,
    ) -> Stage1ExpiryGraceDisableResult:
        """Disable upstream VPN access after the grace policy allows it."""


def evaluate_stage1_expiry_grace(
    record: Stage1ExpiryGraceAccessRecord,
    *,
    now: datetime | None = None,
) -> Stage1ExpiryGraceDecision:
    """Evaluate whether an access record is active, in grace or due for disable."""

    evaluated_at = _ensure_aware_utc(now or datetime.now(UTC))
    access_expires_at = _ensure_aware_utc(record.access_expires_at)
    grace_started_at = access_expires_at
    grace_ends_at = access_expires_at + record.grace_period
    remnawave_uuid_present = bool(record.remnawave_uuid)

    if record.current_user_status in {UserStatus.DISABLED, UserStatus.EXPIRED}:
        return _decision(
            record,
            state=Stage1ExpiryGraceDecisionState.ALREADY_DISABLED,
            access_state=Stage1AccessState.EXPIRED,
            provisioning_state=Stage1ProvisioningState.SUSPENDED,
            support_state=Stage1SupportState.NONE,
            evaluated_at=evaluated_at,
            access_expires_at=access_expires_at,
            grace_started_at=grace_started_at,
            grace_ends_at=grace_ends_at,
            remnawave_uuid_present=remnawave_uuid_present,
        )

    if evaluated_at < access_expires_at:
        return _decision(
            record,
            state=Stage1ExpiryGraceDecisionState.ACTIVE,
            access_state=(
                Stage1AccessState.TRIAL_ACTIVE
                if record.access_kind == Stage1ExpiryAccessKind.TRIAL
                else Stage1AccessState.ACTIVE
            ),
            provisioning_state=Stage1ProvisioningState.READY,
            support_state=Stage1SupportState.NONE,
            evaluated_at=evaluated_at,
            access_expires_at=access_expires_at,
            grace_started_at=grace_started_at,
            grace_ends_at=grace_ends_at,
            remnawave_uuid_present=remnawave_uuid_present,
        )

    if evaluated_at < grace_ends_at:
        return _decision(
            record,
            state=Stage1ExpiryGraceDecisionState.GRACE,
            access_state=Stage1AccessState.GRACE,
            provisioning_state=Stage1ProvisioningState.READY,
            support_state=Stage1SupportState.SELF_SERVICE,
            evaluated_at=evaluated_at,
            access_expires_at=access_expires_at,
            grace_started_at=grace_started_at,
            grace_ends_at=grace_ends_at,
            remnawave_uuid_present=remnawave_uuid_present,
        )

    if not remnawave_uuid_present:
        return _decision(
            record,
            state=Stage1ExpiryGraceDecisionState.RECONCILIATION_REQUIRED,
            access_state=Stage1AccessState.EXPIRED,
            provisioning_state=Stage1ProvisioningState.RECONCILIATION_REQUIRED,
            support_state=Stage1SupportState.SUPPORT_REVIEW,
            evaluated_at=evaluated_at,
            access_expires_at=access_expires_at,
            grace_started_at=grace_started_at,
            grace_ends_at=grace_ends_at,
            remnawave_uuid_present=False,
            error_code="missing_remnawave_uuid",
        )

    return _decision(
        record,
        state=Stage1ExpiryGraceDecisionState.DISABLE_DUE,
        access_state=Stage1AccessState.EXPIRED,
        provisioning_state=Stage1ProvisioningState.EXPIRED,
        support_state=Stage1SupportState.NONE,
        evaluated_at=evaluated_at,
        access_expires_at=access_expires_at,
        grace_started_at=grace_started_at,
        grace_ends_at=grace_ends_at,
        disable_required=True,
        remnawave_uuid_present=True,
    )


class Stage1ExpiryGraceWorker:
    """Runs S1 expiry/grace disable decisions through an injected gateway."""

    def __init__(
        self,
        *,
        gateway: Stage1ExpiryGraceGateway,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._gateway = gateway
        self._now = now or (lambda: datetime.now(UTC))

    async def process_record(self, record: Stage1ExpiryGraceAccessRecord) -> Stage1ExpiryGraceDecision:
        decision = evaluate_stage1_expiry_grace(record, now=self._now())
        if not decision.disable_required:
            return decision

        try:
            disable_result = await self._gateway.disable_expired_access(record, disabled_at=decision.evaluated_at)
        except Exception as exc:
            return replace(
                decision,
                state=Stage1ExpiryGraceDecisionState.RECONCILIATION_REQUIRED,
                provisioning_state=Stage1ProvisioningState.RECONCILIATION_REQUIRED,
                support_state=Stage1SupportState.OPS_ESCALATION,
                disable_required=True,
                disabled=False,
                error_code=f"disable_failed:{type(exc).__name__}",
            )

        return replace(
            decision,
            state=Stage1ExpiryGraceDecisionState.DISABLED,
            provisioning_state=Stage1ProvisioningState.SUSPENDED,
            disabled=disable_result.status == UserStatus.DISABLED,
        )

    async def process_batch(
        self,
        records: list[Stage1ExpiryGraceAccessRecord],
    ) -> list[Stage1ExpiryGraceDecision]:
        """Process a batch of candidate access records in deterministic order."""

        results: list[Stage1ExpiryGraceDecision] = []
        for record in records:
            results.append(await self.process_record(record))
        return results


def _decision(
    record: Stage1ExpiryGraceAccessRecord,
    *,
    state: Stage1ExpiryGraceDecisionState,
    access_state: Stage1AccessState,
    provisioning_state: Stage1ProvisioningState,
    support_state: Stage1SupportState,
    evaluated_at: datetime,
    access_expires_at: datetime,
    grace_started_at: datetime,
    grace_ends_at: datetime,
    disable_required: bool = False,
    remnawave_uuid_present: bool = False,
    error_code: str | None = None,
) -> Stage1ExpiryGraceDecision:
    return Stage1ExpiryGraceDecision(
        customer_account_id=record.customer_account_id,
        access_kind=record.access_kind,
        state=state,
        access_state=access_state,
        provisioning_state=provisioning_state,
        support_state=support_state,
        access_expires_at=access_expires_at,
        grace_started_at=grace_started_at,
        grace_ends_at=grace_ends_at,
        evaluated_at=evaluated_at,
        disable_required=disable_required,
        remnawave_uuid_present=remnawave_uuid_present,
        error_code=error_code,
    )


def _ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
