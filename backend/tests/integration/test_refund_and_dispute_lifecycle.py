from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.models.payment_attempt_model import PaymentAttemptModel
from src.infrastructure.database.models.payment_model import PaymentModel
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
from tests.integration.test_order_commit import _make_customer_access_token, _seed_order_context

pytestmark = [pytest.mark.integration]


class FakeCryptoBotClient:
    def __init__(self) -> None:
        self._counter = 2000

    async def create_invoice(self, amount: str, currency: str, description: str, payload: str | None = None) -> dict:
        _ = amount, currency, description, payload
        self._counter += 1
        invoice_id = str(self._counter)
        return {
            "invoice_id": invoice_id,
            "pay_url": f"https://pay.example.test/{invoice_id}",
            "status": "pending",
            "expiration_date": "2030-01-01T00:00:00+00:00",
        }


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


async def _create_committed_order(
    *,
    async_client: AsyncClient,
    headers: dict[str, str],
    storefront_key: str,
    pricebook_key: str,
    offer_key: str,
    plan_id: str,
) -> dict:
    quote_response = await async_client.post(
        "/api/v1/quotes/",
        headers=headers,
        json={
            "storefront_key": storefront_key,
            "pricebook_key": pricebook_key,
            "offer_key": offer_key,
            "plan_id": plan_id,
            "currency": "USD",
            "channel": "web",
            "use_wallet": 0,
            "addons": [],
        },
    )
    assert quote_response.status_code == 201

    checkout_response = await async_client.post(
        "/api/v1/checkout-sessions/",
        headers={**headers, "Idempotency-Key": "refund-order-checkout"},
        json={"quote_session_id": quote_response.json()["id"]},
    )
    assert checkout_response.status_code == 201

    order_response = await async_client.post(
        "/api/v1/orders/commit",
        headers=headers,
        json={"checkout_session_id": checkout_response.json()["id"]},
    )
    assert order_response.status_code == 201
    return order_response.json()


