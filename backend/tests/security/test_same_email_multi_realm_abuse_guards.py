import uuid

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
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


@pytest.mark.security
@pytest.mark.integration
async def test_same_email_multi_realm_links_block_trial_and_referral_eligibility(
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
                secondary_admin_realm = AuthRealmModel(
                    id=uuid.uuid4(),
                    realm_key="secondary-admin",
                    realm_type="admin",
                    display_name="Secondary Admin Realm",
                    audience="cybervpn:secondary-admin",
                    cookie_namespace="secondary-admin",
                    status="active",
                    is_default=False,
                )
                db.add(secondary_admin_realm)

                caller = AdminUserModel(
                    login="eligibility_operator",
                    email="eligibility-operator@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("EligibilityOperatorP@ssword123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                shared_email = "eligibility-shared@example.com"
                left_principal = AdminUserModel(
                    login="eligibility_left",
                    email=shared_email,
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("EligibilityLeftP@ssword123!"),
                    role="viewer",
                    is_active=True,
                    is_email_verified=True,
                )
                right_principal = AdminUserModel(
                    login="eligibility_right",
                    email=shared_email,
                    auth_realm_id=secondary_admin_realm.id,
                    password_hash=await auth_service.hash_password("EligibilityRightP@ssword123!"),
                    role="viewer",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add_all([caller, left_principal, right_principal])
                db.commit()

                admin_token = _make_access_token(
                    auth_service,
                    user_id=caller.id,
                    role="admin",
                    realm=admin_realm,
                    principal_type="admin",
                )

            left_subject = (
                await async_client.post(
                    "/api/v1/security/risk-subjects",
                    headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                    json={
                        "principal_class": "admin",
                        "principal_subject": str(left_principal.id),
                        "auth_realm_id": str(admin_realm.id),
                    },
                )
            ).json()
            right_subject = (
                await async_client.post(
                    "/api/v1/security/risk-subjects",
                    headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                    json={
                        "principal_class": "admin",
                        "principal_subject": str(right_principal.id),
                        "auth_realm_id": str(secondary_admin_realm.id),
                    },
                )
            ).json()

            await async_client.post(
                f"/api/v1/security/risk-subjects/{left_subject['id']}/identifiers",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "identifier_type": "email",
                    "value": shared_email,
                    "is_verified": True,
                    "source": "manual_review",
                },
            )
            await async_client.post(
                f"/api/v1/security/risk-subjects/{right_subject['id']}/identifiers",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "identifier_type": "email",
                    "value": shared_email,
                    "is_verified": True,
                    "source": "manual_review",
                },
            )

            trial_check = await async_client.post(
                "/api/v1/security/eligibility/checks",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "check_type": "trial_activation",
                    "risk_subject_id": left_subject["id"],
                },
            )
            assert trial_check.status_code == 200
            assert trial_check.json()["allowed"] is False
            assert "shared_email_link_detected" in trial_check.json()["reason_codes"]
            assert right_subject["id"] in trial_check.json()["linked_subject_ids"]

            referral_check = await async_client.post(
                "/api/v1/security/eligibility/checks",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "check_type": "referral_credit",
                    "risk_subject_id": left_subject["id"],
                    "counterparty_subject_id": right_subject["id"],
                },
            )
            assert referral_check.status_code == 200
            assert referral_check.json()["allowed"] is False
            assert "shared_email_link_detected" in referral_check.json()["reason_codes"]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)

