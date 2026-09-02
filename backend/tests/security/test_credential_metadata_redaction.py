from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from src.application.services.remnawave_identity_access import RemnawaveIdentityAccessConflict
from src.application.use_cases.auth.permissions import Permission, has_permission
from src.application.use_cases.auth_realms import RealmResolution
from src.domain.enums import AdminRole, PrincipalClass
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.api.v1.access_delivery_channels import routes as channel_routes
from src.presentation.api.v1.admin import customer_support as customer_support_routes
from src.presentation.api.v1.admin import mobile_users as mobile_user_routes
from src.presentation.api.v1.device_credentials import routes as credential_routes
from src.presentation.api.v1.provisioning_profiles import routes as profile_routes
from src.presentation.api.v1.service_identities import routes as identity_routes
from src.presentation.api.v1.telegram import routes as telegram_routes
from src.presentation.dependencies.auth import CurrentPrincipalActor

_SECRET_URL = "vless://live-secret@example.test:443"
_SECRET_TOKEN = "live-bearer-token-never-return"


def _request(path: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [(b"user-agent", b"security-test")],
            "client": ("127.0.0.1", 443),
            "scheme": "https",
            "server": ("testserver", 443),
            "query_string": b"",
        }
    )


def _realm(realm_type: str) -> RealmResolution:
    realm_id = uuid4()
    return RealmResolution(
        auth_realm=SimpleNamespace(
            id=realm_id,
            realm_type=realm_type,
            realm_key=realm_type,
            audience=f"cybervpn:{realm_type}",
        ),
        source="test",
    )


def _actor(realm: RealmResolution, principal_id: UUID, principal_type: str) -> CurrentPrincipalActor:
    return CurrentPrincipalActor(
        principal_id=principal_id,
        principal_type=principal_type,
        auth_realm_id=realm.auth_realm.id,
        auth_realm_key=realm.realm_key,
        audience=realm.audience,
    )


def _admin(realm_id: UUID, role: AdminRole) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        auth_realm_id=realm_id,
        role=role.value,
        is_active=True,
        deleted_at=None,
        totp_enabled=True,
    )


class _AdminDb:
    def __init__(self, admin: SimpleNamespace) -> None:
        self.admin = admin

    async def get(self, entity: type[object], identifier: UUID) -> object | None:
        if entity is AdminUserModel and self.admin.id == identifier:
            return self.admin
        return None


def _mobile_user() -> SimpleNamespace:
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=uuid4(),
        public_uid=1001,
        email="customer@example.test",
        username="customer",
        status="active",
        is_active=True,
        is_partner=False,
        telegram_id=123456,
        telegram_username="customer",
        remnawave_user_id=314,
        remnawave_uuid=str(uuid4()),
        referral_code=None,
        referred_by_user_id=None,
        partner_user_id=None,
        partner_promoted_at=None,
        created_at=now,
        last_login_at=now,
        updated_at=now,
        devices=[],
        subscription_url=_SECRET_URL,
    )


def _service_access_model() -> SimpleNamespace:
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=uuid4(),
        service_key="service-key",
        customer_account_id=uuid4(),
        auth_realm_id=uuid4(),
        source_order_id=None,
        origin_storefront_id=None,
        provider_name="remnawave",
        identity_scope="subscription",
        subscription_key=_SECRET_TOKEN,
        provider_subject_ref="provider-subject",
        provider_numeric_subject_id=42,
        identity_status="active",
        service_context={"subscription_url": _SECRET_URL, "token": _SECRET_TOKEN},
        service_identity_id=uuid4(),
        profile_key="profile",
        target_channel="shared_client",
        delivery_method="subscription_url",
        profile_status="active",
        provider_profile_ref="provider-profile",
        provisioning_payload={"config": _SECRET_URL, "token": _SECRET_TOKEN},
        provisioning_profile_id=uuid4(),
        credential_key="credential-key",
        credential_type="shared_client",
        credential_status="active",
        subject_key="subject-key",
        provider_credential_ref=_SECRET_TOKEN,
        credential_context={"config": _SECRET_URL, "token": _SECRET_TOKEN},
        issued_at=now,
        last_used_at=None,
        revoked_at=None,
        revoked_by_admin_user_id=None,
        revoke_reason_code=None,
        delivery_key="delivery-key",
        device_credential_id=uuid4(),
        channel_type="shared_client",
        channel_status="active",
        channel_subject_ref="channel-subject",
        delivery_context={"diagnostic": "safe"},
        delivery_payload={"config": _SECRET_URL, "token": _SECRET_TOKEN},
        last_delivered_at=None,
        last_accessed_at=None,
        archived_at=None,
        archived_by_admin_user_id=None,
        archive_reason_code=None,
        created_at=now,
        updated_at=now,
    )


