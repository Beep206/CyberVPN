"""Auth Metrics Seed — Fake data generator for Grafana Auth Dashboard.

Generates realistic Prometheus metrics that mimic production auth/registration
traffic patterns.  Runs as a lightweight HTTP server on port 9099 exposing
/metrics endpoint in Prometheus exposition format.

Usage:
    python auth-metrics-seed.py          # start on :9099
    SEED_PORT=9098 python auth-metrics-seed.py  # override port

The generator simulates:
  • Registrations (email 60%, oauth 25%, telegram 15%)
  • Logins (password, oauth, magic_link, telegram) with ~85-92% success rate
  • Email verification (~80% success)
  • OAuth breakdown by provider
  • Auth errors by type
  • Magic link usage
  • Password reset flow
  • 2FA enable/disable/verify
  • Registration funnel (started → email_sent → verified → activated)
  • Auth latency histograms
  • Active sessions gauge (fluctuating 50-400)
"""

from __future__ import annotations

import math
import os
import random
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

# ── Configuration ───────────────────────────────────────────────────────
SEED_PORT = int(os.environ.get("SEED_PORT", "9099"))
TICK_INTERVAL = int(os.environ.get("TICK_INTERVAL", "30"))  # seconds between updates

# ── Registry (isolated from default to avoid conflicts) ─────────────────
registry = CollectorRegistry()

# ── Counters ────────────────────────────────────────────────────────────
registrations_total = Counter(
    "registrations_total",
    "Total user registrations",
    ["method"],
    registry=registry,
)

auth_attempts_total = Counter(
    "auth_attempts_total",
    "Total authentication attempts",
    ["method", "status"],
    registry=registry,
)

oauth_attempts_total = Counter(
    "oauth_attempts_total",
    "Total OAuth authentication attempts",
    ["provider", "status"],
    registry=registry,
)

email_verification_total = Counter(
    "email_verification_total",
    "Total email verification attempts",
    ["status"],
    registry=registry,
)

auth_errors_total = Counter(
    "auth_errors_total",
    "Total authentication errors by type",
    ["error_type"],
    registry=registry,
)

magic_link_requests_total = Counter(
    "magic_link_requests_total",
    "Total magic link requests",
    ["status"],
    registry=registry,
)

password_reset_total = Counter(
    "password_reset_total",
    "Total password reset operations",
    ["operation", "status"],
    registry=registry,
)

two_factor_operations_total = Counter(
    "two_factor_operations_total",
    "Total 2FA operations",
    ["operation", "status"],
    registry=registry,
)

registration_funnel_total = Counter(
    "registration_funnel_total",
    "Registration funnel tracking",
    ["step"],
    registry=registry,
)

# ── Gauges ──────────────────────────────────────────────────────────────
active_sessions_gauge = Gauge(
    "active_sessions_total",
    "Current number of active user sessions",
    registry=registry,
)

