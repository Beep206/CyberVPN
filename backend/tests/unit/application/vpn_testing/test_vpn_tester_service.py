from __future__ import annotations

import base64
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.vpn_testing import service as service_module
from src.application.vpn_testing.service import (
    VpnTesterService,
    _sanitize_run_request_context,
)
from src.application.vpn_testing.suite_loader import load_default_route_registries, load_default_suites
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


def _spb_de_exceptions_plan() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        name="premium_spb_de_exceptions",
        plan_code="premium_spb_de_exceptions",
        display_name="Premium SPB + DE Exceptions",
        catalog_access_class="private_code_gated",
        catalog_visibility="hidden",
        duration_days=30,
        traffic_limit_bytes=None,
        traffic_policy={},
        connection_modes=["standard", "stealth", "server_side_de_exceptions"],
        server_pool=["premium_spb_de_exceptions"],
        device_limit=5,
    )


def _spb_de_exceptions_suite_and_routes() -> tuple[dict[str, object], list[SimpleNamespace]]:
    suite = next(item for item in load_default_suites() if item["suite_key"] == "premium_spb_de_exceptions_v1")
    registry = next(
        item for item in load_default_route_registries() if item["registry_key"] == "premium_spb_de_exceptions_v1"
    )
    routes = [
        SimpleNamespace(
            route_key=route["route_key"],
            country_code=route["country_code"],
            node_tags=route["node_tags"],
            expected_modes=route["expected_modes"],
            metadata_json=route["metadata"],
        )
        for route in registry["routes"]
    ]
    return suite, routes


def _route_entry(index: int) -> SimpleNamespace:
    domains = ["gosuslugi.ru", "nalog.gov.ru", "sberbank.ru", "telegram.org"]
    return SimpleNamespace(
        route_key=f"route-{index}",
        country_code="RU",
        node_tags=["premium_smart_ru"],
        expected_modes=["xhttp"],
        metadata_json={"domain": domains[index % len(domains)]},
    )


def _generated_mihomo_yaml() -> str:
    groups = [
        "🌍 World / EU",
        "🇩🇪 DE Auto",
        "🇳🇱 NL Auto",
        "⚡ RU Auto",
        "🇷🇺 RU Sites",
        "🇷🇺 Moscow Auto",
        "🇷🇺 SPB Auto",
        "🧲 Torrents",
    ]
    group_yaml = "\n".join(f"  - name: {name!r}\n    type: select\n    proxies: ['smart-node']" for name in groups)
    proxies: list[str] = []
    for index, endpoint in enumerate(
        (
            ("de-relay.cyber-vpn.org", 2053, 2083),
            ("nl-4.cyber-vpn.org", 443, 8443),
            ("msk-relay.cyber-vpn.org", 2053, 2083),
            ("ru-spb-3.cyber-vpn.org", 443, 8443),
        ),
        start=1,
    ):
        server, raw_port, xhttp_port = endpoint
        common = f"""  - name: smart-node-{index}
    type: vless
    server: {server}
    tls: true
    servername: reality-target.example
    reality-opts:
      public-key: public-key-{index}
      short-id: short-id-{index}"""
        proxies.append(
            f"""{common}
    port: {raw_port}
    network: tcp
    flow: xtls-rprx-vision"""
        )
        proxies.append(
            f"""{common}
    port: {xhttp_port}
    network: xhttp"""
        )
    proxy_yaml = "\n".join(proxies)
    return f"""
proxies:
{proxy_yaml}
proxy-groups:
{group_yaml}
rules:
  - MATCH,🌍 World / EU
"""


def _passing_transport_results() -> list[dict[str, object]]:
    return [
        {
            "check_key": key,
            "check_name": key,
            "category": "remnawave",
            "status": "pass",
            "severity": "error",
            "target": "global",
            "safe_summary": "verified",
            "details": {"secrets_redacted": True},
            "duration_ms": 0,
        }
        for key in (
            "remnawave.inbounds.vless_reality_raw_tcp",
            "remnawave.inbounds.vless_reality_xhttp",
            "remnawave.hosts.transport_matrix",
            "remnawave.config_profiles.de_smart_ru_server_routing",
            "remnawave.config_profiles.moscow_smart_global_routing",
            "remnawave.external_squads.premium_smart_ru_headers",
        )
    ]


def _passing_release_gate_results() -> list[SimpleNamespace]:
    keys = [
        "generated_subscription.vless_reality_raw_tcp",
        "generated_subscription.xhttp_transport",
        "remnawave.inbounds.vless_reality_raw_tcp",
        "remnawave.inbounds.vless_reality_xhttp",
        "remnawave.hosts.transport_matrix",
        "remnawave.config_profiles.de_smart_ru_server_routing",
        "remnawave.config_profiles.moscow_smart_global_routing",
        "remnawave.external_squads.premium_smart_ru_headers",
        "runtime.transport_profile_matrix.required",
        *[f"runtime.transport.raw.{location}" for location in ("de", "nl", "moscow", "spb")],
        *[f"runtime.transport.xhttp.{location}" for location in ("de", "nl", "moscow", "spb")],
    ]
    return [
        SimpleNamespace(
            check_key=key,
            status="pass",
            details={
                "server_matrix_valid": True,
                "raw_server_matrix_valid": True,
                "xhttp_server_matrix_valid": True,
            }
            if "runtime.transport_profile_matrix.required" in key
            else {},
        )
        for key in keys
    ]


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
            "details": {"node_count": 4, "xhttp_node_count": 4, "ru_node_count": 2},
            "duration_ms": 0,
        }
    )
    service._remnawave_transport_results = AsyncMock(return_value=_passing_transport_results())
    suite_spec = {
        "suite_key": "premium_smart_ru_v1",
        "version": "v1",
        "checks": [{"key": "premium_smart_ru.connection_modes"}],
        "target_plan_codes": ["premium_smart_ru"],
        "required_connection_modes": ["raw", "xhttp"],
        "required_route_registry": "premium_smart_ru_v2",
        "mihomo_template": HARDENED_TEMPLATE.read_text(encoding="utf-8"),
    }

    results = await service._contract_results(
        suite_spec,
        [_smart_ru_plan("premium_smart_ru_30"), _smart_ru_plan("premium_smart_ru_lifetime")],
        [_route_entry(index) for index in range(40)],
        request_context={"generated_mihomo_yaml": _generated_mihomo_yaml()},
    )
    connection_checks = [item for item in results if item["check_key"] == "premium_smart_ru.connection_modes"]
    generated_group_checks = [item for item in results if item["check_key"] == "generated_subscription.mihomo_groups"]
    generated_xhttp_checks = [item for item in results if item["check_key"] == "generated_subscription.xhttp_transport"]
    generated_raw_checks = [
        item for item in results if item["check_key"] == "generated_subscription.vless_reality_raw_tcp"
    ]

    assert [item["target"] for item in connection_checks] == [
        "premium_smart_ru_30",
        "premium_smart_ru_lifetime",
    ]
    assert {item["status"] for item in connection_checks} == {"pass"}
    assert all("xhttp" in item["details"]["effective_modes"] for item in connection_checks)
    assert all("raw" in item["details"]["effective_modes"] for item in connection_checks)
    assert all(item["details"]["xhttp_satisfied_by_remnawave_assignment"] for item in connection_checks)
    assert all(item["details"]["xhttp_satisfied_by_generated_subscription"] for item in connection_checks)
    assert all(item["details"]["raw_satisfied_by_generated_subscription"] for item in connection_checks)
    assert [item["target"] for item in generated_group_checks] == [
        "premium_smart_ru_30",
        "premium_smart_ru_lifetime",
    ]
    assert {item["status"] for item in generated_group_checks} == {"pass"}
    assert {item["status"] for item in generated_xhttp_checks} == {"pass"}
    assert {item["status"] for item in generated_raw_checks} == {"pass"}


@pytest.mark.asyncio
async def test_contract_results_do_not_infer_xhttp_without_generated_or_node_evidence(monkeypatch) -> None:
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
            "details": {"node_count": 4, "xhttp_node_count": 0, "ru_node_count": 2},
            "duration_ms": 0,
        }
    )
    service._remnawave_transport_results = AsyncMock(return_value=_passing_transport_results())
    suite_spec = {
        "suite_key": "premium_smart_ru_v1",
        "version": "v1",
        "checks": [{"key": "premium_smart_ru.connection_modes"}],
        "target_plan_codes": ["premium_smart_ru"],
        "required_connection_modes": ["raw", "xhttp"],
        "required_route_registry": "premium_smart_ru_v2",
        "mihomo_template": HARDENED_TEMPLATE.read_text(encoding="utf-8"),
    }

    results = await service._contract_results(
        suite_spec,
        [_smart_ru_plan("premium_smart_ru_30")],
        [_route_entry(index) for index in range(40)],
        request_context={},
    )
    by_key = {item["check_key"]: item for item in results}

    assert by_key["premium_smart_ru.connection_modes"]["status"] == "fail"
    assert "xhttp" not in by_key["premium_smart_ru.connection_modes"]["details"]["effective_modes"]
    assert "raw" not in by_key["premium_smart_ru.connection_modes"]["details"]["effective_modes"]
    assert by_key["generated_subscription.mihomo_groups"]["status"] == "fail"
    assert by_key["generated_subscription.xhttp_transport"]["status"] == "fail"
    assert by_key["generated_subscription.vless_reality_raw_tcp"]["status"] == "fail"


