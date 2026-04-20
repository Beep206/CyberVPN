import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.brand_model import BrandModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.storefront_model import StorefrontModel
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


def _make_access_token(
    auth_service: AuthService,
    *,
    user_id,
    role: str,
    realm,
    principal_type: str,
    scope_family: str,
) -> str:
    token, _, _ = auth_service.create_access_token(
        str(user_id),
        role,
        audience=realm.audience,
        principal_type=principal_type,
        realm_id=str(realm.id),
        realm_key=realm.realm_key,
        scope_family=scope_family,
    )
    return token


@pytest.mark.integration
async def test_legal_document_set_acceptance_captures_realm_storefront_and_principal_context(
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
                customer_realm = await realm_repo.get_or_create_default_realm("customer")

                brand = BrandModel(brand_key="cybervpn", display_name="CyberVPN")
                db.add(brand)
                db.flush()

                storefront = StorefrontModel(
                    storefront_key="cybervpn-web",
                    brand_id=brand.id,
                    display_name="CyberVPN Official",
                    host="cybervpn.test",
                    auth_realm_id=customer_realm.id,
                    status="active",
                )
                db.add(storefront)

                admin_user = AdminUserModel(
                    login="policy_admin",
                    email="policy-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("PolicyAdminP@ssword123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                customer_user = MobileUserModel(
                    email="customer@example.com",
                    password_hash=await auth_service.hash_password("CustomerP@ssword123!"),
                    auth_realm_id=customer_realm.id,
                    is_active=True,
                )
                db.add_all([admin_user, customer_user])
                db.commit()

                admin_token = _make_access_token(
                    auth_service,
                    user_id=admin_user.id,
                    role="admin",
                    realm=admin_realm,
                    principal_type="admin",
                    scope_family="admin",
                )
                customer_token = _make_access_token(
                    auth_service,
                    user_id=customer_user.id,
                    role="user",
                    realm=customer_realm,
                    principal_type="customer",
                    scope_family="customer",
                )

            policy_response = await async_client.post(
                "/api/v1/policies/",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "policy_family": "legal_document",
                    "policy_key": "terms-of-service-en",
                    "subject_type": "legal_document",
                    "subject_id": None,
                    "version_number": 1,
                    "payload": {"surface": "official_web"},
                    "approval_state": "draft",
                    "version_status": "draft",
                },
            )
            assert policy_response.status_code == 201
            policy_id = policy_response.json()["id"]

            approve_policy = await async_client.post(
                f"/api/v1/policies/{policy_id}/approve",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={},
            )
            assert approve_policy.status_code == 200
            assert approve_policy.json()["approved_by_admin_user_id"] is not None

            legal_document_response = await async_client.post(
                "/api/v1/legal-documents/",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "document_key": "tos",
                    "document_type": "terms_of_service",
                    "locale": "en-EN",
                    "title": "Terms of Service",
                    "content_markdown": "# Terms\nAccept the terms.",
                    "policy_version_id": policy_id,
                },
            )
            assert legal_document_response.status_code == 201
            legal_document_id = legal_document_response.json()["id"]

            set_policy_response = await async_client.post(
                "/api/v1/policies/",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "policy_family": "storefront_legal_doc_set",
                    "policy_key": "cybervpn-web-legal-set",
                    "subject_type": "storefront",
                    "subject_id": str(storefront.id),
                    "version_number": 1,
                    "payload": {"required_documents": ["tos"]},
                    "approval_state": "draft",
                    "version_status": "draft",
                },
            )
            assert set_policy_response.status_code == 201
            set_policy_id = set_policy_response.json()["id"]

            approve_set_policy = await async_client.post(
                f"/api/v1/policies/{set_policy_id}/approve",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={},
            )
            assert approve_set_policy.status_code == 200

            legal_set_response = await async_client.post(
                "/api/v1/legal-documents/sets",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "set_key": "cybervpn-web-legal-set",
                    "storefront_id": str(storefront.id),
                    "auth_realm_id": str(customer_realm.id),
                    "display_name": "CyberVPN Web Legal Set",
                    "policy_version_id": set_policy_id,
                    "documents": [{"legal_document_id": legal_document_id, "required": True, "display_order": 0}],
                },
            )
            assert legal_set_response.status_code == 201
            legal_set_id = legal_set_response.json()["id"]

            resolve_response = await async_client.get(
                "/api/v1/legal-documents/sets/resolve",
                headers={"X-Auth-Realm": "customer"},
                params={"storefront_key": "cybervpn-web"},
            )
            assert resolve_response.status_code == 200
            assert resolve_response.json()["id"] == legal_set_id

            acceptance_response = await async_client.post(
                "/api/v1/policy-acceptance/",
                headers={"Authorization": f"Bearer {customer_token}", "X-Auth-Realm": "customer"},
                json={
                    "legal_document_set_id": legal_set_id,
                    "storefront_id": str(storefront.id),
                    "acceptance_channel": "web_checkout",
                    "device_context": {"device_class": "browser"},
                },
            )
            assert acceptance_response.status_code == 201
            acceptance_payload = acceptance_response.json()
            assert acceptance_payload["legal_document_set_id"] == legal_set_id
            assert acceptance_payload["storefront_id"] == str(storefront.id)
            assert acceptance_payload["auth_realm_id"] == str(customer_realm.id)
            assert acceptance_payload["actor_principal_id"] == str(customer_user.id)
            assert acceptance_payload["actor_principal_type"] == "customer"
            assert acceptance_payload["accepted_at"] is not None

            my_acceptances = await async_client.get(
                "/api/v1/policy-acceptance/me",
                headers={"Authorization": f"Bearer {customer_token}", "X-Auth-Realm": "customer"},
            )
            assert my_acceptances.status_code == 200
            assert len(my_acceptances.json()) == 1
            assert my_acceptances.json()[0]["id"] == acceptance_payload["id"]

            admin_acceptances = await async_client.get(
                "/api/v1/policy-acceptance/",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                params={"storefront_id": str(storefront.id)},
            )
            assert admin_acceptances.status_code == 200
            admin_acceptance_payload = admin_acceptances.json()
            assert len(admin_acceptance_payload) == 1
            assert admin_acceptance_payload[0]["id"] == acceptance_payload["id"]

            admin_acceptance_detail = await async_client.get(
                f"/api/v1/policy-acceptance/{acceptance_payload['id']}",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
            )
            assert admin_acceptance_detail.status_code == 200
            assert admin_acceptance_detail.json()["actor_principal_id"] == str(customer_user.id)
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
