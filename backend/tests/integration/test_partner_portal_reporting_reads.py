from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.billing_descriptor_model import BillingDescriptorModel
from src.infrastructure.database.models.brand_model import BrandModel
from src.infrastructure.database.models.checkout_session_model import CheckoutSessionModel
from src.infrastructure.database.models.commissionability_evaluation_model import (
    CommissionabilityEvaluationModel,
)
from src.infrastructure.database.models.creative_approval_model import CreativeApprovalModel
from src.infrastructure.database.models.dispute_case_model import DisputeCaseModel
from src.infrastructure.database.models.invoice_profile_model import InvoiceProfileModel
from src.infrastructure.database.models.merchant_profile_model import MerchantProfileModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.order_attribution_result_model import (
    OrderAttributionResultModel,
)
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.models.outbox_event_model import (
    OutboxEventModel,
    OutboxPublicationModel,
)
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeModel
from src.infrastructure.database.models.partner_payout_account_model import (
    PartnerPayoutAccountModel,
)
from src.infrastructure.database.models.partner_statement_model import PartnerStatementModel
from src.infrastructure.database.models.partner_traffic_declaration_model import (
    PartnerTrafficDeclarationModel,
)
from src.infrastructure.database.models.payment_dispute_model import PaymentDisputeModel
from src.infrastructure.database.models.quote_session_model import QuoteSessionModel
from src.infrastructure.database.models.renewal_order_model import RenewalOrderModel
from src.infrastructure.database.models.settlement_period_model import SettlementPeriodModel
from src.infrastructure.database.models.storefront_model import StorefrontModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
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


async def _create_admin_user(
    *,
    session,
    auth_service: AuthService,
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
    )
    session.add(user)
    session.commit()
    return user


