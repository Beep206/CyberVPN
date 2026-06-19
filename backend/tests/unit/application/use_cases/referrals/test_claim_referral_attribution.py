from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from src.application.use_cases.growth_codes.resolve_code import GrowthCodeResolutionOutcome
from src.application.use_cases.referrals.claim_referral_attribution import (
    ClaimReferralAttributionUseCase,
    ReferralAttributionPartnerConflictError,
    ReferralAttributionSelfReferralError,
    ReferralAttributionUnavailableError,
    ReferralAttributionWindowExpiredError,
)
from src.domain.enums import (
    GrowthCodeActionContext,
    GrowthCodeRejectReason,
    GrowthCodeResolutionStatus,
    GrowthCodeType,
)
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel

NOW = datetime(2026, 6, 19, 12, 0, tzinfo=UTC)


class _ScalarResult:
    def __init__(self, value: MobileUserModel | None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> MobileUserModel | None:
        return self._value


class _FakeSession:
    def __init__(
        self,
        locked_user: MobileUserModel | None,
        *,
        mobile_users: dict[UUID, MobileUserModel] | None = None,
        admin_user: object | None = None,
    ) -> None:
        self.locked_user = locked_user
        self.mobile_users = mobile_users or {}
        self.admin_user = admin_user
        self.flush_calls = 0

    async def execute(self, _statement) -> _ScalarResult:
        return _ScalarResult(self.locked_user)

    async def get(self, model, identity):
        if model is AdminUserModel:
            return self.admin_user
        if model is MobileUserModel:
            return self.mobile_users.get(identity)
        return None

    async def flush(self) -> None:
        self.flush_calls += 1


def _mobile_user(
    *,
    user_id: UUID | None = None,
    code: str | None = None,
    created_at: datetime = NOW,
    referred_by_user_id: UUID | None = None,
    partner_user_id: UUID | None = None,
) -> MobileUserModel:
    resolved_id = user_id or uuid4()
    return MobileUserModel(
        id=resolved_id,
        public_uid=10_000_000 + (resolved_id.int % 80_000_000),
        email=f"{resolved_id.hex}@example.com",
        password_hash="not-used-in-this-unit-test",
        referral_code=code,
        referred_by_user_id=referred_by_user_id,
        partner_user_id=partner_user_id,
        is_active=True,
        status="active",
        created_at=created_at,
        updated_at=created_at,
    )


def _accepted_referral(referrer_id: UUID) -> GrowthCodeResolutionOutcome:
    return GrowthCodeResolutionOutcome(
        accepted=True,
        code_type=GrowthCodeType.REFERRAL,
        action_context=GrowthCodeActionContext.SIGNUP,
        result=GrowthCodeResolutionStatus.ACCEPTED,
        user_message_key="growth_codes.referral.accepted",
        resolved_code_id=referrer_id,
    )


def _use_case(
    session: _FakeSession,
    *,
    outcome: GrowthCodeResolutionOutcome | None = None,
    bindings: list[object] | None = None,
):
    resolver = SimpleNamespace(
        execute=AsyncMock(return_value=outcome),
    )
    binding_repo = SimpleNamespace(
        list_active_for_user=AsyncMock(return_value=bindings or []),
    )
    use_case = ClaimReferralAttributionUseCase(
        session,  # type: ignore[arg-type]
        resolver=resolver,  # type: ignore[arg-type]
        binding_repo=binding_repo,  # type: ignore[arg-type]
        clock=lambda: NOW,
    )
    return use_case, resolver, binding_repo


@pytest.mark.asyncio
async def test_claims_referral_once_under_locked_user_row() -> None:
    referred_user = _mobile_user()
    referrer = _mobile_user(code="XSK2SAQE")
    session = _FakeSession(
        referred_user,
        mobile_users={referrer.id: referrer},
    )
    use_case, resolver, _binding_repo = _use_case(
        session,
        outcome=_accepted_referral(referrer.id),
    )

    result = await use_case.execute(
        user_id=referred_user.id,
        referral_code="xsk2saqe",
    )

    assert result.status == "claimed"
    assert result.referral_code == "XSK2SAQE"
    assert result.referrer_user_id == referrer.id
    assert referred_user.referred_by_user_id == referrer.id
    assert session.flush_calls == 1
    resolver.execute.assert_awaited_once_with(
        code="XSK2SAQE",
        action_context=GrowthCodeActionContext.SIGNUP,
        user_id=referred_user.id,
        surface="web_signup_referral",
    )


@pytest.mark.asyncio
async def test_existing_referral_is_idempotent_and_never_overwritten() -> None:
    existing_referrer = _mobile_user(code="FIRST123")
    referred_user = _mobile_user(referred_by_user_id=existing_referrer.id)
    session = _FakeSession(
        referred_user,
        mobile_users={existing_referrer.id: existing_referrer},
    )
    use_case, resolver, binding_repo = _use_case(session)

    result = await use_case.execute(
        user_id=referred_user.id,
        referral_code="SECOND45",
    )

    assert result.status == "already_claimed"
    assert result.referral_code == "FIRST123"
    assert result.referrer_user_id == existing_referrer.id
    assert referred_user.referred_by_user_id == existing_referrer.id
    assert session.flush_calls == 0
    resolver.execute.assert_not_awaited()
    binding_repo.list_active_for_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_blocks_self_referral() -> None:
    referred_user = _mobile_user(code="SELF1234")
    session = _FakeSession(
        referred_user,
        mobile_users={referred_user.id: referred_user},
    )
    outcome = GrowthCodeResolutionOutcome(
        accepted=False,
        code_type=GrowthCodeType.REFERRAL,
        action_context=GrowthCodeActionContext.SIGNUP,
        result=GrowthCodeResolutionStatus.BLOCKED_BY_RISK,
        reject_reason=GrowthCodeRejectReason.CODE_BLOCKED_BY_RISK,
        user_message_key="growth_codes.referral.self_referral_blocked",
        resolved_code_id=referred_user.id,
    )
    use_case, _resolver, _binding_repo = _use_case(session, outcome=outcome)

    with pytest.raises(ReferralAttributionSelfReferralError):
        await use_case.execute(
            user_id=referred_user.id,
            referral_code="SELF1234",
        )

    assert referred_user.referred_by_user_id is None
    assert session.flush_calls == 0


@pytest.mark.asyncio
async def test_blocks_existing_partner_attribution_before_resolution() -> None:
    referred_user = _mobile_user(partner_user_id=uuid4())
    session = _FakeSession(referred_user)
    use_case, resolver, _binding_repo = _use_case(session)

    with pytest.raises(ReferralAttributionPartnerConflictError):
        await use_case.execute(
            user_id=referred_user.id,
            referral_code="XSK2SAQE",
        )

    resolver.execute.assert_not_awaited()
    assert session.flush_calls == 0


@pytest.mark.asyncio
async def test_blocks_claim_after_onboarding_window() -> None:
    referred_user = _mobile_user(created_at=NOW)
    session = _FakeSession(
        referred_user,
        admin_user=SimpleNamespace(created_at=NOW - timedelta(days=8)),
    )
    use_case, resolver, _binding_repo = _use_case(session)

    with pytest.raises(ReferralAttributionWindowExpiredError):
        await use_case.execute(
            user_id=referred_user.id,
            referral_code="XSK2SAQE",
        )

    resolver.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_rejects_non_referral_growth_code() -> None:
    referred_user = _mobile_user()
    session = _FakeSession(referred_user)
    outcome = GrowthCodeResolutionOutcome(
        accepted=True,
        code_type=GrowthCodeType.INVITE,
        action_context=GrowthCodeActionContext.SIGNUP,
        result=GrowthCodeResolutionStatus.ACCEPTED,
        user_message_key="growth_codes.invite.accepted",
        resolved_code_id=uuid4(),
    )
    use_case, _resolver, _binding_repo = _use_case(session, outcome=outcome)

    with pytest.raises(ReferralAttributionUnavailableError):
        await use_case.execute(
            user_id=referred_user.id,
            referral_code="INVITE12",
        )
