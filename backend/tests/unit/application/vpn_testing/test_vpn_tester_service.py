from __future__ import annotations

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
    for index, server in enumerate(
        (
            "de-3.cyber-vpn.org",
            "nl-4.cyber-vpn.org",
            "ru-msk-3.cyber-vpn.org",
            "ru-spb-3.cyber-vpn.org",
        ),
        start=1,
    ):
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
    port: 443
    network: tcp
    flow: xtls-rprx-vision"""
        )
        proxies.append(
            f"""{common}
    port: 8443
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
        )
    ]


def _passing_release_gate_results() -> list[SimpleNamespace]:
    keys = [
        "generated_subscription.vless_reality_raw_tcp",
        "generated_subscription.xhttp_transport",
        "remnawave.inbounds.vless_reality_raw_tcp",
        "remnawave.inbounds.vless_reality_xhttp",
        "remnawave.hosts.transport_matrix",
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
    node_names = {
        "de-3.cyber-vpn.org": "🇩🇪 DE Frankfurt 01 25G",
        "nl-4.cyber-vpn.org": "🇳🇱 NL Amsterdam 01 10G",
        "ru-msk-3.cyber-vpn.org": "🇷🇺 RU Moscow 01 25G",
        "ru-spb-3.cyber-vpn.org": "🇷🇺 RU SPB 01 25G",
    }
    node_rows = []
    hosts = []
    for node_index, (address, node_name) in enumerate(node_names.items(), start=10):
        node_uuid = f"00000000-0000-4000-8000-{node_index:012x}"
        node_rows.append({"uuid": node_uuid, "name": node_name, "isConnected": True, "isDisabled": False})
        for port, tag in ((443, "VLESS_REALITY_443"), (8443, "VLESS_XHTTP_REALITY_8443")):
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
        "/config-profiles/inbounds": {"inbounds": [raw_inbound, xhttp_inbound]},
        "/hosts": hosts,
        "/nodes": {"nodes": node_rows},
        "/internal-squads": {
            "internalSquads": [
                {
                    "name": "CYBERVPN_PREMIUM_SMART_RU_NODES",
                    "inbounds": [
                        {"tag": "VLESS_REALITY_443"},
                        {"tag": "VLESS_XHTTP_REALITY_8443"},
                    ],
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
    safe_output = str(results)
    assert "sensitive-private-key" not in safe_output
    assert "sensitive-short-id" not in safe_output
    assert "reality-target.example" not in safe_output

    raw_inbound = payloads["/config-profiles/inbounds"]["inbounds"][0]
    raw_inbound["rawInbound"]["settings"]["flow"] = ""
    failed = await service._remnawave_transport_results()
    by_key = {item["check_key"]: item for item in failed}

    assert by_key["remnawave.inbounds.vless_reality_raw_tcp"]["status"] == "fail"
    assert by_key["remnawave.inbounds.vless_reality_xhttp"]["status"] == "pass"
    assert by_key["remnawave.hosts.transport_matrix"]["status"] == "pass"


@pytest.mark.asyncio
async def test_remnawave_transport_results_support_v2_8_host_inbound_references() -> None:
    payloads = _remnawave_transport_payloads()
    hosts = payloads["/hosts"]
    assert isinstance(hosts, list)
    for host in hosts:
        tag = host["inbound"]["tag"]
        inbound_uuid = (
            "00000000-0000-4000-8000-000000000001"
            if tag == "VLESS_REALITY_443"
            else "00000000-0000-4000-8000-000000000002"
        )
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
