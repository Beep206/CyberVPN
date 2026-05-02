from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.application.services.config_service import ConfigService
from src.application.use_cases.referrals.process_referral_reward import (
    ProcessReferralRewardUseCase,
)
from src.application.use_cases.referrals.release_referral_rewards import (
    ReleaseReferralRewardsUseCase,
)
from src.application.use_cases.referrals.reverse_referral_rewards import (
    ReverseReferralRewardsForOrderUseCase,
)
from src.domain.enums import GrowthRewardAllocationStatus, GrowthRewardType
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.invite_code_model import InviteCodeModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import PartnerCodeModel
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.infrastructure.database.repositories.growth_reward_allocation_repo import (
    GrowthRewardAllocationRepository,
)
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.main import app
from tests.helpers.realm_auth import (
    FakeRedis,
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)
from tests.integration.test_order_attribution_resolution import _create_quote_checkout
from tests.integration.test_order_commit import _make_customer_access_token, _seed_order_context

pytestmark = [pytest.mark.integration]


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


@pytest.mark.asyncio
async def test_invite_redeem_creates_entitlement_grant_instead_of_bonus_days_reward(
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
            customer_realm = AuthRealmModel(
                id=uuid.uuid4(),
                realm_key="customer",
                realm_type="customer",
                display_name="Customer Realm",
                audience="cybervpn:customer",
                cookie_namespace="customer",
                status="active",
                is_default=True,
            )

            with sessionmaker() as db:
                realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
                admin_realm = await realm_repo.get_or_create_default_realm("admin")

                invite_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="invite-owner@example.test",
                    password_hash=await auth_service.hash_password("InviteOwner123!"),
                    is_active=True,
                    status="active",
                )
                beneficiary = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="invite-beneficiary@example.test",
                    password_hash=await auth_service.hash_password("InviteBeneficiary123!"),
                    is_active=True,
                    status="active",
                )
                support_user = AdminUserModel(
                    login="growth_reward_support",
                    email="growth-reward-support@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("GrowthRewardSupport123!"),
                    role="support",
                    is_active=True,
                    is_email_verified=True,
                )
                invite = InviteCodeModel(
                    id=uuid.uuid4(),
                    code="BONUS-42",
                    owner_user_id=invite_owner.id,
                    free_days=42,
                    source="purchase",
                    is_used=False,
                )
                db.add_all([customer_realm, invite_owner, beneficiary, support_user, invite])
                db.commit()

                support_token = _make_admin_token(auth_service, user_id=support_user.id, realm=admin_realm)

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=beneficiary.id,
                customer_realm=customer_realm,
            )
            customer_headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }
            support_headers = {
                "Authorization": f"Bearer {support_token}",
                "X-Auth-Realm": "admin",
            }

            redeem_response = await async_client.post(
                "/api/v1/invites/redeem",
                headers=customer_headers,
                json={"code": invite.code},
            )
            assert redeem_response.status_code == 200
            redeem_payload = redeem_response.json()
            assert redeem_payload["entitlement_grant_id"] is not None
            assert redeem_payload["entitlement_snapshot"]["status"] == "active"
            assert redeem_payload["entitlement_snapshot"]["plan_code"] == "invite"
            assert redeem_payload["entitlement_snapshot"]["effective_entitlements"]["device_limit"] == 1

            current_entitlement_response = await async_client.get(
                "/api/v1/entitlements/current",
                headers=customer_headers,
            )
            assert current_entitlement_response.status_code == 200
            current_entitlement_payload = current_entitlement_response.json()
            assert current_entitlement_payload["status"] == "active"
            assert current_entitlement_payload["plan_code"] == "invite"
            assert current_entitlement_payload["period_days"] == 42
            assert current_entitlement_payload["effective_entitlements"]["device_limit"] == 1

            list_response = await async_client.get(
                "/api/v1/growth-rewards/allocations",
                headers=support_headers,
                params={"beneficiary_user_id": str(beneficiary.id)},
            )
            assert list_response.status_code == 200
            allocations = list_response.json()
            assert allocations == []
    finally:
        app.dependency_overrides.pop(get_redis, None)
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_referral_reward_creates_pending_growth_reward_without_wallet_credit(
) -> None:
    auth_service = AuthService()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        with sessionmaker() as db:
            adapter = SyncSessionAdapter(db)
            realm = AuthRealmModel(
                id=uuid.uuid4(),
                realm_key=f"customer-{uuid.uuid4().hex[:8]}",
                realm_type="customer",
                display_name="Referral Growth Realm",
                audience=f"cybervpn:customer:{uuid.uuid4().hex[:8]}",
                cookie_namespace=f"customer-{uuid.uuid4().hex[:8]}",
                status="active",
                is_default=False,
            )
            referrer = MobileUserModel(
                id=uuid.uuid4(),
                auth_realm_id=realm.id,
                email=f"referrer-{uuid.uuid4().hex[:8]}@example.test",
                password_hash=await auth_service.hash_password("Referrer123!"),
                is_active=True,
                status="active",
                referral_code=f"REF{uuid.uuid4().hex[:6].upper()}",
            )
            referred = MobileUserModel(
                id=uuid.uuid4(),
                auth_realm_id=realm.id,
                email=f"referred-{uuid.uuid4().hex[:8]}@example.test",
                password_hash=await auth_service.hash_password("Referred123!"),
                is_active=True,
                status="active",
                referred_by_user_id=referrer.id,
            )
            payment = PaymentModel(
                id=uuid.uuid4(),
                user_uuid=referred.id,
                amount=Decimal("125.00"),
                currency="USD",
                status="completed",
                provider="cryptobot",
                subscription_days=365,
                metadata_={},
            )
            db.add_all([realm, referrer, referred, payment])
            db.commit()

            config_repo = SystemConfigRepository(adapter)
            await config_repo.set("referral.enabled", {"enabled": True})
            await config_repo.set("referral.commission_rate", {"rate": 0.10})
            await config_repo.set("referral.duration_mode", {"mode": "first_payment_only"})

            use_case = ProcessReferralRewardUseCase(
                adapter,
                config_service=ConfigService(config_repo),
            )
            allocation = await use_case.execute(
                referrer_user_id=referrer.id,
                referred_user_id=referred.id,
                payment_id=payment.id,
                base_amount=Decimal("125.00"),
                duration_days=365,
            )
            db.commit()

            assert allocation is not None

            allocations = await GrowthRewardAllocationRepository(adapter).list(
                beneficiary_user_id=referrer.id,
            )
            assert len(allocations) == 1
            allocation = allocations[0]
            assert allocation.reward_type == GrowthRewardType.REFERRAL_CREDIT.value
            assert allocation.referral_commission_id is None
            assert allocation.source_code_id is not None
            assert float(allocation.quantity) == 10.0
            assert allocation.unit == "credit"
            assert allocation.currency_code == "USD"
            assert allocation.allocation_status == GrowthRewardAllocationStatus.PENDING.value
            assert allocation.hold_until is not None
            assert allocation.available_at is None
            assert allocation.reward_payload["payment_id"] == str(payment.id)
            assert allocation.reward_payload["referred_user_id"] == str(referred.id)
            assert allocation.reward_payload["reward_was_capped"] is False
    finally:
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_release_referral_rewards_moves_pending_reward_to_available() -> None:
    auth_service = AuthService()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        with sessionmaker() as db:
            adapter = SyncSessionAdapter(db)
            realm = AuthRealmModel(
                id=uuid.uuid4(),
                realm_key=f"customer-{uuid.uuid4().hex[:8]}",
                realm_type="customer",
                display_name="Referral Growth Realm",
                audience=f"cybervpn:customer:{uuid.uuid4().hex[:8]}",
                cookie_namespace=f"customer-{uuid.uuid4().hex[:8]}",
                status="active",
                is_default=False,
            )
            referrer = MobileUserModel(
                id=uuid.uuid4(),
                auth_realm_id=realm.id,
                email=f"referrer-{uuid.uuid4().hex[:8]}@example.test",
                password_hash=await auth_service.hash_password("Referrer123!"),
                is_active=True,
                status="active",
                referral_code=f"REF{uuid.uuid4().hex[:6].upper()}",
            )
            referred = MobileUserModel(
                id=uuid.uuid4(),
                auth_realm_id=realm.id,
                email=f"referred-{uuid.uuid4().hex[:8]}@example.test",
                password_hash=await auth_service.hash_password("Referred123!"),
                is_active=True,
                status="active",
                referred_by_user_id=referrer.id,
            )
            payment = PaymentModel(
                id=uuid.uuid4(),
                user_uuid=referred.id,
                amount=Decimal("125.00"),
                currency="USD",
                status="completed",
                provider="cryptobot",
                subscription_days=365,
                metadata_={},
            )
            db.add_all([realm, referrer, referred, payment])
            db.commit()

            config_repo = SystemConfigRepository(adapter)
            await config_repo.set("referral.enabled", {"enabled": True})

            created = await ProcessReferralRewardUseCase(
                adapter,
                config_service=ConfigService(config_repo),
            ).execute(
                referrer_user_id=referrer.id,
                referred_user_id=referred.id,
                payment_id=payment.id,
                base_amount=Decimal("125.00"),
                duration_days=365,
            )
            db.commit()

            assert created is not None
            released = await ReleaseReferralRewardsUseCase(adapter).execute(
                as_of=datetime.now(UTC) + timedelta(days=30),
                commit=False,
            )
            db.commit()

            assert len(released) == 1
            assert released[0].id == created.id
            assert released[0].allocation_status == GrowthRewardAllocationStatus.AVAILABLE.value
            assert released[0].available_at is not None
            assert released[0].hold_until is None
    finally:
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_reverse_referral_rewards_for_order_marks_reward_reversed(
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
            access_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Auth-Realm": "customer",
            }

            quote_payload, checkout_payload = await _create_quote_checkout(
                async_client=async_client,
                headers=headers,
                storefront_key=seeded["storefront_key"],
                pricebook_key=seeded["pricebook_key"],
                offer_key=seeded["offer_key"],
                plan_id=seeded["plan_id"],
                idempotency_key="referral-reverse-checkout",
            )
            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=headers,
                json={"checkout_session_id": checkout_payload["id"]},
            )
            assert order_response.status_code == 201
            order_payload = order_response.json()

            with sessionmaker() as db:
                adapter = SyncSessionAdapter(db)
                customer_user = db.get(MobileUserModel, uuid.UUID(seeded["customer_user_id"]))
                assert customer_user is not None
                referrer = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_user.auth_realm_id,
                    email=f"referrer-{uuid.uuid4().hex[:8]}@example.test",
                    password_hash=await auth_service.hash_password("Referrer123!"),
                    is_active=True,
                    status="active",
                    referral_code=f"REF{uuid.uuid4().hex[:6].upper()}",
                )
                customer_user.referred_by_user_id = referrer.id
                payment = PaymentModel(
                    id=uuid.uuid4(),
                    user_uuid=customer_user.id,
                    amount=Decimal("125.00"),
                    currency="USD",
                    status="completed",
                    provider="cryptobot",
                    subscription_days=365,
                    metadata_={},
                )
                db.add_all([referrer, payment])
                db.commit()

                config_repo = SystemConfigRepository(adapter)
                await config_repo.set("referral.enabled", {"enabled": True})

                allocation = await ProcessReferralRewardUseCase(
                    adapter,
                    config_service=ConfigService(config_repo),
                ).execute(
                    referrer_user_id=referrer.id,
                    referred_user_id=customer_user.id,
                    payment_id=payment.id,
                    base_amount=Decimal("125.00"),
                    duration_days=365,
                    order_id=uuid.UUID(order_payload["id"]),
                    storefront_id=uuid.UUID(seeded["storefront_id"]),
                )
                db.commit()

                assert allocation is not None
                reversed_allocations = await ReverseReferralRewardsForOrderUseCase(adapter).execute(
                    order_id=uuid.UUID(order_payload["id"]),
                    reversal_reason="refund_succeeded",
                    commit=False,
                )
                db.commit()

                assert len(reversed_allocations) == 1
                assert reversed_allocations[0].id == allocation.id
                assert reversed_allocations[0].allocation_status == GrowthRewardAllocationStatus.REVERSED.value
                assert reversed_allocations[0].reversal_reason == "refund_succeeded"
                assert reversed_allocations[0].reversed_at is not None
    finally:
        app.dependency_overrides.pop(get_redis, None)
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_growth_rewards_can_coexist_with_commercial_owner_and_surface_in_explainability(
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
                    email="growth-owner@example.test",
                    password_hash=await auth_service.hash_password("GrowthOwner123!"),
                    is_active=True,
                    status="active",
                    is_partner=True,
                )
                affiliate_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="GROWTH42",
                    partner_user_id=partner_owner.id,
                    markup_pct=12,
                    is_active=True,
                )
                admin_user = AdminUserModel(
                    login="growth_reward_admin",
                    email="growth-reward-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("GrowthRewardAdmin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                support_user = AdminUserModel(
                    login="growth_reward_support_order",
                    email="growth-reward-support-order@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("GrowthRewardSupportOrder123!"),
                    role="support",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add_all([partner_owner, affiliate_code, admin_user, support_user])
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

            _, checkout_payload = await _create_quote_checkout(
                async_client=async_client,
                headers=customer_headers,
                storefront_key=seeded["storefront_key"],
                pricebook_key=seeded["pricebook_key"],
                offer_key=seeded["offer_key"],
                plan_id=seeded["plan_id"],
                partner_code=affiliate_code.code,
                idempotency_key="growth-reward-checkout",
            )
            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=customer_headers,
                json={"checkout_session_id": checkout_payload["id"]},
            )
            assert order_response.status_code == 201
            order_payload = order_response.json()
            order_id = order_payload["id"]

            initial_attribution = await async_client.get(
                f"/api/v1/attribution/orders/{order_id}/result",
                headers=support_headers,
            )
            assert initial_attribution.status_code == 200
            initial_result = initial_attribution.json()
            assert initial_result["owner_type"] == "affiliate"

            allocation_payloads = (
                {
                    "reward_type": GrowthRewardType.INVITE_REWARD.value,
                    "beneficiary_user_id": seeded["customer_user_id"],
                    "order_id": order_id,
                    "quantity": 1,
                    "unit": "perk",
                    "source_key": f"manual:{order_id}:invite_reward",
                    "reward_payload": {"campaign": "support-grant"},
                },
                {
                    "reward_type": GrowthRewardType.GIFT_BONUS.value,
                    "beneficiary_user_id": seeded["customer_user_id"],
                    "order_id": order_id,
                    "quantity": 1,
                    "unit": "perk",
                    "source_key": f"manual:{order_id}:gift_bonus",
                    "reward_payload": {"gift_bundle": "spring"},
                },
            )
            for payload in allocation_payloads:
                create_response = await async_client.post(
                    "/api/v1/growth-rewards/allocations",
                    headers=admin_headers,
                    json=payload,
                )
                assert create_response.status_code == 201

            list_response = await async_client.get(
                "/api/v1/growth-rewards/allocations",
                headers=support_headers,
                params={"order_id": order_id},
            )
            assert list_response.status_code == 200
            allocations = list_response.json()
            assert len(allocations) == 2
            assert {item["reward_type"] for item in allocations} == {
                GrowthRewardType.INVITE_REWARD.value,
                GrowthRewardType.GIFT_BONUS.value,
            }

            explainability_response = await async_client.get(
                f"/api/v1/orders/{order_id}/explainability",
                headers=support_headers,
            )
            assert explainability_response.status_code == 200
            explainability = explainability_response.json()["explainability"]
            assert explainability["future_phase_placeholders"]["growth_reward_allocation_count"] == 2
            assert len(explainability["linked_growth_reward_allocations"]) == 2
            assert {item["reward_type"] for item in explainability["linked_growth_reward_allocations"]} == {
                GrowthRewardType.INVITE_REWARD.value,
                GrowthRewardType.GIFT_BONUS.value,
            }
            assert explainability["growth_reward_summary"]["allocation_count"] == 2
            assert explainability["lane_views"]["invite_gift"]["active"] is True
            assert explainability["lane_views"]["creator_affiliate"]["active"] is True
            assert explainability["lane_views"]["consumer_referral"]["active"] is False

            final_attribution = await async_client.get(
                f"/api/v1/attribution/orders/{order_id}/result",
                headers=support_headers,
            )
            assert final_attribution.status_code == 200
            final_result = final_attribution.json()
            assert final_result["id"] == initial_result["id"]
            assert final_result["owner_type"] == initial_result["owner_type"]
            assert final_result["owner_source"] == initial_result["owner_source"]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_referral_credit_surfaces_consumer_referral_lane_in_explainability(
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

                admin_user = AdminUserModel(
                    login="growth_reward_admin_referral",
                    email="growth-reward-admin-referral@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("GrowthRewardAdminReferral123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                support_user = AdminUserModel(
                    login="growth_reward_support_referral",
                    email="growth-reward-support-referral@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("GrowthRewardSupportReferral123!"),
                    role="support",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add_all([admin_user, support_user])
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

            _, checkout_payload = await _create_quote_checkout(
                async_client=async_client,
                headers=customer_headers,
                storefront_key=seeded["storefront_key"],
                pricebook_key=seeded["pricebook_key"],
                offer_key=seeded["offer_key"],
                plan_id=seeded["plan_id"],
                idempotency_key="growth-reward-referral-lane",
            )
            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=customer_headers,
                json={"checkout_session_id": checkout_payload["id"]},
            )
            assert order_response.status_code == 201
            order_id = order_response.json()["id"]

            create_response = await async_client.post(
                "/api/v1/growth-rewards/allocations",
                headers=admin_headers,
                json={
                    "reward_type": GrowthRewardType.REFERRAL_CREDIT.value,
                    "beneficiary_user_id": seeded["customer_user_id"],
                    "order_id": order_id,
                    "quantity": 6,
                    "unit": "credit",
                    "currency_code": "USD",
                    "source_key": f"manual:{order_id}:referral_credit",
                    "reward_payload": {"campaign": "support-referral-credit"},
                },
            )
            assert create_response.status_code == 201

            explainability_response = await async_client.get(
                f"/api/v1/orders/{order_id}/explainability",
                headers=support_headers,
            )
            assert explainability_response.status_code == 200
            explainability = explainability_response.json()["explainability"]
            assert explainability["lane_views"]["consumer_referral"]["active"] is True
            assert explainability["lane_views"]["invite_gift"]["active"] is False
            assert explainability["lane_views"]["creator_affiliate"]["active"] is False
            assert explainability["growth_reward_summary"]["active_reward_types"] == [
                GrowthRewardType.REFERRAL_CREDIT.value
            ]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        cleanup_sqlite_file(sqlite_path)
