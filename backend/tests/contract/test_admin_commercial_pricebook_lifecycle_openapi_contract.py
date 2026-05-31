from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_admin_commercial_pricebook_lifecycle_paths_are_exposed() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert f"{API_V1_PREFIX}/admin/pricebooks" in paths
    assert f"{API_V1_PREFIX}/admin/pricebooks/{{pricebook_id}}" in paths
    assert f"{API_V1_PREFIX}/admin/pricebooks/{{pricebook_id}}/publish" in paths
    assert f"{API_V1_PREFIX}/admin/pricebooks/{{pricebook_id}}/schedule" in paths
    assert f"{API_V1_PREFIX}/admin/pricebooks/{{pricebook_id}}/rollback" in paths
    assert f"{API_V1_PREFIX}/admin/pricebooks/{{pricebook_key}}/history" in paths
    assert f"{API_V1_PREFIX}/admin/pricebooks/{{pricebook_id}}/audit" in paths
    assert f"{API_V1_PREFIX}/admin/pricebooks/{{pricebook_id}}/validate" in paths
    assert f"{API_V1_PREFIX}/admin/commercial-context/options" in paths


def test_admin_commercial_pricebook_lifecycle_components_are_exposed() -> None:
    schema = app.openapi()
    component_schemas = schema["components"]["schemas"]

    assert "AdminPricebookLifecycleResponse" in component_schemas
    assert "AdminPricebookHistoryResponse" in component_schemas
    assert "AdminPricebookValidationResponse" in component_schemas
    assert "CommercialContextOptionsResponse" in component_schemas
    assert "UpdateCommercialContextOptionsRequest" in component_schemas


def test_admin_commercial_pricebook_lifecycle_does_not_add_permission_schemas() -> None:
    schema = app.openapi()
    component_schemas = schema["components"]["schemas"]

    assert "CommercialPermission" not in component_schemas
    assert "PricebookPermission" not in component_schemas
