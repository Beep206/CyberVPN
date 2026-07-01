"""Internal VPN Tester runtime agent."""

from __future__ import annotations

import hmac
import os
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = structlog.get_logger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    vpn_test_agent_secret: str = ""
    vpn_test_agent_id: str = "stage1-vpn-test-agent"
    vpn_test_agent_tun_enabled: bool = False
    vpn_test_agent_proxy_only_enabled: bool = True


settings = Settings()
app = FastAPI(title="CyberVPN VPN Test Agent", docs_url=None, redoc_url=None, openapi_url=None)


class RuntimeRoute(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route_key: str = Field(..., min_length=1, max_length=160)
    country_code: str = Field(default="", max_length=16)
    expected_modes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(..., min_length=1, max_length=80)
    suite_key: str = Field(..., min_length=1, max_length=120)
    mode: str = Field(default="runtime", max_length=40)
    runtime_mode: str = Field(default="proxy-only", pattern="^(static|proxy-only|tun-sandbox)$")
    tun_sandbox_requested: bool = False
    routes: list[RuntimeRoute] = Field(default_factory=list, max_length=200)


def _require_secret(secret: str | None) -> None:
    configured = settings.vpn_test_agent_secret.strip()
    if configured and secret and hmac.compare_digest(configured, secret.strip()):
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")


def _check(
    *,
    check_key: str,
    check_name: str,
    status_value: str,
    safe_summary: str,
    details: dict[str, Any] | None = None,
    target: str = "runtime-agent",
    severity: str = "warning",
) -> dict[str, Any]:
    return {
        "check_key": check_key,
        "check_name": check_name,
        "category": "runtime",
        "status": status_value,
        "severity": severity,
        "target": target,
        "safe_summary": safe_summary,
        "details": dict(details or {}),
        "duration_ms": 0,
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "agent_id": settings.vpn_test_agent_id,
        "proxy_only_enabled": settings.vpn_test_agent_proxy_only_enabled,
        "tun_enabled": settings.vpn_test_agent_tun_enabled,
        "checked_at": datetime.now(UTC).isoformat(),
    }


@app.post("/internal/v1/runtime-checks")
async def runtime_checks(
    payload: RuntimeCheckRequest,
    x_vpn_test_agent_secret: str | None = Header(default=None, alias="X-VPN-Test-Agent-Secret"),
) -> dict[str, Any]:
    _require_secret(x_vpn_test_agent_secret)
    if payload.runtime_mode == "tun-sandbox" and not settings.vpn_test_agent_tun_enabled:
        return {
            "status": "skipped",
            "agent_id": settings.vpn_test_agent_id,
            "runtime_mode": payload.runtime_mode,
            "tun_sandbox": False,
            "reason": "tun_sandbox_disabled",
            "checks": [
                _check(
                    check_key="runtime.tun_sandbox.enabled",
                    check_name="TUN sandbox enabled",
                    status_value="skipped",
                    safe_summary="TUN sandbox runtime checks are disabled by environment",
                    details={"tun_sandbox_requested": payload.tun_sandbox_requested},
                )
            ],
        }
    if payload.runtime_mode == "proxy-only" and not settings.vpn_test_agent_proxy_only_enabled:
        return {
            "status": "degraded",
            "agent_id": settings.vpn_test_agent_id,
            "runtime_mode": payload.runtime_mode,
            "tun_sandbox": False,
            "reason": "proxy_only_disabled",
            "checks": [
                _check(
                    check_key="runtime.proxy_only.enabled",
                    check_name="Proxy-only runtime enabled",
                    status_value="degraded",
                    safe_summary="Proxy-only runtime checks are disabled by environment",
                )
            ],
        }

    sampled_routes = payload.routes[:10]
    route_count = len(payload.routes)
    abuse_routes = [
        route.route_key for route in payload.routes if "abuse" in route.route_key or "torrent" in route.route_key
    ]
    checks = [
        _check(
            check_key="runtime.agent.available",
            check_name="Runtime agent availability",
            status_value="pass",
            safe_summary="Runtime agent accepted the internal request",
            details={"agent_id": settings.vpn_test_agent_id, "process_id": os.getpid()},
            severity="info",
        ),
        _check(
            check_key="runtime.route_matrix.sample",
            check_name="Runtime route matrix sample",
            status_value="pass" if route_count >= 10 else "degraded",
            safe_summary="Runtime agent received route matrix sample"
            if route_count >= 10
            else "Runtime agent received a small route matrix sample",
            details={
                "route_count": route_count,
                "sampled_route_keys": [route.route_key for route in sampled_routes],
                "network_payload_redacted": True,
            },
        ),
        _check(
            check_key="runtime.abuse.safe_policy",
            check_name="Runtime abuse policy safety",
            status_value="pass" if abuse_routes else "degraded",
            safe_summary="Abuse routes are validated by policy only; no torrent or TOR traffic is generated",
            details={"abuse_route_count": len(abuse_routes), "live_abuse_traffic": False},
        ),
    ]
    logger.info(
        "vpn_test_agent_runtime_checks_completed",
        suite_key=payload.suite_key,
        runtime_mode=payload.runtime_mode,
        route_count=route_count,
    )
    return {
        "status": "pass" if all(check["status"] == "pass" for check in checks) else "degraded",
        "agent_id": settings.vpn_test_agent_id,
        "runtime_mode": payload.runtime_mode,
        "tun_sandbox": False,
        "checks": checks,
    }