@pytest.mark.asyncio
async def test_task2_contract_uses_spb_de_semantics_without_smart_ru_false_passes(monkeypatch) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    suite, routes = _spb_de_exceptions_suite_and_routes()
    service = VpnTesterService(SimpleNamespace())

    results = await service._contract_results(suite, [_spb_de_exceptions_plan()], routes)

    by_key = {item["check_key"]: item for item in results}
    assert by_key["suite.dsl.valid"]["status"] == "pass"
    assert by_key["premium_spb_de_exceptions.plan.exists"]["status"] == "pass"
    assert by_key["premium_spb_de_exceptions.connection_modes"]["status"] == "pass"
    assert by_key["premium_spb_de_exceptions.exception_categories_de"]["status"] == "pass"
    assert by_key["premium_spb_de_exceptions.default_spb_direct"]["status"] == "pass"
    bridge_down = by_key["premium_spb_de_exceptions.bridge_down_fail_closed"]
    assert bridge_down["status"] == "degraded"
    assert bridge_down["details"] == {
        "metadata_contract_only": True,
        "runtime_evidence_claimed": False,
    }
    assert by_key["premium_spb_de_exceptions.route_registry"]["status"] == "pass"
    assert by_key["premium_spb_de_exceptions.readiness_gate"]["status"] == "pass"
    assert by_key["premium_spb_de_exceptions.runtime_evidence"]["status"] == "degraded"
    assert not any(item["check_key"].startswith("premium_smart_ru.") for item in results)
    assert not any(item["check_key"].startswith("mihomo.") for item in results)
    assert not any(item["check_key"].startswith("generated_subscription.") for item in results)
    assert not any(item["check_key"].startswith("remnawave.nodes.") for item in results)


@pytest.mark.asyncio
async def test_task2_contract_fails_if_readiness_is_enabled_without_runtime_evidence(monkeypatch) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", True)

    def reject_readiness(_plan_code: str) -> bool:
        raise service_module.VpnProductReadinessError(
            "task2_readiness_attestation_missing",
            "Task2 readiness attestation is missing",
        )

    monkeypatch.setattr(service_module, "ensure_spb_de_exceptions_data_plane_ready", reject_readiness)
    suite, routes = _spb_de_exceptions_suite_and_routes()
    service = VpnTesterService(SimpleNamespace())

    results = await service._contract_results(suite, [_spb_de_exceptions_plan()], routes)

    by_key = {item["check_key"]: item for item in results}
    assert by_key["premium_spb_de_exceptions.readiness_gate"]["status"] == "fail"
    assert by_key["premium_spb_de_exceptions.readiness_gate"]["details"]["data_plane_ready"] is False
    assert "attestation" in by_key["premium_spb_de_exceptions.readiness_gate"]["details"]["readiness_reason"]
    assert by_key["premium_spb_de_exceptions.runtime_evidence"]["status"] == "degraded"


@pytest.mark.asyncio
async def test_task2_contract_does_not_promote_runtime_evidence_from_signed_readiness(monkeypatch) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", True)
    monkeypatch.setattr(service_module, "ensure_spb_de_exceptions_data_plane_ready", lambda _plan_code: True)
    suite, routes = _spb_de_exceptions_suite_and_routes()
    service = VpnTesterService(SimpleNamespace())

    results = await service._contract_results(suite, [_spb_de_exceptions_plan()], routes)

    by_key = {item["check_key"]: item for item in results}
    bridge_down = by_key["premium_spb_de_exceptions.bridge_down_fail_closed"]
    assert bridge_down["status"] == "degraded"
    assert bridge_down["details"] == {
        "metadata_contract_only": True,
        "runtime_evidence_claimed": False,
    }
    readiness = by_key["premium_spb_de_exceptions.readiness_gate"]
    assert readiness["status"] == "pass"
    assert readiness["details"]["runtime_evidence_status"] == "not_claimed"
    assert readiness["details"]["data_plane_ready"] is True
    runtime_evidence = by_key["premium_spb_de_exceptions.runtime_evidence"]
    assert runtime_evidence["status"] == "degraded"
    assert runtime_evidence["details"]["runtime_evidence_status"] == "not_claimed"


@pytest.mark.asyncio
async def test_task2_contract_rejects_matched_transport_without_explicit_no_direct_fallback(monkeypatch) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    suite, routes = _spb_de_exceptions_suite_and_routes()
    matched_route = next(route for route in routes if route.route_key == "matched-raw-tcp-de-bridge")
    matched_route.metadata_json.pop("forbidden_outbound_on_bridge_down")
    service = VpnTesterService(SimpleNamespace())

    results = await service._contract_results(suite, [_spb_de_exceptions_plan()], routes)

    by_key = {item["check_key"]: item for item in results}
    assert by_key["premium_spb_de_exceptions.raw_xhttp_matrix"]["status"] == "fail"
    assert by_key["premium_spb_de_exceptions.tcp_udp_matrix"]["status"] == "fail"
    assert by_key["premium_spb_de_exceptions.route_registry"]["status"] == "fail"


@pytest.mark.asyncio
async def test_task2_runtime_does_not_dispatch_to_smart_ru_agent(monkeypatch) -> None:
    runtime_agent = AsyncMock()
    monkeypatch.setattr(service_module, "call_runtime_agent", runtime_agent)
    monkeypatch.setattr(settings, "vpn_tester_runtime_enabled", True)
    monkeypatch.setattr(settings, "vpn_tester_task2_route_evidence_enabled", False)
    service = VpnTesterService(SimpleNamespace())
    run = SimpleNamespace(id=uuid4(), suite_key="premium_spb_de_exceptions_v1", mode="runtime")

    results = await service._runtime_results(run, [])

    assert results[0]["check_key"] == "premium_spb_de_exceptions.runtime.dispatch"
    assert results[0]["status"] == "fail"
    assert results[0]["details"]["runtime_agent_dispatched"] is False
    runtime_agent.assert_not_awaited()


@pytest.mark.asyncio
async def test_task2_runtime_dispatches_only_to_task2_client_when_enabled(monkeypatch) -> None:
    smart_runtime_agent = AsyncMock()
    task2_runtime_agent = AsyncMock(
        return_value={
            "status": "partial",
            "reason": "bridge_down_evidence_not_claimed",
            "checks": [
                {
                    "check_key": "premium_spb_de_exceptions.selected_outbound.matrix",
                    "check_name": "Task2 selected-outbound matrix",
                    "status": "degraded",
                    "severity": "warning",
                    "target": "spb-xray",
                    "safe_summary": "All declared Task2 selected-outbound events matched",
                    "details": {"bridge_down_evidence_claimed": False},
                }
            ],
        }
    )
    monkeypatch.setattr(service_module, "call_runtime_agent", smart_runtime_agent)
    monkeypatch.setattr(service_module, "call_task2_runtime_agent", task2_runtime_agent)
    monkeypatch.setattr(service_module, "task2_runtime_agent_configured", lambda: True)
    monkeypatch.setattr(settings, "vpn_tester_runtime_enabled", True)
    monkeypatch.setattr(settings, "vpn_tester_task2_route_evidence_enabled", True)
    monkeypatch.setattr(settings, "vpn_tester_synthetic_users_enabled", True)
    monkeypatch.setattr(settings, "vpn_tester_task2_synthetic_user", "task2-route-probe")
    monkeypatch.setattr(settings, "vpn_tester_task2_synthetic_xray_email", "94")
    remnawave_client = SimpleNamespace(
        get=AsyncMock(
            return_value={
                "id": 94,
                "username": "task2-route-probe",
                "vlessUuid": "00000000-0000-4000-8000-000000000094",
            }
        )
    )
    service = VpnTesterService(
        SimpleNamespace(),
        remnawave_client=remnawave_client,
        redis_client=SimpleNamespace(),
    )
    run = SimpleNamespace(id=uuid4(), suite_key="premium_spb_de_exceptions_v1", mode="runtime")

    results = await service._runtime_results(run, [], generated_mihomo_artifact={"proxies": []})

    assert results[0]["check_key"] == "premium_spb_de_exceptions.selected_outbound.matrix"
    assert results[0]["status"] == "degraded"
    assert results[-1]["check_key"] == "premium_spb_de_exceptions.runtime.completeness"
    assert results[-1]["status"] == "degraded"
    task2_runtime_agent.assert_awaited_once()
    assert task2_runtime_agent.await_args.kwargs["synthetic_vless_uuid"] == ("00000000-0000-4000-8000-000000000094")
    remnawave_client.get.assert_awaited_once_with("/users/by-username/task2-route-probe")
    smart_runtime_agent.assert_not_awaited()


