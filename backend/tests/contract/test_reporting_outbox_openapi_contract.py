import json
from pathlib import Path

from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX

REPORTING_OUTBOX_PATHS = (
    f"{API_V1_PREFIX}/reporting/outbox-events",
    f"{API_V1_PREFIX}/reporting/outbox-events/{{event_id}}",
    f"{API_V1_PREFIX}/reporting/outbox-publications",
    f"{API_V1_PREFIX}/reporting/outbox-publications/claim",
    f"{API_V1_PREFIX}/reporting/outbox-publications/{{publication_id}}/submitted",
    f"{API_V1_PREFIX}/reporting/outbox-publications/{{publication_id}}/published",
    f"{API_V1_PREFIX}/reporting/outbox-publications/{{publication_id}}/failed",
)

REPORTING_OUTBOX_SCHEMAS = (
    "OutboxEventResponse",
    "OutboxPublicationResponse",
    "ClaimOutboxPublicationsRequest",
    "ClaimOutboxPublicationsResponse",
    "MarkOutboxPublicationSubmittedRequest",
    "MarkOutboxPublicationPublishedRequest",
    "MarkOutboxPublicationFailedRequest",
)


def _exported_openapi_schema() -> dict:
    repo_root = Path(__file__).resolve().parents[3]
    exported_schema_path = repo_root / "backend" / "docs" / "api" / "openapi.json"
    assert exported_schema_path.exists(), "backend/docs/api/openapi.json must exist for frozen reporting contracts"
    return json.loads(exported_schema_path.read_text(encoding="utf-8"))


def test_reporting_outbox_routes_exist_in_live_openapi() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    for path in REPORTING_OUTBOX_PATHS:
        assert path in paths


def test_reporting_outbox_schemas_exist_in_exported_openapi() -> None:
    schema = _exported_openapi_schema()
    components = schema["components"]["schemas"]

    for schema_name in REPORTING_OUTBOX_SCHEMAS:
        assert schema_name in components
