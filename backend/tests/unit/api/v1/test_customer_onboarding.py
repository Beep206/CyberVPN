from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request, Response
from prometheus_client import REGISTRY, generate_latest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.config_service import CustomerOnboardingRuntimeConfig
from src.application.use_cases.customer_onboarding import (
    CustomerConnectionMarkResult,
    CustomerOnboardingApplyResult,
    CustomerOnboardingConnectionBootstrapUseCase,
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
    CustomerOnboardingPreviewRequest,
    CustomerOnboardingSkipRequest,
    MarkOnboardingConnectionConnectedRequest,
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
        telegram_bot_code_apply_enabled=True,
    )


def _flow_token_service() -> CustomerOnboardingFlowTokenService:
    return CustomerOnboardingFlowTokenService(secret="unit-flow-token-placeholder", clock=lambda: 1_000_000)


class _ScalarResult:
    def __init__(self, value: object | None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object | None:
        return self._value

    def scalars(self):
        return self

    def all(self) -> list[object]:
        return [] if self._value is None else [self._value]


class _IdentityDb:
    def __init__(self, reconciliation: object | None) -> None:
        self._reconciliation = reconciliation

    async def execute(self, _statement) -> _ScalarResult:
        return _ScalarResult(self._reconciliation)


def _patch_flow_tokens(monkeypatch: pytest.MonkeyPatch, service: CustomerOnboardingFlowTokenService) -> None:
    monkeypatch.setattr(routes, "CustomerOnboardingFlowTokenService", lambda: service)


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/customer/onboarding/growth-code/apply",
            "headers": [(b"x-device-id", b"customer-onboarding-unit")],
            "client": ("198.51.100.10", 443),
            "server": ("testserver", 443),
            "scheme": "https",
        }
    )


@asynccontextmanager
async def _nested_transaction():
    yield


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
        request=_request(),
        user_id=uuid4(),
        db=db,
    )

    assert response.status == "skipped"
    assert response.message_key == "onboarding.disabled"
    assert response.next_destination == "/dashboard"
    db.commit.assert_not_awaited()
    metric_payload = generate_latest(REGISTRY).decode()
    assert "customer_onboarding_apply_total" in metric_payload
    assert 'status="skipped"' in metric_payload
    assert 'code_type="unknown"' in metric_payload


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
            request=_request(),
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
    gift_provisioning_gateway = object()

    async def provision_gift(*, db, user_id, result, provisioning_gateway):
        assert db is session
        assert result.entitlement_grant_id == entitlement_grant_id
        assert provisioning_gateway is gift_provisioning_gateway
        calls.append(("provision", str(user_id)))

    monkeypatch.setattr(routes, "provision_redeemed_gift_access", provision_gift)
    session = AsyncMock()
    session.begin_nested = _nested_transaction
    user_id = uuid4()

    result = await routes.CustomerOnboardingGrowthCodeApplier(
        session,
        current_realm=SimpleNamespace(realm_id=str(uuid4())),
        gift_provisioning_gateway=gift_provisioning_gateway,
    ).apply_code(
        code="GIFT7",
        user_id=user_id,
        idempotency_key="request-1",
        normalized_code_hash="hash",
        masked_code="GIFT...T7",
    )

    assert calls == [("resolve", "GIFT7"), ("gift", "GIFT7"), ("provision", str(user_id))]
    assert result.result == "accepted"
    assert result.code_type == "gift"
    assert result.message_key == "growth_codes.gift.accepted"
    assert result.resolved_code_id == resolved_code_id
    assert result.growth_code_id == growth_code_id
    assert result.redemption_id == redemption_id
    assert result.entitlement_grant_id == entitlement_grant_id
    assert result.entitlement_snapshot == {"plan_family": "premium"}


