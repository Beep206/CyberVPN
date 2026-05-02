"""Publish measured public DPI substrate snapshots into the backend cache layer."""

from __future__ import annotations

import asyncio
import ssl
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from statistics import median
from typing import Any

import structlog

from src.broker import broker
from src.config import get_settings
from src.metrics import (
    PUBLIC_NETWORK_DPI_ENABLED,
    PUBLIC_NETWORK_DPI_PUBLISH_CONSECUTIVE_FAILURES,
    PUBLIC_NETWORK_DPI_PUBLISH_COUNTRIES_TRACKED,
    PUBLIC_NETWORK_DPI_PUBLISH_DURATION,
    PUBLIC_NETWORK_DPI_PUBLISH_LAST_ATTEMPT_UNIXTIME,
    PUBLIC_NETWORK_DPI_PUBLISH_LAST_SUCCESS_UNIXTIME,
    PUBLIC_NETWORK_DPI_PUBLISH_PROBE_COUNT,
    PUBLIC_NETWORK_DPI_PUBLISH_TOTAL,
    PUBLIC_NETWORK_DPI_SNAPSHOT_FRESHNESS,
)
from src.services.backend_api_client import BackendAPIClient
from src.services.cache_service import CacheService
from src.services.redis_client import get_redis_client
from src.services.remnawave_client import RemnawaveClient

logger = structlog.get_logger(__name__)

DEFAULT_DPI_REASON_CODE = "public_dpi_probe_dimensions_insufficient"
PROBE_TARGETS_UNAVAILABLE_REASON_CODE = "public_dpi_probe_targets_unavailable"
PROBE_SOURCE_UNAVAILABLE_REASON_CODE = "public_dpi_probe_source_unavailable"
SNAPSHOT_TTL_MINUTES = 30
MEASUREMENT_WINDOW_HOURS = 24
PROBE_HISTORY_KEY = "monitoring:public-network:dpi-score:history"
PROBE_HISTORY_TTL_SECONDS = (MEASUREMENT_WINDOW_HOURS + 2) * 60 * 60
PROBE_TIMEOUT_SECONDS = 4.0
PROBE_CONCURRENCY = 8
MAX_PROBES_TOTAL = 24
MAX_PROBES_PER_COUNTRY = 3
CONNECTION_METRIC_KINDS = {"tcp_connect_ms", "tls_handshake_ms"}
MINIMUM_PUBLISH_PROBE_COUNT = 12
MINIMUM_PUBLISH_COUNTRIES = 2
_FRESHNESS_STATES = ("fresh", "degraded", "stale")


def _normalize_country_code(raw_country_code: str | None) -> tuple[str, str]:
    if not raw_country_code:
        return ("unknown", "Unknown")

    normalized = raw_country_code.strip().upper()
    if not normalized:
        return ("unknown", "Unknown")
    return (normalized.lower(), normalized)


def _derive_confidence(*, probe_count: int) -> str:
    if probe_count >= 6:
        return "high"
    if probe_count >= 3:
        return "medium"
    return "low"


def _derive_score(*, success_rate: float) -> int:
    return max(0, min(100, round(success_rate)))


def _derive_latency_score(*, median_handshake_ms: int | None) -> int | None:
    if median_handshake_ms is None:
        return None
    if median_handshake_ms <= 150:
        return 100
    if median_handshake_ms <= 300:
        return 90
    if median_handshake_ms <= 500:
        return 75
    if median_handshake_ms <= 800:
        return 55
    if median_handshake_ms <= 1200:
        return 35
    return 15


def _count_protocol_dimensions(protocol_payload: dict[str, Any]) -> int:
    dimensions = 1
    if protocol_payload.get("medianHandshakeMs") is not None:
        dimensions += 1
    if protocol_payload.get("httpsBaselineSuccessRate") is not None:
        dimensions += 1
    return dimensions


def _derive_protocol_score(protocol_payload: dict[str, Any]) -> int:
    connection_score = float(protocol_payload.get("successRate") or 0.0)
    baseline_score = protocol_payload.get("httpsBaselineSuccessRate")
    latency_score = _derive_latency_score(
        median_handshake_ms=protocol_payload.get("medianHandshakeMs"),
    )

    weighted_score = connection_score * 0.65
    applied_weight = 0.65

    if baseline_score is not None:
        weighted_score += float(baseline_score) * 0.2
        applied_weight += 0.2
    if latency_score is not None:
        weighted_score += latency_score * 0.15
        applied_weight += 0.15

    if applied_weight <= 0:
        return _derive_score(success_rate=connection_score)
    return max(0, min(100, round(weighted_score / applied_weight)))


