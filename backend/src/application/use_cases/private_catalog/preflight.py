from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.application.use_cases.growth_codes.namespace import (
    NormalizedCustomerCode,
    normalize_customer_input_code,
)

PRIVATE_CODE_SET_UUID_NAMESPACE = UUID("923ae21e-0811-44f0-a927-460533ae68df")


@dataclass(frozen=True, slots=True)
class PrivateCatalogCodeInput:
    code: str
    client_slot_id: str


class PrivateCatalogPreflightCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    codes: tuple[PrivateCatalogCodeInput, ...]
    storefront_key: str = Field(min_length=1, max_length=80)
    channel: str = Field(min_length=1, max_length=30)
    currency: str = Field(min_length=3, max_length=3)
    anonymous_session_id: str | None = Field(default=None, max_length=120)
    user_id: UUID | None = None

    @field_validator("codes")
    @classmethod
    def _validate_codes(cls, value: tuple[PrivateCatalogCodeInput, ...]) -> tuple[PrivateCatalogCodeInput, ...]:
        if not value:
            raise ValueError("at least one code is required")
        if len(value) > 5:
            raise ValueError("at most five codes are supported")
        return value

    @field_validator("currency")
    @classmethod
    def _normalize_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("channel")
    @classmethod
    def _normalize_channel(cls, value: str) -> str:
        return value.strip().lower()


@dataclass(frozen=True, slots=True)
class PrivatePolicyRecord:
    id: UUID
    policy_version_id: UUID
    growth_code_id: UUID
    target_plan_ids: tuple[UUID, ...]
    allowed_storefront_ids: tuple[UUID, ...]
    allowed_channels: tuple[str, ...]
    grant_ttl_seconds: int
    max_quote_conversions: int | None
    requires_auth: bool


@dataclass(frozen=True, slots=True)
class PrivateStorefrontRecord:
    id: UUID
    auth_realm_id: UUID
    storefront_key: str


@dataclass(frozen=True, slots=True)
class PrivatePlanPreview:
    plan_id: UUID
    display_name: str
    plan_code: str
    duration_days: int
    amount: Decimal
    currency: str
    entitlement_summary: dict[str, object]


@dataclass(frozen=True, slots=True)
class PrivateCatalogGrantRecord:
    id: UUID
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class PrivateCatalogApplicationResult:
    client_slot_id: str
    masked_code: str
    status: str
    roles: tuple[str, ...]
    message_key: str


@dataclass(frozen=True, slots=True)
class PrivateCatalogGrantResult:
    id: UUID
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class PrivateCatalogOfferResult:
    plan_id: UUID
    display_name: str
    duration_days: int
    price_amount: str
    price_currency: str
    entitlement_summary: dict[str, object]
    private_catalog_grant_id: UUID


@dataclass(frozen=True, slots=True)
class PrivateCatalogRiskResult:
    action: str


class PrivateCatalogRiskBlockedError(ValueError):
    def __init__(self, action: str) -> None:
        super().__init__("PRIVATE_CATALOG_RISK_REVIEW_REQUIRED")
        self.action = action


class PrivateCatalogRiskGuard(Protocol):
    async def evaluate_private_preflight(
        self,
        *,
        user_id: UUID | None,
        anonymous_session_id: str | None,
        storefront: PrivateStorefrontRecord,
        policy: PrivatePolicyRecord,
        code_set_id: UUID,
        code_set_hash: str,
        channel: str,
        currency: str,
        code_count: int,
    ) -> str:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class PrivateCatalogPreflightResult:
    code_set_id: UUID | None
    code_set_hash: str
    status: str
    applications: tuple[PrivateCatalogApplicationResult, ...]
    private_catalog_grant: PrivateCatalogGrantResult | None
    private_offers: tuple[PrivateCatalogOfferResult, ...]
    risk: PrivateCatalogRiskResult