def _mobile_device() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        device_id="device-id",
        platform="android",
        platform_id="platform-id",
        os_version="15",
        app_version="3.4.1",
        device_model="Pixel",
        push_token=_SECRET_TOKEN,
        registered_at=datetime.now(UTC),
        last_active_at=datetime.now(UTC),
    )


@pytest.mark.security
def test_support_user_read_mobile_detail_redacts_subscription_url_and_push_token() -> None:
    assert has_permission(AdminRole.SUPPORT, Permission.USER_READ)
    mobile_user = _mobile_user()
    mobile_user.devices = [_mobile_device()]

    response = mobile_user_routes._serialize_mobile_user_detail(mobile_user)

    assert response.subscription_url is None
    assert response.devices[0].push_token is None
    assert _SECRET_URL not in repr(response)
    assert _SECRET_TOKEN not in repr(response)


@pytest.mark.security
def test_support_vpn_user_serializer_redacts_live_short_and_subscription_identifiers() -> None:
    upstream = SimpleNamespace(
        remnawave_id=42,
        username="customer",
        email="customer@example.test",
        status="active",
        short_uuid=_SECRET_TOKEN,
        subscription_uuid=uuid4(),
        expire_at=datetime.now(UTC),
        traffic_limit_bytes=100,
        used_traffic_bytes=10,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        telegram_id=123456,
    )

    response = customer_support_routes._serialize_vpn_user(42, str(uuid4()), upstream)

    assert response.short_uuid is None
    assert response.subscription_uuid is None
    assert _SECRET_TOKEN not in repr(response)


@pytest.mark.security
@pytest.mark.asyncio
async def test_customer_support_vpn_paths_reject_mapping_conflict_before_upstream_access(monkeypatch) -> None:
    customer = _mobile_user()
    admin = SimpleNamespace(id=uuid4())
    resolver = AsyncMock(side_effect=RemnawaveIdentityAccessConflict("legacy mismatch"))
    monkeypatch.setattr(customer_support_routes, "_require_mobile_user", AsyncMock(return_value=customer))
    monkeypatch.setattr(customer_support_routes, "resolve_exact_mapped_mobile_user_ref", resolver)

    class _NoUpstreamGateway:
        def __init__(self, **kwargs) -> None:
            pass

        async def get_by_ref(self, *_args, **_kwargs):
            pytest.fail("conflicting identity must not reach Remnawave")

        async def update(self, *_args, **_kwargs):
            pytest.fail("conflicting identity must not reach Remnawave")

    monkeypatch.setattr(customer_support_routes, "RemnawaveUserGateway", _NoUpstreamGateway)
    request = _request(f"/admin/mobile-users/{customer.id}/vpn-user")
    db = object()
    client = object()

    operations = (
        lambda: customer_support_routes.get_customer_vpn_user(customer.id, db, client, None),
        lambda: customer_support_routes.enable_customer_vpn_user(
            customer.id,
            customer_support_routes.AdminCustomerSupportActionRequest(reason="exact mapping required"),
            request,
            admin,
            db,
            client,
            None,
        ),
        lambda: customer_support_routes.disable_customer_vpn_user(
            customer.id,
            customer_support_routes.AdminCustomerSupportActionRequest(reason="exact mapping required"),
            request,
            admin,
            db,
            client,
            None,
        ),
        lambda: customer_support_routes.regenerate_customer_vpn_credentials(
            customer.id,
            customer_support_routes.AdminCustomerCredentialRegenerationRequest(reason="exact mapping required"),
            request,
            admin,
            db,
            client,
            None,
        ),
    )

    for operation in operations:
        with pytest.raises(HTTPException) as exc_info:
            await operation()
        assert exc_info.value.status_code == 409

    assert resolver.await_count == len(operations)


