from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.application.use_cases.payments.post_payment import PostPaymentProcessingUseCase
from src.application.use_cases.renewal_orders import ResolveRenewalOrderUseCase
from src.domain.enums import CommercialOwnerType, CustomerCommercialBindingType, PaymentAttemptStatus
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.customer_commercial_binding_model import (
    CustomerCommercialBindingModel,
)
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeModel
from src.infrastructure.database.models.payment_attempt_model import PaymentAttemptModel
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.infrastructure.database.repositories.partner_repo import PartnerRepository
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


def _build_customer_realm(seeded: dict[str, str]) -> AuthRealmModel:
    return AuthRealmModel(
        id=uuid.UUID(seeded["customer_realm_id"]),
        realm_key=seeded["customer_realm_key"],
        realm_type="customer",
        display_name="Customer Realm",
        audience=seeded["customer_realm_audience"],
        cookie_namespace="customer",
        status="active",
        is_default=True,
    )


async def _seed_admin_and_support_tokens(
    sessionmaker,
    auth_service: AuthService,
) -> tuple[str, str]:
    with sessionmaker() as db:
        realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
        admin_realm = await realm_repo.get_or_create_default_realm("admin")

        admin_user = AdminUserModel(
            login="renewal_admin",
            email="renewal-admin@example.com",
            auth_realm_id=admin_realm.id,
            password_hash=await auth_service.hash_password("RenewalAdmin123!"),
            role="admin",
            is_active=True,
            is_email_verified=True,
        )
        support_user = AdminUserModel(
            login="renewal_support",
            email="renewal-support@example.com",
            auth_realm_id=admin_realm.id,
            password_hash=await auth_service.hash_password("RenewalSupport123!"),
            role="support",
            is_active=True,
            is_email_verified=True,
        )
        db.add_all([admin_user, support_user])
        db.commit()
        admin_token = _make_admin_token(auth_service, user_id=admin_user.id, realm=admin_realm)
        support_token = _make_admin_token(auth_service, user_id=support_user.id, realm=admin_realm)
        return admin_token, support_token


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
async def test_renewal_order_inherits_affiliate_provenance_from_initial_acquisition(
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
            customer_realm = _build_customer_realm(seeded)
            admin_token, support_token = await _seed_admin_and_support_tokens(sessionmaker, auth_service)

            with sessionmaker() as db:
                affiliate_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="renewal-affiliate-owner@example.test",
                    password_hash=await auth_service.hash_password("RenewalAffiliateOwner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                affiliate_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="REN-AFF-01",
                    partner_user_id=affiliate_owner.id,
                    markup_pct=15,
                    is_active=True,
                )
                db.add_all([affiliate_owner, affiliate_code])
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
            admin_headers = {
                "Authorization": f"Bearer {admin_token}",
                "X-Auth-Realm": "admin",
            }
            support_headers = {
                "Authorization": f"Bearer {support_token}",
                "X-Auth-Realm": "admin",
            }

            initial_order = await _commit_order(
                async_client=async_client,
                headers=customer_headers,
                seeded=seeded,
                partner_code=affiliate_code.code,
                idempotency_key="renewal-initial-order",
            )
            renewal_candidate = await _commit_order(
                async_client=async_client,
                headers=customer_headers,
                seeded=seeded,
                idempotency_key="renewal-second-order",
            )

            resolve_response = await async_client.post(
                "/api/v1/renewal-orders/resolve",
                headers=admin_headers,
                json={
                    "order_id": renewal_candidate["id"],
                    "prior_order_id": initial_order["id"],
                    "renewal_mode": "manual",
                },
            )
            assert resolve_response.status_code == 201
            payload = resolve_response.json()

            assert payload["initial_order_id"] == initial_order["id"]
            assert payload["prior_order_id"] == initial_order["id"]
            assert payload["renewal_sequence_number"] == 1
            assert payload["provenance_owner_type"] == CommercialOwnerType.AFFILIATE.value
            assert payload["effective_owner_type"] == CommercialOwnerType.AFFILIATE.value
            assert payload["payout_eligible"] is True

            by_id_response = await async_client.get(
                f"/api/v1/renewal-orders/{payload['id']}",
                headers=support_headers,
            )
            assert by_id_response.status_code == 200
            assert by_id_response.json()["id"] == payload["id"]

            by_order_response = await async_client.get(
                f"/api/v1/renewal-orders/by-order/{renewal_candidate['id']}",
                headers=support_headers,
            )
            assert by_order_response.status_code == 200
            assert by_order_response.json()["order_id"] == renewal_candidate["id"]

            explainability_response = await async_client.get(
                f"/api/v1/orders/{renewal_candidate['id']}/explainability",
                headers=support_headers,
            )
            assert explainability_response.status_code == 200
            explainability_payload = explainability_response.json()
            assert explainability_payload["explainability"]["renewal_order"]["effective_owner_type"] == "affiliate"
            assert explainability_payload["commissionability_evaluation"]["partner_context_present"] is True
            assert (
                "missing_partner_context"
                not in explainability_payload["commissionability_evaluation"]["reason_codes"]
            )
    finally:
        app.dependency_overrides.pop(get_redis, None)
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_renewal_order_reseller_binding_overrides_inherited_affiliate_owner(
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
            customer_realm = _build_customer_realm(seeded)
            admin_token, support_token = await _seed_admin_and_support_tokens(sessionmaker, auth_service)

            with sessionmaker() as db:
                affiliate_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="renewal-affiliate-owner-override@example.test",
                    password_hash=await auth_service.hash_password("RenewalAffiliateOverride123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                affiliate_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="REN-AFF-02",
                    partner_user_id=affiliate_owner.id,
                    markup_pct=10,
                    is_active=True,
                )
                reseller_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="renewal-reseller-owner@example.test",
                    password_hash=await auth_service.hash_password("RenewalResellerOwner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                reseller_account = PartnerAccountModel(
                    id=uuid.uuid4(),
                    account_key="renewal-reseller-account",
                    display_name="Renewal Reseller",
                    status="active",
                    legacy_owner_user_id=reseller_owner.id,
                )
                reseller_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="REN-RES-01",
                    partner_account_id=reseller_account.id,
                    partner_user_id=reseller_owner.id,
                    markup_pct=8,
                    is_active=True,
                )
                reseller_binding = CustomerCommercialBindingModel(
                    id=uuid.uuid4(),
                    user_id=uuid.UUID(seeded["customer_user_id"]),
                    auth_realm_id=customer_realm.id,
                    storefront_id=uuid.UUID(seeded["storefront_id"]),
                    binding_type=CustomerCommercialBindingType.RESELLER_BINDING.value,
                    binding_status="active",
                    owner_type=CommercialOwnerType.RESELLER.value,
                    partner_account_id=reseller_account.id,
                    partner_code_id=reseller_code.id,
                    reason_code="test_reseller_override",
                    evidence_payload={"source": "test"},
                )
                db.add_all(
                    [
                        affiliate_owner,
                        affiliate_code,
                        reseller_owner,
                        reseller_account,
                        reseller_code,
                        reseller_binding,
                    ]
                )
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
            admin_headers = {
                "Authorization": f"Bearer {admin_token}",
                "X-Auth-Realm": "admin",
            }
            support_headers = {
                "Authorization": f"Bearer {support_token}",
                "X-Auth-Realm": "admin",
            }

            initial_order = await _commit_order(
                async_client=async_client,
                headers=customer_headers,
                seeded=seeded,
                partner_code=affiliate_code.code,
                idempotency_key="renewal-override-initial",
            )
            renewal_candidate = await _commit_order(
                async_client=async_client,
                headers=customer_headers,
                seeded=seeded,
                idempotency_key="renewal-override-second",
            )

            resolve_response = await async_client.post(
                "/api/v1/renewal-orders/resolve",
                headers=admin_headers,
                json={
                    "order_id": renewal_candidate["id"],
                    "prior_order_id": initial_order["id"],
                    "renewal_mode": "manual",
                },
            )
            assert resolve_response.status_code == 201
            payload = resolve_response.json()

            assert payload["provenance_owner_type"] == CommercialOwnerType.AFFILIATE.value
            assert payload["effective_owner_type"] == CommercialOwnerType.RESELLER.value
            assert payload["effective_owner_source"] == "persistent_reseller_binding"
            assert payload["winning_binding_id"] is not None
            assert payload["payout_eligible"] is True

            explainability_response = await async_client.get(
                f"/api/v1/orders/{renewal_candidate['id']}/explainability",
                headers=support_headers,
            )
            assert explainability_response.status_code == 200
            explainability_payload = explainability_response.json()
            renewal_info = explainability_payload["explainability"]["renewal_order"]
            assert renewal_info["provenance_owner_type"] == "affiliate"
            assert renewal_info["effective_owner_type"] == "reseller"
            assert renewal_info["payout_eligible"] is True
            assert explainability_payload["explainability"]["lane_views"]["reseller_distribution"]["active"] is True
            assert explainability_payload["explainability"]["lane_views"]["renewal_chain"]["active"] is True
    finally:
        app.dependency_overrides.pop(get_redis, None)
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_post_payment_uses_renewal_order_effective_owner_as_partner_fallback(
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
            customer_realm = _build_customer_realm(seeded)

            with sessionmaker() as db:
                partner_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="renewal-post-payment-owner@example.test",
                    password_hash=await auth_service.hash_password("RenewalPostPaymentOwner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                referrer = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="renewal-post-payment-referrer@example.test",
                    password_hash=await auth_service.hash_password("RenewalPostPaymentReferrer123!"),
                    is_active=True,
                    status="active",
                )
                affiliate_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="REN-POST-01",
                    partner_user_id=partner_owner.id,
                    markup_pct=11,
                    is_active=True,
                )
                db.add_all([partner_owner, referrer, affiliate_code])
                db.commit()

                customer = db.get(MobileUserModel, uuid.UUID(seeded["customer_user_id"]))
                assert customer is not None
                customer.referred_by_user_id = referrer.id
                db.commit()

                partner_owner_id = partner_owner.id
                affiliate_code_id = affiliate_code.id

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            customer_headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }

            initial_order = await _commit_order(
                async_client=async_client,
                headers=customer_headers,
                seeded=seeded,
                partner_code="REN-POST-01",
                idempotency_key="renewal-post-payment-initial",
            )
            renewal_candidate = await _commit_order(
                async_client=async_client,
                headers=customer_headers,
                seeded=seeded,
                idempotency_key="renewal-post-payment-second",
            )

            with sessionmaker() as db:
                adapter = SyncSessionAdapter(db)
                resolve_use_case = ResolveRenewalOrderUseCase(adapter)
                renewal_order = await resolve_use_case.execute(
                    order_id=uuid.UUID(renewal_candidate["id"]),
                    prior_order_id=uuid.UUID(initial_order["id"]),
                    renewal_mode="manual",
                )

                payment = PaymentModel(
                    id=uuid.uuid4(),
                    user_uuid=uuid.UUID(seeded["customer_user_id"]),
                    amount=Decimal(str(renewal_candidate["displayed_price"])),
                    currency="USD",
                    status="completed",
                    provider="cryptobot",
                    subscription_days=365,
                    plan_id=uuid.UUID(seeded["plan_id"]),
                    partner_code_id=None,
                    metadata_={"commission_base_amount": str(renewal_candidate["commission_base_amount"])},
                )
                attempt = PaymentAttemptModel(
                    id=uuid.uuid4(),
                    order_id=uuid.UUID(renewal_candidate["id"]),
                    payment_id=payment.id,
                    attempt_number=1,
                    provider="cryptobot",
                    sale_channel="web",
                    currency_code="USD",
                    status=PaymentAttemptStatus.SUCCEEDED.value,
                    displayed_amount=Decimal(str(renewal_candidate["displayed_price"])),
                    wallet_amount=Decimal("0"),
                    gateway_amount=Decimal(str(renewal_candidate["gateway_amount"])),
                    idempotency_key="renewal-post-payment-attempt",
                    provider_snapshot={},
                    request_snapshot={},
                )
                db.add_all([payment, attempt])
                db.commit()

                post_payment = PostPaymentProcessingUseCase(adapter)
                results = await post_payment.execute(payment.id)
                partner_repo = PartnerRepository(adapter)
                earnings = await partner_repo.get_earnings_by_partner(partner_owner_id)
                db.commit()

                assert renewal_order.effective_partner_code_id == affiliate_code_id
                assert results["policy_evaluation"]["partner_cash_payout_allowed"] is True
                assert results["partner_earning"] is not None
                assert results["referral_commission"] is None
                assert "commercial_owner_already_resolved" in results["referral_policy_block_reasons"]
                assert len(earnings) == 1
                assert earnings[0].partner_code_id == affiliate_code_id
    finally:
        app.dependency_overrides.pop(get_redis, None)
        cleanup_sqlite_file(sqlite_path)
