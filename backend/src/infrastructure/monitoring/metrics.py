"""Prometheus metrics for application monitoring.

LOW-006: WebSocket authentication method tracking for deprecation analysis.
"""

from prometheus_client import Counter

# WebSocket authentication metrics (LOW-006)
# Tracks usage of different auth methods to monitor deprecation progress
websocket_auth_method_total = Counter(
    "websocket_auth_method_total",
    "Total WebSocket authentications by method",
    ["method"],  # "ticket" (preferred) or "token" (deprecated)
)
