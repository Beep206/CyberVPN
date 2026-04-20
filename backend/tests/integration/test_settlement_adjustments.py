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
async def test_refund_and_dispute_create_typed_settlement_side_effects(async_client: AsyncClient) -> None:
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
                    email="settlement-adjustments-owner@example.test",
                    password_hash=await auth_service.hash_password("SettlementAdjustmentsOwner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                partner_account = PartnerAccountModel(
                    id=uuid.uuid4(),
                    account_key="settlement-adjustments-workspace",
                    display_name="Settlement Adjustments Workspace",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                partner_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="ADJUSTFLOW01",
                    partner_account_id=partner_account.id,
                    partner_user_id=partner_owner.id,
                    markup_pct=20,
                    is_active=True,
                )
                admin_user = AdminUserModel(
                    login="settlement_adjustments_admin",
                    email="settlement-adjustments-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("SettlementAdjustmentsAdmin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add_all([partner_owner, partner_account, partner_code, admin_user])
                db.commit()
                admin_token = _make_admin_token(auth_service, user_id=admin_user.id, realm=admin_realm)

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

            _, checkout_payload = await _create_quote_checkout(
                async_client=async_client,
                headers=customer_headers,
                storefront_key=seeded["storefront_key"],
                pricebook_key=seeded["pricebook_key"],
                offer_key=seeded["offer_key"],
                plan_id=seeded["plan_id"],
                partner_code=partner_code.code,
                idempotency_key="phase4-adjustment-order",
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
                    idempotency_key="phase4-adjustment-attempt",
                    provider_snapshot={},
                    request_snapshot={},
                )
                db.add_all([payment, attempt])
                db.commit()

                results = await PostPaymentProcessingUseCase(adapter).execute(payment.id)
                db.commit()
                event_id = results["settlement_earning_event_id"]
                assert event_id is not None

            active_holds_response = await async_client.get(
                f"/api/v1/earning-holds/?earning_event_id={event_id}&hold_status=active",
                headers=admin_headers,
            )
            assert active_holds_response.status_code == 200
            hold_id = active_holds_response.json()[0]["id"]

            release_hold_response = await async_client.post(
                f"/api/v1/earning-holds/{hold_id}/release",
                headers=admin_headers,
                json={"release_reason_code": "phase4_adjustments_ready", "force": True},
            )
            assert release_hold_response.status_code == 200

            period_response = await async_client.post(
                "/api/v1/settlement-periods/",
                headers=admin_headers,
                json={
                    "partner_account_id": str(partner_account.id),
                    "period_key": "2026-04-adjustments",
                    "currency_code": "usd",
                    "window_start": "2026-04-01T00:00:00Z",
                    "window_end": "2026-05-01T00:00:00Z",
                },
            )
            assert period_response.status_code == 201
            period_payload = period_response.json()

            statement_response = await async_client.post(
                "/api/v1/partner-statements/generate",
                headers=admin_headers,
                json={"settlement_period_id": period_payload["id"]},
            )
            assert statement_response.status_code == 201
            statement_payload = statement_response.json()
            base_available_amount = statement_payload["available_amount"]
            assert base_available_amount > 0

            create_refund_response = await async_client.post(
                "/api/v1/refunds/",
                headers={**customer_headers, "Idempotency-Key": "phase4-adjustment-refund"},
                json={
                    "order_id": order_payload["id"],
                    "amount": 10,
                    "reason_code": "customer_request",
                },
            )
            assert create_refund_response.status_code == 201
            refund_payload = create_refund_response.json()

            update_refund_response = await async_client.patch(
                f"/api/v1/refunds/{refund_payload['id']}",
                headers=admin_headers,
                json={"refund_status": "succeeded"},
            )
            assert update_refund_response.status_code == 200

            statement_after_refund_response = await async_client.get(
                f"/api/v1/partner-statements/{statement_payload['id']}",
                headers=admin_headers,
            )
            assert statement_after_refund_response.status_code == 200
            statement_after_refund = statement_after_refund_response.json()
            assert statement_after_refund["adjustment_count"] == 1
            assert statement_after_refund["available_amount"] < base_available_amount

            refund_adjustments_response = await async_client.get(
                f"/api/v1/partner-statements/{statement_payload['id']}/adjustments",
                headers=admin_headers,
            )
            assert refund_adjustments_response.status_code == 200
            refund_adjustments = refund_adjustments_response.json()
            assert len(refund_adjustments) == 1
            assert refund_adjustments[0]["adjustment_type"] == "refund_clawback"
            assert refund_adjustments[0]["adjustment_direction"] == "debit"
            assert refund_adjustments[0]["source_reference_type"] == "refund"
            assert refund_adjustments[0]["source_reference_id"] == refund_payload["id"]

            open_dispute_response = await async_client.post(
                "/api/v1/payment-disputes/",
                headers=admin_headers,
                json={
                    "order_id": order_payload["id"],
                    "payment_attempt_id": str(attempt.id),
                    "payment_id": str(payment.id),
                    "provider": "cryptobot",
                    "external_reference": "dispute-001",
                    "subtype": "chargeback",
                    "outcome_class": "open",
                    "lifecycle_status": "under_review",
                    "disputed_amount": 20,
                    "fee_amount": 0,
                    "fee_status": "none",
                },
            )
            assert open_dispute_response.status_code == 201

            event_after_open_dispute = await async_client.get(
                f"/api/v1/earning-events/{event_id}",
                headers=admin_headers,
            )
            assert event_after_open_dispute.status_code == 200
            assert event_after_open_dispute.json()["event_status"] == "blocked"

            active_reserves_response = await async_client.get(
                f"/api/v1/reserves/?source_earning_event_id={event_id}&reserve_status=active",
                headers=admin_headers,
            )
            assert active_reserves_response.status_code == 200
            active_reserves = active_reserves_response.json()
            assert len(active_reserves) == 1
            assert active_reserves[0]["reserve_reason_type"] == "dispute_buffer"

            lost_dispute_response = await async_client.post(
                "/api/v1/payment-disputes/",
                headers=admin_headers,
                json={
                    "order_id": order_payload["id"],
                    "payment_attempt_id": str(attempt.id),
                    "payment_id": str(payment.id),
                    "provider": "cryptobot",
                    "external_reference": "dispute-001",
                    "subtype": "chargeback",
                    "outcome_class": "lost",
                    "lifecycle_status": "closed",
                    "disputed_amount": 20,
                    "fee_amount": 0,
                    "fee_status": "none",
                },
            )
            assert lost_dispute_response.status_code == 200

            active_reserves_after_lost = await async_client.get(
                f"/api/v1/reserves/?source_earning_event_id={event_id}&reserve_status=active",
                headers=admin_headers,
            )
            assert active_reserves_after_lost.status_code == 200
            assert active_reserves_after_lost.json() == []

            adjustments_after_lost = await async_client.get(
                f"/api/v1/partner-statements/{statement_payload['id']}/adjustments",
                headers=admin_headers,
            )
            assert adjustments_after_lost.status_code == 200
            lost_adjustments = adjustments_after_lost.json()
            assert len(lost_adjustments) == 2
            assert {item["adjustment_type"] for item in lost_adjustments} == {
                "refund_clawback",
                "dispute_clawback",
            }

            reversed_dispute_response = await async_client.post(
                "/api/v1/payment-disputes/",
                headers=admin_headers,
                json={
                    "order_id": order_payload["id"],
                    "payment_attempt_id": str(attempt.id),
                    "payment_id": str(payment.id),
                    "provider": "cryptobot",
                    "external_reference": "dispute-001",
                    "subtype": "dispute_reversal",
                    "outcome_class": "reversed",
                    "lifecycle_status": "closed",
                    "disputed_amount": 20,
                    "fee_amount": 0,
                    "fee_status": "none",
                },
            )
            assert reversed_dispute_response.status_code == 200

            adjustments_after_reversal = await async_client.get(
                f"/api/v1/partner-statements/{statement_payload['id']}/adjustments",
                headers=admin_headers,
            )
            assert adjustments_after_reversal.status_code == 200
            final_adjustments = adjustments_after_reversal.json()
            assert len(final_adjustments) == 3
            assert {
                (item["adjustment_type"], item["adjustment_direction"])
                for item in final_adjustments
            } == {
                ("refund_clawback", "debit"),
                ("dispute_clawback", "debit"),
                ("reserve_release", "credit"),
            }
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
