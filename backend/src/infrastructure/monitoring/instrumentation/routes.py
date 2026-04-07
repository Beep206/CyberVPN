"""Route instrumentation helpers for business logic metrics.

Provides functions to track auth, registration, payment, and subscription metrics.
"""

from datetime import UTC, datetime, timedelta
from time import perf_counter

import redis.asyncio as redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.login_protection import LockoutPolicy
from src.infrastructure.monitoring.client_context import (
    CLIENT_APPS,
    CLIENT_TYPES,
    LOCKOUT_TIERS,
    MOBILE_DEVICE_PLATFORMS,
    OS_FAMILIES,
    RISK_LEVELS,
    VERIFICATION_STATES,
    AuthClientContext,
    resolve_web_client_context,
)
from src.infrastructure.monitoring.metrics import (
    active_sessions_gauge,
    auth_activation_duration_seconds,
    auth_active_sessions_client_app_total,
    auth_active_sessions_client_type_total,
    auth_active_sessions_os_family_total,
    auth_attempts_total,
    auth_bruteforce_attempts_current,
    auth_bruteforce_events_total,
    auth_bruteforce_identifiers_current,
    auth_client_activity_total,
    auth_errors_total,
    auth_failed_login_attempts_backlog_current,
    auth_flow_events_total,
    auth_locked_users_db_current,
    auth_lockouts_current_total,
    auth_mobile_devices_total,
    auth_password_identifier_events_total,
    auth_request_duration_seconds,
    auth_security_events_total,
    auth_session_detailed_total,
    auth_session_operations_total,
    auth_users_risk_level_total,
    auth_users_verification_state_total,
    auth_users_with_failed_login_attempts_current,
    email_verification_total,
    first_login_after_activation_total,
    invite_operations_total,
    magic_link_requests_total,
    oauth_attempts_total,
    oauth_callback_failures_total,
    partner_operations_total,
    password_reset_total,
    payments_total,
    plan_queries_total,
    profile_updates_total,
    promo_operations_total,
    referral_operations_total,
    registration_funnel_total,
    registrations_total,
    server_queries_total,
    subscriptions_activated_total,
    trials_activated_total,
    two_factor_operations_total,
    wallet_operations_total,
)


def _normalize_locale(locale: str | None) -> str:
    if not locale:
        return "unknown"
    normalized = locale.strip()
    return normalized or "unknown"


def _normalize_client_context(context: AuthClientContext | None) -> AuthClientContext:
    return context or AuthClientContext()


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


def track_auth_flow_event(
    *,
    channel: str,
    method: str,
    provider: str,
    locale: str | None,
    client_context: AuthClientContext | None = None,
    step: str,
    status: str = "success",
    amount: int = 1,
) -> None:
    """Track a detailed auth or registration flow event."""
    resolved_context = _normalize_client_context(client_context)
    auth_flow_events_total.labels(
        channel=channel,
        method=method,
        provider=provider,
        locale=_normalize_locale(locale),
        step=step,
        status=status,
    ).inc(amount)
    auth_client_activity_total.labels(
        channel=channel,
        method=method,
        provider=provider,
        client_type=resolved_context.client_type,
        os_family=resolved_context.os_family,
        client_app=resolved_context.client_app,
        step=step,
        status=status,
    ).inc(amount)


def track_auth_password_identifier_event(
    *,
    channel: str,
    identifier_type: str,
    step: str,
    client_context: AuthClientContext | None = None,
    status: str = "success",
    amount: int = 1,
) -> None:
    """Track password auth/register events by identifier type."""
    auth_password_identifier_events_total.labels(
        channel=channel,
        identifier_type=identifier_type,
        step=step,
        status=status,
    ).inc(amount)
    if step in {"registered", "email_sent", "activated", "first_successful_login", "login", "session_started"}:
        resolved_context = _normalize_client_context(client_context)
        auth_client_activity_total.labels(
            channel=channel,
            method="password",
            provider="native",
            client_type=resolved_context.client_type,
            os_family=resolved_context.os_family,
            client_app=resolved_context.client_app,
            step=step,
            status=status,
        ).inc(amount)


def track_registration(method: str) -> None:
    """Track a user registration.

    Args:
        method: Registration method (email/oauth/telegram)

    Usage in registration routes:
        # After successful registration
        track_registration(method="email")
    """
    registrations_total.labels(method=method).inc()


def track_registration_funnel_step(step: str, amount: int = 1) -> None:
    """Track a registration funnel step.

    Args:
        step: Funnel step (started/email_sent/email_verified/activated)
        amount: Increment amount
    """
    registration_funnel_total.labels(step=step).inc(amount)


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


def track_email_verification(success: bool, expired: bool = False) -> None:
    """Track an email verification attempt.

    Args:
        success: Whether verification succeeded
        expired: Whether the OTP was expired
    """
    if expired:
        status = "expired"
    else:
        status = "success" if success else "failure"
    email_verification_total.labels(status=status).inc()


