"""Integration tests for codes system flows (TE-3).

Tests the current end-to-end codes workflows:
- Invite codes: admin create -> mobile user redeem
- Promo codes: admin create -> mobile validate
- Referral system: get code -> stats -> recent commissions
- Partner codes: create -> bind users -> markup -> earnings
"""

import os
import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.config.settings import settings
from src.domain.enums import InviteSource
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.invite_code_model import InviteCodeModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import (
    PartnerAccountModel,
    PartnerCodeModel,
    PartnerCommissionContractModel,
)
from src.infrastructure.database.models.promo_code_model import PromoCodeModel
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
from src.main import app
from src.presentation.dependencies.auth import get_current_mobile_user_id
from tests.conftest import TEST_DB_AVAILABLE_ENV
from tests.integration.conftest import admin_auth_headers, get_default_test_realm, issue_admin_access_token


@pytest.fixture(autouse=True)
def require_docker_backed_db() -> None:
    if os.environ.get(TEST_DB_AVAILABLE_ENV) == "0":
        pytest.skip(
            "Docker-backed test database is unavailable. Start the local stack or run targeted sqlite-backed packs."
        )


@pytest.fixture(autouse=True)
def _clear_dependency_overrides():
    yield
    app.dependency_overrides.pop(get_current_mobile_user_id, None)


@pytest.fixture(autouse=True)
def _enable_codes_stage1_features(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "promo_codes_enabled", True)
    monkeypatch.setattr(settings, "referral_enabled", True)
    monkeypatch.setattr(settings, "checkout_code_discounts_enabled", True)
    monkeypatch.setattr(settings, "partner_portal_enabled", True)
    monkeypatch.setattr(settings, "partner_codes_enabled", True)


def _override_mobile_user(user_id) -> None:
    app.dependency_overrides[get_current_mobile_user_id] = lambda: user_id


