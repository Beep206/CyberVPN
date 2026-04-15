#![forbid(unsafe_code)]

use bytes::Bytes;
use ed25519_dalek::SigningKey;
use jsonwebtoken::jwk::{
    AlgorithmParameters, CommonParameters, Jwk, JwkSet, OctetKeyPairParameters, OctetKeyPairType,
};
use ns_auth::{SessionTokenVerifier, TrustedKeySet, VerifierConfig};
use ns_core::{
    Capability, CarrierKind, CarrierProfileId, DeviceBindingId, ManifestId, SessionMode,
};
use ns_manifest::{
    CarrierProfile, ClientConstraints, ConnectBackoff, DevicePolicy, GatewayEndpoint, HttpTemplate,
    HttpTemplateMethod, ManifestCarrierKind, ManifestDocument, ManifestSignature, ManifestSigner,
    ManifestTrustStore, ManifestUser, RefreshMode, RefreshPolicy, RetryPolicy, RoutingFailoverMode,
    RoutingPolicy, RoutingSelectionMode, TelemetryPolicy, TokenService, ZeroRttPolicy,
};
use ns_remnawave_adapter::{AccountLifecycle, AccountSnapshot, BootstrapSubject, VertaAccess};
use ns_session::{CarrierSessionInfo, TransportError, TransportErrorKind};
use ns_wire::{ClientHello, Frame};
use serde::Serialize;
use std::collections::{BTreeMap, VecDeque};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use time::OffsetDateTime;
use url::Url;

pub const FIXTURE_MANIFEST_KEY_ID: &str = "fixture-manifest-key-1";
pub const FIXTURE_TOKEN_KEY_ID: &str = "fixture-token-key-1";
pub const UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA: &str = "udp_rollout_operator_verdict";
pub const UDP_ROLLOUT_OPERATOR_VERDICT_SCHEMA_VERSION: u8 = 20;
pub const UDP_ROLLOUT_OPERATOR_VERDICT_FAMILY: &str = "udp_rollout_operator_decision";
pub const UDP_ROLLOUT_DECISION_SCOPE_HOST: &str = "host";
pub const UDP_ROLLOUT_DECISION_SCOPE_MATRIX: &str = "matrix";
pub const UDP_ROLLOUT_DECISION_SCOPE_RELEASE_WORKFLOW: &str = "release_workflow";
pub const UDP_ROLLOUT_DECISION_SCOPE_DEPLOYMENT_SIGNOFF: &str = "deployment_signoff";
pub const UDP_ROLLOUT_DECISION_SCOPE_RELEASE_PREP: &str = "release_prep";
pub const UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_SIGNOFF: &str = "release_candidate_signoff";
pub const UDP_ROLLOUT_DECISION_SCOPE_RELEASE_BURN_IN: &str = "release_burn_in";
pub const UDP_ROLLOUT_DECISION_SCOPE_RELEASE_SOAK: &str = "release_soak";
pub const UDP_ROLLOUT_DECISION_SCOPE_RELEASE_GATE: &str = "release_gate";
pub const UDP_ROLLOUT_DECISION_SCOPE_RELEASE_READINESS_BURNDOWN: &str =
    "release_readiness_burndown";
pub const UDP_ROLLOUT_DECISION_SCOPE_RELEASE_STABILITY_SIGNOFF: &str = "release_stability_signoff";
pub const UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_CONSOLIDATION: &str =
    "release_candidate_consolidation";
pub const UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_HARDENING: &str =
    "release_candidate_hardening";
pub const UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_EVIDENCE_FREEZE: &str =
    "release_candidate_evidence_freeze";
pub const UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_SIGNOFF_CLOSURE: &str =
    "release_candidate_signoff_closure";
pub const UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_STABILIZATION: &str =
    "release_candidate_stabilization";
pub const UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_READINESS: &str =
    "release_candidate_readiness";
pub const UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_ACCEPTANCE: &str =
    "release_candidate_acceptance";
pub const UDP_ROLLOUT_DECISION_SCOPE_RELEASE_CANDIDATE_CERTIFICATION: &str =
    "release_candidate_certification";
pub const UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_COMPATIBLE_HOST: &str =
    "compatible_host_interop_lab";
pub const UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_WAN_STAGING: &str = "wan_staging_interop";
pub const UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_NET_CHAOS: &str = "net_chaos_campaign";
pub const UDP_ROLLOUT_GATE_STATE_REASON_READY: &str = "all_required_inputs_passed";
pub const UDP_ROLLOUT_GATE_STATE_REASON_MISSING_REQUIRED_INPUTS: &str = "missing_required_inputs";
pub const UDP_ROLLOUT_GATE_STATE_REASON_SUMMARY_CONTRACT_INVALID: &str = "summary_contract_invalid";
pub const UDP_ROLLOUT_GATE_STATE_REASON_REQUIRED_INPUTS_UNREADY: &str = "required_inputs_unready";
pub const UDP_ROLLOUT_GATE_STATE_REASON_DEGRADATION_HOLD: &str = "degradation_hold";
pub const UDP_ROLLOUT_GATE_STATE_REASON_BLOCKING_REASONS_PRESENT: &str = "blocking_reasons_present";
pub const UDP_ROLLOUT_GATE_STATE_REASON_FAMILY_READY: &str = "ready";
pub const UDP_ROLLOUT_GATE_STATE_REASON_FAMILY_SUMMARY_PRESENCE: &str = "summary_presence";
pub const UDP_ROLLOUT_GATE_STATE_REASON_FAMILY_SUMMARY_CONTRACT: &str = "summary_contract";
pub const UDP_ROLLOUT_GATE_STATE_REASON_FAMILY_GATING: &str = "gating";
pub const UDP_ROLLOUT_GATE_STATE_REASON_FAMILY_DEGRADATION: &str = "degradation";

