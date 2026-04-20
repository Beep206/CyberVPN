import json
from pathlib import Path

from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX

REQUIRED_PATHS = (
    f"{API_V1_PREFIX}/renewal-orders/resolve",
    f"{API_V1_PREFIX}/renewal-orders/{{renewal_order_id}}",
    f"{API_V1_PREFIX}/renewal-orders/by-order/{{order_id}}",
)

REQUIRED_SCHEMAS = (
    "ResolveRenewalOrderRequest",
    "RenewalOrderResponse",
)


def _exported_openapi_schema() -> dict:
    repo_root = Path(__file__).resolve().parents[3]
    exported_schema_path = repo_root / "backend" / "docs" / "api" / "openapi.json"
    assert exported_schema_path.exists(), "backend/docs/api/openapi.json must exist for frozen Phase 3 contracts"
    return json.loads(exported_schema_path.read_text(encoding="utf-8"))


def test_live_openapi_contains_renewal_order_paths() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    for required_path in REQUIRED_PATHS:
        assert required_path in paths


def test_exported_openapi_contains_renewal_order_paths_and_schemas() -> None:
    schema = _exported_openapi_schema()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    for required_path in REQUIRED_PATHS:
        assert required_path in paths

    for schema_name in REQUIRED_SCHEMAS:
        assert schema_name in components
