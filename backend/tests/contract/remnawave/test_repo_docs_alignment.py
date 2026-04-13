from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_high_signal_docs_use_current_remnawave_baseline() -> None:
    monitored_files = {
        "docs/PROJECT_OVERVIEW.md": _read("docs/PROJECT_OVERVIEW.md"),
        "docs/CYBERVPN_FULL_DESCRIPTION.md": _read("docs/CYBERVPN_FULL_DESCRIPTION.md"),
        "docs/menu-frontend/USER_MENU_STRUCTURE.md": _read("docs/menu-frontend/USER_MENU_STRUCTURE.md"),
        "docs/menu-frontend/user_menu_structure.md": _read("docs/menu-frontend/user_menu_structure.md"),
        "SDK/python-sdk-production/README.md": _read("SDK/python-sdk-production/README.md"),
    }

    stale_markers = (
        "Remnawave SDK: 2.4.4",
        "v2.4.4+",
        "`remnawave-api`",
        "remnawave/node:2.6.1",
    )

    for path, content in monitored_files.items():
        for marker in stale_markers:
            assert marker not in content, f"{path} still contains stale marker: {marker}"

    assert "2.7.4" in monitored_files["docs/PROJECT_OVERVIEW.md"]
    assert "2.7.4" in monitored_files["docs/CYBERVPN_FULL_DESCRIPTION.md"]
    assert "2.7.4" in monitored_files["SDK/python-sdk-production/README.md"]


def test_upgrade_guardrails_doc_covers_required_invariants() -> None:
    content = _read("docs/runbooks/REMNAWAVE_UPGRADE_GUARDRAILS.md")

    assert "backend/src/infrastructure/remnawave/contracts.py" in content
    assert "REMNAWAVE_WEBHOOK_SECRET" in content
    assert "X-Remnawave-Signature" in content
    assert "X-Remnawave-Timestamp" in content
    assert "Node Plugins" in content
    assert "scripts/check-generated-artifacts.sh" in content
    assert "tests/unit/test_remnawave_normalizers.py" in content
    assert "tests/test_services.py" in content
    assert "cargo test node_registry_inventory_helper_accepts_current_remnawave_fixture" in content
    assert "cargo clippy --all-targets -- -D warnings" in content


def test_helix_docs_keep_node_plugins_boundary_explicit() -> None:
    architecture = _read("docs/helix/architecture.md")
    decision_log = _read("docs/helix/decision-log.md")

    assert "Node Plugins" in architecture
    assert "Node Plugins" in decision_log
