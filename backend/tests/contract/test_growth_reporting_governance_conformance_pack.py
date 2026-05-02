from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_growth_reporting_governance_routes_exist_in_openapi() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    expected_paths = [
        f"{API_V1_PREFIX}/admin/growth-reporting/governance",
        f"{API_V1_PREFIX}/admin/growth-reporting/governance/export",
    ]

    for path in expected_paths:
        assert path in paths

    expected_components = [
        "AdminGrowthReportingGovernanceCoverageCountResponse",
        "AdminGrowthReportingGovernanceDecisionResponse",
        "AdminGrowthReportingGovernanceAuditEventResponse",
        "AdminGrowthReportingGovernanceOverviewResponse",
        "AdminGrowthReportingGovernanceExportResponse",
    ]

    for component in expected_components:
        assert component in components


def test_growth_reporting_governance_components_expose_coverage_and_export_fields() -> None:
    schema = app.openapi()
    components = schema["components"]["schemas"]

    coverage_properties = components["AdminGrowthReportingGovernanceCoverageCountResponse"]["properties"]
    assert "coverage_state" in coverage_properties
    assert "count" in coverage_properties

    decision_properties = components["AdminGrowthReportingGovernanceDecisionResponse"]["properties"]
    assert "delivery_id" in decision_properties
    assert "decision_kind" in decision_properties
    assert "status_reason" in decision_properties
    assert "can_export_artifact" in decision_properties
    assert "summary" in decision_properties

    audit_properties = components["AdminGrowthReportingGovernanceAuditEventResponse"]["properties"]
    assert "action" in audit_properties
    assert "actor_label" in audit_properties
    assert "reason_code" in audit_properties
    assert "changed_fields" in audit_properties

    overview_properties = components["AdminGrowthReportingGovernanceOverviewResponse"]["properties"]
    assert "generated_at" in overview_properties
    assert "coverage_gap_count" in overview_properties
    assert "coverage_counts" in overview_properties
    assert "recent_decisions" in overview_properties
    assert "recent_audit_events" in overview_properties
    assert "notes" in overview_properties

    export_properties = components["AdminGrowthReportingGovernanceExportResponse"]["properties"]
    assert "export_kind" in export_properties
    assert "filename" in export_properties
    assert "exported_at" in export_properties
    assert "overview" in export_properties
    assert "payload" in export_properties
