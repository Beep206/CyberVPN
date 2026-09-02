from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.infrastructure.remnawave.stream_reconciliation_gateway import (
    RemnawaveStreamAuthoritativeReadError,
    RemnawaveStreamRestReconciliationGateway,
)


def _raw_user(user_id: int) -> dict[str, object]:
    return {
        "id": user_id,
        "uuid": str(uuid4()),
        "username": f"user-{user_id}",
        "status": "ACTIVE",
        "createdAt": "2026-08-01T00:00:00Z",
        "updatedAt": "2026-08-30T00:00:00Z",
        "usedTrafficBytes": 10,
        "lifetimeUsedTrafficBytes": 20,
    }


@pytest.mark.unit
async def test_usage_inventory_reads_bounded_cursor_pages_and_requires_numeric_identity() -> None:
    client = SimpleNamespace(
        get_all_users_cursor_page=AsyncMock(
            side_effect=[
                SimpleNamespace(items=[_raw_user(1)], next_cursor="2", has_next_page=True),
                SimpleNamespace(items=[_raw_user(2)], next_cursor=None, has_next_page=False),
            ]
        )
    )

    count = await RemnawaveStreamRestReconciliationGateway(client).read_user_usage_inventory()

    assert count == 2
    assert client.get_all_users_cursor_page.await_args_list[0].kwargs == {"cursor": None, "limit": 1000}
    assert client.get_all_users_cursor_page.await_args_list[1].kwargs == {"cursor": "2", "limit": 1000}


@pytest.mark.unit
async def test_usage_inventory_rejects_duplicate_numeric_identity() -> None:
    client = SimpleNamespace(
        get_all_users_cursor_page=AsyncMock(
            return_value=SimpleNamespace(
                items=[_raw_user(1), _raw_user(1)],
                next_cursor=None,
                has_next_page=False,
            )
        )
    )

    with pytest.raises(RemnawaveStreamAuthoritativeReadError, match="duplicate"):
        await RemnawaveStreamRestReconciliationGateway(client).read_user_usage_inventory()


@pytest.mark.unit
async def test_node_presence_uses_read_job_and_validates_exact_node_result() -> None:
    now = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
    node_uuid = str(uuid4())
    node = SimpleNamespace(id=7, uuid=node_uuid)
    client = SimpleNamespace(
        get_collection_validated=AsyncMock(return_value=[node]),
        post=AsyncMock(return_value={"jobId": "job_1"}),
        get=AsyncMock(
            side_effect=[
                {"isCompleted": False, "isFailed": False, "result": None},
                {
                    "isCompleted": True,
                    "isFailed": False,
                    "result": {
                        "success": True,
                        "nodeUuid": node_uuid,
                        "users": [
                            {
                                "userId": 11,
                                "ips": [{"ip": "203.0.113.1", "lastSeen": now.isoformat()}],
                            }
                        ],
                    },
                },
            ]
        ),
    )
    sleeper = AsyncMock()

    snapshots = await RemnawaveStreamRestReconciliationGateway(
        client,
        clock=lambda: now,
        sleeper=sleeper,
    ).read_node_presence_snapshots()

    assert snapshots[0].node_id == 7
    assert snapshots[0].users[0].user_id == 11
    client.post.assert_awaited_once_with(f"/connections/by-node/{node_uuid}")
    assert client.get.await_args_list[0].args == ("/connections/by-node/job_1",)
    sleeper.assert_awaited_once_with(0.25)


@pytest.mark.unit
async def test_node_presence_rejects_cross_node_job_result() -> None:
    node_uuid = str(uuid4())
    client = SimpleNamespace(
        get_collection_validated=AsyncMock(return_value=[SimpleNamespace(id=7, uuid=node_uuid)]),
        post=AsyncMock(return_value={"jobId": "job_1"}),
        get=AsyncMock(
            return_value={
                "isCompleted": True,
                "isFailed": False,
                "result": {"success": True, "nodeUuid": str(uuid4()), "users": []},
            }
        ),
    )

    with pytest.raises(RemnawaveStreamAuthoritativeReadError, match="inconsistent"):
        await RemnawaveStreamRestReconciliationGateway(client).read_node_presence_snapshots()
