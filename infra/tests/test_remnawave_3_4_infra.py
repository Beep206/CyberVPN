from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


INFRA_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = INFRA_ROOT.parent

BACKEND_DIGEST = (
    "sha256:4ea85b2fc16bd3e5d367b61afc07ec219133eaa12dd7b5e898adc33c84515422"
)
NODE_DIGEST = "sha256:0cdf386dd49f360fc885bb34bde21132e478e40f0deac62d616086ec0fa9257e"
SUBPAGE_DIGEST = (
    "sha256:04e8d479afb3598024e4018e9e15cd7fe879938250090a690ba39f1ee91b79ac"
)
BACKEND_COMMIT = "f8ad8ad3410252215ca7b2e429d157bd275ec564"
FRONTEND_COMMIT = "c2c9ba3b476e4914a3b17e8ce677ab9255e1c02f"
NODE_COMMIT = "44912631321664dbd5822e9bf8d96766ccff7c93"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_custom_backend_is_rebuilt_from_pinned_3_4_3_typescript_source() -> None:
    dockerfile = _read(INFRA_ROOT / "remnawave-backend-compat" / "Dockerfile")
    patcher = _read(
        INFRA_ROOT / "remnawave-backend-compat" / "patch-xray-config-validator.mjs"
    )

    assert "REMNAWAVE_BACKEND_VERSION=3.4.3" in dockerfile
    assert f"REMNAWAVE_BACKEND_COMMIT={BACKEND_COMMIT}" in dockerfile
    assert f"REMNAWAVE_FRONTEND_COMMIT={FRONTEND_COMMIT}" in dockerfile
    assert f"remnawave/backend:3.4.3@{BACKEND_DIGEST}" in dockerfile
    assert "verify-upstream-3.4.3-regressions.mjs" in dockerfile
    assert "__RW_METADATA_GIT_FRONTEND_COMMIT}" in dockerfile
    assert "src/common/helpers/xray-config/xray-config.validator.ts" in dockerfile
    assert "npx --no-install oxfmt --check" in dockerfile
    assert "src/common/helpers/xray-config/xray-config.validator.ts" in dockerfile
    assert "npm run lint" in dockerfile
    assert "npm run build" in dockerfile
    assert "COPY --from=patched-backend-build" in dockerfile
    assert "/opt/app/dist/src/common/helpers" not in dockerfile

    assert "email: user.id.toString()," in patcher
    assert "user.tId" not in patcher
    assert "delete inbound.settings.flow;" in patcher
    assert "...(vlessFlow ? { flow: vlessFlow } : {})" in patcher


def test_node_mirror_verifies_exact_3_4_1_source_and_runtime_dependencies() -> None:
    dockerfile = _read(INFRA_ROOT / "remnawave-node-mirror" / "Dockerfile")
    verifier = _read(INFRA_ROOT / "remnawave-node-mirror" / "verify-upstream-3.4.1.mjs")

    assert "REMNAWAVE_NODE_VERSION=3.4.1" in dockerfile
    assert f"REMNAWAVE_NODE_COMMIT={NODE_COMMIT}" in dockerfile
    assert f"remnawave/node:3.4.1@{NODE_DIGEST}" in dockerfile
    assert "verify-upstream-3.4.1.mjs" in dockerfile
    assert "/opt/app/dist/node_modules/zod/package.json" in dockerfile
    assert (
        "/opt/app/dist/node_modules/@remnawave/node-plugins/package.json" in dockerfile
    )
    assert 'bundle.includes("zod/compile")' in dockerfile
    assert 'bundle.includes("this.nodeVersion=\\"3.4.1\\"")' in dockerfile

    assert "packageJson.dependencies?.zod !== '4.5.4'" in verifier
    assert "node-plugins must be 0.8.2" in verifier
    assert "import 'zod/compile';" in verifier
    assert (
        "const addUserMethod = extractMethod(handler, 'public async addUser(')"
        in verifier
    )
    assert "new DropConnectionsEvent(userIps)" in verifier
    assert "capture/remove/drop/re-add credential sequence" in verifier


def test_edge_role_accepts_only_digest_pinned_node_3_4_1() -> None:
    validator = _read(
        INFRA_ROOT / "ansible" / "roles" / "remnawave_edge" / "tasks" / "validate.yml"
    )

    assert "^remnawave/node:3\\\\.4\\\\.1@sha256:[a-f0-9]{64}$" in validator
    assert "^remnawave/node:3\\\\.4\\\\.0@sha256:[a-f0-9]{64}$" not in validator


