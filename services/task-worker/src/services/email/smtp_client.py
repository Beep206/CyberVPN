"""SMTP email client for development/testing with Mailpit cluster."""

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr
from typing import Any

import redis.asyncio as aioredis
import structlog

from src.config import get_settings
from src.services.email.privacy import recipient_log_fields
from src.services.email.templates import (
    render_growth_notification_template,
    render_magic_link_template,
    render_otp_template,
)

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
    SMTP client for sending emails via Mailpit in dev/test mode or the
    configured cyber-vpn.net SMTP primary route outside dev mode.

    Supports round-robin server rotation for testing email provider failover.
    Each call to send_otp uses the next server in the rotation.
    The counter is persisted to Redis for consistency across restarts.

    Usage:
        async with SmtpClient() as client:
            await client.send_otp(email="user@example.com", code="123456")
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._email_dev_mode = settings.email_dev_mode
        self._servers = settings.smtp_servers
        self._host = settings.smtp_host
        self._port = int(settings.smtp_port)
        self._starttls = False if self._email_dev_mode else bool(settings.smtp_starttls)
        self._use_ssl = False if self._email_dev_mode else bool(settings.smtp_use_ssl)
        self._auth_username = "" if self._email_dev_mode else settings.smtp_auth_username.strip()
        self._auth_password = ""
        if not self._email_dev_mode and settings.smtp_auth_password is not None:
            self._auth_password = settings.smtp_auth_password.get_secret_value()
        self._from_email = settings.smtp_from_email if self._email_dev_mode else settings.smtp_system_from_email
        self._redis_url = settings.redis_url
        self._redis: aioredis.Redis | None = None

    async def __aenter__(self) -> "SmtpClient":
        # Connect to Redis only for dev Mailpit round-robin state.
        if self._email_dev_mode:
            self._redis = aioredis.from_url(self._redis_url)
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
        if not self._email_dev_mode:
            return (self._host, self._port, 0)

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

    def _server_id(self, index: int) -> str:
        if self._email_dev_mode:
            return f"mailpit-{index + 1}"
        return "smtp-primary"

    def _envelope_sender(self) -> str:
        parsed_sender = parseaddr(self._from_email)[1]
        return parsed_sender or self._from_email

    def _send_message(self, *, host: str, port: int, recipient: str, message: MIMEMultipart) -> None:
        context = ssl.create_default_context()
        smtp_cls = smtplib.SMTP_SSL if self._use_ssl else smtplib.SMTP
        smtp_kwargs: dict[str, Any] = {"timeout": 10}
        if self._use_ssl:
            smtp_kwargs["context"] = context

        with smtp_cls(host, port, **smtp_kwargs) as server:
            if self._starttls and not self._use_ssl:
                server.starttls(context=context)
                server.ehlo()
            if self._auth_username or self._auth_password:
                server.login(self._auth_username, self._auth_password)
            server.sendmail(self._envelope_sender(), [recipient], message.as_string())

    async def send_otp(
        self,
        email: str,
        code: str,
        locale: str = "en-EN",
        expires_in: str = "3 hours",
        activation_url: str = "",
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
        server_id = self._server_id(index)
        recipient_fields = recipient_log_fields(email)

        logger.info(
            "smtp_sending_otp",
            server=f"{host}:{port}",
            server_id=server_id,
            server_index=index,
            **recipient_fields,
        )

        html_content = self._render_otp_template(code, expires_in, locale, activation_url=activation_url)
        subject = self._get_subject(locale)
        activation_text = f"\n\nVerify account: {activation_url}" if activation_url else ""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._from_email
        msg["To"] = email
        msg["X-Mailpit-Server"] = server_id

        # Plain text version
        text_part = MIMEText(
            f"Your CyberVPN verification code is: {code}{activation_text}\n\nThis code expires in {expires_in}.",
            "plain",
        )
        msg.attach(text_part)

        # HTML version
        html_part = MIMEText(html_content, "html")
        msg.attach(html_part)

        try:
            self._send_message(host=host, port=port, recipient=email, message=msg)

            logger.info(
                "smtp_otp_sent",
                server=f"{host}:{port}",
                server_id=server_id,
                **recipient_fields,
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
                server=f"{host}:{port}",
                error=str(e),
                **recipient_fields,
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
        server_id = self._server_id(index)
        recipient_fields = recipient_log_fields(email)

        logger.info(
            "smtp_sending_magic_link",
            server=f"{host}:{port}",
            server_id=server_id,
            **recipient_fields,
        )

        html_content = self._render_magic_link_template(magic_link_url, expires_in, locale, otp_code)
        subject = self._get_magic_link_subject(locale)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._from_email
        msg["To"] = email
        msg["X-Mailpit-Server"] = server_id
        msg["X-Magic-Link"] = "true"

        otp_text = f"\n\nOr enter this code: {otp_code}" if otp_code else ""
        text_part = MIMEText(
            f"Sign in to CyberVPN: {magic_link_url}{otp_text}\n\nThis link expires in {expires_in}.",
            "plain",
        )
        msg.attach(text_part)

        html_part = MIMEText(html_content, "html")
        msg.attach(html_part)

        try:
            self._send_message(host=host, port=port, recipient=email, message=msg)

            logger.info(
                "smtp_magic_link_sent",
                server=f"{host}:{port}",
                server_id=server_id,
                **recipient_fields,
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
                server=f"{host}:{port}",
                error=str(e),
                **recipient_fields,
            )
            raise SmtpClientError(f"SMTP send failed: {e}", server=f"{host}:{port}") from e

    async def send_password_reset(
        self,
        email: str,
        code: str,
        locale: str = "en-EN",
        expires_in: str = "3 hours",
    ) -> dict[str, Any]:
        """Send password reset OTP email via SMTP."""
        host, port, index = await self._get_next_server()
        server_id = self._server_id(index)
        recipient_fields = recipient_log_fields(email)

        logger.info(
            "smtp_sending_password_reset",
            server=f"{host}:{port}",
            server_id=server_id,
            **recipient_fields,
        )

        html_content = self._render_password_reset_template(code, expires_in, locale)
        subject = self._get_password_reset_subject(locale)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._from_email
        msg["To"] = email
        msg["X-Mailpit-Server"] = server_id
        msg["X-Password-Reset"] = "true"

        text_part = MIMEText(
            f"Use this CyberVPN password reset code: {code}\n\nThis code expires in {expires_in}.",
            "plain",
        )
        msg.attach(text_part)
        msg.attach(MIMEText(html_content, "html"))

        try:
            self._send_message(host=host, port=port, recipient=email, message=msg)

            logger.info(
                "smtp_password_reset_sent",
                server=f"{host}:{port}",
                server_id=server_id,
                **recipient_fields,
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
                "smtp_password_reset_failed",
                server=f"{host}:{port}",
                error=str(e),
                **recipient_fields,
            )
            raise SmtpClientError(f"SMTP send failed: {e}", server=f"{host}:{port}") from e

    async def send_growth_notification(
        self,
        *,
        email: str,
        subject: str | None = None,
        title: str,
        message: str,
        locale: str = "en-EN",
        cta_url: str = "",
        notes: list[str] | None = None,
    ) -> dict[str, Any]:
        """Send a growth-notification email via SMTP."""
        host, port, index = await self._get_next_server()
        server_id = self._server_id(index)
        recipient_fields = recipient_log_fields(email)

        logger.info(
            "smtp_sending_growth_notification",
            server=f"{host}:{port}",
            server_id=server_id,
            **recipient_fields,
        )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject or self._get_growth_notification_subject(title)
        msg["From"] = self._from_email
        msg["To"] = email
        msg["X-Mailpit-Server"] = server_id
        msg["X-Growth-Notification"] = "true"

        msg.attach(
            MIMEText(
                self._render_growth_notification_text(title, message, cta_url, notes),
                "plain",
            )
        )
        msg.attach(
            MIMEText(
                render_growth_notification_template(
                    title=title,
                    message=message,
                    locale=locale,
                    cta_url=cta_url,
                    notes=notes,
                    dev_banner=True,
                ),
                "html",
            )
        )

        try:
            self._send_message(host=host, port=port, recipient=email, message=msg)

            logger.info(
                "smtp_growth_notification_sent",
                server=f"{host}:{port}",
                server_id=server_id,
                **recipient_fields,
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
                "smtp_growth_notification_failed",
                server=f"{host}:{port}",
                error=str(e),
                **recipient_fields,
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

    def _render_otp_template(self, code: str, expires_in: str, locale: str, *, activation_url: str = "") -> str:
        """Render email-compatible OTP template with DEV banner."""
        return render_otp_template(code, expires_in, locale, activation_url=activation_url, dev_banner=True)

    def _get_password_reset_subject(self, locale: str) -> str:
        """Get localized password reset subject."""
        subjects = {
            "en-EN": "[DEV] CyberVPN - Reset your password",
            "ru-RU": "[DEV] CyberVPN - Сброс пароля",  # noqa: RUF001
            "de-DE": "[DEV] CyberVPN - Passwort zurücksetzen",
            "es-ES": "[DEV] CyberVPN - Restablece tu contraseña",
            "fr-FR": "[DEV] CyberVPN - Réinitialisez votre mot de passe",
        }
        return subjects.get(locale, subjects["en-EN"])

    def _render_password_reset_template(self, code: str, expires_in: str, locale: str) -> str:
        """Render password reset OTP template with DEV banner."""
        return render_otp_template(
            code,
            expires_in,
            locale,
            dev_banner=True,
            html_title="Reset Your CyberVPN Password",
            title="Reset Your Password",
            subtitle="Enter the following code to reset your password:",
            disclaimer="If you didn't request a password reset, ignore this email and keep your account secure.",
        )

    def _get_growth_notification_subject(self, title: str) -> str:
        return f"[DEV] CyberVPN - {title.strip() or 'Account update'}"

    def _render_growth_notification_text(
        self,
        title: str,
        message: str,
        cta_url: str,
        notes: list[str] | None,
    ) -> str:
        lines = [title.strip() or "CyberVPN account update", "", message.strip()]
        clean_notes = [str(item).strip() for item in notes or [] if str(item).strip()]
        if clean_notes:
            lines.extend(["", "Details:"])
            lines.extend(f"- {item}" for item in clean_notes)
        if cta_url:
            lines.extend(["", f"Open: {cta_url}"])
        return "\n".join(lines)
