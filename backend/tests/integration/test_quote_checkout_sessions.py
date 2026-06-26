from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.application.services.auth_service import AuthService
from src.application.use_cases.partner_attribution.attribution import EnsurePendingPartnerAttributionClaimedUseCase
from src.application.use_cases.partner_attribution.utils import (
    PARTNER_ATTRIBUTION_COOKIE_NAME,
    hash_partner_attribution_token,
)
from src.config.settings import settings
from src.domain.enums import AttributionTouchpointType, CustomerCommercialBindingType
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.attribution_touchpoint_model import AttributionTouchpointModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.billing_descriptor_model import BillingDescriptorModel
from src.infrastructure.database.models.brand_model import BrandModel
from src.infrastructure.database.models.checkout_session_model import CheckoutSessionModel
from src.infrastructure.database.models.customer_commercial_binding_model import CustomerCommercialBindingModel
from src.infrastructure.database.models.growth_code_model import GrowthCodeReservationModel
from src.infrastructure.database.models.invoice_profile_model import InvoiceProfileModel
from src.infrastructure.database.models.legal_document_model import LegalDocumentModel
from src.infrastructure.database.models.legal_document_set_model import (
    LegalDocumentSetItemModel,
    LegalDocumentSetModel,
)
from src.infrastructure.database.models.merchant_profile_model import MerchantProfileModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.offer_model import OfferModel
from src.infrastructure.database.models.outbox_event_model import OutboxEventModel
from src.infrastructure.database.models.partner_attribution_session_model import PartnerAttributionSessionModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeModel
from src.infrastructure.database.models.policy_version_model import PolicyVersionModel
from src.infrastructure.database.models.pricebook_model import PricebookEntryModel, PricebookModel
from src.infrastructure.database.models.program_eligibility_policy_model import ProgramEligibilityPolicyModel
from src.infrastructure.database.models.promo_code_model import PromoCodeModel
from src.infrastructure.database.models.quote_session_model import QuoteSessionModel
from src.infrastructure.database.models.storefront_model import StorefrontModel
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
from src.infrastructure.database.repositories.partner_attribution_session_repo import (
    PartnerAttributionSessionRepository,
)
from src.main import app
from src.presentation.dependencies.database import get_db
from tests.helpers.realm_auth import (
    FakeRedis,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)
