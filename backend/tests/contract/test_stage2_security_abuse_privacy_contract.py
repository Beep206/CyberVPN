from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_stage2_security_abuse_privacy_docs_exist_and_cover_required_controls() -> None:
    root = _repo_root()
    stage_doc = (
        root
        / "docs/cybervpn_stage2_launch_docs/12_STAGE2_SECURITY_ABUSE_PRIVACY.md"
    ).read_text(encoding="utf-8")
    runbook = (root / "docs/runbooks/STAGE2_SECURITY_ABUSE_PRIVACY.md").read_text(
        encoding="utf-8"
    )
    evidence = (
        root
        / "docs/evidence/releases/s2-stage-13-security-abuse-privacy-20260523.md"
    ).read_text(encoding="utf-8")

    for fragment in (
        "dependency audit",
        "secrets scan",
        "bundle/env leak scan",
        "webhook",
        "rate limits",
        "admin",
        "2FA",
        "kill switches",
        "log privacy",
        "PASS_WITH_CONTROLLED_GAPS",
    ):
        assert fragment in stage_doc
        assert fragment in evidence

    for fragment in (
        "Dependency Audit",
        "Secret Scan",
        "Bundle / Env Leak Scan",
        "Public Edge Probes",
        "Webhook Safety Probes",
        "Production Runtime Flag Probe",
        "Log Privacy Scan",
        "No-Go Conditions",
    ):
        assert fragment in runbook


def test_stage2_security_abuse_privacy_documents_admin_header_fix() -> None:
    root = _repo_root()
    stage_doc = (
        root
        / "docs/cybervpn_stage2_launch_docs/12_STAGE2_SECURITY_ABUSE_PRIVACY.md"
    ).read_text(encoding="utf-8")
    evidence = (
        root
        / "docs/evidence/releases/s2-stage-13-security-abuse-privacy-20260523.md"
    ).read_text(encoding="utf-8")
    admin_layout = (root / "admin/src/app/[locale]/layout.tsx").read_text(
        encoding="utf-8"
    )
    caddy_stage1 = (
        root / "infra/deploy/stage1/Caddyfile.stage1.snippet"
    ).read_text(encoding="utf-8")
    caddy_system = (
        root / "infra/deploy/stage1/Caddyfile.system-stage1.snippet"
    ).read_text(encoding="utf-8")

    assert "internal 127.0.0.1 origin" in stage_doc
    assert "link_count=0" in evidence
    assert "routeType: 'private'" in admin_layout
    assert "canonicalPath: '/'" not in admin_layout
    assert "header_down -Link" in caddy_stage1
    assert "header_down -Link" in caddy_system


def test_stage2_security_abuse_privacy_carries_controlled_gaps() -> None:
    root = _repo_root()
    stage_doc = (
        root
        / "docs/cybervpn_stage2_launch_docs/12_STAGE2_SECURITY_ABUSE_PRIVACY.md"
    ).read_text(encoding="utf-8")
    evidence = (
        root
        / "docs/evidence/releases/s2-stage-13-security-abuse-privacy-20260523.md"
    ).read_text(encoding="utf-8")

    for fragment in (
        "NPM moderate",
        "CSP",
        "Cloudflare WAF",
        "OAuth plaintext fallback",
        "Paid/referral/promo/gift/autoprolongation",
    ):
        assert fragment in stage_doc
        assert fragment in evidence


def test_stage2_security_abuse_privacy_records_dependency_blocker_fix() -> None:
    root = _repo_root()
    evidence = (
        root
        / "docs/evidence/releases/s2-stage-13-security-abuse-privacy-20260523.md"
    ).read_text(encoding="utf-8")
    pyproject = (root / "services/task-worker/pyproject.toml").read_text(
        encoding="utf-8"
    )

    for fragment in (
        "idna>=3.15",
        "starlette>=1.0.1",
        "urllib3>=2.7.0",
    ):
        assert fragment in pyproject

    for fragment in (
        "idna      3.12  -> 3.16",
        "starlette 1.0.0 -> 1.0.1",
        "urllib3   2.6.3 -> 2.7.0",
        "No known vulnerabilities found",
    ):
        assert fragment in evidence
