"""Route instrumentation helpers for business logic metrics.

Provides functions to track auth, registration, payment, and subscription metrics.
"""

from src.infrastructure.monitoring.metrics import (
    auth_attempts_total,
    invite_operations_total,
    oauth_attempts_total,
    partner_operations_total,
    payments_total,
    plan_queries_total,
    profile_updates_total,
    promo_operations_total,
    referral_operations_total,
    registrations_total,
    server_queries_total,
    subscriptions_activated_total,
    trials_activated_total,
    two_factor_operations_total,
    wallet_operations_total,
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


def track_wallet_operation(operation: str, success: bool) -> None:
    """Track a wallet operation.

    Args:
        operation: Operation type (credit/debit/freeze/unfreeze)
        success: Whether the operation succeeded

    Usage in wallet routes:
        # After wallet operation
        track_wallet_operation(operation="credit", success=True)
    """
    status = "success" if success else "failure"
    wallet_operations_total.labels(operation=operation, status=status).inc()


def track_oauth_attempt(provider: str, success: bool) -> None:
    """Track an OAuth authentication attempt.

    Args:
        provider: OAuth provider (github/google/telegram)
        success: Whether authentication succeeded

    Usage in OAuth routes:
        # After OAuth callback
        track_oauth_attempt(provider="github", success=True)
    """
    status = "success" if success else "failure"
    oauth_attempts_total.labels(provider=provider, status=status).inc()


def track_2fa_operation(operation: str, success: bool) -> None:
    """Track a 2FA operation.

    Args:
        operation: Operation type (enable/disable/verify)
        success: Whether the operation succeeded

    Usage in 2FA routes:
        # After enabling 2FA
        track_2fa_operation(operation="enable", success=True)
    """
    status = "success" if success else "failure"
    two_factor_operations_total.labels(operation=operation, status=status).inc()


def track_profile_update(field: str) -> None:
    """Track a profile update.

    Args:
        field: Field being updated (email/password/preferences/display_name)

    Usage in profile routes:
        # After updating profile
        track_profile_update(field="email")
    """
    profile_updates_total.labels(field=field).inc()


def track_server_query(operation: str) -> None:
    """Track a server query.

    Args:
        operation: Operation type (list/get/create/update/delete)

    Usage in server routes:
        # After querying servers
        track_server_query(operation="list")
    """
    server_queries_total.labels(operation=operation).inc()


def track_plan_query(operation: str) -> None:
    """Track a subscription plan query.

    Args:
        operation: Operation type (list/get/activate)

    Usage in plan routes:
        # After querying plans
        track_plan_query(operation="list")
    """
    plan_queries_total.labels(operation=operation).inc()


def track_invite_operation(operation: str, success: bool) -> None:
    """Track an invite code operation.

    Args:
        operation: Operation type (create/use/list)
        success: Whether the operation succeeded

    Usage in invite routes:
        # After creating invite
        track_invite_operation(operation="create", success=True)
    """
    status = "success" if success else "failure"
    invite_operations_total.labels(operation=operation, status=status).inc()


def track_promo_operation(operation: str, success: bool) -> None:
    """Track a promo code operation.

    Args:
        operation: Operation type (create/use/validate)
        success: Whether the operation succeeded

    Usage in promo code routes:
        # After using promo code
        track_promo_operation(operation="use", success=True)
    """
    status = "success" if success else "failure"
    promo_operations_total.labels(operation=operation, status=status).inc()


def track_referral_operation(operation: str) -> None:
    """Track a referral operation.

    Args:
        operation: Operation type (register/claim/list_earnings)

    Usage in referral routes:
        # After registering referral
        track_referral_operation(operation="register")
    """
    referral_operations_total.labels(operation=operation).inc()


def track_partner_operation(operation: str) -> None:
    """Track a partner operation.

    Args:
        operation: Operation type (create/update/track_sale)

    Usage in partner routes:
        # After tracking sale
        track_partner_operation(operation="track_sale")
    """
    partner_operations_total.labels(operation=operation).inc()
