use std::{net::SocketAddr, time::Duration};

use serde::{Deserialize, Serialize};

pub const PROTOCOL_MAGIC: &str = "cvpt1";
pub const PROTOCOL_VERSION: u16 = 1;

#[derive(Debug, Clone)]
pub struct TransportRoute {
    pub endpoint_ref: String,
    pub dial_host: String,
    pub dial_port: u16,
    pub server_name: Option<String>,
    pub preference: i32,
    pub policy_tag: String,
}

impl TransportRoute {
    pub fn dial_addr(&self) -> String {
        format!("{}:{}", self.dial_host, self.dial_port)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct StreamTarget {
    pub host: String,
    pub port: u16,
}

impl StreamTarget {
    pub fn new(host: impl Into<String>, port: u16) -> Self {
        Self {
            host: host.into(),
            port,
        }
    }

    pub fn authority(&self) -> String {
        format!("{}:{}", self.host, self.port)
    }
}

#[derive(Debug, Clone)]
pub struct ClientConfig {
    pub manifest_id: String,
    pub transport_profile_id: String,
    pub profile_family: String,
    pub profile_version: i32,
    pub policy_version: i32,
    pub session_mode: String,
    pub token: String,
    pub route: TransportRoute,
    pub connect_timeout: Duration,
    pub heartbeat_interval: Duration,
    pub reconnect_delay: Duration,
}

#[derive(Debug, Clone)]
pub struct ServerConfig {
    pub bind_addrs: Vec<SocketAddr>,
    pub transport_profile_id: String,
    pub profile_family: String,
    pub profile_version: i32,
    pub policy_version: i32,
    pub session_mode: String,
    pub token: String,
    pub heartbeat_timeout: Duration,
    pub allow_private_targets: bool,
}

#[derive(Debug, Clone, Default)]
pub struct SessionSnapshot {
    pub status: String,
    pub ready: bool,
    pub connected: bool,
    pub session_id: Option<String>,
    pub resumed_last_session: bool,
    pub active_route: Option<String>,
    pub remote_addr: Option<String>,
    pub last_ping_rtt_ms: Option<u32>,
    pub sent_frames: u64,
    pub received_frames: u64,
    pub reconnect_attempts: u64,
    pub active_streams: u64,
    pub pending_open_streams: u64,
    pub max_concurrent_streams: u64,
    pub frame_queue_depth: u32,
    pub frame_queue_peak: u32,
    pub bytes_sent: u64,
    pub bytes_received: u64,
    pub last_error: Option<String>,
}

#[derive(Debug, Clone, Default)]
pub struct ServerSnapshot {
    pub ready: bool,
    pub bound_addrs: Vec<String>,
    pub active_sessions: u64,
    pub successful_handshakes: u64,
    pub failed_handshakes: u64,
    pub frames_in: u64,
    pub frames_out: u64,
    pub active_streams: u64,
    pub bytes_in: u64,
    pub bytes_out: u64,
    pub rejected_targets: u64,
    pub last_error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HandshakeHello {
    pub magic: String,
    pub protocol_version: u16,
    pub manifest_id: String,
    pub transport_profile_id: String,
    pub profile_family: String,
    pub profile_version: i32,
    pub policy_version: i32,
    pub session_mode: String,
    pub route_ref: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub resume_session_id: Option<String>,
    pub client_nonce: [u8; 16],
    pub timestamp_ms: u64,
    pub proof: [u8; 32],
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HandshakeWelcome {
    pub magic: String,
    pub accepted: bool,
    pub session_id: String,
    #[serde(default)]
    pub resumed: bool,
    pub transport_profile_id: String,
    pub server_nonce: [u8; 16],
    pub heartbeat_interval_ms: u64,
    pub proof: [u8; 32],
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ControlFrame {
    Ping {
        sent_at_ms: u64,
    },
    Pong {
        sent_at_ms: u64,
        server_timestamp_ms: u64,
    },
    StreamOpen {
        stream_id: u64,
        target_host: String,
        target_port: u16,
    },
    StreamOpened {
        stream_id: u64,
        bind_target: String,
    },
    StreamData {
        stream_id: u64,
        data: Vec<u8>,
    },
    StreamFinish {
        stream_id: u64,
    },
    StreamClose {
        stream_id: u64,
        reason: String,
    },
    Close {
        reason: String,
    },
}
