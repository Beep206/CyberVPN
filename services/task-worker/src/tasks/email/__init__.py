"""Email task definitions."""

from src.tasks.email.process_growth_notification_deliveries import (
    process_growth_notification_deliveries,
)
from src.tasks.email.send_magic_link import send_magic_link_email
from src.tasks.email.send_otp import send_otp_email
from src.tasks.email.send_password_reset import send_password_reset_email

__all__ = [
    "process_growth_notification_deliveries",
    "send_magic_link_email",
    "send_otp_email",
    "send_password_reset_email",
]
