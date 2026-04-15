#![forbid(unsafe_code)]

use async_trait::async_trait;
use bytes::Bytes;
use ns_core::{
    Capability, CarrierProfileId, DatagramMode, ManifestId, ProtocolErrorCode, SessionId,
    TransportMode, TransportSelection, ValidationError,
};
use ns_policy::EffectiveSessionPolicy;
use ns_wire::{
    ClientHello, ServerHello, StreamOpen, UdpDatagram, UdpFlowOk, UdpFlowOpen, UdpStreamOpen,
};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};
use thiserror::Error;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CarrierSessionInfo {
    pub carrier_profile_id: CarrierProfileId,
    pub datagrams_available: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IncomingRelayStream<R> {
    pub relay_id: u64,
    pub stream: R,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IncomingUdpFallbackStream<R> {
    pub flow_id: u64,
    pub stream: R,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TransportErrorKind {
    ProtocolViolation,
    ConnectionLost,
    TimedOut,
    Backpressure,
    Unsupported,
    CarrierRejected,
}

#[derive(Debug, Clone, PartialEq, Eq, Error, Serialize, Deserialize)]
#[error("{kind:?}: {message}")]
pub struct TransportError {
    pub kind: TransportErrorKind,
    pub message: String,
}

#[async_trait]
pub trait ControlFrameIo: Send {
    async fn read_frame(&mut self) -> Result<ns_wire::Frame, TransportError>;
    async fn write_frame(&mut self, frame: &ns_wire::Frame) -> Result<(), TransportError>;
}

#[async_trait]
pub trait RelayStreamIo: Send {
    async fn write_preamble(&mut self, frame: &ns_wire::Frame) -> Result<(), TransportError>;
    async fn read_preamble(&mut self) -> Result<ns_wire::Frame, TransportError>;
    async fn send_raw(&mut self, chunk: Bytes) -> Result<(), TransportError>;
    async fn recv_raw(&mut self) -> Result<Option<Bytes>, TransportError>;
    async fn finish_raw(&mut self) -> Result<(), TransportError>;
}

#[async_trait]
pub trait DatagramIo: Send + Sync {
    async fn send(&self, datagram: UdpDatagram) -> Result<(), TransportError>;
    async fn recv(&self) -> Result<Option<UdpDatagram>, TransportError>;
}

#[async_trait]
pub trait UdpFallbackStreamIo: Send {
    async fn write_frame(&mut self, frame: &ns_wire::Frame) -> Result<(), TransportError>;
    async fn read_frame(&mut self) -> Result<ns_wire::Frame, TransportError>;
}

#[async_trait]
pub trait PendingCarrierSession: Send {
    type Control: ControlFrameIo;
    type Established: EstablishedCarrierSession;

    fn info(&self) -> &CarrierSessionInfo;
    fn control(&mut self) -> &mut Self::Control;
    async fn into_established(self) -> Result<Self::Established, TransportError>;
}

#[async_trait]
pub trait EstablishedCarrierSession: Send {
    type Control: ControlFrameIo;
    type Relay: RelayStreamIo;
    type Datagram: DatagramIo;
    type UdpFallback: UdpFallbackStreamIo;

    fn info(&self) -> &CarrierSessionInfo;
    fn control(&mut self) -> &mut Self::Control;
    async fn open_relay_stream(&mut self, open: StreamOpen) -> Result<Self::Relay, TransportError>;
    async fn accept_relay_stream(
        &mut self,
    ) -> Result<IncomingRelayStream<Self::Relay>, TransportError>;
    async fn open_udp_fallback_stream(
        &mut self,
        open: UdpStreamOpen,
    ) -> Result<Self::UdpFallback, TransportError>;
    async fn accept_udp_fallback_stream(
        &mut self,
    ) -> Result<IncomingUdpFallbackStream<Self::UdpFallback>, TransportError>;
    fn datagrams(&self) -> Option<&Self::Datagram>;
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SessionPhase {
    AwaitingClientHello,
    AwaitingServerHello,
    Open,
    Draining,
    Closed,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct GatewayAdmissionContext {
    pub manifest_id: ManifestId,
    pub device_binding_id: Option<String>,
    pub allowed_core_versions: Vec<u64>,
    pub allowed_capabilities: Vec<Capability>,
    pub allowed_carrier_profiles: Vec<CarrierProfileId>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ValidatedClientHello {
    pub transport: TransportSelection,
    pub requested_capabilities: Vec<Capability>,
    pub manifest_id: ManifestId,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SessionController {
    pub phase: SessionPhase,
    pub session_id: Option<SessionId>,
    pub active_relays: BTreeSet<u64>,
    pub active_udp_flows: BTreeMap<u64, TransportMode>,
    pub policy: EffectiveSessionPolicy,
}

#[derive(Debug, Error)]
pub enum SessionError {
    #[error("validation failed: {0}")]
    Validation(#[from] ValidationError),
    #[error("hello requested an invalid version range {min_version}..{max_version}")]
    InvalidVersionRange { min_version: u64, max_version: u64 },
    #[error("hello requested unsupported core version {0}")]
    UnsupportedCoreVersion(u64),
    #[error("hello requested version range {min_version}..{max_version} with no supported overlap")]
    NoSupportedVersionOverlap { min_version: u64, max_version: u64 },
    #[error("hello requested unsupported carrier profile {0}")]
    UnsupportedCarrierProfile(String),
    #[error("hello requested unsupported capabilities")]
    UnsupportedCapabilities,
    #[error("hello manifest does not match validated auth context")]
    ManifestMismatch,
    #[error("hello device binding does not match validated auth context")]
    DeviceBindingMismatch,
    #[error("server selected capabilities not requested by the client")]
    InvalidCapabilitySelection,
    #[error("server hello version {0} is outside the requested range")]
    InvalidSelectedVersion(u64),
    #[error(
        "server hello policy epoch {received_policy_epoch} did not match the expected epoch {expected_policy_epoch}"
    )]
    IncompatiblePolicyEpoch {
        expected_policy_epoch: u64,
        received_policy_epoch: u64,
    },
    #[error(
        "server hello datagram mode {received_datagram_mode:?} was incompatible with local expectation {expected_datagram_mode:?}"
    )]
    InvalidServerDatagramMode {
        expected_datagram_mode: DatagramMode,
        received_datagram_mode: DatagramMode,
    },
    #[error(
        "server hello max_udp_flows {received_max_udp_flows} exceeded the allowed maximum {max_udp_flows}"
    )]
    InvalidServerUdpFlowLimit {
        max_udp_flows: u64,
        received_max_udp_flows: u64,
    },
    #[error(
        "server hello effective_max_udp_payload {received_max_udp_payload} exceeded the allowed maximum {max_udp_payload} or the client-requested maximum {requested_max_udp_payload}"
    )]
    InvalidServerUdpPayloadLimit {
        max_udp_payload: u64,
        requested_max_udp_payload: u64,
        received_max_udp_payload: u64,
    },
    #[error("server hello advertised an unusable zero value for {field}")]
    InvalidServerLimit { field: &'static str },
    #[error("relay id {0} is already active")]
    DuplicateRelayId(u64),
    #[error("udp flow id {0} is already active")]
    DuplicateFlowId(u64),
    #[error("udp flow id {0} is not active")]
    UnknownUdpFlowId(u64),
    #[error("udp flow id {flow_id} expected transport mode {expected:?} but observed {actual:?}")]
    InvalidUdpFlowTransportMode {
        flow_id: u64,
        expected: TransportMode,
        actual: TransportMode,
    },
    #[error(
        "relay open exceeds the configured concurrent relay limit of {max_concurrent_relay_streams}"
    )]
    RelayLimitExceeded { max_concurrent_relay_streams: u64 },
    #[error("udp flow open exceeds the configured concurrent udp-flow limit of {max_udp_flows}")]
    UdpFlowLimitExceeded { max_udp_flows: u64 },
    #[error("udp datagram mode was unavailable and stream fallback was not allowed")]
    DatagramUnavailable,
    #[error("session is not open")]
    SessionNotOpen,
}