@pytest.mark.asyncio
async def test_onboarding_gift_fails_before_redeem_without_provisioning_gateway(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResolver:
        def __init__(self, _session) -> None:
            pass

        async def execute(self, **_kwargs):
            return GrowthCodeResolutionOutcome(
                accepted=True,
                code_type=GrowthCodeType.GIFT,
                action_context=GrowthCodeActionContext.REDEEM,
                result=GrowthCodeResolutionStatus.ACCEPTED,
                user_message_key="growth_codes.gift.accepted",
                resolved_code_id=uuid4(),
                growth_code_id=uuid4(),
            )

    class UnexpectedGiftRedeemer:
        def __init__(self, _session) -> None:
            pass

        async def execute(self, **_kwargs):
            raise AssertionError("disabled provisioning must be rejected before gift redemption")

    monkeypatch.setattr(routes, "ResolveGrowthCodeUseCase", FakeResolver)
    monkeypatch.setattr(routes, "RedeemGiftCodeUseCase", UnexpectedGiftRedeemer)

    with pytest.raises(HTTPException) as exc_info:
        await routes.CustomerOnboardingGrowthCodeApplier(
            AsyncMock(),
            current_realm=SimpleNamespace(realm_id=str(uuid4())),
            gift_provisioning_gateway=None,
        ).apply_code(
            code="GIFT-NO-PROVISIONING",
            user_id=uuid4(),
            idempotency_key="request-1",
            normalized_code_hash="hash",
            masked_code="GIFT...ING",
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Gift VPN provisioning is unavailable"


@pytest.mark.asyncio
async def test_onboarding_gift_business_error_rolls_back_redeemer_savepoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class SavepointDb:
        def __init__(self) -> None:
            self.working: list[str] = []

        def begin_nested(self):
            @asynccontextmanager
            async def savepoint():
                snapshot = list(self.working)
                try:
                    yield
                except Exception:
                    self.working = snapshot
                    raise

            return savepoint()

    db = SavepointDb()

    class FakeResolver:
        def __init__(self, _session) -> None:
            pass

        async def execute(self, **_kwargs):
            return GrowthCodeResolutionOutcome(
                accepted=True,
                code_type=GrowthCodeType.GIFT,
                action_context=GrowthCodeActionContext.REDEEM,
                result=GrowthCodeResolutionStatus.ACCEPTED,
                user_message_key="growth_codes.gift.accepted",
                resolved_code_id=uuid4(),
                growth_code_id=uuid4(),
            )

    class FailingGiftRedeemer:
        def __init__(self, session) -> None:
            self._session = session

        async def execute(self, **_kwargs):
            self._session.working.extend(["redemption", "grant", "outbox", "pending_identity"])
            raise ValueError("Gift code already redeemed")

    monkeypatch.setattr(routes, "ResolveGrowthCodeUseCase", FakeResolver)
    monkeypatch.setattr(routes, "RedeemGiftCodeUseCase", FailingGiftRedeemer)

    with pytest.raises(CustomerOnboardingUnavailableError) as exc_info:
        await routes.CustomerOnboardingGrowthCodeApplier(
            cast(AsyncSession, db),
            current_realm=SimpleNamespace(realm_id=str(uuid4())),
            gift_provisioning_gateway=object(),
        ).apply_code(
            code="GIFT-BUSINESS-ERROR",
            user_id=uuid4(),
            idempotency_key="request-1",
            normalized_code_hash="hash",
            masked_code="GIFT...ROR",
        )

    assert exc_info.value.code == "CUSTOMER_ONBOARDING_CODE_ALREADY_REDEEMED"
    assert db.working == []


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_stage", ["pre_io_target_rejected", "post_io_mapping_failed"])
async def test_onboarding_gift_provisioning_failure_rolls_back_local_redemption_state(
    monkeypatch: pytest.MonkeyPatch,
    failure_stage: str,
) -> None:
    user_id = uuid4()
    realm = SimpleNamespace(realm_id=str(uuid4()))
    provider_calls = 0

    class TransactionDb:
        def __init__(self) -> None:
            self.working: list[str] = []
            self.committed: list[str] = []
            self.rollback_calls = 0
            self.commit_calls = 0

        async def rollback(self) -> None:
            self.rollback_calls += 1
            self.working.clear()

        async def commit(self) -> None:
            self.commit_calls += 1
            self.committed.extend(self.working)
            self.working.clear()

        def begin_nested(self):
            return _nested_transaction()

    db = TransactionDb()

    class FakeResolver:
        def __init__(self, _session) -> None:
            pass

        async def execute(self, **_kwargs):
            return GrowthCodeResolutionOutcome(
                accepted=True,
                code_type=GrowthCodeType.GIFT,
                action_context=GrowthCodeActionContext.REDEEM,
                result=GrowthCodeResolutionStatus.ACCEPTED,
                user_message_key="growth_codes.gift.accepted",
                resolved_code_id=uuid4(),
                growth_code_id=uuid4(),
            )

    class StagingGiftRedeemer:
        def __init__(self, session) -> None:
            self._session = session

        async def execute(self, **_kwargs):
            self._session.working.extend(["redemption", "grant", "outbox", "pending_identity"])
            return SimpleNamespace(
                redemption=SimpleNamespace(id=uuid4()),
                entitlement_grant_id=uuid4(),
                entitlement_snapshot={"plan_family": "premium"},
            )

    class PassthroughApplyUseCase:
        def __init__(self, **_kwargs) -> None:
            pass

        async def execute(self, *, code_applier, code, user_id, **_kwargs):
            return await code_applier.apply_code(
                code=code,
                user_id=user_id,
                idempotency_key="request-1",
                normalized_code_hash="hash",
                masked_code="GIFT...URE",
            )

    async def resolve_actor(**_kwargs):
        return user_id, realm

    async def fail_provisioning(**_kwargs):
        nonlocal provider_calls
        if failure_stage == "post_io_mapping_failed":
            provider_calls += 1
        raise ValueError(failure_stage)

    _patch_config(monkeypatch, _enabled_runtime())
    monkeypatch.setattr(routes, "_resolve_customer_onboarding_actor", resolve_actor)
    monkeypatch.setattr(routes, "ApplyCustomerOnboardingGrowthCodeUseCase", PassthroughApplyUseCase)
    monkeypatch.setattr(routes, "ResolveGrowthCodeUseCase", FakeResolver)
    monkeypatch.setattr(routes, "RedeemGiftCodeUseCase", StagingGiftRedeemer)
    monkeypatch.setattr(routes, "provision_redeemed_gift_access", fail_provisioning)

    with pytest.raises(ValueError, match=failure_stage):
        await routes.apply_customer_onboarding_growth_code(
            payload=CustomerOnboardingApplyRequest(code="GIFT-FAILURE", idempotency_key="request-1"),
            request=_request(),
            user_id=user_id,
            current_realm=realm,
            db=cast(AsyncSession, db),
            gift_provisioning_gateway=object(),
        )

    assert provider_calls == (1 if failure_stage == "post_io_mapping_failed" else 0)
    assert db.rollback_calls == 1
    assert db.commit_calls == 0
    assert db.working == []
    assert db.committed == []


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
@pytest.mark.parametrize(
    ("code_type", "message_key"),
    (
        (GrowthCodeType.INVITE, "growth_codes.invite.accepted"),
        (GrowthCodeType.GIFT, "growth_codes.gift.accepted"),
    ),
)
async def test_preview_onboarding_code_reports_entitlement_code_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
    code_type: GrowthCodeType,
    message_key: str,
) -> None:
    db = AsyncMock()
    user_id = uuid4()
    runtime = _enabled_runtime()
    flow_tokens = _flow_token_service()
    flow_token = flow_tokens.issue(user_id=user_id, flow_key=runtime.flow_key, version=runtime.version)
    resolver_calls: list[dict] = []
    _patch_config(monkeypatch, runtime)
    _patch_flow_tokens(monkeypatch, flow_tokens)

    class FakeResolver:
        def __init__(self, _session) -> None:
            pass

        async def execute(self, **kwargs):
            resolver_calls.append(kwargs)
            return GrowthCodeResolutionOutcome(
                accepted=True,
                code_type=code_type,
                action_context=GrowthCodeActionContext.REDEEM,
                result=GrowthCodeResolutionStatus.ACCEPTED,
                user_message_key=message_key,
                resolved_code_id=uuid4(),
                growth_code_id=uuid4(),
            )

    monkeypatch.setattr(routes, "ResolveGrowthCodeUseCase", FakeResolver)

    response = await routes.preview_customer_onboarding_growth_code(
        payload=CustomerOnboardingPreviewRequest(code="invite7", flow_token=flow_token),
        user_id=user_id,
        db=db,
    )

    assert response.accepted is True
    assert response.detected_code_type == code_type.value
    assert response.status == "preview_available"
    assert response.next_action == "redeem_entitlement"
    assert response.message_key == message_key
    assert response.matched_code_types == [code_type.value]
    assert resolver_calls[0]["record_event"] is False
    assert resolver_calls[0]["ensure_registry"] is False
    db.commit.assert_not_awaited()
    db.rollback.assert_awaited_once()
    metric_payload = generate_latest(REGISTRY).decode()
    assert "customer_onboarding_preview_total" in metric_payload
    assert 'status="preview_available"' in metric_payload
    assert 'detected_code_type="invite"' in metric_payload


@pytest.mark.asyncio
async def test_preview_onboarding_promo_stages_for_checkout_without_redeeming(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    user_id = uuid4()
    runtime = _enabled_runtime()
    flow_tokens = _flow_token_service()
    flow_token = flow_tokens.issue(user_id=user_id, flow_key=runtime.flow_key, version=runtime.version)
    _patch_config(monkeypatch, runtime)
    _patch_flow_tokens(monkeypatch, flow_tokens)

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
            )

    class UnexpectedRedeemer:
        def __init__(self, _session) -> None:
            pass

        async def execute(self, **_kwargs):
            raise AssertionError("preview must not redeem codes")

    monkeypatch.setattr(routes, "ResolveGrowthCodeUseCase", FakeResolver)
    monkeypatch.setattr(routes, "RedeemInviteUseCase", UnexpectedRedeemer)
    monkeypatch.setattr(routes, "RedeemGiftCodeUseCase", UnexpectedRedeemer)

    response = await routes.preview_customer_onboarding_growth_code(
        payload=CustomerOnboardingPreviewRequest(code="promo10", flow_token=flow_token),
        user_id=user_id,
        db=db,
    )

    assert response.accepted is True
    assert response.detected_code_type == "promo"
    assert response.status == "wrong_context"
    assert response.next_action == "stage_for_checkout"
    assert response.safe_details == {
        "reject_reason": "code_wrong_context",
        "wrong_context_target": "checkout",
    }
    db.commit.assert_not_awaited()
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_preview_onboarding_ambiguous_code_returns_safe_matched_types(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    user_id = uuid4()
    runtime = _enabled_runtime()
    flow_tokens = _flow_token_service()
    flow_token = flow_tokens.issue(user_id=user_id, flow_key=runtime.flow_key, version=runtime.version)
    _patch_config(monkeypatch, runtime)
    _patch_flow_tokens(monkeypatch, flow_tokens)

    class FakeResolver:
        def __init__(self, _session) -> None:
            pass

        async def execute(self, **kwargs):
            assert kwargs["record_event"] is False
            assert kwargs["ensure_registry"] is False
            return GrowthCodeResolutionOutcome(
                accepted=False,
                code_type=None,
                action_context=GrowthCodeActionContext.REDEEM,
                result=GrowthCodeResolutionStatus.CONFLICTED,
                reject_reason=GrowthCodeRejectReason.CODE_NAMESPACE_AMBIGUOUS,
                conflict_code="CODE_NAMESPACE_AMBIGUOUS",
                user_message_key="growth_codes.code.namespace_ambiguous",
                policy_snapshot={
                    "matched_code_types": ["invite", "promo"],
                    "code_hash": "safe-hash",
                    "masked_code": "AMBI...ET",
                },
            )

    monkeypatch.setattr(routes, "ResolveGrowthCodeUseCase", FakeResolver)

    response = await routes.preview_customer_onboarding_growth_code(
        payload=CustomerOnboardingPreviewRequest(code="AMBIGBASKET", flow_token=flow_token),
        user_id=user_id,
        db=db,
    )

    assert response.accepted is False
    assert response.detected_code_type is None
    assert response.status == "ambiguous"
    assert response.next_action == "resolve_ambiguity"
    assert response.matched_code_types == ["invite", "promo"]
    assert response.safe_details == {
        "reject_reason": "code_namespace_ambiguous",
        "conflict_code": "CODE_NAMESPACE_AMBIGUOUS",
    }
    assert "AMBIGBASKET" not in response.model_dump_json()
    db.commit.assert_not_awaited()
    db.rollback.assert_awaited_once()


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
            request=_request(),
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
async def test_telegram_bot_growth_code_apply_matches_backend_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    user_id = uuid4()
    state_calls: list[dict[str, object]] = []
    _patch_config(monkeypatch, _enabled_runtime())

    class RecordingStateRepository:
        def __init__(self, _db) -> None:
            pass

        async def get_current(self, **_kwargs):
            return SimpleNamespace(status="pending")

        async def ensure_pending(self, **_kwargs):
            return SimpleNamespace(status="pending")

        async def apply_growth_code(self, **kwargs):
            state_calls.append(dict(kwargs))
            return CustomerOnboardingApplyResult(
                status="completed",
                message_key="growth_codes.invite.accepted",
                masked_code="GI***42",
                code_type="invite",
                connection_required=True,
            )

    class FakeMobileUserRepository:
        def __init__(self, _db) -> None:
            pass

        async def get_by_telegram_id(self, telegram_id: int):
            assert telegram_id == 123456
            return SimpleNamespace(id=user_id, is_active=True, auth_realm_id=None)

    def require_secret(secret: str | None) -> None:
        assert secret == "telegram-internal-secret"

    async def resolve_realm(_db, mobile_user):
        assert mobile_user.id == user_id
        return SimpleNamespace(auth_realm=SimpleNamespace(id=uuid4()), source="telegram_bot")

    monkeypatch.setattr(routes, "CustomerOnboardingStateSqlAlchemyRepository", RecordingStateRepository)
    monkeypatch.setattr(routes, "MobileUserRepository", FakeMobileUserRepository)
    monkeypatch.setattr(routes, "_require_telegram_bot_secret", require_secret)
    monkeypatch.setattr(routes, "_resolve_customer_realm_for_mobile_user", resolve_realm)

    response = await routes.apply_customer_onboarding_growth_code(
        payload=CustomerOnboardingApplyRequest(
            code="GiftSecret42",
            idempotency_key="tg-code-stable",
            source_surface="telegram_bot",
            telegram_id=123456,
        ),
        request=_request(),
        user_id=None,
        telegram_bot_secret="telegram-internal-secret",
        current_realm=SimpleNamespace(auth_realm=SimpleNamespace(id=uuid4()), source="web"),
        db=db,
    )

    assert response.status == "completed"
    assert response.message_key == "growth_codes.invite.accepted"
    assert response.masked_code == "GI***42"
    assert response.connection_required is True
    assert state_calls
    assert state_calls[0]["user_id"] == user_id
    assert state_calls[0]["normalized_code"] == "GIFTSECRET42"
    assert state_calls[0]["idempotency_key"] == "tg-code-stable"
    db.commit.assert_awaited_once()


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
            request=_request(),
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
    metric_payload = generate_latest(REGISTRY).decode()
    assert "customer_onboarding_skip_total" in metric_payload
    assert 'status="skipped"' in metric_payload


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
    request_key = "request-" + "1"

    with pytest.raises(HTTPException) as exc_info:
        await routes.skip_customer_onboarding_growth_code(
            payload=CustomerOnboardingSkipRequest(flow_token=flow_token, idempotency_key=request_key),
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
async def test_connection_bootstrap_returns_config_and_persists_only_hash_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    user_id = uuid4()
    realm_id = uuid4()
    captured: dict[str, object] = {}
    _patch_config(monkeypatch, _enabled_runtime())

    async def fake_get_mobile_user_or_404(_db, _user_id):
        assert _user_id == user_id
        return SimpleNamespace(
            id=user_id,
            is_active=True,
            remnawave_uuid="provider-user-1",
            telegram_id=None,
            subscription_url=None,
        )

    class FakeEntitlementStateUseCase:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, **kwargs):
            assert kwargs["customer_account_id"] == user_id
            assert kwargs["auth_realm_id"] == realm_id
            return {
                "status": "active",
                "expires_at": "2026-06-28T00:00:00+00:00",
                "effective": {
                    "device_limit": 5,
                    "traffic_limit_bytes": 1_073_741_824,
                },
            }

    async def fake_resolve_connection_config(**_kwargs):
        return routes._ConnectionConfigSnapshot(
            subscription_url="https://sub.example/customer-token",
            config_profile_name="unit_profile",
            service_identity_ready=True,
        )

    class FakeSessionRepo:
        def __init__(self, _db) -> None:
            pass

        async def record_available(self, **kwargs):
            captured.update(kwargs)
            return uuid4()

    monkeypatch.setattr(routes, "_get_mobile_user_or_404", fake_get_mobile_user_or_404)
    monkeypatch.setattr(routes, "GetCurrentEntitlementStateUseCase", FakeEntitlementStateUseCase)
    monkeypatch.setattr(routes, "_resolve_connection_config", fake_resolve_connection_config)
    monkeypatch.setattr(routes, "CustomerConnectionSessionSqlAlchemyRepository", FakeSessionRepo)

    http_response = Response()
    response = await routes.get_customer_onboarding_connection_bootstrap(
        response=http_response,
        surface="web",
        platform_hint="ios",
        user_id=user_id,
        current_realm=SimpleNamespace(auth_realm=SimpleNamespace(id=realm_id)),
        db=db,
        remnawave_client=AsyncMock(),
    )

    assert response.available is True
    assert response.status == "available"
    assert response.subscription_url == "https://sub.example/customer-token"
    assert response.qr_payload == "https://sub.example/customer-token"
    assert response.device_limit == 5
    assert response.traffic_limit_bytes == 1_073_741_824
    assert response.instructions[0].steps[0].title_key.startswith("Auth.onboarding.connection.instructions.")
    assert captured["subscription_config_hash"] != "https://sub.example/customer-token"
    assert "https://sub.example/customer-token" not in str(captured["metadata"])
    assert http_response.headers["Cache-Control"] == "no-store, private"
    db.commit.assert_awaited_once()
    metric_payload = generate_latest(REGISTRY).decode()
    assert "customer_onboarding_connection_bootstrap_total" in metric_payload
    assert 'status="available"' in metric_payload
    assert 'surface="web"' in metric_payload


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "mapped_numeric_id"),
    [
        (None, None),
        ("pending", 42),
        ("mapped", 99),
    ],
)
async def test_connection_config_rejects_unmapped_or_stale_numeric_identity(
    state: str | None,
    mapped_numeric_id: int | None,
) -> None:
    user_id = uuid4()
    legacy_uuid = uuid4()
    reconciliation = (
        SimpleNamespace(
            subject_type="mobile_user",
            subject_id=user_id,
            reconciliation_state=state,
            numeric_user_id=mapped_numeric_id,
            legacy_uuid=str(legacy_uuid),
        )
        if state is not None
        else None
    )
    mobile_user = SimpleNamespace(
        id=user_id,
        remnawave_user_id=42,
        remnawave_uuid=str(legacy_uuid),
        telegram_id=123456,
        subscription_url="https://sub.example/must-not-be-returned",
    )

    with pytest.raises(HTTPException) as exc_info:
        await routes._resolve_connection_config(
            db=_IdentityDb(reconciliation),
            mobile_user=mobile_user,
            user_id=user_id,
            auth_realm_id=uuid4(),
            remnawave_client=AsyncMock(),
        )

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_connection_config_uses_only_exact_numeric_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = uuid4()
    legacy_uuid = uuid4()
    captured: dict[str, object] = {}
    reconciliation = SimpleNamespace(
        subject_type="mobile_user",
        subject_id=user_id,
        reconciliation_state="mapped",
        numeric_user_id=42,
        legacy_uuid=str(legacy_uuid),
    )

    class FakeGenerateConfigUseCase:
        def __init__(self, _client) -> None:
            pass

        async def execute(self, user_ref):
            captured["user_ref"] = user_ref
            return {"subscription_url": "https://sub.example/exact-user"}

    class FakeServiceAccessUseCase:
        def __init__(self, db) -> None:
            captured["sync_db"] = db

        async def sync_current_remnawave_subscription_url(self, **kwargs) -> None:
            captured["sync_kwargs"] = kwargs

    monkeypatch.setattr(routes, "GenerateConfigUseCase", FakeGenerateConfigUseCase)
    monkeypatch.setattr(routes, "CustomerSubscriptionServiceAccessUseCase", FakeServiceAccessUseCase)

    auth_realm_id = uuid4()
    result = await routes._resolve_connection_config(
        db=_IdentityDb(reconciliation),
        mobile_user=SimpleNamespace(
            id=user_id,
            remnawave_user_id=42,
            remnawave_uuid=str(legacy_uuid),
            telegram_id=123456,
            subscription_url=None,
        ),
        user_id=user_id,
        auth_realm_id=auth_realm_id,
        remnawave_client=AsyncMock(),
    )

    assert captured["user_ref"].id == 42
    assert captured["user_ref"].legacy_uuid == legacy_uuid
    assert captured["sync_kwargs"] == {
        "customer_account_id": user_id,
        "auth_realm_id": auth_realm_id,
        "remnawave_ref": captured["user_ref"],
        "subscription_url": "https://sub.example/exact-user",
    }
    assert result.subscription_url == "https://sub.example/exact-user"
    assert result.config_profile_name == "remnawave_subscription"


