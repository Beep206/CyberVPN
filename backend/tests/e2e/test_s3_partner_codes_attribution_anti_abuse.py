from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.config.settings import settings
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.main import app
from src.presentation.dependencies.services import get_crypto_client
from tests.helpers.realm_auth import (
    FakeRedis,
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)
from tests.integration.test_order_attribution_resolution import (
    FakeCryptoBotClient,
    _create_quote_checkout,
    _make_admin_token,
)
from tests.integration.test_order_commit import _make_customer_access_token, _seed_order_context

pytestmark = [pytest.mark.e2e]


@pytest.mark.asyncio
async def test_s3_partner_codes_attribution_and_abuse_controls(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    fake_crypto = FakeCryptoBotClient()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    monkeypatch.setattr(settings, "checkout_code_discounts_enabled", True)

    async def _override_redis():
        yield fake_redis

    async def _override_crypto():
        return fake_crypto

    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_crypto_client] = _override_crypto

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
                admin_password = "S3Stage08Admin123!"

                partner_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="s3-stage08-owner@example.test",
                    password_hash=await auth_service.hash_password("S3Stage08Owner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                reseller_workspace = PartnerAccountModel(
                    id=uuid.uuid4(),
                    account_key="s3-stage08-reseller",
                    display_name="S3 Stage08 Reseller",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                reseller_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="S3STAGE08",
                    partner_account_id=reseller_workspace.id,
                    partner_user_id=partner_owner.id,
                    markup_pct=10,
                    is_active=True,
                )
                admin_user = AdminUserModel(
                    login="s3_stage08_admin",
                    email="s3-stage08-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password(admin_password),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                support_user = AdminUserModel(
                    login="s3_stage08_support",
                    email="s3-stage08-support@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("S3Stage08Support123!"),
                    role="support",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add_all([partner_owner, reseller_workspace, reseller_code, admin_user, support_user])
                db.commit()

                support_token = _make_admin_token(auth_service, user_id=support_user.id, realm=admin_realm)
                partner_owner_id = partner_owner.id

            admin_login_response = await async_client.post(
                "/api/v1/auth/login",
                json={
                    "login_or_email": "s3_stage08_admin",
                    "password": admin_password,
                },
                headers={"X-Auth-Realm": "admin"},
            )
            assert admin_login_response.status_code == 200
            admin_token = admin_login_response.json()["access_token"]

            owner_token = _make_customer_access_token(
                auth_service,
                user_id=partner_owner_id,
                customer_realm=customer_realm,
            )
            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            owner_headers = {
                "Authorization": f"Bearer {owner_token}",
                "X-Auth-Realm": "customer",
            }
            customer_headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }
            admin_headers = {
                "Authorization": f"Bearer {admin_token}",
                "X-Auth-Realm": "admin",
                "Host": "testserver",
            }
            support_headers = {
                "Authorization": f"Bearer {support_token}",
                "X-Auth-Realm": "admin",
            }

            for _ in range(3):
                self_referral_response = await async_client.post(
                    "/api/v1/codes/resolve",
                    headers=owner_headers,
                    json={
                        "code": reseller_code.code,
                        "action_context": "checkout",
                        "storefront_key": seeded["storefront_key"],
                        "plan_id": seeded["plan_id"],
                        "amount": 75,
                        "channel": "web",
                    },
                )
                assert self_referral_response.status_code == 200
                self_referral_payload = self_referral_response.json()
                assert self_referral_payload["accepted"] is False
                assert self_referral_payload["code_type"] == "partner"
                assert self_referral_payload["result"] == "blocked_by_risk"
                assert self_referral_payload["reject_reason"] == "code_blocked_by_risk"
                assert self_referral_payload["partner_code_id"] == str(reseller_code.id)

            abuse_queue_response = await async_client.get(
                "/api/v1/admin/growth-signals/abuse-queue?limit=10",
                headers=admin_headers,
            )
            assert abuse_queue_response.status_code == 200, abuse_queue_response.text
            abuse_queue = abuse_queue_response.json()["items"]
            self_referral_signal = next(
                item for item in abuse_queue if item["reason_code"] == "code_blocked_by_risk"
            )
            assert self_referral_signal["code_type"] == "partner"
            assert self_referral_signal["severity"] == "danger"
            assert self_referral_signal["count"] == 3

            first_bind_response = await async_client.post(
                "/api/v1/partner/bind",
                headers=customer_headers,
                json={"partner_code": reseller_code.code},
            )
            assert first_bind_response.status_code == 200

            duplicate_bind_response = await async_client.post(
                "/api/v1/partner/bind",
                headers=customer_headers,
                json={"partner_code": reseller_code.code},
            )
            assert duplicate_bind_response.status_code == 200

            quote_payload, checkout_payload = await _create_quote_checkout(
                async_client=async_client,
                headers=customer_headers,
                storefront_key=seeded["storefront_key"],
                pricebook_key=seeded["pricebook_key"],
                offer_key=seeded["offer_key"],
                plan_id=seeded["plan_id"],
                partner_code=None,
                idempotency_key="s3-stage08-binding-checkout",
            )
            assert quote_payload["quote"]["partner_code_id"] == str(reseller_code.id)

            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=customer_headers,
                json={"checkout_session_id": checkout_payload["id"]},
            )
            assert order_response.status_code == 201
            order_payload = order_response.json()

            result_response = await async_client.get(
                f"/api/v1/attribution/orders/{order_payload['id']}/result",
                headers=support_headers,
            )
            assert result_response.status_code == 200
            result_payload = result_response.json()
            assert result_payload["owner_type"] == "reseller"
            assert result_payload["owner_source"] == "persistent_reseller_binding"
            assert result_payload["partner_account_id"] == str(reseller_workspace.id)
            assert result_payload["partner_code_id"] == str(reseller_code.id)
            assert "persistent_reseller_binding_selected" in result_payload["rule_path"]

            duplicate_resolve_response = await async_client.post(
                f"/api/v1/attribution/orders/{order_payload['id']}/resolve",
                headers=admin_headers,
            )
            assert duplicate_resolve_response.status_code == 200
            assert duplicate_resolve_response.json()["id"] == result_payload["id"]

            explainability_response = await async_client.get(
                f"/api/v1/orders/{order_payload['id']}/explainability",
                headers=support_headers,
            )
            assert explainability_response.status_code == 200
            explainability = explainability_response.json()["explainability"]
            assert explainability["commercial_resolution_summary"]["resolved_owner_type"] == "reseller"
            assert (
                explainability["commercial_resolution_summary"]["resolved_owner_source"]
                == "persistent_reseller_binding"
            )
    finally:
        app.dependency_overrides.pop(get_redis, None)
        app.dependency_overrides.pop(get_crypto_client, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