@pytest.mark.asyncio
async def test_task2_runtime_fails_closed_when_synthetic_xray_identity_mismatches(monkeypatch) -> None:
    task2_runtime_agent = AsyncMock()
    monkeypatch.setattr(service_module, "call_task2_runtime_agent", task2_runtime_agent)
    monkeypatch.setattr(service_module, "task2_runtime_agent_configured", lambda: True)
    monkeypatch.setattr(settings, "vpn_tester_runtime_enabled", True)
    monkeypatch.setattr(settings, "vpn_tester_task2_route_evidence_enabled", True)
    monkeypatch.setattr(settings, "vpn_tester_synthetic_users_enabled", True)
    monkeypatch.setattr(settings, "vpn_tester_task2_synthetic_user", "task2-route-probe")
    monkeypatch.setattr(settings, "vpn_tester_task2_synthetic_xray_email", "94")
    remnawave_client = SimpleNamespace(
        get=AsyncMock(
            return_value={
                "id": 93,
                "username": "task2-route-probe",
                "vlessUuid": "00000000-0000-4000-8000-000000000094",
            }
        )
    )
    service = VpnTesterService(
        SimpleNamespace(),
        remnawave_client=remnawave_client,
        redis_client=SimpleNamespace(),
    )
    run = SimpleNamespace(id=uuid4(), suite_key="premium_spb_de_exceptions_v1", mode="runtime")

    results = await service._runtime_results(run, [], generated_mihomo_artifact={"proxies": []})

    assert results[0]["check_key"] == "premium_spb_de_exceptions.runtime.synthetic_identity"
    assert results[0]["status"] == "fail"
    task2_runtime_agent.assert_not_awaited()


@pytest.mark.asyncio
async def test_task2_runtime_fails_closed_when_synthetic_identity_lookup_fails(monkeypatch) -> None:
    task2_runtime_agent = AsyncMock()
    monkeypatch.setattr(service_module, "call_task2_runtime_agent", task2_runtime_agent)
    monkeypatch.setattr(service_module, "task2_runtime_agent_configured", lambda: True)
    monkeypatch.setattr(settings, "vpn_tester_runtime_enabled", True)
    monkeypatch.setattr(settings, "vpn_tester_task2_route_evidence_enabled", True)
    monkeypatch.setattr(settings, "vpn_tester_synthetic_users_enabled", True)
    monkeypatch.setattr(settings, "vpn_tester_task2_synthetic_user", "task2-route-probe")
    monkeypatch.setattr(settings, "vpn_tester_task2_synthetic_xray_email", "94")
    remnawave_client = SimpleNamespace(get=AsyncMock(side_effect=service_module.HTTPError("provider unavailable")))
    service = VpnTesterService(
        SimpleNamespace(),
        remnawave_client=remnawave_client,
        redis_client=SimpleNamespace(),
    )
    run = SimpleNamespace(id=uuid4(), suite_key="premium_spb_de_exceptions_v1", mode="runtime")

    results = await service._runtime_results(run, [], generated_mihomo_artifact={"proxies": []})

    assert results[0]["check_key"] == "premium_spb_de_exceptions.runtime.synthetic_identity"
    assert results[0]["status"] == "fail"
    assert results[0]["details"] == {
        "error_type": "HTTPError",
        "runtime_agent_dispatched": False,
        "runtime_evidence_status": "not_claimed",
    }
    assert "provider unavailable" not in str(results[0])
    task2_runtime_agent.assert_not_awaited()


@pytest.mark.asyncio
async def test_generated_mihomo_artifact_does_not_fall_back_to_existing_remnawave_user() -> None:
    repository = SimpleNamespace(list_subscription_delivery_candidates=AsyncMock())
    service = VpnTesterService(repository, remnawave_client=SimpleNamespace())

    artifact = await service._generated_mihomo_artifact({})

    assert artifact is None
    repository.list_subscription_delivery_candidates.assert_not_awaited()


def test_persisted_run_context_drops_generated_vpn_material() -> None:
    raw_yaml = _generated_mihomo_yaml()
    context = {
        "source": "task_worker",
        "trigger": "fresh-canary",
        "generated_mihomo_yaml": raw_yaml,
        "subscription_url": "https://cyber-vpn.org/api/sub/sensitive-value",
        "requested_context": {"public-key": "sensitive", "short-id": "sensitive"},
    }

    persisted = _sanitize_run_request_context(context)

    assert persisted == {
        "source": "task_worker",
        "trigger": "fresh-canary",
        "generated_mihomo_artifact_supplied": True,
    }
    assert raw_yaml not in str(persisted)


@pytest.mark.asyncio
async def test_create_scheduled_run_persists_only_sanitized_context() -> None:
    created = SimpleNamespace(id=uuid4())
    repository = SimpleNamespace(
        get_suite=AsyncMock(
            return_value=SimpleNamespace(
                suite_key="premium_smart_ru_v1",
                version="v1",
                mode="runtime",
                spec={"required_route_registry": "premium_smart_ru_v2"},
            )
        ),
        create_run=AsyncMock(return_value=created),
    )
    service = VpnTesterService(repository)
    service.ensure_seeded = AsyncMock()

    result = await service.create_scheduled_run(
        suite_key="premium_smart_ru_v1",
        mode="runtime",
        trigger="fresh-canary",
        request_context={"generated_mihomo_yaml": _generated_mihomo_yaml(), "subscription_url": "sensitive"},
    )

    assert result is created
    persisted = repository.create_run.await_args.kwargs["request_context"]
    assert persisted == {
        "source": "task_worker",
        "trigger": "fresh-canary",
        "generated_mihomo_artifact_supplied": True,
    }


DE_SMART_PROFILE_UUID = "00000000-0000-4000-8000-000000000007"
MOSCOW_SMART_PROFILE_UUID = "00000000-0000-4000-8000-000000000008"


def _base64_json(payload: dict[str, object]) -> str:
    return base64.b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("ascii")


def _external_routing_payload(*, block_sites: list[str] | None = None) -> dict[str, object]:
    return {
        "Name": "CyberVPN Premium Smart RU",
        "GlobalProxy": "true",
        "RemoteDNSType": "DoH",
        "RemoteDNSDomain": "https://cloudflare-dns.com/dns-query",
        "RemoteDNSIP": "1.1.1.1",
        "BlockSites": block_sites
        if block_sites is not None
        else list(service_module.PREMIUM_SMART_RU_EXTERNAL_ROUTING_BLOCK_SITES),
        "BlockIp": [],
        "DomainStrategy": "AsIs",
        "FakeDNS": "false",
    }


def _external_squad_headers(*, routing: str | None = None) -> dict[str, str]:
    headers = {
        "routing": routing if routing is not None else _base64_json(_external_routing_payload()),
        "x-cybervpn-plan": "premium_smart_ru",
        "x-cybervpn-routing": "de-primary-ru-smart",
        "x-cybervpn-unlimited": "true",
    }
    return headers


def _de_smart_config_profile_config() -> dict[str, object]:
    inbound_tags = list(service_module.PREMIUM_SMART_RU_DE_CUSTOMER_INBOUND_TAGS)
    direct_domains = sorted(service_module.PREMIUM_SMART_RU_REQUIRED_DIRECT_DOMAINS)
    ru_domains = sorted(
        item for item in service_module.PREMIUM_SMART_RU_REQUIRED_RU_DOMAINS if item != "geosite:category-ru"
    ) + ["geosite:category-ru"]
    return {
        "inbounds": [
            {"tag": "DE_SMART_REALITY_443", "protocol": "vless"},
            {"tag": "DE_SMART_XHTTP_REALITY_8443", "protocol": "vless"},
            {"tag": "DE_SMART_GLOBAL_BRIDGE_9443", "protocol": "shadowsocks"},
        ],
        "outbounds": [
            {"tag": "DIRECT", "protocol": "freedom"},
            {"tag": "BLOCK", "protocol": "blackhole"},
            {
                "tag": "RU_MSK_BRIDGE",
                "protocol": "shadowsocks",
                "settings": {
                    "servers": [
                        {
                            "address": "sensitive-bridge-endpoint.example",
                            "port": 9443,
                            "password": "sensitive-bridge-password",
                            "method": "chacha20-ietf-poly1305",
                            "level": 0,
                        }
                    ]
                },
            },
        ],
        "routing": {
            "domainStrategy": "IPIfNonMatch",
            "rules": [
                {"ip": ["geoip:private"], "outboundTag": "BLOCK"},
                {"domain": ["geosite:private"], "outboundTag": "BLOCK"},
                {"protocol": ["bittorrent"], "outboundTag": "BLOCK"},
                {"network": "udp", "port": "443", "outboundTag": "BLOCK"},
                {
                    "domain": list(service_module.PREMIUM_SMART_RU_TORRENT_BLOCK_DOMAINS),
                    "inboundTag": inbound_tags,
                    "outboundTag": "BLOCK",
                },
                {
                    "domain": direct_domains,
                    "inboundTag": inbound_tags,
                    "outboundTag": "DIRECT",
                },
                {
                    "domain": ["geosite:category-ads-all"],
                    "inboundTag": inbound_tags,
                    "outboundTag": "BLOCK",
                },
                {
                    "domain": list(service_module.PREMIUM_SMART_RU_TOR_BLOCK_DOMAINS),
                    "inboundTag": inbound_tags,
                    "outboundTag": "BLOCK",
                },
                {
                    "domain": ru_domains,
                    "inboundTag": inbound_tags,
                    "outboundTag": "RU_MSK_BRIDGE",
                },
                {"ip": ["geoip:ru"], "inboundTag": inbound_tags, "outboundTag": "RU_MSK_BRIDGE"},
                {"inboundTag": inbound_tags, "outboundTag": "DIRECT"},
            ],
        },
    }