async def _login(async_client: AsyncClient, login_or_email: str, password: str) -> str:
    response = await async_client.post(
        "/api/v1/auth/login",
        headers={"X-Auth-Realm": "admin"},
        json={"login_or_email": login_or_email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def _create_workspace(
    async_client: AsyncClient,
    *,
    admin_headers: dict[str, str],
    owner_admin_user_id: str,
) -> str:
    response = await async_client.post(
        "/api/v1/admin/partner-workspaces",
        headers=admin_headers,
        json={
            "display_name": "Portal Reporting Workspace",
            "owner_admin_user_id": owner_admin_user_id,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _seed_storefront_context(
    *,
    session,
    customer_realm_id: uuid.UUID,
) -> tuple[BrandModel, InvoiceProfileModel, MerchantProfileModel, BillingDescriptorModel, StorefrontModel]:
    brand = BrandModel(
        id=uuid.uuid4(),
        brand_key="partner-reporting-brand",
        display_name="Partner Reporting Brand",
        status="active",
    )
    invoice_profile = InvoiceProfileModel(
        id=uuid.uuid4(),
        profile_key="partner-reporting-invoice",
        display_name="Partner Reporting Invoice",
        issuer_legal_name="CyberVPN Billing LLC",
        issuer_email="billing@example.com",
        tax_behavior={"mode": "inclusive"},
        status="active",
    )
    merchant_profile = MerchantProfileModel(
        id=uuid.uuid4(),
        profile_key="partner-reporting-merchant",
        legal_entity_name="CyberVPN Merchant LLC",
        billing_descriptor="CYBERVPN",
        invoice_profile_id=invoice_profile.id,
        settlement_reference="merchant-ref",
        supported_currencies=["USD"],
        tax_behavior={"mode": "inclusive"},
        status="active",
    )
    billing_descriptor = BillingDescriptorModel(
        id=uuid.uuid4(),
        descriptor_key="partner-reporting-descriptor",
        merchant_profile_id=merchant_profile.id,
        invoice_profile_id=invoice_profile.id,
        statement_descriptor="CYBERVPN*VPN",
        support_url="https://help.example.com",
        is_default=True,
        status="active",
    )
    storefront = StorefrontModel(
        id=uuid.uuid4(),
        storefront_key="partner-reporting-storefront",
        brand_id=brand.id,
        display_name="Partner Reporting Storefront",
        host="reporting.partner.example.com",
        merchant_profile_id=merchant_profile.id,
        auth_realm_id=customer_realm_id,
        status="active",
    )
    session.add_all([brand, invoice_profile, merchant_profile, billing_descriptor, storefront])
    session.commit()
    return brand, invoice_profile, merchant_profile, billing_descriptor, storefront


def _seed_mobile_users(
    *,
    session,
    customer_realm_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> tuple[MobileUserModel, MobileUserModel]:
    workspace_partner_user = MobileUserModel(
        id=uuid.uuid4(),
        auth_realm_id=customer_realm_id,
        email="workspace-partner@example.com",
        password_hash="not-used",
        status="active",
        is_active=True,
        is_partner=True,
        partner_account_id=workspace_id,
        referral_code="PARTNER42",
    )
    customer_user = MobileUserModel(
        id=uuid.uuid4(),
        auth_realm_id=customer_realm_id,
        email="customer@example.com",
        password_hash="not-used",
        status="active",
        is_active=True,
        referral_code="CUSTOM42",
    )
    session.add_all([workspace_partner_user, customer_user])
    session.commit()
    return workspace_partner_user, customer_user


def _seed_order_lineage(
    *,
    session,
    customer_user_id: uuid.UUID,
    customer_realm_id: uuid.UUID,
    storefront_id: uuid.UUID,
    merchant_profile_id: uuid.UUID,
    invoice_profile_id: uuid.UUID,
    billing_descriptor_id: uuid.UUID,
    partner_account_id: uuid.UUID,
    partner_code_id: uuid.UUID,
    created_at: datetime,
    commissionability_status: str,
    dispute_outcome_class: str | None = None,
) -> OrderModel:
    quote_session = QuoteSessionModel(
        id=uuid.uuid4(),
        user_id=customer_user_id,
        auth_realm_id=customer_realm_id,
        storefront_id=storefront_id,
        merchant_profile_id=merchant_profile_id,
        invoice_profile_id=invoice_profile_id,
        billing_descriptor_id=billing_descriptor_id,
        sale_channel="web",
        currency_code="USD",
        quote_status="open",
        partner_code_id=partner_code_id,
        request_snapshot={"surface": "partner-storefront"},
        quote_snapshot={"catalog": "default"},
        context_snapshot={"storefront_origin": str(storefront_id)},
        expires_at=created_at + timedelta(hours=1),
        created_at=created_at,
        updated_at=created_at,
    )
    checkout_session = CheckoutSessionModel(
        id=uuid.uuid4(),
        quote_session_id=quote_session.id,
        user_id=customer_user_id,
        auth_realm_id=customer_realm_id,
        storefront_id=storefront_id,
        merchant_profile_id=merchant_profile_id,
        invoice_profile_id=invoice_profile_id,
        billing_descriptor_id=billing_descriptor_id,
        sale_channel="web",
        currency_code="USD",
        checkout_status="open",
        idempotency_key=f"checkout-{quote_session.id}",
        partner_code_id=partner_code_id,
        request_snapshot={"surface": "partner-storefront"},
        checkout_snapshot={"catalog": "default"},
        context_snapshot={"storefront_origin": str(storefront_id)},
        expires_at=created_at + timedelta(hours=1),
        created_at=created_at,
        updated_at=created_at,
    )
    order = OrderModel(
        id=uuid.uuid4(),
        quote_session_id=quote_session.id,
        checkout_session_id=checkout_session.id,
        user_id=customer_user_id,
        auth_realm_id=customer_realm_id,
        storefront_id=storefront_id,
        merchant_profile_id=merchant_profile_id,
        invoice_profile_id=invoice_profile_id,
        billing_descriptor_id=billing_descriptor_id,
        partner_code_id=partner_code_id,
        sale_channel="web",
        currency_code="USD",
        order_status="committed",
        settlement_status="paid",
        base_price=Decimal("100.00"),
        addon_amount=Decimal("0.00"),
        displayed_price=Decimal("100.00"),
        discount_amount=Decimal("0.00"),
        wallet_amount=Decimal("0.00"),
        gateway_amount=Decimal("100.00"),
        partner_markup=Decimal("15.00"),
        commission_base_amount=Decimal("85.00"),
        merchant_snapshot={"merchant_profile_id": str(merchant_profile_id)},
        pricing_snapshot={"pricebook_key": "default"},
        policy_snapshot={"stacking": "partner_only"},
        entitlements_snapshot={"channels": ["vpn"]},
        created_at=created_at,
        updated_at=created_at,
    )
    attribution_result = OrderAttributionResultModel(
        id=uuid.uuid4(),
        order_id=order.id,
        user_id=customer_user_id,
        auth_realm_id=customer_realm_id,
        storefront_id=storefront_id,
        owner_type="reseller",
        owner_source="persistent_reseller_binding",
        partner_account_id=partner_account_id,
        partner_code_id=partner_code_id,
        rule_path=["binding", "workspace"],
        evidence_snapshot={"binding": "reseller"},
        explainability_snapshot={"winner": "binding"},
        policy_snapshot={"lane": "reseller"},
        resolved_at=created_at,
        created_at=created_at,
    )
    evaluation = CommissionabilityEvaluationModel(
        id=uuid.uuid4(),
        order_id=order.id,
        commissionability_status=commissionability_status,
        reason_codes=["phase6_portal_overlay"],
        partner_context_present=True,
        program_allows_commissionability=True,
        positive_commission_base=True,
        paid_status=True,
        fully_refunded=False,
        open_payment_dispute_present=dispute_outcome_class == "open",
        risk_allowed=True,
        evaluation_snapshot={"source": "test"},
        explainability_snapshot={"source": "test"},
        evaluated_at=created_at,
        created_at=created_at,
        updated_at=created_at,
    )
    session.add_all([quote_session, checkout_session, order, attribution_result, evaluation])
    if dispute_outcome_class is not None:
        session.add(
            PaymentDisputeModel(
                id=uuid.uuid4(),
                order_id=order.id,
                provider="stripe",
                external_reference=f"dispute-{order.id}",
                subtype="chargeback",
                outcome_class=dispute_outcome_class,
                lifecycle_status="opened" if dispute_outcome_class == "open" else "closed",
                disputed_amount=Decimal("100.00"),
                fee_amount=Decimal("15.00"),
                fee_status="pending",
                currency_code="USD",
                reason_code="fraud",
                evidence_snapshot={"workspace_visible": True},
                provider_snapshot={"source": "test"},
                opened_at=created_at,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    session.commit()
    return order


def _seed_renewal_lineage_override(
    *,
    session,
    order_id: uuid.UUID,
    initial_order_id: uuid.UUID,
    customer_user_id: uuid.UUID,
    customer_realm_id: uuid.UUID,
    storefront_id: uuid.UUID,
    provenance_partner_account_id: uuid.UUID,
    provenance_partner_code_id: uuid.UUID,
    effective_partner_account_id: uuid.UUID,
    effective_partner_code_id: uuid.UUID,
    created_at: datetime,
) -> None:
    attribution_result = (
        session.query(OrderAttributionResultModel)
        .filter(OrderAttributionResultModel.order_id == order_id)
        .one()
    )
    attribution_result.partner_account_id = provenance_partner_account_id
    attribution_result.partner_code_id = provenance_partner_code_id
    attribution_result.owner_type = "affiliate"
    attribution_result.owner_source = "explicit_code"
    attribution_result.rule_path = ["explicit_code", "fallback_partner_code"]

    renewal_order = RenewalOrderModel(
        id=uuid.uuid4(),
        order_id=order_id,
        initial_order_id=initial_order_id,
        prior_order_id=initial_order_id,
        user_id=customer_user_id,
        auth_realm_id=customer_realm_id,
        storefront_id=storefront_id,
        renewal_sequence_number=1,
        renewal_mode="auto",
        provenance_owner_type="affiliate",
        provenance_owner_source="explicit_code",
        provenance_partner_account_id=provenance_partner_account_id,
        provenance_partner_code_id=provenance_partner_code_id,
        effective_owner_type="reseller",
        effective_owner_source="renewal_inheritance",
        effective_partner_account_id=effective_partner_account_id,
        effective_partner_code_id=effective_partner_code_id,
        payout_eligible=True,
        payout_block_reason_codes=[],
        lineage_snapshot={"source": "phase7-reporting-test"},
        explainability_snapshot={
            "effective_owner": {
                "reason_path": ["renewal_inheritance", "workspace_owner"],
            }
        },
        policy_snapshot={"renewal_commissionable": True},
        resolved_at=created_at,
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(renewal_order)
    session.commit()


def _seed_workspace_reporting_outbox(
    *,
    session,
    workspace_id: uuid.UUID,
    order_id: uuid.UUID,
    statement_id: uuid.UUID,
    occurred_at: datetime,
) -> None:
    order_event = OutboxEventModel(
        id=uuid.uuid4(),
        event_key=f"workspace-reporting-order:{order_id}",
        event_name="order.created",
        event_family="commerce",
        aggregate_type="order",
        aggregate_id=str(order_id),
        partition_key=str(workspace_id),
        schema_version=1,
        event_status="partially_published",
        event_payload={"order_id": str(order_id), "partner_account_id": str(workspace_id)},
        actor_context={},
        source_context={"scope": "workspace-reporting"},
        occurred_at=occurred_at,
        created_at=occurred_at,
        updated_at=occurred_at,
    )
    analytics_backlog = OutboxPublicationModel(
        id=uuid.uuid4(),
        outbox_event_id=order_event.id,
        consumer_key="analytics_mart",
        publication_status="submitted",
        attempts=1,
        next_attempt_at=occurred_at,
        submitted_at=occurred_at,
        created_at=occurred_at,
        updated_at=occurred_at,
    )
    replay_published = OutboxPublicationModel(
        id=uuid.uuid4(),
        outbox_event_id=order_event.id,
        consumer_key="operational_replay",
        publication_status="published",
        attempts=1,
        next_attempt_at=occurred_at,
        submitted_at=occurred_at,
        published_at=occurred_at,
        publication_payload={"replay_pack_id": "workspace-reporting"},
        created_at=occurred_at,
        updated_at=occurred_at,
    )
    statement_event = OutboxEventModel(
        id=uuid.uuid4(),
        event_key=f"workspace-reporting-statement:{statement_id}",
        event_name="settlement.statement.closed",
        event_family="settlement",
        aggregate_type="partner_statement",
        aggregate_id=str(statement_id),
        partition_key=str(workspace_id),
        schema_version=1,
        event_status="published",
        event_payload={"partner_statement_id": str(statement_id), "partner_account_id": str(workspace_id)},
        actor_context={},
        source_context={"scope": "workspace-reporting"},
        occurred_at=occurred_at,
        created_at=occurred_at,
        updated_at=occurred_at,
    )
    statement_analytics = OutboxPublicationModel(
        id=uuid.uuid4(),
        outbox_event_id=statement_event.id,
        consumer_key="analytics_mart",
        publication_status="published",
        attempts=1,
        next_attempt_at=occurred_at,
        submitted_at=occurred_at,
        published_at=occurred_at,
        publication_payload={"export_scope": "statement"},
        created_at=occurred_at,
        updated_at=occurred_at,
    )
    statement_replay = OutboxPublicationModel(
        id=uuid.uuid4(),
        outbox_event_id=statement_event.id,
        consumer_key="operational_replay",
        publication_status="published",
        attempts=1,
        next_attempt_at=occurred_at,
        submitted_at=occurred_at,
        published_at=occurred_at,
        publication_payload={"export_scope": "statement"},
        created_at=occurred_at,
        updated_at=occurred_at,
    )
    session.add_all(
        [
            order_event,
            analytics_backlog,
            replay_published,
            statement_event,
            statement_analytics,
            statement_replay,
        ]
    )
    session.commit()


@pytest.mark.asyncio
async def test_partner_workspace_reporting_and_cases_are_visible_to_workspace_members(
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
            with sessionmaker() as db:
                realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
                admin_realm = await realm_repo.get_or_create_default_realm("admin")
                customer_realm = await realm_repo.get_or_create_default_realm("customer")

                await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="portal_reporting_admin",
                    email="portal-reporting-admin@example.com",
                    password="PortalReportingAdmin123!",
                    role="admin",
                )
                owner_user = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="portal_reporting_owner",
                    email="portal-reporting-owner@example.com",
                    password="PortalReportingOwner123!",
                    role="viewer",
                )
                await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="portal_reporting_outsider",
                    email="portal-reporting-outsider@example.com",
                    password="PortalReportingOutsider123!",
                    role="viewer",
                )

            admin_token = await _login(async_client, "portal-reporting-admin@example.com", "PortalReportingAdmin123!")
            owner_token = await _login(async_client, "portal-reporting-owner@example.com", "PortalReportingOwner123!")
            outsider_token = await _login(
                async_client,
                "portal-reporting-outsider@example.com",
                "PortalReportingOutsider123!",
            )

            admin_headers = {"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"}
            owner_headers = {"Authorization": f"Bearer {owner_token}", "X-Auth-Realm": "admin"}
            outsider_headers = {"Authorization": f"Bearer {outsider_token}", "X-Auth-Realm": "admin"}

            workspace_id = await _create_workspace(
                async_client,
                admin_headers=admin_headers,
                owner_admin_user_id=str(owner_user.id),
            )
            workspace_uuid = uuid.UUID(workspace_id)

            with sessionmaker() as db:
                workspace = db.get(PartnerAccountModel, workspace_uuid)
                assert workspace is not None
                workspace.status = "needs_info"

                realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
                customer_realm = await realm_repo.get_or_create_default_realm("customer")
                _brand, invoice_profile, merchant_profile, billing_descriptor, storefront = _seed_storefront_context(
                    session=db,
                    customer_realm_id=customer_realm.id,
                )
                partner_user, customer_user = _seed_mobile_users(
                    session=db,
                    customer_realm_id=customer_realm.id,
                    workspace_id=workspace_uuid,
                )
                partner_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    partner_account_id=workspace_uuid,
                    partner_user_id=partner_user.id,
                    code="REPORT42",
                    markup_pct=Decimal("15.00"),
                    is_active=True,
                )
                legacy_partner_account = PartnerAccountModel(
                    id=uuid.uuid4(),
                    account_key="legacy-workspace",
                    display_name="Legacy Workspace",
                    status="active",
                    legacy_owner_user_id=partner_user.id,
                )
                legacy_partner_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    partner_account_id=legacy_partner_account.id,
                    partner_user_id=partner_user.id,
                    code="LEGACY42",
                    markup_pct=Decimal("10.00"),
                    is_active=True,
                )
                settlement_period = SettlementPeriodModel(
                    id=uuid.uuid4(),
                    partner_account_id=workspace_uuid,
                    period_key="2026-04",
                    period_status="closed",
                    currency_code="USD",
                    window_start=datetime(2026, 4, 1, tzinfo=UTC),
                    window_end=datetime(2026, 5, 1, tzinfo=UTC),
                )
                statement = PartnerStatementModel(
                    id=uuid.uuid4(),
                    partner_account_id=workspace_uuid,
                    settlement_period_id=settlement_period.id,
                    statement_key="portal-reporting-2026-04-v1",
                    statement_version=1,
                    statement_status="closed",
                    currency_code="USD",
                    accrual_amount=Decimal("150.00"),
                    on_hold_amount=Decimal("15.00"),
                    reserve_amount=Decimal("10.00"),
                    adjustment_net_amount=Decimal("0.00"),
                    available_amount=Decimal("125.00"),
                    source_event_count=2,
                    held_event_count=1,
                    active_reserve_count=1,
                    adjustment_count=0,
                    statement_snapshot={"source": "portal-reporting-test"},
                    updated_at=datetime(2026, 4, 18, 9, 0, tzinfo=UTC),
                )
                payout_account = PartnerPayoutAccountModel(
                    id=uuid.uuid4(),
                    partner_account_id=workspace_uuid,
                    payout_rail="crypto",
                    display_label="Primary USDT Wallet",
                    destination_reference="wallet-123",
                    masked_destination="wallet-***123",
                    destination_metadata={"network": "tron"},
                    verification_status="pending",
                    approval_status="pending",
                    account_status="active",
                    is_default=True,
                )
                db.add_all(
                    [
                        partner_code,
                        legacy_partner_account,
                        legacy_partner_code,
                        settlement_period,
                        statement,
                        payout_account,
                    ]
                )
                db.commit()

                first_order = _seed_order_lineage(
                    session=db,
                    customer_user_id=customer_user.id,
                    customer_realm_id=customer_realm.id,
                    storefront_id=storefront.id,
                    merchant_profile_id=merchant_profile.id,
                    invoice_profile_id=invoice_profile.id,
                    billing_descriptor_id=billing_descriptor.id,
                    partner_account_id=workspace_uuid,
                    partner_code_id=partner_code.id,
                    created_at=datetime(2026, 4, 18, 8, 0, tzinfo=UTC),
                    commissionability_status="eligible",
                )
                renewal_order = _seed_order_lineage(
                    session=db,
                    customer_user_id=customer_user.id,
                    customer_realm_id=customer_realm.id,
                    storefront_id=storefront.id,
                    merchant_profile_id=merchant_profile.id,
                    invoice_profile_id=invoice_profile.id,
                    billing_descriptor_id=billing_descriptor.id,
                    partner_account_id=workspace_uuid,
                    partner_code_id=partner_code.id,
                    created_at=datetime(2026, 4, 18, 9, 0, tzinfo=UTC),
                    commissionability_status="eligible",
                )
                chargeback_order = _seed_order_lineage(
                    session=db,
                    customer_user_id=customer_user.id,
                    customer_realm_id=customer_realm.id,
                    storefront_id=storefront.id,
                    merchant_profile_id=merchant_profile.id,
                    invoice_profile_id=invoice_profile.id,
                    billing_descriptor_id=billing_descriptor.id,
                    partner_account_id=workspace_uuid,
                    partner_code_id=partner_code.id,
                    created_at=datetime(2026, 4, 18, 10, 0, tzinfo=UTC),
                    commissionability_status="pending",
                    dispute_outcome_class="open",
                )
                _seed_renewal_lineage_override(
                    session=db,
                    order_id=renewal_order.id,
                    initial_order_id=first_order.id,
                    customer_user_id=customer_user.id,
                    customer_realm_id=customer_realm.id,
                    storefront_id=storefront.id,
                    provenance_partner_account_id=legacy_partner_account.id,
                    provenance_partner_code_id=legacy_partner_code.id,
                    effective_partner_account_id=workspace_uuid,
                    effective_partner_code_id=partner_code.id,
                    created_at=datetime(2026, 4, 18, 9, 5, tzinfo=UTC),
                )
                _seed_workspace_reporting_outbox(
                    session=db,
                    workspace_id=workspace_uuid,
                    order_id=renewal_order.id,
                    statement_id=statement.id,
                    occurred_at=datetime(2026, 4, 18, 11, 0, tzinfo=UTC),
                )
                chargeback_payment_dispute = next(
                    dispute
                    for dispute in db.query(PaymentDisputeModel).all()
                    if dispute.order_id == chargeback_order.id
                )
                db.add_all(
                    [
                        PartnerTrafficDeclarationModel(
                            id=uuid.uuid4(),
                            partner_account_id=workspace_uuid,
                            declaration_kind="approved_sources",
                            declaration_status="action_required",
                            scope_label="Workspace-owned traffic sources",
                            declaration_payload={"channels": ["seo", "direct"]},
                            notes_payload=["Traffic source clarification is still required before expansion."],
                            submitted_by_admin_user_id=owner_user.id,
                            updated_at=datetime(2026, 4, 18, 12, 0, tzinfo=UTC),
                        ),
                        PartnerTrafficDeclarationModel(
                            id=uuid.uuid4(),
                            partner_account_id=workspace_uuid,
                            declaration_kind="postback_readiness",
                            declaration_status="action_required",
                            scope_label="Tracking and postback handoff",
                            declaration_payload={"destination": "https://partner.example/postback"},
                            notes_payload=["Postback configuration still needs explicit review."],
                            submitted_by_admin_user_id=owner_user.id,
                            updated_at=datetime(2026, 4, 18, 12, 5, tzinfo=UTC),
                        ),
                        CreativeApprovalModel(
                            id=uuid.uuid4(),
                            partner_account_id=workspace_uuid,
                            approval_kind="creative_approval",
                            approval_status="action_required",
                            scope_label="Creative and claims posture",
                            creative_ref="banner-42",
                            approval_payload={"claim_family": "performance"},
                            notes_payload=["Creative requires explicit claims review."],
                            submitted_by_admin_user_id=owner_user.id,
                            reviewed_by_admin_user_id=owner_user.id,
                            reviewed_at=datetime(2026, 4, 18, 12, 10, tzinfo=UTC),
                            updated_at=datetime(2026, 4, 18, 12, 10, tzinfo=UTC),
                        ),
                        DisputeCaseModel(
                            id=uuid.uuid4(),
                            partner_account_id=workspace_uuid,
                            payment_dispute_id=chargeback_payment_dispute.id,
                            order_id=chargeback_order.id,
                            case_kind="payout_dispute",
                            case_status="waiting_on_ops",
                            summary="Chargeback evidence review is still in progress.",
                            case_payload={"lane": "reseller"},
                            notes_payload=["Ops is reviewing dispute evidence before settlement release."],
                            opened_by_admin_user_id=owner_user.id,
                            updated_at=datetime(2026, 4, 18, 12, 15, tzinfo=UTC),
                        ),
                    ]
                )
                db.commit()

            workspace_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}",
                headers=owner_headers,
            )
            assert workspace_response.status_code == 200
            assert workspace_response.json()["current_role_key"] == "owner"

            conversions_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/conversion-records",
                headers=owner_headers,
            )
            assert conversions_response.status_code == 200
            conversions_payload = conversions_response.json()
            assert len(conversions_payload) == 3
            assert conversions_payload[0]["kind"] == "chargeback"
            assert conversions_payload[0]["status"] == "on_hold"
            assert conversions_payload[0]["id"] == str(chargeback_order.id)
            assert conversions_payload[0]["code_label"] == "REPORT42"
            assert conversions_payload[0]["customer_scope"] == "workspace_scoped"
            renewal_conversion = next(
                item for item in conversions_payload if item["id"] == str(renewal_order.id)
            )
            assert renewal_conversion["kind"] == "repeat_paid"
            assert renewal_conversion["code_label"] == "REPORT42"
            assert any("Renewal lineage keeps this paid conversion" in note for note in renewal_conversion["notes"])

            analytics_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/analytics-metrics",
                headers=owner_headers,
            )
            assert analytics_response.status_code == 200
            analytics_payload = {item["key"]: item for item in analytics_response.json()}
            assert analytics_payload["first_paid"]["value"] == "1"
            assert analytics_payload["repeat_paid"]["value"] == "1"
            assert analytics_payload["chargeback_rate"]["value"] == "0.00%"
            assert analytics_payload["earnings_available"]["value"] == "125.00 USD"
            assert any(
                "Reporting publication backlog detected: 1." in note
                for note in analytics_payload["earnings_available"]["notes"]
            )

            exports_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/report-exports",
                headers=owner_headers,
            )
            assert exports_response.status_code == 200
            exports_payload = {item["kind"]: item for item in exports_response.json()}
            assert exports_payload["statement_export"]["status"] == "scheduled"
            assert exports_payload["statement_export"]["available_actions"] == ["schedule_export"]
            assert exports_payload["statement_export"]["thread_events"] == []
            assert exports_payload["statement_export"]["last_requested_at"] is None
            assert exports_payload["payout_status_export"]["status"] == "available"
            assert exports_payload["explainability_report"]["status"] == "scheduled"

            schedule_export_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/report-exports/statement-export/schedule",
                headers=owner_headers,
                json={
                    "message": "Please stage the next statement export snapshot.",
                    "request_payload": {
                        "request_origin": "partner_portal_reporting_surface",
                        "delivery_mode": "download_link",
                    },
                },
            )
            assert schedule_export_response.status_code == 201
            scheduled_export_payload = schedule_export_response.json()
            assert scheduled_export_payload["id"] == "statement-export"
            assert scheduled_export_payload["available_actions"] == ["schedule_export"]
            assert scheduled_export_payload["last_requested_at"] is not None
            assert len(scheduled_export_payload["thread_events"]) == 1
            assert scheduled_export_payload["thread_events"][0]["action_kind"] == "partner_export_requested"
            assert (
                scheduled_export_payload["thread_events"][0]["message"]
                == "Please stage the next statement export snapshot."
            )

            explainability_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/conversion-records/{renewal_order.id}/explainability",
                headers=owner_headers,
            )
            assert explainability_response.status_code == 200
            explainability_payload = explainability_response.json()
            assert explainability_payload["order"]["id"] == str(renewal_order.id)
            assert (
                explainability_payload["explainability"]["commercial_resolution_summary"]["resolved_owner_source"]
                == "renewal_inheritance"
            )
            assert explainability_payload["explainability"]["lane_views"]["renewal_chain"]["active"] is True

            review_requests_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/review-requests",
                headers=owner_headers,
            )
            assert review_requests_response.status_code == 200
            review_requests_payload = {item["kind"]: item for item in review_requests_response.json()}
            assert review_requests_payload["business_profile"]["status"] == "open"
            assert review_requests_payload["finance_profile"]["status"] == "open"

            traffic_declarations_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/traffic-declarations",
                headers=owner_headers,
            )
            assert traffic_declarations_response.status_code == 200
            traffic_declarations_payload = {
                item["kind"]: item for item in traffic_declarations_response.json()
            }
            assert traffic_declarations_payload["approved_sources"]["status"] == "action_required"
            assert traffic_declarations_payload["approved_sources"]["scope_label"] == "Workspace-owned traffic sources"
            assert traffic_declarations_payload["postback_readiness"]["status"] == "action_required"
            assert traffic_declarations_payload["creative_approval"]["status"] == "action_required"
            assert any(
                "Creative requires explicit claims review." in note
                for note in traffic_declarations_payload["creative_approval"]["notes"]
            )

            cases_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/cases",
                headers=owner_headers,
            )
            assert cases_response.status_code == 200
            cases_payload = {item["kind"]: item for item in cases_response.json()}
            assert "requested_info" in cases_payload
            assert "finance_onboarding" in cases_payload
            assert "statement_question" in cases_payload
            assert "payout_dispute" in cases_payload
            assert any(
                "Chargeback evidence review is still in progress." in note
                for note in cases_payload["payout_dispute"]["notes"]
            )

            for suffix in (
                "conversion-records",
                "analytics-metrics",
                "report-exports",
                f"conversion-records/{renewal_order.id}/explainability",
                "review-requests",
                "traffic-declarations",
                "cases",
            ):
                outsider_response = await async_client.get(
                    f"/api/v1/partner-workspaces/{workspace_id}/{suffix}",
                    headers=outsider_headers,
                )
                assert outsider_response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
