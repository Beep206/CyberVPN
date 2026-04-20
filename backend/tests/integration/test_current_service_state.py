from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.order_model import OrderModel
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
async def test_current_service_state_is_read_only_without_canonical_objects(
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
                    login="service-state-admin",
                    email="service-state-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("ServiceStateAdmin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                customer_user = db.get(MobileUserModel, uuid.UUID(seeded["customer_user_id"]))
                assert customer_user is not None
                customer_user.remnawave_uuid = "remnawave-state-001"
                customer_user.trial_expires_at = datetime.now(UTC) + timedelta(days=5)
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

            current_entitlements_response = await async_client.get(
                "/api/v1/entitlements/current",
                headers=customer_headers,
            )
            assert current_entitlements_response.status_code == 200
            assert current_entitlements_response.json()["status"] == "trial"

            service_state_response = await async_client.post(
                "/api/v1/access-delivery-channels/current/service-state",
                headers=customer_headers,
                json={
                    "provider_name": "remnawave",
                    "channel_type": "shared_client",
                    "credential_type": "desktop_client",
                    "credential_subject_key": "desktop-readonly-primary",
                },
            )
            assert service_state_response.status_code == 200
            payload = service_state_response.json()
            assert payload["entitlement_snapshot"]["status"] == "trial"
            assert payload["service_identity"] is None
            assert payload["provisioning_profile"] is None
            assert payload["device_credential"] is None
            assert payload["access_delivery_channel"] is None
            assert payload["purchase_context"]["active_entitlement_grant_id"] is None
            assert payload["consumption_context"]["channel_type"] == "shared_client"
            assert payload["consumption_context"]["provisioning_profile_key"] == "shared_client-default"
            assert payload["consumption_context"]["channel_subject_ref"] == "desktop-readonly-primary"
            assert payload["consumption_context"]["credential_type"] == "desktop_client"
            assert payload["consumption_context"]["credential_subject_key"] == "desktop-readonly-primary"

            list_service_identities_response = await async_client.get(
                f"/api/v1/service-identities/?customer_account_id={seeded['customer_user_id']}",
                headers=admin_headers,
            )
            assert list_service_identities_response.status_code == 200
            assert list_service_identities_response.json() == []

            list_device_credentials_response = await async_client.get(
                f"/api/v1/device-credentials/?auth_realm_id={seeded['customer_realm_id']}",
                headers=admin_headers,
            )
            assert list_device_credentials_response.status_code == 200
            assert list_device_credentials_response.json() == []

            list_channels_response = await async_client.get(
                f"/api/v1/access-delivery-channels/?auth_realm_id={seeded['customer_realm_id']}",
                headers=admin_headers,
            )
            assert list_channels_response.status_code == 200
            assert list_channels_response.json() == []
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_current_service_state_shows_purchase_and_consumption_context(
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
                    login="service-state-admin-2",
                    email="service-state-admin-2@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("ServiceStateAdmin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                customer_user = db.get(MobileUserModel, uuid.UUID(seeded["customer_user_id"]))
                assert customer_user is not None
                customer_user.remnawave_uuid = "remnawave-state-002"
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
                headers={**customer_headers, "Idempotency-Key": "phase5-service-state-checkout"},
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

            service_identity_response = await async_client.post(
                "/api/v1/service-identities/",
                headers=admin_headers,
                json={
                    "customer_account_id": seeded["customer_user_id"],
                    "auth_realm_id": seeded["customer_realm_id"],
                    "provider_name": "remnawave",
                    "source_order_id": order_payload["id"],
                },
            )
            assert service_identity_response.status_code == 201
            service_identity_payload = service_identity_response.json()

            grant_response = await async_client.post(
                "/api/v1/entitlements/",
                headers=admin_headers,
                json={
                    "service_identity_id": service_identity_payload["id"],
                    "source_order_id": order_payload["id"],
                },
            )
            assert grant_response.status_code == 201
            grant_payload = grant_response.json()

            with sessionmaker() as db:
                order = db.get(OrderModel, uuid.UUID(order_payload["id"]))
                assert order is not None
                order.settlement_status = "paid"
                db.commit()

            activate_response = await async_client.post(
                f"/api/v1/entitlements/{grant_payload['id']}/activate",
                headers=admin_headers,
            )
            assert activate_response.status_code == 200

            resolve_response = await async_client.post(
                "/api/v1/access-delivery-channels/resolve/current",
                headers=customer_headers,
                json={
                    "provider_name": "remnawave",
                    "channel_type": "shared_client",
                    "credential_type": "desktop_client",
                    "credential_subject_key": "desktop-shared-state-primary",
                },
            )
            assert resolve_response.status_code == 201
            resolve_payload = resolve_response.json()

            current_entitlements_response = await async_client.get(
                "/api/v1/entitlements/current",
                headers=customer_headers,
            )
            assert current_entitlements_response.status_code == 200
            assert current_entitlements_response.json()["status"] == "active"
            assert current_entitlements_response.json()["plan_code"] == "pro"

            service_state_response = await async_client.post(
                "/api/v1/access-delivery-channels/current/service-state",
                headers=customer_headers,
                json={
                    "provider_name": "remnawave",
                    "channel_type": "shared_client",
                    "credential_type": "desktop_client",
                    "credential_subject_key": "desktop-shared-state-primary",
                },
            )
            assert service_state_response.status_code == 200
            payload = service_state_response.json()
            assert payload["entitlement_snapshot"]["status"] == "active"
            assert payload["service_identity"]["id"] == service_identity_payload["id"]
            assert payload["provisioning_profile"]["profile_key"] == "shared_client-default"
            assert payload["device_credential"]["subject_key"] == "desktop-shared-state-primary"
            assert (
                payload["access_delivery_channel"]["id"]
                == resolve_payload["access_delivery_channel"]["id"]
            )
            assert payload["purchase_context"]["active_entitlement_grant_id"] == grant_payload["id"]
            assert payload["purchase_context"]["source_type"] == "order"
            assert payload["purchase_context"]["source_order_id"] == order_payload["id"]
            assert payload["purchase_context"]["origin_storefront_id"] == seeded["storefront_id"]
            assert payload["consumption_context"]["channel_type"] == "shared_client"
            assert payload["consumption_context"]["provisioning_profile_key"] == "shared_client-default"
            assert payload["consumption_context"]["channel_subject_ref"] == "desktop-shared-state-primary"
            assert payload["consumption_context"]["credential_type"] == "desktop_client"
            assert payload["consumption_context"]["credential_subject_key"] == "desktop-shared-state-primary"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