def _moscow_smart_global_config_profile_config() -> dict[str, object]:
    inbound_tags = list(service_module.PREMIUM_SMART_RU_MOSCOW_CUSTOMER_INBOUND_TAGS)
    ru_domains = sorted(
        item for item in service_module.PREMIUM_SMART_RU_REQUIRED_RU_DOMAINS if item != "geosite:category-ru"
    ) + ["geosite:category-ru"]

    def scoped(rule: dict[str, object]) -> dict[str, object]:
        return {**rule, "inboundTag": inbound_tags}

    return {
        "inbounds": [
            {"tag": "MSK_SMART_REALITY_443", "protocol": "vless"},
            {"tag": "MSK_SMART_XHTTP_REALITY_8443", "protocol": "vless"},
            {"tag": "MSK_SMART_RU_BRIDGE_V2_9443", "protocol": "shadowsocks"},
        ],
        "outbounds": [
            {"tag": "DIRECT", "protocol": "freedom"},
            {"tag": "BLOCK", "protocol": "blackhole"},
            {
                "tag": "DE_GLOBAL_BRIDGE",
                "protocol": "shadowsocks",
                "settings": {
                    "servers": [
                        {
                            "address": "sensitive-global-bridge-endpoint.example",
                            "port": 9443,
                            "password": "sensitive-global-bridge-password",
                            "method": "chacha20-ietf-poly1305",
                            "level": 0,
                        }
                    ]
                },
            },
        ],
        "routing": {
            "domainStrategy": "IPIfNonMatch",
            "rules": [
                scoped({"ip": ["geoip:private"], "outboundTag": "BLOCK"}),
                scoped({"domain": ["geosite:private"], "outboundTag": "BLOCK"}),
                scoped({"protocol": ["bittorrent"], "outboundTag": "BLOCK"}),
                scoped({"network": "udp", "port": "443", "outboundTag": "BLOCK"}),
                scoped(
                    {
                        "domain": list(service_module.PREMIUM_SMART_RU_TORRENT_BLOCK_DOMAINS),
                        "outboundTag": "BLOCK",
                    }
                ),
                scoped({"domain": ["geosite:category-ads-all"], "outboundTag": "BLOCK"}),
                scoped(
                    {
                        "domain": list(service_module.PREMIUM_SMART_RU_TOR_BLOCK_DOMAINS),
                        "outboundTag": "BLOCK",
                    }
                ),
                scoped({"domain": ru_domains, "outboundTag": "DIRECT"}),
                scoped({"ip": ["geoip:ru"], "outboundTag": "DIRECT"}),
                scoped({"outboundTag": "DE_GLOBAL_BRIDGE"}),
            ],
        },
    }


def _de_profile_detail(payloads: dict[str, object]) -> dict[str, object]:
    return payloads[f"/config-profiles/{DE_SMART_PROFILE_UUID}"]


def _de_profile_rules(payloads: dict[str, object]) -> list[dict[str, object]]:
    detail = _de_profile_detail(payloads)
    return detail["config"]["routing"]["rules"]


def _moscow_profile_detail(payloads: dict[str, object]) -> dict[str, object]:
    return payloads[f"/config-profiles/{MOSCOW_SMART_PROFILE_UUID}"]


def _moscow_profile_rules(payloads: dict[str, object]) -> list[dict[str, object]]:
    detail = _moscow_profile_detail(payloads)
    return detail["config"]["routing"]["rules"]


def _external_squad(payloads: dict[str, object]) -> dict[str, object]:
    return payloads["/external-squads"]["externalSquads"][0]


def _remnawave_transport_payloads() -> dict[str, object]:
    raw_reality = {
        "serverNames": ["reality-target.example"],
        "shortIds": ["sensitive-short-id"],
        "privateKey": "sensitive-private-key",
        "target": "reality-target.example:443",
    }
    raw_inbound = {
        "uuid": "00000000-0000-4000-8000-000000000001",
        "tag": "VLESS_REALITY_443",
        "type": "vless",
        "network": "raw",
        "security": "reality",
        "port": 443,
        "rawInbound": {
            "protocol": "vless",
            "port": 443,
            "settings": {"decryption": "none", "flow": "xtls-rprx-vision"},
            "streamSettings": {"network": "raw", "security": "reality", "realitySettings": raw_reality},
            "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"]},
        },
    }
    xhttp_inbound = {
        "uuid": "00000000-0000-4000-8000-000000000002",
        "tag": "VLESS_XHTTP_REALITY_8443",
        "type": "vless",
        "network": "xhttp",
        "security": "reality",
        "port": 8443,
        "rawInbound": {
            "protocol": "vless",
            "port": 8443,
            "settings": {"decryption": "none"},
            "streamSettings": {
                "network": "xhttp",
                "security": "reality",
                "realitySettings": raw_reality,
            },
        },
    }
    de_raw_inbound = deepcopy(raw_inbound)
    de_raw_inbound.update(
        uuid="00000000-0000-4000-8000-000000000003",
        tag="DE_SMART_REALITY_443",
    )
    de_xhttp_inbound = deepcopy(xhttp_inbound)
    de_xhttp_inbound.update(
        uuid="00000000-0000-4000-8000-000000000004",
        tag="DE_SMART_XHTTP_REALITY_8443",
    )
    moscow_raw_inbound = deepcopy(raw_inbound)
    moscow_raw_inbound.update(
        uuid="00000000-0000-4000-8000-000000000005",
        tag="MSK_SMART_REALITY_443",
    )
    moscow_xhttp_inbound = deepcopy(xhttp_inbound)
    moscow_xhttp_inbound.update(
        uuid="00000000-0000-4000-8000-000000000006",
        tag="MSK_SMART_XHTTP_REALITY_8443",
    )
    node_endpoints = {
        "de-relay.cyber-vpn.org": (
            "🇩🇪 DE Frankfurt 01 25G",
            (2053, "DE_SMART_REALITY_443"),
            (2083, "DE_SMART_XHTTP_REALITY_8443"),
        ),
        "nl-4.cyber-vpn.org": (
            "🇳🇱 NL Amsterdam 01 10G",
            (443, "VLESS_REALITY_443"),
            (8443, "VLESS_XHTTP_REALITY_8443"),
        ),
        "msk-relay.cyber-vpn.org": (
            "🇷🇺 RU Moscow 01 25G",
            (2053, "MSK_SMART_REALITY_443"),
            (2083, "MSK_SMART_XHTTP_REALITY_8443"),
        ),
        "ru-spb-3.cyber-vpn.org": (
            "🇷🇺 RU SPB 01 25G",
            (443, "VLESS_REALITY_443"),
            (8443, "VLESS_XHTTP_REALITY_8443"),
        ),
    }
    node_rows = []
    hosts = []
    for node_index, (address, endpoint) in enumerate(node_endpoints.items(), start=10):
        node_name, raw_endpoint, xhttp_endpoint = endpoint
        node_uuid = f"00000000-0000-4000-8000-{node_index:012x}"
        node_rows.append({"uuid": node_uuid, "name": node_name, "isConnected": True, "isDisabled": False})
        for port, tag in (raw_endpoint, xhttp_endpoint):
            hosts.append(
                {
                    "address": address,
                    "port": port,
                    "isDisabled": False,
                    "excludeFromSubscriptionTypes": [],
                    "inbound": {"tag": tag},
                    "nodes": [{"uuid": node_uuid, "name": node_name}],
                }
            )
    return {
        "/config-profiles/inbounds": {
            "inbounds": [
                raw_inbound,
                xhttp_inbound,
                de_raw_inbound,
                de_xhttp_inbound,
                moscow_raw_inbound,
                moscow_xhttp_inbound,
                {
                    "uuid": "00000000-0000-4000-8000-000000000009",
                    "tag": "DE_SMART_GLOBAL_BRIDGE_9443",
                    "type": "shadowsocks",
                    "network": "tcp,udp",
                    "port": 9443,
                },
                {
                    "uuid": "00000000-0000-4000-8000-000000000010",
                    "tag": "MSK_SMART_RU_BRIDGE_V2_9443",
                    "type": "shadowsocks",
                    "network": "tcp,udp",
                    "port": 9443,
                },
            ]
        },
        "/config-profiles": {
            "configProfiles": [
                {
                    "uuid": DE_SMART_PROFILE_UUID,
                    "name": "S1 DE Smart RU Server",
                },
                {
                    "uuid": MOSCOW_SMART_PROFILE_UUID,
                    "name": "S1 Moscow Smart Global Server",
                },
            ]
        },
        f"/config-profiles/{DE_SMART_PROFILE_UUID}": {
            "uuid": DE_SMART_PROFILE_UUID,
            "name": "S1 DE Smart RU Server",
            "config": _de_smart_config_profile_config(),
        },
        f"/config-profiles/{MOSCOW_SMART_PROFILE_UUID}": {
            "uuid": MOSCOW_SMART_PROFILE_UUID,
            "name": "S1 Moscow Smart Global Server",
            "config": _moscow_smart_global_config_profile_config(),
        },
        "/hosts": hosts,
        "/nodes": {"nodes": node_rows},
        "/internal-squads": {
            "internalSquads": [
                {
                    "name": "CYBERVPN_PREMIUM_SMART_RU_NODES",
                    "inbounds": [
                        {"tag": "VLESS_REALITY_443"},
                        {"tag": "VLESS_XHTTP_REALITY_8443"},
                        {"tag": "DE_SMART_REALITY_443"},
                        {"tag": "DE_SMART_XHTTP_REALITY_8443"},
                        {"tag": "MSK_SMART_REALITY_443"},
                        {"tag": "MSK_SMART_XHTTP_REALITY_8443"},
                    ],
                }
            ]
        },
        "/external-squads": {
            "externalSquads": [
                {
                    "uuid": "00000000-0000-4000-8000-000000000011",
                    "name": "CYBERVPN_PREMIUM_SMART_RU",
                    "responseHeaders": _external_squad_headers(),
                }
            ]
        },
    }


