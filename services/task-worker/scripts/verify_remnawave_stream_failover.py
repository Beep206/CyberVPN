"""Prove subscription-request XACK+XDEL recovery across a real Valkey restart.

This is an opt-in local evidence harness.  It creates a uniquely named Valkey
container and volume, simulates a durable sink commit followed by a transport
failure before acknowledgement, restarts Valkey, reclaims the PEL entry, and
verifies idempotent replay plus atomic XACK+XDEL.  Only resources carrying the
hard-coded proof prefix are removed during cleanup.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from redis.asyncio import Redis

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from src.services.remnawave_streams import (  # noqa: E402
    REMNAWAVE_STREAM_CONSUMER_GROUP,
    SUBSCRIPTION_REQUESTS_STREAM,
    RedactedDeadLetter,
    RedisStreamTransport,
    RemnawaveStreamConsumer,
    RemnawaveStreamConsumerConfig,
    RemnawaveStreamEvent,
    StreamRuntimeState,
)

RESOURCE_PREFIX = "cybervpn-remnawave-stream-proof-"
DEFAULT_IMAGE = "valkey/valkey:8.1.8-alpine"
HMAC_KEY = b"cybervpn-local-stream-failover-proof-key-v1"


def _resolve_docker() -> str:
    executable = shutil.which("docker")
    if executable is None:
        raise RuntimeError("docker executable is unavailable")
    return executable


DOCKER_EXECUTABLE = _resolve_docker()


def _docker(*arguments: str, capture: bool = True) -> str:
    completed = subprocess.run(  # noqa: S603 - arguments are a fixed list, never a shell string
        [DOCKER_EXECUTABLE, *arguments],
        check=True,
        capture_output=capture,
        text=True,
    )
    return completed.stdout.strip()


def _progress(phase: str) -> None:
    print(json.dumps({"phase": phase}, sort_keys=True), file=sys.stderr, flush=True)  # noqa: T201


def _assert_owned_resource(name: str) -> None:
    if not name.startswith(RESOURCE_PREFIX) or len(name) <= len(RESOURCE_PREFIX):
        raise RuntimeError("refusing to mutate a resource outside the failover-proof namespace")


class _DurableReceiptSink:
    """Minimal deterministic stand-in for the backend's idempotent DB receipt."""

    def __init__(self) -> None:
        self.receipts: set[str] = set()
        self.duplicate_commits = 0
        self.observed_epochs: list[str] = []

    async def persist(self, event: RemnawaveStreamEvent, *, idempotency_key: str) -> None:
        _ = event
        if idempotency_key in self.receipts:
            self.duplicate_commits += 1
            return
        self.receipts.add(idempotency_key)

    async def persist_dead_letter(self, dead_letter: RedactedDeadLetter) -> None:
        raise AssertionError(f"unexpected dead letter: {dead_letter.reason}")

    async def record_gap(
        self,
        stream: str,
        missing_message_ids: Sequence[str],
        *,
        detected_at: datetime,
    ) -> None:
        _ = (stream, missing_message_ids, detected_at)
        raise AssertionError("the restart proof must preserve the pending source entry")

    async def observe_runtime(
        self,
        stream: str,
        state: StreamRuntimeState,
        *,
        observed_at: datetime,
    ) -> None:
        _ = (stream, observed_at)
        self.observed_epochs.append(state.observed_stream_identity)


class _FailBeforeAckTransport(RedisStreamTransport):
    """Inject the exact commit-before-XACK ambiguity once."""

    async def ack_and_delete(self, stream: str, group: str, message_id: str) -> None:
        _ = (stream, group, message_id)
        raise ConnectionError("injected Valkey failure after durable sink commit")


async def _wait_until_ready(port: int) -> Redis:
    client: Redis = Redis(
        host="127.0.0.1",
        port=port,
        decode_responses=False,
        socket_connect_timeout=0.5,
        socket_timeout=1.0,
    )
    last_error: Exception | None = None
    for _attempt in range(100):
        try:
            if await client.ping():
                return client
        except Exception as exc:
            last_error = exc
        await asyncio.sleep(0.1)
    await client.aclose()
    raise RuntimeError("Valkey proof container did not become ready") from last_error


