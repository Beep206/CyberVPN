from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_partner_session_bootstrap_route_exists_in_openapi() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    assert f"{API_V1_PREFIX}/partner-session/bootstrap" in paths
    assert "PartnerSessionBootstrapResponse" in components
    assert "PartnerSessionPrincipalResponse" in components
    assert "PartnerSessionBootstrapCounterResponse" in components
    assert "PartnerSessionBootstrapPendingTaskResponse" in components
    assert "PartnerSessionBootstrapBlockedReasonResponse" in components
