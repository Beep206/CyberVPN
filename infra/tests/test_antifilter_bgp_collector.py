# ruff: noqa: S101

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from jinja2 import Environment, FileSystemLoader

REPO_ROOT = Path(__file__).resolve().parents[2]
INFRA_ROOT = REPO_ROOT / "infra"
ROLE = INFRA_ROOT / "ansible" / "roles" / "antifilter_bgp_collector"
DEFAULTS = ROLE / "defaults" / "main.yml"
VALIDATE = ROLE / "tasks" / "validate.yml"
DEPLOY = ROLE / "tasks" / "deploy.yml"
VERIFY = ROLE / "tasks" / "verify.yml"
BIRD_TEMPLATE = ROLE / "templates" / "bird.conf.j2"
SERVICE_TEMPLATE = ROLE / "templates" / "collector.service.j2"
TIMER_TEMPLATE = ROLE / "templates" / "collector.timer.j2"
PLAYBOOK = INFRA_ROOT / "ansible" / "playbooks" / "antifilter-bgp-collector.yml"
EXPORTER = REPO_ROOT / "scripts" / "remnawave" / "export-antifilter-bird-routes.py"
ANTIFILTER_PARENT = REPO_ROOT / "scripts" / "remnawave"
EXAMPLE_POLICY = REPO_ROOT / "data" / "antifilter" / "example-policy.json"
NOW = datetime(2026, 7, 11, 0, 0, tzinfo=UTC)
IPV6_DISABLED_REASON = "Offline fixture has no proven equivalent IPv6 feed; the tariff profile must disable IPv6."
REQUIRED_COMMUNITIES = (
    "65444:100",
    "65444:700",
    "65444:710",
    "65444:720",
    "65444:730",
    "65444:740",
    "65444:750",
    "65444:760",
    "65444:770",
    "65444:780",
    "65444:790",
    "65444:800",
    "65444:65444",
)

sys.path.insert(0, str(ANTIFILTER_PARENT))
from antifilter.models import COMMUNITY_CATEGORY, load_policy  # noqa: E402


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _load_exporter() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "export_antifilter_bird_routes", EXPORTER
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _render_bird_config(*, bgp_secret: str = "", ipv6_enabled: bool = True) -> str:
    environment = Environment(
        loader=FileSystemLoader(str(BIRD_TEMPLATE.parent)),
        autoescape=True,
    )
    environment.filters["bool"] = bool
    template = environment.get_template(BIRD_TEMPLATE.name)
    return template.render(
        antifilter_bgp_collector_router_id="91.200.1.10",
        antifilter_bgp_collector_table_ipv4="antifilter4",
        antifilter_bgp_collector_table_ipv6="antifilter6",
        antifilter_bgp_collector_ipv6_enabled=ipv6_enabled,
        antifilter_bgp_collector_required_communities=REQUIRED_COMMUNITIES,
        antifilter_bgp_collector_protocol_ipv4="antifilter_v4",
        antifilter_bgp_collector_protocol_ipv6="antifilter_v6",
        antifilter_bgp_collector_local_as=64999,
        antifilter_bgp_collector_remote_as=65444,
        antifilter_bgp_collector_neighbor_ipv4="45.148.244.55",
        antifilter_bgp_collector_neighbor_ipv6="2001:41d0:701:1100::1db1",
        antifilter_bgp_collector_multihop_ttl=32,
        antifilter_bgp_collector_source_ipv4="91.200.1.10",
        antifilter_bgp_collector_source_ipv6="2001:4860:abcd::10",
        antifilter_bgp_collector_bgp_password=bgp_secret,
        antifilter_bgp_collector_hold_time=240,
    )


class FakeBirdClient:
    def __init__(
        self,
        routes: dict[tuple[int, str], str],
        *,
        fail_protocol: str | None = None,
    ) -> None:
        self.routes = routes
        self.fail_protocol = fail_protocol
        self.ready_checks: list[tuple[str, str]] = []
        self.queries: list[tuple[str, str]] = []

    def assert_protocol_ready(self, protocol: str, family: str) -> None:
        self.ready_checks.append((protocol, family))
        if protocol == self.fail_protocol:
            raise RuntimeError("protocol down")

    def query_routes(self, table: str, community: str) -> str:
        family = 6 if table == "antifilter6" else 4
        self.queries.append((table, community))
        return self.routes.get(
            (family, community), f"BIRD 2.0.12 ready.\nTable {table}:\n"
        )


