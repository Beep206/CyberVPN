from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_policy_and_legal_foundation_openapi_paths_are_exposed() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert f"{API_V1_PREFIX}/policies/" in paths
    assert f"{API_V1_PREFIX}/policies/{{policy_version_id}}/approve" in paths
    assert f"{API_V1_PREFIX}/legal-documents/" in paths
    assert f"{API_V1_PREFIX}/legal-documents/sets" in paths
    assert f"{API_V1_PREFIX}/legal-documents/sets/resolve" in paths
    assert f"{API_V1_PREFIX}/policy-acceptance/" in paths
    assert f"{API_V1_PREFIX}/policy-acceptance/me" in paths


def test_policy_and_legal_foundation_openapi_components_are_exposed() -> None:
    schema = app.openapi()
    component_schemas = schema["components"]["schemas"]

    assert "PolicyVersionResponse" in component_schemas
    assert "LegalDocumentResponse" in component_schemas
    assert "LegalDocumentSetResponse" in component_schemas
    assert "AcceptedLegalDocumentResponse" in component_schemas
