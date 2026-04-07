"""Unit tests for TaskIQ queue depth metrics used by the auth dashboard."""

import pytest

from src.metrics import QUEUE_DEPTH
from src.tasks.monitoring.queue_depth import refresh_queue_depth_metrics


def _gauge_value(*, queue: str) -> float:
    return QUEUE_DEPTH.labels(queue=queue)._value.get()


class _FakeRedis:
    def __init__(self) -> None:
        self._entries = {
            "100-0": {
                "data": (
                    '{"task_id":"1","task_name":"send_otp_email",'
                    '"labels":{"queue":"email","retry_policy":"email_delivery"}}'
                )
            },
            "101-0": {
                "data": (
                    '{"task_id":"2","task_name":"send_daily_report",'
                    '"labels":{"queue":"reports"}}'
                )
            },
            "102-0": {
                "data": (
                    '{"task_id":"3","task_name":"send_magic_link_email",'
                    '"labels":{"queue":"email","retry_policy":"email_delivery"}}'
                )
            },
        }
        self.set_calls: list[tuple[str, int, int]] = []

    async def xinfo_groups(self, stream_key: str):
        assert stream_key == "taskiq"
        return [
            {
                "name": "taskiq",
                "pending": 2,
                "lag": 1,
                "last-delivered-id": "101-0",
            }
        ]

    async def xpending_range(self, stream_key: str, group_name: str, _min: str, _max: str, count: int):
        assert stream_key == "taskiq"
        assert group_name == "taskiq"
        assert count == 2
        return [
            {"message_id": "100-0"},
            {"message_id": "101-0"},
        ]

    async def xrange(
        self,
        stream_key: str,
        min_id: str | None = None,
        max_id: str | None = None,
        count: int | None = None,
        **kwargs,
    ):
        min_id = kwargs.get("min", min_id)
        max_id = kwargs.get("max", max_id)
        assert stream_key == "taskiq"
        if min_id == "100-0" and max_id == "100-0":
            return [("100-0", self._entries["100-0"])]
        if min_id == "101-0" and max_id == "101-0":
            return [("101-0", self._entries["101-0"])]
        if min_id == "(101-0" and max_id == "+":
            return [("102-0", self._entries["102-0"])]
        return []

    async def scan(self, cursor: int, match: str, count: int):
        assert match == "taskiq:result:*"
        assert count == 200
        return 0, ["taskiq:result:1", "taskiq:result:2"]

    async def set(self, key: str, value: int, ex: int):
        self.set_calls.append((key, value, ex))


@pytest.mark.asyncio
async def test_refresh_queue_depth_metrics_counts_only_email_backlog():
    """Only outstanding email tasks should contribute to the auth queue depth gauge."""
    fake_redis = _FakeRedis()

    result = await refresh_queue_depth_metrics(fake_redis)

    assert result["email"] == 2
    assert result["result_backend"] == 2
    assert _gauge_value(queue="email") == 2
    assert _gauge_value(queue="result_backend") == 2
    assert fake_redis.set_calls == [("cybervpn:metrics:queue_depth", 4, 300)]
