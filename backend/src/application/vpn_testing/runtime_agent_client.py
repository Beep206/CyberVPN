"""Internal client for the VPN test runtime agent."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx

from src.config.settings import settings


def _agent_secret() -> str:
    secret = settings.vpn_test_agent_secret
    return secret.get_secret_value().strip() if secret is not None else ""


def runtime_agent_configured() -> bool:
    return bool(settings.vpn_test_agent_url and _agent_secret())


async def call_runtime_agent(
    *,
    run_id: str,
    suite_key: str,
    mode: str,
    route_entries: Sequence[Any],
) -> dict[str, Any]:
    url = str(settings.vpn_test_agent_url or "").rstrip("/")
    secret = _agent_secret()
    if not url or not secret:
        return {"status": "degraded", "reason": "agent_unavailable", "agent_id": None, "checks": []}
    routes = []
    for entry in route_entries:
        metadata = getattr(entry, "metadata_json", None)
        routes.append(
            {
                "route_key": getattr(entry, "route_key", ""),
                "country_code": getattr(entry, "country_code", ""),
                "expected_modes": list(getattr(entry, "expected_modes", []) or []),
                "metadata": dict(metadata or {}) if isinstance(metadata, dict) else {},
            }
        )
    payload = {
        "run_id": run_id,
        "suite_key": suite_key,
        "mode": mode,
        "runtime_mode": "proxy-only" if mode == "runtime" else mode,
        "tun_sandbox_requested": False,
        "routes": routes,
    }
    timeout = httpx.Timeout(
        connect=min(5.0, float(settings.vpn_test_agent_timeout_seconds)),
        read=float(settings.vpn_test_agent_timeout_seconds),
        write=10.0,
        pool=5.0,
    )
    async with httpx.AsyncClient(base_url=url, timeout=timeout) as client:
        response = await client.post(
            "/internal/v1/runtime-checks",
            json=payload,
            headers={"X-VPN-Test-Agent-Secret": secret},
        )
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {"status": "degraded", "reason": "agent_invalid_response"}
