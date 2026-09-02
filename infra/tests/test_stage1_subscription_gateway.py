from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_container_caddy_keeps_public_subscriptions_behind_backend_gateway() -> None:
    caddy = (ROOT / "infra/deploy/stage1/Caddyfile.stage1.snippet").read_text(
        encoding="utf-8"
    )
    block = caddy.split("@remnawave_subscription", 1)[1].split("@api", 1)[0]

    assert "reverse_proxy cybervpn-backend:8000" in block
    assert "header_up -X-CyberVPN-*" in block
    assert "reverse_proxy cybervpn-remnawave-subscription-page:3010" not in block
    assert "reverse_proxy remnawave:3000" not in block


def test_system_caddy_keeps_public_subscriptions_behind_backend_gateway() -> None:
    caddy = (ROOT / "infra/deploy/stage1/Caddyfile.system-stage1.snippet").read_text(
        encoding="utf-8"
    )
    block = caddy.split("@stage1_remnawave_subscription", 1)[1].split(
        "@stage1_backend", 1
    )[0]

    assert "reverse_proxy http://127.0.0.1:18080" in block
    assert "header_up -X-CyberVPN-*" in block
    assert "reverse_proxy http://127.0.0.1:13010" not in block
    assert "reverse_proxy http://127.0.0.1:13005" not in block


def test_production_edge_keeps_legacy_path_behind_backend_gateway() -> None:
    caddy = (ROOT / "infra/deploy/stage1/Caddyfile.edge-stage1.production").read_text(
        encoding="utf-8"
    )
    gateway = caddy.split("(product_subscription_gateway)", 1)[1].split(
        "(frontend_proxy)", 1
    )[0]

    assert "reverse_proxy cybervpn-stage1-cybervpn-backend-1:8000" in gateway
    assert "header_up X-Forwarded-For {client_ip}" in gateway
    assert "cybervpn-stage1-cybervpn-remnawave-subscription-page-1:3010" not in gateway


def test_internal_health_is_not_exposed_by_any_public_subscription_route() -> None:
    for filename in (
        "Caddyfile.stage1.snippet",
        "Caddyfile.system-stage1.snippet",
        "Caddyfile.edge-stage1.production",
    ):
        caddy = (ROOT / "infra/deploy/stage1" / filename).read_text(encoding="utf-8")
        assert "/internal/health" not in caddy


def test_stage1_subscription_page_is_digest_pinned_private_and_hardened() -> None:
    compose = (ROOT / "infra/deploy/stage1/docker-compose.stage1.yml").read_text(
        encoding="utf-8"
    )
    page = compose.split("  cybervpn-remnawave-subscription-page:\n", 1)[1].split(
        "  cybervpn-remnawave-node-ssh-proxy:\n", 1
    )[0]

    assert (
        "remnawave/subscription-page:8.0.0@sha256:"
        "04e8d479afb3598024e4018e9e15cd7fe879938250090a690ba39f1ee91b79ac" in page
    )
    assert 'profiles: ["subscription"]' in page
    assert "remnawave-subscription-page.env" in page
    assert "required: true" in page
    assert "REMNAWAVE_API_TOKEN:" not in page
    assert "REMNAWAVE_PANEL_URL: http://cybervpn-remnawave:3000" in page
    assert "CUSTOM_SUB_PREFIX: api/sub" in page
    assert (
        "TRUST_PROXY: ${REMNAWAVE_SUBSCRIPTION_PAGE_TRUST_PROXY:-172.30.3.0/24}" in page
    )
    assert '"127.0.0.1:13010:3010"' in page
    assert "cybervpn-backend: {}" in page
    assert "cybervpn-public" not in page
    assert "cybervpn-egress" not in page
    assert "read_only: true" in page
    assert 'user: "1000:1000"' in page
    assert "cap_drop:\n      - ALL" in page
    assert "<<: *runtime-defaults" in page
    assert "no-new-privileges:true" in compose.split("services:", 1)[0]
    assert "http://127.0.0.1:3010/internal/health" in page


