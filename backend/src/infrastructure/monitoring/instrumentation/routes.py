"""Route instrumentation helpers for business logic metrics.

Provides functions to track auth, registration, payment, and subscription metrics.
"""

from src.infrastructure.monitoring.metrics import (
    auth_attempts_total,
    payments_total,
    registrations_total,
    subscriptions_activated_total,
    trials_activated_total,
)


def track_auth_attempt(method: str, success: bool) -> None:
    """Track an authentication attempt.

    Args:
        method: Authentication method (password/oauth/telegram/magic_link)
        success: Whether authentication succeeded

    Usage in auth routes:
        # After verifying credentials
        track_auth_attempt(method="password", success=True)
        # Or on failure
        track_auth_attempt(method="password", success=False)
    """
    status = "success" if success else "failure"
    auth_attempts_total.labels(method=method, status=status).inc()


def track_registration(method: str) -> None:
    """Track a user registration.

    Args:
        method: Registration method (email/oauth/telegram)

    Usage in registration routes:
        # After successful registration
        track_registration(method="email")
    """
    registrations_total.labels(method=method).inc()


def track_payment(status: str, currency: str) -> None:
    """Track a payment transaction.

    Args:
        status: Payment status (success/pending/failed)
        currency: Payment currency (USD/TON/USDT/etc)

    Usage in payment routes:
        # After payment processing
        track_payment(status="success", currency="TON")
    """
    payments_total.labels(status=status, currency=currency).inc()


def track_subscription_activation(plan_type: str) -> None:
    """Track a subscription activation.

    Args:
        plan_type: Subscription plan type (trial/monthly/yearly)

    Usage in subscription routes:
        # After activating subscription
        track_subscription_activation(plan_type="monthly")
    """
    subscriptions_activated_total.labels(plan_type=plan_type).inc()


def track_trial_activation() -> None:
    """Track a trial subscription activation.

    Usage in trial activation routes:
        # After activating trial
        track_trial_activation()
    """
    trials_activated_total.inc()