from tests.integration.test_partner_commission_contracts_migration_postgres import (
    _create_database,
    _database_url,
    _drop_database,
    _run_alembic,
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


def _seed_partner_attribution_cookie(
    sessionmaker,
    *,
    seeded: dict[str, str],
    cookie_token: str,
    expires_at: datetime | None = None,
    markup_pct: int = 10,
) -> dict[str, str]:
    now = datetime.now(UTC)
    suffix = uuid.uuid4().hex[:10].upper()
    with sessionmaker() as db:
        partner_owner = MobileUserModel(
            id=uuid.uuid4(),
            auth_realm_id=uuid.UUID(seeded["customer_realm_id"]),
            email=f"partner-{suffix.lower()}@partner.example.test",
            password_hash="hashed-partner-password",
            is_active=True,
            status="active",
        )
        account = PartnerAccountModel(
            id=uuid.uuid4(),
            account_key=f"quote-attr-{suffix.lower()}",
            display_name="Quote Attribution Partner",
            status="active",
            legacy_owner_user_id=partner_owner.id,
        )
        code = PartnerCodeModel(
            id=uuid.uuid4(),
            code=f"QA{suffix[:8]}",
            code_normalized=f"QA{suffix[:8]}",
            public_token_hash=hash_partner_attribution_token(f"quote-attr-{suffix.lower()}"),
            partner_account_id=account.id,
            partner_user_id=partner_owner.id,
            markup_pct=markup_pct,
            is_active=True,
            lifecycle_status="active",
            approval_status="approved",
            owner_type="affiliate",
            lane_key="creator_affiliate",
            attribution_model="last_eligible_touch",
            attribution_window_seconds=30 * 24 * 60 * 60,
            default_storefront_id=uuid.UUID(seeded["storefront_id"]),
            allowed_channels=["web"],
            allowed_storefront_ids=[seeded["storefront_id"]],
            allowed_geographies=["*"],
            sub_id_schema={},
        )
        attribution = PartnerAttributionSessionModel(
            id=uuid.uuid4(),
            session_token_hash=hash_partner_attribution_token(cookie_token),
            transfer_token_hash=None,
            consumed_transfer_token_hash=hash_partner_attribution_token(f"consumed-{cookie_token}"),
            transfer_expires_at=now + timedelta(minutes=10),
            transfer_consumed_at=now,
            partner_code_id=code.id,
            partner_account_id=account.id,
            auth_realm_id=uuid.UUID(seeded["customer_realm_id"]),
            storefront_id=uuid.UUID(seeded["storefront_id"]),
            status="transferred",
            owner_type="affiliate",
            attribution_model="last_eligible_touch",
            source_host="partner.example.test",
            source_path="/p/quote-attribution",
            destination_path="/pricing",
            locale="ru-RU",
            sale_channel="web",
            sub_ids={"creator": "quote-safety-net"},
            click_id="quote-safety-click",
            destination_url="https://my.cyber-vpn.net/ru-RU/pricing",
            campaign_params={"utm_source": "quote_safety_net"},
            evidence_payload={"source": "test_cookie_seed"},
            policy_snapshot={"allowed": True, "reason_codes": []},
            expires_at=expires_at or now + timedelta(days=30),
            first_seen_at=now,
            last_seen_at=now,
            transferred_at=now,
        )
        db.add_all([partner_owner, account, code, attribution])
        db.commit()
        return {
            "partner_owner_id": str(partner_owner.id),
            "partner_account_id": str(account.id),
            "partner_code_id": str(code.id),
            "attribution_session_id": str(attribution.id),
        }


async def _seed_postgres_quote_context(
    maker: async_sessionmaker[AsyncSession],
    auth_service: AuthService,
) -> dict[str, str]:
    now = datetime.now(UTC) - timedelta(minutes=5)
    suffix = uuid.uuid4().hex[:12]

    customer_realm = AuthRealmModel(
        id=uuid.uuid4(),
        realm_key=f"pg-customer-{suffix}",
        realm_type="customer",
        display_name="PG Customer Realm",
        audience=f"cybervpn:pg-customer:{suffix}",
        cookie_namespace=f"pgcust{suffix}",
        status="active",
        is_default=True,
    )
    brand = BrandModel(
        id=uuid.uuid4(),
        brand_key=f"pg-partner-brand-{suffix}",
        display_name="PG Partner Brand",
        status="active",
    )
    invoice_profile = InvoiceProfileModel(
        id=uuid.uuid4(),
        profile_key=f"pg-partner-invoice-{suffix}",
        display_name="PG Partner Invoice",
        issuer_legal_name="PG Partner Invoice Ltd",
        tax_identifier=f"PG{suffix.upper()}",
        issuer_email=f"billing-{suffix}@partner.example.test",
        tax_behavior={"pricing_mode": "tax_inclusive"},
        invoice_footer="Thank you",
        receipt_footer="Paid",
        status="active",
    )
    merchant_profile = MerchantProfileModel(
        id=uuid.uuid4(),
        profile_key=f"pg-partner-merchant-{suffix}",
        legal_entity_name="PG Partner Merchant Ltd",
        billing_descriptor="PGPARTNERVPN",
        invoice_profile_id=invoice_profile.id,
        settlement_reference=f"stripe-pg-partner-{suffix}",
        supported_currencies=["USD"],
        tax_behavior={"pricing_mode": "tax_inclusive"},
        refund_responsibility_model="merchant_of_record",
        chargeback_liability_model="merchant_of_record",
        status="active",
    )
    billing_descriptor = BillingDescriptorModel(
        id=uuid.uuid4(),
        descriptor_key=f"pg-partner-default-{suffix}",
        merchant_profile_id=merchant_profile.id,
        invoice_profile_id=invoice_profile.id,
        statement_descriptor="PG PARTNER VPN",
        soft_descriptor="PG*VPN",
        support_phone="+44-20-5555-0100",
        support_url="https://support.partner.example.test",
        is_default=True,
        status="active",
    )
    storefront = StorefrontModel(
        id=uuid.uuid4(),
        storefront_key=f"pg-partner-web-{suffix}",
        brand_id=brand.id,
        display_name="PG Partner Web",
        host=f"pg-partner-{suffix}.example.test",
        merchant_profile_id=merchant_profile.id,
        auth_realm_id=customer_realm.id,
        status="active",
    )
    customer_user = MobileUserModel(
        id=uuid.uuid4(),
        auth_realm_id=customer_realm.id,
        email=f"pg-customer-{suffix}@partner.example.test",
        password_hash=await auth_service.hash_password("CustomerPhase2Password123!"),
        is_active=True,
        status="active",
    )
    plan = SubscriptionPlanModel(
        id=uuid.uuid4(),
        name=f"pg_partner_365d_{suffix}",
        plan_code="pro",
        display_name="PG Partner 365D",
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
        offer_key=f"pg-partner-365-offer-{suffix}",
        display_name="PG Partner 365 Offer",
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
        pricebook_key=f"pg-partner-usd-{suffix}",
        display_name="PG Partner USD",
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
        policy_key=f"pg-partner-offer-eligibility-{suffix}",
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
        policy_key=f"pg-partner-terms-doc-{suffix}",
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
        policy_key=f"pg-partner-terms-set-{suffix}",
        subject_type="legal_document_set",
        version_number=1,
        payload={},
        approval_state="approved",
        version_status="active",
        effective_from=now,
    )
    legal_document = LegalDocumentModel(
        id=uuid.uuid4(),
        document_key=f"pg-partner-terms-{suffix}",
        document_type="terms_of_service",
        locale="en-EN",
        title="PG Partner Terms",
        content_markdown="# Terms",
        content_checksum=f"checksum-pg-partner-terms-{suffix}",
        policy_version_id=legal_doc_policy.id,
    )
    legal_document_set = LegalDocumentSetModel(
        id=uuid.uuid4(),
        set_key=f"pg-partner-web-terms-{suffix}",
        storefront_id=storefront.id,
        auth_realm_id=customer_realm.id,
        display_name="PG Partner Web Terms",
        policy_version_id=legal_set_policy.id,
    )
    legal_document_set_item = LegalDocumentSetItemModel(
        id=uuid.uuid4(),
        legal_document_set_id=legal_document_set.id,
        legal_document_id=legal_document.id,
        required=True,
        display_order=0,
    )

    async with maker() as session:
        session.add_all(
            [
                customer_realm,
                brand,
                invoice_profile,
                plan,
                legal_doc_policy,
                legal_set_policy,
            ]
        )
        await session.flush()

        session.add_all(
            [
                merchant_profile,
                customer_user,
                offer,
            ]
        )
        await session.flush()

        session.add_all(
            [
                billing_descriptor,
                storefront,
            ]
        )
        await session.flush()

        session.add_all(
            [
                pricebook,
                program_eligibility,
                legal_document,
            ]
        )
        await session.flush()

        session.add_all(
            [
                pricebook_entry,
                legal_document_set,
            ]
        )
        await session.flush()

        session.add_all(
            [
                legal_document_set_item,
            ]
        )
        await session.commit()

    return {
        "customer_realm_id": str(customer_realm.id),
        "customer_realm_key": customer_realm.realm_key,
        "customer_realm_audience": customer_realm.audience,
        "customer_user_id": str(customer_user.id),
        "storefront_key": storefront.storefront_key,
        "storefront_host": storefront.host,
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


async def _seed_postgres_partner_attribution_cookie(
    maker: async_sessionmaker[AsyncSession],
    *,
    seeded: dict[str, str],
    cookie_token: str,
    markup_pct: int = 10,
) -> dict[str, str]:
    now = datetime.now(UTC)
    suffix = uuid.uuid4().hex[:10].upper()
    partner_owner = MobileUserModel(
        id=uuid.uuid4(),
        auth_realm_id=uuid.UUID(seeded["customer_realm_id"]),
        email=f"pg-partner-{suffix.lower()}@partner.example.test",
        password_hash="hashed-partner-password",
        is_active=True,
        status="active",
    )
    account = PartnerAccountModel(
        id=uuid.uuid4(),
        account_key=f"pg-quote-attr-{suffix.lower()}",
        display_name="PG Quote Attribution Partner",
        status="active",
        legacy_owner_user_id=partner_owner.id,
    )
    code = PartnerCodeModel(
        id=uuid.uuid4(),
        code=f"PGQA{suffix[:8]}",
        code_normalized=f"PGQA{suffix[:8]}",
        public_slug=f"pg-quote-attr-{suffix.lower()}",
        public_token_hash=hash_partner_attribution_token(f"pg-quote-attr-{suffix.lower()}"),
        partner_account_id=account.id,
        partner_user_id=partner_owner.id,
        markup_pct=markup_pct,
        is_active=True,
        lifecycle_status="active",
        approval_status="approved",
        owner_type="affiliate",
        lane_key="creator_affiliate",
        attribution_model="last_eligible_touch",
        attribution_window_seconds=30 * 24 * 60 * 60,
        default_storefront_id=uuid.UUID(seeded["storefront_id"]),
        allowed_channels=["web"],
        allowed_storefront_ids=[seeded["storefront_id"]],
        allowed_geographies=["*"],
        sub_id_schema={},
    )
    attribution = PartnerAttributionSessionModel(
        id=uuid.uuid4(),
        session_token_hash=hash_partner_attribution_token(cookie_token),
        transfer_token_hash=None,
        consumed_transfer_token_hash=hash_partner_attribution_token(f"consumed-{cookie_token}"),
        transfer_expires_at=now + timedelta(minutes=10),
        transfer_consumed_at=now,
        partner_code_id=code.id,
        partner_account_id=account.id,
        auth_realm_id=uuid.UUID(seeded["customer_realm_id"]),
        storefront_id=uuid.UUID(seeded["storefront_id"]),
        status="transferred",
        owner_type="affiliate",
        attribution_model="last_eligible_touch",
        source_host="partner.example.test",
        source_path="/p/pg-quote-attribution",
        destination_path="/pricing",
        locale="ru-RU",
        sale_channel="web",
        sub_ids={"creator": "pg-quote-safety-net"},
        click_id="pg-quote-safety-click",
        destination_url="https://my.cyber-vpn.net/ru-RU/pricing",
        campaign_params={"utm_source": "pg_quote_safety_net"},
        evidence_payload={"source": "postgres_route_race_seed"},
        policy_snapshot={"allowed": True, "reason_codes": []},
        expires_at=now + timedelta(days=30),
        first_seen_at=now,
        last_seen_at=now,
        transferred_at=now,
    )
    async with maker() as session:
        session.add(partner_owner)
        await session.flush()
        session.add(account)
        await session.flush()
        session.add(code)
        await session.flush()
        session.add(attribution)
        await session.commit()
    return {
        "partner_owner_id": str(partner_owner.id),
        "partner_account_id": str(account.id),
        "partner_code_id": str(code.id),
        "attribution_session_id": str(attribution.id),
    }


def _seed_foreign_partner_attribution_cookie(
    sessionmaker,
    *,
    seeded: dict[str, str],
    cookie_token: str,
    with_foreign_storefront: bool,
) -> dict[str, str]:
    now = datetime.now(UTC)
    suffix = uuid.uuid4().hex[:10].upper()
    with sessionmaker() as db:
        current_storefront = db.get(StorefrontModel, uuid.UUID(seeded["storefront_id"]))
        assert current_storefront is not None
        foreign_realm = AuthRealmModel(
            id=uuid.uuid4(),
            realm_key=f"foreign-{suffix.lower()}",
            realm_type="customer",
            display_name="Foreign Customer Realm",
            audience=f"cybervpn:foreign:{suffix.lower()}",
            cookie_namespace=f"foreign-{suffix.lower()}",
            status="active",
            is_default=False,
        )
        foreign_storefront = None
        if with_foreign_storefront:
            foreign_storefront = StorefrontModel(
                id=uuid.uuid4(),
                storefront_key=f"foreign-web-{suffix.lower()}",
                brand_id=current_storefront.brand_id,
                display_name="Foreign Web",
                host=f"foreign-{suffix.lower()}.example.test",
                merchant_profile_id=current_storefront.merchant_profile_id,
                auth_realm_id=foreign_realm.id,
                status="active",
            )
        partner_owner = MobileUserModel(
            id=uuid.uuid4(),
            auth_realm_id=foreign_realm.id,
            email=f"foreign-partner-{suffix.lower()}@partner.example.test",
            password_hash="hashed-partner-password",
            is_active=True,
            status="active",
        )
        account = PartnerAccountModel(
            id=uuid.uuid4(),
            account_key=f"foreign-attr-{suffix.lower()}",
            display_name="Foreign Attribution Partner",
            status="active",
            legacy_owner_user_id=partner_owner.id,
        )
        storefront_id = foreign_storefront.id if foreign_storefront is not None else None
        code = PartnerCodeModel(
            id=uuid.uuid4(),
            code=f"FA{suffix[:8]}",
            code_normalized=f"FA{suffix[:8]}",
            public_token_hash=hash_partner_attribution_token(f"foreign-attr-{suffix.lower()}"),
            partner_account_id=account.id,
            partner_user_id=partner_owner.id,
            markup_pct=10,
            is_active=True,
            lifecycle_status="active",
            approval_status="approved",
            owner_type="affiliate",
            lane_key="creator_affiliate",
            attribution_model="last_eligible_touch",
            attribution_window_seconds=30 * 24 * 60 * 60,
            default_storefront_id=storefront_id,
            allowed_channels=["web"],
            allowed_storefront_ids=[str(storefront_id)] if storefront_id is not None else ["*"],
            allowed_geographies=["*"],
            sub_id_schema={},
        )
        attribution = PartnerAttributionSessionModel(
            id=uuid.uuid4(),
            session_token_hash=hash_partner_attribution_token(cookie_token),
            transfer_token_hash=None,
            consumed_transfer_token_hash=hash_partner_attribution_token(f"consumed-{cookie_token}"),
            transfer_expires_at=now + timedelta(minutes=10),
            transfer_consumed_at=now,
            partner_code_id=code.id,
            partner_account_id=account.id,
            auth_realm_id=foreign_realm.id,
            storefront_id=storefront_id,
            status="transferred",
            owner_type="affiliate",
            attribution_model="last_eligible_touch",
            source_host="foreign.example.test",
            source_path="/p/foreign-attribution",
            destination_path="/pricing",
            locale="ru-RU",
            sale_channel="web",
            sub_ids={"creator": "foreign"},
            click_id="foreign-click",
            destination_url="https://foreign.example.test/ru-RU/pricing",
            campaign_params={"utm_source": "foreign"},
            evidence_payload={"source": "test_foreign_cookie_seed"},
            policy_snapshot={"allowed": True, "reason_codes": []},
            expires_at=now + timedelta(days=30),
            first_seen_at=now,
            last_seen_at=now,
            transferred_at=now,
        )
        models = [foreign_realm, partner_owner, account, code, attribution]
        if foreign_storefront is not None:
            models.insert(1, foreign_storefront)
        db.add_all(models)
        db.commit()
        return {
            "foreign_realm_id": str(foreign_realm.id),
            "partner_account_id": str(account.id),
            "partner_code_id": str(code.id),
            "attribution_session_id": str(attribution.id),
            "storefront_id": str(storefront_id) if storefront_id is not None else "",
        }


def _assert_attribution_cookie_deleted(response) -> None:
    set_cookie_headers = response.headers.get_list("set-cookie")
    attribution_headers = [
        header for header in set_cookie_headers if header.startswith(f"{PARTNER_ATTRIBUTION_COOKIE_NAME}=")
    ]
    assert attribution_headers
    deleted_header = attribution_headers[-1].lower()
    assert "max-age=0" in deleted_header
    assert "path=/" in deleted_header
    assert "httponly" in deleted_header
    assert "secure" in deleted_header
    assert "samesite=lax" in deleted_header
    assert response.headers.get("cache-control") == "no-store"


@pytest.mark.asyncio
async def test_legacy_payment_commit_is_disabled_and_quote_uses_pricebook_amount(
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
            access_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Auth-Realm": "customer",
            }
            legacy_body = {
                "plan_id": seeded["plan_id"],
                "currency": "USD",
                "channel": "web",
                "use_wallet": 0,
                "addons": [],
            }

            missing_key_response = await async_client.post(
                "/api/v1/payments/checkout/commit",
                headers=headers,
                json=legacy_body,
            )
            assert missing_key_response.status_code == 422

            legacy_response = await async_client.post(
                "/api/v1/payments/checkout/commit",
                headers={**headers, "Idempotency-Key": "legacy-disabled-1"},
                json=legacy_body,
            )
            assert legacy_response.status_code == 410
            assert "disabled" in legacy_response.json()["detail"]

            alias_response = await async_client.post(
                "/api/v1/payments/checkout",
                headers={**headers, "Idempotency-Key": "legacy-disabled-alias-1"},
                json=legacy_body,
            )
            assert alias_response.status_code == 410

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
            assert quote_payload["quote"]["base_price"] == 75.0
            assert quote_payload["quote"]["displayed_price"] == 75.0
            assert quote_payload["quote"]["gateway_amount"] == 75.0
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_quote_session_rejects_pricebook_currency_mismatch(async_client: AsyncClient) -> None:
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

            response = await async_client.post(
                "/api/v1/quotes/",
                headers=headers,
                json={
                    "storefront_key": seeded["storefront_key"],
                    "pricebook_key": seeded["pricebook_key"],
                    "offer_key": seeded["offer_key"],
                    "plan_id": seeded["plan_id"],
                    "currency": "EUR",
                    "channel": "web",
                    "use_wallet": 0,
                    "addons": [],
                },
            )
            assert response.status_code == 400
            assert "currency" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


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
            assert quote_payload["quote"]["base_price"] == 75.0
            assert quote_payload["quote"]["displayed_price"] == 75.0
            assert quote_payload["quote"]["gateway_amount"] == 75.0

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
            assert checkout_payload["quote"]["base_price"] == 75.0
            assert checkout_payload["quote"]["gateway_amount"] == 75.0

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
async def test_quote_session_claims_partner_attribution_cookie_and_snapshots_owner(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "partner_attribution_enabled", True)
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
            cookie_token = "quote-cookie-only-token"
            attribution_ids = _seed_partner_attribution_cookie(
                sessionmaker,
                seeded=seeded,
                cookie_token=cookie_token,
            )
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
                headers={
                    **headers,
                    "Cookie": f"{PARTNER_ATTRIBUTION_COOKIE_NAME}={cookie_token}",
                    "X-Forwarded-Host": "evil.example.test",
                },
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
            _assert_attribution_cookie_deleted(quote_response)
            quote_payload = quote_response.json()
            assert quote_payload["quote"]["partner_markup"] == 7.5
            assert "partner_attribution" not in quote_payload["quote"]

            quote_id = uuid.UUID(quote_payload["id"])
            attribution_session_id = uuid.UUID(attribution_ids["attribution_session_id"])
            with sessionmaker() as db:
                attribution = db.get(PartnerAttributionSessionModel, attribution_session_id)
                assert attribution is not None
                assert attribution.status == "claimed"
                assert attribution.user_id == uuid.UUID(seeded["customer_user_id"])
                assert attribution.binding_id is not None
                binding = db.get(CustomerCommercialBindingModel, attribution.binding_id)
                assert binding is not None
                assert binding.binding_type == CustomerCommercialBindingType.PARTNER_ATTRIBUTION.value
                assert binding.partner_account_id == uuid.UUID(attribution_ids["partner_account_id"])
                assert binding.partner_code_id == uuid.UUID(attribution_ids["partner_code_id"])
                assert binding.attribution_session_id == attribution_session_id
                linked_touchpoints = (
                    db.query(AttributionTouchpointModel)
                    .filter(
                        AttributionTouchpointModel.quote_session_id == quote_id,
                        AttributionTouchpointModel.partner_attribution_session_id == attribution_session_id,
                        AttributionTouchpointModel.touchpoint_type == AttributionTouchpointType.PARTNER_CLAIM.value,
                    )
                    .all()
                )
                assert len(linked_touchpoints) == 1
                assert linked_touchpoints[0].source_host == "partner.example.test"
                quote_session = db.get(QuoteSessionModel, quote_id)
                assert quote_session is not None
                snapshot = quote_session.quote_snapshot["partner_attribution"]
                assert snapshot["source"] == "server_side_quote_safety_net"
                assert snapshot["status"] == "already_claimed"
                assert snapshot["attribution_session_id"] == str(attribution_session_id)
                binding_id = str(binding.id)
                assert snapshot["binding_id"] == binding_id
                assert snapshot["quote_touchpoint_id"] == str(linked_touchpoints[0].id)
                assert cookie_token not in str(snapshot)

            checkout_response = await async_client.post(
                "/api/v1/checkout-sessions/",
                headers={**headers, "Idempotency-Key": "quote-attr-checkout-1"},
                json={"quote_session_id": quote_payload["id"]},
            )
            assert checkout_response.status_code == 201
            checkout_payload = checkout_response.json()
            assert checkout_payload["quote"]["partner_markup"] == 7.5

            with sessionmaker() as db:
                checkout = db.get(CheckoutSessionModel, uuid.UUID(checkout_payload["id"]))
                assert checkout is not None
                checkout_snapshot = checkout.checkout_snapshot["quote_snapshot"]["partner_attribution"]
                assert checkout_snapshot["binding_id"] == binding_id
                assert checkout_snapshot["attribution_session_id"] == str(attribution_session_id)
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_concurrent_quote_and_claim_share_single_partner_attribution_owner(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "partner_attribution_enabled", True)
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
            cookie_token = "concurrent-quote-claim-cookie-token"
            attribution_ids = _seed_partner_attribution_cookie(
                sessionmaker,
                seeded=seeded,
                cookie_token=cookie_token,
                markup_pct=6,
            )
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
                "Cookie": f"{PARTNER_ATTRIBUTION_COOKIE_NAME}={cookie_token}",
            }

            async def create_quote():
                return await async_client.post(
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

            async def claim_attribution():
                return await async_client.post(
                    "/api/v1/partner-attribution/claim",
                    headers=headers,
                    json={},
                )

            quote_response, claim_response = await asyncio.gather(create_quote(), claim_attribution())
            assert quote_response.status_code == 201, quote_response.text
            assert claim_response.status_code == 200, claim_response.text
            assert claim_response.json()["status"] in {"claimed", "already_claimed"}
            _assert_attribution_cookie_deleted(quote_response)

            quote_id = uuid.UUID(quote_response.json()["id"])
            attribution_session_id = uuid.UUID(attribution_ids["attribution_session_id"])
            with sessionmaker() as db:
                attribution = db.get(PartnerAttributionSessionModel, attribution_session_id)
                assert attribution is not None
                assert attribution.status == "claimed"
                assert attribution.binding_id is not None
                binding_count = (
                    db.query(CustomerCommercialBindingModel)
                    .filter(CustomerCommercialBindingModel.attribution_session_id == attribution_session_id)
                    .count()
                )
                assert binding_count == 1
                linked_touchpoints = (
                    db.query(AttributionTouchpointModel)
                    .filter(
                        AttributionTouchpointModel.quote_session_id == quote_id,
                        AttributionTouchpointModel.partner_attribution_session_id == attribution_session_id,
                        AttributionTouchpointModel.touchpoint_type == AttributionTouchpointType.PARTNER_CLAIM.value,
                    )
                    .all()
                )
                assert len(linked_touchpoints) == 1
                quote_session = db.get(QuoteSessionModel, quote_id)
                assert quote_session is not None
                snapshot = quote_session.quote_snapshot["partner_attribution"]
                assert snapshot["binding_id"] == str(attribution.binding_id)
                assert snapshot["quote_touchpoint_id"] == str(linked_touchpoints[0].id)
                assert cookie_token not in str(snapshot)
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_postgres_concurrent_quote_and_claim_routes_share_single_pending_attribution(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "partner_attribution_enabled", True)
    database_name = f"cvpn_quote_claim_race_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    engine = None

    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        engine = create_async_engine(url, pool_pre_ping=True)
        maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async def _override_db():
            async with maker() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        fake_redis = FakeRedis()

        async def _override_redis():
            yield fake_redis

        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_redis] = _override_redis

        auth_service = AuthService()
        seeded = await _seed_postgres_quote_context(maker, auth_service)
        cookie_token = f"pg-quote-claim-cookie-{uuid.uuid4()}"
        attribution_ids = await _seed_postgres_partner_attribution_cookie(
            maker,
            seeded=seeded,
            cookie_token=cookie_token,
            markup_pct=10,
        )
        customer_realm = AuthRealmModel(
            id=uuid.UUID(seeded["customer_realm_id"]),
            realm_key=seeded["customer_realm_key"],
            realm_type="customer",
            display_name="PG Customer Realm",
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
            "X-Auth-Realm": seeded["customer_realm_key"],
            "Host": seeded["storefront_host"],
            "Cookie": f"{PARTNER_ATTRIBUTION_COOKIE_NAME}={cookie_token}",
        }
        quote_body = {
            "storefront_key": seeded["storefront_key"],
            "pricebook_key": seeded["pricebook_key"],
            "offer_key": seeded["offer_key"],
            "plan_id": seeded["plan_id"],
            "currency": "USD",
            "channel": "web",
            "use_wallet": 0,
            "addons": [],
        }

        cookie_hash = hash_partner_attribution_token(cookie_token)
        claim_readers_ready = asyncio.Event()
        claim_reader_count = 0
        claim_reader_lock = asyncio.Lock()
        original_get_by_session_token_hash = PartnerAttributionSessionRepository.get_by_session_token_hash

        async def synchronized_get_by_session_token_hash(
            self: PartnerAttributionSessionRepository,
            session_token_hash: str,
            *,
            auth_realm_id: uuid.UUID | None = None,
            for_update: bool = False,
        ) -> PartnerAttributionSessionModel | None:
            nonlocal claim_reader_count
            if session_token_hash == cookie_hash and for_update:
                async with claim_reader_lock:
                    claim_reader_count += 1
                    if claim_reader_count == 2:
                        claim_readers_ready.set()
                await asyncio.wait_for(claim_readers_ready.wait(), timeout=5)
            return await original_get_by_session_token_hash(
                self,
                session_token_hash,
                auth_realm_id=auth_realm_id,
                for_update=for_update,
            )

        monkeypatch.setattr(
            PartnerAttributionSessionRepository,
            "get_by_session_token_hash",
            synchronized_get_by_session_token_hash,
        )

        route_start = asyncio.Event()

        async def create_quote():
            await route_start.wait()
            return await async_client.post("/api/v1/quotes/", headers=headers, json=quote_body)

        async def claim_attribution():
            await route_start.wait()
            return await async_client.post("/api/v1/partner-attribution/claim", headers=headers, json={})

        quote_task = asyncio.create_task(create_quote())
        claim_task = asyncio.create_task(claim_attribution())
        await asyncio.sleep(0)
        route_start.set()
        quote_response, claim_response = await asyncio.wait_for(
            asyncio.gather(quote_task, claim_task),
            timeout=20,
        )

        assert claim_reader_count >= 2
        assert quote_response.status_code == 201, quote_response.text
        assert claim_response.status_code == 200, claim_response.text
        _assert_attribution_cookie_deleted(quote_response)
        assert claim_response.headers["cache-control"] == "no-store"

        quote_payload = quote_response.json()
        claim_payload = claim_response.json()
        assert quote_payload["quote"]["partner_markup"] == 7.5
        assert quote_payload["quote"]["partner_code_id"] == attribution_ids["partner_code_id"]
        assert claim_payload["status"] in {"claimed", "already_claimed"}
        assert claim_payload["partner_account_id"] == attribution_ids["partner_account_id"]
        assert claim_payload["partner_code_id"] == attribution_ids["partner_code_id"]

        quote_id = uuid.UUID(quote_payload["id"])
        customer_id = uuid.UUID(seeded["customer_user_id"])
        attribution_session_id = uuid.UUID(attribution_ids["attribution_session_id"])
        async with maker() as session:
            attribution = await session.get(PartnerAttributionSessionModel, attribution_session_id)
            assert attribution is not None
            assert attribution.status == "claimed"
            assert attribution.user_id == customer_id
            assert attribution.binding_id is not None
            assert attribution.claimed_at is not None
            assert claim_payload["binding_id"] == str(attribution.binding_id)

            binding = await session.get(CustomerCommercialBindingModel, attribution.binding_id)
            assert binding is not None
            assert binding.binding_type == CustomerCommercialBindingType.PARTNER_ATTRIBUTION.value
            assert binding.user_id == customer_id
            assert binding.partner_account_id == uuid.UUID(attribution_ids["partner_account_id"])
            assert binding.partner_code_id == uuid.UUID(attribution_ids["partner_code_id"])
            assert binding.attribution_session_id == attribution_session_id
            assert binding.claimed_at is not None

            binding_count = await session.scalar(
                select(func.count())
                .select_from(CustomerCommercialBindingModel)
                .where(CustomerCommercialBindingModel.attribution_session_id == attribution_session_id)
            )
            active_owner_count = await session.scalar(
                select(func.count())
                .select_from(CustomerCommercialBindingModel)
                .where(
                    CustomerCommercialBindingModel.user_id == customer_id,
                    CustomerCommercialBindingModel.auth_realm_id == uuid.UUID(seeded["customer_realm_id"]),
                    CustomerCommercialBindingModel.storefront_id == uuid.UUID(seeded["storefront_id"]),
                    CustomerCommercialBindingModel.binding_status == "active",
                    CustomerCommercialBindingModel.binding_type
                    == CustomerCommercialBindingType.PARTNER_ATTRIBUTION.value,
                )
            )
            assert binding_count == 1
            assert active_owner_count == 1

            claim_key = f"partner-claim:{attribution_session_id}:{customer_id}"
            quote_key = f"partner-quote-claim:{attribution_session_id}:{quote_id}"
            partner_claim_touchpoints = (
                (
                    await session.execute(
                        select(AttributionTouchpointModel)
                        .where(
                            AttributionTouchpointModel.partner_attribution_session_id == attribution_session_id,
                            AttributionTouchpointModel.touchpoint_type == AttributionTouchpointType.PARTNER_CLAIM.value,
                        )
                        .order_by(AttributionTouchpointModel.created_at.asc())
                    )
                )
                .scalars()
                .all()
            )
            assert len(partner_claim_touchpoints) == 2
            touchpoints_by_key = {touchpoint.idempotency_key: touchpoint for touchpoint in partner_claim_touchpoints}
            assert set(touchpoints_by_key) == {claim_key, quote_key}
            assert touchpoints_by_key[claim_key].quote_session_id is None
            assert touchpoints_by_key[claim_key].checkout_session_id is None
            assert touchpoints_by_key[quote_key].quote_session_id == quote_id
            assert touchpoints_by_key[quote_key].checkout_session_id is None
            assert attribution.touchpoint_id == touchpoints_by_key[claim_key].id

            claimed_event_count = await session.scalar(
                select(func.count())
                .select_from(OutboxEventModel)
                .where(
                    OutboxEventModel.event_name == "partner.attribution.claimed",
                    OutboxEventModel.aggregate_id == str(attribution_session_id),
                )
            )
            assert claimed_event_count == 1

            quote_session = await session.get(QuoteSessionModel, quote_id)
            assert quote_session is not None
            snapshot = quote_session.quote_snapshot["partner_attribution"]
            assert snapshot["status"] in {"claimed", "already_claimed"}
            assert snapshot["binding_id"] == str(binding.id)
            assert snapshot["attribution_session_id"] == str(attribution_session_id)
            assert snapshot["partner_account_id"] == attribution_ids["partner_account_id"]
            assert snapshot["partner_code_id"] == attribution_ids["partner_code_id"]
            assert snapshot["claim_touchpoint_id"] == str(touchpoints_by_key[claim_key].id)
            assert snapshot["quote_touchpoint_id"] == str(touchpoints_by_key[quote_key].id)
            assert cookie_token not in str(snapshot)
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_redis, None)
        if engine is not None:
            await engine.dispose()
        await _drop_database(database_name)


