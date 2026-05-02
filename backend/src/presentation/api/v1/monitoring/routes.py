"""Monitoring and health check routes."""

import hmac
import logging
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.monitoring.bandwidth_analytics import BandwidthAnalyticsUseCase
from src.application.use_cases.monitoring.server_bandwidth import ServerBandwidthUseCase
from src.application.use_cases.monitoring.system_health import SystemHealthUseCase
from src.application.use_cases.monitoring.system_metadata import SystemMetadataUseCase
from src.application.use_cases.monitoring.system_recap import SystemRecapUseCase
from src.config.settings import settings
from src.infrastructure.cache.redis_client import check_redis_connection
from src.infrastructure.cache.response_cache import response_cache
from src.infrastructure.database.session import check_db_connection
from src.infrastructure.monitoring.instrumentation.partner_runtime import (
    bind_partner_frontend_runtime_context,
    bind_partner_frontend_web_vital_context,
    log_partner_runtime_event,
    observe_partner_frontend_runtime_event,
    observe_partner_frontend_web_vital,
)
from src.infrastructure.monitoring.metrics import monitoring_operations_total
from src.presentation.dependencies.remnawave import get_remnawave_client
from src.presentation.dependencies.roles import require_permission

from .schemas import (
    BandwidthResponse,
    FrontendRuntimeEventAck,
    FrontendRuntimeEventRequest,
    FrontendWebVitalEventAck,
    FrontendWebVitalEventRequest,
    HealthResponse,
    MetadataResponse,
    RecapResponse,
    StatsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


def _sanitize_token(value: str | None, *, fallback: str = "unknown") -> str:
    if not value:
        return fallback

    normalized = "".join(
        char if char.isalnum() or char in "._/-" else "_"
        for char in value.strip().lower()
    )[:80]
    return normalized or fallback


def _sanitize_path(value: str | None, *, fallback: str = "/") -> str:
    if not value:
        return fallback
    return value.strip()[:256] or fallback


def _require_frontend_observability_secret(secret: str | None) -> None:
    configured = settings.frontend_observability_internal_secret.get_secret_value().strip()
    if not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Frontend observability ingest is not configured.",
        )
    if not secret or not hmac.compare_digest(secret.strip(), configured):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")


def _sanitize_frontend_runtime_payload(payload: FrontendRuntimeEventRequest) -> dict[str, Any]:
    return {
        "blocked_reason": _sanitize_token(payload.blocked_reason, fallback="none")
        if payload.blocked_reason
        else None,
        "connection_type": _sanitize_token(payload.connection_type),
        "device_bucket": _sanitize_token(payload.device_bucket),
        "duration_ms": max(payload.duration_ms, 0.0)
        if isinstance(payload.duration_ms, (int, float))
        else None,
        "endpoint_template": _sanitize_path(payload.endpoint_template, fallback="/")
        if payload.endpoint_template
        else None,
        "error_code": _sanitize_token(payload.error_code, fallback="none")
        if payload.error_code
        else None,
        "event": payload.event,
        "form_name": _sanitize_token(payload.form_name, fallback="none") if payload.form_name else None,
        "lane": _sanitize_token(payload.lane, fallback="none") if payload.lane else None,
        "locale": (payload.locale or "").strip()[:16] or None,
        "method": _sanitize_token(payload.method, fallback="unknown") if payload.method else None,
        "path": _sanitize_path(payload.path),
        "reduced_motion": _sanitize_token(payload.reduced_motion),
        "release_ring": _sanitize_token(payload.release_ring, fallback="none")
        if payload.release_ring
        else None,
        "request_id": (payload.request_id or "").strip()[:128] or None,
        "result": _sanitize_token(payload.result, fallback="none") if payload.result else None,
        "route_group": payload.route_group,
        "save_data": _sanitize_token(payload.save_data),
        "surface": payload.surface,
        "viewport_bucket": _sanitize_token(payload.viewport_bucket),
        "workspace_status": _sanitize_token(payload.workspace_status, fallback="none")
        if payload.workspace_status
        else None,
    }


