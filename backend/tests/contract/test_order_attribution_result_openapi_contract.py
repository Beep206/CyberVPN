from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_order_attribution_result_paths_and_components_are_exposed() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    assert f"{API_V1_PREFIX}/attribution/orders/{{order_id}}/resolve" in paths
    assert f"{API_V1_PREFIX}/attribution/orders/{{order_id}}/result" in paths
    assert "OrderAttributionResultResponse" in components
