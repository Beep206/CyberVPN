from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_phase8_operational_overlay_paths_are_exposed() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert f"{API_V1_PREFIX}/policy-acceptance/" in paths
    assert f"{API_V1_PREFIX}/policy-acceptance/me" in paths
    assert f"{API_V1_PREFIX}/policy-acceptance/{{acceptance_id}}" in paths
    assert f"{API_V1_PREFIX}/traffic-declarations/" in paths
    assert f"{API_V1_PREFIX}/traffic-declarations/{{traffic_declaration_id}}" in paths
    assert f"{API_V1_PREFIX}/creative-approvals/" in paths
    assert f"{API_V1_PREFIX}/creative-approvals/{{creative_approval_id}}" in paths
    assert f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/traffic-declarations" in paths
    assert f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/creative-approvals" in paths
    assert (
        f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/review-requests/{{review_request_id}}/responses"
        in paths
    )
    assert f"{API_V1_PREFIX}/dispute-cases/" in paths
    assert f"{API_V1_PREFIX}/dispute-cases/{{dispute_case_id}}" in paths
    assert f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/cases/{{case_id}}/responses" in paths
    assert f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/cases/{{case_id}}/ready-for-ops" in paths


def test_phase8_operational_overlay_components_are_exposed() -> None:
    schema = app.openapi()
    component_schemas = schema["components"]["schemas"]

    assert "AcceptedLegalDocumentResponse" in component_schemas
    assert "CreateTrafficDeclarationRequest" in component_schemas
    assert "TrafficDeclarationResponse" in component_schemas
    assert "CreateCreativeApprovalRequest" in component_schemas
    assert "CreativeApprovalResponse" in component_schemas
    assert "SubmitPartnerWorkspaceTrafficDeclarationRequest" in component_schemas
    assert "SubmitPartnerWorkspaceCreativeApprovalRequest" in component_schemas
    assert "PartnerWorkspaceThreadEventResponse" in component_schemas
    assert "SubmitPartnerWorkspaceReviewRequestResponseRequest" in component_schemas
    assert "SubmitPartnerWorkspaceCaseResponseRequest" in component_schemas
    assert "MarkPartnerWorkspaceCaseReadyForOpsRequest" in component_schemas
    assert "CreateDisputeCaseRequest" in component_schemas
    assert "DisputeCaseResponse" in component_schemas
