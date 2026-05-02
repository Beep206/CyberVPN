from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.application.use_cases.gifts import IssueGiftCodeUseCase
from src.application.use_cases.growth_codes.admin_signals import (
    GetAdminGrowthSignalsOverviewUseCase,
    ListAdminGrowthAbuseSignalsUseCase,
)
from src.application.use_cases.growth_codes.registry import GrowthCodeRegistryService
from src.application.use_cases.growth_codes.resolve_code import ResolveGrowthCodeUseCase
from src.application.use_cases.growth_rewards import CreateGrowthRewardAllocationUseCase
from src.domain.enums import GrowthCodeActionContext, GrowthRewardAllocationStatus, GrowthRewardType
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.promo_code_model import PromoCodeModel
from src.main import app
from tests.helpers.realm_auth import (
    FakeRedis,
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)
from tests.integration.test_quote_checkout_sessions import _seed_quote_context

pytestmark = [pytest.mark.integration]


async def _create_admin_user(sessionmaker, auth_service: AuthService) -> tuple[AdminUserModel, str]:
    password = "GrowthSignalsAdmin123!"
    with sessionmaker() as db:
        user = AdminUserModel(
            id=uuid.uuid4(),
            login="growthsignalsadmin",
            email="growth-signals-admin@example.test",
            password_hash=await auth_service.hash_password(password),
            role="admin",
            is_active=True,
            is_email_verified=True,
            language="en",
            timezone="UTC",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user, password


@pytest.mark.asyncio
async def test_admin_growth_signals_overview_returns_live_growth_metrics(async_client: AsyncClient) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_quote_context(sessionmaker, auth_service)
            admin_user, admin_password = await _create_admin_user(sessionmaker, auth_service)

            with sessionmaker() as db:
                promo = PromoCodeModel(
                    id=uuid.uuid4(),
                    code="OVERVIEWPROMO",
                    discount_type="percent",
                    discount_value=10,
                    is_active=True,
                )
                db.add(promo)
                db.commit()

                session = SyncSessionAdapter(db)
                await ResolveGrowthCodeUseCase(session).execute(
                    code=promo.code,
                    action_context=GrowthCodeActionContext.CHECKOUT,
                    user_id=uuid.UUID(seeded["customer_user_id"]),
                    plan_id=uuid.UUID(seeded["plan_id"]),
                    amount=Decimal("79"),
                    storefront_id=uuid.UUID(seeded["storefront_id"]),
                    surface="web",
                )
                await IssueGiftCodeUseCase(session).execute(
                    owner_user_id=uuid.UUID(seeded["customer_user_id"]),
                    plan_id=uuid.UUID(seeded["plan_id"]),
                    issuer_type="admin",
                    issuance_type="admin_manual_gift",
                    auth_realm_id=uuid.UUID(seeded["customer_realm_id"]),
                    issued_by_admin_id=admin_user.id,
                    reason_code="admin_manual_gift",
                )
                await CreateGrowthRewardAllocationUseCase(session).execute(
                    reward_type=GrowthRewardType.REFERRAL_CREDIT.value,
                    beneficiary_user_id=uuid.UUID(seeded["customer_user_id"]),
                    allocation_status=GrowthRewardAllocationStatus.AVAILABLE.value,
                    quantity=Decimal("15"),
                    unit="credit",
                    currency_code="USD",
                    storefront_id=uuid.UUID(seeded["storefront_id"]),
                    source_key="test:overview:available",
                    commit=False,
                )
                await CreateGrowthRewardAllocationUseCase(session).execute(
                    reward_type=GrowthRewardType.REFERRAL_CREDIT.value,
                    beneficiary_user_id=uuid.UUID(seeded["customer_user_id"]),
                    allocation_status=GrowthRewardAllocationStatus.BLOCKED_BY_RISK.value,
                    quantity=Decimal("5"),
                    unit="credit",
                    currency_code="USD",
                    storefront_id=uuid.UUID(seeded["storefront_id"]),
                    source_key="test:overview:blocked",
                    commit=False,
                )
                db.commit()

                overview = await GetAdminGrowthSignalsOverviewUseCase(session).execute()
                assert overview.total_codes >= 2
                assert overview.available_referral_credit_usd == 15.0
                assert overview.blocked_reward_count == 1

            login_response = await async_client.post(
                "/api/v1/auth/login",
                json={
                    "login_or_email": admin_user.login,
                    "password": admin_password,
                },
                headers={"X-Auth-Realm": "admin"},
            )
            assert login_response.status_code == 200
            admin_token = login_response.json()["access_token"]

            response = await async_client.get(
                "/api/v1/admin/growth-signals/overview",
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "X-Auth-Realm": "admin",
                },
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["total_codes"] >= 2
            assert payload["available_referral_credit_usd"] == 15.0
            assert payload["blocked_reward_count"] == 1
            assert payload["recent_lifecycle_events"]
            assert any(
                item["event_name"] in {"gift.issued", "growth_reward.allocation.created"}
                for item in payload["recent_lifecycle_events"]
            )
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_admin_growth_abuse_queue_returns_resolution_clusters_and_blocked_rewards(
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
            seeded = await _seed_quote_context(sessionmaker, auth_service)
            admin_user, admin_password = await _create_admin_user(sessionmaker, auth_service)

            with sessionmaker() as db:
                session = SyncSessionAdapter(db)
                registry = GrowthCodeRegistryService(session)
                for _ in range(3):
                    await registry.record_resolution_event(
                        growth_code_id=None,
                        raw_code="SELFBLOCK01",
                        code_type="invite",
                        user_id=uuid.UUID(seeded["customer_user_id"]),
                        surface="web",
                        action_context="redeem",
                        result="rejected",
                        reject_reason="invite_self_redemption_blocked",
                        conflict_code=None,
                        policy_version_id=None,
                    )
                await CreateGrowthRewardAllocationUseCase(session).execute(
                    reward_type=GrowthRewardType.REFERRAL_CREDIT.value,
                    beneficiary_user_id=uuid.UUID(seeded["customer_user_id"]),
                    allocation_status=GrowthRewardAllocationStatus.BLOCKED_BY_RISK.value,
                    quantity=Decimal("9"),
                    unit="credit",
                    currency_code="USD",
                    storefront_id=uuid.UUID(seeded["storefront_id"]),
                    source_key="test:abuse:blocked",
                    commit=False,
                )
                db.commit()

                queue = await ListAdminGrowthAbuseSignalsUseCase(session).execute(limit=10)
                assert any(item.reason_code == "invite_self_redemption_blocked" for item in queue)
                assert any(item.signal_type == "blocked_reward" for item in queue)

            login_response = await async_client.post(
                "/api/v1/auth/login",
                json={
                    "login_or_email": admin_user.login,
                    "password": admin_password,
                },
                headers={"X-Auth-Realm": "admin"},
            )
            assert login_response.status_code == 200
            admin_token = login_response.json()["access_token"]

            response = await async_client.get(
                "/api/v1/admin/growth-signals/abuse-queue?limit=10",
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "X-Auth-Realm": "admin",
                },
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["total"] >= 2
            assert any(item["reason_code"] == "invite_self_redemption_blocked" for item in payload["items"])
            assert any(item["signal_type"] == "blocked_reward" for item in payload["items"])
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_admin_referral_endpoints_return_canonical_reward_timeline(
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
            seeded = await _seed_quote_context(sessionmaker, auth_service)
            admin_user, admin_password = await _create_admin_user(sessionmaker, auth_service)

            with sessionmaker() as db:
                referrer = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=uuid.UUID(seeded["customer_realm_id"]),
                    email="referrer-admin-view@example.test",
                    password_hash=await auth_service.hash_password("ReferrerAdminView123!"),
                    is_active=True,
                    status="active",
                    referral_code="REFADMINVIEW",
                )
                referred = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=uuid.UUID(seeded["customer_realm_id"]),
                    email="referred-admin-view@example.test",
                    password_hash=await auth_service.hash_password("ReferredAdminView123!"),
                    is_active=True,
                    status="active",
                    referred_by_user_id=referrer.id,
                )
                db.add_all([referrer, referred])
                db.commit()

                session = SyncSessionAdapter(db)
                await CreateGrowthRewardAllocationUseCase(session).execute(
                    reward_type=GrowthRewardType.REFERRAL_CREDIT.value,
                    beneficiary_user_id=referrer.id,
                    allocation_status=GrowthRewardAllocationStatus.AVAILABLE.value,
                    quantity=Decimal("10"),
                    unit="credit",
                    currency_code="USD",
                    storefront_id=uuid.UUID(seeded["storefront_id"]),
                    source_key="test:admin-referrals:available",
                    reward_payload={
                        "payment_id": str(uuid.uuid4()),
                        "referred_user_id": str(referred.id),
                        "base_amount": "79.00",
                        "friend_discount_value": 10,
                    },
                    commit=False,
                )
                db.commit()

            login_response = await async_client.post(
                "/api/v1/auth/login",
                json={
                    "login_or_email": admin_user.login,
                    "password": admin_password,
                },
                headers={"X-Auth-Realm": "admin"},
            )
            assert login_response.status_code == 200
            admin_token = login_response.json()["access_token"]
            headers = {
                "Authorization": f"Bearer {admin_token}",
                "X-Auth-Realm": "admin",
            }

            overview_response = await async_client.get(
                "/api/v1/admin/referrals/overview",
                headers=headers,
            )
            assert overview_response.status_code == 200
            overview_payload = overview_response.json()
            assert overview_payload["total_commissions"] >= 1
            assert overview_payload["unique_referred_users"] >= 1
            assert overview_payload["recent_commissions"]
            assert any(
                item["source_model"] == "growth_reward"
                and item["reward_status"] == GrowthRewardAllocationStatus.AVAILABLE.value
                for item in overview_payload["recent_commissions"]
            )
            assert any(
                row["user"] is not None and row["user"]["id"] == str(referrer.id)
                for row in overview_payload["top_referrers"]
            )

            detail_response = await async_client.get(
                f"/api/v1/admin/referrals/users/{referrer.id}",
                headers=headers,
            )
            assert detail_response.status_code == 200
            detail_payload = detail_response.json()
            assert detail_payload["user"]["id"] == str(referrer.id)
            assert detail_payload["referred_users"] >= 1
            assert detail_payload["commission_count"] >= 1
            assert detail_payload["total_earned"] >= 10.0
            assert any(
                item["source_model"] == "growth_reward"
                for item in detail_payload["recent_commissions"]
            )
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