def _sanitize_frontend_web_vital_payload(payload: FrontendWebVitalEventRequest) -> dict[str, Any]:
    return {
        "connection_type": _sanitize_token(payload.connection_type),
        "device_bucket": _sanitize_token(payload.device_bucket),
        "locale": (payload.locale or "").strip()[:16] or None,
        "metric": payload.metric,
        "path": _sanitize_path(payload.path),
        "rating": _sanitize_token(payload.rating),
        "reduced_motion": _sanitize_token(payload.reduced_motion),
        "request_id": (payload.request_id or "").strip()[:128] or None,
        "route_group": payload.route_group,
        "save_data": _sanitize_token(payload.save_data),
        "surface": payload.surface,
        "value": max(payload.value, 0.0) if isinstance(payload.value, (int, float)) else 0.0,
        "viewport_bucket": _sanitize_token(payload.viewport_bucket),
    }


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"description": "One or more components unhealthy"}},
)
@router.get(
    "/health/",
    response_model=HealthResponse,
    include_in_schema=False,
)
async def health_check(
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.MONITORING_READ)),
) -> dict[str, Any]:
    """Authenticated system health check endpoint."""

    async def _fetch() -> dict[str, Any]:
        async def db_check() -> None:
            if not await check_db_connection():
                raise RuntimeError("Database connection failed")

        async def redis_check() -> None:
            ok, _ = await check_redis_connection()
            if not ok:
                raise RuntimeError("Redis connection failed")

        async def remnawave_check() -> None:
            if not await client.health_check():
                raise RuntimeError("Remnawave API health check failed")

        use_case = SystemHealthUseCase(
            db_check=db_check,
            redis_check=redis_check,
            remnawave_check=remnawave_check,
        )
        return await use_case.execute()

    result = await response_cache.get_or_fetch("monitoring:health", 10, _fetch)
    monitoring_operations_total.labels(operation="health_check").inc()
    return result


@router.get(
    "/stats",
    response_model=StatsResponse,
    responses={200: {"model": StatsResponse, "description": "Server bandwidth statistics"}},
)
@router.get(
    "/stats/",
    response_model=StatsResponse,
    include_in_schema=False,
)
async def get_system_stats(
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.MONITORING_READ)),
) -> dict[str, Any]:
    """Get bandwidth statistics (authenticated)."""

    async def _fetch() -> dict[str, Any]:
        use_case = ServerBandwidthUseCase(client=client)

        try:
            stats = await use_case.execute()
        except Exception:
            logger.warning("Remnawave unavailable for monitoring stats, returning zeros")
            stats = {
                "total_users": 0,
                "active_users": 0,
                "total_servers": 0,
                "online_servers": 0,
                "total_traffic_bytes": 0,
            }

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            **stats,
        }

    result = await response_cache.get_or_fetch("monitoring:stats", 15, _fetch)
    monitoring_operations_total.labels(operation="stats").inc()
    return result


@router.get(
    "/bandwidth",
    response_model=BandwidthResponse,
    responses={200: {"model": BandwidthResponse, "description": "Bandwidth analytics data"}},
)
@router.get(
    "/bandwidth/",
    response_model=BandwidthResponse,
    include_in_schema=False,
)
async def get_bandwidth_analytics(
    client=Depends(get_remnawave_client),
    period: str = Query(
        "today",
        max_length=50,
        description="Period for analytics: today, week, month",
    ),
    _: None = Depends(require_permission(Permission.MONITORING_READ)),
) -> dict[str, Any]:
    """Get bandwidth analytics for a specific period (authenticated)."""

    async def _fetch() -> dict[str, Any]:
        use_case = BandwidthAnalyticsUseCase(client=client)

        try:
            stats = await use_case.execute(period=period)
        except Exception:
            logger.warning("Remnawave unavailable for bandwidth analytics, returning zeros")
            stats = {"bytes_in": 0, "bytes_out": 0}

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "period": period,
            **stats,
        }

    result = await response_cache.get_or_fetch(f"monitoring:bandwidth:{period}", 10, _fetch)
    monitoring_operations_total.labels(operation="bandwidth").inc()
    return result


@router.get(
    "/metadata",
    response_model=MetadataResponse,
    responses={200: {"model": MetadataResponse, "description": "Remnawave panel metadata"}},
)
@router.get(
    "/metadata/",
    response_model=MetadataResponse,
    include_in_schema=False,
)
async def get_metadata(
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.MONITORING_READ)),
) -> dict[str, Any]:
    """Get Remnawave panel metadata for operational visibility."""

    async def _fetch() -> dict[str, Any]:
        use_case = SystemMetadataUseCase(client=client)

        try:
            metadata = await use_case.execute()
        except Exception:
            logger.warning("Remnawave unavailable for metadata, returning placeholder payload")
            metadata = {
                "version": "unknown",
                "build": {"time": "unknown", "number": "unknown"},
                "git": {
                    "backend": {"commit_sha": "unknown", "branch": "unknown", "commit_url": ""},
                    "frontend": {"commit_sha": "unknown", "commit_url": ""},
                },
            }

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            **metadata,
        }

    result = await response_cache.get_or_fetch("monitoring:metadata", 60, _fetch)
    monitoring_operations_total.labels(operation="metadata").inc()
    return result


