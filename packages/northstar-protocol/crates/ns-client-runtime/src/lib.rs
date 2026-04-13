#![forbid(unsafe_code)]

use ns_bridge_api::TokenExchangeRequest;
use ns_carrier_h3::{
    H3ClientConnector, H3ConnectBackoff, H3DatagramRollout, H3TransportConfig, H3ZeroRttPolicy,
};
use ns_core::{
    Capability, CarrierProfileId, DatagramMode, DeviceBindingId, ManifestId, SESSION_CORE_VERSION,
    SessionId, StatsMode,
};
use ns_manifest::{ManifestDocument, ManifestTrustStore};
use ns_policy::EffectiveSessionPolicy;
use ns_session::{SessionController, SessionError};
use ns_wire::{ClientHello, ServerHello};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use thiserror::Error;
use time::OffsetDateTime;
use url::Url;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ClientRuntimeConfig {
    pub manifest_url: Url,
    pub device_id: DeviceBindingId,
    pub client_version: String,
    pub selected_carrier_profile: CarrierProfileId,
    pub datagram_rollout: H3DatagramRollout,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ClientLaunchPlan {
    pub manifest_id: ManifestId,
    pub carrier_profile_id: CarrierProfileId,
    pub endpoint_id: String,
    pub endpoint_host: String,
    pub endpoint_port: u16,
    pub transport_origin_host: String,
    pub transport_origin_port: u16,
    pub transport_sni: Option<String>,
    pub transport_alpn: Vec<String>,
    pub control_path: String,
    pub relay_path: String,
    pub transport_headers: BTreeMap<String, String>,
    pub datagram_enabled: bool,
    pub datagram_rollout: H3DatagramRollout,
    pub heartbeat_interval_ms: u64,
    pub idle_timeout_ms: u64,
    pub zero_rtt_policy: H3ZeroRttPolicy,
    pub connect_backoff: H3ConnectBackoff,
    pub token_exchange_url: Url,
    pub token_exchange: TokenExchangeRequest,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ClientDatagramStartupContract {
    pub signed_datagram_enabled: bool,
    pub datagram_rollout: H3DatagramRollout,
    pub carrier_datagrams_available: bool,
    pub expected_server_datagram_mode: DatagramMode,
    pub rollout_stage: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ClientNegotiatedDatagramContractInput {
    pub expected_policy_epoch: u64,
    pub expected_max_udp_flows: u64,
    pub expected_max_udp_payload: u64,
    pub requested_max_udp_payload: u64,
    pub carrier_datagrams_available: bool,
    pub received_policy_epoch: u64,
    pub received_datagram_mode: DatagramMode,
    pub received_max_udp_flows: u64,
    pub received_effective_max_udp_payload: u64,
}

impl ClientLaunchPlan {
    pub fn h3_transport_config(&self) -> H3TransportConfig {
        H3TransportConfig {
            carrier_kind: ns_core::CarrierKind::H3,
            carrier_profile_id: self.carrier_profile_id.clone(),
            origin_host: self.transport_origin_host.clone(),
            origin_port: self.transport_origin_port,
            sni: self.transport_sni.clone(),
            alpn: self.transport_alpn.clone(),
            control_path: self.control_path.clone(),
            relay_path: self.relay_path.clone(),
            headers: self.transport_headers.clone(),
            datagram_enabled: self.datagram_enabled,
            datagram_rollout: self.datagram_rollout,
            heartbeat_interval_ms: self.heartbeat_interval_ms,
            idle_timeout_ms: self.idle_timeout_ms,
            zero_rtt_policy: self.zero_rtt_policy.clone(),
            connect_backoff: self.connect_backoff.clone(),
        }
    }

    pub fn expected_server_datagram_mode(&self, carrier_datagrams_available: bool) -> DatagramMode {
        self.h3_transport_config()
            .advertised_datagram_mode(carrier_datagrams_available)
    }

    pub fn datagram_startup_contract(
        &self,
        carrier_datagrams_available: bool,
    ) -> ClientDatagramStartupContract {
        self.validate_startup_datagram_contract(carrier_datagrams_available)
            .expect("validated launch plans should always resolve a startup datagram contract")
    }

    pub fn validate_startup_datagram_contract(
        &self,
        carrier_datagrams_available: bool,
    ) -> Result<ClientDatagramStartupContract, ClientRuntimeError> {
        let transport = self.h3_transport_config();
        let contract = transport.datagram_startup_contract(carrier_datagrams_available)?;
        Ok(ClientDatagramStartupContract {
            signed_datagram_enabled: contract.signed_datagram_enabled,
            datagram_rollout: contract.datagram_rollout,
            carrier_datagrams_available: contract.carrier_datagrams_available,
            expected_server_datagram_mode: contract.resolved_datagram_mode,
            rollout_stage: contract.rollout_stage.to_owned(),
        })
    }

    pub fn validate_negotiated_datagram_contract(
        &self,
        input: &ClientNegotiatedDatagramContractInput,
    ) -> Result<(), ClientRuntimeError> {
        let startup = self.datagram_startup_contract(input.carrier_datagrams_available);
        let mut policy = EffectiveSessionPolicy::tcp_and_udp_defaults(input.expected_policy_epoch);
        policy.limits.datagram_mode = startup.expected_server_datagram_mode;
        policy.limits.max_udp_flows = input.expected_max_udp_flows;
        policy.limits.max_udp_payload = input.expected_max_udp_payload;

        let request = ClientHello {
            min_version: 1,
            max_version: 1,
            client_nonce: [0_u8; 32],
            requested_capabilities: vec![Capability::TcpRelay, Capability::UdpRelay],
            carrier_kind: ns_core::CarrierKind::H3,
            carrier_profile_id: self.carrier_profile_id.clone(),
            manifest_id: self.manifest_id.clone(),
            device_binding_id: DeviceBindingId::new("contract-device")
                .expect("static client contract device id should be valid"),
            requested_idle_timeout_ms: self.idle_timeout_ms,
            requested_max_udp_payload: input.requested_max_udp_payload,
            token: Vec::new(),
            client_metadata: Vec::new(),
        };
        let response = ServerHello {
            selected_version: 1,
            session_id: SessionId::random(),
            server_nonce: [0_u8; 32],
            selected_capabilities: request.requested_capabilities.clone(),
            policy_epoch: input.received_policy_epoch,
            effective_idle_timeout_ms: self.idle_timeout_ms,
            session_lifetime_ms: self.idle_timeout_ms.saturating_mul(10),
            max_concurrent_relay_streams: 16,
            max_udp_flows: input.received_max_udp_flows,
            effective_max_udp_payload: input.received_effective_max_udp_payload,
            datagram_mode: input.received_datagram_mode,
            stats_mode: StatsMode::Off,
            server_metadata: Vec::new(),
        };

        SessionController::new_client(policy).apply_server_hello(&request, &response)?;
        Ok(())
    }
}

pub fn build_launch_plan(
    config: &ClientRuntimeConfig,
    manifest_json: &str,
    trust_store: &ManifestTrustStore,
    now: OffsetDateTime,
) -> Result<ClientLaunchPlan, ClientRuntimeError> {
    let manifest = ManifestDocument::parse_and_verify_json(manifest_json, trust_store, now)?;

    let manifest_id = ManifestId::new(manifest.manifest_id.clone())?;
    let profile = manifest
        .carrier_profile(&config.selected_carrier_profile)
        .ok_or_else(|| {
            ClientRuntimeError::CarrierProfileNotFound(
                config.selected_carrier_profile.as_str().to_owned(),
            )
        })?;
    let endpoint = manifest
        .endpoints_for_profile(&config.selected_carrier_profile)
        .into_iter()
        .next()
        .ok_or_else(|| {
            ClientRuntimeError::NoEndpointForProfile(
                config.selected_carrier_profile.as_str().to_owned(),
            )
        })?;
    if config.datagram_rollout != H3DatagramRollout::Disabled && !profile.datagram_enabled {
        return Err(ClientRuntimeError::IncompatibleDatagramRollout {
            carrier_profile_id: config.selected_carrier_profile.as_str().to_owned(),
            rollout_stage: config.datagram_rollout,
        });
    }
    let h3_config = H3TransportConfig {
        carrier_kind: profile.carrier_kind.clone().into_core(),
        carrier_profile_id: config.selected_carrier_profile.clone(),
        origin_host: profile.origin_host.clone(),
        origin_port: profile.origin_port,
        sni: profile.sni.clone(),
        alpn: profile.alpn.clone(),
        control_path: profile.control_template.path.clone(),
        relay_path: profile.relay_template.path.clone(),
        headers: profile.headers.clone(),
        datagram_enabled: profile.datagram_enabled,
        datagram_rollout: config.datagram_rollout,
        heartbeat_interval_ms: profile.heartbeat_interval_ms,
        idle_timeout_ms: profile.idle_timeout_ms,
        zero_rtt_policy: profile
            .zero_rtt_policy
            .clone()
            .map(|policy| match policy {
                ns_manifest::ZeroRttPolicy::Disabled => H3ZeroRttPolicy::Disabled,
                ns_manifest::ZeroRttPolicy::Allow => H3ZeroRttPolicy::Allow,
                ns_manifest::ZeroRttPolicy::ForceDisabled => H3ZeroRttPolicy::ForceDisabled,
            })
            .unwrap_or(H3ZeroRttPolicy::Disabled),
        connect_backoff: H3ConnectBackoff {
            initial_ms: profile.connect_backoff.initial_ms,
            max_ms: profile.connect_backoff.max_ms,
            jitter: profile.connect_backoff.jitter,
        },
    };
    let _pending = H3ClientConnector::prepare(&h3_config)?;

    Ok(ClientLaunchPlan {
        manifest_id,
        carrier_profile_id: config.selected_carrier_profile.clone(),
        endpoint_id: endpoint.id.clone(),
        endpoint_host: endpoint.host.clone(),
        endpoint_port: endpoint.port,
        transport_origin_host: h3_config.origin_host.clone(),
        transport_origin_port: h3_config.origin_port,
        transport_sni: h3_config.sni.clone(),
        transport_alpn: h3_config.alpn.clone(),
        control_path: h3_config.control_path.clone(),
        relay_path: h3_config.relay_path.clone(),
        transport_headers: h3_config.headers.clone(),
        datagram_enabled: h3_config.datagram_enabled,
        datagram_rollout: h3_config.datagram_rollout,
        heartbeat_interval_ms: h3_config.heartbeat_interval_ms,
        idle_timeout_ms: h3_config.idle_timeout_ms,
        zero_rtt_policy: h3_config.zero_rtt_policy.clone(),
        connect_backoff: h3_config.connect_backoff.clone(),
        token_exchange_url: manifest.token_service.url.clone(),
        token_exchange: TokenExchangeRequest {
            manifest_id: manifest.manifest_id,
            device_id: config.device_id.as_str().to_owned(),
            client_version: config.client_version.clone(),
            core_version: SESSION_CORE_VERSION,
            carrier_profile_id: config.selected_carrier_profile.as_str().to_owned(),
            requested_capabilities: vec![
                Capability::TcpRelay.id() as u16,
                Capability::UdpRelay.id() as u16,
            ],
            refresh_credential: "<bridge-refresh-credential-required>".to_owned(),
        },
    })
}

#[derive(Debug, Error)]
pub enum ClientRuntimeError {
    #[error("manifest validation failed: {0}")]
    Manifest(#[from] ns_manifest::ManifestError),
    #[error("validation failed: {0}")]
    Validation(#[from] ns_core::ValidationError),
    #[error("carrier profile {0} was not present in the manifest")]
    CarrierProfileNotFound(String),
    #[error("no endpoint was available for carrier profile {0}")]
    NoEndpointForProfile(String),
    #[error(
        "carrier profile {carrier_profile_id} disabled datagrams, which is incompatible with local rollout stage {rollout_stage:?}"
    )]
    IncompatibleDatagramRollout {
        carrier_profile_id: String,
        rollout_stage: H3DatagramRollout,
    },
    #[error("negotiated datagram contract was invalid: {0}")]
    Session(#[from] SessionError),
    #[error("failed to map manifest profile into the first carrier: {0}")]
    H3(#[from] ns_carrier_h3::H3TransportError),
}

#[cfg(test)]
mod tests {
    use super::*;
    use ns_manifest::{ManifestError, ManifestSigner};
    use ns_testkit::{
        FIXTURE_MANIFEST_KEY_ID, fixture_manifest_signing_key, fixture_manifest_trust_store,
        load_fixture_text, sample_manifest_document,
    };

    fn verification_now() -> OffsetDateTime {
        OffsetDateTime::parse(
            "2026-04-01T00:20:00Z",
            &time::format_description::well_known::Rfc3339,
        )
        .expect("fixture timestamp should parse")
    }

    #[test]
    fn builds_a_launch_plan_from_a_valid_manifest() {
        let plan = build_launch_plan(
            &ClientRuntimeConfig {
                manifest_url: Url::parse("https://bridge.example/v0/manifest")
                    .expect("fixture url should parse"),
                device_id: DeviceBindingId::new("device-1")
                    .expect("fixture device binding id should be valid"),
                client_version: "0.1.0".to_owned(),
                selected_carrier_profile: CarrierProfileId::new("carrier-primary")
                    .expect("fixture carrier profile should be valid"),
                datagram_rollout: H3DatagramRollout::Automatic,
            },
            &load_fixture_text("manifest/v1/valid/MF-MANIFEST-VALID-001.json"),
            &fixture_manifest_trust_store(),
            verification_now(),
        )
        .expect("valid manifest fixture should produce a launch plan");

        assert_eq!(plan.endpoint_id, "edge-1");
        assert_eq!(plan.endpoint_host, "edge.example.net");
        assert_eq!(plan.endpoint_port, 443);
        assert_eq!(plan.transport_origin_host, "origin.edge.example.net");
        assert_eq!(plan.transport_origin_port, 8443);
        assert_eq!(
            plan.transport_sni.as_deref(),
            Some("origin.edge.example.net")
        );
        assert_eq!(plan.transport_alpn, vec!["h3".to_owned()]);
        assert_eq!(plan.control_path, "/ns/control");
        assert_eq!(plan.relay_path, "/ns/relay");
        assert_eq!(
            plan.transport_headers.get("x-northstar-profile"),
            Some(&"carrier-primary".to_owned())
        );
        assert!(plan.datagram_enabled);
        assert_eq!(plan.datagram_rollout, H3DatagramRollout::Automatic);
        assert_eq!(plan.heartbeat_interval_ms, 20_000);
        assert_eq!(plan.idle_timeout_ms, 90_000);
        assert_eq!(plan.zero_rtt_policy, H3ZeroRttPolicy::Disabled);
        assert_eq!(plan.connect_backoff.initial_ms, 500);
        assert_eq!(plan.connect_backoff.max_ms, 10_000);
        assert_eq!(
            plan.token_exchange_url,
            Url::parse("https://bridge.example/v0/token/exchange")
                .expect("fixture token-exchange url should parse")
        );
    }

    #[test]
    fn rejects_a_tampered_manifest_before_endpoint_selection() {
        let error = build_launch_plan(
            &ClientRuntimeConfig {
                manifest_url: Url::parse("https://bridge.example/v0/manifest")
                    .expect("fixture url should parse"),
                device_id: DeviceBindingId::new("device-1")
                    .expect("fixture device binding id should be valid"),
                client_version: "0.1.0".to_owned(),
                selected_carrier_profile: CarrierProfileId::new("carrier-primary")
                    .expect("fixture carrier profile should be valid"),
                datagram_rollout: H3DatagramRollout::Automatic,
            },
            &load_fixture_text("manifest/v1/invalid/MF-MANIFEST-BADSIG-002.json"),
            &fixture_manifest_trust_store(),
            verification_now(),
        )
        .expect_err("tampered manifest should be rejected");

        assert!(matches!(
            error,
            ClientRuntimeError::Manifest(ManifestError::SignatureVerificationFailed)
        ));
    }

    #[test]
    fn launch_planning_can_fail_closed_by_local_datagram_rollout_policy() {
        let plan = build_launch_plan(
            &ClientRuntimeConfig {
                manifest_url: Url::parse("https://bridge.example/v0/manifest")
                    .expect("fixture url should parse"),
                device_id: DeviceBindingId::new("device-1")
                    .expect("fixture device binding id should be valid"),
                client_version: "0.1.0".to_owned(),
                selected_carrier_profile: CarrierProfileId::new("carrier-primary")
                    .expect("fixture carrier profile should be valid"),
                datagram_rollout: H3DatagramRollout::Disabled,
            },
            &load_fixture_text("manifest/v1/valid/MF-MANIFEST-VALID-001.json"),
            &fixture_manifest_trust_store(),
            verification_now(),
        )
        .expect("valid manifest fixture should still build a launch plan");

        let transport = plan.h3_transport_config();
        assert!(!transport.datagram_runtime_enabled());
        assert_eq!(
            transport.advertised_datagram_mode(true),
            ns_core::DatagramMode::DisabledByPolicy
        );
    }

    #[test]
    fn launch_planning_preserves_canary_rollout_stage() {
        let plan = build_launch_plan(
            &ClientRuntimeConfig {
                manifest_url: Url::parse("https://bridge.example/v0/manifest")
                    .expect("fixture url should parse"),
                device_id: DeviceBindingId::new("device-1")
                    .expect("fixture device binding id should be valid"),
                client_version: "0.1.0".to_owned(),
                selected_carrier_profile: CarrierProfileId::new("carrier-primary")
                    .expect("fixture carrier profile should be valid"),
                datagram_rollout: H3DatagramRollout::Canary,
            },
            &load_fixture_text("manifest/v1/valid/MF-MANIFEST-VALID-001.json"),
            &fixture_manifest_trust_store(),
            verification_now(),
        )
        .expect("valid manifest fixture should still build a launch plan");

        let transport = plan.h3_transport_config();
        assert!(transport.datagram_runtime_enabled());
        assert_eq!(transport.rollout_stage_label(), "canary");
    }

    #[test]
    fn launch_planning_rejects_enabled_rollout_when_signed_profile_disables_datagrams() {
        let generated_at = OffsetDateTime::parse(
            "2026-04-01T00:00:00Z",
            &time::format_description::well_known::Rfc3339,
        )
        .expect("fixture timestamp should parse");
        let expires_at = OffsetDateTime::parse(
            "2026-04-01T01:00:00Z",
            &time::format_description::well_known::Rfc3339,
        )
        .expect("fixture timestamp should parse");
        let mut manifest = sample_manifest_document(generated_at, expires_at);
        manifest.carrier_profiles[0].datagram_enabled = false;
        ManifestSigner::new(FIXTURE_MANIFEST_KEY_ID, fixture_manifest_signing_key())
            .sign(&mut manifest)
            .expect("fixture manifest should sign");
        let manifest_json =
            serde_json::to_string(&manifest).expect("fixture manifest should serialize");

        let error = build_launch_plan(
            &ClientRuntimeConfig {
                manifest_url: Url::parse("https://bridge.example/v0/manifest")
                    .expect("fixture url should parse"),
                device_id: DeviceBindingId::new("device-1")
                    .expect("fixture device binding id should be valid"),
                client_version: "0.1.0".to_owned(),
                selected_carrier_profile: CarrierProfileId::new("carrier-primary")
                    .expect("fixture carrier profile should be valid"),
                datagram_rollout: H3DatagramRollout::Automatic,
            },
            &manifest_json,
            &fixture_manifest_trust_store(),
            verification_now(),
        )
        .expect_err("enabled local rollout should reject signed profiles that disable datagrams");

        assert!(matches!(
            error,
            ClientRuntimeError::IncompatibleDatagramRollout {
                carrier_profile_id,
                rollout_stage: H3DatagramRollout::Automatic,
            } if carrier_profile_id == "carrier-primary"
        ));
    }

    #[test]
    fn launch_planning_allows_disabled_rollout_when_signed_profile_disables_datagrams() {
        let generated_at = OffsetDateTime::parse(
            "2026-04-01T00:00:00Z",
            &time::format_description::well_known::Rfc3339,
        )
        .expect("fixture timestamp should parse");
        let expires_at = OffsetDateTime::parse(
            "2026-04-01T01:00:00Z",
            &time::format_description::well_known::Rfc3339,
        )
        .expect("fixture timestamp should parse");
        let mut manifest = sample_manifest_document(generated_at, expires_at);
        manifest.carrier_profiles[0].datagram_enabled = false;
        ManifestSigner::new(FIXTURE_MANIFEST_KEY_ID, fixture_manifest_signing_key())
            .sign(&mut manifest)
            .expect("fixture manifest should sign");
        let manifest_json =
            serde_json::to_string(&manifest).expect("fixture manifest should serialize");

        let plan = build_launch_plan(
            &ClientRuntimeConfig {
                manifest_url: Url::parse("https://bridge.example/v0/manifest")
                    .expect("fixture url should parse"),
                device_id: DeviceBindingId::new("device-1")
                    .expect("fixture device binding id should be valid"),
                client_version: "0.1.0".to_owned(),
                selected_carrier_profile: CarrierProfileId::new("carrier-primary")
                    .expect("fixture carrier profile should be valid"),
                datagram_rollout: H3DatagramRollout::Disabled,
            },
            &manifest_json,
            &fixture_manifest_trust_store(),
            verification_now(),
        )
        .expect("disabled local rollout should allow signed profiles that disable datagrams");

        let transport = plan.h3_transport_config();
        assert!(!transport.datagram_enabled);
        assert!(!transport.datagram_runtime_enabled());
        assert_eq!(transport.rollout_stage_label(), "disabled");
    }

    #[test]
    fn launch_plan_exposes_the_expected_server_datagram_contract() {
        let plan = build_launch_plan(
            &ClientRuntimeConfig {
                manifest_url: Url::parse("https://bridge.example/v0/manifest")
                    .expect("fixture url should parse"),
                device_id: DeviceBindingId::new("device-1")
                    .expect("fixture device binding id should be valid"),
                client_version: "0.1.0".to_owned(),
                selected_carrier_profile: CarrierProfileId::new("carrier-primary")
                    .expect("fixture carrier profile should be valid"),
                datagram_rollout: H3DatagramRollout::Automatic,
            },
            &load_fixture_text("manifest/v1/valid/MF-MANIFEST-VALID-001.json"),
            &fixture_manifest_trust_store(),
            verification_now(),
        )
        .expect("valid manifest fixture should still build a launch plan");

        assert_eq!(
            plan.expected_server_datagram_mode(true),
            DatagramMode::AvailableAndEnabled
        );
        assert_eq!(
            plan.expected_server_datagram_mode(false),
            DatagramMode::Unavailable
        );

        let mut disabled = plan.clone();
        disabled.datagram_rollout = H3DatagramRollout::Disabled;
        assert_eq!(
            disabled.expected_server_datagram_mode(true),
            DatagramMode::DisabledByPolicy
        );
    }

    #[test]
    fn launch_plan_exposes_a_public_datagram_startup_contract() {
        let plan = build_launch_plan(
            &ClientRuntimeConfig {
                manifest_url: Url::parse("https://bridge.example/v0/manifest")
                    .expect("fixture url should parse"),
                device_id: DeviceBindingId::new("device-1")
                    .expect("fixture device binding id should be valid"),
                client_version: "0.1.0".to_owned(),
                selected_carrier_profile: CarrierProfileId::new("carrier-primary")
                    .expect("fixture carrier profile should be valid"),
                datagram_rollout: H3DatagramRollout::Canary,
            },
            &load_fixture_text("manifest/v1/valid/MF-MANIFEST-VALID-001.json"),
            &fixture_manifest_trust_store(),
            verification_now(),
        )
        .expect("valid manifest fixture should still build a launch plan");

        let contract = plan.datagram_startup_contract(true);
        assert!(contract.signed_datagram_enabled);
        assert_eq!(contract.datagram_rollout, H3DatagramRollout::Canary);
        assert!(contract.carrier_datagrams_available);
        assert_eq!(
            contract.expected_server_datagram_mode,
            DatagramMode::AvailableAndEnabled
        );
        assert_eq!(contract.rollout_stage, "canary");
    }

    #[test]
    fn launch_plan_validates_startup_contract_through_the_public_runtime_surface() {
        let plan = build_launch_plan(
            &ClientRuntimeConfig {
                manifest_url: Url::parse("https://bridge.example/v0/manifest")
                    .expect("fixture url should parse"),
                device_id: DeviceBindingId::new("device-1")
                    .expect("fixture device binding id should be valid"),
                client_version: "0.1.0".to_owned(),
                selected_carrier_profile: CarrierProfileId::new("carrier-primary")
                    .expect("fixture carrier profile should be valid"),
                datagram_rollout: H3DatagramRollout::Automatic,
            },
            &load_fixture_text("manifest/v1/valid/MF-MANIFEST-VALID-001.json"),
            &fixture_manifest_trust_store(),
            verification_now(),
        )
        .expect("valid manifest fixture should still build a launch plan");

        let contract = plan
            .validate_startup_datagram_contract(false)
            .expect("startup validation should stay available through the public runtime API");

        assert_eq!(
            contract.expected_server_datagram_mode,
            DatagramMode::Unavailable
        );
        assert_eq!(contract.rollout_stage, "automatic");
    }

    #[test]
    fn negotiated_datagram_contract_rejects_policy_epoch_drift() {
        let plan = build_launch_plan(
            &ClientRuntimeConfig {
                manifest_url: Url::parse("https://bridge.example/v0/manifest")
                    .expect("fixture url should parse"),
                device_id: DeviceBindingId::new("device-1")
                    .expect("fixture device binding id should be valid"),
                client_version: "0.1.0".to_owned(),
                selected_carrier_profile: CarrierProfileId::new("carrier-primary")
                    .expect("fixture carrier profile should be valid"),
                datagram_rollout: H3DatagramRollout::Automatic,
            },
            &load_fixture_text("manifest/v1/valid/MF-MANIFEST-VALID-001.json"),
            &fixture_manifest_trust_store(),
            verification_now(),
        )
        .expect("valid manifest fixture should still build a launch plan");

        let error = plan
            .validate_negotiated_datagram_contract(&ClientNegotiatedDatagramContractInput {
                expected_policy_epoch: 7,
                expected_max_udp_flows: 4,
                expected_max_udp_payload: 1_200,
                requested_max_udp_payload: 1_100,
                carrier_datagrams_available: true,
                received_policy_epoch: 6,
                received_datagram_mode: DatagramMode::AvailableAndEnabled,
                received_max_udp_flows: 4,
                received_effective_max_udp_payload: 1_100,
            })
            .expect_err("policy epoch drift should fail client datagram contract validation");

        assert!(matches!(
            error,
            ClientRuntimeError::Session(SessionError::IncompatiblePolicyEpoch {
                expected_policy_epoch: 7,
                received_policy_epoch: 6,
            })
        ));
    }

    #[test]
    fn negotiated_datagram_contract_accepts_signed_and_negotiated_udp_limits() {
        let plan = build_launch_plan(
            &ClientRuntimeConfig {
                manifest_url: Url::parse("https://bridge.example/v0/manifest")
                    .expect("fixture url should parse"),
                device_id: DeviceBindingId::new("device-1")
                    .expect("fixture device binding id should be valid"),
                client_version: "0.1.0".to_owned(),
                selected_carrier_profile: CarrierProfileId::new("carrier-primary")
                    .expect("fixture carrier profile should be valid"),
                datagram_rollout: H3DatagramRollout::Automatic,
            },
            &load_fixture_text("manifest/v1/valid/MF-MANIFEST-VALID-001.json"),
            &fixture_manifest_trust_store(),
            verification_now(),
        )
        .expect("valid manifest fixture should still build a launch plan");

        plan.validate_negotiated_datagram_contract(&ClientNegotiatedDatagramContractInput {
            expected_policy_epoch: 7,
            expected_max_udp_flows: 4,
            expected_max_udp_payload: 1_200,
            requested_max_udp_payload: 1_100,
            carrier_datagrams_available: true,
            received_policy_epoch: 7,
            received_datagram_mode: DatagramMode::AvailableAndEnabled,
            received_max_udp_flows: 2,
            received_effective_max_udp_payload: 1_000,
        })
        .expect("smaller negotiated UDP limits should remain valid");
    }
}