def test_stage1_has_separate_digest_pinned_7_2_6_component_rollback() -> None:
    rollback = (
        ROOT / "infra/deploy/stage1/docker-compose.subscription-page-rollback.yml"
    ).read_text(encoding="utf-8")
    deploy = (ROOT / "scripts/deploy/stage1-gitlab-deploy.sh").read_text(
        encoding="utf-8"
    )

    assert "cybervpn-remnawave-subscription-page:" in rollback
    assert (
        "remnawave/subscription-page:7.2.6@sha256:"
        "da5ee26ec70ecd81e57303993e8bfb74c8e52f2fa74644b84aad53324cde2e8c" in rollback
    )
    assert "subscription-page" in deploy
    assert "require_remnawave_subscription_page_contract" in deploy
    assert (
        "REMNAWAVE_SUBSCRIPTION_PAGE_IMAGE must be an immutable digest-pinned image"
        in deploy
    )
    assert "REMNAWAVE_SUBSCRIPTION_PAGE_TRUST_PROXY must exactly match" in deploy
    assert "docker-compose.subscription-page-rollback.yml" in deploy
    assert "subscription-page-health" in deploy


def test_stage1_panel_requires_registry_digest_pinned_3_4_3_compatibility_image() -> (
    None
):
    compose = (ROOT / "infra/deploy/stage1/docker-compose.stage1.yml").read_text(
        encoding="utf-8"
    )
    deploy = (ROOT / "scripts/deploy/stage1-gitlab-deploy.sh").read_text(
        encoding="utf-8"
    )

    assert (
        "${CYBERVPN_REMNAWAVE_BACKEND_IMAGE:?CYBERVPN_REMNAWAVE_BACKEND_IMAGE must be a registry digest-pinned 3.4.3 image}"
        in compose
    )
    assert (
        "CYBERVPN_REMNAWAVE_BACKEND_IMAGE must be the registry digest-pinned 3.4.3 compatibility image"
        in deploy
    )
    assert "3[.]4[.]3-raw-vision-flow" in deploy


def test_ansible_subscription_page_contract_is_private_and_operational() -> None:
    role = ROOT / "infra/ansible/roles/control_plane_stack"
    defaults = (role / "defaults/main.yml").read_text(encoding="utf-8")
    template = (role / "templates/docker-compose.yml.j2").read_text(encoding="utf-8")
    rollback = (
        role / "templates/docker-compose.subscription-page-rollback.yml.j2"
    ).read_text(encoding="utf-8")
    validate = (role / "tasks/validate.yml").read_text(encoding="utf-8")
    verify = (role / "tasks/verify.yml").read_text(encoding="utf-8")
    deploy = (role / "tasks/deploy.yml").read_text(encoding="utf-8")

    assert "control_plane_stack_enable_subscription_page: false" in defaults
    assert "control_plane_stack_subscription_page_bind_host: 127.0.0.1" in defaults
    assert "control_plane_stack_subscription_page_subnet: 172.31.253.0/29" in defaults
    assert "remnawave/subscription-page:7.2.6@sha256:" in defaults
    assert "remnawave-subscription-page:" in template
    assert "control-subscription:" in template
    assert "internal: true" in template
    assert "read_only: true" in template
    assert 'user: "1000:1000"' in template
    assert "/internal/health" in template
    assert "control_plane_stack_subscription_page_rollback_image" in rollback
    assert "Render subscription-page env" in deploy
    assert "Render component-only subscription-page rollback override" in deploy
    assert "subscription-page 8.0 private deployment contract" in validate
    assert "REMNAWAVE_API_TOKEN | length >= 32" in validate
    assert "item.key == 'subscription_page'" in validate
    assert "Check private subscription-page health" in verify
    assert "HostConfig.ReadonlyRootfs" in verify
    assert "NetworkSettings.Networks | length) == 1" in verify


