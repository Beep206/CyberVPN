from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient

from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.growth_code_model import (
    GiftCodePolicyModel,
    GrowthCodeIssuanceModel,
    GrowthCodeModel,
    GrowthCodeRedemptionModel,
)
from src.infrastructure.database.models.growth_reward_allocation_model import GrowthRewardAllocationModel
from src.infrastructure.database.models.invite_code_model import InviteCodeModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.main import app
from src.presentation.dependencies.auth import get_current_mobile_user_id
from tests.helpers.realm_auth import (
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
def _clear_dependency_overrides():
    yield
    app.dependency_overrides.pop(get_current_mobile_user_id, None)


def _override_mobile_user(user_id: uuid.UUID) -> None:
    app.dependency_overrides[get_current_mobile_user_id] = lambda: user_id


@pytest.mark.asyncio
async def test_growth_notifications_feed_lists_customer_growth_lifecycle(async_client: AsyncClient) -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            now = datetime.now(UTC)
            user_id = uuid.uuid4()
            realm_id = uuid.uuid4()
            _override_mobile_user(user_id)

            with sessionmaker() as db:
                realm = AuthRealmModel(
                    id=realm_id,
                    realm_key="customer",
                    realm_type="customer",
                    display_name="Customer Realm",
                    audience="cybervpn:customer",
                    cookie_namespace="customer",
                    status="active",
                    is_default=True,
                )
                user = MobileUserModel(
                    id=user_id,
                    auth_realm_id=realm_id,
                    email="growth-inbox@example.test",
                    password_hash="not-used",
                    is_active=True,
                    status="active",
                )

                invite_active = InviteCodeModel(
                    id=uuid.uuid4(),
                    code="INVITE-ACTIVE",
                    owner_user_id=user_id,
                    free_days=14,
                    source="purchase",
                    is_used=False,
                    expires_at=now + timedelta(days=2),
                    created_at=now - timedelta(days=2),
                )
                invite_used = InviteCodeModel(
                    id=uuid.uuid4(),
                    code="INVITE-USED",
                    owner_user_id=user_id,
                    free_days=7,
                    source="admin_grant",
                    is_used=True,
                    used_by_user_id=uuid.uuid4(),
                    used_at=now - timedelta(hours=6),
                    created_at=now - timedelta(days=5),
                )

                reward_pending = GrowthRewardAllocationModel(
                    id=uuid.uuid4(),
                    reward_type="referral_credit",
                    allocation_status="pending",
                    beneficiary_user_id=user_id,
                    auth_realm_id=realm_id,
                    quantity=Decimal("10.00"),
                    unit="usd",
                    currency_code="USD",
                    reward_payload={},
                    hold_until=now + timedelta(days=7),
                    allocated_at=now - timedelta(hours=4),
                )
                reward_available = GrowthRewardAllocationModel(
                    id=uuid.uuid4(),
                    reward_type="referral_credit",
                    allocation_status="available",
                    beneficiary_user_id=user_id,
                    auth_realm_id=realm_id,
                    quantity=Decimal("6.00"),
                    unit="usd",
                    currency_code="USD",
                    reward_payload={},
                    available_at=now - timedelta(hours=3),
                    allocated_at=now - timedelta(days=1),
                )

                gift_active_code = GrowthCodeModel(
                    id=uuid.uuid4(),
                    code_hash="gift-active-hash",
                    code_prefix="GFTA",
                    code_type="gift",
                    status="active",
                    issuer_type="admin",
                    owner_user_id=user_id,
                    auth_realm_id=realm_id,
                    expires_at=now + timedelta(days=5),
                    created_at=now - timedelta(hours=8),
                    updated_at=now - timedelta(hours=8),
                )
                gift_active_policy = GiftCodePolicyModel(
                    id=uuid.uuid4(),
                    growth_code_id=gift_active_code.id,
                    grant_type="subscription",
                    plan_family="pro",
                    duration_days=180,
                    entitlement_snapshot={},
                    redemption_mode="redeem",
                    transferable=False,
                    policy_snapshot={"recipient_hint": "friend@example.test"},
                    created_at=now - timedelta(hours=8),
                    updated_at=now - timedelta(hours=8),
                )
                gift_active_issuance = GrowthCodeIssuanceModel(
                    id=uuid.uuid4(),
                    growth_code_id=gift_active_code.id,
                    issuance_type="admin_manual_gift",
                    issued_to_user_id=user_id,
                    reason_code="admin_manual_gift",
                    created_at=now - timedelta(hours=8),
                )

                gift_redeemed_code = GrowthCodeModel(
                    id=uuid.uuid4(),
                    code_hash="gift-redeemed-hash",
                    code_prefix="GFTB",
                    code_type="gift",
                    status="redeemed",
                    issuer_type="purchase",
                    owner_user_id=user_id,
                    auth_realm_id=realm_id,
                    uses_count=1,
                    created_at=now - timedelta(days=3),
                    updated_at=now - timedelta(hours=1),
                )
                gift_redeemed_policy = GiftCodePolicyModel(
                    id=uuid.uuid4(),
                    growth_code_id=gift_redeemed_code.id,
                    grant_type="subscription",
                    plan_family="max",
                    duration_days=365,
                    entitlement_snapshot={},
                    redemption_mode="redeem",
                    transferable=False,
                    policy_snapshot={},
                    created_at=now - timedelta(days=3),
                    updated_at=now - timedelta(days=3),
                )
                gift_redeemed_issuance = GrowthCodeIssuanceModel(
                    id=uuid.uuid4(),
                    growth_code_id=gift_redeemed_code.id,
                    issuance_type="gift_purchase",
                    issued_to_user_id=user_id,
                    reason_code="gift_purchase",
                    created_at=now - timedelta(days=3),
                )
                gift_redeemed_redemption = GrowthCodeRedemptionModel(
                    id=uuid.uuid4(),
                    growth_code_id=gift_redeemed_code.id,
                    code_type="gift",
                    redeemer_user_id=uuid.uuid4(),
                    beneficiary_user_id=uuid.uuid4(),
                    status="redeemed",
                    redeemed_at=now - timedelta(hours=2),
                    created_at=now - timedelta(hours=2),
                )

                db.add_all(
                    [
                        realm,
                        user,
                        invite_active,
                        invite_used,
                        reward_pending,
                        reward_available,
                        gift_active_code,
                        gift_active_policy,
                        gift_active_issuance,
                        gift_redeemed_code,
                        gift_redeemed_policy,
                        gift_redeemed_issuance,
                        gift_redeemed_redemption,
                    ]
                )
                db.commit()

            response = await async_client.get("/api/v1/growth-notifications")
            assert response.status_code == 200
            payload = response.json()
            kinds = {item["kind"] for item in payload}
            assert "invite_issued" in kinds
            assert "invite_redeemed" in kinds
            assert "invite_expiring_soon" in kinds
            assert "referral_reward_pending" in kinds
            assert "referral_reward_available" in kinds
            assert "gift_available" in kinds
            assert "gift_redeemed" in kinds

            counters_response = await async_client.get("/api/v1/growth-notifications/counters")
            assert counters_response.status_code == 200
            counters_payload = counters_response.json()
            assert counters_payload["total_notifications"] >= 7
            assert counters_payload["unread_notifications"] >= 7
            assert counters_payload["action_required_notifications"] >= 2
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_growth_notifications_can_be_marked_read_and_archived(async_client: AsyncClient) -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            now = datetime.now(UTC)
            user_id = uuid.uuid4()
            realm_id = uuid.uuid4()
            _override_mobile_user(user_id)

            with sessionmaker() as db:
                realm = AuthRealmModel(
                    id=realm_id,
                    realm_key="customer",
                    realm_type="customer",
                    display_name="Customer Realm",
                    audience="cybervpn:customer",
                    cookie_namespace="customer",
                    status="active",
                    is_default=True,
                )
                user = MobileUserModel(
                    id=user_id,
                    auth_realm_id=realm_id,
                    email="growth-inbox-actions@example.test",
                    password_hash="not-used",
                    is_active=True,
                    status="active",
                )
                invite = InviteCodeModel(
                    id=uuid.uuid4(),
                    code="INVITE-READ",
                    owner_user_id=user_id,
                    free_days=14,
                    source="purchase",
                    is_used=False,
                    expires_at=now + timedelta(days=10),
                    created_at=now - timedelta(hours=1),
                )
                db.add_all([realm, user, invite])
                db.commit()

            feed_response = await async_client.get("/api/v1/growth-notifications")
            assert feed_response.status_code == 200
            notification_id = feed_response.json()[0]["id"]

            read_response = await async_client.post(f"/api/v1/growth-notifications/{notification_id}/read")
            assert read_response.status_code == 200
            assert read_response.json()["notification_id"] == notification_id
            assert read_response.json()["read_at"] is not None

            counters_response = await async_client.get("/api/v1/growth-notifications/counters")
            assert counters_response.status_code == 200
            assert counters_response.json()["unread_notifications"] == 0

            archive_response = await async_client.post(
                f"/api/v1/growth-notifications/{notification_id}/archive"
            )
            assert archive_response.status_code == 200
            assert archive_response.json()["archived_at"] is not None

            feed_after_archive = await async_client.get("/api/v1/growth-notifications")
            assert feed_after_archive.status_code == 200
            assert feed_after_archive.json() == []

            archived_feed = await async_client.get("/api/v1/growth-notifications?include_archived=true")
            assert archived_feed.status_code == 200
            assert len(archived_feed.json()) == 1
            assert archived_feed.json()[0]["id"] == notification_id
            assert archived_feed.json()[0]["unread"] is False
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
