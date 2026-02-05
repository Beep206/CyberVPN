"""Resend.com email client for primary OTP delivery."""

from typing import Any

import httpx
import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)


class ResendError(Exception):
    """Resend API error."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ResendClient:
    """
    Resend.com API client for sending OTP emails.

    Used as the primary email provider for initial OTP delivery.
    Free tier: 100 emails/day, 3000 emails/month.

    Usage:
        async with ResendClient() as client:
            await client.send_otp(email="user@example.com", code="123456")
    """

    BASE_URL = "https://api.resend.com"

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.resend_api_key.get_secret_value() if settings.resend_api_key else None
        self._from_email = settings.resend_from_email
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "ResendClient":
        if not self._api_key:
            logger.warning("resend_api_key_not_configured")
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self._api_key}" if self._api_key else "",
                "Content-Type": "application/json",
            },
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def send_otp(
        self,
        email: str,
        code: str,
        locale: str = "en-EN",
        expires_in: str = "3 hours",
    ) -> dict[str, Any]:
        """
        Send OTP verification email.

        Args:
            email: Recipient email address
            code: 6-digit OTP code
            locale: Locale for email template (for i18n)
            expires_in: Expiration time string for display

        Returns:
            API response with message ID

        Raises:
            ResendError: If API call fails
        """
        if not self._client:
            raise ResendError("Client not initialized. Use async context manager.")

        if not self._api_key:
            logger.warning("resend_skipped_no_api_key", email=email)
            return {"id": "mock_no_key", "status": "skipped"}

        html_content = self._render_otp_template(code, expires_in, locale)
        subject = self._get_subject(locale)

        payload = {
            "from": self._from_email,
            "to": [email],
            "subject": subject,
            "html": html_content,
            "text": f"Your CyberVPN verification code is: {code}\n\nThis code expires in {expires_in}.",
        }

        try:
            response = await self._client.post("/emails", json=payload)

            if response.status_code >= 400:
                error_data = response.json() if response.content else {}
                raise ResendError(
                    f"Resend API error: {error_data.get('message', response.text)}",
                    status_code=response.status_code,
                )

            result = response.json()
            logger.info(
                "otp_email_sent",
                provider="resend",
                email=email,
                message_id=result.get("id"),
            )
            return result

        except httpx.RequestError as e:
            logger.error("resend_request_error", error=str(e), email=email)
            raise ResendError(f"Request failed: {e}") from e

    def _get_subject(self, locale: str) -> str:
        """Get localized email subject."""
        subjects = {
            "en-EN": "CyberVPN - Verify your email",
            "ru-RU": "CyberVPN - Подтвердите email",
            "de-DE": "CyberVPN - Bestätigen Sie Ihre E-Mail",
            "es-ES": "CyberVPN - Verifica tu correo",
            "fr-FR": "CyberVPN - Vérifiez votre email",
        }
        return subjects.get(locale, subjects["en-EN"])

    def _render_otp_template(self, code: str, expires_in: str, locale: str) -> str:
        """Render cyberpunk-styled OTP email template."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your CyberVPN Account</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0a0a0a; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0a0a0a;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background-color: #111111; border: 1px solid #00ff88; border-radius: 8px;">
                    <!-- Header -->
                    <tr>
                        <td style="padding: 30px 40px; text-align: center; border-bottom: 1px solid #00ff88;">
                            <h1 style="margin: 0; color: #00ffff; font-size: 28px; font-weight: bold; letter-spacing: 2px;">
                                CYBERVPN
                            </h1>
                            <p style="margin: 10px 0 0; color: #888888; font-size: 14px;">
                                SECURE // PRIVATE // UNTRACEABLE
                            </p>
                        </td>
                    </tr>

                    <!-- Body -->
                    <tr>
                        <td style="padding: 40px;">
                            <h2 style="color: #ffffff; font-size: 20px; margin: 0 0 20px; text-align: center;">
                                Verify Your Email Address
                            </h2>
                            <p style="color: #cccccc; font-size: 16px; line-height: 1.6; margin: 0 0 30px; text-align: center;">
                                Enter the following code to complete your registration:
                            </p>

                            <!-- OTP Code Box -->
                            <div style="background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%); border: 2px solid #00ff88; border-radius: 8px; padding: 25px; text-align: center; margin: 0 auto 30px; max-width: 300px;">
                                <div style="font-family: 'Courier New', monospace; font-size: 36px; font-weight: bold; color: #00ffff; letter-spacing: 12px; text-shadow: 0 0 20px rgba(0, 255, 255, 0.5);">
                                    {code}
                                </div>
                            </div>

                            <p style="color: #888888; font-size: 14px; text-align: center; margin: 0 0 20px;">
                                This code expires in <span style="color: #ff6b6b;">{expires_in}</span>
                            </p>

                            <p style="color: #666666; font-size: 13px; text-align: center; margin: 0;">
                                If you didn't request this code, you can safely ignore this email.
                            </p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 40px; border-top: 1px solid #333333; text-align: center;">
                            <p style="color: #555555; font-size: 12px; margin: 0;">
                                &copy; 2026 CyberVPN. All rights reserved.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
