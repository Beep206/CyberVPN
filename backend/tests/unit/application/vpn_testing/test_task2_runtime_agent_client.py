from __future__ import annotations

from typing import Any

import pytest
from pydantic import SecretStr

from src.application.vpn_testing import task2_runtime_agent_client as client
from src.application.vpn_testing.task2_probe_plan import Task2RouteProbeSpec
from src.application.vpn_testing.task2_route_evidence import (
    Task2RouteEvidenceExpectation,
    Task2RouteEvidenceRejected,
    Task2RouteEvidenceResult,
    task2_route_evidence_result_digest,
)
from src.config.settings import settings

SYNTHETIC_VLESS_UUID = "00000000-0000-4000-8000-000000000094"


def _generated_mihomo() -> dict[str, Any]:
    common = {
        "type": "vless",
        "server": client.TASK2_SERVER,
        "servername": "www.microsoft.com",
        "client-fingerprint": "chrome",
    }
    return {
        "proxies": [
            {
                **common,
                "name": "Task2 RAW",
                "port": 4443,
                "network": "tcp",
                "uuid": "00000000-0000-4000-8000-000000000001",
                "flow": "xtls-rprx-vision",
                "reality-opts": {"public-key": "RawPublicKeyAbc", "short-id": "00000001"},
            },
            {
                **common,
                "name": "Task2 XHTTP",
                "port": 8444,
                "network": "xhttp",
                "uuid": "00000000-0000-4000-8000-000000000002",
                "reality-opts": {"public-key": "XhttpPublicKeyAbc", "short-id": "00000002"},
                "xhttp-opts": {"path": "/task2", "mode": "auto"},
            },
        ]
    }


def _specs() -> list[Task2RouteProbeSpec]:
    common = {"manifest_sha256": "a" * 64, "route_feed_version": "b" * 64}
    return [
        Task2RouteProbeSpec(
            route_key="matched-raw-tcp",
            traffic_class="matched_exception",
            category="rkn",
            transport="raw",
            probe_network="tcp",
            target_ip="8.8.8.8",
            target_port=443,
            membership="member",
            expected_outbound="DE_EXCEPTIONS_BRIDGE",
            **common,
        ),
        Task2RouteProbeSpec(
            route_key="matched-raw-udp",
            traffic_class="matched_exception",
            category="rkn",
            transport="raw",
            probe_network="udp",
            target_ip="8.8.4.4",
            target_port=53,
            membership="member",
            expected_outbound="DE_EXCEPTIONS_BRIDGE",
            **common,
        ),
        Task2RouteProbeSpec(
            route_key="default-xhttp-tcp",
            traffic_class="unmatched_default",
            category=None,
            transport="xhttp",
            probe_network="tcp",
            target_ip="1.1.1.1",
            target_port=443,
            membership="non_member",
            expected_outbound="DIRECT",
            **common,
        ),
        Task2RouteProbeSpec(
            route_key="default-xhttp-udp",
            traffic_class="unmatched_default",
            category=None,
            transport="xhttp",
            probe_network="udp",
            target_ip="1.0.0.1",
            target_port=53,
            membership="non_member",
            expected_outbound="DIRECT",
            **common,
        ),
    ]


def test_run_scoped_probe_specs_use_unique_unpredictable_target_ports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = iter(range(100, 100 + len(_specs())))
    monkeypatch.setattr(client.secrets, "randbelow", lambda _span: next(values))

    scoped = client._run_scoped_probe_specs(_specs())

    assert len({spec.target_port for spec in scoped}) == len(scoped)
    assert [spec.target_port for spec in scoped] == [
        client.TASK2_CORRELATION_PORT_MIN + value for value in range(100, 104)
    ]
    assert [spec.target_port for spec in scoped] != [spec.target_port for spec in _specs()]