@pytest.mark.asyncio
async def test_remnawave_transport_results_require_exact_safe_matrix() -> None:
    payloads = _remnawave_transport_payloads()
    remnawave_client = SimpleNamespace(get=AsyncMock(side_effect=lambda path: payloads[path]))
    service = VpnTesterService(SimpleNamespace(), remnawave_client=remnawave_client)

    results = await service._remnawave_transport_results()
    by_key = {item["check_key"]: item for item in results}

    assert {item["status"] for item in results} == {"pass"}
    assert results[2]["details"] == {
        "raw_host_count": 4,
        "xhttp_host_count": 4,
        "candidate_host_count": 8,
        "missing_link_count": 0,
        "unexpected_link_count": 0,
        "duplicate_link_count": 0,
        "disabled_host_count": 0,
        "excluded_required_format_count": 0,
        "inbound_reference_resolved_count": 0,
        "expanded_node_link_count": 8,
        "unresolved_node_reference_count": 0,
        "secrets_redacted": True,
    }
    assert by_key["remnawave.config_profiles.de_smart_ru_server_routing"]["details"] == {
        "profile_found": True,
        "profile_config_present": True,
        "de_inbound_tag_count": 3,
        "de_inbound_tags_exact": True,
        "de_customer_inbound_tags_exact": True,
        "de_global_bridge_inbound_present": True,
        "bridge_outbound_count": 1,
        "bridge_outbound_present": True,
        "bridge_protocol_shadowsocks": True,
        "bridge_server_count": 1,
        "bridge_single_server": True,
        "bridge_address_present": True,
        "bridge_method_valid": True,
        "bridge_port_valid": True,
        "bridge_password_present": True,
        "routing": {
            "domain_strategy_ip_if_non_match": True,
            "rule_count": 11,
            "rule_count_exact": True,
            "outbound_order_valid": True,
            "bridge_inbound_excluded_from_customer_rules": True,
            "private_ip_block_rule_valid": True,
            "private_domain_block_rule_valid": True,
            "bittorrent_block_rule_valid": True,
            "udp_443_block_rule_valid": True,
            "torrent_domain_block_rule_valid": True,
            "direct_exceptions_rule_valid": True,
            "ads_block_rule_after_direct_valid": True,
            "tor_block_rule_valid": True,
            "ru_domain_bridge_rule_valid": True,
            "ru_geoip_bridge_rule_valid": True,
            "final_direct_rule_valid": True,
        },
        "profile_match_count": 1,
        "detail_fetched": True,
        "secrets_redacted": True,
    }
    assert by_key["remnawave.config_profiles.moscow_smart_global_routing"]["details"] == {
        "profile_found": True,
        "profile_config_present": True,
        "moscow_inbound_tag_count": 3,
        "moscow_inbound_tags_exact": True,
        "moscow_customer_inbound_tags_exact": True,
        "moscow_bridge_inbound_present": True,
        "bridge_outbound_count": 1,
        "bridge_outbound_present": True,
        "bridge_protocol_shadowsocks": True,
        "bridge_server_count": 1,
        "bridge_single_server": True,
        "bridge_address_present": True,
        "bridge_method_valid": True,
        "bridge_port_valid": True,
        "bridge_password_present": True,
        "routing": {
            "domain_strategy_ip_if_non_match": True,
            "rule_count": 10,
            "rule_count_exact": True,
            "outbound_order_valid": True,
            "all_rules_customer_scoped": True,
            "bridge_inbound_excluded_from_customer_rules": True,
            "private_ip_block_rule_valid": True,
            "private_domain_block_rule_valid": True,
            "bittorrent_block_rule_valid": True,
            "udp_443_block_rule_valid": True,
            "torrent_domain_block_rule_valid": True,
            "ads_block_rule_valid": True,
            "tor_block_rule_valid": True,
            "ru_domain_direct_rule_valid": True,
            "ru_geoip_direct_rule_valid": True,
            "final_global_bridge_rule_valid": True,
        },
        "profile_match_count": 1,
        "detail_fetched": True,
        "secrets_redacted": True,
    }
    assert by_key["remnawave.external_squads.premium_smart_ru_headers"]["details"] == {
        "squad_found": True,
        "response_headers_present": True,
        "routing_header_present": True,
        "routing_header_decoded": True,
        "routing_decode_error": None,
        "name_valid": True,
        "global_proxy_enabled": True,
        "dns_type_doh": True,
        "dns_domain_valid": True,
        "dns_ip_valid": True,
        "domain_strategy_valid": True,
        "fake_dns_disabled": True,
        "block_sites_count": 7,
        "block_sites_exact": True,
        "block_ip_empty": True,
        "plan_header_valid": True,
        "routing_header_marker_valid": True,
        "unlimited_header_valid": True,
        "squad_match_count": 1,
        "secrets_redacted": True,
    }
    assert f"/config-profiles/{DE_SMART_PROFILE_UUID}" in [
        call.args[0] for call in remnawave_client.get.await_args_list
    ]
    assert f"/config-profiles/{MOSCOW_SMART_PROFILE_UUID}" in [
        call.args[0] for call in remnawave_client.get.await_args_list
    ]
    safe_output = str(results)
    assert "sensitive-private-key" not in safe_output
    assert "sensitive-short-id" not in safe_output
    assert "reality-target.example" not in safe_output
    assert "sensitive-bridge-password" not in safe_output
    assert "sensitive-bridge-endpoint.example" not in safe_output
    assert "sensitive-global-bridge-password" not in safe_output
    assert "sensitive-global-bridge-endpoint.example" not in safe_output

    raw_inbound = payloads["/config-profiles/inbounds"]["inbounds"][0]
    raw_inbound["rawInbound"]["settings"]["flow"] = ""
    failed = await service._remnawave_transport_results()
    by_key = {item["check_key"]: item for item in failed}

    assert by_key["remnawave.inbounds.vless_reality_raw_tcp"]["status"] == "fail"
    assert by_key["remnawave.inbounds.vless_reality_xhttp"]["status"] == "pass"
    assert by_key["remnawave.hosts.transport_matrix"]["status"] == "pass"


@pytest.mark.asyncio
async def test_remnawave_transport_results_fail_when_de_specific_xhttp_inbound_contract_is_broken() -> None:
    payloads = _remnawave_transport_payloads()
    de_xhttp_inbound = payloads["/config-profiles/inbounds"]["inbounds"][3]
    de_xhttp_inbound["network"] = "raw"
    de_xhttp_inbound["rawInbound"]["streamSettings"]["network"] = "raw"
    remnawave_client = SimpleNamespace(get=AsyncMock(side_effect=lambda path: payloads[path]))

    results = await VpnTesterService(
        SimpleNamespace(), remnawave_client=remnawave_client
    )._remnawave_transport_results()
    by_key = {item["check_key"]: item for item in results}
    xhttp_result = by_key["remnawave.inbounds.vless_reality_xhttp"]

    assert xhttp_result["status"] == "fail"
    assert xhttp_result["details"]["inbound_count"] == 1
    assert xhttp_result["details"]["de_inbound_count"] == 1
    assert xhttp_result["details"]["contract"]["network_xhttp"] is True
    assert xhttp_result["details"]["de_contract"]["network_xhttp"] is False
    assert by_key["remnawave.hosts.transport_matrix"]["status"] == "pass"


@pytest.mark.asyncio
async def test_remnawave_transport_results_fail_when_de_specific_raw_inbound_contract_is_broken() -> None:
    payloads = _remnawave_transport_payloads()
    de_raw_inbound = payloads["/config-profiles/inbounds"]["inbounds"][2]
    de_raw_inbound["rawInbound"]["settings"]["flow"] = ""
    remnawave_client = SimpleNamespace(get=AsyncMock(side_effect=lambda path: payloads[path]))

    results = await VpnTesterService(
        SimpleNamespace(), remnawave_client=remnawave_client
    )._remnawave_transport_results()
    by_key = {item["check_key"]: item for item in results}
    raw_result = by_key["remnawave.inbounds.vless_reality_raw_tcp"]

    assert raw_result["status"] == "fail"
    assert raw_result["details"]["inbound_count"] == 1
    assert raw_result["details"]["de_inbound_count"] == 1
    assert raw_result["details"]["contract"]["flow_vision"] is True
    assert raw_result["details"]["de_contract"]["flow_vision"] is False
    assert by_key["remnawave.hosts.transport_matrix"]["status"] == "pass"


@pytest.mark.asyncio
async def test_remnawave_transport_results_fail_all_transport_checks_without_client() -> None:
    results = await VpnTesterService(SimpleNamespace(), remnawave_client=None)._remnawave_transport_results()

    assert [item["check_key"] for item in results] == [
        "remnawave.inbounds.vless_reality_raw_tcp",
        "remnawave.inbounds.vless_reality_xhttp",
        "remnawave.hosts.transport_matrix",
        "remnawave.config_profiles.de_smart_ru_server_routing",
        "remnawave.config_profiles.moscow_smart_global_routing",
        "remnawave.external_squads.premium_smart_ru_headers",
    ]
    assert {item["status"] for item in results} == {"fail"}
    assert {item["details"]["reason"] for item in results} == {"remnawave_client_not_configured"}
    assert all(item["details"]["secrets_redacted"] is True for item in results)


