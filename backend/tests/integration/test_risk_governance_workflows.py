import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.outbox_event_model import OutboxEventModel
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


def _make_access_token(auth_service: AuthService, *, user_id, role: str, realm, principal_type: str) -> str:
    token, _, _ = auth_service.create_access_token(
        str(user_id),
        role,
        audience=realm.audience,
        principal_type=principal_type,
        realm_id=str(realm.id),
        realm_key=realm.realm_key,
        scope_family="admin",
    )
    return token


@pytest.mark.integration
async def test_risk_review_queue_and_governance_workflow_are_canonical_and_replay_visible(
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
                partner_admin_realm = AuthRealmModel(
                    id=uuid.uuid4(),
                    realm_key="partner-admin",
                    realm_type="admin",
                    display_name="Partner Admin Realm",
                    audience="cybervpn:partner-admin",
                    cookie_namespace="partner-admin",
                    status="active",
                    is_default=False,
                )
                db.add(partner_admin_realm)

                admin_user = AdminUserModel(
                    login="phase8_admin",
                    email="phase8-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("Phase8AdminP@ssword123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                operator_user = AdminUserModel(
                    login="phase8_operator",
                    email="phase8-operator@example.com",
                    auth_realm_id=partner_admin_realm.id,
                    password_hash=await auth_service.hash_password("Phase8OperatorP@ssword123!"),
                    role="operator",
                    is_active=True,
                    is_email_verified=True,
                )
                subject_principal = AdminUserModel(
                    login="phase8_subject",
                    email="phase8-subject@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("Phase8SubjectP@ssword123!"),
                    role="viewer",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add_all([admin_user, operator_user, subject_principal])
                db.commit()

                admin_token = _make_access_token(
                    auth_service,
                    user_id=admin_user.id,
                    role="admin",
                    realm=admin_realm,
                    principal_type="admin",
                )
                operator_token = _make_access_token(
                    auth_service,
                    user_id=operator_user.id,
                    role="operator",
                    realm=partner_admin_realm,
                    principal_type="admin",
                )

            subject_response = await async_client.post(
                "/api/v1/security/risk-subjects",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "principal_class": "admin",
                    "principal_subject": str(subject_principal.id),
                    "auth_realm_id": str(admin_realm.id),
                    "risk_level": "medium",
                },
            )
            assert subject_response.status_code == 201
            risk_subject = subject_response.json()

            review_response = await async_client.post(
                "/api/v1/security/risk-reviews",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "risk_subject_id": risk_subject["id"],
                    "review_type": "payout_review",
                    "decision": "hold",
                    "reason": "Manual finance investigation before pilot payout",
                    "evidence": {"source": "phase8_t8_1"},
                },
            )
            assert review_response.status_code == 201
            review = review_response.json()

            queue_response = await async_client.get(
                "/api/v1/security/risk-reviews/queue",
                headers={"Authorization": f"Bearer {operator_token}", "X-Auth-Realm": "partner-admin"},
                params={"status": "open"},
            )
            assert queue_response.status_code == 200
            queue_payload = queue_response.json()
            assert len(queue_payload) == 1
            assert queue_payload[0]["review"]["id"] == review["id"]
            assert queue_payload[0]["attachment_count"] == 0
            assert queue_payload[0]["governance_action_count"] == 0

            attachment_response = await async_client.post(
                f"/api/v1/security/risk-reviews/{review['id']}/attachments",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "attachment_type": "screenshot",
                    "storage_key": "risk/reviews/phase8-proof.png",
                    "file_name": "phase8-proof.png",
                    "metadata": {"content_type": "image/png"},
                },
            )
            assert attachment_response.status_code == 201
            attachment = attachment_response.json()
            assert attachment["attachment_type"] == "screenshot"
            assert attachment["metadata"]["content_type"] == "image/png"

            governance_action_response = await async_client.post(
                "/api/v1/security/governance-actions",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "risk_subject_id": risk_subject["id"],
                    "risk_review_id": review["id"],
                    "action_type": "payout_freeze",
                    "reason": "Freeze pilot payout until evidence is reviewed",
                    "target_type": "partner_payout_account",
                    "target_ref": "ppa_demo_001",
                    "payload": {"freeze_scope": "pilot"},
                    "apply_now": True,
                },
            )
            assert governance_action_response.status_code == 201
            governance_action = governance_action_response.json()
            assert governance_action["status"] == "applied"
            assert governance_action["action_type"] == "payout_freeze"

            detail_response = await async_client.get(
                f"/api/v1/security/risk-reviews/{review['id']}",
                headers={"Authorization": f"Bearer {operator_token}", "X-Auth-Realm": "partner-admin"},
            )
            assert detail_response.status_code == 200
            detail = detail_response.json()
            assert detail["subject"]["id"] == risk_subject["id"]
            assert len(detail["attachments"]) == 1
            assert detail["attachments"][0]["id"] == attachment["id"]
            assert len(detail["governance_actions"]) == 1
            assert detail["governance_actions"][0]["id"] == governance_action["id"]

            resolve_response = await async_client.post(
                f"/api/v1/security/risk-reviews/{review['id']}/resolve",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "decision": "block",
                    "resolution_status": "resolved",
                    "resolution_reason": "Pilot payout remains blocked pending operator clearance",
                    "resolution_evidence": {"final_source": "phase8_gate"},
                },
            )
            assert resolve_response.status_code == 200
            resolved_review = resolve_response.json()
            assert resolved_review["status"] == "resolved"
            assert resolved_review["decision"] == "block"
            assert resolved_review["resolved_by_admin_user_id"] == str(admin_user.id)

            resolved_queue_response = await async_client.get(
                "/api/v1/security/risk-reviews/queue",
                headers={"Authorization": f"Bearer {operator_token}", "X-Auth-Realm": "partner-admin"},
                params={"status": "resolved"},
            )
            assert resolved_queue_response.status_code == 200
            resolved_queue_payload = resolved_queue_response.json()
            assert len(resolved_queue_payload) == 1
            assert resolved_queue_payload[0]["review"]["id"] == review["id"]
            assert resolved_queue_payload[0]["attachment_count"] == 1
            assert resolved_queue_payload[0]["governance_action_count"] == 1

            governance_actions_response = await async_client.get(
                "/api/v1/security/governance-actions",
                headers={"Authorization": f"Bearer {operator_token}", "X-Auth-Realm": "partner-admin"},
                params={"risk_subject_id": risk_subject["id"]},
            )
            assert governance_actions_response.status_code == 200
            governance_actions_payload = governance_actions_response.json()
            assert len(governance_actions_payload) == 1
            assert governance_actions_payload[0]["id"] == governance_action["id"]

            with sessionmaker() as db:
                outbox_event_names = list(
                    db.execute(
                        select(OutboxEventModel.event_name).order_by(OutboxEventModel.created_at.asc())
                    ).scalars()
                )
                assert "risk.review.opened" in outbox_event_names
                assert "risk.evidence.attached" in outbox_event_names
                assert "risk.governance_action.recorded" in outbox_event_names
                assert "risk.decision.recorded" in outbox_event_names
                assert "risk.review.resolved" in outbox_event_names
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
