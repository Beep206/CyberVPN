from __future__ import annotations

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
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

pytestmark = [pytest.mark.e2e]


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
    *,
    realm_key: str,
    login_or_email: str,
    password: str,
) -> dict:
    response = await async_client.post(
        "/api/v1/auth/login",
        headers={"X-Auth-Realm": realm_key},
        json={"login_or_email": login_or_email, "password": password},
    )
    assert response.status_code == 200
    return response.json()


def _auth_headers(*, token: str, realm_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Auth-Realm": realm_key,
    }


def _application_payload() -> dict[str, object]:
    return {
        "workspace_name": "Aurora Partner Ops",
        "contact_name": "Aurora Ops",
        "contact_email": "aurora.ops@example.com",
        "country": "DE",
        "website": "https://aurora.example.com",
        "primary_lane": "creator_affiliate",
        "business_description": "Privacy and VPN creator studio.",
        "acquisition_channels": "SEO, YouTube, Telegram",
        "operating_regions": "EU, LATAM",
        "languages": "en,de,es",
        "support_contact": "support@aurora.example.com",
        "technical_contact": "tech@aurora.example.com",
        "finance_contact": "finance@aurora.example.com",
        "compliance_accepted": True,
    }


@pytest.mark.integration
async def test_e2e_partner_001_application_review_probation_legal_and_notification_loop(
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
                partner_realm = await realm_repo.get_or_create_default_realm("partner")

                reviewer = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="partner_reviewer",
                    email="partner-reviewer@example.com",
                    password="PartnerReviewer123!",
                    role="admin",
                )
                applicant = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=partner_realm.id,
                    login="aurora_partner",
                    email="aurora-partner@example.com",
                    password="AuroraPartner123!",
                    role="operator",
                )

            reviewer_login = await _login(
                async_client,
                realm_key="admin",
                login_or_email=reviewer.email,
                password="PartnerReviewer123!",
            )
            applicant_login = await _login(
                async_client,
                realm_key="partner",
                login_or_email=applicant.email,
                password="AuroraPartner123!",
            )

            admin_headers = _auth_headers(token=reviewer_login["access_token"], realm_key="admin")
            partner_headers = _auth_headers(token=applicant_login["access_token"], realm_key="partner")

            create_draft_response = await async_client.post(
                "/api/v1/partner-application-drafts",
                headers=partner_headers,
                json={"draft_payload": _application_payload()},
            )
            assert create_draft_response.status_code == 201
            create_draft_payload = create_draft_response.json()
            draft_id = create_draft_payload["draft"]["id"]
            workspace_id = create_draft_payload["draft"]["workspace"]["id"]
            lane_application_id = create_draft_payload["lane_applications"][0]["id"]
            assert create_draft_payload["draft"]["workspace"]["status"] == "email_verified"
            assert create_draft_payload["lane_applications"][0]["lane_key"] == "creator_affiliate"

            submit_response = await async_client.post(
                f"/api/v1/partner-application-drafts/{draft_id}/submit",
                headers=partner_headers,
            )
            assert submit_response.status_code == 200
            submit_payload = submit_response.json()
            assert submit_payload["draft"]["workspace"]["status"] == "submitted"
            assert submit_payload["lane_applications"][0]["status"] == "pending"

            admin_list_response = await async_client.get(
                "/api/v1/admin/partner-applications",
                headers=admin_headers,
            )
            assert admin_list_response.status_code == 200
            assert any(
                item["workspace"]["id"] == workspace_id and item["workspace"]["status"] == "submitted"
                for item in admin_list_response.json()
            )

            request_info_response = await async_client.post(
                f"/api/v1/admin/partner-applications/{workspace_id}/request-info",
                headers=admin_headers,
                json={
                    "message": "Please attach audience evidence and confirm disclosure wording.",
                    "request_kind": "application_evidence",
                    "required_fields": ["acquisition_channels"],
                    "required_attachments": ["audience_screenshot"],
                    "lane_application_id": lane_application_id,
                },
            )
            assert request_info_response.status_code == 201
            request_info_payload = request_info_response.json()
            review_request_id = request_info_payload["id"]
            assert request_info_payload["status"] == "open"

            bootstrap_needs_info_response = await async_client.get(
                "/api/v1/partner-session/bootstrap",
                headers=partner_headers,
                params={"workspace_id": workspace_id},
            )
            assert bootstrap_needs_info_response.status_code == 200
            bootstrap_needs_info = bootstrap_needs_info_response.json()
            assert bootstrap_needs_info["principal"]["auth_realm_key"] == "partner"
            assert bootstrap_needs_info["active_workspace"]["status"] == "needs_info"
            assert bootstrap_needs_info["counters"]["open_review_requests"] >= 1
            assert any(
                task["source_id"] == review_request_id for task in bootstrap_needs_info["pending_tasks"]
            )

            notifications_before_read_response = await async_client.get(
                "/api/v1/partner-notifications",
                headers=partner_headers,
                params={"workspace_id": workspace_id},
            )
            assert notifications_before_read_response.status_code == 200
            notifications_before_read = notifications_before_read_response.json()
            review_notification = next(
                item
                for item in notifications_before_read
                if item["kind"] == "review_request_opened" and item["source_id"] == review_request_id
            )

            counters_before_read_response = await async_client.get(
                "/api/v1/partner-notifications/counters",
                headers=partner_headers,
                params={"workspace_id": workspace_id},
            )
            assert counters_before_read_response.status_code == 200
            unread_before = counters_before_read_response.json()["unread_notifications"]

            mark_read_response = await async_client.post(
                f"/api/v1/partner-notifications/{review_notification['id']}/read",
                headers=partner_headers,
                params={"workspace_id": workspace_id},
            )
            assert mark_read_response.status_code == 200
            assert mark_read_response.json()["unread"] is False

            counters_after_read_response = await async_client.get(
                "/api/v1/partner-notifications/counters",
                headers=partner_headers,
                params={"workspace_id": workspace_id},
            )
            assert counters_after_read_response.status_code == 200
            unread_after = counters_after_read_response.json()["unread_notifications"]
            assert unread_after <= unread_before - 1

            attachment_response = await async_client.post(
                f"/api/v1/partner-application-drafts/{draft_id}/attachments",
                headers=partner_headers,
                json={
                    "attachment_type": "audience_screenshot",
                    "storage_key": "partner-apps/aurora/audience-proof.png",
                    "file_name": "audience-proof.png",
                    "review_request_id": review_request_id,
                    "attachment_metadata": {"channel": "youtube"},
                },
            )
            assert attachment_response.status_code == 201
            assert attachment_response.json()["review_request_id"] == review_request_id

            respond_review_request_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/review-requests/{review_request_id}/responses",
                headers=partner_headers,
                json={
                    "message": "Audience evidence attached and disclosure wording updated.",
                    "response_payload": {"storage_key": "partner-apps/aurora/audience-proof.png"},
                },
            )
            assert respond_review_request_response.status_code == 201

            resubmit_response = await async_client.post(
                f"/api/v1/partner-application-drafts/{draft_id}/resubmit",
                headers=partner_headers,
            )
            assert resubmit_response.status_code == 200
            assert resubmit_response.json()["draft"]["workspace"]["status"] == "submitted"

            approve_probation_response = await async_client.post(
                f"/api/v1/admin/partner-applications/{workspace_id}/approve-probation",
                headers=admin_headers,
                json={
                    "reason_code": "manual_review_passed",
                    "reason_summary": "Approved to probation after evidence review.",
                },
            )
            assert approve_probation_response.status_code == 200
            approve_probation_payload = approve_probation_response.json()
            assert approve_probation_payload["workspace"]["status"] == "approved_probation"
            assert approve_probation_payload["lane_applications"][0]["status"] == "approved_probation"

            bootstrap_probation_response = await async_client.get(
                "/api/v1/partner-session/bootstrap",
                headers=partner_headers,
                params={"workspace_id": workspace_id},
            )
            assert bootstrap_probation_response.status_code == 200
            bootstrap_probation = bootstrap_probation_response.json()
            assert bootstrap_probation["active_workspace"]["status"] == "approved_probation"
            assert bootstrap_probation["counters"]["pending_tasks"] >= 1

            notifications_after_probation_response = await async_client.get(
                "/api/v1/partner-notifications",
                headers=partner_headers,
                params={"workspace_id": workspace_id},
            )
            assert notifications_after_probation_response.status_code == 200
            notifications_after_probation = notifications_after_probation_response.json()
            assert any(item["kind"] == "application_approved_probation" for item in notifications_after_probation)
            assert any(item["kind"] == "legal_acceptance_required" for item in notifications_after_probation)

            legal_documents_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/legal-documents",
                headers=partner_headers,
            )
            assert legal_documents_response.status_code == 200
            pending_documents = [
                item["kind"]
                for item in legal_documents_response.json()
                if item["status"] == "pending_acceptance"
            ]
            assert pending_documents

            for document_kind in pending_documents:
                accept_response = await async_client.post(
                    f"/api/v1/partner-workspaces/{workspace_id}/legal-documents/{document_kind}/accept",
                    headers=partner_headers,
                )
                assert accept_response.status_code == 200
                assert accept_response.json()["status"] == "accepted"

            legal_documents_after_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/legal-documents",
                headers=partner_headers,
            )
            assert legal_documents_after_response.status_code == 200
            assert all(item["status"] == "accepted" for item in legal_documents_after_response.json())
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
async def test_e2e_perm_010_015_role_permissions_and_admin_partner_sync(
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
                partner_realm = await realm_repo.get_or_create_default_realm("partner")

                admin_user = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="wb10_admin",
                    email="wb10-admin@example.com",
                    password="Wb10Admin123!",
                    role="admin",
                )
                owner_user = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=partner_realm.id,
                    login="wb10_owner",
                    email="wb10-owner@example.com",
                    password="Wb10Owner123!",
                    role="operator",
                )
                finance_user = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=partner_realm.id,
                    login="wb10_finance",
                    email="wb10-finance@example.com",
                    password="Wb10Finance123!",
                    role="operator",
                )
                traffic_user = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=partner_realm.id,
                    login="wb10_traffic",
                    email="wb10-traffic@example.com",
                    password="Wb10Traffic123!",
                    role="operator",
                )

            admin_login = await _login(
                async_client,
                realm_key="admin",
                login_or_email=admin_user.email,
                password="Wb10Admin123!",
            )
            owner_login = await _login(
                async_client,
                realm_key="partner",
                login_or_email=owner_user.email,
                password="Wb10Owner123!",
            )
            finance_login = await _login(
                async_client,
                realm_key="partner",
                login_or_email=finance_user.email,
                password="Wb10Finance123!",
            )
            traffic_login = await _login(
                async_client,
                realm_key="partner",
                login_or_email=traffic_user.email,
                password="Wb10Traffic123!",
            )

            admin_headers = _auth_headers(token=admin_login["access_token"], realm_key="admin")
            owner_headers = _auth_headers(token=owner_login["access_token"], realm_key="partner")
            finance_headers = _auth_headers(token=finance_login["access_token"], realm_key="partner")
            traffic_headers = _auth_headers(token=traffic_login["access_token"], realm_key="partner")

            workspace_response = await async_client.post(
                "/api/v1/admin/partner-workspaces",
                headers=admin_headers,
                json={
                    "display_name": "Conformance Workspace",
                    "owner_admin_user_id": str(owner_user.id),
                },
            )
            assert workspace_response.status_code == 201
            workspace_id = workspace_response.json()["id"]

            add_finance_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/members",
                headers=owner_headers,
                json={"admin_user_id": str(finance_user.id), "role_key": "finance"},
            )
            assert add_finance_response.status_code == 201
            assert add_finance_response.json()["role_key"] == "finance"

            add_traffic_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/members",
                headers=owner_headers,
                json={"admin_user_id": str(traffic_user.id), "role_key": "traffic_manager"},
            )
            assert add_traffic_response.status_code == 201
            assert add_traffic_response.json()["role_key"] == "traffic_manager"

            finance_bootstrap_response = await async_client.get(
                "/api/v1/partner-session/bootstrap",
                headers=finance_headers,
                params={"workspace_id": workspace_id},
            )
            assert finance_bootstrap_response.status_code == 200
            finance_bootstrap = finance_bootstrap_response.json()
            assert "payouts_write" in finance_bootstrap["current_permission_keys"]
            assert "traffic_write" not in finance_bootstrap["current_permission_keys"]

            traffic_bootstrap_response = await async_client.get(
                "/api/v1/partner-session/bootstrap",
                headers=traffic_headers,
                params={"workspace_id": workspace_id},
            )
            assert traffic_bootstrap_response.status_code == 200
            traffic_bootstrap = traffic_bootstrap_response.json()
            assert "traffic_write" in traffic_bootstrap["current_permission_keys"]
            assert "payouts_write" not in traffic_bootstrap["current_permission_keys"]

            create_payout_account_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/payout-accounts",
                headers=finance_headers,
                json={
                    "payout_rail": "manual",
                    "display_label": "Primary finance route",
                    "destination_reference": "finance@example.com",
                    "destination_metadata": {"channel": "email"},
                    "make_default": True,
                },
            )
            assert create_payout_account_response.status_code == 201
            payout_account_id = create_payout_account_response.json()["id"]

            finance_traffic_attempt = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/traffic-declarations",
                headers=finance_headers,
                json={
                    "declaration_kind": "approved_sources",
                    "scope_label": "Finance should not write traffic",
                    "declaration_payload": {"channels": ["seo"]},
                    "notes": ["Should be blocked by permissions."],
                },
            )
            assert finance_traffic_attempt.status_code == 403

            traffic_declaration_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/traffic-declarations",
                headers=traffic_headers,
                json={
                    "declaration_kind": "approved_sources",
                    "scope_label": "Traffic-managed acquisition set",
                    "declaration_payload": {"channels": ["seo", "telegram"]},
                    "notes": ["Traffic manager submitted the approved source list."],
                },
            )
            assert traffic_declaration_response.status_code == 201

            traffic_payout_attempt = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/payout-accounts",
                headers=traffic_headers,
                json={
                    "payout_rail": "manual",
                    "display_label": "Traffic should not create payout routes",
                    "destination_reference": "traffic@example.com",
                    "destination_metadata": {"channel": "email"},
                },
            )
            assert traffic_payout_attempt.status_code == 403

            verify_payout_response = await async_client.post(
                f"/api/v1/partner-payout-accounts/{payout_account_id}/verify",
                headers=admin_headers,
            )
            assert verify_payout_response.status_code == 200
            assert verify_payout_response.json()["verification_status"] == "verified"
            assert verify_payout_response.json()["approval_status"] == "approved"

            finance_payout_accounts_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/payout-accounts",
                headers=finance_headers,
            )
            assert finance_payout_accounts_response.status_code == 200
            assert finance_payout_accounts_response.json()[0]["verification_status"] == "verified"
            assert finance_payout_accounts_response.json()[0]["approval_status"] == "approved"

            admin_traffic_list_response = await async_client.get(
                "/api/v1/traffic-declarations/",
                headers=admin_headers,
                params={"partner_account_id": workspace_id},
            )
            assert admin_traffic_list_response.status_code == 200
            assert admin_traffic_list_response.json()[0]["scope_label"] == "Traffic-managed acquisition set"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