async def _create_admin_user(
    db: AsyncSession,
    *,
    role: str = "admin",
) -> AdminUserModel:
    auth_service = AuthService()
    admin_realm = await get_default_test_realm(db, "admin")
    admin = AdminUserModel(
        auth_realm_id=admin_realm.id,
        login=f"admin{secrets.token_hex(4)}",
        email=f"admin{secrets.token_hex(4)}@example.com",
        password_hash=await auth_service.hash_password("AdminP@ss123!"),
        role=role,
        is_active=True,
        is_email_verified=True,
        language="en-EN",
        timezone="UTC",
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    return admin


async def _create_mobile_user(
    db: AsyncSession,
    *,
    is_partner: bool = False,
    referral_code: str | None = None,
    partner_user_id=None,
) -> MobileUserModel:
    auth_service = AuthService()
    customer_realm = await get_default_test_realm(db, "customer")
    user = MobileUserModel(
        auth_realm_id=customer_realm.id,
        email=f"mobile{secrets.token_hex(4)}@example.com",
        password_hash=await auth_service.hash_password("MobileP@ss123!"),
        username=f"mobile{secrets.token_hex(4)}",
        referral_code=referral_code,
        partner_user_id=partner_user_id,
        is_partner=is_partner,
        is_active=True,
        status="active",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _create_plan(
    db: AsyncSession,
    *,
    name: str,
    price_usd: str,
    duration_days: int = 30,
) -> SubscriptionPlanModel:
    plan = SubscriptionPlanModel(
        name=f"{name}-{secrets.token_hex(4)}",
        tier="pro",
        plan_code="pro",
        display_name=name,
        catalog_visibility="public",
        duration_days=duration_days,
        traffic_limit_bytes=None,
        device_limit=3,
        price_usd=Decimal(price_usd),
        price_rub=None,
        sale_channels=["web"],
        traffic_policy={"policy": "standard"},
        connection_modes=["shared"],
        server_pool=["default"],
        features={},
        is_active=True,
        sort_order=0,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


class TestInviteCodeFlow:
    """Test invite code creation and redemption flow."""

    @pytest.mark.integration
    async def test_complete_invite_flow(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        admin = await _create_admin_user(db)
        admin_token = await issue_admin_access_token(db, admin)
        owner_user = await _create_mobile_user(db)
        redeemer = await _create_mobile_user(db)
        plan = await _create_plan(db, name="Premium Plan", price_usd="10.00")

        create_response = await async_client.post(
            "/api/v1/admin/invite-codes",
            json={
                "user_id": str(owner_user.id),
                "free_days": 7,
                "count": 3,
                "plan_id": str(plan.id),
            },
            headers=admin_auth_headers(admin_token),
        )

        assert create_response.status_code == 201
        invites = create_response.json()
        assert len(invites) == 3
        assert all(inv["free_days"] == 7 for inv in invites)
        invite_code = invites[0]["code"]

        _override_mobile_user(redeemer.id)
        redeem_response = await async_client.post(
            "/api/v1/invites/redeem",
            json={"code": invite_code},
        )

        assert redeem_response.status_code == 200
        redeem_data = redeem_response.json()
        assert redeem_data["code"] == invite_code
        assert redeem_data["is_used"] is True
        assert redeem_data["free_days"] == 7

        result = await db.execute(select(InviteCodeModel).where(InviteCodeModel.code == invite_code))
        invite_record = result.scalar_one()
        assert invite_record.is_used is True
        assert invite_record.used_by_user_id == redeemer.id

    @pytest.mark.integration
    async def test_redeem_expired_invite(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        owner_user = await _create_mobile_user(db)
        redeemer = await _create_mobile_user(db)

        expired_invite = InviteCodeModel(
            code=f"EXPIRED{secrets.token_hex(4).upper()}",
            owner_user_id=owner_user.id,
            free_days=7,
            source=InviteSource.ADMIN_GRANT,
            expires_at=datetime.now(UTC) - timedelta(days=1),
            is_used=False,
        )
        db.add(expired_invite)
        await db.commit()

        _override_mobile_user(redeemer.id)
        redeem_response = await async_client.post(
            "/api/v1/invites/redeem",
            json={"code": expired_invite.code},
        )

        assert redeem_response.status_code == 410
        assert "expired" in redeem_response.json()["detail"].lower()

    @pytest.mark.integration
    async def test_redeem_already_used_invite(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        owner_user = await _create_mobile_user(db)
        first_user = await _create_mobile_user(db)
        second_user = await _create_mobile_user(db)

        used_invite = InviteCodeModel(
            code=f"USED{secrets.token_hex(4).upper()}",
            owner_user_id=owner_user.id,
            free_days=7,
            source=InviteSource.ADMIN_GRANT,
            expires_at=datetime.now(UTC) + timedelta(days=30),
            is_used=True,
            used_by_user_id=first_user.id,
            used_at=datetime.now(UTC),
        )
        db.add(used_invite)
        await db.commit()

        _override_mobile_user(second_user.id)
        redeem_response = await async_client.post(
            "/api/v1/invites/redeem",
            json={"code": used_invite.code},
        )

        assert redeem_response.status_code == 409
        assert "already used" in redeem_response.json()["detail"].lower()


class TestPromoCodeFlow:
    """Test promo code creation, validation, and deactivation."""

    @pytest.mark.integration
    async def test_complete_promo_flow(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        admin = await _create_admin_user(db)
        admin_token = await issue_admin_access_token(db, admin)
        plan = await _create_plan(db, name="Premium Plan", price_usd="100.00")
        mobile_user = await _create_mobile_user(db)

        promo_code = f"SAVE20{secrets.token_hex(2).upper()}"
        create_response = await async_client.post(
            "/api/v1/admin/promo-codes",
            json={
                "code": promo_code,
                "discount_type": "percent",
                "discount_value": 20.0,
                "max_uses": 100,
                "is_single_use": False,
                "plan_ids": [str(plan.id)],
                "expires_at": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
            },
            headers=admin_auth_headers(admin_token),
        )

        assert create_response.status_code == 201
        promo_data = create_response.json()
        assert promo_data["code"] == promo_code
        assert Decimal(str(promo_data["discount_value"])) == Decimal("20.0")

        _override_mobile_user(mobile_user.id)
        validate_response = await async_client.post(
            "/api/v1/promo/validate",
            json={
                "code": promo_code,
                "plan_id": str(plan.id),
                "amount": "100.00",
            },
        )

        assert validate_response.status_code == 200
        validate_data = validate_response.json()
        assert validate_data["code"] == promo_code
        assert validate_data["promo_code_id"] == promo_data["id"]
        assert Decimal(str(validate_data["discount_amount"])) == Decimal("20.00")
        final_amount = Decimal("100.00") - Decimal(str(validate_data["discount_amount"]))
        assert final_amount == Decimal("80.00")

    @pytest.mark.integration
    async def test_promo_code_exhausted(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        plan = await _create_plan(db, name="Premium Plan", price_usd="100.00")
        mobile_user = await _create_mobile_user(db)

        exhausted_promo = PromoCodeModel(
            code=f"EXHAUSTED{secrets.token_hex(4).upper()}",
            discount_type="percent",
            discount_value=Decimal("10.0"),
            currency="USD",
            max_uses=5,
            current_uses=5,
            is_active=True,
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        db.add(exhausted_promo)
        await db.commit()

        _override_mobile_user(mobile_user.id)
        validate_response = await async_client.post(
            "/api/v1/promo/validate",
            json={
                "code": exhausted_promo.code,
                "plan_id": str(plan.id),
                "amount": "100.00",
            },
        )

        assert validate_response.status_code == 422
        assert "usage limit" in validate_response.json()["detail"].lower()

    @pytest.mark.integration
    async def test_admin_deactivate_promo(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        admin = await _create_admin_user(db)
        admin_token = await issue_admin_access_token(db, admin)

        active_promo = PromoCodeModel(
            code=f"ACTIVE{secrets.token_hex(4).upper()}",
            discount_type="fixed",
            discount_value=Decimal("5.0"),
            currency="USD",
            is_active=True,
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        db.add(active_promo)
        await db.commit()
        await db.refresh(active_promo)

        deactivate_response = await async_client.delete(
            f"/api/v1/admin/promo-codes/{active_promo.id}",
            headers=admin_auth_headers(admin_token),
        )

        assert deactivate_response.status_code == 200
        deactivate_data = deactivate_response.json()
        assert deactivate_data["is_active"] is False


class TestReferralFlow:
    """Test referral system: code generation, stats, commissions."""

    @pytest.mark.integration
    async def test_get_referral_code(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        mobile_user = await _create_mobile_user(db)

        _override_mobile_user(mobile_user.id)
        code_response = await async_client.get("/api/v1/referral/code")

        assert code_response.status_code == 200
        code_data = code_response.json()
        assert "referral_code" in code_data
        assert len(code_data["referral_code"]) > 0

    @pytest.mark.integration
    async def test_get_referral_status(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        mobile_user = await _create_mobile_user(db)

        _override_mobile_user(mobile_user.id)
        status_response = await async_client.get("/api/v1/referral/status")

        assert status_response.status_code == 200
        status_data = status_response.json()
        assert "enabled" in status_data
        assert "commission_rate" in status_data
        assert isinstance(status_data["enabled"], bool)

    @pytest.mark.integration
    async def test_get_referral_stats(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        mobile_user = await _create_mobile_user(db)

        _override_mobile_user(mobile_user.id)
        stats_response = await async_client.get("/api/v1/referral/stats")

        assert stats_response.status_code == 200
        stats_data = stats_response.json()
        assert "total_referrals" in stats_data
        assert "total_earned" in stats_data
        assert "commission_rate" in stats_data

    @pytest.mark.integration
    async def test_get_recent_commissions(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        mobile_user = await _create_mobile_user(db)

        _override_mobile_user(mobile_user.id)
        recent_response = await async_client.get("/api/v1/referral/recent")

        assert recent_response.status_code == 200
        recent_data = recent_response.json()
        assert isinstance(recent_data, list)


class TestPartnerFlow:
    """Test partner code system: creation, binding, markup, earnings."""

    @pytest.mark.integration
    async def test_create_partner_code(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        partner_user = await _create_mobile_user(db, is_partner=True)

        _override_mobile_user(partner_user.id)
        create_response = await async_client.post(
            "/api/v1/partner/codes",
            json={
                "code": f"PARTNER{secrets.token_hex(4).upper()}",
                "markup_pct": 15.0,
            },
        )

        assert create_response.status_code == 201
        code_data = create_response.json()
        assert "code" in code_data
        assert Decimal(str(code_data["markup_pct"])) == Decimal("15.0")

    @pytest.mark.integration
    async def test_regular_customer_cannot_create_partner_code(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        regular_user = await _create_mobile_user(db, is_partner=False)
        requested_code = f"CUSTOMER{secrets.token_hex(4).upper()}"

        _override_mobile_user(regular_user.id)
        create_response = await async_client.post(
            "/api/v1/partner/codes",
            json={
                "code": requested_code,
                "markup_pct": 15.0,
            },
        )

        assert create_response.status_code == 403
        stored_code = await db.scalar(select(PartnerCodeModel).where(PartnerCodeModel.code == requested_code))
        assert stored_code is None

    @pytest.mark.integration
    async def test_suspended_partner_account_cannot_create_partner_code(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        partner_user = await _create_mobile_user(db, is_partner=False)
        suspended_account = PartnerAccountModel(
            account_key=f"suspended-{secrets.token_hex(4)}",
            display_name="Suspended Partner Workspace",
            status="suspended",
            legacy_owner_user_id=partner_user.id,
        )
        db.add(suspended_account)
        await db.flush()
        partner_user.partner_account_id = suspended_account.id
        await db.commit()
        requested_code = f"SUSPENDED{secrets.token_hex(4).upper()}"

        _override_mobile_user(partner_user.id)
        create_response = await async_client.post(
            "/api/v1/partner/codes",
            json={
                "code": requested_code,
                "markup_pct": 10.0,
            },
        )

        assert create_response.status_code == 403
        stored_code = await db.scalar(select(PartnerCodeModel).where(PartnerCodeModel.code == requested_code))
        assert stored_code is None

    @pytest.mark.integration
    async def test_non_partner_with_active_workspace_cannot_create_partner_code(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        stale_user = await _create_mobile_user(db, is_partner=False)
        active_account = PartnerAccountModel(
            account_key=f"active-stale-{secrets.token_hex(4)}",
            display_name="Active Stale Partner Workspace",
            status="active",
            legacy_owner_user_id=stale_user.id,
        )
        db.add(active_account)
        await db.flush()
        stale_user.partner_account_id = active_account.id
        await db.commit()
        requested_code = f"STALEACTIVE{secrets.token_hex(3).upper()}"

        _override_mobile_user(stale_user.id)
        create_response = await async_client.post(
            "/api/v1/partner/codes",
            json={
                "code": requested_code,
                "markup_pct": 10.0,
            },
        )

        assert create_response.status_code == 403
        stored_code = await db.scalar(select(PartnerCodeModel).where(PartnerCodeModel.code == requested_code))
        assert stored_code is None
        stored_contract = await db.scalar(
            select(PartnerCommissionContractModel).where(
                PartnerCommissionContractModel.partner_user_id == stale_user.id,
            )
        )
        assert stored_contract is None

    @pytest.mark.integration
    async def test_non_partner_with_active_workspace_cannot_read_partner_surfaces(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        stale_user = await _create_mobile_user(db, is_partner=False)
        active_account = PartnerAccountModel(
            account_key=f"read-stale-{secrets.token_hex(4)}",
            display_name="Read Stale Partner Workspace",
            status="active",
            legacy_owner_user_id=stale_user.id,
        )
        db.add(active_account)
        await db.flush()
        stale_user.partner_account_id = active_account.id
        await db.commit()

        _override_mobile_user(stale_user.id)
        for path in ("/api/v1/partner/codes", "/api/v1/partner/dashboard", "/api/v1/partner/earnings"):
            response = await async_client.get(path)
            assert response.status_code == 403

    @pytest.mark.integration
    async def test_inactive_partner_workspace_cannot_read_partner_surfaces(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        partner_user = await _create_mobile_user(db, is_partner=True)
        suspended_account = PartnerAccountModel(
            account_key=f"read-suspended-{secrets.token_hex(4)}",
            display_name="Read Suspended Partner Workspace",
            status="suspended",
            legacy_owner_user_id=partner_user.id,
        )
        db.add(suspended_account)
        await db.flush()
        partner_user.partner_account_id = suspended_account.id
        await db.commit()

        _override_mobile_user(partner_user.id)
        for path in ("/api/v1/partner/codes", "/api/v1/partner/dashboard", "/api/v1/partner/earnings"):
            response = await async_client.get(path)
            assert response.status_code == 403

    @pytest.mark.integration
    async def test_partner_with_active_workspace_can_create_partner_code(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        partner_user = await _create_mobile_user(db, is_partner=True)
        active_account = PartnerAccountModel(
            account_key=f"active-partner-{secrets.token_hex(4)}",
            display_name="Active Partner Workspace",
            status="active",
            legacy_owner_user_id=partner_user.id,
        )
        db.add(active_account)
        await db.flush()
        partner_user.partner_account_id = active_account.id
        await db.commit()
        requested_code = f"ACTIVEPART{secrets.token_hex(3).upper()}"

        _override_mobile_user(partner_user.id)
        create_response = await async_client.post(
            "/api/v1/partner/codes",
            json={
                "code": requested_code,
                "markup_pct": 10.0,
            },
        )

        assert create_response.status_code == 201
        stored_code = await db.scalar(select(PartnerCodeModel).where(PartnerCodeModel.code == requested_code))
        assert stored_code is not None
        assert stored_code.partner_account_id == active_account.id
        assert stored_code.commission_contract_id is not None
        list_response = await async_client.get("/api/v1/partner/codes")
        assert list_response.status_code == 200
        assert any(item["id"] == str(stored_code.id) for item in list_response.json())
        dashboard_response = await async_client.get("/api/v1/partner/dashboard")
        assert dashboard_response.status_code == 200
        earnings_response = await async_client.get("/api/v1/partner/earnings")
        assert earnings_response.status_code == 200

    @pytest.mark.integration
    async def test_partner_markup_exceeds_limit(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        partner_user = await _create_mobile_user(db, is_partner=True)

        _override_mobile_user(partner_user.id)
        create_response = await async_client.post(
            "/api/v1/partner/codes",
            json={
                "code": f"HIGHMARKUP{secrets.token_hex(4).upper()}",
                "markup_pct": 999.0,
            },
        )

        assert create_response.status_code == 422
        assert "markup" in create_response.json()["detail"].lower()

    @pytest.mark.integration
    async def test_active_partner_can_update_markup_and_rotates_commission_contract(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        partner_user = await _create_mobile_user(db, is_partner=True)
        partner_code = PartnerCodeModel(
            code=f"UPDACTIVE{secrets.token_hex(3).upper()}",
            code_normalized=f"UPDACTIVEN{secrets.token_hex(3).upper()}",
            partner_user_id=partner_user.id,
            markup_pct=Decimal("10.0"),
            is_active=True,
            lifecycle_status="active",
            approval_status="approved",
        )
        db.add(partner_code)
        await db.commit()
        await db.refresh(partner_code)

        _override_mobile_user(partner_user.id)
        update_response = await async_client.put(
            f"/api/v1/partner/codes/{partner_code.id}",
            json={"markup_pct": 18.5},
        )

        assert update_response.status_code == 200
        assert Decimal(str(update_response.json()["markup_pct"])) == Decimal("18.5")
        await db.refresh(partner_code)
        assert partner_code.markup_pct == Decimal("18.50")
        assert partner_code.commission_contract_id is not None
        contract = await db.get(PartnerCommissionContractModel, partner_code.commission_contract_id)
        assert contract is not None
        assert contract.partner_code_id == partner_code.id
        assert contract.terms_snapshot["markup_pct"] == "18.5"

    @pytest.mark.integration
    async def test_regular_customer_cannot_update_partner_code_markup(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        regular_user = await _create_mobile_user(db, is_partner=False)
        partner_code = PartnerCodeModel(
            code=f"UPDCUSTOMER{secrets.token_hex(3).upper()}",
            code_normalized=f"UPDCUSTOMERN{secrets.token_hex(3).upper()}",
            partner_user_id=regular_user.id,
            markup_pct=Decimal("10.0"),
            is_active=True,
            lifecycle_status="active",
            approval_status="approved",
        )
        db.add(partner_code)
        await db.commit()
        await db.refresh(partner_code)

        _override_mobile_user(regular_user.id)
        update_response = await async_client.put(
            f"/api/v1/partner/codes/{partner_code.id}",
            json={"markup_pct": 18.5},
        )

        assert update_response.status_code == 403
        await db.refresh(partner_code)
        assert partner_code.markup_pct == Decimal("10.00")
        assert partner_code.commission_contract_id is None
        contracts = (
            await db.execute(
                select(PartnerCommissionContractModel).where(
                    PartnerCommissionContractModel.partner_code_id == partner_code.id,
                )
            )
        ).scalars()
        assert contracts.all() == []

    @pytest.mark.integration
    async def test_suspended_partner_account_cannot_update_partner_code_markup(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        partner_user = await _create_mobile_user(db, is_partner=True)
        suspended_account = PartnerAccountModel(
            account_key=f"update-suspended-{secrets.token_hex(4)}",
            display_name="Suspended Partner Update Workspace",
            status="suspended",
            legacy_owner_user_id=partner_user.id,
        )
        db.add(suspended_account)
        await db.flush()
        partner_user.partner_account_id = suspended_account.id
        partner_code = PartnerCodeModel(
            code=f"UPDSUSP{secrets.token_hex(3).upper()}",
            code_normalized=f"UPDSUSPN{secrets.token_hex(3).upper()}",
            partner_account_id=suspended_account.id,
            partner_user_id=partner_user.id,
            markup_pct=Decimal("10.0"),
            is_active=True,
            lifecycle_status="active",
            approval_status="approved",
        )
        db.add(partner_code)
        await db.commit()
        await db.refresh(partner_code)

        _override_mobile_user(partner_user.id)
        update_response = await async_client.put(
            f"/api/v1/partner/codes/{partner_code.id}",
            json={"markup_pct": 18.5},
        )

        assert update_response.status_code == 403
        await db.refresh(partner_code)
        assert partner_code.markup_pct == Decimal("10.00")
        assert partner_code.commission_contract_id is None

    @pytest.mark.integration
    async def test_inactive_partner_code_cannot_update_markup(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        partner_user = await _create_mobile_user(db, is_partner=True)
        partner_code = PartnerCodeModel(
            code=f"UPDINACTIVE{secrets.token_hex(3).upper()}",
            code_normalized=f"UPDINACTIVEN{secrets.token_hex(3).upper()}",
            partner_user_id=partner_user.id,
            markup_pct=Decimal("10.0"),
            is_active=False,
            lifecycle_status="revoked",
            approval_status="approved",
        )
        db.add(partner_code)
        await db.commit()
        await db.refresh(partner_code)

        _override_mobile_user(partner_user.id)
        update_response = await async_client.put(
            f"/api/v1/partner/codes/{partner_code.id}",
            json={"markup_pct": 18.5},
        )

        assert update_response.status_code == 403
        await db.refresh(partner_code)
        assert partner_code.markup_pct == Decimal("10.00")
        assert partner_code.commission_contract_id is None

    @pytest.mark.integration
    async def test_negative_partner_code_markup_update_is_rejected_before_mutation(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        partner_user = await _create_mobile_user(db, is_partner=True)
        partner_code = PartnerCodeModel(
            code=f"UPDNEG{secrets.token_hex(3).upper()}",
            code_normalized=f"UPDNEGN{secrets.token_hex(3).upper()}",
            partner_user_id=partner_user.id,
            markup_pct=Decimal("10.0"),
            is_active=True,
            lifecycle_status="active",
            approval_status="approved",
        )
        db.add(partner_code)
        await db.commit()
        await db.refresh(partner_code)

        _override_mobile_user(partner_user.id)
        update_response = await async_client.put(
            f"/api/v1/partner/codes/{partner_code.id}",
            json={"markup_pct": -1},
        )

        assert update_response.status_code == 422
        await db.refresh(partner_code)
        assert partner_code.markup_pct == Decimal("10.00")
        assert partner_code.commission_contract_id is None

    @pytest.mark.integration
    async def test_bind_user_to_partner(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        partner_user = await _create_mobile_user(db, is_partner=True)
        partner_code = PartnerCodeModel(
            code=f"BIND{secrets.token_hex(4).upper()}",
            partner_user_id=partner_user.id,
            markup_pct=Decimal("10.0"),
            is_active=True,
        )
        db.add(partner_code)
        await db.flush()

        regular_user = await _create_mobile_user(db)

        _override_mobile_user(regular_user.id)
        bind_response = await async_client.post(
            "/api/v1/partner/bind",
            json={"partner_code": partner_code.code},
        )

        assert bind_response.status_code == 200
        bind_data = bind_response.json()
        assert bind_data["status"] == "bound"

        await db.refresh(regular_user)
        assert regular_user.partner_user_id == partner_user.id

    @pytest.mark.integration
    async def test_get_partner_dashboard(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        partner_user = await _create_mobile_user(db, is_partner=True)
        code = PartnerCodeModel(
            code=f"DASH{secrets.token_hex(4).upper()}",
            partner_user_id=partner_user.id,
            markup_pct=Decimal("12.0"),
            is_active=True,
        )
        db.add(code)
        await db.commit()

        _override_mobile_user(partner_user.id)
        dashboard_response = await async_client.get("/api/v1/partner/dashboard")

        assert dashboard_response.status_code == 200
        dashboard_data = dashboard_response.json()
        assert "total_clients" in dashboard_data
        assert "total_earned" in dashboard_data
        assert "current_tier" in dashboard_data
        assert isinstance(dashboard_data["codes"], list)

    @pytest.mark.integration
    async def test_admin_promote_to_partner(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        admin = await _create_admin_user(db)
        admin_token = await issue_admin_access_token(db, admin)
        regular_user = await _create_mobile_user(db)

        promote_response = await async_client.post(
            "/api/v1/admin/partners/promote",
            json={"user_id": str(regular_user.id)},
            headers=admin_auth_headers(admin_token),
        )

        assert promote_response.status_code == 200
        promote_data = promote_response.json()
        assert promote_data["status"] == "promoted"

        await db.refresh(regular_user)
        assert regular_user.is_partner is True