def test_changelog_ledger_is_atomic_machine_readable_and_exposes_release_gaps() -> None:
    ledger_path = (
        REPO_ROOT
        / "docs"
        / "contracts"
        / "remnawave-2.8.0-to-3.4.3-changelog-ledger.json"
    )
    raw = _read(ledger_path)
    ledger = json.loads(raw)
    records = ledger["records"]

    assert ledger["targets"] == {
        "panel": "3.4.3",
        "backend": "3.4.3",
        "frontend": "3.4.3",
        "node": "3.4.1",
        "subscription_page": "8.0.0",
    }
    release_chain = (
        "2.8.1",
        "3.0.0",
        "3.1.0",
        "3.2.0",
        "3.2.1",
        "3.2.2",
        "3.2.3",
        "3.3.0",
        "3.3.1",
        "3.3.2",
        "3.4.0",
        "3.4.1",
        "3.4.2",
        "3.4.3",
    )
    for component in ("backend", "frontend"):
        observed = tuple(
            dict.fromkeys(
                record["release"]
                for record in records
                if record["component"] == component
            )
        )
        assert observed == release_chain

    node_release_chain = (
        "3.0.0",
        "3.1.0",
        "3.1.1",
        "3.2.0",
        "3.2.1",
        "3.2.2",
        "3.3.0",
        "3.3.1",
        "3.3.2",
        "3.4.0",
        "3.4.1",
    )
    observed_node_chain = tuple(
        dict.fromkeys(
            record["release"] for record in records if record["component"] == "node"
        )
    )
    assert observed_node_chain == node_release_chain
    assert {
        record["release"]
        for record in records
        if record["component"] == "subscription-page"
    } == {"8.0.0"}

    assert ledger["schema_version"] == "1.1.0"
    assert len(records) == 474
    record_ids = [record["id"] for record in records]
    assert len(set(record_ids)) == len(record_ids)
    assert {record["status"] for record in records} == {
        "adopted",
        "not_applicable",
        "gap",
    }
    assert "deferred" not in raw.lower()

    required = {
        "id",
        "component",
        "release",
        "category",
        "summary",
        "status",
        "owners",
        "test_evidence",
        "rollback",
        "rationale",
        "primary_source",
    }
    required_source = {
        "repository",
        "release_url",
        "tag",
        "tag_commit",
        "change_ref",
        "change_url",
    }
    for record in records:
        assert required <= record.keys()
        assert record["component"]
        assert record["release"]
        assert record["category"]
        assert record["summary"]
        assert record["owners"]
        assert record["test_evidence"]
        assert record["rollback"]
        assert record["rationale"]
        assert required_source <= record["primary_source"].keys()
        for key in required_source:
            assert record["primary_source"][key]

    actual_counts: dict[str, dict[str, int]] = {}
    for record in records:
        component_counts = actual_counts.setdefault(
            record["component"],
            {"adopted": 0, "not_applicable": 0, "gap": 0, "total": 0},
        )
        component_counts[record["status"]] += 1
        component_counts["total"] += 1
    actual_counts["total_records"] = len(records)  # type: ignore[assignment]
    assert actual_counts == ledger["counts"]


def test_capability_surface_matrix_is_exhaustive_and_fail_closed() -> None:
    matrix = json.loads(
        _read(
            REPO_ROOT
            / "docs"
            / "contracts"
            / "remnawave-3.4.3-capability-surface-matrix.json"
        )
    )
    required_surfaces = (
        "backend",
        "task_worker",
        "admin",
        "partner",
        "customer_web",
        "miniapp",
        "mobile",
        "desktop",
        "native_panel",
        "node",
        "subscription_page",
    )

    assert matrix["schema_version"] == "1.0.0"
    assert tuple(matrix["required_surfaces"]) == required_surfaces
    assert len(matrix["capabilities"]) == 25
    assert matrix["summary"]["capabilities"] == 25
    assert matrix["summary"]["capabilities_with_gap"] == 25

    capability_ids = [item["id"] for item in matrix["capabilities"]]
    assert len(capability_ids) == len(set(capability_ids))
    assert "node-3.4.1-runtime-dependencies" in capability_ids

    computed: dict[str, dict[str, int]] = {
        surface: {"adopted": 0, "not_applicable": 0, "gap": 0}
        for surface in required_surfaces
    }
    for capability in matrix["capabilities"]:
        assert tuple(capability["surfaces"].keys()) == required_surfaces
        assert capability["sources"]
        assert capability["production_owner"]
        assert capability["production_paths"]
        assert capability["persisted_state_or_side_effect"]
        assert capability["retry_concurrency_contract"]
        assert capability["rollback"]
        for surface, disposition in capability["surfaces"].items():
            assert disposition["disposition"] in computed[surface]
            assert disposition["rbac_tenant_rationale"]
            assert disposition["tests"]
            computed[surface][disposition["disposition"]] += 1

    assert computed == matrix["summary"]["surface_dispositions"]
    assert set(matrix["summary"]["gap_capability_ids"]) == set(capability_ids)


