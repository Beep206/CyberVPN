"""OpenAPI contract tests for customer public account UID."""

from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_mobile_auth_user_response_exposes_public_uid_contract() -> None:
    schema = app.openapi()
    me_response_schema = schema["paths"][f"{API_V1_PREFIX}/mobile/auth/me"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    user_response_component_name = me_response_schema["$ref"].rsplit("/", maxsplit=1)[-1]
    components = schema["components"]["schemas"]
    user_response = components[user_response_component_name]
    properties = user_response["properties"]

    assert "public_uid" in properties
    assert properties["public_uid"]["type"] == "integer"
    assert properties["public_uid"]["minimum"] == 10_000_000
    assert properties["public_uid"]["maximum"] == 99_999_999
    assert "public_uid" in user_response["required"]


def test_mobile_auth_identity_endpoints_reference_user_response_with_public_uid() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    me_response_schema = paths[f"{API_V1_PREFIX}/mobile/auth/me"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]

    assert me_response_schema["$ref"].endswith("UserResponse")

    register_response_schema = paths[f"{API_V1_PREFIX}/mobile/auth/register"]["post"]["responses"]["201"][
        "content"
    ]["application/json"]["schema"]
    assert register_response_schema == {"$ref": "#/components/schemas/AuthResponse"}
