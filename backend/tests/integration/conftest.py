"""Pytest fixtures for integration tests."""

import secrets
import uuid

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.jwt_revocation_service import JWTRevocationService
from src.infrastructure.cache.redis_client import get_redis_client
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
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

ADMIN_HOST_HEADERS = {"Host": "testserver", "X-Forwarded-Host": "admin.cyber-vpn.net"}


async def get_default_test_realm(db: AsyncSession, realm_type: str) -> AuthRealmModel:
    return await AuthRealmRepository(db).get_or_create_default_realm(realm_type)


async def issue_realm_access_token(
    db: AsyncSession,
    *,
    subject: str,
    role: str,
    realm_type: str,
) -> str:
    auth_service = AuthService()
    realm = await get_default_test_realm(db, realm_type)
    principal_type = "customer" if realm.realm_type == "customer" else "admin"
    access_token, jti, access_exp = auth_service.create_access_token(
        subject=subject,
        role=role,
        audience=realm.audience,
        principal_type=principal_type,
        realm_id=str(realm.id),
        realm_key=realm.realm_key,
        scope_family=realm.realm_type,
    )
    redis_client = await get_redis_client()
    try:
        await JWTRevocationService(redis_client).register_token(
            jti=jti,
            user_id=subject,
            expires_at=access_exp,
            auth_realm_id=str(realm.id),
            principal_class=principal_type,
            principal_subject=subject,
        )
    finally:
        await redis_client.aclose()
    return access_token


async def issue_admin_access_token(
    db: AsyncSession,
    user: AdminUserModel,
    *,
    role: str | None = None,
) -> str:
    return await issue_realm_access_token(
        db,
        subject=str(user.id),
        role=role or str(user.role),
        realm_type="admin",
    )


async def issue_customer_access_token(
    db: AsyncSession,
    user: MobileUserModel,
    *,
    role: str = "customer",
) -> str:
    return await issue_realm_access_token(
        db,
        subject=str(user.id),
        role=role,
        realm_type="customer",
    )


def admin_auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}", **ADMIN_HOST_HEADERS}


def customer_auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}", "X-Auth-Realm": "customer"}


@pytest_asyncio.fixture
async def test_user_with_token(
    db: AsyncSession,
) -> tuple[AdminUserModel, str]:
    """Create a test user and generate an access token.

    Returns:
        tuple[AdminUserModel, str]: User model and access token
    """
    auth_service = AuthService()
    admin_realm = await get_default_test_realm(db, "admin")

    # Create test user
    user = AdminUserModel(
        id=uuid.uuid4(),
        auth_realm_id=admin_realm.id,
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
    access_token = await issue_admin_access_token(db, user)

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
