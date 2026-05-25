from __future__ import annotations

import uuid

import pytest
import structlog.contextvars
from httpx import AsyncClient
from prometheus_client import REGISTRY
from pydantic import SecretStr

from src.application.services.auth_service import AuthService
from src.config.settings import settings
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.dispute_case_model import DisputeCaseModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.infrastructure.monitoring.instrumentation.partner_runtime import bind_partner_runtime_context
from src.main import app
from tests.helpers.realm_auth import (
    FakeRedis,
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)


@pytest.fixture(autouse=True)
def _enable_partner_runtime_surfaces(monkeypatch) -> None:
    monkeypatch.setattr(settings, "partner_portal_enabled", True)
    monkeypatch.setattr(settings, "partner_applications_enabled", True)


def _metric_value(name: str, labels: dict[str, str]) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


def _partner_application_payload() -> dict[str, object]:
    return {
        "workspace_name": "Observability Portal Workspace",
        "contact_name": "Observability Owner",
        "contact_email": "observability-owner@example.com",
        "country": "DE",
        "website": "https://observability.example.com",
        "primary_lane": "creator_affiliate",
        "business_description": "Partner onboarding observability test workspace.",
        "acquisition_channels": "SEO, Telegram",
        "operating_regions": "EU",
        "languages": "en,de",
        "support_contact": "support@example.com",
        "technical_contact": "tech@example.com",
        "finance_contact": "finance@example.com",
        "compliance_accepted": True,
    }


async def _login_partner_and_submit_application(
    *,
    async_client: AsyncClient,
    sessionmaker,
    auth_service: AuthService,
    login: str,
    email: str,
    password: str,
) -> tuple[dict[str, str], str]:
    with sessionmaker() as db:
        realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
        partner_realm = await realm_repo.get_or_create_default_realm("partner")
        partner_user = AdminUserModel(
            login=login,
            email=email,
            auth_realm_id=partner_realm.id,
            password_hash=await auth_service.hash_password(password),
            role="operator",
            is_active=True,
            is_email_verified=True,
        )
        db.add(partner_user)
        db.commit()

    login_response = await async_client.post(
        "/api/v1/auth/login",
        headers={"X-Auth-Realm": "partner"},
        json={
            "login_or_email": email,
            "password": password,
        },
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    auth_headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Auth-Realm": "partner",
    }

    create_response = await async_client.post(
        "/api/v1/partner-application-drafts",
        headers=auth_headers,
        json={"draft_payload": _partner_application_payload()},
    )
    assert create_response.status_code == 201
    create_payload = create_response.json()
    draft_id = create_payload["draft"]["id"]
    workspace_id = create_payload["draft"]["workspace"]["id"]

    submit_response = await async_client.post(
        f"/api/v1/partner-application-drafts/{draft_id}/submit",
        headers=auth_headers,
    )
    assert submit_response.status_code == 200
    return auth_headers, workspace_id