def _published_port(container_name: str) -> int:
    output = _docker("port", container_name, "6379/tcp")
    endpoint = output.splitlines()[0].strip()
    try:
        return int(endpoint.rsplit(":", 1)[1])
    except (IndexError, ValueError) as exc:
        raise RuntimeError("Docker returned an invalid published port") from exc


def _server_run_id(info: dict[Any, Any]) -> str:
    raw = info.get("run_id", info.get(b"run_id"))
    if isinstance(raw, bytes):
        return raw.decode("ascii")
    if isinstance(raw, str) and raw:
        return raw
    raise RuntimeError("Valkey server run_id is unavailable")


def _group_name(group: Mapping[Any, Any]) -> str:
    raw = group.get(b"name", group.get("name"))
    if isinstance(raw, bytes):
        return raw.decode("ascii")
    if isinstance(raw, str) and raw:
        return raw
    raise RuntimeError("Valkey returned an invalid consumer-group name")


async def _prove(container_name: str) -> dict[str, object]:
    _progress("connect_before_restart")
    port = _published_port(container_name)
    redis = await _wait_until_ready(port)
    sink = _DurableReceiptSink()
    config = RemnawaveStreamConsumerConfig(
        consumer_name="proof-consumer-after-restart",
        payload_fingerprint_hmac_key=HMAC_KEY,
        group_name=REMNAWAVE_STREAM_CONSUMER_GROUP,
        block_ms=1,
        reclaim_min_idle_ms=1,
    )
    try:
        transport = RedisStreamTransport(redis, payload_fingerprint_hmac_key=HMAC_KEY)
        await transport.ensure_group(
            SUBSCRIPTION_REQUESTS_STREAM,
            REMNAWAVE_STREAM_CONSUMER_GROUP,
            "0-0",
        )
        message_id_raw = await redis.xadd(
            SUBSCRIPTION_REQUESTS_STREAM,
            {
                "v": "1",
                "userId": "42",
                "requestAt": datetime.now(UTC).isoformat(),
                "requestIp": "198.51.100.42",
                "userAgent": "CyberVPN failover proof",
                "srrResponseType": "raw",
            },
        )
        message_id = message_id_raw.decode() if isinstance(message_id_raw, bytes) else str(message_id_raw)
        messages = await transport.read_new(
            (SUBSCRIPTION_REQUESTS_STREAM,),
            REMNAWAVE_STREAM_CONSUMER_GROUP,
            "proof-consumer-before-restart",
            count=1,
            block_ms=1,
        )
        if len(messages) != 1 or messages[0].message_id != message_id:
            raise AssertionError("proof message was not delivered to the initial consumer")

        _progress("inject_commit_before_ack_failure")
        failing_consumer = RemnawaveStreamConsumer(
            _FailBeforeAckTransport(redis, payload_fingerprint_hmac_key=HMAC_KEY),
            sink,
            config,
        )
        try:
            await failing_consumer._process(messages[0])
        except ConnectionError:
            pass
        else:
            raise AssertionError("the injected acknowledgement failure did not fire")

        if len(sink.receipts) != 1:
            raise AssertionError("the durable sink receipt was not committed before the failure")
        if await transport.pending_count(SUBSCRIPTION_REQUESTS_STREAM, REMNAWAVE_STREAM_CONSUMER_GROUP) != 1:
            raise AssertionError("the unacknowledged entry did not remain in the PEL")
        if await redis.xlen(SUBSCRIPTION_REQUESTS_STREAM) != 1:
            raise AssertionError("the privacy-sensitive source vanished before acknowledgement")
        before_run_id = _server_run_id(await redis.info(section="server"))
        await redis.execute_command("SAVE")
    finally:
        await redis.aclose()

    _progress("stop_valkey")
    _docker("stop", "--time", "10", container_name)
    _progress("start_valkey")
    _docker("start", container_name)

    _progress("connect_after_restart")
    port = _published_port(container_name)
    redis = await _wait_until_ready(port)
    try:
        after_run_id = _server_run_id(await redis.info(section="server"))
        if after_run_id == before_run_id:
            raise AssertionError("Valkey run_id did not change across the restart")

        recovered_transport = RedisStreamTransport(redis, payload_fingerprint_hmac_key=HMAC_KEY)
        recovered_consumer = RemnawaveStreamConsumer(
            recovered_transport,
            sink,
            config,
        )
        _progress("observe_restarted_state")
        await recovered_consumer.initialize()
        await asyncio.sleep(0.01)
        _progress("reclaim_pending_entry")
        reclaimed = await recovered_consumer.reclaim_once()

        pending_after = await recovered_transport.pending_count(
            SUBSCRIPTION_REQUESTS_STREAM,
            REMNAWAVE_STREAM_CONSUMER_GROUP,
        )
        source_length_after = await redis.xlen(SUBSCRIPTION_REQUESTS_STREAM)
        groups = await redis.xinfo_groups(SUBSCRIPTION_REQUESTS_STREAM)
        group_names = sorted(_group_name(item) for item in groups)

        if reclaimed != 1:
            raise AssertionError("the persisted PEL entry was not reclaimed after restart")
        if sink.duplicate_commits != 1 or len(sink.receipts) != 1:
            raise AssertionError("idempotent sink replay did not collapse to the original receipt")
        if pending_after != 0 or source_length_after != 0:
            raise AssertionError("atomic XACK+XDEL did not finalize the recovered entry")
        if group_names != [REMNAWAVE_STREAM_CONSUMER_GROUP]:
            raise AssertionError("the single-consumer-group invariant was not preserved")

        return {
            "status": "passed",
            "stream": "subscription_requests",
            "consumer_group": REMNAWAVE_STREAM_CONSUMER_GROUP,
            "valkey_restart_observed": True,
            "run_id_changed": True,
            "reclaimed_messages": reclaimed,
            "durable_receipts": len(sink.receipts),
            "idempotent_duplicate_commits": sink.duplicate_commits,
            "pending_after": pending_after,
            "source_entries_after": source_length_after,
            "xack_xdel_atomic_finalization": True,
            "single_consumer_group": group_names,
        }
    finally:
        await redis.aclose()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    arguments = parser.parse_args()

    suffix = uuid.uuid4().hex[:12]
    container_name = f"{RESOURCE_PREFIX}valkey-{suffix}"
    volume_name = f"{RESOURCE_PREFIX}data-{suffix}"
    _assert_owned_resource(container_name)
    _assert_owned_resource(volume_name)

    container_created = False
    volume_created = False
    try:
        _docker("image", "inspect", arguments.image)
        _docker("volume", "create", volume_name)
        volume_created = True
        _docker(
            "run",
            "--detach",
            "--name",
            container_name,
            "--mount",
            f"type=volume,source={volume_name},target=/data",
            "--publish",
            "127.0.0.1::6379",
            arguments.image,
            "valkey-server",
            "--appendonly",
            "yes",
            "--appendfsync",
            "always",
        )
        container_created = True
        result = asyncio.run(_prove(container_name))
        result["image"] = arguments.image
        _progress("proof_passed")
        print(json.dumps(result, indent=2, sort_keys=True))  # noqa: T201 - machine-readable evidence
        return 0
    finally:
        if container_created:
            _assert_owned_resource(container_name)
            subprocess.run(  # noqa: S603 - executable and resource namespace are validated
                [DOCKER_EXECUTABLE, "rm", "--force", container_name],
                check=False,
                capture_output=True,
                text=True,
            )
        if volume_created:
            _assert_owned_resource(volume_name)
            subprocess.run(  # noqa: S603 - executable and resource namespace are validated
                [DOCKER_EXECUTABLE, "volume", "rm", volume_name],
                check=False,
                capture_output=True,
                text=True,
            )


if __name__ == "__main__":
    raise SystemExit(main())
