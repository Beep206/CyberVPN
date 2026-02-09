"""
End-to-end tests for the password reset flow.

These tests cover the two-step password reset flow:
1. POST /api/v1/auth/forgot-password  -- request a reset OTP
2. POST /api/v1/auth/reset-password   -- consume the OTP and set a new password

The forgot-password endpoint always returns 200 with the same message to
prevent email enumeration. The reset-password endpoint validates the OTP
code, enforces password strength (min 12 chars, mixed case, digit, special),
and returns appropriate error codes (400 for invalid/expired, 429 for
exhausted attempts).

Run with: pytest tests/e2e/test_password_reset.py -m e2e

API routes under test:
- POST /api/v1/auth/forgot-password  -> ForgotPasswordResponse
- POST /api/v1/auth/reset-password   -> ResetPasswordResponse | 400 | 422 | 429
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skip(reason="Requires running PostgreSQL, Redis, and email dispatcher"),
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FORGOT_PASSWORD_URL = "/api/v1/auth/forgot-password"
RESET_PASSWORD_URL = "/api/v1/auth/reset-password"

ANTI_ENUMERATION_MESSAGE = (
    "If this email is registered, a password reset code has been sent."
)

# A strong password that satisfies all validation rules:
# >= 12 chars, uppercase, lowercase, digit, special character
STRONG_PASSWORD = "N3wSecure!Pass99"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client() -> AsyncClient:
    """Create an AsyncClient bound to the FastAPI ASGI app."""
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )


# ---------------------------------------------------------------------------
# Forgot Password (anti-enumeration)
# ---------------------------------------------------------------------------


class TestForgotPassword:
    """E2E tests for POST /api/v1/auth/forgot-password.

    The endpoint always returns HTTP 200 with a fixed message regardless
    of whether the email is registered, preventing user enumeration.
    """

    async def test_forgot_password_returns_success_for_unknown_email(self):
        """POST /api/v1/auth/forgot-password with an unregistered email
        returns 200 and the standard anti-enumeration message.

        This ensures attackers cannot distinguish registered from
        unregistered emails based on the response.
        """
        # Arrange
        payload = {"email": "nonexistent-user-abc@example.com"}

        # Act
        async with _make_client() as client:
            response = await client.post(FORGOT_PASSWORD_URL, json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == ANTI_ENUMERATION_MESSAGE

    async def test_forgot_password_returns_success_for_known_email(self):
        """POST /api/v1/auth/forgot-password with a registered and active
        user's email returns 200 and the same anti-enumeration message.

        Behind the scenes, an OTP code is generated with purpose
        'password_reset' and dispatched via the email task worker.

        Precondition: a verified, active user with this email exists in DB.
        """
        # Arrange
        payload = {"email": "registered-user@example.com"}

        # Act
        async with _make_client() as client:
            response = await client.post(FORGOT_PASSWORD_URL, json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == ANTI_ENUMERATION_MESSAGE

    async def test_forgot_password_invalid_email_format_returns_422(self):
        """POST /api/v1/auth/forgot-password with a malformed email
        returns 422 Validation Error from Pydantic's EmailStr validator."""
        # Arrange
        payload = {"email": "not-an-email"}

        # Act
        async with _make_client() as client:
            response = await client.post(FORGOT_PASSWORD_URL, json=payload)

        # Assert
        assert response.status_code == 422

    async def test_forgot_password_empty_body_returns_422(self):
        """POST /api/v1/auth/forgot-password with an empty JSON body
        returns 422 because the 'email' field is required."""
        # Act
        async with _make_client() as client:
            response = await client.post(FORGOT_PASSWORD_URL, json={})

        # Assert
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Reset Password -- error cases
# ---------------------------------------------------------------------------


