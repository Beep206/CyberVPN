"""Email tasks for OTP delivery."""

from src.tasks.email.send_otp import send_otp_email

__all__ = ["send_otp_email"]
