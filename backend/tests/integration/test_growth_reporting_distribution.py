from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from pydantic import SecretStr

from src.application.services.auth_service import AuthService
from src.application.use_cases.growth_codes.reporting import RefreshGrowthReportingRollupsUseCase
from src.application.use_cases.growth_codes.reporting_distribution import (
    ClaimDueGrowthReportingDeliveriesUseCase,
    CleanupGrowthReportingArtifactsUseCase,
    CompleteGrowthReportingDeliveryUseCase,
    CreateGrowthReportingSubscriptionUseCase,
    ExportGrowthReportingGovernanceSnapshotUseCase,
    GetGrowthReportingGovernanceOverviewUseCase,
    ListGrowthReportingDeliveriesUseCase,
    ListGrowthReportingSubscriptionsUseCase,
    ProcessGrowthReportingGovernanceFollowupsUseCase,
    UpdateGrowthReportingGovernanceFollowupUseCase,
)
from src.config import settings
from src.infrastructure.database.models.audit_log_model import AuditLog
from src.infrastructure.database.models.growth_reporting_daily_rollup_model import (
    GrowthReportingDailyRollupModel,
)
from src.infrastructure.database.models.growth_reporting_delivery_model import (
    GrowthReportingDeliveryModel,
)
from src.infrastructure.database.models.growth_reporting_refresh_run_model import (
    GrowthReportingRefreshRunModel,
)
from src.infrastructure.database.models.growth_reporting_subscription_model import (
    GrowthReportingSubscriptionModel,
)
from src.main import app
from tests.helpers.realm_auth import (
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)
from tests.integration.test_growth_reporting_rollups import (
    _create_admin_user,
    _seed_growth_reporting_fixtures,
)
from tests.integration.test_quote_checkout_sessions import _seed_quote_context

pytestmark = [pytest.mark.integration]


def _insert_old_reporting_artifacts(sessionmaker) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with sessionmaker() as db:
        subscription = GrowthReportingSubscriptionModel(
            id=uuid.uuid4(),
            recipient_email="stale-growth-reporting@example.test",
            recipient_name="Stale Report Owner",
            audience_key="ops",
            delivery_channel="email",
            cadence="weekly",
            report_window_days=30,
            subscription_status="paused",
            next_delivery_at=now - timedelta(days=30),
            created_at=now - timedelta(days=120),
            updated_at=now - timedelta(days=120),
        )
        db.add(subscription)
        db.flush()

        db.add(
            GrowthReportingDeliveryModel(
                id=uuid.uuid4(),
                subscription_id=subscription.id,
                recipient_email=subscription.recipient_email,
                recipient_name=subscription.recipient_name,
                audience_key=subscription.audience_key,
                delivery_channel=subscription.delivery_channel,
                cadence=subscription.cadence,
                report_window_days=subscription.report_window_days,
                template_key=subscription.template_key,
                template_locale=subscription.template_locale,
                subject_line="[CyberVPN][Growth][Ops] Weekly digest 2026-04-17",
                title_line="Operations growth reporting digest",
                recipient_domain_policy=subscription.recipient_domain_policy,
                allowed_recipient_domains=list(subscription.allowed_recipient_domains or []),
                delivery_status="delivered",
                status_reason=None,
                window_start=date.today() - timedelta(days=35),
                window_end=date.today() - timedelta(days=5),
                freshness_status="fresh",
                artifact_checksum="old-checksum",
                artifact_payload={"kind": "stale"},
                planned_at=now - timedelta(days=120),
                started_at=now - timedelta(days=120),
                delivered_at=now - timedelta(days=120),
                created_at=now - timedelta(days=120),
                updated_at=now - timedelta(days=120),
            )
        )
        db.add(
            GrowthReportingRefreshRunModel(
                id=uuid.uuid4(),
                trigger_kind="worker",
                refresh_status="success",
                requested_window_days=30,
                window_start=date.today() - timedelta(days=150),
                window_end=date.today() - timedelta(days=120),
                latest_rollup_date=date.today() - timedelta(days=120),
                rows_written=3,
                families_updated=["invite", "promo"],
                started_at=now - timedelta(days=200),
                finished_at=now - timedelta(days=200),
                refreshed_at=now - timedelta(days=200),
            )
        )
        db.add(
            GrowthReportingDailyRollupModel(
                id=uuid.uuid4(),
                report_date=date.today() - timedelta(days=220),
                report_family="invite",
                metric_key="issued_total",
                metric_unit="count",
                dimension_key="",
                dimension_value="",
                metric_value=1,
                currency_code="",
                source_watermark_at=now - timedelta(days=200),
                refreshed_at=now - timedelta(days=200),
            )
        )
        db.commit()


