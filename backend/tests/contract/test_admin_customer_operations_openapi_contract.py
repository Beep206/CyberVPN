from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_admin_customer_operations_route_exists_in_openapi() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    assert f"{API_V1_PREFIX}/admin/mobile-users/{{user_id}}/operations-insight" in paths
    assert f"{API_V1_PREFIX}/admin/mobile-users/{{user_id}}/operations-insight/actions" in paths
    assert (
        f"{API_V1_PREFIX}/admin/mobile-users/{{user_id}}/operations-insight/exports/workspaces/{{partner_account_id}}"
        in paths
    )
    assert (
        f"{API_V1_PREFIX}/admin/mobile-users/{{user_id}}/operations-insight/exports/partner-statements/{{statement_id}}"
        in paths
    )
    assert (
        f"{API_V1_PREFIX}/admin/mobile-users/{{user_id}}/operations-insight/exports/payout-instructions/{{payout_instruction_id}}"
        in paths
    )
    assert (
        f"{API_V1_PREFIX}/admin/mobile-users/{{user_id}}/operations-insight/exports/payout-executions/{{payout_execution_id}}"
        in paths
    )
    assert "AdminCustomerOperationsInsightResponse" in components
    assert "AdminCustomerOperationsActionRequest" in components
    assert "AdminCustomerOperationsActionResponse" in components
    assert "AdminCustomerOperationsActionKind" in components
    assert "AdminCustomerOperationsExportKind" in components
    assert "AdminCustomerOperationsExportResponse" in components
    assert "AdminCustomerOperationsSectionAccessResponse" in components
    assert "AdminCustomerOrderInsightResponse" in components
    assert "AdminCustomerSettlementWorkspaceInsightResponse" in components
    assert "AdminCustomerServiceAccessInsightResponse" in components
    assert "AdminCustomerRiskSubjectInsightResponse" in components
    admin_customer_order_schema = components["AdminCustomerOrderInsightResponse"]
    assert "dispute_cases" in admin_customer_order_schema["properties"]
