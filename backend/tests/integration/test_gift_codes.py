from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.application.services.auth_service import AuthService
from src.application.use_cases.gifts import IssueGiftCodeUseCase
from src.application.use_cases.payments.post_payment import PostPaymentProcessingUseCase
from src.domain.enums import PaymentAttemptStatus
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.growth_code_model import GrowthCodeModel
from src.infrastructure.database.models.invite_code_model import InviteCodeModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import PartnerCodeModel, PartnerEarningModel
from src.infrastructure.database.models.payment_attempt_model import PaymentAttemptModel
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.models.referral_commission_model import ReferralCommissionModel
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
from tests.integration.test_quote_checkout_sessions import _seed_quote_context

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_codes_resolve_returns_wrong_context_for_gift_in_checkout(async_client: AsyncClient) -> None:
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
                issued = await IssueGiftCodeUseCase(SyncSessionAdapter(db)).execute(
                    owner_user_id=uuid.UUID(seeded["customer_user_id"]),
                    plan_id=uuid.UUID(seeded["plan_id"]),
                    issuer_type="admin",
                    issuance_type="admin_manual_gift",
                    auth_realm_id=customer_realm.id,
                    reason_code="admin_manual_gift",
                )
                db.commit()

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            response = await async_client.post(
                "/api/v1/codes/resolve",
                headers={
                    "Authorization": f"Bearer {customer_token}",
                    "X-Auth-Realm": "customer",
                },
                json={
                    "code": issued.raw_code,
                    "action_context": "checkout",
                    "channel": "web",
                },
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["accepted"] is False
            assert payload["code_type"] == "gift"
            assert payload["reject_reason"] == "code_wrong_context"
            assert payload["wrong_context_target"] == "redeem"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_redeem_gift_creates_entitlement_grant(async_client: AsyncClient) -> None:
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
            redeemer_id = uuid.uuid4()

            with sessionmaker() as db:
                redeemer = MobileUserModel(
                    id=redeemer_id,
                    auth_realm_id=customer_realm.id,
                    email="gift-redeemer@example.test",
                    password_hash=await auth_service.hash_password("GiftRedeemer123!"),
                    is_active=True,
                    status="active",
                )
                db.add(redeemer)
                db.commit()

                issued = await IssueGiftCodeUseCase(SyncSessionAdapter(db)).execute(
                    owner_user_id=uuid.UUID(seeded["customer_user_id"]),
                    plan_id=uuid.UUID(seeded["plan_id"]),
                    issuer_type="purchase",
                    issuance_type="gift_purchase",
                    auth_realm_id=customer_realm.id,
                    reason_code="gift_purchase",
                )
                db.commit()

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=str(redeemer_id),
                customer_realm=customer_realm,
            )
            response = await async_client.post(
                "/api/v1/gifts/redeem",
                headers={
                    "Authorization": f"Bearer {customer_token}",
                    "X-Auth-Realm": "customer",
                },
                json={"code": issued.raw_code},
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["gift_code"]["status"] == "redeemed"
            assert payload["gift_code"]["redeemed_by_user_id"] == str(redeemer_id)
            assert payload["entitlement_snapshot"]["status"] == "active"

            with sessionmaker() as db:
                growth_code = db.execute(
                    select(GrowthCodeModel).where(GrowthCodeModel.id == issued.growth_code.id)
                ).scalar_one()
                assert growth_code.status == "redeemed"
                assert growth_code.uses_count == 1
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_issue_gift_batch_assigns_shared_batch_id() -> None:
    auth_service = AuthService()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_quote_context(sessionmaker, auth_service)

            with sessionmaker() as db:
                issued_batch = await IssueGiftCodeUseCase(SyncSessionAdapter(db)).execute_batch(
                    owner_user_id=uuid.UUID(seeded["customer_user_id"]),
                    plan_id=uuid.UUID(seeded["plan_id"]),
                    count=3,
                    issuer_type="admin",
                    issuance_type="admin_gift_batch",
                    auth_realm_id=uuid.UUID(seeded["customer_realm_id"]),
                    reason_code="admin_gift_batch",
                )
                db.commit()

                assert len(issued_batch.items) == 3
                assert len({item.growth_code.id for item in issued_batch.items}) == 3
                assert {item.growth_code.batch_id for item in issued_batch.items} == {issued_batch.batch_id}

                persisted_codes = db.execute(
                    select(GrowthCodeModel).where(GrowthCodeModel.batch_id == issued_batch.batch_id)
                ).scalars().all()
                assert len(persisted_codes) == 3
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_post_payment_gift_purchase_issues_gift_without_legacy_payout_side_effects(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

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
            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            customer_headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }

            with sessionmaker() as db:
                partner_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="gift-partner-owner@example.test",
                    password_hash=await auth_service.hash_password("GiftPartnerOwner123!"),
                    is_active=True,
                    status="active",
                    is_partner=True,
                )
                referrer = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="gift-referrer@example.test",
                    password_hash=await auth_service.hash_password("GiftReferrer123!"),
                    is_active=True,
                    status="active",
                )
                affiliate_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="GIFTPARTNER42",
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

            _, checkout_payload = await _create_quote_checkout(
                async_client=async_client,
                headers=customer_headers,
                storefront_key=seeded["storefront_key"],
                pricebook_key=seeded["pricebook_key"],
                offer_key=seeded["offer_key"],
                plan_id=seeded["plan_id"],
                idempotency_key="gift-checkout-flow",
            )
            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=customer_headers,
                json={"checkout_session_id": checkout_payload["id"]},
            )
            assert order_response.status_code == 201
            order_id = order_response.json()["id"]

            with sessionmaker() as db:
                payment = PaymentModel(
                    id=uuid.uuid4(),
                    user_uuid=uuid.UUID(seeded["customer_user_id"]),
                    amount=Decimal("90"),
                    currency="USD",
                    status="completed",
                    provider="cryptobot",
                    subscription_days=365,
                    plan_id=uuid.UUID(seeded["plan_id"]),
                    partner_code_id=affiliate_code.id,
                    metadata_={
                        "commission_base_amount": "90",
                        "checkout_mode": "gift_purchase",
                        "gift_recipient_hint": "friend@example.test",
                        "gift_message": "Enjoy CyberVPN",
                        "gift_storefront_id": seeded["storefront_id"],
                        "gift_auth_realm_id": seeded["customer_realm_id"],
                    },
                )
                attempt = PaymentAttemptModel(
                    id=uuid.uuid4(),
                    order_id=uuid.UUID(order_id),
                    payment_id=payment.id,
                    attempt_number=1,
                    provider="cryptobot",
                    sale_channel="web",
                    currency_code="USD",
                    status=PaymentAttemptStatus.SUCCEEDED.value,
                    displayed_amount=Decimal("90"),
                    wallet_amount=Decimal("0"),
                    gateway_amount=Decimal("90"),
                    idempotency_key="gift-purchase-payment-attempt",
                    provider_snapshot={},
                    request_snapshot={},
                )
                db.add_all([payment, attempt])
                db.commit()

                results = await PostPaymentProcessingUseCase(SyncSessionAdapter(db)).execute(payment.id)
                db.commit()

                assert results["gift_code_issued"] is True
                assert results["invites_generated"] == 0
                assert results["referral_commission"] is None
                assert results["partner_earning"] is None

                gift_codes = db.execute(
                    select(GrowthCodeModel).where(
                        GrowthCodeModel.code_type == "gift",
                        GrowthCodeModel.owner_user_id == uuid.UUID(seeded["customer_user_id"]),
                    )
                ).scalars().all()
                assert len(gift_codes) == 1
                assert db.execute(
                    select(InviteCodeModel).where(InviteCodeModel.source_payment_id == payment.id)
                ).scalars().all() == []
                assert db.execute(select(ReferralCommissionModel)).scalars().all() == []
                assert db.execute(select(PartnerEarningModel)).scalars().all() == []
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
