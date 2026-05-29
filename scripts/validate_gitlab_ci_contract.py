#!/usr/bin/env python3
"""Repository-level checks for the CyberVPN GitLab CI baseline.

This is not a replacement for GitLab's server-side CI linter. It is a local
contract check that keeps the monorepo pipeline shape from drifting before the
project is imported into the home GitLab instance.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CI_FILE = ROOT / ".gitlab-ci.yml"
MR_TEMPLATE_FILE = ROOT / ".gitlab" / "merge_request_templates" / "Default.md"
AI_MR_CONTRACT_FILE = ROOT / "docs" / "gitlab" / "AI_MR_CONTRACT.md"
AI_REVIEW_MAP_FILE = ROOT / "docs" / "gitlab" / "AI_REVIEW_MAP.md"
CODEOWNERS_FILE = ROOT / "CODEOWNERS"
DOCKER_SOCK_MARKER = "/var/run/" + "docker.sock"

REQUIRED_TOP_LEVEL_KEYS = (
    "workflow:",
    "stages:",
    "default:",
    "variables:",
)

REQUIRED_STAGES = (
    "validate",
    "lint",
    "test",
    "build",
    "security",
    "package",
    "deploy",
)

REQUIRED_JOBS = (
    "gitlab:ci-contract:",
    "frontend:lint:",
    "frontend:test:",
    "frontend:build:",
    "admin:lint:",
    "admin:test:",
    "admin:build:",
    "partner:lint:",
    "partner:test:",
    "partner:build:",
    "backend:lint:",
    "backend:test:smoke:",
    "telegram-bot:lint:",
    "telegram-bot:test:smoke:",
    "task-worker:lint:",
    "task-worker:test:smoke:",
    "secret-pattern-scan:",
    "security:gitleaks:",
    "npm-audit:high:",
    "pip-audit:python-locks:",
    "container-scan:trivy-grype:",
    "sbom:release-candidate:",
    "docker:backend:",
    "docker:telegram-bot:",
    "docker:task-worker:",
    "stage1:deploy:backend:",
    "stage1:deploy:frontend:",
    "stage1:deploy:admin:",
    "stage1:deploy:telegram-bot:",
    "stage1:deploy:task-worker:",
    "stage1:deploy:all:",
    "stage2:release-evidence-pack:",
    "stage2:deploy:dry-run:",
    "stage1:limited-publication-preflight:",
)

REQUIRED_RULE_ANCHORS = (
    ".rules_frontend:",
    ".rules_admin:",
    ".rules_partner:",
    ".rules_backend:",
    ".rules_telegram_bot:",
    ".rules_task_worker:",
    ".rules_security:",
    ".rules_stage1_limited_publication:",
    ".rules_stage2_release_speed:",
)

REQUIRED_PATH_MARKERS = (
    "frontend/**/*",
    "admin/**/*",
    "partner/**/*",
    "backend/**/*",
    "services/telegram-bot/**/*",
    "services/task-worker/**/*",
    "scripts/security/**/*",
    "backend/Dockerfile",
    "services/telegram-bot/Dockerfile",
    "services/task-worker/Dockerfile",
)

REQUIRED_SECURITY_RULE_MARKERS = (
    "$CI_PIPELINE_SOURCE == \"schedule\"",
    "$CI_COMMIT_TAG",
    "$SECURITY_RELEASE_CANDIDATE == \"true\"",
)

REQUIRED_SECURITY_SCRIPT_MARKERS = (
    "scan-secrets.sh",
    "audit-dependencies.sh npm",
    "audit-dependencies.sh python",
    "scan-filesystem-vulnerabilities.sh",
    "generate-sbom.sh",
    "GITLEAKS_VERSION:",
    "TRIVY_VERSION:",
    "GRYPE_VERSION:",
    "SYFT_VERSION:",
    "sha256sum -c -",
)

REQUIRED_STAGE1_PUBLICATION_MARKERS = (
    "stage1/limited-public-beta",
    "STAGE1_FULL_CI",
    "STAGE1_LIMITED_PUBLICATION_PREFLIGHT",
    "STAGE1_REQUIRE_BETA_GO",
    "STAGE1_AUTO_DEPLOY",
    "STAGE1_PROD_SSH_PRIVATE_KEY",
    "STAGE1_DEPLOY_DRY_RUN",
    "scripts/deploy/stage1-gitlab-deploy.sh",
    "resource_group: stage1-production",
    "docs/evidence/releases/ci-stage1/",
    "https://cyber-vpn.net/en-EN/status",
    "https://api.cyber-vpn.net/healthz",
)

REQUIRED_STAGE2_RELEASE_SPEED_MARKERS = (
    "STAGE2_RELEASE_SPEED",
    "S2_RELEASE_TAG",
    "S2_DRY_RUN_SERVICES",
    "stage2/public-release",
    "stage2:release-evidence-pack:",
    "stage2:deploy:dry-run:",
    "docs/evidence/releases/ci-stage2/",
    "stage2-public-rc",
    "Production deploys must use immutable SHA/tag",
)

REQUIRED_GITLAB_CONFIG_PATH_MARKERS = (
    "CODEOWNERS",
    ".gitlab/merge_request_templates/**/*",
    "docs/gitlab/**/*",
    "scripts/validate_gitlab_ci_contract.py",
)

REQUIRED_MR_TEMPLATE_MARKERS = (
    "# Summary",
    "# Scope Classification",
    "# Touched Paths",
    "# What Was Intentionally Not Changed",
    "# Tests Run",
    "# Remote CI",
    "# Screenshots / UI Evidence",
    "# Security Notes",
    "# Rollback Notes",
    "# Reviewer Agents Required",
    "# Paperclip Links",
    "# Labels",
    "# Merge Gate",
    "risk::green",
    "risk::amber",
    "risk::red",
    "lane::autonomous",
)

REQUIRED_MR_CONTRACT_MARKERS = (
    "GitLab CE does not expose required approval rules",
    "lane::autonomous",
    "risk::green",
    "risk::amber",
    "risk::red",
    "area::backend",
    "area::frontend",
    "area::admin",
    "area::partner",
    "area::telegram",
    "area::docs",
    "data::none",
    "data::synthetic-only",
    "data::sensitive",
    "needs::security",
    "needs::qa",
    "needs::luma",
    "sentinel::candidate",
    "only_allow_merge_if_pipeline_succeeds",
    "Test and build jobs must not use `allow_failure`",
)

REQUIRED_REVIEW_MAP_MARKERS = (
    "Paperclip AI agents",
    "Risk Levels",
    "Path Review Matrix",
    "Support Platform Initial Gate",
)

REQUIRED_CODEOWNERS_MARKERS = (
    "/backend/",
    "/frontend/",
    "/admin/",
    "/partner/",
    "/services/telegram-bot/",
    "/services/task-worker/",
    "/docs/gitlab/AI_REVIEW_MAP.md",
)

FORBIDDEN_MARKERS = (
    "<<<<<<<",
    "=======",
    ">>>>>>>",
    "force: true",
    "docker push",
    "SENTRY_AUTH_TOKEN=",
    "TELEGRAM_BOT_TOKEN=",
    "CRYPTOBOT_TOKEN=",
    DOCKER_SOCK_MARKER,
)


def require_all(content: str, markers: tuple[str, ...], label: str) -> list[str]:
    return [f"missing {label}: {marker}" for marker in markers if marker not in content]


def read_required_file(path: Path, label: str) -> tuple[list[str], str]:
    if not path.exists():
        return [f"missing {label}: {path.relative_to(ROOT)}"], ""
    return [], path.read_text(encoding="utf-8")


def require_file_markers(path: Path, markers: tuple[str, ...], label: str) -> list[str]:
    failures, content = read_required_file(path, label)
    return failures + require_all(content, markers, label)


def collect_top_level_blocks(content: str) -> dict[str, str]:
    blocks: dict[str, list[str]] = {}
    current_name: str | None = None

    for line in content.splitlines():
        if line and not line.startswith((" ", "\t", "-")) and line.endswith(":"):
            current_name = line[:-1]
            blocks[current_name] = []
            continue

        if current_name is not None:
            blocks[current_name].append(line)

    return {name: "\n".join(lines) for name, lines in blocks.items()}


def require_blocking_test_and_build_jobs(content: str) -> list[str]:
    failures: list[str] = []
    for name, block in collect_top_level_blocks(content).items():
        is_blocking_stage = "  stage: test" in block or "  stage: build" in block
        if is_blocking_stage and "  allow_failure: true" in block:
            failures.append(f"test/build job must not allow failure: {name}")
    return failures


def main() -> int:
    if not CI_FILE.exists():
        print(f"FAIL: missing {CI_FILE.relative_to(ROOT)}")
        return 1

    content = CI_FILE.read_text(encoding="utf-8")
    failures: list[str] = []

    failures.extend(require_all(content, REQUIRED_TOP_LEVEL_KEYS, "top-level key"))
    failures.extend(require_all(content, REQUIRED_STAGES, "stage"))
    failures.extend(require_all(content, REQUIRED_JOBS, "job"))
    failures.extend(require_all(content, REQUIRED_RULE_ANCHORS, "rules anchor"))
    failures.extend(require_all(content, REQUIRED_PATH_MARKERS, "path marker"))
    failures.extend(require_all(content, REQUIRED_SECURITY_RULE_MARKERS, "security rule marker"))
    failures.extend(require_all(content, REQUIRED_SECURITY_SCRIPT_MARKERS, "security script marker"))
    failures.extend(require_all(content, REQUIRED_STAGE1_PUBLICATION_MARKERS, "stage1 publication marker"))
    failures.extend(
        require_all(content, REQUIRED_STAGE2_RELEASE_SPEED_MARKERS, "stage2 release-speed marker")
    )
    failures.extend(
        require_all(content, REQUIRED_GITLAB_CONFIG_PATH_MARKERS, "GitLab config path marker")
    )
    failures.extend(
        require_file_markers(MR_TEMPLATE_FILE, REQUIRED_MR_TEMPLATE_MARKERS, "MR template marker")
    )
    failures.extend(
        require_file_markers(AI_MR_CONTRACT_FILE, REQUIRED_MR_CONTRACT_MARKERS, "MR contract marker")
    )
    failures.extend(
        require_file_markers(AI_REVIEW_MAP_FILE, REQUIRED_REVIEW_MAP_MARKERS, "AI review map marker")
    )
    failures.extend(
        require_file_markers(CODEOWNERS_FILE, REQUIRED_CODEOWNERS_MARKERS, "CODEOWNERS marker")
    )
    failures.extend(require_blocking_test_and_build_jobs(content))

    for marker in FORBIDDEN_MARKERS:
        if marker in content:
            failures.append(f"forbidden marker present: {marker}")

    if "rules:" not in content or "changes:" not in content:
        failures.append("pipeline must use rules:changes for monorepo path gating")

    if "when: manual" not in content:
        failures.append("manual package jobs are required for no-cost home runner control")

    if "tags:\n    - dind" not in content:
        failures.append("Docker-in-Docker package jobs must be isolated to a dind runner tag")

    if failures:
        print("FAIL: GitLab CI contract is not ready")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("PASS: GitLab CI contract is ready for initial GitLab import")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