pub fn summarize_rollout_gate_state(
    required_input_missing_count: usize,
    summary_contract_invalid_count: usize,
    required_input_unready_count: usize,
    degradation_hold_count: usize,
    blocking_reason_count: usize,
) -> (&'static str, &'static str) {
    if required_input_missing_count > 0 {
        (
            UDP_ROLLOUT_GATE_STATE_REASON_MISSING_REQUIRED_INPUTS,
            UDP_ROLLOUT_GATE_STATE_REASON_FAMILY_SUMMARY_PRESENCE,
        )
    } else if summary_contract_invalid_count > 0 {
        (
            UDP_ROLLOUT_GATE_STATE_REASON_SUMMARY_CONTRACT_INVALID,
            UDP_ROLLOUT_GATE_STATE_REASON_FAMILY_SUMMARY_CONTRACT,
        )
    } else if required_input_unready_count > 0 {
        (
            UDP_ROLLOUT_GATE_STATE_REASON_REQUIRED_INPUTS_UNREADY,
            UDP_ROLLOUT_GATE_STATE_REASON_FAMILY_GATING,
        )
    } else if degradation_hold_count > 0 {
        (
            UDP_ROLLOUT_GATE_STATE_REASON_DEGRADATION_HOLD,
            UDP_ROLLOUT_GATE_STATE_REASON_FAMILY_DEGRADATION,
        )
    } else if blocking_reason_count > 0 {
        (
            UDP_ROLLOUT_GATE_STATE_REASON_BLOCKING_REASONS_PRESENT,
            UDP_ROLLOUT_GATE_STATE_REASON_FAMILY_GATING,
        )
    } else {
        (
            UDP_ROLLOUT_GATE_STATE_REASON_READY,
            UDP_ROLLOUT_GATE_STATE_REASON_FAMILY_READY,
        )
    }
}

pub fn rollout_queue_hold_present(
    queue_guard_headroom_missing_count: usize,
    queue_guard_tight_hold_count: usize,
    queue_pressure_hold_count: usize,
) -> bool {
    queue_guard_headroom_missing_count > 0
        || queue_guard_tight_hold_count > 0
        || queue_pressure_hold_count > 0
}

pub fn rollout_queue_hold_input_count<I>(inputs: I) -> usize
where
    I: IntoIterator<Item = (usize, usize, usize)>,
{
    inputs
        .into_iter()
        .filter(|(headroom_missing, tight_hold, pressure_hold)| {
            rollout_queue_hold_present(*headroom_missing, *tight_hold, *pressure_hold)
        })
        .count()
}

pub fn rollout_queue_hold_host_count<I>(hosts: I) -> usize
where
    I: IntoIterator<Item = (usize, usize, usize)>,
{
    rollout_queue_hold_input_count(hosts)
}

