"""Docker healthcheck script for the CyberVPN task worker.

Performs health checks:
1. Redis connectivity (PING)
2. Worker process is alive (implicit via being able to run this script)

Returns exit code 0 for healthy, 1 for unhealthy.
Uses synchronous code for Docker HEALTHCHECK compatibility.
"""

import sys

import redis


def check_redis() -> bool:
    """Check Redis connectivity with PING command.

    Returns:
        bool: True if Redis responds to PING, False otherwise
    """
    try:
        client = redis.from_url(
            "redis://remnawave-redis:6379/0",
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        result = client.ping()
        client.close()
        return bool(result)
    except Exception:
        return False


def main() -> int:
    """Run all health checks and return exit code.

    Returns:
        int: 0 if all checks pass, 1 if any check fails
    """
    checks = {
        "redis": check_redis(),
    }

    all_healthy = all(checks.values())

    if not all_healthy:
        failed = [name for name, status in checks.items() if not status]
        print(f"Health check failed: {', '.join(failed)}", file=sys.stderr)

    return 0 if all_healthy else 1


if __name__ == "__main__":
    sys.exit(main())
