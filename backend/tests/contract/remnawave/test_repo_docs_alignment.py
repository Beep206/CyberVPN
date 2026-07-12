from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _single_code_table_value(content: str, label: str) -> str:
    label_pattern = re.compile(rf"^\s*\|\s*{re.escape(label)}\s*\|")
    rows = [line for line in content.splitlines() if label_pattern.match(line)]
    assert len(rows) == 1, f"Expected exactly one {label!r} row, found {len(rows)}"

    match = re.fullmatch(rf"\s*\|\s*{re.escape(label)}\s*\|\s*`([^`]+)`\s*\|\s*", rows[0])
    assert match is not None, f"Malformed {label!r} row: {rows[0]}"
    return match.group(1)


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


def test_current_vpn_architecture_names_the_audited_runtime() -> None:
    architecture = _read("docs/architecture/CYBERVPN_PREMIUM_SMART_RU_CURRENT_PRODUCTION_ARCHITECTURE.md")
    audit = _read("docs/evidence/releases/task1-task2-20260712/final-main-production-audit-20260712.md")

    current_image = _single_code_table_value(audit, "Current backend image")
    merge_commit = _single_code_table_value(audit, "Main merge commit")
    assert re.fullmatch(r"task1-task2-\d{8}-r\d+-main-[0-9a-f]{8}", current_image)
    assert re.fullmatch(r"[0-9a-f]{40}", merge_commit)
    assert current_image.endswith(f"-main-{merge_commit[:8]}")

    status_heading = "## 1. Краткий статус"
    assert architecture.count(status_heading) == 1
    status_section = architecture.split(status_heading, maxsplit=1)[1].split("\n## ", maxsplit=1)[0]
    status_lines = status_section.splitlines()
    table_header = "| Область | Текущее состояние | Граница доказательства |"
    header_indexes = [index for index, line in enumerate(status_lines) if line.strip() == table_header]
    assert len(header_indexes) == 1

    header_index = header_indexes[0]
    assert re.fullmatch(r"\s*\|\s*---\s*\|\s*---\s*\|\s*---\s*\|\s*", status_lines[header_index + 1])
    table_rows: list[str] = []
    for line in status_lines[header_index + 2 :]:
        if not re.match(r"^\s*\|", line):
            break
        table_rows.append(line)

    backend_rows = [line for line in table_rows if re.match(r"^\s*\|\s*CyberVPN backend\s*\|", line)]
    assert len(backend_rows) == 1
    runtime_match = re.match(r"^\s*\|\s*CyberVPN backend\s*\|\s*image `([^`]+)`,", backend_rows[0])
    assert runtime_match is not None
    assert runtime_match.group(1) == current_image
    for stale_current_claim in (
        "current readiness=true только при valid r8 attestation",
        "Current production\\nr8 readiness=true with signed verifier",
        "**LIVE/PASS:** r8 readiness=true",
    ):
        assert stale_current_claim not in architecture
