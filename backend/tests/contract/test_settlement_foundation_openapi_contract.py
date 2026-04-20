from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_settlement_foundation_routes_exist_in_openapi() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert f"{API_V1_PREFIX}/earning-events/" in paths
    assert f"{API_V1_PREFIX}/earning-events/{{event_id}}" in paths
    assert f"{API_V1_PREFIX}/earning-holds/" in paths
    assert f"{API_V1_PREFIX}/earning-holds/{{hold_id}}" in paths
    assert f"{API_V1_PREFIX}/earning-holds/{{hold_id}}/release" in paths
    assert f"{API_V1_PREFIX}/reserves/" in paths
    assert f"{API_V1_PREFIX}/reserves/{{reserve_id}}" in paths
    assert f"{API_V1_PREFIX}/reserves/{{reserve_id}}/release" in paths
