"""Seed a local partner workspace for AC-18 live BFF/browser smoke evidence.

The script is intentionally local-only. It refuses non-loopback database URLs
and writes generated credentials only under .private so evidence can remain
sanitized.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
import socket
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import select

from src.application.services.auth_service import AuthService
from src.application.use_cases.partners.create_partner_workspace import CreatePartnerWorkspaceUseCase
from src.config.settings import settings
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.brand_model import BrandModel
from src.infrastructure.database.models.legal_document_model import LegalDocumentModel
from src.infrastructure.database.models.legal_document_set_model import LegalDocumentSetItemModel, LegalDocumentSetModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.offer_model import OfferModel
from src.infrastructure.database.models.partner_application_model import PartnerApplicationDraftModel
from src.infrastructure.database.models.partner_payout_account_model import PartnerPayoutAccountModel
from src.infrastructure.database.models.partner_statement_model import PartnerStatementModel
from src.infrastructure.database.models.partner_workspace_profile_model import PartnerWorkspaceProfileModel
from src.infrastructure.database.models.payout_instruction_model import PayoutInstructionModel
from src.infrastructure.database.models.policy_version_model import PolicyVersionModel
from src.infrastructure.database.models.pricebook_model import PricebookEntryModel, PricebookModel
from src.infrastructure.database.models.settlement_period_model import SettlementPeriodModel
from src.infrastructure.database.models.storefront_model import StorefrontModel
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
from src.infrastructure.database.repositories.partner_account_repository import PartnerAccountRepository
from src.infrastructure.database.session import AsyncSessionLocal, engine

REPO_ROOT = Path(__file__).resolve().parents[2]
PRIVATE_OUTPUT = REPO_ROOT / ".private" / "latest-partner-smoke.json"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
FORBIDDEN_HOSTS = {"45.87.41.146", "prod-app-1", "my.cyber-vpn.net", "api.cyber-vpn.net"}


def _database_host(url: str) -> str:
    parsed = urlparse(url.replace("postgresql+asyncpg://", "postgresql://", 1))
    return (parsed.hostname or "").lower()


def _is_loopback(host: str) -> bool:
    if host in LOCAL_HOSTS:
        return True
    try:
        return all(socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)[0][4][0].startswith("127.") for _ in [host])
    except socket.gaierror:
        return False


def _assert_local_database() -> None:
    host = _database_host(settings.database_url)
    if host in FORBIDDEN_HOSTS or not _is_loopback(host):
        raise RuntimeError(
            "Refusing to seed partner smoke data into a non-local database. "
            f"Resolved host: {host or '<missing>'}."
        )


def _new_password() -> str:
    return f"Ac18Smoke-{secrets.token_urlsafe(18)}_1!"


async def _get_or_create_realm(session, *, realm_key: str, realm_type: str, display_name: str) -> AuthRealmModel:
    result = await session.execute(select(AuthRealmModel).where(AuthRealmModel.realm_key == realm_key))
    realm = result.scalar_one_or_none()
    if realm is not None:
        realm.realm_type = realm_type
        realm.display_name = display_name
        realm.audience = f"cybervpn:{realm_key}"
        realm.cookie_namespace = realm_key
        realm.status = "active"
        realm.is_default = True
        return realm

    realm = AuthRealmModel(
        realm_key=realm_key,
        realm_type=realm_type,
        display_name=display_name,
        audience=f"cybervpn:{realm_key}",
        cookie_namespace=realm_key,
        status="active",
        is_default=True,
    )
    session.add(realm)
    await session.flush()
    return realm


async def _create_admin_user(
    session,
    auth_service: AuthService,
    *,
    auth_realm_id,
    login: str,
    email: str,
    password: str,
    role: str,
) -> AdminUserModel:
    user = AdminUserModel(
        login=login,
        email=email,
        auth_realm_id=auth_realm_id,
        password_hash=await auth_service.hash_password(password),
        role=role,
        is_active=True,
        is_email_verified=True,
        status="active",
        language="en",
        timezone="UTC",
        display_name="AC-18 Live Partner Operator",
    )
    session.add(user)
    await session.flush()
    return user


async def _create_mobile_owner(session, auth_service: AuthService, *, suffix: str, password: str) -> MobileUserModel:
    owner = MobileUserModel(
        email=f"ac18-partner-owner-{suffix}@example.invalid",
        password_hash=await auth_service.hash_password(password),
        username=f"ac18_partner_owner_{suffix}",
        is_active=True,
        status="active",
        is_partner=True,
        partner_promoted_at=datetime.now(UTC),
        notification_prefs={},
    )
    session.add(owner)
    await session.flush()
    return owner


async def _create_profile(session, *, partner_account_id, contact_email: str) -> PartnerWorkspaceProfileModel:
    profile = PartnerWorkspaceProfileModel(
        partner_account_id=partner_account_id,
        website="https://ac18-live-smoke.example.invalid",
        country="DE",
        operating_regions="EU, LATAM",
        languages="en,ru,de",
        contact_name="AC-18 Live Partner Ops",
        contact_email=contact_email,
        support_contact=contact_email,
        technical_contact=contact_email,
        finance_contact=contact_email,
        business_description="Local AC-18 smoke workspace for live partner portal route checks.",
        acquisition_channels="SEO, Telegram, creator affiliate",
        preferred_currency="USD",
        require_mfa_for_workspace=False,
        prefer_passkeys=False,
        reviewed_active_sessions=True,
    )
    session.add(profile)
    await session.flush()
    return profile


async def _create_application_draft(
    session,
    *,
    partner_account_id,
    applicant_admin_user_id,
    operator_email: str,
    suffix: str,
) -> PartnerApplicationDraftModel:
    draft = PartnerApplicationDraftModel(
        partner_account_id=partner_account_id,
        applicant_admin_user_id=applicant_admin_user_id,
        draft_payload={
            "workspace_name": f"AC-18 Live Smoke {suffix}",
            "country": "DE",
            "primary_lane": "creator_affiliate",
            "contact_name": "AC-18 Live Partner Ops",
            "contact_email": operator_email,
            "website": "https://ac18-live-smoke.example.invalid",
            "business_description": "Local AC-18 smoke workspace for live partner portal route checks.",
            "acquisition_channels": "SEO, Telegram, creator affiliate",
            "compliance_accepted": True,
        },
        review_ready=False,
    )
    session.add(draft)
    await session.flush()
    return draft


async def _create_finance_snapshot(session, *, partner_account_id, operator_id, suffix: str) -> dict[str, str]:
    now = datetime.now(UTC)
    payout = PartnerPayoutAccountModel(
        partner_account_id=partner_account_id,
        payout_rail="manual",
        display_label="AC-18 smoke payout destination",
        destination_reference=f"ac18-payout-{suffix}@example.invalid",
        masked_destination=f"ac18-payout-{suffix[:4]}***@example.invalid",
        destination_metadata={"kind": "local-smoke", "channel": "email"},
        verification_status="verified",
        approval_status="approved",
        account_status="active",
        is_default=True,
        created_by_admin_user_id=operator_id,
        verified_by_admin_user_id=operator_id,
        verified_at=now,
        approved_by_admin_user_id=operator_id,
        approved_at=now,
        default_selected_by_admin_user_id=operator_id,
        default_selected_at=now,
    )
    session.add(payout)
    await session.flush()

    period = SettlementPeriodModel(
        partner_account_id=partner_account_id,
        period_key=f"ac18-smoke-{suffix}",
        period_status="closed",
        currency_code="USD",
        window_start=now - timedelta(days=30),
        window_end=now,
        closed_at=now,
        closed_by_admin_user_id=operator_id,
    )
    session.add(period)
    await session.flush()

    statement = PartnerStatementModel(
        partner_account_id=partner_account_id,
        settlement_period_id=period.id,
        statement_key=f"ac18-statement-{suffix}",
        statement_status="closed",
        currency_code="USD",
        accrual_amount=Decimal("133.33"),
        on_hold_amount=Decimal("6.78"),
        reserve_amount=Decimal("3.21"),
        adjustment_net_amount=Decimal("1.11"),
        available_amount=Decimal("124.45"),
        source_event_count=7,
        held_event_count=1,
        active_reserve_count=1,
        adjustment_count=1,
        statement_snapshot={
            "source": "ac18_local_seed",
            "redacted": True,
        },
        closed_at=now,
        closed_by_admin_user_id=operator_id,
    )
    session.add(statement)
    await session.flush()

    instruction = PayoutInstructionModel(
        partner_account_id=partner_account_id,
        partner_statement_id=statement.id,
        partner_payout_account_id=payout.id,
        instruction_key=f"ac18-payout-instruction-{suffix}",
        instruction_status="pending_approval",
        payout_amount=Decimal("124.45"),
        currency_code="USD",
        instruction_snapshot={
            "source": "ac18_local_seed",
            "redacted": True,
        },
        created_by_admin_user_id=operator_id,
    )
    session.add(instruction)
    await session.flush()

    return {
        "payout_account_id": str(payout.id),
        "settlement_period_id": str(period.id),
        "statement_id": str(statement.id),
        "payout_instruction_id": str(instruction.id),
    }


async def _create_storefront_snapshot(session, *, storefront_realm_id, operator_id, suffix: str) -> dict[str, str]:
    now = datetime.now(UTC)

    result = await session.execute(select(BrandModel).where(BrandModel.brand_key == "cybervpn"))
    brand = result.scalar_one_or_none()
    if brand is None:
        brand = BrandModel(
            brand_key="cybervpn",
            display_name="CyberVPN",
            status="active",
        )
        session.add(brand)
    else:
        brand.display_name = "CyberVPN"
        brand.status = "active"
    await session.flush()

    result = await session.execute(
        select(StorefrontModel).where(StorefrontModel.storefront_key == "cybervpn-storefront")
    )
    storefront = result.scalar_one_or_none()
    if storefront is None:
        storefront = StorefrontModel(
            storefront_key="cybervpn-storefront",
            brand_id=brand.id,
            display_name="CyberVPN Storefront",
            host="storefront.localhost",
            auth_realm_id=storefront_realm_id,
            status="active",
        )
        session.add(storefront)
    else:
        storefront.brand_id = brand.id
        storefront.display_name = "CyberVPN Storefront"
        storefront.host = "storefront.localhost"
        storefront.auth_realm_id = storefront_realm_id
        storefront.status = "active"
    await session.flush()

    plan = SubscriptionPlanModel(
        name=f"ac18_storefront_plan_{suffix}",
        tier="standard",
        plan_code=f"A18{suffix[:6].upper()}",
        display_name="AC-18 Storefront Plan",
        catalog_visibility="public",
        catalog_access_class="public",
        duration_days=30,
        traffic_limit_bytes=None,
        device_limit=5,
        price_usd=Decimal("9.99"),
        price_rub=Decimal("899.00"),
        sale_channels=["web", "partner_storefront"],
        traffic_policy={"mode": "fair_use", "display_label": "Unlimited"},
        connection_modes=["standard", "stealth"],
        server_pool=["default"],
        support_sla="standard",
        dedicated_ip={"included": 0, "eligible": False},
        invite_bundle={},
        trial_eligible=False,
        features={"source": "ac18_local_seed"},
        is_active=True,
        sort_order=10,
    )
    session.add(plan)
    await session.flush()

    offer = OfferModel(
        offer_key=f"ac18-storefront-offer-{suffix}",
        display_name="AC-18 Storefront Offer",
        subscription_plan_id=plan.id,
        included_addon_codes=[],
        sale_channels=["partner_storefront"],
        visibility_rules={"source": "ac18_local_seed"},
        invite_bundle={},
        trial_eligible=False,
        gift_eligible=False,
        referral_eligible=False,
        renewal_incentives={},
        version_status="active",
        effective_from=now - timedelta(minutes=5),
        effective_to=None,
        is_active=True,
    )
    session.add(offer)
    await session.flush()

    pricebook = PricebookModel(
        pricebook_key=f"ac18-storefront-pricebook-{suffix}",
        display_name="AC-18 Storefront Pricebook",
        storefront_id=storefront.id,
        currency_code="USD",
        region_code=None,
        discount_rules={},
        renewal_pricing_policy={},
        version_status="active",
        effective_from=now - timedelta(minutes=5),
        effective_to=None,
        is_active=True,
    )
    session.add(pricebook)
    await session.flush()

    session.add(
        PricebookEntryModel(
            pricebook_id=pricebook.id,
            offer_id=offer.id,
            visible_price=Decimal("9.99"),
            compare_at_price=Decimal("14.99"),
            included_addon_codes=[],
            display_order=0,
        )
    )
    await session.flush()

    document_policy = PolicyVersionModel(
        policy_family="legal_documents",
        policy_key=f"ac18-storefront-terms-{suffix}",
        subject_type="storefront",
        subject_id=storefront.id,
        version_number=1,
        payload={"source": "ac18_local_seed"},
        approval_state="approved",
        version_status="active",
        effective_from=now - timedelta(minutes=5),
        created_by_admin_user_id=operator_id,
        approved_by_admin_user_id=operator_id,
        approved_at=now,
    )
    set_policy = PolicyVersionModel(
        policy_family="legal_document_sets",
        policy_key=f"ac18-storefront-set-{suffix}",
        subject_type="storefront",
        subject_id=storefront.id,
        version_number=1,
        payload={"source": "ac18_local_seed"},
        approval_state="approved",
        version_status="active",
        effective_from=now - timedelta(minutes=5),
        created_by_admin_user_id=operator_id,
        approved_by_admin_user_id=operator_id,
        approved_at=now,
    )
    session.add_all([document_policy, set_policy])
    await session.flush()

    content_markdown = "# AC-18 Storefront Terms\n\nLocal route-smoke legal document for storefront validation."
    document = LegalDocumentModel(
        document_key=f"ac18-storefront-terms-{suffix}",
        document_type="terms",
        locale="ru-RU",
        title="AC-18 Storefront Terms",
        content_markdown=content_markdown,
        content_checksum=hashlib.sha256(content_markdown.encode("utf-8")).hexdigest(),
        policy_version_id=document_policy.id,
    )
    session.add(document)
    await session.flush()

    legal_set = LegalDocumentSetModel(
        set_key=f"ac18-storefront-set-{suffix}",
        storefront_id=storefront.id,
        auth_realm_id=storefront_realm_id,
        display_name="AC-18 Storefront Legal Set",
        policy_version_id=set_policy.id,
    )
    session.add(legal_set)
    await session.flush()
    session.add(
        LegalDocumentSetItemModel(
            legal_document_set_id=legal_set.id,
            legal_document_id=document.id,
            required=True,
            display_order=0,
        )
    )
    await session.flush()

    return {
        "storefront_id": str(storefront.id),
        "offer_id": str(offer.id),
        "pricebook_id": str(pricebook.id),
        "legal_document_set_id": str(legal_set.id),
    }


async def main() -> None:
    _assert_local_database()
    suffix = secrets.token_hex(5)
    password = _new_password()
    auth_service = AuthService()

    async with AsyncSessionLocal() as session:
        partner_realm = await _get_or_create_realm(
            session,
            realm_key="partner",
            realm_type="partner",
            display_name="Partner",
        )
        storefront_realm = await _get_or_create_realm(
            session,
            realm_key="cybervpn-storefront",
            realm_type="customer",
            display_name="CyberVPN Storefront",
        )
        operator = await _create_admin_user(
            session,
            auth_service,
            auth_realm_id=partner_realm.id,
            login=f"ac18_partner_{suffix}",
            email=f"ac18-partner-{suffix}@example.invalid",
            password=password,
            role="operator",
        )
        legacy_owner = await _create_mobile_owner(session, auth_service, suffix=suffix, password=password)

        repo = PartnerAccountRepository(session)
        workspace, membership = await CreatePartnerWorkspaceUseCase(session, repo).execute(
            display_name=f"AC-18 Live Smoke {suffix}",
            account_key=f"ac18-live-smoke-{suffix}",
            initial_status="active",
            legacy_owner_user_id=legacy_owner.id,
            owner_admin_user_id=operator.id,
            created_by_admin_user_id=operator.id,
        )
        await _create_profile(session, partner_account_id=workspace.id, contact_email=operator.email)
        application_draft = await _create_application_draft(
            session,
            partner_account_id=workspace.id,
            applicant_admin_user_id=operator.id,
            operator_email=operator.email,
            suffix=suffix,
        )
        finance = await _create_finance_snapshot(
            session,
            partner_account_id=workspace.id,
            operator_id=operator.id,
            suffix=suffix,
        )
        storefront = await _create_storefront_snapshot(
            session,
            storefront_realm_id=storefront_realm.id,
            operator_id=operator.id,
            suffix=suffix,
        )
        await session.commit()

    output = {
        "created_at": datetime.now(UTC).isoformat(),
        "identifier": operator.email,
        "password": password,
        "workspace_id": str(workspace.id),
        "workspace_key": workspace.account_key,
        "membership_id": str(membership.id) if membership is not None else None,
        "operator_id": str(operator.id),
        "partner_realm_id": str(partner_realm.id),
        "storefront_realm_id": str(storefront_realm.id),
        "base_url": "http://portal.localhost:3002",
        "connect_base_url": "http://127.0.0.1:3002",
        "backend_url": "http://127.0.0.1:8002",
        "application_draft_id": str(application_draft.id),
        "finance": finance,
        "storefront": storefront,
    }
    PRIVATE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    PRIVATE_OUTPUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    safe_summary = {
        "status": "seeded",
        "credentials_path": str(PRIVATE_OUTPUT.relative_to(REPO_ROOT)),
        "identifier": "<redacted>",
        "workspace_id": output["workspace_id"],
        "workspace_key": output["workspace_key"],
        "application_draft_id": output["application_draft_id"],
        "finance_rows": sorted(finance),
        "storefront_rows": sorted(storefront),
    }
    print(json.dumps(safe_summary, indent=2, sort_keys=True))

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