def _derive_country_confidence(
    *,
    probe_count: int,
    protocol_payloads: list[dict[str, Any]],
) -> str:
    deeply_measured_protocols = sum(
        1 for payload in protocol_payloads if _count_protocol_dimensions(payload) >= 3
    )
    if probe_count >= MINIMUM_PUBLISH_PROBE_COUNT and deeply_measured_protocols >= 1:
        return "high"
    if probe_count >= 6 and deeply_measured_protocols >= 1:
        return "medium"
    return "low"


def _is_country_publishable(country_payload: dict[str, Any]) -> bool:
    if country_payload.get("confidence") not in {"medium", "high"}:
        return False
    return any(
        _count_protocol_dimensions(protocol_payload) >= 3
        for protocol_payload in country_payload.get("protocols", [])
    )


def _derive_snapshot_confidence(*, probe_count: int, publishable_country_count: int) -> str:
    if probe_count >= 24 and publishable_country_count >= 3:
        return "high"
    if probe_count >= MINIMUM_PUBLISH_PROBE_COUNT and publishable_country_count >= MINIMUM_PUBLISH_COUNTRIES:
        return "medium"
    return _derive_confidence(probe_count=probe_count)


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _derive_protocol_label(
    *,
    node: dict[str, Any],
    inbound: dict[str, Any] | None,
    host: dict[str, Any] | None,
    probe_mode: str,
) -> str:
    protocol = str((inbound or {}).get("protocol") or node.get("vpn_protocol") or "unknown").strip().lower()
    security = str(
        (host or {}).get("security") or (inbound or {}).get("security") or (inbound or {}).get("tls") or ""
    ).strip().lower()
    network = str((inbound or {}).get("network") or "").strip().lower()

    parts = [protocol]
    if security:
        parts.append(security)
    if network:
        parts.append(network)
    parts.append("tls" if probe_mode == "tls_handshake" else "tcp")
    return "-".join(part for part in parts if part)


def _build_target_from_binding(
    *,
    node: dict[str, Any],
    inbound: dict[str, Any] | None,
    host: dict[str, Any] | None,
) -> dict[str, Any] | None:
    address = str((host or {}).get("address") or node.get("address") or "").strip()
    port = int((host or {}).get("port") or (inbound or {}).get("port") or node.get("port") or 0)
    if not address or port <= 0:
        return None

    security = str(
        (host or {}).get("security") or (inbound or {}).get("security") or (inbound or {}).get("tls") or ""
    ).strip().lower()
    server_hostname = str(
        (host or {}).get("sni") or (host or {}).get("host") or ""
    ).strip()
    probe_mode = "tls_handshake" if security == "tls" and server_hostname else "tcp_connect"

    country_id, public_name = _normalize_country_code(node.get("country_code"))
    return {
        "country_id": country_id,
        "public_name": public_name,
        "address": address,
        "port": port,
        "server_hostname": server_hostname or None,
        "probe_mode": probe_mode,
        "protocol": _derive_protocol_label(
            node=node,
            inbound=inbound,
            host=host,
            probe_mode=probe_mode,
        ),
    }


