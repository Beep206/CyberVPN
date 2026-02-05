"""SMTP email client for development/testing with Mailpit cluster."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)


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

    Usage:
        async with SmtpClient() as client:
            await client.send_otp(email="user@example.com", code="123456")
    """

    # Class-level counter for round-robin rotation
    _server_index: int = 0

    def __init__(self) -> None:
        settings = get_settings()
        self._servers = settings.smtp_servers
        self._from_email = settings.smtp_from_email

    async def __aenter__(self) -> "SmtpClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    def _get_next_server(self) -> tuple[str, int]:
        """Get next server in round-robin rotation."""
        if not self._servers:
            return ("localhost", 1025)

        server_str = self._servers[SmtpClient._server_index % len(self._servers)]
        SmtpClient._server_index += 1

        # Parse host:port
        if ":" in server_str:
            host, port_str = server_str.split(":", 1)
            port = int(port_str)
        else:
            host = server_str
            port = 1025

        return (host, port)

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
        host, port = self._get_next_server()
        server_id = f"mailpit-{(SmtpClient._server_index - 1) % len(self._servers) + 1}"

        logger.info(
            "smtp_sending_otp",
            email=email,
            server=f"{host}:{port}",
            server_id=server_id,
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
                "id": f"smtp_{server_id}_{SmtpClient._server_index}",
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
        """Render cyberpunk-styled OTP email template with DEV banner."""
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
                <!-- DEV MODE BANNER -->
                <div style="background: #ff6b6b; color: #000; padding: 10px 20px; border-radius: 4px; margin-bottom: 20px; font-weight: bold;">
                    DEV MODE - Sent via Mailpit
                </div>

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
                                &copy; 2026 CyberVPN. Development Environment.
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
