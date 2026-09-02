from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.services.remnawave_identity_access import RemnawaveIdentityAccessConflict
from src.application.use_cases.trial.stage1_trial_provisioning import Stage1TrialProvisioningResult
from src.infrastructure.remnawave.user_gateway import RemnawaveMutationAcceptedPending
from src.presentation.api.v1.invites import routes as invite_routes


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "upstream_legacy_uuid",
    ["2f4a8f2d-e8a5-4a2f-9c70-ef6e35b3a601", None],
)
async def test_provision_redeemed_invite_access_updates_mobile_user(monkeypatch, upstream_legacy_uuid):
    user_id = uuid4()
    auth_realm_id = uuid4()
    service_identity_id = uuid4()
    entitlement_grant_id = uuid4()
    expires_at = datetime(2026, 5, 28, 13, 40, tzinfo=UTC)
    user = SimpleNamespace(
        id=user_id,
        email="tg123456@telegram.local",
        username="telegram-user",
        telegram_id=123456,
        auth_realm_id=auth_realm_id,
        remnawave_uuid=None,
        subscription_url=None,
    )
    updated_users = []
    seen_requests = []

    class FakeDb:
        async def get(self, model, item_id):
            assert model is invite_routes.EntitlementGrantModel
            assert item_id == entitlement_grant_id
            return SimpleNamespace(
                expires_at=expires_at,
                customer_account_id=user_id,
                auth_realm_id=auth_realm_id,
                service_identity_id=service_identity_id,
            )

    class FakeMobileUserRepository:
        def __init__(self, _db):
            pass

        async def get_by_id(self, item_id):
            assert item_id == user_id
            return user

        async def update(self, item):
            updated_users.append(item)
            return item

    class FakeProvisioningGateway:
        async def provision_trial_access(self, request):
            seen_requests.append(request)
            return Stage1TrialProvisioningResult(
                customer_account_id=request.customer_account_id,
                remnawave_uuid=upstream_legacy_uuid,
                profile_id=request.profile_id,
                status="active",
                expires_at=request.trial_expires_at,
                subscription_url="https://sub.example.com/redacted",
                created=True,
                remnawave_user_id=42,
            )

    monkeypatch.setattr(invite_routes, "MobileUserRepository", FakeMobileUserRepository)

    class RoutingOnlyCreateAttemptService:
        calls = 0

        def __init__(self, _session) -> None:
            self.record = SimpleNamespace()

        async def begin(self, **_kwargs):
            type(self).calls += 1
            return SimpleNamespace(record=self.record, should_mutate=type(self).calls == 1)

        async def mark_reconciliation_required(self, _record) -> None:
            return None

        async def mark_completed(self, _record, *, user_ref) -> None:
            assert user_ref.require_numeric_id() == 42

    monkeypatch.setattr(invite_routes, "RemnawaveCreateAttemptService", RoutingOnlyCreateAttemptService)

    class MarkerContext:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, _exc_type, _exc, _tb):
            return False

    monkeypatch.setattr(invite_routes, "AsyncSessionLocal", MarkerContext)

    persisted = []

    async def persist_identity(_db, *, customer, remnawave_user_id, remnawave_uuid, source):
        assert source == "invite_redemption"
        customer.remnawave_user_id = remnawave_user_id
        customer.remnawave_uuid = remnawave_uuid
        persisted.append((remnawave_user_id, remnawave_uuid))

    monkeypatch.setattr(invite_routes, "persist_runtime_mapped_mobile_identity", persist_identity)

    binding_calls = []

    class FakeIdentityBinding:
        def __init__(self, _db) -> None:
            pass

        async def validate_target(self, **kwargs):
            assert kwargs == {
                "service_identity_id": service_identity_id,
                "customer_account_id": user_id,
                "auth_realm_id": auth_realm_id,
            }

        async def execute(self, **kwargs):
            binding_calls.append(kwargs)

    monkeypatch.setattr(
        invite_routes,
        "BindProvisionedRemnawaveServiceIdentityUseCase",
        FakeIdentityBinding,
    )

    await invite_routes._provision_redeemed_invite_access(
        db=FakeDb(),
        user_id=user_id,
        result=SimpleNamespace(
            entitlement_grant_id=entitlement_grant_id,
            invite=SimpleNamespace(free_days=7),
        ),
        provisioning_gateway=FakeProvisioningGateway(),
    )

    assert seen_requests[0].customer_account_id == user_id
    assert seen_requests[0].trial_expires_at == expires_at
    assert user.remnawave_uuid == upstream_legacy_uuid
    assert user.remnawave_user_id == 42
    assert persisted == [(42, upstream_legacy_uuid)]
    assert user.subscription_url == "https://sub.example.com/redacted"
    assert updated_users == [user]
    assert binding_calls == [
        {
            "service_identity_id": service_identity_id,
            "customer_account_id": user_id,
            "auth_realm_id": auth_realm_id,
            "remnawave_user_id": 42,
            "remnawave_uuid": upstream_legacy_uuid,
            "mapping_source": "invite_redemption",
        }
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_provision_redeemed_invite_rejects_split_identity_before_upstream(monkeypatch):
    user_id = uuid4()
    auth_realm_id = uuid4()
    service_identity_id = uuid4()
    entitlement_grant_id = uuid4()
    user = SimpleNamespace(
        id=user_id,
        email="tg123456@telegram.local",
        username="telegram-user",
        telegram_id=123456,
        auth_realm_id=auth_realm_id,
        remnawave_user_id=42,
        remnawave_uuid=str(uuid4()),
        subscription_url=None,
    )
    gateway = SimpleNamespace(provision_trial_access=AsyncMock())

    class FakeDb:
        async def get(self, _model, _item_id):
            return SimpleNamespace(
                expires_at=datetime(2026, 5, 28, 13, 40, tzinfo=UTC),
                customer_account_id=user_id,
                auth_realm_id=auth_realm_id,
                service_identity_id=service_identity_id,
            )

    class FakeMobileUserRepository:
        def __init__(self, _db):
            pass

        async def get_by_id(self, _item_id):
            return user

        async def update(self, _item):
            raise AssertionError("split identity must not be persisted")

    async def reject_identity(_db, _user):
        raise RemnawaveIdentityAccessConflict("split mapping")

    monkeypatch.setattr(invite_routes, "MobileUserRepository", FakeMobileUserRepository)
    monkeypatch.setattr(invite_routes, "resolve_exact_mapped_mobile_user_ref", reject_identity)

    class FakeIdentityBinding:
        def __init__(self, _db) -> None:
            pass

        async def validate_target(self, **_kwargs):
            return None

        async def execute(self, **_kwargs):
            raise AssertionError("split identity must not be bound")

    monkeypatch.setattr(
        invite_routes,
        "BindProvisionedRemnawaveServiceIdentityUseCase",
        FakeIdentityBinding,
    )

    with pytest.raises(RemnawaveIdentityAccessConflict, match="split mapping"):
        await invite_routes._provision_redeemed_invite_access(
            db=FakeDb(),
            user_id=user_id,
            result=SimpleNamespace(
                entitlement_grant_id=entitlement_grant_id,
                invite=SimpleNamespace(free_days=7),
            ),
            provisioning_gateway=gateway,
        )

    gateway.provision_trial_access.assert_not_awaited()


class _AttemptResult:
    def __init__(self, record) -> None:
        self.record = record

    def scalars(self):
        return self

    def one_or_none(self):
        return self.record


class _InviteAttemptDb:
    def __init__(
        self,
        *,
        expires_at: datetime,
        user_id=None,
        auth_realm_id=None,
        service_identity_id=None,
    ) -> None:
        self.expires_at = expires_at
        self.user_id = user_id
        self.auth_realm_id = auth_realm_id
        self.service_identity_id = service_identity_id
        self.record = None
        self.commits = 0

    async def get(self, _model, _item_id):
        return SimpleNamespace(
            expires_at=self.expires_at,
            customer_account_id=self.user_id,
            auth_realm_id=self.auth_realm_id,
            service_identity_id=self.service_identity_id,
        )

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


class _MarkerContext:
    def __init__(self, session) -> None:
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, _exc_type, _exc, _tb):
        return False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_invite_ambiguous_create_is_durable_and_never_reposted(monkeypatch) -> None:
    user_id = uuid4()
    auth_realm_id = uuid4()
    service_identity_id = uuid4()
    entitlement_grant_id = uuid4()
    expires_at = datetime(2026, 9, 5, 13, 40, tzinfo=UTC)
    user = SimpleNamespace(
        id=user_id,
        email="invite@example.test",
        username=None,
        telegram_id=None,
        auth_realm_id=auth_realm_id,
        remnawave_user_id=None,
        remnawave_uuid=None,
        subscription_url=None,
    )
    db = _InviteAttemptDb(
        expires_at=expires_at,
        user_id=user_id,
        auth_realm_id=auth_realm_id,
        service_identity_id=service_identity_id,
    )
    marker_db = _InviteAttemptDb(expires_at=expires_at)

    class FakeMobileUserRepository:
        def __init__(self, _db):
            pass

        async def get_by_id(self, _item_id):
            return user

        async def update(self, _item):
            raise AssertionError("ambiguous provider create must not publish a local mapping")

    class AmbiguousGateway:
        def __init__(self) -> None:
            self.calls = 0

        async def provision_trial_access(self, _request):
            self.calls += 1
            raise RemnawaveMutationAcceptedPending(operation="create")

    async def no_identity(_db, _user):
        return None

    monkeypatch.setattr(invite_routes, "MobileUserRepository", FakeMobileUserRepository)
    monkeypatch.setattr(invite_routes, "resolve_exact_mapped_mobile_user_ref", no_identity)
    monkeypatch.setattr(invite_routes, "AsyncSessionLocal", lambda: _MarkerContext(marker_db))

    class FakeIdentityBinding:
        def __init__(self, _db) -> None:
            pass

        async def validate_target(self, **_kwargs):
            return None

        async def execute(self, **_kwargs):
            raise AssertionError("ambiguous provider create must not bind an identity")

    monkeypatch.setattr(
        invite_routes,
        "BindProvisionedRemnawaveServiceIdentityUseCase",
        FakeIdentityBinding,
    )
    gateway = AmbiguousGateway()
    result = SimpleNamespace(
        entitlement_grant_id=entitlement_grant_id,
        invite=SimpleNamespace(free_days=7),
    )

    for _attempt in range(2):
        with pytest.raises(invite_routes.HTTPException) as exc_info:
            await invite_routes._provision_redeemed_invite_access(
                db=db,
                user_id=user_id,
                result=result,
                provisioning_gateway=gateway,
            )
        assert exc_info.value.status_code == 409

    assert gateway.calls == 1
    assert marker_db.record.status == "reconciliation_required"
    assert marker_db.commits == 2
    assert db.commits == 0
