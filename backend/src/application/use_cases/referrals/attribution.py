"""Referral attribution capture and claim use cases."""

from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.attribution.record_touchpoint import RecordAttributionTouchpointUseCase
from src.application.use_cases.growth_codes.registry import GrowthCodeRegistryService
from src.config.settings import settings
from src.domain.enums import (
    AttributionTouchpointType,
    CustomerCommercialBindingStatus,
    GrowthCodeActionContext,
    GrowthCodeResolutionStatus,
    GrowthCodeType,
)
from src.infrastructure.database.models.growth_code_model import (
    GrowthCodeModel,
    GrowthCodeTouchpointModel,
    GrowthSignupAttributionModel,
)
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.referral_attribution_session_model import (
    ReferralAttributionSessionModel,
)
from src.infrastructure.database.repositories.customer_commercial_binding_repo import (
    CustomerCommercialBindingRepository,
)
from src.infrastructure.database.repositories.growth_code_repo import GrowthCodeRepository
from src.infrastructure.monitoring.instrumentation.growth_codes import (
    CUSTOMER_COMMERCE_SURFACE,
    log_growth_code_event,
)
from src.presentation.dependencies.auth_realms import RealmResolution

REFERRAL_ATTRIBUTION_COOKIE_NAME = "cv_ref_attribution"
REFERRAL_ATTRIBUTION_TTL_DAYS = 30
REFERRAL_ATTRIBUTION_MAX_AGE_SECONDS = REFERRAL_ATTRIBUTION_TTL_DAYS * 24 * 60 * 60
REFERRAL_ATTRIBUTION_STORAGE_VERSION = 2

_REFERRAL_CODE_RE = re.compile(r"^[A-Z0-9_-]{4,64}$")
_CAMPAIGN_KEY_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
_TERMINAL_SESSION_STATUSES = frozenset({"claimed", "expired", "invalidated"})


