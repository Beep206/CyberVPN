from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.main import app
from src.presentation.dependencies.services import get_crypto_client
from tests.helpers.realm_auth import (
    FakeRedis,
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)
from tests.integration.test_order_commit import _make_customer_access_token, _seed_order_context

pytestmark = [pytest.mark.integration]


class FakeCryptoBotClient:
    def __init__(self) -> None:
        self._counter = 4000

    async def create_invoice(self, amount: str, currency: str, description: str, payload: str | None = None) -> dict:
        _ = amount, currency, description, payload
        self._counter += 1
        invoice_id = str(self._counter)
        return {
            "invoice_id": invoice_id,
            "pay_url": f"https://pay.example.test/{invoice_id}",
            "status": "pending",
            "expiration_date": "2030-01-01T00:00:00+00:00",
        }


def _make_admin_token(auth_service: AuthService, *, user_id, realm) -> str:
    token, _, _ = auth_service.create_access_token(
        str(user_id),
        "admin",
        audience=realm.audience,
        principal_type="admin",
        realm_id=str(realm.id),
        realm_key=realm.realm_key,
        scope_family="admin",
    )
    return token


async def _create_quote_checkout(
    *,
    async_client: AsyncClient,
    headers: dict[str, str],
    storefront_key: str,
    pricebook_key: str,
    offer_key: str,
    plan_id: str,
    partner_code: str | None = None,
    idempotency_key: str = "attribution-checkout",
) -> tuple[dict, dict]:
    quote_response = await async_client.post(
        "/api/v1/quotes/",
        headers=headers,
        json={
            "storefront_key": storefront_key,
            "pricebook_key": pricebook_key,
            "offer_key": offer_key,
            "plan_id": plan_id,
            "currency": "USD",
            "channel": "web",
            "partner_code": partner_code,
            "use_wallet": 0,
            "addons": [],
        },
    )
    assert quote_response.status_code == 201
    quote_payload = quote_response.json()

    checkout_response = await async_client.post(
        "/api/v1/checkout-sessions/",
        headers={**headers, "Idempotency-Key": idempotency_key},
        json={"quote_session_id": quote_payload["id"]},
    )
    assert checkout_response.status_code == 201
    checkout_payload = checkout_response.json()
    return quote_payload, checkout_payload