@pytest.mark.asyncio
async def test_remnawave_transport_results_fail_when_de_profile_inbound_tag_is_missing() -> None:
    payloads = _remnawave_transport_payloads()
    detail = _de_profile_detail(payloads)
    detail["config"]["inbounds"].pop()
    remnawave_client = SimpleNamespace(get=AsyncMock(side_effect=lambda path: payloads[path]))

    results = await VpnTesterService(
        SimpleNamespace(), remnawave_client=remnawave_client
    )._remnawave_transport_results()
    profile_result = {item["check_key"]: item for item in results}[
        "remnawave.config_profiles.de_smart_ru_server_routing"
    ]

    assert profile_result["status"] == "fail"
    assert profile_result["details"]["de_inbound_tag_count"] == 2
    assert profile_result["details"]["de_inbound_tags_exact"] is False


@pytest.mark.asyncio
async def test_remnawave_transport_results_fail_when_de_profile_rule_order_is_broken() -> None:
    payloads = _remnawave_transport_payloads()
    rules = _de_profile_rules(payloads)
    rules[5], rules[6] = rules[6], rules[5]
    remnawave_client = SimpleNamespace(get=AsyncMock(side_effect=lambda path: payloads[path]))

    results = await VpnTesterService(
        SimpleNamespace(), remnawave_client=remnawave_client
    )._remnawave_transport_results()
    by_key = {item["check_key"]: item for item in results}
    profile_result = by_key["remnawave.config_profiles.de_smart_ru_server_routing"]

    assert profile_result["status"] == "fail"
    assert profile_result["details"]["routing"]["rule_count"] == 11
    assert profile_result["details"]["routing"]["outbound_order_valid"] is False
    assert profile_result["details"]["routing"]["direct_exceptions_rule_valid"] is False
    assert by_key["remnawave.external_squads.premium_smart_ru_headers"]["status"] == "pass"


@pytest.mark.asyncio
async def test_remnawave_transport_results_fail_when_de_profile_bridge_outbound_is_missing() -> None:
    payloads = _remnawave_transport_payloads()
    detail = _de_profile_detail(payloads)
    config = detail["config"]
    config["outbounds"] = [item for item in config["outbounds"] if item["tag"] != "RU_MSK_BRIDGE"]
    remnawave_client = SimpleNamespace(get=AsyncMock(side_effect=lambda path: payloads[path]))

    results = await VpnTesterService(
        SimpleNamespace(), remnawave_client=remnawave_client
    )._remnawave_transport_results()
    by_key = {item["check_key"]: item for item in results}
    profile_result = by_key["remnawave.config_profiles.de_smart_ru_server_routing"]

    assert profile_result["status"] == "fail"
    assert profile_result["details"]["bridge_outbound_present"] is False
    assert profile_result["details"]["bridge_protocol_shadowsocks"] is False
    assert "sensitive-bridge-password" not in str(results)
    assert "sensitive-bridge-endpoint.example" not in str(results)


@pytest.mark.asyncio
async def test_remnawave_transport_results_fail_when_de_profile_block_rule_is_missing() -> None:
    payloads = _remnawave_transport_payloads()
    rules = _de_profile_rules(payloads)
    del rules[6]
    remnawave_client = SimpleNamespace(get=AsyncMock(side_effect=lambda path: payloads[path]))

    results = await VpnTesterService(
        SimpleNamespace(), remnawave_client=remnawave_client
    )._remnawave_transport_results()
    by_key = {item["check_key"]: item for item in results}
    profile_result = by_key["remnawave.config_profiles.de_smart_ru_server_routing"]

    assert profile_result["status"] == "fail"
    assert profile_result["details"]["routing"]["rule_count"] == 10
    assert profile_result["details"]["routing"]["rule_count_exact"] is False
    assert profile_result["details"]["routing"]["ads_block_rule_after_direct_valid"] is False


@pytest.mark.asyncio
async def test_remnawave_transport_results_fail_when_moscow_profile_is_missing() -> None:
    payloads = _remnawave_transport_payloads()
    profiles = payloads["/config-profiles"]["configProfiles"]
    payloads["/config-profiles"]["configProfiles"] = [
        profile for profile in profiles if profile["name"] != "S1 Moscow Smart Global Server"
    ]
    remnawave_client = SimpleNamespace(get=AsyncMock(side_effect=lambda path: payloads[path]))

    results = await VpnTesterService(
        SimpleNamespace(), remnawave_client=remnawave_client
    )._remnawave_transport_results()
    by_key = {item["check_key"]: item for item in results}
    profile_result = by_key["remnawave.config_profiles.moscow_smart_global_routing"]

    assert profile_result["status"] == "fail"
    assert profile_result["details"]["profile_found"] is False
    assert profile_result["details"]["profile_match_count"] == 0
    assert by_key["remnawave.config_profiles.de_smart_ru_server_routing"]["status"] == "pass"


@pytest.mark.asyncio
async def test_remnawave_transport_results_fail_closed_when_moscow_profile_detail_fetch_fails() -> None:
    payloads = _remnawave_transport_payloads()

    async def get(path: str) -> object:
        if path == f"/config-profiles/{MOSCOW_SMART_PROFILE_UUID}":
            raise service_module.HTTPError("moscow profile detail unavailable")
        return payloads[path]

    remnawave_client = SimpleNamespace(get=AsyncMock(side_effect=get))

    results = await VpnTesterService(
        SimpleNamespace(), remnawave_client=remnawave_client
    )._remnawave_transport_results()

    assert {item["status"] for item in results} == {"fail"}
    assert {item["details"]["reason"] for item in results} == {"remnawave_config_profile_detail_unavailable"}
    assert all(item["details"]["error_type"] == "HTTPError" for item in results)
    assert all(item["details"]["secrets_redacted"] is True for item in results)


@pytest.mark.asyncio
async def test_remnawave_transport_results_fail_when_moscow_profile_bridge_outbound_is_missing() -> None:
    payloads = _remnawave_transport_payloads()
    detail = _moscow_profile_detail(payloads)
    config = detail["config"]
    config["outbounds"] = [item for item in config["outbounds"] if item["tag"] != "DE_GLOBAL_BRIDGE"]
    remnawave_client = SimpleNamespace(get=AsyncMock(side_effect=lambda path: payloads[path]))

    results = await VpnTesterService(
        SimpleNamespace(), remnawave_client=remnawave_client
    )._remnawave_transport_results()
    by_key = {item["check_key"]: item for item in results}
    profile_result = by_key["remnawave.config_profiles.moscow_smart_global_routing"]

    assert profile_result["status"] == "fail"
    assert profile_result["details"]["bridge_outbound_present"] is False
    assert profile_result["details"]["bridge_protocol_shadowsocks"] is False
    assert "sensitive-global-bridge-password" not in str(results)
    assert "sensitive-global-bridge-endpoint.example" not in str(results)


@pytest.mark.asyncio
async def test_remnawave_transport_results_fail_when_moscow_profile_rule_order_is_broken() -> None:
    payloads = _remnawave_transport_payloads()
    rules = _moscow_profile_rules(payloads)
    rules[4], rules[7] = rules[7], rules[4]
    remnawave_client = SimpleNamespace(get=AsyncMock(side_effect=lambda path: payloads[path]))

    results = await VpnTesterService(
        SimpleNamespace(), remnawave_client=remnawave_client
    )._remnawave_transport_results()
    by_key = {item["check_key"]: item for item in results}
    profile_result = by_key["remnawave.config_profiles.moscow_smart_global_routing"]

    assert profile_result["status"] == "fail"
    assert profile_result["details"]["routing"]["rule_count"] == 10
    assert profile_result["details"]["routing"]["outbound_order_valid"] is False
    assert profile_result["details"]["routing"]["torrent_domain_block_rule_valid"] is False
    assert by_key["remnawave.config_profiles.de_smart_ru_server_routing"]["status"] == "pass"


@pytest.mark.asyncio
async def test_remnawave_transport_results_fail_when_moscow_bridge_inbound_leaks_into_customer_rules() -> None:
    payloads = _remnawave_transport_payloads()
    rule = _moscow_profile_rules(payloads)[0]
    rule["inboundTag"] = [
        "MSK_SMART_REALITY_443",
        "MSK_SMART_XHTTP_REALITY_8443",
        "MSK_SMART_RU_BRIDGE_V2_9443",
    ]
    remnawave_client = SimpleNamespace(get=AsyncMock(side_effect=lambda path: payloads[path]))

    results = await VpnTesterService(
        SimpleNamespace(), remnawave_client=remnawave_client
    )._remnawave_transport_results()
    profile_result = {item["check_key"]: item for item in results}[
        "remnawave.config_profiles.moscow_smart_global_routing"
    ]

    assert profile_result["status"] == "fail"
    assert profile_result["details"]["routing"]["all_rules_customer_scoped"] is False
    assert profile_result["details"]["routing"]["bridge_inbound_excluded_from_customer_rules"] is False
    assert profile_result["details"]["routing"]["private_ip_block_rule_valid"] is False


