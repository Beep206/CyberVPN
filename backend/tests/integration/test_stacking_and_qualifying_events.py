from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.application.use_cases.payments.post_payment import PostPaymentProcessingUseCase
from src.domain.enums import PaymentAttemptStatus
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import PartnerCodeModel
from src.infrastructure.database.models.payment_attempt_model import PaymentAttemptModel
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.models.promo_code_model import PromoCodeModel
from src.infrastructure.database.models.wallet_model import WalletModel
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
from tests.integration.test_order_attribution_resolution import _create_quote_checkout
from tests.integration.test_order_commit import _make_customer_access_token, _seed_order_context

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
async def test_quote_rejects_promo_and_partner_code_stacking(
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
                partner_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="stacking-owner@example.test",
                    password_hash=await auth_service.hash_password("StackingOwner123!"),
                    is_active=True,
                    status="active",
                    is_partner=True,
                )
                partner_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="STACK42",
                    partner_user_id=partner_owner.id,
                    markup_pct=15,
                    is_active=True,
                )
                promo_code = PromoCodeModel(
                    id=uuid.uuid4(),
                    code="PROMO15",
                    discount_type="percent",
                    discount_value=15,
                    is_active=True,
                )
                db.add_all([partner_owner, partner_code, promo_code])
                db.commit()

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }

            response = await async_client.post(
                "/api/v1/quotes/",
                headers=headers,
                json={
                    "storefront_key": seeded["storefront_key"],
                    "pricebook_key": seeded["pricebook_key"],
                    "offer_key": seeded["offer_key"],
                    "plan_id": seeded["plan_id"],
                    "currency": "USD",
                    "channel": "web",
                    "promo_code": promo_code.code,
                    "partner_code": partner_code.code,
                    "use_wallet": 0,
                    "addons": [],
                },
            )

            assert response.status_code == 400
            assert response.json()["detail"] == "Promo codes cannot be combined with partner codes"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_policy_evaluation_marks_wallet_funded_first_order_as_qualifying(
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

                support_user = AdminUserModel(
                    login="policy_eval_support",
                    email="policy-eval-support@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("PolicyEvalSupport123!"),
                    role="support",
                    is_active=True,
                    is_email_verified=True,
                )
                wallet = WalletModel(
                    id=uuid.uuid4(),
                    user_id=uuid.UUID(seeded["customer_user_id"]),
                    balance=Decimal("100.00"),
                    frozen=Decimal("0"),
                )
                db.add_all([support_user, wallet])
                db.commit()
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
            support_headers = {
                "Authorization": f"Bearer {support_token}",
                "X-Auth-Realm": "admin",
            }

            quote_response = await async_client.post(
                "/api/v1/quotes/",
                headers=customer_headers,
                json={
                    "storefront_key": seeded["storefront_key"],
                    "pricebook_key": seeded["pricebook_key"],
                    "offer_key": seeded["offer_key"],
                    "plan_id": seeded["plan_id"],
                    "currency": "USD",
                    "channel": "web",
                    "use_wallet": 90,
                    "addons": [],
                },
            )
            assert quote_response.status_code == 201
            quote_payload = quote_response.json()

            checkout_response = await async_client.post(
                "/api/v1/checkout-sessions/",
                headers={**customer_headers, "Idempotency-Key": "wallet-heavy-eval"},
                json={"quote_session_id": quote_payload["id"]},
            )
            assert checkout_response.status_code == 201
            checkout_payload = checkout_response.json()

            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=customer_headers,
                json={"checkout_session_id": checkout_payload["id"]},
            )
            assert order_response.status_code == 201
            order_id = order_response.json()["id"]

            evaluation_response = await async_client.get(
                f"/api/v1/policy-evaluation/orders/{order_id}",
                headers=support_headers,
            )
            assert evaluation_response.status_code == 200
            payload = evaluation_response.json()
            assert payload["stacking"]["stacking_valid"] is True
            assert payload["qualifying_event"]["qualifying_first_payment"] is True
            assert payload["qualifying_event"]["first_paid_order"] is True
            assert payload["qualifying_event"]["order_is_paid"] is True
            assert payload["qualifying_event"]["positive_paid_economic_amount"] is True
            assert payload["payout_rules"]["referral_cash_payout_allowed"] is True
            assert payload["payout_rules"]["partner_cash_payout_allowed"] is False
            assert payload["payout_rules"]["no_double_payout"] is True
    finally:
        app.dependency_overrides.pop(get_redis, None)
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_post_payment_blocks_referral_when_affiliate_owner_exists(
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
                partner_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="double-payout-owner@example.test",
                    password_hash=await auth_service.hash_password("DoublePayoutOwner123!"),
                    is_active=True,
                    status="active",
                    is_partner=True,
                )
                referrer = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="double-payout-referrer@example.test",
                    password_hash=await auth_service.hash_password("DoublePayoutReferrer123!"),
                    is_active=True,
                    status="active",
                )
                affiliate_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="AFFNOREF",
                    partner_user_id=partner_owner.id,
                    markup_pct=12,
                    is_active=True,
                )
                db.add_all([partner_owner, referrer, affiliate_code])
                db.commit()

                customer = db.get(MobileUserModel, uuid.UUID(seeded["customer_user_id"]))
                assert customer is not None
                customer.referred_by_user_id = referrer.id
                customer.partner_user_id = partner_owner.id
                db.commit()

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            customer_headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }

            _, checkout_payload = await _create_quote_checkout(
                async_client=async_client,
                headers=customer_headers,
                storefront_key=seeded["storefront_key"],
                pricebook_key=seeded["pricebook_key"],
                offer_key=seeded["offer_key"],
                plan_id=seeded["plan_id"],
                partner_code=affiliate_code.code,
                idempotency_key="policy-double-payout",
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
                    partner_code_id=affiliate_code.id,
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
                    status=PaymentAttemptStatus.SUCCEEDED.value,
                    displayed_amount=Decimal(str(order_payload["displayed_price"])),
                    wallet_amount=Decimal("0"),
                    gateway_amount=Decimal(str(order_payload["gateway_amount"])),
                    idempotency_key="policy-double-payout-attempt",
                    provider_snapshot={},
                    request_snapshot={},
                )
                db.add_all([payment, attempt])
                db.commit()

                post_payment = PostPaymentProcessingUseCase(adapter)
                results = await post_payment.execute(payment.id)
                db.commit()

                assert results["referral_commission"] is None
                assert "commercial_owner_already_resolved" in results["referral_policy_block_reasons"]
                assert results["partner_earning"] is not None
    finally:
        app.dependency_overrides.pop(get_redis, None)
        cleanup_sqlite_file(sqlite_path)