def _options(
    module: ModuleType, output_root: Path, *, source_version: str = "fixture-v1"
) -> Any:
    return module.ExportOptions(
        birdc=Path("/usr/sbin/birdc"),
        socket=Path("/run/bird/bird.ctl"),
        output_root=output_root,
        collector="cybervpn-antifilter-bgp-bird2",
        protocol_ipv4="antifilter_v4",
        table_ipv4="antifilter4",
        protocol_ipv6="antifilter_v6",
        table_ipv6="antifilter6",
        ipv6_policy="disabled",
        ipv6_policy_reason=IPV6_DISABLED_REASON,
        generated_at=NOW,
        source_version=source_version,
        timeout_seconds=20,
        max_output_bytes=67_108_864,
        max_lines_per_community=1_000_000,
    )


def _routes() -> dict[tuple[int, str], str]:
    result: dict[tuple[int, str], str] = {}
    for index, community in enumerate(REQUIRED_COMMUNITIES, start=1):
        cidr = f"91.{index}.0.0/16"
        result[(4, community)] = (
            "BIRD 2.0.12 ready.\n"
            "Table antifilter4:\n"
            f"{cidr} unicast [antifilter_v4 2026-07-11] * (100) [AS65444i]\n"
            f"{cidr} unicast [antifilter_v4 2026-07-11] * (100) [AS65444i]\n"
            "\tBGP.community: (65444,100)\n"
        )
    return result


def test_role_pins_official_bgp_contract_and_community_mapping() -> None:
    defaults = _read(DEFAULTS)
    validate = _read(VALIDATE)
    bird = _read(BIRD_TEMPLATE)
    playbook = _read(PLAYBOOK)

    assert "antifilter_bgp_collector_remote_as: 65444" in defaults
    assert "antifilter_bgp_collector_local_as: 64999" in defaults
    assert "antifilter_bgp_collector_hold_time: 240" in defaults
    assert "antifilter_bgp_collector_multihop_ttl: 32" in defaults
    assert 'antifilter_bgp_collector_neighbor_ipv4: "45.148.244.55"' in defaults
    assert (
        'antifilter_bgp_collector_neighbor_ipv6: "2001:41d0:701:1100::1db1"' in defaults
    )
    assert "antifilter_bgp_collector_ipv6_enabled: false" in defaults
    assert "vault_antifilter_bgp_collector_bgp_password" in defaults

    for community in REQUIRED_COMMUNITIES:
        assert f'"{community}"' in defaults
    assert "({{ community | replace(':', ',') }}) ~ bgp_community" in bird
    assert f"unique | length == {len(REQUIRED_COMMUNITIES)}" in validate
    assert "antifilter_bgp_collector_multihop_ttl | int >= 16" in validate
    assert "antifilter_bgp_collector_multihop_ttl | int <= 64" in validate
    assert "role: antifilter_bgp_collector" in playbook
    assert "default('antifilter_bgp_collector')" in playbook
    assert "Refuse silent no-op deploy" in playbook
    assert "antifilter_bgp_collector_enabled | default(false) | bool" in playbook

    assert tuple(sorted(COMMUNITY_CATEGORY)) == tuple(sorted(REQUIRED_COMMUNITIES))


def test_bird_template_is_read_only_and_does_not_touch_kernel_routes() -> None:
    bird = _read(BIRD_TEMPLATE)

    assert bird.count("export none;") == 2
    assert "protocol kernel" not in bird.lower()
    assert "protocol direct" not in bird.lower()
    assert "learn;" not in bird
    assert "persist;" not in bird
    assert "scan time" not in bird
    assert "ipv4 table {{ antifilter_bgp_collector_table_ipv4 }}" in bird
    assert "ipv6 table {{ antifilter_bgp_collector_table_ipv6 }}" in bird
    assert "import filter antifilter_required_ipv4" in bird
    assert "import filter antifilter_required_ipv6" in bird
    assert "multihop {{ antifilter_bgp_collector_multihop_ttl }}" in bird
    assert "source address {{ antifilter_bgp_collector_source_ipv4 }}" in bird
    assert "source address {{ antifilter_bgp_collector_source_ipv6 }}" in bird


