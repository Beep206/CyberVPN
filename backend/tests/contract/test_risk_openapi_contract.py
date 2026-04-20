from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_risk_foundation_openapi_paths_are_exposed() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert f"{API_V1_PREFIX}/security/risk-subjects" in paths
    assert f"{API_V1_PREFIX}/security/risk-subjects/{{risk_subject_id}}/identifiers" in paths
    assert f"{API_V1_PREFIX}/security/risk-subjects/{{risk_subject_id}}/links" in paths
    assert f"{API_V1_PREFIX}/security/risk-subjects/{{risk_subject_id}}/reviews" in paths
    assert f"{API_V1_PREFIX}/security/risk-reviews" in paths
    assert f"{API_V1_PREFIX}/security/eligibility/checks" in paths


def test_risk_foundation_openapi_components_are_exposed() -> None:
    schema = app.openapi()
    component_schemas = schema["components"]["schemas"]

    assert "RiskSubjectResponse" in component_schemas
    assert "RiskIdentifierResponse" in component_schemas
    assert "RiskLinkResponse" in component_schemas
    assert "RiskReviewResponse" in component_schemas
    assert "EligibilityCheckResponse" in component_schemas