# ── Histograms ──────────────────────────────────────────────────────────
auth_request_duration_seconds = Histogram(
    "auth_request_duration_seconds",
    "Authentication request latency in seconds",
    ["method"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=registry,
)

# ── Distribution weights ────────────────────────────────────────────────

# Registration methods
REG_METHODS = {"email": 0.60, "oauth": 0.25, "telegram": 0.15}

# Auth methods
AUTH_METHODS = {"password": 0.50, "oauth": 0.25, "magic_link": 0.15, "telegram": 0.10}

# OAuth providers
OAUTH_PROVIDERS = {
    "google": 0.35,
    "github": 0.22,
    "discord": 0.15,
    "twitter": 0.10,
    "facebook": 0.08,
    "apple": 0.06,
    "microsoft": 0.04,
}

# Error types
ERROR_TYPES = {
    "invalid_credentials": 0.55,
    "account_locked": 0.10,
    "rate_limited": 0.15,
    "expired_token": 0.10,
    "invalid_otp": 0.10,
}

# Funnel steps (conversion rates)
# started -> 100%, email_sent -> 95%, email_verified -> 78%, activated -> 75%
FUNNEL_CONVERSION = {
    "started": 1.0,
    "email_sent": 0.95,
    "email_verified": 0.78,
    "activated": 0.75,
}


def _hour_multiplier() -> float:
    """Return a 0.2-1.0 multiplier based on hour-of-day to simulate day/night traffic.

    Peak hours are 10-14 and 18-22 UTC.
    """
    hour = time.gmtime().tm_hour
    # Sinusoidal wave peaking at ~12 and ~20 UTC
    wave = (math.sin((hour - 6) * math.pi / 12) + 1) / 2  # 0..1
    return max(0.2, wave)


def _weighted_choice(weights: dict[str, float]) -> str:
    keys = list(weights.keys())
    vals = list(weights.values())
    return random.choices(keys, weights=vals, k=1)[0]


def _tick() -> None:
    """Single tick: increment counters with realistic distribution."""

    mult = _hour_multiplier()

    # ── Registrations (2-8 per tick depending on time of day) ──────
    reg_count = max(1, int(random.gauss(5 * mult, 1.5)))
    for _ in range(reg_count):
        method = _weighted_choice(REG_METHODS)
        registrations_total.labels(method=method).inc()

    # ── Registration funnel ────────────────────────────────────────
    for step, conversion in FUNNEL_CONVERSION.items():
        step_count = max(0, int(reg_count * conversion))
        registration_funnel_total.labels(step=step).inc(step_count)

    # ── Auth attempts (10-40 per tick) ─────────────────────────────
    auth_count = max(3, int(random.gauss(25 * mult, 5)))
    success_rate = random.uniform(0.85, 0.93)
    failures = 0

    for _ in range(auth_count):
        method = _weighted_choice(AUTH_METHODS)
        success = random.random() < success_rate
        status = "success" if success else "failure"
        auth_attempts_total.labels(method=method, status=status).inc()

        # Latency observation
        if success:
            latency = random.lognormvariate(-1.2, 0.6)  # median ~0.3s
        else:
            latency = random.lognormvariate(-0.7, 0.8)  # median ~0.5s (failures slower)
        auth_request_duration_seconds.labels(method=method).observe(
            min(latency, 10.0)
        )

        if not success:
            failures += 1

    # ── Auth errors (distribute failures) ──────────────────────────
    for _ in range(failures):
        error_type = _weighted_choice(ERROR_TYPES)
        auth_errors_total.labels(error_type=error_type).inc()

    # ── OAuth attempts (subset of auth) ────────────────────────────
    oauth_count = max(1, int(auth_count * 0.25))
    for _ in range(oauth_count):
        provider = _weighted_choice(OAUTH_PROVIDERS)
        success = random.random() < 0.92
        status = "success" if success else "failure"
        oauth_attempts_total.labels(provider=provider, status=status).inc()

    # ── Email verification ─────────────────────────────────────────
    email_verify_count = max(0, int(reg_count * 0.85))
    for _ in range(email_verify_count):
        r = random.random()
        if r < 0.80:
            s = "success"
        elif r < 0.92:
            s = "failure"
        else:
            s = "expired"
        email_verification_total.labels(status=s).inc()

    # ── Magic link ─────────────────────────────────────────────────
    ml_count = max(0, int(random.gauss(3 * mult, 1)))
    for _ in range(ml_count):
        r = random.random()
        if r < 0.88:
            s = "sent"
        elif r < 0.95:
            s = "rate_limited"
        else:
            s = "error"
        magic_link_requests_total.labels(status=s).inc()

    # ── Password reset (1-3 per tick) ──────────────────────────────
    pr_count = random.randint(0, 3)
    for _ in range(pr_count):
        password_reset_total.labels(operation="request", status="success").inc()
        if random.random() < 0.65:
            password_reset_total.labels(operation="complete", status="success").inc()
        else:
            password_reset_total.labels(operation="complete", status="failure").inc()

    # ── 2FA operations (0-2 per tick) ──────────────────────────────
    for _ in range(random.randint(0, 2)):
        op = random.choice(["enable", "disable", "verify"])
        success = random.random() < 0.90
        status = "success" if success else "failure"
        two_factor_operations_total.labels(operation=op, status=status).inc()

    # ── Active sessions gauge (fluctuating) ────────────────────────
    base_sessions = int(200 * mult)
    jitter = random.randint(-30, 30)
    active_sessions_gauge.set(max(10, base_sessions + jitter))


# ── HTTP handler ────────────────────────────────────────────────────────

class MetricsHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler that serves /metrics and /health."""

    def do_GET(self) -> None:
        if self.path == "/metrics":
            output = generate_latest(registry)
            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.end_headers()
            self.wfile.write(output)
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        # Suppress noisy access logs; keep only errors
        pass


def _background_ticker() -> None:
    """Background thread that calls _tick() every TICK_INTERVAL seconds."""
    # Initial burst: fill some history so graphs aren't empty at startup
    print(f"[seed] Generating initial burst of {60} ticks …")
    for _ in range(60):
        _tick()
    print("[seed] Initial burst complete.")

    while True:
        time.sleep(TICK_INTERVAL)
        _tick()


def main() -> None:
    print(f"[seed] Auth metrics seed starting on :{SEED_PORT} (tick every {TICK_INTERVAL}s)")

    ticker = threading.Thread(target=_background_ticker, daemon=True)
    ticker.start()

    server = HTTPServer(("0.0.0.0", SEED_PORT), MetricsHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[seed] Shutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
