from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.config.settings import settings
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.remnawave.client import get_remnawave_client as get_infrastructure_remnawave_client
from src.infrastructure.remnawave.contracts import RemnawaveSubscriptionDetailsResponse, RemnawaveUserResponse
from src.main import app
from src.presentation.dependencies.remnawave import get_remnawave_client
from tests.fixtures.safe_client import (
    assert_safe_payload_is_synthetic,
    make_safe_customer_headers,
    seed_safe_client_fixture_pack,
)
from tests.helpers.realm_auth import (
    FakeRedis,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)

pytestmark = [pytest.mark.integration]


class _SafeClientRemnawave:
    def __init__(self, *, subscription_url: str) -> None:
        self.subscription_url = subscription_url

    async def get_validated(self, path, schema):
        now = datetime.now(UTC)
        if path.startswith("/api/users/") and schema is RemnawaveUserResponse:
            user_uuid = path.rsplit("/", 1)[-1]
            return RemnawaveUserResponse(
                uuid=user_uuid,
                username="safe-client-active",
                status="ACTIVE",
                shortUuid=user_uuid[:8],
                createdAt=now - timedelta(days=1),
                updatedAt=now,
                expireAt=now + timedelta(days=30),
                subscriptionUrl=self.subscription_url,
                trafficLimitBytes=30 * 1024 * 1024 * 1024,
                usedTrafficBytes=1024 * 1024 * 512,
                hwidDeviceLimit=5,
                onlineAt=now - timedelta(minutes=5),
                telegramId=990001,
            )
        if path.startswith("/subscriptions/by-uuid/") and schema is RemnawaveSubscriptionDetailsResponse:
            user_uuid = path.rsplit("/", 1)[-1]
            return RemnawaveSubscriptionDetailsResponse(
                isFound=True,
                user={
                    "shortUuid": user_uuid[:8],
                    "username": "safe-client-active",
                    "userStatus": "ACTIVE",
                },
                links=[self.subscription_url],
                subscriptionUrl=self.subscription_url,
            )
        msg = f"Unexpected Remnawave fixture call: {path}"
        raise AssertionError(msg)