impl SessionError {
    pub fn protocol_error_code(&self) -> Option<ProtocolErrorCode> {
        match self {
            Self::DuplicateRelayId(_)
            | Self::DuplicateFlowId(_)
            | Self::UnknownUdpFlowId(_)
            | Self::InvalidUdpFlowTransportMode { .. }
            | Self::SessionNotOpen => Some(ProtocolErrorCode::ProtocolViolation),
            Self::RelayLimitExceeded { .. } | Self::UdpFlowLimitExceeded { .. } => {
                Some(ProtocolErrorCode::FlowLimitReached)
            }
            Self::DatagramUnavailable => Some(ProtocolErrorCode::UdpDatagramUnavailable),
            _ => None,
        }
    }
}

impl GatewayAdmissionContext {
    pub fn validate_client_hello(
        &self,
        hello: &ClientHello,
    ) -> Result<ValidatedClientHello, SessionError> {
        if hello.min_version > hello.max_version {
            return Err(SessionError::InvalidVersionRange {
                min_version: hello.min_version,
                max_version: hello.max_version,
            });
        }
        if !self
            .allowed_core_versions
            .iter()
            .any(|version| *version >= hello.min_version && *version <= hello.max_version)
        {
            return Err(SessionError::NoSupportedVersionOverlap {
                min_version: hello.min_version,
                max_version: hello.max_version,
            });
        }
        if hello.manifest_id != self.manifest_id {
            return Err(SessionError::ManifestMismatch);
        }
        if let Some(expected) = &self.device_binding_id
            && hello.device_binding_id.as_str() != expected
        {
            return Err(SessionError::DeviceBindingMismatch);
        }
        if !self
            .allowed_carrier_profiles
            .iter()
            .any(|profile| profile == &hello.carrier_profile_id)
        {
            return Err(SessionError::UnsupportedCarrierProfile(
                hello.carrier_profile_id.as_str().to_owned(),
            ));
        }
        if hello
            .requested_capabilities
            .iter()
            .any(|capability| !self.allowed_capabilities.contains(capability))
        {
            return Err(SessionError::UnsupportedCapabilities);
        }

        Ok(ValidatedClientHello {
            transport: TransportSelection {
                carrier_kind: hello.carrier_kind,
                carrier_profile_id: hello.carrier_profile_id.clone(),
                requested_capabilities: hello.requested_capabilities.clone(),
            },
            requested_capabilities: hello.requested_capabilities.clone(),
            manifest_id: hello.manifest_id.clone(),
        })
    }
}

