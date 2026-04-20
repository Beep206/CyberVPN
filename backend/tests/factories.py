"""Test data factories using factory-boy (QUAL-01c)."""

import uuid
from datetime import UTC, datetime

import factory


class AdminUserFactory(factory.Factory):
    """Factory for AdminUser-like dicts (no ORM dependency for unit tests)."""

    class Meta:
        model = dict

    id = factory.LazyFunction(uuid.uuid4)
    login = factory.Sequence(lambda n: f"testuser{n}")
    email = factory.LazyAttribute(lambda o: f"{o.login}@example.com")
    password_hash = "$argon2id$v=19$m=65536,t=3,p=4$fake_hash"
    role = "viewer"
    is_active = True
    is_email_verified = True
    telegram_id = None
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))
    # BF2-3: Profile fields
    display_name = None
    language = "en"
    timezone = "UTC"
    # BF2-5: Notification preferences
    notification_prefs = None


class AuthRealmFactory(factory.Factory):
    """Factory for realm-like dicts used in Phase 0/1 validation packs."""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: f"realm-{n}")
    realm_key = factory.Sequence(lambda n: f"realm_key_{n}")
    realm_type = "customer"
    display_name = factory.Sequence(lambda n: f"Realm {n}")
    status = "active"


class StorefrontFactory(factory.Factory):
    """Factory for storefront-like dicts used in Phase 0/1 validation packs."""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: f"storefront-{n}")
    brand_id = factory.Sequence(lambda n: f"brand-{n}")
    storefront_key = factory.Sequence(lambda n: f"storefront_key_{n}")
    host = factory.Sequence(lambda n: f"storefront-{n}.example.test")
    auth_realm_id = factory.Sequence(lambda n: f"realm-{n}")
    status = "active"


class PartnerWorkspaceFactory(factory.Factory):
    """Factory for partner workspace-like dicts used in Phase 0/1 validation packs."""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: f"workspace-{n}")
    partner_account_id = factory.Sequence(lambda n: f"partner-{n}")
    owner_principal_id = factory.Sequence(lambda n: f"partner-user-{n}")
    role = "owner"
    status = "active"


class AcceptedLegalDocumentFactory(factory.Factory):
    """Factory for legal acceptance evidence used in Phase 0/1 validation packs."""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: f"acceptance-{n}")
    document_version_id = factory.Sequence(lambda n: f"doc-version-{n}")
    storefront_id = factory.Sequence(lambda n: f"storefront-{n}")
    auth_realm_id = factory.Sequence(lambda n: f"realm-{n}")
    actor_principal_id = factory.Sequence(lambda n: f"principal-{n}")
    acceptance_channel = "official-web"
    accepted_at = factory.LazyFunction(lambda: datetime.now(UTC).isoformat())


class OfferFactory(factory.Factory):
    """Factory for offer-like dicts used in Phase 1 validation packs."""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: f"offer-{n}")
    offer_key = factory.Sequence(lambda n: f"offer_key_{n}")
    display_name = factory.Sequence(lambda n: f"Offer {n}")
    subscription_plan_id = factory.Sequence(lambda n: f"plan-{n}")
    sale_channels = factory.LazyFunction(lambda: ["official_web"])
    version_status = "active"
    is_active = True


class PricebookFactory(factory.Factory):
    """Factory for pricebook-like dicts used in Phase 1 validation packs."""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: f"pricebook-{n}")
    pricebook_key = factory.Sequence(lambda n: f"pricebook_key_{n}")
    display_name = factory.Sequence(lambda n: f"Pricebook {n}")
    storefront_id = factory.Sequence(lambda n: f"storefront-{n}")
    currency_code = "USD"
    region_code = None
    version_status = "active"
    is_active = True


class ProgramEligibilityPolicyFactory(factory.Factory):
    """Factory for eligibility-policy-like dicts used in Phase 1 validation packs."""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: f"program-eligibility-{n}")
    policy_key = factory.Sequence(lambda n: f"program_eligibility_{n}")
    subject_type = "offer"
    offer_id = factory.Sequence(lambda n: f"offer-{n}")
    creator_affiliate_allowed = True
    reseller_allowed = False
    performance_allowed = False
    referral_credit_allowed = True
    invite_allowed = True
    renewal_commissionable = False
    addon_commissionable = False
    version_status = "active"
    is_active = True


class RiskSubjectFactory(factory.Factory):
    """Factory for risk-subject-like dicts used in Phase 0/1 validation packs."""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: f"risk-subject-{n}")
    subject_type = "person_cluster"
    status = "active"
    primary_realm_id = factory.Sequence(lambda n: f"realm-{n}")


class RiskLinkFactory(factory.Factory):
    """Factory for risk-link-like dicts used in Phase 1 validation packs."""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: f"risk-link-{n}")
    left_subject_id = factory.Sequence(lambda n: f"risk-subject-{n}")
    right_subject_id = factory.Sequence(lambda n: f"risk-subject-alt-{n}")
    link_type = "identifier_match"
    identifier_type = "email"
    status = "active"
