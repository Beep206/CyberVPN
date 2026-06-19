from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.application.services.privacy_request_service import PrivacyRequestService
from src.application.use_cases.auth_realms import RealmResolution
from src.domain.entities.privacy_request import InvalidPrivacyRequestTransitionError, PrivacyRequestStatus
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.outbox_event_model import OutboxEventModel
from src.infrastructure.database.models.privacy_request_model import PrivacyRequestEventModel, PrivacyRequestModel
from src.infrastructure.database.models.support_ticket_model import (
    SupportTicketEventModel,
    SupportTicketMessageModel,
    SupportTicketModel,
)
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.main import app
from src.presentation.dependencies.auth import get_current_active_user, get_current_active_web_user
from src.presentation.dependencies.auth_realms import get_request_web_auth_realm
from tests.helpers.realm_auth import (
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
def _clear_dependency_overrides():
    yield
    app.dependency_overrides.pop(get_current_active_user, None)
    app.dependency_overrides.pop(get_current_active_web_user, None)
    app.dependency_overrides.pop(get_request_web_auth_realm, None)


def _create_privacy_workflow_tables(engine) -> None:
    with engine.begin() as conn:
        SupportTicketModel.__table__.create(conn, checkfirst=True)
        SupportTicketMessageModel.__table__.create(conn, checkfirst=True)
        SupportTicketEventModel.__table__.create(conn, checkfirst=True)
        PrivacyRequestModel.__table__.create(conn, checkfirst=True)
        PrivacyRequestEventModel.__table__.create(conn, checkfirst=True)


async def _seed_privacy_context(sessionmaker) -> tuple[RealmResolution, AdminUserModel, AdminUserModel]:
    now = datetime.now(UTC)
    with sessionmaker() as db:
        realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
        customer_realm = await realm_repo.get_or_create_default_realm("customer")
        customer = AdminUserModel(
            id=uuid.uuid4(),
            login="privacy-customer",
            email="privacy-customer@example.test",
            auth_realm_id=customer_realm.id,
            password_hash="not-a-real-hash",
            role="user",
            is_active=True,
            is_email_verified=True,
            status="active",
            created_at=now,
            updated_at=now,
        )
        reviewer = AdminUserModel(
            id=uuid.uuid4(),
            login="privacy-reviewer",
            email="privacy-reviewer@example.test",
            password_hash="not-a-real-hash",
            role=AdminRole.ADMIN.value,
            is_active=True,
            is_email_verified=True,
            status="active",
            created_at=now,
            updated_at=now,
        )
        db.add_all([customer, reviewer])
        db.commit()
        return RealmResolution(auth_realm=customer_realm, source="default"), customer, reviewer


@pytest.mark.asyncio
async def test_privacy_request_creation_links_support_ticket_and_outbox_idempotently() -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)
    _create_privacy_workflow_tables(engine)

    try:
        current_realm, customer, _reviewer = await _seed_privacy_context(sessionmaker)
        idempotency_key = str(uuid.uuid4())

        with sessionmaker() as db:
            service = PrivacyRequestService(SyncSessionAdapter(db))
            result = await service.create_customer_request(
                current_user=customer,
                current_realm=current_realm,
                request_type="account_deletion",
                reason_code="delete email privacy-customer@example.test",
                notes="Please remove vless://secret-token and privacy-customer@example.test",
                locale="ru-RU",
                idempotency_key=idempotency_key,
            )

            assert result.existing is False
            assert result.request.public_id.startswith("PRV-")
            assert result.request.customer_account_id == customer.id
            assert result.request.reason_code == "delete email [redacted-email]"
            assert "[redacted-email]" in (result.request.notes_redacted or "")
            assert "[redacted-url]" in (result.request.notes_redacted or "")
            assert result.support_ticket.public_id.startswith("SUP-")
            assert result.support_ticket.status == "pending_support"
            assert result.support_ticket.category == "privacy"
            assert result.support_ticket.priority == "high"
            assert result.support_ticket.source == "customer_web"

            duplicate = await service.create_customer_request(
                current_user=customer,
                current_realm=current_realm,
                request_type="account_deletion",
                reason_code="ignored",
                notes="ignored",
                locale="ru-RU",
                idempotency_key=idempotency_key,
            )

            assert duplicate.existing is True
            assert duplicate.request.id == result.request.id

            event_names = list(db.execute(select(OutboxEventModel.event_name)).scalars().all())
            assert "privacy_request.created" in event_names
            assert "privacy_request.existing_returned" in event_names
            db.commit()
    finally:
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_privacy_request_customer_api_creates_lists_and_updates_admin_queue(
    async_client: AsyncClient,
) -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)
    _create_privacy_workflow_tables(engine)

    try:
        current_realm, customer, reviewer = await _seed_privacy_context(sessionmaker)
        app.dependency_overrides[get_current_active_web_user] = lambda: customer
        app.dependency_overrides[get_request_web_auth_realm] = lambda: current_realm

        async with override_realm_test_db(sessionmaker):
            create_response = await async_client.post(
                "/api/v1/auth/me/privacy-requests",
                headers={"Idempotency-Key": str(uuid.uuid4())},
                json={
                    "request_type": "account_deletion",
                    "reason_code": "customer_requested",
                    "notes": "Please delete my account.",
                },
            )
            assert create_response.status_code == 202
            created = create_response.json()
            assert created["privacy_request_reference"].startswith("PRV-")
            assert created["ticket_reference"].startswith("SUP-")
            assert created["status"] == "submitted"
            assert created["existing"] is False

            list_response = await async_client.get(
                "/api/v1/auth/me/privacy-requests",
                params={"request_type": "account_deletion"},
            )
            assert list_response.status_code == 200
            listed = list_response.json()["requests"]
            assert listed[0]["privacy_request_reference"] == created["privacy_request_reference"]
            assert listed[0]["allowed_actions"] == ["cancel"]

            app.dependency_overrides[get_current_active_user] = lambda: reviewer
            queue_response = await async_client.get(
                "/api/v1/admin/privacy-requests/queue-count",
                headers={"host": "testserver"},
            )
            assert queue_response.status_code == 200
            assert queue_response.json()["count"] == 1
    finally:
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_privacy_request_admin_workflow_requires_identity_before_approval() -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)
    _create_privacy_workflow_tables(engine)

    try:
        current_realm, customer, reviewer = await _seed_privacy_context(sessionmaker)

        with sessionmaker() as db:
            service = PrivacyRequestService(SyncSessionAdapter(db))
            created = await service.create_customer_request(
                current_user=customer,
                current_realm=current_realm,
                request_type="account_deletion",
                reason_code="customer_requested",
                notes=None,
                locale="ru-RU",
                idempotency_key=str(uuid.uuid4()),
            )

            with pytest.raises(InvalidPrivacyRequestTransitionError):
                await service.approve(
                    reference=created.request.public_id,
                    admin_id=reviewer.id,
                    decision_reason="Verified by policy",
                )

            started = await service.start_review(
                reference=created.request.public_id,
                admin_id=reviewer.id,
                assign_to_self=True,
            )
            assert started.request.status == PrivacyRequestStatus.IDENTITY_VERIFICATION.value

            verified = await service.verify_identity(
                reference=created.request.public_id,
                admin_id=reviewer.id,
                verification_method="support_ticket",
                safe_note="No secrets in this note",
            )
            assert verified.request.status == PrivacyRequestStatus.PENDING_DECISION.value

            approved = await service.approve(
                reference=created.request.public_id,
                admin_id=reviewer.id,
                decision_reason="Identity verified and deletion approved",
            )
            assert approved.request.status == PrivacyRequestStatus.APPROVED.value

            scheduled = await service.schedule(
                reference=created.request.public_id,
                admin_id=reviewer.id,
                scheduled_for=None,
            )
            assert scheduled.request.status == PrivacyRequestStatus.SCHEDULED.value
            assert scheduled.request.scheduled_for is not None

            ticket = db.get(SupportTicketModel, created.request.support_ticket_id)
            assert ticket is not None
            assert ticket.assigned_admin_id == reviewer.id

            event_types = set(db.execute(select(PrivacyRequestEventModel.event_type)).scalars().all())
            assert {
                "created",
                "review_started",
                "identity_verified",
                "approved",
                "scheduled",
            }.issubset(event_types)
            db.commit()
    finally:
        cleanup_sqlite_file(sqlite_path)