def test_optional_password_rendering_is_vault_backed_and_hidden_from_logs() -> None:
    defaults = _read(DEFAULTS)
    validate = _read(VALIDATE)
    deploy = _read(DEPLOY)
    bird = _read(BIRD_TEMPLATE)

    assert (
        "antifilter_bgp_collector_bgp_password: "
        "\"{{ vault_antifilter_bgp_collector_bgp_password | default('') }}\""
    ) in defaults
    assert "antifilter_bgp_collector_bgp_password | length == 0 or" in validate
    assert "vault_antifilter_bgp_collector_bgp_password is defined" in validate
    assert "antifilter_bgp_collector_bgp_password ==" in validate
    assert "vault_antifilter_bgp_collector_bgp_password" in validate
    assert "no_log: true" in validate
    assert "Render BIRD2 read-only BGP configuration" in deploy
    assert "no_log: true" in deploy
    assert "antifilter_bgp_collector_bird_string_unsafe_re" in validate
    for unsafe in ('"', "\\\\", "\\r", "\\n", ";", "{", "}", "#"):
        assert unsafe in validate
    assert "{% if antifilter_bgp_collector_bgp_password | length > 0 %}" in bird
    assert 'password "{{ antifilter_bgp_collector_bgp_password }}"' in bird
    assert "live registration" not in defaults.lower()

    without_password = _render_bird_config(bgp_secret="", ipv6_enabled=False)
    assert "password " not in without_password
    assert "source address 91.200.1.10;" in without_password
    assert "multihop 32;" in without_password

    with_password = _render_bird_config(
        bgp_secret="0123456789abcdef", ipv6_enabled=True
    )  # noqa: S106
    assert with_password.count('password "0123456789abcdef";') == 2


def test_enabled_validation_requires_public_source_and_router_id() -> None:
    defaults = _read(DEFAULTS)
    validate = _read(VALIDATE)

    assert 'antifilter_bgp_collector_source_ipv4: ""' in defaults
    assert 'antifilter_bgp_collector_source_ipv6: ""' in defaults
    assert 'antifilter_bgp_collector_router_id: ""' in defaults
    assert "antifilter_bgp_collector_router_id ==" in validate
    assert "antifilter_bgp_collector_source_ipv4 or" in validate
    assert (
        "antifilter_bgp_collector_router_id_override_justification | length >= 20"
        in validate
    )
    for forbidden in (
        "10",
        "127",
        "169\\.254",
        "172\\.(?:1[6-9]|2[0-9]|3[01])",
        "192\\.168",
        "192\\.0\\.(?:0|2)",
        "192\\.88\\.99",
        "198\\.51\\.100",
        "203\\.0\\.113",
        "198\\.(?:18|19)",
        "100\\.(?:6[4-9]|[789][0-9]|1[01][0-9]|12[0-7])",
        "22[4-9]",
        "2001:db8",
        "fe80",
    ):
        assert forbidden in validate


