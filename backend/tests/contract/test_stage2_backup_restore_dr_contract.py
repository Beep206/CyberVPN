from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_stage2_backup_restore_dr_docs_exist_and_cover_required_surfaces() -> None:
    root = _repo_root()
    stage_doc = (
        root / "docs/cybervpn_stage2_launch_docs/11_STAGE2_BACKUP_RESTORE_DR.md"
    ).read_text(encoding="utf-8")
    runbook = (root / "docs/runbooks/STAGE2_BACKUP_RESTORE_DR.md").read_text(
        encoding="utf-8"
    )
    evidence = (
        root / "docs/evidence/releases/s2-stage-12-backup-restore-dr-20260523.md"
    ).read_text(encoding="utf-8")

    for fragment in (
        "CyberVPN app PostgreSQL",
        "Remnawave PostgreSQL",
        "GitLab",
        "Grafana",
        "Sentry",
        "Restic",
        "VPN node",
        "Valkey/Redis",
        "RPO / RTO",
        "rollback",
        "off-host",
    ):
        assert fragment in stage_doc
        assert fragment in runbook

    for fragment in (
        "cybervpn_restore_status=ok",
        "remnawave_restore_status=ok",
        "grafana_restored_dashboard_json_count=33",
        "gitlab_archive_restore_status=ok",
        "rollback_dry_run_status=ok",
        "PASS_WITH_CONTROLLED_GAPS",
    ):
        assert fragment in evidence


def test_stage2_backup_restore_dr_preserves_domain_and_node_boundaries() -> None:
    root = _repo_root()
    stage_doc = (
        root / "docs/cybervpn_stage2_launch_docs/11_STAGE2_BACKUP_RESTORE_DR.md"
    ).read_text(encoding="utf-8")
    evidence = (
        root / "docs/evidence/releases/s2-stage-12-backup-restore-dr-20260523.md"
    ).read_text(encoding="utf-8")

    assert "Node must remain node-only" in stage_doc
    assert "No app, GitLab, Sentry, Grafana, Prometheus, Loki, backend, frontend or payment services were running on the VPN node." in evidence
    assert "cybervpn-remnawave-node" in evidence


def test_stage2_backup_restore_dr_documents_controlled_gaps_without_hiding_them() -> None:
    root = _repo_root()
    stage_doc = (
        root / "docs/cybervpn_stage2_launch_docs/11_STAGE2_BACKUP_RESTORE_DR.md"
    ).read_text(encoding="utf-8")
    evidence = (
        root / "docs/evidence/releases/s2-stage-12-backup-restore-dr-20260523.md"
    ).read_text(encoding="utf-8")

    for fragment in (
        "Automated off-host production backup transfer is not yet installed",
        "GitLab registry",
        "Full GitLab app restore",
        "Sentry full historical event restore",
        "Managed PostgreSQL HA",
    ):
        assert fragment in stage_doc
        assert fragment in evidence


def test_stage2_backup_restore_dr_documents_secret_boundaries() -> None:
    root = _repo_root()
    runbook = (root / "docs/runbooks/STAGE2_BACKUP_RESTORE_DR.md").read_text(
        encoding="utf-8"
    )
    evidence = (
        root / "docs/evidence/releases/s2-stage-12-backup-restore-dr-20260523.md"
    ).read_text(encoding="utf-8")

    for fragment in (
        "Do not paste secrets",
        "Do not commit files from this directory",
        "raw subscription URLs",
    ):
        assert fragment in runbook

    for fragment in (
        "No secret values are stored",
        "Telegram bot token",
        "Remnawave API token",
        "database dumps",
    ):
        assert fragment in evidence
