"""Unit tests for public network DPI score publishing task."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.tasks.monitoring.publish_public_network_dpi_score import (
    _build_country_payloads,
    _build_probe_targets,
    _build_publish_payload,
    _run_probes,
    _trim_probe_history,
    publish_public_network_dpi_score,
)


def test_build_probe_targets_uses_connected_nodes_and_caps_per_country() -> None:
    targets = _build_probe_targets(
        [
            {
                "uuid": "node-de-1",
                "address": "de-1.example.com",
                "port": 443,
                "country_code": "DE",
                "is_connected": True,
                "is_disabled": False,
                "vpn_protocol": "vless",
            },
            {
                "uuid": "node-de-2",
                "address": "de-2.example.com",
                "port": 443,
                "country_code": "DE",
                "is_connected": True,
                "is_disabled": False,
                "vpn_protocol": "vless",
            },
            {
                "uuid": "node-de-3",
                "address": "de-3.example.com",
                "port": 443,
                "country_code": "DE",
                "is_connected": True,
                "is_disabled": False,
                "vpn_protocol": "vless",
            },
            {
                "uuid": "node-de-4",
                "address": "de-4.example.com",
                "port": 443,
                "country_code": "DE",
                "is_connected": True,
                "is_disabled": False,
                "vpn_protocol": "vless",
            },
            {
                "uuid": "node-us-1",
                "address": "offline.example.com",
                "port": 443,
                "country_code": "US",
                "is_connected": False,
                "is_disabled": False,
            },
        ]
    )

    assert len(targets) == 3
    assert all(target["country_id"] == "de" for target in targets)
    assert all(target["protocol"] == "vless-tcp" for target in targets)
    assert all(target["probe_mode"] == "tcp_connect" for target in targets)


def test_build_probe_targets_prefers_host_and_inbound_metadata_for_tls() -> None:
    targets = _build_probe_targets(
        [
            {
                "uuid": "node-de-1",
                "address": "node-de.example.com",
                "port": 443,
                "country_code": "DE",
                "is_connected": True,
                "is_disabled": False,
                "vpn_protocol": "vless",
            }
        ],
        inbounds=[
            {
                "uuid": "inbound-1",
                "nodeUuid": "node-de-1",
                "protocol": "vless",
                "network": "ws",
                "security": "tls",
                "port": 8443,
            }
        ],
        hosts=[
            {
                "uuid": "host-1",
                "inboundUuid": "inbound-1",
                "address": "edge-de.example.com",
                "port": 443,
                "sni": "cdn-de.example.com",
                "security": "tls",
            }
        ],
    )

    assert len(targets) == 1
    assert targets[0]["address"] == "edge-de.example.com"
    assert targets[0]["port"] == 443
    assert targets[0]["server_hostname"] == "cdn-de.example.com"
    assert targets[0]["probe_mode"] == "tls_handshake"
    assert targets[0]["protocol"] == "vless-tls-ws-tls"


def test_build_country_payloads_aggregates_real_probe_results() -> None:
    countries = _build_country_payloads(
        [
            {
                "country_id": "de",
                "public_name": "DE",
                "protocol": "vless-tcp",
                "metric_kind": "tcp_connect_ms",
                "success": True,
                "latency_ms": 120,
                "last_probe_at": "2026-04-22T10:00:00+00:00",
            },
            {
                "country_id": "de",
                "public_name": "DE",
                "protocol": "vless-tcp",
                "metric_kind": "tcp_connect_ms",
                "success": False,
                "latency_ms": None,
                "last_probe_at": "2026-04-22T10:01:00+00:00",
            },
            {
                "country_id": "us",
                "public_name": "US",
                "protocol": "vless-tls-ws-tls",
                "metric_kind": "tls_handshake_ms",
                "success": True,
                "latency_ms": 80,
                "last_probe_at": "2026-04-22T10:02:00+00:00",
            },
        ]
    )

    assert len(countries) == 2
    by_country = {country["countryCode"]: country for country in countries}
    assert by_country["de"]["score"] == 50
    assert by_country["de"]["confidence"] == "low"
    assert by_country["de"]["protocols"][0]["successRate"] == 50.0
    assert by_country["de"]["protocols"][0]["medianHandshakeMs"] is None
    assert by_country["de"]["protocols"][0]["httpsBaselineSuccessRate"] is None
    assert by_country["us"]["score"] == 100
    assert by_country["us"]["protocols"][0]["medianHandshakeMs"] == 80


def test_build_country_payloads_exposes_https_baseline_metrics() -> None:
    countries = _build_country_payloads(
        [
            {
                "country_id": "de",
                "public_name": "DE",
                "protocol": "vless-tls-ws-tls",
                "metric_kind": "tls_handshake_ms",
                "success": True,
                "latency_ms": 120,
                "last_probe_at": "2026-04-22T10:00:00+00:00",
            },
            {
                "country_id": "de",
                "public_name": "DE",
                "protocol": "vless-tls-ws-tls",
                "metric_kind": "https_head_ms",
                "success": True,
                "latency_ms": 180,
                "last_probe_at": "2026-04-22T10:01:00+00:00",
            },
        ]
    )

    assert len(countries) == 1
    assert countries[0]["score"] == 100
    assert countries[0]["protocols"][0]["successRate"] == 100.0
    assert countries[0]["protocols"][0]["medianHandshakeMs"] == 120
    assert countries[0]["protocols"][0]["httpsBaselineSuccessRate"] == 100.0
    assert countries[0]["protocols"][0]["medianHttpsBaselineMs"] == 180


def test_build_publish_payload_sets_truthful_disabled_contract() -> None:
    payload = _build_publish_payload(
        countries=[
            {
                "countryCode": "de",
                "publicName": "DE",
                "score": 50,
                "confidence": "low",
                "lastUpdatedAt": "2026-04-22T10:00:00+00:00",
                "protocols": [
                    {
                        "protocol": "vless-tls-ws-tls",
                        "successRate": 50.0,
                        "medianHandshakeMs": 120,
                        "httpsBaselineSuccessRate": 50.0,
                        "medianHttpsBaselineMs": 180,
                        "lastProbeAt": "2026-04-22T10:00:00+00:00",
                    }
                ],
            }
        ],
        probe_count=2,
        freshness_status="fresh",
        reason_code="public_dpi_probe_dimensions_insufficient",
    )

    assert payload["source"] == "task-worker.monitoring.public_network_dpi_score"
    assert payload["snapshot"]["enabled"] is False
    assert payload["snapshot"]["countriesTracked"] == 1
    assert payload["snapshot"]["reasonCode"] == "public_dpi_probe_dimensions_insufficient"
    assert payload["snapshot"]["methodologyVersion"] == "dpi-score.methodology.v3.reachability-baseline"
    assert payload["snapshot"]["measurementWindow"]["hours"] == 24
    assert payload["snapshot"]["measurementWindow"]["minimumProbeCount"] == 12
    assert payload["snapshot"]["countries"][0]["countryCode"] == "de"
    assert payload["snapshot"]["countries"][0]["protocols"][0]["httpsBaselineSuccessRate"] == 50.0


def test_build_publish_payload_enables_public_score_when_signal_is_sufficient() -> None:
    payload = _build_publish_payload(
        countries=[
            {
                "countryCode": "de",
                "publicName": "DE",
                "score": 92,
                "confidence": "high",
                "lastUpdatedAt": "2026-04-22T10:00:00+00:00",
                "protocols": [
                    {
                        "protocol": "vless-tls-ws-tls",
                        "successRate": 100.0,
                        "medianHandshakeMs": 120,
                        "httpsBaselineSuccessRate": 100.0,
                        "medianHttpsBaselineMs": 180,
                        "lastProbeAt": "2026-04-22T10:00:00+00:00",
                    }
                ],
            },
            {
                "countryCode": "us",
                "publicName": "US",
                "score": 88,
                "confidence": "medium",
                "lastUpdatedAt": "2026-04-22T10:00:00+00:00",
                "protocols": [
                    {
                        "protocol": "vless-tls-ws-tls",
                        "successRate": 95.0,
                        "medianHandshakeMs": 160,
                        "httpsBaselineSuccessRate": 90.0,
                        "medianHttpsBaselineMs": 220,
                        "lastProbeAt": "2026-04-22T10:00:00+00:00",
                    }
                ],
            },
        ],
        probe_count=12,
        freshness_status="fresh",
        reason_code="public_dpi_probe_dimensions_insufficient",
    )

    assert payload["snapshot"]["enabled"] is True
    assert payload["snapshot"]["confidence"] == "medium"
    assert payload["snapshot"]["reasonCode"] is None


@pytest.mark.asyncio
async def test_run_probes_adds_https_baseline_after_successful_tls_handshake() -> None:
    target = {
        "country_id": "de",
        "public_name": "DE",
        "address": "edge-de.example.com",
        "port": 443,
        "server_hostname": "cdn-de.example.com",
        "probe_mode": "tls_handshake",
        "protocol": "vless-tls-ws-tls",
    }

    with (
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score._probe_tls_endpoint",
            new=AsyncMock(
                return_value={
                    **target,
                    "success": True,
                    "latency_ms": 120,
                    "metric_kind": "tls_handshake_ms",
                    "last_probe_at": "2026-04-22T10:00:00+00:00",
                    "error_kind": None,
                }
            ),
        ),
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score._probe_https_endpoint",
            new=AsyncMock(
                return_value={
                    **target,
                    "success": True,
                    "latency_ms": 180,
                    "metric_kind": "https_head_ms",
                    "last_probe_at": "2026-04-22T10:00:01+00:00",
                    "error_kind": None,
                }
            ),
        ),
    ):
        results = await _run_probes([target])

    assert len(results) == 2
    assert [result["metric_kind"] for result in results] == ["tls_handshake_ms", "https_head_ms"]


@pytest.mark.asyncio
async def test_publish_public_network_dpi_score_publishes_measured_snapshot(mock_settings, mock_redis):
    mock_backend = AsyncMock()
    mock_backend.enabled = True
    mock_backend.publish_public_network_dpi_score = AsyncMock(
        return_value={
            "published": True,
            "cacheKey": "public-network:dpi-score:v1",
            "expiresAt": "2026-04-22T10:30:00+00:00",
        }
    )
    mock_remnawave = AsyncMock()
    mock_remnawave.get_nodes = AsyncMock(
        return_value=[
            {
                "uuid": "node-de-1",
                "address": "de-1.example.com",
                "port": 443,
                "country_code": "DE",
                "is_connected": True,
                "is_disabled": False,
                "vpn_protocol": "vless",
            },
            {
                "uuid": "node-us-1",
                "address": "us-1.example.com",
                "port": 443,
                "country_code": "US",
                "is_connected": True,
                "is_disabled": False,
                "vpn_protocol": "vless",
            },
        ]
    )
    mock_remnawave.get_inbounds = AsyncMock(return_value=[])
    mock_remnawave.get_hosts = AsyncMock(return_value=[])
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value={"results": []})
    mock_cache.set = AsyncMock()

    with (
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score.CacheService",
            return_value=mock_cache,
        ),
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score.BackendAPIClient"
        ) as mock_backend_cls,
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score.RemnawaveClient"
        ) as mock_remnawave_cls,
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score._run_probes",
            new=AsyncMock(
                return_value=[
                    {
                        "country_id": "de",
                        "public_name": "DE",
                        "protocol": "vless-tls-ws-tls",
                        "metric_kind": "tls_handshake_ms",
                        "success": True,
                        "latency_ms": 120,
                        "last_probe_at": "2026-04-22T10:00:00+00:00",
                    },
                    {
                        "country_id": "de",
                        "public_name": "DE",
                        "protocol": "vless-tls-ws-tls",
                        "metric_kind": "https_head_ms",
                        "success": True,
                        "latency_ms": 180,
                        "last_probe_at": "2026-04-22T10:00:01+00:00",
                    },
                    {
                        "country_id": "us",
                        "public_name": "US",
                        "protocol": "vless-reality-tcp",
                        "metric_kind": "tcp_connect_ms",
                        "success": False,
                        "latency_ms": None,
                        "last_probe_at": "2026-04-22T10:00:00+00:00",
                    },
                ]
            ),
        ),
    ):
        mock_backend_cls.return_value.__aenter__ = AsyncMock(return_value=mock_backend)
        mock_backend_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_remnawave_cls.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        mock_remnawave_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await publish_public_network_dpi_score()

    assert result["published"] is True
    assert result["countries_tracked"] == 2
    assert result["freshness_status"] == "fresh"
    assert result["reason_code"] == "public_dpi_probe_dimensions_insufficient"
    mock_backend.publish_public_network_dpi_score.assert_awaited_once()
    publish_payload = mock_backend.publish_public_network_dpi_score.await_args.args[0]
    assert publish_payload["snapshot"]["enabled"] is False
    assert publish_payload["snapshot"]["countriesTracked"] == 2
    assert len(publish_payload["snapshot"]["countries"]) == 2
    assert publish_payload["snapshot"]["methodologyVersion"] == "dpi-score.methodology.v3.reachability-baseline"
    assert publish_payload["snapshot"]["countries"][0]["protocols"][0]["httpsBaselineSuccessRate"] == 100.0
    assert result["probe_count"] == 3
    mock_cache.set.assert_awaited_once()
    mock_redis.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_publish_public_network_dpi_score_enables_snapshot_after_sufficient_history(
    mock_settings,
    mock_redis,
):
    mock_backend = AsyncMock()
    mock_backend.enabled = True
    mock_backend.publish_public_network_dpi_score = AsyncMock(
        return_value={
            "published": True,
            "cacheKey": "public-network:dpi-score:v1",
            "expiresAt": "2026-04-22T10:30:00+00:00",
        }
    )
    mock_remnawave = AsyncMock()
    mock_remnawave.get_nodes = AsyncMock(
        return_value=[
            {
                "uuid": "node-de-1",
                "address": "de-1.example.com",
                "port": 443,
                "country_code": "DE",
                "is_connected": True,
                "is_disabled": False,
                "vpn_protocol": "vless",
            },
            {
                "uuid": "node-us-1",
                "address": "us-1.example.com",
                "port": 443,
                "country_code": "US",
                "is_connected": True,
                "is_disabled": False,
                "vpn_protocol": "vless",
            },
        ]
    )
    mock_remnawave.get_inbounds = AsyncMock(return_value=[])
    mock_remnawave.get_hosts = AsyncMock(return_value=[])

    def _build_historical_results(extra_runs: int) -> list[dict[str, object]]:
        return [
            {
                "country_id": country_id,
                "public_name": public_name,
                "protocol": "vless-tls-ws-tls",
                "metric_kind": metric_kind,
                "success": True,
                "latency_ms": latency_ms,
                "last_probe_at": (datetime.now(UTC) - timedelta(hours=2 - run * 0.1)).isoformat(),
            }
            for run in range(extra_runs)
            for country_id, public_name in (("de", "DE"), ("us", "US"))
            for metric_kind, latency_ms in (
                ("tls_handshake_ms", 140 + run),
                ("https_head_ms", 210 + run),
            )
        ]

    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value={"results": _build_historical_results(extra_runs=6)})
    mock_cache.set = AsyncMock()

    with (
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score.CacheService",
            return_value=mock_cache,
        ),
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score.BackendAPIClient"
        ) as mock_backend_cls,
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score.RemnawaveClient"
        ) as mock_remnawave_cls,
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score._run_probes",
            new=AsyncMock(return_value=[]),
        ),
    ):
        mock_backend_cls.return_value.__aenter__ = AsyncMock(return_value=mock_backend)
        mock_backend_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_remnawave_cls.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        mock_remnawave_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await publish_public_network_dpi_score()

    publish_payload = mock_backend.publish_public_network_dpi_score.await_args.args[0]
    assert result["published"] is True
    assert result["freshness_status"] == "fresh"
    assert result["probe_count"] == 24
    assert publish_payload["snapshot"]["enabled"] is True
    assert publish_payload["snapshot"]["reasonCode"] is None
    assert publish_payload["snapshot"]["confidence"] == "medium"


@pytest.mark.asyncio
async def test_publish_public_network_dpi_score_marks_missing_targets(mock_settings, mock_redis):
    mock_backend = AsyncMock()
    mock_backend.enabled = True
    mock_backend.publish_public_network_dpi_score = AsyncMock(
        return_value={
            "published": True,
            "cacheKey": "public-network:dpi-score:v1",
            "expiresAt": "2026-04-22T10:30:00+00:00",
        }
    )
    mock_remnawave = AsyncMock()
    mock_remnawave.get_nodes = AsyncMock(return_value=[])
    mock_remnawave.get_inbounds = AsyncMock(return_value=[])
    mock_remnawave.get_hosts = AsyncMock(return_value=[])
    historical_result = {
        "country_id": "de",
        "public_name": "DE",
        "protocol": "vless-tls-ws-tls",
        "metric_kind": "tls_handshake_ms",
        "success": True,
        "latency_ms": 120,
        "last_probe_at": datetime.now(UTC).isoformat(),
    }
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value={"results": [historical_result]})
    mock_cache.set = AsyncMock()

    with (
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score.CacheService",
            return_value=mock_cache,
        ),
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score.BackendAPIClient"
        ) as mock_backend_cls,
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score.RemnawaveClient"
        ) as mock_remnawave_cls,
    ):
        mock_backend_cls.return_value.__aenter__ = AsyncMock(return_value=mock_backend)
        mock_backend_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_remnawave_cls.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        mock_remnawave_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await publish_public_network_dpi_score()

    assert result["published"] is True
    assert result["countries_tracked"] == 1
    assert result["freshness_status"] == "degraded"
    assert result["reason_code"] == "public_dpi_probe_targets_unavailable"
    assert result["probe_count"] == 1
    mock_cache.set.assert_not_awaited()
    mock_redis.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_publish_public_network_dpi_score_degrades_when_probe_source_unavailable(mock_settings, mock_redis):
    mock_backend = AsyncMock()
    mock_backend.enabled = True
    mock_backend.publish_public_network_dpi_score = AsyncMock(
        return_value={
            "published": True,
            "cacheKey": "public-network:dpi-score:v1",
            "expiresAt": "2026-04-22T10:30:00+00:00",
        }
    )
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value={"results": []})
    mock_cache.set = AsyncMock()

    with (
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score.CacheService",
            return_value=mock_cache,
        ),
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score.BackendAPIClient"
        ) as mock_backend_cls,
        patch(
            "src.tasks.monitoring.publish_public_network_dpi_score.RemnawaveClient"
        ) as mock_remnawave_cls,
    ):
        mock_backend_cls.return_value.__aenter__ = AsyncMock(return_value=mock_backend)
        mock_backend_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_remnawave_cls.return_value.__aenter__ = AsyncMock(side_effect=RuntimeError("boom"))
        mock_remnawave_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await publish_public_network_dpi_score()

    assert result["published"] is True
    assert result["countries_tracked"] == 0
    assert result["freshness_status"] == "degraded"
    assert result["reason_code"] == "public_dpi_probe_source_unavailable"
    assert result["probe_count"] == 0
    mock_redis.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_publish_public_network_dpi_score_skips_without_backend_config(mock_settings):
    mock_settings.backend_api_url = None
    mock_settings.backend_internal_secret = None

    with patch(
        "src.tasks.monitoring.publish_public_network_dpi_score.get_settings",
        return_value=mock_settings,
    ):
        result = await publish_public_network_dpi_score()

    assert result == {"skipped": True, "reason": "backend_api_not_configured"}


def test_trim_probe_history_drops_stale_results() -> None:
    now = datetime.now(UTC)
    recent = {
        "last_probe_at": (now - timedelta(hours=1)).isoformat(),
        "country_id": "de",
    }
    stale = {
        "last_probe_at": (now - timedelta(hours=25)).isoformat(),
        "country_id": "us",
    }

    trimmed = _trim_probe_history([recent, stale], now=now)

    assert trimmed == [recent]
