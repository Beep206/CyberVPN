from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.infrastructure.remnawave.client import RemnawaveTransportError
from src.infrastructure.remnawave.connections_gateway import (
    RemnawaveConnectionDropCommand,
    RemnawaveConnectionJob,
    RemnawaveConnectionsGateway,
    RemnawaveConnectionsInvalidResponseError,
    RemnawaveDropByUserIds,
    RemnawaveDropOnAllNodes,
    RemnawaveNodeConnectionsJobResult,
    RemnawaveUserConnectionsJobResult,
)


@pytest.mark.unit
async def test_connections_gateway_uses_exact_342_numeric_user_job_routes() -> None:
    client = AsyncMock()
    client.post_validated.return_value = RemnawaveConnectionJob(jobId="job_user_1")
    client.get_validated.return_value = RemnawaveUserConnectionsJobResult.model_validate(
        {
            "isCompleted": True,
            "isFailed": False,
            "progress": {"total": 1, "completed": 1, "percent": 100},
            "result": {
                "success": True,
                "userId": 42,
                "nodes": [
                    {
                        "nodeUuid": str(uuid4()),
                        "nodeName": "Moscow",
                        "countryCode": "RU",
                        "ips": [{"ip": "203.0.113.8", "lastSeen": "2026-08-31T12:00:00+05:00"}],
                    }
                ],
            },
        }
    )
    gateway = RemnawaveConnectionsGateway(client)

    job = await gateway.request_by_user(42)
    result = await gateway.get_by_user_result(job_id=job.job_id, expected_user_id=42)

    client.post_validated.assert_awaited_once_with(
        "/connections/by-user/42",
        RemnawaveConnectionJob,
    )
    client.get_validated.assert_awaited_once_with(
        "/connections/by-user/job_user_1",
        RemnawaveUserConnectionsJobResult,
    )
    assert result.result is not None
    assert result.result.user_id == 42
    assert result.result.nodes[0].ips[0].public_ip == "203.0.113.8"
    assert result.result.nodes[0].ips[0].last_seen.isoformat() == "2026-08-31T07:00:00+00:00"


@pytest.mark.unit
async def test_connections_gateway_uses_exact_342_node_job_routes() -> None:
    node_uuid = uuid4()
    client = AsyncMock()
    client.post_validated.return_value = RemnawaveConnectionJob(jobId="job_node_1")
    client.get_validated.return_value = RemnawaveNodeConnectionsJobResult.model_validate(
        {
            "isCompleted": True,
            "isFailed": False,
            "result": {
                "success": True,
                "nodeUuid": str(node_uuid),
                "users": [
                    {
                        "userId": 42,
                        "ips": [{"ip": "2001:db8::1", "lastSeen": "2026-08-31T07:00:00Z"}],
                    }
                ],
            },
        }
    )
    gateway = RemnawaveConnectionsGateway(client)

    job = await gateway.request_by_node(node_uuid)
    result = await gateway.get_by_node_result(job_id=job.job_id, expected_node_uuid=node_uuid)

    client.post_validated.assert_awaited_once_with(
        f"/connections/by-node/{node_uuid}",
        RemnawaveConnectionJob,
    )
    client.get_validated.assert_awaited_once_with(
        "/connections/by-node/job_node_1",
        RemnawaveNodeConnectionsJobResult,
    )
    assert result.result is not None
    assert result.result.node_uuid == node_uuid


@pytest.mark.unit
async def test_connections_gateway_never_retries_ambiguous_post_transport_failure() -> None:
    client = AsyncMock()
    client.post_validated.side_effect = RemnawaveTransportError()
    gateway = RemnawaveConnectionsGateway(client)

    with pytest.raises(RemnawaveTransportError):
        await gateway.request_by_user(42)

    assert client.post_validated.await_count == 1


@pytest.mark.unit
async def test_connections_gateway_rejects_empty_job_acknowledgement() -> None:
    client = AsyncMock()
    client.post_validated.return_value = None

    with pytest.raises(RemnawaveConnectionsInvalidResponseError):
        await RemnawaveConnectionsGateway(client).request_by_user(42)


@pytest.mark.unit
async def test_connections_gateway_rejects_cross_target_user_job_result() -> None:
    client = AsyncMock()
    client.get_validated.return_value = RemnawaveUserConnectionsJobResult.model_validate(
        {
            "isCompleted": True,
            "isFailed": False,
            "progress": {"total": 1, "completed": 1, "percent": 100},
            "result": {"success": True, "userId": 99, "nodes": []},
        }
    )

    with pytest.raises(RemnawaveConnectionsInvalidResponseError, match="target mismatch"):
        await RemnawaveConnectionsGateway(client).get_by_user_result(
            job_id="job_user_1",
            expected_user_id=42,
        )


@pytest.mark.unit
async def test_connections_gateway_rejects_cross_target_node_job_result() -> None:
    expected_node_uuid = uuid4()
    client = AsyncMock()
    client.get_validated.return_value = RemnawaveNodeConnectionsJobResult.model_validate(
        {
            "isCompleted": True,
            "isFailed": False,
            "result": {"success": True, "nodeUuid": str(uuid4()), "users": []},
        }
    )

    with pytest.raises(RemnawaveConnectionsInvalidResponseError, match="target mismatch"):
        await RemnawaveConnectionsGateway(client).get_by_node_result(
            job_id="job_node_1",
            expected_node_uuid=expected_node_uuid,
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "payload",
    [
        {
            "isCompleted": True,
            "isFailed": False,
            "progress": {"total": 1, "completed": 1, "percent": 100},
            "result": None,
        },
        {
            "isCompleted": False,
            "isFailed": False,
            "progress": {"total": 1, "completed": 0, "percent": 0},
            "result": {"success": True, "userId": 42, "nodes": []},
        },
        {
            "isCompleted": True,
            "isFailed": False,
            "progress": {"total": 1, "completed": 1, "percent": 100},
            "result": {
                "success": True,
                "userId": 42,
                "nodes": [
                    {
                        "nodeUuid": str(uuid4()),
                        "nodeName": "Node",
                        "countryCode": "RU",
                        "ips": [{"ip": "203.0.113.8", "lastSeen": "2026-08-31T07:00:00"}],
                    }
                ],
            },
        },
    ],
)
def test_connections_gateway_rejects_inconsistent_or_naive_user_results(payload: dict) -> None:
    with pytest.raises(ValidationError):
        RemnawaveUserConnectionsJobResult.model_validate(payload)


@pytest.mark.unit
async def test_connections_gateway_sends_exact_drop_payload_once() -> None:
    client = AsyncMock()
    client.post.return_value = {}
    command = RemnawaveConnectionDropCommand(
        dropBy=RemnawaveDropByUserIds(userIds=[42]),
        targetNodes=RemnawaveDropOnAllNodes(),
    )

    await RemnawaveConnectionsGateway(client).drop_once(command)

    client.post.assert_awaited_once_with(
        "/connections/drop",
        json={
            "dropBy": {"by": "userIds", "userIds": [42]},
            "targetNodes": {"target": "allNodes"},
        },
    )


@pytest.mark.unit
async def test_connections_gateway_never_retries_ambiguous_drop_transport_failure() -> None:
    client = AsyncMock()
    client.post.side_effect = RemnawaveTransportError()
    command = RemnawaveConnectionDropCommand(
        dropBy=RemnawaveDropByUserIds(userIds=[42]),
        targetNodes=RemnawaveDropOnAllNodes(),
    )

    with pytest.raises(RemnawaveTransportError):
        await RemnawaveConnectionsGateway(client).drop_once(command)

    assert client.post.await_count == 1
