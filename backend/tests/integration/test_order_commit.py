from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.application.services.auth_service import AuthService
from src.application.use_cases.auth_realms import RealmResolution
from src.application.use_cases.growth_codes.hashing import build_growth_code_prefix, hash_growth_code
from src.application.use_cases.refunds.create_refund import CreateRefundUseCase
from src.application.use_cases.refunds.update_refund import UpdateRefundUseCase
from src.config.settings import settings
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.billing_descriptor_model import BillingDescriptorModel
from src.infrastructure.database.models.brand_model import BrandModel
from src.infrastructure.database.models.checkout_session_model import CheckoutSessionModel
from src.infrastructure.database.models.growth_benefit_model import (
    GrowthBenefitFulfillmentModel,
    GrowthCodeBenefitModel,
    InviteBatchModel,
)
from src.infrastructure.database.models.growth_code_model import GrowthCodeModel, GrowthCodeReservationModel
from src.infrastructure.database.models.growth_code_set_model import (
    CheckoutCodeApplicationModel,
    CheckoutCodeSetModel,
    GrowthCodeReservationGroupModel,
    GrowthPrivateCatalogPolicyModel,
    OrderCodeApplicationModel,
    PrivateCatalogAccessGrantModel,
)
from src.infrastructure.database.models.growth_risk_fx_model import GrowthRiskDecisionModel
from src.infrastructure.database.models.invite_code_model import InviteCodeModel
from src.infrastructure.database.models.invoice_profile_model import InvoiceProfileModel
from src.infrastructure.database.models.legal_document_model import LegalDocumentModel
from src.infrastructure.database.models.legal_document_set_model import (
    LegalDocumentSetItemModel,
    LegalDocumentSetModel,
)
from src.infrastructure.database.models.merchant_profile_model import MerchantProfileModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.offer_model import OfferModel
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.models.outbox_event_model import OutboxEventModel
from src.infrastructure.database.models.payment_attempt_model import PaymentAttemptModel
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.models.policy_version_model import PolicyVersionModel
from src.infrastructure.database.models.pricebook_model import PricebookEntryModel, PricebookModel
from src.infrastructure.database.models.program_eligibility_policy_model import ProgramEligibilityPolicyModel
from src.infrastructure.database.models.promo_code_model import PromoCodeModel
from src.infrastructure.database.models.quote_session_model import QuoteSessionModel
from src.infrastructure.database.models.storefront_model import StorefrontModel
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
from src.main import app
from tests.helpers.realm_auth import (
    FakeRedis,
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)

pytestmark = [pytest.mark.integration]


def _make_customer_access_token(
    auth_service: AuthService,
    *,
    user_id,
    customer_realm: AuthRealmModel,
) -> str:
    token, _, _ = auth_service.create_access_token(
        str(user_id),
        "customer",
        audience=customer_realm.audience,
        principal_type="customer",
        realm_id=str(customer_realm.id),
        realm_key=customer_realm.realm_key,
        scope_family="customer",
    )
    return token


async def _seed_order_context(sessionmaker, auth_service: AuthService) -> dict[str, str]:
    now = datetime.now(UTC) - timedelta(minutes=5)

    with sessionmaker() as db:
        customer_realm = AuthRealmModel(
            id=uuid.uuid4(),
            realm_key="customer",
            realm_type="customer",
            display_name="Customer Realm",
            audience="cybervpn:customer",
            cookie_namespace="customer",
            status="active",
            is_default=True,
        )
        brand = BrandModel(
            id=uuid.uuid4(),
            brand_key="partner-brand",
            display_name="Partner Brand",
            status="active",
        )
        invoice_profile = InvoiceProfileModel(
            id=uuid.uuid4(),
            profile_key="partner-invoice",
            display_name="Partner Invoice",
            issuer_legal_name="Partner Invoice Ltd",
            tax_identifier="GB123456789",
            issuer_email="billing@partner.example.test",
            tax_behavior={"pricing_mode": "tax_inclusive"},
            invoice_footer="Thank you",
            receipt_footer="Paid",
            status="active",
        )
        merchant_profile = MerchantProfileModel(
            id=uuid.uuid4(),
            profile_key="partner-merchant",
            legal_entity_name="Partner Merchant Ltd",
            billing_descriptor="PARTNERVPN",
            invoice_profile_id=invoice_profile.id,
            settlement_reference="stripe-partner",
            supported_currencies=["USD"],
            tax_behavior={"pricing_mode": "tax_inclusive"},
            refund_responsibility_model="merchant_of_record",
            chargeback_liability_model="merchant_of_record",
            status="active",
        )
        billing_descriptor = BillingDescriptorModel(
            id=uuid.uuid4(),
            descriptor_key="partner-default",
            merchant_profile_id=merchant_profile.id,
            invoice_profile_id=invoice_profile.id,
            statement_descriptor="PARTNER VPN",
            soft_descriptor="PARTNER*VPN",
            support_phone="+44-20-5555-0100",
            support_url="https://support.partner.example.test",
            is_default=True,
            status="active",
        )
        storefront = StorefrontModel(
            id=uuid.uuid4(),
            storefront_key="partner-web",
            brand_id=brand.id,
            display_name="Partner Web",
            host="partner.example.test",
            merchant_profile_id=merchant_profile.id,
            auth_realm_id=customer_realm.id,
            status="active",
        )
        customer_user = MobileUserModel(
            id=uuid.uuid4(),
            auth_realm_id=customer_realm.id,
            email="customer@partner.example.test",
            password_hash=await auth_service.hash_password("CustomerPhase2Password123!"),
            is_active=True,
            status="active",
        )
        plan = SubscriptionPlanModel(
            id=uuid.uuid4(),
            name="partner_365d",
            plan_code="pro",
            display_name="Partner 365D",
            catalog_visibility="public",
            duration_days=365,
            device_limit=5,
            price_usd=90,
            sale_channels=["web"],
            traffic_policy={},
            connection_modes=["wireguard"],
            server_pool=["eu-west"],
            support_sla="standard",
            dedicated_ip={},
            invite_bundle={},
            trial_eligible=False,
            features={},
            is_active=True,
            sort_order=1,
        )
        offer = OfferModel(
            id=uuid.uuid4(),
            offer_key="partner-365-offer",
            display_name="Partner 365 Offer",
            subscription_plan_id=plan.id,
            included_addon_codes=[],
            sale_channels=["web"],
            visibility_rules={},
            invite_bundle={},
            trial_eligible=False,
            gift_eligible=False,
            referral_eligible=True,
            renewal_incentives={},
            version_status="active",
            effective_from=now,
            is_active=True,
        )
        pricebook = PricebookModel(
            id=uuid.uuid4(),
            pricebook_key="partner-usd",
            display_name="Partner USD",
            storefront_id=storefront.id,
            merchant_profile_id=merchant_profile.id,
            currency_code="USD",
            region_code=None,
            discount_rules={},
            renewal_pricing_policy={},
            version_status="active",
            effective_from=now,
            is_active=True,
        )
        pricebook_entry = PricebookEntryModel(
            id=uuid.uuid4(),
            pricebook_id=pricebook.id,
            offer_id=offer.id,
            visible_price=75,
            compare_at_price=90,
            included_addon_codes=[],
            display_order=0,
        )
        program_eligibility = ProgramEligibilityPolicyModel(
            id=uuid.uuid4(),
            policy_key="partner-offer-eligibility",
            subject_type="offer",
            offer_id=offer.id,
            invite_allowed=False,
            referral_credit_allowed=True,
            creator_affiliate_allowed=True,
            performance_allowed=False,
            reseller_allowed=True,
            renewal_commissionable=True,
            addon_commissionable=False,
            version_status="active",
            effective_from=now,
            is_active=True,
        )
        legal_doc_policy = PolicyVersionModel(
            id=uuid.uuid4(),
            policy_family="legal_documents",
            policy_key="partner-terms-doc",
            subject_type="legal_document",
            version_number=1,
            payload={},
            approval_state="approved",
            version_status="active",
            effective_from=now,
        )
        legal_set_policy = PolicyVersionModel(
            id=uuid.uuid4(),
            policy_family="legal_sets",
            policy_key="partner-terms-set",
            subject_type="legal_document_set",
            version_number=1,
            payload={},
            approval_state="approved",
            version_status="active",
            effective_from=now,
        )
        legal_document = LegalDocumentModel(
            id=uuid.uuid4(),
            document_key="partner-terms",
            document_type="terms_of_service",
            locale="en-EN",
            title="Partner Terms",
            content_markdown="# Terms",
            content_checksum="checksum-partner-terms",
            policy_version_id=legal_doc_policy.id,
        )
        legal_document_set = LegalDocumentSetModel(
            id=uuid.uuid4(),
            set_key="partner-web-terms",
            storefront_id=storefront.id,
            auth_realm_id=customer_realm.id,
            display_name="Partner Web Terms",
            policy_version_id=legal_set_policy.id,
        )
        legal_document_set_item = LegalDocumentSetItemModel(
            id=uuid.uuid4(),
            legal_document_set_id=legal_document_set.id,
            legal_document_id=legal_document.id,
            required=True,
            display_order=0,
        )

        db.add_all(
            [
                customer_realm,
                brand,
                invoice_profile,
                merchant_profile,
                billing_descriptor,
                storefront,
                customer_user,
                plan,
                offer,
                pricebook,
                pricebook_entry,
                program_eligibility,
                legal_doc_policy,
                legal_set_policy,
                legal_document,
                legal_document_set,
                legal_document_set_item,
            ]
        )
        db.commit()

        return {
            "customer_realm_id": str(customer_realm.id),
            "customer_realm_key": customer_realm.realm_key,
            "customer_realm_audience": customer_realm.audience,
            "customer_user_id": str(customer_user.id),
            "storefront_key": storefront.storefront_key,
            "storefront_id": str(storefront.id),
            "merchant_profile_id": str(merchant_profile.id),
            "invoice_profile_id": str(invoice_profile.id),
            "billing_descriptor_id": str(billing_descriptor.id),
            "plan_id": str(plan.id),
            "offer_id": str(offer.id),
            "offer_key": offer.offer_key,
            "pricebook_id": str(pricebook.id),
            "pricebook_key": pricebook.pricebook_key,
            "legal_document_set_id": str(legal_document_set.id),
            "program_eligibility_policy_id": str(program_eligibility.id),
        }


