from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_risk_governance_workflow_openapi_paths_are_exposed() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert f"{API_V1_PREFIX}/security/risk-reviews/queue" in paths
    assert f"{API_V1_PREFIX}/security/risk-reviews/{{risk_review_id}}" in paths
    assert f"{API_V1_PREFIX}/security/risk-reviews/{{risk_review_id}}/attachments" in paths
    assert f"{API_V1_PREFIX}/security/risk-reviews/{{risk_review_id}}/resolve" in paths
    assert f"{API_V1_PREFIX}/security/governance-actions" in paths


def test_risk_governance_workflow_openapi_components_are_exposed() -> None:
    schema = app.openapi()
    component_schemas = schema["components"]["schemas"]

    assert "RiskReviewQueueItemResponse" in component_schemas
    assert "RiskReviewDetailResponse" in component_schemas
    assert "RiskReviewAttachmentResponse" in component_schemas
    assert "AttachRiskReviewAttachmentRequest" in component_schemas
    assert "ResolveRiskReviewRequest" in component_schemas
    assert "GovernanceActionResponse" in component_schemas
    assert "CreateGovernanceActionRequest" in component_schemas