def test_systemd_timer_generates_candidate_input_only_and_is_hardened() -> None:
    deploy = _read(DEPLOY)
    main = _read(ROLE / "tasks" / "main.yml")
    handlers = _read(ROLE / "handlers" / "main.yml")
    service = _read(SERVICE_TEMPLATE)
    timer = _read(TIMER_TEMPLATE)

    assert "owner: root" in deploy
    assert "group: root" in deploy
    assert 'mode: "0750"' in deploy
    assert deploy.count("when: not ansible_check_mode") == 2
    assert "- not ansible_check_mode" in main
    assert handlers.count("when: not ansible_check_mode") == 2
    assert "{{ antifilter_bgp_collector_exporter_path }}" in service
    assert "ConditionPathIsSocket" not in service
    assert (
        "ExecStartPre=/usr/bin/test -S {{ antifilter_bgp_collector_bird_socket }}"
        in service
    )
    assert "--output-root {{ antifilter_bgp_collector_output_root }}" in service
    assert "--ipv6-policy {{ antifilter_bgp_collector_ipv6_policy_mode }}" in service
    assert "antifilter publish" not in service
    assert " publish" not in service
    assert "promote" not in service
    assert "last-known-good" not in service
    assert "active.json" not in service
    assert "NoNewPrivileges=true" in service
    assert "User=root" in service
    assert "Group=bird" in service
    assert "ProtectSystem=strict" in service
    assert "ReadWritePaths={{ antifilter_bgp_collector_output_root }}" in service
    assert "RestrictAddressFamilies=AF_UNIX" in service
    assert "CapabilityBoundingSet=" in service
    assert "MemoryMax={{ antifilter_bgp_collector_unit_memory_max }}" in service
    assert "TasksMax={{ antifilter_bgp_collector_unit_tasks_max }}" in service
    assert (
        "OnUnitActiveSec={{ antifilter_bgp_collector_timer_on_unit_active_sec }}"
        in timer
    )
    assert "Unit={{ antifilter_bgp_collector_service_name }}.service" in timer


def test_template_interpolated_variables_are_strictly_validated() -> None:
    validate = _read(VALIDATE)

    assert "antifilter_bgp_collector_safe_abs_path_re" in validate
    assert "antifilter_bgp_collector_bird_identifier_re" in validate
    assert "antifilter_bgp_collector_systemd_name_re" in validate
    assert "antifilter_bgp_collector_cli_token_re" in validate
    for variable in (
        "antifilter_bgp_collector_bird_binary",
        "antifilter_bgp_collector_birdc_path",
        "antifilter_bgp_collector_python_path",
        "antifilter_bgp_collector_table_ipv4",
        "antifilter_bgp_collector_table_ipv6",
        "antifilter_bgp_collector_protocol_ipv4",
        "antifilter_bgp_collector_protocol_ipv6",
        "antifilter_bgp_collector_bird_service",
        "antifilter_bgp_collector_collector_name",
    ):
        assert variable in validate


def test_verify_runs_exporter_and_checks_candidate_manifest_contract() -> None:
    verify = _read(VERIFY)

    assert "Generate a fresh candidate during verify" in verify
    assert "{{ antifilter_bgp_collector_service_name }}.service" in verify
    assert "patterns: source.json" in verify
    assert "source.type == 'bgp-canonical-cidr'" in verify
    assert "antifilter_bgp_collector_required_communities | length" in verify
    assert "2 if antifilter_bgp_collector_ipv6_enabled | bool else 1" in verify


def test_exporter_writes_deterministic_importer_compatible_source(
    tmp_path: Path,
) -> None:
    module = _load_exporter()
    routes = _routes()

    first = module.export_candidate(
        _options(module, tmp_path / "first"), FakeBirdClient(routes)
    )
    second = module.export_candidate(
        _options(module, tmp_path / "second"), FakeBirdClient(routes)
    )

    first_files = {
        path.relative_to(first.parent): path.read_bytes()
        for path in first.parent.rglob("*")
        if path.is_file()
    }
    second_files = {
        path.relative_to(second.parent): path.read_bytes()
        for path in second.parent.rglob("*")
        if path.is_file()
    }
    assert first_files == second_files

    manifest = _json(first)
    assert manifest["source"]["type"] == "bgp-canonical-cidr"
    assert manifest["source"]["collector"] == "cybervpn-antifilter-bgp-bird2"
    assert manifest["source"]["generatedAt"] == "2026-07-11T00:00:00Z"
    assert "collectedAt" not in manifest["source"]
    assert manifest["ipv6Policy"] == {
        "mode": "disabled",
        "reason": IPV6_DISABLED_REASON,
    }
    assert len(manifest["files"]) == len(REQUIRED_COMMUNITIES)
    assert {item["family"] for item in manifest["files"]} == {4}
    assert {item["community"] for item in manifest["files"]} == set(
        REQUIRED_COMMUNITIES
    )
    for item in manifest["files"]:
        route_path = first.parent / item["path"]
        assert route_path.read_text(encoding="ascii").endswith("\n")
        assert item["sha256"] == hashlib.sha256(route_path.read_bytes()).hexdigest()

    importer = importlib.import_module("antifilter.importer")
    source = importer.load_source(first, load_policy(EXAMPLE_POLICY), NOW)
    routes_by_category = importer.read_route_files(source, load_policy(EXAMPLE_POLICY))
    openai_index = REQUIRED_COMMUNITIES.index("65444:760") + 1
    assert routes_by_category["openai"][4] == [
        module.ipaddress.ip_network(f"91.{openai_index}.0.0/16")
    ]