@pytest.mark.asyncio
async def test_order_commit_creates_canonical_order_and_history_views(async_client: AsyncClient) -> None:
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
            access_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Auth-Realm": "customer",
            }

            quote_response = await async_client.post(
                "/api/v1/quotes/",
                headers=headers,
                json={
                    "storefront_key": seeded["storefront_key"],
                    "pricebook_key": seeded["pricebook_key"],
                    "offer_key": seeded["offer_key"],
                    "plan_id": seeded["plan_id"],
                    "currency": "USD",
                    "channel": "web",
                    "use_wallet": 0,
                    "addons": [],
                },
            )
            assert quote_response.status_code == 201

            checkout_response = await async_client.post(
                "/api/v1/checkout-sessions/",
                headers={**headers, "Idempotency-Key": "order-checkout-1"},
                json={"quote_session_id": quote_response.json()["id"]},
            )
            assert checkout_response.status_code == 201

            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=headers,
                json={"checkout_session_id": checkout_response.json()["id"]},
            )
            assert order_response.status_code == 201, order_response.text
            order_payload = order_response.json()
            assert order_payload["checkout_session_id"] == checkout_response.json()["id"]
            assert order_payload["quote_session_id"] == quote_response.json()["id"]
            assert order_payload["order_status"] == "committed"
            assert order_payload["settlement_status"] == "pending_payment"
            assert order_payload["merchant_snapshot"]["merchant_profile"]["legal_entity_name"] == "Partner Merchant Ltd"
            assert order_payload["policy_snapshot"]["offer"]["offer_key"] == seeded["offer_key"]
            assert order_payload["pricing_snapshot"]["pricebook"]["id"] == seeded["pricebook_id"]
            assert order_payload["base_price"] == 75.0
            assert order_payload["displayed_price"] == 75.0
            assert order_payload["gateway_amount"] == 75.0
            subscription_snapshot = order_payload["entitlements_snapshot"]["subscription_snapshot"]
            assert subscription_snapshot["snapshot_version"] == "commercial_subscription_snapshot.v1"
            assert subscription_snapshot["price"]["base_price"] == "75.00"
            assert subscription_snapshot["price"]["currency"] == "USD"
            assert subscription_snapshot["price"]["pricebook_id"] == seeded["pricebook_id"]
            assert subscription_snapshot["plan"]["offer_key"] == seeded["offer_key"]
            assert subscription_snapshot["addons"] == []
            assert subscription_snapshot["entitlements"]["device_limit"] == 5
            assert subscription_snapshot["provisioning_profile"]["server_pool"] == ["eu-west"]
            assert len(order_payload["items"]) == 1
            assert order_payload["items"][0]["item_type"] == "plan"

            get_order_response = await async_client.get(
                f"/api/v1/orders/{order_payload['id']}",
                headers=headers,
            )
            assert get_order_response.status_code == 200
            assert get_order_response.json()["id"] == order_payload["id"]

            list_orders_response = await async_client.get("/api/v1/orders/", headers=headers)
            assert list_orders_response.status_code == 200
            assert len(list_orders_response.json()) == 1

            duplicate_order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=headers,
                json={"checkout_session_id": checkout_response.json()["id"]},
            )
            assert duplicate_order_response.status_code == 201
            assert duplicate_order_response.json()["id"] == order_payload["id"]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_private_catalog_grant_lifecycle_persists_quote_checkout_and_order(
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
            now = datetime.now(UTC)
            private_policy_version = PolicyVersionModel(
                id=uuid.uuid4(),
                policy_family="private_catalog",
                policy_key="private-catalog-order-flow",
                subject_type="growth_code",
                version_number=1,
                payload={},
                approval_state="approved",
                version_status="active",
                effective_from=now - timedelta(minutes=5),
            )
            private_growth_code = GrowthCodeModel(
                id=uuid.uuid4(),
                code_hash="9" * 64,
                code_prefix="PRIVATE",
                code_type="private_catalog",
                status="active",
                issuer_type="admin",
                storefront_id=uuid.UUID(seeded["storefront_id"]),
                auth_realm_id=customer_realm.id,
                policy_version_id=private_policy_version.id,
                max_uses=1,
                code_namespace="customer_input",
            )
            private_policy = GrowthPrivateCatalogPolicyModel(
                id=uuid.uuid4(),
                policy_version_id=private_policy_version.id,
                growth_code_id=private_growth_code.id,
                unlock_mode="plan_access",
                target_plan_ids=[seeded["plan_id"]],
                target_offer_ids=[],
                target_offer_keys=[],
                allowed_storefront_ids=[seeded["storefront_id"]],
                allowed_channels=["web"],
                grant_ttl_seconds=1800,
                max_quote_conversions=1,
                consume_mode="order_commit",
                requires_auth=True,
                is_active=True,
            )
            grant_id = uuid.uuid4()
            private_grant = PrivateCatalogAccessGrantModel(
                id=grant_id,
                policy_id=private_policy.id,
                policy_version_id=private_policy_version.id,
                growth_code_id=private_growth_code.id,
                code_set_hash="a" * 64,
                grant_token_hash="b" * 64,
                user_id=uuid.UUID(seeded["customer_user_id"]),
                auth_realm_id=customer_realm.id,
                storefront_id=uuid.UUID(seeded["storefront_id"]),
                sale_channel="web",
                allowed_plan_ids=[seeded["plan_id"]],
                allowed_offer_ids=[],
                status="issued",
                max_quote_conversions=1,
                quote_conversions_count=0,
                issued_at=now,
                expires_at=now + timedelta(minutes=30),
                metadata_={"source": "integration_test"},
            )
            with sessionmaker() as db:
                plan = db.get(SubscriptionPlanModel, uuid.UUID(seeded["plan_id"]))
                assert plan is not None
                plan.catalog_visibility = "hidden"
                plan.catalog_access_class = "private_code_gated"
                db.add_all([plan, private_policy_version, private_growth_code, private_policy, private_grant])
                db.commit()

            access_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Auth-Realm": "customer",
            }

            quote_response = await async_client.post(
                "/api/v1/quotes/",
                headers=headers,
                json={
                    "storefront_key": seeded["storefront_key"],
                    "pricebook_key": seeded["pricebook_key"],
                    "offer_key": seeded["offer_key"],
                    "plan_id": seeded["plan_id"],
                    "private_catalog_grant_id": str(grant_id),
                    "currency": "USD",
                    "channel": "web",
                    "use_wallet": 0,
                    "addons": [],
                },
            )
            assert quote_response.status_code == 201
            quote_payload = quote_response.json()
            quote_id = uuid.UUID(quote_payload["id"])
            assert quote_payload["quote"]["private_catalog_grant_id"] == str(grant_id)

            with sessionmaker() as db:
                grant = db.get(PrivateCatalogAccessGrantModel, grant_id)
                quote = db.get(QuoteSessionModel, quote_id)
                assert grant is not None
                assert quote is not None
                assert grant.status == "issued"
                assert grant.quote_conversions_count == 1
                assert grant.attached_quote_session_id == quote_id
                assert quote.private_catalog_access_grant_id == grant_id

            checkout_response = await async_client.post(
                "/api/v1/checkout-sessions/",
                headers={**headers, "Idempotency-Key": "private-catalog-checkout-1"},
                json={"quote_session_id": quote_payload["id"]},
            )
            assert checkout_response.status_code == 201
            checkout_id = uuid.UUID(checkout_response.json()["id"])

            with sessionmaker() as db:
                grant = db.get(PrivateCatalogAccessGrantModel, grant_id)
                checkout_session = db.get(CheckoutSessionModel, checkout_id)
                assert grant is not None
                assert checkout_session is not None
                assert grant.status == "issued"
                assert grant.quote_conversions_count == 1
                assert grant.attached_checkout_session_id == checkout_id
                assert checkout_session.private_catalog_access_grant_id == grant_id

            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=headers,
                json={"checkout_session_id": checkout_response.json()["id"]},
            )
            assert order_response.status_code == 201, order_response.text
            order_id = uuid.UUID(order_response.json()["id"])

            with sessionmaker() as db:
                grant = db.get(PrivateCatalogAccessGrantModel, grant_id)
                order = db.get(OrderModel, order_id)
                assert grant is not None
                assert order is not None
                assert grant.status == "consumed"
                assert grant.consumed_order_id == order_id
                assert order.private_catalog_access_grant_id == grant_id
                assert order.code_set_id is not None
                growth_snapshot = order.pricing_snapshot["growth_checkout_snapshot"]
                private_application = growth_snapshot["code_set"]["applications"][0]
                assert private_application["growth_code_id"] == str(private_growth_code.id)
                assert private_application["roles"] == ["catalog_access"]
                assert private_application["private_access"]["grant_id"] == str(grant_id)
                assert "grant_token_hash" not in str(growth_snapshot)

                code_set = db.get(CheckoutCodeSetModel, order.code_set_id)
                assert code_set is not None
                assert code_set.private_access_grant_id == grant_id
                checkout_application = db.execute(
                    select(CheckoutCodeApplicationModel).where(CheckoutCodeApplicationModel.code_set_id == code_set.id)
                ).scalar_one()
                assert checkout_application.growth_code_id == private_growth_code.id
                assert checkout_application.resolution_status == "accepted"
                assert checkout_application.discount_snapshot["applied_amount"] == "0.00"
                assert checkout_application.private_access_snapshot["grant_id"] == str(grant_id)

                order_application = db.execute(
                    select(OrderCodeApplicationModel).where(OrderCodeApplicationModel.order_id == order.id)
                ).scalar_one()
                assert order_application.code_set_id == code_set.id
                assert order_application.growth_code_id == private_growth_code.id
                assert order_application.application_role == "catalog_access"
                assert order_application.application_status == "applied"
                assert float(order_application.discount_amount) == 0.0
                assert order_application.reservation_id is None
                assert order_application.application_snapshot["application"]["private_access"]["grant_id"] == str(
                    grant_id
                )
                assert order_application.application_snapshot["snapshot_integrity"]["producer"] == (
                    "cybervpn-backend.order_code_ledger"
                )
                assert len(order_application.application_snapshot["snapshot_integrity"]["checksum"]) == 64
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_private_catalog_preflight_issued_grant_flows_through_quote_checkout_and_order(
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
            access_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Auth-Realm": "customer",
            }
            raw_code = "PRIVATE-ROUTE-90"
            now = datetime.now(UTC)
            private_policy_version = PolicyVersionModel(
                id=uuid.uuid4(),
                policy_family="private_catalog",
                policy_key="private-catalog-preflight-route-flow",
                subject_type="growth_code",
                version_number=1,
                payload={},
                approval_state="approved",
                version_status="active",
                effective_from=now - timedelta(minutes=5),
            )
            private_growth_code = GrowthCodeModel(
                id=uuid.uuid4(),
                code_hash=hash_growth_code(raw_code),
                code_prefix=build_growth_code_prefix(raw_code),
                code_type="private_catalog",
                status="active",
                issuer_type="admin",
                storefront_id=uuid.UUID(seeded["storefront_id"]),
                auth_realm_id=customer_realm.id,
                policy_version_id=private_policy_version.id,
                max_uses=1,
                code_namespace="customer_input",
            )
            private_policy = GrowthPrivateCatalogPolicyModel(
                id=uuid.uuid4(),
                policy_version_id=private_policy_version.id,
                growth_code_id=private_growth_code.id,
                unlock_mode="plan_access",
                target_plan_ids=[seeded["plan_id"]],
                target_offer_ids=[],
                target_offer_keys=[],
                allowed_storefront_ids=[seeded["storefront_id"]],
                allowed_channels=["web"],
                grant_ttl_seconds=1800,
                max_quote_conversions=1,
                consume_mode="order_commit",
                requires_auth=True,
                is_active=True,
            )
            with sessionmaker() as db:
                plan = db.get(SubscriptionPlanModel, uuid.UUID(seeded["plan_id"]))
                assert plan is not None
                plan.catalog_visibility = "hidden"
                plan.catalog_access_class = "private_code_gated"
                db.add_all([plan, private_policy_version, private_growth_code, private_policy])
                db.commit()

            preflight_response = await async_client.post(
                "/api/v3/growth/code-sets/preflight",
                headers=headers,
                json={
                    "storefront_key": seeded["storefront_key"],
                    "channel": "web",
                    "currency": "USD",
                    "codes": [
                        {
                            "code": raw_code,
                            "client_slot_id": "private-offer",
                        }
                    ],
                },
            )
            assert preflight_response.status_code == 200, preflight_response.text
            assert raw_code not in preflight_response.text
            preflight_payload = preflight_response.json()
            assert preflight_payload["status"] == "accepted"
            assert preflight_payload["private_catalog_grant"] is not None
            assert len(preflight_payload["private_offers"]) == 1
            grant_id = uuid.UUID(preflight_payload["private_catalog_grant"]["id"])
            assert preflight_payload["private_offers"][0]["quote_handoff"]["private_catalog_grant_id"] == str(grant_id)

            quote_response = await async_client.post(
                "/api/v1/quotes/",
                headers=headers,
                json={
                    "storefront_key": seeded["storefront_key"],
                    "pricebook_key": seeded["pricebook_key"],
                    "offer_key": seeded["offer_key"],
                    "plan_id": seeded["plan_id"],
                    "private_catalog_grant_id": str(grant_id),
                    "currency": "USD",
                    "channel": "web",
                    "use_wallet": 0,
                    "addons": [],
                },
            )
            assert quote_response.status_code == 201, quote_response.text
            quote_payload = quote_response.json()
            assert quote_payload["quote"]["private_catalog_grant_id"] == str(grant_id)

            checkout_response = await async_client.post(
                "/api/v1/checkout-sessions/",
                headers={**headers, "Idempotency-Key": "private-catalog-route-checkout-1"},
                json={"quote_session_id": quote_payload["id"]},
            )
            assert checkout_response.status_code == 201

            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=headers,
                json={"checkout_session_id": checkout_response.json()["id"]},
            )
            assert order_response.status_code == 201, order_response.text
            order_id = uuid.UUID(order_response.json()["id"])

            with sessionmaker() as db:
                grant = db.get(PrivateCatalogAccessGrantModel, grant_id)
                order = db.get(OrderModel, order_id)
                assert grant is not None
                assert order is not None
                assert grant.status == "consumed"
                assert grant.quote_conversions_count == 1
                assert grant.attached_quote_session_id == uuid.UUID(quote_payload["id"])
                assert grant.attached_checkout_session_id == uuid.UUID(checkout_response.json()["id"])
                assert grant.consumed_order_id == order_id
                assert order.private_catalog_access_grant_id == grant_id
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_order_snapshot_stays_stable_after_catalog_mutation(async_client: AsyncClient) -> None:
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
            access_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Auth-Realm": "customer",
            }

            quote_response = await async_client.post(
                "/api/v1/quotes/",
                headers=headers,
                json={
                    "storefront_key": seeded["storefront_key"],
                    "pricebook_key": seeded["pricebook_key"],
                    "offer_key": seeded["offer_key"],
                    "plan_id": seeded["plan_id"],
                    "currency": "USD",
                    "channel": "web",
                    "use_wallet": 0,
                    "addons": [],
                },
            )
            checkout_response = await async_client.post(
                "/api/v1/checkout-sessions/",
                headers={**headers, "Idempotency-Key": "order-checkout-stability"},
                json={"quote_session_id": quote_response.json()["id"]},
            )
            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=headers,
                json={"checkout_session_id": checkout_response.json()["id"]},
            )
            assert order_response.status_code == 201
            order_id = order_response.json()["id"]

            with sessionmaker() as db:
                offer = db.get(OfferModel, uuid.UUID(seeded["offer_id"]))
                offer.display_name = "Mutated Offer Name"
                pricebook = db.get(PricebookModel, uuid.UUID(seeded["pricebook_id"]))
                pricebook.display_name = "Mutated Pricebook"
                merchant = db.get(MerchantProfileModel, uuid.UUID(seeded["merchant_profile_id"]))
                merchant.legal_entity_name = "Mutated Merchant"
                db.add_all([offer, pricebook, merchant])
                db.commit()

            stable_order_response = await async_client.get(f"/api/v1/orders/{order_id}", headers=headers)
            assert stable_order_response.status_code == 200
            stable_order = stable_order_response.json()
            assert stable_order["policy_snapshot"]["offer"]["display_name"] == "Partner 365 Offer"
            assert stable_order["pricing_snapshot"]["pricebook"]["pricebook_key"] == seeded["pricebook_key"]
            assert stable_order["pricing_snapshot"]["quote"]["base_price"] == 75.0
            assert stable_order["pricing_snapshot"]["quote"]["gateway_amount"] == 75.0
            assert stable_order["entitlements_snapshot"]["subscription_snapshot"]["price"]["base_price"] == "75.00"
            assert stable_order["merchant_snapshot"]["merchant_profile"]["legal_entity_name"] == "Partner Merchant Ltd"

            with sessionmaker() as db:
                checkout_session = db.get(CheckoutSessionModel, uuid.UUID(checkout_response.json()["id"]))
                assert checkout_session.checkout_status == "committed"
                order = db.get(OrderModel, uuid.UUID(order_id))
                assert order is not None
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_order_commit_consumes_reserved_promo(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "checkout_code_discounts_enabled", True)
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
                promo = PromoCodeModel(
                    id=uuid.uuid4(),
                    code="PROMOCOMMIT10",
                    discount_type="percent",
                    discount_value=10,
                    is_active=True,
                )
                db.add(promo)
                db.commit()

            access_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Auth-Realm": "customer",
            }

            quote_response = await async_client.post(
                "/api/v1/quotes/",
                headers=headers,
                json={
                    "storefront_key": seeded["storefront_key"],
                    "pricebook_key": seeded["pricebook_key"],
                    "offer_key": seeded["offer_key"],
                    "plan_id": seeded["plan_id"],
                    "currency": "USD",
                    "channel": "web",
                    "code_input": "PROMOCOMMIT10",
                    "use_wallet": 0,
                    "addons": [],
                },
            )
            assert quote_response.status_code == 201
            quote_payload = quote_response.json()
            reservation_id = quote_payload["quote"]["code_resolution"]["reservation_id"]

            checkout_response = await async_client.post(
                "/api/v1/checkout-sessions/",
                headers={**headers, "Idempotency-Key": "order-checkout-promo-1"},
                json={"quote_session_id": quote_payload["id"]},
            )
            assert checkout_response.status_code == 201

            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=headers,
                json={"checkout_session_id": checkout_response.json()["id"]},
            )
            assert order_response.status_code == 201, order_response.text
            order_payload = order_response.json()

            with sessionmaker() as db:
                reservation = db.get(GrowthCodeReservationModel, uuid.UUID(reservation_id))
                assert reservation is not None
                assert reservation.status == "consumed"
                assert reservation.checkout_session_id == uuid.UUID(checkout_response.json()["id"])
                assert reservation.consumed_order_id == uuid.UUID(order_payload["id"])
                assert reservation.release_reason == "order_commit"
                assert reservation.reservation_group_id is not None
                reservation_group = db.get(GrowthCodeReservationGroupModel, reservation.reservation_group_id)
                assert reservation_group is not None
                assert reservation_group.status == "consumed"
                assert reservation_group.order_id == uuid.UUID(order_payload["id"])
                assert reservation_group.release_reason == "order_commit"
                order = db.get(OrderModel, uuid.UUID(order_payload["id"]))
                checkout_session = db.get(CheckoutSessionModel, uuid.UUID(checkout_response.json()["id"]))
                assert order is not None
                assert checkout_session is not None
                assert order.code_set_id is not None
                assert checkout_session.code_set_id == order.code_set_id
                code_set = db.get(CheckoutCodeSetModel, order.code_set_id)
                assert code_set is not None
                assert code_set.status == "consumed"
                assert code_set.acceptance_mode == "single_legacy_code"
                assert code_set.aggregate_result["code_ref"]["redacted"] is True
                assert "PROMOCOMMIT10" not in str(code_set.aggregate_result)
                checkout_application = db.execute(
                    select(CheckoutCodeApplicationModel).where(CheckoutCodeApplicationModel.code_set_id == code_set.id)
                ).scalar_one()
                assert checkout_application.resolution_status == "accepted"
                assert checkout_application.reservation_id == uuid.UUID(reservation_id)
                assert "PROMOCOMMIT10" not in str(checkout_application.discount_snapshot)
                order_application = db.execute(
                    select(OrderCodeApplicationModel).where(OrderCodeApplicationModel.order_id == order.id)
                ).scalar_one()
                assert order_application.code_set_id == code_set.id
                assert order_application.growth_code_id == reservation.growth_code_id
                assert order_application.application_role == "promo"
                assert order_application.application_status == "applied"
                assert float(order_application.discount_amount) == 7.5
                assert order_application.currency_code == "USD"
                assert order_application.reservation_id == uuid.UUID(reservation_id)
                assert order_application.application_snapshot["snapshot_version"] == "order_code_application.v6"
                assert "PROMOCOMMIT10" not in str(order_application.application_snapshot)
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_order_commit_consumes_multi_code_set(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "checkout_code_discounts_enabled", True)
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
                db.add_all(
                    [
                        PromoCodeModel(
                            id=uuid.uuid4(),
                            code="BASKETPERCENT10",
                            discount_type="percent",
                            discount_value=10,
                            is_active=True,
                        ),
                        PromoCodeModel(
                            id=uuid.uuid4(),
                            code="BASKETFIXED5",
                            discount_type="fixed",
                            discount_value=5,
                            is_active=True,
                        ),
                    ]
                )
                db.commit()

            access_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Auth-Realm": "customer",
            }

            quote_response = await async_client.post(
                "/api/v1/quotes/",
                headers=headers,
                json={
                    "storefront_key": seeded["storefront_key"],
                    "pricebook_key": seeded["pricebook_key"],
                    "offer_key": seeded["offer_key"],
                    "plan_id": seeded["plan_id"],
                    "currency": "USD",
                    "channel": "web",
                    "codes": [
                        {"code": "BASKETFIXED5", "client_slot_id": "fixed"},
                        {"code": "BASKETPERCENT10", "client_slot_id": "percent"},
                    ],
                    "use_wallet": 0,
                    "addons": [],
                },
            )
            assert quote_response.status_code == 201, quote_response.text
            quote_payload = quote_response.json()
            assert quote_payload["quote"]["base_price"] == 75.0
            assert quote_payload["quote"]["discount_amount"] == 12.5
            assert quote_payload["quote"]["gateway_amount"] == 62.5
            assert len(quote_payload["quote"]["discounts"]) == 2
            assert "BASKETFIXED5" not in str(quote_payload)
            assert "BASKETPERCENT10" not in str(quote_payload)

            checkout_response = await async_client.post(
                "/api/v1/checkout-sessions/",
                headers={**headers, "Idempotency-Key": "order-checkout-code-set-1"},
                json={"quote_session_id": quote_payload["id"]},
            )
            assert checkout_response.status_code == 201, checkout_response.text

            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=headers,
                json={"checkout_session_id": checkout_response.json()["id"]},
            )
            assert order_response.status_code == 201, order_response.text
            order_payload = order_response.json()

            with sessionmaker() as db:
                quote_session = db.get(QuoteSessionModel, uuid.UUID(quote_payload["id"]))
                checkout_session = db.get(CheckoutSessionModel, uuid.UUID(checkout_response.json()["id"]))
                order = db.get(OrderModel, uuid.UUID(order_payload["id"]))
                assert quote_session is not None
                assert checkout_session is not None
                assert order is not None
                assert quote_session.code_set_id is not None
                assert checkout_session.code_set_id == quote_session.code_set_id
                assert order.code_set_id == quote_session.code_set_id
                assert "BASKETFIXED5" not in str(quote_session.request_snapshot)
                assert "BASKETPERCENT10" not in str(quote_session.request_snapshot)
                assert "BASKETFIXED5" not in str(quote_session.quote_snapshot)
                assert "BASKETPERCENT10" not in str(quote_session.quote_snapshot)

                code_set = db.get(CheckoutCodeSetModel, quote_session.code_set_id)
                assert code_set is not None
                assert code_set.status == "consumed"
                assert code_set.acceptance_mode == "all_or_nothing"
                assert code_set.aggregate_result["application_count"] == 2
                assert code_set.aggregate_result["accepted_count"] == 2
                assert "BASKETFIXED5" not in str(code_set.aggregate_result)
                assert "BASKETPERCENT10" not in str(code_set.aggregate_result)

                reservations = (
                    db.execute(
                        select(GrowthCodeReservationModel)
                        .where(GrowthCodeReservationModel.quote_session_id == quote_session.id)
                        .order_by(GrowthCodeReservationModel.growth_code_id.asc())
                    )
                    .scalars()
                    .all()
                )
                assert len(reservations) == 2
                assert {reservation.status for reservation in reservations} == {"consumed"}
                assert {reservation.checkout_session_id for reservation in reservations} == {checkout_session.id}
                assert {reservation.consumed_order_id for reservation in reservations} == {order.id}
                assert len({reservation.reservation_group_id for reservation in reservations}) == 1

                reservation_group = db.get(GrowthCodeReservationGroupModel, reservations[0].reservation_group_id)
                assert reservation_group is not None
                assert reservation_group.status == "consumed"
                assert reservation_group.order_id == order.id
                assert reservation_group.release_reason == "order_commit"

                checkout_applications = (
                    db.execute(
                        select(CheckoutCodeApplicationModel)
                        .where(CheckoutCodeApplicationModel.code_set_id == code_set.id)
                        .order_by(CheckoutCodeApplicationModel.canonical_order.asc())
                    )
                    .scalars()
                    .all()
                )
                assert len(checkout_applications) == 2
                assert {application.resolution_status for application in checkout_applications} == {"accepted"}
                assert {application.reservation_id for application in checkout_applications} == {
                    reservation.id for reservation in reservations
                }
                assert {application.discount_snapshot["applied_amount"] for application in checkout_applications} == {
                    "5.00",
                    "7.50",
                }
                assert all("BASKET" not in str(application.discount_snapshot) for application in checkout_applications)

                order_applications = (
                    db.execute(
                        select(OrderCodeApplicationModel)
                        .where(OrderCodeApplicationModel.order_id == order.id)
                        .order_by(OrderCodeApplicationModel.created_at.asc())
                    )
                    .scalars()
                    .all()
                )
                assert len(order_applications) == 2
                assert sum(float(application.discount_amount) for application in order_applications) == 12.5
                assert {application.reservation_id for application in order_applications} == {
                    reservation.id for reservation in reservations
                }
                for application in order_applications:
                    snapshot = application.application_snapshot
                    assert snapshot["snapshot_version"] == "order_code_application.v6"
                    assert snapshot["snapshot_integrity"]["producer"] == "cybervpn-backend.order_code_ledger"
                    assert len(snapshot["snapshot_integrity"]["checksum"]) == 64
                    assert snapshot["application"]["discount"]["applied_amount"] in {"5.00", "7.50"}
                fixed_application = next(
                    application
                    for application in order_applications
                    if application.application_snapshot["application"]["discount"]["applied_amount"] == "5.00"
                )
                assert (
                    fixed_application.application_snapshot["application"]["discount"]["fx_conversion"]["no_rerate"]
                    is True
                )
                assert all(
                    "BASKETFIXED5" not in str(application.application_snapshot) for application in order_applications
                )
                assert all(
                    "BASKETPERCENT10" not in str(application.application_snapshot) for application in order_applications
                )
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_zero_gateway_payment_attempt_creates_internal_payment_and_succeeded_attempt(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "checkout_code_discounts_enabled", True)
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
                promo = PromoCodeModel(
                    id=uuid.uuid4(),
                    code="PROMOZERO100",
                    discount_type="percent",
                    discount_value=100,
                    is_active=True,
                )
                db.add(promo)
                db.commit()

            access_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Auth-Realm": "customer",
            }

            quote_response = await async_client.post(
                "/api/v1/quotes/",
                headers=headers,
                json={
                    "storefront_key": seeded["storefront_key"],
                    "pricebook_key": seeded["pricebook_key"],
                    "offer_key": seeded["offer_key"],
                    "plan_id": seeded["plan_id"],
                    "currency": "USD",
                    "channel": "web",
                    "code_input": "PROMOZERO100",
                    "use_wallet": 0,
                    "addons": [],
                },
            )
            assert quote_response.status_code == 201
            quote_payload = quote_response.json()
            assert quote_payload["quote"]["is_zero_gateway"] is True
            assert quote_payload["quote"]["gateway_amount"] == 0.0
            reservation_id = quote_payload["quote"]["code_resolution"]["reservation_id"]

            checkout_response = await async_client.post(
                "/api/v1/checkout-sessions/",
                headers={**headers, "Idempotency-Key": "order-checkout-zero-1"},
                json={"quote_session_id": quote_payload["id"]},
            )
            assert checkout_response.status_code == 201

            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=headers,
                json={"checkout_session_id": checkout_response.json()["id"]},
            )
            assert order_response.status_code == 201
            order_payload = order_response.json()
            assert order_payload["settlement_status"] == "pending_internal_settlement"
            assert order_payload["gateway_amount"] == 0.0
            assert order_payload["discount_amount"] == 75.0

            with sessionmaker() as db:
                order = db.get(OrderModel, uuid.UUID(order_payload["id"]))
                assert order is not None
                assert order.code_set_id is not None
                assert float(order.commission_base_amount) == 0.0
                reservation = db.get(GrowthCodeReservationModel, uuid.UUID(reservation_id))
                assert reservation is not None
                assert reservation.status == "committed"
                assert reservation.consumed_order_id == order.id
                assert reservation.consumed_payment_id is None
                assert reservation.committed_at is not None
                assert reservation.reservation_group_id is not None
                reservation_group = db.get(GrowthCodeReservationGroupModel, reservation.reservation_group_id)
                assert reservation_group is not None
                assert reservation_group.status == "committed"
                assert reservation_group.order_id == order.id
                code_set = db.get(CheckoutCodeSetModel, order.code_set_id)
                assert code_set is not None
                assert code_set.status == "committed"
                assert (
                    db.execute(select(PaymentModel).where(PaymentModel.external_id == f"internal_zero:{order.id}"))
                    .scalars()
                    .first()
                    is None
                )
                assert (
                    db.execute(select(PaymentAttemptModel).where(PaymentAttemptModel.order_id == order.id))
                    .scalars()
                    .first()
                    is None
                )

            attempt_response = await async_client.post(
                "/api/v1/payment-attempts/",
                headers={**headers, "Idempotency-Key": "zero-payment-attempt-1"},
                json={"order_id": order_payload["id"]},
            )
            assert attempt_response.status_code == 201, attempt_response.text
            attempt_payload = attempt_response.json()
            assert attempt_payload["order_id"] == order_payload["id"]
            assert attempt_payload["provider"] == "internal_zero"
            assert attempt_payload["status"] == "succeeded"
            assert attempt_payload["invoice"] is None
            assert attempt_payload["gateway_amount"] == 0.0

            duplicate_attempt_response = await async_client.post(
                "/api/v1/payment-attempts/",
                headers={**headers, "Idempotency-Key": "zero-payment-attempt-1"},
                json={"order_id": order_payload["id"]},
            )
            assert duplicate_attempt_response.status_code == 200
            assert duplicate_attempt_response.json()["id"] == attempt_payload["id"]

            conflicting_replay_response = await async_client.post(
                "/api/v1/payment-attempts/",
                headers={**headers, "Idempotency-Key": "zero-payment-attempt-2"},
                json={"order_id": order_payload["id"]},
            )
            assert conflicting_replay_response.status_code == 409

            with sessionmaker() as db:
                order = db.get(OrderModel, uuid.UUID(order_payload["id"]))
                assert order is not None
                assert order.settlement_status == "paid"
                payment = db.execute(
                    select(PaymentModel).where(PaymentModel.external_id == f"internal_zero:{order.id}")
                ).scalar_one()
                assert payment.provider == "internal_zero"
                assert payment.status == "completed"
                assert float(payment.final_amount) == 0.0
                assert payment.code_set_id == order.code_set_id
                assert payment.metadata_["no_external_invoice"] is True
                assert payment.metadata_["reason_code"] == "promotion_fully_funded"
                assert payment.metadata_["funding_source"] == "promotion"
                assert payment.metadata_["commission_base_amount"] == "0.00"
                assert payment.growth_snapshot["growth_checkout_snapshot"]["snapshot_version"] == "growth-checkout.v3"
                assert "PROMOZERO100" not in str(payment.metadata_)
                assert "PROMOZERO100" not in str(payment.growth_snapshot)
                attempt = db.execute(
                    select(PaymentAttemptModel).where(PaymentAttemptModel.payment_id == payment.id)
                ).scalar_one()
                assert attempt.provider == "internal_zero"
                assert attempt.status == "succeeded"
                assert attempt.code_set_id == order.code_set_id
                assert attempt.external_reference == payment.external_id
                assert attempt.provider_snapshot["invoice_created"] is False
                assert attempt.provider_snapshot["reason_code"] == "promotion_fully_funded"
                assert float(attempt.gateway_amount) == 0.0
                reservation = db.get(GrowthCodeReservationModel, uuid.UUID(reservation_id))
                assert reservation is not None
                assert reservation.status == "consumed"
                assert reservation.consumed_order_id == order.id
                assert reservation.consumed_payment_id == payment.id
                assert reservation.consumed_at is not None
                assert reservation.release_reason == "payment_settlement"
                reservation_group = db.get(GrowthCodeReservationGroupModel, reservation.reservation_group_id)
                assert reservation_group is not None
                assert reservation_group.status == "consumed"
                assert reservation_group.payment_id == payment.id
                code_set = db.get(CheckoutCodeSetModel, order.code_set_id)
                assert code_set is not None
                assert code_set.status == "consumed"
                assert code_set.payment_id == payment.id
                attempts = (
                    db.execute(select(PaymentAttemptModel).where(PaymentAttemptModel.order_id == order.id))
                    .scalars()
                    .all()
                )
                assert len(attempts) == 1
                risk_decisions = (
                    db.execute(
                        select(GrowthRiskDecisionModel)
                        .where(GrowthRiskDecisionModel.order_id == order.id)
                        .order_by(GrowthRiskDecisionModel.decided_at.asc())
                    )
                    .scalars()
                    .all()
                )
                risk_contexts = {decision.action_context for decision in risk_decisions}
                assert {"zero_settlement", "benefit_fulfill"}.issubset(risk_contexts)
                assert all(decision.final_action == "allow" for decision in risk_decisions)

                adapter = SyncSessionAdapter(db)
                refund_result = await CreateRefundUseCase(adapter).execute(
                    order_id=order.id,
                    user_id=order.user_id,
                    current_realm=RealmResolution(auth_realm=customer_realm, source="test"),
                    idempotency_key="zero-payment-refund-1",
                    amount=Decimal("75.00"),
                    payment_attempt_id=attempt.id,
                    reason_code="customer_request",
                    reason_text="Regression proof for per-code reversal ledger",
                )
                assert refund_result.created is True

                updated_refund = await UpdateRefundUseCase(adapter).execute(
                    refund_id=refund_result.refund.id,
                    refund_status="succeeded",
                    external_reference="zero-refund-1",
                    provider_snapshot={"provider_result": "local_reconciled"},
                    skip_provider_execution=True,
                    source_context={"source_test": "zero_gateway_code_ledger_reversal"},
                )
                assert updated_refund.refund_status == "succeeded"
                db.expire_all()

                refreshed_order = db.get(OrderModel, order.id)
                assert refreshed_order is not None
                assert refreshed_order.settlement_status == "refunded"
                refreshed_payment = db.get(PaymentModel, payment.id)
                assert refreshed_payment is not None
                assert refreshed_payment.status == "refunded"
                order_applications = (
                    db.execute(select(OrderCodeApplicationModel).where(OrderCodeApplicationModel.order_id == order.id))
                    .scalars()
                    .all()
                )
                assert len(order_applications) == 1
                reversed_application = order_applications[0]
                assert reversed_application.application_status == "reversed"
                reversal_snapshot = reversed_application.application_snapshot
                assert reversal_snapshot["reversal_state"] == "refund_reversed"
                assert reversal_snapshot["last_reversal"]["refund_id"] == str(refund_result.refund.id)
                assert reversal_snapshot["last_reversal"]["reversal_reason"] == "refund_succeeded"
                assert "PROMOZERO100" not in str(reversal_snapshot)

                refund_event = (
                    db.execute(
                        select(OutboxEventModel).where(
                            OutboxEventModel.event_name == "refund.provider_state_reconciled",
                            OutboxEventModel.aggregate_id == str(refund_result.refund.id),
                        )
                    )
                    .scalars()
                    .one()
                )
                growth_reversal = refund_event.event_payload["growth_code_reversal"]
                assert growth_reversal["order_code_application_count"] == 1
                assert growth_reversal["order_code_application_ids"] == [str(reversed_application.id)]
                assert "PROMOZERO100" not in str(refund_event.event_payload)
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_zero_gateway_payment_attempt_fulfills_issue_invites_benefit(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "checkout_code_discounts_enabled", True)
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
            promo_code = "PROMOBENEFIT100"
            growth_code_id = uuid.uuid4()
            benefit_id = uuid.uuid4()
            with sessionmaker() as db:
                promo = PromoCodeModel(
                    id=uuid.uuid4(),
                    code=promo_code,
                    discount_type="percent",
                    discount_value=100,
                    is_active=True,
                )
                growth_code = GrowthCodeModel(
                    id=growth_code_id,
                    code_hash=hash_growth_code(promo_code),
                    code_prefix=build_growth_code_prefix(promo_code),
                    code_type="promo",
                    status="active",
                    issuer_type="admin",
                    max_uses=1,
                    uses_count=0,
                    code_namespace="customer_input",
                )
                benefit = GrowthCodeBenefitModel(
                    id=benefit_id,
                    growth_code_id=growth_code_id,
                    benefit_type="issue_invites",
                    trigger_type="payment_completed",
                    merge_mode="append",
                    config={
                        "count": 2,
                        "friend_days": 7,
                        "expiry_mode": "relative",
                        "expiry_days": 30,
                        "entitlement_mode": "profile_key",
                        "entitlement_profile_key": "invite_limited_access_v1",
                        "allow_zero_net_payment": True,
                        "minimum_net_paid_amount": "0",
                        "owner_mode": "buyer",
                        "reversal_mode": "revoke_unredeemed",
                    },
                    eligibility={},
                    sort_order=0,
                    is_active=True,
                )
                db.add_all([promo, growth_code, benefit])
                db.commit()

            access_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Auth-Realm": "customer",
            }

            quote_response = await async_client.post(
                "/api/v1/quotes/",
                headers=headers,
                json={
                    "storefront_key": seeded["storefront_key"],
                    "pricebook_key": seeded["pricebook_key"],
                    "offer_key": seeded["offer_key"],
                    "plan_id": seeded["plan_id"],
                    "currency": "USD",
                    "channel": "web",
                    "code_input": promo_code,
                    "use_wallet": 0,
                    "addons": [],
                },
            )
            assert quote_response.status_code == 201
            quote_payload = quote_response.json()
            assert quote_payload["quote"]["is_zero_gateway"] is True
            with sessionmaker() as db:
                quote_session = db.get(QuoteSessionModel, uuid.UUID(quote_payload["id"]))
                assert quote_session is not None
                policy_snapshot = quote_session.quote_snapshot["code_resolution"]["policy_snapshot"]
                assert policy_snapshot["benefits"][0]["benefit_id"] == str(benefit_id)

            checkout_response = await async_client.post(
                "/api/v1/checkout-sessions/",
                headers={**headers, "Idempotency-Key": "order-checkout-zero-benefit-1"},
                json={"quote_session_id": quote_payload["id"]},
            )
            assert checkout_response.status_code == 201

            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=headers,
                json={"checkout_session_id": checkout_response.json()["id"]},
            )
            assert order_response.status_code == 201, order_response.text
            order_payload = order_response.json()
            assert order_payload["settlement_status"] == "pending_internal_settlement"

            with sessionmaker() as db:
                order = db.get(OrderModel, uuid.UUID(order_payload["id"]))
                assert order is not None
                assert (
                    db.execute(
                        select(GrowthBenefitFulfillmentModel).where(
                            GrowthBenefitFulfillmentModel.order_id == order.id,
                            GrowthBenefitFulfillmentModel.benefit_id == benefit_id,
                        )
                    )
                    .scalars()
                    .first()
                    is None
                )

            attempt_response = await async_client.post(
                "/api/v1/payment-attempts/",
                headers={**headers, "Idempotency-Key": "zero-benefit-attempt-1"},
                json={"order_id": order_payload["id"]},
            )
            assert attempt_response.status_code == 201, attempt_response.text
            assert attempt_response.json()["provider"] == "internal_zero"
            assert attempt_response.json()["status"] == "succeeded"

            with sessionmaker() as db:
                order = db.get(OrderModel, uuid.UUID(order_payload["id"]))
                assert order is not None
                assert order.settlement_status == "paid"
                payment = db.execute(
                    select(PaymentModel).where(PaymentModel.external_id == f"internal_zero:{order.id}")
                ).scalar_one()
                fulfillment = db.execute(
                    select(GrowthBenefitFulfillmentModel).where(
                        GrowthBenefitFulfillmentModel.order_id == order.id,
                        GrowthBenefitFulfillmentModel.benefit_id == benefit_id,
                    )
                ).scalar_one()
                batch = db.execute(
                    select(InviteBatchModel).where(InviteBatchModel.source_benefit_id == benefit_id)
                ).scalar_one()
                invite_codes = (
                    db.execute(select(InviteCodeModel).where(InviteCodeModel.batch_id == batch.id)).scalars().all()
                )
                outbox_event = db.execute(
                    select(OutboxEventModel).where(
                        OutboxEventModel.event_name == "growth_benefit.fulfillment.completed"
                    )
                ).scalar_one()

                assert fulfillment.status == "completed"
                assert fulfillment.payment_id == payment.id
                assert fulfillment.idempotency_key.startswith("growth-benefit:")
                assert fulfillment.config_snapshot["count"] == 2
                assert fulfillment.result_payload["invite_batch_id"] == str(batch.id)
                assert fulfillment.result_payload["issued_count"] == 2
                assert batch.status == "issued"
                assert batch.requested_count == 2
                assert batch.issued_count == 2
                assert batch.source_order_id == order.id
                assert batch.source_payment_id == payment.id
                assert len(invite_codes) == 2
                assert {invite.status for invite in invite_codes} == {"issued"}
                assert {invite.source_payment_id for invite in invite_codes} == {payment.id}
                assert all(invite.code_hash and len(invite.code_hash) == 64 for invite in invite_codes)
                assert payment.growth_snapshot["benefit_fulfillments"][0]["fulfillment_id"] == str(fulfillment.id)
                assert payment.growth_snapshot["benefit_fulfillments"][0]["idempotency_key_present"] is True
                assert payment.growth_snapshot["benefit_fulfillments"][0]["idempotency_key_hash"].startswith("sha256:")
                assert "idempotency_key" not in payment.growth_snapshot["benefit_fulfillments"][0]
                assert outbox_event.aggregate_id == str(fulfillment.id)
                assert outbox_event.event_payload["result_payload"]["invite_batch_id"] == str(batch.id)
                persisted_payload = str(
                    {
                        "fulfillment": fulfillment.result_payload,
                        "payment": payment.growth_snapshot,
                        "outbox": outbox_event.event_payload,
                    }
                )
                assert promo_code not in persisted_payload
                assert fulfillment.idempotency_key not in persisted_payload
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_order_commit_rejects_tampered_quote_snapshot_before_side_effects(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "checkout_code_discounts_enabled", True)
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
                db.add(
                    PromoCodeModel(
                        id=uuid.uuid4(),
                        code="PROMOTAMPER100",
                        discount_type="percent",
                        discount_value=100,
                        is_active=True,
                    )
                )
                db.commit()

            access_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Auth-Realm": "customer",
            }

            quote_response = await async_client.post(
                "/api/v1/quotes/",
                headers=headers,
                json={
                    "storefront_key": seeded["storefront_key"],
                    "pricebook_key": seeded["pricebook_key"],
                    "offer_key": seeded["offer_key"],
                    "plan_id": seeded["plan_id"],
                    "currency": "USD",
                    "channel": "web",
                    "code_input": "PROMOTAMPER100",
                    "use_wallet": 0,
                    "addons": [],
                },
            )
            assert quote_response.status_code == 201

            checkout_response = await async_client.post(
                "/api/v1/checkout-sessions/",
                headers={**headers, "Idempotency-Key": "order-checkout-tampered-1"},
                json={"quote_session_id": quote_response.json()["id"]},
            )
            assert checkout_response.status_code == 201
            checkout_session_id = uuid.UUID(checkout_response.json()["id"])

            with sessionmaker() as db:
                checkout_session = db.get(CheckoutSessionModel, checkout_session_id)
                assert checkout_session is not None
                checkout_snapshot = dict(checkout_session.checkout_snapshot)
                quote_snapshot = dict(checkout_snapshot["quote_snapshot"])
                quote_snapshot["discount_amount"] = 1
                checkout_snapshot["quote_snapshot"] = quote_snapshot
                checkout_session.checkout_snapshot = checkout_snapshot
                db.commit()

            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=headers,
                json={"checkout_session_id": str(checkout_session_id)},
            )

            assert order_response.status_code == 409
            assert order_response.json()["detail"] == "SNAPSHOT_INTEGRITY_ERROR"
            with sessionmaker() as db:
                assert (
                    db.execute(select(OrderModel).where(OrderModel.checkout_session_id == checkout_session_id))
                    .scalars()
                    .first()
                    is None
                )
                assert db.execute(select(PaymentModel)).scalars().first() is None
                assert db.execute(select(PaymentAttemptModel)).scalars().first() is None
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
