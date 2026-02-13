"""SMTP email client for development/testing with Mailpit cluster."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import redis.asyncio as aioredis
import structlog

from src.config import get_settings
from src.services.email.templates import render_magic_link_template, render_otp_template

logger = structlog.get_logger(__name__)

# Redis key for persistent round-robin counter
SMTP_COUNTER_KEY = "smtp:round_robin:counter"


class SmtpClientError(Exception):
    """SMTP client error."""

    def __init__(self, message: str, server: str | None = None) -> None:
        super().__init__(message)
        self.server = server


class SmtpClient:
    """
    SMTP client for sending emails via Mailpit in dev/test mode.

    Supports round-robin server rotation for testing email provider failover.
    Each call to send_otp uses the next server in the rotation.
    The counter is persisted to Redis for consistency across restarts.

    Usage:
        async with SmtpClient() as client:
            await client.send_otp(email="user@example.com", code="123456")
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._servers = settings.smtp_servers
        self._from_email = settings.smtp_from_email
        self._redis_url = settings.redis_url
        self._redis: aioredis.Redis | None = None

    async def __aenter__(self) -> "SmtpClient":
        # Connect to Redis for persistent counter
        self._redis = await aioredis.from_url(self._redis_url)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    async def _get_next_server(self) -> tuple[str, int, int]:
        """
        Get next server in round-robin rotation.

        Uses Redis INCR for atomic counter increment that persists across restarts.

        Returns:
            Tuple of (host, port, index) where index is the 0-based server index.
        """
        if not self._servers:
            return ("localhost", 1025, 0)

        # Atomically increment and get the counter from Redis
        if self._redis:
            # INCR returns the new value after incrementing
            counter = await self._redis.incr(SMTP_COUNTER_KEY)
            # Subtract 1 because INCR returns the post-increment value
            # and we want to use the current value for indexing
            index = (counter - 1) % len(self._servers)
        else:
            # Fallback to first server if Redis unavailable
            index = 0
            counter = 1

        server_str = self._servers[index]

        # Parse host:port
        if ":" in server_str:
            host, port_str = server_str.split(":", 1)
            port = int(port_str)
        else:
            host = server_str
            port = 1025

        return (host, port, index)

    async def send_otp(
        self,
        email: str,
        code: str,
        locale: str = "en-EN",
        expires_in: str = "3 hours",
    ) -> dict[str, Any]:
        """
        Send OTP verification email via SMTP.

        Args:
            email: Recipient email address
            code: 6-digit OTP code
            locale: Locale for email template (for i18n)
            expires_in: Expiration time string for display

        Returns:
            Dict with server info and status

        Raises:
            SmtpClientError: If SMTP send fails
        """
        host, port, index = await self._get_next_server()
        server_id = f"mailpit-{index + 1}"

        logger.info(
            "smtp_sending_otp",
            email=email,
            server=f"{host}:{port}",
            server_id=server_id,
            server_index=index,
        )

        html_content = self._render_otp_template(code, expires_in, locale)
        subject = self._get_subject(locale)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._from_email
        msg["To"] = email
        msg["X-Mailpit-Server"] = server_id
        msg["X-OTP-Code"] = code  # For easy filtering in Mailpit UI

        # Plain text version
        text_part = MIMEText(
            f"Your CyberVPN verification code is: {code}\n\nThis code expires in {expires_in}.",
            "plain",
        )
        msg.attach(text_part)

        # HTML version
        html_part = MIMEText(html_content, "html")
        msg.attach(html_part)

        try:
            with smtplib.SMTP(host, port, timeout=10) as server:
                server.sendmail(self._from_email, [email], msg.as_string())

            logger.info(
                "smtp_otp_sent",
                email=email,
                server=f"{host}:{port}",
                server_id=server_id,
            )

            return {
                "id": f"smtp_{server_id}_{index}",
                "server": server_id,
                "host": host,
                "port": port,
                "status": "sent",
            }

        except Exception as e:
            logger.error(
                "smtp_send_failed",
                email=email,
                server=f"{host}:{port}",
                error=str(e),
            )
            raise SmtpClientError(f"SMTP send failed: {e}", server=f"{host}:{port}") from e

    async def send_magic_link(
        self,
        email: str,
        magic_link_url: str,
        locale: str = "en-EN",
        expires_in: str = "1 hour",
        otp_code: str = "",
    ) -> dict[str, Any]:
        """
        Send magic link email via SMTP for passwordless login.

        Args:
            email: Recipient email address
            magic_link_url: Full magic link URL
            locale: Locale for email template
            expires_in: Expiration time string for display
            otp_code: Optional 6-digit OTP code to display alongside the link

        Returns:
            Dict with server info and status

        Raises:
            SmtpClientError: If SMTP send fails
        """
        host, port, index = await self._get_next_server()
        server_id = f"mailpit-{index + 1}"

        logger.info(
            "smtp_sending_magic_link",
            email=email,
            server=f"{host}:{port}",
            server_id=server_id,
        )

        html_content = self._render_magic_link_template(magic_link_url, expires_in, locale, otp_code)
        subject = self._get_magic_link_subject(locale)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._from_email
        msg["To"] = email
        msg["X-Mailpit-Server"] = server_id
        msg["X-Magic-Link"] = "true"
        if otp_code:
            msg["X-OTP-Code"] = otp_code

        otp_text = f"\n\nOr enter this code: {otp_code}" if otp_code else ""
        text_part = MIMEText(
            f"Sign in to CyberVPN: {magic_link_url}{otp_text}\n\nThis link expires in {expires_in}.",
            "plain",
        )
        msg.attach(text_part)

        html_part = MIMEText(html_content, "html")
        msg.attach(html_part)

        try:
            with smtplib.SMTP(host, port, timeout=10) as server:
                server.sendmail(self._from_email, [email], msg.as_string())

            logger.info(
                "smtp_magic_link_sent",
                email=email,
                server=f"{host}:{port}",
                server_id=server_id,
            )

            return {
                "id": f"smtp_{server_id}_{index}",
                "server": server_id,
                "host": host,
                "port": port,
                "status": "sent",
            }

        except Exception as e:
            logger.error(
                "smtp_magic_link_failed",
                email=email,
                server=f"{host}:{port}",
                error=str(e),
            )
            raise SmtpClientError(f"SMTP send failed: {e}", server=f"{host}:{port}") from e

    def _get_magic_link_subject(self, locale: str) -> str:
        """Get localized magic link email subject."""
        subjects = {
            "en-EN": "[DEV] CyberVPN - Sign in with magic link",
            "ru-RU": "[DEV] CyberVPN - Вход по ссылке",
            "de-DE": "[DEV] CyberVPN - Anmeldung per Magic Link",
            "es-ES": "[DEV] CyberVPN - Iniciar sesión con enlace mágico",
            "fr-FR": "[DEV] CyberVPN - Connexion par lien magique",
        }
        return subjects.get(locale, subjects["en-EN"])

    def _render_magic_link_template(self, magic_link_url: str, expires_in: str, locale: str, otp_code: str = "") -> str:
        """Render email-compatible magic link template with DEV banner."""
        return render_magic_link_template(magic_link_url, expires_in, locale, otp_code, dev_banner=True)

    def _get_subject(self, locale: str) -> str:
        """Get localized email subject."""
        subjects = {
            "en-EN": "[DEV] CyberVPN - Verify your email",
            "ru-RU": "[DEV] CyberVPN - Подтвердите email",
            "de-DE": "[DEV] CyberVPN - Bestätigen Sie Ihre E-Mail",
            "es-ES": "[DEV] CyberVPN - Verifica tu correo",
            "fr-FR": "[DEV] CyberVPN - Vérifiez votre email",
        }
        return subjects.get(locale, subjects["en-EN"])

    def _render_otp_template(self, code: str, expires_in: str, locale: str) -> str:
        """Render email-compatible OTP template with DEV banner."""
        return render_otp_template(code, expires_in, locale, dev_banner=True)
