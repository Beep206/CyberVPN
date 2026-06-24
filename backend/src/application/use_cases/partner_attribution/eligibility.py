"""Partner-code eligibility policy for attribution entry points."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import CommercialOwnerType, PrincipalClass
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeLinkModel, PartnerCodeModel
from src.infrastructure.database.repositories.partner_application_repository import PartnerApplicationRepository
from src.infrastructure.database.repositories.risk_subject_repo import RiskSubjectGraphRepository

_ALLOWED_OWNER_TYPES = frozenset(
    {
        CommercialOwnerType.AFFILIATE.value,
        CommercialOwnerType.PERFORMANCE.value,
        CommercialOwnerType.RESELLER.value,
    }
)
_ALLOWED_WORKSPACE_STATUSES = frozenset({"active", "approved_probation"})
_ALLOWED_LANE_STATUSES = frozenset({"active", "approved_active", "approved_probation"})
_BLOCKING_RISK_DECISIONS = frozenset({"hold", "block"})
_COMMISSION_CONTRACT_EFFECTIVE_FROM_LEEWAY = timedelta(seconds=5)


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
    commission_contract_snapshot: dict[str, Any] | None = None
    lane_application_id: UUID | None = None
    lane_application_status: str | None = None
    risk_subject_id: UUID | None = None
    risk_subject_status: str | None = None
    risk_review_ids: tuple[UUID, ...] = ()
    risk_review_decisions: tuple[str, ...] = ()
    require_lane_membership: bool = False
    now: datetime | None = None


class EvaluatePartnerCodeEligibilityWithContextUseCase:
    """Load DB-backed lane/risk context, then evaluate the pure policy."""

    def __init__(self, session: AsyncSession) -> None:
        self._applications = PartnerApplicationRepository(session)
        self._risk = RiskSubjectGraphRepository(session)
        self._pure = EvaluatePartnerCodeEligibilityUseCase()
        self._load_context = callable(getattr(session, "execute", None))

    async def execute(self, command: EvaluatePartnerCodeEligibilityCommand) -> PartnerCodeEligibilityResult:
        code_model = command.code_model
        account = command.account
        lane_application_id = command.lane_application_id
        lane_application_status = command.lane_application_status
        risk_subject_id = command.risk_subject_id
        risk_subject_status = command.risk_subject_status
        risk_review_ids = command.risk_review_ids
        risk_review_decisions = command.risk_review_decisions

        if self._load_context and account is not None and code_model.partner_account_id is not None:
            lane_application = await self._applications.get_lane_application_by_lane_key(
                partner_account_id=code_model.partner_account_id,
                lane_key=str(code_model.lane_key or "").strip(),
            )
            if lane_application is not None:
                lane_application_id = lane_application.id
                lane_application_status = lane_application.status

            risk_subject = await self._risk.get_subject_by_principal(
                principal_class=PrincipalClass.PARTNER_OPERATOR.value,
                principal_subject=_partner_account_risk_subject_key(code_model.partner_account_id),
                auth_realm_id=None,
            )
            if risk_subject is not None:
                risk_subject_id = risk_subject.id
                risk_subject_status = risk_subject.status
                open_reviews = await self._risk.list_open_reviews_for_subject(risk_subject.id)
                risk_review_ids = tuple(review.id for review in open_reviews)
                risk_review_decisions = tuple(str(review.decision or "").strip().lower() for review in open_reviews)

        return self._pure.execute(
            replace(
                command,
                lane_application_id=lane_application_id,
                lane_application_status=lane_application_status,
                risk_subject_id=risk_subject_id,
                risk_subject_status=risk_subject_status,
                risk_review_ids=risk_review_ids,
                risk_review_decisions=risk_review_decisions,
                require_lane_membership=command.require_lane_membership
                or _requires_lane_membership(account=account, code_model=code_model),
            )
        )


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
        if account is not None and account.status not in _ALLOWED_WORKSPACE_STATUSES:
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

        _evaluate_lane_context(command=command, reason_codes=reason_codes, failure=failure)
        _evaluate_commission_contract_context(
            code_model=code_model,
            commission_contract_snapshot=command.commission_contract_snapshot,
            now=now,
            reason_codes=reason_codes,
            failure=failure,
        )
        _evaluate_risk_context(command=command, reason_codes=reason_codes, failure=failure)

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
            commission_contract_snapshot=command.commission_contract_snapshot,
            lane_application_id=command.lane_application_id,
            lane_application_status=command.lane_application_status,
            risk_subject_id=command.risk_subject_id,
            risk_subject_status=command.risk_subject_status,
            risk_review_ids=command.risk_review_ids,
            risk_review_decisions=command.risk_review_decisions,
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


def _evaluate_lane_context(
    *,
    command: EvaluatePartnerCodeEligibilityCommand,
    reason_codes: list[str],
    failure: _Failure,
) -> None:
    lane_status = _normalize_optional(command.lane_application_status)
    if lane_status is None:
        if command.require_lane_membership:
            failure.set("PARTNER_LANE_NOT_APPROVED", "Partner lane is not approved for attribution.", 409)
            reason_codes.append("lane_membership_missing")
        return
    if lane_status not in _ALLOWED_LANE_STATUSES:
        failure.set("PARTNER_LANE_NOT_APPROVED", "Partner lane is not approved for attribution.", 409)
        reason_codes.append("lane_not_approved")


def _evaluate_commission_contract_context(
    *,
    code_model: PartnerCodeModel,
    commission_contract_snapshot: dict[str, Any] | None,
    now: datetime,
    reason_codes: list[str],
    failure: _Failure,
) -> None:
    if not commission_contract_snapshot:
        if code_model.commission_contract_id is not None:
            failure.set(
                "PARTNER_COMMISSION_CONTRACT_MISSING",
                "Partner commission contract snapshot is missing.",
                409,
            )
            reason_codes.append("commission_contract_snapshot_missing")
        return

    if commission_contract_snapshot.get("snapshot_complete") is False:
        failure.set(
            "PARTNER_COMMISSION_CONTRACT_INCOMPLETE",
            "Partner commission contract snapshot is incomplete.",
            409,
        )
        reason_codes.append("commission_contract_snapshot_incomplete")

    contract_status = _normalize_optional(str(commission_contract_snapshot.get("contract_status") or "active"))
    if contract_status != "active":
        failure.set("PARTNER_COMMISSION_CONTRACT_NOT_ACTIVE", "Partner commission contract is not active.", 409)
        reason_codes.append("commission_contract_not_active")

    snapshot_contract_id = _normalize_optional(commission_contract_snapshot.get("commission_contract_id"))
    if code_model.commission_contract_id is not None and snapshot_contract_id != str(code_model.commission_contract_id):
        failure.set(
            "PARTNER_COMMISSION_CONTRACT_MISMATCH",
            "Partner commission contract does not match the code.",
            409,
        )
        reason_codes.append("commission_contract_mismatch")

    snapshot_code_id = _normalize_optional(commission_contract_snapshot.get("partner_code_id"))
    if snapshot_code_id is not None and snapshot_code_id != str(code_model.id):
        failure.set(
            "PARTNER_COMMISSION_CONTRACT_MISMATCH",
            "Partner commission contract does not match the code.",
            409,
        )
        reason_codes.append("commission_contract_code_mismatch")

    effective_from = _parse_snapshot_datetime(commission_contract_snapshot.get("effective_from"))
    if effective_from is not None and effective_from - now > _COMMISSION_CONTRACT_EFFECTIVE_FROM_LEEWAY:
        failure.set(
            "PARTNER_COMMISSION_CONTRACT_NOT_ACTIVE",
            "Partner commission contract is not active yet.",
            409,
        )
        reason_codes.append("commission_contract_not_yet_active")

    effective_to = _parse_snapshot_datetime(commission_contract_snapshot.get("effective_to"))
    if effective_to is not None and effective_to <= now:
        failure.set(
            "PARTNER_COMMISSION_CONTRACT_EXPIRED",
            "Partner commission contract expired.",
            410,
        )
        reason_codes.append("commission_contract_expired")


def _evaluate_risk_context(
    *,
    command: EvaluatePartnerCodeEligibilityCommand,
    reason_codes: list[str],
    failure: _Failure,
) -> None:
    risk_subject_status = _normalize_optional(command.risk_subject_status)
    if risk_subject_status is not None and risk_subject_status != "active":
        failure.set("PARTNER_CODE_BLOCKED_BY_RISK", "Partner code is blocked by risk policy.", 409)
        reason_codes.append("risk_subject_not_active")

    blocking_decisions = {
        _normalize_required(decision).lower()
        for decision in command.risk_review_decisions
        if _normalize_required(decision).lower() in _BLOCKING_RISK_DECISIONS
    }
    if not blocking_decisions:
        return
    failure.set("PARTNER_CODE_BLOCKED_BY_RISK", "Partner code is blocked by risk policy.", 409)
    if "block" in blocking_decisions:
        reason_codes.append("risk_review_block")
    if "hold" in blocking_decisions:
        reason_codes.append("risk_review_hold")


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
    commission_contract_snapshot: dict[str, Any] | None,
    lane_application_id: UUID | None,
    lane_application_status: str | None,
    risk_subject_id: UUID | None,
    risk_subject_status: str | None,
    risk_review_ids: tuple[UUID, ...],
    risk_review_decisions: tuple[str, ...],
    now: datetime,
) -> dict[str, Any]:
    snapshot = {
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
        "lane_application_id": str(lane_application_id) if lane_application_id else None,
        "lane_application_status": lane_application_status,
        "risk_subject_id": str(risk_subject_id) if risk_subject_id else None,
        "risk_subject_status": risk_subject_status,
        "risk_review_ids": [str(review_id) for review_id in risk_review_ids],
        "risk_review_decisions": list(risk_review_decisions),
        "active_from": code_model.active_from.isoformat() if code_model.active_from else None,
        "expires_at": code_model.expires_at.isoformat() if code_model.expires_at else None,
        "snapshot_at": now.isoformat(),
        "snapshot_version": "partner_attribution_v2",
    }
    if commission_contract_snapshot:
        snapshot["commission_contract_snapshot"] = dict(commission_contract_snapshot)
    return snapshot


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


def _parse_snapshot_datetime(value: object | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _coerce_utc(value)
    normalized = _normalize_required(value)
    if not normalized:
        return None
    try:
        return _coerce_utc(datetime.fromisoformat(normalized.replace("Z", "+00:00")))
    except ValueError:
        return None


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _partner_account_risk_subject_key(partner_account_id: UUID) -> str:
    return f"partner_account:{partner_account_id}"


def _requires_lane_membership(*, account: PartnerAccountModel | None, code_model: PartnerCodeModel) -> bool:
    if account is None or code_model.partner_account_id is None:
        return False
    if not _normalize_optional(code_model.lane_key):
        return False
    created_by_admin_user_id = getattr(account, "created_by_admin_user_id", None)
    legacy_owner_user_id = getattr(account, "legacy_owner_user_id", None)
    return created_by_admin_user_id is not None and legacy_owner_user_id is None
