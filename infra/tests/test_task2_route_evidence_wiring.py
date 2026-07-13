from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
COLLECTOR_PATH = "/api/v1/admin/vpn-tester/internal/task2/route-evidence/xray-routing-webhook"


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_task2_evidence_caddy_site_is_dedicated_and_spb_source_restricted() -> None:
    caddy = _read("infra/deploy/stage1/Caddyfile.stage1.snippet")

    assert "task2-evidence.cyber-vpn.org {" in caddy
    site = caddy.split("task2-evidence.cyber-vpn.org {", 1)[1].split("\n}", 1)[0]
    shared_api_routes = caddy.split("(stage1_api_routes)", 1)[1].split("cyber-vpn.net {", 1)[0]

    assert COLLECTOR_PATH in site
    assert "remote_ip 193.233.91.99" in site
    assert "reverse_proxy cybervpn-backend:8000" in site
    assert "header_up -X-CyberVPN-Task2-Evidence-Ingress" in site
    assert "header_up X-CyberVPN-Task2-Evidence-Ingress spb-source-verified-v1" in site
    assert 'respond "Not found" 404' in site
    assert "import stage1_api_routes" not in site
    assert "@remnawave_subscription" not in site
    assert COLLECTOR_PATH in shared_api_routes
    assert '@task2_route_evidence_private path ' + COLLECTOR_PATH in shared_api_routes
    assert 'respond @task2_route_evidence_private "Not found" 404' in shared_api_routes
    assert "header_up -X-CyberVPN-Task2-Evidence-Ingress" in shared_api_routes


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

    env_extra = vault["vault_control_plane_backend_env_extra"]
    assert env_extra == {
        "VPN_TESTER_TASK2_ROUTE_EVIDENCE_ENABLED": "false",
        "VPN_TESTER_TASK2_XRAY_WEBHOOK_SECRET": "",
        "VPN_TESTER_TASK2_SYNTHETIC_USER": "",
    }


def test_task2_evidence_dns_example_is_dns_only_origin_not_subscription_host() -> None:
    example = _read("infra/terraform/live/production/dns/terraform.tfvars.example")

    assert example.count('name         = "task2-evidence.cyber-vpn.org"') == 1
    assert example.count('name         = "spb-exceptions.cyber-vpn.org"') == 1
    record = example.split("task2-evidence-origin-ipv4 = {", 1)[1].split("}", 1)[0]
    assert 'content      = "45.87.41.146"' in record
    assert 'record_class = "vpn-node"' in record
    assert 'type         = "A"' in record
    assert "ttl          = 300" in record
    assert "proxied      = false" in record
    assert "193.233.91.99" not in record