pub fn blocking_reason_accounting_consistent(
    blocking_reason_keys: &[String],
    blocking_reason_key_counts: &BTreeMap<String, usize>,
    blocking_reason_families: &[String],
    blocking_reason_family_counts: &BTreeMap<String, usize>,
) -> bool {
    let expected_keys = blocking_reason_key_counts
        .keys()
        .cloned()
        .collect::<Vec<_>>();
    let expected_families = blocking_reason_family_counts
        .keys()
        .cloned()
        .collect::<Vec<_>>();
    blocking_reason_keys == expected_keys && blocking_reason_families == expected_families
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum UdpWanLabProfileId {
    LossBurst,
    ReorderWindow,
    AssociatedStreamGuardRecovery,
    OversizedPayloadGuardRecovery,
    DelayedDeliveryShortBlackHole,
    MixedDelayLossRecovery,
    MtuPressure,
    QueuePressureSticky,
    PostCloseRejection,
    ReorderedAfterCloseRejection,
    FallbackFlowGuardRejection,
    CarrierUnavailableFallback,
    PolicyDisabledFallback,
    DatagramOnlyUnavailableRejection,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum UdpWanLabCommandKind {
    LiveUdp,
    Lib,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct UdpWanLabProfile {
    pub id: UdpWanLabProfileId,
    pub slug: &'static str,
    pub spec_suite_ids: &'static [&'static str],
    pub description: &'static str,
    pub command_kind: UdpWanLabCommandKind,
    pub command_selector: &'static str,
    pub cargo_args: &'static [&'static str],
    pub requires_no_silent_fallback: bool,
}

const UDP_WAN_LAB_PROFILES: &[UdpWanLabProfile] = &[
    UdpWanLabProfile {
        id: UdpWanLabProfileId::LossBurst,
        slug: "loss-burst",
        spec_suite_ids: &["NT-LOSS-1PCT-001", "NT-LOSS-5PCT-002"],
        description: "Deterministic repeated bounded loss while an established datagram flow stays selected.",
        command_kind: UdpWanLabCommandKind::LiveUdp,
        command_selector: "loopback_h3_datagrams_continue_after_repeated_bounded_loss",
        cargo_args: &[
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_h3_datagrams_continue_after_repeated_bounded_loss",
            "--",
            "--nocapture",
        ],
        requires_no_silent_fallback: true,
    },
    UdpWanLabProfile {
        id: UdpWanLabProfileId::ReorderWindow,
        slug: "reorder-window",
        spec_suite_ids: &["NT-REORDER-004"],
        description: "Deterministic bounded reordering while the selected datagram flow remains active.",
        command_kind: UdpWanLabCommandKind::LiveUdp,
        command_selector: "loopback_h3_datagrams_tolerate_bounded_reordering_without_fallback",
        cargo_args: &[
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_h3_datagrams_tolerate_bounded_reordering_without_fallback",
            "--",
            "--nocapture",
        ],
        requires_no_silent_fallback: true,
    },
    UdpWanLabProfile {
        id: UdpWanLabProfileId::AssociatedStreamGuardRecovery,
        slug: "associated-stream-guard-recovery",
        spec_suite_ids: &["NT-ASSOC-STREAM-GUARD-007"],
        description: "Wrong associated-stream datagrams stay rejected and the selected datagram transport recovers without silent fallback.",
        command_kind: UdpWanLabCommandKind::LiveUdp,
        command_selector: "loopback_h3_datagrams_reject_wrong_associated_stream_and_recover",
        cargo_args: &[
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_h3_datagrams_reject_wrong_associated_stream_and_recover",
            "--",
            "--nocapture",
        ],
        requires_no_silent_fallback: true,
    },
    UdpWanLabProfile {
        id: UdpWanLabProfileId::OversizedPayloadGuardRecovery,
        slug: "oversized-payload-guard-recovery",
        spec_suite_ids: &[],
        description: "Oversized datagrams stay rejected before send while the selected datagram flow remains usable without silent fallback.",
        command_kind: UdpWanLabCommandKind::LiveUdp,
        command_selector: "loopback_h3_datagrams_reject_oversized_payloads_and_keep_flow_state",
        cargo_args: &[
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_h3_datagrams_reject_oversized_payloads_and_keep_flow_state",
            "--",
            "--nocapture",
        ],
        requires_no_silent_fallback: true,
    },
    UdpWanLabProfile {
        id: UdpWanLabProfileId::DelayedDeliveryShortBlackHole,
        slug: "delayed-black-hole",
        spec_suite_ids: &["NT-JITTER-003"],
        description: "Deterministic delayed delivery plus a short datagram black-hole interval without silent fallback.",
        command_kind: UdpWanLabCommandKind::LiveUdp,
        command_selector: "loopback_h3_datagrams_tolerate_delayed_delivery_and_short_black_hole_without_fallback",
        cargo_args: &[
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_h3_datagrams_tolerate_delayed_delivery_and_short_black_hole_without_fallback",
            "--",
            "--nocapture",
        ],
        requires_no_silent_fallback: true,
    },
    UdpWanLabProfile {
        id: UdpWanLabProfileId::MixedDelayLossRecovery,
        slug: "mixed-delay-loss-recovery",
        spec_suite_ids: &[],
        description: "Mixed delay and loss still preserve datagram selection and eventual recovery without silent fallback.",
        command_kind: UdpWanLabCommandKind::LiveUdp,
        command_selector: "loopback_h3_datagrams_continue_after_mixed_delay_and_loss_without_fallback",
        cargo_args: &[
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_h3_datagrams_continue_after_mixed_delay_and_loss_without_fallback",
            "--",
            "--nocapture",
        ],
        requires_no_silent_fallback: true,
    },
    UdpWanLabProfile {
        id: UdpWanLabProfileId::MtuPressure,
        slug: "mtu-pressure",
        spec_suite_ids: &["NT-MTU-1200-005"],
        description: "Datagram delivery exactly at the negotiated effective UDP payload ceiling.",
        command_kind: UdpWanLabCommandKind::LiveUdp,
        command_selector: "loopback_h3_datagrams_accept_payload_at_effective_mtu_ceiling",
        cargo_args: &[
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_h3_datagrams_accept_payload_at_effective_mtu_ceiling",
            "--",
            "--nocapture",
        ],
        requires_no_silent_fallback: true,
    },
    UdpWanLabProfile {
        id: UdpWanLabProfileId::QueuePressureSticky,
        slug: "queue-pressure-sticky",
        spec_suite_ids: &[],
        description: "Repeated queue pressure keeps the selected datagram transport sticky and rejects silent fallback.",
        command_kind: UdpWanLabCommandKind::Lib,
        command_selector: "repeated_queue_pressure_keeps_selected_datagram_transport_without_silent_fallback",
        cargo_args: &[
            "-p",
            "ns-carrier-h3",
            "repeated_queue_pressure_keeps_selected_datagram_transport_without_silent_fallback",
            "--lib",
            "--",
            "--nocapture",
        ],
        requires_no_silent_fallback: true,
    },
    UdpWanLabProfile {
        id: UdpWanLabProfileId::PostCloseRejection,
        slug: "post-close-rejection",
        spec_suite_ids: &[],
        description: "Unknown datagrams after close stay rejected without reopening fallback transport.",
        command_kind: UdpWanLabCommandKind::LiveUdp,
        command_selector: "loopback_h3_datagrams_reject_unknown_flows_after_close",
        cargo_args: &[
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_h3_datagrams_reject_unknown_flows_after_close",
            "--",
            "--nocapture",
        ],
        requires_no_silent_fallback: true,
    },
    UdpWanLabProfile {
        id: UdpWanLabProfileId::ReorderedAfterCloseRejection,
        slug: "reordered-after-close-rejection",
        spec_suite_ids: &[],
        description: "Late reordered datagrams after close stay rejected without reopening fallback transport.",
        command_kind: UdpWanLabCommandKind::LiveUdp,
        command_selector: "loopback_h3_datagrams_reject_reordered_after_close_without_fallback",
        cargo_args: &[
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_h3_datagrams_reject_reordered_after_close_without_fallback",
            "--",
            "--nocapture",
        ],
        requires_no_silent_fallback: true,
    },
    UdpWanLabProfile {
        id: UdpWanLabProfileId::FallbackFlowGuardRejection,
        slug: "fallback-flow-guard-rejection",
        spec_suite_ids: &[],
        description: "Wrong fallback-flow traffic stays rejected with a protocol violation instead of silently reviving stream fallback.",
        command_kind: UdpWanLabCommandKind::LiveUdp,
        command_selector: "loopback_udp_fallback_rejects_wrong_flow_id_with_protocol_violation_close",
        cargo_args: &[
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_udp_fallback_rejects_wrong_flow_id_with_protocol_violation_close",
            "--",
            "--nocapture",
        ],
        requires_no_silent_fallback: true,
    },
    UdpWanLabProfile {
        id: UdpWanLabProfileId::CarrierUnavailableFallback,
        slug: "udp-blocked-fallback",
        spec_suite_ids: &["NT-UDP-BLOCKED-FALLBACK-006"],
        description: "Carrier datagrams are unavailable before flow selection, so explicit stream fallback stays observable.",
        command_kind: UdpWanLabCommandKind::LiveUdp,
        command_selector: "loopback_udp_stream_fallback_round_trips_when_carrier_support_is_unavailable",
        cargo_args: &[
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_udp_stream_fallback_round_trips_when_carrier_support_is_unavailable",
            "--",
            "--nocapture",
        ],
        requires_no_silent_fallback: false,
    },
    UdpWanLabProfile {
        id: UdpWanLabProfileId::PolicyDisabledFallback,
        slug: "policy-disabled-fallback",
        spec_suite_ids: &["NT-UDP-BLOCKED-FALLBACK-006"],
        description: "Datagrams are disabled by policy before selection, so explicit fallback remains observable without silent downgrade.",
        command_kind: UdpWanLabCommandKind::LiveUdp,
        command_selector: "loopback_udp_stream_fallback_round_trips_when_rollout_disables_datagrams",
        cargo_args: &[
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_udp_stream_fallback_round_trips_when_rollout_disables_datagrams",
            "--",
            "--nocapture",
        ],
        requires_no_silent_fallback: false,
    },
    UdpWanLabProfile {
        id: UdpWanLabProfileId::DatagramOnlyUnavailableRejection,
        slug: "datagram-only-unavailable-rejection",
        spec_suite_ids: &["NT-UDP-BLOCKED-FALLBACK-006"],
        description: "Datagram-only requests stay rejected when datagram carriage is unavailable instead of silently reviving stream fallback.",
        command_kind: UdpWanLabCommandKind::LiveUdp,
        command_selector: "loopback_udp_flow_rejects_datagram_only_requests_when_datagrams_are_unavailable",
        cargo_args: &[
            "-p",
            "ns-carrier-h3",
            "--test",
            "live_udp",
            "loopback_udp_flow_rejects_datagram_only_requests_when_datagrams_are_unavailable",
            "--",
            "--nocapture",
        ],
        requires_no_silent_fallback: false,
    },
];

#[derive(Debug, Clone, Copy)]
pub struct DeterministicClock {
    now: OffsetDateTime,
}

impl DeterministicClock {
    pub fn new(now: OffsetDateTime) -> Self {
        Self { now }
    }

    pub fn now(&self) -> OffsetDateTime {
        self.now
    }
}

#[derive(Clone, Default)]
pub struct FrameQueue {
    frames: Arc<Mutex<VecDeque<Frame>>>,
}

impl FrameQueue {
    pub fn push(&self, frame: Frame) {
        self.frames
            .lock()
            .expect("frame queue poisoned")
            .push_back(frame);
    }

    pub fn pop(&self) -> Result<Frame, TransportError> {
        self.frames
            .lock()
            .expect("frame queue poisoned")
            .pop_front()
            .ok_or_else(|| TransportError {
                kind: TransportErrorKind::ConnectionLost,
                message: "frame queue exhausted".to_owned(),
            })
    }
}

pub fn sample_client_hello(token: String) -> ClientHello {
    ClientHello {
        min_version: 1,
        max_version: 1,
        client_nonce: [1_u8; 32],
        requested_capabilities: vec![Capability::TcpRelay, Capability::UdpRelay],
        carrier_kind: CarrierKind::H3,
        carrier_profile_id: CarrierProfileId::new("carrier-primary")
            .expect("fixture carrier profile should be valid"),
        manifest_id: ManifestId::new("man-2026-04-01-001")
            .expect("fixture manifest id should be valid"),
        device_binding_id: DeviceBindingId::new("device-1")
            .expect("fixture device binding id should be valid"),
        requested_idle_timeout_ms: 30_000,
        requested_max_udp_payload: 1_200,
        token: token.into_bytes(),
        client_metadata: Vec::new(),
    }
}

pub fn sample_manifest_json() -> String {
    let generated_at = OffsetDateTime::parse(
        "2026-04-01T00:10:00Z",
        &time::format_description::well_known::Rfc3339,
    )
    .expect("fixture manifest generated_at should parse");
    let expires_at = OffsetDateTime::parse(
        "2026-04-01T06:10:00Z",
        &time::format_description::well_known::Rfc3339,
    )
    .expect("fixture manifest expires_at should parse");
    let mut manifest = sample_manifest_document(generated_at, expires_at);

    ManifestSigner::new(FIXTURE_MANIFEST_KEY_ID, fixture_manifest_signing_key())
        .sign(&mut manifest)
        .expect("sample manifest should sign");

    serde_json::to_string(&manifest).expect("sample manifest should serialize")
}

pub fn sample_manifest_document(
    generated_at: OffsetDateTime,
    expires_at: OffsetDateTime,
) -> ManifestDocument {
    ManifestDocument {
        schema_version: 1,
        manifest_id: "man-2026-04-01-001".to_owned(),
        generated_at,
        expires_at,
        user: Some(ManifestUser {
            account_id: Some("acct-1".to_owned()),
            plan_id: Some("plan-pro".to_owned()),
            display_name: Some("Verta Test User".to_owned()),
        }),
        device_policy: Some(DevicePolicy {
            max_devices: 2,
            require_device_binding: true,
        }),
        client_constraints: ClientConstraints {
            min_client_version: "0.1.0".to_owned(),
            recommended_client_version: "0.1.0".to_owned(),
            allowed_core_versions: vec![1],
        },
        token_service: TokenService {
            url: Url::parse("https://bridge.example/v0/token/exchange")
                .expect("fixture token-service url should parse"),
            issuer: "bridge.example".to_owned(),
            jwks_url: Url::parse("https://bridge.example/.well-known/jwks.json")
                .expect("fixture jwks url should parse"),
            session_token_ttl_seconds: 300,
        },
        refresh: Some(RefreshPolicy {
            mode: RefreshMode::OpaqueSecret,
            credential: "bootstrap-only-redacted".to_owned(),
            rotation_hint_seconds: Some(86_400),
        }),
        carrier_profiles: vec![CarrierProfile {
            id: "carrier-primary".to_owned(),
            carrier_kind: ManifestCarrierKind::H3,
            origin_host: "origin.edge.example.net".to_owned(),
            origin_port: 8443,
            sni: Some("origin.edge.example.net".to_owned()),
            alpn: vec!["h3".to_owned()],
            control_template: HttpTemplate {
                method: HttpTemplateMethod::Connect,
                path: "/ns/control".to_owned(),
            },
            relay_template: HttpTemplate {
                method: HttpTemplateMethod::Connect,
                path: "/ns/relay".to_owned(),
            },
            headers: BTreeMap::from([("x-verta-profile".to_owned(), "carrier-primary".to_owned())]),
            datagram_enabled: true,
            heartbeat_interval_ms: 20_000,
            idle_timeout_ms: 90_000,
            zero_rtt_policy: Some(ZeroRttPolicy::Disabled),
            connect_backoff: ConnectBackoff {
                initial_ms: 500,
                max_ms: 10_000,
                jitter: 0.2,
            },
        }],
        endpoints: vec![GatewayEndpoint {
            id: "edge-1".to_owned(),
            host: "edge.example.net".to_owned(),
            port: 443,
            region: "eu-central".to_owned(),
            routing_group: Some("primary".to_owned()),
            carrier_profile_ids: vec!["carrier-primary".to_owned()],
            priority: 10,
            weight: 100,
            tags: vec!["stable".to_owned()],
        }],
        routing: RoutingPolicy {
            selection_mode: RoutingSelectionMode::LatencyWeighted,
            failover_mode: RoutingFailoverMode::SameRegionThenGlobal,
        },
        retry_policy: RetryPolicy {
            connect_attempts: 3,
            initial_backoff_ms: 500,
            max_backoff_ms: 10_000,
        },
        telemetry: TelemetryPolicy {
            allow_client_reports: true,
            sample_rate: 0.05,
        },
        signature: ManifestSignature {
            alg: "EdDSA".to_owned(),
            key_id: FIXTURE_MANIFEST_KEY_ID.to_owned(),
            value: "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA".to_owned(),
        },
    }
}

pub fn sample_account_snapshot() -> AccountSnapshot {
    AccountSnapshot {
        account_id: "acct-1".to_owned(),
        bootstrap_subjects: vec![BootstrapSubject::ShortUuid("sub-1".to_owned())],
        lifecycle: AccountLifecycle::Active,
        verta_access: VertaAccess {
            verta_enabled: true,
            policy_epoch: 7,
            device_limit: Some(2),
            allowed_core_versions: vec![1],
            allowed_carrier_profiles: vec!["carrier-primary".to_owned()],
            allowed_capabilities: vec![Capability::TcpRelay.id(), Capability::UdpRelay.id()],
            rollout_cohort: Some("alpha".to_owned()),
            preferred_regions: vec!["eu-central".to_owned()],
        },
        metadata: None,
        observed_at_unix: 1_700_000_000,
        source_version: Some("2.7.4".to_owned()),
    }
}

pub fn sample_carrier_info() -> CarrierSessionInfo {
    CarrierSessionInfo {
        carrier_profile_id: CarrierProfileId::new("carrier-primary")
            .expect("fixture carrier profile should be valid"),
        datagrams_available: false,
    }
}

pub fn sample_payload() -> Bytes {
    Bytes::from_static(b"verta-test-payload")
}

pub fn udp_wan_lab_profiles() -> &'static [UdpWanLabProfile] {
    UDP_WAN_LAB_PROFILES
}

