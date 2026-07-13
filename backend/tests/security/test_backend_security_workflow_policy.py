from __future__ import annotations

import runpy
import subprocess
import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _task2_allowed_paths() -> set[str]:
    validator = REPOSITORY_ROOT / "scripts" / "security" / "validate_gitleaks_config.py"
    namespace = runpy.run_path(str(validator), run_name="gitleaks_policy")
    paths = namespace["TASK2_ALLOWED_PATHS"]
    assert isinstance(paths, set)
    return paths


def test_backend_security_workflow_fails_closed() -> None:
    workflow_path = REPOSITORY_ROOT / ".github" / "workflows" / "backend-security.yml"
    workflow = workflow_path.read_text(encoding="utf-8")

    assert "continue-on-error: true" not in workflow
    assert "|| true" not in workflow
    assert "pip-audit" in workflow
    assert "bandit -r src/" in workflow
    assert "ruff check src/ --select S" in workflow
    assert workflow.count("- '.gitleaks.toml'") == 2
    assert "python scripts/security/validate_gitleaks_config.py" in workflow
    for path in _task2_allowed_paths():
        if not path.startswith("backend/"):
            assert workflow.count(f"- '{path}'") == 2


def _run_gitleaks_policy_validator(
    config_path: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(REPOSITORY_ROOT / "scripts" / "security" / "validate_gitleaks_config.py"),
    ]
    if config_path is not None:
        command.extend(["--config", str(config_path)])

    return subprocess.run(  # noqa: S603 - command is a fixed repository test helper
        command,
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_gitleaks_allowlist_policy_accepts_only_exact_task2_paths() -> None:
    result = _run_gitleaks_policy_validator()

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "Gitleaks config policy OK"


@pytest.mark.parametrize(
    ("reviewed_path", "invalid_path", "expected_error"),
    [
        (
            "^backend/tests/helpers/spb_de_readiness\\.py$",
            "backend/tests/helpers/spb_de_readiness\\.py$",
            "Gitleaks allowlist path must be anchored",
        ),
        (
            "^backend/tests/helpers/spb_de_readiness\\.py$",
            "^backend/tests/helpers/spb_de_readiness\\.py.*$",
            "Task2 Gitleaks allowlist differs from the reviewed exact shape",
        ),
    ],
)
def test_gitleaks_allowlist_policy_rejects_broad_task2_paths(
    tmp_path: Path,
    reviewed_path: str,
    invalid_path: str,
    expected_error: str,
) -> None:
    config = (REPOSITORY_ROOT / ".gitleaks.toml").read_text(encoding="utf-8")
    assert reviewed_path in config

    invalid_config = tmp_path / ".gitleaks.toml"
    invalid_config.write_text(
        config.replace(reviewed_path, invalid_path, 1),
        encoding="utf-8",
    )

    result = _run_gitleaks_policy_validator(invalid_config)

    assert result.returncode != 0
    assert expected_error in result.stderr


@pytest.mark.parametrize(
    ("additional_allowlist", "expected_error"),
    [
        (
            """
[[rules]]
id = "generic-api-key"

[[rules.allowlists]]
description = "Unreviewed broad nested allowlist"
condition = "AND"
regexTarget = "line"
paths = ['''^backend/tests/helpers/spb_de_readiness\\.py.*$''']
regexes = ['''(?i)private_key''']
""",
            "Exactly one generic-api-key rule extension is required",
        ),
        (
            """
[[allowlists]]
description = "Unreviewed broad global allowlist"
targetRules = ["generic-api-key"]
condition = "AND"
regexTarget = "line"
paths = ['''^backend/tests/helpers/spb_de_readiness\\.py.*$''']
regexes = ['''(?i)private_key''']
""",
            "Unreviewed generic-api-key allowlist is forbidden",
        ),
        (
            """
[[allowlists]]
description = "Unreviewed pathless global allowlist"
targetRules = ["generic-api-key"]
condition = "OR"
regexTarget = "match"
regexes = ['''.*''']
""",
            "Unreviewed generic-api-key allowlist is forbidden",
        ),
    ],
)
def test_gitleaks_allowlist_policy_rejects_additional_generic_allowlists(
    tmp_path: Path,
    additional_allowlist: str,
    expected_error: str,
) -> None:
    config = (REPOSITORY_ROOT / ".gitleaks.toml").read_text(encoding="utf-8")
    invalid_config = tmp_path / ".gitleaks.toml"
    invalid_config.write_text(config + additional_allowlist, encoding="utf-8")

    result = _run_gitleaks_policy_validator(invalid_config)

    assert result.returncode != 0
    assert expected_error in result.stderr


def test_gitleaks_allowlist_policy_rejects_generic_rule_override(
    tmp_path: Path,
) -> None:
    config = (REPOSITORY_ROOT / ".gitleaks.toml").read_text(encoding="utf-8")
    reviewed_rule = 'id = "generic-api-key"\n\n[[rules.allowlists]]'
    assert reviewed_rule in config

    invalid_config = tmp_path / ".gitleaks.toml"
    invalid_config.write_text(
        config.replace(
            reviewed_rule,
            'id = "generic-api-key"\nregex = "(?i)nevermatchgenericapikey"\n\n[[rules.allowlists]]',
            1,
        ),
        encoding="utf-8",
    )

    result = _run_gitleaks_policy_validator(invalid_config)

    assert result.returncode != 0
    assert "generic-api-key rule extension shape changed" in result.stderr


def test_gitleaks_allowlist_policy_rejects_disabling_generic_default_rule(
    tmp_path: Path,
) -> None:
    config = (REPOSITORY_ROOT / ".gitleaks.toml").read_text(encoding="utf-8")
    reviewed_extend = "[extend]\nuseDefault = true"
    assert reviewed_extend in config

    invalid_config = tmp_path / ".gitleaks.toml"
    invalid_config.write_text(
        config.replace(
            reviewed_extend,
            reviewed_extend + '\ndisabledRules = ["generic-api-key"]',
            1,
        ),
        encoding="utf-8",
    )

    result = _run_gitleaks_policy_validator(invalid_config)

    assert result.returncode != 0
    assert "Gitleaks default-rule extension shape changed" in result.stderr
