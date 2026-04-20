from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import PartnerCodeModel
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
from tests.integration.test_quote_checkout_sessions import _make_customer_access_token, _seed_quote_context

pytestmark = [pytest.mark.integration]


def _make_admin_token(auth_service: AuthService, *, user_id, realm) -> str:
    token, _, _ = auth_service.create_access_token(
        str(user_id),
        "admin",
        audience=realm.audience,
        principal_type="admin",
        realm_id=str(realm.id),
        realm_key=realm.realm_key,
        scope_family="admin",
    )
    return token


@pytest.mark.asyncio
async def test_quote_creation_records_storefront_origin_and_explicit_code_touchpoints(
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
            seeded = await _seed_quote_context(sessionmaker, auth_service)
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

                partner_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="partner-owner@partner.example.test",
                    password_hash=await auth_service.hash_password("PartnerOwnerPass123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                partner_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="NEBULA20",
                    partner_user_id=partner_owner.id,
                    markup_pct=20,
                    is_active=True,
                )
                admin_user = AdminUserModel(
                    login="attribution_admin",
                    email="attribution-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("AttributionAdmin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                support_user = AdminUserModel(
                    login="attribution_support",
                    email="attribution-support@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("AttributionSupport123!"),
                    role="support",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add_all([partner_owner, partner_code, admin_user, support_user])
                db.commit()

                admin_token = _make_admin_token(auth_service, user_id=admin_user.id, realm=admin_realm)
                support_token = _make_admin_token(auth_service, user_id=support_user.id, realm=admin_realm)

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
            support_headers = {
                "Authorization": f"Bearer {support_token}",
                "X-Auth-Realm": "admin",
            }

            quote_response = await async_client.post(
                "/api/v1/quotes/?utm_source=telegram&utm_campaign=launch",
                headers=customer_headers,
                json={
                    "storefront_key": seeded["storefront_key"],
                    "pricebook_key": seeded["pricebook_key"],
                    "offer_key": seeded["offer_key"],
                    "plan_id": seeded["plan_id"],
                    "currency": "USD",
                    "channel": "web",
                    "partner_code": "NEBULA20",
                    "use_wallet": 0,
                    "addons": [],
                },
            )
            assert quote_response.status_code == 201
            quote_payload = quote_response.json()
            assert quote_payload["quote"]["partner_code_id"] == str(partner_code.id)

            list_response = await async_client.get(
                f"/api/v1/attribution/touchpoints?quote_session_id={quote_payload['id']}",
                headers=support_headers,
            )
            assert list_response.status_code == 200
            touchpoints = list_response.json()
            assert [item["touchpoint_type"] for item in touchpoints] == [
                "storefront_origin",
                "explicit_code",
            ]
            assert all(item["quote_session_id"] == quote_payload["id"] for item in touchpoints)
            assert touchpoints[0]["campaign_params"]["utm_source"] == "telegram"
            assert touchpoints[1]["evidence_payload"]["partner_code"] == "NEBULA20"

            get_response = await async_client.get(
                f"/api/v1/attribution/touchpoints/{touchpoints[0]['id']}",
                headers=support_headers,
            )
            assert get_response.status_code == 200
            assert get_response.json()["id"] == touchpoints[0]["id"]

            manual_response = await async_client.post(
                "/api/v1/attribution/touchpoints",
                headers=admin_headers,
                json={
                    "touchpoint_type": "passive_click",
                    "auth_realm_key": seeded["customer_realm_key"],
                    "quote_session_id": quote_payload["id"],
                    "sale_channel": "web",
                    "source_host": "partner.example.test",
                    "source_path": "/landing/review",
                    "campaign_params": {"utm_source": "seo"},
                    "evidence_payload": {"click_id": "click-1"},
                },
            )
            assert manual_response.status_code == 201
            assert manual_response.json()["touchpoint_type"] == "passive_click"

            refreshed_list_response = await async_client.get(
                f"/api/v1/attribution/touchpoints?quote_session_id={quote_payload['id']}",
                headers=support_headers,
            )
            assert refreshed_list_response.status_code == 200
            assert [item["touchpoint_type"] for item in refreshed_list_response.json()] == [
                "storefront_origin",
                "explicit_code",
                "passive_click",
            ]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