@pytest.mark.asyncio
async def test_connection_config_does_not_fallback_after_numeric_upstream_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    legacy_uuid = uuid4()
    reconciliation = SimpleNamespace(
        subject_type="mobile_user",
        subject_id=user_id,
        reconciliation_state="mapped",
        numeric_user_id=42,
        legacy_uuid=str(legacy_uuid),
    )

    class MissingGenerateConfigUseCase:
        def __init__(self, _client) -> None:
            pass

        async def execute(self, _user_ref):
            raise HTTPException(status_code=404, detail="not found")

    class ForbiddenSubscriptionFallback:
        def __init__(self, _db) -> None:
            raise AssertionError("entitlement fallback must not run after exact numeric lookup fails")

    monkeypatch.setattr(routes, "GenerateConfigUseCase", MissingGenerateConfigUseCase)
    monkeypatch.setattr(routes, "ListCustomerSubscriptionsUseCase", ForbiddenSubscriptionFallback)

    with pytest.raises(HTTPException) as exc_info:
        await routes._resolve_connection_config(
            db=_IdentityDb(reconciliation),
            mobile_user=SimpleNamespace(
                id=user_id,
                remnawave_user_id=42,
                remnawave_uuid=str(legacy_uuid),
                telegram_id=123456,
                subscription_url="https://sub.example/stale-url",
            ),
            user_id=user_id,
            auth_realm_id=uuid4(),
            remnawave_client=AsyncMock(),
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_connection_config_does_not_return_unmapped_legacy_subscription_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()

    class EmptySubscriptionListUseCase:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, **_kwargs):
            return SimpleNamespace(default_subscription_key=None)

    monkeypatch.setattr(routes, "ListCustomerSubscriptionsUseCase", EmptySubscriptionListUseCase)

    result = await routes._resolve_connection_config(
        db=_IdentityDb(None),
        mobile_user=SimpleNamespace(
            id=user_id,
            remnawave_user_id=None,
            remnawave_uuid=None,
            telegram_id=123456,
            subscription_url="https://sub.example/legacy-must-not-leak",
        ),
        user_id=user_id,
        auth_realm_id=uuid4(),
        remnawave_client=AsyncMock(),
    )

    assert result.subscription_url is None
    assert result.config_profile_name is None
    assert result.service_identity_ready is False


