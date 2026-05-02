from __future__ import annotations

import hmac
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from src.application.use_cases.monitoring.bandwidth_analytics import BandwidthAnalyticsUseCase
from src.application.use_cases.monitoring.server_bandwidth import ServerBandwidthUseCase
from src.application.use_cases.monitoring.system_recap import SystemRecapUseCase
from src.application.use_cases.servers.manage_servers import ManageServersUseCase
from src.config.settings import settings
from src.infrastructure.cache.response_cache import response_cache
from src.infrastructure.remnawave.server_gateway import RemnawaveServerGateway
from src.presentation.dependencies.remnawave import get_remnawave_client

from .schemas import (
    PublicNetworkDpiMeasurementWindowResponse,
    PublicNetworkDpiScorePublishRequest,
    PublicNetworkDpiScorePublishResponse,
    PublicNetworkDpiScoreResponse,
    PublicNetworkIncidentResponse,
    PublicNetworkIncidentsResponse,
    PublicNetworkLeaderboardEntryResponse,
    PublicNetworkLeaderboardResponse,
    PublicNetworkOverviewGlobalResponse,
    PublicNetworkOverviewResponse,
    PublicNetworkRegionDetailResponse,
    PublicNetworkRegionResponse,
    PublicNetworkRegionsResponse,
    PublicNetworkUptimeResponse,
    PublicNetworkUptimeSummaryResponse,
    PublicNetworkWidgetResponse,
    PublicNetworkWidgetSummaryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public/network", tags=["public-network"])

PUBLIC_NETWORK_DPI_SCORE_CACHE_KEY = "public-network:dpi-score:v1"
PUBLIC_NETWORK_DPI_SCORE_MAX_TTL_SECONDS = 60 * 60 * 24


def _derive_public_status(*, total_servers: int, online_servers: int) -> str:
    if total_servers <= 0 or online_servers <= 0:
        return "major_outage"
    if online_servers < total_servers:
        return "degraded"
    return "online"


def _derive_region_status(*, total_servers: int, online_servers: int) -> str:
    if total_servers <= 0 or online_servers <= 0:
        return "offline"
    if online_servers < total_servers:
        return "degraded"
    return "online"


def _normalize_country_code(raw_country_code: str | None) -> tuple[str, str]:
    if not raw_country_code:
        return ("unknown", "Unknown")

    normalized = raw_country_code.strip().upper()
    if not normalized:
        return ("unknown", "Unknown")
    return (normalized.lower(), normalized)


def _is_valid_telegram_bot_secret(secret: str | None) -> bool:
    configured = settings.telegram_bot_internal_secret.get_secret_value().strip()
    if not configured or not secret:
        return False
    return hmac.compare_digest(secret.strip(), configured)


def _require_telegram_bot_secret(secret: str | None) -> None:
    if _is_valid_telegram_bot_secret(secret):
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")


def _build_incidents(*, regions: list[dict[str, Any]], generated_at: datetime) -> list[dict[str, Any]]:
    incidents: list[dict[str, Any]] = []

    degraded_regions = [region for region in regions if region["status"] != "online"]
    if not degraded_regions:
        return incidents

    total_regions = len(regions)
    major_outage_regions = [region for region in degraded_regions if region["status"] == "offline"]
    if major_outage_regions:
        affected_ids = [region["id"] for region in major_outage_regions]
        incidents.append(
            PublicNetworkIncidentResponse(
                id="incident-major-outage",
                severity="critical",
                status="identified",
                public_title="Regional outage detected",
                public_summary=(
                    f"{len(major_outage_regions)} of {total_regions} tracked regions "
                    "currently report no online servers."
                ),
                affected_regions=affected_ids,
                started_at=generated_at,
                resolved_at=None,
            ).model_dump(by_alias=True, mode="json")
        )

    degraded_only_regions = [region for region in degraded_regions if region["status"] == "degraded"]
    if degraded_only_regions:
        affected_ids = [region["id"] for region in degraded_only_regions]
        incidents.append(
            PublicNetworkIncidentResponse(
                id="incident-regional-degradation",
                severity="major" if len(degraded_only_regions) > 1 else "minor",
                status="monitoring" if not major_outage_regions else "identified",
                public_title="Regional degradation detected",
                public_summary=(
                    f"{len(degraded_only_regions)} of {total_regions} tracked regions "
                    "currently run with partial server availability."
                ),
                affected_regions=affected_ids,
                started_at=generated_at,
                resolved_at=None,
            ).model_dump(by_alias=True, mode="json")
        )

    return incidents


async def _get_public_network_snapshot(*, client) -> dict[str, Any]:
    async def _fetch() -> dict[str, Any]:
        stats_use_case = ServerBandwidthUseCase(client=client)
        bandwidth_use_case = BandwidthAnalyticsUseCase(client=client)
        recap_use_case = SystemRecapUseCase(client=client)
        server_gateway = RemnawaveServerGateway(client=client)
        server_use_case = ManageServersUseCase(gateway=server_gateway)

        degraded = False

        try:
            stats = await stats_use_case.execute()
        except Exception:
            logger.warning("public_network_stats_unavailable")
            degraded = True
            stats = {
                "total_users": 0,
                "active_users": 0,
                "total_servers": 0,
                "online_servers": 0,
                "total_traffic_bytes": 0,
            }

        try:
            bandwidth = await bandwidth_use_case.execute(period="today")
        except Exception:
            logger.warning("public_network_bandwidth_unavailable")
            degraded = True
            bandwidth = {
                "bytes_in": 0,
                "bytes_out": 0,
            }

        try:
            recap = await recap_use_case.execute()
        except Exception:
            logger.warning("public_network_recap_unavailable")
            degraded = True
            recap = {
                "total": {
                    "nodes": 0,
                    "distinct_countries": 0,
                    "traffic_bytes": 0,
                },
                "this_month": {
                    "traffic_bytes": 0,
                },
            }

        try:
            servers = await server_use_case.get_all()
        except Exception:
            logger.warning("public_network_servers_unavailable")
            degraded = True
            servers = []

        region_buckets: dict[str, dict[str, Any]] = {}
        for server in servers:
            region_id, public_name = _normalize_country_code(server.country_code)
            bucket = region_buckets.setdefault(
                region_id,
                {
                    "id": region_id,
                    "country_code": public_name if region_id != "unknown" else "unknown",
                    "public_name": public_name,
                    "total_servers": 0,
                    "online_servers": 0,
                    "active_users": 0,
                    "total_traffic_bytes": 0,
                },
            )
            bucket["total_servers"] += 1
            if server.status.value == "online":
                bucket["online_servers"] += 1
            bucket["active_users"] += max(server.users_online or 0, 0)
            bucket["total_traffic_bytes"] += max(server.used_traffic_bytes or 0, 0)

        regions = [
            PublicNetworkRegionResponse(
                id=region["id"],
                country_code=region["country_code"],
                public_name=region["public_name"],
                status=_derive_region_status(
                    total_servers=region["total_servers"],
                    online_servers=region["online_servers"],
                ),
                total_servers=region["total_servers"],
                online_servers=region["online_servers"],
                active_users=region["active_users"],
                total_traffic_bytes=region["total_traffic_bytes"],
            ).model_dump(by_alias=True, mode="json")
            for region in sorted(
                region_buckets.values(),
                key=lambda item: (
                    -item["online_servers"],
                    -item["active_users"],
                    -item["total_traffic_bytes"],
                    item["public_name"],
                ),
            )
        ]

        now = datetime.now(UTC)
        overview = PublicNetworkOverviewResponse(
            schema_version="public-network-overview.v1",
            generated_at=now,
            expires_at=now + timedelta(seconds=60),
            freshness_status="degraded" if degraded else "fresh",
            global_metrics=PublicNetworkOverviewGlobalResponse(
                status=_derive_public_status(
                    total_servers=int(stats.get("total_servers") or 0),
                    online_servers=int(stats.get("online_servers") or 0),
                ),
                total_users=int(stats.get("total_users") or 0),
                active_users=int(stats.get("active_users") or 0),
                total_servers=int(stats.get("total_servers") or 0),
                online_servers=int(stats.get("online_servers") or 0),
                total_nodes=int(((recap.get("total") or {}).get("nodes")) or 0),
                distinct_countries=int(((recap.get("total") or {}).get("distinct_countries")) or 0),
                total_traffic_bytes=int(stats.get("total_traffic_bytes") or 0),
                monthly_traffic_bytes=int(((recap.get("this_month") or {}).get("traffic_bytes")) or 0),
                today_bytes_in=int(bandwidth.get("bytes_in") or 0),
                today_bytes_out=int(bandwidth.get("bytes_out") or 0),
            ),
        ).model_dump(by_alias=True, mode="json")

        current_availability_pct = round(
            (
                (int(stats.get("online_servers") or 0) / int(stats.get("total_servers") or 1))
                * 100
            ),
            2,
        ) if int(stats.get("total_servers") or 0) > 0 else 0.0

        leaderboard = [
            PublicNetworkLeaderboardEntryResponse(
                rank=index + 1,
                **region,
            ).model_dump(by_alias=True, mode="json")
            for index, region in enumerate(regions)
        ]

        uptime = PublicNetworkUptimeResponse(
            schema_version="public-network-uptime.v1",
            generated_at=now,
            expires_at=now + timedelta(seconds=60),
            freshness_status="degraded" if degraded else "fresh",
            summary=PublicNetworkUptimeSummaryResponse(
                status=overview["global"]["status"],
                current_availability_pct=current_availability_pct,
                history_available=False,
                window_days=90,
                coverage_days=0,
            ),
            history=[],
        ).model_dump(by_alias=True, mode="json")

        incidents = PublicNetworkIncidentsResponse(
            schema_version="public-network-incidents.v1",
            generated_at=now,
            expires_at=now + timedelta(seconds=60),
            freshness_status="degraded" if degraded else "fresh",
            incidents=_build_incidents(regions=regions, generated_at=now),
        ).model_dump(by_alias=True, mode="json")

        regions_response = PublicNetworkRegionsResponse(
            schema_version="public-network-regions.v1",
            generated_at=now,
            expires_at=now + timedelta(seconds=60),
            freshness_status="degraded" if degraded else "fresh",
            regions=[PublicNetworkRegionResponse.model_validate(region) for region in regions],
        ).model_dump(by_alias=True, mode="json")

        leaderboard_response = PublicNetworkLeaderboardResponse(
            schema_version="public-network-leaderboard.v1",
            generated_at=now,
            expires_at=now + timedelta(seconds=60),
            freshness_status="degraded" if degraded else "fresh",
            leaderboard=[PublicNetworkLeaderboardEntryResponse.model_validate(entry) for entry in leaderboard],
        ).model_dump(by_alias=True, mode="json")

        return {
            "overview": overview,
            "regions": regions_response,
            "leaderboard": leaderboard_response,
            "uptime": uptime,
            "incidents": incidents,
        }

    return await response_cache.get_or_fetch("public-network:snapshot:v1", 30, _fetch)


def _build_widget_payload(
    *,
    snapshot: dict[str, Any],
    locale: str,
    theme_variant: str,
    widget_type: str,
    region_id: str | None,
) -> PublicNetworkWidgetResponse:
    overview = PublicNetworkOverviewResponse.model_validate(snapshot["overview"])
    regions = PublicNetworkRegionsResponse.model_validate(snapshot["regions"])
    leaderboard = PublicNetworkLeaderboardResponse.model_validate(snapshot["leaderboard"])
    uptime = PublicNetworkUptimeResponse.model_validate(snapshot["uptime"])
    incidents = PublicNetworkIncidentsResponse.model_validate(snapshot["incidents"])

    focus_region = next((item for item in regions.regions if item.id == region_id), None)
    if region_id is not None and focus_region is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Region not found")

    recommended_height = 420
    top_regions = leaderboard.leaderboard[:3]
    if widget_type == "uptime_badge":
        recommended_height = 220
        top_regions = []
    elif widget_type == "speed_badge":
        recommended_height = 260
        top_regions = leaderboard.leaderboard[:1]

    if focus_region is not None and widget_type == "network_card":
        focused_entry = next((entry for entry in leaderboard.leaderboard if entry.id == focus_region.id), None)
        if focused_entry is None:
            focused_entry = PublicNetworkLeaderboardEntryResponse(rank=0, **focus_region.model_dump())
        top_regions = [focused_entry, *[entry for entry in top_regions if entry.id != focus_region.id]][:3]

    return PublicNetworkWidgetResponse(
        schema_version="public-network-widget.v1",
        generated_at=overview.generated_at,
        expires_at=overview.expires_at,
        freshness_status=overview.freshness_status,
        widget_type=widget_type,
        locale=locale,
        theme_variant=theme_variant,
        recommended_height=recommended_height,
        summary=PublicNetworkWidgetSummaryResponse(
            status=overview.global_metrics.status,
            current_availability_pct=uptime.summary.current_availability_pct,
            online_servers=overview.global_metrics.online_servers,
            active_users=overview.global_metrics.active_users,
            monthly_traffic_bytes=overview.global_metrics.monthly_traffic_bytes,
            incidents_count=len(incidents.incidents),
        ),
        focus_region=focus_region,
        top_regions=top_regions,
    )


def _build_dpi_score_payload(*, snapshot: dict[str, Any]) -> PublicNetworkDpiScoreResponse:
    overview = PublicNetworkOverviewResponse.model_validate(snapshot["overview"])
    regions = PublicNetworkRegionsResponse.model_validate(snapshot["regions"])

    return PublicNetworkDpiScoreResponse(
        schema_version="public-network-dpi-score.v1",
        generated_at=overview.generated_at,
        expires_at=overview.expires_at,
        freshness_status=overview.freshness_status,
        methodology_version="dpi-score.methodology.v3.reachability-baseline",
        measurement_window=PublicNetworkDpiMeasurementWindowResponse(
            hours=24,
            minimum_probe_count=12,
        ),
        enabled=False,
        confidence="low",
        last_updated_at=None,
        reason_code="public_dpi_not_enabled",
        countries_tracked=len(regions.regions),
        countries=[],
    )


async def _get_published_dpi_score_payload() -> PublicNetworkDpiScoreResponse | None:
    cached = await response_cache.get(PUBLIC_NETWORK_DPI_SCORE_CACHE_KEY)
    if cached is None:
        return None

    try:
        return PublicNetworkDpiScoreResponse.model_validate(cached)
    except Exception:
        logger.warning("public_network_dpi_score_cache_invalid")
        await response_cache.invalidate(PUBLIC_NETWORK_DPI_SCORE_CACHE_KEY)
        return None


@router.get("/overview", response_model=PublicNetworkOverviewResponse)
async def get_public_network_overview(
    client=Depends(get_remnawave_client),
) -> PublicNetworkOverviewResponse:
    snapshot = await _get_public_network_snapshot(client=client)
    return PublicNetworkOverviewResponse.model_validate(snapshot["overview"])


@router.get("/regions", response_model=PublicNetworkRegionsResponse)
async def get_public_network_regions(
    client=Depends(get_remnawave_client),
) -> PublicNetworkRegionsResponse:
    snapshot = await _get_public_network_snapshot(client=client)
    return PublicNetworkRegionsResponse.model_validate(snapshot["regions"])


@router.get("/regions/{region_id}", response_model=PublicNetworkRegionDetailResponse)
async def get_public_network_region(
    region_id: str,
    client=Depends(get_remnawave_client),
) -> PublicNetworkRegionDetailResponse:
    snapshot = await _get_public_network_snapshot(client=client)
    regions_payload = PublicNetworkRegionsResponse.model_validate(snapshot["regions"])

    region = next((item for item in regions_payload.regions if item.id == region_id), None)
    if region is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Region not found")

    return PublicNetworkRegionDetailResponse(
        schema_version=regions_payload.schema_version,
        generated_at=regions_payload.generated_at,
        expires_at=regions_payload.expires_at,
        freshness_status=regions_payload.freshness_status,
        region=region,
    )


@router.get("/leaderboard", response_model=PublicNetworkLeaderboardResponse)
async def get_public_network_leaderboard(
    client=Depends(get_remnawave_client),
) -> PublicNetworkLeaderboardResponse:
    snapshot = await _get_public_network_snapshot(client=client)
    return PublicNetworkLeaderboardResponse.model_validate(snapshot["leaderboard"])


@router.get("/uptime", response_model=PublicNetworkUptimeResponse)
async def get_public_network_uptime(
    client=Depends(get_remnawave_client),
) -> PublicNetworkUptimeResponse:
    snapshot = await _get_public_network_snapshot(client=client)
    return PublicNetworkUptimeResponse.model_validate(snapshot["uptime"])


@router.get("/incidents", response_model=PublicNetworkIncidentsResponse)
async def get_public_network_incidents(
    client=Depends(get_remnawave_client),
) -> PublicNetworkIncidentsResponse:
    snapshot = await _get_public_network_snapshot(client=client)
    return PublicNetworkIncidentsResponse.model_validate(snapshot["incidents"])


@router.get("/widget", response_model=PublicNetworkWidgetResponse)
async def get_public_network_widget(
    locale: str = Query("en-EN"),
    theme_variant: Literal["cyber", "matrix", "graphite"] = Query("cyber", alias="themeVariant"),
    widget_type: Literal["network_card", "uptime_badge", "speed_badge"] = Query("network_card", alias="widgetType"),
    region_id: str | None = Query(None, alias="regionId"),
    client=Depends(get_remnawave_client),
) -> PublicNetworkWidgetResponse:
    snapshot = await _get_public_network_snapshot(client=client)
    return _build_widget_payload(
        snapshot=snapshot,
        locale=locale,
        theme_variant=theme_variant,
        widget_type=widget_type,
        region_id=region_id,
    )


@router.get("/dpi-score", response_model=PublicNetworkDpiScoreResponse)
async def get_public_network_dpi_score(
    client=Depends(get_remnawave_client),
) -> PublicNetworkDpiScoreResponse:
    published = await _get_published_dpi_score_payload()
    if published is not None:
        return published

    snapshot = await _get_public_network_snapshot(client=client)
    return _build_dpi_score_payload(snapshot=snapshot)


@router.post(
    "/internal/dpi-score/publish",
    response_model=PublicNetworkDpiScorePublishResponse,
)
async def publish_public_network_dpi_score(
    payload: PublicNetworkDpiScorePublishRequest,
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
) -> PublicNetworkDpiScorePublishResponse:
    _require_telegram_bot_secret(telegram_bot_secret)

    snapshot = payload.snapshot
    now = datetime.now(UTC)
    ttl_seconds = int((snapshot.expires_at - now).total_seconds())
    if ttl_seconds <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="DPI snapshot must expire in the future",
        )

    ttl_seconds = min(ttl_seconds, PUBLIC_NETWORK_DPI_SCORE_MAX_TTL_SECONDS)
    await response_cache.set(
        PUBLIC_NETWORK_DPI_SCORE_CACHE_KEY,
        snapshot.model_dump(by_alias=True, mode="json"),
        ttl=ttl_seconds,
    )
    return PublicNetworkDpiScorePublishResponse(
        published=True,
        source=payload.source,
        cache_key=PUBLIC_NETWORK_DPI_SCORE_CACHE_KEY,
        expires_at=snapshot.expires_at,
    )
