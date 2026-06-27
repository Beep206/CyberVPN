from __future__ import annotations

import json
import secrets
import string
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, Literal, Protocol, Self
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from src.application.use_cases.growth_codes.hashing import build_growth_code_prefix, hash_growth_code


class GrowthBenefitConfigurationError(ValueError):
    """Raised when a persisted benefit snapshot cannot be safely fulfilled."""


class GrowthBenefitSettlementNotEligibleError(ValueError):
    """Raised when benefit fulfillment is attempted before an eligible settlement."""


class DuplicateBenefitFulfillmentError(RuntimeError):
    """Raised by repositories when the deterministic fulfillment key already exists."""

    def __init__(self, idempotency_key: str) -> None:
        super().__init__("growth benefit fulfillment already exists")
        self.idempotency_key = idempotency_key


class DuplicateInviteBatchError(RuntimeError):
    """Raised by repositories when the deterministic invite batch key already exists."""

    def __init__(self, idempotency_key: str) -> None:
        super().__init__("growth invite batch already exists")
        self.idempotency_key = idempotency_key


class BenefitType(StrEnum):
    ISSUE_INVITES = "issue_invites"
    BONUS_DAYS = "bonus_days"
    WALLET_CREDIT = "wallet_credit"
    ISSUE_GIFT = "issue_gift"
    GRANT_ADDON = "grant_addon"


class BenefitMergeMode(StrEnum):
    APPEND = "append"
    REPLACE_SAME_TYPE = "replace_same_type"
    MAX = "max"
    EXCLUSIVE = "exclusive"


class FulfillmentStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    COMPLETED = "completed"
    SKIPPED = "skipped"


_POST_SETTLEMENT_TRIGGERS = frozenset({"payment_completed", "first_payment_completed", "renewal_completed"})
_SENSITIVE_RAW_CODE_KEYS = frozenset(
    {
        "raw_code",
        "rawCode",
        "code",
        "code_input",
        "promo_code",
        "invite_code",
        "gift_code",
        "raw_code_encrypted",
    }
)
_INVITE_CODE_ALPHABET = string.ascii_uppercase + string.digits
_INVITE_CODE_PREFIX = "GI"


class IssueInvitesBenefitConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    count: int = Field(ge=1, le=1_000)
    friend_days: int = Field(ge=1, le=3_660)
    expiry_mode: Literal["none", "relative", "absolute"]
    expiry_days: int | None = Field(default=None, ge=1, le=3_660)
    absolute_expires_at: datetime | None = None
    entitlement_mode: Literal["profile_key", "plan_id", "custom_snapshot"]
    entitlement_profile_key: str | None = Field(default=None, min_length=1, max_length=80)
    plan_id: UUID | None = None
    entitlement_snapshot: dict[str, Any] | None = None
    allow_zero_net_payment: bool = False
    minimum_net_paid_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    owner_mode: Literal["buyer"] = "buyer"
    reversal_mode: Literal[
        "revoke_unredeemed",
        "revoke_if_unused",
        "reverse_always",
        "manual_review",
        "none",
        "never",
    ] = "revoke_unredeemed"

    @field_validator("absolute_expires_at")
    @classmethod
    def _normalize_absolute_expiry(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("absolute_expires_at must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("entitlement_snapshot")
    @classmethod
    def _validate_entitlement_snapshot(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        _ensure_no_raw_code_material(value)
        return _json_dict(value)

    @model_validator(mode="after")
    def _validate_shape(self) -> Self:
        if self.expiry_mode == "none" and (self.expiry_days is not None or self.absolute_expires_at is not None):
            raise ValueError("none expiry cannot include relative or absolute expiry values")
        if self.expiry_mode == "relative" and (self.expiry_days is None or self.absolute_expires_at is not None):
            raise ValueError("relative expiry requires expiry_days only")
        if self.expiry_mode == "absolute" and (self.absolute_expires_at is None or self.expiry_days is not None):
            raise ValueError("absolute expiry requires absolute_expires_at only")
        if self.entitlement_mode == "profile_key" and not self.entitlement_profile_key:
            raise ValueError("profile_key entitlement requires entitlement_profile_key")
        if self.entitlement_mode == "profile_key" and self.plan_id is not None:
            raise ValueError("profile_key entitlement cannot include plan_id")
        if self.entitlement_mode == "plan_id" and self.plan_id is None:
            raise ValueError("plan_id entitlement requires plan_id")
        if self.entitlement_mode == "custom_snapshot" and not self.entitlement_snapshot:
            raise ValueError("custom_snapshot entitlement requires entitlement_snapshot")
        return self


class BonusDaysBenefitConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    days: int = Field(ge=1, le=3_660)
    grant_mode: Literal["extend_current_subscription", "create_reward_allocation"] = "create_reward_allocation"
    entitlement_profile_key: str | None = Field(default=None, min_length=1, max_length=80)
    allow_zero_net_payment: bool = False
    minimum_net_paid_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    reversal_mode: Literal[
        "shorten_entitlement",
        "revoke_unapplied",
        "reverse_always",
        "manual_review",
        "proportional",
        "none",
        "never",
    ] = "revoke_unapplied"


class WalletCreditBenefitConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    amount: Decimal = Field(gt=Decimal("0"))
    currency: str = Field(default="USD", min_length=3, max_length=12)
    description_key: str = Field(default="growth.benefit.walletCredit", min_length=1, max_length=120)
    allow_zero_net_payment: bool = False
    minimum_net_paid_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    reversal_mode: Literal["wallet_debit", "reverse_always", "manual_review", "none", "never"] = "manual_review"

    @field_validator("currency")
    @classmethod
    def _normalize_currency(cls, value: str) -> str:
        return value.upper()


class IssueGiftBenefitConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    count: int = Field(ge=1, le=1_000)
    friend_days: int = Field(ge=1, le=3_660)
    expiry_mode: Literal["none", "relative", "absolute"]
    expiry_days: int | None = Field(default=None, ge=1, le=3_660)
    absolute_expires_at: datetime | None = None
    entitlement_mode: Literal["profile_key", "plan_id", "custom_snapshot"]
    entitlement_profile_key: str | None = Field(default=None, min_length=1, max_length=80)
    plan_id: UUID | None = None
    entitlement_snapshot: dict[str, Any] | None = None
    allow_zero_net_payment: bool = False
    minimum_net_paid_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    reversal_mode: Literal[
        "revoke_unredeemed",
        "revoke_if_unused",
        "reverse_always",
        "manual_review",
        "none",
        "never",
    ] = "revoke_unredeemed"

    @field_validator("absolute_expires_at")
    @classmethod
    def _normalize_absolute_expiry(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("absolute_expires_at must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("entitlement_snapshot")
    @classmethod
    def _validate_entitlement_snapshot(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        _ensure_no_raw_code_material(value)
        return _json_dict(value)

    @model_validator(mode="after")
    def _validate_shape(self) -> Self:
        _validate_expiry_shape(
            expiry_mode=self.expiry_mode,
            expiry_days=self.expiry_days,
            absolute_expires_at=self.absolute_expires_at,
        )
        _validate_entitlement_shape(
            entitlement_mode=self.entitlement_mode,
            entitlement_profile_key=self.entitlement_profile_key,
            plan_id=self.plan_id,
            entitlement_snapshot=self.entitlement_snapshot,
        )
        return self


class GrantAddonBenefitConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    addon_code: str = Field(min_length=1, max_length=80)
    quantity: int = Field(default=1, ge=1, le=100)
    duration_mode: Literal["match_plan", "fixed_days"] = "match_plan"
    duration_days: int | None = Field(default=None, ge=1, le=3_660)
    location_code: str | None = Field(default=None, min_length=1, max_length=64)
    allow_zero_net_payment: bool = False
    minimum_net_paid_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    reversal_mode: Literal["revoke_addon", "reverse_always", "manual_review", "none", "never"] = "revoke_addon"

    @model_validator(mode="after")
    def _validate_shape(self) -> Self:
        if self.duration_mode == "fixed_days" and self.duration_days is None:
            raise ValueError("fixed_days addon grant requires duration_days")
        if self.duration_mode == "match_plan" and self.duration_days is not None:
            raise ValueError("match_plan addon grant cannot include duration_days")
        return self


BenefitConfig = (
    IssueInvitesBenefitConfig
    | BonusDaysBenefitConfig
    | WalletCreditBenefitConfig
    | IssueGiftBenefitConfig
    | GrantAddonBenefitConfig
)


class GrowthBenefitSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True, populate_by_name=True)

    benefit_id: UUID = Field(validation_alias=AliasChoices("benefit_id", "id"))
    benefit_type: BenefitType = Field(validation_alias=AliasChoices("benefit_type", "type"))
    trigger_type: str = "payment_completed"
    merge_mode: BenefitMergeMode = BenefitMergeMode.APPEND
    config: dict[str, Any] = Field(default_factory=dict)
    sort_order: int = 0
    is_active: bool = True
    source_priority: int | None = None
    growth_code_id: UUID | None = None
    campaign_id: UUID | None = None


class GrowthApplicationSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    growth_code_id: UUID | None = None
    campaign_id: UUID | None = None
    source_type: str | None = None
    source_priority: int | None = None
    benefits: list[GrowthBenefitSnapshot] = Field(default_factory=list)


class GrowthSettlementSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    net_customer_paid_amount: Decimal | None = None
    gateway_amount: Decimal | None = None
    settlement_mode: str | None = None


class FulfillGrowthBenefitsCommand(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid", frozen=True)

    order_id: UUID
    payment_id: UUID
    user_id: UUID
    growth_effects_snapshot: Mapping[str, Any] = Field(default_factory=dict)
    settlement_completed: bool = True
    occurred_at: datetime | None = None

    @field_validator("occurred_at")
    @classmethod
    def _normalize_occurred_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class BenefitFulfillmentRecord:
    id: UUID
    benefit_id: UUID
    growth_code_id: UUID
    user_id: UUID
    order_id: UUID
    payment_id: UUID
    idempotency_key: str
    status: str
    attempt_count: int
    config_snapshot: dict[str, Any]
    result_payload: dict[str, Any]
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    next_retry_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class NewBenefitFulfillment:
    benefit_id: UUID
    growth_code_id: UUID
    user_id: UUID
    order_id: UUID
    payment_id: UUID
    idempotency_key: str
    status: str
    attempt_count: int
    config_snapshot: dict[str, Any]
    result_payload: dict[str, Any]
    started_at: datetime


@dataclass(frozen=True, slots=True)
class InviteBatchRecord:
    id: UUID
    owner_user_id: UUID
    campaign_id: UUID | None
    source_growth_code_id: UUID | None
    source_benefit_id: UUID | None
    source_order_id: UUID | None
    source_payment_id: UUID | None
    source_type: str
    requested_count: int
    issued_count: int
    friend_days: int
    expiry_mode: str
    expiry_days: int | None
    expires_at: datetime | None
    entitlement_mode: str
    entitlement_profile_key: str | None
    plan_id: UUID | None
    entitlement_snapshot: dict[str, Any]
    status: str
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class NewInviteBatch:
    owner_user_id: UUID
    campaign_id: UUID | None
    source_growth_code_id: UUID
    source_benefit_id: UUID
    source_order_id: UUID
    source_payment_id: UUID
    source_type: str
    requested_count: int
    issued_count: int
    friend_days: int
    expiry_mode: str
    expiry_days: int | None
    expires_at: datetime | None
    entitlement_mode: str
    entitlement_profile_key: str | None
    plan_id: UUID | None
    entitlement_snapshot: dict[str, Any]
    status: str
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class InviteCodeRecord:
    id: UUID
    owner_user_id: UUID
    batch_id: UUID
    source_growth_code_id: UUID
    source_benefit_id: UUID
    source_payment_id: UUID
    free_days: int
    expires_at: datetime | None
    code_hash: str
    code_prefix: str
    status: str


@dataclass(frozen=True, slots=True)
class NewInviteCode:
    code: str
    owner_user_id: UUID
    free_days: int
    plan_id: UUID | None
    batch_id: UUID
    source_growth_code_id: UUID
    source_benefit_id: UUID
    source_payment_id: UUID
    expires_at: datetime | None
    code_hash: str
    code_prefix: str
    entitlement_mode: str
    entitlement_profile_key: str | None
    entitlement_snapshot: dict[str, Any]


@dataclass(frozen=True, slots=True)
class FulfillmentResult:
    fulfillment_id: UUID
    benefit_id: UUID
    benefit_type: str
    growth_code_id: UUID
    idempotency_key: str
    status: str
    duplicate: bool
    result_payload: dict[str, Any]


class GrowthBenefitFulfillmentRepository(Protocol):
    async def get_fulfillment_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> BenefitFulfillmentRecord | None:
        raise NotImplementedError

    async def create_fulfillment(self, data: NewBenefitFulfillment) -> BenefitFulfillmentRecord:
        raise NotImplementedError

    async def set_fulfillment_result(
        self,
        *,
        fulfillment_id: UUID,
        status: str,
        result_payload: dict[str, Any],
        completed_at: datetime | None,
    ) -> BenefitFulfillmentRecord:
        raise NotImplementedError

    async def get_invite_batch_by_idempotency_key(self, idempotency_key: str) -> InviteBatchRecord | None:
        raise NotImplementedError

    async def create_invite_batch(self, data: NewInviteBatch) -> InviteBatchRecord:
        raise NotImplementedError

    async def set_invite_batch_issued(
        self,
        *,
        batch_id: UUID,
        issued_count: int,
        status: str,
    ) -> InviteBatchRecord:
        raise NotImplementedError

    async def list_invite_codes_for_batch(self, batch_id: UUID) -> tuple[InviteCodeRecord, ...]:
        raise NotImplementedError

    async def create_invite_codes(self, data: tuple[NewInviteCode, ...]) -> tuple[InviteCodeRecord, ...]:
        raise NotImplementedError

    async def apply_wallet_credit_benefit(
        self,
        *,
        user_id: UUID,
        fulfillment_id: UUID,
        amount: Decimal,
        currency: str,
        description_key: str,
    ) -> dict[str, Any]:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class _PreparedBenefit:
    application: GrowthApplicationSnapshot
    benefit: GrowthBenefitSnapshot
    source_priority: int
    input_index: int


class FulfillGrowthBenefitsUseCase:
    """Record post-settlement benefit fulfillment work inside a caller-owned transaction."""

    def __init__(self, repository: GrowthBenefitFulfillmentRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        *,
        order_id: UUID,
        payment_id: UUID,
        user_id: UUID,
        growth_effects_snapshot: Mapping[str, Any],
        settlement_completed: bool = True,
        occurred_at: datetime | None = None,
    ) -> list[FulfillmentResult]:
        command = FulfillGrowthBenefitsCommand(
            order_id=order_id,
            payment_id=payment_id,
            user_id=user_id,
            growth_effects_snapshot=growth_effects_snapshot,
            settlement_completed=settlement_completed,
            occurred_at=occurred_at,
        )
        if not command.settlement_completed:
            raise GrowthBenefitSettlementNotEligibleError("benefits require completed settlement")

        snapshot = _json_dict(command.growth_effects_snapshot)
        _ensure_no_raw_code_material(snapshot)
        settlement = _extract_settlement(snapshot)
        selected = _apply_merge_modes(_extract_post_settlement_benefits(snapshot))
        now = command.occurred_at or datetime.now(UTC)

        results: list[FulfillmentResult] = []
        for prepared in selected:
            if not prepared.benefit.is_active:
                continue
            config = _validate_benefit_config(prepared.benefit)
            _enforce_settlement_allowed(config=config, settlement=settlement)
            growth_code_id = prepared.benefit.growth_code_id or prepared.application.growth_code_id
            if growth_code_id is None:
                raise GrowthBenefitConfigurationError("benefit snapshot is missing growth_code_id")
            fulfillment, duplicate = await self._get_or_create_fulfillment(
                benefit=prepared.benefit,
                growth_code_id=growth_code_id,
                command=command,
                config=config,
                now=now,
            )

            if _has_recorded_result(fulfillment):
                results.append(_result_from_record(fulfillment, prepared.benefit.benefit_type, duplicate=True))
                continue

            if prepared.benefit.benefit_type != BenefitType.ISSUE_INVITES:
                fulfillment = await self._fulfill_non_invite_benefit(
                    benefit=prepared.benefit,
                    fulfillment=fulfillment,
                    config=config,
                    command=command,
                    now=now,
                )
                results.append(_result_from_record(fulfillment, prepared.benefit.benefit_type, duplicate=duplicate))
                continue

            if not isinstance(config, IssueInvitesBenefitConfig):
                raise GrowthBenefitConfigurationError("issue_invites benefit config is invalid")
            batch, batch_duplicate = await self._get_or_create_invite_batch(
                prepared=prepared,
                growth_code_id=growth_code_id,
                config=config,
                command=command,
                now=now,
            )
            invite_codes = await self._ensure_invite_codes(
                batch=batch,
                growth_code_id=growth_code_id,
                config=config,
                command=command,
            )
            if batch.issued_count != len(invite_codes) or batch.status != "issued":
                batch = await self._repository.set_invite_batch_issued(
                    batch_id=batch.id,
                    issued_count=len(invite_codes),
                    status="issued",
                )
            result_payload = {
                "invite_batch_id": str(batch.id),
                "requested_count": batch.requested_count,
                "issued_count": batch.issued_count,
                "reversal_mode": config.reversal_mode,
                "reversal_policy": _canonical_reversal_policy(config.reversal_mode),
                "invite_code_ids": [str(code.id) for code in invite_codes],
                "invite_code_refs": [
                    {
                        "id": str(code.id),
                        "code_hash": code.code_hash,
                        "code_prefix": code.code_prefix,
                        "status": code.status,
                    }
                    for code in invite_codes
                ],
            }
            fulfillment = await self._repository.set_fulfillment_result(
                fulfillment_id=fulfillment.id,
                status=FulfillmentStatus.COMPLETED.value,
                result_payload=result_payload,
                completed_at=now,
            )
            results.append(
                FulfillmentResult(
                    fulfillment_id=fulfillment.id,
                    benefit_id=fulfillment.benefit_id,
                    benefit_type=prepared.benefit.benefit_type.value,
                    growth_code_id=fulfillment.growth_code_id,
                    idempotency_key=fulfillment.idempotency_key,
                    status=fulfillment.status,
                    duplicate=duplicate or batch_duplicate,
                    result_payload=result_payload,
                )
            )

        return results

    async def _get_or_create_fulfillment(
        self,
        *,
        benefit: GrowthBenefitSnapshot,
        growth_code_id: UUID,
        command: FulfillGrowthBenefitsCommand,
        config: BenefitConfig,
        now: datetime,
    ) -> tuple[BenefitFulfillmentRecord, bool]:
        idempotency_key = build_growth_benefit_idempotency_key(
            benefit_id=benefit.benefit_id,
            payment_id=command.payment_id,
        )
        existing = await self._repository.get_fulfillment_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing, True

        try:
            created = await self._repository.create_fulfillment(
                NewBenefitFulfillment(
                    benefit_id=benefit.benefit_id,
                    growth_code_id=growth_code_id,
                    user_id=command.user_id,
                    order_id=command.order_id,
                    payment_id=command.payment_id,
                    idempotency_key=idempotency_key,
                    status=FulfillmentStatus.PENDING.value,
                    attempt_count=1,
                    config_snapshot=_fulfillment_config_snapshot(config),
                    result_payload={},
                    started_at=now,
                )
            )
        except DuplicateBenefitFulfillmentError:
            existing = await self._repository.get_fulfillment_by_idempotency_key(idempotency_key)
            if existing is None:
                raise
            return existing, True
        return created, False

    async def _fulfill_non_invite_benefit(
        self,
        *,
        benefit: GrowthBenefitSnapshot,
        fulfillment: BenefitFulfillmentRecord,
        config: BenefitConfig,
        command: FulfillGrowthBenefitsCommand,
        now: datetime,
    ) -> BenefitFulfillmentRecord:
        config_payload = _fulfillment_config_snapshot(config)
        if benefit.benefit_type == BenefitType.WALLET_CREDIT:
            if not isinstance(config, WalletCreditBenefitConfig):
                raise GrowthBenefitConfigurationError("wallet_credit benefit config is invalid")
            wallet_result = await self._repository.apply_wallet_credit_benefit(
                user_id=command.user_id,
                fulfillment_id=fulfillment.id,
                amount=config.amount,
                currency=config.currency,
                description_key=config.description_key,
            )
            result_payload = {
                "benefit_type": benefit.benefit_type.value,
                "side_effect_mode": "wallet_transaction",
                "wallet_credit": {
                    "amount": str(config.amount),
                    "currency": config.currency,
                    "description_key": config.description_key,
                    **wallet_result,
                },
                "reversal_mode": config.reversal_mode,
                "reversal_policy": _canonical_reversal_policy(config.reversal_mode),
            }
            return await self._repository.set_fulfillment_result(
                fulfillment_id=fulfillment.id,
                status=FulfillmentStatus.COMPLETED.value,
                result_payload=result_payload,
                completed_at=now,
            )

        result_payload = {
            "benefit_type": benefit.benefit_type.value,
            "side_effect_mode": "queued_domain_worker",
            "config": config_payload,
            "reversal_mode": config_payload.get("reversal_mode"),
            "reversal_policy": config_payload.get("reversal_policy"),
        }
        return await self._repository.set_fulfillment_result(
            fulfillment_id=fulfillment.id,
            status=FulfillmentStatus.QUEUED.value,
            result_payload=result_payload,
            completed_at=None,
        )

    async def _ensure_invite_codes(
        self,
        *,
        batch: InviteBatchRecord,
        growth_code_id: UUID,
        config: IssueInvitesBenefitConfig,
        command: FulfillGrowthBenefitsCommand,
    ) -> tuple[InviteCodeRecord, ...]:
        existing = await self._repository.list_invite_codes_for_batch(batch.id)
        if len(existing) >= config.count:
            return tuple(sorted(existing, key=lambda item: str(item.id))[: config.count])
        missing_count = config.count - len(existing)
        new_codes = tuple(
            _new_invite_code(
                batch=batch,
                growth_code_id=growth_code_id,
                config=config,
                command=command,
            )
            for _ in range(missing_count)
        )
        created = await self._repository.create_invite_codes(new_codes)
        return tuple(sorted((*existing, *created), key=lambda item: str(item.id)))

    async def _get_or_create_invite_batch(
        self,
        *,
        prepared: _PreparedBenefit,
        growth_code_id: UUID,
        config: IssueInvitesBenefitConfig,
        command: FulfillGrowthBenefitsCommand,
        now: datetime,
    ) -> tuple[InviteBatchRecord, bool]:
        idempotency_key = build_invite_batch_idempotency_key(
            benefit_id=prepared.benefit.benefit_id,
            payment_id=command.payment_id,
        )
        existing = await self._repository.get_invite_batch_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing, True

        try:
            created = await self._repository.create_invite_batch(
                NewInviteBatch(
                    owner_user_id=command.user_id,
                    campaign_id=prepared.benefit.campaign_id or prepared.application.campaign_id,
                    source_growth_code_id=growth_code_id,
                    source_benefit_id=prepared.benefit.benefit_id,
                    source_order_id=command.order_id,
                    source_payment_id=command.payment_id,
                    source_type="growth_benefit",
                    requested_count=config.count,
                    issued_count=0,
                    friend_days=config.friend_days,
                    expiry_mode=config.expiry_mode,
                    expiry_days=config.expiry_days,
                    expires_at=_resolve_invite_batch_expiry(config=config, now=now),
                    entitlement_mode=config.entitlement_mode,
                    entitlement_profile_key=config.entitlement_profile_key,
                    plan_id=config.plan_id,
                    entitlement_snapshot=config.entitlement_snapshot or {},
                    status="pending_codes",
                    idempotency_key=idempotency_key,
                )
            )
        except DuplicateInviteBatchError:
            existing = await self._repository.get_invite_batch_by_idempotency_key(idempotency_key)
            if existing is None:
                raise
            return existing, True
        return created, False


def build_growth_benefit_idempotency_key(*, benefit_id: UUID, payment_id: UUID) -> str:
    return f"growth-benefit:{benefit_id}:payment:{payment_id}"


def build_invite_batch_idempotency_key(*, benefit_id: UUID, payment_id: UUID) -> str:
    return f"growth-invite-batch:{benefit_id}:payment:{payment_id}"


def build_growth_invite_code_value() -> str:
    suffix = "".join(secrets.choice(_INVITE_CODE_ALPHABET) for _ in range(14))
    return f"{_INVITE_CODE_PREFIX}-{suffix}"


def _new_invite_code(
    *,
    batch: InviteBatchRecord,
    growth_code_id: UUID,
    config: IssueInvitesBenefitConfig,
    command: FulfillGrowthBenefitsCommand,
) -> NewInviteCode:
    if batch.source_benefit_id is None:
        raise GrowthBenefitConfigurationError("invite batch is missing source_benefit_id")
    code = build_growth_invite_code_value()
    return NewInviteCode(
        code=code,
        owner_user_id=command.user_id,
        free_days=config.friend_days,
        plan_id=config.plan_id,
        batch_id=batch.id,
        source_growth_code_id=growth_code_id,
        source_benefit_id=batch.source_benefit_id,
        source_payment_id=command.payment_id,
        expires_at=batch.expires_at,
        code_hash=hash_growth_code(code),
        code_prefix=build_growth_code_prefix(code),
        entitlement_mode=config.entitlement_mode,
        entitlement_profile_key=config.entitlement_profile_key,
        entitlement_snapshot=config.entitlement_snapshot or {},
    )


def _extract_post_settlement_benefits(snapshot: dict[str, Any]) -> list[_PreparedBenefit]:
    applications = _extract_application_snapshots(snapshot)
    prepared: list[_PreparedBenefit] = []
    input_index = 0
    for application in applications:
        for benefit in application.benefits:
            if benefit.trigger_type not in _POST_SETTLEMENT_TRIGGERS:
                continue
            prepared.append(
                _PreparedBenefit(
                    application=application,
                    benefit=benefit,
                    source_priority=benefit.source_priority
                    if benefit.source_priority is not None
                    else _source_priority(application),
                    input_index=input_index,
                )
            )
            input_index += 1
    return prepared


def _extract_application_snapshots(snapshot: dict[str, Any]) -> list[GrowthApplicationSnapshot]:
    raw_applications: list[Mapping[str, Any]] = []
    code_set = snapshot.get("code_set")
    if isinstance(code_set, Mapping):
        applications = code_set.get("applications")
        if isinstance(applications, list):
            raw_applications.extend(item for item in applications if isinstance(item, Mapping))

    applications = snapshot.get("applications")
    if isinstance(applications, list):
        raw_applications.extend(item for item in applications if isinstance(item, Mapping))

    growth_effects = snapshot.get("growth_effects")
    if isinstance(growth_effects, Mapping):
        raw_applications.append(growth_effects)

    if isinstance(snapshot.get("benefits"), list):
        raw_applications.append(snapshot)

    parsed: list[GrowthApplicationSnapshot] = []
    for raw in raw_applications:
        try:
            parsed.append(GrowthApplicationSnapshot.model_validate(raw))
        except ValidationError as exc:
            raise GrowthBenefitConfigurationError("growth application snapshot is invalid") from exc
    return parsed


def _apply_merge_modes(prepared: list[_PreparedBenefit]) -> list[_PreparedBenefit]:
    selected: list[_PreparedBenefit] = []
    for item in sorted(
        prepared,
        key=lambda candidate: (
            candidate.source_priority,
            candidate.benefit.sort_order,
            str(candidate.benefit.benefit_id),
            candidate.input_index,
        ),
    ):
        same_type = [candidate for candidate in selected if candidate.benefit.benefit_type == item.benefit.benefit_type]
        if item.benefit.merge_mode == BenefitMergeMode.APPEND or not same_type:
            selected.append(item)
            continue
        if item.benefit.merge_mode == BenefitMergeMode.EXCLUSIVE:
            raise GrowthBenefitConfigurationError("exclusive benefit conflicts with an existing benefit type")
        if item.benefit.merge_mode == BenefitMergeMode.REPLACE_SAME_TYPE:
            selected = [
                candidate for candidate in selected if candidate.benefit.benefit_type != item.benefit.benefit_type
            ]
            selected.append(item)
            continue
        if item.benefit.merge_mode == BenefitMergeMode.MAX:
            winner = max(
                [*same_type, item],
                key=lambda candidate: (
                    _benefit_merge_value(candidate.benefit),
                    candidate.source_priority,
                    -candidate.input_index,
                ),
            )
            selected = [
                candidate for candidate in selected if candidate.benefit.benefit_type != item.benefit.benefit_type
            ]
            selected.append(winner)
    return selected


def _source_priority(application: GrowthApplicationSnapshot) -> int:
    if application.source_priority is not None:
        return application.source_priority
    return {
        "plan": 10,
        "offer": 20,
        "promo": 30,
        "admin": 40,
        "manual": 40,
    }.get(application.source_type or "", 30)


def _issue_invites_count(benefit: GrowthBenefitSnapshot) -> int:
    if benefit.benefit_type != BenefitType.ISSUE_INVITES:
        return 0
    try:
        config = _validate_issue_invites_config(benefit.config)
    except GrowthBenefitConfigurationError:
        return 0
    return config.count


def _benefit_merge_value(benefit: GrowthBenefitSnapshot) -> Decimal:
    try:
        config = _validate_benefit_config(benefit)
    except GrowthBenefitConfigurationError:
        return Decimal("0")
    if isinstance(config, IssueInvitesBenefitConfig | IssueGiftBenefitConfig):
        return Decimal(config.count)
    if isinstance(config, BonusDaysBenefitConfig):
        return Decimal(config.days)
    if isinstance(config, WalletCreditBenefitConfig):
        return config.amount
    if isinstance(config, GrantAddonBenefitConfig):
        return Decimal(config.quantity)
    return Decimal("0")


def _validate_benefit_config(benefit: GrowthBenefitSnapshot) -> BenefitConfig:
    if benefit.benefit_type == BenefitType.ISSUE_INVITES:
        return _validate_issue_invites_config(benefit.config)
    normalized_config = _normalize_reversal_policy_alias(benefit.config)
    _ensure_no_raw_code_material(normalized_config)
    try:
        if benefit.benefit_type == BenefitType.BONUS_DAYS:
            return BonusDaysBenefitConfig.model_validate(normalized_config)
        if benefit.benefit_type == BenefitType.WALLET_CREDIT:
            return WalletCreditBenefitConfig.model_validate(normalized_config)
        if benefit.benefit_type == BenefitType.ISSUE_GIFT:
            return IssueGiftBenefitConfig.model_validate(normalized_config)
        if benefit.benefit_type == BenefitType.GRANT_ADDON:
            return GrantAddonBenefitConfig.model_validate(normalized_config)
    except ValidationError as exc:
        raise GrowthBenefitConfigurationError(f"{benefit.benefit_type.value} benefit config is invalid") from exc
    raise GrowthBenefitConfigurationError(f"{benefit.benefit_type.value} benefit type is unsupported")


def _validate_issue_invites_config(config: Mapping[str, Any]) -> IssueInvitesBenefitConfig:
    normalized_config = _normalize_reversal_policy_alias(config)
    _ensure_no_raw_code_material(normalized_config)
    try:
        return IssueInvitesBenefitConfig.model_validate(normalized_config)
    except ValidationError as exc:
        raise GrowthBenefitConfigurationError("issue_invites benefit config is invalid") from exc


def _normalize_reversal_policy_alias(config: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(config)
    policy = payload.pop("reversal_policy", None)
    mode = payload.get("reversal_mode")
    if policy in (None, ""):
        return payload
    policy_text = str(policy)
    if policy_text not in {"never", "revoke_if_unused", "reverse_always", "manual_review", "proportional"}:
        raise GrowthBenefitConfigurationError("reversal_policy is unsupported")
    if mode not in (None, "") and _canonical_reversal_policy(str(mode)) != policy_text:
        raise GrowthBenefitConfigurationError("reversal_policy conflicts with reversal_mode")
    payload["reversal_mode"] = policy_text if mode in (None, "") else mode
    return payload


def _fulfillment_config_snapshot(config: BenefitConfig) -> dict[str, Any]:
    payload = config.model_dump(mode="json")
    payload["reversal_policy"] = _canonical_reversal_policy(str(payload.get("reversal_mode") or "manual_review"))
    return payload


def _canonical_reversal_policy(reversal_mode: str) -> str:
    return {
        "none": "never",
        "never": "never",
        "revoke_unredeemed": "revoke_if_unused",
        "revoke_unapplied": "revoke_if_unused",
        "revoke_if_unused": "revoke_if_unused",
        "revoke_addon": "reverse_always",
        "wallet_debit": "reverse_always",
        "shorten_entitlement": "reverse_always",
        "reverse_always": "reverse_always",
        "manual_review": "manual_review",
        "proportional": "proportional",
    }.get(reversal_mode, "manual_review")


def _validate_expiry_shape(
    *,
    expiry_mode: str,
    expiry_days: int | None,
    absolute_expires_at: datetime | None,
) -> None:
    if expiry_mode == "none" and (expiry_days is not None or absolute_expires_at is not None):
        raise ValueError("none expiry cannot include relative or absolute expiry values")
    if expiry_mode == "relative" and (expiry_days is None or absolute_expires_at is not None):
        raise ValueError("relative expiry requires expiry_days only")
    if expiry_mode == "absolute" and (absolute_expires_at is None or expiry_days is not None):
        raise ValueError("absolute expiry requires absolute_expires_at only")


def _validate_entitlement_shape(
    *,
    entitlement_mode: str,
    entitlement_profile_key: str | None,
    plan_id: UUID | None,
    entitlement_snapshot: dict[str, Any] | None,
) -> None:
    if entitlement_mode == "profile_key" and not entitlement_profile_key:
        raise ValueError("profile_key entitlement requires entitlement_profile_key")
    if entitlement_mode == "profile_key" and plan_id is not None:
        raise ValueError("profile_key entitlement cannot include plan_id")
    if entitlement_mode == "plan_id" and plan_id is None:
        raise ValueError("plan_id entitlement requires plan_id")
    if entitlement_mode == "custom_snapshot" and not entitlement_snapshot:
        raise ValueError("custom_snapshot entitlement requires entitlement_snapshot")


def _extract_settlement(snapshot: dict[str, Any]) -> GrowthSettlementSnapshot:
    raw_settlement: Mapping[str, Any] = {}
    growth_effects = snapshot.get("growth_effects")
    if isinstance(growth_effects, Mapping) and isinstance(growth_effects.get("settlement"), Mapping):
        raw_settlement = growth_effects["settlement"]
    elif isinstance(snapshot.get("settlement"), Mapping):
        raw_settlement = snapshot["settlement"]
    elif isinstance(snapshot.get("pricing"), Mapping):
        pricing = snapshot["pricing"]
        raw_settlement = {
            "net_customer_paid_amount": pricing.get("gateway_amount"),
            "gateway_amount": pricing.get("gateway_amount"),
            "settlement_mode": "internal_zero" if _decimal_or_zero(pricing.get("gateway_amount")) <= 0 else None,
        }
    try:
        return GrowthSettlementSnapshot.model_validate(raw_settlement)
    except ValidationError as exc:
        raise GrowthBenefitSettlementNotEligibleError("settlement snapshot is invalid") from exc


def _enforce_settlement_allowed(
    *,
    config: BenefitConfig,
    settlement: GrowthSettlementSnapshot,
) -> None:
    paid_amount = settlement.net_customer_paid_amount
    if paid_amount is None:
        paid_amount = settlement.gateway_amount
    paid_amount = paid_amount if paid_amount is not None else Decimal("0")
    is_zero_net = paid_amount <= Decimal("0") or settlement.settlement_mode == "internal_zero"
    if is_zero_net and not bool(getattr(config, "allow_zero_net_payment", False)):
        raise GrowthBenefitSettlementNotEligibleError("zero-net settlement is not allowed for this benefit")
    minimum_net_paid_amount = getattr(config, "minimum_net_paid_amount", Decimal("0"))
    if not is_zero_net and paid_amount < minimum_net_paid_amount:
        raise GrowthBenefitSettlementNotEligibleError("settlement paid amount is below benefit minimum")


def _resolve_invite_batch_expiry(*, config: IssueInvitesBenefitConfig, now: datetime) -> datetime | None:
    if config.expiry_mode == "none":
        return None
    if config.expiry_mode == "absolute":
        return config.absolute_expires_at
    if config.expiry_days is None:
        raise GrowthBenefitConfigurationError("relative invite expiry requires expiry_days")
    return now + timedelta(days=config.expiry_days)


def _has_recorded_result(record: BenefitFulfillmentRecord) -> bool:
    if not record.result_payload:
        return False
    invite_batch_id = record.result_payload.get("invite_batch_id")
    if isinstance(invite_batch_id, str) and invite_batch_id:
        return True
    benefit_type = record.result_payload.get("benefit_type")
    return isinstance(benefit_type, str) and bool(benefit_type)


def _result_from_record(
    record: BenefitFulfillmentRecord,
    benefit_type: BenefitType,
    *,
    duplicate: bool,
) -> FulfillmentResult:
    return FulfillmentResult(
        fulfillment_id=record.id,
        benefit_id=record.benefit_id,
        benefit_type=benefit_type.value,
        growth_code_id=record.growth_code_id,
        idempotency_key=record.idempotency_key,
        status=record.status,
        duplicate=duplicate,
        result_payload=_json_dict(record.result_payload),
    )


def _ensure_no_raw_code_material(value: object) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) in _SENSITIVE_RAW_CODE_KEYS:
                raise GrowthBenefitConfigurationError("benefit snapshot contains raw code material")
            _ensure_no_raw_code_material(item)
        return
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for item in value:
            _ensure_no_raw_code_material(item)


def _json_dict(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(dict(value), default=str))


def _decimal_or_zero(value: object) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise GrowthBenefitSettlementNotEligibleError("settlement amount is invalid") from exc


def copy_fulfillment_with_result(
    record: BenefitFulfillmentRecord,
    *,
    status: str,
    result_payload: dict[str, Any],
    completed_at: datetime | None,
) -> BenefitFulfillmentRecord:
    """Return an updated fulfillment record for fake repositories in tests."""

    return replace(
        record,
        status=status,
        result_payload=_json_dict(result_payload),
        completed_at=completed_at,
    )
