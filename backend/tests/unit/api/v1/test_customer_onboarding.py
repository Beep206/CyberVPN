from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.application.services.config_service import CustomerOnboardingRuntimeConfig
from src.application.use_cases.customer_onboarding import (
    CustomerOnboardingFlowTokenService,
    CustomerOnboardingUnavailableError,
)
from src.application.use_cases.growth_codes import GrowthCodeResolutionOutcome
from src.domain.enums import (
    GrowthCodeActionContext,
    GrowthCodeRejectReason,
    GrowthCodeResolutionStatus,
    GrowthCodeType,
    GrowthCodeWrongContextTarget,
)
from src.presentation.api.v1.customer_onboarding import routes
from src.presentation.api.v1.customer_onboarding.schemas import (
    CustomerOnboardingApplyRequest,
    CustomerOnboardingSkipRequest,
)


class StaticConfigService:
    def __init__(self, runtime: CustomerOnboardingRuntimeConfig) -> None:
        self._runtime = runtime

    async def get_customer_onboarding_runtime_config(self) -> CustomerOnboardingRuntimeConfig:
        return self._runtime


def _patch_config(monkeypatch: pytest.MonkeyPatch, runtime: CustomerOnboardingRuntimeConfig) -> None:
    monkeypatch.setattr(routes, "ConfigService", lambda _repo: StaticConfigService(runtime))


def _enabled_runtime() -> CustomerOnboardingRuntimeConfig:
    return CustomerOnboardingRuntimeConfig(
        post_registration_code_prompt_enabled=True,
        web_otp_enabled=True,
        state_store_ready=True,
    )


def _flow_token_service() -> CustomerOnboardingFlowTokenService:
    return CustomerOnboardingFlowTokenService(secret="unit-flow-token-placeholder", clock=lambda: 1_000_000)


def _patch_flow_tokens(monkeypatch: pytest.MonkeyPatch, service: CustomerOnboardingFlowTokenService) -> None:
    monkeypatch.setattr(routes, "CustomerOnboardingFlowTokenService", lambda: service)


class MissingOnboardingStateRepository:
    def __init__(self, _db) -> None:
        pass

    async def apply_growth_code(self, **_kwargs):
        raise CustomerOnboardingUnavailableError(
            code="CUSTOMER_ONBOARDING_STATE_UNAVAILABLE",
            message_key="onboarding.state_unavailable",
        )

    async def skip(self, **_kwargs):
        raise CustomerOnboardingUnavailableError(
            code="CUSTOMER_ONBOARDING_STATE_UNAVAILABLE",
            message_key="onboarding.state_unavailable",
        )


