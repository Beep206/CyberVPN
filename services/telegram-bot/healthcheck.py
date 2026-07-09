"""CyberVPN Telegram Bot — Docker healthcheck script.

Verifies bot connectivity by checking Redis connection
and optionally the Prometheus metrics endpoint.
"""

from __future__ import annotations

import asyncio
import sys
import urllib.request


def _metrics_endpoint_healthy(prometheus_port: int) -> bool:
    req = urllib.request.Request(
        f"http://localhost:{prometheus_port}/metrics",
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=3) as resp:  # noqa: S310
        return resp.status == 200


async def check_health() -> bool:
    """Run health checks against Redis and metrics endpoint."""
    import os

    checks_passed = True

    # Check 1: Redis connectivity
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_db = int(os.getenv("REDIS_DB", "1"))
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(f"{redis_url}/{redis_db}", socket_timeout=3)
        await client.ping()
        await client.aclose()
    except Exception:
        print("UNHEALTHY: Redis connection failed")  # noqa: T201
        checks_passed = False

    # Check 2: Prometheus metrics endpoint (if enabled)
    prometheus_enabled = os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true"
    if prometheus_enabled:
        prometheus_port = int(os.getenv("PROMETHEUS_PORT", "9092"))
        try:
            if not await asyncio.to_thread(_metrics_endpoint_healthy, prometheus_port):
                print("UNHEALTHY: Metrics endpoint returned non-200")  # noqa: T201
                checks_passed = False
        except Exception as exc:
            # Metrics endpoint may not be up yet in polling mode;
            # don't fail the healthcheck for this alone.
            print(f"WARNING: Metrics endpoint health skipped: {exc}")  # noqa: T201

    return checks_passed


def main() -> None:
    """Entry point for Docker HEALTHCHECK."""
    try:
        healthy = asyncio.run(check_health())
    except Exception as exc:
        print(f"UNHEALTHY: {exc}")  # noqa: T201
        sys.exit(1)

    if healthy:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
