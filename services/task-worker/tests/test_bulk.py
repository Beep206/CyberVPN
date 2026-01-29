"""Tests for bulk operations task modules."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_bulk_disable_users_success():
    """Test bulk disable users processes all users."""
    user_uuids = ["user-1", "user-2", "user-3"]

    with (
        patch("src.tasks.bulk.bulk_operations.RemnawaveClient") as mock_rw_cls,
        patch("src.tasks.bulk.bulk_operations.TelegramClient") as mock_tg_cls,
        patch("src.tasks.bulk.bulk_operations.get_redis_client") as mock_redis_fn,
        patch("src.tasks.bulk.bulk_operations.CacheService") as mock_cache_cls,
        patch("src.tasks.bulk.bulk_operations.get_settings") as mock_settings,
        patch("src.tasks.bulk.bulk_operations.publish_event", new_callable=AsyncMock) as mock_publish,
    ):
        mock_settings.return_value.bulk_batch_size = 10

        mock_rw = AsyncMock()
        mock_rw.disable_user.return_value = {"status": "disabled"}
        mock_rw_cls.return_value.__aenter__.return_value = mock_rw

        mock_tg = AsyncMock()
        mock_tg_cls.return_value.__aenter__.return_value = mock_tg

        mock_redis = AsyncMock()
        mock_redis_fn.return_value = mock_redis

        mock_cache = AsyncMock()
        mock_cache_cls.return_value = mock_cache

        from src.tasks.bulk.bulk_operations import bulk_disable_users

        result = await bulk_disable_users(user_uuids, "admin-1")

        assert result["total"] == 3
        assert result["processed"] == 3
        assert result["failed"] == 0
        assert mock_rw.disable_user.call_count == 3
        mock_tg.send_admin_alert.assert_called_once()


@pytest.mark.asyncio
async def test_bulk_disable_users_partial_failure():
    """Test bulk disable handles individual failures."""
    user_uuids = ["user-1", "user-2", "user-3"]

    with (
        patch("src.tasks.bulk.bulk_operations.RemnawaveClient") as mock_rw_cls,
        patch("src.tasks.bulk.bulk_operations.TelegramClient") as mock_tg_cls,
        patch("src.tasks.bulk.bulk_operations.get_redis_client") as mock_redis_fn,
        patch("src.tasks.bulk.bulk_operations.CacheService") as mock_cache_cls,
        patch("src.tasks.bulk.bulk_operations.get_settings") as mock_settings,
        patch("src.tasks.bulk.bulk_operations.publish_event", new_callable=AsyncMock) as mock_publish,
    ):
        mock_settings.return_value.bulk_batch_size = 10

        mock_rw = AsyncMock()
        mock_rw.disable_user.side_effect = [
            {"status": "disabled"},
            Exception("API error"),
            {"status": "disabled"},
        ]
        mock_rw_cls.return_value.__aenter__.return_value = mock_rw

        mock_tg = AsyncMock()
        mock_tg_cls.return_value.__aenter__.return_value = mock_tg

        mock_redis = AsyncMock()
        mock_redis_fn.return_value = mock_redis

        mock_cache = AsyncMock()
        mock_cache_cls.return_value = mock_cache

        from src.tasks.bulk.bulk_operations import bulk_disable_users

        result = await bulk_disable_users(user_uuids, "admin-1")

        assert result["processed"] == 2
        assert result["failed"] == 1


@pytest.mark.asyncio
async def test_bulk_enable_users_success():
    """Test bulk enable users processes all users."""
    user_uuids = ["user-1", "user-2"]

    with (
        patch("src.tasks.bulk.bulk_operations.RemnawaveClient") as mock_rw_cls,
        patch("src.tasks.bulk.bulk_operations.TelegramClient") as mock_tg_cls,
        patch("src.tasks.bulk.bulk_operations.get_redis_client") as mock_redis_fn,
        patch("src.tasks.bulk.bulk_operations.CacheService") as mock_cache_cls,
        patch("src.tasks.bulk.bulk_operations.get_settings") as mock_settings,
        patch("src.tasks.bulk.bulk_operations.publish_event", new_callable=AsyncMock) as mock_publish,
    ):
        mock_settings.return_value.bulk_batch_size = 10

        mock_rw = AsyncMock()
        mock_rw.enable_user.return_value = {"status": "active"}
        mock_rw_cls.return_value.__aenter__.return_value = mock_rw

        mock_tg = AsyncMock()
        mock_tg_cls.return_value.__aenter__.return_value = mock_tg

        mock_redis = AsyncMock()
        mock_redis_fn.return_value = mock_redis

        mock_cache = AsyncMock()
        mock_cache_cls.return_value = mock_cache

        from src.tasks.bulk.bulk_operations import bulk_enable_users

        result = await bulk_enable_users(user_uuids, "admin-1")

        assert result["total"] == 2
        assert result["processed"] == 2
        assert result["failed"] == 0


@pytest.mark.asyncio
async def test_bulk_broadcast_queuing():
    """Test bulk broadcast queues notifications."""
    telegram_ids = [123456, 789012, 345678]
    message = "Important announcement"

    with (
        patch("src.tasks.bulk.broadcast.get_session_factory") as mock_factory,
        patch("src.tasks.bulk.broadcast.get_redis_client") as mock_redis_fn,
        patch("src.tasks.bulk.broadcast.publish_event", new_callable=AsyncMock) as mock_publish,
    ):
        mock_session = AsyncMock()
        mock_factory.return_value.return_value.__aenter__.return_value = mock_session

        mock_redis = AsyncMock()
        mock_redis_fn.return_value = mock_redis

        from src.tasks.bulk.broadcast import bulk_broadcast

        result = await bulk_broadcast(telegram_ids, message, "broadcast")

        assert result["queued"] == 3
        assert "job_id" in result
        assert mock_session.add_all.called
        mock_session.commit.assert_called()


@pytest.mark.asyncio
async def test_bulk_broadcast_large_batch():
    """Test bulk broadcast handles large batches."""
    telegram_ids = list(range(1000))  # 1000 recipients
    message = "Test message"

    with (
        patch("src.tasks.bulk.broadcast.get_session_factory") as mock_factory,
        patch("src.tasks.bulk.broadcast.get_redis_client") as mock_redis_fn,
        patch("src.tasks.bulk.broadcast.publish_event", new_callable=AsyncMock) as mock_publish,
    ):
        mock_session = AsyncMock()
        mock_factory.return_value.return_value.__aenter__.return_value = mock_session

        mock_redis = AsyncMock()
        mock_redis_fn.return_value = mock_redis

        from src.tasks.bulk.broadcast import bulk_broadcast

        result = await bulk_broadcast(telegram_ids, message)

        assert result["queued"] == 1000
        # Should batch at 500, so 2 calls to add_all
        assert mock_session.add_all.call_count == 2


@pytest.mark.asyncio
async def test_bulk_export_csv():
    """Test CSV export generation."""
    with (
        patch("src.tasks.bulk.export.get_session_factory") as mock_factory,
        patch("src.tasks.bulk.export.get_redis_client") as mock_redis_fn,
        patch("builtins.open", create=True) as mock_open,
    ):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchmany.side_effect = [
            [MagicMock(_mapping={"id": 1, "name": "User 1"}), MagicMock(_mapping={"id": 2, "name": "User 2"})],
            [],
        ]
        mock_session.execute.return_value = mock_result
        mock_factory.return_value.return_value.__aenter__.return_value = mock_session

        mock_redis = AsyncMock()
        mock_redis_fn.return_value = mock_redis

        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        from src.tasks.bulk.export import bulk_export

        result = await bulk_export("users", "csv")

        assert result["rows_exported"] == 2
        assert "file_path" in result
        assert ".csv" in result["file_path"]


@pytest.mark.asyncio
async def test_bulk_export_json():
    """Test JSON export generation."""
    with (
        patch("src.tasks.bulk.export.get_session_factory") as mock_factory,
        patch("src.tasks.bulk.export.get_redis_client") as mock_redis_fn,
        patch("builtins.open", create=True) as mock_open,
    ):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchmany.side_effect = [
            [MagicMock(_mapping={"id": 1, "name": "User 1"})],
            [],
        ]
        mock_session.execute.return_value = mock_result
        mock_factory.return_value.return_value.__aenter__.return_value = mock_session

        mock_redis = AsyncMock()
        mock_redis_fn.return_value = mock_redis

        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        from src.tasks.bulk.export import bulk_export

        result = await bulk_export("users", "json")

        assert result["rows_exported"] == 1
        assert ".json" in result["file_path"]


@pytest.mark.asyncio
async def test_bulk_export_invalid_type():
    """Test export rejects invalid export types."""
    with pytest.raises(ValueError, match="Invalid export_type"):
        from src.tasks.bulk.export import bulk_export

        await bulk_export("invalid_type", "csv")
