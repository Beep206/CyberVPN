from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest
from redis.exceptions import RedisError

from src.application.vpn_testing.task2_route_evidence import (
    TASK2_ROUTE_EVIDENCE_EXPECTATION_PREFIX,
    TASK2_ROUTE_EVIDENCE_RESULT_PREFIX,
    Task2RouteEvidenceExpectation,
    Task2RouteEvidenceRejected,
    Task2RouteEvidenceStore,
    Task2RouteEvidenceUnavailable,
    Task2XrayRoutingWebhook,
    task2_route_evidence_target_digest,
)

WEBHOOK_SECRET = "liveRouteEvidenceWebhookCredentialAlpha123456"
SYNTHETIC_USER = "task2-route-evidence@cybervpn.internal"
NOW = 1_771_886_901


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.fail_on: str | None = None

    async def set(self, name: str, value: str, *, ex: int, nx: bool = False) -> bool:
        if self.fail_on == "set":
            raise RedisError("redis unavailable")
        if nx and name in self.values:
            return False
        self.values[name] = value
        self.ttls[name] = ex
        return True

    async def getdel(self, name: str) -> str | None:
        if self.fail_on == "getdel":
            raise RedisError("redis unavailable")
        self.ttls.pop(name, None)
        return self.values.pop(name, None)

    async def get(self, name: str) -> str | None:
        if self.fail_on == "get":
            raise RedisError("redis unavailable")
        return self.values.get(name)

    async def delete(self, *names: str) -> int:
        if self.fail_on == "delete":
            raise RedisError("redis unavailable")
        deleted = 0
        for name in names:
            self.ttls.pop(name, None)
            deleted += int(self.values.pop(name, None) is not None)
        return deleted


def _store(redis: FakeRedis) -> Task2RouteEvidenceStore:
    return Task2RouteEvidenceStore(
        redis,
        expectation_ttl_seconds=300,
        result_ttl_seconds=3600,
        webhook_secret=WEBHOOK_SECRET,
    )


def _payload(
    *,
    target: str = "tcp:example.org:443",
    selected_outbound: str | None = "DE_EXCEPTIONS_BRIDGE",
    expected_user: str | None = SYNTHETIC_USER,
    network: str = "tcp",
    inbound_tag: str | None = "SPB_EXCEPTIONS_REALITY_443",
    ts: int = NOW,
) -> dict[str, Any]:
    return {
        "email": expected_user,
        "level": None,
        "protocol": "tls",
        "network": network,
        "source": "tcp:198.51.100.10:54203",
        "destination": target,
        "routeTarget": "tcp:de-bridge.cybervpn.internal:443",
        "originalTarget": target,
        "inboundTag": inbound_tag,
        "inboundName": "vless",
        "inboundLocal": "tcp:192.0.2.10:443",
        "outboundTag": selected_outbound,
        "ts": ts,
    }


def _webhook(**overrides: Any) -> Task2XrayRoutingWebhook:
    return Task2XrayRoutingWebhook.model_validate(_payload(**overrides))


async def _seed_expectation(
    store: Task2RouteEvidenceStore,
    *,
    target: str = "tcp:example.org:443",
    run_id: str = "run-1",
    route_key: str = "task2.route.tcp.example",
    expected_outbound: str = "DE_EXCEPTIONS_BRIDGE",
    expected_inbound_tag: str = "SPB_EXCEPTIONS_REALITY_443",
    expected_network: str = "tcp",
) -> Task2RouteEvidenceExpectation:
    expectation = Task2RouteEvidenceExpectation(
        run_id=run_id,
        route_key=route_key,
        target_digest=task2_route_evidence_target_digest(WEBHOOK_SECRET, target),
        expected_outbound=expected_outbound,
        expected_inbound_tag=expected_inbound_tag,
        expected_network=expected_network,
    )
    await store.create_expectation(expectation)
    return expectation


