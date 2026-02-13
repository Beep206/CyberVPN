"""Email task definitions."""

from src.tasks.email.send_magic_link import send_magic_link_email
from src.tasks.email.send_otp import send_otp_email

__all__ = ["send_magic_link_email", "send_otp_email"]
