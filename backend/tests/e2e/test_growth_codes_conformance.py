from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.application.use_cases.growth_codes.registry import GrowthCodeRegistryService
from src.application.use_cases.invites.generate_invites import GenerateInvitesForPaymentUseCase
from src.application.use_cases.payments.post_payment import PostPaymentProcessingUseCase
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.customer_commercial_binding_model import (
    CustomerCommercialBindingModel,
)
from src.infrastructure.database.models.growth_code_model import (
    GrowthCodeTouchpointModel,
    GrowthSignupAttributionModel,
)
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.offer_model import OfferModel
from src.infrastructure.database.models.partner_model import PartnerEarningModel
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.models.promo_code_model import PromoCodeModel
from src.infrastructure.database.models.referral_commission_model import ReferralCommissionModel
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.infrastructure.database.repositories.growth_code_repo import GrowthCodeRepository
from src.infrastructure.database.repositories.invite_code_repo import InviteCodeRepository
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository
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
from tests.integration.test_order_commit import _make_customer_access_token
from tests.integration.test_quote_checkout_sessions import _seed_quote_context

pytestmark = [pytest.mark.e2e, pytest.mark.integration]


class FakeCryptoBotClient:
    def __init__(self) -> None:
        self._counter = 6000

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


def _make_admin_access_token(auth_service: AuthService, *, user_id, admin_realm: AuthRealmModel) -> str:
    token, _, _ = auth_service.create_access_token(
        str(user_id),
        "admin",
        audience=admin_realm.audience,
        principal_type="admin",
        realm_id=str(admin_realm.id),
        realm_key=admin_realm.realm_key,
        scope_family="admin",
    )
    return token


