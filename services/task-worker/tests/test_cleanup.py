"""Tests for cleanup task modules."""

import os
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_cleanup_old_records_deletes_both():
    """Test cleanup deletes both audit and webhook logs."""
    # Import the function first
    from src.tasks.cleanup.cleanup_old_records import cleanup_old_records

    with patch("src.tasks.cleanup.cleanup_old_records.get_session_factory") as mock_factory, \
         patch("src.tasks.cleanup.cleanup_old_records.get_settings") as mock_settings:

        mock_settings.return_value.cleanup_audit_retention_days = 90
        mock_settings.return_value.cleanup_webhook_retention_days = 30

        mock_session = AsyncMock()
        mock_audit_result = MagicMock(rowcount=10)
        mock_webhook_result = MagicMock(rowcount=5)
        mock_session.execute.side_effect = [mock_audit_result, mock_webhook_result]
        mock_factory.return_value.return_value.__aenter__.return_value = mock_session

        result = await cleanup_old_records()

        assert result["audit_deleted"] == 10
        assert result["webhook_deleted"] == 5
        assert mock_session.execute.call_count == 2
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_expired_tokens_batch():
    """Test token cleanup processes in batches."""
    from src.tasks.cleanup.tokens import cleanup_expired_tokens

    with patch("src.tasks.cleanup.tokens.get_session_factory") as mock_factory:
        mock_session = AsyncMock()
        mock_result1 = MagicMock(rowcount=1000)
        mock_result2 = MagicMock(rowcount=500)
        mock_result3 = MagicMock(rowcount=0)
        mock_session.execute.side_effect = [mock_result1, mock_result2, mock_result3]
        mock_factory.return_value.return_value.__aenter__.return_value = mock_session

        result = await cleanup_expired_tokens()

        assert result["deleted"] == 1500
        assert mock_session.execute.call_count == 2


@pytest.mark.asyncio
async def test_cleanup_audit_logs_retention():
    """Test audit log cleanup respects retention period."""
    from src.tasks.cleanup.audit_logs import cleanup_audit_logs

    with patch("src.tasks.cleanup.audit_logs.get_session_factory") as mock_factory, \
         patch("src.tasks.cleanup.audit_logs.get_settings") as mock_settings:

        mock_settings.return_value.cleanup_audit_retention_days = 90

        mock_session = AsyncMock()
        mock_result = MagicMock(rowcount=25)
        mock_session.execute.return_value = mock_result
        mock_factory.return_value.return_value.__aenter__.return_value = mock_session

        result = await cleanup_audit_logs()

        assert result["deleted"] == 25
        assert result["retention_days"] == 90


@pytest.mark.asyncio
async def test_cleanup_webhook_logs_batch():
    """Test webhook log cleanup in batches."""
    from src.tasks.cleanup.webhook_logs import cleanup_webhook_logs

    with patch("src.tasks.cleanup.webhook_logs.get_session_factory") as mock_factory, \
         patch("src.tasks.cleanup.webhook_logs.get_settings") as mock_settings:

        mock_settings.return_value.cleanup_webhook_retention_days = 30

        mock_session = AsyncMock()
        mock_result = MagicMock(rowcount=100)
        mock_session.execute.return_value = mock_result
        mock_factory.return_value.return_value.__aenter__.return_value = mock_session

        result = await cleanup_webhook_logs()

        assert result["deleted"] == 100


@pytest.mark.asyncio
async def test_cleanup_notifications_old_only():
    """Test notifications cleanup only deletes old sent/failed."""
    from src.tasks.cleanup.notifications import cleanup_notifications

    with patch("src.tasks.cleanup.notifications.get_session_factory") as mock_factory:
        mock_session = AsyncMock()
        mock_result = MagicMock(rowcount=15)
        mock_session.execute.return_value = mock_result
        mock_factory.return_value.return_value.__aenter__.return_value = mock_session

        result = await cleanup_notifications()

        assert result["deleted"] == 15


@pytest.mark.asyncio
async def test_cleanup_cache_patterns():
    """Test cache cleanup processes multiple patterns."""
    from src.tasks.cleanup.cache import cleanup_cache

    with patch("src.tasks.cleanup.cache.get_redis_client") as mock_redis_fn, \
         patch("src.tasks.cleanup.cache._scan_and_delete_by_date") as mock_scan_date, \
         patch("src.tasks.cleanup.cache._scan_and_delete_pattern") as mock_scan_pattern, \
         patch("src.tasks.cleanup.cache._scan_and_delete_by_timestamp") as mock_scan_ts:

        mock_redis = AsyncMock()
        mock_redis_fn.return_value = mock_redis

        mock_scan_date.return_value = 10
        mock_scan_pattern.return_value = 5
        mock_scan_ts.side_effect = [3, 7]

        result = await cleanup_cache()

        assert result["total_deleted"] == 25
        assert result["stats_deleted"] == 10
        assert result["health_deleted"] == 5
        assert result["bandwidth_raw_deleted"] == 3
        assert result["bandwidth_hourly_deleted"] == 7


@pytest.mark.asyncio
async def test_cleanup_cache_scan_and_delete_by_date():
    """Test cache deletion by date pattern."""
    from src.tasks.cleanup.cache import _scan_and_delete_by_date

    with patch("src.tasks.cleanup.cache.get_redis_client") as mock_redis_fn:
        mock_redis = AsyncMock()
        mock_redis.scan.side_effect = [
            (100, [b"cybervpn:stats:daily:2023-01-01"]),
            (0, [b"cybervpn:stats:daily:2025-01-01"]),
        ]
        mock_redis.unlink.return_value = 1
        mock_redis_fn.return_value = mock_redis

        cutoff = datetime(2024, 1, 1, tzinfo=timezone.utc)
        result = await _scan_and_delete_by_date(mock_redis, "cybervpn:stats:daily:*", cutoff)

        assert result == 1


@pytest.mark.asyncio
async def test_cleanup_export_files_removes_old():
    """Test export file cleanup removes old files."""
    from src.tasks.cleanup.export_files import cleanup_export_files

    with patch("src.tasks.cleanup.export_files.os.path.exists") as mock_exists, \
         patch("src.tasks.cleanup.export_files.os.listdir") as mock_listdir, \
         patch("src.tasks.cleanup.export_files.os.path.isfile") as mock_isfile, \
         patch("src.tasks.cleanup.export_files.os.path.getmtime") as mock_getmtime, \
         patch("src.tasks.cleanup.export_files.os.path.getsize") as mock_getsize, \
         patch("src.tasks.cleanup.export_files.os.remove") as mock_remove:

        mock_exists.return_value = True
        mock_listdir.return_value = ["old_file.csv", "new_file.csv"]
        mock_isfile.return_value = True

        old_time = time.time() - 100000  # Older than 24h
        new_time = time.time() - 1000    # Recent
        mock_getmtime.side_effect = [old_time, new_time]
        mock_getsize.return_value = 1024

        result = await cleanup_export_files()

        assert result["deleted"] == 1
        assert result["errors"] == 0
        assert result["size_freed_bytes"] == 1024
        mock_remove.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_export_files_no_directory():
    """Test export cleanup creates directory if missing."""
    from src.tasks.cleanup.export_files import cleanup_export_files

    with patch("src.tasks.cleanup.export_files.os.path.exists") as mock_exists, \
         patch("src.tasks.cleanup.export_files.os.makedirs") as mock_makedirs:

        mock_exists.return_value = False

        result = await cleanup_export_files()

        assert result["deleted"] == 0
        mock_makedirs.assert_called_once()
