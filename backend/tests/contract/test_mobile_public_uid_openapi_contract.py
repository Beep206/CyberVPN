from typing import Any

from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def _schema_ref(operation: dict[str, Any]) -> str:
    success_status = next(status for status in operation["responses"] if status.startswith("2"))
    return operation["responses"][success_status]["content"]["application/json"]["schema"]["$ref"]


def _component_name(ref: str) -> str:
    return ref.rsplit("/", 1)[-1]


def test_mobile_user_response_exposes_public_uid_contract() -> None:
    app.openapi_schema = None
    schema = app.openapi()
    me_operation = schema["paths"][f"{API_V1_PREFIX}/mobile/auth/me"]["get"]
    me_ref = _schema_ref(me_operation)

    assert _component_name(me_ref).endswith("UserResponse")

    user_response = schema["components"]["schemas"][_component_name(me_ref)]
    public_uid = user_response["properties"]["public_uid"]

    assert public_uid["type"] == "integer"
    assert public_uid["minimum"] == 10_000_000
    assert public_uid["maximum"] == 99_999_999
    assert "public_uid" in user_response["required"]


def test_mobile_auth_paths_reference_public_identity_response_shapes() -> None:
    app.openapi_schema = None
    schema = app.openapi()
    paths = schema["paths"]

    me_ref = _schema_ref(paths[f"{API_V1_PREFIX}/mobile/auth/me"]["get"])
    register_ref = _schema_ref(paths[f"{API_V1_PREFIX}/mobile/auth/register"]["post"])

    assert _component_name(me_ref).endswith("UserResponse")
    assert _component_name(register_ref).endswith("AuthResponse")
