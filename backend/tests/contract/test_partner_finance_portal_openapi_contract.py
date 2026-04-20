from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_partner_finance_portal_routes_exist_in_openapi() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    assert f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/payout-accounts" in paths
    assert (
        f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/payout-accounts/{{payout_account_id}}/eligibility"
        in paths
    )
    assert (
        f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/payout-accounts/{{payout_account_id}}/make-default"
        in paths
    )
    assert f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/payout-history" in paths

    assert "PartnerWorkspacePayoutAccountResponse" in components
    assert "CreatePartnerWorkspacePayoutAccountRequest" in components
    assert "PartnerWorkspacePayoutAccountEligibilityResponse" in components
    assert "PartnerWorkspacePayoutHistoryResponse" in components
