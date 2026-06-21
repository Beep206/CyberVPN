"""Partner-code eligibility policy for attribution entry points."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.domain.enums import CommercialOwnerType
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeLinkModel, PartnerCodeModel

_ALLOWED_OWNER_TYPES = frozenset(
    {
        CommercialOwnerType.AFFILIATE.value,
        CommercialOwnerType.PERFORMANCE.value,
        CommercialOwnerType.RESELLER.value,
    }
)


@dataclass(frozen=True)
class PartnerCodeEligibilityResult:
    allowed: bool
    reason_codes: list[str]
    policy_snapshot: dict[str, Any]
    error_code: str | None = None
    message: str | None = None
    status_code: int = 409
    clear_cookie: bool = True
    owner_type: str | None = None


@dataclass(frozen=True)
class EvaluatePartnerCodeEligibilityCommand:
    code_model: PartnerCodeModel
    account: PartnerAccountModel | None
    link_model: PartnerCodeLinkModel | None = None
    sale_channel: str | None = None
    storefront_id: UUID | None = None
    geography: str | None = None
    now: datetime | None = None


class EvaluatePartnerCodeEligibilityUseCase:
    def execute(self, command: EvaluatePartnerCodeEligibilityCommand) -> PartnerCodeEligibilityResult:
        code_model = command.code_model
        account = command.account
        link_model = command.link_model
        now = _coerce_utc(command.now or datetime.now(UTC))
        owner_type = (code_model.owner_type or "").strip()
        reason_codes: list[str] = []
        failure = _Failure()

        if not code_model.is_active:
            failure.set("PARTNER_CODE_NOT_ACTIVE", "Partner code is not active.", 409)
            reason_codes.append("code_inactive")
        if code_model.lifecycle_status != "active":
            failure.set("PARTNER_CODE_NOT_ACTIVE", "Partner code is not active.", 409)
            reason_codes.append("code_lifecycle_not_active")
        if code_model.approval_status != "approved":
            failure.set("PARTNER_CODE_NOT_ACTIVE", "Partner code is not active.", 409)
            reason_codes.append("code_not_approved")
        if code_model.active_from is not None and _coerce_utc(code_model.active_from) > now:
            failure.set("PARTNER_CODE_NOT_ACTIVE", "Partner code is not active yet.", 409)
            reason_codes.append("code_not_yet_active")
        if code_model.expires_at is not None and _coerce_utc(code_model.expires_at) <= now:
            failure.set("PARTNER_CODE_EXPIRED", "Partner code expired.", 410)
            reason_codes.append("code_expired")

        if code_model.partner_account_id is not None and account is None:
            failure.set("PARTNER_ACCOUNT_NOT_FOUND", "Partner account was not found.", 409)
            reason_codes.append("partner_account_not_found")
        if account is not None and account.status != "active":
            failure.set("PARTNER_ACCOUNT_NOT_ACTIVE", "Partner account is not active.", 409)
            reason_codes.append("partner_account_not_active")
        if code_model.partner_account_id is None and code_model.partner_user_id is None:
            failure.set("PARTNER_OWNER_NOT_CONFIGURED", "Partner code owner is not configured.", 409)
            reason_codes.append("partner_owner_not_configured")
        if owner_type not in _ALLOWED_OWNER_TYPES:
            failure.set(
                "PARTNER_OWNER_TYPE_NOT_ELIGIBLE",
                "Partner owner type is not eligible for attribution.",
                409,
            )
            reason_codes.append("owner_type_not_eligible")

        if link_model is not None:
            _evaluate_link(link_model=link_model, now=now, reason_codes=reason_codes, failure=failure)

        normalized_sale_channel = _normalize_optional(command.sale_channel)
        if not _is_allowed_value(normalized_sale_channel, code_model.allowed_channels):
            failure.set("PARTNER_CODE_CHANNEL_NOT_ALLOWED", "Partner code is not eligible for this channel.", 409)
            reason_codes.append("sale_channel_not_allowed")

        normalized_storefront_id = str(command.storefront_id) if command.storefront_id is not None else None
        if not _is_allowed_value(normalized_storefront_id, code_model.allowed_storefront_ids):
            failure.set("PARTNER_CODE_STOREFRONT_NOT_ALLOWED", "Partner code is not eligible for this storefront.", 409)
            reason_codes.append("storefront_not_allowed")

        normalized_geography = _normalize_optional(command.geography)
        if not _is_allowed_value(normalized_geography, code_model.allowed_geographies):
            failure.set("PARTNER_CODE_GEOGRAPHY_NOT_ALLOWED", "Partner code is not eligible for this geography.", 409)
            reason_codes.append("geography_not_allowed")

        reason_codes = sorted(set(reason_codes))
        snapshot = _build_policy_snapshot(
            code_model=code_model,
            account=account,
            link_model=link_model,
            owner_type=owner_type,
            sale_channel=normalized_sale_channel,
            storefront_id=normalized_storefront_id,
            geography=normalized_geography,
            reason_codes=reason_codes,
            now=now,
        )
        return PartnerCodeEligibilityResult(
            allowed=not reason_codes,
            reason_codes=reason_codes,
            policy_snapshot=snapshot,
            error_code=failure.error_code,
            message=failure.message,
            status_code=failure.status_code,
            owner_type=owner_type if owner_type in _ALLOWED_OWNER_TYPES else None,
        )


@dataclass
class _Failure:
    error_code: str | None = None
    message: str | None = None
    status_code: int = 409

    def set(self, error_code: str, message: str, status_code: int) -> None:
        if self.error_code is None:
            self.error_code = error_code
            self.message = message
            self.status_code = status_code


def _evaluate_link(
    *,
    link_model: PartnerCodeLinkModel,
    now: datetime,
    reason_codes: list[str],
    failure: _Failure,
) -> None:
    if link_model.status != "active":
        failure.set("PARTNER_CODE_LINK_NOT_ACTIVE", "Partner link is not active.", 409)
        reason_codes.append("link_not_active")
    if link_model.active_from is not None and _coerce_utc(link_model.active_from) > now:
        failure.set("PARTNER_CODE_LINK_NOT_ACTIVE", "Partner link is not active yet.", 409)
        reason_codes.append("link_not_yet_active")
    if link_model.expires_at is not None and _coerce_utc(link_model.expires_at) <= now:
        failure.set("PARTNER_CODE_LINK_EXPIRED", "Partner link expired.", 410)
        reason_codes.append("link_expired")


def _build_policy_snapshot(
    *,
    code_model: PartnerCodeModel,
    account: PartnerAccountModel | None,
    link_model: PartnerCodeLinkModel | None,
    owner_type: str,
    sale_channel: str | None,
    storefront_id: str | None,
    geography: str | None,
    reason_codes: list[str],
    now: datetime,
) -> dict[str, Any]:
    return {
        "partner_account_id": str(code_model.partner_account_id) if code_model.partner_account_id else None,
        "partner_account_status": account.status if account else None,
        "partner_code_id": str(code_model.id),
        "partner_code_link_id": str(link_model.id) if link_model is not None else None,
        "partner_code_link_status": link_model.status if link_model is not None else None,
        "code_kind": code_model.code_kind,
        "owner_type": owner_type,
        "lane_key": code_model.lane_key,
        "attribution_model": code_model.attribution_model,
        "attribution_window_seconds": int(code_model.attribution_window_seconds or 0),
        "policy_version_id": str(code_model.policy_version_id) if code_model.policy_version_id else None,
        "commission_contract_id": str(code_model.commission_contract_id) if code_model.commission_contract_id else None,
        "markup_pct": str(code_model.markup_pct or 0),
        "allowed_channels": list(code_model.allowed_channels or []),
        "allowed_storefront_ids": list(code_model.allowed_storefront_ids or []),
        "allowed_geographies": list(code_model.allowed_geographies or []),
        "evaluated_sale_channel": sale_channel,
        "evaluated_storefront_id": storefront_id,
        "evaluated_geography": geography,
        "reason_codes": reason_codes,
        "allowed": not reason_codes,
        "active_from": code_model.active_from.isoformat() if code_model.active_from else None,
        "expires_at": code_model.expires_at.isoformat() if code_model.expires_at else None,
        "snapshot_at": now.isoformat(),
        "snapshot_version": "partner_attribution_v2",
    }


def _is_allowed_value(value: str | None, allowed_values: list[str] | None) -> bool:
    normalized_allowed = {_normalize_required(item) for item in allowed_values or []}
    normalized_allowed.discard("")
    if not normalized_allowed or "*" in normalized_allowed:
        return True
    return value is not None and value in normalized_allowed


def _normalize_optional(value: str | None) -> str | None:
    normalized = _normalize_required(value)
    return normalized or None


def _normalize_required(value: object | None) -> str:
    return str(value or "").strip()


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