pub fn udp_wan_lab_profile(id: UdpWanLabProfileId) -> &'static UdpWanLabProfile {
    udp_wan_lab_profiles()
        .iter()
        .find(|profile| profile.id == id)
        .expect("requested UDP WAN lab profile should exist")
}

pub fn udp_wan_lab_profile_by_slug(slug: &str) -> Option<&'static UdpWanLabProfile> {
    udp_wan_lab_profiles()
        .iter()
        .find(|profile| profile.slug == slug)
}

pub fn udp_wan_lab_profile_slugs() -> Vec<&'static str> {
    udp_wan_lab_profiles()
        .iter()
        .map(|profile| profile.slug)
        .collect()
}

pub fn udp_wan_lab_required_no_silent_fallback_profile_slugs() -> Vec<&'static str> {
    udp_wan_lab_profiles()
        .iter()
        .filter(|profile| profile.requires_no_silent_fallback)
        .map(|profile| profile.slug)
        .collect()
}

pub fn repo_root() -> PathBuf {
    let mut root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    root.pop();
    root.pop();
    root
}

pub fn verta_target_root() -> PathBuf {
    env::var_os("VERTA_TARGET_ROOT")
        .map(PathBuf::from)
        .unwrap_or_else(|| repo_root().join("target").join("verta"))
}