@pytest.mark.asyncio
async def test_order_attribution_prefers_explicit_code_over_passive_click_and_binding(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    fake_crypto = FakeCryptoBotClient()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    async def _override_crypto():
        return fake_crypto

    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_crypto_client] = _override_crypto

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_order_context(sessionmaker, auth_service)
            customer_realm = AuthRealmModel(
                id=uuid.UUID(seeded["customer_realm_id"]),
                realm_key=seeded["customer_realm_key"],
                realm_type="customer",
                display_name="Customer Realm",
                audience=seeded["customer_realm_audience"],
                cookie_namespace="customer",
                status="active",
                is_default=True,
            )

            with sessionmaker() as db:
                realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
                admin_realm = await realm_repo.get_or_create_default_realm("admin")

                partner_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="owner-attribution@example.test",
                    password_hash=await auth_service.hash_password("OwnerAttribution123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                reseller_workspace = PartnerAccountModel(
                    id=uuid.uuid4(),
                    account_key="reseller-attribution",
                    display_name="Reseller Attribution",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                reseller_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="RESELLER88",
                    partner_account_id=reseller_workspace.id,
                    partner_user_id=partner_owner.id,
                    markup_pct=18,
                    is_active=True,
                )
                affiliate_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="AFFILIATE12",
                    partner_user_id=partner_owner.id,
                    markup_pct=12,
                    is_active=True,
                )
                passive_click_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="CLICK09",
                    partner_user_id=partner_owner.id,
                    markup_pct=9,
                    is_active=True,
                )
                admin_user = AdminUserModel(
                    login="order_attr_admin",
                    email="order-attr-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("OrderAttrAdmin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                support_user = AdminUserModel(
                    login="order_attr_support",
                    email="order-attr-support@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("OrderAttrSupport123!"),
                    role="support",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add_all(
                    [
                        partner_owner,
                        reseller_workspace,
                        reseller_code,
                        affiliate_code,
                        passive_click_code,
                        admin_user,
                        support_user,
                    ]
                )
                db.commit()
                admin_token = _make_admin_token(auth_service, user_id=admin_user.id, realm=admin_realm)
                support_token = _make_admin_token(auth_service, user_id=support_user.id, realm=admin_realm)

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            customer_headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }
            admin_headers = {
                "Authorization": f"Bearer {admin_token}",
                "X-Auth-Realm": "admin",
            }
            support_headers = {
                "Authorization": f"Bearer {support_token}",
                "X-Auth-Realm": "admin",
            }

            bind_response = await async_client.post(
                "/api/v1/partner/bind",
                headers=customer_headers,
                json={"partner_code": reseller_code.code},
            )
            assert bind_response.status_code == 200

            quote_payload, checkout_payload = await _create_quote_checkout(
                async_client=async_client,
                headers=customer_headers,
                storefront_key=seeded["storefront_key"],
                pricebook_key=seeded["pricebook_key"],
                offer_key=seeded["offer_key"],
                plan_id=seeded["plan_id"],
                partner_code=affiliate_code.code,
                idempotency_key="attribution-explicit-checkout",
            )

            manual_touchpoint = await async_client.post(
                "/api/v1/attribution/touchpoints",
                headers=admin_headers,
                json={
                    "touchpoint_type": "passive_click",
                    "auth_realm_key": seeded["customer_realm_key"],
                    "quote_session_id": quote_payload["id"],
                    "partner_code": passive_click_code.code,
                    "sale_channel": "web",
                    "source_host": "partner.example.test",
                    "source_path": "/reviews/best-vpn",
                    "evidence_payload": {"click_id": "click-explicit-1"},
                },
            )
            assert manual_touchpoint.status_code == 201

            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=customer_headers,
                json={"checkout_session_id": checkout_payload["id"]},
            )
            assert order_response.status_code == 201
            order_payload = order_response.json()

            result_response = await async_client.get(
                f"/api/v1/attribution/orders/{order_payload['id']}/result",
                headers=support_headers,
            )
            assert result_response.status_code == 200
            result_payload = result_response.json()
            assert result_payload["owner_type"] == "affiliate"
            assert result_payload["owner_source"] == "explicit_code"
            assert result_payload["partner_code_id"] == str(affiliate_code.id)
            assert result_payload["winning_binding_id"] is None
            assert "explicit_code_touchpoint_selected" in result_payload["rule_path"]

            quote_touchpoints = await async_client.get(
                f"/api/v1/attribution/touchpoints?quote_session_id={quote_payload['id']}",
                headers=support_headers,
            )
            assert quote_touchpoints.status_code == 200
            explicit_touchpoint_id = next(
                item["id"] for item in quote_touchpoints.json() if item["touchpoint_type"] == "explicit_code"
            )
            assert result_payload["winning_touchpoint_id"] == explicit_touchpoint_id

            resolve_again = await async_client.post(
                f"/api/v1/attribution/orders/{order_payload['id']}/resolve",
                headers=admin_headers,
            )
            assert resolve_again.status_code == 200
            assert resolve_again.json()["id"] == result_payload["id"]

    finally:
        app.dependency_overrides.pop(get_redis, None)
        app.dependency_overrides.pop(get_crypto_client, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_order_attribution_prefers_reseller_binding_over_passive_click(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    fake_crypto = FakeCryptoBotClient()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    async def _override_crypto():
        return fake_crypto

    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_crypto_client] = _override_crypto

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_order_context(sessionmaker, auth_service)
            customer_realm = AuthRealmModel(
                id=uuid.UUID(seeded["customer_realm_id"]),
                realm_key=seeded["customer_realm_key"],
                realm_type="customer",
                display_name="Customer Realm",
                audience=seeded["customer_realm_audience"],
                cookie_namespace="customer",
                status="active",
                is_default=True,
            )

            with sessionmaker() as db:
                realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
                admin_realm = await realm_repo.get_or_create_default_realm("admin")

                partner_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="binding-owner@example.test",
                    password_hash=await auth_service.hash_password("BindingOwner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                reseller_workspace = PartnerAccountModel(
                    id=uuid.uuid4(),
                    account_key="binding-reseller",
                    display_name="Binding Reseller",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                reseller_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="RESELLER55",
                    partner_account_id=reseller_workspace.id,
                    partner_user_id=partner_owner.id,
                    markup_pct=15,
                    is_active=True,
                )
                passive_click_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="CLICK07",
                    partner_user_id=partner_owner.id,
                    markup_pct=7,
                    is_active=True,
                )
                admin_user = AdminUserModel(
                    login="binding_attr_admin",
                    email="binding-attr-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("BindingAttrAdmin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                support_user = AdminUserModel(
                    login="binding_attr_support",
                    email="binding-attr-support@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("BindingAttrSupport123!"),
                    role="support",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add_all(
                    [
                        partner_owner,
                        reseller_workspace,
                        reseller_code,
                        passive_click_code,
                        admin_user,
                        support_user,
                    ]
                )
                db.commit()
                admin_token = _make_admin_token(auth_service, user_id=admin_user.id, realm=admin_realm)
                support_token = _make_admin_token(auth_service, user_id=support_user.id, realm=admin_realm)

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            customer_headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }
            admin_headers = {
                "Authorization": f"Bearer {admin_token}",
                "X-Auth-Realm": "admin",
            }
            support_headers = {
                "Authorization": f"Bearer {support_token}",
                "X-Auth-Realm": "admin",
            }

            bind_response = await async_client.post(
                "/api/v1/partner/bind",
                headers=customer_headers,
                json={"partner_code": reseller_code.code},
            )
            assert bind_response.status_code == 200

            quote_payload, checkout_payload = await _create_quote_checkout(
                async_client=async_client,
                headers=customer_headers,
                storefront_key=seeded["storefront_key"],
                pricebook_key=seeded["pricebook_key"],
                offer_key=seeded["offer_key"],
                plan_id=seeded["plan_id"],
                partner_code=None,
                idempotency_key="attribution-binding-checkout",
            )

            manual_touchpoint = await async_client.post(
                "/api/v1/attribution/touchpoints",
                headers=admin_headers,
                json={
                    "touchpoint_type": "passive_click",
                    "auth_realm_key": seeded["customer_realm_key"],
                    "quote_session_id": quote_payload["id"],
                    "partner_code": passive_click_code.code,
                    "sale_channel": "web",
                    "source_host": "partner.example.test",
                    "source_path": "/ads/telegram",
                    "evidence_payload": {"click_id": "click-binding-1"},
                },
            )
            assert manual_touchpoint.status_code == 201

            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=customer_headers,
                json={"checkout_session_id": checkout_payload["id"]},
            )
            assert order_response.status_code == 201
            order_payload = order_response.json()

            result_response = await async_client.get(
                f"/api/v1/attribution/orders/{order_payload['id']}/result",
                headers=support_headers,
            )
            assert result_response.status_code == 200
            result_payload = result_response.json()
            assert result_payload["owner_type"] == "reseller"
            assert result_payload["owner_source"] == "persistent_reseller_binding"
            assert result_payload["partner_code_id"] == str(reseller_code.id)
            assert result_payload["partner_account_id"] == str(reseller_workspace.id)
            assert result_payload["winning_touchpoint_id"] is None
            assert result_payload["winning_binding_id"] is not None
            assert "persistent_reseller_binding_selected" in result_payload["rule_path"]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        app.dependency_overrides.pop(get_crypto_client, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
