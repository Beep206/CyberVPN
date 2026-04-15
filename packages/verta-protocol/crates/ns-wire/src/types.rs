use ns_core::{
    Capability, CarrierKind, CarrierProfileId, DatagramMode, DeviceBindingId, ManifestId,
    ProtocolErrorCode, SessionId, StatsMode, TransportMode,
};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FrameType {
    ClientHello,
    ServerHello,
    Ping,
    Pong,
    Error,
    UdpFlowOpen,
    UdpFlowOk,
    UdpFlowClose,
    SessionClose,
    StreamOpen,
    StreamAccept,
    StreamReject,
    UdpStreamOpen,
    UdpStreamAccept,
    UdpStreamPacket,
    UdpStreamClose,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MetadataTlv {
    pub kind: u64,
    pub value: Vec<u8>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ClientHello {
    pub min_version: u64,
    pub max_version: u64,
    pub client_nonce: [u8; 32],
    pub requested_capabilities: Vec<Capability>,
    pub carrier_kind: CarrierKind,
    pub carrier_profile_id: CarrierProfileId,
    pub manifest_id: ManifestId,
    pub device_binding_id: DeviceBindingId,
    pub requested_idle_timeout_ms: u64,
    pub requested_max_udp_payload: u64,
    pub token: Vec<u8>,
    pub client_metadata: Vec<MetadataTlv>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ServerHello {
    pub selected_version: u64,
    pub session_id: SessionId,
    pub server_nonce: [u8; 32],
    pub selected_capabilities: Vec<Capability>,
    pub policy_epoch: u64,
    pub effective_idle_timeout_ms: u64,
    pub session_lifetime_ms: u64,
    pub max_concurrent_relay_streams: u64,
    pub max_udp_flows: u64,
    pub effective_max_udp_payload: u64,
    pub datagram_mode: DatagramMode,
    pub stats_mode: StatsMode,
    pub server_metadata: Vec<MetadataTlv>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Ping {
    pub ping_id: u64,
    pub timestamp: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Pong {
    pub ping_id: u64,
    pub timestamp: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ErrorFrame {
    pub code: ProtocolErrorCode,
    pub message: String,
    pub is_terminal: bool,
    pub details: Vec<MetadataTlv>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SessionClose {
    pub code: ProtocolErrorCode,
    pub message: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct StreamOpen {
    pub relay_id: u64,
    pub target: TargetAddress,
    pub target_port: u16,
    pub flags: OpenFlags,
    pub metadata: Vec<MetadataTlv>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct StreamAccept {
    pub relay_id: u64,
    pub bind_address: TargetAddress,
    pub bind_port: u16,
    pub metadata: Vec<MetadataTlv>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct StreamReject {
    pub relay_id: u64,
    pub code: ProtocolErrorCode,
    pub retryable: bool,
    pub message: String,
    pub metadata: Vec<MetadataTlv>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct UdpFlowOpen {
    pub flow_id: u64,
    pub target: TargetAddress,
    pub target_port: u16,
    pub idle_timeout_ms: u64,
    pub flags: FlowFlags,
    pub metadata: Vec<MetadataTlv>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct UdpFlowOk {
    pub flow_id: u64,
    pub transport_mode: TransportMode,
    pub effective_idle_timeout_ms: u64,
    pub effective_max_payload: u64,
    pub metadata: Vec<MetadataTlv>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct UdpFlowClose {
    pub flow_id: u64,
    pub code: ProtocolErrorCode,
    pub message: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct UdpStreamOpen {
    pub flow_id: u64,
    pub metadata: Vec<MetadataTlv>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct UdpStreamAccept {
    pub flow_id: u64,
    pub metadata: Vec<MetadataTlv>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct UdpStreamPacket {
    pub payload: Vec<u8>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct UdpStreamClose {
    pub flow_id: u64,
    pub code: ProtocolErrorCode,
    pub message: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct UdpDatagram {
    pub flow_id: u64,
    pub flags: DatagramFlags,
    pub payload: Vec<u8>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum TargetAddress {
    Domain(String),
    Ipv4([u8; 4]),
    Ipv6([u8; 16]),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct OpenFlags(u64);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct FlowFlags(u64);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct DatagramFlags(u64);

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum Frame {
    ClientHello(ClientHello),
    ServerHello(ServerHello),
    Ping(Ping),
    Pong(Pong),
    Error(ErrorFrame),
    UdpFlowOpen(UdpFlowOpen),
    UdpFlowOk(UdpFlowOk),
    UdpFlowClose(UdpFlowClose),
    SessionClose(SessionClose),
    StreamOpen(StreamOpen),
    StreamAccept(StreamAccept),
    StreamReject(StreamReject),
    UdpStreamOpen(UdpStreamOpen),
    UdpStreamAccept(UdpStreamAccept),
    UdpStreamPacket(UdpStreamPacket),
    UdpStreamClose(UdpStreamClose),
}

impl FrameType {
    pub fn id(self) -> u64 {
        match self {
            Self::ClientHello => 0x01,
            Self::ServerHello => 0x02,
            Self::Ping => 0x03,
            Self::Pong => 0x04,
            Self::Error => 0x05,
            Self::UdpFlowOpen => 0x08,
            Self::UdpFlowOk => 0x09,
            Self::UdpFlowClose => 0x0A,
            Self::SessionClose => 0x0E,
            Self::StreamOpen => 0x40,
            Self::StreamAccept => 0x41,
            Self::StreamReject => 0x42,
            Self::UdpStreamOpen => 0x43,
            Self::UdpStreamAccept => 0x44,
            Self::UdpStreamPacket => 0x45,
            Self::UdpStreamClose => 0x46,
        }
    }
}

impl OpenFlags {
    const RESERVED_MASK: u64 = !0b1011;

    pub fn new(raw: u64) -> Result<Self, u64> {
        if raw & Self::RESERVED_MASK != 0 {
            return Err(raw);
        }

        Ok(Self(raw))
    }

    pub fn raw(self) -> u64 {
        self.0
    }
}

impl FlowFlags {
    const RESERVED_MASK: u64 = !0b1111;
    const PREFER_DATAGRAM: u64 = 1 << 0;
    const ALLOW_STREAM_FALLBACK: u64 = 1 << 1;
    const DNS_OPTIMIZED: u64 = 1 << 2;
    const CLIENT_KEEPALIVE: u64 = 1 << 3;

    pub fn new(raw: u64) -> Result<Self, u64> {
        if raw & Self::RESERVED_MASK != 0 {
            return Err(raw);
        }

        Ok(Self(raw))
    }

    pub fn raw(self) -> u64 {
        self.0
    }

    pub fn prefer_datagram(self) -> bool {
        self.0 & Self::PREFER_DATAGRAM != 0
    }

    pub fn allow_stream_fallback(self) -> bool {
        self.0 & Self::ALLOW_STREAM_FALLBACK != 0
    }

    pub fn dns_optimized(self) -> bool {
        self.0 & Self::DNS_OPTIMIZED != 0
    }

    pub fn client_keepalive(self) -> bool {
        self.0 & Self::CLIENT_KEEPALIVE != 0
    }
}

impl DatagramFlags {
    pub fn new(raw: u64) -> Result<Self, u64> {
        if raw != 0 {
            return Err(raw);
        }

        Ok(Self(raw))
    }

    pub fn raw(self) -> u64 {
        self.0
    }
}

impl Frame {
    pub fn frame_type(&self) -> FrameType {
        match self {
            Self::ClientHello(_) => FrameType::ClientHello,
            Self::ServerHello(_) => FrameType::ServerHello,
            Self::Ping(_) => FrameType::Ping,
            Self::Pong(_) => FrameType::Pong,
            Self::Error(_) => FrameType::Error,
            Self::UdpFlowOpen(_) => FrameType::UdpFlowOpen,
            Self::UdpFlowOk(_) => FrameType::UdpFlowOk,
            Self::UdpFlowClose(_) => FrameType::UdpFlowClose,
            Self::SessionClose(_) => FrameType::SessionClose,
            Self::StreamOpen(_) => FrameType::StreamOpen,
            Self::StreamAccept(_) => FrameType::StreamAccept,
            Self::StreamReject(_) => FrameType::StreamReject,
            Self::UdpStreamOpen(_) => FrameType::UdpStreamOpen,
            Self::UdpStreamAccept(_) => FrameType::UdpStreamAccept,
            Self::UdpStreamPacket(_) => FrameType::UdpStreamPacket,
            Self::UdpStreamClose(_) => FrameType::UdpStreamClose,
        }
    }
}