pub fn verta_output_path(relative: impl AsRef<Path>) -> PathBuf {
    verta_target_root().join(relative)
}

pub fn verta_legacy_output_path(relative: impl AsRef<Path>) -> PathBuf {
    verta_output_path(relative)
}

pub fn prefer_verta_input_path(relative: impl AsRef<Path>) -> PathBuf {
    verta_output_path(relative)
}

pub fn verta_env_value(canonical: &str, _legacy: &str) -> Option<String> {
    env::var(canonical).ok()
}

pub fn verta_env_path(canonical: &str, _legacy: &str, file_name: &str) -> PathBuf {
    env::var_os(canonical)
        .map(PathBuf::from)
        .unwrap_or_else(|| verta_output_path(file_name))
}

pub fn prefer_verta_env_input_path(canonical: &str, _legacy: &str, file_name: &str) -> PathBuf {
    env::var_os(canonical)
        .map(PathBuf::from)
        .unwrap_or_else(|| prefer_verta_input_path(file_name))
}

pub fn fixture_path(relative: impl AsRef<Path>) -> PathBuf {
    repo_root().join("fixtures").join(relative)
}

pub fn load_fixture_text(relative: impl AsRef<Path>) -> String {
    let path = fixture_path(relative);
    fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("failed to read fixture {}: {error}", path.display()))
}

