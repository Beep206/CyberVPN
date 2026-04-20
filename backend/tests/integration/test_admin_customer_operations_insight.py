from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.access_delivery_channel_model import (
    AccessDeliveryChannelModel,
)
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.device_credential_model import DeviceCredentialModel
from src.infrastructure.database.models.dispute_case_model import DisputeCaseModel
from src.infrastructure.database.models.entitlement_grant_model import EntitlementGrantModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeModel
from src.infrastructure.database.models.partner_payout_account_model import (
    PartnerPayoutAccountModel,
)
from src.infrastructure.database.models.partner_statement_model import PartnerStatementModel
from src.infrastructure.database.models.payment_dispute_model import PaymentDisputeModel
from src.infrastructure.database.models.payout_execution_model import PayoutExecutionModel
from src.infrastructure.database.models.payout_instruction_model import PayoutInstructionModel
from src.infrastructure.database.models.provisioning_profile_model import (
    ProvisioningProfileModel,
)
from src.infrastructure.database.models.risk_review_model import RiskReviewModel
from src.infrastructure.database.models.risk_subject_model import RiskSubjectModel
from src.infrastructure.database.models.service_identity_model import ServiceIdentityModel
from src.infrastructure.database.models.settlement_period_model import SettlementPeriodModel
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
from tests.integration.test_order_commit import _seed_order_context
from tests.integration.test_partner_portal_reporting_reads import _seed_order_lineage

pytestmark = [pytest.mark.integration]


def _make_admin_access_token(
    auth_service: AuthService,
    *,
    user_id: uuid.UUID,
    admin_realm,
) -> str:
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