def _build_probe_targets(
    nodes: list[dict[str, Any]],
    *,
    inbounds: list[dict[str, Any]] | None = None,
    hosts: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    probes_per_country: dict[str, int] = defaultdict(int)
    seen_targets: set[tuple[str, int, str, str]] = set()

    inbounds_by_node_uuid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for inbound in inbounds or []:
        node_uuid = str(inbound.get("nodeUuid") or inbound.get("node_uuid") or "").strip()
        if node_uuid:
            inbounds_by_node_uuid[node_uuid].append(inbound)

    hosts_by_inbound_uuid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for host in hosts or []:
        inbound_uuid = str(host.get("inboundUuid") or host.get("inbound_uuid") or "").strip()
        if inbound_uuid:
            hosts_by_inbound_uuid[inbound_uuid].append(host)

    for node in nodes:
        if bool(node.get("is_disabled")) or not bool(node.get("is_connected")):
            continue

        country_id, public_name = _normalize_country_code(node.get("country_code"))
        node_uuid = str(node.get("uuid") or "").strip()
        related_inbounds = inbounds_by_node_uuid.get(node_uuid) or [None]

        for inbound in related_inbounds:
            inbound_uuid = str((inbound or {}).get("uuid") or "").strip()
            related_hosts = hosts_by_inbound_uuid.get(inbound_uuid) if inbound_uuid else None
            bindings = related_hosts or [None]

            for host in bindings:
                if probes_per_country[country_id] >= MAX_PROBES_PER_COUNTRY or len(targets) >= MAX_PROBES_TOTAL:
                    break

                target = _build_target_from_binding(node=node, inbound=inbound, host=host)
                if target is None:
                    continue
                target["public_name"] = public_name

                dedupe_key = (
                    target["address"],
                    target["port"],
                    target["protocol"],
                    target["probe_mode"],
                )
                if dedupe_key in seen_targets:
                    continue

                seen_targets.add(dedupe_key)
                probes_per_country[country_id] += 1
                targets.append(target)

            if probes_per_country[country_id] >= MAX_PROBES_PER_COUNTRY or len(targets) >= MAX_PROBES_TOTAL:
                break

    return targets


async def _probe_tcp_endpoint(target: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    writer = None
    now = datetime.now(UTC).isoformat()

    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(target["address"], target["port"]),
            timeout=PROBE_TIMEOUT_SECONDS,
        )
        latency_ms = round((time.perf_counter() - started) * 1000)
        return {
            **target,
            "success": True,
            "latency_ms": latency_ms,
            "metric_kind": "tcp_connect_ms",
            "last_probe_at": now,
            "error_kind": None,
        }
    except Exception as exc:
        return {
            **target,
            "success": False,
            "latency_ms": None,
            "metric_kind": "tcp_connect_ms",
            "last_probe_at": now,
            "error_kind": exc.__class__.__name__,
        }
    finally:
        if writer is not None:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                logger.debug("public_network_dpi_probe_writer_close_failed")


async def _probe_tls_endpoint(target: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    writer = None
    now = datetime.now(UTC).isoformat()
    context = ssl.create_default_context()

    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(
                target["address"],
                target["port"],
                ssl=context,
                server_hostname=target["server_hostname"],
                ssl_handshake_timeout=PROBE_TIMEOUT_SECONDS,
            ),
            timeout=PROBE_TIMEOUT_SECONDS,
        )
        latency_ms = round((time.perf_counter() - started) * 1000)
        return {
            **target,
            "success": True,
            "latency_ms": latency_ms,
            "metric_kind": "tls_handshake_ms",
            "last_probe_at": now,
            "error_kind": None,
        }
    except Exception as exc:
        return {
            **target,
            "success": False,
            "latency_ms": None,
            "metric_kind": "tls_handshake_ms",
            "last_probe_at": now,
            "error_kind": exc.__class__.__name__,
        }
    finally:
        if writer is not None:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                logger.debug("public_network_dpi_tls_probe_writer_close_failed")


async def _probe_https_endpoint(target: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    writer = None
    now = datetime.now(UTC).isoformat()
    context = ssl.create_default_context()

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(
                target["address"],
                target["port"],
                ssl=context,
                server_hostname=target["server_hostname"],
                ssl_handshake_timeout=PROBE_TIMEOUT_SECONDS,
            ),
            timeout=PROBE_TIMEOUT_SECONDS,
        )
        request = (
            f"HEAD / HTTP/1.1\r\n"
            f"Host: {target['server_hostname']}\r\n"
            "User-Agent: CyberVPN-DPI-Probe/1.0\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii", errors="ignore")
        writer.write(request)
        await writer.drain()
        status_line = await asyncio.wait_for(reader.readline(), timeout=PROBE_TIMEOUT_SECONDS)
        latency_ms = round((time.perf_counter() - started) * 1000)
        success = status_line.startswith(b"HTTP/")

        return {
            **target,
            "success": success,
            "latency_ms": latency_ms if success else None,
            "metric_kind": "https_head_ms",
            "last_probe_at": now,
            "error_kind": None if success else "InvalidHttpResponse",
        }
    except Exception as exc:
        return {
            **target,
            "success": False,
            "latency_ms": None,
            "metric_kind": "https_head_ms",
            "last_probe_at": now,
            "error_kind": exc.__class__.__name__,
        }
    finally:
        if writer is not None:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                logger.debug("public_network_dpi_https_probe_writer_close_failed")


async def _run_probes(targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    semaphore = asyncio.Semaphore(PROBE_CONCURRENCY)

    async def _run_single(target: dict[str, Any]) -> list[dict[str, Any]]:
        async with semaphore:
            if target["probe_mode"] == "tls_handshake":
                handshake_result = await _probe_tls_endpoint(target)
                results = [handshake_result]
                if handshake_result["success"] and target.get("server_hostname"):
                    results.append(await _probe_https_endpoint(target))
                return results
            return [await _probe_tcp_endpoint(target)]

    nested_results = await asyncio.gather(*(_run_single(target) for target in targets))
    return [result for results in nested_results for result in results]


def _build_country_payloads(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_country: dict[str, dict[str, Any]] = {}

    for result in results:
        country_id = result["country_id"]
        bucket = by_country.setdefault(
            country_id,
            {
                "countryCode": country_id,
                "publicName": result["public_name"],
                "results": [],
                "protocols": defaultdict(list),
            },
        )
        bucket["results"].append(result)
        bucket["protocols"][result["protocol"]].append(result)

    countries: list[dict[str, Any]] = []
    for _country_id, bucket in sorted(by_country.items()):
        country_results = list(bucket["results"])
        country_score_results = [
            item for item in country_results if item.get("metric_kind") in CONNECTION_METRIC_KINDS
        ]
        total = len(country_score_results)
        last_probe_at = max((item["last_probe_at"] for item in country_results), default=None)

        protocol_payloads: list[dict[str, Any]] = []
        for protocol, protocol_results in sorted(bucket["protocols"].items()):
            protocol_connection_results = [
                item for item in protocol_results if item.get("metric_kind") in CONNECTION_METRIC_KINDS
            ]
            protocol_total = len(protocol_connection_results)
            protocol_successes = sum(1 for item in protocol_connection_results if item["success"])
            protocol_success_rate = (
                (protocol_successes / protocol_total) * 100 if protocol_total else 0.0
            )
            latencies = [
                item["latency_ms"]
                for item in protocol_results
                if item["latency_ms"] is not None and item.get("metric_kind") == "tls_handshake_ms"
            ]
            baseline_results = [
                item for item in protocol_results if item.get("metric_kind") == "https_head_ms"
            ]
            baseline_total = len(baseline_results)
            baseline_successes = sum(1 for item in baseline_results if item["success"])
            baseline_success_rate = (
                (baseline_successes / baseline_total) * 100 if baseline_total else None
            )
            baseline_latencies = [
                item["latency_ms"]
                for item in baseline_results
                if item["latency_ms"] is not None
            ]
            protocol_payloads.append(
                {
                    "protocol": protocol,
                    "successRate": round(protocol_success_rate, 2),
                    "medianHandshakeMs": round(median(latencies)) if latencies else None,
                    "httpsBaselineSuccessRate": round(baseline_success_rate, 2)
                    if baseline_success_rate is not None
                    else None,
                    "medianHttpsBaselineMs": round(median(baseline_latencies)) if baseline_latencies else None,
                    "lastProbeAt": max((item["last_probe_at"] for item in protocol_results), default=None),
                }
            )

        protocol_scores = [_derive_protocol_score(payload) for payload in protocol_payloads]
        country_score = (
            round(sum(protocol_scores) / len(protocol_scores))
            if protocol_scores
            else _derive_score(success_rate=0.0)
        )

        countries.append(
            {
                "countryCode": bucket["countryCode"],
                "publicName": bucket["publicName"],
                "score": country_score,
                "confidence": _derive_country_confidence(
                    probe_count=total,
                    protocol_payloads=protocol_payloads,
                ),
                "lastUpdatedAt": last_probe_at,
                "protocols": protocol_payloads,
            }
        )

    return sorted(
        countries,
        key=lambda item: (-int(item["score"]), item["publicName"]),
    )


def _trim_probe_history(results: list[dict[str, Any]], *, now: datetime) -> list[dict[str, Any]]:
    cutoff = now - timedelta(hours=MEASUREMENT_WINDOW_HOURS)
    trimmed: list[dict[str, Any]] = []
    for result in results:
        last_probe_at = _parse_iso_datetime(str(result.get("last_probe_at") or ""))
        if last_probe_at is None or last_probe_at < cutoff:
            continue
        trimmed.append(result)
    return trimmed


async def _load_probe_history(cache: CacheService) -> list[dict[str, Any]]:
    payload = await cache.get(PROBE_HISTORY_KEY)
    if not isinstance(payload, dict):
        return []
    results = payload.get("results")
    if not isinstance(results, list):
        return []
    return [item for item in results if isinstance(item, dict)]


async def _persist_probe_history(
    cache: CacheService,
    *,
    results: list[dict[str, Any]],
    updated_at: datetime,
) -> None:
    await cache.set(
        PROBE_HISTORY_KEY,
        {
            "updatedAt": updated_at.isoformat(),
            "windowHours": MEASUREMENT_WINDOW_HOURS,
            "results": results,
        },
        ttl=PROBE_HISTORY_TTL_SECONDS,
    )


def _build_publish_payload(
    *,
    countries: list[dict[str, Any]],
    probe_count: int,
    freshness_status: str,
    reason_code: str,
) -> dict[str, Any]:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=SNAPSHOT_TTL_MINUTES)
    countries_tracked = len(countries)
    last_updated_at = max(
        (country.get("lastUpdatedAt") for country in countries if country.get("lastUpdatedAt")),
        default=None,
    )
    publishable_country_count = sum(1 for country in countries if _is_country_publishable(country))
    enabled = (
        freshness_status == "fresh"
        and probe_count >= MINIMUM_PUBLISH_PROBE_COUNT
        and publishable_country_count >= MINIMUM_PUBLISH_COUNTRIES
    )

    return {
        "source": "task-worker.monitoring.public_network_dpi_score",
        "snapshot": {
            "schemaVersion": "public-network-dpi-score.v1",
            "generatedAt": now.isoformat(),
            "expiresAt": expires_at.isoformat(),
            "freshnessStatus": freshness_status,
            "methodologyVersion": "dpi-score.methodology.v3.reachability-baseline",
            "measurementWindow": {
                "hours": MEASUREMENT_WINDOW_HOURS,
                "minimumProbeCount": MINIMUM_PUBLISH_PROBE_COUNT,
            },
            "enabled": enabled,
            "confidence": _derive_snapshot_confidence(
                probe_count=probe_count,
                publishable_country_count=publishable_country_count,
            ),
            "lastUpdatedAt": last_updated_at if countries_tracked > 0 else None,
            "reasonCode": None if enabled else reason_code,
            "countriesTracked": countries_tracked,
            "countries": countries,
        },
    }


def _set_freshness_state_metrics(current_state: str) -> None:
    for freshness_state in _FRESHNESS_STATES:
        PUBLIC_NETWORK_DPI_SNAPSHOT_FRESHNESS.labels(
            freshness_status=freshness_state,
        ).set(1 if freshness_state == current_state else 0)


def _record_publish_success(
    *,
    freshness_status: str,
    enabled: bool,
    countries_tracked: int,
    probe_count: int,
    duration_seconds: float,
) -> None:
    now_unix = time.time()
    PUBLIC_NETWORK_DPI_PUBLISH_LAST_ATTEMPT_UNIXTIME.set(now_unix)
    PUBLIC_NETWORK_DPI_PUBLISH_LAST_SUCCESS_UNIXTIME.set(now_unix)
    PUBLIC_NETWORK_DPI_PUBLISH_CONSECUTIVE_FAILURES.set(0)
    PUBLIC_NETWORK_DPI_PUBLISH_COUNTRIES_TRACKED.set(countries_tracked)
    PUBLIC_NETWORK_DPI_PUBLISH_PROBE_COUNT.set(probe_count)
    PUBLIC_NETWORK_DPI_ENABLED.set(1 if enabled else 0)
    _set_freshness_state_metrics(freshness_status)
    PUBLIC_NETWORK_DPI_PUBLISH_DURATION.observe(duration_seconds)
    PUBLIC_NETWORK_DPI_PUBLISH_TOTAL.labels(
        result="success",
        freshness_status=freshness_status,
        enabled="true" if enabled else "false",
    ).inc()


def _record_publish_failure(*, freshness_status: str, duration_seconds: float) -> None:
    PUBLIC_NETWORK_DPI_PUBLISH_LAST_ATTEMPT_UNIXTIME.set(time.time())
    PUBLIC_NETWORK_DPI_PUBLISH_CONSECUTIVE_FAILURES.inc()
    PUBLIC_NETWORK_DPI_PUBLISH_DURATION.observe(duration_seconds)
    PUBLIC_NETWORK_DPI_PUBLISH_TOTAL.labels(
        result="failure",
        freshness_status=freshness_status,
        enabled="false",
    ).inc()


@broker.task(task_name="publish_public_network_dpi_score", queue="monitoring")
async def publish_public_network_dpi_score() -> dict[str, Any]:
    """Publish a truthful measured DPI substrate snapshot for public consumption.

    The public score is enabled only when the current measurement window has
    enough fresh multi-signal evidence. Until then the same publication path
    stays active but remains honestly gated rather than fabricating a score.
    """
    settings = get_settings()
    if not settings.backend_api_url or settings.backend_internal_secret is None:
        logger.info("public_network_dpi_publish_skipped", reason="backend_api_not_configured")
        return {"skipped": True, "reason": "backend_api_not_configured"}

    freshness_status = "fresh"
    reason_code = DEFAULT_DPI_REASON_CODE
    countries: list[dict[str, Any]] = []
    probe_count = 0
    now = datetime.now(UTC)
    started = time.perf_counter()

    async with BackendAPIClient() as backend:
        if not backend.enabled:
            logger.info("public_network_dpi_publish_skipped", reason="backend_api_disabled")
            return {"skipped": True, "reason": "backend_api_disabled"}

        redis = get_redis_client()
        cache = CacheService(redis)

        try:
            historical_results = _trim_probe_history(await _load_probe_history(cache), now=now)

            current_probe_results: list[dict[str, Any]] = []
            try:
                async with RemnawaveClient() as remnawave:
                    nodes = await remnawave.get_nodes()
                    try:
                        inbounds = await remnawave.get_inbounds()
                        hosts = await remnawave.get_hosts()
                    except Exception as exc:
                        logger.warning("public_network_dpi_probe_enrichment_unavailable", error=str(exc))
                        inbounds = []
                        hosts = []
                targets = _build_probe_targets(nodes, inbounds=inbounds, hosts=hosts)
                if not targets:
                    freshness_status = "degraded"
                    reason_code = PROBE_TARGETS_UNAVAILABLE_REASON_CODE
                else:
                    current_probe_results = await _run_probes(targets)
                    merged_results = _trim_probe_history([*historical_results, *current_probe_results], now=now)
                    await _persist_probe_history(
                        cache,
                        results=merged_results,
                        updated_at=now,
                    )
                    historical_results = merged_results
                    current_probe_results = []
            except Exception as exc:
                freshness_status = "degraded"
                reason_code = PROBE_SOURCE_UNAVAILABLE_REASON_CODE
                logger.warning("public_network_dpi_probe_source_unavailable", error=str(exc))

            effective_results = _trim_probe_history([*historical_results, *current_probe_results], now=now)
            probe_count = len(effective_results)
            countries = _build_country_payloads(effective_results)

            payload = _build_publish_payload(
                countries=countries,
                probe_count=probe_count,
                freshness_status=freshness_status,
                reason_code=reason_code,
            )
            try:
                response = await backend.publish_public_network_dpi_score(payload)
            except Exception:
                _record_publish_failure(
                    freshness_status=freshness_status,
                    duration_seconds=time.perf_counter() - started,
                )
                raise

            enabled = bool((payload.get("snapshot") or {}).get("enabled"))
            _record_publish_success(
                freshness_status=freshness_status,
                enabled=enabled,
                countries_tracked=len(countries),
                probe_count=probe_count,
                duration_seconds=time.perf_counter() - started,
            )
            result = {
                "published": True,
                "countries_tracked": len(countries),
                "freshness_status": freshness_status,
                "reason_code": reason_code,
                "probe_count": probe_count,
                "cache_key": response.get("cacheKey"),
                "expires_at": response.get("expiresAt"),
            }
            logger.info("public_network_dpi_snapshot_published", **result)
            return result
        finally:
            await redis.aclose()