@pytest.mark.asyncio
async def test_safe_client_fixture_pack_exercises_business_flows_without_secret_exposure(
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
    monkeypatch.setattr(settings, "referral_enabled", True)
    monkeypatch.setattr(settings, "checkout_code_discounts_enabled", True)
    monkeypatch.setattr(settings, "partner_codes_enabled", True)

    try:
        async with override_realm_test_db(sessionmaker):
            pack = await seed_safe_client_fixture_pack(sessionmaker, auth_service)

            async def _override_remnawave():
                return _SafeClientRemnawave(subscription_url=pack.subscription_url)

            app.dependency_overrides[get_remnawave_client] = _override_remnawave
            app.dependency_overrides[get_infrastructure_remnawave_client] = _override_remnawave
            headers = make_safe_customer_headers(auth_service, pack, pack.active)

            subscriptions = await async_client.get("/api/v1/customer-subscriptions/", headers=headers)
            assert subscriptions.status_code == 200
            subscriptions_payload = subscriptions.json()
            assert subscriptions_payload["default_subscription_key"] == pack.active.subscription_key
            assert subscriptions_payload["items"][0]["status"] == "active"
            assert subscriptions_payload["items"][0]["management_scope"] == "subscription_vpn_identity"
            assert subscriptions_payload["items"][0]["can_deliver_config"] is True

            entitlements = await async_client.get(
                f"/api/v1/customer-subscriptions/{pack.active.subscription_key}/entitlements",
                headers=headers,
            )
            assert entitlements.status_code == 200
            assert entitlements.json()["effective_entitlements"]["device_limit"] == 5

            config = await async_client.get(
                f"/api/v1/customer-subscriptions/{pack.active.subscription_key}/config",
                headers=headers,
            )
            assert config.status_code == 200
            config_payload = config.json()
            assert config_payload["config"] == pack.subscription_url
            assert config_payload["subscriptionUrl"] == pack.subscription_url

            service_state = await async_client.post(
                f"/api/v1/customer-subscriptions/{pack.active.subscription_key}/service-state",
                headers=headers,
                json={
                    "provider_name": "remnawave",
                    "channel_type": "shared_client",
                    "credential_type": "desktop_client",
                    "credential_subject_key": pack.active.device_subject_key,
                },
            )
            assert service_state.status_code == 200
            service_state_payload = service_state.json()
            assert service_state_payload["device_credential"]["subject_key"] == pack.active.device_subject_key
            assert service_state_payload["device_credential"]["credential_status"] == "active"
            assert (
                service_state_payload["access_delivery_channel"]["device_credential_id"]
                == (service_state_payload["device_credential"]["id"])
            )
            assert service_state_payload["access_delivery_channel"]["channel_subject_ref"] == (
                pack.active.device_subject_key
            )
            assert service_state_payload["access_delivery_channel"]["channel_status"] == "active"
            assert service_state_payload["access_delivery_channel"]["delivery_payload"]["subscription_url"] == (
                pack.subscription_url
            )

            current_delivery = await async_client.post(
                "/api/v1/access-delivery-channels/resolve/current",
                headers=headers,
                json={
                    "provider_name": "remnawave",
                    "channel_type": "shared_client",
                    "credential_type": "desktop_client",
                    "credential_subject_key": pack.active.device_subject_key,
                },
            )
            assert current_delivery.status_code == 201
            current_delivery_payload = current_delivery.json()
            assert current_delivery_payload["device_credential"]["subject_key"] == pack.active.device_subject_key
            assert current_delivery_payload["entitlement_status"] == "active"

            wallet = await async_client.get("/api/v1/wallet", headers=headers)
            assert wallet.status_code == 200
            assert wallet.json()["balance"] == 42.5
            wallet_transactions = await async_client.get("/api/v1/wallet/transactions", headers=headers)
            assert wallet_transactions.status_code == 200
            assert [item["type"] for item in wallet_transactions.json()] == ["debit", "credit"]

            payments = await async_client.get("/api/v1/payments/history", headers=headers)
            assert payments.status_code == 200
            assert payments.json()["payments"][0]["provider"] == "cryptobot"
            assert payments.json()["payments"][0]["status"] == "completed"

            promo = await async_client.post(
                "/api/v1/codes/resolve",
                headers=headers,
                json={
                    "code": pack.promo_code,
                    "action_context": "checkout",
                    "amount": 75,
                    "channel": "web",
                },
            )
            assert promo.status_code == 200
            assert promo.json()["accepted"] is True
            assert promo.json()["code_type"] == "promo"

            referral = await async_client.post(
                "/api/v1/codes/resolve",
                headers=headers,
                json={
                    "code": pack.referral_owner.referral_code,
                    "action_context": "checkout",
                    "amount": 75,
                    "channel": "web",
                },
            )
            assert referral.status_code == 200
            assert referral.json()["accepted"] is True
            assert referral.json()["code_type"] == "referral"

            partner = await async_client.post(
                "/api/v1/codes/resolve",
                headers=headers,
                json={
                    "code": pack.partner_code,
                    "action_context": "checkout",
                    "amount": 75,
                    "channel": "web",
                },
            )
            assert partner.status_code == 200
            assert partner.json()["accepted"] is True
            assert partner.json()["code_type"] == "partner"

            miniapp = await async_client.get(
                "/api/v1/miniapp/bootstrap",
                headers=headers,
                params={"locale": "en-EN", "selectedSubscriptionKey": pack.active.subscription_key},
            )
            assert miniapp.status_code == 200
            miniapp_payload = miniapp.json()
            assert miniapp_payload["subscription"]["status"] == "active"
            assert miniapp_payload["wallet"]["balance"] == 42.5
            assert miniapp_payload["devices"]["hasConfig"] is True
            assert miniapp_payload["usage"]["usageSource"] == "remnawave"
            assert miniapp_payload["serviceState"]["channelType"] == "telegram_bot"
            assert "hash=" in pack.miniapp_init_data

            assert_safe_payload_is_synthetic(
                {
                    "subscriptions": subscriptions_payload,
                    "config": config_payload,
                    "service_state": service_state_payload,
                    "current_delivery": current_delivery_payload,
                    "wallet": wallet.json(),
                    "wallet_transactions": wallet_transactions.json(),
                    "payments": payments.json(),
                    "promo": promo.json(),
                    "referral": referral.json(),
                    "partner": partner.json(),
                    "miniapp": miniapp_payload,
                    "miniapp_init_data": pack.miniapp_init_data,
                }
            )
    finally:
        app.dependency_overrides.pop(get_redis, None)
        app.dependency_overrides.pop(get_remnawave_client, None)
        app.dependency_overrides.pop(get_infrastructure_remnawave_client, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_safe_client_fixture_pack_covers_trial_expired_and_empty_subscription_states(
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
            pack = await seed_safe_client_fixture_pack(sessionmaker, auth_service)

            trial_headers = make_safe_customer_headers(auth_service, pack, pack.trial)
            expired_headers = make_safe_customer_headers(auth_service, pack, pack.expired)
            empty_headers = make_safe_customer_headers(auth_service, pack, pack.no_subscription)

            trial = await async_client.get("/api/v1/customer-subscriptions/", headers=trial_headers)
            assert trial.status_code == 200
            trial_items = trial.json()["items"]
            assert len(trial_items) == 1
            assert trial_items[0]["kind"] == "trial"
            assert trial_items[0]["status"] == "trial"

            expired = await async_client.get("/api/v1/customer-subscriptions/", headers=expired_headers)
            assert expired.status_code == 200
            expired_items = expired.json()["items"]
            assert len(expired_items) == 1
            assert expired_items[0]["status"] == "expired"

            empty = await async_client.get("/api/v1/customer-subscriptions/", headers=empty_headers)
            assert empty.status_code == 200
            assert empty.json()["items"] == []
            current_state = await async_client.post(
                "/api/v1/access-delivery-channels/current/service-state",
                headers=empty_headers,
                json={
                    "provider_name": "remnawave",
                    "channel_type": "shared_client",
                    "credential_type": "desktop_client",
                    "credential_subject_key": f"safe-empty-{uuid.uuid4().hex[:8]}",
                },
            )
            assert current_state.status_code == 200
            assert current_state.json()["entitlement_snapshot"]["status"] == "none"
            assert current_state.json()["service_identity"] is None
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
