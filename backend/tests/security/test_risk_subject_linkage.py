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
async def test_risk_subjects_can_link_across_realms_without_collapsing_identity(
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

                caller = AdminUserModel(
                    login="risk_operator",
                    email="risk-operator@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("RiskOperatorP@ssword123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                shared_email = "shared-risk@example.com"
                left_principal = AdminUserModel(
                    login="risk_left",
                    email=shared_email,
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("RiskLeftP@ssword123!"),
                    role="viewer",
                    is_active=True,
                    is_email_verified=True,
                )
                right_principal = AdminUserModel(
                    login="risk_right",
                    email=shared_email,
                    auth_realm_id=partner_admin_realm.id,
                    password_hash=await auth_service.hash_password("RiskRightP@ssword123!"),
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

            left_subject_response = await async_client.post(
                "/api/v1/security/risk-subjects",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "principal_class": "admin",
                    "principal_subject": str(left_principal.id),
                    "auth_realm_id": str(admin_realm.id),
                },
            )
            assert left_subject_response.status_code == 201
            left_subject = left_subject_response.json()

            right_subject_response = await async_client.post(
                "/api/v1/security/risk-subjects",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "principal_class": "admin",
                    "principal_subject": str(right_principal.id),
                    "auth_realm_id": str(partner_admin_realm.id),
                },
            )
            assert right_subject_response.status_code == 201
            right_subject = right_subject_response.json()

            first_identifier = await async_client.post(
                f"/api/v1/security/risk-subjects/{left_subject['id']}/identifiers",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "identifier_type": "email",
                    "value": shared_email,
                    "is_verified": True,
                    "source": "manual_review",
                },
            )
            assert first_identifier.status_code == 201
            assert first_identifier.json()["links_created"] == []

            second_identifier = await async_client.post(
                f"/api/v1/security/risk-subjects/{right_subject['id']}/identifiers",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "identifier_type": "email",
                    "value": shared_email,
                    "is_verified": True,
                    "source": "manual_review",
                },
            )
            assert second_identifier.status_code == 201
            assert len(second_identifier.json()["links_created"]) == 1

            links_response = await async_client.get(
                f"/api/v1/security/risk-subjects/{right_subject['id']}/links",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
            )
            assert links_response.status_code == 200
            links_payload = links_response.json()
            assert len(links_payload) == 1
            assert links_payload[0]["identifier_type"] == "email"
            assert {links_payload[0]["left_subject_id"], links_payload[0]["right_subject_id"]} == {
                left_subject["id"],
                right_subject["id"],
            }
            assert left_subject["auth_realm_id"] != right_subject["auth_realm_id"]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)

