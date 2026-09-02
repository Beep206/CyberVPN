"""Tests for cleanup task modules."""

import os
import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_cleanup_old_records_deletes_both():
    """Test cleanup deletes both audit and webhook logs."""
    # Import the function first
    from src.tasks.cleanup.cleanup_old_records import cleanup_old_records

    with (
        patch("src.tasks.cleanup.cleanup_old_records.get_session_factory") as mock_factory,
        patch("src.tasks.cleanup.cleanup_old_records.get_settings") as mock_settings,
    ):
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

    with (
        patch("src.tasks.cleanup.audit_logs.get_session_factory") as mock_factory,
        patch("src.tasks.cleanup.audit_logs.get_settings") as mock_settings,
    ):
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

    with (
        patch("src.tasks.cleanup.webhook_logs.get_session_factory") as mock_factory,
        patch("src.tasks.cleanup.webhook_logs.get_settings") as mock_settings,
    ):
        mock_settings.return_value.cleanup_webhook_retention_days = 30

        mock_session = AsyncMock()
        mock_result = MagicMock(rowcount=100)
        mock_session.execute.return_value = mock_result
        mock_factory.return_value.return_value.__aenter__.return_value = mock_session

        result = await cleanup_webhook_logs()

        assert result["deleted"] == 100


@pytest.mark.asyncio
async def test_cleanup_webhook_logs_uses_bounded_committed_chunks() -> None:
    """A backlog larger than one batch never becomes one unbounded DELETE."""

    from sqlalchemy.dialects import postgresql

    from src.tasks.cleanup.webhook_logs import cleanup_webhook_logs

    with (
        patch("src.tasks.cleanup.webhook_logs.get_session_factory") as mock_factory,
        patch("src.tasks.cleanup.webhook_logs.get_settings") as mock_settings,
    ):
        mock_settings.return_value.cleanup_webhook_retention_days = 30
        mock_session = AsyncMock()
        mock_session.execute.side_effect = [
            MagicMock(rowcount=1000),
            MagicMock(rowcount=1000),
            MagicMock(rowcount=25),
        ]
        mock_factory.return_value.return_value.__aenter__.return_value = mock_session

        result = await cleanup_webhook_logs()

    assert result["deleted"] == 2025
    assert mock_session.execute.await_count == 3
    assert mock_session.commit.await_count == 3
    for execute_call in mock_session.execute.await_args_list:
        compiled = str(
            execute_call.args[0].compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        ).lower()
        assert "limit 1000" in compiled


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

    with (
        patch("src.tasks.cleanup.cache.get_redis_client") as mock_redis_fn,
        patch("src.tasks.cleanup.cache._scan_and_delete_by_date") as mock_scan_date,
        patch("src.tasks.cleanup.cache._scan_and_delete_pattern") as mock_scan_pattern,
        patch("src.tasks.cleanup.cache._cleanup_health_history") as mock_cleanup_health,
        patch("src.tasks.cleanup.cache._scan_and_delete_by_timestamp") as mock_scan_ts,
    ):
        mock_redis = AsyncMock()
        mock_redis_fn.return_value = mock_redis

        mock_scan_date.return_value = 10
        mock_scan_pattern.return_value = 5
        mock_cleanup_health.return_value = 5
        mock_scan_ts.side_effect = [3, 7]

        result = await cleanup_cache()

        assert result["total_deleted"] == 30
        assert result["stats_deleted"] == 10
        assert result["cache_deleted"] == 5
        assert result["health_deleted"] == 5
        assert result["bandwidth_raw_deleted"] == 3
        assert result["bandwidth_hourly_deleted"] == 7