def test_local_image_and_runtime_evidence_cannot_be_mistaken_for_promotion() -> None:
    panel_evidence = json.loads(
        _read(
            REPO_ROOT
            / "docs"
            / "evidence"
            / "remnawave-3.4.3"
            / "local-image-runtime-verification.json"
        )
    )
    unchanged_artifact_evidence = json.loads(
        _read(
            REPO_ROOT
            / "docs"
            / "evidence"
            / "remnawave-3.4.2"
            / "local-image-build-verification.json"
        )
    )

    assert panel_evidence["scope"] == "local-build-and-runtime-verification-only"
    assert panel_evidence["promotion_eligible"] is False
    assert len(panel_evidence["promotion_blockers"]) >= 3
    panel = panel_evidence["panel_backend_frontend"]
    assert panel["backend_tag_commit"] == BACKEND_COMMIT
    assert panel["frontend_tag_commit"] == FRONTEND_COMMIT
    assert BACKEND_DIGEST in panel["upstream_image"]
    assert panel["disposable_runtime_smoke"]["health"] == "pass"
    assert (
        panel["disposable_runtime_smoke"]["lowercase_backend_tools_without_auth"] == 403
    )
    assert (
        panel["disposable_runtime_smoke"]["mixed_case_backend_tools_without_auth"]
        == 403
    )
    artifacts = unchanged_artifact_evidence["artifacts"]
    assert artifacts["node"]["source_commit"] == NODE_COMMIT
    assert NODE_DIGEST in artifacts["node"]["upstream_image"]
    assert SUBPAGE_DIGEST in artifacts["subscription_page"]["image"]


def test_local_sboms_bind_exact_images_but_are_not_promotion_attestations() -> None:
    evidence = json.loads(
        _read(
            REPO_ROOT
            / "docs"
            / "evidence"
            / "remnawave-3.4.3"
            / "local-image-runtime-verification.json"
        )
    )
    records = (
        evidence["panel_backend_frontend"]["local_sbom"],
        evidence["node_local_sbom"],
        evidence["subscription_page_local_sbom"],
    )
    for record in records:
        path = REPO_ROOT / record["path"]
        document = json.loads(_read(path))
        assert record["scope"] == "local-image-only-not-registry-attested"
        assert record["format"] == "SPDX-2.3"
        assert document["spdxVersion"] == "SPDX-2.3"
        assert len(document["packages"]) == record["document_packages"]
        assert _sha256(path) == record["sha256"]
        assert record["source_image_digest"] in _read(path)

    scans = (
        evidence["panel_backend_frontend"]["local_scout_quickview"],
        evidence["node_local_sbom"]["local_scout_quickview"],
        evidence["subscription_page_local_sbom"]["local_scout_quickview"],
    )
    for scan in scans:
        assert scan["exit_code"] == 0
        assert scan["owner_disposition"] == "critical_high_non_blocking_but_visible"
        assert set(scan["target"]) == {"critical", "high", "medium", "low", "unknown"}
        assert all(
            isinstance(value, int) and value >= 0 for value in scan["target"].values()
        )

    blockers = " ".join(evidence["promotion_blockers"])
    assert "registry-bound" in blockers
    assert "provenance" in blockers


