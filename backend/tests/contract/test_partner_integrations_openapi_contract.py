from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_partner_integrations_and_reporting_snapshot_routes_exist_in_openapi() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    assert f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/integration-credentials" in paths
    assert (
        f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/integration-credentials/"
        "{credential_kind}/rotate"
    ) in paths
    assert f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/integration-delivery-logs" in paths
    assert f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/postback-readiness" in paths
    assert f"{API_V1_PREFIX}/reporting/partner-workspaces/{{workspace_id}}/snapshot" in paths

    assert "PartnerWorkspaceIntegrationCredentialResponse" in components
    assert "RotatePartnerWorkspaceIntegrationCredentialRequest" in components
    assert "RotatePartnerWorkspaceIntegrationCredentialResponse" in components
    assert "PartnerWorkspaceIntegrationDeliveryLogResponse" in components
    assert "PartnerWorkspacePostbackReadinessResponse" in components
    assert "PartnerReportingApiSnapshotResponse" in components
