"""Prometheus metrics for application monitoring.

Custom metrics for tracking application-level events beyond HTTP metrics.
These metrics complement the HTTP metrics provided by prometheus-fastapi-instrumentator.
"""

from prometheus_client import Counter, Gauge, Histogram

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
