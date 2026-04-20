from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_partner_statement_and_settlement_period_routes_exist_in_openapi() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    assert f"{API_V1_PREFIX}/settlement-periods/" in paths
    assert f"{API_V1_PREFIX}/settlement-periods/{{settlement_period_id}}" in paths
    assert f"{API_V1_PREFIX}/settlement-periods/{{settlement_period_id}}/close" in paths
    assert f"{API_V1_PREFIX}/settlement-periods/{{settlement_period_id}}/reopen" in paths
    assert f"{API_V1_PREFIX}/partner-statements/generate" in paths
    assert f"{API_V1_PREFIX}/partner-statements/" in paths
    assert f"{API_V1_PREFIX}/partner-statements/{{statement_id}}" in paths
    assert f"{API_V1_PREFIX}/partner-statements/{{statement_id}}/close" in paths
    assert f"{API_V1_PREFIX}/partner-statements/{{statement_id}}/reopen" in paths
    assert f"{API_V1_PREFIX}/partner-statements/{{statement_id}}/adjustments" in paths
    assert f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/statements" in paths
    assert f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/programs" in paths
    assert f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/codes" in paths
    assert f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/conversion-records" in paths
    assert (
        f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/conversion-records/{{order_id}}/explainability"
        in paths
    )
    assert f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/analytics-metrics" in paths
    assert f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/report-exports" in paths
    assert (
        f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/report-exports/{{export_id}}/schedule"
        in paths
    )
    assert f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/review-requests" in paths
    assert f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/traffic-declarations" in paths
    assert f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/cases" in paths

    assert "SettlementPeriodResponse" in components
    assert "PartnerStatementResponse" in components
    assert "StatementAdjustmentResponse" in components
    assert "PartnerWorkspaceProgramsResponse" in components
    assert "PartnerWorkspaceProgramLaneResponse" in components
    assert "PartnerWorkspaceProgramReadinessItemResponse" in components
    assert "PartnerWorkspaceCodeResponse" in components
    assert "PartnerWorkspaceConversionRecordResponse" in components
    assert "PartnerWorkspaceAnalyticsMetricResponse" in components
    assert "PartnerWorkspaceReportExportResponse" in components
    assert "SchedulePartnerWorkspaceReportExportRequest" in components
    assert "PartnerWorkspaceReviewRequestResponse" in components
    assert "PartnerWorkspaceTrafficDeclarationResponse" in components
    assert "PartnerWorkspaceCaseResponse" in components
    assert "OrderExplainabilityResponse" in components