def test_local_compose_pins_target_versions_and_preserves_data_services() -> None:
    compose = _read(INFRA_ROOT / "docker-compose.yml")

    assert "cybervpn/remnawave-backend:3.4.3-raw-vision-flow.2" in compose
    assert f"remnawave/subscription-page:8.0.0@{SUBPAGE_DIGEST}" in compose
    assert "http://localhost:3010/internal/health" in compose
    assert "postgres:17.10" in compose
    assert "valkey/valkey:8.1.8-alpine" in compose
    assert "REDIS_HOST=remnawave-redis" in _read(INFRA_ROOT / ".env.example")
    assert "REDIS_PORT=6379" in _read(INFRA_ROOT / ".env.example")


def test_stage1_and_ansible_pin_node_and_expose_explicit_safety_flags() -> None:
    stage1_compose = _read(
        INFRA_ROOT / "deploy" / "stage1" / "docker-compose.stage1.yml"
    )
    node_example = _read(
        INFRA_ROOT / "deploy" / "stage1" / "remnawave-node.env.example"
    )
    panel_example = _read(
        INFRA_ROOT / "deploy" / "stage1" / "remnawave-panel.env.example"
    )
    edge_defaults = _read(
        INFRA_ROOT / "ansible" / "roles" / "remnawave_edge" / "defaults" / "main.yml"
    )
    edge_env = _read(
        INFRA_ROOT
        / "ansible"
        / "roles"
        / "remnawave_edge"
        / "templates"
        / "remnanode.env.j2"
    )
    edge_validate = _read(
        INFRA_ROOT / "ansible" / "roles" / "remnawave_edge" / "tasks" / "validate.yml"
    )

    assert f"remnawave/node:3.4.1@{NODE_DIGEST}" in stage1_compose
    assert "FRONT_END_DOMAIN=*" not in panel_example
    assert "FRONT_END_DOMAIN=remnawave.internal.cyber-vpn.net" in panel_example
    assert f"remnawave/node:3.4.1@{NODE_DIGEST}" in edge_defaults
    for key, value in (
        ("SNI_VERIFICATION", "true"),
        ("NFTABLES_LOGGING", "true"),
        ("NFTABLES_ACCEPT_REPLY_TRAFFIC", "false"),
    ):
        assert f"{key}={value}" in node_example
        assert f"{key}=" in edge_env

    assert "remnawave_edge_sni_verification: true" in edge_defaults
    assert "- remnawave_edge_sni_verification" in edge_validate
    assert "remnawave_edge_preupgrade_secret_key_sha256" in edge_defaults
    assert "remnawave_edge_secret_key | length >= 512" in edge_validate
    assert "^[A-Za-z0-9+/]+={0,2}$" in edge_validate
    assert "hash('sha256')" in edge_validate
    assert "Placeholder, weak" in edge_validate
    assert (
        "Reject extra environment overrides of protected safety settings"
        in edge_validate
    )
    assert "item.key not in remnawave_edge_protected_env_keys" in edge_env
    for protected_key in (
        "NODE_PORT",
        "SECRET_KEY",
        "SNI_VERIFICATION",
        "NFTABLES_LOGGING",
        "NFTABLES_ACCEPT_REPLY_TRAFFIC",
    ):
        assert protected_key in edge_validate
        assert protected_key in edge_env
    for environment in ("staging", "production"):
        inventory = _read(
            INFRA_ROOT
            / "ansible"
            / "inventories"
            / environment
            / "group_vars"
            / f"remnawave_edge_{environment}"
            / "main.yml"
        )
        assert "remnawave_edge_sni_verification: true" in inventory

    staging_inventory = _read(
        INFRA_ROOT
        / "ansible"
        / "inventories"
        / "staging"
        / "group_vars"
        / "remnawave_edge_staging"
        / "main.yml"
    )
    production_hosts = _read(
        INFRA_ROOT / "ansible" / "inventories" / "production" / "hosts.yml"
    )
    assert "vault_remnawave_edge_preupgrade_secret_key_sha256" in staging_inventory
    assert production_hosts.count("remnawave_edge_preupgrade_secret_key_sha256") == 4


