from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from src.presentation.api.v1.public_network import routes as public_network_routes
from src.presentation.api.v1.public_network.routes import (
    _derive_public_status,
    _derive_region_status,
    get_public_network_dpi_score,
    get_public_network_incidents,
    get_public_network_overview,
    get_public_network_regions,
    get_public_network_widget,
    publish_public_network_dpi_score,
)
from src.presentation.api.v1.public_network.schemas import (
    PublicNetworkDpiCountryResponse,
    PublicNetworkDpiMeasurementWindowResponse,
    PublicNetworkDpiScorePublishRequest,
    PublicNetworkDpiScoreResponse,
)


def _patch_snapshot_sources(monkeypatch, *, stats, bandwidth, recap, servers) -> None:
    async def fake_get_or_fetch(_key, _ttl, fetcher):
        return await fetcher()

    class FakeServerBandwidthUseCase:
        def __init__(self, client) -> None:
            self.client = client

        async def execute(self):
            return stats

    class FakeBandwidthAnalyticsUseCase:
        def __init__(self, client) -> None:
            self.client = client

        async def execute(self, period="today"):
            assert period == "today"
            return bandwidth

    class FakeSystemRecapUseCase:
        def __init__(self, client) -> None:
            self.client = client

        async def execute(self):
            return recap

    class FakeManageServersUseCase:
        def __init__(self, gateway) -> None:
            self.gateway = gateway

        async def get_all(self):
            return servers

    monkeypatch.setattr(public_network_routes.response_cache, "get_or_fetch", fake_get_or_fetch)
    monkeypatch.setattr(public_network_routes, "ServerBandwidthUseCase", FakeServerBandwidthUseCase)
    monkeypatch.setattr(public_network_routes, "BandwidthAnalyticsUseCase", FakeBandwidthAnalyticsUseCase)
    monkeypatch.setattr(public_network_routes, "SystemRecapUseCase", FakeSystemRecapUseCase)
    monkeypatch.setattr(public_network_routes, "ManageServersUseCase", FakeManageServersUseCase)


def _build_published_dpi_snapshot(*, countries_tracked: int = 0) -> PublicNetworkDpiScoreResponse:
    now = datetime.now(UTC)
    return PublicNetworkDpiScoreResponse(
        schema_version="public-network-dpi-score.v1",
        generated_at=now,
        expires_at=now + timedelta(minutes=30),
        freshness_status="fresh",
        methodology_version="dpi-score.methodology.v3.reachability-baseline",
        measurement_window=PublicNetworkDpiMeasurementWindowResponse(hours=24, minimum_probe_count=12),
        enabled=False,
        confidence="low",
        last_updated_at=None,
        reason_code="public_dpi_probe_pipeline_not_enabled",
        countries_tracked=countries_tracked,
        countries=[],
    )


def test_derive_status_helpers_handle_outage_and_degraded_states() -> None:
    assert _derive_public_status(total_servers=0, online_servers=0) == "major_outage"
    assert _derive_public_status(total_servers=10, online_servers=0) == "major_outage"
    assert _derive_public_status(total_servers=10, online_servers=9) == "degraded"
    assert _derive_public_status(total_servers=10, online_servers=10) == "online"

    assert _derive_region_status(total_servers=0, online_servers=0) == "offline"
    assert _derive_region_status(total_servers=2, online_servers=0) == "offline"
    assert _derive_region_status(total_servers=2, online_servers=1) == "degraded"
    assert _derive_region_status(total_servers=2, online_servers=2) == "online"


def test_get_public_network_overview_returns_sanitized_metrics(monkeypatch) -> None:
    _patch_snapshot_sources(
        monkeypatch,
        stats={
            "total_users": 1120,
            "active_users": 278,
            "total_servers": 24,
            "online_servers": 24,
            "total_traffic_bytes": 4_500_000_000_000,
        },
        bandwidth={
            "bytes_in": 1_250_000_000,
            "bytes_out": 3_750_000_000,
        },
        recap={
            "total": {
                "nodes": 24,
                "distinct_countries": 8,
                "traffic_bytes": 4_500_000_000_000,
            },
            "this_month": {
                "traffic_bytes": 900_000_000_000,
            },
        },
        servers=[
            SimpleNamespace(
                country_code="US",
                status=SimpleNamespace(value="online"),
                users_online=150,
                used_traffic_bytes=1_500_000_000,
            ),
        ],
    )

    response = asyncio.run(get_public_network_overview(client=object()))

    assert response.freshness_status == "fresh"
    assert response.global_metrics.status == "online"
    assert response.global_metrics.active_users == 278
    assert response.global_metrics.online_servers == 24
    assert response.global_metrics.total_nodes == 24
    assert response.global_metrics.distinct_countries == 8
    assert response.global_metrics.monthly_traffic_bytes == 900_000_000_000
    assert response.global_metrics.today_bytes_out == 3_750_000_000


