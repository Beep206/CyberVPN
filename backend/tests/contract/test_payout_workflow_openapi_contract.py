from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_payout_workflow_routes_exist_in_openapi() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    assert f"{API_V1_PREFIX}/payouts/instructions" in paths
    assert f"{API_V1_PREFIX}/payouts/instructions/{{payout_instruction_id}}" in paths
    assert f"{API_V1_PREFIX}/payouts/instructions/{{payout_instruction_id}}/approve" in paths
    assert f"{API_V1_PREFIX}/payouts/instructions/{{payout_instruction_id}}/reject" in paths
    assert f"{API_V1_PREFIX}/payouts/executions" in paths
    assert f"{API_V1_PREFIX}/payouts/executions/{{payout_execution_id}}" in paths
    assert f"{API_V1_PREFIX}/payouts/executions/{{payout_execution_id}}/submit" in paths
    assert f"{API_V1_PREFIX}/payouts/executions/{{payout_execution_id}}/complete" in paths
    assert f"{API_V1_PREFIX}/payouts/executions/{{payout_execution_id}}/fail" in paths
    assert f"{API_V1_PREFIX}/payouts/executions/{{payout_execution_id}}/reconcile" in paths

    assert "PayoutInstructionResponse" in components
    assert "PayoutExecutionResponse" in components
