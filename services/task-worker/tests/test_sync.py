"""Tests for sync task modules."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_sync_nodes_caching():
    """Test node sync caches all nodes."""
    mock_nodes = [
        {"uuid": "node-1", "name": "Server 1"},
        {"uuid": "node-2", "name": "Server 2"},
    ]

    with patch("src.tasks.sync.sync_nodes.RemnawaveClient") as mock_rw_cls, \
         patch("src.tasks.sync.sync_nodes.get_redis_client") as mock_redis_fn, \
         patch("src.tasks.sync.sync_nodes.CacheService") as mock_cache_cls:

        mock_rw = AsyncMock()
        mock_rw.get_nodes.return_value = mock_nodes
        mock_rw_cls.return_value.__aenter__.return_value = mock_rw

        mock_redis = AsyncMock()
        mock_redis_fn.return_value = mock_redis

        mock_cache = AsyncMock()
        mock_cache_cls.return_value = mock_cache

        from src.tasks.sync.sync_nodes import sync_node_configs

        result = await sync_node_configs()

        assert result["synced"] == 2
        assert mock_cache.set.call_count == 2


@pytest.mark.asyncio
async def test_sync_geolocations_upsert():
    """Test geolocation sync upserts nodes with coordinates."""
    mock_nodes = [
        {"uuid": "550e8400-e29b-41d4-a716-446655440000", "country_code": "US", "city": "New York"},
        {"uuid": "650e8400-e29b-41d4-a716-446655440001", "country_code": "GB", "city": "London"},
    ]

    with patch("src.tasks.sync.geolocations.RemnawaveClient") as mock_rw_cls, \
         patch("src.tasks.sync.geolocations.get_session_factory") as mock_factory, \
         patch("src.tasks.sync.geolocations.COUNTRY_COORDS", {"US": (37.0902, -95.7129), "GB": (51.5074, -0.1278)}):

        mock_rw = AsyncMock()
        mock_rw.get_nodes.return_value = mock_nodes
        mock_rw_cls.return_value.__aenter__.return_value = mock_rw

        mock_session = AsyncMock()
        mock_factory.return_value.return_value.__aenter__.return_value = mock_session

        from src.tasks.sync.geolocations import sync_server_geolocations

        result = await sync_server_geolocations()

        assert result["synced"] == 2
        assert mock_session.execute.call_count == 2
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_sync_geolocations_unknown_country():
    """Test geolocation sync skips nodes with unknown country codes."""
    mock_nodes = [
        {"uuid": "550e8400-e29b-41d4-a716-446655440000", "country_code": "XX", "city": "Unknown"},
        {"uuid": "650e8400-e29b-41d4-a716-446655440001", "country_code": "US", "city": "New York"},
    ]

    with patch("src.tasks.sync.geolocations.RemnawaveClient") as mock_rw_cls, \
         patch("src.tasks.sync.geolocations.get_session_factory") as mock_factory, \
         patch("src.tasks.sync.geolocations.COUNTRY_COORDS", {"US": (37.0902, -95.7129)}):

        mock_rw = AsyncMock()
        mock_rw.get_nodes.return_value = mock_nodes
        mock_rw_cls.return_value.__aenter__.return_value = mock_rw

        mock_session = AsyncMock()
        mock_factory.return_value.return_value.__aenter__.return_value = mock_session

        from src.tasks.sync.geolocations import sync_server_geolocations

        result = await sync_server_geolocations()

        assert result["synced"] == 1


@pytest.mark.asyncio
async def test_sync_user_stats_aggregation():
    """Test user stats sync aggregates all categories."""
    mock_users = [
        {"status": "active", "is_online": True, "expire_at": None, "traffic_limit_bytes": 0, "used_traffic_bytes": 0},
        {
            "status": "active",
            "is_online": False,
            "expire_at": "2023-01-01T00:00:00Z",
            "traffic_limit_bytes": 1000,
            "used_traffic_bytes": 1500,
        },
        {
            "status": "disabled",
            "is_online": False,
            "expire_at": None,
            "traffic_limit_bytes": 0,
            "used_traffic_bytes": 0,
        },
    ]

    with patch("src.tasks.sync.user_stats.RemnawaveClient") as mock_rw_cls, \
         patch("src.tasks.sync.user_stats.get_redis_client") as mock_redis_fn, \
         patch("src.tasks.sync.user_stats.CacheService") as mock_cache_cls:

        mock_rw = AsyncMock()
        mock_rw.get_users.return_value = mock_users
        mock_rw_cls.return_value.__aenter__.return_value = mock_rw

        mock_redis = AsyncMock()
        mock_redis_fn.return_value = mock_redis

        mock_cache = AsyncMock()
        mock_cache_cls.return_value = mock_cache

        from src.tasks.sync.user_stats import sync_user_stats

        result = await sync_user_stats()

        assert result["total"] == 3
        assert result["active"] == 2
        assert result["disabled"] == 1
        assert result["online"] == 1
        assert result["expired"] == 1
        assert result["limited"] == 1
        mock_cache.set.assert_called_once()


@pytest.mark.asyncio
async def test_sync_user_stats_no_users():
    """Test user stats sync with empty user list."""
    with patch("src.tasks.sync.user_stats.RemnawaveClient") as mock_rw_cls, \
         patch("src.tasks.sync.user_stats.get_redis_client") as mock_redis_fn, \
         patch("src.tasks.sync.user_stats.CacheService") as mock_cache_cls:

        mock_rw = AsyncMock()
        mock_rw.get_users.return_value = []
        mock_rw_cls.return_value.__aenter__.return_value = mock_rw

        mock_redis = AsyncMock()
        mock_redis_fn.return_value = mock_redis

        mock_cache = AsyncMock()
        mock_cache_cls.return_value = mock_cache

        from src.tasks.sync.user_stats import sync_user_stats

        result = await sync_user_stats()

        assert result["total"] == 0
        assert result["active"] == 0


@pytest.mark.asyncio
async def test_sync_node_configurations_ttl():
    """Test node config sync sets correct TTL."""
    mock_nodes = [
        {"uuid": "node-1", "name": "Server 1"},
    ]

    with patch("src.tasks.sync.node_configs.RemnawaveClient") as mock_rw_cls, \
         patch("src.tasks.sync.node_configs.get_redis_client") as mock_redis_fn, \
         patch("src.tasks.sync.node_configs.CacheService") as mock_cache_cls:

        mock_rw = AsyncMock()
        mock_rw.get_nodes.return_value = mock_nodes
        mock_rw_cls.return_value.__aenter__.return_value = mock_rw

        mock_redis = AsyncMock()
        mock_redis_fn.return_value = mock_redis

        mock_cache = AsyncMock()
        mock_cache_cls.return_value = mock_cache

        from src.tasks.sync.node_configs import sync_node_configurations

        result = await sync_node_configurations()

        assert result["synced"] == 1
        # Verify cache.set was called with correct TTL (CacheService adds prefix)
        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args
        assert call_args[1]["ttl"] == 2100
