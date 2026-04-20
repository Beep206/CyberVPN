from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.application.use_cases.settlement import CreateReserveUseCase
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel
from src.infrastructure.database.models.risk_review_model import RiskReviewModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.infrastructure.database.repositories.risk_subject_repo import RiskSubjectGraphRepository
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


@pytest.mark.asyncio
async def test_partner_payout_account_lifecycle_and_default_selection(async_client: AsyncClient) -> None:
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

                await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="payout_admin",
                    email="payout-admin@example.com",
                    password="PayoutAdmin123!",
                    role="admin",
                )
                owner_user = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="payout_owner",
                    email="payout-owner@example.com",
                    password="PayoutOwner123!",
                    role="viewer",
                )

            admin_token = await _login(async_client, "payout-admin@example.com", "PayoutAdmin123!")
            owner_token = await _login(async_client, "payout-owner@example.com", "PayoutOwner123!")
            admin_headers = {"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"}
            owner_headers = {"Authorization": f"Bearer {owner_token}", "X-Auth-Realm": "admin"}

            workspace_response = await async_client.post(
                "/api/v1/admin/partner-workspaces",
                headers=admin_headers,
                json={
                    "display_name": "Payout Workspace",
                    "owner_admin_user_id": str(owner_user.id),
                },
            )
            assert workspace_response.status_code == 201
            workspace_id = workspace_response.json()["id"]

            first_response = await async_client.post(
                "/api/v1/partner-payout-accounts/",
                headers=owner_headers,
                json={
                    "partner_account_id": workspace_id,
                    "payout_rail": "cryptobot",
                    "display_label": "Primary Crypto",
                    "destination_reference": "UQA1234567890PRIMARY",
                    "destination_metadata": {"network": "TRC20"},
                },
            )
            assert first_response.status_code == 201
            first_payload = first_response.json()
            assert first_payload["is_default"] is True
            assert first_payload["verification_status"] == "pending"
            assert first_payload["approval_status"] == "pending"

            second_response = await async_client.post(
                "/api/v1/partner-payout-accounts/",
                headers=owner_headers,
                json={
                    "partner_account_id": workspace_id,
                    "payout_rail": "manual",
                    "display_label": "Manual Reserve Route",
                    "destination_reference": "finance@example.test",
                    "destination_metadata": {"channel": "email"},
                },
            )
            assert second_response.status_code == 201
            second_payload = second_response.json()
            assert second_payload["is_default"] is False

            list_response = await async_client.get(
                f"/api/v1/partner-payout-accounts/?partner_account_id={workspace_id}",
                headers=owner_headers,
            )
            assert list_response.status_code == 200
            assert len(list_response.json()) == 2

            verify_response = await async_client.post(
                f"/api/v1/partner-payout-accounts/{second_payload['id']}/verify",
                headers=admin_headers,
            )
            assert verify_response.status_code == 200
            verified_payload = verify_response.json()
            assert verified_payload["verification_status"] == "verified"
            assert verified_payload["approval_status"] == "approved"

            make_default_response = await async_client.post(
                f"/api/v1/partner-payout-accounts/{second_payload['id']}/make-default",
                headers=owner_headers,
            )
            assert make_default_response.status_code == 200
            assert make_default_response.json()["is_default"] is True

            refreshed_first = await async_client.get(
                f"/api/v1/partner-payout-accounts/{first_payload['id']}",
                headers=owner_headers,
            )
            assert refreshed_first.status_code == 200
            assert refreshed_first.json()["is_default"] is False

            suspend_response = await async_client.post(
                f"/api/v1/partner-payout-accounts/{second_payload['id']}/suspend",
                headers=admin_headers,
                json={"reason_code": "risk_manual_hold"},
            )
            assert suspend_response.status_code == 200
            suspended_payload = suspend_response.json()
            assert suspended_payload["account_status"] == "suspended"
            assert suspended_payload["is_default"] is False

            archive_response = await async_client.post(
                f"/api/v1/partner-payout-accounts/{first_payload['id']}/archive",
                headers=admin_headers,
                json={"reason_code": "legacy_destination_retired"},
            )
            assert archive_response.status_code == 200
            archived_payload = archive_response.json()
            assert archived_payload["account_status"] == "archived"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_partner_payout_account_eligibility_reflects_workspace_risk_and_finance_controls(
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
                    login="eligibility_admin",
                    email="eligibility-admin@example.com",
                    password="EligibilityAdmin123!",
                    role="admin",
                )
                owner_user = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="eligibility_owner",
                    email="eligibility-owner@example.com",
                    password="EligibilityOwner123!",
                    role="viewer",
                )

            admin_token = await _login(async_client, "eligibility-admin@example.com", "EligibilityAdmin123!")
            owner_token = await _login(async_client, "eligibility-owner@example.com", "EligibilityOwner123!")
            admin_headers = {"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"}
            owner_headers = {"Authorization": f"Bearer {owner_token}", "X-Auth-Realm": "admin"}

            workspace_response = await async_client.post(
                "/api/v1/admin/partner-workspaces",
                headers=admin_headers,
                json={
                    "display_name": "Eligibility Workspace",
                    "owner_admin_user_id": str(owner_user.id),
                },
            )
            assert workspace_response.status_code == 201
            workspace_id = workspace_response.json()["id"]

            create_response = await async_client.post(
                "/api/v1/partner-payout-accounts/",
                headers=owner_headers,
                json={
                    "partner_account_id": workspace_id,
                    "payout_rail": "cryptobot",
                    "display_label": "Eligibility Route",
                    "destination_reference": "UQA0987654321ELIGIBILITY",
                },
            )
            assert create_response.status_code == 201
            payout_account_id = create_response.json()["id"]

            verify_response = await async_client.post(
                f"/api/v1/partner-payout-accounts/{payout_account_id}/verify",
                headers=admin_headers,
            )
            assert verify_response.status_code == 200

            eligibility_response = await async_client.get(
                f"/api/v1/partner-payout-accounts/{payout_account_id}/eligibility",
                headers=owner_headers,
            )
            assert eligibility_response.status_code == 200
            assert eligibility_response.json()["eligible"] is True

            with sessionmaker() as db:
                adapter = SyncSessionAdapter(db)
                reserve = await CreateReserveUseCase(adapter).execute(
                    partner_account_id=uuid.UUID(workspace_id),
                    amount=Decimal("25.00"),
                    currency_code="USD",
                    reserve_scope="partner_account",
                    reserve_reason_type="manual",
                    reason_code="finance_buffer",
                    created_by_admin_user_id=admin_user.id,
                )
                risk_repo = RiskSubjectGraphRepository(adapter)
                risk_subject = await risk_repo.get_subject_by_principal(
                    principal_class="partner_operator",
                    principal_subject=f"partner_account:{workspace_id}",
                    auth_realm_id=None,
                )
                assert risk_subject is not None
                db.add(
                    RiskReviewModel(
                        id=uuid.uuid4(),
                        risk_subject_id=risk_subject.id,
                        review_type="partner_payout",
                        status="open",
                        decision="hold",
                        reason="manual finance hold",
                        evidence={"reserve_id": str(reserve.id)},
                        created_by_admin_user_id=admin_user.id,
                    )
                )
                workspace = db.get(PartnerAccountModel, uuid.UUID(workspace_id))
                assert workspace is not None
                workspace.status = "suspended"
                db.commit()

            blocked_response = await async_client.get(
                f"/api/v1/partner-payout-accounts/{payout_account_id}/eligibility",
                headers=owner_headers,
            )
            assert blocked_response.status_code == 200
            blocked_payload = blocked_response.json()
            assert blocked_payload["eligible"] is False
            assert "active_partner_reserve" in blocked_payload["reason_codes"]
            assert "risk_review_hold" in blocked_payload["reason_codes"]
            assert "workspace_inactive" in blocked_payload["reason_codes"]
            assert blocked_payload["blocking_risk_review_ids"]
            assert blocked_payload["active_reserve_ids"]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
