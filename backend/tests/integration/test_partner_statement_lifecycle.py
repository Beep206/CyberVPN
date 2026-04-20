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
async def test_partner_statement_lifecycle_close_reopen_and_adjustments(async_client: AsyncClient) -> None:
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
                    email="statement-owner@example.test",
                    password_hash=await auth_service.hash_password("StatementOwner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                partner_account = PartnerAccountModel(
                    id=uuid.uuid4(),
                    account_key="statement-workspace",
                    display_name="Statement Workspace",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                partner_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="STATEMENT01",
                    partner_account_id=partner_account.id,
                    partner_user_id=partner_owner.id,
                    markup_pct=20,
                    is_active=True,
                )
                admin_user = AdminUserModel(
                    login="statement_admin",
                    email="statement-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("StatementAdmin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                support_user = AdminUserModel(
                    login="statement_support",
                    email="statement-support@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("StatementSupport123!"),
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
                idempotency_key="phase4-statement-order",
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
                    idempotency_key="phase4-statement-attempt",
                    provider_snapshot={},
                    request_snapshot={},
                )
                db.add_all([payment, attempt])
                db.commit()

                results = await PostPaymentProcessingUseCase(adapter).execute(payment.id)
                db.commit()
                event_id = results["settlement_earning_event_id"]
                assert event_id is not None

            earning_event_response = await async_client.get(
                f"/api/v1/earning-events/{event_id}",
                headers=support_headers,
            )
            assert earning_event_response.status_code == 200
            earning_event_payload = earning_event_response.json()

            holds_response = await async_client.get(
                f"/api/v1/earning-holds/?earning_event_id={event_id}&hold_status=active",
                headers=support_headers,
            )
            assert holds_response.status_code == 200
            active_hold_id = holds_response.json()[0]["id"]

            period_response = await async_client.post(
                "/api/v1/settlement-periods/",
                headers=admin_headers,
                json={
                    "partner_account_id": str(partner_account.id),
                    "period_key": "2026-04-main",
                    "currency_code": "usd",
                    "window_start": "2026-04-01T00:00:00Z",
                    "window_end": "2026-05-01T00:00:00Z",
                },
            )
            assert period_response.status_code == 201
            period_payload = period_response.json()

            generate_statement_response = await async_client.post(
                "/api/v1/partner-statements/generate",
                headers=admin_headers,
                json={"settlement_period_id": period_payload["id"]},
            )
            assert generate_statement_response.status_code == 201
            statement_payload = generate_statement_response.json()
            assert statement_payload["statement_status"] == "open"
            assert statement_payload["source_event_count"] == 1
            assert statement_payload["held_event_count"] == 1
            assert statement_payload["accrual_amount"] == earning_event_payload["total_amount"]
            assert statement_payload["on_hold_amount"] == earning_event_payload["total_amount"]
            assert statement_payload["available_amount"] == 0.0

            close_statement_response = await async_client.post(
                f"/api/v1/partner-statements/{statement_payload['id']}/close",
                headers=admin_headers,
            )
            assert close_statement_response.status_code == 200
            assert close_statement_response.json()["statement_status"] == "closed"

            close_period_response = await async_client.post(
                f"/api/v1/settlement-periods/{period_payload['id']}/close",
                headers=admin_headers,
            )
            assert close_period_response.status_code == 200
            assert close_period_response.json()["period_status"] == "closed"

            release_hold_response = await async_client.post(
                f"/api/v1/earning-holds/{active_hold_id}/release",
                headers=admin_headers,
                json={"release_reason_code": "statement_reopen_test", "force": True},
            )
            assert release_hold_response.status_code == 200

            reopen_period_response = await async_client.post(
                f"/api/v1/settlement-periods/{period_payload['id']}/reopen",
                headers=admin_headers,
            )
            assert reopen_period_response.status_code == 200
            assert reopen_period_response.json()["period_status"] == "open"

            reopen_statement_response = await async_client.post(
                f"/api/v1/partner-statements/{statement_payload['id']}/reopen",
                headers=admin_headers,
            )
            assert reopen_statement_response.status_code == 200
            reopened_statement = reopen_statement_response.json()
            assert reopened_statement["statement_version"] == 2
            assert reopened_statement["reopened_from_statement_id"] == statement_payload["id"]
            assert reopened_statement["held_event_count"] == 0
            assert reopened_statement["on_hold_amount"] == 0.0
            assert reopened_statement["available_amount"] == earning_event_payload["total_amount"]

            adjustment_response = await async_client.post(
                f"/api/v1/partner-statements/{reopened_statement['id']}/adjustments",
                headers=admin_headers,
                json={
                    "adjustment_type": "manual",
                    "adjustment_direction": "credit",
                    "amount": 1.25,
                    "currency_code": "usd",
                    "reason_code": "manual_bonus",
                    "adjustment_payload": {"source": "phase4-lifecycle-test"},
                },
            )
            assert adjustment_response.status_code == 201
            adjustment_payload = adjustment_response.json()
            assert adjustment_payload["adjustment_type"] == "manual"
            assert adjustment_payload["adjustment_direction"] == "credit"
            assert adjustment_payload["amount"] == 1.25

            adjustments_response = await async_client.get(
                f"/api/v1/partner-statements/{reopened_statement['id']}/adjustments",
                headers=support_headers,
            )
            assert adjustments_response.status_code == 200
            assert len(adjustments_response.json()) == 1

            refreshed_statement_response = await async_client.get(
                f"/api/v1/partner-statements/{reopened_statement['id']}",
                headers=support_headers,
            )
            assert refreshed_statement_response.status_code == 200
            refreshed_statement = refreshed_statement_response.json()
            assert refreshed_statement["adjustment_count"] == 1
            assert refreshed_statement["adjustment_net_amount"] == 1.25
            assert refreshed_statement["available_amount"] == earning_event_payload["total_amount"] + 1.25

            final_close_response = await async_client.post(
                f"/api/v1/partner-statements/{reopened_statement['id']}/close",
                headers=admin_headers,
            )
            assert final_close_response.status_code == 200
            assert final_close_response.json()["statement_status"] == "closed"

            original_statement_response = await async_client.get(
                f"/api/v1/partner-statements/{statement_payload['id']}",
                headers=support_headers,
            )
            assert original_statement_response.status_code == 200
            original_statement = original_statement_response.json()
            assert original_statement["statement_status"] == "closed"
            assert original_statement["held_event_count"] == 1
            assert original_statement["superseded_by_statement_id"] == reopened_statement["id"]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        cleanup_sqlite_file(sqlite_path)