@pytest.mark.asyncio
async def test_valid_callback_consumes_expectation_and_persists_safe_result() -> None:
    redis = FakeRedis()
    store = _store(redis)
    expectation = await _seed_expectation(store)

    result = await store.record_xray_routing_webhook(
        _webhook(),
        synthetic_user=SYNTHETIC_USER,
        max_skew_seconds=60,
        now_epoch_seconds=NOW,
    )

    assert result.run_id == expectation.run_id
    assert result.route_key == expectation.route_key
    assert result.selected_outbound == "DE_EXCEPTIONS_BRIDGE"
    assert result.verdict == "pass"
    assert store.expectation_key(expectation.target_digest) not in redis.values
    persisted = json.loads(redis.values[store.result_key(expectation.run_id, expectation.target_digest)])
    assert set(persisted) == {"run_id", "route_key", "selected_outbound", "verdict", "digest"}
    assert persisted == result.model_dump()
    assert redis.ttls[store.result_key(expectation.run_id, expectation.target_digest)] == 3600


@pytest.mark.asyncio
async def test_new_run_cannot_delete_previous_result_for_same_bounded_target() -> None:
    redis = FakeRedis()
    store = _store(redis)
    first = await _seed_expectation(store)
    await store.record_xray_routing_webhook(
        _webhook(),
        synthetic_user=SYNTHETIC_USER,
        max_skew_seconds=60,
        now_epoch_seconds=NOW,
    )

    second = await _seed_expectation(store, run_id="run-2")

    assert second.target_digest == first.target_digest
    assert store.result_key(first.run_id, first.target_digest) in redis.values
    assert store.result_key(second.run_id, second.target_digest) not in redis.values
    assert store.expectation_key(second.target_digest) in redis.values


@pytest.mark.asyncio
async def test_delete_expectations_removes_only_pending_keys() -> None:
    redis = FakeRedis()
    store = _store(redis)
    expectation = await _seed_expectation(store)

    await store.delete_expectations([expectation.target_digest])

    assert store.expectation_key(expectation.target_digest) not in redis.values


@pytest.mark.asyncio
async def test_wrong_synthetic_user_rejected_without_consuming_expectation() -> None:
    redis = FakeRedis()
    store = _store(redis)
    expectation = await _seed_expectation(store)

    with pytest.raises(Task2RouteEvidenceRejected) as exc_info:
        await store.record_xray_routing_webhook(
            _webhook(expected_user="customer@example.org"),
            synthetic_user=SYNTHETIC_USER,
            max_skew_seconds=60,
            now_epoch_seconds=NOW,
        )

    assert exc_info.value.reason == "invalid_synthetic_user"
    assert store.expectation_key(expectation.target_digest) in redis.values


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("webhook_overrides", "reason"),
    [
        ({"inbound_tag": "SPB_EXCEPTIONS_XHTTP_REALITY_8443"}, "expectation_inbound_mismatch"),
        ({"network": "udp"}, "expectation_network_mismatch"),
    ],
)
async def test_allowed_but_wrong_transport_cannot_satisfy_expectation(
    webhook_overrides: dict[str, Any],
    reason: str,
) -> None:
    redis = FakeRedis()
    store = _store(redis)
    expectation = await _seed_expectation(store)

    with pytest.raises(Task2RouteEvidenceRejected) as exc_info:
        await store.record_xray_routing_webhook(
            _webhook(**webhook_overrides),
            synthetic_user=SYNTHETIC_USER,
            max_skew_seconds=60,
            now_epoch_seconds=NOW,
        )

    assert exc_info.value.reason == reason
    assert store.expectation_key(expectation.target_digest) not in redis.values


@pytest.mark.parametrize(
    ("ts", "reason"),
    [(NOW - 61, "timestamp_out_of_window"), (NOW + 61, "timestamp_out_of_window")],
)
@pytest.mark.asyncio
async def test_stale_and_future_timestamp_rejected_without_consuming_expectation(ts: int, reason: str) -> None:
    redis = FakeRedis()
    store = _store(redis)
    expectation = await _seed_expectation(store)

    with pytest.raises(Task2RouteEvidenceRejected) as exc_info:
        await store.record_xray_routing_webhook(
            _webhook(ts=ts),
            synthetic_user=SYNTHETIC_USER,
            max_skew_seconds=60,
            now_epoch_seconds=NOW,
        )

    assert exc_info.value.reason == reason
    assert store.expectation_key(expectation.target_digest) in redis.values