@router.get(
    "/recap",
    response_model=RecapResponse,
    responses={200: {"model": RecapResponse, "description": "Remnawave system recap"}},
)
@router.get(
    "/recap/",
    response_model=RecapResponse,
    include_in_schema=False,
)
async def get_recap(
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.MONITORING_READ)),
) -> dict[str, Any]:
    """Get aggregated Remnawave recap data for operations."""

    async def _fetch() -> dict[str, Any]:
        use_case = SystemRecapUseCase(client=client)

        try:
            recap = await use_case.execute()
        except Exception:
            logger.warning("Remnawave unavailable for recap, returning zeros")
            recap = {
                "version": "unknown",
                "init_date": None,
                "total": {
                    "users": 0,
                    "nodes": 0,
                    "traffic_bytes": 0,
                    "nodes_ram": None,
                    "nodes_cpu_cores": 0,
                    "distinct_countries": 0,
                },
                "this_month": {
                    "users": 0,
                    "traffic_bytes": 0,
                },
            }

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            **recap,
        }

    result = await response_cache.get_or_fetch("monitoring:recap", 60, _fetch)
    monitoring_operations_total.labels(operation="recap").inc()
    return result


@router.post(
    "/frontend-runtime-events",
    response_model=FrontendRuntimeEventAck,
    status_code=status.HTTP_202_ACCEPTED,
    responses={401: {"description": "Internal secret missing or invalid"}},
)
@router.post(
    "/frontend-runtime-events/",
    response_model=FrontendRuntimeEventAck,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
async def ingest_frontend_runtime_event(
    payload: FrontendRuntimeEventRequest,
    request: Request,
    frontend_observability_secret: Annotated[
        str | None,
        Header(alias="X-Frontend-Observability-Secret"),
    ] = None,
) -> FrontendRuntimeEventAck:
    """Accept frontend UX telemetry from trusted partner/admin app routes."""

    _require_frontend_observability_secret(frontend_observability_secret)
    event = _sanitize_frontend_runtime_payload(payload)
    bind_partner_frontend_runtime_context(
        surface=event["surface"],
        route_group=event["route_group"],
        workspace_status=event["workspace_status"],
        lane=event["lane"],
        blocked_reason=event["blocked_reason"],
        result=event["result"],
        error_code=event["error_code"],
        endpoint_template=event["endpoint_template"],
        form_name=event["form_name"],
        request_id=event["request_id"],
        method=event["method"],
    )
    observe_partner_frontend_runtime_event(
        event=event["event"],
        surface=event["surface"],
        route_group=event["route_group"],
        duration_ms=event["duration_ms"],
        endpoint_template=event["endpoint_template"],
        error_code=event["error_code"],
        form_name=event["form_name"],
        lane=event["lane"],
        method=event["method"],
        result=event["result"],
        workspace_status=event["workspace_status"],
        blocked_reason=event["blocked_reason"],
    )
    log_partner_runtime_event(
        "partner_frontend_runtime.ingested",
        frontend_event=event["event"],
        surface=event["surface"],
        route_group=event["route_group"],
        path=event["path"],
        locale=event["locale"],
        request_id=event["request_id"],
        endpoint_template=event["endpoint_template"],
        form_name=event["form_name"],
        blocked_reason=event["blocked_reason"],
        workspace_status=event["workspace_status"],
        lane=event["lane"],
        result=event["result"],
        error_code=event["error_code"],
        forwarded_for=request.headers.get("x-forwarded-for"),
    )
    monitoring_operations_total.labels(operation="frontend_runtime_event").inc()
    return FrontendRuntimeEventAck(status="accepted")


@router.post(
    "/frontend-web-vitals",
    response_model=FrontendWebVitalEventAck,
    status_code=status.HTTP_202_ACCEPTED,
    responses={401: {"description": "Internal secret missing or invalid"}},
)
@router.post(
    "/frontend-web-vitals/",
    response_model=FrontendWebVitalEventAck,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
async def ingest_frontend_web_vital(
    payload: FrontendWebVitalEventRequest,
    request: Request,
    frontend_observability_secret: Annotated[
        str | None,
        Header(alias="X-Frontend-Observability-Secret"),
    ] = None,
) -> FrontendWebVitalEventAck:
    """Accept frontend web-vitals telemetry from trusted partner/admin app routes."""

    _require_frontend_observability_secret(frontend_observability_secret)
    event = _sanitize_frontend_web_vital_payload(payload)
    bind_partner_frontend_web_vital_context(
        surface=event["surface"],
        route_group=event["route_group"],
        metric=event["metric"],
        rating=event["rating"],
        request_id=event["request_id"],
    )
    observe_partner_frontend_web_vital(
        surface=event["surface"],
        route_group=event["route_group"],
        metric=event["metric"],
        rating=event["rating"],
        value=event["value"],
    )
    log_partner_runtime_event(
        "partner_frontend_web_vital.ingested",
        surface=event["surface"],
        route_group=event["route_group"],
        metric=event["metric"],
        rating=event["rating"],
        value=event["value"],
        path=event["path"],
        locale=event["locale"],
        request_id=event["request_id"],
        forwarded_for=request.headers.get("x-forwarded-for"),
    )
    monitoring_operations_total.labels(operation="frontend_web_vital").inc()
    return FrontendWebVitalEventAck(status="accepted")