def test_get_public_network_regions_aggregates_country_buckets(monkeypatch) -> None:
    _patch_snapshot_sources(
        monkeypatch,
        stats={
            "total_users": 100,
            "active_users": 45,
            "total_servers": 3,
            "online_servers": 2,
            "total_traffic_bytes": 1_000_000_000,
        },
        bandwidth={"bytes_in": 0, "bytes_out": 0},
        recap={
            "total": {
                "nodes": 3,
                "distinct_countries": 2,
                "traffic_bytes": 1_000_000_000,
            },
            "this_month": {
                "traffic_bytes": 100_000_000,
            },
        },
        servers=[
            SimpleNamespace(
                country_code="US",
                status=SimpleNamespace(value="online"),
                users_online=20,
                used_traffic_bytes=500_000_000,
            ),
            SimpleNamespace(
                country_code="US",
                status=SimpleNamespace(value="offline"),
                users_online=0,
                used_traffic_bytes=100_000_000,
            ),
            SimpleNamespace(
                country_code="DE",
                status=SimpleNamespace(value="online"),
                users_online=25,
                used_traffic_bytes=400_000_000,
            ),
        ],
    )

    response = asyncio.run(get_public_network_regions(client=object()))

    assert response.freshness_status == "fresh"
    assert len(response.regions) == 2
    assert response.regions[0].id == "de"
    assert response.regions[0].status == "online"
    assert response.regions[1].id == "us"
    assert response.regions[1].status == "degraded"
    assert response.regions[1].total_servers == 2
    assert response.regions[1].online_servers == 1
    assert response.regions[1].active_users == 20


def test_get_public_network_incidents_emits_current_degradation(monkeypatch) -> None:
    _patch_snapshot_sources(
        monkeypatch,
        stats={
            "total_users": 100,
            "active_users": 12,
            "total_servers": 2,
            "online_servers": 1,
            "total_traffic_bytes": 1_000_000,
        },
        bandwidth={"bytes_in": 0, "bytes_out": 0},
        recap={
            "total": {
                "nodes": 2,
                "distinct_countries": 2,
                "traffic_bytes": 1_000_000,
            },
            "this_month": {
                "traffic_bytes": 500_000,
            },
        },
        servers=[
            SimpleNamespace(
                country_code="US",
                status=SimpleNamespace(value="offline"),
                users_online=0,
                used_traffic_bytes=0,
            ),
            SimpleNamespace(
                country_code="DE",
                status=SimpleNamespace(value="online"),
                users_online=12,
                used_traffic_bytes=1_000_000,
            ),
        ],
    )

    response = asyncio.run(get_public_network_incidents(client=object()))

    assert response.freshness_status == "fresh"
    assert len(response.incidents) == 1
    assert response.incidents[0].severity == "critical"
    assert response.incidents[0].affected_regions == ["us"]


def test_get_public_network_widget_returns_embed_ready_payload(monkeypatch) -> None:
    _patch_snapshot_sources(
        monkeypatch,
        stats={
            "total_users": 420,
            "active_users": 126,
            "total_servers": 3,
            "online_servers": 2,
            "total_traffic_bytes": 2_000_000_000,
        },
        bandwidth={"bytes_in": 0, "bytes_out": 0},
        recap={
            "total": {
                "nodes": 3,
                "distinct_countries": 2,
                "traffic_bytes": 2_000_000_000,
            },
            "this_month": {
                "traffic_bytes": 500_000_000,
            },
        },
        servers=[
            SimpleNamespace(
                country_code="DE",
                status=SimpleNamespace(value="online"),
                users_online=66,
                used_traffic_bytes=800_000_000,
            ),
            SimpleNamespace(
                country_code="US",
                status=SimpleNamespace(value="online"),
                users_online=60,
                used_traffic_bytes=900_000_000,
            ),
            SimpleNamespace(
                country_code="US",
                status=SimpleNamespace(value="offline"),
                users_online=0,
                used_traffic_bytes=300_000_000,
            ),
        ],
    )

    response = asyncio.run(
        get_public_network_widget(
            locale="en-EN",
            theme_variant="cyber",
            widget_type="network_card",
            region_id="us",
            client=object(),
        )
    )

    assert response.schema_version == "public-network-widget.v1"
    assert response.widget_type == "network_card"
    assert response.theme_variant == "cyber"
    assert response.summary.status == "degraded"
    assert response.summary.current_availability_pct == 66.67
    assert response.summary.incidents_count == 1
    assert response.focus_region is not None
    assert response.focus_region.id == "us"
    assert response.top_regions[0].id == "us"
    assert response.recommended_height == 420


