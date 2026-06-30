"""Public runtime fingerprint endpoint for deploy parity checks."""

import os
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.config_service import ConfigService, CustomerSiteRuntimeConfig
from src.config.settings import settings
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.infrastructure.monitoring.metrics import route_operations_total
from src.presentation.dependencies.database import get_db

router = APIRouter(prefix="/runtime", tags=["runtime"])


class RuntimeFingerprintResponse(BaseModel):
    service: str
    release: str | None = None
    git_sha: str | None = None
    container_image: str | None = None
    origin_marker: str
    customer_site_mode: str
    remnawave_token_rotation_required: bool | None = None
    generated_at: datetime


def _first_non_empty(*values: str | None) -> str | None:
    for value in values:
        normalized = (value or "").strip()
        if normalized:
            return normalized
    return None


def _parse_utc_datetime(value: str) -> datetime | None:
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _remnawave_token_rotation_required(now: datetime) -> bool | None:
    expires_at = _parse_utc_datetime(settings.remnawave_token_expires_at)
    if expires_at is not None:
        expires_in_days = int((expires_at - now).total_seconds() // 86400)
        return expires_in_days <= max(0, settings.remnawave_token_rotation_warning_days)
    return None


@router.get("/fingerprint", response_model=RuntimeFingerprintResponse)
async def get_runtime_fingerprint(
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> RuntimeFingerprintResponse:
    """Return a non-secret deploy fingerprint for external/origin parity checks."""
    response.headers["Cache-Control"] = "no-store, max-age=0"
    try:
        site_runtime = await ConfigService(SystemConfigRepository(db)).get_customer_site_runtime_config()
    except Exception:
        site_runtime = CustomerSiteRuntimeConfig()

    route_operations_total.labels(route="runtime", action="fingerprint", status="success").inc()
    now = datetime.now(UTC)
    return RuntimeFingerprintResponse(
        service="backend",
        release=_first_non_empty(settings.sentry_release, os.getenv("SENTRY_RELEASE"), os.getenv("CYBERVPN_IMAGE_TAG")),
        git_sha=_first_non_empty(settings.runtime_git_sha, os.getenv("GIT_SHA"), os.getenv("CI_COMMIT_SHA")),
        container_image=_first_non_empty(
            settings.runtime_container_image,
            os.getenv("CYBERVPN_CONTAINER_IMAGE"),
            os.getenv("CYBERVPN_IMAGE_TAG"),
        ),
        origin_marker=settings.runtime_origin_marker,
        customer_site_mode=site_runtime.mode,
        remnawave_token_rotation_required=_remnawave_token_rotation_required(now),
        generated_at=now,
    )
