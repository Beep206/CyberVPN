import json
from pathlib import Path

from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX

PHASE7_REQUIRED_PATHS = (
    f"{API_V1_PREFIX}/reporting/outbox-events",
    f"{API_V1_PREFIX}/reporting/outbox-events/{{event_id}}",
    f"{API_V1_PREFIX}/reporting/outbox-publications",
    f"{API_V1_PREFIX}/reporting/outbox-publications/claim",
    f"{API_V1_PREFIX}/reporting/outbox-publications/{{publication_id}}/submitted",
    f"{API_V1_PREFIX}/reporting/outbox-publications/{{publication_id}}/published",
    f"{API_V1_PREFIX}/reporting/outbox-publications/{{publication_id}}/failed",
    f"{API_V1_PREFIX}/reporting/partner-workspaces/{{workspace_id}}/snapshot",
    f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/integration-credentials",
    (
        f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/integration-credentials/"
        "{credential_kind}/rotate"
    ),
    f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/integration-delivery-logs",
    f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/postback-readiness",
)


def _exported_openapi_schema() -> dict:
    repo_root = Path(__file__).resolve().parents[3]
    exported_schema_path = repo_root / "backend" / "docs" / "api" / "openapi.json"
    assert exported_schema_path.exists(), "backend/docs/api/openapi.json must exist for frozen Phase 7 contracts"
    return json.loads(exported_schema_path.read_text(encoding="utf-8"))


def _read_text(relative_path: str) -> str:
    repo_root = Path(__file__).resolve().parents[3]
    return (repo_root / relative_path).read_text(encoding="utf-8")


def test_phase7_reporting_paths_exist_in_live_and_exported_openapi() -> None:
    live_paths = app.openapi()["paths"]
    exported_paths = _exported_openapi_schema()["paths"]

    for required_path in PHASE7_REQUIRED_PATHS:
        assert required_path in live_paths
        assert required_path in exported_paths


def test_phase7_freeze_docs_capture_outbox_lifecycle_terms() -> None:
    enum_registry = _read_text("docs/api/partner-platform-enum-registry.md")
    event_taxonomy = _read_text("docs/api/partner-platform-event-taxonomy.md")

    for required_term in (
        "pending_publication",
        "partially_published",
        "claimed",
        "submitted",
        "outbox_events",
        "outbox_publications",
        "reporting.mart.refreshed",
        "reporting_api_token",
        "postback_secret",
    ):
        assert required_term in enum_registry or required_term in event_taxonomy
