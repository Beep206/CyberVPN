from uuid import UUID

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.brand_model import BrandModel
from src.infrastructure.database.models.storefront_model import StorefrontModel
from src.main import app
from tests.helpers.realm_auth import (
    FakeRedis,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)


async def _create_admin_user(
    *,
    session,
    auth_service: AuthService,
    auth_realm_id,
    login: str,
    email: str,
    password: str,
) -> AdminUserModel:
    user = AdminUserModel(
        login=login,
        email=email,
        auth_realm_id=auth_realm_id,
        password_hash=await auth_service.hash_password(password),
        role="admin",
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


@pytest.mark.integration
async def test_merchant_invoice_and_billing_descriptor_foundations_resolve_from_storefront(
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
                admin_realm = AuthRealmModel(
                    realm_key="admin",
                    realm_type="admin",
                    display_name="Admin",
                    audience="cybervpn-admin",
                    cookie_namespace="cybervpn_admin",
                    status="active",
                    is_default=True,
                )
                customer_realm = AuthRealmModel(
                    realm_key="customer",
                    realm_type="customer",
                    display_name="Customer",
                    audience="cybervpn-customer",
                    cookie_namespace="cybervpn_customer",
                    status="active",
                    is_default=True,
                )
                brand = BrandModel(brand_key="cybervpn", display_name="CyberVPN")
                db.add_all([admin_realm, customer_realm, brand])
                db.flush()

                storefront = StorefrontModel(
                    storefront_key="partner-web",
                    brand_id=brand.id,
                    display_name="Partner Web",
                    host="partner.example.test",
                    auth_realm_id=customer_realm.id,
                    status="active",
                )
                db.add(storefront)
                await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="merchant_admin",
                    email="merchant-admin@example.com",
                    password="MerchantAdminP@ssword123!",
                )
                db.commit()

            admin_token = await _login(async_client, "merchant-admin@example.com", "MerchantAdminP@ssword123!")

            invoice_profile_response = await async_client.post(
                "/api/v1/invoice-profiles/",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "profile_key": "cybervpn-eu",
                    "display_name": "CyberVPN EU",
                    "issuer_legal_name": "CyberVPN EU GmbH",
                    "tax_identifier": "DE123456789",
                    "issuer_email": "billing@cybervpn.test",
                    "tax_behavior": {"pricing_mode": "tax_inclusive", "audience": "consumer"},
                    "invoice_footer": "VAT applied where required",
                    "receipt_footer": "Thank you",
                },
            )
            assert invoice_profile_response.status_code == 201
            invoice_profile_id = invoice_profile_response.json()["id"]

            merchant_response = await async_client.post(
                "/api/v1/merchant-profiles/",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "profile_key": "cybervpn-mor",
                    "legal_entity_name": "CyberVPN LLC",
                    "billing_descriptor": "CYBERVPN",
                    "invoice_profile_id": invoice_profile_id,
                    "settlement_reference": "stripe-main",
                    "supported_currencies": ["usd", "eur"],
                    "tax_behavior": {"pricing_mode": "tax_inclusive", "country": "DE"},
                    "refund_responsibility_model": "merchant_of_record",
                    "chargeback_liability_model": "merchant_of_record",
                },
            )
            assert merchant_response.status_code == 201
            merchant_payload = merchant_response.json()
            merchant_profile_id = merchant_payload["id"]
            assert merchant_payload["invoice_profile_id"] == invoice_profile_id
            assert merchant_payload["supported_currencies"] == ["EUR", "USD"]

            billing_descriptor_response = await async_client.post(
                "/api/v1/billing-descriptors/",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
                json={
                    "descriptor_key": "cybervpn-default",
                    "merchant_profile_id": merchant_profile_id,
                    "invoice_profile_id": invoice_profile_id,
                    "statement_descriptor": "CYBERVPN EU",
                    "soft_descriptor": "CYBERVPN*EU",
                    "support_phone": "+49-555-0101",
                    "support_url": "https://support.cybervpn.test",
                    "is_default": True,
                },
            )
            assert billing_descriptor_response.status_code == 201
            assert billing_descriptor_response.json()["is_default"] is True

            with sessionmaker() as db:
                storefront = db.query(StorefrontModel).filter(StorefrontModel.storefront_key == "partner-web").one()
                storefront.merchant_profile_id = UUID(merchant_payload["id"])
                db.add(storefront)
                db.commit()

            resolved_merchant = await async_client.get(
                "/api/v1/merchant-profiles/resolve",
                params={"storefront_key": "partner-web"},
            )
            assert resolved_merchant.status_code == 200
            assert resolved_merchant.json()["profile_key"] == "cybervpn-mor"

            resolved_descriptor = await async_client.get(
                "/api/v1/billing-descriptors/resolve",
                params={
                    "merchant_profile_id": merchant_profile_id,
                    "invoice_profile_id": invoice_profile_id,
                },
            )
            assert resolved_descriptor.status_code == 200
            assert resolved_descriptor.json()["statement_descriptor"] == "CYBERVPN EU"

            listed_merchants = await async_client.get(
                "/api/v1/merchant-profiles/",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
            )
            assert listed_merchants.status_code == 200
            assert len(listed_merchants.json()) == 1

            listed_invoices = await async_client.get(
                "/api/v1/invoice-profiles/",
                headers={"Authorization": f"Bearer {admin_token}", "X-Auth-Realm": "admin"},
            )
            assert listed_invoices.status_code == 200
            assert len(listed_invoices.json()) == 1
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
