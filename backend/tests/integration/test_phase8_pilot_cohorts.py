from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.earning_event_model import EarningEventModel
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.models.outbox_event_model import OutboxEventModel
from src.infrastructure.database.models.partner_statement_model import PartnerStatementModel
from src.infrastructure.database.models.partner_traffic_declaration_model import (
    PartnerTrafficDeclarationModel,
)
from src.infrastructure.database.models.risk_review_model import RiskReviewModel
from src.infrastructure.database.models.risk_subject_model import RiskSubjectModel
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


async def _login(
    async_client: AsyncClient,
    login_or_email: str,
    password: str,
    *,
    realm_key: str,
) -> str:
    response = await async_client.post(
        "/api/v1/auth/login",
        headers={"X-Auth-Realm": realm_key},
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
            "display_name": "Phase 8 Pilot Workspace",
            "owner_admin_user_id": owner_admin_user_id,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _workspace_risk_subject_key(workspace_id: str) -> str:
    return f"partner_account:{workspace_id}"


async def test_phase8_pilot_cohorts_enforce_green_posture_and_allow_reversible_pause(
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
                operator_realm = AuthRealmModel(
                    id=uuid.uuid4(),
                    realm_key="pilot-ops",
                    realm_type="admin",
                    display_name="Pilot Ops Realm",
                    audience="cybervpn:pilot-ops",
                    cookie_namespace="pilot-ops",
                    status="active",
                    is_default=False,
                )
                db.add(operator_realm)

                admin_user = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="phase8_pilot_admin",
                    email="phase8-pilot-admin@example.com",
                    password="Phase8PilotAdmin123!",
                    role="admin",
                )
                operator_user = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=operator_realm.id,
                    login="phase8_pilot_operator",
                    email="phase8-pilot-operator@example.com",
                    password="Phase8PilotOperator123!",
                    role="operator",
                )
                owner_user = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="phase8_pilot_owner",
                    email="phase8-pilot-owner@example.com",
                    password="Phase8PilotOwner123!",
                    role="viewer",
                )

            admin_token = await _login(
                async_client,
                admin_user.email,
                "Phase8PilotAdmin123!",
                realm_key="admin",
            )
            operator_token = await _login(
                async_client,
                operator_user.email,
                "Phase8PilotOperator123!",
                realm_key="pilot-ops",
            )
            owner_token = await _login(
                async_client,
                owner_user.email,
                "Phase8PilotOwner123!",
                realm_key="admin",
            )

            admin_headers = {"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"}
            operator_headers = {"Authorization": f"Bearer {operator_token}", "X-Auth-Realm": "pilot-ops"}
            owner_headers = {"Authorization": f"Bearer {owner_token}", "X-Auth-Realm": "admin"}

            workspace_id = await _create_workspace(
                async_client,
                admin_headers=admin_headers,
                owner_admin_user_id=str(owner_user.id),
            )

            create_response = await async_client.post(
                "/api/v1/pilot-cohorts/",
                headers=admin_headers,
                json={
                    "cohort_key": "perf-lane-01",
                    "display_name": "Performance Lane Pilot 01",
                    "lane_key": "performance_media_buyer",
                    "surface_key": "partner_storefront",
                    "partner_account_id": workspace_id,
                    "owner_team": "partner_ops",
                    "owner_admin_user_id": str(owner_user.id),
                    "rollback_trigger_code": "shadow_divergence_exceeded",
                    "shadow_evidence": {
                        "attribution_reference": "phase8-attribution-shadow-001",
                        "attribution_gate_status": "green",
                        "settlement_reference": "phase8-settlement-shadow-001",
                        "settlement_gate_status": "green",
                        "notes": ["Pilot depends on green T8.3/T8.4 shadow packs."],
                    },
                    "rollout_windows": [
                        {
                            "window_kind": "host",
                            "target_ref": "performance.partner.example",
                            "starts_at": "2026-04-21T09:00:00Z",
                            "ends_at": "2026-04-28T09:00:00Z",
                            "notes": ["Primary partner storefront host"],
                        },
                        {
                            "window_kind": "partner_workspace",
                            "target_ref": workspace_id,
                            "starts_at": "2026-04-21T09:00:00Z",
                            "ends_at": "2026-04-28T09:00:00Z",
                            "notes": ["Workspace-scoped pilot enablement"],
                        },
                    ],
                    "monitoring_payload": {"max_live_orders": 50},
                    "notes": ["Performance lane starts only after green risk and governance posture."],
                },
            )
            assert create_response.status_code == 201
            cohort = create_response.json()
            cohort_id = cohort["id"]
            assert cohort["cohort_status"] == "scheduled"
            assert len(cohort["rollout_windows"]) == 2

            blocked_readiness_response = await async_client.get(
                f"/api/v1/pilot-cohorts/{cohort_id}/readiness",
                headers=operator_headers,
            )
            assert blocked_readiness_response.status_code == 200
            blocked_readiness = blocked_readiness_response.json()
            assert blocked_readiness["activation_allowed"] is False
            assert "traffic_declaration_incomplete" in blocked_readiness["blocking_reason_codes"]
            assert "creative_approval_incomplete" in blocked_readiness["blocking_reason_codes"]

            approved_sources_response = await async_client.post(
                "/api/v1/traffic-declarations/",
                headers=owner_headers,
                json={
                    "partner_account_id": workspace_id,
                    "declaration_kind": "approved_sources",
                    "scope_label": "Approved performance sources",
                    "declaration_payload": {"channels": ["native", "search"]},
                    "notes": ["Performance sources declared before pilot launch."],
                },
            )
            assert approved_sources_response.status_code == 201

            with sessionmaker() as db:
                declaration = db.execute(select(PartnerTrafficDeclarationModel)).scalar_one()
                declaration.declaration_status = "complete"
                db.commit()

            creative_approval_response = await async_client.post(
                "/api/v1/creative-approvals/",
                headers=admin_headers,
                json={
                    "partner_account_id": workspace_id,
                    "approval_kind": "creative_approval",
                    "approval_status": "complete",
                    "scope_label": "Performance creative posture",
                    "creative_ref": "creative-pilot-001",
                    "approval_payload": {"claims_family": "performance"},
                    "notes": ["Creative approved for limited pilot."],
                },
            )
            assert creative_approval_response.status_code == 201

            with sessionmaker() as db:
                risk_subject = RiskSubjectModel(
                    id=uuid.uuid4(),
                    principal_class="partner_operator",
                    principal_subject=_workspace_risk_subject_key(workspace_id),
                    auth_realm_id=None,
                    storefront_id=None,
                    status="active",
                    risk_level="medium",
                    metadata_payload={"partner_account_id": workspace_id, "synthetic_subject": True},
                )
                risk_review = RiskReviewModel(
                    id=uuid.uuid4(),
                    risk_subject_id=risk_subject.id,
                    review_type="pilot_activation",
                    status="open",
                    decision="hold",
                    reason="Hold performance pilot until ops clears remaining review",
                    evidence={"source": "t8.5"},
                    created_by_admin_user_id=admin_user.id,
                    resolved_by_admin_user_id=None,
                    resolved_at=None,
                    created_at=datetime(2026, 4, 19, 13, 0, tzinfo=UTC),
                    updated_at=datetime(2026, 4, 19, 13, 0, tzinfo=UTC),
                )
                db.add_all([risk_subject, risk_review])
                db.commit()
                risk_review_id = risk_review.id

            risk_blocked_response = await async_client.get(
                f"/api/v1/pilot-cohorts/{cohort_id}/readiness",
                headers=operator_headers,
            )
            assert risk_blocked_response.status_code == 200
            risk_blocked_payload = risk_blocked_response.json()
            assert risk_blocked_payload["activation_allowed"] is False
            assert "risk_review_blocking" in risk_blocked_payload["blocking_reason_codes"]
            assert risk_blocked_payload["blocking_risk_review_ids"] == [str(risk_review_id)]

            with sessionmaker() as db:
                risk_review = db.get(RiskReviewModel, risk_review_id)
                assert risk_review is not None
                risk_review.status = "resolved"
                risk_review.resolved_by_admin_user_id = admin_user.id
                risk_review.resolved_at = datetime(2026, 4, 19, 14, 0, tzinfo=UTC)
                db.commit()

            ready_response = await async_client.get(
                f"/api/v1/pilot-cohorts/{cohort_id}/readiness",
                headers=operator_headers,
            )
            assert ready_response.status_code == 200
            readiness_payload = ready_response.json()
            assert readiness_payload["activation_allowed"] is False
            assert "owner_acknowledgement_missing" in readiness_payload["blocking_reason_codes"]
            assert "rollback_drill_missing" in readiness_payload["blocking_reason_codes"]
            assert "go_no_go_missing" in readiness_payload["blocking_reason_codes"]
            assert readiness_payload["runbook_gate_status"] == "red"
            assert set(readiness_payload["required_owner_teams"]) == {
                "platform",
                "finance_ops",
                "risk_ops",
                "support",
                "partner_ops",
                "qa",
            }
            assert readiness_payload["live_monitoring_snapshot"]["complete_traffic_declaration_count"] == 1
            assert readiness_payload["live_monitoring_snapshot"]["complete_creative_approval_count"] == 1

            premature_activate_response = await async_client.post(
                f"/api/v1/pilot-cohorts/{cohort_id}/activate",
                headers=admin_headers,
            )
            assert premature_activate_response.status_code == 400
            assert "owner_acknowledgement_missing" in premature_activate_response.json()["detail"]

            for owner_team in ("platform", "finance_ops", "risk_ops", "support", "partner_ops", "qa"):
                acknowledgement_response = await async_client.post(
                    f"/api/v1/pilot-cohorts/{cohort_id}/owner-acknowledgements",
                    headers=admin_headers,
                    json={
                        "owner_team": owner_team,
                        "runbook_reference": f"docs/runbooks/{owner_team}/pilot-window.md",
                        "notes": [f"{owner_team} ack for limited pilot activation."],
                    },
                )
                assert acknowledgement_response.status_code == 201

            acknowledgement_list_response = await async_client.get(
                f"/api/v1/pilot-cohorts/{cohort_id}/owner-acknowledgements",
                headers=operator_headers,
            )
            assert acknowledgement_list_response.status_code == 200
            assert len(acknowledgement_list_response.json()) == 6

            rollback_drill_response = await async_client.post(
                f"/api/v1/pilot-cohorts/{cohort_id}/rollback-drills",
                headers=admin_headers,
                json={
                    "cutover_unit_key": "CU10",
                    "rollback_scope_class": "traffic_rollback",
                    "trigger_code": "shadow_divergence_exceeded",
                    "drill_status": "passed",
                    "runbook_reference": (
                        "docs/plans/"
                        "2026-04-17-partner-platform-environment-specific-cutover-runbooks.md"
                    ),
                    "observed_metric_payload": {
                        "attribution_divergence_rate": 0.0,
                        "refund_rate": 0.0,
                        "dispute_rate": 0.0,
                    },
                    "notes": ["Traffic rollback drill completed before live pilot activation."],
                },
            )
            assert rollback_drill_response.status_code == 201

            hold_decision_response = await async_client.post(
                f"/api/v1/pilot-cohorts/{cohort_id}/go-no-go-decisions",
                headers=admin_headers,
                json={
                    "decision_status": "hold",
                    "decision_reason_code": "waiting_for_staffing_confirmation",
                    "release_ring": "R3",
                    "rollback_scope_class": "traffic_rollback",
                    "cutover_unit_keys": ["CU10", "CU11"],
                    "evidence_links": [
                        "docs/testing/partner-platform-phase8-attribution-shadow-pack.md",
                        "docs/testing/partner-platform-phase8-settlement-shadow-pack.md",
                    ],
                    "monitoring_snapshot_payload": {
                        "shadow_divergence_rate": 0.0,
                        "support_staffing_confirmed": False,
                    },
                    "notes": ["Hold until support staffing is confirmed."],
                },
            )
            assert hold_decision_response.status_code == 201

            hold_readiness_response = await async_client.get(
                f"/api/v1/pilot-cohorts/{cohort_id}/readiness",
                headers=operator_headers,
            )
            assert hold_readiness_response.status_code == 200
            hold_readiness_payload = hold_readiness_response.json()
            assert hold_readiness_payload["activation_allowed"] is False
            assert "go_no_go_hold" in hold_readiness_payload["blocking_reason_codes"]

            approve_decision_response = await async_client.post(
                f"/api/v1/pilot-cohorts/{cohort_id}/go-no-go-decisions",
                headers=admin_headers,
                json={
                    "decision_status": "approved",
                    "release_ring": "R3",
                    "rollback_scope_class": "traffic_rollback",
                    "cutover_unit_keys": ["CU10", "CU11"],
                    "evidence_links": [
                        "docs/testing/partner-platform-phase8-attribution-shadow-pack.md",
                        "docs/testing/partner-platform-phase8-settlement-shadow-pack.md",
                        "docs/testing/partner-platform-phase7-parity-and-evidence-pack.md",
                    ],
                    "monitoring_snapshot_payload": {
                        "shadow_divergence_rate": 0.0,
                        "refund_rate": 0.0,
                        "dispute_rate": 0.0,
                        "support_staffing_confirmed": True,
                    },
                    "notes": ["Pilot approved after staffing and rollback drill confirmation."],
                },
            )
            assert approve_decision_response.status_code == 201

            approved_readiness_response = await async_client.get(
                f"/api/v1/pilot-cohorts/{cohort_id}/readiness",
                headers=operator_headers,
            )
            assert approved_readiness_response.status_code == 200
            approved_readiness_payload = approved_readiness_response.json()
            assert approved_readiness_payload["activation_allowed"] is True
            assert approved_readiness_payload["runbook_gate_status"] == "green"
            assert approved_readiness_payload["missing_owner_teams"] == []
            assert approved_readiness_payload["latest_rollback_drill_status"] == "passed"
            assert approved_readiness_payload["latest_go_no_go_status"] == "approved"

            activate_response = await async_client.post(
                f"/api/v1/pilot-cohorts/{cohort_id}/activate",
                headers=admin_headers,
            )
            assert activate_response.status_code == 200
            active_payload = activate_response.json()
            assert active_payload["cohort_status"] == "active"
            assert {item["window_status"] for item in active_payload["rollout_windows"]} == {"active"}

            pause_response = await async_client.post(
                f"/api/v1/pilot-cohorts/{cohort_id}/pause",
                headers=admin_headers,
                json={"reason_code": "manual_pause_for_support_review"},
            )
            assert pause_response.status_code == 200
            paused_payload = pause_response.json()
            assert paused_payload["cohort_status"] == "paused"
            assert paused_payload["pause_reason_code"] == "manual_pause_for_support_review"
            assert {item["window_status"] for item in paused_payload["rollout_windows"]} == {"paused"}

            with sessionmaker() as db:
                assert list(db.execute(select(OrderModel)).scalars()) == []
                assert list(db.execute(select(EarningEventModel)).scalars()) == []
                assert list(db.execute(select(PartnerStatementModel)).scalars()) == []
                outbox_event_names = list(
                    db.execute(
                        select(OutboxEventModel.event_name).order_by(OutboxEventModel.created_at.asc())
                    ).scalars()
                )
                assert "rollout.pilot_cohort.created" in outbox_event_names
                assert "rollout.runbook_acknowledged" in outbox_event_names
                assert "rollout.rollback_drill.recorded" in outbox_event_names
                assert "rollout.go_no_go.recorded" in outbox_event_names
                assert "rollout.pilot_cohort.activated" in outbox_event_names
                assert "rollout.pilot_cohort.paused" in outbox_event_names
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
