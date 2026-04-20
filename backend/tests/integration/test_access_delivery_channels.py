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
async def test_resolve_current_access_delivery_channel_auto_bridges_customer_realm(
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
                    login="access-delivery-admin",
                    email="access-delivery-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("AccessDeliveryAdmin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                customer_user = db.get(MobileUserModel, uuid.UUID(seeded["customer_user_id"]))
                assert customer_user is not None
                customer_user.remnawave_uuid = "remnawave-bridge-001"
                customer_user.trial_expires_at = datetime.now(UTC) + timedelta(days=3)
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

            resolve_response = await async_client.post(
                "/api/v1/access-delivery-channels/resolve/current",
                headers=customer_headers,
                json={
                    "provider_name": "remnawave",
                    "channel_type": "shared_client",
                    "credential_type": "desktop_client",
                    "credential_subject_key": "desktop-win11-primary",
                    "delivery_context": {"client_family": "desktop"},
                },
            )
            assert resolve_response.status_code == 201
            payload = resolve_response.json()
            assert payload["auth_realm_id"] == seeded["customer_realm_id"]
            assert payload["provider_name"] == "remnawave"
            assert payload["entitlement_status"] == "trial"
            assert payload["device_credential"]["credential_type"] == "desktop_client"
            assert payload["device_credential"]["credential_status"] == "active"
            assert payload["access_delivery_channel"]["channel_type"] == "shared_client"
            assert payload["access_delivery_channel"]["channel_status"] == "active"
            assert payload["access_delivery_channel"]["last_accessed_at"] is not None
            assert payload["access_delivery_channel"]["last_delivered_at"] is not None

            repeated_resolve_response = await async_client.post(
                "/api/v1/access-delivery-channels/resolve/current",
                headers=customer_headers,
                json={
                    "provider_name": "remnawave",
                    "channel_type": "shared_client",
                    "credential_type": "desktop_client",
                    "credential_subject_key": "desktop-win11-primary",
                },
            )
            assert repeated_resolve_response.status_code == 200
            repeated_payload = repeated_resolve_response.json()
            assert repeated_payload["service_identity_id"] == payload["service_identity_id"]
            assert repeated_payload["device_credential"]["id"] == payload["device_credential"]["id"]
            assert (
                repeated_payload["access_delivery_channel"]["id"]
                == payload["access_delivery_channel"]["id"]
            )

            list_device_credentials_response = await async_client.get(
                f"/api/v1/device-credentials/?service_identity_id={payload['service_identity_id']}",
                headers=admin_headers,
            )
            assert list_device_credentials_response.status_code == 200
            assert len(list_device_credentials_response.json()) == 1

            list_channels_response = await async_client.get(
                f"/api/v1/access-delivery-channels/?service_identity_id={payload['service_identity_id']}",
                headers=admin_headers,
            )
            assert list_channels_response.status_code == 200
            assert len(list_channels_response.json()) == 1
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_suspended_entitlement_blocks_current_access_delivery_resolution(
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
                    login="access-delivery-admin-2",
                    email="access-delivery-admin-2@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("AccessDeliveryAdmin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                customer_user = db.get(MobileUserModel, uuid.UUID(seeded["customer_user_id"]))
                assert customer_user is not None
                customer_user.remnawave_uuid = "remnawave-bridge-002"
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

            service_identity_response = await async_client.post(
                "/api/v1/service-identities/",
                headers=admin_headers,
                json={
                    "customer_account_id": seeded["customer_user_id"],
                    "auth_realm_id": seeded["customer_realm_id"],
                    "provider_name": "remnawave",
                    "provider_subject_ref": "remnawave-bridge-002",
                    "service_context": {"created_for": "suspend-test"},
                },
            )
            assert service_identity_response.status_code == 201
            service_identity_payload = service_identity_response.json()

            grant_response = await async_client.post(
                "/api/v1/entitlements/",
                headers=admin_headers,
                json={
                    "service_identity_id": service_identity_payload["id"],
                    "manual_source_key": "manual-delivery-grant",
                    "grant_snapshot": {
                        "display_name": "Manual Grant",
                        "period_days": 30,
                        "effective_entitlements": {"device_limit": 2},
                    },
                },
            )
            assert grant_response.status_code == 201
            grant_payload = grant_response.json()

            activate_grant_response = await async_client.post(
                f"/api/v1/entitlements/{grant_payload['id']}/activate",
                headers=admin_headers,
            )
            assert activate_grant_response.status_code == 200

            resolve_response = await async_client.post(
                "/api/v1/access-delivery-channels/resolve/current",
                headers=customer_headers,
                json={
                    "provider_name": "remnawave",
                    "channel_type": "telegram_bot",
                    "credential_type": "telegram_bot",
                    "credential_subject_key": "telegram-chat-2001",
                },
            )
            assert resolve_response.status_code == 201

            suspend_grant_response = await async_client.post(
                f"/api/v1/entitlements/{grant_payload['id']}/suspend",
                headers=admin_headers,
                json={"reason_code": "support_hold"},
            )
            assert suspend_grant_response.status_code == 200

            blocked_resolve_response = await async_client.post(
                "/api/v1/access-delivery-channels/resolve/current",
                headers=customer_headers,
                json={
                    "provider_name": "remnawave",
                    "channel_type": "telegram_bot",
                    "credential_type": "telegram_bot",
                    "credential_subject_key": "telegram-chat-2001",
                },
            )
            assert blocked_resolve_response.status_code == 403
            assert "not entitled" in blocked_resolve_response.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