def test_exporter_queries_each_required_community_separately(tmp_path: Path) -> None:
    module = _load_exporter()
    client = FakeBirdClient(_routes())

    module.export_candidate(_options(module, tmp_path / "out"), client)

    assert client.ready_checks == [("antifilter_v4", "ipv4")]
    assert client.queries == [
        ("antifilter4", community) for community in REQUIRED_COMMUNITIES
    ]


def test_exporter_strict_parser_deduplicates_sorts_and_rejects_malformed_output() -> (
    None
):
    module = _load_exporter()

    parsed = module.parse_route_output(
        "BIRD 2.0.12 ready.\n"
        "Table antifilter4:\n"
        "91.2.0.0/16 unicast [antifilter_v4]\n"
        "91.1.0.0/16 unicast [antifilter_v4]\n"
        "91.1.0.0/16 unicast [antifilter_v4]\n"
        "\tBGP.community: (65444,100)\n",
        family=4,
        community="65444:100",
        max_lines=100,
    )
    assert [str(network) for network in parsed] == ["91.1.0.0/16", "91.2.0.0/16"]

    with pytest.raises(module.ExportError, match="malformed BIRD route output"):
        module.parse_route_output(
            "Table antifilter4:\nnot-a-cidr\n",
            family=4,
            community="65444:100",
            max_lines=100,
        )
    with pytest.raises(module.ExportError, match="malformed BIRD route output"):
        module.parse_route_output(
            "Table antifilter4:\n\tunexpected detail\n",
            family=4,
            community="65444:100",
            max_lines=100,
        )
    with pytest.raises(module.ExportError, match="invalid CIDR prefix"):
        module.parse_route_output(
            "91.1.1.1/16 unicast\n", family=4, community="65444:100", max_lines=100
        )
    with pytest.raises(module.ExportError, match="forbidden or unsafe CIDR"):
        module.parse_route_output(
            "0.0.0.0/0 unicast\n", family=4, community="65444:100", max_lines=100
        )
    with pytest.raises(module.ExportError, match="forbidden or unsafe CIDR"):
        module.parse_route_output(
            "10.0.0.0/8 unicast\n", family=4, community="65444:100", max_lines=100
        )
    with pytest.raises(module.ExportError, match="forbidden or unsafe CIDR"):
        module.parse_route_output(
            "::/0 unicast\n", family=6, community="65444:100", max_lines=100
        )
    with pytest.raises(module.ExportError, match="forbidden or unsafe CIDR"):
        module.parse_route_output(
            "fc00::/7 unicast\n", family=6, community="65444:100", max_lines=100
        )
    with pytest.raises(module.ExportError, match="has no IPv4 routes"):
        module.parse_route_output(
            "BIRD 2.0.12 ready.\nTable antifilter4:\n",
            family=4,
            community="65444:100",
            max_lines=100,
        )
    with pytest.raises(module.ExportError, match="exceeds 1 lines"):
        module.parse_route_output(
            "91.1.0.0/16\n91.2.0.0/16\n", family=4, community="65444:100", max_lines=1
        )


def test_exporter_fails_closed_without_partial_candidate_on_missing_community(
    tmp_path: Path,
) -> None:
    module = _load_exporter()
    routes = _routes()
    routes[(4, "65444:760")] = "BIRD 2.0.12 ready.\nTable antifilter4:\n"

    with pytest.raises(
        module.ExportError, match="required community 65444:760 has no IPv4 routes"
    ):
        module.export_candidate(
            _options(module, tmp_path / "out"), FakeBirdClient(routes)
        )

    assert not list((tmp_path / "out").glob("fixture-v1"))
    assert not list((tmp_path / "out").glob(".fixture-v1.tmp-*"))


