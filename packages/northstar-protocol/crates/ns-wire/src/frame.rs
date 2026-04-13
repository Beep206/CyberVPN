use ns_core::{
    CapabilityId, CarrierKind, CarrierProfileId, CoreVersion, DeviceBindingId, ErrorCode, FlowId,
    ManifestId, PathEventType, RelayId, SessionId, StatsMode, TargetType, TransportMode,
};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Tlv {
    pub id: u64,
    pub value: Vec<u8>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum TargetHost {
    Domain(String),
    Ipv4([u8; 4]),
    Ipv6([u8; 16]),
}

impl TargetHost {
    pub fn target_type(&self) -> TargetType {
        match self {
            Self::Domain(_) => TargetType::Domain,
            Self::Ipv4(_) => TargetType::Ipv4,
            Self::Ipv6(_) => TargetType::Ipv6,
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ClientHello {
    pub min_version: CoreVersion,
    pub max_version: CoreVersion,
    pub client_nonce: [u8; 32],
    pub requested_capabilities: Vec<CapabilityId>,
    pub carrier_kind: CarrierKind,
    pub carrier_profile_id: CarrierProfileId,
    pub manifest_id: ManifestId,
    pub device_binding_id: DeviceBindingId,
    pub requested_idle_timeout_ms: u64,
    pub requested_max_udp_payload: u64,
    pub token: Vec<u8>,
    pub client_metadata: Vec<Tlv>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ServerHello {
    pub selected_version: CoreVersion,
    pub session_id: SessionId,
    pub server_nonce: [u8; 32],
    pub selected_capabilities: Vec<CapabilityId>,
    pub policy_epoch: u64,
    pub effective_idle_timeout_ms: u64,
    pub session_lifetime_ms: u64,
    pub max_concurrent_relay_streams: u64,
    pub max_udp_flows: u64,
    pub effective_max_udp_payload: u64,
    pub datagram_mode: ns_core::DatagramMode,
    pub stats_mode: StatsMode,
    pub server_metadata: Vec<Tlv>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Ping {
    pub ping_id: u64,
    pub timestamp: u64,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ErrorFrame {
    pub error_code: ErrorCode,
    pub error_message: String,
    pub is_terminal: bool,
    pub details: Vec<Tlv>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct GoawayFrame {
    pub reason_code: u64,
    pub retry_after_ms: u64,
    pub preferred_endpoints: Vec<String>,
    pub message: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct PolicyUpdate {
    pub policy_epoch: u64,
    pub effective_idle_timeout_ms: u64,
    pub max_concurrent_relay_streams: u64,
    pub max_udp_flows: u64,
    pub effective_max_udp_payload: u64,
    pub flags: u64,
    pub metadata: Vec<Tlv>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct UdpFlowOpen {
    pub flow_id: FlowId,
    pub target_host: TargetHost,
    pub target_port: u16,
    pub idle_timeout_ms: u64,
    pub flow_flags: u64,
    pub metadata: Vec<Tlv>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct UdpFlowOk {
    pub flow_id: FlowId,
    pub transport_mode: TransportMode,
    pub effective_idle_timeout_ms: u64,
    pub effective_max_payload: u64,
    pub metadata: Vec<Tlv>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct UdpFlowClose {
    pub flow_id: FlowId,
    pub error_code: ErrorCode,
    pub message: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct SessionStats {
    pub stats_kind: u64,
    pub sample_start_ms: u64,
    pub sample_end_ms: u64,
    pub metrics: Vec<Tlv>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct PathEvent {
    pub event_type: PathEventType,
    pub previous_network: String,
    pub new_network: String,
    pub client_hints: Vec<Tlv>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct SessionClose {
    pub error_code: ErrorCode,
    pub message: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct StreamOpen {
    pub relay_id: RelayId,
    pub target_host: TargetHost,
    pub target_port: u16,
    pub open_flags: u64,
    pub metadata: Vec<Tlv>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct StreamAccept {
    pub relay_id: RelayId,
    pub bind_host: TargetHost,
    pub bind_port: u16,
    pub metadata: Vec<Tlv>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct StreamReject {
    pub relay_id: RelayId,
    pub error_code: ErrorCode,
    pub retryable: bool,
    pub message: String,
    pub metadata: Vec<Tlv>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct UdpStreamOpen {
    pub flow_id: FlowId,
    pub metadata: Vec<Tlv>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct UdpStreamAccept {
    pub flow_id: FlowId,
    pub metadata: Vec<Tlv>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct UdpStreamPacket {
    pub payload: Vec<u8>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct UdpStreamClose {
    pub flow_id: FlowId,
    pub error_code: ErrorCode,
    pub message: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum Frame {
    ClientHello(ClientHello),
    ServerHello(ServerHello),
    Ping(Ping),
    Pong(Ping),
    Error(ErrorFrame),
    Goaway(GoawayFrame),
    PolicyUpdate(PolicyUpdate),
    UdpFlowOpen(UdpFlowOpen),
    UdpFlowOk(UdpFlowOk),
    UdpFlowClose(UdpFlowClose),
    SessionStats(SessionStats),
    PathEvent(PathEvent),
    SessionClose(SessionClose),
    StreamOpen(StreamOpen),
    StreamAccept(StreamAccept),
    StreamReject(StreamReject),
    UdpStreamOpen(UdpStreamOpen),
    UdpStreamAccept(UdpStreamAccept),
    UdpStreamPacket(UdpStreamPacket),
    UdpStreamClose(UdpStreamClose),
}

impl Frame {
    pub fn frame_type(&self) -> u64 {
        match self {
            Self::ClientHello(_) => 0x01,
            Self::ServerHello(_) => 0x02,
            Self::Ping(_) => 0x03,
            Self::Pong(_) => 0x04,
            Self::Error(_) => 0x05,
            Self::Goaway(_) => 0x06,
            Self::PolicyUpdate(_) => 0x07,
            Self::UdpFlowOpen(_) => 0x08,
            Self::UdpFlowOk(_) => 0x09,
            Self::UdpFlowClose(_) => 0x0A,
            Self::SessionStats(_) => 0x0B,
            Self::PathEvent(_) => 0x0C,
            Self::SessionClose(_) => 0x0E,
            Self::StreamOpen(_) => 0x40,
            Self::StreamAccept(_) => 0x41,
            Self::StreamReject(_) => 0x42,
            Self::UdpStreamOpen(_) => 0x43,
            Self::UdpStreamAccept(_) => 0x44,
            Self::UdpStreamPacket(_) => 0x45,
            Self::UdpStreamClose(_) => 0x46,
        }
    }
}
