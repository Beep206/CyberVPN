from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.payment_dispute_model import PaymentDisputeModel
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
            "display_name": "Phase 8 Overlay Workspace",
            "owner_admin_user_id": owner_admin_user_id,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


async def test_phase8_operational_overlays_are_canonical_and_workspace_visible(
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
                    login="phase8_overlay_admin",
                    email="phase8-overlay-admin@example.com",
                    password="Phase8OverlayAdmin123!",
                    role="admin",
                )
                owner_user = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="phase8_overlay_owner",
                    email="phase8-overlay-owner@example.com",
                    password="Phase8OverlayOwner123!",
                    role="viewer",
                )

            admin_token = await _login(async_client, admin_user.email, "Phase8OverlayAdmin123!")
            owner_token = await _login(async_client, owner_user.email, "Phase8OverlayOwner123!")

            admin_headers = {"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"}
            owner_headers = {"Authorization": f"Bearer {owner_token}", "X-Auth-Realm": "admin"}

            workspace_id = await _create_workspace(
                async_client,
                admin_headers=admin_headers,
                owner_admin_user_id=str(owner_user.id),
            )

            with sessionmaker() as db:
                dispute = PaymentDisputeModel(
                    id=uuid.uuid4(),
                    order_id=uuid.uuid4(),
                    provider="stripe",
                    external_reference="phase8-dispute-001",
                    subtype="chargeback",
                    outcome_class="open",
                    lifecycle_status="opened",
                    disputed_amount=25,
                    fee_amount=0,
                    fee_status="none",
                    currency_code="USD",
                    reason_code="fraudulent",
                    evidence_snapshot={"source": "phase8"},
                    provider_snapshot={},
                    opened_at=datetime(2026, 4, 19, 10, 0, tzinfo=UTC),
                    created_at=datetime(2026, 4, 19, 10, 0, tzinfo=UTC),
                    updated_at=datetime(2026, 4, 19, 10, 0, tzinfo=UTC),
                )
                db.add(dispute)
                db.commit()
                payment_dispute_id = dispute.id
                dispute_order_id = dispute.order_id

            approved_sources_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/traffic-declarations",
                headers=owner_headers,
                json={
                    "declaration_kind": "approved_sources",
                    "scope_label": "Workspace-owned traffic sources",
                    "declaration_payload": {"channels": ["seo", "direct"]},
                    "notes": ["Primary acquisition channels declared."],
                },
            )
            assert approved_sources_response.status_code == 201

            postback_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/traffic-declarations",
                headers=owner_headers,
                json={
                    "declaration_kind": "postback_readiness",
                    "scope_label": "Tracking and postback handoff",
                    "declaration_payload": {"destination": "https://partner.example/postback"},
                    "notes": ["Webhook destination prepared for review."],
                },
            )
            assert postback_response.status_code == 201

            creative_approval_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/creative-approvals",
                headers=owner_headers,
                json={
                    "scope_label": "Creative and claims posture",
                    "creative_ref": "banner-001",
                    "approval_payload": {"claim_family": "performance"},
                    "notes": ["Creative requires claims validation."],
                },
            )
            assert creative_approval_response.status_code == 201

            dispute_case_response = await async_client.post(
                "/api/v1/dispute-cases/",
                headers=admin_headers,
                json={
                    "partner_account_id": workspace_id,
                    "payment_dispute_id": str(payment_dispute_id),
                    "case_kind": "chargeback_review",
                    "case_status": "waiting_on_ops",
                    "summary": "Collect provider evidence before reserve release.",
                    "case_payload": {"lane": "performance"},
                    "notes": ["Ops needs provider outcome and supporting files."],
                },
            )
            assert dispute_case_response.status_code == 201
            dispute_case_payload = dispute_case_response.json()
            assert dispute_case_payload["payment_dispute_id"] == str(payment_dispute_id)
            assert dispute_case_payload["order_id"] == str(dispute_order_id)

            traffic_list_response = await async_client.get(
                "/api/v1/traffic-declarations/",
                headers=owner_headers,
                params={"partner_account_id": workspace_id},
            )
            assert traffic_list_response.status_code == 200
            traffic_payload = {item["declaration_kind"]: item for item in traffic_list_response.json()}
            assert traffic_payload["approved_sources"]["declaration_status"] == "submitted"
            assert traffic_payload["postback_readiness"]["scope_label"] == "Tracking and postback handoff"

            creative_list_response = await async_client.get(
                "/api/v1/creative-approvals/",
                headers=admin_headers,
                params={"partner_account_id": workspace_id},
            )
            assert creative_list_response.status_code == 200
            assert creative_list_response.json()[0]["approval_kind"] == "creative_approval"

            dispute_cases_list_response = await async_client.get(
                "/api/v1/dispute-cases/",
                headers=admin_headers,
                params={"partner_account_id": workspace_id},
            )
            assert dispute_cases_list_response.status_code == 200
            assert dispute_cases_list_response.json()[0]["case_kind"] == "chargeback_review"

            workspace_traffic_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/traffic-declarations",
                headers=owner_headers,
            )
            assert workspace_traffic_response.status_code == 200
            workspace_traffic_payload = {item["kind"]: item for item in workspace_traffic_response.json()}
            assert workspace_traffic_payload["approved_sources"]["status"] == "submitted"
            assert workspace_traffic_payload["postback_readiness"]["status"] == "submitted"
            assert workspace_traffic_payload["creative_approval"]["status"] == "under_review"

            review_requests_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/review-requests",
                headers=owner_headers,
            )
            assert review_requests_response.status_code == 200
            review_requests_payload = {item["id"]: item for item in review_requests_response.json()}
            finance_request_id = f"finance-profile:{workspace_id}"
            assert review_requests_payload[finance_request_id]["status"] == "open"
            assert "submit_response" in review_requests_payload[finance_request_id]["available_actions"]

            finance_case_id = f"case:{finance_request_id}"
            ready_for_ops_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/cases/{finance_case_id}/ready-for-ops",
                headers=owner_headers,
                json={
                    "message": "Finance package is complete and ready for partner ops review.",
                    "response_payload": {
                        "handoff": "finance_package_complete",
                    },
                },
            )
            assert ready_for_ops_response.status_code == 201
            assert ready_for_ops_response.json()["action_kind"] == "partner_ready_for_ops"

            case_reply_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/cases/{finance_case_id}/responses",
                headers=owner_headers,
                json={
                    "message": "Added follow-up note with billing contact and payout destination context.",
                    "response_payload": {
                        "attachments": ["billing-contact.txt"],
                    },
                },
            )
            assert case_reply_response.status_code == 201
            assert case_reply_response.json()["action_kind"] == "partner_reply"

            review_request_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/review-requests/{finance_request_id}/responses",
                headers=owner_headers,
                json={
                    "message": "Uploaded payout profile evidence and settlement contacts for finance review.",
                    "response_payload": {
                        "attachments": ["payout-profile.pdf"],
                        "checklist": ["payout_profile", "settlement_contact"],
                    },
                },
            )
            assert review_request_response.status_code == 201
            assert review_request_response.json()["action_kind"] == "partner_response_submitted"

            review_requests_after_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/review-requests",
                headers=owner_headers,
            )
            assert review_requests_after_response.status_code == 200
            review_requests_after_payload = {
                item["id"]: item for item in review_requests_after_response.json()
            }
            assert review_requests_after_payload[finance_request_id]["status"] == "submitted"
            assert (
                review_requests_after_payload[finance_request_id]["thread_events"][0]["message"]
                == "Uploaded payout profile evidence and settlement contacts for finance review."
            )

            workspace_cases_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/cases",
                headers=owner_headers,
            )
            assert workspace_cases_response.status_code == 200
            workspace_cases_payload = {item["id"]: item for item in workspace_cases_response.json()}
            finance_case = workspace_cases_payload[finance_case_id]
            assert finance_case["status"] == "waiting_on_ops"
            assert finance_case["thread_events"][0]["action_kind"] == "partner_ready_for_ops"
            assert finance_case["thread_events"][1]["action_kind"] == "partner_reply"
            assert finance_case["available_actions"] == ["reply"]
            workspace_cases_by_kind = {item["kind"]: item for item in workspace_cases_response.json()}
            assert "chargeback_review" in workspace_cases_by_kind
            assert workspace_cases_by_kind["chargeback_review"]["status"] == "waiting_on_ops"
            assert any(
                "Collect provider evidence before reserve release."
                in note
                for note in workspace_cases_by_kind["chargeback_review"]["notes"]
            )
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