@pytest.mark.security
@pytest.mark.asyncio
async def test_device_revoke_responses_redact_raw_push_tokens(monkeypatch) -> None:
    assert has_permission(AdminRole.SUPPORT, Permission.USER_UPDATE)
    user_id = uuid4()
    device = _mobile_device()
    audit = AsyncMock()

    class _DeviceRepo:
        def __init__(self, _db: object) -> None:
            pass

        async def get_by_id_for_user(self, device_id: UUID, requested_user_id: UUID):
            assert device_id == device.id
            assert requested_user_id == user_id
            return device

        async def get_user_devices(self, requested_user_id: UUID):
            assert requested_user_id == user_id
            return [device]

        async def delete(self, _device: object) -> None:
            return None

    monkeypatch.setattr(customer_support_routes, "MobileDeviceRepository", _DeviceRepo)
    monkeypatch.setattr(customer_support_routes, "_require_mobile_user", AsyncMock())
    monkeypatch.setattr(customer_support_routes, "_write_audit_entry", audit)
    admin = SimpleNamespace(id=uuid4())
    request = _request(f"/admin/mobile-users/{user_id}/devices/{device.id}")

    single = await customer_support_routes.revoke_customer_device(
        user_id,
        device.id,
        request,
        admin,
        object(),
        None,
    )
    bulk = await customer_support_routes.revoke_all_customer_devices(
        user_id,
        customer_support_routes.AdminCustomerSupportActionRequest(reason="security-test"),
        request,
        admin,
        object(),
        None,
    )

    assert single.push_token is None
    assert bulk.revoked_devices[0].push_token is None
    assert _SECRET_TOKEN not in repr((single, bulk))
    assert audit.await_count == 2


@pytest.mark.security
@pytest.mark.asyncio
async def test_user_read_mobile_snapshot_never_fetches_or_returns_live_config(monkeypatch) -> None:
    mobile_user = _mobile_user()
    upstream_user = SimpleNamespace(
        status=SimpleNamespace(value="active"),
        short_uuid=_SECRET_TOKEN,
        subscription_uuid=uuid4(),
        subscription_url=_SECRET_URL,
        expire_at=datetime.now(UTC),
        traffic_limit_bytes=100,
        used_traffic_bytes=20,
        download_bytes=10,
        upload_bytes=10,
        lifetime_used_traffic_bytes=20,
        online_at=None,
        sub_last_user_agent=None,
        sub_revoked_at=None,
        last_traffic_reset_at=None,
        hwid_device_limit=3,
    )

    class _Gateway:
        def __init__(self, *, client: object) -> None:
            self.client = client

        async def get_by_ref(self, _user_ref):
            return upstream_user

    upstream_config_read = AsyncMock(side_effect=AssertionError("credential endpoint must not be called"))
    monkeypatch.setattr(mobile_user_routes, "RemnawaveUserGateway", _Gateway)
    resolved_mappings: list[dict] = []

    async def fake_resolve_exact_mapped_remnawave_ref(db, **kwargs):
        resolved_mappings.append({"db": db, **kwargs})
        return RemnawaveUserRef(
            id=mobile_user.remnawave_user_id,
            legacy_uuid=UUID(mobile_user.remnawave_uuid),
        )

    monkeypatch.setattr(
        mobile_user_routes,
        "resolve_exact_mapped_remnawave_ref",
        fake_resolve_exact_mapped_remnawave_ref,
    )
    client = SimpleNamespace(get_validated=upstream_config_read)
    db = object()

    response = await mobile_user_routes.build_mobile_user_subscription_snapshot(mobile_user, client, db)

    assert response.subscription_url is None
    assert response.config is None
    assert response.config_available is False
    assert response.links == []
    assert response.ss_conf_links == {}
    assert response.short_uuid is None
    assert response.subscription_uuid is None
    assert _SECRET_URL not in repr(response)
    assert _SECRET_TOKEN not in repr(response)
    upstream_config_read.assert_not_awaited()
    assert resolved_mappings == [
        {
            "db": db,
            "subject_type": "mobile_user",
            "subject_id": mobile_user.id,
            "numeric_user_id": mobile_user.remnawave_user_id,
            "legacy_uuid_raw": mobile_user.remnawave_uuid,
        }
    ]