@pytest.mark.asyncio
async def test_refunds_and_payment_disputes_are_order_linked_and_support_normalized_lifecycle(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    fake_crypto = FakeCryptoBotClient()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

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
                admin_user = AdminUserModel(
                    login="refund_admin",
                    email="refund-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("RefundAdminP@ssword123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add(admin_user)
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

            order_payload = await _create_committed_order(
                async_client=async_client,
                headers=customer_headers,
                storefront_key=seeded["storefront_key"],
                pricebook_key=seeded["pricebook_key"],
                offer_key=seeded["offer_key"],
                plan_id=seeded["plan_id"],
            )
            displayed_price = float(order_payload["displayed_price"])
            first_refund_amount = 20.0
            remaining_after_first = displayed_price - first_refund_amount

            attempt_response = await async_client.post(
                "/api/v1/payment-attempts/",
                headers={**customer_headers, "Idempotency-Key": "attempt-refund-1"},
                json={"order_id": order_payload["id"]},
            )
            assert attempt_response.status_code == 201
            attempt_payload = attempt_response.json()

            with sessionmaker() as db:
                payment_attempt = db.get(PaymentAttemptModel, uuid.UUID(attempt_payload["id"]))
                payment = db.get(PaymentModel, uuid.UUID(attempt_payload["payment_id"]))
                order = db.get(OrderModel, uuid.UUID(order_payload["id"]))
                assert payment_attempt is not None
                assert payment is not None
                assert order is not None
                payment_attempt.status = "succeeded"
                payment.status = "completed"
                order.settlement_status = "paid"
                db.commit()

            first_refund_response = await async_client.post(
                "/api/v1/refunds/",
                headers={**customer_headers, "Idempotency-Key": "refund-1"},
                json={
                    "order_id": order_payload["id"],
                    "amount": first_refund_amount,
                    "reason_code": "customer_request",
                    "reason_text": "Please refund part of the order",
                },
            )
            assert first_refund_response.status_code == 201
            first_refund = first_refund_response.json()
            assert first_refund["refund_status"] == "requested"
            assert first_refund["payment_attempt_id"] == attempt_payload["id"]

            duplicate_refund_response = await async_client.post(
                "/api/v1/refunds/",
                headers={**customer_headers, "Idempotency-Key": "refund-1"},
                json={
                    "order_id": order_payload["id"],
                    "amount": first_refund_amount,
                },
            )
            assert duplicate_refund_response.status_code == 200
            assert duplicate_refund_response.json()["id"] == first_refund["id"]

            overflow_refund_response = await async_client.post(
                "/api/v1/refunds/",
                headers={**customer_headers, "Idempotency-Key": "refund-overflow"},
                json={
                    "order_id": order_payload["id"],
                    "amount": remaining_after_first + 1,
                },
            )
            assert overflow_refund_response.status_code == 400

            first_refund_completed = await async_client.patch(
                f"/api/v1/refunds/{first_refund['id']}",
                headers=admin_headers,
                json={
                    "refund_status": "succeeded",
                    "external_reference": "refund-ext-1",
                    "provider_snapshot": {"provider_ref": "refund-ext-1"},
                },
            )
            assert first_refund_completed.status_code == 200
            assert first_refund_completed.json()["refund_status"] == "succeeded"

            second_refund_response = await async_client.post(
                "/api/v1/refunds/",
                headers={**customer_headers, "Idempotency-Key": "refund-2"},
                json={
                    "order_id": order_payload["id"],
                    "amount": remaining_after_first,
                    "reason_code": "service_issue",
                },
            )
            assert second_refund_response.status_code == 201
            second_refund = second_refund_response.json()

            second_refund_completed = await async_client.patch(
                f"/api/v1/refunds/{second_refund['id']}",
                headers=admin_headers,
                json={
                    "refund_status": "succeeded",
                    "external_reference": "refund-ext-2",
                    "provider_snapshot": {"provider_ref": "refund-ext-2"},
                },
            )
            assert second_refund_completed.status_code == 200

            refunds_response = await async_client.get(
                f"/api/v1/refunds/?order_id={order_payload['id']}",
                headers=customer_headers,
            )
            assert refunds_response.status_code == 200
            refunds_payload = refunds_response.json()
            assert len(refunds_payload) == 2
            assert [refund["amount"] for refund in refunds_payload] == [first_refund_amount, remaining_after_first]

            order_response = await async_client.get(
                f"/api/v1/orders/{order_payload['id']}",
                headers=customer_headers,
            )
            assert order_response.status_code == 200
            assert order_response.json()["settlement_status"] == "refunded"

            initial_dispute_response = await async_client.post(
                "/api/v1/payment-disputes/",
                headers=admin_headers,
                json={
                    "order_id": order_payload["id"],
                    "payment_attempt_id": attempt_payload["id"],
                    "provider": "cryptobot",
                    "external_reference": "dispute-2001",
                    "subtype": "inquiry",
                    "outcome_class": "open",
                    "lifecycle_status": "opened",
                    "disputed_amount": displayed_price,
                    "fee_amount": 0,
                    "fee_status": "none",
                    "reason_code": "cardholder_inquiry",
                    "evidence_snapshot": {"stage": "inquiry"},
                    "provider_snapshot": {"provider_state": "warning_open"},
                },
            )
            assert initial_dispute_response.status_code == 201
            initial_dispute = initial_dispute_response.json()

            chargeback_update_response = await async_client.post(
                "/api/v1/payment-disputes/",
                headers=admin_headers,
                json={
                    "order_id": order_payload["id"],
                    "payment_attempt_id": attempt_payload["id"],
                    "provider": "cryptobot",
                    "external_reference": "dispute-2001",
                    "subtype": "chargeback",
                    "outcome_class": "open",
                    "lifecycle_status": "under_review",
                    "disputed_amount": displayed_price,
                    "fee_amount": 15,
                    "fee_status": "assessed",
                    "reason_code": "chargeback_received",
                    "evidence_snapshot": {"stage": "chargeback"},
                    "provider_snapshot": {"provider_state": "chargeback_open"},
                },
            )
            assert chargeback_update_response.status_code == 200
            chargeback_update = chargeback_update_response.json()
            assert chargeback_update["id"] == initial_dispute["id"]
            assert chargeback_update["subtype"] == "chargeback"
            assert chargeback_update["fee_status"] == "assessed"

            reversal_update_response = await async_client.post(
                "/api/v1/payment-disputes/",
                headers=admin_headers,
                json={
                    "order_id": order_payload["id"],
                    "payment_attempt_id": attempt_payload["id"],
                    "provider": "cryptobot",
                    "external_reference": "dispute-2001",
                    "subtype": "dispute_reversal",
                    "outcome_class": "reversed",
                    "lifecycle_status": "closed",
                    "disputed_amount": displayed_price,
                    "fee_amount": 0,
                    "fee_status": "reversed",
                    "reason_code": "chargeback_reversed",
                    "evidence_snapshot": {"stage": "reversed"},
                    "provider_snapshot": {"provider_state": "reversed"},
                },
            )
            assert reversal_update_response.status_code == 200
            reversal_update = reversal_update_response.json()
            assert reversal_update["id"] == initial_dispute["id"]
            assert reversal_update["subtype"] == "dispute_reversal"
            assert reversal_update["outcome_class"] == "reversed"
            assert reversal_update["lifecycle_status"] == "closed"
            assert reversal_update["fee_status"] == "reversed"
            assert reversal_update["closed_at"] is not None

            list_disputes_response = await async_client.get(
                f"/api/v1/payment-disputes/?order_id={order_payload['id']}",
                headers=admin_headers,
            )
            assert list_disputes_response.status_code == 200
            disputes_payload = list_disputes_response.json()
            assert len(disputes_payload) == 1
            assert disputes_payload[0]["id"] == initial_dispute["id"]

            with sessionmaker() as db:
                payment = db.get(PaymentModel, uuid.UUID(attempt_payload["payment_id"]))
                order = db.get(OrderModel, uuid.UUID(order_payload["id"]))
                assert payment is not None
                assert payment.status == "refunded"
                assert order is not None
                assert order.settlement_status == "refunded"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        app.dependency_overrides.pop(get_crypto_client, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