pub fn load_fixture_bytes(relative: impl AsRef<Path>) -> Vec<u8> {
    let path = fixture_path(relative);
    fs::read(&path)
        .unwrap_or_else(|error| panic!("failed to read fixture {}: {error}", path.display()))
}

pub fn load_fixture_hex(relative: impl AsRef<Path>) -> Vec<u8> {
    let path = fixture_path(relative);
    let encoded = fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("failed to read fixture {}: {error}", path.display()));
    hex::decode(encoded.trim())
        .unwrap_or_else(|error| panic!("failed to decode hex fixture {}: {error}", path.display()))
}

pub fn fixed_test_now() -> OffsetDateTime {
    OffsetDateTime::from_unix_timestamp(1_700_000_100)
        .expect("fixed test timestamp should be valid")
}

pub fn fixture_manifest_signing_key() -> SigningKey {
    SigningKey::from_bytes(&[41_u8; 32])
}

pub fn fixture_manifest_trust_store() -> ManifestTrustStore {
    let mut trust_store = ManifestTrustStore::default();
    trust_store.insert(
        FIXTURE_MANIFEST_KEY_ID,
        fixture_manifest_signing_key().verifying_key(),
    );
    trust_store
}

pub fn fixture_token_signing_key() -> SigningKey {
    SigningKey::from_bytes(&[42_u8; 32])
}

