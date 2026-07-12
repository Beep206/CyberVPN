from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_container_caddy_routes_public_subscriptions_through_backend() -> None:
    caddy = (ROOT / "infra/deploy/stage1/Caddyfile.stage1.snippet").read_text(
        encoding="utf-8"
    )
    block = caddy.split("@remnawave_subscription", 1)[1].split("@api", 1)[0]

    assert "reverse_proxy cybervpn-backend:8000" in block
    assert "header_up -X-CyberVPN-*" in block
    assert "reverse_proxy remnawave:3000" not in block


def test_system_caddy_routes_public_subscriptions_through_backend() -> None:
    caddy = (ROOT / "infra/deploy/stage1/Caddyfile.system-stage1.snippet").read_text(
        encoding="utf-8"
    )
    block = caddy.split("@stage1_remnawave_subscription", 1)[1].split(
        "@stage1_backend", 1
    )[0]

    assert "reverse_proxy http://127.0.0.1:18080" in block
    assert "header_up -X-CyberVPN-*" in block
    assert "reverse_proxy http://127.0.0.1:13005" not in block


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
