from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.growth_reward_allocation_model import GrowthRewardAllocationModel
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
async def test_entitlement_grant_lifecycle_controls_current_entitlements(async_client: AsyncClient) -> None:
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
                    login="entitlement_admin",
                    email="entitlement-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("EntitlementAdmin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                customer_user = db.get(MobileUserModel, uuid.UUID(seeded["customer_user_id"]))
                assert customer_user is not None
                customer_user.remnawave_uuid = "remnawave-entitlement-001"
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
                headers={**customer_headers, "Idempotency-Key": "phase5-entitlements-checkout"},
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
            service_identity_id = service_identity_response.json()["id"]

            empty_entitlements_response = await async_client.get(
                "/api/v1/subscriptions/current/entitlements",
                headers=customer_headers,
            )
            assert empty_entitlements_response.status_code == 200
            assert empty_entitlements_response.json()["status"] == "none"

            create_grant_response = await async_client.post(
                "/api/v1/entitlements/",
                headers=admin_headers,
                json={
                    "service_identity_id": service_identity_id,
                    "source_order_id": order_payload["id"],
                },
            )
            assert create_grant_response.status_code == 201
            grant_payload = create_grant_response.json()
            assert grant_payload["grant_status"] == "pending"
            assert grant_payload["source_type"] == "order"

            repeated_grant_response = await async_client.post(
                "/api/v1/entitlements/",
                headers=admin_headers,
                json={
                    "service_identity_id": service_identity_id,
                    "source_order_id": order_payload["id"],
                },
            )
            assert repeated_grant_response.status_code == 200
            assert repeated_grant_response.json()["id"] == grant_payload["id"]

            activate_before_payment_response = await async_client.post(
                f"/api/v1/entitlements/{grant_payload['id']}/activate",
                headers=admin_headers,
            )
            assert activate_before_payment_response.status_code == 400
            assert "not payout-settled" in activate_before_payment_response.json()["detail"]

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
            assert activate_response.json()["grant_status"] == "active"

            active_entitlements_response = await async_client.get(
                "/api/v1/subscriptions/current/entitlements",
                headers=customer_headers,
            )
            assert active_entitlements_response.status_code == 200
            assert active_entitlements_response.json()["status"] == "active"
            assert active_entitlements_response.json()["plan_uuid"] == seeded["plan_id"]
            assert active_entitlements_response.json()["plan_code"] == "pro"

            suspend_response = await async_client.post(
                f"/api/v1/entitlements/{grant_payload['id']}/suspend",
                headers=admin_headers,
                json={"reason_code": "risk_manual_hold"},
            )
            assert suspend_response.status_code == 200
            assert suspend_response.json()["grant_status"] == "suspended"

            suspended_entitlements_response = await async_client.get(
                "/api/v1/subscriptions/current/entitlements",
                headers=customer_headers,
            )
            assert suspended_entitlements_response.status_code == 200
            assert suspended_entitlements_response.json()["status"] == "none"

            reactivate_response = await async_client.post(
                f"/api/v1/entitlements/{grant_payload['id']}/activate",
                headers=admin_headers,
            )
            assert reactivate_response.status_code == 200
            assert reactivate_response.json()["grant_status"] == "active"

            revoke_response = await async_client.post(
                f"/api/v1/entitlements/{grant_payload['id']}/revoke",
                headers=admin_headers,
                json={"reason_code": "support_revocation"},
            )
            assert revoke_response.status_code == 200
            assert revoke_response.json()["grant_status"] == "revoked"

            revoked_entitlements_response = await async_client.get(
                "/api/v1/subscriptions/current/entitlements",
                headers=customer_headers,
            )
            assert revoked_entitlements_response.status_code == 200
            assert revoked_entitlements_response.json()["status"] == "none"

            list_grants_response = await async_client.get(
                f"/api/v1/entitlements/?customer_account_id={seeded['customer_user_id']}",
                headers=admin_headers,
            )
            assert list_grants_response.status_code == 200
            assert [item["id"] for item in list_grants_response.json()] == [grant_payload["id"]]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_growth_reward_based_entitlement_can_affect_service_access(async_client: AsyncClient) -> None:
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
                    login="growth_reward_entitlement_admin",
                    email="growth-reward-entitlement-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("GrowthRewardEntitlementAdmin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                customer_user = db.get(MobileUserModel, uuid.UUID(seeded["customer_user_id"]))
                assert customer_user is not None
                customer_user.remnawave_uuid = "remnawave-growth-reward-001"
                growth_reward = GrowthRewardAllocationModel(
                    id=uuid.uuid4(),
                    reward_type="bonus_days",
                    allocation_status="allocated",
                    beneficiary_user_id=customer_user.id,
                    auth_realm_id=customer_realm.id,
                    storefront_id=uuid.UUID(seeded["storefront_id"]),
                    quantity=14,
                    unit="days",
                    reward_payload={"note": "invite bonus"},
                    allocated_at=datetime.now(UTC) - timedelta(minutes=5),
                )
                db.add_all([admin_user, growth_reward])
                db.commit()
                admin_token = _make_admin_access_token(auth_service, user_id=admin_user.id, admin_realm=admin_realm)
                growth_reward_id = str(growth_reward.id)

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
                    "service_context": {"provisioning_mode": "reward_only"},
                },
            )
            assert service_identity_response.status_code == 201
            service_identity_id = service_identity_response.json()["id"]

            create_grant_response = await async_client.post(
                "/api/v1/entitlements/",
                headers=admin_headers,
                json={
                    "service_identity_id": service_identity_id,
                    "source_growth_reward_allocation_id": growth_reward_id,
                    "grant_snapshot": {
                        "status": "active",
                        "plan_uuid": None,
                        "plan_code": "bonus_access",
                        "display_name": "Bonus Access",
                        "period_days": 14,
                        "effective_entitlements": {
                            "device_limit": 1,
                            "traffic_policy": "fair_use",
                            "display_traffic_label": "Unlimited",
                            "connection_modes": ["standard"],
                            "server_pool": ["shared"],
                            "support_sla": "standard",
                            "dedicated_ip_count": 0,
                        },
                        "invite_bundle": {"count": 0, "friend_days": 0, "expiry_days": 0},
                        "is_trial": False,
                        "addons": [],
                    },
                },
            )
            assert create_grant_response.status_code == 201
            grant_payload = create_grant_response.json()
            assert grant_payload["source_type"] == "growth_reward"
            assert grant_payload["grant_status"] == "pending"

            activate_response = await async_client.post(
                f"/api/v1/entitlements/{grant_payload['id']}/activate",
                headers=admin_headers,
            )
            assert activate_response.status_code == 200
            assert activate_response.json()["grant_status"] == "active"

            current_entitlements_response = await async_client.get(
                "/api/v1/subscriptions/current/entitlements",
                headers=customer_headers,
            )
            assert current_entitlements_response.status_code == 200
            assert current_entitlements_response.json()["status"] == "active"
            assert current_entitlements_response.json()["plan_code"] == "bonus_access"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
