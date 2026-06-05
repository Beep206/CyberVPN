"""Scoped fixtures for API v1 integration tests."""

import os
from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlparse

import pytest
import pytest_asyncio

from src.config.settings import settings
from src.infrastructure.cache.redis_client import get_redis_client

ALLOW_API_V1_REDIS_FLUSHDB_ENV = "PYTEST_ALLOW_API_V1_REDIS_FLUSHDB"
SAFE_API_V1_REDIS_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "redis", "valkey"})
SAFE_API_V1_REDIS_DB_MIN = 15


def _redis_db_index(redis_url: str) -> int | None:
    parsed = urlparse(redis_url)
    query_db = parse_qs(parsed.query).get("db", [None])[0]
    raw_db = (parsed.path or "").lstrip("/") or query_db or "0"
    try:
        return int(raw_db)
    except ValueError:
        return None


def _assert_safe_api_v1_redis_flushdb() -> None:
    if os.environ.get(ALLOW_API_V1_REDIS_FLUSHDB_ENV) == "1":
        return

    parsed = urlparse(settings.redis_url)
    db_index = _redis_db_index(settings.redis_url)
    environment = settings.environment.lower()
    hostname = (parsed.hostname or "").lower()
    is_safe_test_db = (
        environment == "test"
        and hostname in SAFE_API_V1_REDIS_HOSTS
        and db_index is not None
        and db_index >= SAFE_API_V1_REDIS_DB_MIN
    )
    if is_safe_test_db:
        return

    pytest.fail(
        "Refusing to run API v1 Redis isolation flushdb against a non-isolated Redis target. "
        f"Set REDIS_URL to a local/test DB >= {SAFE_API_V1_REDIS_DB_MIN} "
        f"or set {ALLOW_API_V1_REDIS_FLUSHDB_ENV}=1 for an explicitly disposable Redis instance.",
        pytrace=False,
    )


@pytest_asyncio.fixture(autouse=True)
async def isolate_api_v1_redis_state() -> AsyncGenerator[None]:
    """Keep route rate-limit and token state from leaking between API v1 tests."""
    _assert_safe_api_v1_redis_flushdb()
    redis_client = await get_redis_client()
    try:
        await redis_client.flushdb()
        yield
        await redis_client.flushdb()
    finally:
        await redis_client.aclose()
