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
async def test_service_access_observability_can_inspect_trial_realm_without_service_identity(
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

            with sessionmaker() as db:
                realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
                admin_realm = await realm_repo.get_or_create_default_realm("admin")
                admin_user = AdminUserModel(
                    login="service-observability-admin",
                    email="service-observability-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("ServiceObservabilityAdmin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                customer_user = db.get(MobileUserModel, uuid.UUID(seeded["customer_user_id"]))
                assert customer_user is not None
                customer_user.remnawave_uuid = "remnawave-observe-001"
                customer_user.trial_expires_at = datetime.now(UTC) + timedelta(days=2)
                db.add(admin_user)
                db.commit()
                admin_token = _make_admin_access_token(auth_service, user_id=admin_user.id, admin_realm=admin_realm)

            admin_headers = {
                "Authorization": f"Bearer {admin_token}",
                "X-Auth-Realm": "admin",
            }

            response = await async_client.post(
                "/api/v1/service-identities/inspect/service-state",
                headers=admin_headers,
                json={
                    "customer_account_id": seeded["customer_user_id"],
                    "auth_realm_id": seeded["customer_realm_id"],
                    "provider_name": "remnawave",
                    "channel_type": "shared_client",
                    "credential_type": "desktop_client",
                    "credential_subject_key": "desktop-observe-readonly",
                },
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload["provider_name"] == "remnawave"
            assert payload["entitlement_snapshot"]["status"] == "trial"
            assert payload["service_identity"] is None
            assert payload["active_entitlement_grant"] is None
            assert payload["purchase_context"]["source_type"] is None
            assert payload["requested_context"]["lookup_mode"] == "customer_realm_provider"
            assert payload["requested_context"]["channel_type"] == "shared_client"
            assert payload["requested_context"]["provisioning_profile_key"] == "shared_client-default"
            assert payload["requested_context"]["channel_subject_ref"] == "desktop-observe-readonly"
            assert payload["provisioning_profiles"] == []
            assert payload["device_credentials"] == []
            assert payload["access_delivery_channels"] == []
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_service_access_observability_shows_purchase_vs_consumption_context(
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
                    login="service-observability-admin-2",
                    email="service-observability-admin-2@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("ServiceObservabilityAdmin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                customer_user = db.get(MobileUserModel, uuid.UUID(seeded["customer_user_id"]))
                assert customer_user is not None
                customer_user.remnawave_uuid = "remnawave-observe-002"
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
                headers={**customer_headers, "Idempotency-Key": "phase5-observability-checkout"},
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
                    "channel_type": "desktop_manifest",
                    "credential_type": "desktop_client",
                    "credential_subject_key": "desktop-observe-primary",
                },
            )
            assert resolve_response.status_code == 201
            resolve_payload = resolve_response.json()

            inspect_by_lookup_response = await async_client.post(
                "/api/v1/service-identities/inspect/service-state",
                headers=admin_headers,
                json={
                    "customer_account_id": seeded["customer_user_id"],
                    "auth_realm_id": seeded["customer_realm_id"],
                    "provider_name": "remnawave",
                    "channel_type": "desktop_manifest",
                    "credential_type": "desktop_client",
                    "credential_subject_key": "desktop-observe-primary",
                },
            )
            assert inspect_by_lookup_response.status_code == 200
            inspect_lookup_payload = inspect_by_lookup_response.json()
            assert inspect_lookup_payload["service_identity"]["id"] == service_identity_payload["id"]
            assert inspect_lookup_payload["active_entitlement_grant"]["id"] == grant_payload["id"]
            assert inspect_lookup_payload["purchase_context"]["source_type"] == "order"
            assert inspect_lookup_payload["purchase_context"]["source_order_id"] == order_payload["id"]
            assert inspect_lookup_payload["purchase_context"]["source_order_sale_channel"] == "web"
            assert (
                inspect_lookup_payload["purchase_context"]["source_order_settlement_status"] == "paid"
            )
            assert inspect_lookup_payload["selected_provisioning_profile"]["profile_key"] == "desktop_manifest-default"
            assert (
                inspect_lookup_payload["selected_access_delivery_channel"]["id"]
                == resolve_payload["access_delivery_channel"]["id"]
            )
            assert inspect_lookup_payload["requested_context"]["lookup_mode"] == "customer_realm_provider"
            assert len(inspect_lookup_payload["provisioning_profiles"]) == 1
            assert len(inspect_lookup_payload["device_credentials"]) == 1
            assert len(inspect_lookup_payload["access_delivery_channels"]) == 1

            inspect_by_identity_response = await async_client.get(
                (
                    f"/api/v1/service-identities/{service_identity_payload['id']}/service-state"
                    "?channel_type=desktop_manifest"
                    "&credential_type=desktop_client"
                    "&credential_subject_key=desktop-observe-primary"
                ),
                headers=admin_headers,
            )
            assert inspect_by_identity_response.status_code == 200
            inspect_identity_payload = inspect_by_identity_response.json()
            assert inspect_identity_payload["service_identity"]["id"] == service_identity_payload["id"]
            assert inspect_identity_payload["requested_context"]["lookup_mode"] == "service_identity"
            assert (
                inspect_identity_payload["selected_access_delivery_channel"]["id"]
                == resolve_payload["access_delivery_channel"]["id"]
            )
            assert inspect_identity_payload["purchase_context"]["source_order_sale_channel"] == "web"
            assert inspect_identity_payload["purchase_context"]["source_order_storefront_id"] == seeded["storefront_id"]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
