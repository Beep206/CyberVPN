"""Partner attribution capture, transfer, and claim use cases."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService
from src.application.use_cases.attribution.record_touchpoint import RecordAttributionTouchpointUseCase
from src.application.use_cases.commercial_bindings.create_binding import (
    CreateCustomerCommercialBindingUseCase,
)
from src.application.use_cases.partner_attribution.eligibility import (
    EvaluatePartnerCodeEligibilityCommand,
    EvaluatePartnerCodeEligibilityUseCase,
    PartnerCodeEligibilityResult,
)
from src.application.use_cases.partner_attribution.utils import (
    PARTNER_ATTRIBUTION_STORAGE_VERSION,
    PARTNER_ATTRIBUTION_TRANSFER_TTL_SECONDS,
    build_customer_destination_url,
    build_public_token_for_code_id,
    clamp_optional,
    generate_transfer_token,
    hash_partner_attribution_token,
    mask_partner_code,
    normalize_customer_destination_path,
    normalize_customer_locale,
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
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeLinkModel, PartnerCodeModel
from src.infrastructure.database.repositories.customer_commercial_binding_repo import (
    CustomerCommercialBindingRepository,
)
from src.infrastructure.database.repositories.partner_attribution_session_repo import (
    PartnerAttributionSessionRepository,
)
from src.infrastructure.database.repositories.partner_repo import PartnerRepository
from src.infrastructure.monitoring.partner_runtime_metrics import partner_attribution_legacy_public_token_total
from src.presentation.dependencies.auth_realms import RealmResolution

_logger = logging.getLogger(__name__)

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
    destination_path: str | None
    locale: str | None
    sale_channel: str | None
    sub_ids: dict[str, str] | None
    click_id: str | None
    browser_key: str | None
    capture_idempotency_key: str | None
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
    captured_at: datetime
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


@dataclass(frozen=True)
class _ResolvedPublicToken:
    code_model: PartnerCodeModel
    link_model: PartnerCodeLinkModel | None
    source: str


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

        resolved = await self._find_code_by_public_token(command.public_token)
        code_model = resolved.code_model
        link_model = resolved.link_model
        partner_account = await self._load_partner_account(code_model)

        now = datetime.now(UTC)
        browser_key_hash = hash_partner_attribution_token(command.browser_key.strip()) if command.browser_key else None
        idempotency_key_hash = (
            hash_partner_attribution_token(command.capture_idempotency_key.strip())
            if command.capture_idempotency_key
            else None
        )
        locale = normalize_customer_locale(link_model.locale if link_model and link_model.locale else command.locale)
        if link_model is not None:
            raw_destination_path = link_model.destination_path
        else:
            raw_destination_path = command.destination_path or code_model.destination_path
        destination_path = normalize_customer_destination_path(raw_destination_path)
        sale_channel = link_model.sale_channel if link_model and link_model.sale_channel else command.sale_channel
        campaign_params = link_model.campaign_params if link_model is not None else command.campaign_params
        sub_ids = link_model.sub_ids if link_model is not None else command.sub_ids
        eligibility = EvaluatePartnerCodeEligibilityUseCase().execute(
            EvaluatePartnerCodeEligibilityCommand(
                code_model=code_model,
                account=partner_account,
                link_model=link_model,
                sale_channel=sale_channel,
                storefront_id=code_model.default_storefront_id,
                now=now,
            )
        )
        _assert_eligibility_allowed(eligibility)

        existing = await self._find_existing_capture(
            code_model=code_model,
            current_realm=command.current_realm,
            browser_key_hash=browser_key_hash,
            idempotency_key_hash=idempotency_key_hash,
            now=now,
        )
        if existing is not None:
            existing.last_seen_at = now
            existing.updated_at = now
            await self._session.flush()
            transfer_token = _extract_transfer_token_from_destination_url(existing.destination_url)
            if transfer_token is not None:
                return CapturePartnerAttributionResult(
                    attribution_id=existing.id,
                    captured_at=existing.created_at,
                    expires_at=existing.expires_at,
                    masked_code=mask_partner_code(code_model.code),
                    transfer_token=transfer_token,
                    redirect_url=existing.destination_url,
                )

        transfer_token = generate_transfer_token()
        transfer_hash = hash_partner_attribution_token(transfer_token)
        window_seconds = max(int(code_model.attribution_window_seconds or 0), PARTNER_ATTRIBUTION_TRANSFER_TTL_SECONDS)
        expires_at = now + timedelta(seconds=window_seconds)
        transfer_expires_at = now + timedelta(seconds=min(PARTNER_ATTRIBUTION_TRANSFER_TTL_SECONDS, window_seconds))
        destination_url = build_customer_destination_url(
            transfer_token,
            locale=locale,
            destination_path=destination_path,
        )
        policy_snapshot = eligibility.policy_snapshot
        session_model = PartnerAttributionSessionModel(
            session_token_hash=None,
            transfer_token_hash=transfer_hash,
            transfer_expires_at=transfer_expires_at,
            partner_code_id=code_model.id,
            partner_code_link_id=link_model.id if link_model is not None else None,
            partner_account_id=code_model.partner_account_id,
            auth_realm_id=UUID(command.current_realm.realm_id),
            storefront_id=code_model.default_storefront_id,
            status="pending",
            owner_type=eligibility.owner_type or _code_owner_type(code_model),
            attribution_model=code_model.attribution_model,
            policy_version_id=code_model.policy_version_id,
            commission_contract_id=code_model.commission_contract_id,
            source_host=clamp_optional(command.source_host, 255),
            source_path=clamp_optional(command.source_path, 500),
            destination_path=destination_path,
            locale=locale,
            sale_channel=clamp_optional(sale_channel, 40),
            sub_ids=_sanitize_sub_ids(sub_ids),
            click_id=clamp_optional(command.click_id, 160),
            browser_key_hash=browser_key_hash,
            capture_idempotency_key_hash=idempotency_key_hash,
            destination_url=destination_url,
            campaign_params=_sanitize_campaign_params(campaign_params),
            evidence_payload={
                "public_token_hash": hash_partner_attribution_token(command.public_token),
                "public_token_source": resolved.source,
                "partner_code_link_id": str(link_model.id) if link_model is not None else None,
                "link_destination_key": link_model.destination_key if link_model is not None else None,
                "masked_code": mask_partner_code(code_model.code),
                "storage_version": PARTNER_ATTRIBUTION_STORAGE_VERSION,
                "transfer_token_ttl_seconds": PARTNER_ATTRIBUTION_TRANSFER_TTL_SECONDS,
            },
            policy_snapshot=policy_snapshot,
            expires_at=expires_at,
            first_seen_at=now,
            last_seen_at=now,
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
            sale_channel=created.sale_channel,
            campaign_params=created.campaign_params,
            evidence_payload={
                "partner_attribution_session_id": str(created.id),
                "partner_account_id": str(created.partner_account_id) if created.partner_account_id else None,
                "partner_code_link_id": str(link_model.id) if link_model is not None else None,
                "owner_type": created.owner_type,
                "destination_path": created.destination_path,
                "locale": created.locale,
                "sub_ids": dict(created.sub_ids or {}),
                "click_id": created.click_id,
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
                "transfer_expires_at": transfer_expires_at.isoformat(),
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

    async def _find_code_by_public_token(self, public_token: str) -> _ResolvedPublicToken:
        token_value = public_token.strip()
        token_hash = hash_partner_attribution_token(token_value)
        link_model = await self._partners.get_code_link_by_public_slug(token_value)
        if link_model is not None:
            code_model = await self._partners.get_code_by_id(link_model.partner_code_id)
            if code_model is None:
                raise PartnerAttributionError(
                    code="PARTNER_CODE_NOT_FOUND",
                    message="Partner public token was not found.",
                    status_code=404,
                )
            return _ResolvedPublicToken(code_model=code_model, link_model=link_model, source="partner_code_link")
        if settings.partner_legacy_code_public_slug_enabled:
            code_model = await self._partners.get_code_by_public_slug(token_value)
            if code_model is not None:
                _record_legacy_public_token_resolution(
                    source="code_public_slug",
                    result="resolved",
                    public_token_hash=token_hash,
                )
                return _ResolvedPublicToken(
                    code_model=code_model, link_model=None, source="partner_code_public_slug_legacy"
                )
            code_model = await self._partners.get_code_by_public_token_hash(token_hash)
            if code_model is not None:
                _record_legacy_public_token_resolution(
                    source="code_public_token_hash",
                    result="resolved",
                    public_token_hash=token_hash,
                )
                if not code_model.public_slug:
                    code_model.public_slug = token_value
                    await self._session.flush()
                return _ResolvedPublicToken(
                    code_model=code_model,
                    link_model=None,
                    source="partner_code_public_token_hash_legacy",
                )
        else:
            legacy_source = await self._resolve_disabled_legacy_code_source(
                token_value=token_value,
                token_hash=token_hash,
            )
            if legacy_source is not None:
                _record_legacy_public_token_resolution(
                    source=legacy_source,
                    result="disabled",
                    public_token_hash=token_hash,
                )
                raise PartnerAttributionError(
                    code="PARTNER_LEGACY_PUBLIC_TOKEN_DISABLED",
                    message="Legacy partner public token fallback is disabled.",
                    status_code=410,
                    clear_cookie=True,
                )
        fallback_id = _parse_deterministic_public_token(token_value)
        if fallback_id is None:
            raise PartnerAttributionError(
                code="PARTNER_CODE_NOT_FOUND",
                message="Partner public token was not found.",
                status_code=404,
            )
        if not settings.partner_deterministic_public_token_fallback_enabled:
            _record_legacy_public_token_resolution(
                source="deterministic_px",
                result="disabled",
                public_token_hash=token_hash,
            )
            raise PartnerAttributionError(
                code="PARTNER_LEGACY_PUBLIC_TOKEN_DISABLED",
                message="Legacy partner public token fallback is disabled.",
                status_code=410,
                clear_cookie=True,
            )
        code_model = await self._partners.get_code_by_id(fallback_id)
        if code_model is None:
            _record_legacy_public_token_resolution(
                source="deterministic_px",
                result="not_found",
                public_token_hash=token_hash,
            )
            raise PartnerAttributionError(
                code="PARTNER_CODE_NOT_FOUND",
                message="Partner public token was not found.",
                status_code=404,
            )
        _record_legacy_public_token_resolution(
            source="deterministic_px",
            result="resolved",
            public_token_hash=token_hash,
        )
        if not code_model.public_token_hash:
            code_model.public_token_hash = hash_partner_attribution_token(build_public_token_for_code_id(code_model.id))
        if not code_model.public_slug:
            code_model.public_slug = build_public_token_for_code_id(code_model.id)
            await self._session.flush()
        return _ResolvedPublicToken(code_model=code_model, link_model=None, source="partner_code_deterministic_legacy")

    async def _load_partner_account(self, code_model: PartnerCodeModel) -> PartnerAccountModel | None:
        if code_model.partner_account_id is None:
            return None
        return await self._partners.get_account_by_id(code_model.partner_account_id)

    async def _resolve_disabled_legacy_code_source(self, *, token_value: str, token_hash: str) -> str | None:
        if await self._partners.get_code_by_public_slug(token_value) is not None:
            return "code_public_slug"
        if await self._partners.get_code_by_public_token_hash(token_hash) is not None:
            return "code_public_token_hash"
        return None

    async def _find_existing_capture(
        self,
        *,
        code_model: PartnerCodeModel,
        current_realm: RealmResolution,
        browser_key_hash: str | None,
        idempotency_key_hash: str | None,
        now: datetime,
    ) -> PartnerAttributionSessionModel | None:
        if idempotency_key_hash:
            existing = await self._sessions.get_by_capture_idempotency_key(
                idempotency_key_hash,
                for_update=True,
            )
            if _is_reusable_capture(existing, code_model=code_model, current_realm=current_realm, now=now):
                return existing
        if browser_key_hash:
            existing = await self._sessions.get_active_for_browser(
                partner_code_id=code_model.id,
                auth_realm_id=UUID(current_realm.realm_id),
                storefront_id=code_model.default_storefront_id,
                browser_key_hash=browser_key_hash,
                now=now,
                for_update=True,
            )
            if _is_reusable_capture(existing, code_model=code_model, current_realm=current_realm, now=now):
                return existing
        return None


class ConsumePartnerAttributionTransferUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._sessions = PartnerAttributionSessionRepository(session)
        self._session = session
        self._partners = PartnerRepository(session)

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
                code="PARTNER_TRANSFER_TOKEN_INVALID",
                message="Partner attribution transfer token was not found.",
                status_code=404,
                clear_cookie=True,
            )

        now = datetime.now(UTC)
        if attribution.transfer_consumed_at is not None:
            raise PartnerAttributionError(
                code="PARTNER_TRANSFER_TOKEN_CONSUMED",
                message="Partner attribution transfer token was already consumed.",
                status_code=409,
                clear_cookie=True,
            )
        if attribution.transfer_expires_at is not None and _coerce_utc(attribution.transfer_expires_at) <= now:
            attribution.rejection_reason_code = "transfer_token_expired"
            attribution.updated_at = now
            await self._session.flush()
            raise PartnerAttributionError(
                code="PARTNER_TRANSFER_TOKEN_EXPIRED",
                message="Partner attribution transfer token expired.",
                status_code=410,
                clear_cookie=True,
            )
        if attribution.status in _TERMINAL_STATUSES or _coerce_utc(attribution.expires_at) <= now:
            attribution.status = "expired" if attribution.status not in _TERMINAL_STATUSES else attribution.status
            attribution.rejection_reason_code = attribution.rejection_reason_code or "attribution_window_expired"
            attribution.updated_at = now
            await self._session.flush()
            raise PartnerAttributionError(
                code="PARTNER_ATTRIBUTION_SESSION_EXPIRED",
                message="Partner attribution transfer token expired.",
                status_code=410,
                clear_cookie=True,
            )

        code_model = await self._partners.get_code_by_id(attribution.partner_code_id)
        if code_model is None:
            attribution.status = "invalidated"
            attribution.updated_at = now
            await self._session.flush()
            raise PartnerAttributionError(
                code="PARTNER_CODE_NOT_FOUND",
                message="Partner public token was not found.",
                status_code=404,
                clear_cookie=True,
            )
        partner_account = (
            await self._partners.get_account_by_id(code_model.partner_account_id)
            if code_model.partner_account_id is not None
            else None
        )
        link_model = (
            await self._partners.get_code_link_by_id(attribution.partner_code_link_id)
            if attribution.partner_code_link_id is not None
            else None
        )
        eligibility = EvaluatePartnerCodeEligibilityUseCase().execute(
            EvaluatePartnerCodeEligibilityCommand(
                code_model=code_model,
                account=partner_account,
                link_model=link_model,
                sale_channel=attribution.sale_channel,
                storefront_id=attribution.storefront_id,
                now=now,
            )
        )
        _assert_eligibility_allowed(eligibility)

        session_token = generate_transfer_token()
        attribution.consumed_transfer_token_hash = attribution.transfer_token_hash
        attribution.session_token_hash = hash_partner_attribution_token(session_token)
        attribution.transfer_token_hash = None
        attribution.transfer_consumed_at = now
        if attribution.status == "pending":
            attribution.status = "transferred"
            attribution.transferred_at = now
        attribution.last_seen_at = now
        attribution.updated_at = now
        await self._session.flush()

        return ConsumePartnerAttributionTransferResult(
            attribution_id=attribution.id,
            captured_at=attribution.created_at,
            expires_at=attribution.expires_at,
            cookie_token=session_token,
            masked_code=mask_partner_code(code_model.code),
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

        attribution = await self._sessions.get_by_session_token_hash(
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
        link_model = (
            await self._partners.get_code_link_by_id(attribution.partner_code_link_id)
            if attribution.partner_code_link_id is not None
            else None
        )
        eligibility = EvaluatePartnerCodeEligibilityUseCase().execute(
            EvaluatePartnerCodeEligibilityCommand(
                code_model=code_model,
                account=partner_account,
                link_model=link_model,
                sale_channel=attribution.sale_channel,
                storefront_id=attribution.storefront_id,
                now=now,
            )
        )
        _assert_eligibility_allowed(eligibility)
        _assert_not_self_attribution(user, code_model, partner_account)

        active_bindings = await self._bindings.list_active_for_user(
            user_id=user.id,
            storefront_id=attribution.storefront_id,
            for_update=True,
        )
        existing_binding = _find_active_owner(active_bindings, storefront_id=attribution.storefront_id)
        if existing_binding is not None:
            return await self._claim_existing_owner(attribution=attribution, existing_binding=existing_binding, now=now)

        try:
            async with self._session.begin_nested():
                binding = await CreateCustomerCommercialBindingUseCase(self._session).execute(
                    user_id=user.id,
                    binding_type=CustomerCommercialBindingType.PARTNER_ATTRIBUTION.value,
                    owner_type=attribution.owner_type,
                    storefront_id=attribution.storefront_id,
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
                claim_touchpoint = await RecordAttributionTouchpointUseCase(self._session).execute(
                    current_realm=command.current_realm,
                    touchpoint_type=AttributionTouchpointType.PARTNER_CLAIM.value,
                    user_id=user.id,
                    storefront_id=attribution.storefront_id,
                    partner_code_id=code_model.id,
                    partner_attribution_session_id=attribution.id,
                    policy_version_id=attribution.policy_version_id,
                    source_event_id=f"partner_claim:{attribution.id}:{user.id}",
                    idempotency_key=f"partner-claim:{attribution.id}:{user.id}",
                    sale_channel=attribution.sale_channel,
                    source_host=attribution.source_host,
                    source_path=attribution.source_path,
                    campaign_params=attribution.campaign_params,
                    evidence_payload={
                        "binding_id": str(binding.id),
                        "partner_account_id": (
                            str(code_model.partner_account_id) if code_model.partner_account_id else None
                        ),
                        "owner_type": attribution.owner_type,
                        "storefront_id": str(attribution.storefront_id) if attribution.storefront_id else None,
                    },
                    occurred_at=now,
                    commit=False,
                )
                attribution.status = "claimed"
                attribution.user_id = user.id
                attribution.binding_id = binding.id
                attribution.claimed_at = now
                attribution.touchpoint_id = claim_touchpoint.id
                attribution.updated_at = now

                await self._outbox.append_event(
                    event_name="partner.attribution.claimed",
                    aggregate_type="partner_attribution_session",
                    aggregate_id=str(attribution.id),
                    partition_key=str(user.id),
                    event_payload={
                        "user_id": str(user.id),
                        "partner_code_id": str(code_model.id),
                        "partner_account_id": (
                            str(code_model.partner_account_id) if code_model.partner_account_id else None
                        ),
                        "binding_id": str(binding.id),
                        "owner_type": attribution.owner_type,
                    },
                    source_context={"source_use_case": "ClaimPartnerAttributionUseCase"},
                )
        except IntegrityError as exc:
            if not _is_active_owner_unique_violation(exc):
                raise
            active_bindings = await self._bindings.list_active_for_user(
                user_id=user.id,
                storefront_id=attribution.storefront_id,
                for_update=True,
            )
            existing_binding = _find_active_owner(active_bindings, storefront_id=attribution.storefront_id)
            if existing_binding is None:
                raise
            return await self._claim_existing_owner(attribution=attribution, existing_binding=existing_binding, now=now)
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

    async def _claim_existing_owner(
        self,
        *,
        attribution: PartnerAttributionSessionModel,
        existing_binding: CustomerCommercialBindingModel,
        now: datetime,
    ) -> ClaimPartnerAttributionResult:
        attribution.user_id = existing_binding.user_id
        attribution.updated_at = now
        if existing_binding.partner_account_id is None and existing_binding.partner_code_id is None:
            attribution.status = "rejected"
            attribution.rejection_reason_code = "manual_review_required_active_owner_conflict"
            await self._session.flush()
            return ClaimPartnerAttributionResult(
                status="manual_review_required",
                binding_id=existing_binding.id,
                clear_cookie=True,
            )

        if _is_same_owner_binding(existing_binding, attribution):
            attribution.status = "claimed"
            attribution.binding_id = existing_binding.id
            attribution.claimed_at = attribution.claimed_at or now
            await self._session.flush()
            return ClaimPartnerAttributionResult(
                status="already_claimed_same_owner",
                partner_account_id=existing_binding.partner_account_id,
                partner_code_id=existing_binding.partner_code_id,
                binding_id=existing_binding.id,
                claimed_at=attribution.claimed_at,
                clear_cookie=True,
            )

        attribution.status = "rejected"
        attribution.rejection_reason_code = "existing_active_owner_conflict"
        await self._session.flush()
        return ClaimPartnerAttributionResult(
            status="rejected_existing_owner",
            partner_account_id=existing_binding.partner_account_id,
            partner_code_id=existing_binding.partner_code_id,
            binding_id=existing_binding.id,
            clear_cookie=True,
        )


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


_ACTIVE_OWNER_UNIQUE_INDEXES = frozenset(
    {
        "uq_customer_commercial_bindings_active_owner_global_scope",
        "uq_customer_commercial_bindings_active_owner_storefront_scope",
    }
)


def _is_active_owner_unique_violation(exc: IntegrityError) -> bool:
    orig = getattr(exc, "orig", None)
    diag = getattr(orig, "diag", None)
    constraint_name = getattr(diag, "constraint_name", None)
    if constraint_name in _ACTIVE_OWNER_UNIQUE_INDEXES:
        return True
    details = f"{orig!s} {exc!s}"
    return any(index_name in details for index_name in _ACTIVE_OWNER_UNIQUE_INDEXES)


def _record_legacy_public_token_resolution(*, source: str, result: str, public_token_hash: str) -> None:
    partner_attribution_legacy_public_token_total.labels(source=source, result=result).inc()
    sunset_date = (
        settings.partner_deterministic_public_token_sunset_date
        if source == "deterministic_px"
        else settings.partner_legacy_code_public_slug_sunset_date
    )
    _logger.warning(
        "partner_attribution_legacy_public_token_%s",
        result,
        extra={
            "source": source,
            "result": result,
            "public_token_hash": public_token_hash,
            "sunset_date": sunset_date,
        },
    )


def _is_reusable_capture(
    attribution: PartnerAttributionSessionModel | None,
    *,
    code_model: PartnerCodeModel,
    current_realm: RealmResolution,
    now: datetime,
) -> bool:
    return (
        attribution is not None
        and attribution.partner_code_id == code_model.id
        and str(attribution.auth_realm_id) == current_realm.realm_id
        and attribution.status == "pending"
        and attribution.transfer_consumed_at is None
        and _coerce_utc(attribution.expires_at) > now
    )


def _extract_transfer_token_from_destination_url(destination_url: str | None) -> str | None:
    if not destination_url:
        return None
    values = parse_qs(urlsplit(destination_url).query).get("pat")
    if not values:
        return None
    token = values[0].strip()
    return token or None


def _assert_eligibility_allowed(result: PartnerCodeEligibilityResult) -> None:
    if result.allowed:
        return
    raise PartnerAttributionError(
        code=result.error_code or "PARTNER_CODE_NOT_ELIGIBLE",
        message=result.message or "Partner code is not eligible for attribution.",
        status_code=result.status_code,
        clear_cookie=result.clear_cookie,
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


_IMMUTABLE_GLOBAL_BINDING_TYPES = frozenset(
    {
        CustomerCommercialBindingType.MANUAL_OVERRIDE.value,
        CustomerCommercialBindingType.CONTRACT_ASSIGNMENT.value,
    }
)


def _find_active_owner(
    bindings: list[CustomerCommercialBindingModel],
    *,
    storefront_id: UUID | None,
) -> CustomerCommercialBindingModel | None:
    candidates = [
        binding
        for binding in bindings
        if (
            binding.binding_status == CustomerCommercialBindingStatus.ACTIVE.value
            and binding.owner_type != CommercialOwnerType.NONE.value
        )
    ]
    if storefront_id is None:
        return next((binding for binding in candidates if binding.storefront_id is None), None)

    exact_storefront_owner = next((binding for binding in candidates if binding.storefront_id == storefront_id), None)
    if exact_storefront_owner is not None:
        return exact_storefront_owner

    return next(
        (
            binding
            for binding in candidates
            if binding.storefront_id is None and binding.binding_type in _IMMUTABLE_GLOBAL_BINDING_TYPES
        ),
        None,
    )


def _is_same_owner_binding(
    binding: CustomerCommercialBindingModel,
    attribution: PartnerAttributionSessionModel,
) -> bool:
    return (
        binding.owner_type == attribution.owner_type
        and binding.partner_account_id == attribution.partner_account_id
        and binding.partner_code_id == attribution.partner_code_id
        and binding.storefront_id == attribution.storefront_id
    )


def _code_owner_type(code_model: PartnerCodeModel) -> str:
    owner_type = (code_model.owner_type or "").strip()
    if owner_type not in _ALLOWED_OWNER_TYPES:
        raise PartnerAttributionError(
            code="PARTNER_OWNER_TYPE_INVALID",
            message="Partner owner type is invalid.",
            status_code=409,
            clear_cookie=True,
        )
    return owner_type


def _sanitize_campaign_params(campaign_params: dict[str, Any] | None) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    allowed_exact = {"gclid", "fbclid", "click_id", "sub_id"}
    for key, value in dict(campaign_params or {}).items():
        key_text = str(key).strip()
        if not key_text or len(key_text) > 64:
            continue
        if not (key_text.startswith("utm_") or key_text.startswith("sub_") or key_text in allowed_exact):
            continue
        if isinstance(value, dict | list | tuple | set):
            continue
        sanitized[key_text] = str(value).strip()[:200]
        if len(sanitized) >= 24:
            break
    return sanitized


def _sanitize_sub_ids(sub_ids: dict[str, str] | None) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    for key, value in dict(sub_ids or {}).items():
        key_text = str(key).strip()
        if not key_text or len(key_text) > 48:
            continue
        if isinstance(value, dict | list | tuple | set):
            continue
        sanitized[key_text] = str(value).strip()[:160]
        if len(sanitized) >= 16:
            break
    return sanitized


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
