# ruff: noqa: S101

"""Static deploy-contract tests for the Task2 route-evidence rollout path."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEPLOY_SCRIPT = ROOT / "scripts" / "deploy" / "stage1-gitlab-deploy.sh"
SPB_COMPOSE = (
    ROOT / "infra" / "deploy" / "stage1" / "docker-compose.vpn-test-agent-spb.yml"
)
EDGE_CADDYFILE = (
    ROOT / "infra" / "deploy" / "stage1" / "Caddyfile.edge-stage1.production"
)
STAGE1_CADDYFILE = ROOT / "infra" / "deploy" / "stage1" / "Caddyfile.stage1.snippet"
OPERATOR_EVIDENCE_HEADER = "X-CyberVPN-Task2-Operator-Evidence-Ingress"


def _script() -> str:
    return DEPLOY_SCRIPT.read_text(encoding="utf-8")


def _spb_compose() -> str:
    return SPB_COMPOSE.read_text(encoding="utf-8")


def _edge_caddyfile() -> str:
    return EDGE_CADDYFILE.read_text(encoding="utf-8")


def _stage1_caddyfile() -> str:
    return STAGE1_CADDYFILE.read_text(encoding="utf-8")


def _between(content: str, start: str, end: str) -> str:
    assert start in content, f"missing start marker: {start}"
    assert end in content, f"missing end marker: {end}"
    return content.split(start, 1)[1].split(end, 1)[0]


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


def _assert_in_order(content: str, *markers: str) -> None:
    positions = [content.index(marker) for marker in markers]
    assert positions == sorted(positions), markers


def test_task2_route_evidence_target_and_runtime_archive_are_explicit() -> None:
    script = _script()

    assert "task2-route-evidence" in script
    assert "validate_optional_absolute_remote_path STAGE1_CADDYFILE_PATH" in script
    assert "validate_optional_absolute_remote_path STAGE1_CADDY_CONFIG_DIR" in script
    assert "validate_optional_absolute_remote_path STAGE1_SPB_AGENT_ENV_FILE" in script
    assert "validate_optional_absolute_remote_path STAGE1_SPB_COMPOSE_DIR" in script
    assert "validate_optional_absolute_remote_path STAGE1_SPB_COMPOSE_FILE" in script
    assert "validate_optional_absolute_remote_path STAGE1_EDGE_COMPOSE_DIR" in script
    assert "validate_optional_absolute_remote_path STAGE1_EDGE_COMPOSE_FILE" in script
    assert "validate_optional_absolute_remote_path STAGE1_EDGE_CADDYFILE_PATH" in script
    assert "task2_requested=false" in script
    assert "Task2 runtime archive artifact must be tracked" in script
    assert 'git ls-files --error-unmatch "$artifact"' in script

    for path in (
        "infra/deploy/stage1/Caddyfile.edge-stage1.production",
        "infra/deploy/stage1/docker-compose.vpn-test-agent-spb.yml",
        "infra/nftables/cybervpn-task2-evidence-ingress.nft",
        "infra/systemd/cybervpn-task2-evidence-firewall.service",
        "scripts/deploy/stage1-gitlab-deploy.sh",
    ):
        assert path in script

    runtime_archive = _between(
        script,
        'elif [[ "$source_sync_mode" == "runtime-archive" ]]; then',
        'else\n  log "syncing source without secrets/heavy build artifacts"',
    )
    assert "infra\\/deploy\\/stage1" in runtime_archive
    assert "infra\\/nftables\\/cybervpn-task2-evidence-ingress\\.nft" in runtime_archive
    assert (
        "infra\\/systemd\\/cybervpn-task2-evidence-firewall\\.service"
        in runtime_archive
    )
    assert "scripts\\/deploy\\/stage1-gitlab-deploy\\.sh" in runtime_archive


def test_all_preserves_an_explicit_task2_route_evidence_request() -> None:
    selection = _between(
        _script(),
        '[[ ${#requested[@]} -gt 0 ]] || fail "no valid services requested"',
        'services_csv="$(IFS=,; echo "${!requested[*]}")"',
    )
    capture_index = selection.index("task2_requested=false")
    all_index = selection.index('if [[ -n "${requested[all]:-}" ]]; then')
    assert capture_index < all_index

    all_expansion = selection[all_index:]
    assert 'if [[ "$task2_requested" == "true" ]]; then' in all_expansion
    assert "requested[task2-route-evidence]=1" in all_expansion


def test_task2_edge_caddy_artifact_matches_production_edge_shape() -> None:
    caddy = _edge_caddyfile()

    assert "https://task2-evidence.cyber-vpn.org:9445 {" in caddy
    assert "https://vpn-test-spb.cyber-vpn.org {" in caddy
    assert "reverse_proxy cybervpn-stage1-cybervpn-backend-1:8000" in caddy
    assert "header_up X-CyberVPN-Task2-Evidence-Ingress spb-source-verified-v1" in caddy
    assert "remote_ip 172.30.0.1" in caddy
    assert "remote_ip 172.30.3.0/24" in caddy
    assert "reverse_proxy cybervpn-vpn-test-agent-spb-target:8080" in caddy
    assert "cybervpn-backend:8000" not in caddy


def test_task2_operator_evidence_is_not_publicly_exposed_by_stage1_or_edge_caddy() -> None:
    edge_caddy = _edge_caddyfile()
    backend_proxy = _between(
        edge_caddy, "(backend_proxy) {", "\n}\n\n(product_subscription_gateway)"
    )
    dedicated_task2 = _between(
        edge_caddy,
        "https://task2-evidence.cyber-vpn.org:9445 {",
        "\n}\n\nhttps://vpn-test-spb.cyber-vpn.org",
    )

    assert "header_up -X-CyberVPN-*" in backend_proxy
    assert "request_header -X-CyberVPN-Task2-Evidence-Ingress" in dedicated_task2
    assert f"request_header -{OPERATOR_EVIDENCE_HEADER}" in dedicated_task2
    assert "request_header -X-CyberVPN-Task2-Xray-Webhook-Secret" not in dedicated_task2
    assert "request_header -X-CyberVPN-*" not in dedicated_task2
    assert "header_up -X-CyberVPN-*" not in dedicated_task2
    edge_backend_proxies = _backend_reverse_proxy_blocks(
        edge_caddy, "cybervpn-stage1-cybervpn-backend-1:8000"
    )
    assert len(edge_backend_proxies) == 3
    assert sum("header_up -X-CyberVPN-*" in proxy for proxy in edge_backend_proxies) == 2

    assert f"header_up {OPERATOR_EVIDENCE_HEADER} " not in edge_caddy
    assert edge_caddy.count(OPERATOR_EVIDENCE_HEADER) == 1
    assert "task2-operator-evidence.cyber-vpn" not in edge_caddy.lower()

    stage1_caddy = _stage1_caddyfile()
    stage1_backend_proxies = _backend_reverse_proxy_blocks(
        stage1_caddy, "cybervpn-backend:8000"
    )
    assert len(stage1_backend_proxies) == 2
    for proxy in stage1_backend_proxies:
        assert "header_up -X-CyberVPN-*" in proxy

    assert f"header_up {OPERATOR_EVIDENCE_HEADER} " not in stage1_caddy
    assert OPERATOR_EVIDENCE_HEADER not in stage1_caddy
    assert "task2-operator-evidence.cyber-vpn" not in stage1_caddy.lower()


def test_manual_dry_run_branch_exits_before_remote_mutation() -> None:
    script = _script()
    dry_run = _between(
        script,
        'if [[ "$deploy_dry_run" == "true" ]]; then',
        "ssh_key_file=",
    )

    assert "dry-run.invalid" in script
    assert (
        "No SSH, rsync, Docker build, compose restart or public smoke was executed."
        in dry_run
    )
    assert 'cat "$evidence_file"' in dry_run
    assert "exit 0" in dry_run
    for forbidden in (
        "ssh_cmd",
        "rsync -az",
        "docker build",
        "docker compose",
        "systemctl",
    ):
        assert forbidden not in dry_run


def test_task2_deploy_sequence_gates_before_caddy_exposure() -> None:
    script = _script()
    deploy = _between(
        script, "deploy_task2_route_evidence_surface() {", "\n}\n\nimage_for()"
    )

    _assert_in_order(
        deploy,
        "require_stage1_backend_network_contract",
        "require_task2_evidence_config_if_enabled",
        "require_spb_compose_contract",
        "require_spb_sidecar_secret_env",
        "require_edge_caddy_contract",
        "capture_task2_spb_sidecar_state",
        "install_task2_route_evidence_files",
        "start_task2_firewall",
        "start_task2_spb_sidecar",
        "recreate_caddy_for_task2_evidence",
    )

    install = _between(
        script,
        "install_task2_route_evidence_files() {",
        "\n}\n\nstart_task2_firewall()",
    )
    _assert_in_order(
        install,
        "Caddyfile.edge-stage1.production",
        "cybervpn-task2-evidence-ingress.nft",
        "cybervpn-task2-evidence-firewall.service",
        "docker-compose.vpn-test-agent-spb.yml",
    )

    firewall = _between(
        script, "start_task2_firewall() {", "\n}\n\nstart_task2_spb_sidecar()"
    )
    assert "systemctl daemon-reload" in firewall
    assert 'systemctl enable --now "$task2_firewall_unit"' in firewall
    assert 'systemctl is-active --quiet "$task2_firewall_unit"' in firewall

    caddy = _between(
        script, "recreate_caddy_for_task2_evidence() {", "\n}\n\ndeploy_task2"
    )
    assert (
        'edge_compose up -d --no-deps --force-recreate "$EDGE_CADDY_SERVICE"' in caddy
    )
    assert "task2-edge-caddy-validate" in caddy
    assert "task2-edge-caddy-task2-deny" in caddy
    assert "cybervpn-caddy" not in caddy


def test_task2_uses_real_edge_compose_and_refuses_app_caddy_service() -> None:
    script = _script()
    edge = _between(
        script,
        "require_edge_caddy_contract() {",
        "\n}\n\nrequire_spb_sidecar_secret_env()",
    )
    rollback = _between(
        script, "rollback_task2_files() {", "\n}\n\nrollback_task2_on_error()"
    )

    assert "/srv/cybervpn/compose/edge" in script
    assert "/srv/cybervpn/compose/edge/docker-compose.yml" in script
    assert "/srv/cybervpn/edge/caddy/Caddyfile" in script
    assert "EDGE_CADDY_SERVICE='$edge_caddy_service'" in script
    assert 'EDGE_CADDY_SERVICE" = "caddy"' in edge
    assert "refusing to use app Caddy service name cybervpn-caddy" in edge
    assert '"[2a0d:2787:1b:12f5::a]:9445:9445/tcp"' in edge
    assert "/srv/cybervpn/edge/caddy/Caddyfile:/etc/caddy/Caddyfile:ro" in edge
    assert "docker network inspect cybervpn-edge" in edge
    assert "172.30.0.0/24 | 172.30.0.1" in edge
    assert "Task2 Caddy source matcher" in edge
    assert "edge_compose config --format json" in edge
    assert "Task2 evidence requires exactly one 9445 publish" in edge
    assert "Task2 evidence 9445 publish is not bound exclusively" in edge
    assert 'edge_compose ps -q "$EDGE_CADDY_SERVICE"' in edge
    assert 'docker compose -f "$EDGE_COMPOSE_FILE"' in script
    assert "docker compose up -d --no-deps cybervpn-caddy" not in script
    assert (
        'docker compose -f "$EDGE_COMPOSE_FILE" up -d --no-deps --force-recreate "$EDGE_CADDY_SERVICE"'
        in rollback
    )


def test_task2_edge_publish_validator_rejects_an_additional_broad_publish(
    tmp_path: Path,
) -> None:
    validator = _between(
        _script(),
        'python3 - "$edge_config_file" "$EDGE_CADDY_SERVICE" <<\'PY\'\n',
        "\nPY\n",
    )
    expected = {
        "mode": "ingress",
        "host_ip": "2a0d:2787:1b:12f5::a",
        "target": 9445,
        "published": "9445",
        "protocol": "tcp",
    }
    good_config = {"services": {"caddy": {"ports": [expected]}}}
    unsafe_config = {
        "services": {
            "caddy": {"ports": [expected]},
            "other": {
                "ports": [
                    {
                        "mode": "ingress",
                        "host_ip": "0.0.0.0",
                        "target": 9445,
                        "published": "9445",
                        "protocol": "tcp",
                    }
                ]
            },
        }
    }

    good_path = tmp_path / "good.json"
    unsafe_path = tmp_path / "unsafe.json"
    good_path.write_text(json.dumps(good_config), encoding="utf-8")
    unsafe_path.write_text(json.dumps(unsafe_config), encoding="utf-8")

    good = subprocess.run(
        [sys.executable, "-c", validator, str(good_path), "caddy"],
        capture_output=True,
        text=True,
        check=False,
    )
    unsafe = subprocess.run(
        [sys.executable, "-c", validator, str(unsafe_path), "caddy"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert good.returncode == 0, good.stderr
    assert unsafe.returncode != 0
    assert "exactly one 9445 publish" in unsafe.stderr


def test_task2_evidence_enabled_requires_complete_fail_closed_config() -> None:
    script = _script()
    config = _between(
        script,
        "require_task2_evidence_config_if_enabled() {",
        "\n}\n\nensure_backend_device_cookie_pepper()",
    )

    assert "Task2 route evidence remains disabled" in config
    for key in (
        "VPN_TESTER_ENABLED",
        "VPN_TESTER_RUNTIME_ENABLED",
        "VPN_TESTER_SYNTHETIC_USERS_ENABLED",
        "VPN_TEST_AGENT_SPB_URL",
        "VPN_TEST_AGENT_SPB_SECRET",
        "VPN_TESTER_TASK2_XRAY_WEBHOOK_SECRET",
        "VPN_TESTER_TASK2_SYNTHETIC_USER",
        "VPN_TESTER_TASK2_SYNTHETIC_XRAY_EMAIL",
    ):
        assert key in config

    remote_env_updates = _between(
        script,
        "ensure_remote_env_value .env VPN_TESTER_ENABLED true",
        "ensure_remote_env_value .env VPN_TESTER_SCHEDULED_ENABLED true",
    )
    assert (
        "preserving runtime and synthetic-user switches for validation"
        in remote_env_updates
    )
    assert "VPN_TESTER_RUNTIME_ENABLED false" in remote_env_updates
    assert "VPN_TESTER_SYNTHETIC_USERS_ENABLED false" in remote_env_updates


def test_task2_backend_network_is_inspected_not_recreated() -> None:
    script = _script()
    network = _between(
        script,
        "require_stage1_backend_network_contract() {",
        "\n}\n\ntask2_spb_compose()",
    )

    assert "cybervpn_stage1_backend" in network
    assert "172.30.3.0/24" in network
    assert "172.30.3.1" in network
    assert 'docker network inspect "$stage1_backend_network"' in network
    assert "refusing unsafe recreation" in network

    forbidden = (
        "docker network create",
        "docker network rm",
        "docker compose down",
        "docker volume rm",
        "docker system prune",
    )
    for marker in forbidden:
        assert marker not in network
        assert marker not in script


def test_task2_spb_sidecar_uses_same_tag_and_preexisting_secret_file() -> None:
    script = _script()
    compose = _spb_compose()
    sidecar_with_image = _between(
        script,
        "task2_spb_compose_with_image() {",
        "\n}\n\ntask2_spb_compose()",
    )
    sidecar = _between(
        script, "task2_spb_compose() {", "\n}\n\ncapture_task2_spb_sidecar_state()"
    )
    capture = _between(
        script,
        "capture_task2_spb_sidecar_state() {",
        "\n}\n\nrequire_spb_compose_contract()",
    )
    contract = _between(
        script,
        "require_spb_compose_contract() {",
        "\n}\n\nedge_compose()",
    )
    secret = _between(
        script,
        "require_spb_sidecar_secret_env() {",
        "\n}\n\ninstall_task2_route_evidence_files()",
    )
    start = _between(
        script,
        "start_task2_spb_sidecar() {",
        "\n}\n\nrecreate_caddy_for_task2_evidence()",
    )

    assert 'CYBERVPN_IMAGE_TAG="$tag"' in sidecar_with_image
    assert (
        'CYBERVPN_SPB_AGENT_ENV_FILE="$task2_spb_agent_env_file"' in sidecar_with_image
    )
    assert 'cd "$SPB_COMPOSE_DIR"' in sidecar_with_image
    assert 'docker compose -f "$SPB_COMPOSE_FILE"' in sidecar_with_image
    assert 'task2_spb_compose_with_image "$IMAGE_REGISTRY" "$RELEASE_TAG"' in sidecar
    assert "/srv/cybervpn/compose/vpn-test-agent-spb" in contract
    assert "/srv/cybervpn/compose/vpn-test-agent-spb/docker-compose.yml" in contract
    assert 'docker inspect "$container" --format' in capture
    assert 'test -s "$task2_spb_agent_env_file"' in secret
    assert "VPN_TEST_AGENT_SECRET" in secret
    assert "placeholder VPN_TEST_AGENT_SECRET" in secret
    assert (
        'backend_spb_secret="$(remote_env_value "$COMPOSE_DIR/.env" VPN_TEST_AGENT_SPB_SECRET || true)"'
        in secret
    )
    assert (
        "VPN_TEST_AGENT_SPB_SECRET must match SPB sidecar VPN_TEST_AGENT_SECRET"
        in secret
    )
    assert 'docker image inspect "$agent_image"' in start
    assert "task2_spb_compose config --quiet" in start
    assert "task2_spb_compose up -d --force-recreate" in start
    assert "task2-spb-agent-health" in start

    for marker in (
        "VPN_TEST_AGENT_ROLE: spb",
        'VPN_TEST_AGENT_PROXY_ONLY_ENABLED: "true"',
        'VPN_TEST_AGENT_TUN_ENABLED: "false"',
        'VPN_TEST_AGENT_LEGACY_V1_ENABLED: "false"',
        "read_only: true",
        "cap_drop:",
        "- ALL",
    ):
        assert marker in compose
    assert "ports:" not in compose
    assert "expose:" not in compose

    for leaking_fragment in (
        'cat "$task2_spb_agent_env_file"',
        'tee -a "$task2_spb_agent_env_file"',
        "env |",
        "set -x",
    ):
        assert leaking_fragment not in sidecar_with_image
        assert leaking_fragment not in sidecar
        assert leaking_fragment not in capture
        assert leaking_fragment not in secret
        assert leaking_fragment not in start


def test_task2_backups_rollback_and_bounded_smoke_are_present() -> None:
    script = _script()
    backup = _between(script, "backup_remote_file() {", "\n}\n\ninstall_remote_file")
    rollback = _between(
        script, "rollback_task2_files() {", "\n}\n\nrollback_task2_on_error()"
    )
    retry = _between(script, "retry_curl() {", "\n}\n\nis_requested()")

    assert 'printf \'%s|%s\\n\' "$path" "$backup" >>"$task2_backup_manifest"' in backup
    assert 'cp -a "$path" "$backup"' in backup
    assert "trap rollback_task2_on_error ERR" in script
    assert "rolling back Task2 route evidence files" in rollback
    assert "stopping Task2 SPB sidecar" in rollback
    assert "task2_spb_compose stop cybervpn-vpn-test-agent-spb-target" in rollback
    assert "task2_spb_compose rm -f -s cybervpn-vpn-test-agent-spb-target" in rollback
    assert "restoring previous Task2 SPB sidecar image" in rollback
    assert (
        'task2_spb_compose_with_image "$task2_spb_previous_registry" "$task2_spb_previous_tag"'
        in rollback
    )
    assert "reloading Caddy with restored Task2 route evidence config" in rollback
    assert (
        'docker compose -f "$EDGE_COMPOSE_FILE" up -d --no-deps --force-recreate "$EDGE_CADDY_SERVICE"'
        in rollback
    )
    assert 'systemctl stop "$task2_firewall_unit"' in rollback
    assert 'systemctl disable "$task2_firewall_unit"' in rollback
    assert 'max_attempts="${STAGE1_DEPLOY_SMOKE_ATTEMPTS:-30}"' in retry
    assert 'sleep_seconds="${STAGE1_DEPLOY_SMOKE_SLEEP_SECONDS:-2}"' in retry
    assert "STAGE1_DEPLOY_SMOKE_ATTEMPTS must be between 1 and 60" in retry
    assert "STAGE1_DEPLOY_SMOKE_SLEEP_SECONDS must be between 1 and 10" in retry
    assert 'while [ "$attempt" -le "$max_attempts" ]; do' in retry
    assert "while true" not in retry


def test_task2_rollback_remains_armed_until_remote_deploy_smokes_finish() -> None:
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    surface = _between(
        script, "deploy_task2_route_evidence_surface() {", "\n}\n\nimage_for()"
    )

    assert "task2_deploy_completed=true" not in surface
    assert "task2_deploy_active=false" not in surface

    completion_index = script.index(
        "task2_deploy_completed=true", script.index("REMOTE_SCRIPT")
    )
    agent_smoke_index = script.index("retry_curl vpn-test-agent-health")
    deployment_complete_index = script.index('log "deployment complete"')
    assert agent_smoke_index < completion_index < deployment_complete_index


def test_task2_only_target_does_not_start_all_compose_services_by_accident() -> None:
    script = _script()

    main_compose = _between(
        script,
        "if task2_route_evidence_requested; then",
        "if is_requested backend; then",
    )
    assert 'if [ "${#compose_services[@]}" -gt 0 ]; then' in main_compose
    assert 'docker compose up -d "${compose_services[@]}"' in main_compose
    assert "no primary compose services requested" in main_compose