class PrivateCatalogRepository(Protocol):
    async def get_storefront(self, storefront_key: str) -> PrivateStorefrontRecord | None:
        raise NotImplementedError

    async def find_active_private_policy(self, code_hash: str) -> PrivatePolicyRecord | None:
        raise NotImplementedError

    async def list_private_plan_previews(
        self,
        *,
        plan_ids: tuple[UUID, ...],
        channel: str,
        currency: str,
    ) -> tuple[PrivatePlanPreview, ...]:
        raise NotImplementedError

    async def create_private_catalog_grant(
        self,
        *,
        policy: PrivatePolicyRecord,
        storefront: PrivateStorefrontRecord,
        normalized_codes: tuple[NormalizedCustomerCode, ...],
        code_set_hash: str,
        channel: str,
        user_id: UUID | None,
        anonymous_session_id: str | None,
        issued_at: datetime,
        expires_at: datetime,
    ) -> PrivateCatalogGrantRecord:
        raise NotImplementedError


class PrivateCatalogPreflightUseCase:
    def __init__(
        self,
        repository: PrivateCatalogRepository,
        risk_guard: PrivateCatalogRiskGuard | None = None,
    ) -> None:
        self._repository = repository
        self._risk_guard = risk_guard

    async def execute(self, command: PrivateCatalogPreflightCommand) -> PrivateCatalogPreflightResult:
        normalized_codes = tuple(normalize_customer_input_code(item.code) for item in command.codes)
        applications = tuple(
            PrivateCatalogApplicationResult(
                client_slot_id=input_item.client_slot_id,
                masked_code=normalized.masked_code,
                status="rejected",
                roles=(),
                message_key="growth.code.notEligible",
            )
            for input_item, normalized in zip(command.codes, normalized_codes, strict=True)
        )
        code_set_hash = build_private_code_set_hash(
            normalized_codes=normalized_codes,
            storefront_key=command.storefront_key,
            channel=command.channel,
        )
        code_set_id = build_private_code_set_id(code_set_hash)
        duplicate_hashes = _duplicate_code_hashes(normalized_codes)
        if duplicate_hashes:
            duplicate_applications = tuple(
                PrivateCatalogApplicationResult(
                    client_slot_id=input_item.client_slot_id,
                    masked_code=normalized.masked_code,
                    status="rejected",
                    roles=(),
                    message_key=(
                        "growth.errors.duplicateCode"
                        if normalized.code_hash in duplicate_hashes
                        else "growth.code.notEligible"
                    ),
                )
                for input_item, normalized in zip(command.codes, normalized_codes, strict=True)
            )
            return PrivateCatalogPreflightResult(
                code_set_id=code_set_id,
                code_set_hash=code_set_hash,
                status="rejected",
                applications=duplicate_applications,
                private_catalog_grant=None,
                private_offers=(),
                risk=PrivateCatalogRiskResult(action="allow"),
            )
        rejected = PrivateCatalogPreflightResult(
            code_set_id=code_set_id,
            code_set_hash=code_set_hash,
            status="rejected",
            applications=applications,
            private_catalog_grant=None,
            private_offers=(),
            risk=PrivateCatalogRiskResult(action="allow"),
        )
        if command.user_id is None and not command.anonymous_session_id:
            return rejected

        storefront = await self._repository.get_storefront(command.storefront_key)
        if storefront is None:
            return rejected

        matched_policy: PrivatePolicyRecord | None = None
        matched_index: int | None = None
        for index, normalized in enumerate(normalized_codes):
            policy = await self._repository.find_active_private_policy(normalized.code_hash)
            if policy is not None:
                matched_policy = policy
                matched_index = index
                break
        if matched_policy is None or matched_index is None:
            return rejected
        if matched_policy.requires_auth and command.user_id is None:
            return rejected
        if matched_policy.allowed_storefront_ids and storefront.id not in matched_policy.allowed_storefront_ids:
            return rejected
        if matched_policy.allowed_channels and command.channel not in matched_policy.allowed_channels:
            return rejected

        plan_previews = await self._repository.list_private_plan_previews(
            plan_ids=matched_policy.target_plan_ids,
            channel=command.channel,
            currency=command.currency,
        )
        if not plan_previews:
            return rejected

        risk_action = "allow"
        if self._risk_guard is not None:
            try:
                risk_action = await self._risk_guard.evaluate_private_preflight(
                    user_id=command.user_id,
                    anonymous_session_id=command.anonymous_session_id,
                    storefront=storefront,
                    policy=matched_policy,
                    code_set_id=code_set_id,
                    code_set_hash=code_set_hash,
                    channel=command.channel,
                    currency=command.currency,
                    code_count=len(command.codes),
                )
            except PrivateCatalogRiskBlockedError as exc:
                risk_applications = list(applications)
                matched_application = risk_applications[matched_index]
                risk_applications[matched_index] = PrivateCatalogApplicationResult(
                    client_slot_id=matched_application.client_slot_id,
                    masked_code=matched_application.masked_code,
                    status="rejected",
                    roles=(),
                    message_key="growth.risk.verificationRequired",
                )
                return PrivateCatalogPreflightResult(
                    code_set_id=code_set_id,
                    code_set_hash=code_set_hash,
                    status="denied_by_risk",
                    applications=tuple(risk_applications),
                    private_catalog_grant=None,
                    private_offers=(),
                    risk=PrivateCatalogRiskResult(action=exc.action),
                )

        issued_at = datetime.now(UTC)
        expires_at = issued_at + timedelta(seconds=matched_policy.grant_ttl_seconds)
        grant = await self._repository.create_private_catalog_grant(
            policy=matched_policy,
            storefront=storefront,
            normalized_codes=normalized_codes,
            code_set_hash=code_set_hash,
            channel=command.channel,
            user_id=command.user_id,
            anonymous_session_id=command.anonymous_session_id,
            issued_at=issued_at,
            expires_at=expires_at,
        )
        accepted_applications = list(applications)
        matched_application = accepted_applications[matched_index]
        accepted_applications[matched_index] = PrivateCatalogApplicationResult(
            client_slot_id=matched_application.client_slot_id,
            masked_code=matched_application.masked_code,
            status="accepted",
            roles=("catalog_access",),
            message_key="growth.code.privateOfferUnlocked",
        )
        return PrivateCatalogPreflightResult(
            code_set_id=code_set_id,
            code_set_hash=code_set_hash,
            status="accepted",
            applications=tuple(accepted_applications),
            private_catalog_grant=PrivateCatalogGrantResult(id=grant.id, expires_at=grant.expires_at),
            private_offers=tuple(
                PrivateCatalogOfferResult(
                    plan_id=plan.plan_id,
                    display_name=plan.display_name,
                    duration_days=plan.duration_days,
                    price_amount=format(plan.amount, "f"),
                    price_currency=plan.currency,
                    entitlement_summary=plan.entitlement_summary,
                    private_catalog_grant_id=grant.id,
                )
                for plan in plan_previews
            ),
            risk=PrivateCatalogRiskResult(action=risk_action),
        )


def build_private_code_set_hash(
    *,
    normalized_codes: tuple[NormalizedCustomerCode, ...],
    storefront_key: str,
    channel: str,
) -> str:
    payload = {
        "codes": sorted(
            (
                {"namespace": code.namespace, "hash": code.code_hash, "prefix": code.code_prefix}
                for code in normalized_codes
            ),
            key=lambda item: (str(item["namespace"]), str(item["hash"]), str(item["prefix"])),
        ),
        "storefront_key": storefront_key,
        "channel": channel,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_private_code_set_id(code_set_hash: str) -> UUID:
    return uuid5(PRIVATE_CODE_SET_UUID_NAMESPACE, code_set_hash)


def _duplicate_code_hashes(normalized_codes: tuple[NormalizedCustomerCode, ...]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for code in normalized_codes:
        if code.code_hash in seen:
            duplicates.add(code.code_hash)
        seen.add(code.code_hash)
    return duplicates