def test_native_panel_is_loopback_only_and_absent_from_public_caddy_routes() -> None:
    compose = _read(INFRA_ROOT / "deploy" / "stage1" / "docker-compose.stage1.yml")
    panel = compose.split("  cybervpn-remnawave:\n", 1)[1].split(
        "  cybervpn-remnawave-postgres:\n", 1
    )[0]
    defaults = _read(
        INFRA_ROOT
        / "ansible"
        / "roles"
        / "control_plane_stack"
        / "defaults"
        / "main.yml"
    )
    validate = _read(
        INFRA_ROOT
        / "ansible"
        / "roles"
        / "control_plane_stack"
        / "tasks"
        / "validate.yml"
    )
    system_caddy = _read(
        INFRA_ROOT / "deploy" / "stage1" / "Caddyfile.system-stage1.snippet"
    )

    assert '"127.0.0.1:13005:3000"' in panel
    assert '"0.0.0.0:13005:3000"' not in panel
    assert "control_plane_stack_remnawave_bind_host: 127.0.0.1" in defaults
    assert "control_plane_stack_remnawave_bind_host == '127.0.0.1'" in validate
    assert "127.0.0.1:13005" not in system_caddy


def test_panel_env_uses_3_x_names_and_bounded_stream_configuration() -> None:
    env_files = (
        INFRA_ROOT / ".env.example",
        INFRA_ROOT / "deploy" / "stage1" / "remnawave-panel.env.example",
    )
    for path in env_files:
        content = _read(path)
        assert "APP_SECRET=" in content
        assert "JWT_API_TOKENS_SECRET=" not in content
        assert "EXPORT_TO_STREAM_ENABLED=" in content
        assert "EXPORT_TO_STREAM_MAXLEN=3000" in content
        assert "SHORT_UUID_METHOD=nanoid" in content
        assert "SHORT_UUID_LENGTH=16" in content


def test_node_ssh_is_disabled_by_default_and_allowlists_fail_closed() -> None:
    compose = _read(INFRA_ROOT / "deploy" / "stage1" / "docker-compose.stage1.yml")
    env_example = _read(INFRA_ROOT / ".env.example")
    panel_env_example = _read(
        INFRA_ROOT / "deploy" / "stage1" / "remnawave-panel.env.example"
    )
    validate = _read(
        INFRA_ROOT
        / "ansible"
        / "roles"
        / "control_plane_stack"
        / "tasks"
        / "validate.yml"
    )

    for content in (compose, env_example):
        assert "REMNAWAVE_NODE_SSH_ENABLED" in content
        assert "REMNAWAVE_NODE_SSH_TRUSTED_ADMIN_IDS" in content
        assert "REMNAWAVE_NODE_SSH_ALLOWED_NODE_IDS" in content
        assert "REMNAWAVE_NODE_SSH_TICKET_TTL_SECONDS" in content
        assert "REMNAWAVE_NODE_SSH_SESSION_MAX_SECONDS" in content
        assert "REMNAWAVE_NODE_SSH_REVOCATION_POLL_SECONDS" in content
    assert "REMNAWAVE_NODE_SSH_ENABLED=false" in env_example
    assert "REMNAWAVE_NODE_SSH_TRUSTED_ADMIN_IDS=\n" in env_example
    assert "REMNAWAVE_NODE_SSH_ALLOWED_NODE_IDS=\n" in env_example
    assert "REMNAWAVE_NODE_SSH_ENABLED: ${REMNAWAVE_NODE_SSH_ENABLED:-false}" in compose
    assert "CYBERVPN_NODE_SSH_PROXY_IMAGE:?" in compose
    assert (
        "caddy:2.11.4-alpine@"
        not in compose.split("  cybervpn-remnawave-node-ssh-proxy:\n", 1)[1].split(
            "\n  ", 1
        )[0]
    )
    assert "CYBERVPN_NODE_SSH_PROXY_IMAGE=\n" in panel_env_example

    for environment in ("staging", "production"):
        inventory = _read(
            INFRA_ROOT
            / "ansible"
            / "inventories"
            / environment
            / "group_vars"
            / f"control_plane_{environment}"
            / "main.yml"
        )
        assert "control_plane_node_ssh_enabled: false" in inventory
        assert (
            "'REMNAWAVE_NODE_SSH_ENABLED': (control_plane_node_ssh_enabled | bool)"
            in inventory
        )
        assert (
            "'REMNAWAVE_NODE_SSH_BROKER_URL': (control_plane_node_ssh_enabled | bool)"
            in inventory
        )
        assert (
            "vault_control_plane_backend_remnawave_node_ssh_trusted_admin_ids"
            in inventory
        )
        assert (
            "vault_control_plane_backend_remnawave_node_ssh_allowed_node_ids"
            in inventory
        )
        assert "vault_control_plane_backend_passkey_enabled" in inventory
        assert "vault_control_plane_backend_passkey_admin_enabled" in inventory
        assert "CYBERVPN_NODE_SSH_BROKER_TRUSTED_PROXY_RANGES" in inventory

    assert "remnawave_node_ssh_uuid_list_pattern" in validate
    assert "REMNAWAVE_NODE_SSH_TRUSTED_ADMIN_IDS is match" in validate
    assert "REMNAWAVE_NODE_SSH_ALLOWED_NODE_IDS is match" in validate
    assert "PASSKEY_ENABLED | bool" in validate
    assert "PASSKEY_ADMIN_ENABLED | bool" in validate
    assert "REMNAWAVE_NODE_SSH_BROKER_SECRET is match('^[a-f0-9]{128}$')" in validate
    assert "control_plane_stack_node_ssh_proxy_ipv4" in validate

    pattern_match = re.search(
        r"remnawave_node_ssh_uuid_list_pattern: '([^']+)'", validate
    )
    assert pattern_match is not None
    uuid_list_pattern = re.compile(pattern_match.group(1))
    first = "018f0f6d-6688-7c3f-9f1a-7f2d438255a0"
    second = "5d5ddab9-a012-4bde-a5ab-41d7bf09681f"
    assert uuid_list_pattern.fullmatch(first)
    assert uuid_list_pattern.fullmatch(f"{first},{second}")
    assert not uuid_list_pattern.fullmatch("")
    assert not uuid_list_pattern.fullmatch("not-a-uuid")
    assert not uuid_list_pattern.fullmatch(f"{first},")


