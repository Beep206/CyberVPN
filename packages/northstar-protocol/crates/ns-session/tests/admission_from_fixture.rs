use hex::decode;
use ns_core::{Capability, CarrierProfileId, ManifestId};
use ns_session::{GatewayAdmissionContext, SessionError};
use ns_wire::{Frame, FrameCodec};
use serde::Deserialize;
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Deserialize)]
struct HelloFixture {
    hex: String,
}

fn load_hello(relative: &str) -> ns_wire::ClientHello {
    let fixture: HelloFixture = serde_json::from_str(&load_fixture_text(relative))
        .expect("hello fixture json should parse");
    let bytes = decode(fixture.hex).expect("hello fixture hex should decode");
    let frame = FrameCodec::decode(&bytes).expect("hello fixture should decode");
    match frame {
        Frame::ClientHello(hello) => hello,
        other => panic!("expected client hello fixture, got {other:?}"),
    }
}

fn load_fixture_text(relative: &str) -> String {
    let mut root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    root.pop();
    root.pop();
    fs::read_to_string(root.join("fixtures").join(relative))
        .expect("session fixture should be readable")
}

#[test]
fn rejects_device_binding_mismatch_from_fixture() {
    let hello = load_hello("wire/v1/valid/NS-FX-HELLO-001.json");
    let context = GatewayAdmissionContext {
        manifest_id: ManifestId::new("man-2026-04-01-001")
            .expect("fixture manifest id should be valid"),
        device_binding_id: Some("device-other".to_owned()),
        allowed_core_versions: vec![1],
        allowed_capabilities: vec![Capability::TcpRelay, Capability::UdpRelay],
        allowed_carrier_profiles: vec![
            CarrierProfileId::new("carrier-primary")
                .expect("fixture carrier profile should be valid"),
        ],
    };

    let error = context
        .validate_client_hello(&hello)
        .expect_err("device-binding mismatch should be rejected");
    assert!(matches!(error, SessionError::DeviceBindingMismatch));
}

#[test]
fn rejects_capability_drift_from_fixture() {
    let hello = load_hello("wire/v1/valid/NS-FX-HELLO-001.json");
    let context = GatewayAdmissionContext {
        manifest_id: ManifestId::new("man-2026-04-01-001")
            .expect("fixture manifest id should be valid"),
        device_binding_id: Some("device-1".to_owned()),
        allowed_core_versions: vec![1],
        allowed_capabilities: vec![Capability::TcpRelay],
        allowed_carrier_profiles: vec![
            CarrierProfileId::new("carrier-primary")
                .expect("fixture carrier profile should be valid"),
        ],
    };

    let error = context
        .validate_client_hello(&hello)
        .expect_err("unsupported capability should be rejected");
    assert!(matches!(error, SessionError::UnsupportedCapabilities));
}

#[test]
fn rejects_no_supported_version_overlap_from_fixture() {
    let hello = load_hello("wire/v1/valid/NS-FX-HELLO-NOOVERLAP-002.json");
    let context = GatewayAdmissionContext {
        manifest_id: ManifestId::new("man-2026-04-01-001")
            .expect("fixture manifest id should be valid"),
        device_binding_id: Some("device-1".to_owned()),
        allowed_core_versions: vec![1],
        allowed_capabilities: vec![Capability::TcpRelay, Capability::UdpRelay],
        allowed_carrier_profiles: vec![
            CarrierProfileId::new("carrier-primary")
                .expect("fixture carrier profile should be valid"),
        ],
    };

    let error = context
        .validate_client_hello(&hello)
        .expect_err("no-overlap hello fixture should be rejected");
    assert!(matches!(
        error,
        SessionError::NoSupportedVersionOverlap {
            min_version: 2,
            max_version: 2
        }
    ));
}
