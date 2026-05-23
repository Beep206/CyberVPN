from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_stage2_release_rehearsal_docs_exist_and_cover_required_surfaces() -> None:
    root = _repo_root()
    stage_doc = (
        root / "docs/cybervpn_stage2_launch_docs/14_STAGE2_RELEASE_REHEARSAL.md"
    ).read_text(encoding="utf-8")
    runbook = (root / "docs/runbooks/STAGE2_RELEASE_REHEARSAL.md").read_text(
        encoding="utf-8"
    )
    evidence = (
        root
        / "docs/evidence/releases/s2-stage-15-release-rehearsal-20260523.md"
    ).read_text(encoding="utf-8")

    for fragment in (
        "stage2-public-rc.1",
        "stage2-public-rc.2",
        "deploy dry-run",
        "public frontend route probes",
        "home observability",
        "rollback",
        "PASS_WITH_CONTROLLED_GAPS",
    ):
        assert fragment in stage_doc
        assert fragment in evidence

    for fragment in (
        "Safety Rules",
        "Create RC Tag",
        "Deploy Dry-Run",
        "Public Route Probes",
        "Runtime Inventory",
        "Observability Checks",
        "Rollback Check",
        "Owner Manual Canary Checklist",
    ):
        assert fragment in runbook


def test_stage2_release_rehearsal_preserves_domain_and_node_boundaries() -> None:
    root = _repo_root()
    stage_doc = (
        root / "docs/cybervpn_stage2_launch_docs/14_STAGE2_RELEASE_REHEARSAL.md"
    ).read_text(encoding="utf-8")
    runbook = (root / "docs/runbooks/STAGE2_RELEASE_REHEARSAL.md").read_text(
        encoding="utf-8"
    )
    evidence = (
        root
        / "docs/evidence/releases/s2-stage-15-release-rehearsal-20260523.md"
    ).read_text(encoding="utf-8")

    for content in (stage_doc, runbook, evidence):
        assert "cyber-vpn.org" in content
        assert "VPN node" in content
        assert "node-only" in content

    assert ".org` is not a customer mirror" in stage_doc
    assert "No application, database, observability, GitLab or payment containers" in runbook
    assert "No app, GitLab, Sentry, Grafana, Prometheus, backend, frontend, admin, database or payment services were observed on the node." in evidence


def test_stage2_release_rehearsal_preserves_quic_and_secret_boundaries() -> None:
    root = _repo_root()
    stage_doc = (
        root / "docs/cybervpn_stage2_launch_docs/14_STAGE2_RELEASE_REHEARSAL.md"
    ).read_text(encoding="utf-8")
    runbook = (root / "docs/runbooks/STAGE2_RELEASE_REHEARSAL.md").read_text(
        encoding="utf-8"
    )
    evidence = (
        root
        / "docs/evidence/releases/s2-stage-15-release-rehearsal-20260523.md"
    ).read_text(encoding="utf-8")

    for content in (stage_doc, runbook, evidence):
        assert "HTTP/3/QUIC" in content
        assert 'alt-svc: h3=":443"; ma=86400' in content

    for content in (runbook, evidence):
        assert "Do not paste secrets" in content or "No secret values" in content
        assert "raw subscription" in content


def test_stage2_release_rehearsal_classifies_live_mutation_gaps() -> None:
    root = _repo_root()
    stage_doc = (
        root / "docs/cybervpn_stage2_launch_docs/14_STAGE2_RELEASE_REHEARSAL.md"
    ).read_text(encoding="utf-8")
    evidence = (
        root
        / "docs/evidence/releases/s2-stage-15-release-rehearsal-20260523.md"
    ).read_text(encoding="utf-8")

    for fragment in (
        "live real-money payment",
        "production trial activation",
        "new provisioning mutation",
        "VPN client connection",
        "S2-STAGE-16",
    ):
        assert fragment in stage_doc
        assert fragment in evidence