class ReferralAttributionError(Exception):
    def __init__(self, *, code: str, message: str, status_code: int = 400, clear_cookie: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.clear_cookie = clear_cookie


@dataclass(frozen=True)
class CaptureReferralAttributionCommand:
    referral_code: str
    source_host: str | None
    source_path: str | None
    campaign_params: dict[str, Any] | None
    existing_cookie_token: str | None
    current_realm: RealmResolution


@dataclass(frozen=True)
class CaptureReferralAttributionResult:
    attribution_id: UUID
    captured_at: datetime
    expires_at: datetime
    masked_code: str
    set_cookie_token: str | None


@dataclass(frozen=True)
class ClaimReferralAttributionCommand:
    user_id: UUID
    cookie_token: str | None
    fallback_referral_code: str | None
    current_realm: RealmResolution


@dataclass(frozen=True)
class ClaimReferralAttributionResult:
    status: str
    referrer_user_id: UUID | None = None
    claimed_at: datetime | None = None
    clear_cookie: bool = False


class CaptureReferralAttributionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._growth_codes = GrowthCodeRepository(session)
        self._registry = GrowthCodeRegistryService(session)

    async def execute(self, command: CaptureReferralAttributionCommand) -> CaptureReferralAttributionResult:
        if not settings.referral_enabled:
            raise ReferralAttributionError(
                code="REFERRAL_PROGRAM_DISABLED",
                message="Referral program is disabled.",
                status_code=403,
            )

        existing_session = await self._get_reusable_pending_session(command.existing_cookie_token)
        if existing_session is not None:
            existing_code = await self._session.get(GrowthCodeModel, existing_session.growth_code_id)
            return CaptureReferralAttributionResult(
                attribution_id=existing_session.id,
                captured_at=_coerce_utc(existing_session.first_seen_at),
                expires_at=_coerce_utc(existing_session.expires_at),
                masked_code=_mask_code(existing_code.code_prefix if existing_code else None),
                set_cookie_token=None,
            )

        referral_code = _normalize_referral_code(command.referral_code)
        owner = await _find_referral_owner(self._session, referral_code)
        _assert_referral_owner_valid(owner)
        growth_code = await self._registry.ensure_shadow_referral(owner)
        _assert_growth_referral_code_valid(growth_code)

        now = datetime.now(UTC)
        cookie_token = _generate_cookie_token()
        attribution = ReferralAttributionSessionModel(
            token_hash=hash_referral_attribution_token(cookie_token),
            growth_code_id=growth_code.id,
            referrer_user_id=owner.id,
            source_host=_clamp_optional(command.source_host, 255),
            source_path=_clamp_optional(command.source_path, 500),
            campaign_params=_sanitize_campaign_params(command.campaign_params),
            evidence_payload={
                "code_prefix": build_masked_code_prefix(referral_code),
                "capture_surface": CUSTOMER_COMMERCE_SURFACE,
                "storage_version": REFERRAL_ATTRIBUTION_STORAGE_VERSION,
            },
            first_seen_at=now,
            expires_at=now + timedelta(days=REFERRAL_ATTRIBUTION_TTL_DAYS),
        )
        self._session.add(attribution)
        await self._session.flush()

        touchpoint = await self._create_growth_touchpoint(
            growth_code=growth_code,
            attribution_id=attribution.id,
            command=command,
        )
        attribution.growth_code_touchpoint_id = touchpoint.id

        await RecordAttributionTouchpointUseCase(self._session).execute(
            current_realm=command.current_realm,
            touchpoint_type=AttributionTouchpointType.EXPLICIT_CODE.value,
            source_host=attribution.source_host,
            source_path=attribution.source_path,
            campaign_params=attribution.campaign_params,
            evidence_payload={
                "referral_attribution_session_id": str(attribution.id),
                "growth_code_id": str(growth_code.id),
                "referrer_user_id": str(owner.id),
                "code_prefix": build_masked_code_prefix(referral_code),
            },
            commit=False,
        )
        await self._session.flush()

        log_growth_code_event(
            "referral_attribution.captured",
            surface=CUSTOMER_COMMERCE_SURFACE,
            code_type=GrowthCodeType.REFERRAL.value,
            action_context=GrowthCodeActionContext.SIGNUP.value,
            result=GrowthCodeResolutionStatus.ACCEPTED.value,
            growth_code_id=str(growth_code.id),
            referrer_user_id=str(owner.id),
            attribution_session_id=str(attribution.id),
        )

        return CaptureReferralAttributionResult(
            attribution_id=attribution.id,
            captured_at=attribution.first_seen_at,
            expires_at=attribution.expires_at,
            masked_code=_mask_code(referral_code),
            set_cookie_token=cookie_token,
        )

    async def _get_reusable_pending_session(self, cookie_token: str | None) -> ReferralAttributionSessionModel | None:
        if not cookie_token:
            return None

        token_hash = hash_referral_attribution_token(cookie_token)
        result = await self._session.execute(
            select(ReferralAttributionSessionModel)
            .where(ReferralAttributionSessionModel.token_hash == token_hash)
            .limit(1)
        )
        attribution = result.scalars().first()
        if attribution is None or attribution.status in _TERMINAL_SESSION_STATUSES:
            return None

        now = datetime.now(UTC)
        if _coerce_utc(attribution.expires_at) <= now:
            attribution.status = "expired"
            attribution.updated_at = now
            await self._session.flush()
            return None

        return attribution

    async def _create_growth_touchpoint(
        self,
        *,
        growth_code: GrowthCodeModel,
        attribution_id: UUID,
        command: CaptureReferralAttributionCommand,
    ) -> GrowthCodeTouchpointModel:
        campaign = _sanitize_campaign_params(command.campaign_params)
        touchpoint = GrowthCodeTouchpointModel(
            growth_code_id=growth_code.id,
            code_type=GrowthCodeType.REFERRAL.value,
            anonymous_session_id=str(attribution_id),
            auth_realm_id=UUID(command.current_realm.realm_id),
            surface=CUSTOMER_COMMERCE_SURFACE,
            channel="web",
            utm_source=_campaign_value(campaign, "utm_source"),
            utm_medium=_campaign_value(campaign, "utm_medium"),
            utm_campaign=_campaign_value(campaign, "utm_campaign"),
            click_id=_campaign_value(campaign, "click_id") or _campaign_value(campaign, "gclid"),
            sub_id=_campaign_value(campaign, "sub_id"),
        )
        return await self._growth_codes.create_touchpoint(touchpoint)


class ClaimReferralAttributionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._growth_codes = GrowthCodeRepository(session)
        self._registry = GrowthCodeRegistryService(session)
        self._commercial_bindings = CustomerCommercialBindingRepository(session)

    async def execute(self, command: ClaimReferralAttributionCommand) -> ClaimReferralAttributionResult:
        if not settings.referral_enabled:
            raise ReferralAttributionError(
                code="REFERRAL_PROGRAM_DISABLED",
                message="Referral program is disabled.",
                status_code=403,
            )

        user = await self._lock_user(command.user_id)
        if user is None or not user.is_active:
            raise ReferralAttributionError(
                code="REFERRAL_USER_NOT_READY",
                message="User is not ready for referral attribution.",
                status_code=409,
                clear_cookie=False,
            )

        existing = await self._load_existing_signup_attribution(user.id)
        if user.referred_by_user_id is not None or existing is not None:
            return ClaimReferralAttributionResult(
                status="already_claimed",
                referrer_user_id=user.referred_by_user_id,
                claimed_at=user.referral_claimed_at or (existing.created_at if existing else None),
                clear_cookie=True,
            )

        await self._assert_no_partner_conflict(user)

        attribution = await self._find_usable_session(
            command.cookie_token,
            raise_on_expired=not bool(command.fallback_referral_code),
        )
        if attribution is None and command.fallback_referral_code:
            attribution = await self._build_fallback_session(command)

        if attribution is None:
            return ClaimReferralAttributionResult(status="no_pending")

        if attribution.status == "claimed" and attribution.claimed_by_user_id == user.id:
            return ClaimReferralAttributionResult(
                status="already_claimed",
                referrer_user_id=attribution.referrer_user_id,
                claimed_at=attribution.claimed_at,
                clear_cookie=True,
            )

        if attribution.claimed_by_user_id is not None and attribution.claimed_by_user_id != user.id:
            raise ReferralAttributionError(
                code="REFERRAL_ALREADY_CLAIMED",
                message="Referral attribution was already claimed.",
                status_code=409,
                clear_cookie=True,
            )

        growth_code = await self._session.get(GrowthCodeModel, attribution.growth_code_id)
        if growth_code is None:
            raise ReferralAttributionError(
                code="REFERRAL_CODE_NOT_FOUND",
                message="Referral code was not found.",
                status_code=404,
                clear_cookie=True,
            )
        _assert_growth_referral_code_valid(growth_code)

        referrer = await self._session.get(MobileUserModel, attribution.referrer_user_id)
        referrer = _assert_referral_owner_valid(referrer)
        if referrer.id == user.id:
            raise ReferralAttributionError(
                code="REFERRAL_SELF_ATTRIBUTION_BLOCKED",
                message="Self-referral is not allowed.",
                status_code=409,
                clear_cookie=True,
            )
        if referrer.auth_realm_id and user.auth_realm_id and referrer.auth_realm_id != user.auth_realm_id:
            raise ReferralAttributionError(
                code="REFERRAL_CODE_NOT_FOUND",
                message="Referral code was not found.",
                status_code=404,
                clear_cookie=True,
            )

        now = datetime.now(UTC)
        touchpoint_id = await self._ensure_claim_touchpoint(
            attribution=attribution,
            growth_code=growth_code,
            user=user,
            current_realm=command.current_realm,
        )

        signup_attribution = GrowthSignupAttributionModel(
            user_id=user.id,
            growth_code_id=growth_code.id,
            code_type=GrowthCodeType.REFERRAL.value,
            touchpoint_id=touchpoint_id,
            attribution_source="referral_attribution_session",
            auth_realm_id=user.auth_realm_id,
        )
        await self._growth_codes.create_signup_attribution(signup_attribution)

        user.referred_by_user_id = referrer.id
        user.referral_claimed_at = now
        user.referral_source_code_id = growth_code.id
        user.referral_attribution_session_id = attribution.id
        user.updated_at = now

        attribution.status = "claimed"
        attribution.claimed_by_user_id = user.id
        attribution.claimed_at = now
        attribution.updated_at = now

        await RecordAttributionTouchpointUseCase(self._session).execute(
            current_realm=command.current_realm,
            touchpoint_type=AttributionTouchpointType.EXPLICIT_CODE.value,
            user_id=user.id,
            source_host=attribution.source_host,
            source_path=attribution.source_path,
            campaign_params=attribution.campaign_params,
            evidence_payload={
                "referral_attribution_session_id": str(attribution.id),
                "growth_code_id": str(growth_code.id),
                "referrer_user_id": str(referrer.id),
                "claimed_by_user_id": str(user.id),
            },
            commit=False,
        )
        await self._session.flush()

        log_growth_code_event(
            "referral_attribution.claimed",
            surface=CUSTOMER_COMMERCE_SURFACE,
            code_type=GrowthCodeType.REFERRAL.value,
            action_context=GrowthCodeActionContext.SIGNUP.value,
            result=GrowthCodeResolutionStatus.ACCEPTED.value,
            growth_code_id=str(growth_code.id),
            referrer_user_id=str(referrer.id),
            claimed_by_user_id=str(user.id),
            attribution_session_id=str(attribution.id),
        )

        return ClaimReferralAttributionResult(
            status="claimed",
            referrer_user_id=referrer.id,
            claimed_at=now,
            clear_cookie=True,
        )

    async def _lock_user(self, user_id: UUID) -> MobileUserModel | None:
        result = await self._session.execute(
            select(MobileUserModel).where(MobileUserModel.id == user_id).with_for_update()
        )
        return result.scalars().one_or_none()

    async def _load_existing_signup_attribution(self, user_id: UUID) -> GrowthSignupAttributionModel | None:
        result = await self._session.execute(
            select(GrowthSignupAttributionModel).where(GrowthSignupAttributionModel.user_id == user_id).limit(1)
        )
        return result.scalars().first()

    async def _assert_no_partner_conflict(self, user: MobileUserModel) -> None:
        if user.partner_user_id is not None or user.partner_account_id is not None:
            raise ReferralAttributionError(
                code="REFERRAL_PARTNER_ATTRIBUTION_CONFLICT",
                message="Partner attribution already owns this customer.",
                status_code=409,
                clear_cookie=False,
            )

        bindings = await self._commercial_bindings.list_active_for_user(user_id=user.id, storefront_id=None)
        for binding in bindings:
            if binding.binding_status == CustomerCommercialBindingStatus.ACTIVE.value and (
                binding.partner_account_id is not None or binding.partner_code_id is not None
            ):
                raise ReferralAttributionError(
                    code="REFERRAL_PARTNER_ATTRIBUTION_CONFLICT",
                    message="Partner attribution already owns this customer.",
                    status_code=409,
                    clear_cookie=False,
                )

    async def _find_usable_session(
        self,
        cookie_token: str | None,
        *,
        raise_on_expired: bool,
    ) -> ReferralAttributionSessionModel | None:
        if not cookie_token:
            return None

        result = await self._session.execute(
            select(ReferralAttributionSessionModel)
            .where(ReferralAttributionSessionModel.token_hash == hash_referral_attribution_token(cookie_token))
            .with_for_update()
            .limit(1)
        )
        attribution = result.scalars().first()
        if attribution is None:
            return None
        if attribution.status == "claimed":
            return attribution
        if attribution.status in _TERMINAL_SESSION_STATUSES:
            return None

        now = datetime.now(UTC)
        if _coerce_utc(attribution.expires_at) <= now:
            attribution.status = "expired"
            attribution.updated_at = now
            await self._session.flush()
            if not raise_on_expired:
                return None
            raise ReferralAttributionError(
                code="REFERRAL_ATTRIBUTION_EXPIRED",
                message="Referral attribution has expired.",
                status_code=410,
                clear_cookie=True,
            )

        return attribution

    async def _build_fallback_session(
        self,
        command: ClaimReferralAttributionCommand,
    ) -> ReferralAttributionSessionModel:
        referral_code = _normalize_referral_code(command.fallback_referral_code or "")
        owner = await _find_referral_owner(self._session, referral_code)
        _assert_referral_owner_valid(owner)
        growth_code = await self._registry.ensure_shadow_referral(owner)
        _assert_growth_referral_code_valid(growth_code)
        now = datetime.now(UTC)
        fallback_token = _generate_cookie_token()
        attribution = ReferralAttributionSessionModel(
            token_hash=hash_referral_attribution_token(fallback_token),
            growth_code_id=growth_code.id,
            referrer_user_id=owner.id,
            status="pending",
            source_host=None,
            source_path=None,
            campaign_params={},
            evidence_payload={
                "capture_surface": CUSTOMER_COMMERCE_SURFACE,
                "fallback": "local_storage",
                "code_prefix": build_masked_code_prefix(referral_code),
                "storage_version": REFERRAL_ATTRIBUTION_STORAGE_VERSION,
            },
            first_seen_at=now,
            expires_at=now + timedelta(days=REFERRAL_ATTRIBUTION_TTL_DAYS),
        )
        self._session.add(attribution)
        await self._session.flush()
        touchpoint = GrowthCodeTouchpointModel(
            growth_code_id=growth_code.id,
            code_type=GrowthCodeType.REFERRAL.value,
            anonymous_session_id=str(attribution.id),
            registered_user_id=command.user_id,
            auth_realm_id=UUID(command.current_realm.realm_id),
            surface=CUSTOMER_COMMERCE_SURFACE,
            channel="web",
        )
        created_touchpoint = await self._growth_codes.create_touchpoint(touchpoint)
        attribution.growth_code_touchpoint_id = created_touchpoint.id
        await self._session.flush()
        return attribution

    async def _ensure_claim_touchpoint(
        self,
        *,
        attribution: ReferralAttributionSessionModel,
        growth_code: GrowthCodeModel,
        user: MobileUserModel,
        current_realm: RealmResolution,
    ) -> UUID:
        if attribution.growth_code_touchpoint_id is not None:
            touchpoint = await self._session.get(GrowthCodeTouchpointModel, attribution.growth_code_touchpoint_id)
            if touchpoint is not None:
                touchpoint.registered_user_id = user.id
                touchpoint.converted_to_signup_at = datetime.now(UTC)
                await self._session.flush()
                return touchpoint.id

        touchpoint = GrowthCodeTouchpointModel(
            growth_code_id=growth_code.id,
            code_type=GrowthCodeType.REFERRAL.value,
            anonymous_session_id=str(attribution.id),
            registered_user_id=user.id,
            auth_realm_id=UUID(current_realm.realm_id),
            surface=CUSTOMER_COMMERCE_SURFACE,
            channel="web",
            converted_to_signup_at=datetime.now(UTC),
        )
        created = await self._growth_codes.create_touchpoint(touchpoint)
        attribution.growth_code_touchpoint_id = created.id
        await self._session.flush()
        return created.id


async def _find_referral_owner(session: AsyncSession, referral_code: str) -> MobileUserModel:
    result = await session.execute(
        select(MobileUserModel).where(MobileUserModel.referral_code == referral_code).limit(1)
    )
    owner = result.scalars().first()
    if owner is None:
        raise ReferralAttributionError(
            code="REFERRAL_CODE_NOT_FOUND",
            message="Referral code was not found.",
            status_code=404,
        )
    return owner


def _assert_referral_owner_valid(owner: MobileUserModel | None) -> MobileUserModel:
    if owner is None:
        raise ReferralAttributionError(
            code="REFERRAL_CODE_NOT_FOUND",
            message="Referral code was not found.",
            status_code=404,
        )
    if not owner.is_active or owner.status != "active":
        raise ReferralAttributionError(
            code="REFERRAL_CODE_INACTIVE",
            message="Referral code is inactive.",
            status_code=409,
        )
    return owner


def _assert_growth_referral_code_valid(growth_code: GrowthCodeModel) -> None:
    now = datetime.now(UTC)
    if growth_code.code_type != GrowthCodeType.REFERRAL.value:
        raise ReferralAttributionError(
            code="REFERRAL_CODE_INVALID",
            message="Referral code is invalid for signup attribution.",
            status_code=400,
        )
    if growth_code.status != "active" or growth_code.revoked_at is not None:
        raise ReferralAttributionError(
            code="REFERRAL_CODE_INACTIVE",
            message="Referral code is inactive.",
            status_code=409,
        )
    if growth_code.starts_at and _coerce_utc(growth_code.starts_at) > now:
        raise ReferralAttributionError(
            code="REFERRAL_CODE_INACTIVE",
            message="Referral code is not active yet.",
            status_code=409,
        )
    if growth_code.expires_at and _coerce_utc(growth_code.expires_at) <= now:
        raise ReferralAttributionError(
            code="REFERRAL_ATTRIBUTION_EXPIRED",
            message="Referral code has expired.",
            status_code=410,
        )


def _normalize_referral_code(raw_code: str) -> str:
    normalized = raw_code.strip().upper()
    if not _REFERRAL_CODE_RE.fullmatch(normalized):
        raise ReferralAttributionError(
            code="REFERRAL_CODE_INVALID",
            message="Referral code is invalid.",
            status_code=400,
        )
    return normalized


def _generate_cookie_token() -> str:
    return secrets.token_urlsafe(32)


def hash_referral_attribution_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def build_masked_code_prefix(code: str | None) -> str:
    normalized = (code or "").strip().upper()
    return normalized[:4]


def _mask_code(code: str | None) -> str:
    prefix = build_masked_code_prefix(code)
    return f"{prefix}****" if prefix else "****"


def _sanitize_campaign_params(raw_params: dict[str, Any] | None) -> dict[str, str]:
    if not raw_params:
        return {}

    cleaned: dict[str, str] = {}
    for key, value in raw_params.items():
        normalized_key = str(key).strip()
        if not _CAMPAIGN_KEY_RE.fullmatch(normalized_key):
            continue
        if value is None:
            continue
        cleaned[normalized_key] = str(value).strip()[:160]
        if len(cleaned) >= 24:
            break
    return cleaned


def _campaign_value(campaign: dict[str, str], key: str) -> str | None:
    value = campaign.get(key)
    return value[:120] if value else None


def _clamp_optional(value: str | None, max_length: int) -> str | None:
    normalized = value.strip() if value else None
    if not normalized:
        return None
    return normalized[:max_length]


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
