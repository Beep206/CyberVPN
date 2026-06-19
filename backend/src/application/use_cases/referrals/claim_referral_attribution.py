"""Persist first-touch referral attribution for newly onboarded users."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.growth_codes.resolve_code import ResolveGrowthCodeUseCase
from src.domain.enums import (
    CommercialOwnerType,
    GrowthCodeActionContext,
    GrowthCodeRejectReason,
    GrowthCodeType,
)
from src.domain.exceptions import UserNotFoundError
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.customer_commercial_binding_repo import (
    CustomerCommercialBindingRepository,
)

REFERRAL_ATTRIBUTION_CLAIM_WINDOW = timedelta(days=7)
REFERRAL_CODE_PATTERN = re.compile(r"^[A-Z0-9_-]{4,12}$")
REFERRAL_CLAIM_SURFACE = "web_signup_referral"
PARTNER_FLOW_OWNER_TYPES = {
    CommercialOwnerType.AFFILIATE.value,
    CommercialOwnerType.PERFORMANCE.value,
    CommercialOwnerType.RESELLER.value,
}

ReferralAttributionClaimStatus = Literal["claimed", "already_claimed"]


@dataclass(frozen=True, slots=True)
class ReferralAttributionClaimResult:
    status: ReferralAttributionClaimStatus
    referral_code: str | None
    referrer_user_id: UUID


class ReferralAttributionError(Exception):
    """Base error carrying a stable API-safe reason code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ReferralAttributionInvalidCodeError(ReferralAttributionError):
    def __init__(self) -> None:
        super().__init__(
            "REFERRAL_CODE_INVALID",
            "Referral code has an invalid format",
        )


class ReferralAttributionUnavailableError(ReferralAttributionError):
    def __init__(self) -> None:
        super().__init__(
            "REFERRAL_CODE_UNAVAILABLE",
            "Referral code is unavailable",
        )


class ReferralAttributionSelfReferralError(ReferralAttributionError):
    def __init__(self) -> None:
        super().__init__(
            "REFERRAL_SELF_ATTRIBUTION_BLOCKED",
            "Self-referral is not allowed",
        )


class ReferralAttributionPartnerConflictError(ReferralAttributionError):
    def __init__(self) -> None:
        super().__init__(
            "REFERRAL_PARTNER_ATTRIBUTION_CONFLICT",
            "Referral attribution conflicts with an existing partner attribution",
        )


class ReferralAttributionWindowExpiredError(ReferralAttributionError):
    def __init__(self) -> None:
        super().__init__(
            "REFERRAL_ATTRIBUTION_WINDOW_EXPIRED",
            "Referral attribution is only available during account onboarding",
        )


def normalize_referral_code(value: str | None) -> str:
    normalized = (value or "").strip().upper()
    if not REFERRAL_CODE_PATTERN.fullmatch(normalized):
        raise ReferralAttributionInvalidCodeError()
    return normalized


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class ClaimReferralAttributionUseCase:
    """Bind a referral exactly once, under a row lock, after authentication.

    The browser-side attribution value is deliberately treated as untrusted.
    This use case resolves it against canonical growth-code policy, blocks
    partner/self conflicts, and never overwrites an existing referral binding.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        resolver: ResolveGrowthCodeUseCase | None = None,
        binding_repo: CustomerCommercialBindingRepository | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._resolver = resolver or ResolveGrowthCodeUseCase(session)
        self._bindings = binding_repo or CustomerCommercialBindingRepository(session)
        self._clock = clock or (lambda: datetime.now(UTC))

    async def execute(
        self,
        *,
        user_id: UUID,
        referral_code: str,
    ) -> ReferralAttributionClaimResult:
        normalized_code = normalize_referral_code(referral_code)
        user = await self._get_locked_user(user_id)

        if user.referred_by_user_id is not None:
            existing_referrer = await self._session.get(
                MobileUserModel,
                user.referred_by_user_id,
            )
            return ReferralAttributionClaimResult(
                status="already_claimed",
                referral_code=(existing_referrer.referral_code if existing_referrer else None),
                referrer_user_id=user.referred_by_user_id,
            )

        await self._assert_onboarding_window(user)
        await self._assert_no_partner_attribution(user)

        outcome = await self._resolver.execute(
            code=normalized_code,
            action_context=GrowthCodeActionContext.SIGNUP,
            user_id=user_id,
            surface=REFERRAL_CLAIM_SURFACE,
        )

        if (
            outcome.reject_reason == GrowthCodeRejectReason.CODE_BLOCKED_BY_RISK
            and outcome.resolved_code_id == user_id
        ):
            raise ReferralAttributionSelfReferralError()

        if outcome.reject_reason in {
            GrowthCodeRejectReason.CODE_CONFLICTS_WITH_PARTNER_BINDING,
            GrowthCodeRejectReason.CODE_CONFLICTS_WITH_PARTNER_CODE,
        }:
            raise ReferralAttributionPartnerConflictError()

        if (
            not outcome.accepted
            or outcome.code_type != GrowthCodeType.REFERRAL
            or outcome.resolved_code_id is None
        ):
            raise ReferralAttributionUnavailableError()

        referrer = await self._session.get(MobileUserModel, outcome.resolved_code_id)
        if (
            referrer is None
            or not referrer.is_active
            or referrer.referral_code != normalized_code
        ):
            raise ReferralAttributionUnavailableError()

        if referrer.id == user_id:
            raise ReferralAttributionSelfReferralError()

        user.referred_by_user_id = referrer.id
        await self._session.flush()

        return ReferralAttributionClaimResult(
            status="claimed",
            referral_code=normalized_code,
            referrer_user_id=referrer.id,
        )

    async def _get_locked_user(self, user_id: UUID) -> MobileUserModel:
        result = await self._session.execute(
            select(MobileUserModel)
            .where(MobileUserModel.id == user_id)
            .with_for_update()
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise UserNotFoundError(str(user_id))
        return user

    async def _assert_onboarding_window(self, user: MobileUserModel) -> None:
        created_at = _to_utc(user.created_at)
        admin_user = await self._session.get(AdminUserModel, user.id)
        if admin_user is not None:
            created_at = min(created_at, _to_utc(admin_user.created_at))

        if _to_utc(self._clock()) - created_at > REFERRAL_ATTRIBUTION_CLAIM_WINDOW:
            raise ReferralAttributionWindowExpiredError()

    async def _assert_no_partner_attribution(self, user: MobileUserModel) -> None:
        if user.partner_user_id is not None or user.partner_account_id is not None:
            raise ReferralAttributionPartnerConflictError()

        bindings = await self._bindings.list_active_for_user(
            user_id=user.id,
            storefront_id=None,
        )
        if any(binding.owner_type in PARTNER_FLOW_OWNER_TYPES for binding in bindings):
            raise ReferralAttributionPartnerConflictError()