def test_stage1_worker_uses_dedicated_remnawave_stream_transport() -> None:
    compose = _read(INFRA_ROOT / "deploy" / "stage1" / "docker-compose.stage1.yml")
    worker = compose.split("  cybervpn-worker:\n", 1)[1].split(
        "  cybervpn-scheduler:\n", 1
    )[0]
    scheduler = compose.split("  cybervpn-scheduler:\n", 1)[1].split(
        "  cybervpn-remnawave:\n", 1
    )[0]

    assert "REDIS_URL: ${CYBERVPN_REDIS_URL:-redis://cybervpn-valkey:6379/0}" in worker
    assert (
        "REMNAWAVE_STREAM_REDIS_URL: "
        "${REMNAWAVE_STREAM_REDIS_URL:-redis://cybervpn-remnawave-valkey:6379/0}"
        in worker
    )
    assert (
        "REMNAWAVE_STREAM_CONSUMER_ENABLED: ${REMNAWAVE_STREAM_CONSUMER_ENABLED:-true}"
        in worker
    )
    assert (
        "REMNAWAVE_STREAM_CONSUMER_GROUP: ${REMNAWAVE_STREAM_CONSUMER_GROUP:-cybervpn-remnawave-v1}"
        in worker
    )
    assert (
        "REMNAWAVE_STREAM_IP_HMAC_SECRET: "
        "${REMNAWAVE_STREAM_IP_HMAC_SECRET:?set a dedicated 32-plus-character Remnawave stream IP HMAC secret}"
        in worker
    )
    assert (
        "REMNAWAVE_STREAM_RECEIPT_RETENTION_DAYS: "
        "${REMNAWAVE_STREAM_RECEIPT_RETENTION_DAYS:-14}" in worker
    )
    assert "cybervpn-remnawave-valkey:\n        condition: service_healthy" in worker
    assert "cybervpn-remnawave-data: {}" in worker
    assert "os.environ['REMNAWAVE_STREAM_REDIS_URL']" in worker
    assert 'REMNAWAVE_STREAM_CONSUMER_ENABLED: "false"' in scheduler