@pytest.mark.security
@pytest.mark.asyncio
async def test_user_read_mobile_snapshot_rejects_unreconciled_identity_before_upstream_lookup(monkeypatch) -> None:
    mobile_user = _mobile_user()

    async def fake_resolve_exact_mapped_remnawave_ref(db, **kwargs):
        raise RemnawaveIdentityAccessConflict("foreign mapping")

    monkeypatch.setattr(
        mobile_user_routes,
        "resolve_exact_mapped_remnawave_ref",
        fake_resolve_exact_mapped_remnawave_ref,
    )
    monkeypatch.setattr(
        mobile_user_routes,
        "RemnawaveUserGateway",
        lambda **kwargs: pytest.fail("unreconciled identity must not reach Remnawave"),
    )

    with pytest.raises(HTTPException) as exc_info:
        await mobile_user_routes.build_mobile_user_subscription_snapshot(mobile_user, object(), object())

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Remnawave identity reconciliation required"


@pytest.mark.security
@pytest.mark.asyncio
async def test_support_subscription_resync_is_denied_before_customer_lookup(monkeypatch) -> None:
    realm = _realm("admin")
    admin = _admin(realm.auth_realm.id, AdminRole.SUPPORT)
    actor = _actor(realm, admin.id, PrincipalClass.ADMIN.value)
    credential_boundary = AsyncMock(side_effect=HTTPException(status_code=403, detail="VPN credential access denied"))
    customer_lookup = AsyncMock()
    monkeypatch.setattr(
        customer_support_routes,
        "read_customer_vpn_credentials_as_admin",
        credential_boundary,
    )
    monkeypatch.setattr(customer_support_routes, "_require_mobile_user", customer_lookup)

    with pytest.raises(HTTPException) as exc_info:
        await customer_support_routes.resync_customer_subscription(
            user_id=uuid4(),
            body=customer_support_routes.AdminCustomerSupportActionRequest(reason="diagnose without credentials"),
            request=_request("/admin/mobile-users/customer/subscription/resync"),
            current_user=admin,
            current_actor=actor,
            current_realm=realm,
            db=object(),
            client=object(),
            redis_client=object(),
            _=None,
        )

    assert exc_info.value.status_code == 403
    customer_lookup.assert_not_awaited()


@pytest.mark.security
@pytest.mark.asyncio
async def test_trusted_admin_subscription_resync_uses_unified_boundary_and_redacts_response(monkeypatch) -> None:
    realm = _realm("admin")
    admin = _admin(realm.auth_realm.id, AdminRole.SUPER_ADMIN)
    actor = _actor(realm, admin.id, PrincipalClass.ADMIN.value)
    customer = _mobile_user()
    customer.subscription_url = "https://old-secret.example/subscription"
    credential_boundary = AsyncMock(
        return_value={
            "config": _SECRET_URL,
            "config_string": _SECRET_URL,
            "client_type": "subscription",
            "links": [_SECRET_URL],
            "subscription_url": _SECRET_URL,
        }
    )
    audit = AsyncMock()
    updated_users: list[object] = []

    class _UserRepo:
        def __init__(self, _db: object) -> None:
            pass

        async def update(self, user: object) -> object:
            updated_users.append(user)
            return user

    monkeypatch.setattr(
        customer_support_routes,
        "read_customer_vpn_credentials_as_admin",
        credential_boundary,
    )
    monkeypatch.setattr(customer_support_routes, "_require_mobile_user", AsyncMock(return_value=customer))
    monkeypatch.setattr(customer_support_routes, "MobileUserRepository", _UserRepo)
    monkeypatch.setattr(customer_support_routes, "_write_audit_entry", audit)
    request = _request(f"/admin/mobile-users/{customer.id}/subscription/resync")
    db = object()
    redis_client = object()

    response = await customer_support_routes.resync_customer_subscription(
        user_id=customer.id,
        body=customer_support_routes.AdminCustomerSupportActionRequest(reason="repair local subscription reference"),
        request=request,
        current_user=admin,
        current_actor=actor,
        current_realm=realm,
        db=db,
        client=object(),
        redis_client=redis_client,
        _=None,
    )

    assert customer.subscription_url == _SECRET_URL
    assert updated_users == [customer]
    assert response.previous_subscription_url == "[REDACTED]"
    assert response.stored_subscription_url == "[REDACTED]"
    assert response.upstream_subscription_url == "[REDACTED]"
    assert _SECRET_URL not in repr(response)
    credential_boundary.assert_awaited_once()
    boundary_call = credential_boundary.await_args.kwargs
    assert boundary_call["customer_id"] == customer.id
    assert boundary_call["actor"] == actor
    assert boundary_call["current_realm"] == realm
    assert boundary_call["redis_client"] is redis_client
    audit.assert_awaited_once()
    assert _SECRET_URL not in repr(audit.await_args.kwargs)


