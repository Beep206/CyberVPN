from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
COLLECTOR_PATH = (
    "/api/v1/admin/vpn-tester/internal/task2/route-evidence/xray-routing-webhook"
)
RUNTIME_AGENT_PATH = "/internal/v2/runtime-checks"
OPERATOR_EVIDENCE_HEADER = "X-CyberVPN-Task2-Operator-Evidence-Ingress"
OPERATOR_EVIDENCE_PUBLIC_KEY_PATH = (
    "/run/cybervpn/readiness/task2/runtime-evidence-public-key.pem"
)
OPERATOR_EVIDENCE_ENV_DEFAULTS = {
    "VPN_TESTER_TASK2_OPERATOR_EVIDENCE_ENABLED": "${VPN_TESTER_TASK2_OPERATOR_EVIDENCE_ENABLED:-false}",
    "VPN_TESTER_TASK2_OPERATOR_EVIDENCE_PUBLIC_KEY_PATH": OPERATOR_EVIDENCE_PUBLIC_KEY_PATH,
    "VPN_TESTER_TASK2_OPERATOR_EVIDENCE_KEY_ID": "${VPN_TESTER_TASK2_OPERATOR_EVIDENCE_KEY_ID:-}",
    "VPN_TESTER_TASK2_OPERATOR_EVIDENCE_REVOKED_KEY_IDS": "${VPN_TESTER_TASK2_OPERATOR_EVIDENCE_REVOKED_KEY_IDS:-}",
    "VPN_TESTER_TASK2_OPERATOR_EVIDENCE_BACKEND_IMAGE_ID": "${VPN_TESTER_TASK2_OPERATOR_EVIDENCE_BACKEND_IMAGE_ID:-}",
    "VPN_TESTER_TASK2_OPERATOR_EVIDENCE_AGENT_GIT_SHA": "${VPN_TESTER_TASK2_OPERATOR_EVIDENCE_AGENT_GIT_SHA:-}",
    "VPN_TESTER_TASK2_OPERATOR_EVIDENCE_AGENT_IMAGE_REF": "${VPN_TESTER_TASK2_OPERATOR_EVIDENCE_AGENT_IMAGE_REF:-}",
    "VPN_TESTER_TASK2_OPERATOR_EVIDENCE_AGENT_IMAGE_ID": "${VPN_TESTER_TASK2_OPERATOR_EVIDENCE_AGENT_IMAGE_ID:-}",
    "VPN_TESTER_TASK2_OPERATOR_EVIDENCE_MAX_SKEW_SECONDS": "${VPN_TESTER_TASK2_OPERATOR_EVIDENCE_MAX_SKEW_SECONDS:-60}",
    "VPN_TESTER_TASK2_OPERATOR_EVIDENCE_MAX_VALIDITY_SECONDS": "${VPN_TESTER_TASK2_OPERATOR_EVIDENCE_MAX_VALIDITY_SECONDS:-900}",
    "VPN_TESTER_TASK2_OPERATOR_EVIDENCE_MAX_FAULT_SECONDS": "${VPN_TESTER_TASK2_OPERATOR_EVIDENCE_MAX_FAULT_SECONDS:-240}",
    "VPN_TESTER_TASK2_OPERATOR_EVIDENCE_MAX_BODY_BYTES": "${VPN_TESTER_TASK2_OPERATOR_EVIDENCE_MAX_BODY_BYTES:-65536}",
}


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _backend_proxy_block(caddy: str) -> str:
    return caddy.split("(backend_proxy) {", 1)[1].split("\n}", 1)[0]


def _backend_reverse_proxy_blocks(caddy: str, upstream: str) -> list[str]:
    blocks: list[str] = []
    lines = caddy.splitlines()
    for index, line in enumerate(lines):
        if "reverse_proxy" not in line or upstream not in line:
            continue
        if not line.rstrip().endswith("{"):
            continue

        depth = line.count("{") - line.count("}")
        block = [line]
        for nested in lines[index + 1 :]:
            block.append(nested)
            depth += nested.count("{") - nested.count("}")
            if depth == 0:
                break
        blocks.append("\n".join(block))
    return blocks


