from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.application.use_cases.payments.payment_webhook import ProcessPaymentWebhookUseCase
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.models.payment_attempt_model import PaymentAttemptModel
from src.infrastructure.payments.cryptobot.webhook_handler import CryptoBotWebhookHandler
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
        self._counter = 1000

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
        headers={**headers, "Idempotency-Key": "attempt-order-checkout"},
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
async def test_payment_attempts_are_idempotent_and_support_retry_after_terminal_failure(
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
            access_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Auth-Realm": "customer",
            }
            order_payload = await _create_committed_order(
                async_client=async_client,
                headers=headers,
                storefront_key=seeded["storefront_key"],
                pricebook_key=seeded["pricebook_key"],
                offer_key=seeded["offer_key"],
                plan_id=seeded["plan_id"],
            )

            first_attempt_response = await async_client.post(
                "/api/v1/payment-attempts/",
                headers={**headers, "Idempotency-Key": "attempt-1"},
                json={"order_id": order_payload["id"]},
            )
            assert first_attempt_response.status_code == 201
            first_attempt = first_attempt_response.json()
            assert first_attempt["order_id"] == order_payload["id"]
            assert first_attempt["attempt_number"] == 1
            assert first_attempt["status"] == "pending"
            assert first_attempt["invoice"]["invoice_id"] == "1001"

            duplicate_response = await async_client.post(
                "/api/v1/payment-attempts/",
                headers={**headers, "Idempotency-Key": "attempt-1"},
                json={"order_id": order_payload["id"]},
            )
            assert duplicate_response.status_code == 200
            assert duplicate_response.json()["id"] == first_attempt["id"]

            active_conflict_response = await async_client.post(
                "/api/v1/payment-attempts/",
                headers={**headers, "Idempotency-Key": "attempt-2"},
                json={"order_id": order_payload["id"]},
            )
            assert active_conflict_response.status_code == 409

            with sessionmaker() as session:
                adapter = SyncSessionAdapter(session)
                webhook_use_case = ProcessPaymentWebhookUseCase(
                    adapter,
                    CryptoBotWebhookHandler(api_token="test-token"),
                )
                failed = await webhook_use_case._handle_invoice_failed("1001", "invoice_expired")
                assert failed["status"] == "processed"

            retry_response = await async_client.post(
                "/api/v1/payment-attempts/",
                headers={**headers, "Idempotency-Key": "attempt-2"},
                json={"order_id": order_payload["id"]},
            )
            assert retry_response.status_code == 201
            retry_attempt = retry_response.json()
            assert retry_attempt["attempt_number"] == 2
            assert retry_attempt["supersedes_attempt_id"] == first_attempt["id"]
            assert retry_attempt["invoice"]["invoice_id"] == "1002"

            list_response = await async_client.get(
                f"/api/v1/payment-attempts/?order_id={order_payload['id']}",
                headers=headers,
            )
            assert list_response.status_code == 200
            attempts = list_response.json()
            assert len(attempts) == 2
            assert [attempt["attempt_number"] for attempt in attempts] == [1, 2]
            assert attempts[0]["status"] == "expired"
            assert attempts[1]["status"] == "pending"

            with sessionmaker() as session:
                order = session.get(OrderModel, uuid.UUID(order_payload["id"]))
                assert order is not None
                assert order.settlement_status == "pending_payment"
                first_attempt_model = session.get(PaymentAttemptModel, uuid.UUID(first_attempt["id"]))
                assert first_attempt_model is not None
                assert first_attempt_model.status == "expired"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        app.dependency_overrides.pop(get_crypto_client, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_payment_attempt_creation_rejects_paid_orders(async_client: AsyncClient) -> None:
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
            access_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Auth-Realm": "customer",
            }
            order_payload = await _create_committed_order(
                async_client=async_client,
                headers=headers,
                storefront_key=seeded["storefront_key"],
                pricebook_key=seeded["pricebook_key"],
                offer_key=seeded["offer_key"],
                plan_id=seeded["plan_id"],
            )

            with sessionmaker() as session:
                order = session.get(OrderModel, uuid.UUID(order_payload["id"]))
                assert order is not None
                order.settlement_status = "paid"
                session.add(order)
                session.commit()

            response = await async_client.post(
                "/api/v1/payment-attempts/",
                headers={**headers, "Idempotency-Key": "paid-order-attempt"},
                json={"order_id": order_payload["id"]},
            )
            assert response.status_code == 409
    finally:
        app.dependency_overrides.pop(get_redis, None)
        app.dependency_overrides.pop(get_crypto_client, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