@pytest.mark.security
@pytest.mark.asyncio
async def test_user_read_telegram_metadata_redacts_subscription_url(monkeypatch) -> None:
    user = SimpleNamespace(
        uuid=uuid4(),
        username="telegram-user",
        status="active",
        data_usage=1,
        data_limit=10,
        expires_at=datetime.now(UTC),
        subscription_url=_SECRET_URL,
    )

    mobile_user = SimpleNamespace(id=uuid4())

    class _UserRepo:
        def __init__(self, _db: object) -> None:
            pass

        async def get_by_telegram_id(self, telegram_id: int):
            assert telegram_id == 123456
            return mobile_user

    exact_user = AsyncMock(return_value=user)
    monkeypatch.setattr(telegram_routes, "MobileUserRepository", _UserRepo)
    monkeypatch.setattr(telegram_routes, "_get_exact_remnawave_user_for_mobile", exact_user)

    response = await telegram_routes.get_telegram_user(123456, object(), object(), None)

    assert response.subscription_url is None
    assert _SECRET_URL not in repr(response)
    exact_user.assert_awaited_once()


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [AdminRole.SUPPORT, AdminRole.OPERATOR, AdminRole.FINANCE, AdminRole.VIEWER],
)
async def test_telegram_config_route_rejects_low_privilege_roles_before_target_lookup(role: AdminRole) -> None:
    realm = _realm("admin")
    admin = _admin(realm.auth_realm.id, role)
    actor = _actor(realm, admin.id, PrincipalClass.ADMIN.value)

    with pytest.raises(HTTPException) as exc_info:
        await telegram_routes.get_user_config(
            123456,
            _request("/telegram/user/123456/config"),
            actor,
            realm,
            _AdminDb(admin),
            object(),
            object(),
        )

    assert exc_info.value.status_code == 403


@pytest.mark.security
def test_service_access_metadata_serializers_fail_closed_on_credential_material() -> None:
    model = _service_access_model()

    identity = identity_routes._serialize_service_identity(model)
    profile = profile_routes._serialize_provisioning_profile(model)
    credential = credential_routes._serialize_device_credential(model)
    channel = channel_routes._serialize_access_delivery_channel(model)
    nested_profile = identity_routes._serialize_provisioning_profile(model)
    nested_credential = identity_routes._serialize_device_credential(model)
    nested_channel = identity_routes._serialize_observed_channel(model)

    assert identity.subscription_key is None
    assert identity.service_context == {}
    assert profile.provisioning_payload == {}
    assert credential.provider_credential_ref is None
    assert credential.credential_context == {}
    assert channel.delivery_payload == {}
    assert nested_profile.provisioning_payload == {}
    assert nested_credential.provider_credential_ref is None
    assert nested_credential.credential_context == {}
    assert nested_channel.delivery_payload == {}

    serialized = repr((identity, profile, credential, channel, nested_profile, nested_credential, nested_channel))
    assert _SECRET_URL not in serialized
    assert _SECRET_TOKEN not in serialized
