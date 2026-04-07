"""Prometheus metrics for application monitoring.

Custom metrics for tracking application-level events beyond HTTP metrics.
These metrics complement the HTTP metrics provided by prometheus-fastapi-instrumentator.
"""

from prometheus_client import Counter, Gauge, Histogram

# ──────────────────────────────────────────────
# Email verification metrics
# ──────────────────────────────────────────────
email_verification_total = Counter(
    "email_verification_total",
    "Total email verification attempts",
    ["status"],  # success / failure / expired
)

# ──────────────────────────────────────────────
# Auth error breakdown
# ──────────────────────────────────────────────
auth_errors_total = Counter(
    "auth_errors_total",
    "Total authentication errors by type",
    ["error_type"],  # invalid_credentials / account_locked / rate_limited / expired_token / invalid_otp
)

# ──────────────────────────────────────────────
# Magic link metrics
# ──────────────────────────────────────────────
magic_link_requests_total = Counter(
    "magic_link_requests_total",
    "Total magic link requests",
    ["status"],  # sent / rate_limited / error
)

# ──────────────────────────────────────────────
# Password reset metrics
# ──────────────────────────────────────────────
password_reset_total = Counter(
    "password_reset_total",
    "Total password reset operations",
    ["operation", "status"],  # operation: request/complete, status: success/failure
)

# ──────────────────────────────────────────────
# Active sessions gauge
# ──────────────────────────────────────────────
active_sessions_gauge = Gauge(
    "active_sessions_total",
    "Current number of active user sessions",
)

# ──────────────────────────────────────────────
# Registration funnel
# ──────────────────────────────────────────────
registration_funnel_total = Counter(
    "registration_funnel_total",
    "Registration funnel tracking",
    ["step"],  # started / email_sent / email_verified / activated
)

