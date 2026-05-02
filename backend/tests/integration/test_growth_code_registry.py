from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from src.application.services.auth_service import AuthService
from src.application.use_cases.growth_codes.hashing import build_growth_code_prefix, hash_growth_code
from src.application.use_cases.growth_codes.registry import GrowthCodeRegistryService
from src.application.use_cases.growth_rewards.create_allocation import CreateGrowthRewardAllocationUseCase
from src.domain.enums import GrowthCodeType, GrowthRewardAllocationStatus, GrowthRewardType
from src.infrastructure.database.models.growth_code_model import (
    GrowthCodeIssuanceModel,
    GrowthCodeModel,
    GrowthCodeRedemptionModel,
    GrowthCodeReservationModel,
    GrowthCodeResolutionEventModel,
    GrowthCodeTouchpointModel,
    GrowthSignupAttributionModel,
    InviteCodePolicyModel,
)
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.policy_version_model import PolicyVersionModel
from src.infrastructure.database.repositories.growth_code_repo import GrowthCodeRepository
from src.infrastructure.database.repositories.growth_reward_allocation_repo import (
    GrowthRewardAllocationRepository,
)
from tests.helpers.realm_auth import (
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
)
from tests.integration.test_quote_checkout_sessions import _seed_quote_context

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_growth_code_repository_persists_canonical_lifecycle_chain() -> None:
    auth_service = AuthService()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        seeded = await _seed_quote_context(sessionmaker, auth_service)
        now = datetime.now(UTC)
        owner_user_id = uuid.UUID(seeded["customer_user_id"])
        auth_realm_id = uuid.UUID(seeded["customer_realm_id"])
        storefront_id = uuid.UUID(seeded["storefront_id"])

        with sessionmaker() as db:
            redeemer = MobileUserModel(
                id=uuid.uuid4(),
                auth_realm_id=auth_realm_id,
                email="growth-redeemer@example.test",
                password_hash=await auth_service.hash_password("GrowthRedeemer123!"),
                is_active=True,
                status="active",
            )
            db.add(redeemer)
            db.commit()

            policy_version_id = db.execute(select(PolicyVersionModel.id).limit(1)).scalar_one()
            adapter = SyncSessionAdapter(db)
            codes = GrowthCodeRepository(adapter)
            rewards = GrowthRewardAllocationRepository(adapter)
            allocation_use_case = CreateGrowthRewardAllocationUseCase(adapter)

            growth_code = await codes.create_code(
                GrowthCodeModel(
                    code_hash=hash_growth_code("WB02INVITE01"),
                    code_prefix=build_growth_code_prefix("WB02INVITE01"),
                    code_type=GrowthCodeType.INVITE.value,
                    status="active",
                    issuer_type="purchase",
                    owner_user_id=owner_user_id,
                    auth_realm_id=auth_realm_id,
                    storefront_id=storefront_id,
                    starts_at=now,
                    expires_at=now + timedelta(days=60),
                    max_uses=1,
                )
            )
            invite_policy = await codes.create_invite_policy(
                InviteCodePolicyModel(
                    growth_code_id=growth_code.id,
                    friend_days=14,
                    entitlement_profile_key="invite_limited_access_v1",
                    self_redemption_block=True,
                    policy_snapshot={"source_type": "plan_invite_bundle"},
                )
            )
            issuance = await codes.create_issuance(
                GrowthCodeIssuanceModel(
                    growth_code_id=growth_code.id,
                    issuance_type="plan_invite_bundle",
                    issued_to_user_id=owner_user_id,
                    source_plan_sku="max_365",
                    source_bundle_snapshot={"friend_days": 14, "invite_count": 3},
                    reason_code="plan_invite_bundle",
                )
            )
            touchpoint = await codes.create_touchpoint(
                GrowthCodeTouchpointModel(
                    growth_code_id=growth_code.id,
                    code_type=GrowthCodeType.INVITE.value,
                    anonymous_session_id="anon-session-growth-01",
                    registered_user_id=redeemer.id,
                    storefront_id=storefront_id,
                    auth_realm_id=auth_realm_id,
                    surface="redeem_page",
                    channel="web",
                    utm_campaign="wb02",
                    converted_to_signup_at=now,
                )
            )
            signup = await codes.create_signup_attribution(
                GrowthSignupAttributionModel(
                    user_id=redeemer.id,
                    growth_code_id=growth_code.id,
                    code_type=GrowthCodeType.INVITE.value,
                    touchpoint_id=touchpoint.id,
                    attribution_source="invite_link",
                    storefront_id=storefront_id,
                    auth_realm_id=auth_realm_id,
                )
            )
            resolution_event = await codes.create_resolution_event(
                GrowthCodeResolutionEventModel(
                    growth_code_id=growth_code.id,
                    raw_code_hash=hash_growth_code("WB02INVITE01"),
                    code_type=GrowthCodeType.INVITE.value,
                    user_id=redeemer.id,
                    surface="redeem_page",
                    action_context="redeem",
                    result="accepted",
                    policy_version_id=policy_version_id,
                )
            )
            reservation = await codes.create_reservation(
                GrowthCodeReservationModel(
                    growth_code_id=growth_code.id,
                    checkout_session_id=uuid.uuid4(),
                    user_id=redeemer.id,
                    reserved_at=now,
                    expires_at=now + timedelta(minutes=30),
                    status="reserved",
                )
            )
            redemption = await codes.create_redemption(
                GrowthCodeRedemptionModel(
                    growth_code_id=growth_code.id,
                    code_type=GrowthCodeType.INVITE.value,
                    redeemer_user_id=redeemer.id,
                    beneficiary_user_id=redeemer.id,
                    policy_version_id=policy_version_id,
                    status="redeemed",
                    redeemed_at=now,
                )
            )
            allocation = await allocation_use_case.execute(
                reward_type=GrowthRewardType.BONUS_DAYS.value,
                allocation_status=GrowthRewardAllocationStatus.PENDING.value,
                beneficiary_user_id=owner_user_id,
                quantity=7,
                unit="days",
                storefront_id=storefront_id,
                source_code_id=growth_code.id,
                source_redemption_id=redemption.id,
                policy_version_id=policy_version_id,
                source_key=f"invite-reward:{redemption.id}",
                reward_payload={"trigger": "invite_to_paid_conversion"},
                hold_until=now + timedelta(days=14),
                commit=False,
            )
            redemption.reward_allocation_id = allocation.id
            await adapter.flush()
            await adapter.commit()

            stored_policy = await codes.get_invite_policy(growth_code.id)
            issuances = await codes.list_issuances(growth_code.id)
            touchpoints = await codes.list_touchpoints(growth_code.id)
            signups = await codes.list_signup_attributions(growth_code.id)
            events = await codes.list_resolution_events(growth_code_id=growth_code.id)
            reservations = await codes.list_reservations(growth_code.id)
            redemptions = await codes.list_redemptions(growth_code.id)
            reward_from_redemption = await rewards.get_by_source_redemption_id(redemption.id)
            reward_for_code = await rewards.list_for_source_code(growth_code.id)

            assert growth_code.code_type == GrowthCodeType.INVITE.value
            assert invite_policy.friend_days == 14
            assert issuance.issuance_type == "plan_invite_bundle"
            assert touchpoint.registered_user_id == redeemer.id
            assert signup.touchpoint_id == touchpoint.id
            assert resolution_event.result == "accepted"
            assert reservation.status == "reserved"
            assert redemption.reward_allocation_id == allocation.id

            assert stored_policy is not None
            assert stored_policy.entitlement_profile_key == "invite_limited_access_v1"
            assert len(issuances) == 1
            assert len(touchpoints) == 1
            assert len(signups) == 1
            assert len(events) == 1
            assert len(reservations) == 1
            assert len(redemptions) == 1
            assert reward_from_redemption is not None
            assert reward_from_redemption.id == allocation.id
            assert reward_from_redemption.allocation_status == GrowthRewardAllocationStatus.PENDING.value
            assert len(reward_for_code) == 1
            assert reward_for_code[0].id == allocation.id
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_growth_code_registry_service_creates_referral_shadow_code_and_policy() -> None:
    auth_service = AuthService()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        seeded = await _seed_quote_context(sessionmaker, auth_service)
        auth_realm_id = uuid.UUID(seeded["customer_realm_id"])

        with sessionmaker() as db:
            referral_owner = MobileUserModel(
                id=uuid.uuid4(),
                auth_realm_id=auth_realm_id,
                email="referral-owner@example.test",
                password_hash=await auth_service.hash_password("ReferralOwner123!"),
                is_active=True,
                status="active",
                referral_code="REFERWB0201",
            )
            db.add(referral_owner)
            db.commit()

            adapter = SyncSessionAdapter(db)
            registry = GrowthCodeRegistryService(adapter)
            codes = GrowthCodeRepository(adapter)

            growth_code = await registry.ensure_shadow_referral(referral_owner)
            await adapter.commit()

            stored_code = await codes.get_code_by_hash(
                hash_growth_code("REFERWB0201"),
                code_type=GrowthCodeType.REFERRAL.value,
            )
            referral_policy = await codes.get_referral_policy(growth_code.id)
            issuances = await codes.list_issuances(growth_code.id)

            assert stored_code is not None
            assert stored_code.id == growth_code.id
            assert stored_code.owner_user_id == referral_owner.id
            assert stored_code.code_type == GrowthCodeType.REFERRAL.value
            assert referral_policy is not None
            assert referral_policy.friend_discount_type == "percent"
            assert referral_policy.friend_discount_value == 10
            assert referral_policy.reward_type == "nonwithdrawable_credit"
            assert referral_policy.eligible_durations == [90, 180, 365]
            assert len(issuances) == 1
            assert issuances[0].issuance_type == "user_owned_referral"
            assert issuances[0].issued_to_user_id == referral_owner.id
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