def test_exporter_atomic_directory_switch_cleans_temp_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_exporter()

    def fail_replace(_source: object, _destination: object) -> None:
        raise OSError("injected replace failure")

    monkeypatch.setattr(module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="injected replace failure"):
        module.export_candidate(
            _options(module, tmp_path / "out"), FakeBirdClient(_routes())
        )

    assert not (tmp_path / "out" / "fixture-v1").exists()
    assert not list((tmp_path / "out").glob(".fixture-v1.tmp-*"))


def test_exporter_rejects_path_symlink_timeout_and_shell_risks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_exporter()

    with pytest.raises(module.ExportError, match="unsafe relative path"):
        module._safe_relative_path("../evil.cidr")

    output_root = tmp_path / "out"
    original_is_symlink = Path.is_symlink

    def simulated_is_symlink(path: Path) -> bool:
        return path == output_root or original_is_symlink(path)

    monkeypatch.setattr(Path, "is_symlink", simulated_is_symlink)
    with pytest.raises(module.ExportError, match="refusing symlinked output path"):
        module.export_candidate(
            _options(module, output_root), FakeBirdClient(_routes())
        )

    exporter = _read(EXPORTER)
    assert "shell=True" not in exporter
    assert "subprocess.Popen(" in exporter
    assert "TimeoutExpired" in exporter
    assert "_read_bounded_process_output" in exporter


def test_bird_client_rejects_output_above_byte_limit_without_full_buffering(
    tmp_path: Path,
) -> None:
    module = _load_exporter()
    fake_birdc = tmp_path / "fake_birdc.py"
    fake_birdc.write_text(
        "import sys\nsys.stdout.buffer.write(b'x' * 4097)\nsys.stdout.flush()\n",
        encoding="utf-8",
    )
    client = module.BirdClient(
        Path(sys.executable),
        fake_birdc,
        timeout_seconds=5,
        max_output_bytes=4096,
    )

    with pytest.raises(module.ExportError, match="birdc output exceeds 4096 bytes"):
        client.run("show protocols all antifilter_v4")


def test_exporter_requires_complete_ipv6_when_policy_is_enabled(tmp_path: Path) -> None:
    module = _load_exporter()
    routes = _routes()
    for index, community in enumerate(REQUIRED_COMMUNITIES[:-1], start=1):
        routes[(6, community)] = (
            f"Table antifilter6:\n2001:4860:{index:x}::/48 unicast [antifilter_v6]\n"
        )

    options = module.ExportOptions(
        **{
            **_options(module, tmp_path / "out").__dict__,
            "ipv6_policy": "enabled",
            "ipv6_policy_reason": "Equivalent IPv6 feed is explicitly enabled for this test fixture.",
        }
    )
    with pytest.raises(
        module.ExportError, match="required community 65444:65444 has no IPv6 routes"
    ):
        module.export_candidate(options, FakeBirdClient(routes))

    routes[(6, REQUIRED_COMMUNITIES[-1])] = (
        "Table antifilter6:\n2001:4860:ff::/48 unicast [antifilter_v6]\n"
    )
    source_path = module.export_candidate(options, FakeBirdClient(routes))
    manifest = _json(source_path)
    assert len(manifest["files"]) == len(REQUIRED_COMMUNITIES) * 2
    assert {item["family"] for item in manifest["files"]} == {4, 6}
    assert manifest["ipv6Policy"]["mode"] == "enabled"


def test_bird_client_protocol_state_parser_and_command_contract() -> None:
    module = _load_exporter()
    output = (
        "BIRD 2.0.12 ready.\n"
        "BGP state:          Established\n"
        "Channel ipv4\n"
        "  State:          UP\n"
    )
    assert module._channel_is_up(output, "ipv4")
    assert not module._channel_is_up(output, "ipv6")

    source = _read(EXPORTER)
    assert "show protocols all {protocol}" in source
    assert "show route table {table} where ({asn},{value}) ~ bgp_community" in source