@pytest.mark.asyncio
async def test_growth_codes_invite_conformance_bundle_redeem_and_lookup(
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
            owner_id = uuid.UUID(seeded["customer_user_id"])
            redeemer_id = uuid.uuid4()

            with sessionmaker() as db:
                session = SyncSessionAdapter(db)
                realm_repo = AuthRealmRepository(session)
                admin_realm = await realm_repo.get_or_create_default_realm("admin")
                admin_user = AdminUserModel(
                    login="growth_codes_conformance_admin",
                    email="growth-codes-conformance-admin@example.test",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("GrowthCodesConformanceAdmin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                plan = db.get(SubscriptionPlanModel, uuid.UUID(seeded["plan_id"]))
                assert plan is not None
                plan.plan_code = "max"
                plan.display_name = "Max 365"
                plan.invite_bundle = {"count": 3, "friend_days": 14, "expiry_days": 60}
                payment = PaymentModel(
                    id=uuid.uuid4(),
                    user_uuid=owner_id,
                    amount=Decimal("99.00"),
                    currency="USD",
                    status="completed",
                    provider="cryptobot",
                    subscription_days=365,
                    plan_id=plan.id,
                    metadata_={},
                )
                redeemer = MobileUserModel(
                    id=redeemer_id,
                    auth_realm_id=customer_realm.id,
                    email="invite-redeemer@example.test",
                    password_hash=await auth_service.hash_password("InviteRedeemer123!"),
                    is_active=True,
                    status="active",
                )
                db.add_all([admin_user, payment, redeemer])
                db.commit()

                invites = await GenerateInvitesForPaymentUseCase(
                    invite_repo=InviteCodeRepository(session),
                    plan_repo=SubscriptionPlanRepository(session),
                ).execute(
                    owner_user_id=owner_id,
                    plan_id=plan.id,
                    payment_id=payment.id,
                )
                assert len(invites) == 3
                assert {invite.free_days for invite in invites} == {14}

                registry = GrowthCodeRegistryService(session)
                growth_repo = GrowthCodeRepository(session)
                first_shadow = await registry.ensure_shadow_invite(invites[0])
                touchpoint = await growth_repo.create_touchpoint(
                    GrowthCodeTouchpointModel(
                        growth_code_id=first_shadow.id,
                        code_type="invite",
                        anonymous_session_id="invite-conformance-session-1",
                        registered_user_id=redeemer_id,
                        storefront_id=uuid.UUID(seeded["storefront_id"]),
                        auth_realm_id=customer_realm.id,
                        surface="invite_link",
                        channel="web",
                        utm_source="invite",
                        utm_campaign="gc-wb-09",
                        created_at=datetime.now(UTC),
                        converted_to_signup_at=datetime.now(UTC),
                    )
                )
                await growth_repo.create_signup_attribution(
                    GrowthSignupAttributionModel(
                        user_id=redeemer_id,
                        growth_code_id=first_shadow.id,
                        code_type="invite",
                        touchpoint_id=touchpoint.id,
                        attribution_source="invite_link",
                        storefront_id=uuid.UUID(seeded["storefront_id"]),
                        auth_realm_id=customer_realm.id,
                    )
                )
                db.commit()

                admin_token = _make_admin_access_token(
                    auth_service,
                    user_id=admin_user.id,
                    admin_realm=admin_realm,
                )

            owner_token = _make_customer_access_token(
                auth_service,
                user_id=owner_id,
                customer_realm=customer_realm,
            )
            redeemer_token = _make_customer_access_token(
                auth_service,
                user_id=redeemer_id,
                customer_realm=customer_realm,
            )
            owner_headers = {
                "Authorization": f"Bearer {owner_token}",
                "X-Auth-Realm": "customer",
            }
            redeemer_headers = {
                "Authorization": f"Bearer {redeemer_token}",
                "X-Auth-Realm": "customer",
            }
            admin_headers = {
                "Authorization": f"Bearer {admin_token}",
                "X-Auth-Realm": "admin",
            }

            self_redeem_response = await async_client.post(
                "/api/v1/invites/redeem",
                headers=owner_headers,
                json={"code": invites[1].code},
            )
            assert self_redeem_response.status_code == 400
            assert "owner" in self_redeem_response.json()["detail"].lower()

            redeem_response = await async_client.post(
                "/api/v1/invites/redeem",
                headers=redeemer_headers,
                json={"code": invites[0].code},
            )
            assert redeem_response.status_code == 200
            redeem_payload = redeem_response.json()
            assert redeem_payload["entitlement_grant_id"] is not None
            assert redeem_payload["entitlement_snapshot"]["status"] == "active"
            assert redeem_payload["entitlement_snapshot"]["plan_code"] == "invite"
            assert redeem_payload["entitlement_snapshot"]["period_days"] == 14
            assert redeem_payload["entitlement_snapshot"]["effective_entitlements"]["device_limit"] == 1

            entitlement_response = await async_client.get(
                "/api/v1/entitlements/current",
                headers=redeemer_headers,
            )
            assert entitlement_response.status_code == 200
            entitlement_payload = entitlement_response.json()
            assert entitlement_payload["status"] == "active"
            assert entitlement_payload["plan_code"] == "invite"
            assert entitlement_payload["period_days"] == 14
            assert entitlement_payload["effective_entitlements"]["device_limit"] == 1

            lookup_response = await async_client.post(
                "/api/v1/admin/growth-codes/lookup",
                headers=admin_headers,
                json={
                    "code": invites[0].code,
                    "action_context": "redeem",
                    "lookup_user_id": str(redeemer_id),
                    "channel": "web",
                },
            )
            assert lookup_response.status_code == 200
            lookup_payload = lookup_response.json()
            assert lookup_payload["code_type"] == "invite"
            assert lookup_payload["growth_code_id"] is not None
            assert lookup_payload["lifecycle_summary"]["issuance_count"] == 1
            assert lookup_payload["lifecycle_summary"]["touchpoint_count"] == 1
            assert lookup_payload["lifecycle_summary"]["signup_attribution_count"] == 1
            assert lookup_payload["lifecycle_summary"]["redemption_count"] == 1
            assert lookup_payload["redemptions"][0]["redeemer_user_id"] == str(redeemer_id)
            assert lookup_payload["redemptions"][0]["entitlement_grant_id"] == redeem_payload["entitlement_grant_id"]
            assert lookup_payload["touchpoints"][0]["channel"] == "web"
            assert lookup_payload["signup_attributions"][0]["user_id"] == str(redeemer_id)
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_growth_codes_promo_conformance_accepts_rejects_and_conflicts_with_partner_binding(
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
            alternate_plan_id = uuid.uuid4()

            with sessionmaker() as db:
                other_plan = SubscriptionPlanModel(
                    id=alternate_plan_id,
                    name="growth_codes_alt_30d",
                    plan_code="basic",
                    display_name="Growth Codes Alt 30D",
                    catalog_visibility="hidden",
                    duration_days=30,
                    device_limit=1,
                    price_usd=19,
                    sale_channels=["web"],
                    traffic_policy={},
                    connection_modes=["standard"],
                    server_pool=["shared"],
                    support_sla="standard",
                    dedicated_ip={},
                    invite_bundle={},
                    trial_eligible=False,
                    features={},
                    is_active=True,
                    sort_order=99,
                )
                promo = PromoCodeModel(
                    id=uuid.uuid4(),
                    code="GCCONFORMANCE10",
                    discount_type="percent",
                    discount_value=10,
                    is_active=True,
                    min_amount=Decimal("50.00"),
                )
                db.add_all([other_plan, promo])
                db.commit()

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            customer_headers = {"Authorization": f"Bearer {customer_token}", "X-Auth-Realm": "customer"}

            accepted_response = await async_client.post(
                "/api/v1/codes/resolve",
                headers=customer_headers,
                json={
                    "code": "GCCONFORMANCE10",
                    "action_context": "checkout",
                    "storefront_key": seeded["storefront_key"],
                    "plan_id": seeded["plan_id"],
                    "amount": 75,
                    "channel": "web",
                },
            )
            assert accepted_response.status_code == 200
            accepted_payload = accepted_response.json()
            assert accepted_payload["accepted"] is True
            assert accepted_payload["code_type"] == "promo"
            assert accepted_payload["result"] == "accepted"

            ineligible_response = await async_client.post(
                "/api/v1/codes/resolve",
                headers=customer_headers,
                json={
                    "code": "GCCONFORMANCE10",
                    "action_context": "checkout",
                    "storefront_key": seeded["storefront_key"],
                    "plan_id": str(alternate_plan_id),
                    "amount": 19,
                    "channel": "web",
                },
            )
            assert ineligible_response.status_code == 200
            ineligible_payload = ineligible_response.json()
            assert ineligible_payload["accepted"] is False
            assert ineligible_payload["result"] == "rejected"
            assert ineligible_payload["reject_reason"] == "code_not_eligible_for_sku"

            with sessionmaker() as db:
                binding = CustomerCommercialBindingModel(
                    id=uuid.uuid4(),
                    user_id=uuid.UUID(seeded["customer_user_id"]),
                    auth_realm_id=customer_realm.id,
                    storefront_id=uuid.UUID(seeded["storefront_id"]),
                    binding_type="reseller_binding",
                    binding_status="active",
                    owner_type="reseller",
                    reason_code="gc_wb_09_partner_binding",
                    evidence_payload={"source": "gc-wb-09"},
                )
                db.add(binding)
                db.commit()

            conflicted_quote_response = await async_client.post(
                "/api/v1/quotes/",
                headers=customer_headers,
                json={
                    "storefront_key": seeded["storefront_key"],
                    "pricebook_key": seeded["pricebook_key"],
                    "offer_key": seeded["offer_key"],
                    "plan_id": seeded["plan_id"],
                    "currency": "USD",
                    "channel": "web",
                    "code_input": "GCCONFORMANCE10",
                    "use_wallet": 0,
                    "addons": [],
                },
            )
            assert conflicted_quote_response.status_code == 400
            assert conflicted_quote_response.json()["detail"] == (
                "Promo codes cannot be combined with active partner bindings"
            )
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_growth_codes_gift_conformance_purchase_and_redeem_do_not_create_partner_or_referral_payouts(
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
            recipient_id = uuid.uuid4()

            with sessionmaker() as db:
                offer = db.get(OfferModel, uuid.UUID(seeded["offer_id"]))
                assert offer is not None
                offer.gift_eligible = True
                recipient = MobileUserModel(
                    id=recipient_id,
                    auth_realm_id=customer_realm.id,
                    email="gift-conformance-recipient@example.test",
                    password_hash=await auth_service.hash_password("GiftConformanceRecipient123!"),
                    is_active=True,
                    status="active",
                )
                db.add(recipient)
                db.commit()

            purchaser_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            recipient_token = _make_customer_access_token(
                auth_service,
                user_id=recipient_id,
                customer_realm=customer_realm,
            )
            purchaser_headers = {
                "Authorization": f"Bearer {purchaser_token}",
                "X-Auth-Realm": "customer",
                "Host": "partner.example.test",
            }
            recipient_headers = {"Authorization": f"Bearer {recipient_token}", "X-Auth-Realm": "customer"}

            commit_response = await async_client.post(
                "/api/v1/gifts/purchase/commit",
                headers=purchaser_headers,
                json={
                    "storefront_key": seeded["storefront_key"],
                    "plan_id": seeded["plan_id"],
                    "use_wallet": 0,
                    "currency": "USD",
                    "channel": "web",
                    "recipient_hint": "r***@example.test",
                    "gift_message": "Enjoy CyberVPN",
                },
            )
            assert commit_response.status_code == 200
            commit_payload = commit_response.json()
            assert commit_payload["payment_id"] is not None
            assert commit_payload["status"] == "pending"
            assert commit_payload["gift_code"] is None

            with sessionmaker() as db:
                payment = db.get(PaymentModel, uuid.UUID(commit_payload["payment_id"]))
                assert payment is not None
                payment.status = "completed"
                db.commit()

                results = await PostPaymentProcessingUseCase(SyncSessionAdapter(db)).execute(payment.id)
                db.commit()
                assert results["gift_code_issued"] is True
                assert results["referral_commission"] is None
                assert results["partner_earning"] is None

            my_gifts_response = await async_client.get(
                "/api/v1/gifts/my",
                headers=purchaser_headers,
            )
            assert my_gifts_response.status_code == 200
            gift_items = my_gifts_response.json()
            assert len(gift_items) == 1
            assert gift_items[0]["raw_code"] is not None
            assert gift_items[0]["status"] == "active"

            redeem_response = await async_client.post(
                "/api/v1/gifts/redeem",
                headers=recipient_headers,
                json={"code": gift_items[0]["raw_code"]},
            )
            assert redeem_response.status_code == 200
            redeem_payload = redeem_response.json()
            assert redeem_payload["gift_code"]["status"] == "redeemed"
            assert redeem_payload["gift_code"]["redeemed_by_user_id"] == str(recipient_id)
            assert redeem_payload["entitlement_snapshot"]["status"] == "active"

            entitlement_response = await async_client.get(
                "/api/v1/entitlements/current",
                headers=recipient_headers,
            )
            assert entitlement_response.status_code == 200
            entitlement_payload = entitlement_response.json()
            assert entitlement_payload["status"] == "active"
            assert entitlement_payload["plan_code"] == "pro"

            with sessionmaker() as db:
                referral_commissions = db.query(ReferralCommissionModel).all()
                partner_earnings = db.query(PartnerEarningModel).all()
                assert referral_commissions == []
                assert partner_earnings == []
    finally:
        app.dependency_overrides.pop(get_redis, None)
        app.dependency_overrides.pop(get_crypto_client, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
