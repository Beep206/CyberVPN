from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.application.services.config_service import CustomerOnboardingRuntimeConfig
from src.application.use_cases.customer_onboarding import CustomerOnboardingCurrentState
from src.presentation.api.v1.auth import routes


class StaticConfigService:
    def __init__(self, runtime: CustomerOnboardingRuntimeConfig) -> None:
        self._runtime = runtime

    async def get_customer_onboarding_runtime_config(self) -> CustomerOnboardingRuntimeConfig:
        return self._runtime


class RecordingOnboardingRepository:
    ensure_calls: list[dict[str, object]] = []

    def __init__(self, _db) -> None:
        self.state: CustomerOnboardingCurrentState | None = None

    async def ensure_pending(self, **kwargs):
        self.ensure_calls.append(kwargs)
        runtime_config = kwargs["runtime_config"]
        assert isinstance(runtime_config, CustomerOnboardingRuntimeConfig)
        self.state = CustomerOnboardingCurrentState(
            required=True,
            status="pending",
            flow_key=runtime_config.flow_key,
            version=runtime_config.version,
            allowed_code_types=runtime_config.allowed_code_types,
            message_key="onboarding.required",
            server_state_available=True,
        )
        return self.state

    async def get_current(self, *, user_id, flow_key, version):
        return self.state or CustomerOnboardingCurrentState(
            required=True,
            status="pending",
            flow_key=flow_key,
            version=version,
            allowed_code_types=("promo", "invite", "gift"),
            message_key="onboarding.required",
            server_state_available=True,
        )


def _mobile_user():
    return SimpleNamespace(id=uuid4())


@pytest.mark.asyncio
async def test_auth_activation_creates_customer_onboarding_state_and_flow_token(monkeypatch) -> None:
    runtime = CustomerOnboardingRuntimeConfig(
        post_registration_code_prompt_enabled=True,
        web_otp_enabled=True,
        telegram_miniapp_enabled=True,
        state_store_ready=True,
    )
    RecordingOnboardingRepository.ensure_calls = []
    monkeypatch.setattr(routes, "ConfigService", lambda _repo: StaticConfigService(runtime))
    monkeypatch.setattr(routes, "CustomerOnboardingStateSqlAlchemyRepository", RecordingOnboardingRepository)

    state = await routes._resolve_post_registration_onboarding(
        db=SimpleNamespace(),
        mobile_user=_mobile_user(),
        realm_type="customer",
        auth_channel="web_otp",
        create_if_missing=True,
    )
    response = routes._auth_onboarding_response(state)

    assert state is not None
    assert state.required is True
    assert state.flow_token
    assert response is not None
    assert response.status == "pending"
    assert response.server_state_available is True
    assert RecordingOnboardingRepository.ensure_calls[0]["auth_channel"] == "web_otp"


@pytest.mark.asyncio
async def test_auth_activation_does_not_create_onboarding_when_channel_disabled(monkeypatch) -> None:
    runtime = CustomerOnboardingRuntimeConfig(
        post_registration_code_prompt_enabled=True,
        web_otp_enabled=False,
        telegram_miniapp_enabled=True,
        state_store_ready=True,
    )
    RecordingOnboardingRepository.ensure_calls = []
    monkeypatch.setattr(routes, "ConfigService", lambda _repo: StaticConfigService(runtime))
    monkeypatch.setattr(routes, "CustomerOnboardingStateSqlAlchemyRepository", RecordingOnboardingRepository)

    state = await routes._resolve_post_registration_onboarding(
        db=SimpleNamespace(),
        mobile_user=_mobile_user(),
        realm_type="customer",
        auth_channel="web_otp",
        create_if_missing=True,
    )

    assert state is None
    assert RecordingOnboardingRepository.ensure_calls == []
