from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request
from pydantic import ValidationError

from src.application.services.config_service import CustomerOnboardingRuntimeConfig
from src.application.use_cases.customer_onboarding import CustomerOnboardingFlowTokenService
from src.presentation.api.v1.customer_onboarding import routes
from src.presentation.api.v1.customer_onboarding.schemas import (
    CustomerOnboardingApplyRequest,
    CustomerOnboardingSkipRequest,
)


def _request_with_device() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/customer/onboarding/growth-code/apply",
            "headers": [(b"x-device-id", b"miniapp-device-1")],
            "client": ("198.51.100.10", 443),
            "server": ("testserver", 443),
            "scheme": "https",
        }
    )


class StaticConfigService:
    def __init__(self, runtime: CustomerOnboardingRuntimeConfig | None = None) -> None:
        self._runtime = runtime or CustomerOnboardingRuntimeConfig(
            post_registration_code_prompt_enabled=True,
            web_otp_enabled=True,
            state_store_ready=False,
        )

    async def get_customer_onboarding_runtime_config(self) -> CustomerOnboardingRuntimeConfig:
        return self._runtime


def _enabled_runtime() -> CustomerOnboardingRuntimeConfig:
    return CustomerOnboardingRuntimeConfig(
        post_registration_code_prompt_enabled=True,
        web_otp_enabled=True,
        state_store_ready=True,
    )


def _patch_config(monkeypatch: pytest.MonkeyPatch, runtime: CustomerOnboardingRuntimeConfig | None = None) -> None:
    monkeypatch.setattr(routes, "ConfigService", lambda _repo: StaticConfigService(runtime))


def _patch_flow_tokens(monkeypatch: pytest.MonkeyPatch) -> CustomerOnboardingFlowTokenService:
    flow_tokens = CustomerOnboardingFlowTokenService(secret="security-flow-token-placeholder", clock=lambda: 1_000_000)
    monkeypatch.setattr(routes, "CustomerOnboardingFlowTokenService", lambda: flow_tokens)
    return flow_tokens


def test_onboarding_apply_rejects_registration_access_token_payload_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_config(monkeypatch)
    forbidden_field = "_".join(("registration", "access", "token"))

    with pytest.raises(ValidationError) as exc_info:
        CustomerOnboardingApplyRequest.model_validate(
            {
                "code": "SAVE20",
                forbidden_field: str(uuid4()),
            }
        )

    assert exc_info.value.errors()[0]["type"] == "extra_forbidden"


def test_miniapp_forged_telegram_id_does_not_change_invite_runtime_fingerprint() -> None:
    first = routes._invite_redemption_runtime_context(
        request=_request_with_device(),
        source_surface="miniapp",
        telegram_id=111111,
    )
    second = routes._invite_redemption_runtime_context(
        request=_request_with_device(),
        source_surface="miniapp",
        telegram_id=222222,
    )
    bot_context = routes._invite_redemption_runtime_context(
        request=None,
        source_surface="telegram_bot",
        telegram_id=111111,
    )

    assert first.client_ip_hash is not None
    assert first.device_key_hash is not None
    assert second.client_ip_hash == first.client_ip_hash
    assert second.device_key_hash == first.device_key_hash
    assert bot_context.client_ip_hash != first.client_ip_hash
    assert bot_context.device_key_hash != first.device_key_hash


