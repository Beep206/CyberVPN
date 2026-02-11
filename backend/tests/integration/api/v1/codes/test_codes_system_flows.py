"""Integration tests for codes system flows (TE-3).

Tests the full end-to-end codes workflows:
- Invite codes: admin create → mobile user redeem
- Promo codes: admin create → mobile validate → apply discount
- Referral system: get code → referrals earn → commission tracking
- Partner codes: create → bind users → markup → earnings

Requires: AsyncClient, test database.
"""

import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.invite_code_model import InviteCodeModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import PartnerCodeModel
from src.infrastructure.database.models.promo_code_model import PromoCodeModel
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel


class TestInviteCodeFlow:
    """Test invite code creation and redemption flow."""

    @pytest.mark.integration
    async def test_complete_invite_flow(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test complete invite flow:
        1. Admin creates invite codes
        2. Mobile user redeems invite code
        3. Invite code marked as used
        4. User gets benefits (free days)
        """
        # Create admin user
        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        admin_password_hash = await auth_service.hash_password("AdminP@ss123!")

        admin = AdminUserModel(
            login=f"admin{secrets.token_hex(4)}",
            email=f"admin{secrets.token_hex(4)}@example.com",
            password_hash=admin_password_hash,
            role="admin",
            is_active=True,
            is_email_verified=True,
        )
        db.add(admin)
        await db.commit()

        # Login as admin
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": admin.email, "password": "AdminP@ss123!"},
        )
        admin_token = login_response.json()["access_token"]

        # Create subscription plan
        plan = SubscriptionPlanModel(
            name="Premium Plan",
            duration_days=30,
            price=Decimal("10.00"),
            is_active=True,
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        # Mobile user who will redeem
        mobile_user_id = uuid4()

        # Step 1: Admin creates invite codes
        create_response = await async_client.post(
            "/api/v1/admin/invite-codes",
            json={
                "user_id": str(mobile_user_id),
                "free_days": 7,
                "count": 3,
                "plan_id": str(plan.id),
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert create_response.status_code == 201
        invites = create_response.json()
        assert len(invites) == 3
        assert all(inv["free_days"] == 7 for inv in invites)
        invite_code = invites[0]["code"]

        # Step 2: Mobile user redeems invite code
        with patch("src.presentation.dependencies.auth.get_current_mobile_user_id") as mock_user_id:
            mock_user_id.return_value = mobile_user_id

            redeem_response = await async_client.post(
                "/api/v1/invites/redeem",
                json={"code": invite_code},
            )

            assert redeem_response.status_code == 200
            redeem_data = redeem_response.json()
            assert redeem_data["code"] == invite_code
            assert redeem_data["is_used"] is True
            assert redeem_data["free_days"] == 7

        # Step 3: Verify invite is marked as used in database
        result = await db.execute(
            select(InviteCodeModel).where(InviteCodeModel.code == invite_code)
        )
        invite_record = result.scalar_one()
        assert invite_record.is_used is True
        assert invite_record.used_by_user_id == mobile_user_id

    @pytest.mark.integration
    async def test_redeem_expired_invite(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test that expired invite codes cannot be redeemed.
        """
        mobile_user_id = uuid4()

        # Create expired invite code
        expired_invite = InviteCodeModel(
            code=f"EXPIRED{secrets.token_hex(4).upper()}",
            owner_user_id=uuid4(),
            free_days=7,
            expires_at=datetime.now(UTC) - timedelta(days=1),  # Expired yesterday
            is_used=False,
        )
        db.add(expired_invite)
        await db.commit()

        # Try to redeem expired code
        with patch("src.presentation.dependencies.auth.get_current_mobile_user_id") as mock_user_id:
            mock_user_id.return_value = mobile_user_id

            redeem_response = await async_client.post(
                "/api/v1/invites/redeem",
                json={"code": expired_invite.code},
            )

            assert redeem_response.status_code == 410  # HTTP 410 Gone
            assert "expired" in redeem_response.json()["detail"].lower()

    @pytest.mark.integration
    async def test_redeem_already_used_invite(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test that already-used invite codes cannot be redeemed again.
        """
        first_user_id = uuid4()
        second_user_id = uuid4()

        # Create already-used invite code
        used_invite = InviteCodeModel(
            code=f"USED{secrets.token_hex(4).upper()}",
            owner_user_id=uuid4(),
            free_days=7,
            expires_at=datetime.now(UTC) + timedelta(days=30),
            is_used=True,
            used_by_user_id=first_user_id,
            used_at=datetime.now(UTC),
        )
        db.add(used_invite)
        await db.commit()

        # Try to redeem already-used code
        with patch("src.presentation.dependencies.auth.get_current_mobile_user_id") as mock_user_id:
            mock_user_id.return_value = second_user_id

            redeem_response = await async_client.post(
                "/api/v1/invites/redeem",
                json={"code": used_invite.code},
            )

            assert redeem_response.status_code == 409  # HTTP 409 Conflict
            assert "already used" in redeem_response.json()["detail"].lower()


class TestPromoCodeFlow:
    """Test promo code creation, validation, and application."""

    @pytest.mark.integration
    async def test_complete_promo_flow(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test complete promo flow:
        1. Admin creates promo code
        2. Mobile user validates promo
        3. Discount calculated correctly
        4. Promo usage tracked
        """
        # Create admin
        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        admin_password_hash = await auth_service.hash_password("AdminP@ss123!")

        admin = AdminUserModel(
            login=f"admin{secrets.token_hex(4)}",
            email=f"admin{secrets.token_hex(4)}@example.com",
            password_hash=admin_password_hash,
            role="admin",
            is_active=True,
            is_email_verified=True,
        )
        db.add(admin)
        await db.commit()

        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": admin.email, "password": "AdminP@ss123!"},
        )
        admin_token = login_response.json()["access_token"]

        # Create plan
        plan = SubscriptionPlanModel(
            name="Premium Plan",
            duration_days=30,
            price=Decimal("100.00"),
            is_active=True,
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        mobile_user_id = uuid4()

        # Step 1: Admin creates promo code (20% discount)
        promo_code = f"SAVE20{secrets.token_hex(2).upper()}"
        create_response = await async_client.post(
            "/api/v1/admin/promo-codes",
            json={
                "code": promo_code,
                "discount_type": "percentage",
                "discount_value": "20.0",
                "max_uses": 100,
                "is_single_use": False,
                "plan_ids": [str(plan.id)],
                "expires_at": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert create_response.status_code == 201
        promo_data = create_response.json()
        assert promo_data["code"] == promo_code
        assert Decimal(promo_data["discount_value"]) == Decimal("20.0")

        # Step 2: Mobile user validates promo
        with patch("src.presentation.dependencies.auth.get_current_mobile_user_id") as mock_user_id:
            mock_user_id.return_value = mobile_user_id

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
            assert Decimal(validate_data["discount_amount"]) == Decimal("20.00")  # 20% of 100
            assert Decimal(validate_data["final_amount"]) == Decimal("80.00")

    @pytest.mark.integration
    async def test_promo_code_exhausted(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test that promo code with exhausted uses cannot be validated.
        """
        mobile_user_id = uuid4()

        # Create plan
        plan = SubscriptionPlanModel(
            name="Premium Plan",
            duration_days=30,
            price=Decimal("100.00"),
            is_active=True,
        )
        db.add(plan)
        await db.commit()

        # Create exhausted promo code
        exhausted_promo = PromoCodeModel(
            code=f"EXHAUSTED{secrets.token_hex(4).upper()}",
            discount_type="percentage",
            discount_value=Decimal("10.0"),
            max_uses=5,
            times_used=5,  # All uses exhausted
            is_active=True,
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        db.add(exhausted_promo)
        await db.commit()

        # Try to validate exhausted promo
        with patch("src.presentation.dependencies.auth.get_current_mobile_user_id") as mock_user_id:
            mock_user_id.return_value = mobile_user_id

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
        """
        Test admin can deactivate a promo code.
        """
        # Create admin
        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        admin_password_hash = await auth_service.hash_password("AdminP@ss123!")

        admin = AdminUserModel(
            login=f"admin{secrets.token_hex(4)}",
            email=f"admin{secrets.token_hex(4)}@example.com",
            password_hash=admin_password_hash,
            role="admin",
            is_active=True,
            is_email_verified=True,
        )
        db.add(admin)
        await db.commit()

        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": admin.email, "password": "AdminP@ss123!"},
        )
        admin_token = login_response.json()["access_token"]

        # Create active promo
        active_promo = PromoCodeModel(
            code=f"ACTIVE{secrets.token_hex(4).upper()}",
            discount_type="fixed",
            discount_value=Decimal("5.0"),
            is_active=True,
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        db.add(active_promo)
        await db.commit()
        await db.refresh(active_promo)

        # Admin deactivates promo
        deactivate_response = await async_client.delete(
            f"/api/v1/admin/promo-codes/{active_promo.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
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
        """
        Test user can get or generate their referral code.
        """
        mobile_user_id = uuid4()

        # Create mobile user
        mobile_user = MobileUserModel(
            id=mobile_user_id,
            email=f"mobile{secrets.token_hex(4)}@example.com",
            is_active=True,
        )
        db.add(mobile_user)
        await db.commit()

        with patch("src.presentation.dependencies.auth.get_current_mobile_user_id") as mock_user_id:
            mock_user_id.return_value = mobile_user_id

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
        """
        Test getting referral program status (enabled/disabled, commission rate).
        """
        mobile_user_id = uuid4()

        with patch("src.presentation.dependencies.auth.get_current_mobile_user_id") as mock_user_id:
            mock_user_id.return_value = mobile_user_id

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
        """
        Test getting referral statistics (total referrals, earned commissions).
        """
        mobile_user_id = uuid4()

        # Create mobile user
        mobile_user = MobileUserModel(
            id=mobile_user_id,
            email=f"referrer{secrets.token_hex(4)}@example.com",
            is_active=True,
        )
        db.add(mobile_user)
        await db.commit()

        with patch("src.presentation.dependencies.auth.get_current_mobile_user_id") as mock_user_id:
            mock_user_id.return_value = mobile_user_id

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
        """
        Test getting recent referral commissions.
        """
        mobile_user_id = uuid4()

        with patch("src.presentation.dependencies.auth.get_current_mobile_user_id") as mock_user_id:
            mock_user_id.return_value = mobile_user_id

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
        """
        Test partner can create a partner code with markup.
        """
        partner_user_id = uuid4()

        # Create partner user
        partner_user = MobileUserModel(
            id=partner_user_id,
            email=f"partner{secrets.token_hex(4)}@example.com",
            is_active=True,
            is_partner=True,
        )
        db.add(partner_user)
        await db.commit()

        with patch("src.presentation.dependencies.auth.get_current_mobile_user_id") as mock_user_id:
            mock_user_id.return_value = partner_user_id

            create_response = await async_client.post(
                "/api/v1/partner/codes",
                json={
                    "code": f"PARTNER{secrets.token_hex(4).upper()}",
                    "markup_pct": "15.0",
                },
            )

            assert create_response.status_code == 201
            code_data = create_response.json()
            assert "code" in code_data
            assert Decimal(code_data["markup_pct"]) == Decimal("15.0")

    @pytest.mark.integration
    async def test_partner_markup_exceeds_limit(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test that partner code creation fails if markup exceeds limit.
        """
        partner_user_id = uuid4()

        partner_user = MobileUserModel(
            id=partner_user_id,
            email=f"partner{secrets.token_hex(4)}@example.com",
            is_active=True,
            is_partner=True,
        )
        db.add(partner_user)
        await db.commit()

        with patch("src.presentation.dependencies.auth.get_current_mobile_user_id") as mock_user_id:
            mock_user_id.return_value = partner_user_id

            create_response = await async_client.post(
                "/api/v1/partner/codes",
                json={
                    "code": f"HIGHMARKUP{secrets.token_hex(4).upper()}",
                    "markup_pct": "999.0",  # Way too high
                },
            )

            assert create_response.status_code == 422
            assert "markup" in create_response.json()["detail"].lower()

    @pytest.mark.integration
    async def test_bind_user_to_partner(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test user can bind to a partner via partner code.
        """
        # Create partner
        partner_user_id = uuid4()
        partner_user = MobileUserModel(
            id=partner_user_id,
            email=f"partner{secrets.token_hex(4)}@example.com",
            is_active=True,
            is_partner=True,
        )
        db.add(partner_user)
        await db.flush()

        # Create partner code
        partner_code = PartnerCodeModel(
            code=f"BIND{secrets.token_hex(4).upper()}",
            partner_user_id=partner_user_id,
            markup_pct=Decimal("10.0"),
            is_active=True,
        )
        db.add(partner_code)
        await db.commit()

        # Regular user who will bind
        regular_user_id = uuid4()
        regular_user = MobileUserModel(
            id=regular_user_id,
            email=f"regular{secrets.token_hex(4)}@example.com",
            is_active=True,
        )
        db.add(regular_user)
        await db.commit()

        # User binds to partner
        with patch("src.presentation.dependencies.auth.get_current_mobile_user_id") as mock_user_id:
            mock_user_id.return_value = regular_user_id

            bind_response = await async_client.post(
                "/api/v1/partner/bind",
                json={"partner_code": partner_code.code},
            )

            assert bind_response.status_code == 200
            bind_data = bind_response.json()
            assert bind_data["status"] == "bound"

        # Verify user is bound in database
        await db.refresh(regular_user)
        assert regular_user.partner_user_id == partner_user_id

    @pytest.mark.integration
    async def test_get_partner_dashboard(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test partner can view their dashboard with stats.
        """
        partner_user_id = uuid4()

        partner_user = MobileUserModel(
            id=partner_user_id,
            email=f"partner{secrets.token_hex(4)}@example.com",
            is_active=True,
            is_partner=True,
        )
        db.add(partner_user)
        await db.commit()

        with patch("src.presentation.dependencies.auth.get_current_mobile_user_id") as mock_user_id:
            mock_user_id.return_value = partner_user_id

            dashboard_response = await async_client.get("/api/v1/partner/dashboard")

            assert dashboard_response.status_code == 200
            dashboard_data = dashboard_response.json()
            assert "total_clients" in dashboard_data
            assert "total_earned" in dashboard_data
            assert "current_tier" in dashboard_data

    @pytest.mark.integration
    async def test_admin_promote_to_partner(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test admin can promote a regular user to partner status.
        """
        # Create admin
        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        admin_password_hash = await auth_service.hash_password("AdminP@ss123!")

        admin = AdminUserModel(
            login=f"admin{secrets.token_hex(4)}",
            email=f"admin{secrets.token_hex(4)}@example.com",
            password_hash=admin_password_hash,
            role="admin",
            is_active=True,
            is_email_verified=True,
        )
        db.add(admin)
        await db.commit()

        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": admin.email, "password": "AdminP@ss123!"},
        )
        admin_token = login_response.json()["access_token"]

        # Create regular user
        regular_user_id = uuid4()
        regular_user = MobileUserModel(
            id=regular_user_id,
            email=f"promote{secrets.token_hex(4)}@example.com",
            is_active=True,
        )
        db.add(regular_user)
        await db.commit()

        # Admin promotes user to partner
        promote_response = await async_client.post(
            "/api/v1/admin/partners/promote",
            json={"user_id": str(regular_user_id)},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert promote_response.status_code == 200
        promote_data = promote_response.json()
        assert promote_data["status"] == "promoted"

        # Verify user is now a partner
        await db.refresh(regular_user)
        assert regular_user.is_partner is True
