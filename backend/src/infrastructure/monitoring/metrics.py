"""Prometheus metrics for application monitoring."""

from prometheus_client import Counter

# WebSocket authentication metrics
websocket_auth_method_total = Counter(
    "websocket_auth_method_total",
    "Total WebSocket authentications by method",
    ["method"],  # "ticket" only (token auth removed in v2.0)
)