@pytest.mark.asyncio
async def test_connection_bootstrap_does_not_expose_legacy_url_without_active_entitlement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    user_id = uuid4()
    realm_id = uuid4()
    record_available = AsyncMock()
    _patch_config(monkeypatch, _enabled_runtime())

    async def fake_get_mobile_user_or_404(_db, _user_id):
        assert _user_id == user_id
        return SimpleNamespace(
            id=user_id,
            is_active=True,
            remnawave_uuid=None,
            telegram_id=None,
            subscription_url="https://sub.example/legacy-customer-token",
        )

    class FakeEntitlementStateUseCase:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, **kwargs):
            assert kwargs["customer_account_id"] == user_id
            assert kwargs["auth_realm_id"] == realm_id
            return {
                "status": "expired",
                "expires_at": "2026-06-20T00:00:00+00:00",
                "effective": {
                    "device_limit": 5,
                    "traffic_limit_bytes": 1_073_741_824,
                },
            }

    async def fake_resolve_connection_config(**_kwargs):
        return routes._ConnectionConfigSnapshot(
            subscription_url="https://sub.example/legacy-customer-token",
            config_profile_name="legacy_profile",
            service_identity_ready=True,
        )

    class FakeSessionRepo:
        def __init__(self, _db) -> None:
            pass

        async def record_available(self, **kwargs):
            return await record_available(**kwargs)

    monkeypatch.setattr(routes, "_get_mobile_user_or_404", fake_get_mobile_user_or_404)
    monkeypatch.setattr(routes, "GetCurrentEntitlementStateUseCase", FakeEntitlementStateUseCase)
    monkeypatch.setattr(routes, "_resolve_connection_config", fake_resolve_connection_config)
    monkeypatch.setattr(routes, "CustomerConnectionSessionSqlAlchemyRepository", FakeSessionRepo)

    http_response = Response()
    response = await routes.get_customer_onboarding_connection_bootstrap(
        response=http_response,
        surface="web",
        platform_hint="ios",
        user_id=user_id,
        current_realm=SimpleNamespace(auth_realm=SimpleNamespace(id=realm_id)),
        db=db,
        remnawave_client=AsyncMock(),
    )

    assert response.available is False
    assert response.status == "no_active_entitlement"
    assert response.subscription_url is None
    assert response.qr_payload is None
    record_available.assert_not_awaited()
    assert http_response.headers["Cache-Control"] == "no-store, private"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_telegram_connection_bootstrap_use_case_does_not_expose_url_without_entitlement() -> None:
    record_available = AsyncMock()
    runtime = _enabled_runtime()

    class FakeSessionRepo:
        async def record_available(self, **kwargs):
            return await record_available(**kwargs)

    result = await CustomerOnboardingConnectionBootstrapUseCase(
        runtime_config=runtime,
        session_repo=FakeSessionRepo(),
    ).execute(
        user_id=uuid4(),
        surface="telegram_bot",
        platform_hint="android",
        subscription_url="https://sub.example/legacy-telegram-token",
        entitlement_status="none",
        service_identity_ready=True,
    )

    assert result.available is False
    assert result.status == "no_active_entitlement"
    assert result.subscription_url is None
    assert result.qr_payload is None
    assert result.telegram_payload is None
    record_available.assert_not_awaited()


