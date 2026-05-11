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
    "docs/evidence/releases/ci-stage1/",
    "https://cyber-vpn.net/en-EN/status",
    "https://api.cyber-vpn.net/healthz",
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
