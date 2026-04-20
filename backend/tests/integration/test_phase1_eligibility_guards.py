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
async def test_phase1_partner_payout_eligibility_respects_open_hold_reviews(
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

                caller = AdminUserModel(
                    login="payout_operator",
                    email="payout-operator@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("PayoutOperatorP@ssword123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                clean_principal = AdminUserModel(
                    login="payout_clean",
                    email="payout-clean@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("PayoutCleanP@ssword123!"),
                    role="viewer",
                    is_active=True,
                    is_email_verified=True,
                )
                blocked_principal = AdminUserModel(
                    login="payout_blocked",
                    email="payout-blocked@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("PayoutBlockedP@ssword123!"),
                    role="viewer",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add_all([caller, clean_principal, blocked_principal])
                db.commit()

                admin_token = _make_access_token(
                    auth_service,
                    user_id=caller.id,
                    role="admin",
                    realm=admin_realm,
                    principal_type="admin",
                )

            clean_subject = (
                await async_client.post(
                    "/api/v1/security/risk-subjects",
                    headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                    json={
                        "principal_class": "admin",
                        "principal_subject": str(clean_principal.id),
                        "auth_realm_id": str(admin_realm.id),
                    },
                )
            ).json()
            blocked_subject = (
                await async_client.post(
                    "/api/v1/security/risk-subjects",
                    headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                    json={
                        "principal_class": "admin",
                        "principal_subject": str(blocked_principal.id),
                        "auth_realm_id": str(admin_realm.id),
                    },
                )
            ).json()

            hold_review = await async_client.post(
                "/api/v1/security/risk-reviews",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "risk_subject_id": blocked_subject["id"],
                    "review_type": "payout_review",
                    "decision": "hold",
                    "reason": "Manual finance hold for payout verification",
                    "evidence": {"source": "phase1_test"},
                },
            )
            assert hold_review.status_code == 201

            clean_check = await async_client.post(
                "/api/v1/security/eligibility/checks",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "check_type": "partner_payout",
                    "risk_subject_id": clean_subject["id"],
                },
            )
            assert clean_check.status_code == 200
            assert clean_check.json()["allowed"] is True
            assert clean_check.json()["reason_codes"] == []

            blocked_check = await async_client.post(
                "/api/v1/security/eligibility/checks",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "check_type": "partner_payout",
                    "risk_subject_id": blocked_subject["id"],
                },
            )
            assert blocked_check.status_code == 200
            assert blocked_check.json()["allowed"] is False
            assert "risk_review_hold" in blocked_check.json()["reason_codes"]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)

