from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel
from src.infrastructure.database.models.partner_payout_account_model import (
    PartnerPayoutAccountModel,
)
from src.infrastructure.database.models.pilot_cohort_model import (
    PilotCohortModel,
    PilotGoNoGoDecisionModel,
    PilotOwnerAcknowledgementModel,
    PilotRollbackDrillModel,
    PilotRolloutWindowModel,
)
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
            "display_name": "Programs Workspace",
            "owner_admin_user_id": owner_admin_user_id,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _seed_payout_account(*, session, workspace_id: uuid.UUID, admin_user_id: uuid.UUID) -> None:
    session.add(
        PartnerPayoutAccountModel(
            id=uuid.uuid4(),
            partner_account_id=workspace_id,
            payout_rail="bank_transfer",
            display_label="Primary Finance Rail",
            destination_reference="DE89370400440532013000",
            masked_destination="DE89...3000",
            destination_metadata={"country": "DE"},
            verification_status="verified",
            approval_status="approved",
            account_status="active",
            is_default=True,
            created_by_admin_user_id=admin_user_id,
            verified_by_admin_user_id=admin_user_id,
            verified_at=datetime(2026, 4, 19, 8, 0, tzinfo=UTC),
            approved_by_admin_user_id=admin_user_id,
            approved_at=datetime(2026, 4, 19, 8, 0, tzinfo=UTC),
            default_selected_by_admin_user_id=admin_user_id,
            default_selected_at=datetime(2026, 4, 19, 8, 0, tzinfo=UTC),
        )
    )


def _seed_green_creator_lane(
    *,
    session,
    workspace_id: uuid.UUID,
    owner_admin_user_id: uuid.UUID,
    actor_admin_user_id: uuid.UUID,
) -> None:
    activated_at = datetime(2026, 4, 19, 9, 0, tzinfo=UTC)
    creator_cohort_id = uuid.uuid4()
    creator_cohort = PilotCohortModel(
        id=creator_cohort_id,
        cohort_key="rb003-creator-lane",
        display_name="RB003 Creator Lane",
        lane_key="creator_affiliate",
        surface_key="partner_storefront",
        cohort_status="active",
        partner_account_id=workspace_id,
        owner_team="partner_ops",
        owner_admin_user_id=owner_admin_user_id,
        rollback_trigger_code="shadow_divergence_exceeded",
        shadow_gate_payload={
            "attribution_reference": "phase8-attribution-shadow-creator",
            "attribution_gate_status": "green",
            "settlement_reference": "phase8-settlement-shadow-creator",
            "settlement_gate_status": "green",
            "notes": ["Creator lane is green."],
        },
        monitoring_payload={"max_live_orders": 25},
        notes_payload=["Creator lane is active for the workspace."],
        scheduled_start_at=activated_at - timedelta(days=1),
        scheduled_end_at=activated_at + timedelta(days=7),
        activated_at=activated_at,
        created_by_admin_user_id=actor_admin_user_id,
        activated_by_admin_user_id=actor_admin_user_id,
        created_at=activated_at - timedelta(days=2),
        updated_at=activated_at,
    )
    session.add(creator_cohort)
    session.add(
        PilotRolloutWindowModel(
            id=uuid.uuid4(),
            pilot_cohort_id=creator_cohort_id,
            window_kind="host",
            target_ref="creator.partner.example",
            window_status="active",
            starts_at=activated_at - timedelta(days=1),
            ends_at=activated_at + timedelta(days=7),
            notes_payload=["Creator lane host window"],
            created_by_admin_user_id=actor_admin_user_id,
            created_at=activated_at - timedelta(days=2),
            updated_at=activated_at,
        )
    )

    for owner_team in ("platform", "support", "qa", "partner_ops", "finance_ops"):
        session.add(
            PilotOwnerAcknowledgementModel(
                id=uuid.uuid4(),
                pilot_cohort_id=creator_cohort_id,
                owner_team=owner_team,
                acknowledgement_status="acknowledged",
                runbook_reference=f"runbook://{owner_team}/rb003-creator",
                notes_payload=[f"{owner_team} acknowledged creator lane readiness."],
                acknowledged_by_admin_user_id=actor_admin_user_id,
                acknowledged_at=activated_at - timedelta(hours=6),
                created_at=activated_at - timedelta(hours=6),
                updated_at=activated_at - timedelta(hours=6),
            )
        )

    session.add(
        PilotRollbackDrillModel(
            id=uuid.uuid4(),
            pilot_cohort_id=creator_cohort_id,
            cutover_unit_key="partner_storefront",
            rollback_scope_class="workspace",
            trigger_code="shadow_divergence_exceeded",
            drill_status="passed",
            runbook_reference="runbook://rollback/rb003-creator",
            observed_metric_payload={"orders_checked": 12},
            notes_payload=["Rollback drill passed for creator lane."],
            executed_by_admin_user_id=actor_admin_user_id,
            executed_at=activated_at - timedelta(hours=5),
            created_at=activated_at - timedelta(hours=5),
            updated_at=activated_at - timedelta(hours=5),
        )
    )
    session.add(
        PilotGoNoGoDecisionModel(
            id=uuid.uuid4(),
            pilot_cohort_id=creator_cohort_id,
            decision_status="approved",
            decision_reason_code=None,
            release_ring="R3",
            rollback_scope_class="workspace",
            cutover_unit_keys_payload=["partner_storefront"],
            evidence_links_payload=["evidence://rb003/creator"],
            acknowledged_owner_teams_payload=[
                "platform",
                "support",
                "qa",
                "partner_ops",
                "finance_ops",
            ],
            monitoring_snapshot_payload={"shadow_status": "green"},
            notes_payload=["Creator lane is approved for rollout."],
            decided_by_admin_user_id=actor_admin_user_id,
            decided_at=activated_at - timedelta(hours=4),
            created_at=activated_at - timedelta(hours=4),
            updated_at=activated_at - timedelta(hours=4),
        )
    )


