from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.billing_descriptor_model import BillingDescriptorModel
from src.infrastructure.database.models.brand_model import BrandModel
from src.infrastructure.database.models.checkout_session_model import CheckoutSessionModel
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
from src.infrastructure.database.models.policy_version_model import PolicyVersionModel
from src.infrastructure.database.models.pricebook_model import PricebookEntryModel, PricebookModel
from src.infrastructure.database.models.program_eligibility_policy_model import ProgramEligibilityPolicyModel
from src.infrastructure.database.models.storefront_model import StorefrontModel
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
from src.main import app
from tests.helpers.realm_auth import (
    FakeRedis,
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
            assert order_response.status_code == 201
            order_payload = order_response.json()
            assert order_payload["checkout_session_id"] == checkout_response.json()["id"]
            assert order_payload["quote_session_id"] == quote_response.json()["id"]
            assert order_payload["order_status"] == "committed"
            assert order_payload["settlement_status"] == "pending_payment"
            assert order_payload["merchant_snapshot"]["merchant_profile"]["legal_entity_name"] == "Partner Merchant Ltd"
            assert order_payload["policy_snapshot"]["offer"]["offer_key"] == seeded["offer_key"]
            assert order_payload["pricing_snapshot"]["pricebook"]["id"] == seeded["pricebook_id"]
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
            assert duplicate_order_response.status_code == 409
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