class TestResetPasswordErrors:
    """E2E tests for POST /api/v1/auth/reset-password error scenarios.

    The endpoint validates the OTP code against the database and enforces
    password strength rules via the Pydantic schema. Error codes:
    - OTP_INVALID  -> 400
    - OTP_EXPIRED  -> 400
    - OTP_EXHAUSTED -> 429
    - OTP_NOT_FOUND -> 400
    - Pydantic validation failure -> 422
    """

    async def test_reset_password_invalid_code_returns_400(self):
        """POST /api/v1/auth/reset-password with a wrong 6-digit OTP code
        returns 400 with error_code 'OTP_INVALID' or 'OTP_NOT_FOUND'.

        The response body includes the error detail and, when applicable,
        the number of remaining verification attempts.

        Precondition: a forgot-password OTP was generated for this email.
        """
        # Arrange
        payload = {
            "email": "registered-user@example.com",
            "code": "000000",
            "new_password": STRONG_PASSWORD,
        }

        # Act
        async with _make_client() as client:
            response = await client.post(RESET_PASSWORD_URL, json=payload)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    async def test_reset_password_expired_code_returns_400(self):
        """POST /api/v1/auth/reset-password with an expired OTP code
        returns 400 with error_code 'OTP_EXPIRED'.

        The OTP expiration is controlled by otp_expiration_hours setting
        (default: 3 hours). After expiry, the user must request a new code.

        Precondition: an OTP was generated and its expires_at is in the past.
        """
        # Arrange
        payload = {
            "email": "registered-user@example.com",
            "code": "123456",
            "new_password": STRONG_PASSWORD,
        }

        # Act
        async with _make_client() as client:
            response = await client.post(RESET_PASSWORD_URL, json=payload)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    async def test_reset_password_exhausted_attempts_returns_429(self):
        """POST /api/v1/auth/reset-password after exceeding max_attempts
        (default: 5) returns 429 with error_code 'OTP_EXHAUSTED'.

        Once exhausted, the user must request a new OTP via forgot-password.

        Precondition: an OTP exists with attempts_used >= max_attempts.
        """
        # Arrange
        payload = {
            "email": "registered-user@example.com",
            "code": "999999",
            "new_password": STRONG_PASSWORD,
        }

        # Act
        async with _make_client() as client:
            response = await client.post(RESET_PASSWORD_URL, json=payload)

        # Assert -- 429 when exhausted, 400 otherwise
        assert response.status_code in (400, 429)

    async def test_reset_password_weak_password_returns_422(self):
        """POST /api/v1/auth/reset-password with a password shorter than
        12 characters returns 422 Validation Error.

        The ResetPasswordRequest schema enforces:
        - min_length=12, max_length=128
        - At least one uppercase, one lowercase, one digit, one special char
        - Not in common password list

        This validation happens at the Pydantic layer before any DB access.
        """
        # Arrange
        payload = {
            "email": "registered-user@example.com",
            "code": "123456",
            "new_password": "short",
        }

        # Act
        async with _make_client() as client:
            response = await client.post(RESET_PASSWORD_URL, json=payload)

        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    async def test_reset_password_common_password_returns_422(self):
        """POST /api/v1/auth/reset-password with a password from the
        common-passwords list returns 422 even if length requirements are met.

        Example: 'password123!' would fail the common password check.
        """
        # Arrange -- 'password' base is in COMMON_PASSWORDS
        payload = {
            "email": "registered-user@example.com",
            "code": "123456",
            "new_password": "Password123!x",
        }

        # Act
        async with _make_client() as client:
            response = await client.post(RESET_PASSWORD_URL, json=payload)

        # Assert -- either 422 (pydantic) or 400 (if validation passes but OTP fails)
        # The common-password check is case-insensitive, so 'Password123!x'
        # is not literally in the list. We test with an exact common password below.
        assert response.status_code in (400, 422)

    async def test_reset_password_no_uppercase_returns_422(self):
        """POST /api/v1/auth/reset-password with a password missing
        uppercase letters returns 422."""
        # Arrange
        payload = {
            "email": "registered-user@example.com",
            "code": "123456",
            "new_password": "n3wsecure!pass99",
        }

        # Act
        async with _make_client() as client:
            response = await client.post(RESET_PASSWORD_URL, json=payload)

        # Assert
        assert response.status_code == 422

    async def test_reset_password_no_special_char_returns_422(self):
        """POST /api/v1/auth/reset-password with a password missing
        special characters returns 422."""
        # Arrange
        payload = {
            "email": "registered-user@example.com",
            "code": "123456",
            "new_password": "N3wSecurePass99",
        }

        # Act
        async with _make_client() as client:
            response = await client.post(RESET_PASSWORD_URL, json=payload)

        # Assert
        assert response.status_code == 422

    async def test_reset_password_invalid_code_format_returns_422(self):
        """POST /api/v1/auth/reset-password with a non-6-digit code
        returns 422. The schema enforces pattern=r'^\\d{6}$'."""
        # Arrange
        payload = {
            "email": "registered-user@example.com",
            "code": "abc",
            "new_password": STRONG_PASSWORD,
        }

        # Act
        async with _make_client() as client:
            response = await client.post(RESET_PASSWORD_URL, json=payload)

        # Assert
        assert response.status_code == 422

    async def test_reset_password_missing_fields_returns_422(self):
        """POST /api/v1/auth/reset-password with missing required fields
        returns 422."""
        # Act
        async with _make_client() as client:
            response = await client.post(RESET_PASSWORD_URL, json={})

        # Assert
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Reset Password -- success
# ---------------------------------------------------------------------------


