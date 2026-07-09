from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.vpn_testing.service import VpnTesterService
from src.config.settings import settings

REPO_ROOT = Path(__file__).resolve().parents[5]
HARDENED_TEMPLATE = REPO_ROOT / "scripts/remnawave/templates/cybervpn-premium-smart-ru-de-primary-hardened.yaml"


def _smart_ru_plan(name: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        name=name,
        plan_code="premium_smart_ru",
        display_name="Premium Smart RU",
        catalog_access_class="private_code_gated",
        catalog_visibility="hidden",
        duration_days=30,
        traffic_limit_bytes=None,
        traffic_policy={},
        connection_modes=["standard", "stealth", "smart_routing"],
        server_pool=["premium_smart_ru"],
        device_limit=5,
    )


def _route_entry(index: int) -> SimpleNamespace:
    domains = ["gosuslugi.ru", "nalog.gov.ru", "sberbank.ru", "telegram.org"]
    return SimpleNamespace(
        route_key=f"route-{index}",
        country_code="RU",
        node_tags=["premium_smart_ru"],
        expected_modes=["xhttp"],
        metadata_json={"domain": domains[index % len(domains)]},
    )


@pytest.mark.asyncio
async def test_contract_results_treat_smart_ru_assignment_as_xhttp_and_uses_unique_plan_targets(
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")
    monkeypatch.setattr(settings, "remnawave_smart_ru_internal_squad_uuid", str(uuid4()))
    monkeypatch.setattr(settings, "remnawave_smart_ru_external_squad_uuid", str(uuid4()))
    monkeypatch.setattr(settings, "remnawave_smart_ru_subscription_template_name", "CyberVPN Premium Smart RU")
    monkeypatch.setattr(settings, "vpn_tester_synthetic_users_enabled", False)

    service = VpnTesterService(SimpleNamespace())
    service._remnawave_nodes_result = AsyncMock(
        return_value={
            "check_key": "remnawave.nodes.contract",
            "check_name": "Remnawave node contract snapshot",
            "category": "remnawave",
            "status": "pass",
            "severity": "warning",
            "target": "global",
            "safe_summary": "Remnawave nodes snapshot loaded",
            "details": {},
            "duration_ms": 0,
        }
    )
    suite_spec = {
        "suite_key": "premium_smart_ru_v1",
        "version": "v1",
        "checks": [{"key": "premium_smart_ru.connection_modes"}],
        "target_plan_codes": ["premium_smart_ru"],
        "required_connection_modes": ["xhttp"],
        "required_route_registry": "premium_smart_ru_v2",
        "mihomo_template": HARDENED_TEMPLATE.read_text(encoding="utf-8"),
    }

    results = await service._contract_results(
        suite_spec,
        [_smart_ru_plan("premium_smart_ru_30"), _smart_ru_plan("premium_smart_ru_lifetime")],
        [_route_entry(index) for index in range(40)],
    )
    connection_checks = [item for item in results if item["check_key"] == "premium_smart_ru.connection_modes"]
    generated_group_checks = [item for item in results if item["check_key"] == "generated_subscription.mihomo_groups"]

    assert [item["target"] for item in connection_checks] == [
        "premium_smart_ru_30",
        "premium_smart_ru_lifetime",
    ]
    assert {item["status"] for item in connection_checks} == {"pass"}
    assert all("xhttp" in item["details"]["effective_modes"] for item in connection_checks)
    assert all(item["details"]["xhttp_satisfied_by_remnawave_assignment"] for item in connection_checks)
    assert [item["target"] for item in generated_group_checks] == [
        "premium_smart_ru_30",
        "premium_smart_ru_lifetime",
    ]
    assert {item["status"] for item in generated_group_checks} == {"pass"}