def test_get_public_network_dpi_score_returns_truthful_disabled_contract(monkeypatch) -> None:
    _patch_snapshot_sources(
        monkeypatch,
        stats={
            "total_users": 420,
            "active_users": 126,
            "total_servers": 2,
            "online_servers": 2,
            "total_traffic_bytes": 2_000_000_000,
        },
        bandwidth={"bytes_in": 0, "bytes_out": 0},
        recap={
            "total": {
                "nodes": 2,
                "distinct_countries": 2,
                "traffic_bytes": 2_000_000_000,
            },
            "this_month": {
                "traffic_bytes": 500_000_000,
            },
        },
        servers=[
            SimpleNamespace(
                country_code="DE",
                status=SimpleNamespace(value="online"),
                users_online=66,
                used_traffic_bytes=800_000_000,
            ),
            SimpleNamespace(
                country_code="US",
                status=SimpleNamespace(value="online"),
                users_online=60,
                used_traffic_bytes=900_000_000,
            ),
        ],
    )

    response = asyncio.run(get_public_network_dpi_score(client=object()))

    assert response.schema_version == "public-network-dpi-score.v1"
    assert response.methodology_version == "dpi-score.methodology.v3.reachability-baseline"
    assert response.measurement_window.hours == 24
    assert response.measurement_window.minimum_probe_count == 12
    assert response.enabled is False
    assert response.confidence == "low"
    assert response.reason_code == "public_dpi_not_enabled"
    assert response.countries_tracked == 2
    assert response.countries == []


def test_get_public_network_dpi_score_prefers_published_snapshot(monkeypatch) -> None:
    published_snapshot = _build_published_dpi_snapshot(countries_tracked=1).model_copy(
        update={
            "confidence": "medium",
            "countries": [
                PublicNetworkDpiCountryResponse(
                    country_code="de",
                    public_name="DE",
                    score=0,
                    confidence="low",
                    last_updated_at=None,
                    protocols=[],
                )
            ],
        }
    ).model_dump(by_alias=True, mode="json")

    async def fake_cache_get(_key):
        return published_snapshot

    async def fail_if_snapshot_fetch_runs(*, client):
        raise AssertionError("network snapshot fallback should not run when published DPI snapshot exists")

    monkeypatch.setattr(public_network_routes.response_cache, "get", fake_cache_get)
    monkeypatch.setattr(public_network_routes, "_get_public_network_snapshot", fail_if_snapshot_fetch_runs)

    response = asyncio.run(get_public_network_dpi_score(client=object()))

    assert response.confidence == "medium"
    assert response.countries_tracked == 1
    assert response.reason_code == "public_dpi_probe_pipeline_not_enabled"


def test_publish_public_network_dpi_score_requires_internal_secret(monkeypatch) -> None:
    payload = PublicNetworkDpiScorePublishRequest(
        source="tests.public-network",
        snapshot=_build_published_dpi_snapshot(),
    )

    async def fail_if_cache_set(*args, **kwargs):
        raise AssertionError("cache write should not run without auth")

    monkeypatch.setattr(public_network_routes.response_cache, "set", fail_if_cache_set)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            publish_public_network_dpi_score(
                payload=payload,
                telegram_bot_secret="wrong-secret",
            )
        )

    assert exc_info.value.status_code == 401


def test_publish_public_network_dpi_score_writes_cache(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_cache_set(key, value, ttl):
        captured["key"] = key
        captured["value"] = value
        captured["ttl"] = ttl

    monkeypatch.setattr(public_network_routes.response_cache, "set", fake_cache_set)
    monkeypatch.setattr(public_network_routes, "_require_telegram_bot_secret", lambda _secret: None)

    payload = PublicNetworkDpiScorePublishRequest(
        source="tests.public-network",
        snapshot=_build_published_dpi_snapshot(),
    )

    response = asyncio.run(
        publish_public_network_dpi_score(
            payload=payload,
            telegram_bot_secret="internal-secret",
        )
    )

    assert response.published is True
    assert response.cache_key == public_network_routes.PUBLIC_NETWORK_DPI_SCORE_CACHE_KEY
    assert captured["key"] == public_network_routes.PUBLIC_NETWORK_DPI_SCORE_CACHE_KEY
    assert isinstance(captured["ttl"], int)
    assert captured["ttl"] > 0
