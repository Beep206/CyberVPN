"""S1-VPN-004 trial provisioning checks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
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
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.remnawave.stage1_trial_gateway import RemnawaveStage1TrialProvisioningGateway
from src.infrastructure.remnawave.user_gateway import RemnawaveMutationAcceptedPending
from src.presentation.api.shared import STAGE1_DEFAULT_VPN_PROFILE_ID, STAGE1_XHTTP_VPN_PROFILE_ID


class RecordingTrialGateway:
    def __init__(self, *, with_legacy_uuid: bool = True, remnawave_user_id: int | None = 42) -> None:
        self.requests: list[Stage1TrialProvisioningRequest] = []
        self.remnawave_uuid = str(uuid4()) if with_legacy_uuid else None
        self.remnawave_user_id = remnawave_user_id

    async def provision_trial_access(
        self,
        request: Stage1TrialProvisioningRequest,
    ) -> Stage1TrialProvisioningResult:
        self.requests.append(request)
        return Stage1TrialProvisioningResult(
            customer_account_id=request.customer_account_id,
            remnawave_uuid=self.remnawave_uuid,
            profile_id=request.profile_id,
            status="active",
            expires_at=request.trial_expires_at,
            subscription_url="https://subscription.example.local/sub/redacted-user",
            created=request.existing_remnawave_uuid is None,
            remnawave_user_id=self.remnawave_user_id,
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


class _AttemptResult:
    def __init__(self, record) -> None:
        self.record = record

    def scalars(self):
        return self

    def one_or_none(self):
        return self.record


class _AttemptSession:
    def __init__(self) -> None:
        self.record = None
        self.commits = 0

    async def execute(self, _statement):
        return _AttemptResult(self.record)

    def add(self, record) -> None:
        self.record = record

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None

    async def flush(self) -> None:
        return None


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
    assert request.remnawave_username == f"cvpn_t_{user_id.hex[:28]}"
    assert len(request.remnawave_username) <= 36


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
@pytest.mark.parametrize("remnawave_user_id", [None, True, 0, -1])
async def test_stage1_trial_provisioning_rejects_invalid_numeric_result(remnawave_user_id: int | None) -> None:
    gateway = RecordingTrialGateway(remnawave_user_id=remnawave_user_id)

    with pytest.raises(Stage1TrialProvisioningError, match="incomplete Remnawave 3.x identity"):
        await Stage1TrialProvisioningService(gateway).provision(
            customer_account_id=uuid4(),
            email="trial-user@example.test",
            username=None,
            telegram_id=None,
            trial_expires_at=datetime.now(UTC) + timedelta(days=STAGE1_TRIAL_DURATION_DAYS),
        )


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
async def test_stage1_trial_gateway_rejects_legacy_only_existing_identity() -> None:
    user_gateway = SimpleNamespace(
        update=AsyncMock(),
        create=AsyncMock(),
    )
    request = build_stage1_trial_provisioning_request(
        customer_account_id=uuid4(),
        email="trial-user@example.test",
        username=None,
        telegram_id=None,
        trial_expires_at=datetime.now(UTC) + timedelta(days=STAGE1_TRIAL_DURATION_DAYS),
        existing_remnawave_uuid=str(uuid4()),
    )

    with pytest.raises(Stage1TrialProvisioningError, match="numeric identity is not reconciled"):
        await RemnawaveStage1TrialProvisioningGateway(user_gateway).provision_trial_access(request)

    user_gateway.update.assert_not_awaited()
    user_gateway.create.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("with_legacy_uuid", [True, False])
async def test_activate_trial_use_case_provisions_vpn_access(
    monkeypatch: pytest.MonkeyPatch,
    with_legacy_uuid: bool,
) -> None:
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

    class RoutingOnlyCreateAttemptService:
        def __init__(self, _session) -> None:
            self.record = SimpleNamespace()

        async def begin(self, **_kwargs):
            return SimpleNamespace(record=self.record, should_mutate=True)

        async def mark_reconciliation_required(self, _record) -> None:
            return None

        async def mark_completed(self, _record, *, user_ref) -> None:
            assert user_ref.require_numeric_id() == 42

    monkeypatch.setattr(module, "RemnawaveCreateAttemptService", RoutingOnlyCreateAttemptService)

    persisted: list[tuple[int | None, str | None]] = []

    async def persist_identity(_session, *, customer, remnawave_user_id, remnawave_uuid, source):
        assert source == "trial_activation"
        customer.remnawave_user_id = remnawave_user_id
        customer.remnawave_uuid = remnawave_uuid
        persisted.append((remnawave_user_id, remnawave_uuid))

    monkeypatch.setattr(module, "persist_runtime_mapped_mobile_identity", persist_identity)

    gateway = RecordingTrialGateway(with_legacy_uuid=with_legacy_uuid)
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
    assert user.remnawave_user_id == 42
    assert persisted == [(42, result.provisioning.remnawave_uuid)]
    assert user.subscription_url == result.provisioning.subscription_url


@pytest.mark.asyncio
async def test_activate_trial_ambiguous_create_is_latched_before_second_entrypoint_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.application.use_cases.trial import activate_trial as module

    user_id = uuid4()
    user = SimpleNamespace(
        id=user_id,
        email="trial-user@example.test",
        username="trial-user",
        telegram_id=None,
        remnawave_user_id=None,
        remnawave_uuid=None,
        subscription_url=None,
        trial_activated_at=None,
        trial_expires_at=None,
    )
    repo = _FakeMobileUserRepository(user)
    session = _AttemptSession()

    class AmbiguousGateway:
        def __init__(self) -> None:
            self.calls = 0

        async def provision_trial_access(self, request):
            self.calls += 1
            raise RemnawaveMutationAcceptedPending(operation="create")

    async def no_identity(_session, _user):
        return None

    monkeypatch.setattr(module, "MobileUserRepository", lambda _session: repo)
    monkeypatch.setattr(module, "resolve_exact_mapped_mobile_user_ref", no_identity)
    gateway = AmbiguousGateway()

    with pytest.raises(RemnawaveMutationAcceptedPending):
        await ActivateTrialUseCase(session, provisioning_gateway=gateway).execute(user_id)
    with pytest.raises(ValueError, match="requires reconciliation"):
        await ActivateTrialUseCase(session, provisioning_gateway=gateway).execute(user_id)

    assert gateway.calls == 1
    assert session.record.status == "reconciliation_required"
    assert session.commits == 2
    assert user.trial_activated_at is None


@pytest.mark.asyncio
async def test_activate_trial_rejects_split_identity_before_any_upstream_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.application.services.remnawave_identity_access import RemnawaveIdentityAccessConflict
    from src.application.use_cases.trial import activate_trial as module

    user_id = uuid4()
    user = SimpleNamespace(
        id=user_id,
        email="trial-user@example.test",
        username="trial-user",
        telegram_id=555,
        remnawave_user_id=42,
        remnawave_uuid=str(uuid4()),
        subscription_url=None,
        trial_activated_at=None,
        trial_expires_at=None,
    )
    repo = _FakeMobileUserRepository(user)
    gateway = RecordingTrialGateway()

    async def reject_identity(_session, _user):
        raise RemnawaveIdentityAccessConflict("split mapping")

    monkeypatch.setattr(module, "MobileUserRepository", lambda _session: repo)
    monkeypatch.setattr(module, "resolve_exact_mapped_mobile_user_ref", reject_identity)

    with pytest.raises(RemnawaveIdentityAccessConflict, match="split mapping"):
        await ActivateTrialUseCase(object(), provisioning_gateway=gateway).execute(user_id)

    assert gateway.requests == []
    assert repo.updated is None
    assert user.trial_activated_at is None


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


@pytest.mark.asyncio
async def test_miniapp_trial_activation_passes_provisioning_gateway(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.presentation.api.v1.miniapp import routes as miniapp_routes

    user_id = uuid4()
    gateway = object()
    seen: dict[str, object | None] = {}

    class FakeRedis:
        async def get(self, _key: str) -> None:
            return None

        async def ttl(self, _key: str) -> int:
            return 0

        def pipeline(self):
            class FakePipeline:
                async def incr(self, _key: str):
                    return self

                async def expire(self, _key: str, _ttl: int):
                    return self

                async def execute(self) -> None:
                    return None

            return FakePipeline()

    class FakeActivateTrialUseCase:
        def __init__(self, _db, provisioning_gateway=None) -> None:
            seen["gateway"] = provisioning_gateway

        async def execute(self, _user_id: UUID):
            return SimpleNamespace(
                activated=True,
                trial_end=datetime.now(UTC) + timedelta(days=STAGE1_TRIAL_DURATION_DAYS),
                message="Trial activated successfully.",
            )

    async def fake_runtime_config(_db=None):
        return miniapp_routes.MiniAppRuntimeConfig()

    monkeypatch.setattr(miniapp_routes, "ActivateTrialUseCase", FakeActivateTrialUseCase)
    monkeypatch.setattr(miniapp_routes, "_get_miniapp_runtime_config", fake_runtime_config)

    response = await miniapp_routes.activate_miniapp_trial(
        db=object(),
        user_id=user_id,
        redis_client=FakeRedis(),
        provisioning_gateway=gateway,
    )

    assert response.activated is True
    assert seen["gateway"] is gateway


@pytest.mark.asyncio
async def test_telegram_bot_trial_activation_passes_provisioning_gateway(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.presentation.api.v1.telegram import routes as telegram_routes
    from src.presentation.api.v1.telegram.schemas import TelegramBotTrialStatusResponse

    user_id = uuid4()
    gateway = object()
    user = SimpleNamespace(id=user_id)
    seen: dict[str, object | None] = {}

    class FakeActivateTrialUseCase:
        def __init__(self, _db, provisioning_gateway=None) -> None:
            seen["gateway"] = provisioning_gateway

        async def execute(self, _user_id: UUID):
            return SimpleNamespace(activated=True)

    async def fake_get_user(_db, _telegram_id: int):
        return user

    status_calls = {"count": 0}

    async def fake_trial_status(_db, _user):
        status_calls["count"] += 1
        return TelegramBotTrialStatusResponse(
            eligible=status_calls["count"] == 1,
            reason=None,
            is_trial_active=status_calls["count"] > 1,
            trial_start=None,
            trial_end=datetime.now(UTC) + timedelta(days=STAGE1_TRIAL_DURATION_DAYS),
            days_remaining=STAGE1_TRIAL_DURATION_DAYS,
            duration_days=STAGE1_TRIAL_DURATION_DAYS,
        )

    monkeypatch.setattr(telegram_routes, "_require_telegram_bot_secret", lambda _secret: None)
    monkeypatch.setattr(telegram_routes, "_get_mobile_user_or_404", fake_get_user)
    monkeypatch.setattr(telegram_routes, "_build_mobile_trial_status", fake_trial_status)
    monkeypatch.setattr(telegram_routes, "ActivateTrialUseCase", FakeActivateTrialUseCase)

    response = await telegram_routes.activate_bot_user_trial(
        telegram_id=123456,
        telegram_bot_secret="internal-secret",
        db=object(),
        provisioning_gateway=gateway,
    )

    assert response.is_trial_active is True
    assert seen["gateway"] is gateway


@pytest.mark.asyncio
async def test_telegram_bot_config_uses_exact_mapped_numeric_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.presentation.api.v1.telegram import routes as telegram_routes

    remnawave_uuid = uuid4()
    mobile_user_id = uuid4()
    seen: dict[str, object] = {}

    reconciliation = SimpleNamespace(
        subject_type="mobile_user",
        subject_id=mobile_user_id,
        reconciliation_state="mapped",
        numeric_user_id=42,
        legacy_uuid=str(remnawave_uuid),
    )

    class ScalarResult:
        def scalars(self):
            return self

        def all(self):
            return [reconciliation]

    class FakeDb:
        async def execute(self, _statement):
            return ScalarResult()

    class FakeMobileUserRepo:
        def __init__(self, _db) -> None:
            pass

        async def get_by_telegram_id(self, _telegram_id: int):
            return SimpleNamespace(
                id=mobile_user_id,
                remnawave_user_id=42,
                remnawave_uuid=str(remnawave_uuid),
                subscription_url="https://legacy.example/sub",
            )

    class FakeGenerateConfigUseCase:
        def __init__(self, _client) -> None:
            pass

        async def execute(self, user_ref):
            seen["user_ref"] = user_ref
            return {
                "config_string": "vless://generated",
                "client_type": "vless",
                "subscription_url": "https://generated.example/sub",
            }

    class UnexpectedGateway:
        def __init__(self, *args, **kwargs) -> None:
            raise AssertionError("telegram_id Remnawave lookup should not run when local Remnawave UUID exists")

    monkeypatch.setattr(telegram_routes, "_require_telegram_bot_secret", lambda _secret: None)
    monkeypatch.setattr(telegram_routes, "MobileUserRepository", FakeMobileUserRepo)
    monkeypatch.setattr(telegram_routes, "GenerateConfigUseCase", FakeGenerateConfigUseCase)
    monkeypatch.setattr(telegram_routes, "RemnawaveUserGateway", UnexpectedGateway)

    response = await telegram_routes.get_bot_user_config(
        telegram_id=123456,
        telegram_bot_secret="internal-secret",
        db=FakeDb(),
        remnawave_client=object(),
    )

    assert seen["user_ref"] == RemnawaveUserRef(id=42, legacy_uuid=remnawave_uuid)
    assert response.config_string == "https://generated.example/sub"
    assert response.client_type == "subscription"
    assert response.subscription_url == "https://generated.example/sub"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "mapped_numeric_id"),
    [
        (None, None),
        ("pending", 42),
        ("mapped", 99),
    ],
)
async def test_telegram_bot_config_rejects_missing_pending_or_wrong_mapping(
    monkeypatch: pytest.MonkeyPatch,
    state: str | None,
    mapped_numeric_id: int | None,
) -> None:
    from src.presentation.api.v1.telegram import routes as telegram_routes

    remnawave_uuid = uuid4()
    mobile_user_id = uuid4()
    reconciliation = (
        SimpleNamespace(
            subject_type="mobile_user",
            subject_id=mobile_user_id,
            reconciliation_state=state,
            numeric_user_id=mapped_numeric_id,
            legacy_uuid=str(remnawave_uuid),
        )
        if state is not None
        else None
    )

    class ScalarResult:
        def scalars(self):
            return self

        def all(self):
            return [] if reconciliation is None else [reconciliation]

    class FakeDb:
        async def execute(self, _statement):
            return ScalarResult()

    class FakeMobileUserRepo:
        def __init__(self, _db) -> None:
            pass

        async def get_by_telegram_id(self, _telegram_id: int):
            return SimpleNamespace(
                id=mobile_user_id,
                remnawave_user_id=42,
                remnawave_uuid=str(remnawave_uuid),
                subscription_url="https://legacy.example/must-not-leak",
            )

    class ForbiddenGenerateConfigUseCase:
        def __init__(self, _client) -> None:
            raise AssertionError("config generation must not run for an unreconciled identity")

    monkeypatch.setattr(telegram_routes, "_require_telegram_bot_secret", lambda _secret: None)
    monkeypatch.setattr(telegram_routes, "MobileUserRepository", FakeMobileUserRepo)
    monkeypatch.setattr(telegram_routes, "GenerateConfigUseCase", ForbiddenGenerateConfigUseCase)

    with pytest.raises(telegram_routes.HTTPException) as exc_info:
        await telegram_routes.get_bot_user_config(
            telegram_id=123456,
            telegram_bot_secret="internal-secret",
            db=FakeDb(),
            remnawave_client=object(),
        )

    assert exc_info.value.status_code == 409
