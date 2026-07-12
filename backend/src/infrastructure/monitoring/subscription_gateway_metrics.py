"""Bounded-cardinality metrics for public subscription delivery."""

from prometheus_client import Counter

subscription_gateway_resolution_total = Counter(
    "cybervpn_subscription_gateway_resolution_total",
    "Authoritative public subscription product resolution outcomes",
    ["result", "client"],
)

subscription_response_total = Counter(
    "cybervpn_subscription_response_total",
    "Successful subscription responses by trusted product and client family",
    ["product", "client", "response_type"],
)

subscription_generation_failures_total = Counter(
    "cybervpn_subscription_generation_failures_total",
    "Upstream subscription generation failures",
    ["product", "client"],
)
