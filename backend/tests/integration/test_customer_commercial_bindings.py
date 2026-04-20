from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeModel
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
async def test_reseller_binding_persists_separately_from_touchpoints(async_client: AsyncClient) -> None:
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
                    email="reseller-owner@partner.example.test",
                    password_hash=await auth_service.hash_password("ResellerOwner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                partner_workspace = PartnerAccountModel(
                    id=uuid.uuid4(),
                    account_key="nebula-reseller",
                    display_name="Nebula Reseller",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                reseller_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="RESELLER20",
                    partner_account_id=partner_workspace.id,
                    partner_user_id=partner_owner.id,
                    markup_pct=20,
                    is_active=True,
                )
                affiliate_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="AFFILIATE10",
                    partner_user_id=partner_owner.id,
                    markup_pct=10,
                    is_active=True,
                )
                admin_user = AdminUserModel(
                    login="binding_admin",
                    email="binding-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("BindingAdmin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                support_user = AdminUserModel(
                    login="binding_support",
                    email="binding-support@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("BindingSupport123!"),
                    role="support",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add_all(
                    [
                        partner_owner,
                        partner_workspace,
                        reseller_code,
                        affiliate_code,
                        admin_user,
                        support_user,
                    ]
                )
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

            bind_response = await async_client.post(
                "/api/v1/partner/bind",
                headers=customer_headers,
                json={"partner_code": reseller_code.code},
            )
            assert bind_response.status_code == 200

            bindings_response = await async_client.get(
                f"/api/v1/commercial-bindings/?user_id={seeded['customer_user_id']}&binding_status=active",
                headers=support_headers,
            )
            assert bindings_response.status_code == 200
            bindings = bindings_response.json()
            assert len(bindings) == 1
            assert bindings[0]["binding_type"] == "reseller_binding"
            assert bindings[0]["owner_type"] == "reseller"
            assert bindings[0]["partner_code_id"] == str(reseller_code.id)
            assert bindings[0]["partner_account_id"] == str(partner_workspace.id)

            quote_response = await async_client.post(
                "/api/v1/quotes/?utm_source=review",
                headers=customer_headers,
                json={
                    "storefront_key": seeded["storefront_key"],
                    "pricebook_key": seeded["pricebook_key"],
                    "offer_key": seeded["offer_key"],
                    "plan_id": seeded["plan_id"],
                    "currency": "USD",
                    "channel": "web",
                    "partner_code": affiliate_code.code,
                    "use_wallet": 0,
                    "addons": [],
                },
            )
            assert quote_response.status_code == 201
            quote_payload = quote_response.json()

            touchpoints_response = await async_client.get(
                f"/api/v1/attribution/touchpoints?quote_session_id={quote_payload['id']}",
                headers=support_headers,
            )
            assert touchpoints_response.status_code == 200
            assert [item["touchpoint_type"] for item in touchpoints_response.json()] == [
                "storefront_origin",
                "explicit_code",
            ]
            assert touchpoints_response.json()[1]["partner_code_id"] == str(affiliate_code.id)

            bindings_after_click = await async_client.get(
                f"/api/v1/commercial-bindings/?user_id={seeded['customer_user_id']}&binding_status=active",
                headers=support_headers,
            )
            assert bindings_after_click.status_code == 200
            assert len(bindings_after_click.json()) == 1
            assert bindings_after_click.json()[0]["partner_code_id"] == str(reseller_code.id)

            manual_override_response = await async_client.post(
                "/api/v1/commercial-bindings/",
                headers=admin_headers,
                json={
                    "user_id": seeded["customer_user_id"],
                    "binding_type": "manual_override",
                    "owner_type": "reseller",
                    "partner_code_id": str(affiliate_code.id),
                    "reason_code": "support_reassignment",
                    "evidence_payload": {"ticket_id": "SUP-101"},
                },
            )
            assert manual_override_response.status_code == 201
            manual_override = manual_override_response.json()
            assert manual_override["binding_type"] == "manual_override"
            assert manual_override["partner_code_id"] == str(affiliate_code.id)

            get_manual_override_response = await async_client.get(
                f"/api/v1/commercial-bindings/{manual_override['id']}",
                headers=support_headers,
            )
            assert get_manual_override_response.status_code == 200
            assert get_manual_override_response.json()["id"] == manual_override["id"]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
