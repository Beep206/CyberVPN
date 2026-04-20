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
from tests.integration.test_order_attribution_resolution import _create_quote_checkout, _make_admin_token
from tests.integration.test_order_commit import _make_customer_access_token, _seed_order_context

pytestmark = [pytest.mark.e2e, pytest.mark.integration]


async def _commit_order(
    *,
    async_client: AsyncClient,
    headers: dict[str, str],
    seeded: dict[str, str],
    idempotency_key: str,
    partner_code: str | None = None,
) -> dict:
    _, checkout_payload = await _create_quote_checkout(
        async_client=async_client,
        headers=headers,
        storefront_key=seeded["storefront_key"],
        pricebook_key=seeded["pricebook_key"],
        offer_key=seeded["offer_key"],
        plan_id=seeded["plan_id"],
        partner_code=partner_code,
        idempotency_key=idempotency_key,
    )
    order_response = await async_client.post(
        "/api/v1/orders/commit",
        headers=headers,
        json={"checkout_session_id": checkout_payload["id"]},
    )
    assert order_response.status_code == 201
    return order_response.json()


@pytest.mark.asyncio
async def test_phase3_attribution_foundations_end_to_end(async_client: AsyncClient) -> None:
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

                affiliate_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="phase3-affiliate-owner@example.test",
                    password_hash=await auth_service.hash_password("Phase3AffiliateOwner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                affiliate_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="PH3AFF01",
                    partner_user_id=affiliate_owner.id,
                    markup_pct=12,
                    is_active=True,
                )
                reseller_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="phase3-reseller-owner@example.test",
                    password_hash=await auth_service.hash_password("Phase3ResellerOwner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                reseller_account = PartnerAccountModel(
                    id=uuid.uuid4(),
                    account_key="phase3-reseller-account",
                    display_name="Phase3 Reseller",
                    status="active",
                    legacy_owner_user_id=reseller_owner.id,
                )
                reseller_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="PH3RES01",
                    partner_account_id=reseller_account.id,
                    partner_user_id=reseller_owner.id,
                    markup_pct=9,
                    is_active=True,
                )
                admin_user = AdminUserModel(
                    login="phase3_admin",
                    email="phase3-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("Phase3AdminP@ssword123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                support_user = AdminUserModel(
                    login="phase3_support",
                    email="phase3-support@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("Phase3SupportP@ssword123!"),
                    role="support",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add_all(
                    [
                        affiliate_owner,
                        affiliate_code,
                        reseller_owner,
                        reseller_account,
                        reseller_code,
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

            affiliate_order = await _commit_order(
                async_client=async_client,
                headers=customer_headers,
                seeded=seeded,
                idempotency_key="phase3-affiliate-order",
                partner_code=affiliate_code.code,
            )
            attribution_result_response = await async_client.get(
                f"/api/v1/attribution/orders/{affiliate_order['id']}/result",
                headers=support_headers,
            )
            assert attribution_result_response.status_code == 200
            assert attribution_result_response.json()["owner_type"] == "affiliate"

            for reward_type, source_key in (
                ("invite_reward", f"phase3:{affiliate_order['id']}:invite_reward"),
                ("gift_bonus", f"phase3:{affiliate_order['id']}:gift_bonus"),
            ):
                reward_response = await async_client.post(
                    "/api/v1/growth-rewards/allocations",
                    headers=admin_headers,
                    json={
                        "reward_type": reward_type,
                        "beneficiary_user_id": seeded["customer_user_id"],
                        "order_id": affiliate_order["id"],
                        "quantity": 1,
                        "unit": "perk",
                        "source_key": source_key,
                        "reward_payload": {"source": "phase3-e2e"},
                    },
                )
                assert reward_response.status_code == 201

            affiliate_explainability = await async_client.get(
                f"/api/v1/orders/{affiliate_order['id']}/explainability",
                headers=support_headers,
            )
            assert affiliate_explainability.status_code == 200
            affiliate_payload = affiliate_explainability.json()["explainability"]
            assert affiliate_payload["lane_views"]["creator_affiliate"]["active"] is True
            assert affiliate_payload["lane_views"]["invite_gift"]["active"] is True
            assert affiliate_payload["commercial_resolution_summary"]["resolved_owner_type"] == "affiliate"

            referral_order = await _commit_order(
                async_client=async_client,
                headers=customer_headers,
                seeded=seeded,
                idempotency_key="phase3-referral-order",
            )
            referral_reward_response = await async_client.post(
                "/api/v1/growth-rewards/allocations",
                headers=admin_headers,
                json={
                    "reward_type": "referral_credit",
                    "beneficiary_user_id": seeded["customer_user_id"],
                    "order_id": referral_order["id"],
                    "quantity": 6,
                    "unit": "credit",
                    "currency_code": "USD",
                    "source_key": f"phase3:{referral_order['id']}:referral_credit",
                    "reward_payload": {"source": "phase3-e2e"},
                },
            )
            assert referral_reward_response.status_code == 201

            referral_explainability = await async_client.get(
                f"/api/v1/orders/{referral_order['id']}/explainability",
                headers=support_headers,
            )
            assert referral_explainability.status_code == 200
            referral_payload = referral_explainability.json()["explainability"]
            assert referral_payload["lane_views"]["consumer_referral"]["active"] is True
            assert referral_payload["growth_reward_summary"]["active_reward_types"] == ["referral_credit"]

            binding_response = await async_client.post(
                "/api/v1/partner/bind",
                headers=customer_headers,
                json={"partner_code": reseller_code.code},
            )
            assert binding_response.status_code == 200

            reseller_order = await _commit_order(
                async_client=async_client,
                headers=customer_headers,
                seeded=seeded,
                idempotency_key="phase3-reseller-order",
            )
            reseller_attribution = await async_client.get(
                f"/api/v1/attribution/orders/{reseller_order['id']}/result",
                headers=support_headers,
            )
            assert reseller_attribution.status_code == 200
            assert reseller_attribution.json()["owner_type"] == "reseller"

            reseller_explainability = await async_client.get(
                f"/api/v1/orders/{reseller_order['id']}/explainability",
                headers=support_headers,
            )
            assert reseller_explainability.status_code == 200
            reseller_payload = reseller_explainability.json()["explainability"]
            assert reseller_payload["lane_views"]["reseller_distribution"]["active"] is True
            assert reseller_payload["commercial_resolution_summary"]["resolved_owner_type"] == "reseller"

            renewal_order = await _commit_order(
                async_client=async_client,
                headers=customer_headers,
                seeded=seeded,
                idempotency_key="phase3-renewal-order",
            )
            renewal_response = await async_client.post(
                "/api/v1/renewal-orders/resolve",
                headers=admin_headers,
                json={
                    "order_id": renewal_order["id"],
                    "prior_order_id": affiliate_order["id"],
                    "renewal_mode": "manual",
                },
            )
            assert renewal_response.status_code == 201
            renewal_payload = renewal_response.json()
            assert renewal_payload["payout_eligible"] is True

            renewal_explainability = await async_client.get(
                f"/api/v1/orders/{renewal_order['id']}/explainability",
                headers=support_headers,
            )
            assert renewal_explainability.status_code == 200
            renewal_explainability_payload = renewal_explainability.json()["explainability"]
            assert renewal_explainability_payload["lane_views"]["renewal_chain"]["active"] is True
            assert renewal_explainability_payload["renewal_order"]["renewal_mode"] == "manual"
            assert renewal_explainability_payload["renewal_order"]["effective_owner_type"] == "reseller"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        cleanup_sqlite_file(sqlite_path)