def track_magic_link_request(status: str) -> None:
    """Track a magic link request outcome.

    Args:
        status: Request status (sent/rate_limited/error)
    """
    magic_link_requests_total.labels(status=status).inc()


def track_password_reset(operation: str, success: bool) -> None:
    """Track a password reset operation.

    Args:
        operation: Reset flow operation (request/complete)
        success: Whether the operation succeeded
    """
    status = "success" if success else "failure"
    password_reset_total.labels(operation=operation, status=status).inc()


def observe_auth_request_duration(method: str, started_at: float) -> None:
    """Observe auth flow duration using a monotonic start timestamp."""
    auth_request_duration_seconds.labels(method=method).observe(max(perf_counter() - started_at, 0.0))


def track_auth_error(error_type: str) -> None:
    """Track an authentication error by type.

    Args:
        error_type: Error category
            (invalid_credentials/account_locked/rate_limited/expired_token/invalid_otp)
    """
    auth_errors_total.labels(error_type=error_type).inc()


def track_auth_security_event(
    *,
    channel: str,
    method: str,
    provider: str,
    locale: str | None,
    error_type: str,
    amount: int = 1,
) -> None:
    """Track a detailed auth error/security event."""
    auth_security_events_total.labels(
        channel=channel,
        method=method,
        provider=provider,
        locale=_normalize_locale(locale),
        error_type=error_type,
    ).inc(amount)


def track_auth_bruteforce_event(
    *,
    channel: str,
    identifier_type: str,
    outcome: str,
    lockout_tier: str = "none",
    amount: int = 1,
) -> None:
    """Track brute-force protection events with bounded tier labels."""
    auth_bruteforce_events_total.labels(
        channel=channel,
        identifier_type=identifier_type,
        outcome=outcome,
        lockout_tier=lockout_tier if lockout_tier in LOCKOUT_TIERS else "none",
    ).inc(amount)


def track_auth_session_operation(operation: str, status: str = "success") -> None:
    """Track an auth session lifecycle operation.

    Args:
        operation: Session operation (refresh/logout/logout_all/revoke_device)
        status: Operation result (success/failure/missing_token/not_found)
    """
    auth_session_operations_total.labels(operation=operation, status=status).inc()


def track_auth_session_detail(
    *,
    channel: str,
    method: str,
    operation: str,
    status: str = "success",
    reason: str = "none",
    amount: int = 1,
) -> None:
    """Track a detailed auth session lifecycle event with failure reason."""
    auth_session_detailed_total.labels(
        channel=channel,
        method=method,
        operation=operation,
        status=status,
        reason=reason,
    ).inc(amount)


def track_first_login_after_activation(method: str) -> None:
    """Track the first successful login that happens during activation/onboarding."""
    first_login_after_activation_total.labels(method=method).inc()


def track_oauth_callback_failure(*, channel: str, provider: str, reason: str) -> None:
    """Track an OAuth callback failure by provider and reason."""
    oauth_callback_failures_total.labels(channel=channel, provider=provider, reason=reason).inc()


def observe_auth_activation_duration(
    *,
    channel: str,
    method: str,
    locale: str | None,
    stage: str,
    started_at: datetime | None,
    ended_at: datetime | None = None,
) -> None:
    """Observe registration-to-activation/login timing in seconds."""
    if started_at is None:
        return

    finished_at = ended_at or datetime.now(UTC)
    duration = (finished_at - started_at).total_seconds()
    if duration < 0:
        return

    auth_activation_duration_seconds.labels(
        channel=channel,
        method=method,
        locale=_normalize_locale(locale),
        stage=stage,
    ).observe(duration)


async def sync_active_sessions(session: AsyncSession) -> int:
    """Set the active sessions gauge from persisted refresh tokens.

    This reflects refresh-token-backed admin/web sessions only.
    """
    from src.infrastructure.database.models.refresh_token_model import RefreshToken

    result = await session.execute(
        select(func.count())
        .select_from(RefreshToken)
        .where(
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(UTC),
        )
    )
    active_sessions = int(result.scalar_one() or 0)
    active_sessions_gauge.set(active_sessions)

    session_user_agents = await session.execute(
        select(RefreshToken.user_agent).where(
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(UTC),
        )
    )

    client_type_counts = {client_type: 0 for client_type in CLIENT_TYPES}
    os_family_counts = {os_family: 0 for os_family in OS_FAMILIES}
    client_app_counts = {client_app: 0 for client_app in CLIENT_APPS}

    for user_agent in session_user_agents.scalars():
        context = resolve_web_client_context(user_agent)
        client_type_counts[context.client_type] += 1
        os_family_counts[context.os_family] += 1
        client_app_counts[context.client_app] += 1

    for client_type in CLIENT_TYPES:
        auth_active_sessions_client_type_total.labels(client_type=client_type).set(client_type_counts[client_type])
    for os_family in OS_FAMILIES:
        auth_active_sessions_os_family_total.labels(os_family=os_family).set(os_family_counts[os_family])
    for client_app in CLIENT_APPS:
        auth_active_sessions_client_app_total.labels(client_app=client_app).set(client_app_counts[client_app])

    return active_sessions


