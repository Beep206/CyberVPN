from __future__ import annotations

from pathlib import Path


def test_backend_security_workflow_fails_closed() -> None:
    workflow_path = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "backend-security.yml"
    workflow = workflow_path.read_text(encoding="utf-8")

    assert "continue-on-error: true" not in workflow
    assert "|| true" not in workflow
    assert "pip-audit" in workflow
    assert "bandit -r src/" in workflow
    assert "ruff check src/ --select S" in workflow