async def _seed_customer_operations_context(sessionmaker, auth_service: AuthService) -> dict[str, str]:
    seeded = await _seed_order_context(sessionmaker, auth_service)
    now = datetime.now(UTC) - timedelta(minutes=5)

    with sessionmaker() as db:
        realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
        admin_realm = await realm_repo.get_or_create_default_realm("admin")

        admin_user = AdminUserModel(
            login="customer_ops_admin",
            email="customer-ops-admin@example.com",
            auth_realm_id=admin_realm.id,
            password_hash=await auth_service.hash_password("CustomerOpsAdmin123!"),
            role="admin",
            is_active=True,
            is_email_verified=True,
        )
        support_user = AdminUserModel(
            login="customer_ops_support",
            email="customer-ops-support@example.com",
            auth_realm_id=admin_realm.id,
            password_hash=await auth_service.hash_password("CustomerOpsSupport123!"),
            role="support",
            is_active=True,
            is_email_verified=True,
        )
        db.add_all([admin_user, support_user])
        db.flush()

        customer_realm_id = uuid.UUID(seeded["customer_realm_id"])
        customer_user_id = uuid.UUID(seeded["customer_user_id"])
        storefront_id = uuid.UUID(seeded["storefront_id"])
        merchant_profile_id = uuid.UUID(seeded["merchant_profile_id"])
        invoice_profile_id = uuid.UUID(seeded["invoice_profile_id"])
        billing_descriptor_id = uuid.UUID(seeded["billing_descriptor_id"])

        workspace = PartnerAccountModel(
            id=uuid.uuid4(),
            account_key="customer-ops-workspace",
            display_name="Customer Ops Workspace",
            status="active",
            legacy_owner_user_id=customer_user_id,
            created_by_admin_user_id=admin_user.id,
        )
        reseller_code = PartnerCodeModel(
            id=uuid.uuid4(),
            code="OPSRESELLER1",
            partner_account_id=workspace.id,
            partner_user_id=customer_user_id,
            markup_pct=Decimal("15.00"),
            is_active=True,
        )
        db.add_all([workspace, reseller_code])
        db.flush()

        order = _seed_order_lineage(
            session=db,
            customer_user_id=customer_user_id,
            customer_realm_id=customer_realm_id,
            storefront_id=storefront_id,
            merchant_profile_id=merchant_profile_id,
            invoice_profile_id=invoice_profile_id,
            billing_descriptor_id=billing_descriptor_id,
            partner_account_id=workspace.id,
            partner_code_id=reseller_code.id,
            created_at=now,
            commissionability_status="eligible",
            dispute_outcome_class="open",
        )
        payment_dispute = db.execute(
            select(PaymentDisputeModel).where(PaymentDisputeModel.order_id == order.id)
        ).scalar_one()
        dispute_case = DisputeCaseModel(
            id=uuid.uuid4(),
            partner_account_id=workspace.id,
            payment_dispute_id=payment_dispute.id,
            order_id=order.id,
            case_kind="evidence_collection",
            case_status="waiting_on_ops",
            summary="Collect provider evidence for customer ops dispute",
            case_payload={"requested_artifacts": ["receipt", "provider_email"]},
            notes_payload=["Initial evidence request opened by admin"],
            opened_by_admin_user_id=admin_user.id,
            assigned_to_admin_user_id=admin_user.id,
        )

        service_identity = ServiceIdentityModel(
            id=uuid.uuid4(),
            service_key="svc_customer_ops",
            customer_account_id=customer_user_id,
            auth_realm_id=customer_realm_id,
            source_order_id=order.id,
            origin_storefront_id=storefront_id,
            provider_name="remnawave",
            provider_subject_ref="remnawave-customer-ops",
            identity_status="active",
            service_context={"legacy_subscription_url": "https://sub.example.test/customer-ops"},
        )
        provisioning_profile = ProvisioningProfileModel(
            id=uuid.uuid4(),
            service_identity_id=service_identity.id,
            profile_key="shared_client-default",
            target_channel="shared_client",
            delivery_method="shared_link",
            profile_status="active",
            provider_name="remnawave",
            provider_profile_ref="profile-customer-ops",
            provisioning_payload={"config_url": "https://sub.example.test/customer-ops"},
        )
        device_credential = DeviceCredentialModel(
            id=uuid.uuid4(),
            credential_key="cred_customer_ops",
            service_identity_id=service_identity.id,
            auth_realm_id=customer_realm_id,
            origin_storefront_id=storefront_id,
            provisioning_profile_id=provisioning_profile.id,
            credential_type="desktop_client",
            credential_status="active",
            subject_key="desktop-customer-ops",
            provider_name="remnawave",
            provider_credential_ref="cred-provider-customer-ops",
            credential_context={"platform": "desktop"},
            issued_at=now,
        )
        access_delivery_channel = AccessDeliveryChannelModel(
            id=uuid.uuid4(),
            delivery_key="delivery_customer_ops",
            service_identity_id=service_identity.id,
            auth_realm_id=customer_realm_id,
            origin_storefront_id=storefront_id,
            provisioning_profile_id=provisioning_profile.id,
            device_credential_id=device_credential.id,
            channel_type="shared_client",
            channel_status="active",
            channel_subject_ref="desktop-customer-ops",
            provider_name="remnawave",
            delivery_context={"surface": "desktop"},
            delivery_payload={"config_url": "https://sub.example.test/customer-ops"},
            last_delivered_at=now,
        )
        entitlement_grant = EntitlementGrantModel(
            id=uuid.uuid4(),
            grant_key="grant_customer_ops",
            service_identity_id=service_identity.id,
            customer_account_id=customer_user_id,
            auth_realm_id=customer_realm_id,
            origin_storefront_id=storefront_id,
            source_type="order",
            source_order_id=order.id,
            grant_status="active",
            grant_snapshot={"status": "active", "access_window": "paid"},
            source_snapshot={"source_order_id": str(order.id)},
            effective_from=now - timedelta(days=1),
            expires_at=now + timedelta(days=30),
            created_by_admin_user_id=admin_user.id,
            activated_at=now,
            activated_by_admin_user_id=admin_user.id,
        )

        risk_subject = RiskSubjectModel(
            id=uuid.uuid4(),
            principal_class="customer",
            principal_subject=str(customer_user_id),
            auth_realm_id=customer_realm_id,
            storefront_id=storefront_id,
            status="active",
            risk_level="medium",
            metadata_payload={"seed": "customer-ops"},
        )
        risk_review = RiskReviewModel(
            id=uuid.uuid4(),
            risk_subject_id=risk_subject.id,
            review_type="manual_review",
            status="open",
            decision="pending",
            reason="Customer ops review",
            evidence={"ticket": "OPS-42"},
            created_by_admin_user_id=admin_user.id,
        )

        settlement_period = SettlementPeriodModel(
            id=uuid.uuid4(),
            partner_account_id=workspace.id,
            period_key="2026-04-customer-ops",
            period_status="closed",
            currency_code="USD",
            window_start=now - timedelta(days=30),
            window_end=now,
            closed_at=now,
            closed_by_admin_user_id=admin_user.id,
        )
        statement = PartnerStatementModel(
            id=uuid.uuid4(),
            partner_account_id=workspace.id,
            settlement_period_id=settlement_period.id,
            statement_key="stmt_customer_ops",
            statement_version=1,
            statement_status="closed",
            currency_code="USD",
            accrual_amount=Decimal("25.00"),
            on_hold_amount=Decimal("0.00"),
            reserve_amount=Decimal("5.00"),
            adjustment_net_amount=Decimal("0.00"),
            available_amount=Decimal("20.00"),
            source_event_count=1,
            held_event_count=0,
            active_reserve_count=1,
            adjustment_count=0,
            statement_snapshot={"orders": [str(order.id)]},
            closed_at=now,
            closed_by_admin_user_id=admin_user.id,
        )
        payout_account = PartnerPayoutAccountModel(
            id=uuid.uuid4(),
            partner_account_id=workspace.id,
            payout_rail="bank_transfer",
            display_label="Primary USD Account",
            destination_reference="US1234567890",
            masked_destination="****7890",
            destination_metadata={"bank_name": "Cyber Bank"},
            verification_status="verified",
            approval_status="approved",
            account_status="active",
            is_default=True,
            created_by_admin_user_id=admin_user.id,
            verified_by_admin_user_id=admin_user.id,
            verified_at=now,
            approved_by_admin_user_id=admin_user.id,
            approved_at=now,
            default_selected_by_admin_user_id=admin_user.id,
            default_selected_at=now,
        )
        payout_instruction = PayoutInstructionModel(
            id=uuid.uuid4(),
            partner_account_id=workspace.id,
            partner_statement_id=statement.id,
            partner_payout_account_id=payout_account.id,
            instruction_key="pi_customer_ops",
            instruction_status="completed",
            payout_amount=Decimal("20.00"),
            currency_code="USD",
            instruction_snapshot={"statement_id": str(statement.id)},
            created_by_admin_user_id=admin_user.id,
            approved_by_admin_user_id=admin_user.id,
            approved_at=now,
            completed_at=now,
        )
        payout_execution = PayoutExecutionModel(
            id=uuid.uuid4(),
            payout_instruction_id=payout_instruction.id,
            partner_account_id=workspace.id,
            partner_statement_id=statement.id,
            partner_payout_account_id=payout_account.id,
            execution_key="pe_customer_ops",
            execution_mode="dry_run",
            execution_status="reconciled",
            request_idempotency_key="ops-customer-payout",
            external_reference="external-customer-ops",
            execution_payload={"mode": "dry_run"},
            result_payload={"status": "ok"},
            requested_by_admin_user_id=admin_user.id,
            submitted_by_admin_user_id=admin_user.id,
            submitted_at=now,
            completed_by_admin_user_id=admin_user.id,
            completed_at=now,
            reconciled_by_admin_user_id=admin_user.id,
            reconciled_at=now,
        )

        db.add_all(
            [
                service_identity,
                provisioning_profile,
                device_credential,
                access_delivery_channel,
                entitlement_grant,
                risk_subject,
                risk_review,
                dispute_case,
                settlement_period,
                statement,
                payout_account,
                payout_instruction,
                payout_execution,
            ]
        )
        db.commit()

        return {
            "user_id": str(customer_user_id),
            "admin_token": _make_admin_access_token(
                auth_service,
                user_id=admin_user.id,
                admin_realm=admin_realm,
            ),
            "support_token": _make_admin_access_token(
                auth_service,
                user_id=support_user.id,
                admin_realm=admin_realm,
            ),
            "admin_id": str(admin_user.id),
            "support_admin_id": str(support_user.id),
            "workspace_id": str(workspace.id),
            "order_id": str(order.id),
            "statement_id": str(statement.id),
            "payout_instruction_id": str(payout_instruction.id),
            "payout_execution_id": str(payout_execution.id),
        }


