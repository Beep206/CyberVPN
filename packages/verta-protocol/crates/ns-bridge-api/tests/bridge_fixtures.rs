use ns_bridge_api::{
    BridgeApiError, DeviceRegisterRequest, ManifestRequestMode, TokenExchangeRequest,
    parse_manifest_request,
};
use serde::Deserialize;
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Deserialize)]
struct ManifestRequestFixture {
    authorization_header: Option<String>,
    subscription_token: Option<String>,
}

fn load_fixture(path: &str) -> ManifestRequestFixture {
    serde_json::from_str(&load_fixture_text(path)).expect("bridge fixture json should parse")
}

fn load_fixture_text(relative: &str) -> String {
    let mut root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    root.pop();
    root.pop();
    fs::read_to_string(root.join("fixtures").join(relative))
        .expect("bridge fixture should be readable")
}

#[test]
fn parses_bootstrap_manifest_request_fixture() {
    let fixture = load_fixture("bridge/bootstrap/BG-MANIFEST-FETCH-BOOTSTRAP-001.json");
    let mode = parse_manifest_request(
        fixture.subscription_token.as_deref(),
        fixture.authorization_header.as_deref(),
    )
    .expect("bootstrap manifest request fixture should parse");

    assert!(matches!(mode, ManifestRequestMode::Bootstrap { .. }));
}

#[test]
fn parses_refresh_manifest_request_fixture() {
    let fixture = load_fixture("bridge/bootstrap/BG-MANIFEST-FETCH-REFRESH-002.json");
    let mode = parse_manifest_request(
        fixture.subscription_token.as_deref(),
        fixture.authorization_header.as_deref(),
    )
    .expect("refresh manifest request fixture should parse");

    assert!(matches!(mode, ManifestRequestMode::Refresh { .. }));
}

#[test]
fn rejects_conflicting_manifest_request_fixture() {
    let fixture = load_fixture("bridge/bootstrap/BG-MANIFEST-FETCH-CONFLICT-003.json");
    let error = parse_manifest_request(
        fixture.subscription_token.as_deref(),
        fixture.authorization_header.as_deref(),
    )
    .expect_err("conflicting manifest request fixture should be rejected");

    assert!(matches!(
        error,
        BridgeApiError::ConflictingManifestAuthModes
    ));
}

#[test]
fn parses_valid_device_register_fixture() {
    let body = load_fixture_text("bridge/device/BG-DEVICE-REGISTER-VALID-004.json");
    let request: DeviceRegisterRequest =
        serde_json::from_str(&body).expect("device register fixture should parse");

    assert_eq!(request.device_id, "device-1");
    assert_eq!(request.platform, "windows");
    assert_eq!(request.requested_capabilities, vec![1, 2]);
}

#[test]
fn rejects_unknown_field_in_device_register_fixture() {
    let body = load_fixture_text("bridge/device/BG-DEVICE-REGISTER-UNKNOWNFIELD-005.json");
    let error = serde_json::from_str::<DeviceRegisterRequest>(&body)
        .expect_err("unknown field should be rejected");

    assert!(error.to_string().contains("unexpected_field"));
}

#[test]
fn parses_valid_token_exchange_fixture() {
    let body = load_fixture_text("bridge/token/BG-TOKEN-EXCHANGE-VALID-006.json");
    let request: TokenExchangeRequest =
        serde_json::from_str(&body).expect("token exchange fixture should parse");

    assert_eq!(request.manifest_id, "man-2026-04-01-001");
    assert_eq!(request.device_id, "device-1");
    assert_eq!(request.requested_capabilities, vec![1, 2]);
}

#[test]
fn rejects_missing_refresh_credential_in_token_exchange_fixture() {
    let body = load_fixture_text("bridge/token/BG-TOKEN-EXCHANGE-MISSINGREFRESH-007.json");
    let error = serde_json::from_str::<TokenExchangeRequest>(&body)
        .expect_err("missing refresh_credential should be rejected");

    assert!(error.to_string().contains("refresh_credential"));
}