class FakeEvidenceStore:
    def __init__(self, *, missing_route: str | None = None, tampered_route: str | None = None) -> None:
        self.expectations: dict[str, Task2RouteEvidenceExpectation] = {}
        self.missing_route = missing_route
        self.tampered_route = tampered_route

    async def create_expectation(self, expectation: Task2RouteEvidenceExpectation) -> None:
        self.expectations[expectation.target_digest] = expectation

    async def delete_expectations(self, target_digests: list[str]) -> None:
        for digest in target_digests:
            self.expectations.pop(digest, None)

    async def get_result_for_target_digest(
        self,
        run_id: str,
        target_digest: str,
    ) -> Task2RouteEvidenceResult | None:
        expectation = self.expectations.get(target_digest)
        if expectation is None or expectation.run_id != run_id or expectation.route_key == self.missing_route:
            return None
        digest = task2_route_evidence_result_digest(
            settings.vpn_tester_task2_xray_webhook_secret.get_secret_value(),
            run_id=expectation.run_id,
            route_key=expectation.route_key,
            selected_outbound=expectation.expected_outbound,
            verdict="pass",
            target_digest=target_digest,
        )
        return Task2RouteEvidenceResult(
            run_id=expectation.run_id,
            route_key=expectation.route_key,
            selected_outbound=expectation.expected_outbound,
            verdict="pass",
            digest="c" * 64 if expectation.route_key == self.tampered_route else digest,
        )


@pytest.mark.asyncio
async def test_collect_results_rejects_unbound_redis_result() -> None:
    spec = _specs()[0]
    run_id = "00000000-0000-4000-8000-000000000099"
    target_digest = "a" * 64
    store = FakeEvidenceStore(tampered_route=spec.route_key)
    await store.create_expectation(
        Task2RouteEvidenceExpectation(
            run_id=run_id,
            route_key=spec.route_key,
            target_digest=target_digest,
            expected_outbound=spec.expected_outbound,
            expected_inbound_tag="SPB_EXCEPTIONS_REALITY_443",
            expected_network=spec.probe_network,
        )
    )

    with pytest.raises(Task2RouteEvidenceRejected, match="result_binding_mismatch"):
        await client._collect_results(
            store,  # type: ignore[arg-type]
            {spec.route_key: target_digest},
            {spec.route_key: spec},
            run_id=run_id,
            webhook_secret=settings.vpn_tester_task2_xray_webhook_secret.get_secret_value(),
        )


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "vpn_test_agent_spb_url", "https://spb-agent.internal")
    monkeypatch.setattr(settings, "vpn_test_agent_spb_secret", SecretStr("spb-agent-secret-value"))
    monkeypatch.setattr(
        settings,
        "vpn_tester_task2_xray_webhook_secret",
        SecretStr("task2-webhook-secret-value-with-32-chars"),
    )


def test_task2_profile_parser_accepts_only_exact_raw_xhttp_pair() -> None:
    profiles = client.task2_runtime_profiles_from_generated_mihomo(_generated_mihomo())

    assert [profile.transport for profile in profiles] == ["raw", "xhttp"]
    literal_ip = _generated_mihomo()
    for proxy in literal_ip["proxies"]:
        proxy["server"] = client.TASK2_SERVER_IPV4
    literal_profiles = client.task2_runtime_profiles_from_generated_mihomo(literal_ip)
    assert [profile.server for profile in literal_profiles] == [
        client.TASK2_SERVER_IPV4,
        client.TASK2_SERVER_IPV4,
    ]
    invalid = _generated_mihomo()
    invalid["proxies"][0]["server"] = "ru-spb-3.cyber-vpn.org"
    assert client.task2_runtime_profiles_from_generated_mihomo(invalid) == []