def test_task2_evidence_caddy_site_is_dedicated_and_spb_source_restricted() -> None:
    caddy = _read("infra/deploy/stage1/Caddyfile.edge-stage1.production")

    assert "https://task2-evidence.cyber-vpn.org {" in caddy
    public_site = caddy.split("https://task2-evidence.cyber-vpn.org {", 1)[1].split(
        "\n}", 1
    )[0]
    assert 'respond "Not found" 404' in public_site
    assert COLLECTOR_PATH not in public_site
    assert "reverse_proxy" not in public_site

    assert "https://task2-evidence.cyber-vpn.org:9445 {" in caddy
    site = caddy.split("https://task2-evidence.cyber-vpn.org:9445 {", 1)[1].split(
        "\n}", 1
    )[0]
    assert COLLECTOR_PATH in site
    assert "remote_ip 172.30.0.1" in site
    assert "IPv6 userland proxy" in site
    assert "reverse_proxy cybervpn-stage1-cybervpn-backend-1:8000" in site
    assert "header_up X-CyberVPN-Task2-Evidence-Ingress spb-source-verified-v1" in site
    assert 'respond "Not found" 404' in site
    assert "import stage1_api_routes" not in site
    assert "@remnawave_subscription" not in site

    app_caddy = _read("infra/deploy/stage1/Caddyfile.stage1.snippet")
    shared_api_routes = app_caddy.split("(stage1_api_routes)", 1)[1].split(
        "cyber-vpn.net {", 1
    )[0]
    assert "task2-evidence.cyber-vpn.org" not in app_caddy
    assert COLLECTOR_PATH in shared_api_routes
    assert "@task2_route_evidence_private path " + COLLECTOR_PATH in shared_api_routes
    assert 'respond @task2_route_evidence_private "Not found" 404' in shared_api_routes
    assert "header_up -X-CyberVPN-Task2-Evidence-Ingress" in shared_api_routes
    assert f"header_up -{OPERATOR_EVIDENCE_HEADER}" in shared_api_routes


def test_task2_operator_evidence_public_backend_proxies_strip_ingress_marker() -> None:
    edge_caddy = _read("infra/deploy/stage1/Caddyfile.edge-stage1.production")
    backend_proxy = _backend_proxy_block(edge_caddy)
    dedicated_task2 = edge_caddy.split(
        "https://task2-evidence.cyber-vpn.org:9445 {",
        1,
    )[1].split(
        "https://vpn-test-spb.cyber-vpn.org",
        1,
    )[0]

    assert f"header_up -{OPERATOR_EVIDENCE_HEADER}" in backend_proxy
    assert f"header_up -{OPERATOR_EVIDENCE_HEADER}" in dedicated_task2
    edge_backend_proxies = _backend_reverse_proxy_blocks(
        edge_caddy, "cybervpn-stage1-cybervpn-backend-1:8000"
    )
    assert len(edge_backend_proxies) == 3
    for proxy in edge_backend_proxies:
        assert (
            f"header_up -{OPERATOR_EVIDENCE_HEADER}" in proxy
            or "header_up -X-CyberVPN-*" in proxy
        )

    assert f"header_up {OPERATOR_EVIDENCE_HEADER} " not in edge_caddy
    assert edge_caddy.count(OPERATOR_EVIDENCE_HEADER) == 2
    assert "task2-operator-evidence.cyber-vpn" not in edge_caddy.lower()

    stage1_caddy = _read("infra/deploy/stage1/Caddyfile.stage1.snippet")
    stage1_backend_proxies = _backend_reverse_proxy_blocks(
        stage1_caddy, "cybervpn-backend:8000"
    )
    assert len(stage1_backend_proxies) == 2
    for proxy in stage1_backend_proxies:
        assert (
            f"header_up -{OPERATOR_EVIDENCE_HEADER}" in proxy
            or "header_up -X-CyberVPN-*" in proxy
        )

    assert f"header_up {OPERATOR_EVIDENCE_HEADER} " not in stage1_caddy
    assert stage1_caddy.count(OPERATOR_EVIDENCE_HEADER) == 1
    assert "task2-operator-evidence.cyber-vpn" not in stage1_caddy.lower()


