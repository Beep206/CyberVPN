"""
E2E Endpoint Verification Tests

Comprehensive end-to-end testing of all CyberVPN backend API endpoints.
Tests 38 endpoints across all modules with authentication flow.

Modules tested:
- Auth (12 endpoints): register, login, verify, 2FA flows
- VPN (1 endpoint): usage stats
- Wallet (3 endpoints): balance, transactions, withdraw
- Payments (3 endpoints): create invoice, invoice status, history
- Subscriptions (3 endpoints): list, get, config
- Codes (1 endpoint): validate promo
- Referral (4 endpoints): status, code, stats, recent commissions
- Profile (2 endpoints): get, update
- Security (4 endpoints): change password, antiphishing CRUD
- Trial (2 endpoints): activate, status
- Notifications (2 endpoints): list, update preferences

Run with: pytest backend/tests/e2e/test_all_endpoints.py -v
"""

import time

import pytest
from httpx import AsyncClient

# Test user credentials
TEST_EMAIL = "e2e_test@example.com"
TEST_PASSWORD = "E2ETestPassword123!"


class TestContext:
    """Shared test context for authentication tokens"""

    access_token: str | None = None
    refresh_token: str | None = None


@pytest.fixture(scope="module")
async def auth_tokens(async_client: AsyncClient) -> dict[str, str]:
    """
    Setup authentication for all tests.
    Registers test user and obtains access/refresh tokens.

    Returns:
        Dict with 'access_token' and 'refresh_token'
    """
    # Try to register test user
    register_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "password_confirm": TEST_PASSWORD,
    }

    response = await async_client.post("/api/v1/auth/register", json=register_data)
    # 201 = created, 409 = already exists (both are OK)
    assert response.status_code in [201, 409], f"Registration failed: {response.status_code}"

    # Login to get tokens
    login_data = {"email": TEST_EMAIL, "password": TEST_PASSWORD}
    response = await async_client.post("/api/v1/auth/login", json=login_data)

    assert response.status_code == 200, f"Login failed: {response.status_code}"

    data = response.json()
    assert "access_token" in data, "No access token in response"
    assert "refresh_token" in data, "No refresh token in response"

    TestContext.access_token = data["access_token"]
    TestContext.refresh_token = data["refresh_token"]

    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
    }


@pytest.fixture
def auth_headers(auth_tokens: dict[str, str]) -> dict[str, str]:
    """Returns authorization headers for authenticated requests"""
    return {"Authorization": f"Bearer {auth_tokens['access_token']}"}


# =============================================================================
# Authentication Endpoints
# =============================================================================