@pytest.mark.asyncio
async def test_transfer_consume_then_immediate_quote_claims_server_side_cookie(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "partner_attribution_enabled", True)
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
            transfer_token = "transfer-immediate-quote-token"
            seed_cookie_token = "placeholder-cookie-before-transfer"
            attribution_ids = _seed_partner_attribution_cookie(
                sessionmaker,
                seeded=seeded,
                cookie_token=seed_cookie_token,
                markup_pct=9,
            )
            attribution_session_id = uuid.UUID(attribution_ids["attribution_session_id"])
            with sessionmaker() as db:
                attribution = db.get(PartnerAttributionSessionModel, attribution_session_id)
                assert attribution is not None
                attribution.status = "pending"
                attribution.session_token_hash = None
                attribution.transfer_token_hash = hash_partner_attribution_token(transfer_token)
                attribution.consumed_transfer_token_hash = None
                attribution.transfer_consumed_at = None
                db.commit()

            transfer_response = await async_client.post(
                "/api/v1/partner-attribution/transfer/consume",
                json={"transfer_token": transfer_token},
            )
            assert transfer_response.status_code == 200, transfer_response.text
            cookie_token = transfer_response.cookies.get(PARTNER_ATTRIBUTION_COOKIE_NAME)
            assert cookie_token

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
            quote_response = await async_client.post(
                "/api/v1/quotes/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Auth-Realm": "customer",
                    "Cookie": f"{PARTNER_ATTRIBUTION_COOKIE_NAME}={cookie_token}",
                },
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
            assert quote_response.status_code == 201, quote_response.text
            _assert_attribution_cookie_deleted(quote_response)
            quote_payload = quote_response.json()
            assert quote_payload["quote"]["partner_markup"] == 6.75

            quote_id = uuid.UUID(quote_payload["id"])
            with sessionmaker() as db:
                attribution = db.get(PartnerAttributionSessionModel, attribution_session_id)
                assert attribution is not None
                assert attribution.status == "claimed"
                assert attribution.transfer_token_hash is None
                assert attribution.consumed_transfer_token_hash == hash_partner_attribution_token(transfer_token)
                quote_session = db.get(QuoteSessionModel, quote_id)
                assert quote_session is not None
                snapshot = quote_session.quote_snapshot["partner_attribution"]
                assert snapshot["attribution_session_id"] == str(attribution_session_id)
                assert snapshot["binding_id"] == str(attribution.binding_id)
                assert cookie_token not in str(snapshot)
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_quote_partner_attribution_retryable_failure_rolls_back_quote(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "partner_attribution_enabled", True)
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    async def fail_claim(*_args, **_kwargs):
        raise RuntimeError("simulated transient attribution failure")

    app.dependency_overrides[get_redis] = _override_redis
    monkeypatch.setattr(EnsurePendingPartnerAttributionClaimedUseCase, "execute", fail_claim)

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_quote_context(sessionmaker, auth_service)
            cookie_token = "retryable-quote-cookie-token"
            _seed_partner_attribution_cookie(
                sessionmaker,
                seeded=seeded,
                cookie_token=cookie_token,
            )
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
            quote_response = await async_client.post(
                "/api/v1/quotes/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Auth-Realm": "customer",
                    "Cookie": f"{PARTNER_ATTRIBUTION_COOKIE_NAME}={cookie_token}",
                },
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
            assert quote_response.status_code == 503
            detail = quote_response.json()["detail"]
            assert detail["code"] == "PARTNER_ATTRIBUTION_TRANSIENT_FAILURE"
            assert detail["retryable"] is True
            assert quote_response.headers["cache-control"] == "no-store"
            with sessionmaker() as db:
                assert db.query(QuoteSessionModel).count() == 0
                assert db.query(CustomerCommercialBindingModel).count() == 0
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_self_attribution_cookie_is_ignored_and_does_not_create_quote_owner(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "partner_attribution_enabled", True)
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
            cookie_token = "self-attribution-cookie-token"
            attribution_ids = _seed_partner_attribution_cookie(
                sessionmaker,
                seeded=seeded,
                cookie_token=cookie_token,
            )
            customer_user_id = uuid.UUID(seeded["customer_user_id"])
            with sessionmaker() as db:
                code = db.get(PartnerCodeModel, uuid.UUID(attribution_ids["partner_code_id"]))
                account = db.get(PartnerAccountModel, uuid.UUID(attribution_ids["partner_account_id"]))
                assert code is not None
                assert account is not None
                code.partner_user_id = customer_user_id
                account.legacy_owner_user_id = customer_user_id
                db.commit()

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
            quote_response = await async_client.post(
                "/api/v1/quotes/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Auth-Realm": "customer",
                    "Cookie": f"{PARTNER_ATTRIBUTION_COOKIE_NAME}={cookie_token}",
                },
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
            assert quote_response.status_code == 201, quote_response.text
            _assert_attribution_cookie_deleted(quote_response)
            quote_payload = quote_response.json()
            assert quote_payload["quote"]["partner_markup"] == 0.0

            attribution_session_id = uuid.UUID(attribution_ids["attribution_session_id"])
            with sessionmaker() as db:
                attribution = db.get(PartnerAttributionSessionModel, attribution_session_id)
                assert attribution is not None
                assert attribution.status == "transferred"
                assert attribution.binding_id is None
                quote_session = db.get(QuoteSessionModel, uuid.UUID(quote_payload["id"]))
                assert quote_session is not None
                snapshot = quote_session.quote_snapshot["partner_attribution"]
                assert snapshot["status"] == "ignored_partner_self_attribution_blocked"
                assert snapshot["binding_id"] is None
                assert snapshot["quote_touchpoint_id"] is None
                assert (
                    db.query(CustomerCommercialBindingModel)
                    .filter(CustomerCommercialBindingModel.attribution_session_id == attribution_session_id)
                    .count()
                    == 0
                )
                assert (
                    db.query(AttributionTouchpointModel)
                    .filter(AttributionTouchpointModel.partner_attribution_session_id == attribution_session_id)
                    .count()
                    == 0
                )
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_terminal_rejected_attribution_cookie_does_not_block_quote_or_create_owner(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "partner_attribution_enabled", True)
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
            cookie_token = "terminal-rejected-cookie-token"
            attribution_ids = _seed_partner_attribution_cookie(
                sessionmaker,
                seeded=seeded,
                cookie_token=cookie_token,
            )
            attribution_session_id = uuid.UUID(attribution_ids["attribution_session_id"])
            with sessionmaker() as db:
                attribution = db.get(PartnerAttributionSessionModel, attribution_session_id)
                assert attribution is not None
                attribution.status = "rejected"
                attribution.rejection_reason_code = "risk_review_block"
                db.commit()

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
            quote_response = await async_client.post(
                "/api/v1/quotes/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Auth-Realm": "customer",
                    "Cookie": f"{PARTNER_ATTRIBUTION_COOKIE_NAME}={cookie_token}",
                },
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
            assert quote_response.status_code == 201, quote_response.text
            _assert_attribution_cookie_deleted(quote_response)
            quote_payload = quote_response.json()
            assert quote_payload["quote"]["partner_markup"] == 0.0

            with sessionmaker() as db:
                attribution = db.get(PartnerAttributionSessionModel, attribution_session_id)
                assert attribution is not None
                assert attribution.status == "expired"
                assert attribution.binding_id is None
                quote_session = db.get(QuoteSessionModel, uuid.UUID(quote_payload["id"]))
                assert quote_session is not None
                snapshot = quote_session.quote_snapshot["partner_attribution"]
                assert snapshot["status"] == "expired"
                assert snapshot["binding_id"] is None
                assert (
                    db.query(CustomerCommercialBindingModel)
                    .filter(CustomerCommercialBindingModel.attribution_session_id == attribution_session_id)
                    .count()
                    == 0
                )
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_checkout_safety_net_claims_legacy_quote_cookie_and_marks_stale(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "partner_attribution_enabled", True)
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
            assert quote_payload["quote"]["partner_markup"] == 0.0

            cookie_token = "checkout-cookie-fallback-token"
            attribution_ids = _seed_partner_attribution_cookie(
                sessionmaker,
                seeded=seeded,
                cookie_token=cookie_token,
            )
            checkout_response = await async_client.post(
                "/api/v1/checkout-sessions/",
                headers={
                    **headers,
                    "Cookie": f"{PARTNER_ATTRIBUTION_COOKIE_NAME}={cookie_token}",
                    "Idempotency-Key": "checkout-attr-stale-1",
                },
                json={"quote_session_id": quote_payload["id"]},
            )
            assert checkout_response.status_code == 409
            assert "stale" in checkout_response.json()["detail"]
            _assert_attribution_cookie_deleted(checkout_response)

            quote_id = uuid.UUID(quote_payload["id"])
            attribution_session_id = uuid.UUID(attribution_ids["attribution_session_id"])
            with sessionmaker() as db:
                attribution = db.get(PartnerAttributionSessionModel, attribution_session_id)
                assert attribution is not None
                assert attribution.status == "claimed"
                assert attribution.binding_id is not None
                quote_session = db.get(QuoteSessionModel, quote_id)
                assert quote_session is not None
                assert quote_session.quote_status == "stale"
                snapshot = quote_session.quote_snapshot["partner_attribution"]
                assert snapshot["source"] == "server_side_checkout_safety_net"
                assert snapshot["attribution_session_id"] == str(attribution_session_id)
                assert snapshot["binding_id"] == str(attribution.binding_id)
                assert cookie_token not in str(snapshot)
                assert (
                    db.query(CheckoutSessionModel).filter(CheckoutSessionModel.quote_session_id == quote_id).count()
                    == 0
                )
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_expired_partner_attribution_cookie_does_not_block_quote(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "partner_attribution_enabled", True)
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
            cookie_token = "expired-quote-cookie-token"
            attribution_ids = _seed_partner_attribution_cookie(
                sessionmaker,
                seeded=seeded,
                cookie_token=cookie_token,
                expires_at=datetime.now(UTC) - timedelta(minutes=1),
            )
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
                headers={**headers, "Cookie": f"{PARTNER_ATTRIBUTION_COOKIE_NAME}={cookie_token}"},
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
            _assert_attribution_cookie_deleted(quote_response)
            quote_payload = quote_response.json()
            assert quote_payload["quote"]["partner_markup"] == 0.0

            attribution_session_id = uuid.UUID(attribution_ids["attribution_session_id"])
            with sessionmaker() as db:
                attribution = db.get(PartnerAttributionSessionModel, attribution_session_id)
                assert attribution is not None
                assert attribution.status == "expired"
                assert attribution.binding_id is None
                quote_session = db.get(QuoteSessionModel, uuid.UUID(quote_payload["id"]))
                assert quote_session is not None
                snapshot = quote_session.quote_snapshot["partner_attribution"]
                assert snapshot["status"] == "expired"
                assert snapshot["attribution_session_id"] == str(attribution_session_id)
                assert snapshot["binding_id"] is None
                assert cookie_token not in str(snapshot)
                assert (
                    db.query(CustomerCommercialBindingModel)
                    .filter(CustomerCommercialBindingModel.attribution_session_id == attribution_session_id)
                    .count()
                    == 0
                )
                assert (
                    db.query(AttributionTouchpointModel)
                    .filter(
                        AttributionTouchpointModel.quote_session_id == uuid.UUID(quote_payload["id"]),
                        AttributionTouchpointModel.partner_attribution_session_id == attribution_session_id,
                    )
                    .count()
                    == 0
                )
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_unauthenticated_quote_with_partner_attribution_cookie_does_not_mutate_state(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "partner_attribution_enabled", True)
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
            cookie_token = "unauthenticated-quote-cookie-token"
            attribution_ids = _seed_partner_attribution_cookie(
                sessionmaker,
                seeded=seeded,
                cookie_token=cookie_token,
            )

            quote_response = await async_client.post(
                "/api/v1/quotes/",
                headers={
                    "X-Auth-Realm": "customer",
                    "Cookie": f"{PARTNER_ATTRIBUTION_COOKIE_NAME}={cookie_token}",
                },
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
            assert quote_response.status_code in {401, 403}

            attribution_session_id = uuid.UUID(attribution_ids["attribution_session_id"])
            with sessionmaker() as db:
                attribution = db.get(PartnerAttributionSessionModel, attribution_session_id)
                assert attribution is not None
                assert attribution.status == "transferred"
                assert attribution.user_id is None
                assert attribution.binding_id is None
                assert db.query(QuoteSessionModel).count() == 0
                assert (
                    db.query(CustomerCommercialBindingModel)
                    .filter(CustomerCommercialBindingModel.attribution_session_id == attribution_session_id)
                    .count()
                    == 0
                )
                assert (
                    db.query(AttributionTouchpointModel)
                    .filter(AttributionTouchpointModel.partner_attribution_session_id == attribution_session_id)
                    .count()
                    == 0
                )
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
@pytest.mark.parametrize("with_foreign_storefront", [True, False])
async def test_foreign_realm_partner_attribution_cookie_does_not_bind_or_block_quote(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    with_foreign_storefront: bool,
) -> None:
    monkeypatch.setattr(settings, "partner_attribution_enabled", True)
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
            cookie_token = f"foreign-realm-cookie-token-{int(with_foreign_storefront)}"
            attribution_ids = _seed_foreign_partner_attribution_cookie(
                sessionmaker,
                seeded=seeded,
                cookie_token=cookie_token,
                with_foreign_storefront=with_foreign_storefront,
            )
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
                headers={**headers, "Cookie": f"{PARTNER_ATTRIBUTION_COOKIE_NAME}={cookie_token}"},
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
            _assert_attribution_cookie_deleted(quote_response)
            quote_payload = quote_response.json()
            assert quote_payload["quote"]["partner_markup"] == 0.0
            assert "partner_attribution" not in quote_payload["quote"]

            quote_id = uuid.UUID(quote_payload["id"])
            attribution_session_id = uuid.UUID(attribution_ids["attribution_session_id"])
            with sessionmaker() as db:
                attribution = db.get(PartnerAttributionSessionModel, attribution_session_id)
                assert attribution is not None
                assert attribution.status == "transferred"
                assert attribution.user_id is None
                assert attribution.binding_id is None
                quote_session = db.get(QuoteSessionModel, quote_id)
                assert quote_session is not None
                snapshot = quote_session.quote_snapshot["partner_attribution"]
                assert snapshot["status"] == "no_pending"
                assert snapshot["attribution_session_id"] is None
                assert snapshot["partner_account_id"] is None
                assert snapshot["partner_code_id"] is None
                assert snapshot["binding_id"] is None
                assert snapshot["quote_touchpoint_id"] is None
                assert cookie_token not in str(snapshot)
                assert (
                    db.query(CustomerCommercialBindingModel)
                    .filter(CustomerCommercialBindingModel.attribution_session_id == attribution_session_id)
                    .count()
                    == 0
                )
                assert (
                    db.query(AttributionTouchpointModel)
                    .filter(
                        AttributionTouchpointModel.quote_session_id == quote_id,
                        AttributionTouchpointModel.partner_attribution_session_id == attribution_session_id,
                    )
                    .count()
                    == 0
                )
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_quote_session_reserves_promo_and_binds_it_to_checkout(
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
                promo = PromoCodeModel(
                    id=uuid.uuid4(),
                    code="PROMOSESSION10",
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
                    "code_input": "PROMOSESSION10",
                    "use_wallet": 0,
                    "addons": [],
                },
            )
            assert quote_response.status_code == 201
            quote_payload = quote_response.json()
            reservation_id = quote_payload["quote"]["code_resolution"]["reservation_id"]
            assert quote_payload["quote"]["code_input"] != "PROMOSESSION10"
            assert quote_payload["quote"]["code_input_ref"]["redacted"] is True
            assert quote_payload["quote"]["code_input_ref"]["code_prefix"] == "PRO"
            assert quote_payload["quote"]["code_resolution"]["code_type"] == "promo"
            assert quote_payload["quote"]["discounts"][0]["type"] == "promo"
            assert quote_payload["quote"]["discounts"][0]["code"] != "PROMOSESSION10"
            assert quote_payload["quote"]["discounts"][0]["code_ref"]["redacted"] is True
            assert quote_payload["quote"]["base_price"] == 75.0
            assert quote_payload["quote"]["discount_amount"] == 7.5
            assert reservation_id is not None

            with sessionmaker() as db:
                reservation = db.get(GrowthCodeReservationModel, uuid.UUID(reservation_id))
                assert reservation is not None
                assert reservation.quote_session_id == uuid.UUID(quote_payload["id"])
                assert reservation.checkout_session_id is None
                assert reservation.status == "reserved"

            checkout_response = await async_client.post(
                "/api/v1/checkout-sessions/",
                headers={**headers, "Idempotency-Key": "promo-bind-1"},
                json={"quote_session_id": quote_payload["id"]},
            )
            assert checkout_response.status_code == 201
            checkout_payload = checkout_response.json()
            assert checkout_payload["quote"]["code_resolution"]["reservation_id"] == reservation_id

            with sessionmaker() as db:
                reservation = db.get(GrowthCodeReservationModel, uuid.UUID(reservation_id))
                assert reservation is not None
                assert reservation.checkout_session_id == uuid.UUID(checkout_payload["id"])
                assert reservation.status == "reserved"
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
async def test_stale_quote_releases_reserved_promo(
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
                promo = PromoCodeModel(
                    id=uuid.uuid4(),
                    code="PROMOSTALE10",
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
                    "code_input": "PROMOSTALE10",
                    "use_wallet": 0,
                    "addons": [],
                },
            )
            assert quote_response.status_code == 201
            quote_payload = quote_response.json()
            reservation_id = quote_payload["quote"]["code_resolution"]["reservation_id"]

            with sessionmaker() as db:
                entry = db.get(PricebookEntryModel, uuid.UUID(seeded["pricebook_entry_id"]))
                entry.visible_price = 69
                db.add(entry)
                db.commit()

            request_marker = "stale-quote-promo-1"
            checkout_response = await async_client.post(
                "/api/v1/checkout-sessions/",
                headers={**headers, "Idempotency-Key": request_marker},
                json={"quote_session_id": quote_payload["id"]},
            )
            assert checkout_response.status_code == 409
            assert "stale" in checkout_response.json()["detail"]

            with sessionmaker() as db:
                reservation = db.get(GrowthCodeReservationModel, uuid.UUID(reservation_id))
                assert reservation is not None
                assert reservation.status == "released"
                assert reservation.release_reason == "quote_session_stale"
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


@pytest.mark.asyncio
async def test_expired_quote_expires_reserved_promo(
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
                promo = PromoCodeModel(
                    id=uuid.uuid4(),
                    code="PROMOEXPIRED10",
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
                    "code_input": "PROMOEXPIRED10",
                    "use_wallet": 0,
                    "addons": [],
                },
            )
            assert quote_response.status_code == 201
            quote_payload = quote_response.json()
            reservation_id = quote_payload["quote"]["code_resolution"]["reservation_id"]

            with sessionmaker() as db:
                quote_session = db.get(QuoteSessionModel, uuid.UUID(quote_payload["id"]))
                quote_session.expires_at = datetime.now(UTC) - timedelta(minutes=1)
                db.add(quote_session)
                db.commit()

            checkout_response = await async_client.post(
                "/api/v1/checkout-sessions/",
                headers={**headers, "Idempotency-Key": "expired-quote-promo-1"},
                json={"quote_session_id": quote_payload["id"]},
            )
            assert checkout_response.status_code == 409
            assert "expired" in checkout_response.json()["detail"]

            with sessionmaker() as db:
                reservation = db.get(GrowthCodeReservationModel, uuid.UUID(reservation_id))
                assert reservation is not None
                assert reservation.status == "expired"
                assert reservation.release_reason == "quote_session_expired"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
