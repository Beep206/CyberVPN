"""Tests for reports task modules."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_send_daily_report_success():
    """Test daily report generation and sending."""
    mock_stats = {
        "date": "2025-01-28",
        "total_users": 100,
        "active_users": 85,
        "new_users": 10,
        "churned_users": 2,
        "revenue_usd": 500.0,
        "total_bandwidth_bytes": 1000000000,
        "server_uptime_pct": 99.9,
        "incidents": 0,
    }

    with (
        patch("src.tasks.reports.daily_report.get_redis_client") as mock_redis_fn,
        patch("src.tasks.reports.daily_report.CacheService") as mock_cache_cls,
        patch("src.tasks.reports.daily_report.TelegramClient") as mock_tg_cls,
        patch("src.tasks.reports.daily_report.publish_event", new_callable=AsyncMock) as mock_publish,
    ):
        mock_redis = AsyncMock()
        mock_redis_fn.return_value = mock_redis

        mock_cache = AsyncMock()
        mock_cache.get.return_value = mock_stats
        mock_cache_cls.return_value = mock_cache

        mock_tg = AsyncMock()
        mock_tg_cls.return_value.__aenter__.return_value = mock_tg

        from src.tasks.reports.daily_report import send_daily_report

        result = await send_daily_report()

        assert result["sent"] is True
        mock_tg.send_admin_alert.assert_called_once()
        mock_publish.assert_called_once()


@pytest.mark.asyncio
async def test_send_daily_report_no_stats():
    """Test daily report handles missing stats."""
    with (
        patch("src.tasks.reports.daily_report.get_redis_client") as mock_redis_fn,
        patch("src.tasks.reports.daily_report.CacheService") as mock_cache_cls,
    ):
        mock_redis = AsyncMock()
        mock_redis_fn.return_value = mock_redis

        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        mock_cache_cls.return_value = mock_cache

        from src.tasks.reports.daily_report import send_daily_report

        result = await send_daily_report()

        assert result["sent"] is False
        assert result["reason"] == "no_stats"


@pytest.mark.asyncio
async def test_generate_weekly_report_trends():
    """Test weekly report calculates correct trends."""
    current_week_data = [
        {"total_users": 100, "revenue_usd": 50.0, "total_bandwidth_bytes": 1000, "server_uptime_pct": 99.5},
        {"total_users": 105, "revenue_usd": 55.0, "total_bandwidth_bytes": 1100, "server_uptime_pct": 99.7},
    ]
    prev_week_data = [
        {"total_users": 90, "revenue_usd": 45.0, "total_bandwidth_bytes": 900, "server_uptime_pct": 99.0},
        {"total_users": 95, "revenue_usd": 48.0, "total_bandwidth_bytes": 950, "server_uptime_pct": 99.2},
    ]

    with (
        patch("src.tasks.reports.weekly_report.get_redis_client") as mock_redis_fn,
        patch("src.tasks.reports.weekly_report.TelegramClient") as mock_tg_cls,
        patch("src.tasks.reports.weekly_report.publish_event", new_callable=AsyncMock) as mock_publish,
    ):
        mock_redis = AsyncMock()

        # Mock redis.get to return JSON-encoded stats
        def get_side_effect(key):
            if "2025-01-22" in key or "2025-01-23" in key:
                return json.dumps(current_week_data[0])
            elif "2025-01-15" in key or "2025-01-16" in key:
                return json.dumps(prev_week_data[0])
            return None

        mock_redis.get.side_effect = get_side_effect
        mock_redis_fn.return_value = mock_redis

        mock_tg = AsyncMock()
        mock_tg_cls.return_value.__aenter__.return_value = mock_tg

        from src.tasks.reports.weekly_report import generate_weekly_report

        result = await generate_weekly_report()

        assert result["report_sent"] is True
        assert "user_growth_pct" in result
        assert "revenue_growth_pct" in result
        mock_tg.send_admin_alert.assert_called_once()
        mock_publish.assert_called_once()


@pytest.mark.asyncio
async def test_generate_weekly_report_no_data():
    """Test weekly report handles missing data gracefully."""
    with (
        patch("src.tasks.reports.weekly_report.get_redis_client") as mock_redis_fn,
        patch("src.tasks.reports.weekly_report.TelegramClient") as mock_tg_cls,
        patch("src.tasks.reports.weekly_report.publish_event", new_callable=AsyncMock) as mock_publish,
    ):
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis_fn.return_value = mock_redis

        mock_tg = AsyncMock()
        mock_tg_cls.return_value.__aenter__.return_value = mock_tg

        from src.tasks.reports.weekly_report import generate_weekly_report

        result = await generate_weekly_report()

        assert result["report_sent"] is True
        assert result["user_growth_pct"] == 0


@pytest.mark.asyncio
async def test_check_anomalies_server_offline():
    """Test anomaly detection for offline servers."""
    with (
        patch("src.tasks.reports.anomaly_alert.get_redis_client") as mock_redis_fn,
        patch("src.tasks.reports.anomaly_alert.TelegramClient") as mock_tg_cls,
    ):
        mock_redis = AsyncMock()
        mock_redis.scan.side_effect = [
            (0, [b"cybervpn:health:node1:current"]),
        ]
        health_data = json.dumps({"is_online": False, "name": "Server 1"})
        mock_redis.get.return_value = health_data
        mock_redis_fn.return_value = mock_redis

        mock_tg = AsyncMock()
        mock_tg_cls.return_value.__aenter__.return_value = mock_tg

        from src.tasks.reports.anomaly_alert import check_anomalies

        result = await check_anomalies()

        assert result["alerts_sent"] >= 1
        mock_tg.send_admin_alert.assert_called()


@pytest.mark.asyncio
async def test_check_anomalies_error_rate():
    """Test anomaly detection for high error rate."""
    with (
        patch("src.tasks.reports.anomaly_alert.get_redis_client") as mock_redis_fn,
        patch("src.tasks.reports.anomaly_alert.TelegramClient") as mock_tg_cls,
    ):
        mock_redis = AsyncMock()
        mock_redis.scan.return_value = (0, [])

        def get_side_effect(key):
            if "error_rate" in key:
                return b"10.5"
            return None

        mock_redis.get.side_effect = get_side_effect
        mock_redis_fn.return_value = mock_redis

        mock_tg = AsyncMock()
        mock_tg_cls.return_value.__aenter__.return_value = mock_tg

        from src.tasks.reports.anomaly_alert import check_anomalies

        result = await check_anomalies()

        assert result["alerts_sent"] >= 1


@pytest.mark.asyncio
async def test_check_anomalies_queue_depth():
    """Test anomaly detection for high queue depth."""
    with (
        patch("src.tasks.reports.anomaly_alert.get_redis_client") as mock_redis_fn,
        patch("src.tasks.reports.anomaly_alert.TelegramClient") as mock_tg_cls,
    ):
        mock_redis = AsyncMock()
        mock_redis.scan.return_value = (0, [])

        def get_side_effect(key):
            if "queue_depth" in key:
                return b"750"
            return None

        mock_redis.get.side_effect = get_side_effect
        mock_redis_fn.return_value = mock_redis

        mock_tg = AsyncMock()
        mock_tg_cls.return_value.__aenter__.return_value = mock_tg

        from src.tasks.reports.anomaly_alert import check_anomalies

        result = await check_anomalies()

        assert result["alerts_sent"] >= 1
