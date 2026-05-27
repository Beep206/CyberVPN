from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.entitlement_grant_model import EntitlementGrantModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.service_identity_model import ServiceIdentityModel
from src.infrastructure.remnawave.contracts import RemnawaveSubscriptionDetailsResponse, RemnawaveUserResponse
from src.main import app
from src.presentation.dependencies.remnawave import get_remnawave_client
from tests.helpers.realm_auth import (
    FakeRedis,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)
from tests.integration.test_quote_checkout_sessions import _make_customer_access_token

pytestmark = [pytest.mark.integration]


class _FakeRemnawaveClient:
    def __init__(self) -> None:
        self.created_uuid = uuid.uuid4()

    async def post_validated(self, path, schema, *, json=None):
        assert path == "/api/users"
        now = datetime.now(UTC)
        return RemnawaveUserResponse(
            uuid=str(self.created_uuid),
            username=(json or {}).get("username", "cvpn_s_test"),
            status="ACTIVE",
            short_uuid=str(self.created_uuid)[:8],
            created_at=now,
            updated_at=now,
            expire_at=(json or {}).get("expireAt"),
            subscription_url=f"https://cyber-vpn.org/api/sub/{self.created_uuid.hex[:16]}",
            traffic_limit_bytes=(json or {}).get("trafficLimitBytes"),
            hwid_device_limit=(json or {}).get("hwidDeviceLimit"),
        )

    async def get_validated(self, path, schema):
        assert path == f"/subscriptions/by-uuid/{self.created_uuid}"
        return RemnawaveSubscriptionDetailsResponse(
            is_found=True,
            user={
                "shortUuid": str(self.created_uuid)[:8],
                "username": "cvpn_s_test",
                "userStatus": "ACTIVE",
            },
            links=["vless://selected-subscription"],
            subscription_url=f"https://cyber-vpn.org/api/sub/{self.created_uuid.hex[:16]}",
        )


async def _seed_customer_with_grants(sessionmaker, auth_service: AuthService) -> dict[str, str]:
    now = datetime.now(UTC)
    customer_realm = AuthRealmModel(
        id=uuid.uuid4(),
        realm_key="customer",
        realm_type="customer",
        display_name="Customer Realm",
        audience="cybervpn:customer",
        cookie_namespace="customer",
        status="active",
        is_default=True,
    )
    customer = MobileUserModel(
        id=uuid.uuid4(),
        auth_realm_id=customer_realm.id,
        email="multi-sub@example.test",
        password_hash=await auth_service.hash_password("MultiSubscription123!"),
        is_active=True,
        status="active",
    )
    other_customer = MobileUserModel(
        id=uuid.uuid4(),
        auth_realm_id=customer_realm.id,
        email="other-multi-sub@example.test",
        password_hash=await auth_service.hash_password("MultiSubscription123!"),
        is_active=True,
        status="active",
    )
    service_identity = ServiceIdentityModel(
        id=uuid.uuid4(),
        service_key="svc-multi-sub-primary",
        customer_account_id=customer.id,
        auth_realm_id=customer_realm.id,
        provider_name="remnawave",
        provider_subject_ref="rw-multi-sub-primary",
        identity_status="active",
        service_context={},
    )
    other_service_identity = ServiceIdentityModel(
        id=uuid.uuid4(),
        service_key="svc-multi-sub-other",
        customer_account_id=other_customer.id,
        auth_realm_id=customer_realm.id,
        provider_name="remnawave",
        provider_subject_ref="rw-multi-sub-other",
        identity_status="active",
        service_context={},
    )
    basic_grant = EntitlementGrantModel(
        id=uuid.uuid4(),
        grant_key="grant-multi-basic",
        service_identity_id=service_identity.id,
        customer_account_id=customer.id,
        auth_realm_id=customer_realm.id,
        source_type="manual",
        manual_source_key="manual-multi-basic",
        grant_status="active",
        grant_snapshot={
            "status": "active",
            "plan_uuid": str(uuid.uuid4()),
            "plan_code": "basic",
            "display_name": "Basic 30D",
            "effective_entitlements": {
                "device_limit": 1,
                "traffic_policy": "quota",
                "display_traffic_label": "30 GB",
            },
            "invite_bundle": {"count": 1, "friend_days": 3, "expiry_days": 30},
            "is_trial": False,
            "addons": [],
        },
        effective_from=now - timedelta(days=1),
        expires_at=now + timedelta(days=30),
    )
    pro_grant = EntitlementGrantModel(
        id=uuid.uuid4(),
        grant_key="grant-multi-pro",
        service_identity_id=service_identity.id,
        customer_account_id=customer.id,
        auth_realm_id=customer_realm.id,
        source_type="manual",
        manual_source_key="manual-multi-pro",
        grant_status="active",
        grant_snapshot={
            "status": "active",
            "plan_uuid": str(uuid.uuid4()),
            "plan_code": "pro",
            "display_name": "Pro 180D",
            "effective_entitlements": {
                "device_limit": 5,
                "traffic_policy": "fair_use",
                "display_traffic_label": "Unlimited",
            },
            "invite_bundle": {"count": 3, "friend_days": 7, "expiry_days": 60},
            "is_trial": False,
            "addons": [{"code": "device_pack", "qty": 1}],
        },
        effective_from=now,
        expires_at=now + timedelta(days=180),
    )
    other_grant = EntitlementGrantModel(
        id=uuid.uuid4(),
        grant_key="grant-multi-other",
        service_identity_id=other_service_identity.id,
        customer_account_id=other_customer.id,
        auth_realm_id=customer_realm.id,
        source_type="manual",
        manual_source_key="manual-multi-other",
        grant_status="active",
        grant_snapshot={"plan_code": "other", "display_name": "Other Customer"},
        effective_from=now,
        expires_at=now + timedelta(days=30),
    )

    with sessionmaker() as db:
        db.add_all(
            [
                customer_realm,
                customer,
                other_customer,
                service_identity,
                other_service_identity,
                basic_grant,
                pro_grant,
                other_grant,
            ]
        )
        db.commit()

    return {
        "customer_realm_id": str(customer_realm.id),
        "customer_realm_key": customer_realm.realm_key,
        "customer_realm_audience": customer_realm.audience,
        "customer_user_id": str(customer.id),
        "basic_grant_id": str(basic_grant.id),
        "pro_grant_id": str(pro_grant.id),
        "other_grant_id": str(other_grant.id),
    }