@pytest.mark.asyncio
async def test_invalid_outbound_rejected_without_consuming_expectation() -> None:
    redis = FakeRedis()
    store = _store(redis)
    expectation = await _seed_expectation(store)

    with pytest.raises(Task2RouteEvidenceRejected) as exc_info:
        await store.record_xray_routing_webhook(
            _webhook(selected_outbound="UNEXPECTED_PROXY"),
            synthetic_user=SYNTHETIC_USER,
            max_skew_seconds=60,
            now_epoch_seconds=NOW,
        )

    assert exc_info.value.reason == "invalid_outbound"
    assert store.expectation_key(expectation.target_digest) in redis.values


@pytest.mark.asyncio
async def test_non_task2_inbound_rejected_without_consuming_expectation() -> None:
    redis = FakeRedis()
    store = _store(redis)
    expectation = await _seed_expectation(store)

    with pytest.raises(Task2RouteEvidenceRejected) as exc_info:
        await store.record_xray_routing_webhook(
            _webhook(inbound_tag="SMART_RU_REALITY_443"),
            synthetic_user=SYNTHETIC_USER,
            max_skew_seconds=60,
            now_epoch_seconds=NOW,
        )

    assert exc_info.value.reason == "invalid_inbound"
    assert store.expectation_key(expectation.target_digest) in redis.values


@pytest.mark.asyncio
async def test_unknown_expectation_rejected_and_no_result_persisted() -> None:
    redis = FakeRedis()
    store = _store(redis)

    with pytest.raises(Task2RouteEvidenceRejected) as exc_info:
        await store.record_xray_routing_webhook(
            _webhook(),
            synthetic_user=SYNTHETIC_USER,
            max_skew_seconds=60,
            now_epoch_seconds=NOW,
        )

    assert exc_info.value.reason == "expectation_not_found"
    assert not any(key.startswith(TASK2_ROUTE_EVIDENCE_RESULT_PREFIX) for key in redis.values)


@pytest.mark.asyncio
async def test_replay_is_rejected_after_one_shot_expectation_consumed() -> None:
    redis = FakeRedis()
    store = _store(redis)
    await _seed_expectation(store)
    webhook = _webhook()

    await store.record_xray_routing_webhook(
        webhook,
        synthetic_user=SYNTHETIC_USER,
        max_skew_seconds=60,
        now_epoch_seconds=NOW,
    )
    with pytest.raises(Task2RouteEvidenceRejected) as exc_info:
        await store.record_xray_routing_webhook(
            webhook,
            synthetic_user=SYNTHETIC_USER,
            max_skew_seconds=60,
            now_epoch_seconds=NOW,
        )

    assert exc_info.value.reason == "expectation_not_found"


@pytest.mark.asyncio
async def test_previous_run_target_replay_does_not_consume_new_run_scoped_target() -> None:
    redis = FakeRedis()
    store = _store(redis)
    new_target = "tcp:example.org:45123"
    expectation = await _seed_expectation(store, run_id="run-2", target=new_target)

    with pytest.raises(Task2RouteEvidenceRejected) as exc_info:
        await store.record_xray_routing_webhook(
            _webhook(target="tcp:example.org:443"),
            synthetic_user=SYNTHETIC_USER,
            max_skew_seconds=60,
            now_epoch_seconds=NOW,
        )

    assert exc_info.value.reason == "expectation_not_found"
    assert store.expectation_key(expectation.target_digest) in redis.values


@pytest.mark.asyncio
async def test_allowed_outbound_mismatch_persists_fail_verdict_from_callback_outbound() -> None:
    redis = FakeRedis()
    store = _store(redis)
    expectation = await _seed_expectation(store, expected_outbound="DE_EXCEPTIONS_BRIDGE")

    result = await store.record_xray_routing_webhook(
        _webhook(selected_outbound="DIRECT"),
        synthetic_user=SYNTHETIC_USER,
        max_skew_seconds=60,
        now_epoch_seconds=NOW,
    )

    assert result.selected_outbound == "DIRECT"
    assert result.verdict == "fail"
    target_digest = task2_route_evidence_target_digest(WEBHOOK_SECRET, "tcp:example.org:443")
    persisted = json.loads(redis.values[store.result_key(expectation.run_id, target_digest)])
    assert persisted["selected_outbound"] == "DIRECT"
    assert persisted["verdict"] == "fail"


