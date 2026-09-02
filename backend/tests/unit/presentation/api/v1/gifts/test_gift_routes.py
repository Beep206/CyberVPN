from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.application.use_cases.gifts.provisioning import GiftProvisioningResult
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.presentation.api.v1.gifts import routes as gift_routes
from src.presentation.api.v1.gifts.schemas import GiftRedeemRequest


class _MarkerContext:
    def __init__(self, session) -> None:
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, _exc_type, _exc, _tb):
        return False


def _result(*, grant_id, gift_code_id, expires_at, device_limit=3):
    return SimpleNamespace(
        entitlement_grant_id=grant_id,
        entitlement_snapshot={
            "plan_code": "pro",
            "effective_entitlements": {
                "device_limit": device_limit,
                "traffic_limit_bytes": None,
            },
        },
        growth_code=SimpleNamespace(id=gift_code_id),
        policy=SimpleNamespace(plan_family="pro", duration_days=30),
    )


@pytest.mark.asyncio
async def test_gift_redeem_fails_before_mutation_without_provisioning_gateway(monkeypatch) -> None:
    class UnexpectedRedeemer:
        def __init__(self, _db) -> None:
            pass

        async def execute(self, **_kwargs):
            raise AssertionError("disabled provisioning must be rejected before gift redemption")

    monkeypatch.setattr(gift_routes, "_assert_gift_public_flow_enabled", lambda: None)
    monkeypatch.setattr(gift_routes, "RedeemGiftCodeUseCase", UnexpectedRedeemer)

    with pytest.raises(HTTPException) as exc_info:
        await gift_routes.redeem_gift(
            payload=GiftRedeemRequest(code="GIFT-NO-PROVISIONING"),
            db=AsyncMock(),
            user_id=uuid4(),
            current_realm=SimpleNamespace(realm_id=str(uuid4())),
            provisioning_gateway=None,
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Gift VPN provisioning is unavailable"


@pytest.mark.asyncio
async def test_gift_provisioning_maps_and_activates_exact_recipient(monkeypatch) -> None:
    user_id = uuid4()
    auth_realm_id = uuid4()
    service_identity_id = uuid4()
    grant_id = uuid4()
    gift_code_id = uuid4()
    expires_at = datetime(2026, 10, 1, tzinfo=UTC)
    user = SimpleNamespace(
        id=user_id,
        auth_realm_id=auth_realm_id,
        email="gift@example.test",
        username=None,
        telegram_id=None,
        remnawave_user_id=None,
        remnawave_uuid=None,
        subscription_url=None,
    )
    grant = SimpleNamespace(
        id=grant_id,
        customer_account_id=user_id,
        auth_realm_id=auth_realm_id,
        service_identity_id=service_identity_id,
        expires_at=expires_at,
    )

    class FakeDb:
        async def get(self, model, item_id):
            assert model is gift_routes.EntitlementGrantModel
            assert item_id == grant_id
            return grant

    class FakeMobileUserRepository:
        def __init__(self, _db) -> None:
            pass

        async def get_by_id(self, item_id):
            assert item_id == user_id
            return user

        async def update(self, item):
            assert item is user

    class FakeAttemptService:
        record = None

        async def begin(self, **kwargs):
            if type(self).record is None:
                type(self).record = SimpleNamespace(status="pending", request_hash=kwargs["request_hash"])
                return SimpleNamespace(
                    gift_record=type(self).record,
                    customer_record=type(self).record,
                    should_mutate=True,
                )
            assert type(self).record.request_hash == kwargs["request_hash"]
            return SimpleNamespace(
                gift_record=type(self).record,
                customer_record=type(self).record,
                should_mutate=False,
            )

        async def mark_reconciliation_required(self, decision):
            decision.gift_record.status = "reconciliation_required"

        async def mark_completed(self, decision, *, user_ref):
            assert user_ref.require_numeric_id() == 42
            decision.gift_record.status = "completed"

    binding_calls = []

    class FakeIdentityBinding:
        def __init__(self, _db) -> None:
            pass

        async def validate_target(self, **kwargs):
            assert kwargs["customer_account_id"] == user_id

        async def execute(self, **kwargs):
            binding_calls.append(kwargs)

    class FakeGateway:
        def __init__(self) -> None:
            self.requests = []

        async def provision_gift_access(self, request):
            self.requests.append(request)
            return GiftProvisioningResult(
                customer_account_id=request.customer_account_id,
                gift_code_id=request.gift_code_id,
                remnawave_uuid=None,
                remnawave_user_id=42,
                profile_id=request.profile_id,
                status="active",
                expires_at=request.access_expires_at,
                subscription_url="https://sub.example.test/redacted",
                created=True,
            )

    async def no_existing_identity(_db, _user):
        return None

    persisted = []

    async def persist_mobile(_db, *, customer, remnawave_user_id, remnawave_uuid, source):
        assert customer is user
        persisted.append((remnawave_user_id, remnawave_uuid, source))

    monkeypatch.setattr(gift_routes, "MobileUserRepository", FakeMobileUserRepository)
    attempts = FakeAttemptService()
    monkeypatch.setattr(gift_routes, "_gift_provisioning_attempts", lambda _db, *, is_create: attempts)
    monkeypatch.setattr(gift_routes, "AsyncSessionLocal", lambda: _MarkerContext(object()))
    monkeypatch.setattr(gift_routes, "BindProvisionedRemnawaveServiceIdentityUseCase", FakeIdentityBinding)
    monkeypatch.setattr(gift_routes, "resolve_exact_mapped_mobile_user_ref", no_existing_identity)
    monkeypatch.setattr(gift_routes, "persist_runtime_mapped_mobile_identity", persist_mobile)
    gateway = FakeGateway()

    await gift_routes.provision_redeemed_gift_access(
        db=FakeDb(),
        user_id=user_id,
        result=_result(grant_id=grant_id, gift_code_id=gift_code_id, expires_at=expires_at),
        provisioning_gateway=gateway,
    )

    assert len(gateway.requests) == 1
    assert gateway.requests[0].device_limit == 3
    assert persisted == [(42, None, "gift_redemption")]
    assert binding_calls == [
        {
            "service_identity_id": service_identity_id,
            "customer_account_id": user_id,
            "auth_realm_id": auth_realm_id,
            "remnawave_user_id": 42,
            "remnawave_uuid": None,
            "mapping_source": "gift_redemption",
        }
    ]
    assert FakeAttemptService.record.status == "completed"
    assert user.subscription_url == "https://sub.example.test/redacted"


@pytest.mark.asyncio
async def test_gift_ambiguous_create_is_latched_and_never_reposted(monkeypatch) -> None:
    user_id = uuid4()
    auth_realm_id = uuid4()
    service_identity_id = uuid4()
    grant_id = uuid4()
    gift_code_id = uuid4()
    expires_at = datetime(2026, 10, 1, tzinfo=UTC)
    user = SimpleNamespace(
        id=user_id,
        auth_realm_id=auth_realm_id,
        email="gift@example.test",
        username=None,
        telegram_id=None,
        remnawave_user_id=None,
        remnawave_uuid=None,
        subscription_url=None,
    )
    grant = SimpleNamespace(
        customer_account_id=user_id,
        auth_realm_id=auth_realm_id,
        service_identity_id=service_identity_id,
        expires_at=expires_at,
    )

    class FakeDb:
        async def get(self, _model, _item_id):
            return grant

    class FakeMobileUserRepository:
        def __init__(self, _db) -> None:
            pass

        async def get_by_id(self, _item_id):
            return user

        async def update(self, _item):
            raise AssertionError("ambiguous create must not publish local access")

    class FakeAttemptService:
        record = None

        async def begin(self, **kwargs):
            if type(self).record is None:
                type(self).record = SimpleNamespace(status="pending", request_hash=kwargs["request_hash"])
                return SimpleNamespace(
                    gift_record=type(self).record,
                    customer_record=type(self).record,
                    should_mutate=True,
                )
            return SimpleNamespace(
                gift_record=type(self).record,
                customer_record=type(self).record,
                should_mutate=False,
            )

        async def mark_reconciliation_required(self, decision):
            decision.gift_record.status = "reconciliation_required"

    class FakeIdentityBinding:
        def __init__(self, _db) -> None:
            pass

        async def validate_target(self, **_kwargs):
            return None

        async def execute(self, **_kwargs):
            raise AssertionError("ambiguous create must not bind an identity")

    class AmbiguousGateway:
        def __init__(self) -> None:
            self.calls = 0

        async def provision_gift_access(self, _request):
            self.calls += 1
            raise RuntimeError("transport outcome unknown")

    async def no_existing_identity(_db, _user):
        return None

    monkeypatch.setattr(gift_routes, "MobileUserRepository", FakeMobileUserRepository)
    attempts = FakeAttemptService()
    monkeypatch.setattr(gift_routes, "_gift_provisioning_attempts", lambda _db, *, is_create: attempts)
    monkeypatch.setattr(gift_routes, "AsyncSessionLocal", lambda: _MarkerContext(object()))
    monkeypatch.setattr(gift_routes, "BindProvisionedRemnawaveServiceIdentityUseCase", FakeIdentityBinding)
    monkeypatch.setattr(gift_routes, "resolve_exact_mapped_mobile_user_ref", no_existing_identity)
    gateway = AmbiguousGateway()
    result = _result(grant_id=grant_id, gift_code_id=gift_code_id, expires_at=expires_at)

    for _attempt in range(2):
        with pytest.raises(gift_routes.HTTPException) as exc_info:
            await gift_routes.provision_redeemed_gift_access(
                db=FakeDb(),
                user_id=user_id,
                result=result,
                provisioning_gateway=gateway,
            )
        assert exc_info.value.status_code == 409

    assert gateway.calls == 1
    assert FakeAttemptService.record.status == "reconciliation_required"


@pytest.mark.asyncio
async def test_gift_ambiguous_existing_user_update_is_latched_and_never_reposted(monkeypatch) -> None:
    user_id = uuid4()
    auth_realm_id = uuid4()
    grant_id = uuid4()
    gift_code_id = uuid4()
    expires_at = datetime(2026, 10, 1, tzinfo=UTC)
    user = SimpleNamespace(
        id=user_id,
        auth_realm_id=auth_realm_id,
        email="gift@example.test",
        username=None,
        telegram_id=None,
        remnawave_user_id=42,
        remnawave_uuid=None,
        subscription_url=None,
    )
    grant = SimpleNamespace(
        customer_account_id=user_id,
        auth_realm_id=auth_realm_id,
        service_identity_id=uuid4(),
        expires_at=expires_at,
    )

    class FakeDb:
        async def get(self, _model, _item_id):
            return grant

    class FakeMobileUserRepository:
        def __init__(self, _db) -> None:
            pass

        async def get_by_id(self, _item_id):
            return user

    class FakeUpdateAttemptService:
        record = None

        async def begin(self, **kwargs):
            if type(self).record is None:
                type(self).record = SimpleNamespace(status="pending", request_hash=kwargs["request_hash"])
                return SimpleNamespace(
                    gift_record=type(self).record,
                    customer_record=type(self).record,
                    should_mutate=True,
                )
            assert type(self).record.request_hash == kwargs["request_hash"]
            return SimpleNamespace(
                gift_record=type(self).record,
                customer_record=type(self).record,
                should_mutate=False,
            )

        async def mark_reconciliation_required(self, decision):
            decision.gift_record.status = "reconciliation_required"

    class FakeIdentityBinding:
        def __init__(self, _db) -> None:
            pass

        async def validate_target(self, **_kwargs):
            return None

    class AmbiguousUpdateGateway:
        def __init__(self) -> None:
            self.calls = 0

        async def provision_gift_access(self, request):
            assert request.existing_remnawave_user_id == 42
            self.calls += 1
            raise RuntimeError("update outcome unknown")

    async def exact_existing_identity(_db, _user):
        return RemnawaveUserRef(id=42)

    monkeypatch.setattr(gift_routes, "MobileUserRepository", FakeMobileUserRepository)
    attempts = FakeUpdateAttemptService()
    monkeypatch.setattr(gift_routes, "_gift_provisioning_attempts", lambda _db, *, is_create: attempts)
    monkeypatch.setattr(gift_routes, "AsyncSessionLocal", lambda: _MarkerContext(object()))
    monkeypatch.setattr(gift_routes, "BindProvisionedRemnawaveServiceIdentityUseCase", FakeIdentityBinding)
    monkeypatch.setattr(gift_routes, "resolve_exact_mapped_mobile_user_ref", exact_existing_identity)
    gateway = AmbiguousUpdateGateway()
    result = _result(grant_id=grant_id, gift_code_id=gift_code_id, expires_at=expires_at)

    for _attempt in range(2):
        with pytest.raises(gift_routes.HTTPException) as exc_info:
            await gift_routes.provision_redeemed_gift_access(
                db=FakeDb(),
                user_id=user_id,
                result=result,
                provisioning_gateway=gateway,
            )
        assert exc_info.value.status_code == 409

    assert gateway.calls == 1
    assert FakeUpdateAttemptService.record.status == "reconciliation_required"


@pytest.mark.asyncio
async def test_gift_cross_customer_grant_is_rejected_before_provider_io(monkeypatch) -> None:
    user_id = uuid4()
    auth_realm_id = uuid4()
    grant = SimpleNamespace(
        customer_account_id=uuid4(),
        auth_realm_id=auth_realm_id,
        service_identity_id=uuid4(),
        expires_at=datetime(2026, 10, 1, tzinfo=UTC),
    )
    user = SimpleNamespace(id=user_id, auth_realm_id=auth_realm_id)

    class FakeDb:
        async def get(self, _model, _item_id):
            return grant

    class FakeMobileUserRepository:
        def __init__(self, _db) -> None:
            pass

        async def get_by_id(self, _item_id):
            return user

    gateway = SimpleNamespace(provision_gift_access=AsyncMock())
    monkeypatch.setattr(gift_routes, "MobileUserRepository", FakeMobileUserRepository)

    with pytest.raises(RuntimeError, match="does not belong"):
        await gift_routes.provision_redeemed_gift_access(
            db=FakeDb(),
            user_id=user_id,
            result=_result(grant_id=uuid4(), gift_code_id=uuid4(), expires_at=grant.expires_at),
            provisioning_gateway=gateway,
        )

    gateway.provision_gift_access.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("device_limit", [None, True, "3", 0, -1])
async def test_gift_invalid_snapshot_device_limit_fails_before_provider_mutation(
    monkeypatch,
    device_limit,
) -> None:
    user_id = uuid4()
    auth_realm_id = uuid4()
    grant_id = uuid4()
    gift_code_id = uuid4()
    expires_at = datetime(2026, 10, 1, tzinfo=UTC)
    user = SimpleNamespace(
        id=user_id,
        auth_realm_id=auth_realm_id,
        email="gift@example.test",
        username=None,
        telegram_id=None,
    )
    grant = SimpleNamespace(
        customer_account_id=user_id,
        auth_realm_id=auth_realm_id,
        service_identity_id=uuid4(),
        expires_at=expires_at,
    )

    class FakeDb:
        async def get(self, _model, _item_id):
            return grant

    update = AsyncMock()

    class FakeMobileUserRepository:
        def __init__(self, _db) -> None:
            pass

        async def get_by_id(self, _item_id):
            return user

        async def update(self, item):
            await update(item)

    execute_binding = AsyncMock()

    class FakeIdentityBinding:
        def __init__(self, _db) -> None:
            pass

        async def validate_target(self, **_kwargs):
            return None

        async def execute(self, **kwargs):
            await execute_binding(**kwargs)

    provider = AsyncMock()
    resolve_identity = AsyncMock()
    persist_identity = AsyncMock()
    monkeypatch.setattr(gift_routes, "MobileUserRepository", FakeMobileUserRepository)
    monkeypatch.setattr(gift_routes, "BindProvisionedRemnawaveServiceIdentityUseCase", FakeIdentityBinding)
    monkeypatch.setattr(gift_routes, "resolve_exact_mapped_mobile_user_ref", resolve_identity)
    monkeypatch.setattr(gift_routes, "persist_runtime_mapped_mobile_identity", persist_identity)
    monkeypatch.setattr(
        gift_routes,
        "_gift_provisioning_attempts",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("attempt marker must not start")),
    )

    with pytest.raises(RuntimeError, match="no valid device limit"):
        await gift_routes.provision_redeemed_gift_access(
            db=FakeDb(),
            user_id=user_id,
            result=_result(
                grant_id=grant_id,
                gift_code_id=gift_code_id,
                expires_at=expires_at,
                device_limit=device_limit,
            ),
            provisioning_gateway=SimpleNamespace(provision_gift_access=provider),
        )

    resolve_identity.assert_not_awaited()
    provider.assert_not_awaited()
    persist_identity.assert_not_awaited()
    execute_binding.assert_not_awaited()
    update.assert_not_awaited()
