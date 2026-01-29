"""Docker healthcheck script for the CyberVPN task worker.

Performs comprehensive health checks:
1. Redis connectivity (PING)
2. PostgreSQL connectivity (SELECT 1)
3. Broker connectivity (implicit via Redis check)

Returns exit code 0 for healthy, 1 for unhealthy.
Uses synchronous code for Docker HEALTHCHECK compatibility.
"""

import sys

import psycopg
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
        return result
    except Exception:
        return False


def check_postgres() -> bool:
    """Check PostgreSQL connectivity with simple query.

    Returns:
        bool: True if PostgreSQL responds to SELECT 1, False otherwise
    """
    try:
        # Use synchronous psycopg for healthcheck
        with psycopg.connect(
            "postgresql://cybervpn:cybervpn@remnawave-db:6767/cybervpn",
            connect_timeout=5,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                return result is not None and result[0] == 1
    except Exception:
        return False


def main() -> int:
    """Run all health checks and return exit code.

    Returns:
        int: 0 if all checks pass, 1 if any check fails
    """
    checks = {
        "redis": check_redis(),
        "postgres": check_postgres(),
    }

    all_healthy = all(checks.values())

    if not all_healthy:
        failed = [name for name, status in checks.items() if not status]
        print(f"Health check failed: {', '.join(failed)}", file=sys.stderr)

    return 0 if all_healthy else 1


if __name__ == "__main__":
    sys.exit(main())