@pytest.mark.asyncio
async def test_remnawave_transport_results_fail_when_external_squad_routing_header_is_missing() -> None:
    payloads = _remnawave_transport_payloads()
    headers = _external_squad(payloads)["responseHeaders"]
    headers.pop("routing")
    remnawave_client = SimpleNamespace(get=AsyncMock(side_effect=lambda path: payloads[path]))

    results = await VpnTesterService(
        SimpleNamespace(), remnawave_client=remnawave_client
    )._remnawave_transport_results()
    by_key = {item["check_key"]: item for item in results}
    squad_result = by_key["remnawave.external_squads.premium_smart_ru_headers"]

    assert squad_result["status"] == "fail"
    assert squad_result["details"]["routing_header_present"] is False
    assert squad_result["details"]["routing_decode_error"] == "missing_routing_header"
    assert by_key["remnawave.config_profiles.de_smart_ru_server_routing"]["status"] == "pass"
    assert by_key["remnawave.config_profiles.moscow_smart_global_routing"]["status"] == "pass"


@pytest.mark.asyncio
async def test_remnawave_transport_results_fail_when_external_squad_routing_header_is_malformed() -> None:
    payloads = _remnawave_transport_payloads()
    _external_squad(payloads)["responseHeaders"]["routing"] = "not-base64-routing"
    remnawave_client = SimpleNamespace(get=AsyncMock(side_effect=lambda path: payloads[path]))

    results = await VpnTesterService(
        SimpleNamespace(), remnawave_client=remnawave_client
    )._remnawave_transport_results()
    squad_result = {item["check_key"]: item for item in results}["remnawave.external_squads.premium_smart_ru_headers"]

    assert squad_result["status"] == "fail"
    assert squad_result["details"]["routing_header_decoded"] is False
    assert squad_result["details"]["routing_decode_error"] == "malformed_routing_header"
    assert "not-base64-routing" not in str(results)


@pytest.mark.asyncio
async def test_remnawave_transport_results_fail_when_external_squad_domain_strategy_is_stale_ip_if_non_match() -> None:
    payloads = _remnawave_transport_payloads()
    routing_payload = _external_routing_payload()
    routing_payload["DomainStrategy"] = "IPIfNonMatch"
    _external_squad(payloads)["responseHeaders"]["routing"] = _base64_json(routing_payload)
    remnawave_client = SimpleNamespace(get=AsyncMock(side_effect=lambda path: payloads[path]))

    results = await VpnTesterService(
        SimpleNamespace(), remnawave_client=remnawave_client
    )._remnawave_transport_results()
    squad_result = {item["check_key"]: item for item in results}["remnawave.external_squads.premium_smart_ru_headers"]

    assert squad_result["status"] == "fail"
    assert squad_result["details"]["routing_header_decoded"] is True
    assert squad_result["details"]["domain_strategy_valid"] is False


@pytest.mark.asyncio
async def test_remnawave_transport_results_fail_when_external_squad_block_sites_are_incomplete() -> None:
    payloads = _remnawave_transport_payloads()
    block_sites = list(service_module.PREMIUM_SMART_RU_EXTERNAL_ROUTING_BLOCK_SITES)
    block_sites.remove("domain:rutracker.org")
    _external_squad(payloads)["responseHeaders"]["routing"] = _base64_json(
        _external_routing_payload(block_sites=block_sites)
    )
    remnawave_client = SimpleNamespace(get=AsyncMock(side_effect=lambda path: payloads[path]))

    results = await VpnTesterService(
        SimpleNamespace(), remnawave_client=remnawave_client
    )._remnawave_transport_results()
    squad_result = {item["check_key"]: item for item in results}["remnawave.external_squads.premium_smart_ru_headers"]

    assert squad_result["status"] == "fail"
    assert squad_result["details"]["block_sites_count"] == 6
    assert squad_result["details"]["block_sites_exact"] is False


@pytest.mark.asyncio
async def test_remnawave_transport_results_support_v2_8_host_inbound_references() -> None:
    payloads = _remnawave_transport_payloads()
    hosts = payloads["/hosts"]
    assert isinstance(hosts, list)
    for host in hosts:
        tag = host["inbound"]["tag"]
        inbound_uuid = {
            "VLESS_REALITY_443": "00000000-0000-4000-8000-000000000001",
            "VLESS_XHTTP_REALITY_8443": "00000000-0000-4000-8000-000000000002",
            "DE_SMART_REALITY_443": "00000000-0000-4000-8000-000000000003",
            "DE_SMART_XHTTP_REALITY_8443": "00000000-0000-4000-8000-000000000004",
            "MSK_SMART_REALITY_443": "00000000-0000-4000-8000-000000000005",
            "MSK_SMART_XHTTP_REALITY_8443": "00000000-0000-4000-8000-000000000006",
        }[tag]
        host["inbound"] = {"configProfileInboundUuid": inbound_uuid}
        node = host["nodes"][0]
        host["nodes"] = [node["uuid"]]
    remnawave_client = SimpleNamespace(get=AsyncMock(side_effect=lambda path: payloads[path]))
    service = VpnTesterService(SimpleNamespace(), remnawave_client=remnawave_client)

    results = await service._remnawave_transport_results()
    by_key = {item["check_key"]: item for item in results}
    details = by_key["remnawave.hosts.transport_matrix"]["details"]

    assert by_key["remnawave.hosts.transport_matrix"]["status"] == "pass"
    assert details["candidate_host_count"] == 8
    assert details["inbound_reference_resolved_count"] == 8
    assert details["expanded_node_link_count"] == 8
    assert details["unresolved_node_reference_count"] == 0
    assert details["secrets_redacted"] is True


@pytest.mark.asyncio
async def test_remnawave_transport_results_fail_when_moscow_public_hosts_use_base_tags() -> None:
    payloads = _remnawave_transport_payloads()
    hosts = payloads["/hosts"]
    assert isinstance(hosts, list)
    moscow_hosts = [host for host in hosts if host["address"] == "msk-relay.cyber-vpn.org"]
    moscow_hosts[0]["inbound"]["tag"] = "VLESS_REALITY_443"
    moscow_hosts[1]["inbound"]["tag"] = "VLESS_XHTTP_REALITY_8443"
    remnawave_client = SimpleNamespace(get=AsyncMock(side_effect=lambda path: payloads[path]))

    results = await VpnTesterService(
        SimpleNamespace(), remnawave_client=remnawave_client
    )._remnawave_transport_results()
    by_key = {item["check_key"]: item for item in results}
    details = by_key["remnawave.hosts.transport_matrix"]["details"]

    assert by_key["remnawave.hosts.transport_matrix"]["status"] == "fail"
    assert details["missing_link_count"] == 2
    assert details["unexpected_link_count"] == 2


@pytest.mark.asyncio
async def test_remnawave_transport_results_fail_when_host_node_links_are_absent() -> None:
    payloads = _remnawave_transport_payloads()
    for host in payloads["/hosts"]:
        host["nodes"] = []
    remnawave_client = SimpleNamespace(get=AsyncMock(side_effect=lambda path: payloads[path]))

    results = await VpnTesterService(
        SimpleNamespace(), remnawave_client=remnawave_client
    )._remnawave_transport_results()
    by_key = {item["check_key"]: item for item in results}

    assert by_key["remnawave.hosts.transport_matrix"]["status"] == "fail"
    assert by_key["remnawave.hosts.transport_matrix"]["details"]["missing_link_count"] == 8


@pytest.mark.asyncio
async def test_remnawave_transport_results_fail_when_host_has_unresolved_extra_node_link() -> None:
    payloads = _remnawave_transport_payloads()
    payloads["/hosts"][0]["nodes"].append("00000000-0000-4000-8000-ffffffffffff")
    remnawave_client = SimpleNamespace(get=AsyncMock(side_effect=lambda path: payloads[path]))

    results = await VpnTesterService(
        SimpleNamespace(), remnawave_client=remnawave_client
    )._remnawave_transport_results()
    by_key = {item["check_key"]: item for item in results}

    assert by_key["remnawave.hosts.transport_matrix"]["status"] == "fail"
    details = by_key["remnawave.hosts.transport_matrix"]["details"]
    assert details["expanded_node_link_count"] == 8
    assert details["unresolved_node_reference_count"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("latest_status", ["degraded", "skipped", "fail"])
async def test_release_gate_blocks_every_non_pass_status(latest_status: str) -> None:
    repository = SimpleNamespace(
        list_runs=AsyncMock(
            return_value=[
                SimpleNamespace(
                    id=uuid4(),
                    status=latest_status,
                    suite_key="premium_smart_ru_v1",
                    suite_version="v1",
                    mode="runtime",
                    finished_at=service_module._utc_now(),
                    results=_passing_release_gate_results(),
                )
            ]
        ),
        get_active_release_gate_override=AsyncMock(return_value=None),
    )
    service = VpnTesterService(repository)

    gate = await service.release_gate()

    assert gate["blocking"] is True
    assert gate["status"] == "blocked"


@pytest.mark.asyncio
async def test_release_gate_opens_only_for_pass_status() -> None:
    repository = SimpleNamespace(
        list_runs=AsyncMock(
            return_value=[
                SimpleNamespace(
                    id=uuid4(),
                    status="pass",
                    suite_key="premium_smart_ru_v1",
                    suite_version="v1",
                    mode="runtime",
                    finished_at=service_module._utc_now(),
                    results=_passing_release_gate_results(),
                )
            ]
        ),
        get_active_release_gate_override=AsyncMock(return_value=None),
    )
    service = VpnTesterService(repository)

    gate = await service.release_gate()

    assert gate["blocking"] is False
    assert gate["status"] == "pass"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("suite_key", "mode"),
    [
        ("default_subscription_smoke_v1", "runtime"),
        ("premium_smart_ru_v1", "contract"),
    ],
)
async def test_release_gate_blocks_passing_run_from_wrong_suite_or_mode(suite_key: str, mode: str) -> None:
    repository = SimpleNamespace(
        list_runs=AsyncMock(
            return_value=[
                SimpleNamespace(
                    id=uuid4(),
                    status="pass",
                    suite_key=suite_key,
                    suite_version="v1",
                    mode=mode,
                    finished_at=service_module._utc_now(),
                    results=_passing_release_gate_results(),
                )
            ]
        ),
        get_active_release_gate_override=AsyncMock(return_value=None),
    )

    gate = await VpnTesterService(repository).release_gate()

    assert gate["blocking"] is True
    assert gate["reason"] == "latest_vpn_tester_run_missing_required_evidence"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "missing_key",
    [
        "generated_subscription.vless_reality_raw_tcp",
        "generated_subscription.xhttp_transport",
        "remnawave.config_profiles.de_smart_ru_server_routing",
        "remnawave.config_profiles.moscow_smart_global_routing",
        "remnawave.external_squads.premium_smart_ru_headers",
        "runtime.transport.raw.de",
        "runtime.transport.xhttp.de",
        "runtime.transport_profile_matrix.required",
    ],
)
async def test_release_gate_blocks_missing_mandatory_transport_evidence(missing_key: str) -> None:
    results = [result for result in _passing_release_gate_results() if result.check_key != missing_key]
    repository = SimpleNamespace(
        list_runs=AsyncMock(
            return_value=[
                SimpleNamespace(
                    id=uuid4(),
                    status="pass",
                    suite_key="premium_smart_ru_v1",
                    suite_version="v1",
                    mode="runtime",
                    finished_at=service_module._utc_now(),
                    results=results,
                )
            ]
        ),
        get_active_release_gate_override=AsyncMock(return_value=None),
    )

    gate = await VpnTesterService(repository).release_gate()

    assert gate["blocking"] is True


