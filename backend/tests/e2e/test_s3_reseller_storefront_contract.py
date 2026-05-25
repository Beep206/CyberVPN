from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.config.settings import settings
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.attribution_touchpoint_model import AttributionTouchpointModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeModel
from src.main import app
from tests.helpers.realm_auth import (
    FakeRedis,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)
from tests.integration.test_order_commit import _make_customer_access_token, _seed_order_context

pytestmark = [pytest.mark.e2e]


@pytest.mark.asyncio
async def test_s3_reseller_storefront_preview_is_gated_readonly_and_does_not_change_checkout(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
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
                partner_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="s3-stage09-owner@example.test",
                    password_hash=await auth_service.hash_password("S3Stage09Owner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                reseller_workspace = PartnerAccountModel(
                    id=uuid.uuid4(),
                    account_key="s3-stage09-reseller",
                    display_name="S3 Stage09 Reseller",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                reseller_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="S3STORE09",
                    partner_account_id=reseller_workspace.id,
                    partner_user_id=partner_owner.id,
                    markup_pct=8,
                    is_active=True,
                )
                db.add_all([partner_owner, reseller_workspace, reseller_code])
                db.commit()

            hidden_response = await async_client.get(f"/api/v1/storefronts/{seeded['storefront_key']}/preview")
            assert hidden_response.status_code == 404
            assert hidden_response.headers["x-cybervpn-partner-boundary"] == "partner_storefronts_disabled"

            monkeypatch.setattr(settings, "partner_storefronts_enabled", True)
            with sessionmaker() as db:
                touchpoints_before_preview = db.query(AttributionTouchpointModel).count()

            preview_response = await async_client.get(
                f"/api/v1/storefronts/{seeded['storefront_key']}/preview",
                params={"partner_code": reseller_code.code},
            )
            assert preview_response.status_code == 200
            preview_payload = preview_response.json()
            assert preview_payload["storefront_key"] == seeded["storefront_key"]
            assert preview_payload["route_contract"]["route_status"] == "preview"
            assert preview_payload["route_contract"]["checkout_side_effects"] is False
            assert preview_payload["route_contract"]["public_launch_requires_stages"] == [
                "S3-STAGE-15",
                "S3-STAGE-16",
                "S3-STAGE-17",
            ]
            assert preview_payload["branding_boundary"]["legal_copy_source"] == "CyberVPN approved legal pack"
            assert "custom_legal_promises" in preview_payload["branding_boundary"]["prohibited_claims"]
            assert preview_payload["pricing_boundary"]["display_policy"].startswith("show native storefront price")
            assert preview_payload["pricing_boundary"]["offers"]
            assert preview_payload["attribution_contract"]["owner_type"] == "reseller"
            assert preview_payload["attribution_contract"]["owner_source"] == "explicit_code"
            assert preview_payload["attribution_contract"]["partner_account_id"] == str(reseller_workspace.id)
            assert preview_payload["attribution_contract"]["partner_code_id"] == str(reseller_code.id)
            assert preview_payload["analytics_contract"]["preview_records_touchpoint"] is False

            with sessionmaker() as db:
                touchpoints_after_preview = db.query(AttributionTouchpointModel).count()
            assert touchpoints_after_preview == touchpoints_before_preview

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            quote_response = await async_client.post(
                "/api/v1/quotes/",
                headers={
                    "Authorization": f"Bearer {customer_token}",
                    "X-Auth-Realm": "customer",
                },
                json={
                    "storefront_key": seeded["storefront_key"],
                    "pricebook_key": seeded["pricebook_key"],
                    "offer_key": seeded["offer_key"],
                    "plan_id": seeded["plan_id"],
                    "currency": "USD",
                    "channel": "web",
                    "use_wallet": 0,
                    "addons": [],
                },
            )
            assert quote_response.status_code == 201
            quote_payload = quote_response.json()
            assert quote_payload["quote"]["partner_code_id"] is None
            assert quote_payload["quote"]["code_resolution"] is None
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
