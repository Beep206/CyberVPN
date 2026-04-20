from pathlib import Path


def _read_policy_lifecycle() -> str:
    repo_root = Path(__file__).resolve().parents[3]
    return (repo_root / "docs/api/partner-platform-policy-version-lifecycle.md").read_text(encoding="utf-8")


def test_policy_lifecycle_contains_required_fields_and_states() -> None:
    content = _read_policy_lifecycle()

    for required_term in (
        "effective_from",
        "effective_to",
        "approval_state",
        "version_status",
        "draft",
        "approved",
        "active",
        "superseded",
        "archived",
    ):
        assert required_term in content


def test_policy_lifecycle_contains_non_retroactive_history_rules() -> None:
    content = _read_policy_lifecycle()

    assert "Finalized orders always retain references to the original version identifiers" in content
    assert "never rewrites finalized financial history retroactively" in content
