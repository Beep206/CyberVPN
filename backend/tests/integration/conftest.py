"""Pytest fixtures for integration tests."""

import secrets
import uuid

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.jwt_revocation_service import JWTRevocationService
from src.infrastructure.cache.redis_client import get_redis_client
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from tests.factories import (
    AcceptedLegalDocumentFactory,
    AuthRealmFactory,
    OfferFactory,
    PartnerWorkspaceFactory,
    PricebookFactory,
    ProgramEligibilityPolicyFactory,
    RiskLinkFactory,
    RiskSubjectFactory,
    StorefrontFactory,
)


@pytest_asyncio.fixture
async def test_user_with_token(
    db: AsyncSession,
) -> tuple[AdminUserModel, str]:
    """Create a test user and generate an access token.

    Returns:
        tuple[AdminUserModel, str]: User model and access token
    """
    auth_service = AuthService()

    # Create test user
    user = AdminUserModel(
        id=uuid.uuid4(),
        login=f"testuser_{secrets.token_hex(4)}",
        email=f"test_{secrets.token_hex(4)}@example.com",
        password_hash=await auth_service.hash_password("TestPassword123!"),
        role="user",
        is_active=True,
        language="en-EN",
        timezone="UTC",
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Generate access token
    access_token, jti, access_exp = auth_service.create_access_token(
        subject=str(user.id),
        role=user.role,
    )
    redis_client = await get_redis_client()
    try:
        await JWTRevocationService(redis_client).register_token(
            jti=jti,
            user_id=str(user.id),
            expires_at=access_exp,
        )
    finally:
        await redis_client.aclose()

    return user, access_token


@pytest_asyncio.fixture
async def phase0_phase1_validation_context() -> dict[str, dict]:
    """Synthetic context used by Phase 0/1 contract and integration tests."""

    official_realm = AuthRealmFactory(id="realm-official", realm_key="official", display_name="Official Realm")
    partner_realm = AuthRealmFactory(id="realm-partner", realm_key="partner", display_name="Partner Realm")

    official_storefront = StorefrontFactory(
        id="storefront-official",
        brand_id="brand-cybervpn",
        storefront_key="official-web",
        host="cybervpn.example.test",
        auth_realm_id=official_realm["id"],
    )
    partner_storefront = StorefrontFactory(
        id="storefront-partner",
        brand_id="brand-partner",
        storefront_key="partner-web",
        host="partner.example.test",
        auth_realm_id=partner_realm["id"],
    )

    partner_workspace = PartnerWorkspaceFactory(
        id="workspace-growth-01",
        partner_account_id="partner-account-01",
        owner_principal_id="partner-operator-01",
    )

    legal_acceptance = AcceptedLegalDocumentFactory(
        id="acceptance-01",
        document_version_id="terms-v1",
        storefront_id=partner_storefront["id"],
        auth_realm_id=partner_realm["id"],
        actor_principal_id=partner_workspace["owner_principal_id"],
    )

    risk_subject = RiskSubjectFactory(
        id="risk-subject-01",
        primary_realm_id=partner_realm["id"],
    )
    offer = OfferFactory(
        id="offer-growth-01",
        subscription_plan_id="plan-365",
        sale_channels=["official_web", "partner_storefront"],
    )
    pricebook = PricebookFactory(
        id="pricebook-partner-01",
        storefront_id=partner_storefront["id"],
    )
    program_eligibility = ProgramEligibilityPolicyFactory(
        id="eligibility-offer-01",
        offer_id=offer["id"],
        reseller_allowed=True,
        creator_affiliate_allowed=True,
    )
    risk_link = RiskLinkFactory(
        id="risk-link-01",
        left_subject_id=risk_subject["id"],
        right_subject_id="risk-subject-02",
    )

    return {
        "official_realm": official_realm,
        "partner_realm": partner_realm,
        "official_storefront": official_storefront,
        "partner_storefront": partner_storefront,
        "partner_workspace": partner_workspace,
        "legal_acceptance": legal_acceptance,
        "risk_subject": risk_subject,
        "offer": offer,
        "pricebook": pricebook,
        "program_eligibility": program_eligibility,
        "risk_link": risk_link,
        "phase1_api_paths": (
            "/api/v1/auth/login",
            "/api/v1/auth/me",
            "/api/v1/realms/",
            "/api/v1/realms/resolve",
            "/api/v1/admin/partner-workspaces",
            "/api/v1/partner-workspaces/me",
            "/api/v1/offers/",
            "/api/v1/pricebooks/resolve",
            "/api/v1/program-eligibility/",
            "/api/v1/policies/",
            "/api/v1/legal-documents/",
            "/api/v1/legal-documents/sets/resolve",
            "/api/v1/policy-acceptance/",
            "/api/v1/security/risk-subjects",
            "/api/v1/security/risk-reviews",
            "/api/v1/security/eligibility/checks",
        ),
    }