def test_task2_evidence_host_firewall_restricts_dedicated_ipv6_before_docker() -> None:
    rules = _read("infra/nftables/cybervpn-task2-evidence-ingress.nft")
    unit = _read("infra/systemd/cybervpn-task2-evidence-firewall.service")

    assert "table inet cybervpn_task2_evidence_ingress" in rules
    assert "type filter hook input priority -10; policy accept;" in rules
    assert (
        "ip6 daddr 2a0d:2787:1b:12f5::a ip6 saddr 2a01:e5c0:1368::3 "
        "tcp dport 9445 counter accept"
    ) in rules
    assert ("ip6 daddr 2a0d:2787:1b:12f5::a tcp dport 9445 counter drop") in rules
    assert "Before=docker.service" in unit
    assert (
        "ExecStartPre=/usr/sbin/nft -c -f /etc/nftables.d/cybervpn-task2-evidence-ingress.nft"
        in unit
    )
    assert (
        "ExecStartPre=-/usr/sbin/nft delete table inet cybervpn_task2_evidence_ingress"
        in unit
    )
    assert (
        "ExecStart=/usr/sbin/nft -f /etc/nftables.d/cybervpn-task2-evidence-ingress.nft"
        in unit
    )
    assert "After=network-online.target ufw.service" in unit
    assert (
        "ExecStartPost=/usr/sbin/ufw allow proto tcp from 2a01:e5c0:1368::3 "
        "to 2a0d:2787:1b:12f5::a port 9445"
    ) in unit
    assert (
        "ExecStop=-/usr/sbin/ufw --force delete allow proto tcp from 2a01:e5c0:1368::3 "
        "to 2a0d:2787:1b:12f5::a port 9445"
    ) in unit
    assert "ReadWritePaths=/etc/ufw /lib/ufw /run" in unit


def test_task2_evidence_compose_and_vault_env_defaults_are_disabled_or_empty() -> None:
    compose = yaml.safe_load(_read("infra/deploy/stage1/docker-compose.stage1.yml"))
    backend_env = compose["services"]["cybervpn-backend"]["environment"]
    vault = yaml.safe_load(
        _read(
            "infra/ansible/inventories/production/group_vars/control_plane_production/vault.yml.example"
        )
    )

    assert (
        backend_env["VPN_TESTER_TASK2_ROUTE_EVIDENCE_ENABLED"]
        == "${VPN_TESTER_TASK2_ROUTE_EVIDENCE_ENABLED:-false}"
    )
    assert (
        backend_env["VPN_TESTER_TASK2_XRAY_WEBHOOK_SECRET"]
        == "${VPN_TESTER_TASK2_XRAY_WEBHOOK_SECRET:-}"
    )
    assert (
        backend_env["VPN_TESTER_TASK2_SYNTHETIC_USER"]
        == "${VPN_TESTER_TASK2_SYNTHETIC_USER:-}"
    )
    assert (
        backend_env["VPN_TESTER_TASK2_SYNTHETIC_XRAY_EMAIL"]
        == "${VPN_TESTER_TASK2_SYNTHETIC_XRAY_EMAIL:-}"
    )

    caddy_ports = compose["services"]["cybervpn-caddy"]["ports"]
    assert "[2a0d:2787:1b:12f5::a]:9445:9445/tcp" not in caddy_ports

    env_extra = vault["vault_control_plane_backend_env_extra"]
    assert env_extra == {
        "VPN_TESTER_TASK2_ROUTE_EVIDENCE_ENABLED": "false",
        "VPN_TESTER_TASK2_XRAY_WEBHOOK_SECRET": "",
        "VPN_TESTER_TASK2_SYNTHETIC_USER": "",
        "VPN_TESTER_TASK2_SYNTHETIC_XRAY_EMAIL": "",
    }


def test_task2_operator_evidence_compose_uses_public_key_mount_and_fail_closed_defaults() -> (
    None
):
    compose = yaml.safe_load(_read("infra/deploy/stage1/docker-compose.stage1.yml"))
    backend = compose["services"]["cybervpn-backend"]
    backend_env = backend["environment"]

    for key, expected in OPERATOR_EVIDENCE_ENV_DEFAULTS.items():
        assert backend_env[key] == expected

    assert (
        "${CYBERVPN_READINESS_DIR:-/srv/cybervpn/readiness}/task2:"
        "/run/cybervpn/readiness/task2:ro"
    ) in backend["volumes"]
    assert OPERATOR_EVIDENCE_PUBLIC_KEY_PATH.startswith(
        "/run/cybervpn/readiness/task2/"
    )
    assert OPERATOR_EVIDENCE_PUBLIC_KEY_PATH.endswith("runtime-evidence-public-key.pem")
    assert "VPN_TESTER_TASK2_OPERATOR_EVIDENCE_PRIVATE_KEY" not in backend_env
    assert "VPN_TESTER_TASK2_OPERATOR_EVIDENCE_PRIVATE_KEY_PATH" not in backend_env
    assert "VPN_TESTER_TASK2_OPERATOR_EVIDENCE_SIGNING_KEY" not in backend_env


def test_task2_evidence_dns_example_is_dns_only_origin_not_subscription_host() -> None:
    example = _read("infra/terraform/live/production/dns/terraform.tfvars.example")

    assert example.count('name         = "task2-evidence.cyber-vpn.org"') == 1
    assert example.count('name         = "spb-exceptions.cyber-vpn.org"') == 1
    record = example.split("task2-evidence-origin-ipv6 = {", 1)[1].split("}", 1)[0]
    assert 'content      = "2a0d:2787:1b:12f5::a"' in record
    assert 'record_class = "vpn-node"' in record
    assert 'type         = "AAAA"' in record
    assert "ttl          = 300" in record
    assert "proxied      = false" in record
    assert "193.233.91.99" not in record
    assert "45.87.41.146" not in record


