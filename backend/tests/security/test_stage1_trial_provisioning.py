"""S1-VPN-004 trial provisioning checks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from src.application.use_cases.trial.activate_trial import ActivateTrialUseCase
from src.application.use_cases.trial.stage1_trial_provisioning import (
    STAGE1_TRIAL_DEVICE_LIMIT,
    STAGE1_TRIAL_DURATION_DAYS,
    STAGE1_TRIAL_TRAFFIC_LIMIT_BYTES,
    STAGE1_TRIAL_TRAFFIC_LIMIT_STRATEGY,
    Stage1TrialProvisioningError,
    Stage1TrialProvisioningRequest,
    Stage1TrialProvisioningResult,
    Stage1TrialProvisioningService,
    build_stage1_trial_provisioning_request,
)
from src.presentation.api.shared import STAGE1_DEFAULT_VPN_PROFILE_ID, STAGE1_XHTTP_VPN_PROFILE_ID


class RecordingTrialGateway:
    def __init__(self) -> None:
        self.requests: list[Stage1TrialProvisioningRequest] = []

    async def provision_trial_access(
        self,
        request: Stage1TrialProvisioningRequest,
    ) -> Stage1TrialProvisioningResult:
        self.requests.append(request)
        return Stage1TrialProvisioningResult(
            customer_account_id=request.customer_account_id,
            remnawave_uuid=str(uuid4()),
            profile_id=request.profile_id,
            status="active",
            expires_at=request.trial_expires_at,
            subscription_url="https://subscription.example.local/sub/redacted-user",
            created=request.existing_remnawave_uuid is None,
        )


class _FakeMobileUserRepository:
    def __init__(self, user: SimpleNamespace | None) -> None:
        self.user = user
        self.updated: SimpleNamespace | None = None

    async def get_by_id(self, _user_id: UUID) -> SimpleNamespace | None:
        return self.user

    async def update(self, model: SimpleNamespace) -> SimpleNamespace:
        self.updated = model
        return model


def test_stage1_trial_request_uses_default_vpn_profile_and_limits() -> None:
    user_id = uuid4()
    trial_expires_at = datetime.now(UTC) + timedelta(days=STAGE1_TRIAL_DURATION_DAYS)

    request = build_stage1_trial_provisioning_request(
        customer_account_id=user_id,
        email="trial-user@example.test",
        username="trial-user",
        telegram_id=123456,
        trial_expires_at=trial_expires_at,
    )

    assert request.profile_id == STAGE1_DEFAULT_VPN_PROFILE_ID
    assert request.traffic_limit_bytes == STAGE1_TRIAL_TRAFFIC_LIMIT_BYTES
    assert request.device_limit == STAGE1_TRIAL_DEVICE_LIMIT
    assert request.traffic_limit_strategy == STAGE1_TRIAL_TRAFFIC_LIMIT_STRATEGY
    assert request.remnawave_username == f"cvpn_trial_{user_id.hex}"


@pytest.mark.asyncio
async def test_stage1_trial_provisioning_service_creates_safe_result() -> None:
    gateway = RecordingTrialGateway()
    user_id = uuid4()
    trial_expires_at = datetime.now(UTC) + timedelta(days=STAGE1_TRIAL_DURATION_DAYS)

    result = await Stage1TrialProvisioningService(gateway).provision(
        customer_account_id=user_id,
        email="trial-user@example.test",
        username="trial-user",
        telegram_id=None,
        trial_expires_at=trial_expires_at,
    )

    assert len(gateway.requests) == 1
    assert gateway.requests[0].profile_id == STAGE1_DEFAULT_VPN_PROFILE_ID
    assert result.status == "active"
    assert result.created is True
    safe = result.to_safe_dict()
    serialized = str(safe).lower()
    assert safe["profile_id"] == STAGE1_DEFAULT_VPN_PROFILE_ID
    assert "subscription" not in serialized
    assert "config_link" not in serialized
    assert "secret" not in serialized
    assert "token" not in serialized


@pytest.mark.asyncio
async def test_stage1_trial_can_use_xhttp_allowlisted_profile() -> None:
    gateway = RecordingTrialGateway()
    trial_expires_at = datetime.now(UTC) + timedelta(days=STAGE1_TRIAL_DURATION_DAYS)

    result = await Stage1TrialProvisioningService(gateway).provision(
        customer_account_id=uuid4(),
        email="trial-user@example.test",
        username=None,
        telegram_id=None,
        trial_expires_at=trial_expires_at,
        profile_id=STAGE1_XHTTP_VPN_PROFILE_ID,
    )

    assert result.profile_id == STAGE1_XHTTP_VPN_PROFILE_ID
    assert gateway.requests[0].profile_id == STAGE1_XHTTP_VPN_PROFILE_ID


def test_stage1_trial_rejects_disabled_profile() -> None:
    with pytest.raises(Stage1TrialProvisioningError):
        build_stage1_trial_provisioning_request(
            customer_account_id=uuid4(),
            email="trial-user@example.test",
            username=None,
            telegram_id=None,
            trial_expires_at=datetime.now(UTC) + timedelta(days=STAGE1_TRIAL_DURATION_DAYS),
            profile_id="wireguard",
        )


@pytest.mark.asyncio
async def test_activate_trial_use_case_provisions_vpn_access(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.application.use_cases.trial import activate_trial as module

    user_id = uuid4()
    user = SimpleNamespace(
        id=user_id,
        email="trial-user@example.test",
        username="trial-user",
        telegram_id=555,
        remnawave_uuid=None,
        subscription_url=None,
        trial_activated_at=None,
        trial_expires_at=None,
    )
    repo = _FakeMobileUserRepository(user)

    monkeypatch.setattr(module, "MobileUserRepository", lambda _session: repo)

    gateway = RecordingTrialGateway()
    result = await ActivateTrialUseCase(object(), provisioning_gateway=gateway).execute(user_id)

    assert result.activated is True
    assert result.provisioning_state == "ready"
    assert result.duration_days == STAGE1_TRIAL_DURATION_DAYS
    assert result.device_limit == STAGE1_TRIAL_DEVICE_LIMIT
    assert result.traffic_limit_bytes == STAGE1_TRIAL_TRAFFIC_LIMIT_BYTES
    assert result.one_trial_per_account is True
    assert result.provisioning is not None
    assert result.provisioning.profile_id == STAGE1_DEFAULT_VPN_PROFILE_ID
    assert len(gateway.requests) == 1
    assert gateway.requests[0].customer_account_id == user_id
    assert gateway.requests[0].traffic_limit_bytes == STAGE1_TRIAL_TRAFFIC_LIMIT_BYTES
    assert gateway.requests[0].device_limit == STAGE1_TRIAL_DEVICE_LIMIT
    assert repo.updated is user
    assert user.trial_activated_at is not None
    assert user.trial_expires_at == result.trial_end
    assert user.remnawave_uuid == result.provisioning.remnawave_uuid
    assert user.subscription_url == result.provisioning.subscription_url


@pytest.mark.asyncio
async def test_activate_trial_use_case_does_not_provision_when_gateway_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.application.use_cases.trial import activate_trial as module

    user_id = uuid4()
    user = SimpleNamespace(
        id=user_id,
        email="trial-user@example.test",
        username=None,
        telegram_id=None,
        remnawave_uuid=None,
        subscription_url=None,
        trial_activated_at=None,
        trial_expires_at=None,
    )
    repo = _FakeMobileUserRepository(user)
    monkeypatch.setattr(module, "MobileUserRepository", lambda _session: repo)

    result = await ActivateTrialUseCase(object()).execute(user_id)

    assert result.activated is True
    assert result.provisioning_state == "not_requested"
    assert result.provisioning is None
    assert user.remnawave_uuid is None
    assert user.subscription_url is None


@pytest.mark.asyncio
async def test_activate_trial_use_case_rejects_duplicate_trial(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.application.use_cases.trial import activate_trial as module

    user_id = uuid4()
    user = SimpleNamespace(
        id=user_id,
        email="trial-user@example.test",
        username="trial-user",
        telegram_id=None,
        remnawave_uuid=None,
        subscription_url=None,
        trial_activated_at=datetime.now(UTC) - timedelta(days=10),
        trial_expires_at=datetime.now(UTC) - timedelta(days=7),
    )
    repo = _FakeMobileUserRepository(user)
    monkeypatch.setattr(module, "MobileUserRepository", lambda _session: repo)

    with pytest.raises(ValueError, match="Only one trial per user"):
        await ActivateTrialUseCase(object()).execute(user_id)

    assert repo.updated is None