def _seed_pending_performance_lane(
    *,
    session,
    workspace_id: uuid.UUID,
    owner_admin_user_id: uuid.UUID,
    actor_admin_user_id: uuid.UUID,
) -> None:
    scheduled_at = datetime(2026, 4, 20, 9, 0, tzinfo=UTC)
    performance_cohort_id = uuid.uuid4()
    performance_cohort = PilotCohortModel(
        id=performance_cohort_id,
        cohort_key="rb003-performance-lane",
        display_name="RB003 Performance Lane",
        lane_key="performance_media_buyer",
        surface_key="partner_storefront",
        cohort_status="scheduled",
        partner_account_id=workspace_id,
        owner_team="traffic_desk",
        owner_admin_user_id=owner_admin_user_id,
        rollback_trigger_code="shadow_divergence_exceeded",
        shadow_gate_payload={
            "attribution_reference": "phase8-attribution-shadow-performance",
            "attribution_gate_status": "green",
            "settlement_reference": "phase8-settlement-shadow-performance",
            "settlement_gate_status": "yellow",
            "notes": ["Performance lane still carries settlement caution."],
        },
        monitoring_payload={"max_live_orders": 10},
        notes_payload=["Performance lane is still in readiness review."],
        scheduled_start_at=scheduled_at,
        scheduled_end_at=scheduled_at + timedelta(days=7),
        created_by_admin_user_id=actor_admin_user_id,
        created_at=scheduled_at - timedelta(days=1),
        updated_at=scheduled_at - timedelta(hours=1),
    )
    session.add(performance_cohort)
    session.add(
        PilotRolloutWindowModel(
            id=uuid.uuid4(),
            pilot_cohort_id=performance_cohort_id,
            window_kind="host",
            target_ref="performance.partner.example",
            window_status="scheduled",
            starts_at=scheduled_at,
            ends_at=scheduled_at + timedelta(days=7),
            notes_payload=["Performance lane host window"],
            created_by_admin_user_id=actor_admin_user_id,
            created_at=scheduled_at - timedelta(days=1),
            updated_at=scheduled_at - timedelta(hours=1),
        )
    )