@pytest.mark.asyncio
async def test_admin_customer_operations_insight_returns_full_role_scoped_payload(
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
            seeded = await _seed_customer_operations_context(sessionmaker, auth_service)
            response = await async_client.get(
                f"/api/v1/admin/mobile-users/{seeded['user_id']}/operations-insight",
                headers={
                    "Authorization": f"Bearer {seeded['admin_token']}",
                    "X-Auth-Realm": "admin",
                },
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["section_access"] == {
                "explainability_visible": True,
                "finance_visible": True,
                "finance_actions_visible": True,
                "risk_visible": True,
            }
            assert len(payload["order_insights"]) == 1
            assert payload["order_insights"][0]["attribution_result"]["owner_type"] == "reseller"
            assert payload["order_insights"][0]["resolved_partner_account_id"] == seeded["workspace_id"]
            assert len(payload["order_insights"][0]["payment_disputes"]) == 1
            assert len(payload["order_insights"][0]["dispute_cases"]) == 1
            assert payload["order_insights"][0]["dispute_cases"][0]["case_status"] == "waiting_on_ops"
            assert len(payload["settlement_workspaces"]) == 1
            assert payload["settlement_workspaces"][0]["partner_account_id"] == seeded["workspace_id"]
            assert len(payload["settlement_workspaces"][0]["payout_accounts"]) == 1
            assert len(payload["settlement_workspaces"][0]["partner_statements"]) == 1
            assert len(payload["settlement_workspaces"][0]["payout_instructions"]) == 1
            assert len(payload["settlement_workspaces"][0]["payout_executions"]) == 1
            assert len(payload["service_access_insights"]) == 1
            assert payload["service_access_insights"][0]["service_state"]["purchase_context"]["source_order_id"] == (
                seeded["order_id"]
            )
            assert len(payload["risk_subject_insights"]) == 1
            assert len(payload["risk_subject_insights"][0]["reviews"]) == 1
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_support_customer_operations_insight_hides_finance_and_risk_sections(
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
            seeded = await _seed_customer_operations_context(sessionmaker, auth_service)
            response = await async_client.get(
                f"/api/v1/admin/mobile-users/{seeded['user_id']}/operations-insight",
                headers={
                    "Authorization": f"Bearer {seeded['support_token']}",
                    "X-Auth-Realm": "admin",
                },
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["section_access"] == {
                "explainability_visible": True,
                "finance_visible": False,
                "finance_actions_visible": False,
                "risk_visible": False,
            }
            assert len(payload["order_insights"]) == 1
            assert payload["order_insights"][0]["payment_disputes"] == []
            assert payload["order_insights"][0]["dispute_cases"] == []
            assert payload["settlement_workspaces"] == []
            assert len(payload["service_access_insights"]) == 1
            assert payload["risk_subject_insights"] == []
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_admin_customer_operations_action_executes_canonical_maker_checker_flow(
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
            seeded = await _seed_customer_operations_context(sessionmaker, auth_service)

            with sessionmaker() as db:
                now = datetime.now(UTC)
                pending_period = SettlementPeriodModel(
                    id=uuid.uuid4(),
                    partner_account_id=uuid.UUID(seeded["workspace_id"]),
                    period_key="2026-05-customer-ops-pending",
                    period_status="closed",
                    currency_code="USD",
                    window_start=now - timedelta(days=15),
                    window_end=now,
                    closed_at=now,
                    closed_by_admin_user_id=uuid.UUID(seeded["support_admin_id"]),
                )
                pending_statement = PartnerStatementModel(
                    id=uuid.uuid4(),
                    partner_account_id=uuid.UUID(seeded["workspace_id"]),
                    settlement_period_id=pending_period.id,
                    statement_key="stmt_customer_ops_pending",
                    statement_version=1,
                    statement_status="closed",
                    currency_code="USD",
                    accrual_amount=Decimal("12.50"),
                    on_hold_amount=Decimal("0.00"),
                    reserve_amount=Decimal("0.00"),
                    adjustment_net_amount=Decimal("0.00"),
                    available_amount=Decimal("12.50"),
                    source_event_count=1,
                    held_event_count=0,
                    active_reserve_count=0,
                    adjustment_count=0,
                    statement_snapshot={"orders": [seeded["order_id"]]},
                    closed_at=now,
                    closed_by_admin_user_id=uuid.UUID(seeded["support_admin_id"]),
                )
                pending_payout_account = PartnerPayoutAccountModel(
                    id=uuid.uuid4(),
                    partner_account_id=uuid.UUID(seeded["workspace_id"]),
                    settlement_profile_id=None,
                    payout_rail="bank_transfer",
                    display_label="Secondary USD Account",
                    destination_reference="US0099887766554433",
                    masked_destination="US00...4433",
                    destination_metadata={"bank": "Example Bank"},
                    verification_status="pending",
                    approval_status="pending",
                    account_status="active",
                    is_default=False,
                    created_by_admin_user_id=uuid.UUID(seeded["support_admin_id"]),
                )
                pending_instruction = PayoutInstructionModel(
                    id=uuid.uuid4(),
                    partner_account_id=uuid.UUID(seeded["workspace_id"]),
                    partner_statement_id=pending_statement.id,
                    partner_payout_account_id=pending_payout_account.id,
                    instruction_key="stmt_customer_ops:pending_approval",
                    instruction_status="pending_approval",
                    payout_amount=Decimal("12.50"),
                    currency_code="USD",
                    instruction_snapshot={"seed": "customer-ops"},
                    created_by_admin_user_id=uuid.UUID(seeded["support_admin_id"]),
                )
                db.add_all([pending_period, pending_statement, pending_payout_account, pending_instruction])
                db.commit()

            read_response = await async_client.get(
                f"/api/v1/admin/mobile-users/{seeded['user_id']}/operations-insight",
                headers={
                    "Authorization": f"Bearer {seeded['admin_token']}",
                    "X-Auth-Realm": "admin",
                },
            )
            assert read_response.status_code == 200
            read_payload = read_response.json()
            workspace_payload = read_payload["settlement_workspaces"][0]
            assert workspace_payload["payout_account_actions"][str(pending_payout_account.id)] == [
                "verify_payout_account",
                "suspend_payout_account",
            ]
            assert workspace_payload["payout_instruction_actions"][str(pending_instruction.id)] == [
                "approve_payout_instruction",
                "reject_payout_instruction",
            ]

            verify_response = await async_client.post(
                f"/api/v1/admin/mobile-users/{seeded['user_id']}/operations-insight/actions",
                headers={
                    "Authorization": f"Bearer {seeded['admin_token']}",
                    "X-Auth-Realm": "admin",
                },
                json={
                    "action_kind": "verify_payout_account",
                    "payout_account_id": str(pending_payout_account.id),
                },
            )
            assert verify_response.status_code == 200
            verify_payload = verify_response.json()
            assert verify_payload["action_kind"] == "verify_payout_account"
            assert verify_payload["target_kind"] == "payout_account"
            assert verify_payload["target_id"] == str(pending_payout_account.id)
            assert verify_payload["payout_account"]["verification_status"] == "verified"
            assert verify_payload["payout_account"]["approval_status"] == "approved"
            assert verify_payload["payout_account"]["account_status"] == "active"
            assert verify_payload["payout_instruction"] is None

            approve_response = await async_client.post(
                f"/api/v1/admin/mobile-users/{seeded['user_id']}/operations-insight/actions",
                headers={
                    "Authorization": f"Bearer {seeded['admin_token']}",
                    "X-Auth-Realm": "admin",
                },
                json={
                    "action_kind": "approve_payout_instruction",
                    "payout_instruction_id": str(pending_instruction.id),
                },
            )
            assert approve_response.status_code == 200
            approve_payload = approve_response.json()
            assert approve_payload["action_kind"] == "approve_payout_instruction"
            assert approve_payload["target_kind"] == "payout_instruction"
            assert approve_payload["target_id"] == str(pending_instruction.id)
            assert approve_payload["payout_instruction"]["instruction_status"] == "approved"
            assert approve_payload["payout_instruction"]["approved_by_admin_user_id"] == seeded["admin_id"]
            assert approve_payload["payout_account"] is None
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_admin_customer_operations_exports_return_role_scoped_download_payloads(
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
            seeded = await _seed_customer_operations_context(sessionmaker, auth_service)
            headers = {
                "Authorization": f"Bearer {seeded['admin_token']}",
                "X-Auth-Realm": "admin",
            }

            workspace_response = await async_client.get(
                f"/api/v1/admin/mobile-users/{seeded['user_id']}/operations-insight/exports/workspaces/{seeded['workspace_id']}",
                headers=headers,
            )
            assert workspace_response.status_code == 200
            assert "attachment;" in workspace_response.headers["content-disposition"]
            workspace_payload = workspace_response.json()
            assert workspace_payload["export_kind"] == "workspace_finance_evidence"
            assert workspace_payload["partner_account_id"] == seeded["workspace_id"]
            assert workspace_payload["scope"]["statement_ids"] == [seeded["statement_id"]]
            assert len(workspace_payload["evidence"]["workspace"]["partner_statements"]) == 1
            assert len(workspace_payload["evidence"]["order_insights"]) == 1

            statement_response = await async_client.get(
                f"/api/v1/admin/mobile-users/{seeded['user_id']}/operations-insight/exports/partner-statements/{seeded['statement_id']}",
                headers=headers,
            )
            assert statement_response.status_code == 200
            statement_payload = statement_response.json()
            assert statement_payload["export_kind"] == "partner_statement_evidence"
            assert statement_payload["evidence"]["statement"]["id"] == seeded["statement_id"]
            assert len(statement_payload["evidence"]["payout_instructions"]) == 1
            assert len(statement_payload["evidence"]["payout_executions"]) == 1

            execution_response = await async_client.get(
                f"/api/v1/admin/mobile-users/{seeded['user_id']}/operations-insight/exports/payout-executions/{seeded['payout_execution_id']}",
                headers=headers,
            )
            assert execution_response.status_code == 200
            execution_payload = execution_response.json()
            assert execution_payload["export_kind"] == "payout_execution_evidence"
            assert execution_payload["evidence"]["payout_execution"]["id"] == seeded["payout_execution_id"]
            assert execution_payload["evidence"]["payout_instruction"]["id"] == seeded["payout_instruction_id"]
            assert execution_payload["evidence"]["partner_statement"]["id"] == seeded["statement_id"]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