@pytest.mark.asyncio
async def test_remnawave_stream_retention_commits_bounded_backend_batches():
    from src.services.backend_api_client import BackendRemnawaveRetentionResult
    from src.tasks.cleanup.remnawave_stream_retention import purge_remnawave_stream_retention

    first_counts = {
        "remnawave_stream_receipts": 2,
        "remnawave_stream_dead_letters": 0,
        "remnawave_user_usage_hourly": 0,
        "remnawave_subscription_request_events": 0,
        "remnawave_node_user_presence": 0,
        "remnawave_node_connections_hourly": 0,
    }
    second_counts = {name: 0 for name in first_counts}
    second_counts["remnawave_stream_dead_letters"] = 1
    receipts = [
        BackendRemnawaveRetentionResult(
            deleted_by_table=first_counts,
            total_deleted=2,
            has_more=True,
            purged_at=datetime(2026, 8, 30, 12, 0, tzinfo=UTC),
        ),
        BackendRemnawaveRetentionResult(
            deleted_by_table=second_counts,
            total_deleted=1,
            has_more=False,
            purged_at=datetime(2026, 8, 30, 12, 0, 1, tzinfo=UTC),
        ),
    ]

    with (
        patch("src.tasks.cleanup.remnawave_stream_retention.get_settings") as settings_fn,
        patch("src.tasks.cleanup.remnawave_stream_retention.BackendAPIClient") as backend_cls,
    ):
        settings_fn.return_value.remnawave_stream_retention_enabled = True
        settings_fn.return_value.remnawave_stream_retention_batch_limit = 1000
        settings_fn.return_value.remnawave_stream_retention_max_batches = 20
        backend = AsyncMock()
        backend.purge_remnawave_stream_retention.side_effect = receipts
        backend_cls.return_value.__aenter__.return_value = backend

        result = await purge_remnawave_stream_retention()

    assert result["total_deleted"] == 3
    assert result["batches"] == 2
    assert result["has_more"] is False
    assert result["deleted_by_table"] == {
        **first_counts,
        "remnawave_stream_dead_letters": 1,
    }
    assert backend.purge_remnawave_stream_retention.await_count == 2


@pytest.mark.asyncio
async def test_remnawave_stream_retention_disabled_is_noop():
    from src.tasks.cleanup.remnawave_stream_retention import purge_remnawave_stream_retention

    with (
        patch("src.tasks.cleanup.remnawave_stream_retention.get_settings") as settings_fn,
        patch("src.tasks.cleanup.remnawave_stream_retention.BackendAPIClient") as backend_cls,
    ):
        settings_fn.return_value.remnawave_stream_retention_enabled = False

        result = await purge_remnawave_stream_retention()

    assert result == {"enabled": False, "total_deleted": 0, "batches": 0, "has_more": False}
    backend_cls.assert_not_called()


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

        cutoff = datetime(2024, 1, 1, tzinfo=UTC)
        result = await _scan_and_delete_by_date(mock_redis, "cybervpn:stats:daily:*", cutoff)

        assert result == 1


@pytest.mark.asyncio
async def test_cleanup_export_files_removes_old(tmp_path, monkeypatch):
    """Test export file cleanup removes old files."""
    from src.tasks.cleanup import export_files

    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    old_file = export_dir / "old_file.csv"
    new_file = export_dir / "new_file.csv"
    old_file.write_text("old")
    new_file.write_text("new")
    old_time = time.time() - 100000
    new_time = time.time() - 1000
    monkeypatch.setattr(export_files, "EXPORT_DIR", export_dir)
    monkeypatch.setattr(export_files, "MAX_FILE_AGE_SECONDS", 86400)
    os.utime(old_file, (old_time, old_time))
    os.utime(new_file, (new_time, new_time))

    result = await export_files.cleanup_export_files()

    assert result["deleted"] == 1
    assert result["errors"] == 0
    assert result["size_freed_bytes"] == 3
    assert not old_file.exists()
    assert new_file.exists()


@pytest.mark.asyncio
async def test_cleanup_export_files_no_directory(tmp_path, monkeypatch):
    """Test export cleanup creates directory if missing."""
    from src.tasks.cleanup import export_files

    export_dir = tmp_path / "missing-exports"
    monkeypatch.setattr(export_files, "EXPORT_DIR", export_dir)

    result = await export_files.cleanup_export_files()

    assert result["deleted"] == 0
    assert export_dir.exists()