def test_ansible_worker_stream_validation_has_no_redis_url_fallback() -> None:
    validate = _read(
        INFRA_ROOT
        / "ansible"
        / "roles"
        / "control_plane_stack"
        / "tasks"
        / "validate.yml"
    )
    for environment in ("staging", "production"):
        inventory = _read(
            INFRA_ROOT
            / "ansible"
            / "inventories"
            / environment
            / "group_vars"
            / f"control_plane_{environment}"
            / "main.yml"
        )
        worker = inventory.split("control_plane_stack_worker_env:", 1)[1].split(
            "control_plane_stack_scheduler_env:", 1
        )[0]
        backend = inventory.split("control_plane_stack_backend_env:", 1)[1].split(
            "control_plane_stack_worker_env:", 1
        )[0]
        assert "'REMNAWAVE_STREAM_CONSUMER_ENABLED': 'true'" in worker
        assert (
            "'REMNAWAVE_STREAM_REDIS_URL': 'redis://remnawave-redis:6379/0'" in worker
        )
        assert "'REMNAWAVE_STREAM_CONSUMER_GROUP': 'cybervpn-remnawave-v1'" in worker
        assert (
            "'REMNAWAVE_STREAM_IP_HMAC_SECRET': "
            "vault_control_plane_backend_remnawave_stream_ip_hmac_secret" in worker
        )
        assert "'REMNAWAVE_STREAM_RECEIPT_RETENTION_DAYS': '14'" in worker
        assert "'REMNAWAVE_STREAM_RECEIPT_RETENTION_DAYS': '14'" in backend
        assert "REMNAWAVE_STREAM_REDIS_URL" not in backend

    assert "REDIS_URL remains the Taskiq/cache" in validate
    assert (
        "control_plane_stack_worker_env.REMNAWAVE_STREAM_REDIS_URL | length > 0"
        in validate
    )
    assert (
        "control_plane_stack_worker_env.REMNAWAVE_STREAM_IP_HMAC_SECRET | length >= 32"
        in validate
    )
    assert (
        "control_plane_stack_worker_env.REMNAWAVE_STREAM_RECEIPT_RETENTION_DAYS | int == 14"
        in validate
    )
    assert (
        "== control_plane_stack_backend_env.REMNAWAVE_STREAM_RECEIPT_RETENTION_DAYS"
        in validate
    )
    assert (
        "control_plane_stack_effective_scheduler_env.REMNAWAVE_STREAM_CONSUMER_ENABLED"
        in validate
    )


def test_environment_release_manifest_requires_custom_remnawave_digest() -> None:
    promote = _read(
        INFRA_ROOT / "ansible" / "scripts" / "promote_control_plane_release.py"
    )
    validate = _read(
        INFRA_ROOT
        / "ansible"
        / "roles"
        / "control_plane_stack"
        / "tasks"
        / "validate.yml"
    )
    staging = _read(
        INFRA_ROOT
        / "ansible"
        / "inventories"
        / "staging"
        / "group_vars"
        / "control_plane_staging"
        / "main.yml"
    )
    makefile = _read(INFRA_ROOT / "Makefile")
    runbook = _read(REPO_ROOT / "docs" / "runbooks" / "REMNAWAVE_3_4_3_UPGRADE.md")
    promotion_runbook = _read(
        REPO_ROOT / "docs" / "runbooks" / "CONTROL_PLANE_RELEASE_PROMOTION_RUNBOOK.md"
    )

    assert '"remnawave": remnawave_image' in promote
    assert '"--remnawave-image"' in promote
    assert '"node": node_image' in promote
    assert '"subscription_page": subscription_page_image' in promote
    assert '"node_ssh_proxy": node_ssh_proxy_image' in promote
    assert '"--evidence-manifest"' in promote
    assert '"control_plane_release_supply_chain"' in promote
    assert "'remnawave': control_plane_stack_remnawave_image" in validate
    assert (
        "control_plane_stack_release_supply_chain.components[item.key].provenance.verified"
        in validate
    )
    assert (
        "control_plane_stack_release_supply_chain.components[item.key].sbom.verified"
        in validate
    )
    assert "control_plane_release_scan.verified" in validate
    assert "control_plane_release_scan.risk_disposition" in validate
    assert "control_plane_release_accepted_risk.components[item.key]" in validate
    assert "control_plane_release_images.remnawave" in staging
    assert "control_plane_release_images.node" in staging
    assert "control_plane_release_images.subscription_page" in staging
    assert "control_plane_release_images.node_ssh_proxy" in staging
    assert makefile.count('test -n "$(NODE_SSH_PROXY_IMAGE)"') == 2
    assert makefile.count('--image "node_ssh_proxy=$(NODE_SSH_PROXY_IMAGE)"') == 2
    assert makefile.count('--node-ssh-proxy-image "$(NODE_SSH_PROXY_IMAGE)"') == 2
    assert (
        makefile.count(
            "$(if $(ACCEPTED_RISK_DECISION),--accepted-risk-decision "
            '"$(ACCEPTED_RISK_DECISION)",)'
        )
        == 2
    )
    assert 'test -n "$(SIGNER_WORKFLOW)"' not in makefile
    assert "all seven CyberVPN release images" in runbook
    assert (
        "NODE_SSH_PROXY_IMAGE=ghcr.io/<owner>/<repo>/node-ssh-proxy@sha256:<digest>"
        in runbook
    )
    assert "All seven release images" in promotion_runbook
    assert "all 21 component/predicate combinations" in promotion_runbook
    assert "node-ssh-proxy" in promotion_runbook
    assert "all seven digests" in promotion_runbook