pub fn fixture_token_jwks() -> JwkSet {
    let x = {
        use base64::Engine as _;
        base64::engine::general_purpose::URL_SAFE_NO_PAD
            .encode(fixture_token_signing_key().verifying_key().to_bytes())
    };

    JwkSet {
        keys: vec![Jwk {
            common: CommonParameters {
                key_id: Some(FIXTURE_TOKEN_KEY_ID.to_owned()),
                key_algorithm: Some(jsonwebtoken::jwk::KeyAlgorithm::EdDSA),
                ..Default::default()
            },
            algorithm: AlgorithmParameters::OctetKeyPair(OctetKeyPairParameters {
                key_type: OctetKeyPairType::OctetKeyPair,
                curve: jsonwebtoken::jwk::EllipticCurve::Ed25519,
                x,
            }),
        }],
    }
}

pub fn fixture_token_verifier() -> SessionTokenVerifier {
    SessionTokenVerifier::new(
        VerifierConfig {
            trusted_issuers: vec!["bridge.example".to_owned()],
            audience: "verta-gateway".to_owned(),
            clock_skew: time::Duration::seconds(5),
            revoked_subjects: Vec::new(),
            minimum_policy_epoch: None,
        },
        TrustedKeySet::from_jwks(&fixture_token_jwks())
            .expect("fixture JWKS should initialize a trusted key set"),
    )
}

pub fn fixture_session_mode() -> SessionMode {
    SessionMode::Tcp
}

#[cfg(test)]
mod tests {
    use super::{
        UdpWanLabProfileId, rollout_queue_hold_host_count, udp_wan_lab_profile,
        udp_wan_lab_profile_by_slug, udp_wan_lab_profile_slugs, udp_wan_lab_profiles,
        udp_wan_lab_required_no_silent_fallback_profile_slugs,
    };
    use std::collections::BTreeSet;

    #[test]
    fn udp_wan_lab_profiles_stay_unique_and_named() {
        let mut slugs = BTreeSet::new();
        let mut selectors = BTreeSet::new();

        for profile in udp_wan_lab_profiles() {
            assert!(
                slugs.insert(profile.slug),
                "duplicate UDP WAN lab slug {}",
                profile.slug
            );
            assert!(
                selectors.insert(profile.command_selector),
                "duplicate UDP WAN lab command selector {}",
                profile.command_selector
            );
            assert!(
                profile
                    .spec_suite_ids
                    .iter()
                    .all(|suite_id| !suite_id.trim().is_empty()),
                "profile {} should not include empty spec suite ids",
                profile.slug
            );
            assert!(
                !profile.description.trim().is_empty(),
                "profile {} should describe its impairment surface",
                profile.slug
            );
            assert!(
                !profile.command_selector.trim().is_empty(),
                "profile {} should describe its command selector",
                profile.slug
            );
            assert!(
                !profile.cargo_args.is_empty(),
                "profile {} should define a cargo invocation",
                profile.slug
            );
        }
    }

    #[test]
    fn udp_wan_lab_profile_lookup_returns_expected_profile() {
        let profile = udp_wan_lab_profile(UdpWanLabProfileId::DelayedDeliveryShortBlackHole);

        assert_eq!(profile.slug, "delayed-black-hole");
        assert_eq!(profile.spec_suite_ids, ["NT-JITTER-003"]);
        assert!(profile.requires_no_silent_fallback);
    }

    #[test]
    fn udp_wan_lab_profile_lookup_by_slug_returns_expected_profile() {
        let profile = udp_wan_lab_profile_by_slug("loss-burst")
            .expect("loss-burst profile should be discoverable by slug");

        assert_eq!(profile.id, UdpWanLabProfileId::LossBurst);
        assert_eq!(
            profile.command_selector,
            "loopback_h3_datagrams_continue_after_repeated_bounded_loss"
        );
    }

    #[test]
    fn udp_wan_lab_profile_lookup_includes_policy_disabled_fallback() {
        let profile = udp_wan_lab_profile(UdpWanLabProfileId::PolicyDisabledFallback);

        assert_eq!(profile.slug, "policy-disabled-fallback");
        assert_eq!(profile.spec_suite_ids, ["NT-UDP-BLOCKED-FALLBACK-006"]);
        assert_eq!(
            profile.command_selector,
            "loopback_udp_stream_fallback_round_trips_when_rollout_disables_datagrams"
        );
        assert!(!profile.requires_no_silent_fallback);
    }