def test_candidate_files_are_root_owned_by_role_and_not_auto_published() -> None:
    deploy = _read(DEPLOY)
    service = _read(SERVICE_TEMPLATE)
    verify = _read(VERIFY)

    assert "Antifilter BGP collector | Ensure root-owned directories exist" in deploy
    assert "owner: root" in deploy
    assert "group: root" in deploy
    assert 'mode: "0755"' in deploy
    assert "systemd_service:" in deploy
    assert "state: started" in deploy
    assert "show protocols all {{ antifilter_bgp_collector_protocol_ipv4 }}" in verify
    assert "source.json" not in service
    assert "compile" not in service
    assert "publish" not in service


def test_bird_configuration_is_readable_after_bird_drops_privileges() -> None:
    deploy = _read(DEPLOY)
    task = deploy.split(
        "- name: Antifilter BGP collector | Render BIRD2 read-only BGP configuration",
        maxsplit=1,
    )[1].split("\n- name:", maxsplit=1)[0]

    assert "owner: root" in task
    assert "group: bird" in task
    assert 'mode: "0640"' in task
    assert 'mode: "0600"' not in task


def test_exporter_does_not_leave_candidate_when_destination_already_exists(
    tmp_path: Path,
) -> None:
    module = _load_exporter()
    output_root = tmp_path / "out"
    existing = output_root / "fixture-v1"
    existing.mkdir(parents=True)
    (existing / "source.json").write_text("existing\n", encoding="utf-8")

    with pytest.raises(module.ExportError, match="candidate already exists"):
        module.export_candidate(
            _options(module, output_root), FakeBirdClient(_routes())
        )

    assert (existing / "source.json").read_text(encoding="utf-8") == "existing\n"
    assert not list(output_root.glob(".fixture-v1.tmp-*"))


def test_exporter_main_reports_rejected_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    module = _load_exporter()
    missing = tmp_path / "missing-birdc"

    status = module.main(
        [
            "--birdc",
            str(missing),
            "--socket",
            "/run/bird/bird.ctl",
            "--output-root",
            str(tmp_path / "out"),
            "--ipv6-policy-reason",
            IPV6_DISABLED_REASON,
            "--generated-at",
            "2026-07-11T00:00:00Z",
        ]
    )

    captured = capsys.readouterr()
    assert status == 1
    assert '"status": "rejected"' in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_failed_export_does_not_modify_unrelated_existing_candidate(
    tmp_path: Path,
) -> None:
    module = _load_exporter()
    output_root = tmp_path / "out"
    stable = output_root / "stable-v1"
    stable.mkdir(parents=True)
    (stable / "source.json").write_text("stable\n", encoding="utf-8")
    routes = _routes()
    routes[(4, REQUIRED_COMMUNITIES[0])] = "Table antifilter4:\n"

    with pytest.raises(module.ExportError):
        module.export_candidate(
            _options(module, output_root, source_version="new-v1"),
            FakeBirdClient(routes),
        )

    assert (stable / "source.json").read_text(encoding="utf-8") == "stable\n"
    assert not (output_root / "new-v1").exists()


def test_exporter_outputs_only_ascii_cidr_files(tmp_path: Path) -> None:
    module = _load_exporter()
    source_path = module.export_candidate(
        _options(module, tmp_path / "out"), FakeBirdClient(_routes())
    )

    for item in _json(source_path)["files"]:
        route_path = source_path.parent / item["path"]
        content = route_path.read_bytes()
        assert content.decode("ascii").encode("ascii") == content
        assert all(
            line and "#" not in line and "," not in line and " " not in line
            for line in content.decode("ascii").splitlines()
        )


def test_test_fixture_cleanup_proves_atomic_directory_not_move_copy(
    tmp_path: Path,
) -> None:
    module = _load_exporter()
    source_path = module.export_candidate(
        _options(module, tmp_path / "out"), FakeBirdClient(_routes())
    )
    copied = tmp_path / "copy"
    shutil.copytree(source_path.parent, copied)

    assert (copied / "source.json").read_bytes() == source_path.read_bytes()
    assert not any(
        path.name.startswith(".fixture-v1.tmp-")
        for path in (tmp_path / "out").iterdir()
    )