@pytest.mark.asyncio
async def test_growth_reporting_distribution_use_cases_cover_subscription_claim_complete_and_cleanup() -> None:
    auth_service = AuthService()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_quote_context(sessionmaker, auth_service)
            admin_user, _ = await _create_admin_user(sessionmaker, auth_service)
            _seed_growth_reporting_fixtures(sessionmaker, seeded)
            _insert_old_reporting_artifacts(sessionmaker)

            with sessionmaker() as db:
                session = SyncSessionAdapter(db)
                refresh_result = await RefreshGrowthReportingRollupsUseCase(session).execute(window_days=30)
                assert refresh_result.rows_written > 0
                db.commit()
                db.commit()

                subscription = await CreateGrowthReportingSubscriptionUseCase(session).execute(
                    recipient_email="finance-growth@example.test",
                    recipient_name="Finance",
                    audience_key="finance",
                    cadence="daily",
                    report_window_days=30,
                    template_key="finance_exec",
                    template_locale="en-EN",
                    email_subject_prefix="[CyberVPN][Growth][Finance]",
                    title_override=None,
                    recipient_domain_policy="allowlist_only",
                    allowed_recipient_domains=["example.test"],
                    suppressed_until=None,
                    suppression_reason_code=None,
                    created_by_admin_user_id=admin_user.id,
                )
                assert subscription.subscription_status == "active"
                assert subscription.health_status == "healthy"
                assert subscription.policy.template_key == "finance_exec"
                assert subscription.policy.recipient_domain_policy == "allowlist_only"

                suppressed_subscription = await CreateGrowthReportingSubscriptionUseCase(session).execute(
                    recipient_email="ops-growth@example.test",
                    recipient_name="Ops",
                    audience_key="ops",
                    cadence="weekly",
                    report_window_days=14,
                    template_key="ops_exec",
                    template_locale="en-EN",
                    email_subject_prefix=None,
                    title_override=None,
                    recipient_domain_policy="allow_any",
                    allowed_recipient_domains=[],
                    suppressed_until=datetime.now(UTC) + timedelta(days=1),
                    suppression_reason_code="ops_blackout",
                    created_by_admin_user_id=admin_user.id,
                )
                assert suppressed_subscription.health_status == "suppressed"

                blocked_model = GrowthReportingSubscriptionModel(
                    id=uuid.uuid4(),
                    recipient_email="ops-growth@blocked.test",
                    recipient_name="Blocked Ops",
                    audience_key="ops",
                    delivery_channel="email",
                    cadence="weekly",
                    report_window_days=14,
                    template_key="ops_exec",
                    template_locale="en-EN",
                    recipient_domain_policy="allowlist_only",
                    allowed_recipient_domains=["example.test"],
                    subscription_status="active",
                    next_delivery_at=datetime.now(UTC),
                    created_by_admin_user_id=admin_user.id,
                    updated_by_admin_user_id=admin_user.id,
                )
                db.add(blocked_model)
                db.flush()

                subscriptions = await ListGrowthReportingSubscriptionsUseCase(session).execute()
                assert subscriptions.total >= 4
                assert any(item.recipient_email == "finance-growth@example.test" for item in subscriptions.items)
                assert any(item.health_status == "suppressed" for item in subscriptions.items)
                assert any(item.health_status == "recipient_domain_blocked" for item in subscriptions.items)

                claim_result = await ClaimDueGrowthReportingDeliveriesUseCase(session).execute(limit=10)
                assert claim_result.claimed_count == 1
                assert claim_result.skipped_count == 2
                assert claim_result.deliveries[0].recipient_email == "finance-growth@example.test"
                assert claim_result.deliveries[0].delivery_channel == "email"
                assert claim_result.deliveries[0].subject.startswith("[CyberVPN][Growth][Finance]")
                assert claim_result.deliveries[0].notes

                claimed_delivery = claim_result.deliveries[0]
                completed = await CompleteGrowthReportingDeliveryUseCase(session).execute(
                    delivery_id=uuid.UUID(claimed_delivery.delivery_id),
                    delivery_status="delivered",
                    provider_name="email",
                    provider_message_id="provider-message-1",
                    failure_message=None,
                )
                assert completed.delivery_status == "delivered"
                assert completed.provider_message_id == "provider-message-1"

                deliveries = await ListGrowthReportingDeliveriesUseCase(session).execute(limit=10)
                assert any(item.id == claimed_delivery.delivery_id for item in deliveries.items)
                assert any(item.status_reason == "delivery_suppressed" for item in deliveries.items)
                assert any(item.status_reason == "recipient_domain_blocked" for item in deliveries.items)

                governance = await GetGrowthReportingGovernanceOverviewUseCase(session).execute()
                assert governance.coverage_gap_count >= 2
                assert governance.followup_open_count >= 2
                assert any(item.coverage_state == "delivery_suppressed" for item in governance.coverage_counts)
                assert any(item.coverage_state == "recipient_domain_blocked" for item in governance.coverage_counts)
                assert any(item.status_reason == "recipient_domain_blocked" for item in governance.recent_decisions)
                assert governance.followup_queue

                followup_result = await ProcessGrowthReportingGovernanceFollowupsUseCase(session).execute()
                assert followup_result.scanned_count >= 4
                assert followup_result.open_count >= 2

                resolved_subscription = await UpdateGrowthReportingGovernanceFollowupUseCase(session).execute(
                    subscription_id=uuid.UUID(governance.followup_queue[0].subscription_id),
                    action="resolve",
                    reason_code="operator_validated",
                    updated_by_admin_user_id=admin_user.id,
                )
                assert resolved_subscription.subscription.followup.status == "resolved"
                assert resolved_subscription.subscription.followup.resolution_code == "operator_validated"

                governance_export = await ExportGrowthReportingGovernanceSnapshotUseCase(session).execute()
                assert governance_export[1]["coverage"]["coverage_gap_count"] >= 2
                assert governance_export[1]["coverage"]["followup_open_count"] >= 1
                assert governance_export[1]["followup_queue"]
                assert governance_export[1]["subscriptions"]

                cleanup_result = await CleanupGrowthReportingArtifactsUseCase(session).execute()
                assert cleanup_result.deliveries_deleted >= 1
                assert cleanup_result.refresh_runs_deleted >= 1
                assert cleanup_result.rollups_deleted >= 1
                db.commit()
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_admin_growth_reporting_distribution_endpoints_cover_subscription_delivery_and_cleanup(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_service = AuthService()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    original_secret = settings.telegram_bot_internal_secret
    monkeypatch.setattr(settings, "telegram_bot_internal_secret", SecretStr("worker-secret"))

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_quote_context(sessionmaker, auth_service)
            admin_user, admin_password = await _create_admin_user(sessionmaker, auth_service)
            _seed_growth_reporting_fixtures(sessionmaker, seeded)
            _insert_old_reporting_artifacts(sessionmaker)

            with sessionmaker() as db:
                session = SyncSessionAdapter(db)
                refresh_result = await RefreshGrowthReportingRollupsUseCase(session).execute(window_days=30)
                assert refresh_result.rows_written > 0
                db.commit()

            login_response = await async_client.post(
                "/api/v1/auth/login",
                json={"login_or_email": admin_user.login, "password": admin_password},
                headers={"X-Auth-Realm": "admin"},
            )
            assert login_response.status_code == 200
            admin_token = login_response.json()["access_token"]
            admin_headers = {
                "Authorization": f"Bearer {admin_token}",
                "X-Auth-Realm": "admin",
            }

            create_response = await async_client.post(
                "/api/v1/admin/growth-reporting/subscriptions",
                json={
                    "recipient_email": "risk-growth@example.test",
                    "recipient_name": "Risk",
                    "audience_key": "risk",
                    "cadence": "daily",
                    "report_window_days": 30,
                    "policy": {
                        "template_key": "risk_exec",
                        "template_locale": "en-EN",
                        "recipient_domain_policy": "allowlist_only",
                        "allowed_recipient_domains": ["example.test"],
                    },
                },
                headers=admin_headers,
            )
            assert create_response.status_code == 201
            subscription_payload = create_response.json()
            subscription_id = subscription_payload["id"]
            assert subscription_payload["subscription_status"] == "active"
            assert subscription_payload["policy"]["template_key"] == "risk_exec"

            invalid_response = await async_client.post(
                "/api/v1/admin/growth-reporting/subscriptions",
                json={
                    "recipient_email": "bad-growth@example.test",
                    "recipient_name": "Bad",
                    "audience_key": "finance",
                    "cadence": "monthly",
                    "report_window_days": 30,
                    "policy": {
                        "recipient_domain_policy": "allow_any",
                    },
                },
                headers=admin_headers,
            )
            assert invalid_response.status_code == 422
            assert invalid_response.json()["detail"] == "growth_reporting_invalid_cadence"

            update_response = await async_client.put(
                f"/api/v1/admin/growth-reporting/subscriptions/{subscription_id}",
                json={
                    "recipient_email": "risk-ops@example.test",
                    "recipient_name": "Risk Ops",
                    "audience_key": "risk",
                    "cadence": "weekly",
                    "report_window_days": 45,
                    "policy": {
                        "template_key": "cross_function_exec",
                        "template_locale": "en-EN",
                        "email_subject_prefix": "[CyberVPN][Growth][Risk][Board]",
                        "title_override": "Risk board digest",
                        "recipient_domain_policy": "allowlist_only",
                        "allowed_recipient_domains": ["example.test"],
                        "suppressed_until": None,
                        "suppression_reason_code": None,
                    },
                    "reason_code": "recipient_governance_refresh",
                },
                headers=admin_headers,
            )
            assert update_response.status_code == 200
            assert update_response.json()["recipient_email"] == "risk-ops@example.test"
            assert update_response.json()["policy"]["title_override"] == "Risk board digest"

            list_response = await async_client.get(
                "/api/v1/admin/growth-reporting/subscriptions",
                headers=admin_headers,
            )
            assert list_response.status_code == 200
            assert any(item["id"] == subscription_id for item in list_response.json()["items"])

            with sessionmaker() as db:
                db.add(
                    GrowthReportingSubscriptionModel(
                        id=uuid.uuid4(),
                        recipient_email="ops-board@blocked.test",
                        recipient_name="Blocked Ops",
                        audience_key="ops",
                        delivery_channel="email",
                        cadence="weekly",
                        report_window_days=14,
                        template_key="ops_exec",
                        template_locale="en-EN",
                        recipient_domain_policy="allowlist_only",
                        allowed_recipient_domains=["example.test"],
                        subscription_status="active",
                        next_delivery_at=datetime.now(UTC),
                        created_by_admin_user_id=admin_user.id,
                        updated_by_admin_user_id=admin_user.id,
                    )
                )
                db.commit()

            pause_response = await async_client.post(
                f"/api/v1/admin/growth-reporting/subscriptions/{subscription_id}/pause",
                json={"reason_code": "ops_pause"},
                headers=admin_headers,
            )
            assert pause_response.status_code == 200
            assert pause_response.json()["subscription_status"] == "paused"

            resume_response = await async_client.post(
                f"/api/v1/admin/growth-reporting/subscriptions/{subscription_id}/resume",
                json={"reason_code": "ops_resume"},
                headers=admin_headers,
            )
            assert resume_response.status_code == 200
            assert resume_response.json()["subscription_status"] == "active"

            worker_headers = {"X-Telegram-Bot-Secret": "worker-secret"}
            claim_response = await async_client.post(
                "/api/v1/admin/growth-reporting/internal/deliveries/claim?limit=10",
                headers=worker_headers,
            )
            assert claim_response.status_code == 200
            claim_payload = claim_response.json()
            assert claim_payload["claimed_count"] == 1
            assert claim_payload["skipped_count"] >= 1
            delivery_id = claim_payload["deliveries"][0]["delivery_id"]

            complete_response = await async_client.post(
                f"/api/v1/admin/growth-reporting/internal/deliveries/{delivery_id}/complete",
                json={
                    "delivery_status": "delivered",
                    "provider_name": "email",
                    "provider_message_id": "provider-msg-42",
                    "failure_message": None,
                },
                headers=worker_headers,
            )
            assert complete_response.status_code == 200
            assert complete_response.json()["delivery_status"] == "delivered"

            deliveries_response = await async_client.get(
                "/api/v1/admin/growth-reporting/deliveries?limit=10",
                headers=admin_headers,
            )
            assert deliveries_response.status_code == 200
            matching_delivery = next(
                item for item in deliveries_response.json()["items"] if item["id"] == delivery_id
            )
            assert matching_delivery["template_key"] == "cross_function_exec"
            assert any(
                item["status_reason"] == "recipient_domain_blocked"
                for item in deliveries_response.json()["items"]
            )

            governance_response = await async_client.get(
                "/api/v1/admin/growth-reporting/governance",
                headers=admin_headers,
            )
            assert governance_response.status_code == 200
            governance_payload = governance_response.json()
            assert governance_payload["coverage_gap_count"] >= 1
            assert governance_payload["followup_open_count"] >= 1
            assert any(
                item["coverage_state"] == "recipient_domain_blocked"
                for item in governance_payload["coverage_counts"]
            )
            assert governance_payload["followup_queue"]
            assert governance_payload["recent_audit_events"]

            followup_process_response = await async_client.post(
                "/api/v1/admin/growth-reporting/internal/governance/followups/process",
                headers={"X-Telegram-Bot-Secret": settings.telegram_bot_internal_secret.get_secret_value()},
            )
            assert followup_process_response.status_code == 200
            assert followup_process_response.json()["open_count"] >= 1

            followup_subscription_id = governance_payload["followup_queue"][0]["subscription_id"]
            followup_action_response = await async_client.post(
                f"/api/v1/admin/growth-reporting/subscriptions/{followup_subscription_id}/follow-up/resolve",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"reason_code": "admin_recovered"},
            )
            assert followup_action_response.status_code == 200
            assert followup_action_response.json()["followup"]["status"] == "resolved"
            assert followup_action_response.json()["followup"]["resolution_code"] == "admin_recovered"

            governance_export_response = await async_client.get(
                "/api/v1/admin/growth-reporting/governance/export",
                headers=admin_headers,
            )
            assert governance_export_response.status_code == 200
            governance_export_payload = governance_export_response.json()
            assert governance_export_payload["export_kind"] == "growth_reporting_governance_snapshot"
            assert governance_export_payload["overview"]["coverage_gap_count"] >= 1
            assert governance_export_payload["payload"]["subscriptions"]

            artifact_response = await async_client.get(
                f"/api/v1/admin/growth-reporting/deliveries/{delivery_id}/artifact",
                headers=admin_headers,
            )
            assert artifact_response.status_code == 200
            artifact_payload = artifact_response.json()
            assert artifact_payload["delivery"]["id"] == delivery_id
            assert artifact_payload["payload"]["audience_key"] == "risk"

            cleanup_response = await async_client.post(
                "/api/v1/admin/growth-reporting/internal/cleanup",
                headers=worker_headers,
            )
            assert cleanup_response.status_code == 200
            cleanup_payload = cleanup_response.json()
            assert cleanup_payload["deliveries_deleted"] >= 1
            assert cleanup_payload["refresh_runs_deleted"] >= 1
            assert cleanup_payload["rollups_deleted"] >= 1

            with sessionmaker() as db:
                audit_logs = (
                    db.query(AuditLog)
                    .filter(AuditLog.entity_type == "growth_reporting_subscription")
                    .all()
                )
                assert any(log.action == "growth_reporting.subscription.created" for log in audit_logs)
                assert any(log.action == "growth_reporting.subscription.updated" for log in audit_logs)
    finally:
        monkeypatch.setattr(settings, "telegram_bot_internal_secret", original_secret)
        app.dependency_overrides.clear()
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
