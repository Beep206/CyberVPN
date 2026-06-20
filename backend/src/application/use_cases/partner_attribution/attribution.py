"""Partner attribution capture, transfer, and claim use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService
from src.application.use_cases.attribution.record_touchpoint import RecordAttributionTouchpointUseCase
from src.application.use_cases.commercial_bindings.create_binding import (
    CreateCustomerCommercialBindingUseCase,
)
from src.application.use_cases.partner_attribution.utils import (
    PARTNER_ATTRIBUTION_STORAGE_VERSION,
    build_customer_register_url,
    build_public_token_for_code_id,
    clamp_optional,
    generate_transfer_token,
    hash_partner_attribution_token,
    mask_partner_code,
)
from src.config.settings import settings
from src.domain.enums import (
    AttributionTouchpointType,
    CommercialOwnerType,
    CustomerCommercialBindingStatus,
    CustomerCommercialBindingType,
)
from src.infrastructure.database.models.customer_commercial_binding_model import (
    CustomerCommercialBindingModel,
)
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_attribution_session_model import (
    PartnerAttributionSessionModel,
)
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeModel
from src.infrastructure.database.repositories.customer_commercial_binding_repo import (
    CustomerCommercialBindingRepository,
)
from src.infrastructure.database.repositories.partner_attribution_session_repo import (
    PartnerAttributionSessionRepository,
)
from src.infrastructure.database.repositories.partner_repo import PartnerRepository
from src.presentation.dependencies.auth_realms import RealmResolution

_TERMINAL_STATUSES = frozenset({"claimed", "expired", "invalidated", "rejected"})
_ALLOWED_OWNER_TYPES = {
    CommercialOwnerType.AFFILIATE.value,
    CommercialOwnerType.PERFORMANCE.value,
    CommercialOwnerType.RESELLER.value,
}


class PartnerAttributionError(Exception):
    def __init__(self, *, code: str, message: str, status_code: int = 400, clear_cookie: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.clear_cookie = clear_cookie


@dataclass(frozen=True)
class CapturePartnerAttributionCommand:
    public_token: str
    source_host: str | None
    source_path: str | None
    campaign_params: dict[str, Any] | None
    current_realm: RealmResolution


@dataclass(frozen=True)
class CapturePartnerAttributionResult:
    attribution_id: UUID
    captured_at: datetime
    expires_at: datetime
    masked_code: str
    transfer_token: str
    redirect_url: str


@dataclass(frozen=True)
class ConsumePartnerAttributionTransferCommand:
    transfer_token: str


@dataclass(frozen=True)
class ConsumePartnerAttributionTransferResult:
    attribution_id: UUID
    expires_at: datetime
    cookie_token: str
    masked_code: str


@dataclass(frozen=True)
class ClaimPartnerAttributionCommand:
    user_id: UUID
    cookie_token: str | None
    current_realm: RealmResolution


@dataclass(frozen=True)
class ClaimPartnerAttributionResult:
    status: str
    partner_account_id: UUID | None = None
    partner_code_id: UUID | None = None
    binding_id: UUID | None = None
    claimed_at: datetime | None = None
    clear_cookie: bool = False


class CapturePartnerAttributionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._partners = PartnerRepository(session)
        self._sessions = PartnerAttributionSessionRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(self, command: CapturePartnerAttributionCommand) -> CapturePartnerAttributionResult:
        if not settings.partner_attribution_enabled:
            raise PartnerAttributionError(
                code="PARTNER_ATTRIBUTION_DISABLED",
                message="Partner attribution is disabled.",
                status_code=403,
            )

        code_model = await self._find_code_by_public_token(command.public_token)
        partner_account = await self._load_partner_account(code_model)
        _assert_code_eligible(code_model, partner_account)

        now = datetime.now(UTC)
        transfer_token = generate_transfer_token()
        transfer_hash = hash_partner_attribution_token(transfer_token)
        expires_at = now + timedelta(seconds=int(code_model.attribution_window_seconds or 0))
        destination_url = build_customer_register_url(transfer_token)
        policy_snapshot = _build_policy_snapshot(code_model, partner_account)
        session_model = PartnerAttributionSessionModel(
            token_hash=transfer_hash,
            transfer_token_hash=transfer_hash,
            partner_code_id=code_model.id,
            partner_account_id=code_model.partner_account_id,
            auth_realm_id=UUID(command.current_realm.realm_id),
            storefront_id=code_model.default_storefront_id,
            status="pending",
            owner_type=_code_owner_type(code_model),
            attribution_model=code_model.attribution_model,
            policy_version_id=code_model.policy_version_id,
            commission_contract_id=code_model.commission_contract_id,
            source_host=clamp_optional(command.source_host, 255),
            source_path=clamp_optional(command.source_path, 500),
            destination_url=destination_url,
            campaign_params=_sanitize_campaign_params(command.campaign_params),
            evidence_payload={
                "public_token_hash": hash_partner_attribution_token(command.public_token),
                "masked_code": mask_partner_code(code_model.code),
                "storage_version": PARTNER_ATTRIBUTION_STORAGE_VERSION,
            },
            policy_snapshot=policy_snapshot,
            expires_at=expires_at,
        )
        created = await self._sessions.create(session_model)
        touchpoint = await RecordAttributionTouchpointUseCase(self._session).execute(
            current_realm=command.current_realm,
            touchpoint_type=AttributionTouchpointType.PASSIVE_CLICK.value,
            partner_code_id=code_model.id,
            partner_attribution_session_id=created.id,
            policy_version_id=code_model.policy_version_id,
            source_event_id=f"partner_public_click:{created.id}",
            idempotency_key=f"partner-public-click:{created.id}",
            source_host=created.source_host,
            source_path=created.source_path,
            campaign_params=created.campaign_params,
            evidence_payload={
                "partner_attribution_session_id": str(created.id),
                "partner_account_id": str(created.partner_account_id) if created.partner_account_id else None,
                "owner_type": created.owner_type,
                "policy_snapshot": policy_snapshot,
            },
            commit=False,
        )
        created.touchpoint_id = touchpoint.id
        await self._outbox.append_event(
            event_name="partner.attribution.captured",
            aggregate_type="partner_attribution_session",
            aggregate_id=str(created.id),
            partition_key=str(code_model.partner_account_id or code_model.partner_user_id or code_model.id),
            event_payload={
                "partner_code_id": str(code_model.id),
                "partner_account_id": str(code_model.partner_account_id) if code_model.partner_account_id else None,
                "masked_code": mask_partner_code(code_model.code),
                "expires_at": expires_at.isoformat(),
            },
            source_context={"source_use_case": "CapturePartnerAttributionUseCase"},
        )
        await self._session.flush()
        return CapturePartnerAttributionResult(
            attribution_id=created.id,
            captured_at=created.created_at,
            expires_at=created.expires_at,
            masked_code=mask_partner_code(code_model.code),
            transfer_token=transfer_token,
            redirect_url=destination_url,
        )

    async def _find_code_by_public_token(self, public_token: str) -> PartnerCodeModel:
        token_hash = hash_partner_attribution_token(public_token.strip())
        code_model = await self._partners.get_code_by_public_token_hash(token_hash)
        if code_model is not None:
            return code_model
        fallback_id = _parse_deterministic_public_token(public_token)
        if fallback_id is None:
            raise PartnerAttributionError(
                code="PARTNER_CODE_NOT_FOUND",
                message="Partner public token was not found.",
                status_code=404,
            )
        code_model = await self._partners.get_code_by_id(fallback_id)
        if code_model is None:
            raise PartnerAttributionError(
                code="PARTNER_CODE_NOT_FOUND",
                message="Partner public token was not found.",
                status_code=404,
            )
        if not code_model.public_token_hash:
            code_model.public_token_hash = hash_partner_attribution_token(build_public_token_for_code_id(code_model.id))
            await self._session.flush()
        return code_model

    async def _load_partner_account(self, code_model: PartnerCodeModel) -> PartnerAccountModel | None:
        if code_model.partner_account_id is None:
            return None
        return await self._partners.get_account_by_id(code_model.partner_account_id)


class ConsumePartnerAttributionTransferUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._sessions = PartnerAttributionSessionRepository(session)
        self._session = session

    async def execute(
        self,
        command: ConsumePartnerAttributionTransferCommand,
    ) -> ConsumePartnerAttributionTransferResult:
        token = command.transfer_token.strip()
        attribution = await self._sessions.get_by_transfer_token_hash(
            hash_partner_attribution_token(token),
            for_update=True,
        )
        if attribution is None:
            raise PartnerAttributionError(
                code="PARTNER_TRANSFER_NOT_FOUND",
                message="Partner attribution transfer token was not found.",
                status_code=404,
                clear_cookie=True,
            )

        now = datetime.now(UTC)
        if attribution.status in _TERMINAL_STATUSES or _coerce_utc(attribution.expires_at) <= now:
            attribution.status = "expired" if attribution.status not in _TERMINAL_STATUSES else attribution.status
            attribution.updated_at = now
            await self._session.flush()
            raise PartnerAttributionError(
                code="PARTNER_TRANSFER_EXPIRED",
                message="Partner attribution transfer token expired.",
                status_code=410,
                clear_cookie=True,
            )

        if attribution.status == "pending":
            attribution.status = "transferred"
            attribution.transferred_at = now
            attribution.updated_at = now
            await self._session.flush()

        code_model = await self._session.get(PartnerCodeModel, attribution.partner_code_id)
        return ConsumePartnerAttributionTransferResult(
            attribution_id=attribution.id,
            expires_at=attribution.expires_at,
            cookie_token=token,
            masked_code=mask_partner_code(code_model.code if code_model else None),
        )


class ClaimPartnerAttributionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sessions = PartnerAttributionSessionRepository(session)
        self._bindings = CustomerCommercialBindingRepository(session)
        self._partners = PartnerRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(self, command: ClaimPartnerAttributionCommand) -> ClaimPartnerAttributionResult:
        if not settings.partner_attribution_enabled:
            raise PartnerAttributionError(
                code="PARTNER_ATTRIBUTION_DISABLED",
                message="Partner attribution is disabled.",
                status_code=403,
            )
        if not command.cookie_token:
            return ClaimPartnerAttributionResult(status="no_pending", clear_cookie=False)

        attribution = await self._sessions.get_by_token_hash(
            hash_partner_attribution_token(command.cookie_token.strip()),
            for_update=True,
        )
        if attribution is None:
            return ClaimPartnerAttributionResult(status="no_pending", clear_cookie=True)

        now = datetime.now(UTC)
        if attribution.status == "claimed":
            return ClaimPartnerAttributionResult(
                status="already_claimed",
                partner_account_id=attribution.partner_account_id,
                partner_code_id=attribution.partner_code_id,
                binding_id=attribution.binding_id,
                claimed_at=attribution.claimed_at,
                clear_cookie=True,
            )
        if attribution.status in _TERMINAL_STATUSES or _coerce_utc(attribution.expires_at) <= now:
            attribution.status = "expired"
            attribution.updated_at = now
            await self._session.flush()
            return ClaimPartnerAttributionResult(status="expired", clear_cookie=True)

        user = await self._lock_user(command.user_id)
        if user is None or not user.is_active:
            raise PartnerAttributionError(
                code="PARTNER_ATTRIBUTION_USER_NOT_READY",
                message="User is not ready for partner attribution.",
                status_code=409,
            )
        if str(user.auth_realm_id) != command.current_realm.realm_id:
            raise PartnerAttributionError(
                code="PARTNER_ATTRIBUTION_REALM_MISMATCH",
                message="User realm does not match the attribution realm.",
                status_code=409,
                clear_cookie=False,
            )

        code_model = await self._partners.get_code_by_id(attribution.partner_code_id)
        if code_model is None:
            attribution.status = "invalidated"
            attribution.updated_at = now
            await self._session.flush()
            return ClaimPartnerAttributionResult(status="no_pending", clear_cookie=True)
        partner_account = await self._load_partner_account(code_model)
        _assert_code_eligible(code_model, partner_account)
        _assert_not_self_attribution(user, code_model, partner_account)

        active_bindings = await self._bindings.list_active_for_user(user_id=user.id, storefront_id=None)
        existing_binding = _find_active_owner(active_bindings)
        if existing_binding is not None:
            attribution.status = "claimed"
            attribution.user_id = user.id
            attribution.binding_id = existing_binding.id
            attribution.claimed_at = attribution.claimed_at or now
            attribution.updated_at = now
            await self._session.flush()
            return ClaimPartnerAttributionResult(
                status="already_claimed",
                partner_account_id=existing_binding.partner_account_id,
                partner_code_id=existing_binding.partner_code_id,
                binding_id=existing_binding.id,
                claimed_at=attribution.claimed_at,
                clear_cookie=True,
            )

        binding = await CreateCustomerCommercialBindingUseCase(self._session).execute(
            user_id=user.id,
            binding_type=CustomerCommercialBindingType.PARTNER_ATTRIBUTION.value,
            owner_type=attribution.owner_type,
            partner_code_id=code_model.id,
            partner_account_id=code_model.partner_account_id,
            reason_code="partner_public_attribution_claim",
            evidence_payload={
                "partner_attribution_session_id": str(attribution.id),
                "touchpoint_id": str(attribution.touchpoint_id) if attribution.touchpoint_id else None,
                "policy_snapshot": dict(attribution.policy_snapshot or {}),
                "campaign_params": dict(attribution.campaign_params or {}),
            },
            effective_from=now,
            commit=False,
        )
        binding.policy_version_id = attribution.policy_version_id
        binding.commission_contract_id = attribution.commission_contract_id
        binding.attribution_session_id = attribution.id
        binding.claimed_at = now
        attribution.status = "claimed"
        attribution.user_id = user.id
        attribution.binding_id = binding.id
        attribution.claimed_at = now
        attribution.updated_at = now

        await self._outbox.append_event(
            event_name="partner.attribution.claimed",
            aggregate_type="partner_attribution_session",
            aggregate_id=str(attribution.id),
            partition_key=str(user.id),
            event_payload={
                "user_id": str(user.id),
                "partner_code_id": str(code_model.id),
                "partner_account_id": str(code_model.partner_account_id) if code_model.partner_account_id else None,
                "binding_id": str(binding.id),
                "owner_type": attribution.owner_type,
            },
            source_context={"source_use_case": "ClaimPartnerAttributionUseCase"},
        )
        await self._session.flush()
        return ClaimPartnerAttributionResult(
            status="claimed",
            partner_account_id=code_model.partner_account_id,
            partner_code_id=code_model.id,
            binding_id=binding.id,
            claimed_at=now,
            clear_cookie=True,
        )

    async def _lock_user(self, user_id: UUID) -> MobileUserModel | None:
        result = await self._session.execute(
            select(MobileUserModel).where(MobileUserModel.id == user_id).with_for_update()
        )
        return result.scalars().first()

    async def _load_partner_account(self, code_model: PartnerCodeModel) -> PartnerAccountModel | None:
        if code_model.partner_account_id is None:
            return None
        return await self._partners.get_account_by_id(code_model.partner_account_id)


def _parse_deterministic_public_token(public_token: str) -> UUID | None:
    token = public_token.strip()
    if not token.startswith("px_"):
        return None
    raw = token[3:]
    if len(raw) != 32:
        return None
    try:
        return UUID(hex=raw)
    except ValueError:
        return None


def _assert_code_eligible(code_model: PartnerCodeModel, account: PartnerAccountModel | None) -> None:
    now = datetime.now(UTC)
    if not code_model.is_active or code_model.lifecycle_status != "active" or code_model.approval_status != "approved":
        raise PartnerAttributionError(
            code="PARTNER_CODE_NOT_ACTIVE",
            message="Partner code is not active.",
            status_code=409,
            clear_cookie=True,
        )
    if code_model.expires_at is not None and _coerce_utc(code_model.expires_at) <= now:
        raise PartnerAttributionError(
            code="PARTNER_CODE_EXPIRED",
            message="Partner code expired.",
            status_code=410,
            clear_cookie=True,
        )
    if code_model.partner_account_id is not None and account is None:
        raise PartnerAttributionError(
            code="PARTNER_ACCOUNT_NOT_FOUND",
            message="Partner account was not found.",
            status_code=409,
            clear_cookie=True,
        )
    if account is not None and account.status != "active":
        raise PartnerAttributionError(
            code="PARTNER_ACCOUNT_NOT_ACTIVE",
            message="Partner account is not active.",
            status_code=409,
            clear_cookie=True,
        )
    if code_model.partner_account_id is None and code_model.partner_user_id is None:
        raise PartnerAttributionError(
            code="PARTNER_OWNER_NOT_CONFIGURED",
            message="Partner code owner is not configured.",
            status_code=409,
            clear_cookie=True,
        )
    if _code_owner_type(code_model) not in _ALLOWED_OWNER_TYPES:
        raise PartnerAttributionError(
            code="PARTNER_OWNER_TYPE_NOT_ELIGIBLE",
            message="Partner owner type is not eligible for attribution.",
            status_code=409,
            clear_cookie=True,
        )


def _assert_not_self_attribution(
    user: MobileUserModel,
    code_model: PartnerCodeModel,
    account: PartnerAccountModel | None,
) -> None:
    if code_model.partner_user_id is not None and code_model.partner_user_id == user.id:
        raise PartnerAttributionError(
            code="PARTNER_SELF_ATTRIBUTION_BLOCKED",
            message="Partner cannot claim their own code.",
            status_code=409,
            clear_cookie=True,
        )
    if account is not None and account.legacy_owner_user_id == user.id:
        raise PartnerAttributionError(
            code="PARTNER_SELF_ATTRIBUTION_BLOCKED",
            message="Partner cannot claim their own account code.",
            status_code=409,
            clear_cookie=True,
        )
    if code_model.partner_account_id is not None and user.partner_account_id == code_model.partner_account_id:
        raise PartnerAttributionError(
            code="PARTNER_SELF_ATTRIBUTION_BLOCKED",
            message="Partner workspace members cannot claim their own account code.",
            status_code=409,
            clear_cookie=True,
        )


def _find_active_owner(bindings: list[CustomerCommercialBindingModel]) -> CustomerCommercialBindingModel | None:
    for binding in bindings:
        if (
            binding.binding_status == CustomerCommercialBindingStatus.ACTIVE.value
            and binding.owner_type != CommercialOwnerType.NONE.value
            and (binding.partner_account_id is not None or binding.partner_code_id is not None)
        ):
            return binding
    return None


def _code_owner_type(code_model: PartnerCodeModel) -> str:
    owner_type = (code_model.owner_type or "").strip()
    return owner_type if owner_type in _ALLOWED_OWNER_TYPES else CommercialOwnerType.AFFILIATE.value


def _build_policy_snapshot(code_model: PartnerCodeModel, account: PartnerAccountModel | None) -> dict[str, Any]:
    return {
        "partner_account_id": str(code_model.partner_account_id) if code_model.partner_account_id else None,
        "partner_account_status": account.status if account else None,
        "partner_code_id": str(code_model.id),
        "code_kind": code_model.code_kind,
        "owner_type": _code_owner_type(code_model),
        "lane_key": code_model.lane_key,
        "attribution_model": code_model.attribution_model,
        "attribution_window_seconds": int(code_model.attribution_window_seconds or 0),
        "policy_version_id": str(code_model.policy_version_id) if code_model.policy_version_id else None,
        "commission_contract_id": str(code_model.commission_contract_id) if code_model.commission_contract_id else None,
        "markup_pct": float(code_model.markup_pct or 0),
        "allowed_channels": list(code_model.allowed_channels or []),
        "allowed_storefront_ids": list(code_model.allowed_storefront_ids or []),
        "allowed_geographies": list(code_model.allowed_geographies or []),
        "active_from": code_model.active_from.isoformat() if code_model.active_from else None,
        "expires_at": code_model.expires_at.isoformat() if code_model.expires_at else None,
        "snapshot_at": datetime.now(UTC).isoformat(),
        "snapshot_version": "partner_attribution_v2",
    }


def _sanitize_campaign_params(campaign_params: dict[str, Any] | None) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    for key, value in dict(campaign_params or {}).items():
        key_text = str(key).strip()
        if not key_text or len(key_text) > 64:
            continue
        sanitized[key_text] = str(value).strip()[:200]
    return sanitized


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