@pytest.mark.asyncio
async def test_task2_runtime_correlates_server_results_without_agent_selected_outbound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    specs = _specs()
    monkeypatch.setattr(client, "build_task2_route_probe_specs", lambda _routes: specs)

    async def signed_agent(**kwargs: Any) -> dict[str, Any]:
        payload = kwargs["payload"]
        assert {profile["uuid"] for profile in payload["transport_profiles"]} == {SYNTHETIC_VLESS_UUID}
        return {
            "status": "partial",
            "agent_id": "spb-agent",
            "checks": [],
            "route_attempts": [
                {
                    "expectation_id": route["expectation_id"],
                    "route_key": route["route_key"],
                    "transport": route["transport"],
                    "probe_network": route["probe_network"],
                    "terminal_class": "udp_datagram_sent"
                    if route["probe_network"] == "udp"
                    else "tcp_connect_established",
                }
                for route in payload["routes"]
            ],
        }

    monkeypatch.setattr(client, "_post_signed_payload", signed_agent)
    store = FakeEvidenceStore()

    result = await client.call_task2_runtime_agent(
        run_id="00000000-0000-4000-8000-000000000099",
        route_entries=[],
        generated_mihomo_artifact=_generated_mihomo(),
        synthetic_vless_uuid=SYNTHETIC_VLESS_UUID,
        evidence_store=store,  # type: ignore[arg-type]
    )

    assert result["status"] == "partial"
    assert result["reason"] == "bridge_down_evidence_not_claimed"
    matrix = next(check for check in result["checks"] if check["check_key"].endswith(".matrix"))
    assert matrix["status"] == "degraded"
    assert matrix["details"]["bridge_down_evidence_claimed"] is False
    assert all(
        check["details"].get("selected_outbound") in {"DE_EXCEPTIONS_BRIDGE", "DIRECT"}
        for check in result["checks"]
        if ".selected_outbound." in check["check_key"] and not check["check_key"].endswith(".matrix")
    )


@pytest.mark.asyncio
async def test_task2_runtime_rejects_agent_manufactured_selected_outbound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    specs = _specs()
    monkeypatch.setattr(client, "build_task2_route_probe_specs", lambda _routes: specs)

    async def invalid_agent(**_kwargs: Any) -> dict[str, Any]:
        return {"status": "pass", "selected_outbound": "DIRECT", "route_attempts": []}

    monkeypatch.setattr(client, "_post_signed_payload", invalid_agent)

    result = await client.call_task2_runtime_agent(
        run_id="00000000-0000-4000-8000-000000000099",
        route_entries=[],
        generated_mihomo_artifact=_generated_mihomo(),
        synthetic_vless_uuid=SYNTHETIC_VLESS_UUID,
        evidence_store=FakeEvidenceStore(),  # type: ignore[arg-type]
    )

    assert result["status"] == "fail"
    assert result["reason"] == "task2_agent_attempt_evidence_invalid"


@pytest.mark.asyncio
async def test_task2_runtime_missing_webhook_result_fails_matrix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    specs = _specs()
    monkeypatch.setattr(client, "build_task2_route_probe_specs", lambda _routes: specs)
    monkeypatch.setattr(client, "TASK2_RESULT_POLL_SECONDS", 0.0)

    async def signed_agent(**kwargs: Any) -> dict[str, Any]:
        return {
            "status": "partial",
            "agent_id": "spb-agent",
            "route_attempts": [
                {
                    "expectation_id": route["expectation_id"],
                    "route_key": route["route_key"],
                    "transport": route["transport"],
                    "probe_network": route["probe_network"],
                    "terminal_class": "socks_request_rejected",
                }
                for route in kwargs["payload"]["routes"]
            ],
        }

    monkeypatch.setattr(client, "_post_signed_payload", signed_agent)

    result = await client.call_task2_runtime_agent(
        run_id="00000000-0000-4000-8000-000000000099",
        route_entries=[],
        generated_mihomo_artifact=_generated_mihomo(),
        synthetic_vless_uuid=SYNTHETIC_VLESS_UUID,
        evidence_store=FakeEvidenceStore(missing_route=specs[0].route_key),  # type: ignore[arg-type]
    )

    assert result["status"] == "fail"
    assert result["reason"] == "selected_outbound_matrix_failed"