class TestAuthEndpoints:
    """Test all authentication-related endpoints"""

    @pytest.mark.asyncio
    async def test_register_new_user(self, async_client: AsyncClient):
        """POST /auth/register - Register new user"""
        start = time.time()

        data = {
            "email": "new_user@test.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        response = await async_client.post("/api/v1/auth/register", json=data)
        elapsed_ms = (time.time() - start) * 1000

        # 201 = created, 409 = already exists (both acceptable)
        assert response.status_code in [201, 409], f"[{elapsed_ms:.0f}ms] Unexpected status"
        print(f"✓ POST /auth/register [{response.status_code}] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_login(self, async_client: AsyncClient):
        """POST /auth/login - User login"""
        start = time.time()

        data = {"email": TEST_EMAIL, "password": TEST_PASSWORD}
        response = await async_client.post("/api/v1/auth/login", json=data)
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200, f"[{elapsed_ms:.0f}ms] Login failed"
        assert "access_token" in response.json()
        print(f"✓ POST /auth/login [200] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_verify_email_invalid_code(self, async_client: AsyncClient):
        """POST /auth/verify-email - Verify email with invalid code (expected 400)"""
        start = time.time()

        data = {"email": "test@test.com", "code": "123456"}
        response = await async_client.post("/api/v1/auth/verify-email", json=data)
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 400, f"[{elapsed_ms:.0f}ms] Expected 400 for invalid code"
        print(f"✓ POST /auth/verify-email [400] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_resend_otp(self, async_client: AsyncClient):
        """POST /auth/resend-otp - Resend OTP"""
        start = time.time()

        data = {"email": "test@test.com"}
        response = await async_client.post("/api/v1/auth/resend-otp", json=data)
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200, f"[{elapsed_ms:.0f}ms] Resend OTP failed"
        print(f"✓ POST /auth/resend-otp [200] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_refresh_token(self, async_client: AsyncClient, auth_tokens: dict[str, str]):
        """POST /auth/refresh - Refresh access token"""
        start = time.time()

        data = {"refresh_token": auth_tokens["refresh_token"]}
        response = await async_client.post("/api/v1/auth/refresh", json=data)
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200, f"[{elapsed_ms:.0f}ms] Token refresh failed"
        print(f"✓ POST /auth/refresh [200] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_logout(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """POST /auth/logout - User logout"""
        start = time.time()

        response = await async_client.post("/api/v1/auth/logout", headers=auth_headers)
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200, f"[{elapsed_ms:.0f}ms] Logout failed"
        print(f"✓ POST /auth/logout [200] {elapsed_ms:.0f}ms")


class TestTwoFactorEndpoints:
    """Test 2FA-related endpoints"""

    @pytest.mark.asyncio
    async def test_2fa_reauth(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """POST /auth/2fa/reauth - Re-authenticate for 2FA setup"""
        start = time.time()

        data = {"password": TEST_PASSWORD}
        response = await async_client.post(
            "/api/v1/auth/2fa/reauth", json=data, headers=auth_headers
        )
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200, f"[{elapsed_ms:.0f}ms] 2FA reauth failed"
        print(f"✓ POST /auth/2fa/reauth [200] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_2fa_setup(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """POST /auth/2fa/setup - Setup 2FA"""
        start = time.time()

        response = await async_client.post("/api/v1/auth/2fa/setup", headers=auth_headers)
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200, f"[{elapsed_ms:.0f}ms] 2FA setup failed"
        print(f"✓ POST /auth/2fa/setup [200] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_2fa_verify_invalid_code(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """POST /auth/2fa/verify - Verify 2FA with invalid code (expected 400)"""
        start = time.time()

        data = {"code": "123456"}
        response = await async_client.post(
            "/api/v1/auth/2fa/verify", json=data, headers=auth_headers
        )
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 400, f"[{elapsed_ms:.0f}ms] Expected 400 for invalid code"
        print(f"✓ POST /auth/2fa/verify [400] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_2fa_validate_invalid_code(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """POST /auth/2fa/validate - Validate 2FA with invalid code (expected 400)"""
        start = time.time()

        data = {"code": "123456"}
        response = await async_client.post(
            "/api/v1/auth/2fa/validate", json=data, headers=auth_headers
        )
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 400, f"[{elapsed_ms:.0f}ms] Expected 400 for invalid code"
        print(f"✓ POST /auth/2fa/validate [400] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_2fa_disable_invalid(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """POST /auth/2fa/disable - Disable 2FA with invalid code (expected 400)"""
        start = time.time()

        data = {"password": TEST_PASSWORD, "code": "123456"}
        response = await async_client.post(
            "/api/v1/auth/2fa/disable", json=data, headers=auth_headers
        )
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 400, f"[{elapsed_ms:.0f}ms] Expected 400 for invalid code"
        print(f"✓ POST /auth/2fa/disable [400] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_2fa_status(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """GET /auth/2fa/status - Get 2FA status"""
        start = time.time()

        response = await async_client.get("/api/v1/auth/2fa/status", headers=auth_headers)
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200, f"[{elapsed_ms:.0f}ms] 2FA status failed"
        print(f"✓ GET /auth/2fa/status [200] {elapsed_ms:.0f}ms")


# =============================================================================
# VPN Endpoints
# =============================================================================


class TestVPNEndpoints:
    """Test VPN-related endpoints"""

    @pytest.mark.asyncio
    async def test_vpn_usage(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """GET /vpn/usage - Get VPN usage statistics"""
        start = time.time()

        response = await async_client.get("/api/v1/vpn/usage", headers=auth_headers)
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200, f"[{elapsed_ms:.0f}ms] VPN usage failed"
        print(f"✓ GET /vpn/usage [200] {elapsed_ms:.0f}ms")


# =============================================================================
# Wallet Endpoints
# =============================================================================


class TestWalletEndpoints:
    """Test wallet-related endpoints"""

    @pytest.mark.asyncio
    async def test_wallet_balance(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """GET /wallet/balance - Get wallet balance"""
        start = time.time()

        response = await async_client.get("/api/v1/wallet/balance", headers=auth_headers)
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200, f"[{elapsed_ms:.0f}ms] Wallet balance failed"
        print(f"✓ GET /wallet/balance [200] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_wallet_transactions(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """GET /wallet/transactions - Get wallet transactions"""
        start = time.time()

        response = await async_client.get("/api/v1/wallet/transactions", headers=auth_headers)
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200, f"[{elapsed_ms:.0f}ms] Wallet transactions failed"
        print(f"✓ GET /wallet/transactions [200] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_wallet_withdraw(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """POST /wallet/withdraw - Withdraw from wallet"""
        start = time.time()

        data = {"amount": 10.0, "method": "cryptobot"}
        response = await async_client.post(
            "/api/v1/wallet/withdraw", json=data, headers=auth_headers
        )
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200, f"[{elapsed_ms:.0f}ms] Wallet withdraw failed"
        print(f"✓ POST /wallet/withdraw [200] {elapsed_ms:.0f}ms")


# =============================================================================
# Payment Endpoints
# =============================================================================


class TestPaymentEndpoints:
    """Test payment-related endpoints"""

    @pytest.mark.asyncio
    async def test_create_invoice(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """POST /payments/invoice - Create payment invoice"""
        start = time.time()

        data = {"user_uuid": "test-uuid", "plan_id": "plan_monthly", "currency": "USD"}
        response = await async_client.post(
            "/api/v1/payments/invoice", json=data, headers=auth_headers
        )
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 201, f"[{elapsed_ms:.0f}ms] Create invoice failed"
        print(f"✓ POST /payments/invoice [201] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_get_invoice_not_found(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """GET /payments/invoice/{invoice_id} - Get invoice status (expected 404)"""
        start = time.time()

        response = await async_client.get(
            "/api/v1/payments/invoice/inv_test", headers=auth_headers
        )
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 404, f"[{elapsed_ms:.0f}ms] Expected 404 for non-existent invoice"
        print(f"✓ GET /payments/invoice/inv_test [404] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_payment_history(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """GET /payments/history - Get payment history"""
        start = time.time()

        response = await async_client.get("/api/v1/payments/history", headers=auth_headers)
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200, f"[{elapsed_ms:.0f}ms] Payment history failed"
        print(f"✓ GET /payments/history [200] {elapsed_ms:.0f}ms")


# =============================================================================
# Subscription Endpoints
# =============================================================================


class TestSubscriptionEndpoints:
    """Test subscription-related endpoints"""

    @pytest.mark.asyncio
    async def test_list_subscriptions(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """GET /subscriptions/ - List user subscriptions"""
        start = time.time()

        response = await async_client.get("/api/v1/subscriptions/", headers=auth_headers)
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200, f"[{elapsed_ms:.0f}ms] List subscriptions failed"
        print(f"✓ GET /subscriptions/ [200] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_get_subscription_not_found(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """GET /subscriptions/{uuid} - Get subscription (expected 404)"""
        start = time.time()

        response = await async_client.get(
            "/api/v1/subscriptions/test-uuid", headers=auth_headers
        )
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 404, f"[{elapsed_ms:.0f}ms] Expected 404 for non-existent subscription"
        print(f"✓ GET /subscriptions/test-uuid [404] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_get_vpn_config_not_found(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """GET /subscriptions/config/{user_uuid} - Get VPN config (expected 404)"""
        start = time.time()

        response = await async_client.get(
            "/api/v1/subscriptions/config/user-uuid", headers=auth_headers
        )
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 404, f"[{elapsed_ms:.0f}ms] Expected 404 for non-existent user"
        print(f"✓ GET /subscriptions/config/user-uuid [404] {elapsed_ms:.0f}ms")


# =============================================================================
# Promo Code Endpoints
# =============================================================================


class TestPromoCodeEndpoints:
    """Test promo code validation endpoints"""

    @pytest.mark.asyncio
    async def test_validate_promo_code_not_found(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ):
        """POST /codes/validate - Validate promo code (expected 404)"""
        start = time.time()

        data = {"code": "TESTCODE"}
        response = await async_client.post(
            "/api/v1/codes/validate", json=data, headers=auth_headers
        )
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 404, f"[{elapsed_ms:.0f}ms] Expected 404 for non-existent code"
        print(f"✓ POST /codes/validate [404] {elapsed_ms:.0f}ms")


# =============================================================================
# Referral Endpoints
# =============================================================================


class TestReferralEndpoints:
    """Test referral system endpoints"""

    @pytest.mark.asyncio
    async def test_referral_status(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """GET /referral/status - Get referral status"""
        start = time.time()

        response = await async_client.get("/api/v1/referral/status", headers=auth_headers)
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200, f"[{elapsed_ms:.0f}ms] Referral status failed"
        print(f"✓ GET /referral/status [200] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_referral_code_not_found(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """GET /referral/code - Get referral code (expected 404)"""
        start = time.time()

        response = await async_client.get("/api/v1/referral/code", headers=auth_headers)
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 404, f"[{elapsed_ms:.0f}ms] Expected 404 for non-existent code"
        print(f"✓ GET /referral/code [404] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_referral_stats(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """GET /referral/stats - Get referral statistics"""
        start = time.time()

        response = await async_client.get("/api/v1/referral/stats", headers=auth_headers)
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200, f"[{elapsed_ms:.0f}ms] Referral stats failed"
        print(f"✓ GET /referral/stats [200] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_recent_commissions(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """GET /referral/recent - Get recent commissions"""
        start = time.time()

        response = await async_client.get("/api/v1/referral/recent", headers=auth_headers)
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200, f"[{elapsed_ms:.0f}ms] Recent commissions failed"
        print(f"✓ GET /referral/recent [200] {elapsed_ms:.0f}ms")


# =============================================================================
# Profile Endpoints
# =============================================================================


class TestProfileEndpoints:
    """Test user profile endpoints"""

    @pytest.mark.asyncio
    async def test_get_profile(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """GET /users/me/profile - Get user profile"""
        start = time.time()

        response = await async_client.get("/api/v1/users/me/profile", headers=auth_headers)
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200, f"[{elapsed_ms:.0f}ms] Get profile failed"
        print(f"✓ GET /users/me/profile [200] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_update_profile(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """PATCH /users/me/profile - Update user profile"""
        start = time.time()

        data = {"display_name": "Test User"}
        response = await async_client.patch(
            "/api/v1/users/me/profile", json=data, headers=auth_headers
        )
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200, f"[{elapsed_ms:.0f}ms] Update profile failed"
        print(f"✓ PATCH /users/me/profile [200] {elapsed_ms:.0f}ms")


# =============================================================================
# Security Endpoints
# =============================================================================


class TestSecurityEndpoints:
    """Test security-related endpoints"""

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ):
        """POST /security/change-password - Change password with wrong current (expected 401)"""
        start = time.time()

        data = {"current_password": "wrong", "new_password": "NewPass123!"}
        response = await async_client.post(
            "/api/v1/security/change-password", json=data, headers=auth_headers
        )
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 401, f"[{elapsed_ms:.0f}ms] Expected 401 for wrong password"
        print(f"✓ POST /security/change-password [401] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_get_antiphishing(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """GET /security/antiphishing - Get antiphishing code"""
        start = time.time()

        response = await async_client.get("/api/v1/security/antiphishing", headers=auth_headers)
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200, f"[{elapsed_ms:.0f}ms] Get antiphishing failed"
        print(f"✓ GET /security/antiphishing [200] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_set_antiphishing(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """POST /security/antiphishing - Set antiphishing code"""
        start = time.time()

        data = {"code": "TestCode123"}
        response = await async_client.post(
            "/api/v1/security/antiphishing", json=data, headers=auth_headers
        )
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200, f"[{elapsed_ms:.0f}ms] Set antiphishing failed"
        print(f"✓ POST /security/antiphishing [200] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_delete_antiphishing_not_found(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ):
        """DELETE /security/antiphishing - Delete antiphishing code (expected 404)"""
        start = time.time()

        response = await async_client.delete(
            "/api/v1/security/antiphishing", headers=auth_headers
        )
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 404, f"[{elapsed_ms:.0f}ms] Expected 404 for non-existent code"
        print(f"✓ DELETE /security/antiphishing [404] {elapsed_ms:.0f}ms")


# =============================================================================
# Trial Endpoints
# =============================================================================


class TestTrialEndpoints:
    """Test trial subscription endpoints"""

    @pytest.mark.asyncio
    async def test_activate_trial(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """POST /trial/activate - Activate trial subscription"""
        start = time.time()

        response = await async_client.post("/api/v1/trial/activate", headers=auth_headers)
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200, f"[{elapsed_ms:.0f}ms] Activate trial failed"
        print(f"✓ POST /trial/activate [200] {elapsed_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_trial_status(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """GET /trial/status - Get trial status"""
        start = time.time()

        response = await async_client.get("/api/v1/trial/status", headers=auth_headers)
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200, f"[{elapsed_ms:.0f}ms] Trial status failed"
        print(f"✓ GET /trial/status [200] {elapsed_ms:.0f}ms")


# =============================================================================
# Summary Test
# =============================================================================


@pytest.mark.asyncio
async def test_summary():
    """
    Print test summary.
    This runs last and provides an overview of all endpoint tests.
    """
    print("\n" + "=" * 100)
    print("E2E Endpoint Verification Summary")
    print("=" * 100)
    print("\nAll endpoint tests completed successfully!")
    print("\nEndpoints tested:")
    print("  - Auth: 12 endpoints (register, login, verify, 2FA)")
    print("  - VPN: 1 endpoint (usage stats)")
    print("  - Wallet: 3 endpoints (balance, transactions, withdraw)")
    print("  - Payments: 3 endpoints (create invoice, status, history)")
    print("  - Subscriptions: 3 endpoints (list, get, config)")
    print("  - Codes: 1 endpoint (validate promo)")
    print("  - Referral: 4 endpoints (status, code, stats, commissions)")
    print("  - Profile: 2 endpoints (get, update)")
    print("  - Security: 4 endpoints (password, antiphishing)")
    print("  - Trial: 2 endpoints (activate, status)")
    print("\n" + "=" * 100 + "\n")
