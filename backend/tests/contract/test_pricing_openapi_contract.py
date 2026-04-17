from src.main import app


def test_pricing_openapi_contains_canonical_paths() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert "/api/v1/plans/" in paths
    assert "/api/v1/addons/catalog" in paths
    assert "/api/v1/payments/checkout/quote" in paths
    assert "/api/v1/payments/checkout/commit" in paths
    assert "/api/v1/subscriptions/current/entitlements" in paths
    assert "/api/v1/subscriptions/current/upgrade/quote" in paths
    assert "/api/v1/subscriptions/current/upgrade" in paths
    assert "/api/v1/subscriptions/current/addons/quote" in paths
    assert "/api/v1/subscriptions/current/addons" in paths
    assert "/api/v1/trial/activate" in paths
    assert "/api/v1/trial/status" in paths


def test_plans_response_is_structured_catalog_shape() -> None:
    schema = app.openapi()
    plans_schema_ref = (
        schema["paths"]["/api/v1/plans/"]["get"]["responses"]["200"]["content"]["application/json"]["schema"][
            "items"
        ]["$ref"]
    )
    assert plans_schema_ref.endswith("/PlanResponse")

    plan_schema = schema["components"]["schemas"]["PlanResponse"]
    properties = plan_schema["properties"]
    assert "plan_code" in properties
    assert "display_name" in properties
    assert "traffic_policy" in properties
    assert "connection_modes" in properties
    assert "server_pool" in properties
    assert "invite_bundle" in properties


def test_checkout_quote_and_commit_expose_entitlements_snapshot() -> None:
    schema = app.openapi()
    quote_ref = schema["components"]["schemas"]["CheckoutQuoteResponse"]["properties"]["entitlements_snapshot"]["$ref"]
    commit_ref = schema["components"]["schemas"]["CheckoutCommitResponse"]["properties"]["entitlements_snapshot"][
        "$ref"
    ]

    assert quote_ref.endswith("/EntitlementsSnapshotResponse")
    assert commit_ref.endswith("/EntitlementsSnapshotResponse")

    entitlements_schema = schema["components"]["schemas"]["EntitlementsSnapshotResponse"]
    assert "effective_entitlements" in entitlements_schema["properties"]
    assert "addons" in entitlements_schema["properties"]
