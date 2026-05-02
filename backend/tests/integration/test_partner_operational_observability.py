from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from prometheus_client import REGISTRY

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeModel
from src.infrastructure.database.models.partner_payout_account_model import PartnerPayoutAccountModel
from src.infrastructure.database.models.partner_statement_model import PartnerStatementModel
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
from tests.integration.test_order_attribution_resolution import _create_quote_checkout
from tests.integration.test_order_commit import _make_customer_access_token, _seed_order_context

pytestmark = [pytest.mark.integration]


def _metric_value(name: str, labels: dict[str, str]) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


async def _login_admin(
    *,
    async_client: AsyncClient,
    email: str,
    password: str,
) -> str:
    response = await async_client.post(
        "/api/v1/auth/login",
        headers={"X-Auth-Realm": "admin"},
        json={"login_or_email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_partner_finance_and_outbox_metrics_increment_for_statement_and_payout_lifecycle(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    statement_close_labels = {
        "surface": "partner_admin",
        "settlement_state": "closed",
        "result": "success",
    }
    payout_instruction_labels = {
        "surface": "partner_admin",
        "payout_state": "pending_approval",
        "result": "success",
    }
    payout_execution_labels = {
        "surface": "partner_admin",
        "payout_state": "reconciled",
        "result": "success",
    }
    outbox_created_labels = {
        "event_type": "settlement.statement.closed",
        "aggregate_type": "partner_statement",
        "result": "success",
    }
    outbox_published_labels = {
        "event_type": "settlement.statement.closed",
        "consumer_name": "analytics_mart",
        "result": "success",
    }
    outbox_failed_labels = {
        "event_type": "settlement.statement.closed",
        "consumer_name": "operational_replay",
        "result": "failure",
    }

    before_statement_close = _metric_value("cybervpn_partner_statements_closed_total", statement_close_labels)
    before_payout_instruction = _metric_value(
        "cybervpn_partner_payout_instructions_created_total",
        payout_instruction_labels,
    )
    before_payout_execution = _metric_value(
        "cybervpn_partner_payout_executions_total",
        payout_execution_labels,
    )
    before_outbox_created = _metric_value(
        "cybervpn_partner_outbox_events_created_total",
        outbox_created_labels,
    )
    before_outbox_published = _metric_value(
        "cybervpn_partner_outbox_events_published_total",
        outbox_published_labels,
    )
    before_outbox_failed = _metric_value(
        "cybervpn_partner_outbox_publish_failures_total",
        outbox_failed_labels,
    )

    try:
        async with override_realm_test_db(sessionmaker):
            with sessionmaker() as db:
                realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
                admin_realm = await realm_repo.get_or_create_default_realm("admin")
                admin_user = AdminUserModel(
                    login="obs03_finance_admin",
                    email="obs03-finance-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("Obs03FinanceAdmin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                approver_admin = AdminUserModel(
                    login="obs03_finance_approver",
                    email="obs03-finance-approver@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("Obs03FinanceApprover123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                workspace = PartnerAccountModel(
                    id=uuid.uuid4(),
                    account_key="obs03-finance-workspace",
                    display_name="OBS-03 Finance Workspace",
                    status="active",
                    legacy_owner_user_id=None,
                    created_by_admin_user_id=admin_user.id,
                )
                period = SettlementPeriodModel(
                    id=uuid.uuid4(),
                    partner_account_id=workspace.id,
                    period_key="2026-04-obs03",
                    period_status="open",
                    currency_code="USD",
                    window_start=datetime.now(UTC) - timedelta(days=7),
                    window_end=datetime.now(UTC) + timedelta(days=1),
                )
                statement = PartnerStatementModel(
                    id=uuid.uuid4(),
                    partner_account_id=workspace.id,
                    settlement_period_id=period.id,
                    statement_key="2026-04-obs03-v1",
                    statement_version=1,
                    statement_status="open",
                    currency_code="USD",
                    accrual_amount=Decimal("125.50"),
                    on_hold_amount=Decimal("0"),
                    reserve_amount=Decimal("0"),
                    adjustment_net_amount=Decimal("0"),
                    available_amount=Decimal("125.50"),
                    source_event_count=1,
                    held_event_count=0,
                    active_reserve_count=0,
                    adjustment_count=0,
                    statement_snapshot={},
                )
                payout_account = PartnerPayoutAccountModel(
                    id=uuid.uuid4(),
                    partner_account_id=workspace.id,
                    settlement_profile_id=None,
                    payout_rail="sepa",
                    display_label="Treasury SEPA",
                    destination_reference="DE89370400440532013000",
                    masked_destination="DE89...3000",
                    destination_metadata={"bank_country": "DE"},
                    verification_status="verified",
                    approval_status="approved",
                    account_status="active",
                    is_default=True,
                    created_by_admin_user_id=admin_user.id,
                    verified_by_admin_user_id=admin_user.id,
                    verified_at=datetime.now(UTC),
                    approved_by_admin_user_id=admin_user.id,
                    approved_at=datetime.now(UTC),
                )
                db.add_all([admin_user, approver_admin, workspace, period, statement, payout_account])
                db.commit()
                statement_id = statement.id
                payout_account_id = payout_account.id

            admin_token = await _login_admin(
                async_client=async_client,
                email="obs03-finance-admin@example.com",
                password="Obs03FinanceAdmin123!",
            )
            admin_headers = {
                "Authorization": f"Bearer {admin_token}",
                "X-Auth-Realm": "admin",
            }
            approver_token = await _login_admin(
                async_client=async_client,
                email="obs03-finance-approver@example.com",
                password="Obs03FinanceApprover123!",
            )
            approver_headers = {
                "Authorization": f"Bearer {approver_token}",
                "X-Auth-Realm": "admin",
            }

            close_statement_response = await async_client.post(
                f"/api/v1/partner-statements/{statement_id}/close",
                headers=admin_headers,
            )
            assert close_statement_response.status_code == 200
            closed_statement = close_statement_response.json()

            # The test harness seeds a synthetic statement without underlying earning events,
            # so the close flow recomputes availability to zero. Patch the closed statement
            # back to a positive payout amount to exercise the payout lifecycle telemetry.
            with sessionmaker() as db:
                statement_model = db.get(PartnerStatementModel, uuid.UUID(closed_statement["id"]))
                assert statement_model is not None
                statement_model.accrual_amount = Decimal("125.50")
                statement_model.available_amount = Decimal("125.50")
                statement_model.source_event_count = 1
                snapshot = dict(statement_model.statement_snapshot or {})
                totals = dict(snapshot.get("totals") or {})
                totals["accrual_amount"] = 125.5
                totals["available_amount"] = 125.5
                snapshot["totals"] = totals
                statement_model.statement_snapshot = snapshot
                db.commit()

            instruction_response = await async_client.post(
                "/api/v1/payouts/instructions",
                headers=admin_headers,
                json={
                    "partner_statement_id": closed_statement["id"],
                    "partner_payout_account_id": str(payout_account_id),
                },
            )
            assert instruction_response.status_code == 201
            instruction_payload = instruction_response.json()

            approve_instruction_response = await async_client.post(
                f"/api/v1/payouts/instructions/{instruction_payload['id']}/approve",
                headers=approver_headers,
            )
            assert approve_instruction_response.status_code == 200

            execution_response = await async_client.post(
                "/api/v1/payouts/executions",
                headers={**admin_headers, "Idempotency-Key": "obs03-payout-execution"},
                json={
                    "payout_instruction_id": instruction_payload["id"],
                    "execution_mode": "dry_run",
                    "execution_payload": {"source": "obs03"},
                },
            )
            assert execution_response.status_code == 201
            execution_payload = execution_response.json()

            submit_execution_response = await async_client.post(
                f"/api/v1/payouts/executions/{execution_payload['id']}/submit",
                headers=admin_headers,
                json={"external_reference": "obs03-submit", "submission_payload": {"step": "submitted"}},
            )
            assert submit_execution_response.status_code == 200

            complete_execution_response = await async_client.post(
                f"/api/v1/payouts/executions/{execution_payload['id']}/complete",
                headers=admin_headers,
                json={"external_reference": "obs03-complete", "completion_payload": {"step": "completed"}},
            )
            assert complete_execution_response.status_code == 200

            reconcile_execution_response = await async_client.post(
                f"/api/v1/payouts/executions/{execution_payload['id']}/reconcile",
                headers=admin_headers,
                json={"reconciliation_payload": {"step": "reconciled"}},
            )
            assert reconcile_execution_response.status_code == 200

            claim_analytics_response = await async_client.post(
                "/api/v1/reporting/outbox-publications/claim",
                headers=admin_headers,
                json={
                    "consumer_key": "analytics_mart",
                    "lease_owner": "obs03-analytics",
                    "batch_size": 1,
                    "lease_seconds": 60,
                },
            )
            assert claim_analytics_response.status_code == 200
            analytics_publication = claim_analytics_response.json()["claimed_publications"][0]

            submitted_response = await async_client.post(
                f"/api/v1/reporting/outbox-publications/{analytics_publication['id']}/submitted",
                headers=admin_headers,
                json={"lease_owner": "obs03-analytics"},
            )
            assert submitted_response.status_code == 200

            published_response = await async_client.post(
                f"/api/v1/reporting/outbox-publications/{analytics_publication['id']}/published",
                headers=admin_headers,
                json={"lease_owner": "obs03-analytics", "publication_payload": {"status": "ok"}},
            )
            assert published_response.status_code == 200

            claim_replay_response = await async_client.post(
                "/api/v1/reporting/outbox-publications/claim",
                headers=admin_headers,
                json={
                    "consumer_key": "operational_replay",
                    "lease_owner": "obs03-replay",
                    "batch_size": 1,
                    "lease_seconds": 60,
                },
            )
            assert claim_replay_response.status_code == 200
            replay_publication = claim_replay_response.json()["claimed_publications"][0]

            failed_response = await async_client.post(
                f"/api/v1/reporting/outbox-publications/{replay_publication['id']}/failed",
                headers=admin_headers,
                json={
                    "lease_owner": "obs03-replay",
                    "retry_after_seconds": 30,
                    "error_message": "OBS-03 synthetic failure",
                },
            )
            assert failed_response.status_code == 200

        assert (
            _metric_value("cybervpn_partner_statements_closed_total", statement_close_labels)
            > before_statement_close
        )
        assert (
            _metric_value("cybervpn_partner_payout_instructions_created_total", payout_instruction_labels)
            > before_payout_instruction
        )
        assert (
            _metric_value("cybervpn_partner_payout_executions_total", payout_execution_labels)
            > before_payout_execution
        )
        assert (
            _metric_value("cybervpn_partner_outbox_events_created_total", outbox_created_labels)
            > before_outbox_created
        )
        assert (
            _metric_value("cybervpn_partner_outbox_events_published_total", outbox_published_labels)
            > before_outbox_published
        )
        assert (
            _metric_value("cybervpn_partner_outbox_publish_failures_total", outbox_failed_labels)
            > before_outbox_failed
        )
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_partner_attribution_metrics_increment_for_checkout_and_order_commit(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    touchpoint_labels = {
        "surface": "customer_commerce",
        "touchpoint_type": "explicit_code",
        "result": "success",
    }
    attribution_labels = {
        "surface": "customer_commerce",
        "owner_type": "reseller",
        "owner_source": "explicit_code",
        "result": "success",
        "reason": "resolved",
    }

    before_touchpoints = _metric_value("cybervpn_partner_touchpoints_recorded_total", touchpoint_labels)
    before_resolutions = _metric_value("cybervpn_partner_attribution_resolutions_total", attribution_labels)

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
                partner_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="obs03-partner-owner@example.test",
                    password_hash=await auth_service.hash_password("Obs03PartnerOwner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                partner_account = PartnerAccountModel(
                    id=uuid.uuid4(),
                    account_key="obs03-attribution-workspace",
                    display_name="OBS-03 Attribution Workspace",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                partner_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="OBS03CODE",
                    partner_account_id=partner_account.id,
                    partner_user_id=partner_owner.id,
                    markup_pct=14,
                    is_active=True,
                )
                db.add_all([partner_owner, partner_account, partner_code])
                db.commit()

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            customer_headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }

            _, checkout_payload = await _create_quote_checkout(
                async_client=async_client,
                headers=customer_headers,
                storefront_key=seeded["storefront_key"],
                pricebook_key=seeded["pricebook_key"],
                offer_key=seeded["offer_key"],
                plan_id=seeded["plan_id"],
                partner_code=partner_code.code,
                idempotency_key="obs03-attribution-checkout",
            )
            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=customer_headers,
                json={"checkout_session_id": checkout_payload["id"]},
            )
            assert order_response.status_code == 201

        assert _metric_value("cybervpn_partner_touchpoints_recorded_total", touchpoint_labels) > before_touchpoints
        assert (
            _metric_value("cybervpn_partner_attribution_resolutions_total", attribution_labels)
            > before_resolutions
        )
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
