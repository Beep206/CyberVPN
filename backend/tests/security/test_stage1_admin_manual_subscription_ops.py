"""S1-ADM-006 manual subscription operation checks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from src.application.services.remnawave_identity_access import RemnawaveIdentityAccessConflict
from src.application.use_cases.auth.permissions import Permission, has_permission
from src.application.use_cases.subscriptions.stage1_manual_subscription import (
    STAGE1_MANUAL_SUBSCRIPTION_ACTION,
    Stage1ManualSubscriptionError,
    Stage1ManualSubscriptionService,
    build_stage1_manual_subscription_request,
    can_apply_stage1_manual_subscription,
)
from src.config.settings import settings
from src.domain.entities.user import User
from src.domain.enums import AdminRole, UserStatus
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.remnawave.stage1_manual_subscription_gateway import (
    RemnawaveStage1ManualSubscriptionGateway,
)
from src.infrastructure.remnawave.user_gateway import RemnawaveMutationAcceptedPending
from src.presentation.api.v1.admin import customer_support
from src.presentation.api.v1.admin.customer_support_schemas import (
    AdminCustomerManualSubscriptionRequest,
)

TASK2_PLAN_CODE = "premium_spb_de_exceptions"


class FakeRemnawaveUserGateway:
    def __init__(self, *, current_user: User | None = None, applied_user: User | None = None) -> None:
        self.current_user = current_user
        self.applied_user = applied_user
        self.created: list[tuple[str, dict]] = []
        self.updated: list[tuple[RemnawaveUserRef, dict]] = []

    async def get_by_uuid(self, uuid: UUID) -> User | None:
        return self.current_user

    async def get_by_ref(self, user_ref: RemnawaveUserRef) -> User | None:
        return self.current_user

    async def create(self, username: str, **kwargs) -> User:
        self.created.append((username, kwargs))
        assert self.applied_user is not None
        return self.applied_user

    async def update(self, user_ref: RemnawaveUserRef, **kwargs) -> User:
        self.updated.append((user_ref, kwargs))
        assert self.applied_user is not None
        return self.applied_user


class _AttemptResult:
    def __init__(self, record) -> None:
        self.record = record

    def scalars(self):
        return self

    def one_or_none(self):
        return self.record


class _ManualAttemptDb:
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


def test_stage1_manual_subscription_permission_matrix_uses_subscription_create() -> None:
    assert can_apply_stage1_manual_subscription(AdminRole.OWNER_SUPER_ADMIN)
    assert can_apply_stage1_manual_subscription(AdminRole.SUPER_ADMIN)
    assert can_apply_stage1_manual_subscription(AdminRole.ADMIN)
    assert can_apply_stage1_manual_subscription(AdminRole.OPERATOR)
    assert not can_apply_stage1_manual_subscription(AdminRole.SUPPORT)
    assert not can_apply_stage1_manual_subscription(AdminRole.FINANCE)
    assert not can_apply_stage1_manual_subscription(AdminRole.VIEWER)
    assert has_permission(AdminRole.OPERATOR, Permission.SUBSCRIPTION_CREATE)


def test_admin_manual_subscription_schema_accepts_task2_plan_code() -> None:
    request = AdminCustomerManualSubscriptionRequest(
        reason="grant Task2 access",
        plan_code=TASK2_PLAN_CODE,
        duration_days=30,
    )

    assert request.plan_code == TASK2_PLAN_CODE


@pytest.mark.asyncio
async def test_stage1_manual_subscription_service_extends_from_current_expiry_with_safe_audit() -> None:
    now = datetime(2026, 5, 4, 9, 30, tzinfo=UTC)
    customer_id = uuid4()
    remnawave_uuid = uuid4()
    current_expiry = now + timedelta(days=20)
    request = build_stage1_manual_subscription_request(
        customer_account_id=customer_id,
        actor_admin_id=uuid4(),
        email="alpha@example.test",
        username="alpha",
        telegram_id=123456,
        reason="manual beta support grant after provider failure",
        duration_days=30,
        requested_at=now,
        current_access_expires_at=current_expiry,
        traffic_limit_bytes=2_147_483_648,
        device_limit=3,
        existing_remnawave_user_id=73,
        existing_remnawave_uuid=str(remnawave_uuid),
        previous_subscription_url="https://sub.example.local/old-secret-token",
    )
    gateway = RemnawaveStage1ManualSubscriptionGateway(
        FakeRemnawaveUserGateway(
            applied_user=_build_user(
                uuid=remnawave_uuid,
                short_uuid="new-short",
                subscription_url="https://sub.example.local/manual-secret-token",
                expires_at=current_expiry + timedelta(days=30),
            ),
        )
    )

    result = await Stage1ManualSubscriptionService(gateway).apply(request)

    assert request.operation == "extend"
    assert request.access_starts_at == current_expiry
    assert result.expires_at == current_expiry + timedelta(days=30)
    assert result.operation == "extend"
    audit = result.to_audit_details(reason=request.reason)
    serialized = f"{result.to_safe_dict()} {audit}".lower()
    assert audit["audit_action"] == STAGE1_MANUAL_SUBSCRIPTION_ACTION
    assert audit["reason_length"] == len(request.reason)
    assert audit["config_delivery_required"] is True
    assert "manual-secret-token" not in serialized
    assert "new-short" not in serialized
    assert "https://" not in serialized


@pytest.mark.asyncio
async def test_stage1_manual_subscription_gateway_creates_new_remnawave_user(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2026, 5, 4, 9, 30, tzinfo=UTC)
    customer_id = uuid4()
    remnawave_uuid = uuid4()
    ru_bundle_squad_uuid = str(uuid4())
    monkeypatch.setattr(settings, "remnawave_ru_bundle_external_squad_uuid", ru_bundle_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_ru_bundle_plan_codes", "ru_start,ru_basic")
    request = build_stage1_manual_subscription_request(
        customer_account_id=customer_id,
        actor_admin_id=uuid4(),
        email="Beta@Example.Test",
        username=None,
        telegram_id=None,
        plan_code="ru_basic",
        reason="grant controlled beta access",
        duration_days=14,
        requested_at=now,
        traffic_limit_bytes=None,
        device_limit=2,
        previous_subscription_url=None,
    )
    fake_gateway = FakeRemnawaveUserGateway(
        applied_user=_build_user(
            uuid=remnawave_uuid,
            short_uuid="manual-short",
            subscription_url="https://sub.example.local/create-secret-token",
            expires_at=now + timedelta(days=14),
        ),
    )

    result = await RemnawaveStage1ManualSubscriptionGateway(fake_gateway).apply_manual_subscription(request)

    assert result.created is True
    assert result.remnawave_uuid == str(remnawave_uuid)
    assert fake_gateway.created[0][0] == f"cvpn_m_{customer_id.hex[:28]}"
    assert len(fake_gateway.created[0][0]) <= 36
    payload = fake_gateway.created[0][1]
    assert payload["email"] == "beta@example.test"
    assert payload["expire_at"] == now + timedelta(days=14)
    assert payload["traffic_limit_bytes"] is None
    assert payload["hwid_device_limit"] == 2
    assert payload["status"] == UserStatus.ACTIVE
    assert payload["external_squad_uuid"] == ru_bundle_squad_uuid


@pytest.mark.asyncio
async def test_stage1_manual_subscription_service_accepts_numeric_only_create() -> None:
    now = datetime(2026, 5, 4, 9, 30, tzinfo=UTC)
    request = build_stage1_manual_subscription_request(
        customer_account_id=uuid4(),
        actor_admin_id=uuid4(),
        email="numeric-only@example.test",
        username=None,
        telegram_id=None,
        reason="grant after target 3.4 numeric identity cutover",
        duration_days=14,
        requested_at=now,
        traffic_limit_bytes=None,
        device_limit=2,
        previous_subscription_url=None,
    )
    fake_gateway = FakeRemnawaveUserGateway(
        applied_user=_build_user(
            uuid=None,
            short_uuid="numeric-only-short",
            subscription_url="https://sub.example.local/numeric-only-secret",
            expires_at=now + timedelta(days=14),
            remnawave_id=4201,
        ),
    )

    result = await Stage1ManualSubscriptionService(RemnawaveStage1ManualSubscriptionGateway(fake_gateway)).apply(
        request
    )

    assert result.created is True
    assert result.remnawave_user_id == 4201
    assert result.remnawave_uuid is None


@pytest.mark.asyncio
async def test_stage1_manual_subscription_gateway_uses_smart_ru_external_squad(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 5, 4, 9, 30, tzinfo=UTC)
    customer_id = uuid4()
    remnawave_uuid = uuid4()
    smart_ru_squad_uuid = str(uuid4())
    smart_ru_internal_squad_uuid = str(uuid4())
    monkeypatch.setattr(settings, "remnawave_smart_ru_external_squad_uuid", smart_ru_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_smart_ru_internal_squad_uuid", smart_ru_internal_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")
    request = build_stage1_manual_subscription_request(
        customer_account_id=customer_id,
        actor_admin_id=uuid4(),
        email="Premium@Example.Test",
        username=None,
        telegram_id=None,
        plan_code="premium_smart_ru",
        reason="grant controlled premium smart ru access",
        duration_days=30,
        requested_at=now,
        traffic_limit_bytes=None,
        device_limit=5,
        previous_subscription_url=None,
    )
    fake_gateway = FakeRemnawaveUserGateway(
        applied_user=_build_user(
            uuid=remnawave_uuid,
            short_uuid="smart-manual-short",
            subscription_url="https://sub.example.local/smart-secret-token",
            expires_at=now + timedelta(days=30),
        ),
    )

    result = await RemnawaveStage1ManualSubscriptionGateway(fake_gateway).apply_manual_subscription(request)

    assert result.created is True
    assert result.remnawave_uuid == str(remnawave_uuid)
    payload = fake_gateway.created[0][1]
    assert payload["email"] == "premium@example.test"
    assert payload["hwid_device_limit"] == 5
    assert payload["external_squad_uuid"] == smart_ru_squad_uuid
    assert payload["active_internal_squads"] == [smart_ru_internal_squad_uuid]


@pytest.mark.asyncio
async def test_stage1_manual_subscription_gateway_updates_existing_smart_ru_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 5, 4, 9, 30, tzinfo=UTC)
    customer_id = uuid4()
    remnawave_uuid = uuid4()
    smart_ru_squad_uuid = str(uuid4())
    smart_ru_internal_squad_uuid = str(uuid4())
    monkeypatch.setattr(settings, "remnawave_smart_ru_external_squad_uuid", smart_ru_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_smart_ru_internal_squad_uuid", smart_ru_internal_squad_uuid)
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")
    request = build_stage1_manual_subscription_request(
        customer_account_id=customer_id,
        actor_admin_id=uuid4(),
        email="Premium@Example.Test",
        username=None,
        telegram_id=None,
        plan_code="premium_smart_ru",
        reason="extend controlled premium smart ru access",
        duration_days=30,
        requested_at=now,
        traffic_limit_bytes=None,
        device_limit=5,
        existing_remnawave_user_id=74,
        existing_remnawave_uuid=str(remnawave_uuid),
        previous_subscription_url="https://sub.example.local/old-smart-token",
    )
    fake_gateway = FakeRemnawaveUserGateway(
        applied_user=_build_user(
            uuid=remnawave_uuid,
            short_uuid="smart-manual-short",
            subscription_url="https://sub.example.local/new-smart-token",
            expires_at=now + timedelta(days=30),
        ),
    )

    result = await RemnawaveStage1ManualSubscriptionGateway(fake_gateway).apply_manual_subscription(request)

    assert result.created is False
    assert result.remnawave_uuid == str(remnawave_uuid)
    assert fake_gateway.created == []
    assert fake_gateway.updated[0][0] == RemnawaveUserRef(id=74, legacy_uuid=remnawave_uuid)
    payload = fake_gateway.updated[0][1]
    assert payload["external_squad_uuid"] == smart_ru_squad_uuid
    assert payload["active_internal_squads"] == [smart_ru_internal_squad_uuid]


@pytest.mark.asyncio
async def test_stage1_manual_subscription_gateway_rejects_legacy_only_existing_identity() -> None:
    now = datetime(2026, 5, 4, 9, 30, tzinfo=UTC)
    fake_gateway = FakeRemnawaveUserGateway()
    request = build_stage1_manual_subscription_request(
        customer_account_id=uuid4(),
        actor_admin_id=uuid4(),
        email="manual@example.test",
        username=None,
        telegram_id=None,
        reason="extend only after numeric reconciliation",
        duration_days=30,
        requested_at=now,
        traffic_limit_bytes=None,
        device_limit=3,
        existing_remnawave_uuid=str(uuid4()),
        previous_subscription_url=None,
    )

    with pytest.raises(Stage1ManualSubscriptionError, match="numeric identity is not reconciled"):
        await RemnawaveStage1ManualSubscriptionGateway(fake_gateway).apply_manual_subscription(request)

    assert fake_gateway.created == []
    assert fake_gateway.updated == []


@pytest.mark.asyncio
async def test_stage1_manual_subscription_gateway_fails_closed_when_smart_ru_squads_are_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 5, 4, 9, 30, tzinfo=UTC)
    monkeypatch.setattr(settings, "remnawave_smart_ru_external_squad_uuid", "")
    monkeypatch.setattr(settings, "remnawave_smart_ru_internal_squad_uuid", str(uuid4()))
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")
    request = build_stage1_manual_subscription_request(
        customer_account_id=uuid4(),
        actor_admin_id=uuid4(),
        email="Premium@Example.Test",
        username=None,
        telegram_id=None,
        plan_code="premium_smart_ru",
        reason="grant controlled premium smart ru access",
        duration_days=30,
        requested_at=now,
        traffic_limit_bytes=None,
        device_limit=5,
        previous_subscription_url=None,
    )
    fake_gateway = FakeRemnawaveUserGateway(
        applied_user=_build_user(
            uuid=uuid4(),
            short_uuid="unused-smart-manual-short",
            subscription_url="https://sub.example.local/unused-smart-token",
            expires_at=now + timedelta(days=30),
        ),
    )

    with pytest.raises(Stage1ManualSubscriptionError, match="REMNAWAVE_SMART_RU_EXTERNAL_SQUAD_UUID"):
        await RemnawaveStage1ManualSubscriptionGateway(fake_gateway).apply_manual_subscription(request)

    assert fake_gateway.created == []
    assert fake_gateway.updated == []


def test_stage1_manual_subscription_request_rejects_unsafe_values() -> None:
    base = {
        "customer_account_id": uuid4(),
        "actor_admin_id": uuid4(),
        "email": "alpha@example.test",
        "username": None,
        "telegram_id": None,
        "reason": "manual grant",
        "duration_days": 30,
        "requested_at": datetime(2026, 5, 4, 9, 30, tzinfo=UTC),
        "traffic_limit_bytes": None,
        "device_limit": 1,
    }

    with pytest.raises(Stage1ManualSubscriptionError, match="reason"):
        build_stage1_manual_subscription_request(**{**base, "reason": "no"})
    with pytest.raises(Stage1ManualSubscriptionError, match="duration"):
        build_stage1_manual_subscription_request(**{**base, "duration_days": 366})
    with pytest.raises(Stage1ManualSubscriptionError, match="device"):
        build_stage1_manual_subscription_request(**{**base, "device_limit": 11})
    with pytest.raises(Stage1ManualSubscriptionError, match="traffic"):
        build_stage1_manual_subscription_request(**{**base, "traffic_limit_bytes": 0})


@pytest.mark.asyncio
async def test_admin_route_applies_manual_subscription_with_required_sanitized_audit(monkeypatch) -> None:
    route_now = datetime.now(UTC)
    user_id = uuid4()
    remnawave_uuid = uuid4()
    admin_id = uuid4()
    current_expiry = route_now + timedelta(days=1)
    expected_expiry = current_expiry + timedelta(days=30)
    current_vpn_user = _build_user(
        uuid=remnawave_uuid,
        short_uuid="old-short",
        subscription_url="https://sub.example.local/old-secret-token",
        expires_at=current_expiry,
        remnawave_id=75,
    )
    applied_vpn_user = _build_user(
        uuid=remnawave_uuid,
        short_uuid="old-short",
        subscription_url="https://sub.example.local/new-secret-token",
        expires_at=expected_expiry,
        remnawave_id=75,
    )
    mobile_user = SimpleNamespace(
        id=user_id,
        email="alpha@example.test",
        username="alpha",
        telegram_id=123456,
        remnawave_user_id=75,
        remnawave_uuid=str(remnawave_uuid),
        subscription_url="https://sub.example.local/old-secret-token",
        status="expired",
        is_active=False,
    )
    fake_gateway = FakeRemnawaveUserGateway(current_user=current_vpn_user, applied_user=applied_vpn_user)
    updated_users: list[object] = []
    audit_events: list[dict] = []
    resolved_mappings: list[dict] = []
    persisted_mappings: list[dict] = []

    async def fake_require_mobile_user(received_user_id, db):
        assert received_user_id == user_id
        return mobile_user

    class FakeMobileUserRepository:
        def __init__(self, db) -> None:
            self.db = db

        async def update(self, model):
            updated_users.append(model)
            return model

    async def fake_write_required_audit_entry(**kwargs) -> None:
        audit_events.append(kwargs)

    async def fake_resolve_exact_mapped_mobile_user_ref(db, customer):
        resolved_mappings.append({"db": db, "customer": customer})
        return RemnawaveUserRef(id=75, legacy_uuid=remnawave_uuid)

    async def fake_persist_runtime_mapped_mobile_identity(db, **kwargs):
        persisted_mappings.append({"db": db, **kwargs})
        return RemnawaveUserRef(id=75, legacy_uuid=remnawave_uuid)

    monkeypatch.setattr(customer_support, "_require_mobile_user", fake_require_mobile_user)
    monkeypatch.setattr(customer_support, "RemnawaveUserGateway", lambda client: fake_gateway)
    monkeypatch.setattr(customer_support, "MobileUserRepository", FakeMobileUserRepository)
    monkeypatch.setattr(customer_support, "_write_required_audit_entry", fake_write_required_audit_entry)
    monkeypatch.setattr(
        customer_support,
        "resolve_exact_mapped_mobile_user_ref",
        fake_resolve_exact_mapped_mobile_user_ref,
    )
    monkeypatch.setattr(
        customer_support,
        "persist_runtime_mapped_mobile_identity",
        fake_persist_runtime_mapped_mobile_identity,
    )

    db = object()

    response = await customer_support.apply_manual_customer_subscription(
        user_id=user_id,
        body=AdminCustomerManualSubscriptionRequest(
            reason="paid provider failed; apply controlled beta access",
            duration_days=30,
            device_limit=3,
            traffic_limit_bytes=2_147_483_648,
        ),
        request=SimpleNamespace(client=None, headers={}),
        current_user=SimpleNamespace(id=admin_id),
        db=db,
        client=object(),
    )

    assert response.user_id == user_id
    assert response.remnawave_uuid == remnawave_uuid
    assert response.operation == "extend"
    assert response.duration_days == 30
    assert response.config_delivery_required is True
    assert response.audit_action == STAGE1_MANUAL_SUBSCRIPTION_ACTION
    assert mobile_user.subscription_url == "https://sub.example.local/new-secret-token"
    assert mobile_user.status == UserStatus.ACTIVE.value
    assert mobile_user.is_active is True
    assert updated_users == [mobile_user]
    assert fake_gateway.updated[0][0] == RemnawaveUserRef(id=75, legacy_uuid=remnawave_uuid)
    assert resolved_mappings == [
        {
            "db": db,
            "customer": mobile_user,
        }
    ]
    assert persisted_mappings == [
        {
            "db": db,
            "customer": mobile_user,
            "remnawave_user_id": 75,
            "remnawave_uuid": str(remnawave_uuid),
            "source": "admin_customer_support_manual_subscription",
        }
    ]
    assert audit_events[0]["action"] == STAGE1_MANUAL_SUBSCRIPTION_ACTION
    audit_details = str(audit_events[0]["details"]).lower()
    response_payload = response.model_dump_json().lower()
    assert "old-secret-token" not in audit_details
    assert "new-secret-token" not in audit_details
    assert "https://" not in audit_details
    assert "old-secret-token" not in response_payload
    assert "new-secret-token" not in response_payload
    assert "https://" not in response_payload


@pytest.mark.asyncio
async def test_admin_route_rejects_unreconciled_manual_subscription_before_provider_mutation(monkeypatch) -> None:
    user_id = uuid4()
    remnawave_uuid = uuid4()
    mobile_user = SimpleNamespace(
        id=user_id,
        email="conflict@example.test",
        username="conflict",
        telegram_id=None,
        remnawave_user_id=75,
        remnawave_uuid=str(remnawave_uuid),
        subscription_url=None,
        status=UserStatus.ACTIVE.value,
        is_active=True,
    )
    fake_gateway = FakeRemnawaveUserGateway()

    async def fake_require_mobile_user(received_user_id, db):
        assert received_user_id == user_id
        return mobile_user

    async def fake_resolve_exact_mapped_mobile_user_ref(db, customer):
        raise RemnawaveIdentityAccessConflict("conflicting ledger row")

    monkeypatch.setattr(customer_support, "_require_mobile_user", fake_require_mobile_user)
    monkeypatch.setattr(customer_support, "RemnawaveUserGateway", lambda client: fake_gateway)
    monkeypatch.setattr(
        customer_support,
        "resolve_exact_mapped_mobile_user_ref",
        fake_resolve_exact_mapped_mobile_user_ref,
    )

    with pytest.raises(HTTPException) as exc_info:
        await customer_support.apply_manual_customer_subscription(
            user_id=user_id,
            body=AdminCustomerManualSubscriptionRequest(
                reason="do not mutate a conflicting mapped identity",
                duration_days=30,
            ),
            request=SimpleNamespace(client=None, headers={}),
            current_user=SimpleNamespace(id=uuid4()),
            db=object(),
            client=object(),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Remnawave identity reconciliation required"
    assert fake_gateway.created == []
    assert fake_gateway.updated == []


@pytest.mark.asyncio
async def test_admin_manual_create_ambiguity_is_durable_and_never_reposted(monkeypatch) -> None:
    user_id = uuid4()
    mobile_user = SimpleNamespace(
        id=user_id,
        email="manual@example.test",
        username=None,
        telegram_id=None,
        remnawave_user_id=None,
        remnawave_uuid=None,
        subscription_url=None,
        status=UserStatus.ACTIVE.value,
        is_active=True,
    )
    db = _ManualAttemptDb()

    class AmbiguousGateway(FakeRemnawaveUserGateway):
        async def create(self, username: str, **kwargs) -> User:
            self.created.append((username, kwargs))
            raise RemnawaveMutationAcceptedPending(operation="create")

    gateway = AmbiguousGateway()

    async def fake_require_mobile_user(_user_id, _db):
        return mobile_user

    async def no_identity(_db, _customer):
        return None

    monkeypatch.setattr(customer_support, "_require_mobile_user", fake_require_mobile_user)
    monkeypatch.setattr(customer_support, "_resolve_customer_vpn_ref", no_identity)
    monkeypatch.setattr(customer_support, "RemnawaveUserGateway", lambda client: gateway)

    for _attempt in range(2):
        with pytest.raises(HTTPException) as exc_info:
            await customer_support.apply_manual_customer_subscription(
                user_id=user_id,
                body=AdminCustomerManualSubscriptionRequest(
                    reason="operator approved reconciliation-safe manual grant",
                    duration_days=30,
                ),
                request=SimpleNamespace(client=None, headers={}),
                current_user=SimpleNamespace(id=uuid4()),
                db=db,
                client=object(),
                _=None,
            )
        assert exc_info.value.status_code == 409

    assert len(gateway.created) == 1
    assert db.record.status == "reconciliation_required"
    assert db.commits == 2


def _build_user(
    *,
    uuid: UUID | None,
    short_uuid: str,
    subscription_url: str,
    expires_at: datetime,
    remnawave_id: int = 73,
) -> User:
    return User(
        uuid=uuid,
        username=f"cvpn_m_{uuid.hex[:28] if uuid is not None else 'numeric_only'}",
        status=UserStatus.ACTIVE,
        short_uuid=short_uuid,
        created_at=datetime(2026, 5, 4, 9, 0, tzinfo=UTC),
        updated_at=datetime(2026, 5, 4, 9, 30, tzinfo=UTC),
        remnawave_id=remnawave_id,
        expire_at=expires_at,
        subscription_url=subscription_url,
    )