@pytest.mark.asyncio
async def test_current_onboarding_reports_disabled_without_placeholder_state(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_config(monkeypatch, CustomerOnboardingRuntimeConfig())

    response = await routes.get_current_customer_onboarding(user_id=uuid4(), db=AsyncMock())

    assert response.required is False
    assert response.status == "disabled"
    assert response.server_state_available is False
    assert response.message_key == "onboarding.disabled"


@pytest.mark.asyncio
async def test_apply_onboarding_code_is_noop_when_onboarding_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    _patch_config(monkeypatch, CustomerOnboardingRuntimeConfig())

    response = await routes.apply_customer_onboarding_growth_code(
        payload=CustomerOnboardingApplyRequest(code="SAVE20", idempotency_key="request-1"),
        user_id=uuid4(),
        db=db,
    )

    assert response.status == "skipped"
    assert response.message_key == "onboarding.disabled"
    assert response.next_destination == "/dashboard"
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_apply_onboarding_code_fails_closed_when_state_store_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    _patch_config(
        monkeypatch,
        CustomerOnboardingRuntimeConfig(
            post_registration_code_prompt_enabled=True,
            web_otp_enabled=True,
            state_store_ready=False,
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        await routes.apply_customer_onboarding_growth_code(
            payload=CustomerOnboardingApplyRequest(code="SAVE20", idempotency_key="request-1"),
            user_id=uuid4(),
            db=db,
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == {
        "code": "CUSTOMER_ONBOARDING_STATE_UNAVAILABLE",
        "message_key": "onboarding.state_unavailable",
    }
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_onboarding_code_applier_redeems_invite_with_canonical_use_case(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved_code_id = uuid4()
    growth_code_id = uuid4()
    redemption_id = uuid4()
    entitlement_grant_id = uuid4()
    calls: list[tuple[str, str]] = []

    class FakeResolver:
        def __init__(self, _session) -> None:
            pass

        async def execute(self, **kwargs):
            calls.append(("resolve", kwargs["code"]))
            assert kwargs["action_context"] == GrowthCodeActionContext.REDEEM
            assert kwargs["surface"] == "customer_onboarding"
            return GrowthCodeResolutionOutcome(
                accepted=True,
                code_type=GrowthCodeType.INVITE,
                action_context=GrowthCodeActionContext.REDEEM,
                result=GrowthCodeResolutionStatus.ACCEPTED,
                user_message_key="growth_codes.invite.accepted",
                resolved_code_id=resolved_code_id,
                growth_code_id=growth_code_id,
            )

    class FakeInviteRedeemer:
        def __init__(self, _session) -> None:
            pass

        async def execute(self, **kwargs):
            calls.append(("invite", kwargs["code"]))
            return SimpleNamespace(
                redemption=SimpleNamespace(id=redemption_id),
                entitlement_grant_id=entitlement_grant_id,
                entitlement_snapshot={"duration_days": 7},
            )

    class UnexpectedGiftRedeemer:
        def __init__(self, _session) -> None:
            pass

        async def execute(self, **_kwargs):
            raise AssertionError("gift redeemer must not be used for invite codes")

    monkeypatch.setattr(routes, "ResolveGrowthCodeUseCase", FakeResolver)
    monkeypatch.setattr(routes, "RedeemInviteUseCase", FakeInviteRedeemer)
    monkeypatch.setattr(routes, "RedeemGiftCodeUseCase", UnexpectedGiftRedeemer)

    result = await routes.CustomerOnboardingGrowthCodeApplier(
        AsyncMock(),
        current_realm=SimpleNamespace(realm_id=str(uuid4())),
    ).apply_code(
        code="INVITE7",
        user_id=uuid4(),
        idempotency_key="request-1",
        normalized_code_hash="hash",
        masked_code="INVI...E7",
    )

    assert calls == [("resolve", "INVITE7"), ("invite", "INVITE7")]
    assert result.result == "accepted"
    assert result.code_type == "invite"
    assert result.message_key == "growth_codes.invite.accepted"
    assert result.resolved_code_id == resolved_code_id
    assert result.growth_code_id == growth_code_id
    assert result.redemption_id == redemption_id
    assert result.entitlement_grant_id == entitlement_grant_id
    assert result.entitlement_snapshot == {"duration_days": 7}


@pytest.mark.asyncio
async def test_onboarding_code_applier_redeems_gift_with_canonical_use_case(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved_code_id = uuid4()
    growth_code_id = uuid4()
    redemption_id = uuid4()
    entitlement_grant_id = uuid4()
    calls: list[tuple[str, str]] = []

    class FakeResolver:
        def __init__(self, _session) -> None:
            pass

        async def execute(self, **kwargs):
            calls.append(("resolve", kwargs["code"]))
            return GrowthCodeResolutionOutcome(
                accepted=True,
                code_type=GrowthCodeType.GIFT,
                action_context=GrowthCodeActionContext.REDEEM,
                result=GrowthCodeResolutionStatus.ACCEPTED,
                user_message_key="growth_codes.gift.accepted",
                resolved_code_id=resolved_code_id,
                growth_code_id=growth_code_id,
            )

    class UnexpectedInviteRedeemer:
        def __init__(self, _session) -> None:
            pass

        async def execute(self, **_kwargs):
            raise AssertionError("invite redeemer must not be used for gift codes")

    class FakeGiftRedeemer:
        def __init__(self, _session) -> None:
            pass

        async def execute(self, **kwargs):
            calls.append(("gift", kwargs["code"]))
            return SimpleNamespace(
                redemption=SimpleNamespace(id=redemption_id),
                entitlement_grant_id=entitlement_grant_id,
                entitlement_snapshot={"plan_family": "premium"},
            )

    monkeypatch.setattr(routes, "ResolveGrowthCodeUseCase", FakeResolver)
    monkeypatch.setattr(routes, "RedeemInviteUseCase", UnexpectedInviteRedeemer)
    monkeypatch.setattr(routes, "RedeemGiftCodeUseCase", FakeGiftRedeemer)

    result = await routes.CustomerOnboardingGrowthCodeApplier(
        AsyncMock(),
        current_realm=SimpleNamespace(realm_id=str(uuid4())),
    ).apply_code(
        code="GIFT7",
        user_id=uuid4(),
        idempotency_key="request-1",
        normalized_code_hash="hash",
        masked_code="GIFT...T7",
    )

    assert calls == [("resolve", "GIFT7"), ("gift", "GIFT7")]
    assert result.result == "accepted"
    assert result.code_type == "gift"
    assert result.message_key == "growth_codes.gift.accepted"
    assert result.resolved_code_id == resolved_code_id
    assert result.growth_code_id == growth_code_id
    assert result.redemption_id == redemption_id
    assert result.entitlement_grant_id == entitlement_grant_id
    assert result.entitlement_snapshot == {"plan_family": "premium"}


@pytest.mark.asyncio
async def test_onboarding_code_applier_stages_promo_without_redeeming(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved_code_id = uuid4()
    growth_code_id = uuid4()

    class FakeResolver:
        def __init__(self, _session) -> None:
            pass

        async def execute(self, **_kwargs):
            return GrowthCodeResolutionOutcome(
                accepted=False,
                code_type=GrowthCodeType.PROMO,
                action_context=GrowthCodeActionContext.REDEEM,
                result=GrowthCodeResolutionStatus.REJECTED,
                reject_reason=GrowthCodeRejectReason.CODE_WRONG_CONTEXT,
                wrong_context_target=GrowthCodeWrongContextTarget.CHECKOUT,
                user_message_key="growth_codes.promo.checkout_required",
                resolved_code_id=resolved_code_id,
                growth_code_id=growth_code_id,
            )

    class UnexpectedRedeemer:
        def __init__(self, _session) -> None:
            pass

        async def execute(self, **_kwargs):
            raise AssertionError("promo onboarding must not redeem codes")

    monkeypatch.setattr(routes, "ResolveGrowthCodeUseCase", FakeResolver)
    monkeypatch.setattr(routes, "RedeemInviteUseCase", UnexpectedRedeemer)
    monkeypatch.setattr(routes, "RedeemGiftCodeUseCase", UnexpectedRedeemer)

    result = await routes.CustomerOnboardingGrowthCodeApplier(
        AsyncMock(),
        current_realm=SimpleNamespace(realm_id=str(uuid4())),
    ).apply_code(
        code="PROMO10",
        user_id=uuid4(),
        idempotency_key="request-1",
        normalized_code_hash="hash",
        masked_code="PROM...10",
    )

    assert result.result == "staged"
    assert result.code_type == "promo"
    assert result.message_key == "growth_codes.promo.checkout_required"
    assert result.next_destination == "/subscriptions"
    assert result.safe_details == {"wrong_context_target": "checkout"}


@pytest.mark.asyncio
async def test_onboarding_code_applier_rejects_unknown_code_with_stable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResolver:
        def __init__(self, _session) -> None:
            pass

        async def execute(self, **_kwargs):
            return GrowthCodeResolutionOutcome(
                accepted=False,
                code_type=None,
                action_context=GrowthCodeActionContext.REDEEM,
                result=GrowthCodeResolutionStatus.REJECTED,
                reject_reason=GrowthCodeRejectReason.CODE_NOT_FOUND,
                user_message_key="growth_codes.code.not_found",
            )

    monkeypatch.setattr(routes, "ResolveGrowthCodeUseCase", FakeResolver)

    with pytest.raises(CustomerOnboardingUnavailableError) as exc_info:
        await routes.CustomerOnboardingGrowthCodeApplier(
            AsyncMock(),
            current_realm=SimpleNamespace(realm_id=str(uuid4())),
        ).apply_code(
            code="UNKNOWN",
            user_id=uuid4(),
            idempotency_key="request-1",
            normalized_code_hash="hash",
            masked_code="UNKN...WN",
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "CUSTOMER_ONBOARDING_CODE_NOT_FOUND"
    assert exc_info.value.message_key == "growth_codes.code.not_found"


@pytest.mark.asyncio
async def test_apply_onboarding_code_requires_flow_token_when_runtime_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    _patch_config(monkeypatch, _enabled_runtime())
    _patch_flow_tokens(monkeypatch, _flow_token_service())

    with pytest.raises(HTTPException) as exc_info:
        await routes.apply_customer_onboarding_growth_code(
            payload=CustomerOnboardingApplyRequest(code="SAVE20", idempotency_key="request-1"),
            user_id=uuid4(),
            db=db,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == {
        "code": "CUSTOMER_ONBOARDING_FLOW_TOKEN_REQUIRED",
        "message_key": "onboarding.flow_token.required",
    }
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_apply_onboarding_code_does_not_succeed_without_state_repo_even_with_signed_flow_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    user_id = uuid4()
    runtime = _enabled_runtime()
    flow_tokens = _flow_token_service()
    flow_token = flow_tokens.issue(user_id=user_id, flow_key=runtime.flow_key, version=runtime.version)
    _patch_config(monkeypatch, runtime)
    _patch_flow_tokens(monkeypatch, flow_tokens)
    monkeypatch.setattr(routes, "CustomerOnboardingStateSqlAlchemyRepository", MissingOnboardingStateRepository)

    with pytest.raises(HTTPException) as exc_info:
        await routes.apply_customer_onboarding_growth_code(
            payload=CustomerOnboardingApplyRequest(
                code="SAVE20",
                flow_token=flow_token,
                idempotency_key="request-1",
            ),
            user_id=user_id,
            db=db,
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == {
        "code": "CUSTOMER_ONBOARDING_STATE_UNAVAILABLE",
        "message_key": "onboarding.state_unavailable",
    }
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_skip_onboarding_code_fails_closed_when_state_store_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    _patch_config(
        monkeypatch,
        CustomerOnboardingRuntimeConfig(
            post_registration_code_prompt_enabled=True,
            web_otp_enabled=True,
            state_store_ready=False,
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        await routes.skip_customer_onboarding_growth_code(
            payload=CustomerOnboardingSkipRequest(idempotency_key="request-1"),
            user_id=uuid4(),
            db=db,
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "CUSTOMER_ONBOARDING_STATE_UNAVAILABLE"
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_skip_onboarding_code_is_noop_when_onboarding_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    _patch_config(monkeypatch, CustomerOnboardingRuntimeConfig())

    response = await routes.skip_customer_onboarding_growth_code(
        payload=CustomerOnboardingSkipRequest(idempotency_key="request-1"),
        user_id=uuid4(),
        db=db,
    )

    assert response.status == "skipped"
    assert response.message_key == "onboarding.disabled"
    assert response.next_destination == "/dashboard"
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_skip_onboarding_code_requires_flow_token_when_runtime_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    _patch_config(monkeypatch, _enabled_runtime())
    _patch_flow_tokens(monkeypatch, _flow_token_service())

    with pytest.raises(HTTPException) as exc_info:
        await routes.skip_customer_onboarding_growth_code(
            payload=CustomerOnboardingSkipRequest(idempotency_key="request-1"),
            user_id=uuid4(),
            db=db,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == {
        "code": "CUSTOMER_ONBOARDING_FLOW_TOKEN_REQUIRED",
        "message_key": "onboarding.flow_token.required",
    }
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_skip_onboarding_code_does_not_succeed_without_state_repo_even_with_signed_flow_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    user_id = uuid4()
    runtime = _enabled_runtime()
    flow_tokens = _flow_token_service()
    flow_token = flow_tokens.issue(user_id=user_id, flow_key=runtime.flow_key, version=runtime.version)
    _patch_config(monkeypatch, runtime)
    _patch_flow_tokens(monkeypatch, flow_tokens)
    monkeypatch.setattr(routes, "CustomerOnboardingStateSqlAlchemyRepository", MissingOnboardingStateRepository)

    with pytest.raises(HTTPException) as exc_info:
        await routes.skip_customer_onboarding_growth_code(
            payload=CustomerOnboardingSkipRequest(flow_token=flow_token, idempotency_key="request-1"),
            user_id=user_id,
            db=db,
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == {
        "code": "CUSTOMER_ONBOARDING_STATE_UNAVAILABLE",
        "message_key": "onboarding.state_unavailable",
    }
    db.commit.assert_not_awaited()
