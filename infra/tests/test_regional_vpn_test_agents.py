# ruff: noqa: S101

"""Deployment contract for optional regional VPN test agents."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INFRA_ROOT = REPO_ROOT / "infra"
AGENT_DOCKERFILE = REPO_ROOT / "services" / "vpn-test-agent" / "Dockerfile"

STAGE1_COMPOSE = INFRA_ROOT / "deploy" / "stage1" / "docker-compose.stage1.yml"
LOCAL_COMPOSE = INFRA_ROOT / "docker-compose.yml"
INFRA_ENV_EXAMPLE = INFRA_ROOT / ".env.example"

CONTROL_PLANE_DEFAULTS = (
    INFRA_ROOT / "ansible" / "roles" / "control_plane_stack" / "defaults" / "main.yml"
)
CONTROL_PLANE_VALIDATE = (
    INFRA_ROOT / "ansible" / "roles" / "control_plane_stack" / "tasks" / "validate.yml"
)
PRODUCTION_CONTROL_PLANE = (
    INFRA_ROOT
    / "ansible"
    / "inventories"
    / "production"
    / "group_vars"
    / "control_plane_production"
    / "main.yml"
)
STAGING_CONTROL_PLANE = (
    INFRA_ROOT
    / "ansible"
    / "inventories"
    / "staging"
    / "group_vars"
    / "control_plane_staging"
    / "main.yml"
)
PRODUCTION_VAULT_EXAMPLE = (
    INFRA_ROOT
    / "ansible"
    / "inventories"
    / "production"
    / "group_vars"
    / "control_plane_production"
    / "vault.yml.example"
)
STAGING_VAULT_EXAMPLE = (
    INFRA_ROOT
    / "ansible"
    / "inventories"
    / "staging"
    / "group_vars"
    / "control_plane_staging"
    / "vault.yml.example"
)

REGION_ROLE = INFRA_ROOT / "ansible" / "roles" / "vpn_test_agent_region"
REGION_DEFAULTS = REGION_ROLE / "defaults" / "main.yml"
REGION_VALIDATE = REGION_ROLE / "tasks" / "validate.yml"
REGION_DEPLOY = REGION_ROLE / "tasks" / "deploy.yml"
REGION_VERIFY = REGION_ROLE / "tasks" / "verify.yml"
REGION_COMPOSE_TEMPLATE = REGION_ROLE / "templates" / "docker-compose.yml.j2"
REGION_NFTABLES_TEMPLATE = REGION_ROLE / "templates" / "nftables.conf.j2"
REGION_FIREWALL_UNIT_TEMPLATE = REGION_ROLE / "templates" / "firewall.service.j2"
REGION_EXAMPLE = (
    INFRA_ROOT / "ansible" / "examples" / "vpn-test-agent-region-vars.yml.example"
)
RELAY_ROLE = INFRA_ROOT / "ansible" / "roles" / "vpn_test_agent_relay"
RELAY_DEFAULTS = RELAY_ROLE / "defaults" / "main.yml"
RELAY_TASKS = RELAY_ROLE / "tasks" / "main.yml"
RELAY_TEMPLATE = RELAY_ROLE / "templates" / "relay.service.j2"
RELAY_PLAYBOOK = (
    INFRA_ROOT / "ansible" / "playbooks" / "vpn-test-agent-relay-rollout.yml"
)
RELAY_EXAMPLE = (
    INFRA_ROOT / "ansible" / "examples" / "vpn-test-agent-relay-vars.yml.example"
)

REGIONAL_ENV_KEYS = (
    "VPN_TEST_AGENT_MOSCOW_URL",
    "VPN_TEST_AGENT_MOSCOW_SECRET",
    "VPN_TEST_AGENT_SPB_URL",
    "VPN_TEST_AGENT_SPB_SECRET",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _stage1_service(compose: str, service: str) -> str:
    match = re.search(
        rf"\n  {re.escape(service)}:\n(?P<body>.*?)(?=\n  [A-Za-z0-9_-]+:\n|\nnetworks:)",
        f"\n{compose}",
        flags=re.S,
    )
    assert match is not None, f"missing stage1 service {service}"
    return match.group("body")


def test_no_legacy_ru_agent_names_remain_in_infra() -> None:
    legacy_prefix = "VPN_TEST_AGENT_" + "RU"
    for path in INFRA_ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if path.suffix in {".png", ".crt", ".db", ".sqlite"}:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        assert legacy_prefix not in content, str(path)


def test_stage1_backend_worker_scheduler_receive_optional_regional_env() -> None:
    compose = _read(STAGE1_COMPOSE)

    for service_name in ("cybervpn-backend", "cybervpn-worker", "cybervpn-scheduler"):
        service = _stage1_service(compose, service_name)
        for key in REGIONAL_ENV_KEYS:
            assert f"{key}: ${{{key}:-}}" in service

    assert (
        "VPN_TEST_AGENT_URL: ${VPN_TEST_AGENT_URL:-http://cybervpn-vpn-test-agent:8080}"
        in compose
    )
    assert "  cybervpn-vpn-test-agent:\n" in compose
    agent_service = _stage1_service(compose, "cybervpn-vpn-test-agent")
    assert "app.env" not in agent_service
    assert "sentry-runtime.env" not in agent_service
    assert "VPN_TEST_AGENT_SECRET: ${VPN_TEST_AGENT_SECRET:-}" in agent_service
    assert "VPN_TEST_AGENT_ROLE: primary" in agent_service
    assert (
        "VPN_TEST_AGENT_LEGACY_V1_ENABLED: ${VPN_TEST_AGENT_LEGACY_V1_ENABLED:-false}"
        in agent_service
    )
    assert (
        "VPN_TEST_AGENT_LEGACY_V1_SECRET: ${VPN_TEST_AGENT_LEGACY_V1_SECRET:-}"
        in agent_service
    )
    assert "replace-before-live-vpn-test-agent" not in compose
    assert "read_only: true" in agent_service
    assert "cap_drop:" in agent_service
    assert "- ALL" in agent_service


def test_local_worker_scheduler_receive_optional_regional_env() -> None:
    compose = _read(LOCAL_COMPOSE)

    for key in REGIONAL_ENV_KEYS:
        assert compose.count(f"- {key}=${{{key}:-}}") == 2


def test_control_plane_ansible_env_uses_empty_urls_and_secret_references() -> None:
    defaults = _read(CONTROL_PLANE_DEFAULTS)
    assert 'control_plane_stack_vpn_test_agent_url: ""' in defaults
    assert 'control_plane_stack_vpn_test_agent_moscow_url: ""' in defaults
    assert 'control_plane_stack_vpn_test_agent_spb_url: ""' in defaults

    for path in (PRODUCTION_CONTROL_PLANE, STAGING_CONTROL_PLANE):
        inventory = _read(path)
        assert 'control_plane_stack_vpn_test_agent_url: ""' in inventory
        assert 'control_plane_stack_vpn_test_agent_moscow_url: ""' in inventory
        assert 'control_plane_stack_vpn_test_agent_spb_url: ""' in inventory
        assert inventory.count("'VPN_TEST_AGENT_URL':") == 2
        assert inventory.count("'VPN_TEST_AGENT_SECRET':") == 2
        assert inventory.count("'VPN_TEST_AGENT_MOSCOW_URL':") == 2
        assert inventory.count("'VPN_TEST_AGENT_MOSCOW_SECRET':") == 2
        assert inventory.count("'VPN_TEST_AGENT_SPB_URL':") == 2
        assert inventory.count("'VPN_TEST_AGENT_SPB_SECRET':") == 2
        assert "vault_control_plane_vpn_test_agent_secret | default('')" in inventory
        assert (
            "vault_control_plane_vpn_test_agent_moscow_secret | default('')"
            in inventory
        )
        assert (
            "vault_control_plane_vpn_test_agent_spb_secret | default('')" in inventory
        )

    validation = _read(
        INFRA_ROOT
        / "ansible"
        / "roles"
        / "control_plane_stack"
        / "tasks"
        / "validate.yml"
    )
    assert "^http://cybervpn-vpn-test-agent(?::[0-9]+)?/?$" in validation
    assert "VPN_TEST_AGENT_MOSCOW_URL is match('^https://[A-Za-z0-9.-]+" in validation
    assert "VPN_TEST_AGENT_SPB_URL is match('^https://[A-Za-z0-9.-]+" in validation

    for path in (PRODUCTION_VAULT_EXAMPLE, STAGING_VAULT_EXAMPLE):
        vault_example = _read(path)
        assert 'vault_control_plane_vpn_test_agent_secret: ""' in vault_example
        assert 'vault_control_plane_vpn_test_agent_moscow_secret: ""' in vault_example
        assert 'vault_control_plane_vpn_test_agent_spb_secret: ""' in vault_example


def test_env_example_documents_logical_target_to_physical_agent_mapping() -> None:
    env_example = _read(INFRA_ENV_EXAMPLE)

    assert (
        "Logical Moscow-target checks should call the physically SPB agent."
        in env_example
    )
    assert (
        "Logical SPB-target checks should call the physically Moscow agent."
        in env_example
    )
    for key in REGIONAL_ENV_KEYS:
        assert f"{key}=" in env_example


def test_regional_role_is_generic_disabled_by_default_and_firewall_guarded() -> None:
    defaults = _read(REGION_DEFAULTS)
    validate = _read(REGION_VALIDATE)
    deploy = _read(REGION_DEPLOY)
    verify = _read(REGION_VERIFY)
    compose_template = _read(REGION_COMPOSE_TEMPLATE)
    nftables_template = _read(REGION_NFTABLES_TEMPLATE)
    firewall_unit_template = _read(REGION_FIREWALL_UNIT_TEMPLATE)
    example = _read(REGION_EXAMPLE)

    assert "vpn_test_agent_region_enabled: false" in defaults
    assert "vpn_test_agent_region_name:" in defaults
    assert 'vpn_test_agent_region_role: "{{ vpn_test_agent_region_name }}"' in defaults
    assert 'VPN_TEST_AGENT_ROLE: "{{ vpn_test_agent_region_role }}"' in defaults
    assert "vpn_test_agent_region_legacy_v1_enabled: false" in defaults
    assert 'vpn_test_agent_region_legacy_v1_secret: ""' in defaults
    assert "VPN_TEST_AGENT_LEGACY_V1_ENABLED:" in defaults
    assert "VPN_TEST_AGENT_LEGACY_V1_SECRET:" in defaults
    assert 'vpn_test_agent_region_tls_server_name: ""' in defaults
    assert 'vpn_test_agent_region_tls_cert_pem: ""' in defaults
    assert 'vpn_test_agent_region_tls_key_pem: ""' in defaults

    compose_template = _read(REGION_COMPOSE_TEMPLATE)
    assert "--ssl-certfile" in compose_template
    assert "--ssl-keyfile" in compose_template
    assert "https://{{ vpn_test_agent_region_tls_server_name }}:" in compose_template
    assert ":{{ vpn_test_agent_region_tls_container_key_path }}:ro" in compose_template
    assert "vpn_test_agent_region_physical_region:" in defaults
    assert "vpn_test_agent_region_target_region:" in defaults
    assert "vpn_test_agent_region_port: 18080" in defaults
    assert "45.87.41.146/32" in defaults
    assert "vpn_test_agent_region_required_source_ipv4_cidr" in validate
    assert "vpn_test_agent_region_required_source_ipv6_cidr" in validate
    assert "in ['', '45.87.41.146/32']" in validate
    assert "in ['', '2a0d:2787:1b:12f5::a/128']" in validate
    assert "(['45.87.41.146/32'] if" in validate
    assert "(['2a0d:2787:1b:12f5::a/128'] if" in validate
    assert "| length == 1" in validate
    assert "/32$" in validate
    assert "/128$" in validate
    assert "vpn_test_agent_region_manage_nftables | bool" in validate
    assert "BEGIN CERTIFICATE" in validate
    assert "~ 'PRIVATE' ~ ' KEY-----'" in validate
    assert "vpn_test_agent_region_legacy_v1_secret | lower" in validate
    assert "@sha256:[0-9a-f]{64}$" in validate
    assert "@sha256:0{64}$" in validate

    assert "network_mode: host" in compose_template
    assert 'user: "10001:10001"' in compose_template
    assert "ports:" not in compose_template
    assert "--port" in compose_template
    assert "vpn_test_agent_region_port" in compose_template
    assert "cap_drop:" in compose_template
    assert "read_only: true" in compose_template
    assert "nft" in deploy
    assert "-c" in deploy
    assert "-f" in deploy
    assert "/etc/nftables.conf" not in deploy
    assert "vpn_test_agent_region_firewall_unit_name" in deploy
    assert "community.general.ufw" in deploy
    assert "vpn_test_agent_region_manage_ufw" in deploy
    assert "from_ip:" in deploy
    assert "to_port:" in deploy
    assert 'mode: "0440"' in deploy
    assert 'group: "10001"' in deploy
    assert deploy.count("no_log: true") >= 3
    assert "NetworkSettings.Ports | length == 0" in verify
    assert "Config.User == '10001:10001'" in verify
    assert "health.json.agent_role == vpn_test_agent_region_role" in verify
    assert "health.json.legacy_v1_enabled" in verify

    assert "ip saddr @allowed_ipv4 accept" in nftables_template
    assert "ip6 saddr @allowed_ipv6 accept" in nftables_template
    assert (
        "tcp dport {{ vpn_test_agent_region_port }} counter drop" in nftables_template
    )
    assert "ExecStartPre=-/usr/sbin/nft delete table inet" in firewall_unit_template
    assert "ExecStart=/usr/sbin/nft -f" in firewall_unit_template
    assert "45.87.41.146/32" in example
    assert "vpn_test_agent_region_enabled: false" in example
    assert "vpn_test_agent_region_enabled: true" not in example
    assert "vpn_test_agent_region_name: moscow" in example
    assert "vpn_test_agent_region_physical_region: spb" in example
    assert "vpn_test_agent_region_target_region: moscow" in example
    assert "vpn_test_agent_region_name: spb" in example
    assert "vpn_test_agent_region_physical_region: moscow" in example
    assert "vpn_test_agent_region_target_region: spb" in example

    dockerfile = _read(AGENT_DOCKERFILE)
    assert "addgroup -S -g 10001 vpnagent" in dockerfile
    assert "adduser -S -u 10001" in dockerfile


def test_ipv6_relay_is_bridge_only_hardened_and_opt_in() -> None:
    defaults = _read(RELAY_DEFAULTS)
    tasks = _read(RELAY_TASKS)
    template = _read(RELAY_TEMPLATE)
    playbook = _read(RELAY_PLAYBOOK)
    example = _read(RELAY_EXAMPLE)

    assert "vpn_test_agent_relay_enabled: false" in defaults
    assert "community.general.ufw" in tasks
    assert "vpn_test_agent_relay_allowed_source_ipv4_cidr" in tasks
    assert "0.0.0.0/0" in tasks
    assert "192\\.168" in tasks
    assert "(?:2[4-9]|3[0-2])" in tasks
    assert "vpn_test_agent_relay_required_source_ipv4_cidr" not in tasks
    assert "== '172.30.2.0/24'" in tasks
    assert "vpn_test_agent_relay_listen_ipv4" in tasks
    assert "status_code: 200" in tasks
    assert "DynamicUser=yes" in template
    assert "NoNewPrivileges=yes" in template
    assert "ProtectSystem=strict" in template
    assert "RestrictAddressFamilies=AF_INET AF_INET6" in template
    assert "TCP4-LISTEN:" in template
    assert "TCP6:[" in template
    assert "role: vpn_test_agent_relay" in playbook
    assert "vpn_test_agent_relay_listen_ipv4: 172.30.2.1" in example
    assert "vpn_test_agent_relay_allowed_source_ipv4_cidr: 172.30.2.0/24" in example


def test_regional_role_rejects_placeholder_agent_secrets() -> None:
    validate = _read(REGION_VALIDATE)

    for marker in (
        "replace",
        "example",
        "test",
        "placeholder",
        "changeme",
        "dummy",
        "local",
        "development",
        "dev-",
        "redacted",
        "your_",
    ):
        assert marker in validate


def test_control_plane_rejects_partial_or_placeholder_agent_configuration() -> None:
    validate = _read(CONTROL_PLANE_VALIDATE)

    for key in (
        "VPN_TEST_AGENT_URL",
        "VPN_TEST_AGENT_SECRET",
        "VPN_TEST_AGENT_MOSCOW_URL",
        "VPN_TEST_AGENT_MOSCOW_SECRET",
        "VPN_TEST_AGENT_SPB_URL",
        "VPN_TEST_AGENT_SPB_SECRET",
    ):
        assert key in validate
    assert "VPN_TESTER_RUNTIME_ENABLED" in validate
    assert "vpn_test_agent_placeholder_pattern" in validate
    assert "control_plane_stack_worker_env" in validate
    assert "control_plane_stack_effective_scheduler_env" in validate