def test_environment_inventories_enable_page_with_dedicated_token_and_prefix() -> None:
    for environment in ("staging", "production"):
        inventory = (
            ROOT
            / "infra/ansible/inventories"
            / environment
            / "group_vars"
            / f"control_plane_{environment}"
            / "main.yml"
        ).read_text(encoding="utf-8")
        vault = (
            ROOT
            / "infra/ansible/inventories"
            / environment
            / "group_vars"
            / f"control_plane_{environment}"
            / "vault.yml.example"
        ).read_text(encoding="utf-8")

        assert "control_plane_stack_enable_subscription_page: true" in inventory
        assert "'CUSTOM_SUB_PREFIX': 'api/sub'" in inventory
        assert (
            "'TRUST_PROXY': control_plane_stack_subscription_page_subnet" in inventory
        )
        assert "vault_control_plane_subscription_page_remnawave_api_token" in inventory
        assert "vault_control_plane_subscription_page_remnawave_api_token" in vault
        assert "vault_control_plane_subscription_page_env_extra" in vault


def test_subscription_page_cutover_preserves_sni_and_amd64_fail_closed_gates() -> None:
    edge_defaults = (
        ROOT / "infra/ansible/roles/remnawave_edge/defaults/main.yml"
    ).read_text(encoding="utf-8")
    edge_validate = (
        ROOT / "infra/ansible/roles/remnawave_edge/tasks/validate.yml"
    ).read_text(encoding="utf-8")
    control_validate = (
        ROOT / "infra/ansible/roles/control_plane_stack/tasks/validate.yml"
    ).read_text(encoding="utf-8")

    assert "remnawave_edge_sni_verification: true" in edge_defaults
    assert "ansible_architecture == 'x86_64'" in edge_validate
    assert "ansible_architecture == 'x86_64'" in control_validate


def test_task2_readiness_uses_read_only_signed_artifacts_and_defaults_closed() -> None:
    compose = (ROOT / "infra/deploy/stage1/docker-compose.stage1.yml").read_text(
        encoding="utf-8"
    )
    backend = compose.split("  cybervpn-backend:", 1)[1].split(
        "  cybervpn-vpn-test-agent:", 1
    )[0]

    assert "      ENVIRONMENT: production" in backend
    assert (
        "REMNAWAVE_SPB_DE_EXCEPTIONS_DATA_PLANE_READY: "
        "${REMNAWAVE_SPB_DE_EXCEPTIONS_DATA_PLANE_READY:-false}"
    ) in backend
    assert (
        "REMNAWAVE_SPB_DE_EXCEPTIONS_READINESS_ATTESTATION_PATH: "
        "/run/cybervpn/readiness/task2/attestation.jwt"
    ) in backend
    assert (
        "REMNAWAVE_SPB_DE_EXCEPTIONS_READINESS_PUBLIC_KEY_PATH: "
        "/run/cybervpn/readiness/task2/public-key.pem"
    ) in backend
    assert (
        "REMNAWAVE_SPB_DE_EXCEPTIONS_READINESS_ACTIVE_POINTER_PATH: "
        "/run/cybervpn/readiness/task2/active.json"
    ) in backend
    assert (
        "REMNAWAVE_SPB_DE_EXCEPTIONS_READINESS_LKG_POINTER_PATH: "
        "/run/cybervpn/readiness/task2/last-known-good.json"
    ) in backend
    assert (
        "REMNAWAVE_SPB_DE_EXCEPTIONS_READINESS_STORE_PATH: "
        "/run/cybervpn/readiness/task2"
    ) in backend
    assert "REMNAWAVE_SPB_DE_EXCEPTIONS_READINESS_MANIFEST:" not in backend
    assert (
        "${CYBERVPN_READINESS_DIR:-/srv/cybervpn/readiness}/task2:"
        "/run/cybervpn/readiness/task2:ro"
    ) in backend
    assert "readiness/task2:rw" not in backend