# ──────────────────────────────────────────────
# Auth latency histogram
# ──────────────────────────────────────────────
auth_request_duration_seconds = Histogram(
    "auth_request_duration_seconds",
    "Authentication request latency in seconds",
    ["method"],  # password / oauth / magic_link / telegram
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Database metrics
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

db_connections_active = Gauge(
    "db_connections_active",
    "Number of active database connections in the pool",
)

# Cache metrics
cache_operations_total = Counter(
    "cache_operations_total",
    "Total cache operations",
    ["operation", "status"],  # operation: get/set/delete, status: hit/miss/error
)

# External API metrics
external_api_duration_seconds = Histogram(
    "external_api_duration_seconds",
    "External API call duration in seconds",
    ["service", "endpoint", "method"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

# Authentication metrics
auth_attempts_total = Counter(
    "auth_attempts_total",
    "Total authentication attempts",
    ["method", "status"],  # method: password/oauth/telegram, status: success/failure
)

auth_password_identifier_events_total = Counter(
    "auth_password_identifier_events_total",
    "Password auth and registration events split by identifier type",
    ["channel", "identifier_type", "step", "status"],
)

auth_client_activity_total = Counter(
    "auth_client_activity_total",
    "Auth and registration flow events split by normalized client context",
    ["channel", "method", "provider", "client_type", "os_family", "client_app", "step", "status"],
)

# Rich auth flow metrics for product-level dashboards and drilldowns
auth_flow_events_total = Counter(
    "auth_flow_events_total",
    "Detailed auth and registration flow events with channel/provider/locale context",
    ["channel", "method", "provider", "locale", "step", "status"],
)

auth_security_events_total = Counter(
    "auth_security_events_total",
    "Detailed auth security and error events with channel/provider/locale context",
    ["channel", "method", "provider", "locale", "error_type"],
)

# Auth session lifecycle metrics
auth_session_operations_total = Counter(
    "auth_session_operations_total",
    "Total auth session lifecycle operations",
    ["operation", "status"],  # operation: refresh/logout/logout_all/revoke_device
    # status: success/failure/missing_token/not_found
)

auth_session_detailed_total = Counter(
    "auth_session_detailed_total",
    "Detailed auth session lifecycle events with failure reason context",
    ["channel", "method", "operation", "status", "reason"],
)

auth_bruteforce_events_total = Counter(
    "auth_bruteforce_events_total",
    "Brute-force protection events by identifier type and lockout tier",
    ["channel", "identifier_type", "outcome", "lockout_tier"],
)

auth_users_risk_level_total = Gauge(
    "auth_users_risk_level_total",
    "Current number of auth users by risk level",
    ["risk_level"],
)

auth_users_verification_state_total = Gauge(
    "auth_users_verification_state_total",
    "Current number of auth users by email verification state",
    ["verification_state"],
)

auth_users_with_failed_login_attempts_current = Gauge(
    "auth_users_with_failed_login_attempts_current",
    "Current number of auth users with failed login attempts recorded in the database",
)

auth_failed_login_attempts_backlog_current = Gauge(
    "auth_failed_login_attempts_backlog_current",
    "Current backlog of failed login attempts recorded for auth users",
)

auth_bruteforce_identifiers_current = Gauge(
    "auth_bruteforce_identifiers_current",
    "Current number of identifiers with failed login attempts tracked in Redis",
)

auth_bruteforce_attempts_current = Gauge(
    "auth_bruteforce_attempts_current",
    "Current failed login attempt pressure tracked in Redis",
)

auth_lockouts_current_total = Gauge(
    "auth_lockouts_current_total",
    "Current number of lockouts by source and tier",
    ["source", "lockout_tier"],
)

auth_locked_users_db_current = Gauge(
    "auth_locked_users_db_current",
    "Current number of auth users locked in the database via locked_until",
)

auth_active_sessions_client_type_total = Gauge(
    "auth_active_sessions_client_type_total",
    "Current number of active refresh sessions by normalized client type",
    ["client_type"],
)

auth_active_sessions_os_family_total = Gauge(
    "auth_active_sessions_os_family_total",
    "Current number of active refresh sessions by normalized OS family",
    ["os_family"],
)

auth_active_sessions_client_app_total = Gauge(
    "auth_active_sessions_client_app_total",
    "Current number of active refresh sessions by normalized client app",
    ["client_app"],
)

auth_mobile_devices_total = Gauge(
    "auth_mobile_devices_total",
    "Current number of registered and recently active mobile devices by platform",
    ["platform", "state"],
)

# First successful login after activation/onboarding
first_login_after_activation_total = Counter(
    "first_login_after_activation_total",
    "Total first successful logins after account activation",
    ["method"],  # method: email_verification/magic_link/oauth/telegram
)

oauth_callback_failures_total = Counter(
    "oauth_callback_failures_total",
    "OAuth callback failures by provider and reason",
    ["channel", "provider", "reason"],
)

auth_activation_duration_seconds = Histogram(
    "auth_activation_duration_seconds",
    "Time from registration to verification or first successful login",
    ["channel", "method", "locale", "stage"],
    buckets=(5, 15, 30, 60, 120, 300, 900, 1800, 3600, 7200, 21600, 43200, 86400, 172800, 604800),
)

# User registration metrics
registrations_total = Counter(
    "registrations_total",
    "Total user registrations",
    ["method"],  # method: email/oauth/telegram
)

# Subscription metrics
subscriptions_activated_total = Counter(
    "subscriptions_activated_total",
    "Total subscriptions activated",
    ["plan_type"],  # plan_type: trial/monthly/yearly
)

# Payment metrics
payments_total = Counter(
    "payments_total",
    "Total payments processed",
    ["status", "currency"],  # status: success/pending/failed
)

# Trial metrics
trials_activated_total = Counter(
    "trials_activated_total",
    "Total trial subscriptions activated",
)

# WebSocket authentication metrics
websocket_auth_method_total = Counter(
    "websocket_auth_method_total",
    "Total WebSocket authentications by method",
    ["method"],  # "ticket" only (token auth removed in v2.0)
)

# Wallet operations metrics
wallet_operations_total = Counter(
    "wallet_operations_total",
    "Total wallet operations",
    ["operation", "status"],  # operation: credit/debit/freeze/unfreeze, status: success/failure
)

# OAuth operations metrics
oauth_attempts_total = Counter(
    "oauth_attempts_total",
    "Total OAuth authentication attempts",
    ["provider", "status"],  # provider: github/google/telegram, status: success/failure
)

# 2FA operations metrics
two_factor_operations_total = Counter(
    "two_factor_operations_total",
    "Total 2FA operations",
    ["operation", "status"],  # operation: enable/disable/verify, status: success/failure
)

# Profile update metrics
profile_updates_total = Counter(
    "profile_updates_total",
    "Total profile updates",
    ["field"],  # field: email/password/preferences/display_name
)

# Server query metrics
server_queries_total = Counter(
    "server_queries_total",
    "Total server queries",
    ["operation"],  # operation: list/get/create/update/delete
)

# Plan query metrics
plan_queries_total = Counter(
    "plan_queries_total",
    "Total subscription plan queries",
    ["operation"],  # operation: list/get/activate
)

# Invite operations metrics
invite_operations_total = Counter(
    "invite_operations_total",
    "Total invite code operations",
    ["operation", "status"],  # operation: create/use/list, status: success/failure
)

# Promo code operations metrics
promo_operations_total = Counter(
    "promo_operations_total",
    "Total promo code operations",
    ["operation", "status"],  # operation: create/use/validate, status: success/failure
)

# Referral operations metrics
referral_operations_total = Counter(
    "referral_operations_total",
    "Total referral operations",
    ["operation"],  # operation: register/claim/list_earnings
)

# Partner operations metrics
partner_operations_total = Counter(
    "partner_operations_total",
    "Total partner operations",
    ["operation"],  # operation: create/update/track_sale
)

# Generic route operations metrics (for routes without specific counters)
route_operations_total = Counter(
    "route_operations_total",
    "Total route operations",
    ["route", "action", "status"],
)

# Webhook operations metrics
webhook_operations_total = Counter(
    "webhook_operations_total",
    "Total webhook operations",
    ["provider", "status"],  # provider: remnawave/cryptobot, status: success/failure
)

# User management operations metrics
user_management_total = Counter(
    "user_management_total",
    "Total user management operations",
    ["operation", "status"],  # operation: list/get/create/update/delete, status: success/failure
)

# Notification operations metrics
notification_operations_total = Counter(
    "notification_operations_total",
    "Total notification operations",
    ["operation"],  # operation: get_preferences/update_preferences
)

# FCM token operations metrics
fcm_operations_total = Counter(
    "fcm_operations_total",
    "Total FCM token operations",
    ["operation"],  # operation: register/unregister
)

# Monitoring operations metrics
monitoring_operations_total = Counter(
    "monitoring_operations_total",
    "Total monitoring operations",
    ["operation"],  # operation: health_check/stats/bandwidth
)
