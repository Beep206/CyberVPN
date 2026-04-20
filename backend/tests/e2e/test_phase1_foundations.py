import uuid

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
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

pytestmark = [pytest.mark.e2e, pytest.mark.integration]


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
    session.flush()
    return user


async def _login(async_client: AsyncClient, login_or_email: str, password: str) -> str:
    response = await async_client.post(
        "/api/v1/auth/login",
        headers={"X-Auth-Realm": "admin"},
        json={"login_or_email": login_or_email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def _approve_policy(async_client: AsyncClient, admin_token: str, policy_id: str) -> None:
    response = await async_client.post(
        f"/api/v1/policies/{policy_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
        json={},
    )
    assert response.status_code == 200


async def _create_policy(
    async_client: AsyncClient,
    admin_token: str,
    payload: dict,
) -> dict:
    response = await async_client.post(
        "/api/v1/policies/",
        headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
        json=payload,
    )
    assert response.status_code == 201
    return response.json()


async def _create_risk_subject(
    async_client: AsyncClient,
    admin_token: str,
    *,
    principal_class: str,
    principal_subject: str,
    auth_realm_id: str,
) -> dict:
    response = await async_client.post(
        "/api/v1/security/risk-subjects",
        headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
        json={
            "principal_class": principal_class,
            "principal_subject": principal_subject,
            "auth_realm_id": auth_realm_id,
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_phase1_foundations_end_to_end(async_client: AsyncClient) -> None:
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
                official_customer_realm = await realm_repo.get_or_create_default_realm("customer")
                partner_customer_realm = AuthRealmModel(
                    id=uuid.uuid4(),
                    realm_key="partner-customer",
                    realm_type="customer",
                    display_name="Partner Customer Realm",
                    audience="cybervpn:partner-customer",
                    cookie_namespace="partner-customer",
                    status="active",
                    is_default=False,
                )
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
                db.add_all([partner_customer_realm, secondary_admin_realm])

                official_brand = BrandModel(brand_key="cybervpn", display_name="CyberVPN")
                partner_brand = BrandModel(brand_key="partner-brand", display_name="Partner Brand")
                db.add_all([official_brand, partner_brand])
                db.flush()

                official_storefront = StorefrontModel(
                    storefront_key="cybervpn-web",
                    brand_id=official_brand.id,
                    display_name="CyberVPN Official",
                    host="cybervpn.example.test",
                    auth_realm_id=official_customer_realm.id,
                    status="active",
                )
                partner_storefront = StorefrontModel(
                    storefront_key="partner-web",
                    brand_id=partner_brand.id,
                    display_name="Partner Web",
                    host="partner.example.test",
                    auth_realm_id=partner_customer_realm.id,
                    status="active",
                )
                db.add_all([official_storefront, partner_storefront])

                await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="phase1_admin",
                    email="phase1-admin@example.com",
                    password="Phase1AdminP@ssword123!",
                    role="admin",
                )
                owner_operator = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="phase1_owner",
                    email="phase1-owner@example.com",
                    password="Phase1OwnerP@ssword123!",
                    role="viewer",
                )
                analyst_operator = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="phase1_analyst",
                    email="phase1-analyst@example.com",
                    password="Phase1AnalystP@ssword123!",
                    role="viewer",
                )
                shadow_operator = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=secondary_admin_realm.id,
                    login="phase1_shadow",
                    email="phase1-shadow@example.com",
                    password="Phase1ShadowP@ssword123!",
                    role="viewer",
                )
                partner_customer = MobileUserModel(
                    email="partner-customer@example.com",
                    password_hash=await auth_service.hash_password("PartnerCustomerP@ssword123!"),
                    auth_realm_id=partner_customer_realm.id,
                    is_active=True,
                )
                db.add(partner_customer)
                db.commit()

            admin_token = await _login(async_client, "phase1-admin@example.com", "Phase1AdminP@ssword123!")
            admin_me = await async_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
            )
            assert admin_me.status_code == 200

            partner_realm_resolution = await async_client.get(
                "/api/v1/realms/resolve",
                headers={"Host": "partner.example.test"},
            )
            assert partner_realm_resolution.status_code == 200
            assert partner_realm_resolution.json()["source"] == "host"
            assert partner_realm_resolution.json()["realm"]["realm_key"] == "partner-customer"

            official_realm_resolution = await async_client.get(
                "/api/v1/realms/resolve",
                headers={"Host": "cybervpn.example.test"},
            )
            assert official_realm_resolution.status_code == 200
            assert official_realm_resolution.json()["source"] == "host"
            assert official_realm_resolution.json()["realm"]["realm_key"] == "customer"

            workspace_response = await async_client.post(
                "/api/v1/admin/partner-workspaces",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "display_name": "Phase 1 Launch Partners",
                    "owner_admin_user_id": str(owner_operator.id),
                },
            )
            assert workspace_response.status_code == 201
            workspace_payload = workspace_response.json()
            workspace_id = workspace_payload["id"]
            assert workspace_payload["members"][0]["admin_user_id"] == str(owner_operator.id)
            assert workspace_payload["members"][0]["role_key"] == "owner"

            owner_token = await _login(async_client, "phase1-owner@example.com", "Phase1OwnerP@ssword123!")
            add_member_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/members",
                headers={"Authorization": f"Bearer {owner_token}", "X-Auth-Realm": "admin"},
                json={
                    "admin_user_id": str(analyst_operator.id),
                    "role_key": "analyst",
                },
            )
            assert add_member_response.status_code == 201
            assert add_member_response.json()["role_key"] == "analyst"

            owner_workspace = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}",
                headers={"Authorization": f"Bearer {owner_token}", "X-Auth-Realm": "admin"},
            )
            assert owner_workspace.status_code == 200
            assert owner_workspace.json()["current_role_key"] == "owner"
            assert "membership_write" in owner_workspace.json()["current_permission_keys"]

            legal_policy = await _create_policy(
                async_client,
                admin_token,
                {
                    "policy_family": "legal_document",
                    "policy_key": "partner-tos-en",
                    "subject_type": "legal_document",
                    "subject_id": None,
                    "version_number": 1,
                    "payload": {"surface": "partner_storefront"},
                    "approval_state": "draft",
                    "version_status": "draft",
                },
            )
            await _approve_policy(async_client, admin_token, legal_policy["id"])

            legal_document_response = await async_client.post(
                "/api/v1/legal-documents/",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "document_key": "partner-tos",
                    "document_type": "terms_of_service",
                    "locale": "en-EN",
                    "title": "Partner Terms of Service",
                    "content_markdown": "# Partner Terms\nAccept the partner terms.",
                    "policy_version_id": legal_policy["id"],
                },
            )
            assert legal_document_response.status_code == 201
            legal_document_id = legal_document_response.json()["id"]

            legal_set_policy = await _create_policy(
                async_client,
                admin_token,
                {
                    "policy_family": "storefront_legal_doc_set",
                    "policy_key": "partner-web-legal-set",
                    "subject_type": "storefront",
                    "subject_id": str(partner_storefront.id),
                    "version_number": 1,
                    "payload": {"required_documents": ["partner-tos"]},
                    "approval_state": "draft",
                    "version_status": "draft",
                },
            )
            await _approve_policy(async_client, admin_token, legal_set_policy["id"])

            legal_set_response = await async_client.post(
                "/api/v1/legal-documents/sets",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "set_key": "partner-web-legal-set",
                    "storefront_id": str(partner_storefront.id),
                    "auth_realm_id": str(partner_customer_realm.id),
                    "display_name": "Partner Web Legal Set",
                    "policy_version_id": legal_set_policy["id"],
                    "documents": [{"legal_document_id": legal_document_id, "required": True, "display_order": 0}],
                },
            )
            assert legal_set_response.status_code == 201
            legal_set_id = legal_set_response.json()["id"]

            resolved_legal_set = await async_client.get(
                "/api/v1/legal-documents/sets/resolve",
                headers={"Host": "partner.example.test"},
                params={"storefront_key": "partner-web"},
            )
            assert resolved_legal_set.status_code == 200
            assert resolved_legal_set.json()["id"] == legal_set_id
            assert resolved_legal_set.json()["auth_realm_id"] == str(partner_customer_realm.id)

            customer_token = _make_access_token(
                auth_service,
                user_id=partner_customer.id,
                role="user",
                realm=partner_customer_realm,
                principal_type="customer",
                scope_family="customer",
            )
            acceptance_response = await async_client.post(
                "/api/v1/policy-acceptance/",
                headers={"Authorization": f"Bearer {customer_token}", "X-Auth-Realm": "partner-customer"},
                json={
                    "legal_document_set_id": legal_set_id,
                    "storefront_id": str(partner_storefront.id),
                    "acceptance_channel": "partner_storefront_checkout",
                    "device_context": {"device_class": "browser"},
                },
            )
            assert acceptance_response.status_code == 201
            acceptance_payload = acceptance_response.json()
            assert acceptance_payload["storefront_id"] == str(partner_storefront.id)
            assert acceptance_payload["auth_realm_id"] == str(partner_customer_realm.id)
            assert acceptance_payload["actor_principal_id"] == str(partner_customer.id)
            assert acceptance_payload["actor_principal_type"] == "customer"

            owner_subject = await _create_risk_subject(
                async_client,
                admin_token,
                principal_class="admin",
                principal_subject=str(owner_operator.id),
                auth_realm_id=str(admin_realm.id),
            )
            shadow_subject = await _create_risk_subject(
                async_client,
                admin_token,
                principal_class="admin",
                principal_subject=str(shadow_operator.id),
                auth_realm_id=str(secondary_admin_realm.id),
            )

            attach_owner_identifier = await async_client.post(
                f"/api/v1/security/risk-subjects/{owner_subject['id']}/identifiers",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "identifier_type": "email",
                    "value": "shared-phase1@example.com",
                    "is_verified": True,
                    "source": "phase1_gate",
                },
            )
            assert attach_owner_identifier.status_code == 201

            attach_shadow_identifier = await async_client.post(
                f"/api/v1/security/risk-subjects/{shadow_subject['id']}/identifiers",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "identifier_type": "email",
                    "value": "shared-phase1@example.com",
                    "is_verified": True,
                    "source": "phase1_gate",
                },
            )
            assert attach_shadow_identifier.status_code == 201
            links_created = attach_shadow_identifier.json()["links_created"]
            assert len(links_created) == 1
            assert {
                links_created[0]["left_subject_id"],
                links_created[0]["right_subject_id"],
            } == {owner_subject["id"], shadow_subject["id"]}

            eligibility_response = await async_client.post(
                "/api/v1/security/eligibility/checks",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "check_type": "trial_activation",
                    "risk_subject_id": owner_subject["id"],
                },
            )
            assert eligibility_response.status_code == 200
            assert eligibility_response.json()["allowed"] is False
            assert "shared_email_link_detected" in eligibility_response.json()["reason_codes"]
            assert shadow_subject["id"] in eligibility_response.json()["linked_subject_ids"]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
