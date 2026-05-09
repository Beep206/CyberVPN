"""S1-VPN-008 credential regeneration checks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from src.application.use_cases.auth.permissions import Permission, has_permission
from src.application.use_cases.subscriptions.stage1_credential_regeneration import (
    STAGE1_CREDENTIAL_REGENERATION_ACTION,
    Stage1CredentialRegenerationService,
    build_stage1_credential_regeneration_request,
    can_regenerate_stage1_credentials,
)
from src.domain.entities.user import User
from src.domain.enums import AdminRole, UserStatus
from src.infrastructure.remnawave.stage1_credential_regeneration_gateway import (
    RemnawaveStage1CredentialRegenerationGateway,
)
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway
from src.presentation.api.v1.admin import customer_support
from src.presentation.api.v1.admin.customer_support_schemas import AdminCustomerCredentialRegenerationRequest


class FakeRemnawaveUserGateway:
    def __init__(self, current_user: User | None = None, regenerated_user: User | None = None) -> None:
        self.current_user = current_user
        self.regenerated_user = regenerated_user
        self.revoked: list[tuple[UUID, bool]] = []

    async def get_by_uuid(self, uuid: UUID) -> User | None:
        return self.current_user

    async def revoke_subscription(self, uuid: UUID, *, revoke_only_passwords: bool = False) -> User:
        self.revoked.append((uuid, revoke_only_passwords))
        assert self.regenerated_user is not None
        return self.regenerated_user


class FakeValidatedUser:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def model_dump(self, **kwargs) -> dict:
        return self._payload


class RecordingClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls: list[tuple[str, object, dict]] = []

    async def post_validated(self, path: str, schema, **kwargs) -> FakeValidatedUser:
        self.calls.append((path, schema, kwargs))
        return FakeValidatedUser(self.payload)


def test_stage1_credential_regeneration_permission_matrix() -> None:
    assert can_regenerate_stage1_credentials(AdminRole.OWNER_SUPER_ADMIN)
    assert can_regenerate_stage1_credentials(AdminRole.SUPER_ADMIN)
    assert can_regenerate_stage1_credentials(AdminRole.ADMIN)
    assert can_regenerate_stage1_credentials(AdminRole.SUPPORT)
    assert not can_regenerate_stage1_credentials(AdminRole.OPERATOR)
    assert not can_regenerate_stage1_credentials(AdminRole.VIEWER)
    assert has_permission(AdminRole.ADMIN, Permission.VPN_CREDENTIAL_REGENERATE)
    assert has_permission(AdminRole.SUPPORT, Permission.VPN_CREDENTIAL_REGENERATE)


@pytest.mark.asyncio
async def test_stage1_credential_regeneration_service_returns_safe_audit_payload() -> None:
    now = datetime(2026, 5, 4, 9, 30, tzinfo=UTC)
    customer_id = uuid4()
    remnawave_uuid = uuid4()
    request = build_stage1_credential_regeneration_request(
        customer_account_id=customer_id,
        remnawave_uuid=str(remnawave_uuid),
        actor_admin_id=uuid4(),
        reason="user lost device; rotate credentials",
        previous_short_uuid="old-short",
        previous_subscription_url="https://sub.example.local/old-secret-token",
        requested_at=now,
    )
    gateway = RemnawaveStage1CredentialRegenerationGateway(
        FakeRemnawaveUserGateway(
            regenerated_user=_build_user(
                uuid=remnawave_uuid,
                short_uuid="new-short",
                subscription_url="https://sub.example.local/new-secret-token",
                expires_at=now + timedelta(days=30),
            ),
        )
    )

    result = await Stage1CredentialRegenerationService(gateway).regenerate(request)

    assert result.subscription_url_changed is True
    assert result.current_short_uuid == "new-short"
    assert result.short_uuid_changed is True
    safe = result.to_safe_dict()
    audit = result.to_audit_details(reason=request.reason)
    serialized = f"{safe} {audit}".lower()
    assert audit["audit_action"] == STAGE1_CREDENTIAL_REGENERATION_ACTION
    assert audit["reason_length"] == len(request.reason)
    assert "old-secret-token" not in serialized
    assert "new-secret-token" not in serialized
    assert "old-short" not in serialized
    assert "new-short" not in serialized
    assert "https://" not in serialized
    assert "trojanpassword" not in serialized
    assert "sspassword" not in serialized
    assert "token" not in serialized


@pytest.mark.asyncio
async def test_remnawave_user_gateway_calls_official_revoke_endpoint() -> None:
    remnawave_uuid = uuid4()
    client = RecordingClient(
        _raw_remnawave_user(
            uuid=remnawave_uuid,
            short_uuid="rotated-short",
            subscription_url="https://sub.example.local/rotated-secret",
        )
    )
    gateway = RemnawaveUserGateway(client=client)

    user = await gateway.revoke_subscription(remnawave_uuid, revoke_only_passwords=True)

    assert user.short_uuid == "rotated-short"
    assert client.calls[0][0] == f"/api/users/{remnawave_uuid}/actions/revoke"
    assert client.calls[0][2]["json"] == {"revokeOnlyPasswords": True}


@pytest.mark.asyncio
async def test_admin_route_regenerates_credentials_with_required_sanitized_audit(monkeypatch) -> None:
    now = datetime(2026, 5, 4, 9, 30, tzinfo=UTC)
    user_id = uuid4()
    remnawave_uuid = uuid4()
    admin_id = uuid4()
    mobile_user = SimpleNamespace(
        id=user_id,
        remnawave_uuid=str(remnawave_uuid),
        subscription_url="https://sub.example.local/old-secret-token",
    )
    current_vpn_user = _build_user(
        uuid=remnawave_uuid,
        short_uuid="old-short",
        subscription_url="https://sub.example.local/old-secret-token",
        expires_at=now + timedelta(days=30),
    )
    regenerated_user = _build_user(
        uuid=remnawave_uuid,
        short_uuid="new-short",
        subscription_url="https://sub.example.local/new-secret-token",
        expires_at=now + timedelta(days=30),
    )
    fake_gateway = FakeRemnawaveUserGateway(current_user=current_vpn_user, regenerated_user=regenerated_user)
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

    response = await customer_support.regenerate_customer_vpn_credentials(
        user_id=user_id,
        body=AdminCustomerCredentialRegenerationRequest(reason="support requested credential rotation"),
        request=SimpleNamespace(client=None, headers={}),
        current_user=SimpleNamespace(id=admin_id),
        db=object(),
        client=object(),
    )

    assert response.user_id == user_id
    assert response.remnawave_uuid == remnawave_uuid
    assert response.short_uuid_changed is True
    assert response.subscription_url_changed is True
    assert response.config_delivery_required is True
    assert response.audit_action == STAGE1_CREDENTIAL_REGENERATION_ACTION
    assert mobile_user.subscription_url == "https://sub.example.local/new-secret-token"
    assert updated_users == [mobile_user]
    assert fake_gateway.revoked == [(remnawave_uuid, False)]
    assert audit_events[0]["action"] == STAGE1_CREDENTIAL_REGENERATION_ACTION
    audit_details = str(audit_events[0]["details"]).lower()
    response_payload = response.model_dump_json().lower()
    assert "old-secret-token" not in audit_details
    assert "new-secret-token" not in audit_details
    assert "old-short" not in audit_details
    assert "new-short" not in audit_details
    assert "https://" not in audit_details
    assert "secret-token" not in response_payload


def _build_user(
    *,
    uuid: UUID,
    short_uuid: str,
    subscription_url: str,
    expires_at: datetime,
) -> User:
    return User(
        uuid=uuid,
        username=f"cvpn_paid_{uuid.hex}",
        status=UserStatus.ACTIVE,
        short_uuid=short_uuid,
        created_at=datetime(2026, 5, 4, 9, 0, tzinfo=UTC),
        updated_at=datetime(2026, 5, 4, 9, 30, tzinfo=UTC),
        expire_at=expires_at,
        subscription_url=subscription_url,
    )


def _raw_remnawave_user(
    *,
    uuid: UUID,
    short_uuid: str,
    subscription_url: str,
) -> dict:
    return {
        "uuid": str(uuid),
        "username": f"cvpn_paid_{uuid.hex}",
        "status": "ACTIVE",
        "shortUuid": short_uuid,
        "createdAt": "2026-05-04T09:00:00+00:00",
        "updatedAt": "2026-05-04T09:30:00+00:00",
        "subscriptionUuid": str(uuid4()),
        "subscriptionUrl": subscription_url,
        "expireAt": "2026-06-03T09:30:00+00:00",
        "trafficLimitBytes": 2147483648,
        "usedTrafficBytes": 0,
        "downloadBytes": 0,
        "uploadBytes": 0,
        "lifetimeUsedTrafficBytes": 0,
        "onlineAt": None,
        "subLastUserAgent": None,
        "subRevokedAt": None,
        "lastTrafficResetAt": None,
        "telegramId": None,
        "email": None,
        "hwidDeviceLimit": 3,
        "activeUserInbounds": [],
    }
