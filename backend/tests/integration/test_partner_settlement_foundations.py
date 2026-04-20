from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.application.use_cases.payments.post_payment import PostPaymentProcessingUseCase
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeModel
from src.infrastructure.database.models.payment_attempt_model import PaymentAttemptModel
from src.infrastructure.database.models.payment_model import PaymentModel
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

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_partner_settlement_foundations_dual_write_and_manual_controls(async_client: AsyncClient) -> None:
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

                partner_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="settlement-owner@example.test",
                    password_hash=await auth_service.hash_password("SettlementOwner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                partner_account = PartnerAccountModel(
                    id=uuid.uuid4(),
                    account_key="settlement-workspace",
                    display_name="Settlement Workspace",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                partner_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="SETTLE01",
                    partner_account_id=partner_account.id,
                    partner_user_id=partner_owner.id,
                    markup_pct=15,
                    is_active=True,
                )
                admin_user = AdminUserModel(
                    login="settlement_admin",
                    email="settlement-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("SettlementAdmin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                support_user = AdminUserModel(
                    login="settlement_support",
                    email="settlement-support@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("SettlementSupport123!"),
                    role="support",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add_all([partner_owner, partner_account, partner_code, admin_user, support_user])
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

            _, checkout_payload = await _create_quote_checkout(
                async_client=async_client,
                headers=customer_headers,
                storefront_key=seeded["storefront_key"],
                pricebook_key=seeded["pricebook_key"],
                offer_key=seeded["offer_key"],
                plan_id=seeded["plan_id"],
                partner_code=partner_code.code,
                idempotency_key="phase4-settlement-order",
            )
            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=customer_headers,
                json={"checkout_session_id": checkout_payload["id"]},
            )
            assert order_response.status_code == 201
            order_payload = order_response.json()

            with sessionmaker() as db:
                adapter = SyncSessionAdapter(db)
                payment = PaymentModel(
                    id=uuid.uuid4(),
                    user_uuid=uuid.UUID(seeded["customer_user_id"]),
                    amount=Decimal(str(order_payload["displayed_price"])),
                    currency="USD",
                    status="completed",
                    provider="cryptobot",
                    subscription_days=365,
                    plan_id=uuid.UUID(seeded["plan_id"]),
                    partner_code_id=partner_code.id,
                    metadata_={"commission_base_amount": str(order_payload["commission_base_amount"])},
                )
                attempt = PaymentAttemptModel(
                    id=uuid.uuid4(),
                    order_id=uuid.UUID(order_payload["id"]),
                    payment_id=payment.id,
                    attempt_number=1,
                    provider="cryptobot",
                    sale_channel="web",
                    currency_code="USD",
                    status="succeeded",
                    displayed_amount=Decimal(str(order_payload["displayed_price"])),
                    wallet_amount=Decimal("0"),
                    gateway_amount=Decimal(str(order_payload["gateway_amount"])),
                    idempotency_key="phase4-settlement-attempt",
                    provider_snapshot={},
                    request_snapshot={},
                )
                db.add_all([payment, attempt])
                db.commit()

                results = await PostPaymentProcessingUseCase(adapter).execute(payment.id)
                db.commit()

                assert results["partner_earning"] is not None
                assert results["settlement_earning_event_id"] is not None
                event_id = results["settlement_earning_event_id"]

            event_response = await async_client.get(
                f"/api/v1/earning-events/{event_id}",
                headers=support_headers,
            )
            assert event_response.status_code == 200
            event_payload = event_response.json()
            assert event_payload["order_id"] == order_payload["id"]
            assert event_payload["partner_account_id"] == str(partner_account.id)
            assert event_payload["event_status"] == "on_hold"

            holds_response = await async_client.get(
                f"/api/v1/earning-holds/?earning_event_id={event_id}&hold_status=active",
                headers=support_headers,
            )
            assert holds_response.status_code == 200
            holds_payload = holds_response.json()
            assert len(holds_payload) == 1
            hold_id = holds_payload[0]["id"]
            assert holds_payload[0]["hold_reason_type"] == "payout_hold"

            release_hold_response = await async_client.post(
                f"/api/v1/earning-holds/{hold_id}/release",
                headers=admin_headers,
                json={"release_reason_code": "manual_internal_release", "force": True},
            )
            assert release_hold_response.status_code == 200
            assert release_hold_response.json()["hold_status"] == "released"

            event_after_hold_release = await async_client.get(
                f"/api/v1/earning-events/{event_id}",
                headers=support_headers,
            )
            assert event_after_hold_release.status_code == 200
            assert event_after_hold_release.json()["event_status"] == "available"
            assert event_after_hold_release.json()["available_at"] is not None

            reserve_response = await async_client.post(
                "/api/v1/reserves/",
                headers=admin_headers,
                json={
                    "partner_account_id": str(partner_account.id),
                    "amount": 5,
                    "currency_code": "USD",
                    "reserve_scope": "earning_event",
                    "reserve_reason_type": "manual",
                    "source_earning_event_id": event_id,
                    "reason_code": "manual_review_buffer",
                    "reserve_payload": {"source": "phase4-test"},
                },
            )
            assert reserve_response.status_code == 201
            reserve_id = reserve_response.json()["id"]

            event_after_reserve = await async_client.get(
                f"/api/v1/earning-events/{event_id}",
                headers=support_headers,
            )
            assert event_after_reserve.status_code == 200
            assert event_after_reserve.json()["event_status"] == "blocked"

            release_reserve_response = await async_client.post(
                f"/api/v1/reserves/{reserve_id}/release",
                headers=admin_headers,
                json={"release_reason_code": "buffer_cleared"},
            )
            assert release_reserve_response.status_code == 200
            assert release_reserve_response.json()["reserve_status"] == "released"

            final_event_response = await async_client.get(
                f"/api/v1/earning-events/{event_id}",
                headers=support_headers,
            )
            assert final_event_response.status_code == 200
            assert final_event_response.json()["event_status"] == "available"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        cleanup_sqlite_file(sqlite_path)
