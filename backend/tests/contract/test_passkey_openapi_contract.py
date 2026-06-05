from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_passkey_openapi_paths_are_exposed() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert f"{API_V1_PREFIX}/auth/passkeys/policy" in paths
    assert f"{API_V1_PREFIX}/auth/passkeys/registration/options" in paths
    assert f"{API_V1_PREFIX}/auth/passkeys/registration/verify" in paths
    assert f"{API_V1_PREFIX}/auth/passkeys/authentication/options" in paths
    assert f"{API_V1_PREFIX}/auth/passkeys/authentication/verify" in paths
    assert f"{API_V1_PREFIX}/auth/passkeys/reauthentication/options" in paths
    assert f"{API_V1_PREFIX}/auth/passkeys/reauthentication/verify" in paths
    assert f"{API_V1_PREFIX}/security/passkeys/policy" in paths
    assert f"{API_V1_PREFIX}/security/passkeys/compliance" in paths
    assert f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/security/passkeys/policy" in paths
    assert f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/security/passkeys/compliance" in paths
    assert "patch" in paths[f"{API_V1_PREFIX}/security/passkeys/policy"]
    assert "patch" in paths[f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/security/passkeys/policy"]


def test_passkey_openapi_components_are_exposed() -> None:
    schema = app.openapi()
    components = schema["components"]["schemas"]

    assert "PasskeyPolicyResponse" in components
    assert "PasskeyOptionsResponse" in components
    assert "PasskeyAuthenticationVerifyResponse" in components
    assert "PasskeyCredentialResponse" in components
    assert "PasskeyComplianceResponse" in components
    assert "PasskeyComplianceCredentialResponse" in components
    assert "PartnerWorkspacePasskeyPolicyResponse" in components
    assert "PartnerWorkspacePasskeyComplianceResponse" in components
    assert "UpdateAdminPasskeyPolicyRequest" in components
    assert "UpdatePartnerWorkspacePasskeyPolicyRequest" in components

    auth_verify_response = components["PasskeyAuthenticationVerifyResponse"]
    properties = auth_verify_response["properties"]
    assert "access_token" not in properties
    assert "refresh_token" not in properties
    assert "expires_in" not in properties
    assert "token_type" not in properties
    assert set(properties) == {
        "auth_realm_id",
        "auth_realm_key",
        "audience",
        "principal_type",
        "scope_family",
        "requires_2fa",
        "tfa_token",
    }


def test_passkey_authentication_verify_uses_tokenless_response_schema() -> None:
    schema = app.openapi()
    operation = schema["paths"][f"{API_V1_PREFIX}/auth/passkeys/authentication/verify"]["post"]

    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/PasskeyAuthenticationVerifyResponse"
    }


def test_partner_workspace_settings_update_contract_excludes_passkey_policy_fields() -> None:
    schema = app.openapi()
    properties = schema["components"]["schemas"]["UpdatePartnerWorkspaceSettingsRequest"]["properties"]

    assert "prefer_passkeys" not in properties
    assert "require_mfa_for_workspace" not in properties