@pytest.mark.asyncio
async def test_partner_workspace_programs_surface_prefers_canonical_lane_and_readiness_state(
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

                admin_user = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="rb003_admin",
                    email="rb003-admin@example.com",
                    password="RB003Admin123!",
                    role="admin",
                )
                owner_user = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="rb003_owner",
                    email="rb003-owner@example.com",
                    password="RB003Owner123!",
                    role="viewer",
                )

            admin_token = await _login(async_client, admin_user.email, "RB003Admin123!")
            owner_token = await _login(async_client, owner_user.email, "RB003Owner123!")

            admin_headers = {"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"}
            owner_headers = {"Authorization": f"Bearer {owner_token}", "X-Auth-Realm": "admin"}

            workspace_id = await _create_workspace(
                async_client,
                admin_headers=admin_headers,
                owner_admin_user_id=str(owner_user.id),
            )
            workspace_uuid = uuid.UUID(workspace_id)

            with sessionmaker() as db:
                workspace = db.get(PartnerAccountModel, workspace_uuid)
                assert workspace is not None
                assert workspace.status == "active"

                _seed_payout_account(
                    session=db,
                    workspace_id=workspace_uuid,
                    admin_user_id=admin_user.id,
                )
                _seed_green_creator_lane(
                    session=db,
                    workspace_id=workspace_uuid,
                    owner_admin_user_id=owner_user.id,
                    actor_admin_user_id=admin_user.id,
                )
                _seed_pending_performance_lane(
                    session=db,
                    workspace_id=workspace_uuid,
                    owner_admin_user_id=owner_user.id,
                    actor_admin_user_id=admin_user.id,
                )
                db.commit()

            response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/programs",
                headers=owner_headers,
            )
            assert response.status_code == 200
            payload = response.json()

            assert payload["canonical_source"] == "pilot_cohorts"
            assert payload["primary_lane_key"] == "creator_affiliate"

            creator_lane = next(
                item for item in payload["lane_memberships"] if item["lane_key"] == "creator_affiliate"
            )
            performance_lane = next(
                item for item in payload["lane_memberships"] if item["lane_key"] == "performance_media"
            )

            assert creator_lane["membership_status"] == "approved_active"
            assert creator_lane["owner_context_label"] == "Partner Ops"
            assert creator_lane["pilot_cohort_status"] == "active"
            assert creator_lane["runbook_gate_status"] == "green"
            assert creator_lane["blocking_reason_codes"] == []

            assert performance_lane["membership_status"] == "pending"
            assert performance_lane["pilot_cohort_status"] == "scheduled"
            assert performance_lane["runbook_gate_status"] == "red"
            assert "traffic_declaration_incomplete" in performance_lane["blocking_reason_codes"]
            assert "creative_approval_incomplete" in performance_lane["blocking_reason_codes"]
            assert "owner_acknowledgement_missing" in performance_lane["blocking_reason_codes"]
            assert "rollback_drill_missing" in performance_lane["blocking_reason_codes"]
            assert "go_no_go_missing" in performance_lane["blocking_reason_codes"]
            assert "settlement_shadow_requires_caution" in performance_lane["warning_reason_codes"]

            readiness_by_key = {
                item["key"]: item for item in payload["readiness_items"]
            }
            assert readiness_by_key["finance"]["status"] == "ready"
            assert readiness_by_key["compliance"]["status"] == "evidence_requested"
            assert "traffic_declaration_incomplete" in readiness_by_key["compliance"]["blocking_reason_codes"]
            assert readiness_by_key["technical"]["status"] == "in_progress"
            assert "postback_pending" in readiness_by_key["technical"]["blocking_reason_codes"]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
