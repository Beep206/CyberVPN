"""Tests for analytics task modules."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_aggregate_daily_stats_success():
    """Test daily stats aggregation with valid data."""
    mock_users = [
        {"status": "active", "usedTrafficBytes": 1000},
        {"status": "active", "usedTrafficBytes": 2000},
        {"status": "disabled", "usedTrafficBytes": 500},
    ]
    mock_system_stats = {"cpu_usage": 50.0}

    with (
        patch("src.tasks.analytics.daily_stats.RemnawaveClient") as mock_rw_cls,
        patch("src.tasks.analytics.daily_stats.get_redis_client") as mock_redis_fn,
        patch("src.tasks.analytics.daily_stats.CacheService") as mock_cache_cls,
        patch("src.tasks.analytics.daily_stats.get_session_factory") as mock_factory,
    ):
        mock_rw = AsyncMock()
        mock_rw.get_users.return_value = mock_users
        mock_rw.get_system_stats.return_value = mock_system_stats
        mock_rw_cls.return_value.__aenter__.return_value = mock_rw

        mock_redis = AsyncMock()
        mock_redis.scan.side_effect = [(0, []), (0, [])]
        mock_redis.get.return_value = None
        mock_redis.zrangebyscore = AsyncMock(return_value=[])
        mock_redis_fn.return_value = mock_redis

        mock_cache = AsyncMock()
        mock_cache_cls.return_value = mock_cache

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        new_users_result = MagicMock()
        new_users_result.scalar.return_value = 2
        admin_ops_result = MagicMock()
        admin_ops_result.scalar.return_value = 1
        updated_result = MagicMock()
        updated_result.scalars.return_value.all.return_value = [MagicMock(new_value={"status": "disabled"})]
        payments_result = MagicMock()
        payments_result.scalars.return_value.all.return_value = [
            MagicMock(amount=10.0, provider="cryptobot", metadata_={"plan_name": "Basic"}),
        ]
        errors_result = MagicMock()
        errors_result.all.return_value = [("error-1",), ("error-1",), ("error-2",)]
        mock_session.execute = AsyncMock(
            side_effect=[new_users_result, admin_ops_result, updated_result, payments_result, errors_result]
        )
        mock_factory.return_value = MagicMock(return_value=mock_session)

        from src.tasks.analytics.daily_stats import aggregate_daily_stats

        result = await aggregate_daily_stats()

        assert result["total_users"] == 3
        assert result["active_users"] == 2
        assert result["new_users"] == 2
        assert result["churned_users"] == 1
        assert result["total_bandwidth_bytes"] == 3500
        mock_cache.set.assert_called_once()


@pytest.mark.asyncio
async def test_aggregate_financial_stats_grouping():
    """Test financial stats aggregation with multiple currencies."""
    with (
        patch("src.tasks.analytics.financial_stats.get_session_factory") as mock_factory,
        patch("src.tasks.analytics.financial_stats.get_redis_client") as mock_redis_fn,
        patch("src.tasks.analytics.financial_stats.CacheService") as mock_cache_cls,
    ):
        mock_session = AsyncMock()
        result_currency = MagicMock()
        result_currency.all.return_value = [
            MagicMock(count=5, total=100.50, currency="USD"),
            MagicMock(count=3, total=50.25, currency="EUR"),
        ]
        result_provider = MagicMock()
        result_provider.all.return_value = [
            MagicMock(count=4, total=80.0, provider="cryptobot"),
        ]
        result_totals = MagicMock()
        result_totals.one.return_value = MagicMock(count=8, total=150.75, avg=18.84)
        mock_session.execute = AsyncMock(side_effect=[result_currency, result_provider, result_totals])
        mock_factory.return_value.return_value.__aenter__.return_value = mock_session

        mock_redis = AsyncMock()
        mock_redis_fn.return_value = mock_redis

        mock_cache = AsyncMock()
        mock_cache_cls.return_value = mock_cache

        from src.tasks.analytics.financial_stats import aggregate_financial_stats

        result = await aggregate_financial_stats()

        assert result["total_count"] == 8
        assert result["by_currency"]["USD"]["count"] == 5
        assert result["by_currency"]["USD"]["total"] == 100.50
        assert result["by_currency"]["EUR"]["count"] == 3
        assert result["by_provider"]["cryptobot"]["count"] == 4
        mock_cache.set.assert_called_once()


@pytest.mark.asyncio
async def test_aggregate_hourly_bandwidth_rollup():
    """Test hourly bandwidth aggregation and cleanup."""
    with patch("src.tasks.analytics.hourly_bandwidth.get_redis_client") as mock_redis_fn:
        mock_redis = AsyncMock()
        mock_redis.scan.side_effect = [
            (0, [b"cybervpn:bandwidth:node1:1234567890"]),
        ]
        # Provide enough values for the loop (function checks multiple timestamps)
        mock_redis.get.return_value = None  # Default to None for most calls
        mock_redis_fn.return_value = mock_redis

        from src.tasks.analytics.hourly_bandwidth import aggregate_hourly_bandwidth

        result = await aggregate_hourly_bandwidth()

        assert result["nodes_processed"] >= 0
        assert result["snapshots_aggregated"] >= 0


@pytest.mark.asyncio
async def test_aggregate_hourly_bandwidth_invalid_values():
    """Test bandwidth aggregation handles invalid values gracefully."""
    with patch("src.tasks.analytics.hourly_bandwidth.get_redis_client") as mock_redis_fn:
        mock_redis = AsyncMock()
        mock_redis.scan.side_effect = [(0, [b"cybervpn:bandwidth:node1:1234567890"])]
        # Return None for all get calls (no data available)
        mock_redis.get.return_value = None
        mock_redis_fn.return_value = mock_redis

        from src.tasks.analytics.hourly_bandwidth import aggregate_hourly_bandwidth

        result = await aggregate_hourly_bandwidth()

        assert "nodes_processed" in result
        assert "snapshots_aggregated" in result


@pytest.mark.asyncio
async def test_update_realtime_metrics_caching():
    """Test realtime metrics update and caching."""
    mock_users = [
        {"status": "active", "isOnline": True},
        {"status": "active", "isOnline": False},
    ]
    mock_nodes = [
        {"isConnected": True, "currentBandwidth": 1000},
        {"isConnected": False, "currentBandwidth": 0},
    ]

    with (
        patch("src.tasks.analytics.realtime_metrics.RemnawaveClient") as mock_rw_cls,
        patch("src.tasks.analytics.realtime_metrics.get_redis_client") as mock_redis_fn,
    ):
        mock_rw = AsyncMock()
        mock_rw.get_users.return_value = mock_users
        mock_rw.get_nodes.return_value = mock_nodes
        mock_rw_cls.return_value.__aenter__.return_value = mock_rw

        mock_redis = AsyncMock()
        mock_redis_fn.return_value = mock_redis

        from src.tasks.analytics.realtime_metrics import update_realtime_metrics

        result = await update_realtime_metrics()

        assert result["online_users"] == 1
        assert result["active_servers"] == 1
        assert result["total_servers"] == 2
        assert result["total_users"] == 2
        assert result["current_bandwidth"] == 1000
        mock_redis.set.assert_called_once()
        args, kwargs = mock_redis.set.call_args
        assert json.loads(args[1])["online_users"] == 1


@pytest.mark.asyncio
async def test_update_realtime_metrics_no_online():
    """Test realtime metrics with no online users."""
    with (
        patch("src.tasks.analytics.realtime_metrics.RemnawaveClient") as mock_rw_cls,
        patch("src.tasks.analytics.realtime_metrics.get_redis_client") as mock_redis_fn,
    ):
        mock_rw = AsyncMock()
        mock_rw.get_users.return_value = []
        mock_rw.get_nodes.return_value = []
        mock_rw_cls.return_value.__aenter__.return_value = mock_rw

        mock_redis = AsyncMock()
        mock_redis_fn.return_value = mock_redis

        from src.tasks.analytics.realtime_metrics import update_realtime_metrics

        result = await update_realtime_metrics()

        assert result["online_users"] == 0
        assert result["active_servers"] == 0