@pytest.mark.security
async def test_e2e_auth_010_016_partner_realm_bootstrap_requires_partner_session_and_revocation(
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
                partner_realm = await realm_repo.get_or_create_default_realm("partner")

                admin_user = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="conformance_admin",
                    email="conformance-admin@example.com",
                    password="ConformanceAdmin123!",
                    role="admin",
                )
                partner_user = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=partner_realm.id,
                    login="conformance_partner",
                    email="conformance-partner@example.com",
                    password="ConformancePartner123!",
                    role="operator",
                )

            admin_login = await _login(
                async_client,
                realm_key="admin",
                login_or_email=admin_user.email,
                password="ConformanceAdmin123!",
            )
            partner_login = await _login(
                async_client,
                realm_key="partner",
                login_or_email=partner_user.email,
                password="ConformancePartner123!",
            )

            admin_headers = _auth_headers(token=admin_login["access_token"], realm_key="admin")
            partner_headers = _auth_headers(token=partner_login["access_token"], realm_key="partner")

            create_draft_response = await async_client.post(
                "/api/v1/partner-application-drafts",
                headers=partner_headers,
                json={"draft_payload": _application_payload()},
            )
            assert create_draft_response.status_code == 201
            workspace_id = create_draft_response.json()["draft"]["workspace"]["id"]

            partner_bootstrap_response = await async_client.get(
                "/api/v1/partner-session/bootstrap",
                headers=partner_headers,
                params={"workspace_id": workspace_id},
            )
            assert partner_bootstrap_response.status_code == 200
            assert partner_bootstrap_response.json()["principal"]["principal_type"] == "partner_operator"

            admin_realm_bootstrap_response = await async_client.get(
                "/api/v1/partner-session/bootstrap",
                headers=admin_headers,
                params={"workspace_id": workspace_id},
            )
            assert admin_realm_bootstrap_response.status_code == 403

            partner_token_on_admin_realm_response = await async_client.get(
                "/api/v1/partner-session/bootstrap",
                headers={
                    "Authorization": f"Bearer {partner_login['access_token']}",
                    "X-Auth-Realm": "admin",
                },
                params={"workspace_id": workspace_id},
            )
            assert partner_token_on_admin_realm_response.status_code == 401

            admin_token_on_partner_realm_response = await async_client.get(
                "/api/v1/partner-session/bootstrap",
                headers={
                    "Authorization": f"Bearer {admin_login['access_token']}",
                    "X-Auth-Realm": "partner",
                },
                params={"workspace_id": workspace_id},
            )
            assert admin_token_on_partner_realm_response.status_code == 401

            logout_all_response = await async_client.post(
                "/api/v1/auth/logout-all",
                headers=partner_headers,
            )
            assert logout_all_response.status_code == 200
            assert logout_all_response.json()["sessions_revoked"] >= 1

            revoked_bootstrap_response = await async_client.get(
                "/api/v1/partner-session/bootstrap",
                headers=partner_headers,
                params={"workspace_id": workspace_id},
            )
            assert revoked_bootstrap_response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
