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
from src.infrastructure.database.models.invoice_profile_model import InvoiceProfileModel
from src.infrastructure.database.models.legal_document_model import LegalDocumentModel
from src.infrastructure.database.models.legal_document_set_model import (
    LegalDocumentSetItemModel,
    LegalDocumentSetModel,
)
from src.infrastructure.database.models.merchant_profile_model import MerchantProfileModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.offer_model import OfferModel
from src.infrastructure.database.models.policy_version_model import PolicyVersionModel
from src.infrastructure.database.models.pricebook_model import PricebookEntryModel, PricebookModel
from src.infrastructure.database.models.program_eligibility_policy_model import ProgramEligibilityPolicyModel
from src.infrastructure.database.models.quote_session_model import QuoteSessionModel
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


async def _seed_quote_context(sessionmaker, auth_service: AuthService) -> dict[str, str]:
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
            "pricebook_entry_id": str(pricebook_entry.id),
            "legal_document_set_id": str(legal_document_set.id),
            "program_eligibility_policy_id": str(program_eligibility.id),
        }


@pytest.mark.asyncio
async def test_quote_and_checkout_sessions_follow_lineage_and_idempotency(async_client: AsyncClient) -> None:
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
            quote_payload = quote_response.json()
            assert quote_payload["storefront_key"] == seeded["storefront_key"]
            assert quote_payload["merchant_profile_id"] == seeded["merchant_profile_id"]
            assert quote_payload["invoice_profile_id"] == seeded["invoice_profile_id"]
            assert quote_payload["billing_descriptor_id"] == seeded["billing_descriptor_id"]
            assert quote_payload["pricebook_id"] == seeded["pricebook_id"]
            assert quote_payload["offer_id"] == seeded["offer_id"]
            assert quote_payload["legal_document_set_id"] == seeded["legal_document_set_id"]
            assert quote_payload["program_eligibility_policy_id"] == seeded["program_eligibility_policy_id"]

            checkout_response = await async_client.post(
                "/api/v1/checkout-sessions/",
                headers={**headers, "Idempotency-Key": "quote-checkout-1"},
                json={"quote_session_id": quote_payload["id"]},
            )
            assert checkout_response.status_code == 201
            checkout_payload = checkout_response.json()
            assert checkout_payload["quote_session_id"] == quote_payload["id"]
            assert checkout_payload["storefront_key"] == seeded["storefront_key"]
            assert checkout_payload["idempotency_key"] == "quote-checkout-1"

            repeated_response = await async_client.post(
                "/api/v1/checkout-sessions/",
                headers={**headers, "Idempotency-Key": "quote-checkout-1"},
                json={"quote_session_id": quote_payload["id"]},
            )
            assert repeated_response.status_code == 200
            assert repeated_response.json()["id"] == checkout_payload["id"]

            conflicting_response = await async_client.post(
                "/api/v1/checkout-sessions/",
                headers={**headers, "Idempotency-Key": "quote-checkout-2"},
                json={"quote_session_id": quote_payload["id"]},
            )
            assert conflicting_response.status_code == 409
            assert "already exists" in conflicting_response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_checkout_session_creation_fails_when_quote_becomes_stale(async_client: AsyncClient) -> None:
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

            with sessionmaker() as db:
                entry = db.get(PricebookEntryModel, uuid.UUID(seeded["pricebook_entry_id"]))
                entry.visible_price = 69
                db.add(entry)
                db.commit()

            checkout_response = await async_client.post(
                "/api/v1/checkout-sessions/",
                headers={**headers, "Idempotency-Key": "stale-quote-1"},
                json={"quote_session_id": quote_response.json()["id"]},
            )
            assert checkout_response.status_code == 409
            assert "stale" in checkout_response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_checkout_session_creation_fails_for_expired_quote(async_client: AsyncClient) -> None:
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

            with sessionmaker() as db:
                quote_session = db.get(QuoteSessionModel, uuid.UUID(quote_response.json()["id"]))
                quote_session.expires_at = datetime.now(UTC) - timedelta(minutes=1)
                db.add(quote_session)
                db.commit()

            checkout_response = await async_client.post(
                "/api/v1/checkout-sessions/",
                headers={**headers, "Idempotency-Key": "expired-quote-1"},
                json={"quote_session_id": quote_response.json()["id"]},
            )
            assert checkout_response.status_code == 409
            assert "expired" in checkout_response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