@pytest.mark.asyncio
async def test_connection_bootstrap_rejects_telegram_without_internal_secret() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await routes.get_customer_onboarding_connection_bootstrap(
            response=Response(),
            surface="telegram_bot",
            platform_hint="android",
            telegram_id=123456,
            user_id=None,
            telegram_bot_secret=None,
            db=AsyncMock(),
            remnawave_client=AsyncMock(),
        )

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_mark_connected_commits_idempotent_result(monkeypatch: pytest.MonkeyPatch) -> None:
    db = AsyncMock()
    user_id = uuid4()
    connection_session_id = uuid4()
    connected_at = datetime(2026, 6, 27, 12, 0, tzinfo=UTC)

    class FakeSessionRepo:
        def __init__(self, _db) -> None:
            pass

        async def mark_connected(self, **kwargs):
            assert kwargs["user_id"] == user_id
            assert kwargs["connection_session_id"] == connection_session_id
            assert kwargs["source_surface"] == "miniapp"
            assert kwargs["selected_platform"] == "android"
            return CustomerConnectionMarkResult(
                status="already_recorded",
                next_destination="/dashboard",
                connected_at=connected_at,
                flow_key="post_registration_code_prompt",
                version=1,
            )

    monkeypatch.setattr(routes, "CustomerConnectionSessionSqlAlchemyRepository", FakeSessionRepo)

    response = await routes.mark_customer_onboarding_connection_connected(
        payload=MarkOnboardingConnectionConnectedRequest(
            connection_session_id=str(connection_session_id),
            source_surface="miniapp",
            platform="android",
            flow_key="post_registration_code_prompt",
            version=1,
        ),
        user_id=user_id,
        db=db,
    )

    assert response.status == "already_recorded"
    assert response.next_destination == "/miniapp/home"
    assert response.connected_at == connected_at.isoformat()
    assert response.flow_key == "post_registration_code_prompt"
    assert response.version == 1
    db.commit.assert_awaited_once()


def test_mark_connected_request_requires_connection_session_id() -> None:
    with pytest.raises(ValidationError):
        MarkOnboardingConnectionConnectedRequest(
            source_surface="miniapp",
            platform="android",
        )

    with pytest.raises(ValidationError):
        MarkOnboardingConnectionConnectedRequest(
            connection_session_id=None,
            source_surface="miniapp",
            platform="android",
        )
