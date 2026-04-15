use ns_carrier_h3::{H3DatagramRollout, H3RequestKind};
use ns_client_runtime::{ClientRuntimeConfig, ClientRuntimeError, build_launch_plan};
use ns_core::{CarrierProfileId, DeviceBindingId};
use ns_testkit::{fixed_test_now, fixture_manifest_trust_store, load_fixture_text};
use url::Url;

fn config() -> ClientRuntimeConfig {
    config_with_rollout(H3DatagramRollout::Automatic)
}

fn config_with_rollout(datagram_rollout: H3DatagramRollout) -> ClientRuntimeConfig {
    ClientRuntimeConfig {
        manifest_url: Url::parse("https://bridge.example/v0/manifest")
            .expect("fixture manifest url should parse"),
        device_id: DeviceBindingId::new("device-1")
            .expect("fixture device binding id should be valid"),
        client_version: "0.1.0".to_owned(),
        selected_carrier_profile: CarrierProfileId::new("carrier-primary")
            .expect("fixture carrier profile should be valid"),
        datagram_rollout,
    }
}

#[test]
fn builds_a_launch_plan_from_the_valid_signed_manifest_fixture() {
    let manifest = load_fixture_text("manifest/v1/valid/MF-MANIFEST-VALID-001.json");

    let plan = build_launch_plan(
        &config(),
        &manifest,
        &fixture_manifest_trust_store(),
        fixed_test_now(),
    )
    .expect("valid signed manifest fixture should produce a launch plan");

    assert_eq!(plan.endpoint_host, "edge.example.net");
    assert_eq!(plan.endpoint_port, 443);
}

#[test]
fn builds_manifest_driven_h3_request_templates_from_the_launch_plan() {
    let manifest = load_fixture_text("manifest/v1/valid/MF-MANIFEST-VALID-001.json");

    let plan = build_launch_plan(
        &config(),
        &manifest,
        &fixture_manifest_trust_store(),
        fixed_test_now(),
    )
    .expect("valid signed manifest fixture should produce a launch plan");
    let transport = plan.h3_transport_config();
    let control = transport
        .request_template(H3RequestKind::Control)
        .expect("control request template should build");
    let relay = transport
        .request_template(H3RequestKind::Relay)
        .expect("relay request template should build");

    assert_eq!(control.authority(), "origin.edge.example.net:8443");
    assert_eq!(control.path(), "/ns/control");
    assert_eq!(relay.path(), "/ns/relay");
    assert_eq!(
        control.headers().get("x-verta-profile"),
        Some(&"carrier-primary".to_owned())
    );
    assert_eq!(transport.connect_backoff.initial_ms, 500);
    assert_eq!(transport.connect_backoff.max_ms, 10_000);
    assert_eq!(transport.datagram_rollout, H3DatagramRollout::Automatic);
}

#[test]
fn rejects_the_tampered_manifest_fixture_before_planning() {
    let manifest = load_fixture_text("manifest/v1/invalid/MF-MANIFEST-BADSIG-002.json");

    let error = build_launch_plan(
        &config(),
        &manifest,
        &fixture_manifest_trust_store(),
        fixed_test_now(),
    )
    .expect_err("tampered manifest fixture should be rejected");

    assert!(matches!(error, ClientRuntimeError::Manifest(_)));
}

#[test]
fn rejects_manifest_fixture_when_the_selected_profile_has_no_signed_endpoint() {
    let manifest = load_fixture_text("manifest/v1/valid/MF-DISABLEDPROFILE-006.json");

    let error = build_launch_plan(
        &config(),
        &manifest,
        &fixture_manifest_trust_store(),
        fixed_test_now(),
    )
    .expect_err("disabled-profile fixture should fail closed during launch planning");

    assert!(matches!(
        error,
        ClientRuntimeError::NoEndpointForProfile(profile) if profile == "carrier-primary"
    ));
}

#[test]
fn launch_planning_supports_operator_disabled_datagram_rollout() {
    let manifest = load_fixture_text("manifest/v1/valid/MF-MANIFEST-VALID-001.json");
    let mut config = config();
    config.datagram_rollout = H3DatagramRollout::Disabled;

    let plan = build_launch_plan(
        &config,
        &manifest,
        &fixture_manifest_trust_store(),
        fixed_test_now(),
    )
    .expect("valid signed manifest fixture should still produce a launch plan");

    let transport = plan.h3_transport_config();
    assert!(!transport.datagram_runtime_enabled());
    assert_eq!(
        transport.advertised_datagram_mode(true),
        ns_core::DatagramMode::DisabledByPolicy
    );
}

#[test]
fn launch_planning_supports_operator_canary_datagram_rollout() {
    let plan = build_launch_plan(
        &config_with_rollout(H3DatagramRollout::Canary),
        &load_fixture_text("manifest/v1/valid/MF-MANIFEST-VALID-001.json"),
        &fixture_manifest_trust_store(),
        fixed_test_now(),
    )
    .expect("valid manifest fixture should still build a launch plan under canary rollout");

    let transport = plan.h3_transport_config();
    assert!(transport.datagram_runtime_enabled());
    assert_eq!(transport.rollout_stage_label(), "canary");
    assert_eq!(
        transport.advertised_datagram_mode(true),
        ns_core::DatagramMode::AvailableAndEnabled
    );
}