    #[test]
    fn udp_wan_lab_profile_lookup_includes_datagram_only_unavailable_rejection() {
        let profile = udp_wan_lab_profile(UdpWanLabProfileId::DatagramOnlyUnavailableRejection);

        assert_eq!(profile.slug, "datagram-only-unavailable-rejection");
        assert_eq!(profile.spec_suite_ids, ["NT-UDP-BLOCKED-FALLBACK-006"]);
        assert_eq!(
            profile.command_selector,
            "loopback_udp_flow_rejects_datagram_only_requests_when_datagrams_are_unavailable"
        );
        assert!(!profile.requires_no_silent_fallback);
    }

    #[test]
    fn udp_wan_lab_profile_lookup_includes_queue_pressure_surface() {
        let profile = udp_wan_lab_profile(UdpWanLabProfileId::QueuePressureSticky);

        assert_eq!(profile.slug, "queue-pressure-sticky");
        assert!(profile.spec_suite_ids.is_empty());
        assert_eq!(
            profile.command_selector,
            "repeated_queue_pressure_keeps_selected_datagram_transport_without_silent_fallback"
        );
        assert!(profile.requires_no_silent_fallback);
    }

    #[test]
    fn udp_wan_lab_profile_lookup_includes_post_close_rejection_surface() {
        let profile = udp_wan_lab_profile(UdpWanLabProfileId::PostCloseRejection);

        assert_eq!(profile.slug, "post-close-rejection");
        assert!(profile.spec_suite_ids.is_empty());
        assert_eq!(
            profile.command_selector,
            "loopback_h3_datagrams_reject_unknown_flows_after_close"
        );
        assert!(profile.requires_no_silent_fallback);
    }

    #[test]
    fn udp_wan_lab_profile_lookup_includes_associated_stream_guard_surface() {
        let profile = udp_wan_lab_profile(UdpWanLabProfileId::AssociatedStreamGuardRecovery);

        assert_eq!(profile.slug, "associated-stream-guard-recovery");
        assert_eq!(
            profile.command_selector,
            "loopback_h3_datagrams_reject_wrong_associated_stream_and_recover"
        );
        assert!(profile.requires_no_silent_fallback);
    }

    #[test]
    fn udp_wan_lab_profile_lookup_includes_fallback_flow_guard_surface() {
        let profile = udp_wan_lab_profile(UdpWanLabProfileId::FallbackFlowGuardRejection);

        assert_eq!(profile.slug, "fallback-flow-guard-rejection");
        assert_eq!(
            profile.command_selector,
            "loopback_udp_fallback_rejects_wrong_flow_id_with_protocol_violation_close"
        );
        assert!(profile.requires_no_silent_fallback);
    }

    #[test]
    fn udp_wan_lab_profile_lookup_includes_oversized_payload_guard_surface() {
        let profile = udp_wan_lab_profile(UdpWanLabProfileId::OversizedPayloadGuardRecovery);

        assert_eq!(profile.slug, "oversized-payload-guard-recovery");
        assert_eq!(
            profile.command_selector,
            "loopback_h3_datagrams_reject_oversized_payloads_and_keep_flow_state"
        );
        assert!(profile.requires_no_silent_fallback);
    }

    #[test]
    fn udp_wan_lab_profile_helpers_return_expected_profile_sets() {
        let all_profiles = udp_wan_lab_profile_slugs();
        let required_profiles = udp_wan_lab_required_no_silent_fallback_profile_slugs();

        assert!(all_profiles.contains(&"queue-pressure-sticky"));
        assert!(required_profiles.contains(&"queue-pressure-sticky"));
        assert!(all_profiles.contains(&"associated-stream-guard-recovery"));
        assert!(required_profiles.contains(&"associated-stream-guard-recovery"));
        assert!(all_profiles.contains(&"oversized-payload-guard-recovery"));
        assert!(required_profiles.contains(&"oversized-payload-guard-recovery"));
        assert!(all_profiles.contains(&"post-close-rejection"));
        assert!(required_profiles.contains(&"post-close-rejection"));
        assert!(all_profiles.contains(&"reordered-after-close-rejection"));
        assert!(required_profiles.contains(&"reordered-after-close-rejection"));
        assert!(all_profiles.contains(&"fallback-flow-guard-rejection"));
        assert!(required_profiles.contains(&"fallback-flow-guard-rejection"));
        assert!(all_profiles.contains(&"mixed-delay-loss-recovery"));
        assert!(required_profiles.contains(&"mixed-delay-loss-recovery"));
        assert!(!required_profiles.contains(&"policy-disabled-fallback"));
        assert!(all_profiles.contains(&"datagram-only-unavailable-rejection"));
        assert!(!required_profiles.contains(&"datagram-only-unavailable-rejection"));
        assert_eq!(all_profiles.len(), 14);
        assert_eq!(required_profiles.len(), 11);
    }

    #[test]
    fn rollout_queue_hold_host_count_counts_hosts_with_any_queue_hold() {
        let count = rollout_queue_hold_host_count([(0, 0, 0), (1, 0, 0), (0, 0, 2), (0, 3, 0)]);

        assert_eq!(count, 3);
    }
}