impl SessionController {
    pub fn new_client(policy: EffectiveSessionPolicy) -> Self {
        Self {
            phase: SessionPhase::AwaitingServerHello,
            session_id: None,
            active_relays: BTreeSet::new(),
            active_udp_flows: BTreeMap::new(),
            policy,
        }
    }

    pub fn new_gateway(policy: EffectiveSessionPolicy) -> Self {
        Self {
            phase: SessionPhase::AwaitingClientHello,
            session_id: None,
            active_relays: BTreeSet::new(),
            active_udp_flows: BTreeMap::new(),
            policy,
        }
    }

    pub fn apply_server_hello(
        &mut self,
        request: &ClientHello,
        response: &ServerHello,
    ) -> Result<(), SessionError> {
        if response.selected_version < request.min_version
            || response.selected_version > request.max_version
        {
            return Err(SessionError::InvalidSelectedVersion(
                response.selected_version,
            ));
        }
        if response
            .selected_capabilities
            .iter()
            .any(|capability| !request.requested_capabilities.contains(capability))
        {
            return Err(SessionError::InvalidCapabilitySelection);
        }
        if response.policy_epoch != self.policy.policy_epoch {
            return Err(SessionError::IncompatiblePolicyEpoch {
                expected_policy_epoch: self.policy.policy_epoch,
                received_policy_epoch: response.policy_epoch,
            });
        }
        for (field, value) in [
            (
                "effective_idle_timeout_ms",
                response.effective_idle_timeout_ms,
            ),
            ("session_lifetime_ms", response.session_lifetime_ms),
            (
                "max_concurrent_relay_streams",
                response.max_concurrent_relay_streams,
            ),
            ("max_udp_flows", response.max_udp_flows),
            (
                "effective_max_udp_payload",
                response.effective_max_udp_payload,
            ),
        ] {
            if value == 0 {
                return Err(SessionError::InvalidServerLimit { field });
            }
        }
        if !server_datagram_mode_is_compatible(
            self.policy.limits.datagram_mode,
            response.datagram_mode,
        ) {
            return Err(SessionError::InvalidServerDatagramMode {
                expected_datagram_mode: self.policy.limits.datagram_mode,
                received_datagram_mode: response.datagram_mode,
            });
        }
        if response.max_udp_flows > self.policy.limits.max_udp_flows {
            return Err(SessionError::InvalidServerUdpFlowLimit {
                max_udp_flows: self.policy.limits.max_udp_flows,
                received_max_udp_flows: response.max_udp_flows,
            });
        }
        let allowed_udp_payload = self
            .policy
            .limits
            .max_udp_payload
            .min(request.requested_max_udp_payload);
        if response.effective_max_udp_payload > allowed_udp_payload {
            return Err(SessionError::InvalidServerUdpPayloadLimit {
                max_udp_payload: self.policy.limits.max_udp_payload,
                requested_max_udp_payload: request.requested_max_udp_payload,
                received_max_udp_payload: response.effective_max_udp_payload,
            });
        }

        self.policy.limits.datagram_mode = response.datagram_mode;
        self.policy.limits.max_udp_flows = response.max_udp_flows;
        self.policy.limits.max_udp_payload = response.effective_max_udp_payload;
        self.phase = SessionPhase::Open;
        self.session_id = Some(response.session_id);
        Ok(())
    }

    pub fn accept_hello(&mut self, session_id: SessionId) {
        self.session_id = Some(session_id);
        self.phase = SessionPhase::Open;
    }

    pub fn register_stream_open(&mut self, frame: &StreamOpen) -> Result<(), SessionError> {
        if self.phase != SessionPhase::Open {
            return Err(SessionError::SessionNotOpen);
        }
        if self.active_relays.len() as u64 >= self.policy.limits.max_concurrent_relay_streams {
            return Err(SessionError::RelayLimitExceeded {
                max_concurrent_relay_streams: self.policy.limits.max_concurrent_relay_streams,
            });
        }
        if !self.active_relays.insert(frame.relay_id) {
            return Err(SessionError::DuplicateRelayId(frame.relay_id));
        }
        Ok(())
    }

    pub fn release_relay(&mut self, relay_id: u64) -> bool {
        self.active_relays.remove(&relay_id)
    }

