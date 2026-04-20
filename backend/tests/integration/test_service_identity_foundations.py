from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.main import app
from tests.helpers.realm_auth import (
    FakeRedis,
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)
from tests.integration.test_order_commit import _seed_order_context
from tests.integration.test_quote_checkout_sessions import _make_customer_access_token

pytestmark = [pytest.mark.integration]


def _make_admin_access_token(auth_service: AuthService, *, user_id, admin_realm: AuthRealmModel) -> str:
    token, _, _ = auth_service.create_access_token(
        str(user_id),
        "admin",
        audience=admin_realm.audience,
        principal_type="admin",
        realm_id=str(admin_realm.id),
        realm_key=admin_realm.realm_key,
        scope_family="admin",
    )
    return token


@pytest.mark.asyncio
async def test_service_identity_and_provisioning_profile_foundations_are_idempotent(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_order_context(sessionmaker, auth_service)
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

            with sessionmaker() as db:
                realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
                admin_realm = await realm_repo.get_or_create_default_realm("admin")
                admin_user = AdminUserModel(
                    login="service_identity_admin",
                    email="service-identity-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("ServiceIdentityAdmin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                customer_user = db.get(MobileUserModel, uuid.UUID(seeded["customer_user_id"]))
                assert customer_user is not None
                customer_user.remnawave_uuid = "remnawave-subject-001"
                customer_user.subscription_url = "https://partner.example.test/sub/legacy-001"
                db.add(admin_user)
                db.commit()
                admin_token = _make_admin_access_token(auth_service, user_id=admin_user.id, admin_realm=admin_realm)

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            customer_headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }
            admin_headers = {
                "Authorization": f"Bearer {admin_token}",
                "X-Auth-Realm": "admin",
            }

            quote_response = await async_client.post(
                "/api/v1/quotes/",
                headers=customer_headers,
                json={
                    "storefront_key": seeded["storefront_key"],
                    "pricebook_key": seeded["pricebook_key"],
                    "offer_key": seeded["offer_key"],
                    "plan_id": seeded["plan_id"],
                    "currency": "USD",
                    "channel": "web",
                    "use_wallet": 0,
                    "addons": [],
                },
            )
            assert quote_response.status_code == 201

            checkout_response = await async_client.post(
                "/api/v1/checkout-sessions/",
                headers={**customer_headers, "Idempotency-Key": "phase5-service-identity-checkout"},
                json={"quote_session_id": quote_response.json()["id"]},
            )
            assert checkout_response.status_code == 201

            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=customer_headers,
                json={"checkout_session_id": checkout_response.json()["id"]},
            )
            assert order_response.status_code == 201
            order_payload = order_response.json()

            create_service_identity_response = await async_client.post(
                "/api/v1/service-identities/",
                headers=admin_headers,
                json={
                    "customer_account_id": seeded["customer_user_id"],
                    "auth_realm_id": seeded["customer_realm_id"],
                    "provider_name": "remnawave",
                    "source_order_id": order_payload["id"],
                    "service_context": {"delivery_hint": "shared-clients"},
                },
            )
            assert create_service_identity_response.status_code == 201
            service_identity_payload = create_service_identity_response.json()
            assert service_identity_payload["customer_account_id"] == seeded["customer_user_id"]
            assert service_identity_payload["auth_realm_id"] == seeded["customer_realm_id"]
            assert service_identity_payload["source_order_id"] == order_payload["id"]
            assert service_identity_payload["origin_storefront_id"] == seeded["storefront_id"]
            assert service_identity_payload["provider_name"] == "remnawave"
            assert service_identity_payload["provider_subject_ref"] == "remnawave-subject-001"
            assert service_identity_payload["identity_status"] == "active"
            assert service_identity_payload["service_context"]["delivery_hint"] == "shared-clients"
            assert (
                service_identity_payload["service_context"]["legacy_subscription_url"]
                == "https://partner.example.test/sub/legacy-001"
            )

            repeated_service_identity_response = await async_client.post(
                "/api/v1/service-identities/",
                headers=admin_headers,
                json={
                    "customer_account_id": seeded["customer_user_id"],
                    "auth_realm_id": seeded["customer_realm_id"],
                    "provider_name": "remnawave",
                    "source_order_id": order_payload["id"],
                    "service_context": {"delivery_hint": "shared-clients"},
                },
            )
            assert repeated_service_identity_response.status_code == 200
            assert repeated_service_identity_response.json()["id"] == service_identity_payload["id"]

            list_service_identities_response = await async_client.get(
                (
                    "/api/v1/service-identities/"
                    f"?customer_account_id={seeded['customer_user_id']}"
                    f"&auth_realm_id={seeded['customer_realm_id']}"
                ),
                headers=admin_headers,
            )
            assert list_service_identities_response.status_code == 200
            assert [item["id"] for item in list_service_identities_response.json()] == [service_identity_payload["id"]]

            get_service_identity_response = await async_client.get(
                f"/api/v1/service-identities/{service_identity_payload['id']}",
                headers=admin_headers,
            )
            assert get_service_identity_response.status_code == 200
            assert get_service_identity_response.json()["id"] == service_identity_payload["id"]

            create_provisioning_profile_response = await async_client.post(
                "/api/v1/provisioning-profiles/",
                headers=admin_headers,
                json={
                    "service_identity_id": service_identity_payload["id"],
                    "profile_key": "shared-clients-default",
                    "target_channel": "shared_clients",
                    "delivery_method": "subscription_url",
                    "provisioning_payload": {"config_format": "vless"},
                },
            )
            assert create_provisioning_profile_response.status_code == 201
            provisioning_profile_payload = create_provisioning_profile_response.json()
            assert provisioning_profile_payload["service_identity_id"] == service_identity_payload["id"]
            assert provisioning_profile_payload["provider_name"] == "remnawave"
            assert provisioning_profile_payload["profile_status"] == "active"
            assert provisioning_profile_payload["provisioning_payload"]["config_format"] == "vless"

            repeated_provisioning_profile_response = await async_client.post(
                "/api/v1/provisioning-profiles/",
                headers=admin_headers,
                json={
                    "service_identity_id": service_identity_payload["id"],
                    "profile_key": "shared-clients-default",
                    "target_channel": "shared_clients",
                    "delivery_method": "subscription_url",
                    "provisioning_payload": {"config_format": "vless"},
                },
            )
            assert repeated_provisioning_profile_response.status_code == 200
            assert repeated_provisioning_profile_response.json()["id"] == provisioning_profile_payload["id"]

            list_provisioning_profiles_response = await async_client.get(
                f"/api/v1/provisioning-profiles/?service_identity_id={service_identity_payload['id']}",
                headers=admin_headers,
            )
            assert list_provisioning_profiles_response.status_code == 200
            assert [item["id"] for item in list_provisioning_profiles_response.json()] == [
                provisioning_profile_payload["id"]
            ]

            get_provisioning_profile_response = await async_client.get(
                f"/api/v1/provisioning-profiles/{provisioning_profile_payload['id']}",
                headers=admin_headers,
            )
            assert get_provisioning_profile_response.status_code == 200
            assert get_provisioning_profile_response.json()["id"] == provisioning_profile_payload["id"]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
