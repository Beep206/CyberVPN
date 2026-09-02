from unittest.mock import AsyncMock

import pytest
from fastapi import Response, status

from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.api.v1.node_plugins.routes import (
    create_node_plugin,
    delete_node_plugin,
    truncate_torrent_blocker_reports,
)
from src.presentation.api.v1.node_plugins.schemas import CreateNodePluginRequest


@pytest.mark.unit
async def test_empty_create_ack_is_exposed_as_202_without_repeating_mutation() -> None:
    client = AsyncMock(spec=RemnawaveClient)
    client.post_validated.return_value = None

    result = await create_node_plugin(
        body=CreateNodePluginRequest(name="torrent-blocker"),
        _current_user=object(),
        client=client,
    )

    assert isinstance(result, Response)
    assert result.status_code == status.HTTP_202_ACCEPTED
    client.post_validated.assert_awaited_once()


@pytest.mark.unit
async def test_empty_torrent_truncate_ack_is_exposed_as_204_once() -> None:
    client = AsyncMock(spec=RemnawaveClient)
    client.delete_validated.return_value = None

    result = await truncate_torrent_blocker_reports(
        _current_user=object(),
        client=client,
    )

    assert isinstance(result, Response)
    assert result.status_code == status.HTTP_204_NO_CONTENT
    client.delete_validated.assert_awaited_once_with(
        "/node-plugins/torrent-blocker/truncate",
        None,
    )


@pytest.mark.unit
async def test_empty_plugin_delete_ack_is_exposed_as_204_once() -> None:
    client = AsyncMock(spec=RemnawaveClient)
    client.delete_validated.return_value = None

    result = await delete_node_plugin(
        uuid="plugin-42",
        _current_user=object(),
        client=client,
    )

    assert isinstance(result, Response)
    assert result.status_code == status.HTTP_204_NO_CONTENT
    client.delete_validated.assert_awaited_once()