@pytest.mark.asyncio
async def test_customer_can_list_and_select_own_subscriptions(async_client: AsyncClient) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_customer_with_grants(sessionmaker, auth_service)
            customer_realm = AuthRealmModel(
                id=uuid.UUID(seeded["customer_realm_id"]),
                realm_key=seeded["customer_realm_key"],
                realm_type="customer",
                display_name="Customer Realm",
                audience=seeded["customer_realm_audience"],
                cookie_namespace="customer",
                status="active",
                is_default=True,
            )
            token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {"Authorization": f"Bearer {token}", "X-Auth-Realm": "customer"}

            list_response = await async_client.get("/api/v1/customer-subscriptions/", headers=headers)
            assert list_response.status_code == 200
            payload = list_response.json()
            assert payload["default_subscription_key"] == f"grant:{seeded['pro_grant_id']}"
            assert [item["subscription_key"] for item in payload["items"]] == [
                f"grant:{seeded['pro_grant_id']}",
                f"grant:{seeded['basic_grant_id']}",
            ]
            assert all(item["management_scope"] == "account_vpn_identity" for item in payload["items"])
            assert payload["limitations"]

            selected_response = await async_client.get(
                f"/api/v1/customer-subscriptions/?selected_subscription_key=grant:{seeded['basic_grant_id']}",
                headers=headers,
            )
            assert selected_response.status_code == 200
            assert selected_response.json()["selected_subscription_key"] == f"grant:{seeded['basic_grant_id']}"

            entitlements_response = await async_client.get(
                f"/api/v1/customer-subscriptions/grant:{seeded['basic_grant_id']}/entitlements",
                headers=headers,
            )
            assert entitlements_response.status_code == 200
            entitlements = entitlements_response.json()
            assert entitlements["status"] == "active"
            assert entitlements["plan_code"] == "basic"
            assert entitlements["effective_entitlements"]["device_limit"] == 1

            foreign_response = await async_client.get(
                f"/api/v1/customer-subscriptions/grant:{seeded['other_grant_id']}/entitlements",
                headers=headers,
            )
            assert foreign_response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_selected_subscription_config_creates_subscription_scoped_identity(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    fake_remnawave = _FakeRemnawaveClient()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    async def _override_remnawave():
        return fake_remnawave

    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_remnawave_client] = _override_remnawave

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_customer_with_grants(sessionmaker, auth_service)
            customer_realm = AuthRealmModel(
                id=uuid.UUID(seeded["customer_realm_id"]),
                realm_key=seeded["customer_realm_key"],
                realm_type="customer",
                display_name="Customer Realm",
                audience=seeded["customer_realm_audience"],
                cookie_namespace="customer",
                status="active",
                is_default=True,
            )
            token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {"Authorization": f"Bearer {token}", "X-Auth-Realm": "customer"}
            selected_key = f"grant:{seeded['basic_grant_id']}"

            config_response = await async_client.get(
                f"/api/v1/customer-subscriptions/{selected_key}/config",
                headers=headers,
            )
            assert config_response.status_code == 200
            payload = config_response.json()
            assert payload["subscriptionUrl"].startswith("https://cyber-vpn.org/api/sub/")
            assert payload["config"].startswith("https://cyber-vpn.org/api/sub/")

            with sessionmaker() as db:
                grant = db.get(EntitlementGrantModel, uuid.UUID(seeded["basic_grant_id"]))
                service_identity = db.get(ServiceIdentityModel, grant.service_identity_id)
                assert service_identity.identity_scope == "subscription"
                assert service_identity.subscription_key == selected_key
                assert service_identity.provider_subject_ref == str(fake_remnawave.created_uuid)

            list_response = await async_client.get("/api/v1/customer-subscriptions/", headers=headers)
            assert list_response.status_code == 200
            selected_item = next(
                item for item in list_response.json()["items"] if item["subscription_key"] == selected_key
            )
            assert selected_item["management_scope"] == "subscription_vpn_identity"
            assert selected_item["can_deliver_config"] is True
    finally:
        app.dependency_overrides.pop(get_redis, None)
        app.dependency_overrides.pop(get_remnawave_client, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