    pub fn register_udp_flow_open(
        &mut self,
        frame: &UdpFlowOpen,
        carrier_datagrams_available: bool,
    ) -> Result<UdpFlowOk, SessionError> {
        if self.phase != SessionPhase::Open {
            return Err(SessionError::SessionNotOpen);
        }
        if self.active_udp_flows.len() as u64 >= self.policy.limits.max_udp_flows {
            return Err(SessionError::UdpFlowLimitExceeded {
                max_udp_flows: self.policy.limits.max_udp_flows,
            });
        }
        if self.active_udp_flows.contains_key(&frame.flow_id) {
            return Err(SessionError::DuplicateFlowId(frame.flow_id));
        }

        let transport_mode =
            self.choose_udp_transport_mode(frame.flags, carrier_datagrams_available);
        match transport_mode {
            Some(transport_mode) => {
                self.active_udp_flows.insert(frame.flow_id, transport_mode);
                Ok(UdpFlowOk {
                    flow_id: frame.flow_id,
                    transport_mode,
                    effective_idle_timeout_ms: frame
                        .idle_timeout_ms
                        .min(self.policy.limits.idle_timeout_ms),
                    effective_max_payload: self.policy.limits.max_udp_payload,
                    metadata: Vec::new(),
                })
            }
            None => Err(SessionError::DatagramUnavailable),
        }
    }

    fn choose_udp_transport_mode(
        &self,
        flags: ns_wire::FlowFlags,
        carrier_datagrams_available: bool,
    ) -> Option<TransportMode> {
        let datagrams_negotiated = self.policy.limits.datagram_mode
            == DatagramMode::AvailableAndEnabled
            && carrier_datagrams_available;
        if datagrams_negotiated {
            return Some(TransportMode::Datagram);
        }
        if flags.allow_stream_fallback() {
            return Some(TransportMode::StreamFallback);
        }
        None
    }

    pub fn validate_udp_datagram(&self, datagram: &UdpDatagram) -> Result<(), SessionError> {
        if self.phase != SessionPhase::Open {
            return Err(SessionError::SessionNotOpen);
        }
        self.validate_udp_flow_transport(datagram.flow_id, TransportMode::Datagram)
    }

    pub fn validate_udp_fallback_stream(&self, flow_id: u64) -> Result<(), SessionError> {
        if self.phase != SessionPhase::Open {
            return Err(SessionError::SessionNotOpen);
        }
        self.validate_udp_flow_transport(flow_id, TransportMode::StreamFallback)
    }

    pub fn close_udp_flow(
        &mut self,
        flow_id: u64,
        transport_mode: TransportMode,
    ) -> Result<(), SessionError> {
        self.validate_udp_flow_transport(flow_id, transport_mode)?;
        self.active_udp_flows.remove(&flow_id);
        Ok(())
    }

    fn validate_udp_flow_transport(
        &self,
        flow_id: u64,
        expected_transport: TransportMode,
    ) -> Result<(), SessionError> {
        let actual_transport = self
            .active_udp_flows
            .get(&flow_id)
            .copied()
            .ok_or(SessionError::UnknownUdpFlowId(flow_id))?;
        if actual_transport != expected_transport {
            return Err(SessionError::InvalidUdpFlowTransportMode {
                flow_id,
                expected: expected_transport,
                actual: actual_transport,
            });
        }
        Ok(())
    }

    pub fn release_udp_flow(&mut self, flow_id: u64) -> bool {
        self.active_udp_flows.remove(&flow_id).is_some()
    }
}

