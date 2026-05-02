from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_growth_codes_conformance_surface_exists_in_openapi() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    expected_paths = [
        f"{API_V1_PREFIX}/codes/resolve",
        f"{API_V1_PREFIX}/invites/redeem",
        f"{API_V1_PREFIX}/gifts/purchase/quote",
        f"{API_V1_PREFIX}/gifts/purchase/commit",
        f"{API_V1_PREFIX}/gifts/redeem",
        f"{API_V1_PREFIX}/admin/growth-codes/lookup",
        f"{API_V1_PREFIX}/admin/growth-signals/overview",
        f"{API_V1_PREFIX}/admin/growth-signals/abuse-queue",
        f"{API_V1_PREFIX}/quotes/",
        f"{API_V1_PREFIX}/checkout-sessions/",
        f"{API_V1_PREFIX}/orders/commit",
        f"{API_V1_PREFIX}/entitlements/current",
    ]

    for path in expected_paths:
        assert path in paths

    expected_components = [
        "ResolveGrowthCodeResponse",
        "CheckoutCodeResolutionResponse",
        "InviteCodeResponse",
        "GiftPurchaseQuoteResponse",
        "GiftPurchaseCommitResponse",
        "GiftRedeemResponse",
        "AdminGrowthCodeLookupResponse",
        "AdminGrowthSignalsOverviewResponse",
        "AdminGrowthAbuseSignalsResponse",
        "CheckoutQuoteResponse",
        "CurrentEntitlementStateResponse",
    ]

    for component in expected_components:
        assert component in components


def test_growth_codes_conformance_components_expose_target_state_fields() -> None:
    schema = app.openapi()
    components = schema["components"]["schemas"]

    invite_properties = components["InviteCodeResponse"]["properties"]
    assert "entitlement_grant_id" in invite_properties
    assert "entitlement_snapshot" in invite_properties

    lookup_properties = components["AdminGrowthCodeLookupResponse"]["properties"]
    assert "lifecycle_summary" in lookup_properties
    assert "issuances" in lookup_properties
    assert "touchpoints" in lookup_properties
    assert "signup_attributions" in lookup_properties
    assert "redemptions" in lookup_properties
    assert "rewards" in lookup_properties
    assert "resolution_events" in lookup_properties

    gift_redeem_properties = components["GiftRedeemResponse"]["properties"]
    assert "entitlement_grant_id" in gift_redeem_properties
    assert "entitlement_snapshot" in gift_redeem_properties

    resolve_code_properties = components["ResolveGrowthCodeResponse"]["properties"]
    assert "wrong_context_target" in resolve_code_properties
    assert "user_message_key" in resolve_code_properties

    checkout_code_resolution_properties = components["CheckoutCodeResolutionResponse"]["properties"]
    assert "wrong_context_target" in checkout_code_resolution_properties
    assert "reservation_id" in checkout_code_resolution_properties
    assert "user_message_key" in checkout_code_resolution_properties
