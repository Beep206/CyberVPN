from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_order_explainability_path_and_components_are_exposed() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    assert f"{API_V1_PREFIX}/orders/{{order_id}}/explainability" in paths
    assert "OrderExplainabilityResponse" in components
    assert "CommissionabilityEvaluationResponse" in components
    assert "OrderExplainabilityOrderSummary" in components
