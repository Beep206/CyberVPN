"""End-to-end smoke coverage for the current public API surface.

This module intentionally follows the live contracts that exist today:
- admin/web auth lives under ``/api/v1/auth``
- mobile auth-protected endpoints use mobile JWTs
- 2FA lives under ``/api/v1/2fa``
- wallet/referral/promo mobile endpoints require mobile-user tokens

The goal here is broad smoke coverage, not deep business-rule verification.
"""

import secrets
import time
import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.jwt_revocation_service import JWTRevocationService
from src.config.settings import settings
from src.infrastructure.cache.redis_client import get_redis_client
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.wallet_model import WalletModel

ADMIN_PASSWORD = "FixtureAdminPassword123!"
MOBILE_PASSWORD = "MobileFixturePassword123!"


def _elapsed_ms(started_at: float) -> float:
    return (time.perf_counter() - started_at) * 1000


async def _issue_access_token(subject: str, role: str) -> str:
    auth_service = AuthService()
    access_token, jti, expires_at = auth_service.create_access_token(subject=subject, role=role)
    redis_client = await get_redis_client()
    try:
        await JWTRevocationService(redis_client).register_token(
            jti=jti,
            user_id=subject,
            expires_at=expires_at,
        )
    finally:
        await redis_client.aclose()
    return access_token