def test_release_workflow_and_stage_deploy_enforce_remnawave_release_secrets() -> None:
    workflow = _read(REPO_ROOT / ".github" / "workflows" / "control-plane-promote.yml")
    image_workflow = _read(
        REPO_ROOT / ".github" / "workflows" / "control-plane-images.yml"
    )
    attestation_verifier = _read(
        INFRA_ROOT / "ansible" / "scripts" / "verify_control_plane_attestations.py"
    )
    stage_deploy = _read(REPO_ROOT / "scripts" / "deploy" / "stage1-gitlab-deploy.sh")

    assert "release_images_json:" in workflow
    assert (
        "required: true"
        in workflow.split("release_images_json:", 1)[1].split(
            "remnawave_auth_secret_sha256:", 1
        )[0]
    )
    assert '"remnawave": "ghcr.io/beep206/cybervpn/remnawave-backend"' in workflow
    assert "release_images_json must contain exactly all seven components" in workflow
    assert '--remnawave-image "$REMNAWAVE_IMAGE"' in workflow
    assert "contents: write" not in workflow
    assert "git push" not in workflow
    assert "base_ref:" not in workflow
    assert "persist-credentials: false" in workflow
    assert "NODE_IMAGE" in workflow
    assert "SUBSCRIPTION_PAGE_IMAGE" in workflow
    assert "NODE_SSH_PROXY_IMAGE" in workflow
    assert "verify_control_plane_attestations.py" in workflow
    assert "accepted_risk_decision_path:" in workflow
    assert "control-plane-accepted-risks/" in workflow
    assert "--deny-self-hosted-runners" in attestation_verifier
    assert "https://slsa.dev/provenance/v1" in attestation_verifier
    assert "https://spdx.dev/Document/v2.3" in attestation_verifier
    assert (
        "https://cybervpn.dev/attestations/vulnerability-scan/v1"
        in attestation_verifier
    )
    assert "cybervpn-control-plane-supply-chain/v2" in image_workflow
    assert "report_sha256" in image_workflow
    assert "linux/arm64" not in image_workflow
    assert image_workflow.count("platforms: linux/amd64") == 7
    assert '"platforms": os.environ["PLATFORMS"].split(",")' in image_workflow
    assert "Control-plane release images are gated only for linux/amd64" in _read(
        INFRA_ROOT
        / "ansible"
        / "roles"
        / "control_plane_stack"
        / "tasks"
        / "validate.yml"
    )

    for component in (
        "backend",
        "worker",
        "helix_adapter",
        "remnawave",
        "node",
        "subscription_page",
        "node_ssh_proxy",
    ):
        assert f"name: {component}" in image_workflow
    assert "actions/checkout@v" not in image_workflow
    assert "docker/setup-buildx-action@v" not in image_workflow
    assert "docker/login-action@v" not in image_workflow
    assert "docker/build-push-action@v" not in image_workflow
    assert "aquasecurity/trivy-action@v" not in image_workflow
    assert (
        image_workflow.count("actions/attest@f7c74d28b9d84cb8768d0b8ca14a4bac6ef463e6")
        == 3
    )

    hmac_guard = stage_deploy.split("require_remnawave_stream_hmac_secret() {", 1)[
        1
    ].split("\n}", 1)[0]
    assert "${#stream_secret}" in hmac_guard
    assert "-lt 32" in hmac_guard
    assert "must not use a placeholder value" in hmac_guard
    assert '"$stream_secret" = "$backend_secret"' in hmac_guard
    assert stage_deploy.count("require_remnawave_stream_hmac_secret") == 2