@pytest.mark.asyncio
async def test_release_gate_blocks_spoofed_runtime_transport_keys() -> None:
    results = [
        result
        for result in _passing_release_gate_results()
        if result.check_key not in {"runtime.transport.raw.de", "runtime.transport.xhttp.de"}
    ]
    results.extend(
        [
            SimpleNamespace(check_key="runtime.transport.raw.fake-de", status="pass", details={}),
            SimpleNamespace(check_key="runtime.transport.xhttp.fake-de", status="pass", details={}),
        ]
    )
    repository = SimpleNamespace(
        list_runs=AsyncMock(
            return_value=[
                SimpleNamespace(
                    id=uuid4(),
                    status="pass",
                    suite_key="premium_smart_ru_v1",
                    suite_version="v1",
                    mode="runtime",
                    finished_at=service_module._utc_now(),
                    results=results,
                )
            ]
        ),
        get_active_release_gate_override=AsyncMock(return_value=None),
    )

    gate = await VpnTesterService(repository).release_gate()

    assert gate["blocking"] is True


@pytest.mark.asyncio
async def test_release_gate_blocks_spoofed_runtime_matrix_key() -> None:
    results = _passing_release_gate_results()
    matrix = next(result for result in results if result.check_key == "runtime.transport_profile_matrix.required")
    matrix.check_key = "runtime.transport_profile_matrix.required.spoof"
    repository = SimpleNamespace(
        list_runs=AsyncMock(
            return_value=[
                SimpleNamespace(
                    id=uuid4(),
                    status="pass",
                    suite_key="premium_smart_ru_v1",
                    suite_version="v1",
                    mode="runtime",
                    finished_at=service_module._utc_now(),
                    results=results,
                )
            ]
        ),
        get_active_release_gate_override=AsyncMock(return_value=None),
    )

    gate = await VpnTesterService(repository).release_gate()

    assert gate["blocking"] is True


@pytest.mark.asyncio
async def test_release_gate_blocks_non_pass_mandatory_check_inside_nominal_pass_run() -> None:
    results = _passing_release_gate_results()
    results[0].status = "skipped"
    repository = SimpleNamespace(
        list_runs=AsyncMock(
            return_value=[
                SimpleNamespace(
                    id=uuid4(),
                    status="pass",
                    suite_key="premium_smart_ru_v1",
                    suite_version="v1",
                    mode="runtime",
                    finished_at=service_module._utc_now(),
                    results=results,
                )
            ]
        ),
        get_active_release_gate_override=AsyncMock(return_value=None),
    )

    gate = await VpnTesterService(repository).release_gate()

    assert gate["blocking"] is True


@pytest.mark.asyncio
async def test_release_gate_blocks_stale_runtime_evidence() -> None:
    repository = SimpleNamespace(
        list_runs=AsyncMock(
            return_value=[
                SimpleNamespace(
                    id=uuid4(),
                    status="pass",
                    suite_key="premium_smart_ru_v1",
                    suite_version="v1",
                    mode="runtime",
                    finished_at=service_module._utc_now() - service_module.timedelta(hours=25),
                    results=_passing_release_gate_results(),
                )
            ]
        ),
        get_active_release_gate_override=AsyncMock(return_value=None),
    )

    gate = await VpnTesterService(repository).release_gate()

    assert gate["blocking"] is True


@pytest.mark.asyncio
async def test_release_gate_blocks_matrix_without_exact_server_evidence() -> None:
    results = _passing_release_gate_results()
    matrix = next(result for result in results if "transport_profile_matrix" in result.check_key)
    matrix.details["raw_server_matrix_valid"] = False
    repository = SimpleNamespace(
        list_runs=AsyncMock(
            return_value=[
                SimpleNamespace(
                    id=uuid4(),
                    status="pass",
                    suite_key="premium_smart_ru_v1",
                    suite_version="v1",
                    mode="runtime",
                    finished_at=service_module._utc_now(),
                    results=results,
                )
            ]
        ),
        get_active_release_gate_override=AsyncMock(return_value=None),
    )

    gate = await VpnTesterService(repository).release_gate()

    assert gate["blocking"] is True


@pytest.mark.asyncio
async def test_release_gate_does_not_allow_override_to_bypass_required_evidence() -> None:
    now = service_module._utc_now()
    active_override = SimpleNamespace(
        id=uuid4(),
        latest_run_id=None,
        overridden_by_admin_id=uuid4(),
        previous_status="blocked",
        previous_blocking=True,
        reason="Emergency override that cannot bypass transport evidence",
        expires_at=now + service_module.timedelta(hours=1),
        created_at=now,
    )
    repository = SimpleNamespace(
        list_runs=AsyncMock(return_value=[]),
        get_active_release_gate_override=AsyncMock(return_value=active_override),
    )

    gate = await VpnTesterService(repository).release_gate()

    assert gate["blocking"] is True
    assert gate["status"] == "blocked"
    assert gate["reason"] == "manual_release_gate_override_not_permitted_for_premium_smart_ru"


@pytest.mark.asyncio
async def test_runtime_run_combines_contract_and_live_transport_results() -> None:
    suite_spec = {
        "suite_key": "premium_smart_ru_v1",
        "version": "v1",
        "required_route_registry": "premium_smart_ru_v2",
    }
    run = SimpleNamespace(
        id=uuid4(),
        status="queued",
        suite_key="premium_smart_ru_v1",
        suite_version="v1",
        mode="runtime",
        request_context={},
        route_registry_version="premium_smart_ru_v2",
        trigger="manual",
    )
    repository = SimpleNamespace(
        mark_run_running=AsyncMock(),
        get_suite=AsyncMock(return_value=SimpleNamespace(spec=suite_spec)),
        list_active_plans=AsyncMock(return_value=[]),
        get_route_registry=AsyncMock(return_value=[]),
        replace_run_results=AsyncMock(side_effect=lambda current_run, **_kwargs: current_run),
    )
    generated_artifact = {"generated_mihomo_yaml": _generated_mihomo_yaml()}
    contract_result = {
        "check_key": "contract.required",
        "status": "pass",
        "severity": "error",
        "category": "contract",
    }
    runtime_result = {
        "check_key": "runtime.required",
        "status": "pass",
        "severity": "error",
        "category": "runtime",
    }
    service = VpnTesterService(repository)
    service._generated_mihomo_artifact = AsyncMock(return_value=generated_artifact)
    service._contract_results = AsyncMock(return_value=[contract_result])
    service._runtime_results = AsyncMock(return_value=[runtime_result])

    completed = await service.execute_run(run)

    assert completed is run
    service._contract_results.assert_awaited_once_with(
        suite_spec,
        [],
        [],
        request_context={},
        generated_mihomo_artifact=generated_artifact,
    )
    service._runtime_results.assert_awaited_once_with(
        run,
        [],
        generated_mihomo_artifact=generated_artifact,
    )
    assert repository.replace_run_results.await_args.kwargs["results"] == [contract_result, runtime_result]
    assert repository.replace_run_results.await_args.kwargs["status"] == "pass"
    execution_attempt_id = repository.mark_run_running.await_args.kwargs["execution_attempt_id"]
    assert len(execution_attempt_id) == 32
    assert int(execution_attempt_id, 16) >= 0
    assert repository.replace_run_results.await_args.kwargs["summary"]["execution_attempt_id"] == execution_attempt_id
    assert "preserve_evidence_types" not in repository.replace_run_results.await_args.kwargs