async def _create_admin_user(
    db: AsyncSession,
    *,
    role: str = "super_admin",
    verified: bool = True,
    totp_enabled: bool = False,
    totp_secret: str | None = None,
) -> AdminUserModel:
    auth_service = AuthService()
    suffix = secrets.token_hex(4)
    user = AdminUserModel(
        id=uuid.uuid4(),
        login=f"e2e-admin-{suffix}",
        email=f"e2e-admin-{suffix}@example.com",
        password_hash=await auth_service.hash_password(ADMIN_PASSWORD),
        role=role,
        is_active=True,
        is_email_verified=verified,
        totp_enabled=totp_enabled,
        totp_secret=totp_secret,
        language="en-EN",
        timezone="UTC",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _create_mobile_user(
    db: AsyncSession,
    *,
    balance: str = "100.00",
) -> tuple[MobileUserModel, WalletModel]:
    auth_service = AuthService()
    suffix = secrets.token_hex(4)
    user = MobileUserModel(
        id=uuid.uuid4(),
        email=f"e2e-mobile-{suffix}@example.com",
        password_hash=await auth_service.hash_password(MOBILE_PASSWORD),
        username=f"e2e-mobile-{suffix}",
        is_active=True,
        status="active",
    )
    db.add(user)
    await db.flush()

    wallet = WalletModel(
        user_id=user.id,
        balance=Decimal(balance),
        currency="USD",
        frozen=Decimal("0.00"),
    )
    db.add(wallet)
    await db.commit()
    await db.refresh(user)
    await db.refresh(wallet)
    return user, wallet


@pytest_asyncio.fixture
async def admin_api_session(
    async_client: AsyncClient,
    db: AsyncSession,
) -> dict[str, str]:
    """Create a real admin user and authenticate through the HTTP login route."""
    user = await _create_admin_user(db)

    response = await async_client.post(
        "/api/v1/auth/login",
        json={"login_or_email": user.email, "password": ADMIN_PASSWORD},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["requires_2fa"] is False

    return {
        "user_id": str(user.id),
        "email": user.email or "",
        "access_token": payload["access_token"],
        "refresh_token": payload["refresh_token"],
    }


@pytest_asyncio.fixture
async def admin_auth_context(db: AsyncSession) -> dict[str, str]:
    """Create an authenticated admin context without depending on login route state."""
    user = await _create_admin_user(db)
    access_token = await _issue_access_token(str(user.id), "super_admin")
    return {
        "user_id": str(user.id),
        "email": user.email or "",
        "access_token": access_token,
        "password": ADMIN_PASSWORD,
    }


@pytest_asyncio.fixture
async def admin_2fa_context(db: AsyncSession) -> dict[str, str]:
    """Create an admin with 2FA already enabled and issue a direct access token."""
    totp_secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    user = await _create_admin_user(
        db,
        totp_enabled=True,
        totp_secret=totp_secret,
    )
    access_token = await _issue_access_token(str(user.id), "super_admin")
    return {
        "user_id": str(user.id),
        "access_token": access_token,
        "password": ADMIN_PASSWORD,
        "totp_secret": totp_secret,
    }


@pytest_asyncio.fixture
async def unverified_admin_context(db: AsyncSession) -> dict[str, str]:
    """Create an unverified admin account for OTP resend / verify flows."""
    user = await _create_admin_user(db, verified=False)
    return {"email": user.email or ""}


@pytest_asyncio.fixture
async def mobile_auth_context(db: AsyncSession) -> dict[str, str]:
    """Create a mobile user with wallet balance and issue a mobile access token."""
    user, _wallet = await _create_mobile_user(db)
    access_token = await _issue_access_token(str(user.id), "user")
    return {
        "user_id": str(user.id),
        "access_token": access_token,
    }


@pytest.fixture
def admin_headers(admin_auth_context: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_auth_context['access_token']}"}


@pytest.fixture
def admin_2fa_headers(admin_2fa_context: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_2fa_context['access_token']}"}


@pytest.fixture
def mobile_headers(mobile_auth_context: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {mobile_auth_context['access_token']}"}


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_register_new_user(self, async_client: AsyncClient):
        started_at = time.perf_counter()
        suffix = secrets.token_hex(4)
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "login": f"register_{suffix}",
                "email": f"register_{suffix}@example.com",
                "password": "RegisterPassword123!",
                "tos_accepted": True,
                "locale": "en-EN",
            },
        )
        elapsed_ms = _elapsed_ms(started_at)

        if not settings.registration_enabled or settings.registration_invite_required:
            assert response.status_code == 403, f"[{elapsed_ms:.0f}ms] Registration policy mismatch"
        else:
            assert response.status_code == 201, f"[{elapsed_ms:.0f}ms] Registration failed"

    @pytest.mark.asyncio
    async def test_login(self, async_client: AsyncClient, admin_api_session: dict[str, str]):
        started_at = time.perf_counter()
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": admin_api_session["email"], "password": ADMIN_PASSWORD},
        )
        elapsed_ms = _elapsed_ms(started_at)

        assert response.status_code == 200, f"[{elapsed_ms:.0f}ms] Login failed"
        assert "access_token" in response.json()
        assert "refresh_token" in response.json()

    @pytest.mark.asyncio
    async def test_verify_email_invalid_code(
        self,
        async_client: AsyncClient,
        unverified_admin_context: dict[str, str],
    ):
        response = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"email": unverified_admin_context["email"], "code": "123456"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_resend_otp(
        self,
        async_client: AsyncClient,
        unverified_admin_context: dict[str, str],
    ):
        response = await async_client.post(
            "/api/v1/auth/resend-otp",
            json={"email": unverified_admin_context["email"], "locale": "en-EN"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_refresh_token(self, async_client: AsyncClient, admin_api_session: dict[str, str]):
        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": admin_api_session["refresh_token"]},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    @pytest.mark.asyncio
    async def test_logout(self, async_client: AsyncClient, admin_api_session: dict[str, str]):
        response = await async_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": admin_api_session["refresh_token"]},
        )
        assert response.status_code == 204


class TestTwoFactorEndpoints:
    @pytest.mark.asyncio
    async def test_2fa_reauth(self, async_client: AsyncClient, admin_headers: dict[str, str]):
        response = await async_client.post(
            "/api/v1/2fa/reauth",
            json={"password": ADMIN_PASSWORD},
            headers=admin_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_2fa_setup(self, async_client: AsyncClient, admin_headers: dict[str, str]):
        reauth = await async_client.post(
            "/api/v1/2fa/reauth",
            json={"password": ADMIN_PASSWORD},
            headers=admin_headers,
        )
        assert reauth.status_code == 200

        setup = await async_client.post("/api/v1/2fa/setup", headers=admin_headers)
        assert setup.status_code == 200
        payload = setup.json()
        assert "secret" in payload
        assert "qr_uri" in payload

    @pytest.mark.asyncio
    async def test_2fa_verify_invalid_code(self, async_client: AsyncClient, admin_headers: dict[str, str]):
        reauth = await async_client.post(
            "/api/v1/2fa/reauth",
            json={"password": ADMIN_PASSWORD},
            headers=admin_headers,
        )
        assert reauth.status_code == 200

        setup = await async_client.post("/api/v1/2fa/setup", headers=admin_headers)
        assert setup.status_code == 200

        verify = await async_client.post(
            "/api/v1/2fa/verify",
            json={"code": "000000"},
            headers=admin_headers,
        )
        assert verify.status_code == 400

    @pytest.mark.asyncio
    async def test_2fa_validate_invalid_code(
        self,
        async_client: AsyncClient,
        admin_2fa_headers: dict[str, str],
    ):
        response = await async_client.post(
            "/api/v1/2fa/validate",
            json={"code": "000000"},
            headers=admin_2fa_headers,
        )
        assert response.status_code == 200
        assert response.json()["valid"] is False

    @pytest.mark.asyncio
    async def test_2fa_disable_invalid(
        self,
        async_client: AsyncClient,
        admin_2fa_context: dict[str, str],
        admin_2fa_headers: dict[str, str],
    ):
        response = await async_client.post(
            "/api/v1/2fa/disable",
            json={"password": admin_2fa_context["password"], "code": "000000"},
            headers=admin_2fa_headers,
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_2fa_status(
        self,
        async_client: AsyncClient,
        admin_2fa_headers: dict[str, str],
    ):
        response = await async_client.get("/api/v1/2fa/status", headers=admin_2fa_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "enabled"


class TestVPNEndpoints:
    @pytest.mark.asyncio
    async def test_vpn_usage(self, async_client: AsyncClient, admin_headers: dict[str, str]):
        response = await async_client.get("/api/v1/users/me/usage", headers=admin_headers)
        assert response.status_code == 200


class TestWalletEndpoints:
    @pytest.mark.asyncio
    async def test_wallet_balance(self, async_client: AsyncClient, mobile_headers: dict[str, str]):
        response = await async_client.get("/api/v1/wallet/balance", headers=mobile_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_wallet_transactions(self, async_client: AsyncClient, mobile_headers: dict[str, str]):
        response = await async_client.get("/api/v1/wallet/transactions", headers=mobile_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_wallet_withdraw(self, async_client: AsyncClient, mobile_headers: dict[str, str]):
        response = await async_client.post(
            "/api/v1/wallet/withdraw",
            json={"amount": "50.00", "method": "cryptobot"},
            headers=mobile_headers,
        )
        assert response.status_code == 201


class TestPaymentEndpoints:
    @pytest.mark.asyncio
    async def test_create_invoice_invalid_plan(
        self,
        async_client: AsyncClient,
        admin_auth_context: dict[str, str],
        admin_headers: dict[str, str],
    ):
        response = await async_client.post(
            "/api/v1/payments/crypto/invoice",
            json={
                "user_uuid": admin_auth_context["user_id"],
                "plan_id": "missing-plan",
                "currency": "USD",
            },
            headers=admin_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_payment_history(self, async_client: AsyncClient, admin_headers: dict[str, str]):
        response = await async_client.get("/api/v1/payments/history", headers=admin_headers)
        assert response.status_code == 200
        assert "payments" in response.json()


class TestSubscriptionEndpoints:
    @pytest.mark.asyncio
    async def test_list_subscriptions(self, async_client: AsyncClient, admin_headers: dict[str, str]):
        response = await async_client.get("/api/v1/subscriptions/", headers=admin_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_vpn_config_not_found(self, async_client: AsyncClient, admin_headers: dict[str, str]):
        response = await async_client.get(
            f"/api/v1/subscriptions/config/{uuid.uuid4()}",
            headers=admin_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_subscription(self, async_client: AsyncClient, admin_headers: dict[str, str]):
        response = await async_client.post("/api/v1/subscriptions/cancel", headers=admin_headers)
        assert response.status_code == 404


class TestPromoCodeEndpoints:
    @pytest.mark.asyncio
    async def test_validate_promo_code_not_found(
        self,
        async_client: AsyncClient,
        mobile_headers: dict[str, str],
    ):
        response = await async_client.post(
            "/api/v1/promo/validate",
            json={"code": "MISSING-PROMO"},
            headers=mobile_headers,
        )
        assert response.status_code == 404


class TestReferralEndpoints:
    @pytest.mark.asyncio
    async def test_referral_status(self, async_client: AsyncClient, mobile_headers: dict[str, str]):
        response = await async_client.get("/api/v1/referral/status", headers=mobile_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_referral_code(self, async_client: AsyncClient, mobile_headers: dict[str, str]):
        response = await async_client.get("/api/v1/referral/code", headers=mobile_headers)
        assert response.status_code == 200
        assert "referral_code" in response.json()

    @pytest.mark.asyncio
    async def test_referral_stats(self, async_client: AsyncClient, mobile_headers: dict[str, str]):
        response = await async_client.get("/api/v1/referral/stats", headers=mobile_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_recent_commissions(self, async_client: AsyncClient, mobile_headers: dict[str, str]):
        response = await async_client.get("/api/v1/referral/recent", headers=mobile_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestProfileEndpoints:
    @pytest.mark.asyncio
    async def test_get_profile(self, async_client: AsyncClient, admin_headers: dict[str, str]):
        response = await async_client.get("/api/v1/users/me/profile", headers=admin_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_profile(self, async_client: AsyncClient, admin_headers: dict[str, str]):
        response = await async_client.patch(
            "/api/v1/users/me/profile",
            json={"display_name": "E2E Admin"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["display_name"] == "E2E Admin"


class TestSecurityEndpoints:
    @pytest.mark.asyncio
    async def test_change_password_wrong_current(
        self,
        async_client: AsyncClient,
        admin_headers: dict[str, str],
    ):
        response = await async_client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "wrong-password", "new_password": "NewPassword123!"},
            headers=admin_headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_antiphishing(self, async_client: AsyncClient, admin_headers: dict[str, str]):
        response = await async_client.get("/api/v1/security/antiphishing", headers=admin_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_set_antiphishing(self, async_client: AsyncClient, admin_headers: dict[str, str]):
        response = await async_client.post(
            "/api/v1/security/antiphishing",
            json={"code": "E2ECode123"},
            headers=admin_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_antiphishing(self, async_client: AsyncClient, admin_headers: dict[str, str]):
        response = await async_client.delete("/api/v1/security/antiphishing", headers=admin_headers)
        assert response.status_code == 200


class TestTrialEndpoints:
    @pytest.mark.asyncio
    async def test_activate_trial(self, async_client: AsyncClient, mobile_headers: dict[str, str]):
        response = await async_client.post("/api/v1/trial/activate", headers=mobile_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_trial_status(self, async_client: AsyncClient, mobile_headers: dict[str, str]):
        response = await async_client.get("/api/v1/trial/status", headers=mobile_headers)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_summary():
    """Human-readable summary marker."""
    assert True
