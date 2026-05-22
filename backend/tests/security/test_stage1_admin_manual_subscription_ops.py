"""S1-ADM-006 manual subscription operation checks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

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
from src.infrastructure.remnawave.stage1_manual_subscription_gateway import (
    RemnawaveStage1ManualSubscriptionGateway,
)
from src.presentation.api.v1.admin import customer_support
from src.presentation.api.v1.admin.customer_support_schemas import (
    AdminCustomerManualSubscriptionRequest,
)


class FakeRemnawaveUserGateway:
    def __init__(self, *, current_user: User | None = None, applied_user: User | None = None) -> None:
        self.current_user = current_user
        self.applied_user = applied_user
        self.created: list[tuple[str, dict]] = []
        self.updated: list[tuple[UUID, dict]] = []

    async def get_by_uuid(self, uuid: UUID) -> User | None:
        return self.current_user

    async def create(self, username: str, **kwargs) -> User:
        self.created.append((username, kwargs))
        assert self.applied_user is not None
        return self.applied_user

    async def update(self, uuid: UUID, **kwargs) -> User:
        self.updated.append((uuid, kwargs))
        assert self.applied_user is not None
        return self.applied_user


def test_stage1_manual_subscription_permission_matrix_uses_subscription_create() -> None:
    assert can_apply_stage1_manual_subscription(AdminRole.OWNER_SUPER_ADMIN)
    assert can_apply_stage1_manual_subscription(AdminRole.SUPER_ADMIN)
    assert can_apply_stage1_manual_subscription(AdminRole.ADMIN)
    assert can_apply_stage1_manual_subscription(AdminRole.OPERATOR)
    assert not can_apply_stage1_manual_subscription(AdminRole.SUPPORT)
    assert not can_apply_stage1_manual_subscription(AdminRole.FINANCE)
    assert not can_apply_stage1_manual_subscription(AdminRole.VIEWER)
    assert has_permission(AdminRole.OPERATOR, Permission.SUBSCRIPTION_CREATE)


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
    )
    applied_vpn_user = _build_user(
        uuid=remnawave_uuid,
        short_uuid="old-short",
        subscription_url="https://sub.example.local/new-secret-token",
        expires_at=expected_expiry,
    )
    mobile_user = SimpleNamespace(
        id=user_id,
        email="alpha@example.test",
        username="alpha",
        telegram_id=123456,
        remnawave_uuid=str(remnawave_uuid),
        subscription_url="https://sub.example.local/old-secret-token",
        status="expired",
        is_active=False,
    )
    fake_gateway = FakeRemnawaveUserGateway(current_user=current_vpn_user, applied_user=applied_vpn_user)
    updated_users: list[object] = []
    audit_events: list[dict] = []

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

    monkeypatch.setattr(customer_support, "_require_mobile_user", fake_require_mobile_user)
    monkeypatch.setattr(customer_support, "RemnawaveUserGateway", lambda client: fake_gateway)
    monkeypatch.setattr(customer_support, "MobileUserRepository", FakeMobileUserRepository)
    monkeypatch.setattr(customer_support, "_write_required_audit_entry", fake_write_required_audit_entry)

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
        db=object(),
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
    assert fake_gateway.updated[0][0] == remnawave_uuid
    assert audit_events[0]["action"] == STAGE1_MANUAL_SUBSCRIPTION_ACTION
    audit_details = str(audit_events[0]["details"]).lower()
    response_payload = response.model_dump_json().lower()
    assert "old-secret-token" not in audit_details
    assert "new-secret-token" not in audit_details
    assert "https://" not in audit_details
    assert "old-secret-token" not in response_payload
    assert "new-secret-token" not in response_payload
    assert "https://" not in response_payload


def _build_user(
    *,
    uuid: UUID,
    short_uuid: str,
    subscription_url: str,
    expires_at: datetime,
) -> User:
    return User(
        uuid=uuid,
        username=f"cvpn_m_{uuid.hex[:28]}",
        status=UserStatus.ACTIVE,
        short_uuid=short_uuid,
        created_at=datetime(2026, 5, 4, 9, 0, tzinfo=UTC),
        updated_at=datetime(2026, 5, 4, 9, 30, tzinfo=UTC),
        expire_at=expires_at,
        subscription_url=subscription_url,
    )
