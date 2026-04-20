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
from src.infrastructure.database.models.risk_review_model import RiskReviewModel
from src.infrastructure.database.models.risk_subject_model import RiskSubjectModel
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
        self._counter = 3000

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
        headers={**headers, "Idempotency-Key": "commissionability-checkout"},
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
async def test_order_explainability_persists_commissionability_preconditions_without_payout_logic(
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
                support_admin = AdminUserModel(
                    login="support_explainability",
                    email="support-explainability@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("SupportAdminP@ssword123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add(support_admin)
                db.commit()
                support_token = _make_admin_token(auth_service, user_id=support_admin.id, realm=admin_realm)

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            customer_headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }
            support_headers = {
                "Authorization": f"Bearer {support_token}",
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

            attempt_response = await async_client.post(
                "/api/v1/payment-attempts/",
                headers={**customer_headers, "Idempotency-Key": "commissionability-attempt-1"},
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
                order.partner_code_id = uuid.uuid4()
                db.commit()

            explainability_response = await async_client.get(
                f"/api/v1/orders/{order_payload['id']}/explainability",
                headers=support_headers,
            )
            assert explainability_response.status_code == 200
            explainability_payload = explainability_response.json()
            evaluation = explainability_payload["commissionability_evaluation"]
            assert evaluation["commissionability_status"] == "eligible"
            assert evaluation["reason_codes"] == []
            assert evaluation["partner_context_present"] is True
            assert evaluation["program_allows_commissionability"] is True
            assert evaluation["positive_commission_base"] is True
            assert evaluation["paid_status"] is True
            assert evaluation["fully_refunded"] is False
            assert evaluation["open_payment_dispute_present"] is False
            assert evaluation["risk_allowed"] is True
            assert (
                explainability_payload["explainability"]["future_phase_placeholders"]["payout_owner_computed"]
                is False
            )

            evaluation_id = evaluation["id"]

            with sessionmaker() as db:
                risk_subject = RiskSubjectModel(
                    principal_class="customer",
                    principal_subject=seeded["customer_user_id"],
                    auth_realm_id=uuid.UUID(seeded["customer_realm_id"]),
                    storefront_id=uuid.UUID(seeded["storefront_id"]),
                    status="active",
                    risk_level="medium",
                    metadata_payload={},
                )
                db.add(risk_subject)
                db.flush()
                review = RiskReviewModel(
                    risk_subject_id=risk_subject.id,
                    review_type="partner_payout",
                    status="open",
                    decision="hold",
                    reason="needs manual review",
                    evidence={"source": "test"},
                    created_by_admin_user_id=support_admin.id,
                )
                db.add(review)
                db.commit()

            dispute_response = await async_client.post(
                "/api/v1/payment-disputes/",
                headers=support_headers,
                json={
                    "order_id": order_payload["id"],
                    "payment_attempt_id": attempt_payload["id"],
                    "provider": "cryptobot",
                    "external_reference": "commissionability-dispute-1",
                    "subtype": "chargeback",
                    "outcome_class": "open",
                    "lifecycle_status": "under_review",
                    "disputed_amount": float(order_payload["displayed_price"]),
                    "fee_amount": 15,
                    "fee_status": "assessed",
                    "reason_code": "chargeback_received",
                    "provider_snapshot": {"provider_state": "open"},
                },
            )
            assert dispute_response.status_code == 201

            updated_explainability_response = await async_client.get(
                f"/api/v1/orders/{order_payload['id']}/explainability",
                headers=support_headers,
            )
            assert updated_explainability_response.status_code == 200
            updated_payload = updated_explainability_response.json()
            updated_evaluation = updated_payload["commissionability_evaluation"]
            assert updated_evaluation["id"] == evaluation_id
            assert updated_evaluation["commissionability_status"] == "ineligible"
            assert sorted(updated_evaluation["reason_codes"]) == ["open_payment_dispute", "risk_review_hold"]
            assert updated_evaluation["open_payment_dispute_present"] is True
            assert updated_evaluation["risk_allowed"] is False
            assert len(updated_payload["explainability"]["linked_payment_disputes"]) == 1
            assert updated_payload["explainability"]["commissionability_reasons"] == [
                "open_payment_dispute",
                "risk_review_hold",
            ]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        app.dependency_overrides.pop(get_crypto_client, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
