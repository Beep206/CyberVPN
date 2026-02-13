"""Resend.com email client for primary OTP delivery."""

from typing import Any

import httpx
import structlog

from src.config import get_settings
from src.services.email.templates import render_magic_link_template, render_otp_template

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

    async def send_magic_link(
        self,
        email: str,
        magic_link_url: str,
        locale: str = "en-EN",
        expires_in: str = "1 hour",
        otp_code: str = "",
    ) -> dict[str, Any]:
        """
        Send magic link email for passwordless login.

        Args:
            email: Recipient email address
            magic_link_url: Full magic link URL
            locale: Locale for email template
            expires_in: Expiration time string for display
            otp_code: Optional 6-digit OTP code to display alongside the link

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

        html_content = self._render_magic_link_template(magic_link_url, expires_in, locale, otp_code)
        subject = self._get_magic_link_subject(locale)

        otp_text = f"\n\nOr enter this code: {otp_code}" if otp_code else ""
        payload = {
            "from": self._from_email,
            "to": [email],
            "subject": subject,
            "html": html_content,
            "text": f"Sign in to CyberVPN: {magic_link_url}{otp_text}\n\nThis link expires in {expires_in}.",
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
                "magic_link_email_sent",
                provider="resend",
                email=email,
                message_id=result.get("id"),
            )
            return result

        except httpx.RequestError as e:
            logger.error("resend_request_error", error=str(e), email=email)
            raise ResendError(f"Request failed: {e}") from e

    def _get_magic_link_subject(self, locale: str) -> str:
        """Get localized magic link email subject."""
        subjects = {
            "en-EN": "CyberVPN - Sign in with magic link",
            "ru-RU": "CyberVPN - Вход по ссылке",
            "de-DE": "CyberVPN - Anmeldung per Magic Link",
            "es-ES": "CyberVPN - Iniciar sesión con enlace mágico",
            "fr-FR": "CyberVPN - Connexion par lien magique",
        }
        return subjects.get(locale, subjects["en-EN"])

    def _render_magic_link_template(self, magic_link_url: str, expires_in: str, locale: str, otp_code: str = "") -> str:
        """Render email-compatible magic link template."""
        return render_magic_link_template(magic_link_url, expires_in, locale, otp_code)

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
        """Render email-compatible OTP template."""
        return render_otp_template(code, expires_in, locale)