async def sync_auth_security_posture(
    session: AsyncSession,
    redis_client: redis.Redis | None = None,
) -> None:
    """Synchronize current auth security posture gauges from DB and Redis."""
    from src.infrastructure.database.models.admin_user_model import AdminUserModel
    from src.infrastructure.database.models.mobile_device_model import MobileDeviceModel

    now = datetime.now(UTC)

    risk_rows = await session.execute(
        select(AdminUserModel.risk_level, func.count())
        .group_by(AdminUserModel.risk_level)
    )
    risk_counts = {risk_level: 0 for risk_level in RISK_LEVELS}
    for risk_level, count in risk_rows.all():
        normalized_risk = (risk_level or "unknown").strip().lower()
        risk_counts[normalized_risk if normalized_risk in risk_counts else "unknown"] += int(count or 0)
    for risk_level in RISK_LEVELS:
        auth_users_risk_level_total.labels(risk_level=risk_level).set(risk_counts[risk_level])

    verification_rows = await session.execute(
        select(AdminUserModel.is_email_verified, func.count())
        .group_by(AdminUserModel.is_email_verified)
    )
    verification_counts = {state: 0 for state in VERIFICATION_STATES}
    for is_verified, count in verification_rows.all():
        verification_counts["verified" if is_verified else "unverified"] += int(count or 0)
    for verification_state in VERIFICATION_STATES:
        auth_users_verification_state_total.labels(verification_state=verification_state).set(
            verification_counts[verification_state]
        )

    users_with_failed_attempts, failed_attempts_backlog, db_locked_users = (
        await session.execute(
            select(
                func.count().filter(AdminUserModel.failed_login_attempts > 0),
                func.coalesce(func.sum(AdminUserModel.failed_login_attempts), 0),
                func.count().filter(
                    AdminUserModel.locked_until.is_not(None),
                    AdminUserModel.locked_until > now,
                ),
            )
        )
    ).one()
    auth_users_with_failed_login_attempts_current.set(int(users_with_failed_attempts or 0))
    auth_failed_login_attempts_backlog_current.set(int(failed_attempts_backlog or 0))
    auth_locked_users_db_current.set(int(db_locked_users or 0))

    registered_mobile_rows = await session.execute(
        select(MobileDeviceModel.platform, func.count()).group_by(MobileDeviceModel.platform)
    )
    recent_mobile_rows = await session.execute(
        select(MobileDeviceModel.platform, func.count())
        .where(
            MobileDeviceModel.last_active_at.is_not(None),
            MobileDeviceModel.last_active_at > now.replace(microsecond=0) - timedelta(hours=24),
        )
        .group_by(MobileDeviceModel.platform)
    )

    mobile_registered_counts = {platform: 0 for platform in MOBILE_DEVICE_PLATFORMS}
    mobile_recent_counts = {platform: 0 for platform in MOBILE_DEVICE_PLATFORMS}
    for platform, count in registered_mobile_rows.all():
        normalized_platform = platform if platform in mobile_registered_counts else "unknown"
        mobile_registered_counts[normalized_platform] += int(count or 0)
    for platform, count in recent_mobile_rows.all():
        normalized_platform = platform if platform in mobile_recent_counts else "unknown"
        mobile_recent_counts[normalized_platform] += int(count or 0)

    for platform in MOBILE_DEVICE_PLATFORMS:
        auth_mobile_devices_total.labels(platform=platform, state="registered").set(mobile_registered_counts[platform])
        auth_mobile_devices_total.labels(platform=platform, state="recently_active").set(mobile_recent_counts[platform])

    redis_tier_counts = {lockout_tier: 0 for lockout_tier in LOCKOUT_TIERS}
    redis_identifiers = 0
    redis_attempts = 0
    if redis_client is not None:
        async for key in redis_client.scan_iter(match="login_attempts:*", count=100):
            redis_identifiers += 1
            value = await redis_client.get(key)
            if value:
                redis_attempts += int(value)

        async for key in redis_client.scan_iter(match="lockout:*", count=100):
            value = await redis_client.get(key)
            if not value:
                continue
            if value == "permanent":
                redis_tier_counts["permanent"] += 1
                continue
            attempts = int(value)
            redis_tier_counts[LockoutPolicy.get_lockout_tier(attempts)] += 1

    auth_bruteforce_identifiers_current.set(redis_identifiers)
    auth_bruteforce_attempts_current.set(redis_attempts)
    for lockout_tier in LOCKOUT_TIERS:
        auth_lockouts_current_total.labels(source="db", lockout_tier=lockout_tier).set(0)
        auth_lockouts_current_total.labels(source="redis", lockout_tier=lockout_tier).set(
            redis_tier_counts[lockout_tier]
        )
