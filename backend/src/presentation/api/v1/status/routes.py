"""Public status endpoint.

Provides a lightweight health/version check that the mobile app calls
on startup to verify backend reachability.  No authentication required.
"""

from datetime import UTC, datetime

from fastapi import APIRouter

from src.version import __version__

from .schemas import ServiceStatuses, StatusResponse

router = APIRouter(prefix="/status", tags=["status"])


@router.get(
    "",
    response_model=StatusResponse,
    summary="Public API status",
    description=(
        "Returns backend status, version, server timestamp, and "
        "placeholder service health.  Accessible without authentication."
    ),
)
async def get_status() -> StatusResponse:
    """Return current API status.

    This endpoint is intentionally unauthenticated so that mobile
    clients can check connectivity before presenting a login screen.

    Service checks are placeholders that always return ``"ok"``; real
    health probes live behind ``/api/v1/monitoring/health`` (authed).
    """
    return StatusResponse(
        status="ok",
        version=__version__,
        timestamp=datetime.now(UTC),
        services=ServiceStatuses(database="ok", redis="ok"),
    )
