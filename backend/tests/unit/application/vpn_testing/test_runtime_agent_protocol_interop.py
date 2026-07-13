from __future__ import annotations

import importlib.util
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

import httpx
import pytest

from src.application.vpn_testing import runtime_agent_client as client


def _agent_credential() -> str:
    return "-".join(("alpha",) * 8)


def _load_runtime_agent(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    secret = _agent_credential()
    monkeypatch.setenv("VPN_TEST_AGENT_SECRET", secret)
    monkeypatch.setenv("VPN_TEST_AGENT_ROLE", "primary")
    repository_root = Path(__file__).resolve().parents[5]
    module_path = repository_root / "services" / "vpn-test-agent" / "src" / "main.py"
    module_name = "vpn_test_agent_protocol_interop"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_backend_post_interoperates_with_real_agent_v2_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = _agent_credential()
    agent = _load_runtime_agent(monkeypatch)

    async def successful_runtime_checks(payload: Any) -> dict[str, Any]:
        assert payload.run_id == "interop-run"
        return {
            "status": "pass",
            "agent_id": "primary-interop-agent",
            "checks": [{"check_key": "runtime.interop", "status": "pass", "details": {}}],
        }

    monkeypatch.setattr(agent, "_run_runtime_checks", successful_runtime_checks)
    real_async_client = httpx.AsyncClient

    class AgentASGIClient:
        captured_request: tuple[str, str, bytes, dict[str, str]] | None = None

        def __init__(self, **_kwargs: Any) -> None:
            self._client = real_async_client(
                transport=httpx.ASGITransport(app=agent.app),
                base_url="http://runtime-agent.test",
            )

        async def __aenter__(self) -> AgentASGIClient:
            await self._client.__aenter__()
            return self

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            await self._client.__aexit__(exc_type, exc, tb)

        def stream(
            self,
            method: str,
            path: str,
            *,
            content: bytes,
            headers: Mapping[str, str],
        ) -> Any:
            assert "X-VPN-Test-Agent-Secret" not in headers
            type(self).captured_request = (method, path, content, dict(headers))
            return self._client.stream(method, path, content=content, headers=headers)

    monkeypatch.setattr(client.httpx, "AsyncClient", AgentASGIClient)
    target = client.RuntimeAgentTarget(
        role="primary",
        url="https://primary-agent.internal",
        secret=secret,
        profiles=(),
    )

    role, result = await client._post_runtime_agent(
        target=target,
        base_payload={
            "run_id": "interop-run",
            "suite_key": "premium_smart_ru_v1",
            "mode": "runtime",
            "runtime_mode": "proxy-only",
            "routes": [],
        },
        redaction_values={secret},
    )

    assert role == "primary"
    assert result["status"] == "pass"
    assert result["agent_id"] == "primary-interop-agent"
    assert secret not in str(result)

    captured_request = AgentASGIClient.captured_request
    assert captured_request is not None
    method, path, content, headers = captured_request
    async with real_async_client(
        transport=httpx.ASGITransport(app=agent.app),
        base_url="http://runtime-agent.test",
    ) as replay_client:
        replay = await replay_client.request(method, path, content=content, headers=headers)

    assert replay.status_code == 401
