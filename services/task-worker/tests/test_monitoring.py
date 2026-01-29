"""Unit tests for monitoring tasks."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Set required environment variables before importing modules
os.environ.setdefault("REMNAWAVE_API_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:test-bot")
os.environ.setdefault("CRYPTOBOT_TOKEN", "test-crypto")

from src.tasks.monitoring.health_check import check_server_health
from src.tasks.monitoring.bandwidth import collect_bandwidth_snapshot
from src.tasks.monitoring.services_health import check_external_services


@pytest.mark.asyncio
async def test_health_check_all_nodes_healthy(mock_redis, mock_remnawave, mock_telegram):
    """Test health check with all nodes online."""
    nodes = [
        {
            "uuid": "node-1",
            "name": "US-East",
            "isConnected": True,
            "countryCode": "US",
        },
        {
            "uuid": "node-2",
            "name": "EU-West",
            "isConnected": True,
            "countryCode": "NL",
        },
    ]
    mock_remnawave.get_nodes.return_value = nodes

    # Mock cache returns to simulate all nodes were previously online
    mock_cache_data = MagicMock()
    mock_cache_data.get = MagicMock(return_value={"is_online": True, "name": "US-East", "country": "US"})

    with (
        patch("src.tasks.monitoring.health_check.get_redis_client", return_value=mock_redis),
        patch("src.tasks.monitoring.health_check.CacheService") as MockCache,
        patch("src.tasks.monitoring.health_check.RemnawaveClient") as MockRW,
        patch("src.tasks.monitoring.health_check.TelegramClient") as MockTg,
        patch("src.tasks.monitoring.health_check.publish_event", new_callable=AsyncMock) as mock_publish,
    ):
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(
            side_effect=[
                {"status": "online"},
                {"status": "online"},
            ]
        )
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        MockRW.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        MockRW.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await check_server_health()

        assert result["nodes_checked"] == 2
        assert result["alerts_sent"] == 0
        mock_telegram.send_admin_alert.assert_not_called()


@pytest.mark.asyncio
async def test_health_check_node_goes_offline(mock_redis, mock_remnawave, mock_telegram):
    """Test health check detects node going offline and sends alert."""
    nodes = [
        {
            "uuid": "node-1",
            "name": "US-East",
            "isConnected": False,  # Now offline
            "countryCode": "US",
        },
    ]
    mock_remnawave.get_nodes.return_value = nodes

    with (
        patch("src.tasks.monitoring.health_check.get_redis_client", return_value=mock_redis),
        patch("src.tasks.monitoring.health_check.CacheService") as MockCache,
        patch("src.tasks.monitoring.health_check.RemnawaveClient") as MockRW,
        patch("src.tasks.monitoring.health_check.TelegramClient") as MockTg,
        patch("src.tasks.monitoring.health_check.publish_event", new_callable=AsyncMock) as mock_publish,
    ):
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(return_value={"status": "online"})  # Was online
        mock_cache.set = AsyncMock()
        mock_cache.add_to_sorted_set = AsyncMock()
        MockCache.return_value = mock_cache

        MockRW.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        MockRW.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await check_server_health()

        assert result["nodes_checked"] == 1
        assert result["alerts_sent"] == 1
        mock_telegram.send_admin_alert.assert_called_once()
        call_args = mock_telegram.send_admin_alert.call_args
        assert "US-East" in call_args[0][0]
        assert call_args[1]["severity"] == "critical"


@pytest.mark.asyncio
async def test_health_check_node_recovers(mock_redis, mock_remnawave, mock_telegram):
    """Test health check detects node recovery and sends recovery alert."""
    nodes = [
        {
            "uuid": "node-1",
            "name": "US-East",
            "isConnected": True,  # Back online
            "countryCode": "US",
        },
    ]
    mock_remnawave.get_nodes.return_value = nodes

    with (
        patch("src.tasks.monitoring.health_check.get_redis_client", return_value=mock_redis),
        patch("src.tasks.monitoring.health_check.CacheService") as MockCache,
        patch("src.tasks.monitoring.health_check.RemnawaveClient") as MockRW,
        patch("src.tasks.monitoring.health_check.TelegramClient") as MockTg,
        patch("src.tasks.monitoring.health_check.publish_event", new_callable=AsyncMock) as mock_publish,
    ):
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(return_value={"status": "offline"})  # Was offline
        mock_cache.set = AsyncMock()
        mock_cache.add_to_sorted_set = AsyncMock()
        MockCache.return_value = mock_cache

        MockRW.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        MockRW.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await check_server_health()

        assert result["nodes_checked"] == 1
        assert result["alerts_sent"] == 1
        mock_telegram.send_admin_alert.assert_called_once()
        call_args = mock_telegram.send_admin_alert.call_args
        assert call_args[1]["severity"] == "resolved"


@pytest.mark.asyncio
async def test_health_check_first_run_no_cache(mock_redis, mock_remnawave, mock_telegram):
    """Test health check when no previous state exists (first run)."""
    nodes = [
        {
            "uuid": "node-1",
            "name": "US-East",
            "isConnected": False,
            "countryCode": "US",
        },
    ]
    mock_remnawave.get_nodes.return_value = nodes

    with (
        patch("src.tasks.monitoring.health_check.get_redis_client", return_value=mock_redis),
        patch("src.tasks.monitoring.health_check.CacheService") as MockCache,
        patch("src.tasks.monitoring.health_check.RemnawaveClient") as MockRW,
        patch("src.tasks.monitoring.health_check.TelegramClient") as MockTg,
        patch("src.tasks.monitoring.health_check.publish_event", new_callable=AsyncMock) as mock_publish,
    ):
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(return_value=None)  # No previous state
        mock_cache.set = AsyncMock()
        mock_cache.add_to_sorted_set = AsyncMock()
        MockCache.return_value = mock_cache

        MockRW.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        MockRW.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await check_server_health()

        assert result["nodes_checked"] == 1
        assert result["alerts_sent"] == 1  # Alerts because default is True (was online)


@pytest.mark.asyncio
async def test_bandwidth_collects_snapshots(mock_redis, mock_remnawave):
    """Test bandwidth snapshot collection from nodes."""
    nodes = [
        {
            "uuid": "node-1",
            "trafficUp": 1000000,
            "trafficDown": 5000000,
        },
        {
            "uuid": "node-2",
            "trafficUp": 2000000,
            "trafficDown": 8000000,
        },
    ]
    mock_remnawave.get_nodes.return_value = nodes

    with (
        patch("src.tasks.monitoring.bandwidth.get_redis_client", return_value=mock_redis),
        patch("src.tasks.monitoring.bandwidth.CacheService") as MockCache,
        patch("src.tasks.monitoring.bandwidth.RemnawaveClient") as MockRW,
    ):
        mock_cache = MagicMock()
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        MockRW.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        MockRW.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await collect_bandwidth_snapshot()

        assert result["nodes"] == 2
        assert result["total_up"] == 3000000
        assert result["total_down"] == 13000000
        assert mock_cache.set.call_count == 3  # 2 nodes + 1 dashboard


@pytest.mark.asyncio
async def test_bandwidth_updates_dashboard_cache(mock_redis, mock_remnawave):
    """Test bandwidth collection updates real-time dashboard cache."""
    nodes = [
        {
            "uuid": "node-1",
            "trafficUp": 100,
            "trafficDown": 200,
        },
    ]
    mock_remnawave.get_nodes.return_value = nodes

    with (
        patch("src.tasks.monitoring.bandwidth.get_redis_client", return_value=mock_redis),
        patch("src.tasks.monitoring.bandwidth.CacheService") as MockCache,
        patch("src.tasks.monitoring.bandwidth.RemnawaveClient") as MockRW,
    ):
        mock_cache = MagicMock()
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        MockRW.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        MockRW.return_value.__aexit__ = AsyncMock(return_value=False)

        await collect_bandwidth_snapshot()

        # Check dashboard cache update
        calls = mock_cache.set.call_args_list
        dashboard_call = calls[-1]  # Last call should be dashboard
        cache_data = dashboard_call[0][1]

        assert cache_data["total_up"] == 100
        assert cache_data["total_down"] == 200
        assert cache_data["nodes_count"] == 1
        assert "timestamp" in cache_data
        assert dashboard_call[1]["ttl"] == 120


@pytest.mark.asyncio
async def test_bandwidth_handles_null_traffic(mock_redis, mock_remnawave):
    """Test bandwidth collection handles None traffic values."""
    nodes = [
        {
            "uuid": "node-1",
            "trafficUp": None,
            "trafficDown": None,
        },
        {
            "uuid": "node-2",
            "trafficUp": 1000,
            "trafficDown": 2000,
        },
    ]
    mock_remnawave.get_nodes.return_value = nodes

    with (
        patch("src.tasks.monitoring.bandwidth.get_redis_client", return_value=mock_redis),
        patch("src.tasks.monitoring.bandwidth.CacheService") as MockCache,
        patch("src.tasks.monitoring.bandwidth.RemnawaveClient") as MockRW,
    ):
        mock_cache = MagicMock()
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        MockRW.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        MockRW.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await collect_bandwidth_snapshot()

        assert result["nodes"] == 2
        assert result["total_up"] == 1000  # None treated as 0
        assert result["total_down"] == 2000


@pytest.mark.asyncio
async def test_services_health_all_services_up(mock_redis, mock_remnawave, mock_telegram):
    """Test services health check when all services are healthy."""
    with (
        patch("src.tasks.monitoring.services_health.get_redis_client", return_value=mock_redis),
        patch("src.tasks.monitoring.services_health.CacheService") as MockCache,
        patch("src.tasks.monitoring.services_health.check_db_connection", return_value=True),
        patch("src.tasks.monitoring.services_health.check_redis", return_value=True),
        patch("src.tasks.monitoring.services_health.RemnawaveClient") as MockRW,
        patch("src.tasks.monitoring.services_health.TelegramClient") as MockTg,
    ):
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(
            return_value={
                "database": True,
                "redis": True,
                "remnawave": True,
                "telegram": True,
            }
        )
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        mock_remnawave.health_check.return_value = True
        MockRW.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        MockRW.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_telegram.health_check.return_value = True
        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await check_external_services()

        assert result["database"] is True
        assert result["redis"] is True
        assert result["remnawave"] is True
        assert result["telegram"] is True
        mock_telegram.send_admin_alert.assert_not_called()


@pytest.mark.asyncio
async def test_services_health_service_down_triggers_alert(mock_redis, mock_remnawave, mock_telegram):
    """Test services health check sends alert when service goes down."""
    with (
        patch("src.tasks.monitoring.services_health.get_redis_client", return_value=mock_redis),
        patch("src.tasks.monitoring.services_health.CacheService") as MockCache,
        patch("src.tasks.monitoring.services_health.check_db_connection", return_value=False),
        patch("src.tasks.monitoring.services_health.check_redis", return_value=True),
        patch("src.tasks.monitoring.services_health.RemnawaveClient") as MockRW,
        patch("src.tasks.monitoring.services_health.TelegramClient") as MockTg,
    ):
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(
            return_value={
                "database": True,  # Was up
                "redis": True,
                "remnawave": True,
                "telegram": True,
            }
        )
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        mock_remnawave.health_check.return_value = True
        MockRW.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        MockRW.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_telegram.health_check.return_value = True
        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await check_external_services()

        assert result["database"] is False
        mock_telegram.send_admin_alert.assert_called_once()
        call_args = mock_telegram.send_admin_alert.call_args
        assert "database" in call_args[0][0]
        assert call_args[1]["severity"] == "critical"


@pytest.mark.asyncio
async def test_services_health_service_recovers(mock_redis, mock_remnawave, mock_telegram):
    """Test services health check sends recovery alert."""
    with (
        patch("src.tasks.monitoring.services_health.get_redis_client", return_value=mock_redis),
        patch("src.tasks.monitoring.services_health.CacheService") as MockCache,
        patch("src.tasks.monitoring.services_health.check_db_connection", return_value=True),
        patch("src.tasks.monitoring.services_health.check_redis", return_value=True),
        patch("src.tasks.monitoring.services_health.RemnawaveClient") as MockRW,
        patch("src.tasks.monitoring.services_health.TelegramClient") as MockTg,
    ):
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(
            return_value={
                "database": False,  # Was down
                "redis": True,
                "remnawave": True,
                "telegram": True,
            }
        )
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        mock_remnawave.health_check.return_value = True
        MockRW.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        MockRW.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_telegram.health_check.return_value = True
        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await check_external_services()

        assert result["database"] is True
        mock_telegram.send_admin_alert.assert_called_once()
        call_args = mock_telegram.send_admin_alert.call_args
        assert call_args[1]["severity"] == "resolved"


@pytest.mark.asyncio
async def test_services_health_handles_exceptions(mock_redis, mock_remnawave, mock_telegram):
    """Test services health check handles API exceptions gracefully."""
    with (
        patch("src.tasks.monitoring.services_health.get_redis_client", return_value=mock_redis),
        patch("src.tasks.monitoring.services_health.CacheService") as MockCache,
        patch("src.tasks.monitoring.services_health.check_db_connection", return_value=True),
        patch("src.tasks.monitoring.services_health.check_redis", return_value=True),
        patch("src.tasks.monitoring.services_health.RemnawaveClient") as MockRW,
        patch("src.tasks.monitoring.services_health.TelegramClient") as MockTg,
    ):
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        # Remnawave throws exception
        mock_remnawave.health_check.side_effect = Exception("Connection error")
        MockRW.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        MockRW.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_telegram.health_check.return_value = True
        MockTg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await check_external_services()

        assert result["database"] is True
        assert result["redis"] is True
        assert result["remnawave"] is False  # Exception = False
        assert result["telegram"] is True
