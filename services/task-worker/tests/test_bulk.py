"""Tests for bulk operations task modules."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_bulk_disable_users_success():
    """The registered disable task is explicit and performs no provider I/O."""
    user_ids = [101, 102, 103]
    from src.tasks.bulk import bulk_operations

    result = await bulk_operations.bulk_disable_users(user_ids, "admin-1")

    assert result["total"] == 3
    assert result["processed"] == 0
    assert result["failed"] == 0
    assert result["safety_disabled"] is True
    assert "durable receipts" in result["reason"]
    for forbidden_boundary in (
        "RemnawaveClient",
        "TelegramClient",
        "CacheService",
        "get_redis_client",
        "publish_event",
    ):
        assert not hasattr(bulk_operations, forbidden_boundary)


@pytest.mark.asyncio
async def test_bulk_disable_users_partial_failure():
    """No partial mutation path is reachable while safety-disabled."""
    user_ids = [101, 102, 103]
    from src.tasks.bulk.bulk_operations import bulk_disable_users

    result = await bulk_disable_users(user_ids, "admin-1")

    assert result["processed"] == 0
    assert result["failed"] == 0
    assert result["safety_disabled"] is True


@pytest.mark.asyncio
async def test_bulk_enable_users_success():
    """The registered enable task is explicit and performs no provider I/O."""
    user_ids = [101, 102]
    from src.tasks.bulk import bulk_operations

    result = await bulk_operations.bulk_enable_users(user_ids, "admin-1")

    assert result["total"] == 2
    assert result["processed"] == 0
    assert result["failed"] == 0
    assert result["safety_disabled"] is True
    for forbidden_boundary in (
        "RemnawaveClient",
        "TelegramClient",
        "CacheService",
        "get_redis_client",
        "publish_event",
    ):
        assert not hasattr(bulk_operations, forbidden_boundary)


@pytest.mark.asyncio
async def test_bulk_broadcast_queuing():
    """Test bulk broadcast queues notifications."""
    telegram_ids = [123456, 789012, 345678]
    message = "Important announcement"

    with (
        patch("src.tasks.bulk.broadcast.get_session_factory") as mock_factory,
        patch("src.tasks.bulk.broadcast.get_redis_client") as mock_redis_fn,
        patch("src.tasks.bulk.broadcast.publish_event", new_callable=AsyncMock),
    ):
        mock_session = AsyncMock()
        mock_session.add_all = MagicMock()
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
        patch("src.tasks.bulk.broadcast.publish_event", new_callable=AsyncMock),
    ):
        mock_session = AsyncMock()
        mock_session.add_all = MagicMock()
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