fn server_datagram_mode_is_compatible(expected: DatagramMode, received: DatagramMode) -> bool {
    match expected {
        DatagramMode::DisabledByPolicy => received == DatagramMode::DisabledByPolicy,
        DatagramMode::Unavailable => received == DatagramMode::Unavailable,
        DatagramMode::AvailableAndEnabled => matches!(
            received,
            DatagramMode::AvailableAndEnabled | DatagramMode::Unavailable
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ns_core::{CarrierKind, DeviceBindingId, ManifestId};
    use ns_policy::EffectiveSessionPolicy;
    use ns_wire::{FlowFlags, OpenFlags, TargetAddress, UdpFlowOpen};

    fn hello() -> ClientHello {
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
            token: b"token".to_vec(),
            client_metadata: Vec::new(),
        }
    }

    fn server_hello() -> ServerHello {
        ServerHello {
            selected_version: 1,
            session_id: SessionId::random(),
            server_nonce: [2_u8; 32],
            selected_capabilities: vec![Capability::TcpRelay, Capability::UdpRelay],
            policy_epoch: 1,
            effective_idle_timeout_ms: 30_000,
            session_lifetime_ms: 300_000,
            max_concurrent_relay_streams: 8,
            max_udp_flows: 4,
            effective_max_udp_payload: 1_200,
            datagram_mode: ns_core::DatagramMode::AvailableAndEnabled,
            stats_mode: ns_core::StatsMode::Off,
            server_metadata: Vec::new(),
        }
    }

    #[test]
    fn admission_rejects_wrong_manifest() {
        let context = GatewayAdmissionContext {
            manifest_id: ManifestId::new("man-2026-04-01-999")
                .expect("fixture manifest id should be valid"),
            device_binding_id: Some("device-1".to_owned()),
            allowed_core_versions: vec![1],
            allowed_capabilities: vec![Capability::TcpRelay, Capability::UdpRelay],
            allowed_carrier_profiles: vec![
                CarrierProfileId::new("carrier-primary")
                    .expect("fixture carrier profile should be valid"),
            ],
        };

        assert!(matches!(
            context.validate_client_hello(&hello()),
            Err(SessionError::ManifestMismatch)
        ));
    }

    #[test]
    fn client_rejects_server_capability_drift() {
        let mut session =
            SessionController::new_client(EffectiveSessionPolicy::tcp_and_udp_defaults(1));
        let request = hello();
        let mut response = server_hello();
        response.selected_capabilities = vec![Capability::TcpRelay, Capability::QuicDatagram];

        assert!(matches!(
            session.apply_server_hello(&request, &response),
            Err(SessionError::InvalidCapabilitySelection)
        ));
    }

    #[test]
    fn client_rejects_server_hello_policy_epoch_drift() {
        let mut session =
            SessionController::new_client(EffectiveSessionPolicy::tcp_and_udp_defaults(7));
        let request = hello();
        let mut response = server_hello();
        response.policy_epoch = 6;

        assert!(matches!(
            session.apply_server_hello(&request, &response),
            Err(SessionError::IncompatiblePolicyEpoch {
                expected_policy_epoch: 7,
                received_policy_epoch: 6,
            })
        ));
    }

    #[test]
    fn client_rejects_server_hello_datagram_mode_that_conflicts_with_local_rollout() {
        let mut policy = EffectiveSessionPolicy::tcp_and_udp_defaults(1);
        policy.limits.datagram_mode = DatagramMode::DisabledByPolicy;
        let mut session = SessionController::new_client(policy);
        let request = hello();
        let mut response = server_hello();
        response.datagram_mode = DatagramMode::AvailableAndEnabled;

        assert!(matches!(
            session.apply_server_hello(&request, &response),
            Err(SessionError::InvalidServerDatagramMode {
                expected_datagram_mode: DatagramMode::DisabledByPolicy,
                received_datagram_mode: DatagramMode::AvailableAndEnabled,
            })
        ));
    }

    #[test]
    fn client_allows_server_hello_to_surface_carrier_unavailable_datagrams() {
        let mut session =
            SessionController::new_client(EffectiveSessionPolicy::tcp_and_udp_defaults(1));
        let request = hello();
        let mut response = server_hello();
        response.datagram_mode = DatagramMode::Unavailable;

        session.apply_server_hello(&request, &response).expect(
            "carrier-unavailable datagrams should stay compatible with enabled local policy",
        );
        assert_eq!(session.phase, SessionPhase::Open);
    }

    #[test]
    fn client_applies_negotiated_udp_flow_limit_after_server_hello() {
        let mut policy = EffectiveSessionPolicy::tcp_and_udp_defaults(1);
        policy.limits.max_udp_flows = 4;
        let mut session = SessionController::new_client(policy);
        let request = hello();
        let mut response = server_hello();
        response.max_udp_flows = 1;

        session
            .apply_server_hello(&request, &response)
            .expect("smaller negotiated udp-flow limit should be accepted");

        let first = UdpFlowOpen {
            flow_id: 21,
            target: ns_wire::TargetAddress::Domain("resolver.example.net".to_owned()),
            target_port: 53,
            idle_timeout_ms: 5_000,
            flags: ns_wire::FlowFlags::new(0b0011).expect("fixture udp flow flags should be valid"),
            metadata: Vec::new(),
        };
        let second = UdpFlowOpen {
            flow_id: 22,
            ..first.clone()
        };

        session
            .register_udp_flow_open(&first, true)
            .expect("the first negotiated udp flow should be accepted");
        let error = session
            .register_udp_flow_open(&second, true)
            .expect_err("negotiated udp-flow limit should clamp future local opens");
        assert!(matches!(
            error,
            SessionError::UdpFlowLimitExceeded { max_udp_flows: 1 }
        ));
    }

    #[test]
    fn client_applies_negotiated_udp_payload_limit_after_server_hello() {
        let mut policy = EffectiveSessionPolicy::tcp_and_udp_defaults(1);
        policy.limits.max_udp_payload = 1_200;
        let mut session = SessionController::new_client(policy);
        let mut request = hello();
        request.requested_max_udp_payload = 1_100;
        let mut response = server_hello();
        response.effective_max_udp_payload = 900;

        session
            .apply_server_hello(&request, &response)
            .expect("smaller negotiated udp payload limit should be accepted");

        let open = UdpFlowOpen {
            flow_id: 23,
            target: ns_wire::TargetAddress::Domain("resolver.example.net".to_owned()),
            target_port: 53,
            idle_timeout_ms: 5_000,
            flags: ns_wire::FlowFlags::new(0b0001).expect("fixture udp flow flags should be valid"),
            metadata: Vec::new(),
        };

        let ok = session
            .register_udp_flow_open(&open, true)
            .expect("datagram flow should still open under the negotiated payload ceiling");
        assert_eq!(ok.effective_max_payload, 900);
    }

    #[test]
    fn client_rejects_server_hello_udp_flow_limit_drift() {
        let mut policy = EffectiveSessionPolicy::tcp_and_udp_defaults(1);
        policy.limits.max_udp_flows = 4;
        let mut session = SessionController::new_client(policy);
        let request = hello();
        let mut response = server_hello();
        response.max_udp_flows = 5;

        assert!(matches!(
            session.apply_server_hello(&request, &response),
            Err(SessionError::InvalidServerUdpFlowLimit {
                max_udp_flows: 4,
                received_max_udp_flows: 5,
            })
        ));
    }

    #[test]
    fn client_rejects_server_hello_udp_payload_drift() {
        let mut policy = EffectiveSessionPolicy::tcp_and_udp_defaults(1);
        policy.limits.max_udp_payload = 900;
        let mut session = SessionController::new_client(policy);
        let mut request = hello();
        request.requested_max_udp_payload = 1_000;
        let mut response = server_hello();
        response.effective_max_udp_payload = 901;

        assert!(matches!(
            session.apply_server_hello(&request, &response),
            Err(SessionError::InvalidServerUdpPayloadLimit {
                max_udp_payload: 900,
                requested_max_udp_payload: 1_000,
                received_max_udp_payload: 901,
            })
        ));
    }

    #[test]
    fn client_rejects_server_hello_with_unusable_zero_limits() {
        let mut session =
            SessionController::new_client(EffectiveSessionPolicy::tcp_and_udp_defaults(1));
        let request = hello();
        let mut response = server_hello();
        response.max_udp_flows = 0;

        assert!(matches!(
            session.apply_server_hello(&request, &response),
            Err(SessionError::InvalidServerLimit {
                field: "max_udp_flows"
            })
        ));
    }

    #[test]
    fn admission_rejects_invalid_requested_version_range() {
        let mut request = hello();
        request.min_version = 2;
        request.max_version = 1;
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

        assert!(matches!(
            context.validate_client_hello(&request),
            Err(SessionError::InvalidVersionRange {
                min_version: 2,
                max_version: 1
            })
        ));
    }

    #[test]
    fn admission_rejects_when_no_supported_version_overlaps_request() {
        let mut request = hello();
        request.min_version = 1;
        request.max_version = 2;
        let context = GatewayAdmissionContext {
            manifest_id: ManifestId::new("man-2026-04-01-001")
                .expect("fixture manifest id should be valid"),
            device_binding_id: Some("device-1".to_owned()),
            allowed_core_versions: vec![3],
            allowed_capabilities: vec![Capability::TcpRelay, Capability::UdpRelay],
            allowed_carrier_profiles: vec![
                CarrierProfileId::new("carrier-primary")
                    .expect("fixture carrier profile should be valid"),
            ],
        };

        assert!(matches!(
            context.validate_client_hello(&request),
            Err(SessionError::NoSupportedVersionOverlap {
                min_version: 1,
                max_version: 2
            })
        ));
    }

    #[test]
    fn gateway_rejects_duplicate_relay_open_after_session_is_established() {
        let mut session =
            SessionController::new_gateway(EffectiveSessionPolicy::tcp_and_udp_defaults(1));
        session.accept_hello(SessionId::random());
        let open = StreamOpen {
            relay_id: 7,
            target: TargetAddress::Domain("example.net".to_owned()),
            target_port: 443,
            flags: OpenFlags::new(0).expect("zero flags should be valid"),
            metadata: Vec::new(),
        };

        session
            .register_stream_open(&open)
            .expect("first relay open should be accepted");
        let error = session
            .register_stream_open(&open)
            .expect_err("duplicate relay id should be rejected");

        assert!(matches!(error, SessionError::DuplicateRelayId(7)));
    }

    #[test]
    fn gateway_rejects_relay_open_beyond_policy_limit() {
        let mut policy = EffectiveSessionPolicy::tcp_and_udp_defaults(1);
        policy.limits.max_concurrent_relay_streams = 1;
        let mut session = SessionController::new_gateway(policy);
        session.accept_hello(SessionId::random());

        let open_one = StreamOpen {
            relay_id: 7,
            target: TargetAddress::Domain("example.net".to_owned()),
            target_port: 443,
            flags: OpenFlags::new(0).expect("zero flags should be valid"),
            metadata: Vec::new(),
        };
        let open_two = StreamOpen {
            relay_id: 8,
            ..open_one.clone()
        };

        session
            .register_stream_open(&open_one)
            .expect("first relay open should be accepted");
        let error = session
            .register_stream_open(&open_two)
            .expect_err("relay opens beyond the policy limit should be rejected");

        assert!(matches!(
            error,
            SessionError::RelayLimitExceeded {
                max_concurrent_relay_streams: 1
            }
        ));
    }

    #[test]
    fn releasing_a_relay_frees_capacity_for_the_next_stream() {
        let mut policy = EffectiveSessionPolicy::tcp_and_udp_defaults(1);
        policy.limits.max_concurrent_relay_streams = 1;
        let mut session = SessionController::new_gateway(policy);
        session.accept_hello(SessionId::random());

        let open_one = StreamOpen {
            relay_id: 7,
            target: TargetAddress::Domain("example.net".to_owned()),
            target_port: 443,
            flags: OpenFlags::new(0).expect("zero flags should be valid"),
            metadata: Vec::new(),
        };
        let open_two = StreamOpen {
            relay_id: 8,
            ..open_one.clone()
        };

        session
            .register_stream_open(&open_one)
            .expect("first relay open should be accepted");
        assert!(session.release_relay(open_one.relay_id));
        assert!(!session.release_relay(open_one.relay_id));
        session
            .register_stream_open(&open_two)
            .expect("a released relay should free capacity for the next stream");
    }

    #[test]
    fn gateway_rejects_duplicate_udp_flow_open_after_session_is_established() {
        let mut session =
            SessionController::new_gateway(EffectiveSessionPolicy::tcp_and_udp_defaults(1));
        session.accept_hello(SessionId::random());
        let open = UdpFlowOpen {
            flow_id: 7,
            target: TargetAddress::Domain("resolver.example.net".to_owned()),
            target_port: 53,
            idle_timeout_ms: 5_000,
            flags: FlowFlags::new(0b0011).expect("fixture udp flow flags should be valid"),
            metadata: Vec::new(),
        };

        session
            .register_udp_flow_open(&open, true)
            .expect("first udp flow open should be accepted");
        let error = session
            .register_udp_flow_open(&open, true)
            .expect_err("duplicate udp flow id should be rejected");

        assert!(matches!(error, SessionError::DuplicateFlowId(7)));
    }

    #[test]
    fn gateway_rejects_udp_flow_open_beyond_policy_limit() {
        let mut policy = EffectiveSessionPolicy::tcp_and_udp_defaults(1);
        policy.limits.max_udp_flows = 1;
        let mut session = SessionController::new_gateway(policy);
        session.accept_hello(SessionId::random());

        let open_one = UdpFlowOpen {
            flow_id: 7,
            target: TargetAddress::Domain("resolver.example.net".to_owned()),
            target_port: 53,
            idle_timeout_ms: 5_000,
            flags: FlowFlags::new(0b0011).expect("fixture udp flow flags should be valid"),
            metadata: Vec::new(),
        };
        let open_two = UdpFlowOpen {
            flow_id: 8,
            ..open_one.clone()
        };

        session
            .register_udp_flow_open(&open_one, true)
            .expect("first udp flow open should be accepted");
        let error = session
            .register_udp_flow_open(&open_two, true)
            .expect_err("udp flow opens beyond the policy limit should be rejected");

        assert!(matches!(
            error,
            SessionError::UdpFlowLimitExceeded { max_udp_flows: 1 }
        ));
    }

    #[test]
    fn gateway_selects_stream_fallback_when_datagrams_are_unavailable() {
        let mut session =
            SessionController::new_gateway(EffectiveSessionPolicy::tcp_and_udp_defaults(1));
        session.accept_hello(SessionId::random());
        let open = UdpFlowOpen {
            flow_id: 9,
            target: TargetAddress::Domain("resolver.example.net".to_owned()),
            target_port: 53,
            idle_timeout_ms: 5_000,
            flags: FlowFlags::new(0b0011).expect("fixture udp flow flags should be valid"),
            metadata: Vec::new(),
        };

        let ok = session
            .register_udp_flow_open(&open, false)
            .expect("fallback should be selected when datagrams are unavailable");
        assert_eq!(ok.transport_mode, TransportMode::StreamFallback);
    }

    #[test]
    fn gateway_prefers_datagrams_when_they_are_available_even_if_fallback_is_allowed() {
        let mut session =
            SessionController::new_gateway(EffectiveSessionPolicy::tcp_and_udp_defaults(1));
        session.accept_hello(SessionId::random());
        let open = UdpFlowOpen {
            flow_id: 11,
            target: TargetAddress::Domain("resolver.example.net".to_owned()),
            target_port: 53,
            idle_timeout_ms: 5_000,
            flags: FlowFlags::new(0b0010).expect("fixture udp flow flags should be valid"),
            metadata: Vec::new(),
        };

        let ok = session
            .register_udp_flow_open(&open, true)
            .expect("datagrams should be selected explicitly when they are available");
        assert_eq!(ok.transport_mode, TransportMode::Datagram);
    }

    #[test]
    fn gateway_rejects_udp_flow_when_datagrams_are_unavailable_and_fallback_is_disallowed() {
        let mut session =
            SessionController::new_gateway(EffectiveSessionPolicy::tcp_and_udp_defaults(1));
        session.accept_hello(SessionId::random());
        let open = UdpFlowOpen {
            flow_id: 10,
            target: TargetAddress::Domain("resolver.example.net".to_owned()),
            target_port: 53,
            idle_timeout_ms: 5_000,
            flags: FlowFlags::new(0b0001).expect("fixture udp flow flags should be valid"),
            metadata: Vec::new(),
        };

        let error = session.register_udp_flow_open(&open, false).expect_err(
            "datagram-only udp flows should be rejected when datagrams are unavailable",
        );
        assert!(matches!(error, SessionError::DatagramUnavailable));
        assert_eq!(
            error.protocol_error_code(),
            Some(ProtocolErrorCode::UdpDatagramUnavailable)
        );
    }

    #[test]
    fn gateway_rejects_datagram_only_flow_when_policy_disables_datagrams() {
        let mut policy = EffectiveSessionPolicy::tcp_and_udp_defaults(1);
        policy.limits.datagram_mode = DatagramMode::DisabledByPolicy;
        let mut session = SessionController::new_gateway(policy);
        session.accept_hello(SessionId::random());
        let open = UdpFlowOpen {
            flow_id: 12,
            target: TargetAddress::Domain("resolver.example.net".to_owned()),
            target_port: 53,
            idle_timeout_ms: 5_000,
            flags: FlowFlags::new(0b0001).expect("fixture udp flow flags should be valid"),
            metadata: Vec::new(),
        };

        let error = session
            .register_udp_flow_open(&open, true)
            .expect_err("policy-disabled datagrams should fail closed when fallback is disallowed");
        assert!(matches!(error, SessionError::DatagramUnavailable));
        assert_eq!(
            error.protocol_error_code(),
            Some(ProtocolErrorCode::UdpDatagramUnavailable)
        );
    }

    #[test]
    fn session_rejects_datagrams_for_unknown_or_closed_udp_flows() {
        let mut session =
            SessionController::new_gateway(EffectiveSessionPolicy::tcp_and_udp_defaults(1));
        session.accept_hello(SessionId::random());
        let open = UdpFlowOpen {
            flow_id: 14,
            target: TargetAddress::Domain("resolver.example.net".to_owned()),
            target_port: 53,
            idle_timeout_ms: 5_000,
            flags: FlowFlags::new(0b0001).expect("fixture udp flow flags should be valid"),
            metadata: Vec::new(),
        };

        let ok = session
            .register_udp_flow_open(&open, true)
            .expect("datagram-capable flow should be accepted");
        assert_eq!(ok.transport_mode, TransportMode::Datagram);
        session
            .validate_udp_datagram(&UdpDatagram {
                flow_id: open.flow_id,
                flags: ns_wire::DatagramFlags::new(0).expect("zero datagram flags should be valid"),
                payload: b"dns".to_vec(),
            })
            .expect("active datagram flow should validate");
        session
            .close_udp_flow(open.flow_id, TransportMode::Datagram)
            .expect("closing an active datagram flow should succeed");

        let error = session
            .validate_udp_datagram(&UdpDatagram {
                flow_id: open.flow_id,
                flags: ns_wire::DatagramFlags::new(0).expect("zero datagram flags should be valid"),
                payload: b"dns".to_vec(),
            })
            .expect_err("datagrams after close should be rejected");
        assert!(matches!(error, SessionError::UnknownUdpFlowId(14)));
        assert_eq!(
            error.protocol_error_code(),
            Some(ProtocolErrorCode::ProtocolViolation)
        );
    }

    #[test]
    fn session_rejects_fallback_streams_for_the_wrong_udp_flow_id() {
        let mut session =
            SessionController::new_gateway(EffectiveSessionPolicy::tcp_and_udp_defaults(1));
        session.accept_hello(SessionId::random());
        let open = UdpFlowOpen {
            flow_id: 15,
            target: TargetAddress::Domain("resolver.example.net".to_owned()),
            target_port: 53,
            idle_timeout_ms: 5_000,
            flags: FlowFlags::new(0b0011).expect("fixture udp flow flags should be valid"),
            metadata: Vec::new(),
        };

        let ok = session
            .register_udp_flow_open(&open, false)
            .expect("fallback-capable flow should be accepted");
        assert_eq!(ok.transport_mode, TransportMode::StreamFallback);

        let unknown = session
            .validate_udp_fallback_stream(99)
            .expect_err("unknown fallback flow ids should be rejected");
        assert!(matches!(unknown, SessionError::UnknownUdpFlowId(99)));

        let wrong_transport = session
            .validate_udp_datagram(&UdpDatagram {
                flow_id: open.flow_id,
                flags: ns_wire::DatagramFlags::new(0).expect("zero datagram flags should be valid"),
                payload: b"dns".to_vec(),
            })
            .expect_err("fallback-only flow ids should reject datagram transport");
        assert!(matches!(
            wrong_transport,
            SessionError::InvalidUdpFlowTransportMode {
                flow_id: 15,
                expected: TransportMode::Datagram,
                actual: TransportMode::StreamFallback,
            }
        ));
        assert_eq!(
            wrong_transport.protocol_error_code(),
            Some(ProtocolErrorCode::ProtocolViolation)
        );
    }

    #[test]
    fn session_error_mappings_keep_udp_protocol_codes_aligned_with_the_frozen_registry() {
        assert_eq!(
            SessionError::DuplicateFlowId(7).protocol_error_code(),
            Some(ProtocolErrorCode::ProtocolViolation)
        );
        assert_eq!(
            SessionError::UnknownUdpFlowId(7).protocol_error_code(),
            Some(ProtocolErrorCode::ProtocolViolation)
        );
        assert_eq!(
            SessionError::UdpFlowLimitExceeded { max_udp_flows: 1 }.protocol_error_code(),
            Some(ProtocolErrorCode::FlowLimitReached)
        );
        assert_eq!(
            SessionError::DatagramUnavailable.protocol_error_code(),
            Some(ProtocolErrorCode::UdpDatagramUnavailable)
        );
    }
}