@pytest.mark.integration
async def test_partner_runtime_metrics_increment_for_login_draft_submit_and_bootstrap(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    login_labels = {
        "surface": "partner_portal",
        "realm_type": "partner",
        "principal_class": "partner_operator",
        "result": "success",
        "reason": "none",
    }
    draft_labels = {
        "surface": "partner_portal",
        "lane": "creator_affiliate",
        "workspace_status": "email_verified",
        "result": "success",
    }
    submit_labels = {
        "surface": "partner_portal",
        "lane": "creator_affiliate",
        "workspace_status": "submitted",
        "result": "success",
        "reason": "initial_submission",
    }
    bootstrap_labels = {
        "surface": "partner_portal",
        "realm_type": "partner",
        "principal_class": "partner_operator",
        "workspace_status": "submitted",
        "result": "success",
    }

    before_login = _metric_value("cybervpn_partner_auth_login_attempts_total", login_labels)
    before_drafts = _metric_value("cybervpn_partner_application_drafts_created_total", draft_labels)
    before_submissions = _metric_value("cybervpn_partner_application_submissions_total", submit_labels)
    before_bootstrap = _metric_value("cybervpn_partner_bootstrap_requests_total", bootstrap_labels)
    before_submit_histogram = _metric_value("cybervpn_partner_application_submit_duration_seconds_count", {
        "surface": "partner_portal",
        "lane": "creator_affiliate",
        "workspace_status": "submitted",
        "result": "success",
    })

    try:
        async with override_realm_test_db(sessionmaker):
            with sessionmaker() as db:
                realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
                partner_realm = await realm_repo.get_or_create_default_realm("partner")
                partner_user = AdminUserModel(
                    login="partner_observability_operator",
                    email="partner-observability@example.com",
                    auth_realm_id=partner_realm.id,
                    password_hash=await auth_service.hash_password("PartnerObservability123!"),
                    role="operator",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add(partner_user)
                db.commit()

            login_response = await async_client.post(
                "/api/v1/auth/login",
                headers={"X-Auth-Realm": "partner"},
                json={
                    "login_or_email": "partner-observability@example.com",
                    "password": "PartnerObservability123!",
                },
            )
            assert login_response.status_code == 200
            access_token = login_response.json()["access_token"]
            auth_headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Auth-Realm": "partner",
            }

            create_response = await async_client.post(
                "/api/v1/partner-application-drafts",
                headers=auth_headers,
                json={"draft_payload": _partner_application_payload()},
            )
            assert create_response.status_code == 201
            create_payload = create_response.json()
            draft_id = create_payload["draft"]["id"]
            workspace_id = create_payload["draft"]["workspace"]["id"]

            submit_response = await async_client.post(
                f"/api/v1/partner-application-drafts/{draft_id}/submit",
                headers=auth_headers,
            )
            assert submit_response.status_code == 200

            bootstrap_response = await async_client.get(
                "/api/v1/partner-session/bootstrap",
                headers=auth_headers,
                params={"workspace_id": workspace_id},
            )
            assert bootstrap_response.status_code == 200
            assert bootstrap_response.json()["active_workspace"]["status"] == "submitted"

        assert _metric_value("cybervpn_partner_auth_login_attempts_total", login_labels) > before_login
        assert _metric_value("cybervpn_partner_application_drafts_created_total", draft_labels) > before_drafts
        assert _metric_value("cybervpn_partner_application_submissions_total", submit_labels) > before_submissions
        assert _metric_value("cybervpn_partner_bootstrap_requests_total", bootstrap_labels) > before_bootstrap
        assert _metric_value(
            "cybervpn_partner_application_submit_duration_seconds_count",
            {
                "surface": "partner_portal",
                "lane": "creator_affiliate",
                "workspace_status": "submitted",
                "result": "success",
            },
        ) > before_submit_histogram
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
async def test_partner_cross_realm_denial_metrics_increment_for_admin_token_on_partner_surface(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    mismatch_labels = {
        "surface": "partner_portal",
        "realm_type": "partner",
        "principal_class": "partner_operator",
        "reason": "realm_key_mismatch",
    }
    before_cross_realm = _metric_value("cybervpn_partner_auth_cross_realm_denied_total", mismatch_labels)
    before_wrong_host = _metric_value("cybervpn_partner_auth_wrong_host_token_rejected_total", mismatch_labels)

    try:
        async with override_realm_test_db(sessionmaker):
            with sessionmaker() as db:
                realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
                admin_realm = await realm_repo.get_or_create_default_realm("admin")
                await realm_repo.get_or_create_default_realm("partner")
                admin_user = AdminUserModel(
                    login="partner_metric_admin",
                    email="partner-metric-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("AdminObservability123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add(admin_user)
                db.commit()

            login_response = await async_client.post(
                "/api/v1/auth/login",
                headers={"X-Auth-Realm": "admin"},
                json={
                    "login_or_email": "partner-metric-admin@example.com",
                    "password": "AdminObservability123!",
                },
            )
            assert login_response.status_code == 200
            admin_access_token = login_response.json()["access_token"]

            partner_session_response = await async_client.get(
                "/api/v1/auth/session",
                headers={
                    "Authorization": f"Bearer {admin_access_token}",
                    "X-Auth-Realm": "partner",
                },
            )
            assert partner_session_response.status_code == 401

        assert _metric_value("cybervpn_partner_auth_cross_realm_denied_total", mismatch_labels) > before_cross_realm
        assert (
            _metric_value("cybervpn_partner_auth_wrong_host_token_rejected_total", mismatch_labels)
            > before_wrong_host
        )
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.integration
async def test_frontend_runtime_ingest_updates_frontend_observability_metrics(
    async_client: AsyncClient,
) -> None:
    route_load_labels = {
        "surface": "partner_portal",
        "route_group": "dashboard",
    }
    submit_failure_labels = {
        "surface": "partner_portal",
        "route_group": "auth",
        "form_name": "partner_login",
        "error_code": "invalid_credentials",
    }
    render_error_labels = {
        "surface": "admin_portal",
        "route_group": "dashboard",
        "error_code": "route_render_error",
    }
    before_route_load = _metric_value(
        "cybervpn_partner_frontend_route_load_duration_seconds_count",
        route_load_labels,
    )
    before_submit_failures = _metric_value(
        "cybervpn_partner_frontend_submit_failures_total",
        submit_failure_labels,
    )
    before_render_errors = _metric_value(
        "cybervpn_partner_frontend_render_errors_total",
        render_error_labels,
    )
    previous_secret = settings.frontend_observability_internal_secret
    settings.frontend_observability_internal_secret = SecretStr("frontend-obs-secret")

    try:
        route_load_response = await async_client.post(
            "/api/v1/monitoring/frontend-runtime-events",
            headers={"X-Frontend-Observability-Secret": "frontend-obs-secret"},
            json={
                "event": "route_load",
                "surface": "partner_portal",
                "connectionType": "4g",
                "deviceBucket": "desktop",
                "path": "/ru-RU/dashboard",
                "reducedMotion": "no-preference",
                "routeGroup": "dashboard",
                "saveData": "off",
                "viewportBucket": "desktop",
                "durationMs": 420,
            },
        )
        assert route_load_response.status_code == 202
        assert route_load_response.json() == {"status": "accepted"}

        submit_failure_response = await async_client.post(
            "/api/v1/monitoring/frontend-runtime-events",
            headers={"X-Frontend-Observability-Secret": "frontend-obs-secret"},
            json={
                "event": "submit_failure",
                "surface": "partner_portal",
                "connectionType": "4g",
                "deviceBucket": "desktop",
                "path": "/ru-RU/login",
                "reducedMotion": "no-preference",
                "routeGroup": "auth",
                "saveData": "off",
                "viewportBucket": "desktop",
                "formName": "partner_login",
                "errorCode": "invalid_credentials",
            },
        )
        assert submit_failure_response.status_code == 202

        render_error_response = await async_client.post(
            "/api/v1/monitoring/frontend-runtime-events",
            headers={"X-Frontend-Observability-Secret": "frontend-obs-secret"},
            json={
                "event": "render_error",
                "surface": "admin_portal",
                "connectionType": "ethernet",
                "deviceBucket": "desktop",
                "path": "/ru-RU/growth/partners",
                "reducedMotion": "no-preference",
                "routeGroup": "dashboard",
                "saveData": "off",
                "viewportBucket": "desktop",
                "errorCode": "route_render_error",
            },
        )
        assert render_error_response.status_code == 202

        assert _metric_value(
            "cybervpn_partner_frontend_route_load_duration_seconds_count",
            route_load_labels,
        ) > before_route_load
        assert _metric_value(
            "cybervpn_partner_frontend_submit_failures_total",
            submit_failure_labels,
        ) > before_submit_failures
        assert _metric_value(
            "cybervpn_partner_frontend_render_errors_total",
            render_error_labels,
        ) > before_render_errors
    finally:
        settings.frontend_observability_internal_secret = previous_secret


@pytest.mark.integration
async def test_frontend_runtime_ingest_requires_internal_secret(async_client: AsyncClient) -> None:
    previous_secret = settings.frontend_observability_internal_secret
    settings.frontend_observability_internal_secret = SecretStr("frontend-obs-secret")

    try:
        response = await async_client.post(
            "/api/v1/monitoring/frontend-runtime-events",
            json={
                "event": "route_load",
                "surface": "partner_portal",
                "connectionType": "4g",
                "deviceBucket": "desktop",
                "path": "/ru-RU/dashboard",
                "reducedMotion": "no-preference",
                "routeGroup": "dashboard",
                "saveData": "off",
                "viewportBucket": "desktop",
                "durationMs": 420,
            },
        )
        assert response.status_code == 401
    finally:
        settings.frontend_observability_internal_secret = previous_secret


@pytest.mark.integration
async def test_frontend_web_vital_ingest_updates_frontend_vital_metrics(
    async_client: AsyncClient,
) -> None:
    lcp_labels = {
        "surface": "partner_portal",
        "route_group": "dashboard",
        "rating": "good",
    }
    cls_labels = {
        "surface": "admin_portal",
        "route_group": "dashboard",
        "rating": "needs-improvement",
    }
    before_lcp = _metric_value(
        "cybervpn_partner_frontend_lcp_seconds_count",
        lcp_labels,
    )
    before_cls = _metric_value(
        "cybervpn_partner_frontend_cls_ratio_count",
        cls_labels,
    )
    previous_secret = settings.frontend_observability_internal_secret
    settings.frontend_observability_internal_secret = SecretStr("frontend-obs-secret")

    try:
        lcp_response = await async_client.post(
            "/api/v1/monitoring/frontend-web-vitals",
            headers={"X-Frontend-Observability-Secret": "frontend-obs-secret"},
            json={
                "surface": "partner_portal",
                "connectionType": "4g",
                "deviceBucket": "desktop",
                "locale": "ru-RU",
                "metric": "lcp",
                "path": "/ru-RU/dashboard",
                "rating": "good",
                "reducedMotion": "no-preference",
                "routeGroup": "dashboard",
                "saveData": "off",
                "value": 1800,
                "viewportBucket": "desktop",
            },
        )
        assert lcp_response.status_code == 202
        assert lcp_response.json() == {"status": "accepted"}

        cls_response = await async_client.post(
            "/api/v1/monitoring/frontend-web-vitals",
            headers={"X-Frontend-Observability-Secret": "frontend-obs-secret"},
            json={
                "surface": "admin_portal",
                "connectionType": "ethernet",
                "deviceBucket": "desktop",
                "locale": "ru-RU",
                "metric": "cls",
                "path": "/ru-RU/growth/partners",
                "rating": "needs-improvement",
                "reducedMotion": "no-preference",
                "routeGroup": "dashboard",
                "saveData": "off",
                "value": 0.14,
                "viewportBucket": "desktop",
            },
        )
        assert cls_response.status_code == 202

        assert _metric_value(
            "cybervpn_partner_frontend_lcp_seconds_count",
            lcp_labels,
        ) > before_lcp
        assert _metric_value(
            "cybervpn_partner_frontend_cls_ratio_count",
            cls_labels,
        ) > before_cls
    finally:
        settings.frontend_observability_internal_secret = previous_secret


@pytest.mark.integration
async def test_frontend_web_vital_ingest_requires_internal_secret(async_client: AsyncClient) -> None:
    previous_secret = settings.frontend_observability_internal_secret
    settings.frontend_observability_internal_secret = SecretStr("frontend-obs-secret")

    try:
        response = await async_client.post(
            "/api/v1/monitoring/frontend-web-vitals",
            json={
                "surface": "partner_portal",
                "connectionType": "4g",
                "deviceBucket": "desktop",
                "metric": "lcp",
                "path": "/ru-RU/dashboard",
                "rating": "good",
                "reducedMotion": "no-preference",
                "routeGroup": "dashboard",
                "saveData": "off",
                "value": 1800,
                "viewportBucket": "desktop",
            },
        )
        assert response.status_code == 401
    finally:
        settings.frontend_observability_internal_secret = previous_secret


@pytest.mark.integration
def test_partner_runtime_context_binds_trace_and_span_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeSpanContext:
        is_valid = True
        trace_id = int("1" * 32, 16)
        span_id = int("2" * 16, 16)

    class _FakeSpan:
        def __init__(self) -> None:
            self.attributes: dict[str, str] = {}

        def get_span_context(self) -> _FakeSpanContext:
            return _FakeSpanContext()

        def is_recording(self) -> bool:
            return True

        def set_attribute(self, key: str, value: str) -> None:
            self.attributes[key] = value

    fake_span = _FakeSpan()
    monkeypatch.setattr(
        "src.infrastructure.monitoring.instrumentation.partner_runtime.trace.get_current_span",
        lambda: fake_span,
    )

    structlog.contextvars.clear_contextvars()
    try:
        bind_partner_runtime_context(
            surface="partner_portal",
            realm_type="partner",
            principal_class="partner_operator",
            route_group="bootstrap",
        )
        context = structlog.contextvars.get_contextvars()
        assert context["trace_id"] == "1" * 32
        assert context["span_id"] == "2" * 16
        assert fake_span.attributes["cybervpn.surface"] == "partner_portal"
        assert fake_span.attributes["cybervpn.route_group"] == "bootstrap"
    finally:
        structlog.contextvars.clear_contextvars()


@pytest.mark.integration
async def test_partner_operational_metrics_increment_for_notifications_and_cases(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    notification_generated_labels = {
        "surface": "partner_portal",
        "notification_type": "application_submitted",
        "result": "success",
    }
    notification_read_labels = {
        "surface": "partner_portal",
        "notification_type": "application_submitted",
        "action": "read",
        "result": "success",
    }
    notification_archive_labels = {
        "surface": "partner_portal",
        "notification_type": "application_submitted",
        "action": "archive",
        "result": "success",
    }
    case_reply_labels = {
        "surface": "partner_portal",
        "case_type": "workspace_case",
        "action": "partner_reply",
        "result": "success",
    }
    case_ready_labels = {
        "surface": "partner_portal",
        "case_type": "workspace_case",
        "action": "partner_ready_for_ops",
        "result": "success",
    }

    before_notification_generated = _metric_value(
        "cybervpn_partner_notifications_generated_total",
        notification_generated_labels,
    )
    before_notification_read = _metric_value(
        "cybervpn_partner_notification_state_changes_total",
        notification_read_labels,
    )
    before_notification_archive = _metric_value(
        "cybervpn_partner_notification_state_changes_total",
        notification_archive_labels,
    )
    before_case_reply = _metric_value(
        "cybervpn_partner_case_actions_total",
        case_reply_labels,
    )
    before_case_ready = _metric_value(
        "cybervpn_partner_case_actions_total",
        case_ready_labels,
    )

    try:
        async with override_realm_test_db(sessionmaker):
            auth_headers, workspace_id = await _login_partner_and_submit_application(
                async_client=async_client,
                sessionmaker=sessionmaker,
                auth_service=auth_service,
                login="partner_operational_observer",
                email="partner-operational-observer@example.com",
                password="PartnerOperational123!",
            )

            with sessionmaker() as db:
                created_case = DisputeCaseModel(
                    id=uuid.uuid4(),
                    partner_account_id=uuid.UUID(workspace_id),
                    payment_dispute_id=None,
                    order_id=None,
                    case_kind="payment_dispute",
                    case_status="open",
                    summary="Operational observability test case",
                    case_payload={"source": "obs-03"},
                    notes_payload=["Partner action required"],
                    opened_by_admin_user_id=None,
                    assigned_to_admin_user_id=None,
                )
                db.add(created_case)
                db.commit()
                case_id = str(created_case.id)

            notifications_response = await async_client.get(
                "/api/v1/partner-notifications",
                headers=auth_headers,
                params={"workspace_id": workspace_id},
            )
            assert notifications_response.status_code == 200
            notifications = notifications_response.json()
            target_notification = next(
                (item for item in notifications if item["kind"] == "application_submitted"),
                None,
            )
            assert target_notification is not None

            mark_read_response = await async_client.post(
                f"/api/v1/partner-notifications/{target_notification['id']}/read",
                headers=auth_headers,
                params={"workspace_id": workspace_id},
            )
            assert mark_read_response.status_code == 200

            archive_response = await async_client.post(
                f"/api/v1/partner-notifications/{target_notification['id']}/archive",
                headers=auth_headers,
                params={"workspace_id": workspace_id},
            )
            assert archive_response.status_code == 200

            case_reply_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/cases/{case_id}/responses",
                headers=auth_headers,
                json={
                    "message": "Partner replied with evidence for observability coverage.",
                    "response_payload": {"kind": "reply"},
                },
            )
            assert case_reply_response.status_code == 201

            ready_for_ops_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/cases/{case_id}/ready-for-ops",
                headers=auth_headers,
                json={
                    "message": "Partner marked the case ready for ops review.",
                    "response_payload": {"kind": "ready_for_ops"},
                },
            )
            assert ready_for_ops_response.status_code == 201

        assert (
            _metric_value("cybervpn_partner_notifications_generated_total", notification_generated_labels)
            > before_notification_generated
        )
        assert (
            _metric_value("cybervpn_partner_notification_state_changes_total", notification_read_labels)
            > before_notification_read
        )
        assert (
            _metric_value("cybervpn_partner_notification_state_changes_total", notification_archive_labels)
            > before_notification_archive
        )
        assert _metric_value("cybervpn_partner_case_actions_total", case_reply_labels) > before_case_reply
        assert _metric_value("cybervpn_partner_case_actions_total", case_ready_labels) > before_case_ready
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
