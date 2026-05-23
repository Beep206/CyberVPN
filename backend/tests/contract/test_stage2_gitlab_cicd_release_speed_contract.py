from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_stage2_gitlab_cicd_release_speed_docs_exist_and_cover_required_flow() -> None:
    root = _repo_root()
    stage_doc = (
        root
        / "docs/cybervpn_stage2_launch_docs/13_STAGE2_GITLAB_CICD_RELEASE_SPEED.md"
    ).read_text(encoding="utf-8")
    runbook = (
        root / "docs/runbooks/STAGE2_GITLAB_CICD_RELEASE_SPEED.md"
    ).read_text(encoding="utf-8")
    evidence = (
        root
        / "docs/evidence/releases/s2-stage-14-gitlab-cicd-release-speed-20260523.md"
    ).read_text(encoding="utf-8")

    for fragment in (
        "GitLab",
        "GitHub",
        "stage2:release-evidence-pack",
        "stage2:deploy:dry-run",
        "immutable",
        "manual",
        "rollback",
        "PASS_WITH_CONTROLLED_GAPS",
    ):
        assert fragment in stage_doc
        assert fragment in evidence

    for fragment in (
        "GitLab is first",
        "Normal Commit Flow",
        "Deploy Dry-Run",
        "Real Deploy",
        "Hotfix Path",
        "No-Go Conditions",
    ):
        assert fragment in runbook


def test_stage2_gitlab_ci_contract_has_release_speed_jobs_and_rules() -> None:
    root = _repo_root()
    ci = (root / ".gitlab-ci.yml").read_text(encoding="utf-8")
    validator = (root / "scripts/validate_gitlab_ci_contract.py").read_text(
        encoding="utf-8"
    )

    for fragment in (
        ".rules_stage2_release_speed:",
        "stage2:release-evidence-pack:",
        "stage2:deploy:dry-run:",
        "docs/evidence/releases/ci-stage2/",
        "STAGE2_RELEASE_SPEED",
        "S2_RELEASE_TAG",
        "S2_DRY_RUN_SERVICES",
        "stage2-public-rc",
    ):
        assert fragment in ci
        assert fragment in validator


def test_stage2_deploy_script_supports_no_network_dry_run() -> None:
    root = _repo_root()
    deploy_script = (root / "scripts/deploy/stage1-gitlab-deploy.sh").read_text(
        encoding="utf-8"
    )

    for fragment in (
        "STAGE1_DEPLOY_DRY_RUN",
        "dry-run.invalid",
        "No SSH, rsync, Docker build, compose restart or public smoke was executed.",
        "exit 0",
    ):
        assert fragment in deploy_script

    assert "ssh_cmd" in deploy_script
    assert "rsync -az --delete" in deploy_script


def test_stage2_gitlab_cicd_documents_no_secret_rotation_requirement() -> None:
    root = _repo_root()
    stage_doc = (
        root
        / "docs/cybervpn_stage2_launch_docs/13_STAGE2_GITLAB_CICD_RELEASE_SPEED.md"
    ).read_text(encoding="utf-8")
    runbook = (
        root / "docs/runbooks/STAGE2_GITLAB_CICD_RELEASE_SPEED.md"
    ).read_text(encoding="utf-8")
    evidence = (
        root
        / "docs/evidence/releases/s2-stage-14-gitlab-cicd-release-speed-20260523.md"
    ).read_text(encoding="utf-8")

    for content in (stage_doc, runbook, evidence):
        assert "No key rotation is required" in content
