"""Integration tests for payment flows (BT-3).

Tests the payment and webhook endpoints:
- create crypto invoice success
- create crypto invoice with invalid plan
- get payment history
- webhook valid signature
- webhook invalid signature
- payments require auth

Requires: AsyncClient, test database, Redis.
"""

import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.payment_dto import InvoiceResponseDTO
from src.application.services.auth_service import AuthService
from src.infrastructure.database.models.admin_user_model import AdminUserModel


async def _create_admin_user(db: AsyncSession) -> tuple[str, str, str]:
    """Helper: create a user with admin role and return (user_id, password, email)."""
    password = "TestP@ssw0rd123!"
    email = f"payadmin{secrets.token_hex(4)}@example.com"
    auth_service = AuthService()
    password_hash = await auth_service.hash_password(password)

    user = AdminUserModel(
        login=f"payadmin{secrets.token_hex(4)}",
        email=email,
        password_hash=password_hash,
        role="admin",
        is_active=True,
        is_email_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return str(user.id), password, email


async def _login(async_client: AsyncClient, email: str, password: str) -> str:
    """Helper: login and return access token."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"login_or_email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


class TestCreateCryptoInvoice:
    """Test crypto invoice creation."""

    @pytest.mark.integration
    async def test_create_invoice_success(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test POST /api/v1/payments/crypto/invoice with valid plan_id -> 201 + invoice URL.

        Mocks the CryptoBot client and subscription plan lookup.
        """
        user_id, password, email = await _create_admin_user(db)
        access_token = await _login(async_client, email, password)

        mock_invoice = InvoiceResponseDTO(
            invoice_id="inv_12345",
            payment_url="https://t.me/CryptoBot?start=inv_12345",
            amount=Decimal("9.99"),
            currency="USD",
            status="pending",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

        with (
            patch(
                "src.presentation.api.v1.payments.routes.CreateCryptoInvoiceUseCase"
            ) as mock_uc_class,
            patch(
                "src.presentation.api.v1.payments.routes.SubscriptionPlanRepository"
            ),
            patch(
                "src.presentation.dependencies.services.container"
            ) as mock_container,
        ):
            # Mock the use case
            mock_uc = AsyncMock()
            mock_uc.execute.return_value = mock_invoice
            mock_uc_class.return_value = mock_uc

            # Mock the crypto client dependency
            mock_crypto = MagicMock()
            mock_container.get.return_value = lambda: mock_crypto

            response = await async_client.post(
                "/api/v1/payments/crypto/invoice",
                json={
                    "user_uuid": user_id,
                    "plan_id": "premium_monthly",
                    "currency": "USD",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["invoice_id"] == "inv_12345"
        assert "payment_url" in data
        assert data["amount"] == 9.99
        assert data["currency"] == "USD"
        assert data["status"] == "pending"

    @pytest.mark.integration
    async def test_create_invoice_invalid_plan(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test POST /api/v1/payments/crypto/invoice with non-existent plan_id -> 404.
        """
        user_id, password, email = await _create_admin_user(db)
        access_token = await _login(async_client, email, password)

        with (
            patch(
                "src.presentation.api.v1.payments.routes.CreateCryptoInvoiceUseCase"
            ) as mock_uc_class,
            patch(
                "src.presentation.api.v1.payments.routes.SubscriptionPlanRepository"
            ),
            patch(
                "src.presentation.dependencies.services.container"
            ) as mock_container,
        ):
            mock_uc = AsyncMock()
            mock_uc.execute.side_effect = ValueError("Plan not found: nonexistent_plan")
            mock_uc_class.return_value = mock_uc

            mock_crypto = MagicMock()
            mock_container.get.return_value = lambda: mock_crypto

            response = await async_client.post(
                "/api/v1/payments/crypto/invoice",
                json={
                    "user_uuid": user_id,
                    "plan_id": "nonexistent_plan",
                    "currency": "USD",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert response.status_code == 404
        assert "Plan not found" in response.json()["detail"]


class TestPaymentHistory:
    """Test payment history endpoint."""

    @pytest.mark.integration
    async def test_get_payment_history(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test GET /api/v1/payments/history with auth -> 200 + list.

        Uses a fresh test database so the payment list should be empty.
        """
        _user_id, password, email = await _create_admin_user(db)
        access_token = await _login(async_client, email, password)

        response = await async_client.get(
            "/api/v1/payments/history",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "payments" in data
        assert isinstance(data["payments"], list)


class TestCryptobotWebhook:
    """Test CryptoBot webhook handling."""

    @pytest.mark.integration
    async def test_webhook_valid_signature(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test POST /api/v1/webhooks/cryptobot with valid HMAC signature -> 200.

        Computes a valid HMAC-SHA256 signature using a test API token.
        """
        test_api_token = "test-webhook-token"
        hmac_secret = hashlib.sha256(test_api_token.encode()).digest()

        body_dict = {
            "update_type": "invoice_paid",
            "payload": {"invoice_id": "99999"},
        }
        body_bytes = json.dumps(body_dict).encode()
        valid_signature = hmac.new(hmac_secret, body_bytes, hashlib.sha256).hexdigest()

        with patch(
            "src.presentation.api.v1.webhooks.routes.settings"
        ) as mock_settings:
            mock_token = MagicMock()
            mock_token.get_secret_value.return_value = test_api_token
            mock_settings.cryptobot_token = mock_token
            mock_settings.remnawave_token = MagicMock()

            response = await async_client.post(
                "/api/v1/webhooks/cryptobot",
                content=body_bytes,
                headers={
                    "Content-Type": "application/json",
                    "crypto-pay-api-signature": valid_signature,
                },
            )

        assert response.status_code == 200
        data = response.json()
        # Valid signature, invoice_paid event processed (payment may not exist in test DB)
        assert data["status"] in ("processed", "already_processed")

    @pytest.mark.integration
    async def test_webhook_invalid_signature(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test POST /api/v1/webhooks/cryptobot with bad signature -> 200 with invalid_signature status.

        The webhook handler logs invalid signatures but returns 200 to prevent retries.
        """
        test_api_token = "test-webhook-token"

        body_dict = {
            "update_type": "invoice_paid",
            "payload": {"invoice_id": "99999"},
        }
        body_bytes = json.dumps(body_dict).encode()
        invalid_signature = "deadbeef" * 8  # Wrong signature

        with patch(
            "src.presentation.api.v1.webhooks.routes.settings"
        ) as mock_settings:
            mock_token = MagicMock()
            mock_token.get_secret_value.return_value = test_api_token
            mock_settings.cryptobot_token = mock_token
            mock_settings.remnawave_token = MagicMock()

            response = await async_client.post(
                "/api/v1/webhooks/cryptobot",
                content=body_bytes,
                headers={
                    "Content-Type": "application/json",
                    "crypto-pay-api-signature": invalid_signature,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "invalid_signature"


class TestPaymentAuth:
    """Test that payment endpoints require authentication."""

    @pytest.mark.integration
    async def test_payments_require_auth(
        self,
        async_client: AsyncClient,
    ):
        """
        Test that creating an invoice without auth -> 401/403.
        """
        response = await async_client.post(
            "/api/v1/payments/crypto/invoice",
            json={
                "user_uuid": str(uuid4()),
                "plan_id": "premium_monthly",
                "currency": "USD",
            },
        )
        assert response.status_code in (401, 403)
