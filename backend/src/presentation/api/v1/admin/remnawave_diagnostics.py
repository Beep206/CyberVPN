from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from httpx import HTTPError
from pydantic import BaseModel, Field

from src.config.settings import settings
from src.domain.enums import AdminRole
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.dependencies import get_remnawave_client, require_role

router = APIRouter(prefix="/admin/remnawave", tags=["admin", "remnawave"])


class AdminRemnawaveNodeDiagnosticsItem(BaseModel):
    uuid: str
    name: str
    status: str
    cpu_load_1m: float | None = None
    cpu_load_5m: float | None = None
    cpu_load_15m: float | None = None
    online_users: int | None = None
    xray_version: str | None = None
    node_version: str | None = None
    tags: list[str] = Field(default_factory=list)
    xhttp_enabled: bool = False
    consumption_multiplier: float | None = None


class AdminRemnawaveNodeDiagnosticsResponse(BaseModel):
    nodes: list[AdminRemnawaveNodeDiagnosticsItem] = Field(default_factory=list)
    metrics_source: str
    updated_at: datetime
    token_scope_label: str | None = None
    token_expires_at: datetime | None = None
    token_expires_in_days: int | None = None
    token_rotation_required: bool = False
    feature_flags: dict[str, str | bool | list[str]] = Field(default_factory=dict)
    degraded_reason: str | None = None


def _as_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("response", "nodes", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _str_value(value: Any, fallback: str = "") -> str:
    return str(value).strip() if value is not None and str(value).strip() else fallback


def _float_value(*values: Any) -> float | None:
    for value in values:
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _int_value(*values: Any) -> int | None:
    for value in values:
        if value is None or value == "":
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _csv_values(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


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


def _token_metadata(now: datetime) -> tuple[datetime | None, int | None, bool]:
    expires_at = _parse_utc_datetime(settings.remnawave_token_expires_at)
    expires_in_days: int | None = None
    rotation_required = False
    if expires_at is not None:
        expires_in_days = int((expires_at - now).total_seconds() // 86400)
        rotation_required = expires_in_days <= max(0, settings.remnawave_token_rotation_warning_days)
    return expires_at, expires_in_days, rotation_required


def _feature_flags() -> dict[str, str | bool | list[str]]:
    return {
        "xhttp_enabled": settings.remnawave_feature_xhttp_enabled,
        "xhttp_mihomo_enabled": settings.remnawave_feature_xhttp_mihomo_enabled,
        "xhttp_rollout_mode": settings.remnawave_feature_xhttp_rollout_mode,
        "xhttp_force_disabled": settings.remnawave_feature_xhttp_force_disabled,
        "xhttp_allowed_plan_codes": _csv_values(settings.remnawave_feature_xhttp_allowed_plan_codes),
        "xhttp_allowed_user_segments": _csv_values(settings.remnawave_feature_xhttp_allowed_user_segments),
        "hysteria2_enabled": settings.remnawave_feature_hysteria2_enabled,
        "ech_enabled": settings.remnawave_feature_ech_enabled,
        "tun_enabled": settings.remnawave_feature_tun_enabled,
        "v2plus_enabled": settings.remnawave_feature_v2plus_enabled,
    }


def _tags_from_node(node: dict[str, Any]) -> list[str]:
    tags = node.get("tags")
    if isinstance(tags, list):
        return sorted({str(tag).strip() for tag in tags if str(tag).strip()})
    tag = node.get("tag")
    if isinstance(tag, str) and tag.strip():
        return [tag.strip()]
    return []


def _node_metric(node: dict[str, Any], *keys: str) -> Any:
    metrics = node.get("metrics")
    for key in keys:
        if key in node:
            return node[key]
        if isinstance(metrics, dict) and key in metrics:
            return metrics[key]
    return None


def _diagnostics_item(node: dict[str, Any]) -> AdminRemnawaveNodeDiagnosticsItem:
    tags = _tags_from_node(node)
    status_text = "connected" if bool(node.get("isConnected") or node.get("connected")) else "disconnected"
    if bool(node.get("isDisabled")):
        status_text = "disabled"
    return AdminRemnawaveNodeDiagnosticsItem(
        uuid=_str_value(node.get("uuid") or node.get("id"), "unknown"),
        name=_str_value(node.get("name") or node.get("remark"), "unknown"),
        status=status_text,
        cpu_load_1m=_float_value(_node_metric(node, "cpuLoad1m", "cpuLoadAverage1m", "loadAverage1m")),
        cpu_load_5m=_float_value(_node_metric(node, "cpuLoad5m", "cpuLoadAverage5m", "loadAverage5m")),
        cpu_load_15m=_float_value(_node_metric(node, "cpuLoad15m", "cpuLoadAverage15m", "loadAverage15m")),
        online_users=_int_value(node.get("usersOnline"), node.get("onlineUsers"), node.get("online")),
        xray_version=_str_value(node.get("xrayVersion") or (node.get("versions") or {}).get("xray"), ""),
        node_version=_str_value(node.get("nodeVersion") or (node.get("versions") or {}).get("node"), ""),
        tags=tags,
        xhttp_enabled=any(tag.lower() == "xhttp" for tag in tags),
        consumption_multiplier=_float_value(node.get("nodeConsumptionMultiplier"), node.get("consumptionMultiplier")),
    )


@router.get("/nodes/diagnostics", response_model=AdminRemnawaveNodeDiagnosticsResponse)
async def get_remnawave_node_diagnostics(
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> AdminRemnawaveNodeDiagnosticsResponse:
    now = datetime.now(UTC)
    token_expires_at, token_expires_in_days, token_rotation_required = _token_metadata(now)
    try:
        payload = await client.get("/nodes")
    except HTTPError as exc:
        return AdminRemnawaveNodeDiagnosticsResponse(
            nodes=[],
            metrics_source="unavailable",
            updated_at=now,
            token_scope_label=settings.remnawave_token_scope_label.strip() or None,
            token_expires_at=token_expires_at,
            token_expires_in_days=token_expires_in_days,
            token_rotation_required=token_rotation_required,
            feature_flags=_feature_flags(),
            degraded_reason=type(exc).__name__,
        )

    nodes = [_diagnostics_item(item) for item in _as_items(payload)]
    metrics_source = "remnawave_api"
    if any(
        node.cpu_load_1m is not None or node.cpu_load_5m is not None or node.cpu_load_15m is not None
        for node in nodes
    ):
        metrics_source = "remnawave_api_with_node_load"
    return AdminRemnawaveNodeDiagnosticsResponse(
        nodes=nodes,
        metrics_source=metrics_source,
        updated_at=now,
        token_scope_label=settings.remnawave_token_scope_label.strip() or None,
        token_expires_at=token_expires_at,
        token_expires_in_days=token_expires_in_days,
        token_rotation_required=token_rotation_required,
        feature_flags=_feature_flags(),
    )