def test_spb_runtime_agent_caddy_site_is_internal_and_source_restricted() -> None:
    caddy = _read("infra/deploy/stage1/Caddyfile.stage1.snippet")

    assert "vpn-test-spb.cyber-vpn.org {" in caddy
    site = caddy.split("vpn-test-spb.cyber-vpn.org {", 1)[1].split("\n}", 1)[0]

    assert f"path {RUNTIME_AGENT_PATH}" in site
    assert "method POST" in site
    assert 'query ""' in site
    assert "remote_ip 172.30.3.0/24" in site
    assert "private_ranges" not in site
    assert "reverse_proxy cybervpn-vpn-test-agent-spb-target:8080" in site
    assert "header_up -Forwarded" in site
    assert "header_up -X-Forwarded-For" in site
    assert "header_up -X-Forwarded-Host" in site
    assert "header_up -X-Forwarded-Proto" in site
    assert "header_up -X-Real-IP" in site
    assert "header_up -X-Original-*" in site
    assert "header_up -X-CyberVPN-*" in site
    assert "header_up -X-VPN-Test-Agent-Secret" in site
    assert "header_up -Authorization" in site
    assert "header_up -Proxy-Authorization" in site
    assert "header_up -Cookie" in site
    assert 'respond "Not found" 404' in site
    assert "import stage1_api_routes" not in site
    assert COLLECTOR_PATH not in site


def test_regional_runtime_agent_dns_examples_are_distinct_dns_only_origins() -> None:
    example = _read("infra/terraform/live/production/dns/terraform.tfvars.example")

    assert example.count('name         = "vpn-test-moscow.cyber-vpn.org"') == 1
    assert example.count('name         = "vpn-test-spb.cyber-vpn.org"') == 1
    moscow = example.split("vpn-test-moscow-agent-ipv4 = {", 1)[1].split("}", 1)[0]
    spb = example.split("vpn-test-spb-agent-ipv4 = {", 1)[1].split("}", 1)[0]
    assert 'content      = "193.233.91.99"' in moscow
    assert 'content      = "45.87.41.146"' in spb
    for record in (moscow, spb):
        assert 'record_class = "vpn-node"' in record
        assert 'type         = "A"' in record
        assert "ttl          = 300" in record
        assert "proxied      = false" in record


def test_spb_runtime_agent_compose_is_internal_proxy_only_and_role_scoped() -> None:
    compose = yaml.safe_load(
        _read("infra/deploy/stage1/docker-compose.vpn-test-agent-spb.yml")
    )
    service = compose["services"]["cybervpn-vpn-test-agent-spb-target"]

    assert service["environment"]["VPN_TEST_AGENT_ROLE"] == "spb"
    assert service["environment"]["VPN_TEST_AGENT_LEGACY_V1_ENABLED"] == "false"
    assert service["environment"]["VPN_TEST_AGENT_PROXY_ONLY_ENABLED"] == "true"
    assert service["environment"]["VPN_TEST_AGENT_TUN_ENABLED"] == "false"
    assert service["env_file"] == [
        "${CYBERVPN_SPB_AGENT_ENV_FILE:-/srv/cybervpn/secrets/vpn-test-agent-spb.env}"
    ]
    assert set(service["networks"]) == {"cybervpn-backend", "cybervpn-egress"}
    assert "ports" not in service
    assert "expose" not in service
    assert service["read_only"] is True
    assert service["cap_drop"] == ["ALL"]
    assert service["security_opt"] == ["no-new-privileges:true"]

    stage1 = yaml.safe_load(_read("infra/deploy/stage1/docker-compose.stage1.yml"))
    caddy_network = stage1["services"]["cybervpn-caddy"]["networks"]
    assert caddy_network["cybervpn-backend"]["aliases"] == [
        "vpn-test-spb.cyber-vpn.org"
    ]
    backend_network = stage1["networks"]["cybervpn-backend"]
    assert backend_network["internal"] is True
    assert backend_network["ipam"]["config"] == [
        {
            "subnet": "${CYBERVPN_STAGE1_BACKEND_SUBNET:-172.30.3.0/24}",
            "gateway": "${CYBERVPN_STAGE1_BACKEND_GATEWAY:-172.30.3.1}",
        }
    ]