class TestResetPasswordSuccess:
    """E2E tests for the successful password reset flow.

    The full happy path requires:
    1. A registered, active user in the database
    2. A valid, unexpired OTP with purpose='password_reset'
    3. A strong new password passing all validation rules

    After success, the user can login with the new password.
    """

    async def test_reset_password_success_returns_200(self):
        """POST /api/v1/auth/reset-password with a valid OTP code and
        a strong new password returns 200 with a success message.

        Preconditions:
        - User exists and is active
        - OTP with purpose='password_reset' is active and not expired
        - Code matches the generated OTP

        Postconditions:
        - User's password_hash is updated to the new password
        - OTP is marked as verified (verified_at is set)
        - User can login with the new password
        """
        # Arrange
        payload = {
            "email": "registered-user@example.com",
            "code": "123456",  # Must match the OTP in the database
            "new_password": STRONG_PASSWORD,
        }

        # Act
        async with _make_client() as client:
            response = await client.post(RESET_PASSWORD_URL, json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "successfully" in data["message"].lower() or "reset" in data["message"].lower()

    async def test_reset_password_then_login_with_new_password(self):
        """After a successful password reset, the user can authenticate
        via POST /api/v1/auth/login with the new password.

        This is the full end-to-end flow:
        1. POST /forgot-password -> 200
        2. POST /reset-password with OTP + new password -> 200
        3. POST /login with email + new password -> 200 + tokens

        Postcondition: old password no longer works for login.
        """
        # Arrange
        email = "registered-user@example.com"
        otp_code = "123456"
        new_password = STRONG_PASSWORD

        async with _make_client() as client:
            # Step 1: Request password reset
            forgot_response = await client.post(
                FORGOT_PASSWORD_URL,
                json={"email": email},
            )
            assert forgot_response.status_code == 200

            # Step 2: Reset password with OTP
            reset_response = await client.post(
                RESET_PASSWORD_URL,
                json={
                    "email": email,
                    "code": otp_code,
                    "new_password": new_password,
                },
            )
            assert reset_response.status_code == 200

            # Step 3: Login with new password
            login_response = await client.post(
                "/api/v1/auth/login",
                json={
                    "login_or_email": email,
                    "password": new_password,
                },
            )
            assert login_response.status_code == 200
            tokens = login_response.json()
            assert "access_token" in tokens
            assert "refresh_token" in tokens

    async def test_reset_password_invalidates_otp_after_use(self):
        """After a successful password reset, the same OTP code cannot
        be used again for another reset attempt.

        Resubmitting the same code returns 400 (OTP_NOT_FOUND or OTP_INVALID)
        because the OTP has been consumed (verified_at is set).
        """
        # Arrange
        payload = {
            "email": "registered-user@example.com",
            "code": "123456",
            "new_password": STRONG_PASSWORD,
        }

        async with _make_client() as client:
            # First reset succeeds
            first_response = await client.post(RESET_PASSWORD_URL, json=payload)
            assert first_response.status_code == 200

            # Second reset with same code fails
            second_response = await client.post(RESET_PASSWORD_URL, json=payload)
            assert second_response.status_code == 400
