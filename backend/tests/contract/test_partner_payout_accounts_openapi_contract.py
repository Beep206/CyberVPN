from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_partner_payout_account_routes_exist_in_openapi() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    assert f"{API_V1_PREFIX}/partner-payout-accounts/" in paths
    assert f"{API_V1_PREFIX}/partner-payout-accounts/{{payout_account_id}}" in paths
    assert f"{API_V1_PREFIX}/partner-payout-accounts/{{payout_account_id}}/eligibility" in paths
    assert f"{API_V1_PREFIX}/partner-payout-accounts/{{payout_account_id}}/verify" in paths
    assert f"{API_V1_PREFIX}/partner-payout-accounts/{{payout_account_id}}/suspend" in paths
    assert f"{API_V1_PREFIX}/partner-payout-accounts/{{payout_account_id}}/archive" in paths
    assert f"{API_V1_PREFIX}/partner-payout-accounts/{{payout_account_id}}/make-default" in paths

    assert "PartnerPayoutAccountResponse" in components
    assert "PartnerPayoutAccountEligibilityResponse" in components