@pytest.mark.asyncio
async def test_onboarding_apply_rejects_uuid_like_registration_access_token_without_consuming(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    _patch_config(monkeypatch)

    with pytest.raises(HTTPException) as exc_info:
        await routes.apply_customer_onboarding_growth_code(
            payload=CustomerOnboardingApplyRequest(code=str(uuid4())),
            request=_request_with_device(),
            user_id=uuid4(),
            db=db,
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == {
        "code": "REGISTRATION_ACCESS_TOKEN_NOT_ACCEPTED",
        "message_key": "onboarding.code.registration_access_token_not_accepted",
    }
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_onboarding_apply_rejects_forged_flow_token_without_consuming(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    _patch_config(monkeypatch, _enabled_runtime())
    _patch_flow_tokens(monkeypatch)

    with pytest.raises(HTTPException) as exc_info:
        await routes.apply_customer_onboarding_growth_code(
            payload=CustomerOnboardingApplyRequest(
                code="SAVE20",
                flow_token="forged-flow-token-000",
                idempotency_key="request-1",
            ),
            request=_request_with_device(),
            user_id=uuid4(),
            db=db,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == {
        "code": "CUSTOMER_ONBOARDING_FLOW_TOKEN_INVALID",
        "message_key": "onboarding.flow_token.invalid",
    }
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_onboarding_apply_rejects_non_ascii_forged_flow_token_without_500_or_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    _patch_config(monkeypatch, _enabled_runtime())
    _patch_flow_tokens(monkeypatch)

    with pytest.raises(HTTPException) as exc_info:
        await routes.apply_customer_onboarding_growth_code(
            payload=CustomerOnboardingApplyRequest(
                code="SAVE20",
                flow_token="cot1.éééééééééééé.sig",
                idempotency_key="request-1",
            ),
            request=_request_with_device(),
            user_id=uuid4(),
            db=db,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == {
        "code": "CUSTOMER_ONBOARDING_FLOW_TOKEN_INVALID",
        "message_key": "onboarding.flow_token.invalid",
    }
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_onboarding_skip_rejects_forged_flow_token_without_consuming(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    _patch_config(monkeypatch, _enabled_runtime())
    _patch_flow_tokens(monkeypatch)

    with pytest.raises(HTTPException) as exc_info:
        await routes.skip_customer_onboarding_growth_code(
            payload=CustomerOnboardingSkipRequest(
                flow_token="forged-flow-token-000",
                idempotency_key="request-1",
            ),
            user_id=uuid4(),
            db=db,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == {
        "code": "CUSTOMER_ONBOARDING_FLOW_TOKEN_INVALID",
        "message_key": "onboarding.flow_token.invalid",
    }
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_onboarding_skip_rejects_non_ascii_forged_flow_token_without_500_or_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    _patch_config(monkeypatch, _enabled_runtime())
    _patch_flow_tokens(monkeypatch)

    with pytest.raises(HTTPException) as exc_info:
        await routes.skip_customer_onboarding_growth_code(
            payload=CustomerOnboardingSkipRequest(
                flow_token="cot1.abc.éééééééééééé",
                idempotency_key="request-1",
            ),
            user_id=uuid4(),
            db=db,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == {
        "code": "CUSTOMER_ONBOARDING_FLOW_TOKEN_INVALID",
        "message_key": "onboarding.flow_token.invalid",
    }
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_onboarding_apply_rejects_flow_token_bound_to_different_user_without_consuming(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    runtime = _enabled_runtime()
    _patch_config(monkeypatch, runtime)
    flow_tokens = _patch_flow_tokens(monkeypatch)
    flow_token = flow_tokens.issue(user_id=uuid4(), flow_key=runtime.flow_key, version=runtime.version)

    with pytest.raises(HTTPException) as exc_info:
        await routes.apply_customer_onboarding_growth_code(
            payload=CustomerOnboardingApplyRequest(
                code="SAVE20",
                flow_token=flow_token,
                idempotency_key="request-1",
            ),
            request=_request_with_device(),
            user_id=uuid4(),
            db=db,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == {
        "code": "CUSTOMER_ONBOARDING_FLOW_TOKEN_INVALID",
        "message_key": "onboarding.flow_token.invalid",
    }
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_onboarding_skip_rejects_flow_token_bound_to_different_user_without_consuming(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    runtime = _enabled_runtime()
    _patch_config(monkeypatch, runtime)
    flow_tokens = _patch_flow_tokens(monkeypatch)
    flow_token = flow_tokens.issue(user_id=uuid4(), flow_key=runtime.flow_key, version=runtime.version)

    with pytest.raises(HTTPException) as exc_info:
        await routes.skip_customer_onboarding_growth_code(
            payload=CustomerOnboardingSkipRequest(
                flow_token=flow_token,
                idempotency_key="request-1",
            ),
            user_id=uuid4(),
            db=db,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == {
        "code": "CUSTOMER_ONBOARDING_FLOW_TOKEN_INVALID",
        "message_key": "onboarding.flow_token.invalid",
    }
    db.commit.assert_not_awaited()