@pytest.mark.asyncio
async def test_raw_webhook_payload_and_customer_fields_are_not_persisted() -> None:
    redis = FakeRedis()
    store = _store(redis)
    raw_target = "tcp:customer-private-target.example:443"
    expectation = await _seed_expectation(
        store,
        target=raw_target,
        run_id="run-privacy",
        route_key="task2.privacy",
    )

    result = await store.record_xray_routing_webhook(
        _webhook(target=raw_target),
        synthetic_user=SYNTHETIC_USER,
        max_skew_seconds=60,
        now_epoch_seconds=NOW,
    )

    assert result.verdict == "pass"
    serialized_store = json.dumps({"keys": sorted(redis.values), "values": redis.values}, sort_keys=True)
    for forbidden in (
        raw_target,
        "customer-private-target",
        "198.51.100.10",
        "203.0.113.20",
        SYNTHETIC_USER,
        WEBHOOK_SECRET,
        "destination",
        "routeTarget",
        "originalTarget",
        "source",
        "inboundTag",
        "email",
        "inboundLocal",
        "protocol",
        "ts",
    ):
        assert forbidden not in serialized_store
    target_digest = task2_route_evidence_target_digest(WEBHOOK_SECRET, raw_target)
    persisted = json.loads(redis.values[store.result_key(expectation.run_id, target_digest)])
    assert set(persisted) == {"run_id", "route_key", "selected_outbound", "verdict", "digest"}


@pytest.mark.asyncio
async def test_digest_is_secret_keyed_hmac_not_plain_target_sha256() -> None:
    target = "tcp:customer-private-target.example:443"
    digest = task2_route_evidence_target_digest(WEBHOOK_SECRET, target)

    assert digest != hashlib.sha256(target.encode()).hexdigest()
    assert digest != task2_route_evidence_target_digest("anotherLiveWebhookCredentialAlpha123456", target)


@pytest.mark.asyncio
async def test_result_can_be_polled_by_precreated_expectation_target_digest() -> None:
    redis = FakeRedis()
    store = _store(redis)
    expectation = await _seed_expectation(store)

    result = await store.record_xray_routing_webhook(
        _webhook(),
        synthetic_user=SYNTHETIC_USER,
        max_skew_seconds=60,
        now_epoch_seconds=NOW,
    )

    assert await store.get_result_for_target_digest(expectation.run_id, expectation.target_digest) == result
    assert store.result_key(expectation.run_id, expectation.target_digest) in redis.values
    assert store.result_key(expectation.run_id, result.digest) not in redis.values


@pytest.mark.asyncio
async def test_redis_failure_is_explicit_unavailable_not_success() -> None:
    redis = FakeRedis()
    store = _store(redis)
    await _seed_expectation(store)
    redis.fail_on = "getdel"

    with pytest.raises(Task2RouteEvidenceUnavailable):
        await store.record_xray_routing_webhook(
            _webhook(),
            synthetic_user=SYNTHETIC_USER,
            max_skew_seconds=60,
            now_epoch_seconds=NOW,
        )


@pytest.mark.asyncio
async def test_expectation_payload_contains_only_safe_metadata_and_digest() -> None:
    redis = FakeRedis()
    store = _store(redis)
    target = "tcp:customer-private-target.example:443"
    expectation = await _seed_expectation(store, target=target)
    expectation_key = f"{TASK2_ROUTE_EVIDENCE_EXPECTATION_PREFIX}{expectation.target_digest}"

    persisted = json.loads(redis.values[expectation_key])
    assert set(persisted) == {
        "run_id",
        "route_key",
        "target_digest",
        "expected_outbound",
        "expected_inbound_tag",
        "expected_network",
    }
    assert target not in json.dumps(persisted, sort_keys=True)
