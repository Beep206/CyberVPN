#![forbid(unsafe_code)]

use async_trait::async_trait;
use bytes::{Buf, Bytes};
use h3::quic::StreamId;
use h3_datagram::datagram_handler::{DatagramReader, DatagramSender};
use h3_datagram::quic_traits::{RecvDatagram, SendDatagram};
use http::header::{HeaderName, HeaderValue};
use http::{Method, Request, Uri};
use ns_core::{CarrierKind, CarrierProfileId, DatagramMode, TransportMode};
use ns_observability::{
    record_carrier_datagram_guard, record_carrier_datagram_io, record_carrier_datagram_selection,
    record_carrier_relay_closed,
};
use ns_session::{
    CarrierSessionInfo, ControlFrameIo, DatagramIo, EstablishedCarrierSession, IncomingRelayStream,
    IncomingUdpFallbackStream, PendingCarrierSession, RelayStreamIo, SessionController,
    SessionError, TransportError, TransportErrorKind, UdpFallbackStreamIo,
};
use ns_wire::{
    FlowFlags, Frame, FrameCodec, StreamAccept, StreamOpen, UdpDatagram, UdpFlowOk, UdpFlowOpen,
    UdpStreamAccept, UdpStreamOpen,
};
use quinn::{IdleTimeout, TransportConfig};
use rustls::RootCertStore;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, VecDeque};
use std::sync::{Arc, Mutex};
use std::time::Duration;
use thiserror::Error;
use tokio::io::{AsyncRead, AsyncReadExt, AsyncWrite, AsyncWriteExt};

pub const CARRIER_NAME: &str = "h3";
pub const MAX_TUNNEL_FRAME_BYTES: usize = 16 * 1024;
pub const DEFAULT_MAX_RAW_PREBUFFER_BYTES: usize = 64 * 1024;
pub const DEFAULT_MAX_UDP_PAYLOAD_BYTES: usize = 1_200;
pub const DEFAULT_MAX_BUFFERED_DATAGRAM_BYTES: usize = 8 * 1024;
pub const DEFAULT_MAX_BUFFERED_DATAGRAMS: usize = 8;
pub const DEFAULT_MAX_BUFFERED_DATAGRAMS_PER_FLOW: usize = 4;
const DISALLOWED_REQUEST_HEADERS: &[&str] = &[
    "connection",
    "proxy-connection",
    "keep-alive",
    "upgrade",
    "transfer-encoding",
    "te",
    "trailer",
    "content-length",
    "host",
    "expect",
];

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct H3ConnectBackoff {
    pub initial_ms: u64,
    pub max_ms: u64,
    pub jitter: f64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum H3ZeroRttPolicy {
    Disabled,
    Allow,
    ForceDisabled,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum H3DatagramRollout {
    #[default]
    Disabled,
    Canary,
    Automatic,
}

impl H3DatagramRollout {
    pub fn stage_label(self) -> &'static str {
        match self {
            Self::Disabled => "disabled",
            Self::Canary => "canary",
            Self::Automatic => "automatic",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum H3RequestKind {
    Control,
    Relay,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct H3DatagramRuntimeConfig {
    pub max_payload_bytes: usize,
    pub max_buffered_bytes: usize,
    pub max_buffered_datagrams: usize,
    pub max_buffered_datagrams_per_flow: usize,
}

impl Default for H3DatagramRuntimeConfig {
    fn default() -> Self {
        Self {
            max_payload_bytes: DEFAULT_MAX_UDP_PAYLOAD_BYTES,
            max_buffered_bytes: DEFAULT_MAX_BUFFERED_DATAGRAM_BYTES,
            max_buffered_datagrams: DEFAULT_MAX_BUFFERED_DATAGRAMS,
            max_buffered_datagrams_per_flow: DEFAULT_MAX_BUFFERED_DATAGRAMS_PER_FLOW,
        }
    }
}

impl H3DatagramRuntimeConfig {
    fn validate(&self) -> Result<(), TransportError> {
        if self.max_payload_bytes == 0 {
            return Err(TransportError {
                kind: TransportErrorKind::ProtocolViolation,
                message: "datagram runtime max_payload_bytes must be non-zero".to_owned(),
            });
        }
        if self.max_buffered_bytes == 0 {
            return Err(TransportError {
                kind: TransportErrorKind::ProtocolViolation,
                message: "datagram runtime max_buffered_bytes must be non-zero".to_owned(),
            });
        }
        if self.max_buffered_datagrams == 0 {
            return Err(TransportError {
                kind: TransportErrorKind::ProtocolViolation,
                message: "datagram runtime max_buffered_datagrams must be non-zero".to_owned(),
            });
        }
        if self.max_buffered_datagrams_per_flow == 0 {
            return Err(TransportError {
                kind: TransportErrorKind::ProtocolViolation,
                message: "datagram runtime max_buffered_datagrams_per_flow must be non-zero"
                    .to_owned(),
            });
        }
        Ok(())
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct H3RequestTemplate {
    authority: String,
    path: String,
    headers: BTreeMap<String, String>,
}

impl H3RequestTemplate {
    pub fn authority(&self) -> &str {
        &self.authority
    }

    pub fn path(&self) -> &str {
        &self.path
    }

    pub fn headers(&self) -> &BTreeMap<String, String> {
        &self.headers
    }

    pub fn uri(&self) -> Result<Uri, H3TransportError> {
        format!("https://{}{}", self.authority, self.path)
            .parse()
            .map_err(|_| H3TransportError::InvalidRequestUri)
    }

    pub fn build_request(&self) -> Result<Request<()>, H3TransportError> {
        let mut builder = Request::builder().method(Method::CONNECT).uri(self.uri()?);
        for (name, value) in &self.headers {
            let header_name = HeaderName::from_bytes(name.as_bytes())
                .map_err(|_| H3TransportError::InvalidHeaderName(name.clone()))?;
            let header_value = HeaderValue::from_str(value)
                .map_err(|_| H3TransportError::InvalidHeaderValue(name.clone()))?;
            builder = builder.header(header_name, header_value);
        }
        builder
            .body(())
            .map_err(|_| H3TransportError::InvalidRequestTemplate)
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct H3TransportConfig {
    pub carrier_kind: CarrierKind,
    pub carrier_profile_id: CarrierProfileId,
    pub origin_host: String,
    pub origin_port: u16,
    pub sni: Option<String>,
    pub alpn: Vec<String>,
    pub control_path: String,
    pub relay_path: String,
    pub headers: BTreeMap<String, String>,
    pub datagram_enabled: bool,
    #[serde(default)]
    pub datagram_rollout: H3DatagramRollout,
    pub heartbeat_interval_ms: u64,
    pub idle_timeout_ms: u64,
    pub zero_rtt_policy: H3ZeroRttPolicy,
    pub connect_backoff: H3ConnectBackoff,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct H3DatagramStartupContract {
    pub signed_datagram_enabled: bool,
    pub datagram_rollout: H3DatagramRollout,
    pub carrier_datagrams_available: bool,
    pub resolved_datagram_mode: DatagramMode,
    pub rollout_stage: &'static str,
}

pub fn resolve_h3_datagram_startup_contract(
    signed_datagram_enabled: bool,
    datagram_rollout: H3DatagramRollout,
    carrier_datagrams_available: bool,
) -> Result<H3DatagramStartupContract, H3TransportError> {
    if datagram_rollout != H3DatagramRollout::Disabled && !signed_datagram_enabled {
        return Err(H3TransportError::InvalidConfig("datagram_rollout"));
    }

    let resolved_datagram_mode =
        if !signed_datagram_enabled || datagram_rollout == H3DatagramRollout::Disabled {
            DatagramMode::DisabledByPolicy
        } else if carrier_datagrams_available {
            DatagramMode::AvailableAndEnabled
        } else {
            DatagramMode::Unavailable
        };

    Ok(H3DatagramStartupContract {
        signed_datagram_enabled,
        datagram_rollout,
        carrier_datagrams_available,
        resolved_datagram_mode,
        rollout_stage: datagram_rollout.stage_label(),
    })
}

impl H3TransportConfig {
    pub fn validate(&self) -> Result<(), H3TransportError> {
        if self.carrier_kind != CarrierKind::H3 {
            return Err(H3TransportError::UnsupportedCarrierKind);
        }
        if self.origin_host.trim().is_empty() {
            return Err(H3TransportError::InvalidConfig("origin_host"));
        }
        if self.origin_port == 0 {
            return Err(H3TransportError::InvalidConfig("origin_port"));
        }
        if self.alpn.is_empty() || self.alpn.iter().any(|value| value.trim().is_empty()) {
            return Err(H3TransportError::InvalidConfig("alpn"));
        }
        if self.control_path.trim().is_empty() {
            return Err(H3TransportError::InvalidConfig("control_path"));
        }
        if !self.control_path.starts_with('/') {
            return Err(H3TransportError::InvalidConfig("control_path"));
        }
        if self.relay_path.trim().is_empty() {
            return Err(H3TransportError::InvalidConfig("relay_path"));
        }
        if !self.relay_path.starts_with('/') {
            return Err(H3TransportError::InvalidConfig("relay_path"));
        }
        if self.heartbeat_interval_ms == 0 {
            return Err(H3TransportError::InvalidConfig("heartbeat_interval_ms"));
        }
        if self.idle_timeout_ms == 0 {
            return Err(H3TransportError::InvalidConfig("idle_timeout_ms"));
        }
        if self.datagram_rollout != H3DatagramRollout::Disabled && !self.datagram_enabled {
            return Err(H3TransportError::InvalidConfig("datagram_rollout"));
        }
        validate_h3_headers(&self.headers)?;
        validate_connect_backoff(&self.connect_backoff)?;

        Ok(())
    }

    pub fn authority(&self) -> String {
        format!("{}:{}", self.origin_host, self.origin_port)
    }

    pub fn request_template(
        &self,
        kind: H3RequestKind,
    ) -> Result<H3RequestTemplate, H3TransportError> {
        self.validate()?;
        let path = match kind {
            H3RequestKind::Control => self.control_path.clone(),
            H3RequestKind::Relay => self.relay_path.clone(),
        };

        Ok(H3RequestTemplate {
            authority: self.authority(),
            path,
            headers: self.headers.clone(),
        })
    }

    pub fn build_request(&self, kind: H3RequestKind) -> Result<Request<()>, H3TransportError> {
        self.request_template(kind)?.build_request()
    }

    pub fn control_request(&self) -> Result<Request<()>, H3TransportError> {
        self.build_request(H3RequestKind::Control)
    }

    pub fn relay_request(&self) -> Result<Request<()>, H3TransportError> {
        self.build_request(H3RequestKind::Relay)
    }

    pub fn datagram_runtime_enabled(&self) -> bool {
        self.datagram_enabled && self.datagram_rollout != H3DatagramRollout::Disabled
    }

    pub fn rollout_stage_label(&self) -> &'static str {
        self.datagram_rollout.stage_label()
    }

    pub fn datagram_runtime_enabled_for_flow(
        &self,
        flags: FlowFlags,
        carrier_datagrams_available: bool,
    ) -> bool {
        if !self.datagram_runtime_enabled() || !carrier_datagrams_available {
            return false;
        }

        match self.datagram_rollout {
            H3DatagramRollout::Disabled => false,
            H3DatagramRollout::Canary => flags.prefer_datagram(),
            H3DatagramRollout::Automatic => true,
        }
    }

    pub fn advertised_datagram_mode(&self, carrier_datagrams_available: bool) -> DatagramMode {
        resolve_h3_datagram_startup_contract(
            self.datagram_enabled,
            self.datagram_rollout,
            carrier_datagrams_available,
        )
        .expect("validated H3 transport config should resolve a startup datagram contract")
        .resolved_datagram_mode
    }

    pub fn datagram_startup_contract(
        &self,
        carrier_datagrams_available: bool,
    ) -> Result<H3DatagramStartupContract, H3TransportError> {
        resolve_h3_datagram_startup_contract(
            self.datagram_enabled,
            self.datagram_rollout,
            carrier_datagrams_available,
        )
    }
}

fn validate_h3_headers(headers: &BTreeMap<String, String>) -> Result<(), H3TransportError> {
    for (name, value) in headers {
        if name.trim().is_empty()
            || name.starts_with(':')
            || name.bytes().any(|byte| byte.is_ascii_uppercase())
        {
            return Err(H3TransportError::InvalidHeaderName(name.clone()));
        }
        if HeaderName::from_bytes(name.as_bytes()).is_err() {
            return Err(H3TransportError::InvalidHeaderName(name.clone()));
        }
        if DISALLOWED_REQUEST_HEADERS
            .iter()
            .any(|reserved| reserved == &name.as_str())
        {
            return Err(H3TransportError::InvalidHeaderName(name.clone()));
        }
        if HeaderValue::from_str(value).is_err() {
            return Err(H3TransportError::InvalidHeaderValue(name.clone()));
        }
    }

    Ok(())
}

fn validate_connect_backoff(backoff: &H3ConnectBackoff) -> Result<(), H3TransportError> {
    if !(50..=60_000).contains(&backoff.initial_ms) {
        return Err(H3TransportError::InvalidConfig(
            "connect_backoff.initial_ms",
        ));
    }
    if !(50..=600_000).contains(&backoff.max_ms) {
        return Err(H3TransportError::InvalidConfig("connect_backoff.max_ms"));
    }
    if backoff.initial_ms > backoff.max_ms {
        return Err(H3TransportError::InvalidConfig("connect_backoff"));
    }
    if !(0.0..=1.0).contains(&backoff.jitter) {
        return Err(H3TransportError::InvalidConfig("connect_backoff.jitter"));
    }

    Ok(())
}

pub fn build_quinn_transport_config(
    config: &H3TransportConfig,
) -> Result<TransportConfig, H3TransportError> {
    config.validate()?;

    let mut transport = TransportConfig::default();
    let idle_timeout = IdleTimeout::try_from(Duration::from_millis(config.idle_timeout_ms))
        .map_err(|_| H3TransportError::InvalidConfig("idle_timeout_ms"))?;
    transport.max_idle_timeout(Some(idle_timeout));
    Ok(transport)
}

pub fn build_client_tls_config(
    config: &H3TransportConfig,
) -> Result<rustls::ClientConfig, H3TransportError> {
    build_client_tls_config_with_roots(config, RootCertStore::empty())
}

pub fn build_client_tls_config_with_roots(
    config: &H3TransportConfig,
    root_certificates: RootCertStore,
) -> Result<rustls::ClientConfig, H3TransportError> {
    config.validate()?;

    let mut tls = rustls::ClientConfig::builder()
        .with_root_certificates(root_certificates)
        .with_no_client_auth();
    tls.enable_early_data = false;
    tls.alpn_protocols = config
        .alpn
        .iter()
        .map(|value| value.as_bytes().to_vec())
        .collect();
    Ok(tls)
}

pub fn encode_tunnel_frame(frame: &Frame) -> Result<Bytes, H3TransportError> {
    let encoded = FrameCodec::encode(frame).map_err(|_| H3TransportError::InvalidTunnelFrame)?;
    if encoded.len() > MAX_TUNNEL_FRAME_BYTES {
        return Err(H3TransportError::TunnelFrameTooLarge {
            max_bytes: MAX_TUNNEL_FRAME_BYTES,
            actual_bytes: encoded.len(),
        });
    }
    Ok(Bytes::from(encoded))
}

pub fn decode_tunnel_frame(payload: &[u8]) -> Result<Frame, H3TransportError> {
    if payload.len() > MAX_TUNNEL_FRAME_BYTES {
        return Err(H3TransportError::TunnelFrameTooLarge {
            max_bytes: MAX_TUNNEL_FRAME_BYTES,
            actual_bytes: payload.len(),
        });
    }
    FrameCodec::decode(payload).map_err(|_| H3TransportError::InvalidTunnelFrame)
}

fn datagram_mode_label(mode: DatagramMode) -> &'static str {
    match mode {
        DatagramMode::Unavailable => "unavailable",
        DatagramMode::AvailableAndEnabled => "available_and_enabled",
        DatagramMode::DisabledByPolicy => "disabled_by_policy",
    }
}

pub fn select_h3_udp_flow(
    controller: &mut SessionController,
    open: &UdpFlowOpen,
    carrier_datagrams_available_for_flow: bool,
    raw_carrier_datagrams_available: bool,
    rollout_stage: &'static str,
) -> Result<UdpFlowOk, SessionError> {
    let datagram_mode = controller.policy.limits.datagram_mode;
    let fallback_allowed = open.flags.allow_stream_fallback();
    match controller.register_udp_flow_open(open, carrier_datagrams_available_for_flow) {
        Ok(ok) => {
            let selection = match ok.transport_mode {
                TransportMode::Datagram => "datagram",
                TransportMode::StreamFallback => "stream_fallback",
            };
            record_carrier_datagram_selection(
                selection,
                datagram_mode_label(datagram_mode),
                raw_carrier_datagrams_available,
                fallback_allowed,
                rollout_stage,
            );
            Ok(ok)
        }
        Err(error) => {
            if matches!(error, SessionError::DatagramUnavailable) {
                record_carrier_datagram_selection(
                    "unavailable",
                    datagram_mode_label(datagram_mode),
                    raw_carrier_datagrams_available,
                    fallback_allowed,
                    rollout_stage,
                );
            }
            Err(error)
        }
    }
}

pub fn select_h3_udp_flow_for_config(
    controller: &mut SessionController,
    open: &UdpFlowOpen,
    config: &H3TransportConfig,
    raw_carrier_datagrams_available: bool,
) -> Result<UdpFlowOk, SessionError> {
    select_h3_udp_flow(
        controller,
        open,
        config.datagram_runtime_enabled_for_flow(open.flags, raw_carrier_datagrams_available),
        raw_carrier_datagrams_available,
        config.rollout_stage_label(),
    )
}

pub fn prepare_udp_datagram_for_send(
    datagram: &UdpDatagram,
    max_payload_bytes: usize,
) -> Result<Bytes, TransportError> {
    if datagram.payload.len() > max_payload_bytes {
        record_carrier_datagram_guard(
            "udp_payload_too_large",
            "max_udp_payload_bytes",
            max_payload_bytes as u64,
            Some(datagram.payload.len() as u64),
        );
        return Err(TransportError {
            kind: TransportErrorKind::Backpressure,
            message: format!(
                "udp datagram payload exceeded the configured maximum of {} bytes",
                max_payload_bytes
            ),
        });
    }

    ns_wire::encode_udp_datagram(datagram)
        .map(Bytes::from)
        .map_err(|error| TransportError {
            kind: TransportErrorKind::ProtocolViolation,
            message: format!("failed to encode udp datagram: {error}"),
        })
}

pub fn decode_received_udp_datagram(
    payload: &[u8],
    max_payload_bytes: usize,
) -> Result<UdpDatagram, TransportError> {
    let datagram = ns_wire::decode_udp_datagram(payload).map_err(|error| TransportError {
        kind: TransportErrorKind::ProtocolViolation,
        message: format!("failed to decode udp datagram: {error}"),
    })?;
    if datagram.payload.len() > max_payload_bytes {
        record_carrier_datagram_guard(
            "udp_payload_too_large",
            "max_udp_payload_bytes",
            max_payload_bytes as u64,
            Some(datagram.payload.len() as u64),
        );
        return Err(TransportError {
            kind: TransportErrorKind::Backpressure,
            message: format!(
                "received udp datagram payload exceeded the configured maximum of {} bytes",
                max_payload_bytes
            ),
        });
    }
    Ok(datagram)
}

pub fn send_h3_associated_udp_datagram<H>(
    sender: &mut DatagramSender<H, Bytes>,
    datagram: &UdpDatagram,
    max_payload_bytes: usize,
) -> Result<(), TransportError>
where
    H: SendDatagram<Bytes>,
{
    let payload = prepare_udp_datagram_for_send(datagram, max_payload_bytes)?;
    sender.send_datagram(payload).map_err(|error| {
        let message = error.to_string();
        let kind = if message.contains("not available") {
            TransportErrorKind::CarrierRejected
        } else if message.contains("too large") {
            TransportErrorKind::Backpressure
        } else {
            TransportErrorKind::ConnectionLost
        };

        TransportError {
            kind,
            message: format!("h3 datagram send failed: {message}"),
        }
    })?;
    record_carrier_datagram_io("outbound");
    Ok(())
}

pub async fn recv_h3_associated_udp_datagram<H>(
    reader: &mut DatagramReader<H>,
    associated_stream_id: StreamId,
    max_payload_bytes: usize,
) -> Result<UdpDatagram, TransportError>
where
    H: RecvDatagram,
{
    let datagram = reader
        .read_datagram()
        .await
        .map_err(|error| TransportError {
            kind: TransportErrorKind::ConnectionLost,
            message: format!("h3 datagram receive failed: {error}"),
        })?;
    if datagram.stream_id() != associated_stream_id {
        record_carrier_datagram_guard(
            "udp_associated_stream_mismatch",
            "associated_stream_id",
            0,
            None,
        );
        return Err(TransportError {
            kind: TransportErrorKind::ProtocolViolation,
            message: "received h3 datagram on the wrong associated stream".to_owned(),
        });
    }

    let mut payload = datagram.into_payload();
    let payload = payload.copy_to_bytes(payload.remaining());
    let datagram = decode_received_udp_datagram(payload.as_ref(), max_payload_bytes)?;
    record_carrier_datagram_io("inbound");
    Ok(datagram)
}

#[derive(Debug, Default)]
struct H3ControlQueue {
    inbound: VecDeque<Frame>,
    outbound: VecDeque<Frame>,
}

#[derive(Clone, Default)]
pub struct H3ControlIo {
    queue: Arc<Mutex<H3ControlQueue>>,
}

impl H3ControlIo {
    pub fn push_inbound(&self, frame: Frame) {
        self.queue
            .lock()
            .expect("control queue poisoned")
            .inbound
            .push_back(frame);
    }

    pub fn drain_outbound(&self) -> Vec<Frame> {
        self.queue
            .lock()
            .expect("control queue poisoned")
            .outbound
            .drain(..)
            .collect()
    }
}

#[async_trait]
impl ControlFrameIo for H3ControlIo {
    async fn read_frame(&mut self) -> Result<Frame, TransportError> {
        self.queue
            .lock()
            .expect("control queue poisoned")
            .inbound
            .pop_front()
            .ok_or_else(|| TransportError {
                kind: TransportErrorKind::ConnectionLost,
                message: "no control frame available".to_owned(),
            })
    }

    async fn write_frame(&mut self, frame: &Frame) -> Result<(), TransportError> {
        self.queue
            .lock()
            .expect("control queue poisoned")
            .outbound
            .push_back(frame.clone());
        Ok(())
    }
}

#[derive(Debug)]
struct RelayState {
    preamble: VecDeque<Frame>,
    raw_chunks: VecDeque<Bytes>,
    raw_buffered_bytes: usize,
    max_raw_prebuffer_bytes: usize,
    write_finished: bool,
}

impl Default for RelayState {
    fn default() -> Self {
        Self {
            preamble: VecDeque::new(),
            raw_chunks: VecDeque::new(),
            raw_buffered_bytes: 0,
            max_raw_prebuffer_bytes: DEFAULT_MAX_RAW_PREBUFFER_BYTES,
            write_finished: false,
        }
    }
}

#[derive(Clone, Default)]
pub struct H3RelayStream {
    state: Arc<Mutex<RelayState>>,
}

#[async_trait]
impl RelayStreamIo for H3RelayStream {
    async fn write_preamble(&mut self, frame: &Frame) -> Result<(), TransportError> {
        self.state
            .lock()
            .expect("relay state poisoned")
            .preamble
            .push_back(frame.clone());
        Ok(())
    }

    async fn read_preamble(&mut self) -> Result<Frame, TransportError> {
        self.state
            .lock()
            .expect("relay state poisoned")
            .preamble
            .pop_front()
            .ok_or_else(|| TransportError {
                kind: TransportErrorKind::ConnectionLost,
                message: "no relay preamble available".to_owned(),
            })
    }

    async fn send_raw(&mut self, chunk: Bytes) -> Result<(), TransportError> {
        let mut guard = self.state.lock().expect("relay state poisoned");
        if guard.write_finished {
            return Err(TransportError {
                kind: TransportErrorKind::ConnectionLost,
                message: "relay raw send attempted after finish".to_owned(),
            });
        }
        let next = guard.raw_buffered_bytes.saturating_add(chunk.len());
        if next > guard.max_raw_prebuffer_bytes {
            return Err(TransportError {
                kind: TransportErrorKind::Backpressure,
                message: format!(
                    "relay raw prebuffer exceeded {} bytes",
                    guard.max_raw_prebuffer_bytes
                ),
            });
        }
        guard.raw_buffered_bytes = next;
        guard.raw_chunks.push_back(chunk);
        Ok(())
    }

    async fn recv_raw(&mut self) -> Result<Option<Bytes>, TransportError> {
        let mut guard = self.state.lock().expect("relay state poisoned");
        if let Some(chunk) = guard.raw_chunks.pop_front() {
            guard.raw_buffered_bytes = guard.raw_buffered_bytes.saturating_sub(chunk.len());
            return Ok(Some(chunk));
        }
        if guard.write_finished {
            return Ok(None);
        }
        Err(TransportError {
            kind: TransportErrorKind::ConnectionLost,
            message: "no relay raw bytes available".to_owned(),
        })
    }

    async fn finish_raw(&mut self) -> Result<(), TransportError> {
        self.state
            .lock()
            .expect("relay state poisoned")
            .write_finished = true;
        Ok(())
    }
}

#[derive(Debug)]
struct H3DatagramState {
    inbound: VecDeque<UdpDatagram>,
    outbound: VecDeque<UdpDatagram>,
    buffered_outbound_bytes: usize,
    buffered_outbound_datagrams: usize,
    buffered_outbound_per_flow: BTreeMap<u64, usize>,
    max_payload_bytes: usize,
    max_buffered_bytes: usize,
    max_buffered_datagrams: usize,
    max_buffered_datagrams_per_flow: usize,
}

impl Default for H3DatagramState {
    fn default() -> Self {
        let config = H3DatagramRuntimeConfig::default();
        Self {
            inbound: VecDeque::new(),
            outbound: VecDeque::new(),
            buffered_outbound_bytes: 0,
            buffered_outbound_datagrams: 0,
            buffered_outbound_per_flow: BTreeMap::new(),
            max_payload_bytes: config.max_payload_bytes,
            max_buffered_bytes: config.max_buffered_bytes,
            max_buffered_datagrams: config.max_buffered_datagrams,
            max_buffered_datagrams_per_flow: config.max_buffered_datagrams_per_flow,
        }
    }
}

#[derive(Clone, Default)]
pub struct H3DatagramSocket {
    state: Arc<Mutex<H3DatagramState>>,
}

impl H3DatagramSocket {
    pub fn with_runtime_config(config: H3DatagramRuntimeConfig) -> Result<Self, TransportError> {
        config.validate()?;
        Ok(Self {
            state: Arc::new(Mutex::new(H3DatagramState {
                inbound: VecDeque::new(),
                outbound: VecDeque::new(),
                buffered_outbound_bytes: 0,
                buffered_outbound_datagrams: 0,
                buffered_outbound_per_flow: BTreeMap::new(),
                max_payload_bytes: config.max_payload_bytes,
                max_buffered_bytes: config.max_buffered_bytes,
                max_buffered_datagrams: config.max_buffered_datagrams,
                max_buffered_datagrams_per_flow: config.max_buffered_datagrams_per_flow,
            })),
        })
    }

    pub fn push_inbound(&self, datagram: UdpDatagram) -> Result<(), TransportError> {
        let mut guard = self.state.lock().expect("datagram queue poisoned");
        if datagram.payload.len() > guard.max_payload_bytes {
            record_carrier_datagram_guard(
                "udp_payload_too_large",
                "max_udp_payload_bytes",
                guard.max_payload_bytes as u64,
                Some(datagram.payload.len() as u64),
            );
            return Err(TransportError {
                kind: TransportErrorKind::Backpressure,
                message: format!(
                    "udp datagram payload exceeded the configured maximum of {} bytes",
                    guard.max_payload_bytes
                ),
            });
        }
        guard.inbound.push_back(datagram);
        record_carrier_datagram_io("inbound");
        Ok(())
    }

    pub fn drain_outbound(&self) -> Vec<UdpDatagram> {
        let mut guard = self.state.lock().expect("datagram queue poisoned");
        guard.buffered_outbound_bytes = 0;
        guard.buffered_outbound_datagrams = 0;
        guard.buffered_outbound_per_flow.clear();
        guard.outbound.drain(..).collect()
    }
}

#[async_trait]
impl DatagramIo for H3DatagramSocket {
    async fn send(&self, datagram: UdpDatagram) -> Result<(), TransportError> {
        let mut guard = self.state.lock().expect("datagram queue poisoned");
        if datagram.payload.len() > guard.max_payload_bytes {
            record_carrier_datagram_guard(
                "udp_payload_too_large",
                "max_udp_payload_bytes",
                guard.max_payload_bytes as u64,
                Some(datagram.payload.len() as u64),
            );
            return Err(TransportError {
                kind: TransportErrorKind::Backpressure,
                message: format!(
                    "udp datagram payload exceeded the configured maximum of {} bytes",
                    guard.max_payload_bytes
                ),
            });
        }
        let next_datagrams = guard.buffered_outbound_datagrams.saturating_add(1);
        if next_datagrams > guard.max_buffered_datagrams {
            record_carrier_datagram_guard(
                "udp_datagram_session_burst_exceeded",
                "max_buffered_datagrams",
                guard.max_buffered_datagrams as u64,
                Some(next_datagrams as u64),
            );
            return Err(TransportError {
                kind: TransportErrorKind::Backpressure,
                message: format!(
                    "udp datagram queue exceeded the configured maximum of {} datagrams",
                    guard.max_buffered_datagrams
                ),
            });
        }
        let next_flow_datagrams = guard
            .buffered_outbound_per_flow
            .get(&datagram.flow_id)
            .copied()
            .unwrap_or(0)
            .saturating_add(1);
        if next_flow_datagrams > guard.max_buffered_datagrams_per_flow {
            record_carrier_datagram_guard(
                "udp_datagram_flow_burst_exceeded",
                "max_buffered_datagrams_per_flow",
                guard.max_buffered_datagrams_per_flow as u64,
                Some(next_flow_datagrams as u64),
            );
            return Err(TransportError {
                kind: TransportErrorKind::Backpressure,
                message: format!(
                    "udp datagram flow burst exceeded the configured maximum of {} datagrams",
                    guard.max_buffered_datagrams_per_flow
                ),
            });
        }
        let next = guard
            .buffered_outbound_bytes
            .saturating_add(datagram.payload.len());
        if next > guard.max_buffered_bytes {
            record_carrier_datagram_guard(
                "udp_datagram_queue_full",
                "max_buffered_datagram_bytes",
                guard.max_buffered_bytes as u64,
                Some(next as u64),
            );
            return Err(TransportError {
                kind: TransportErrorKind::Backpressure,
                message: format!(
                    "udp datagram queue exceeded the configured maximum of {} bytes",
                    guard.max_buffered_bytes
                ),
            });
        }
        guard.buffered_outbound_bytes = next;
        guard.buffered_outbound_datagrams = next_datagrams;
        guard
            .buffered_outbound_per_flow
            .insert(datagram.flow_id, next_flow_datagrams);
        guard.outbound.push_back(datagram);
        record_carrier_datagram_io("outbound");
        Ok(())
    }

    async fn recv(&self) -> Result<Option<UdpDatagram>, TransportError> {
        Ok(self
            .state
            .lock()
            .expect("datagram queue poisoned")
            .inbound
            .pop_front())
    }
}

#[derive(Debug, Default)]
struct H3UdpFallbackState {
    inbound: VecDeque<Frame>,
    outbound: VecDeque<Frame>,
}

#[derive(Clone, Default)]
pub struct H3UdpFallbackStream {
    state: Arc<Mutex<H3UdpFallbackState>>,
}

impl H3UdpFallbackStream {
    pub fn push_inbound(&self, frame: Frame) {
        self.state
            .lock()
            .expect("udp fallback state poisoned")
            .inbound
            .push_back(frame);
    }

    pub fn drain_outbound(&self) -> Vec<Frame> {
        self.state
            .lock()
            .expect("udp fallback state poisoned")
            .outbound
            .drain(..)
            .collect()
    }
}

#[async_trait]
impl UdpFallbackStreamIo for H3UdpFallbackStream {
    async fn write_frame(&mut self, frame: &Frame) -> Result<(), TransportError> {
        self.state
            .lock()
            .expect("udp fallback state poisoned")
            .outbound
            .push_back(frame.clone());
        Ok(())
    }

    async fn read_frame(&mut self) -> Result<Frame, TransportError> {
        self.state
            .lock()
            .expect("udp fallback state poisoned")
            .inbound
            .pop_front()
            .ok_or_else(|| TransportError {
                kind: TransportErrorKind::ConnectionLost,
                message: "no udp fallback frame available".to_owned(),
            })
    }
}

pub struct H3PendingSession {
    info: CarrierSessionInfo,
    control: H3ControlIo,
    datagrams_available: bool,
}

pub struct H3EstablishedSession {
    info: CarrierSessionInfo,
    control: H3ControlIo,
    datagrams: Option<H3DatagramSocket>,
}

impl H3PendingSession {
    pub fn new(config: &H3TransportConfig) -> Result<Self, H3TransportError> {
        config.validate()?;
        Ok(Self {
            info: CarrierSessionInfo {
                carrier_profile_id: config.carrier_profile_id.clone(),
                datagrams_available: config.datagram_runtime_enabled(),
            },
            control: H3ControlIo::default(),
            datagrams_available: config.datagram_runtime_enabled(),
        })
    }
}

#[async_trait]
impl PendingCarrierSession for H3PendingSession {
    type Control = H3ControlIo;
    type Established = H3EstablishedSession;

    fn info(&self) -> &CarrierSessionInfo {
        &self.info
    }

    fn control(&mut self) -> &mut Self::Control {
        &mut self.control
    }

    async fn into_established(self) -> Result<Self::Established, TransportError> {
        Ok(H3EstablishedSession {
            info: self.info,
            control: self.control,
            datagrams: self.datagrams_available.then(H3DatagramSocket::default),
        })
    }
}

#[async_trait]
impl EstablishedCarrierSession for H3EstablishedSession {
    type Control = H3ControlIo;
    type Relay = H3RelayStream;
    type Datagram = H3DatagramSocket;
    type UdpFallback = H3UdpFallbackStream;

    fn info(&self) -> &CarrierSessionInfo {
        &self.info
    }

    fn control(&mut self) -> &mut Self::Control {
        &mut self.control
    }

    async fn open_relay_stream(&mut self, open: StreamOpen) -> Result<Self::Relay, TransportError> {
        let relay = H3RelayStream::default();
        let mut relay_writer = relay.clone();
        relay_writer
            .write_preamble(&Frame::StreamOpen(open))
            .await?;
        Ok(relay)
    }

    async fn accept_relay_stream(
        &mut self,
    ) -> Result<IncomingRelayStream<Self::Relay>, TransportError> {
        let relay = H3RelayStream::default();
        let mut relay_writer = relay.clone();
        relay_writer
            .write_preamble(&Frame::StreamAccept(StreamAccept {
                relay_id: 1,
                bind_address: ns_wire::TargetAddress::Domain("accepted-bind".to_owned()),
                bind_port: 443,
                metadata: Vec::new(),
            }))
            .await?;

        Ok(IncomingRelayStream {
            relay_id: 1,
            stream: relay,
        })
    }

    async fn open_udp_fallback_stream(
        &mut self,
        open: UdpStreamOpen,
    ) -> Result<Self::UdpFallback, TransportError> {
        let stream = H3UdpFallbackStream::default();
        let mut writer = stream.clone();
        writer.write_frame(&Frame::UdpStreamOpen(open)).await?;
        Ok(stream)
    }

    async fn accept_udp_fallback_stream(
        &mut self,
    ) -> Result<IncomingUdpFallbackStream<Self::UdpFallback>, TransportError> {
        let stream = H3UdpFallbackStream::default();
        let mut writer = stream.clone();
        writer
            .write_frame(&Frame::UdpStreamAccept(UdpStreamAccept {
                flow_id: 1,
                metadata: Vec::new(),
            }))
            .await?;
        Ok(IncomingUdpFallbackStream { flow_id: 1, stream })
    }

    fn datagrams(&self) -> Option<&Self::Datagram> {
        self.datagrams.as_ref()
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct H3RelayRuntimeConfig {
    pub max_raw_prebuffer_bytes: usize,
    pub idle_timeout_ms: u64,
    pub io_buffer_bytes: usize,
}

impl Default for H3RelayRuntimeConfig {
    fn default() -> Self {
        Self {
            max_raw_prebuffer_bytes: DEFAULT_MAX_RAW_PREBUFFER_BYTES,
            idle_timeout_ms: 30_000,
            io_buffer_bytes: 8 * 1024,
        }
    }
}

impl H3RelayRuntimeConfig {
    fn validate(&self) -> Result<(), TransportError> {
        if self.max_raw_prebuffer_bytes == 0 {
            return Err(TransportError {
                kind: TransportErrorKind::ProtocolViolation,
                message: "relay runtime max_raw_prebuffer_bytes must be non-zero".to_owned(),
            });
        }
        if self.idle_timeout_ms == 0 {
            return Err(TransportError {
                kind: TransportErrorKind::ProtocolViolation,
                message: "relay runtime idle_timeout_ms must be non-zero".to_owned(),
            });
        }
        if self.io_buffer_bytes == 0 {
            return Err(TransportError {
                kind: TransportErrorKind::ProtocolViolation,
                message: "relay runtime io_buffer_bytes must be non-zero".to_owned(),
            });
        }
        Ok(())
    }

    fn idle_timeout(&self) -> Duration {
        Duration::from_millis(self.idle_timeout_ms)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum H3RelayCloseReason {
    ClientFinished,
    UpstreamFinished,
    IdleTimeout,
    PrebufferOverflow,
    CarrierReadFailed,
    CarrierWriteFailed,
    UpstreamReadFailed,
    UpstreamWriteFailed,
}

impl H3RelayCloseReason {
    fn as_str(self) -> &'static str {
        match self {
            Self::ClientFinished => "client_finished",
            Self::UpstreamFinished => "upstream_finished",
            Self::IdleTimeout => "idle_timeout",
            Self::PrebufferOverflow => "prebuffer_overflow",
            Self::CarrierReadFailed => "carrier_read_failed",
            Self::CarrierWriteFailed => "carrier_write_failed",
            Self::UpstreamReadFailed => "upstream_read_failed",
            Self::UpstreamWriteFailed => "upstream_write_failed",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct H3RelayRuntimeOutcome {
    pub relay_id: u64,
    pub close_reason: H3RelayCloseReason,
    pub bytes_from_client: u64,
    pub bytes_to_client: u64,
    pub client_half_closed: bool,
    pub upstream_half_closed: bool,
}

fn set_relay_close_reason(close_reason: &mut Option<H3RelayCloseReason>, next: H3RelayCloseReason) {
    match next {
        H3RelayCloseReason::ClientFinished | H3RelayCloseReason::UpstreamFinished => {
            if close_reason.is_none() {
                *close_reason = Some(next);
            }
        }
        _ => *close_reason = Some(next),
    }
}

fn record_relay_runtime_close(outcome: &H3RelayRuntimeOutcome) {
    record_carrier_relay_closed(
        outcome.close_reason.as_str(),
        outcome.bytes_from_client,
        outcome.bytes_to_client,
        outcome.client_half_closed,
        outcome.upstream_half_closed,
    );
}

pub async fn forward_raw_tcp_relay<R, U>(
    relay_id: u64,
    relay: &mut R,
    mut upstream: U,
    config: &H3RelayRuntimeConfig,
) -> Result<H3RelayRuntimeOutcome, TransportError>
where
    R: RelayStreamIo + Send,
    U: AsyncRead + AsyncWrite + Unpin + Send,
{
    config.validate()?;

    let mut close_reason = None;
    let mut outcome = H3RelayRuntimeOutcome {
        relay_id,
        close_reason: H3RelayCloseReason::ClientFinished,
        bytes_from_client: 0,
        bytes_to_client: 0,
        client_half_closed: false,
        upstream_half_closed: false,
    };
    let mut upstream_buffer = vec![0_u8; config.io_buffer_bytes];
    let mut client_read_open = true;
    let mut upstream_read_open = true;

    while client_read_open || upstream_read_open {
        let idle_timeout = tokio::time::sleep(config.idle_timeout());
        tokio::pin!(idle_timeout);

        tokio::select! {
            _ = &mut idle_timeout => {
                set_relay_close_reason(&mut close_reason, H3RelayCloseReason::IdleTimeout);
                outcome.close_reason = close_reason.unwrap_or(H3RelayCloseReason::IdleTimeout);
                record_relay_runtime_close(&outcome);
                return Err(TransportError {
                    kind: TransportErrorKind::TimedOut,
                    message: format!(
                        "relay {relay_id} exceeded the idle timeout of {}ms",
                        config.idle_timeout_ms
                    ),
                });
            }
            relay_read = relay.recv_raw(), if client_read_open => {
                let maybe_chunk = match relay_read {
                    Ok(chunk) => chunk,
                    Err(error) => {
                        set_relay_close_reason(&mut close_reason, H3RelayCloseReason::CarrierReadFailed);
                        outcome.close_reason = close_reason.unwrap_or(H3RelayCloseReason::CarrierReadFailed);
                        record_relay_runtime_close(&outcome);
                        return Err(error);
                    }
                };
                match maybe_chunk {
                    Some(chunk) => {
                        if chunk.len() > config.max_raw_prebuffer_bytes {
                            set_relay_close_reason(&mut close_reason, H3RelayCloseReason::PrebufferOverflow);
                            outcome.close_reason = close_reason.unwrap_or(H3RelayCloseReason::PrebufferOverflow);
                            record_relay_runtime_close(&outcome);
                            return Err(TransportError {
                                kind: TransportErrorKind::Backpressure,
                                message: format!(
                                    "relay {relay_id} raw chunk exceeded the configured prebuffer budget of {} bytes",
                                    config.max_raw_prebuffer_bytes
                                ),
                            });
                        }
                        upstream.write_all(chunk.as_ref()).await.map_err(|error| {
                            set_relay_close_reason(&mut close_reason, H3RelayCloseReason::UpstreamWriteFailed);
                            outcome.close_reason = close_reason.unwrap_or(H3RelayCloseReason::UpstreamWriteFailed);
                            record_relay_runtime_close(&outcome);
                            TransportError {
                                kind: TransportErrorKind::ConnectionLost,
                                message: format!("relay {relay_id} upstream write failed: {error}"),
                            }
                        })?;
                        outcome.bytes_from_client += chunk.len() as u64;
                    }
                    None => {
                        client_read_open = false;
                        outcome.client_half_closed = true;
                        upstream.shutdown().await.map_err(|error| {
                            set_relay_close_reason(&mut close_reason, H3RelayCloseReason::UpstreamWriteFailed);
                            outcome.close_reason = close_reason.unwrap_or(H3RelayCloseReason::UpstreamWriteFailed);
                            record_relay_runtime_close(&outcome);
                            TransportError {
                                kind: TransportErrorKind::ConnectionLost,
                                message: format!(
                                    "relay {relay_id} upstream shutdown after client EOF failed: {error}"
                                ),
                            }
                        })?;
                        set_relay_close_reason(&mut close_reason, H3RelayCloseReason::ClientFinished);
                    }
                }
            }
            upstream_read = upstream.read(&mut upstream_buffer), if upstream_read_open => {
                match upstream_read {
                    Ok(0) => {
                        upstream_read_open = false;
                        outcome.upstream_half_closed = true;
                        relay.finish_raw().await.inspect_err(|_error| {
                            set_relay_close_reason(&mut close_reason, H3RelayCloseReason::CarrierWriteFailed);
                            outcome.close_reason = close_reason.unwrap_or(H3RelayCloseReason::CarrierWriteFailed);
                            record_relay_runtime_close(&outcome);
                        })?;
                        set_relay_close_reason(&mut close_reason, H3RelayCloseReason::UpstreamFinished);
                    }
                    Ok(read) => {
                        let chunk = Bytes::copy_from_slice(&upstream_buffer[..read]);
                        relay.send_raw(chunk).await.inspect_err(|error| {
                            let next_reason = match error.kind {
                                TransportErrorKind::Backpressure => H3RelayCloseReason::PrebufferOverflow,
                                _ => H3RelayCloseReason::CarrierWriteFailed,
                            };
                            set_relay_close_reason(&mut close_reason, next_reason);
                            outcome.close_reason = close_reason.unwrap_or(next_reason);
                            record_relay_runtime_close(&outcome);
                        })?;
                        outcome.bytes_to_client += read as u64;
                    }
                    Err(error) => {
                        set_relay_close_reason(&mut close_reason, H3RelayCloseReason::UpstreamReadFailed);
                        outcome.close_reason = close_reason.unwrap_or(H3RelayCloseReason::UpstreamReadFailed);
                        record_relay_runtime_close(&outcome);
                        return Err(TransportError {
                            kind: TransportErrorKind::ConnectionLost,
                            message: format!("relay {relay_id} upstream read failed: {error}"),
                        });
                    }
                }
            }
        }
    }

    outcome.close_reason = close_reason.unwrap_or(H3RelayCloseReason::ClientFinished);
    record_relay_runtime_close(&outcome);
    Ok(outcome)
}

pub struct H3ClientConnector;

impl H3ClientConnector {
    pub fn prepare(config: &H3TransportConfig) -> Result<H3PendingSession, H3TransportError> {
        let _transport = build_quinn_transport_config(config)?;
        let _tls = build_client_tls_config(config)?;
        let _control_request = config.control_request()?;
        let _relay_request = config.relay_request()?;
        H3PendingSession::new(config)
    }
}

#[derive(Debug, Error)]
pub enum H3TransportError {
    #[error("the carrier config did not describe an h3 profile")]
    UnsupportedCarrierKind,
    #[error("invalid h3 transport config field {0}")]
    InvalidConfig(&'static str),
    #[error("invalid h3 request header name {0}")]
    InvalidHeaderName(String),
    #[error("invalid h3 request header value for {0}")]
    InvalidHeaderValue(String),
    #[error("invalid h3 request uri")]
    InvalidRequestUri,
    #[error("failed to build h3 request template")]
    InvalidRequestTemplate,
    #[error("h3 tunnel frame exceeded {max_bytes} bytes (got {actual_bytes})")]
    TunnelFrameTooLarge {
        max_bytes: usize,
        actual_bytes: usize,
    },
    #[error("h3 tunnel frame failed to encode or decode")]
    InvalidTunnelFrame,
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeMap;
    use std::collections::VecDeque;
    use std::future::Future;
    use std::io;
    use std::sync::Arc;
    use tokio::io::{AsyncReadExt, AsyncWriteExt, duplex};
    use tokio::sync::Notify;
    use tokio::time::sleep;
    use tracing_subscriber::fmt::MakeWriter;

    fn config() -> H3TransportConfig {
        H3TransportConfig {
            carrier_kind: CarrierKind::H3,
            carrier_profile_id: CarrierProfileId::new("carrier-primary")
                .expect("fixture carrier profile should be valid"),
            origin_host: "edge.example.net".to_owned(),
            origin_port: 443,
            sni: Some("edge.example.net".to_owned()),
            alpn: vec!["h3".to_owned()],
            control_path: "/control".to_owned(),
            relay_path: "/relay".to_owned(),
            headers: BTreeMap::from([("x-verta-profile".to_owned(), "carrier-primary".to_owned())]),
            datagram_enabled: false,
            datagram_rollout: H3DatagramRollout::Disabled,
            heartbeat_interval_ms: 15_000,
            idle_timeout_ms: 60_000,
            zero_rtt_policy: H3ZeroRttPolicy::Disabled,
            connect_backoff: H3ConnectBackoff {
                initial_ms: 500,
                max_ms: 10_000,
                jitter: 0.2,
            },
        }
    }

    #[derive(Clone, Default)]
    struct TestLogSink(Arc<Mutex<Vec<u8>>>);

    struct TestLogWriter(Arc<Mutex<Vec<u8>>>);

    impl io::Write for TestLogWriter {
        fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
            self.0
                .lock()
                .expect("test log sink poisoned")
                .extend_from_slice(buf);
            Ok(buf.len())
        }

        fn flush(&mut self) -> io::Result<()> {
            Ok(())
        }
    }

    impl<'a> MakeWriter<'a> for TestLogSink {
        type Writer = TestLogWriter;

        fn make_writer(&'a self) -> Self::Writer {
            TestLogWriter(self.0.clone())
        }
    }

    async fn capture_logs_async<T>(future: impl Future<Output = T>) -> (T, String) {
        let sink = TestLogSink::default();
        let subscriber = tracing_subscriber::fmt()
            .with_writer(sink.clone())
            .with_ansi(false)
            .without_time()
            .json()
            .finish();
        let dispatch = tracing::Dispatch::new(subscriber);
        let guard = tracing::dispatcher::set_default(&dispatch);
        let result = future.await;
        drop(guard);
        let bytes = sink.0.lock().expect("test log sink poisoned").clone();
        let output = String::from_utf8(bytes).expect("captured tracing output should be UTF-8");
        (result, output)
    }

    #[test]
    fn rejects_empty_alpn() {
        let mut cfg = config();
        cfg.alpn.clear();
        assert!(matches!(
            cfg.validate(),
            Err(H3TransportError::InvalidConfig("alpn"))
        ));
    }

    #[test]
    fn builds_control_request_template_from_signed_profile_fields() {
        let cfg = config();
        let request = cfg
            .control_request()
            .expect("valid h3 config should produce a control request");

        assert_eq!(request.method(), Method::CONNECT);
        assert_eq!(request.uri().scheme_str(), Some("https"));
        assert_eq!(
            request.uri().authority().map(|value| value.as_str()),
            Some("edge.example.net:443")
        );
        assert_eq!(request.uri().path(), "/control");
        assert_eq!(request.headers()["x-verta-profile"], "carrier-primary");
    }

    #[test]
    fn zero_rtt_policy_is_parsed_but_early_data_stays_disabled() {
        let mut cfg = config();
        cfg.zero_rtt_policy = H3ZeroRttPolicy::Allow;

        let tls =
            build_client_tls_config(&cfg).expect("allow policy should still build a TLS config");
        assert!(!tls.enable_early_data);
    }

    #[test]
    fn rejects_hop_by_hop_headers_in_signed_request_templates() {
        let mut cfg = config();
        cfg.headers
            .insert("content-length".to_owned(), "128".to_owned());

        assert!(matches!(
            cfg.validate(),
            Err(H3TransportError::InvalidHeaderName(name)) if name == "content-length"
        ));
    }

    #[test]
    fn datagram_rollout_maps_runtime_and_advertised_modes_explicitly() {
        let mut cfg = config();
        cfg.datagram_enabled = true;
        cfg.datagram_rollout = H3DatagramRollout::Automatic;
        assert!(cfg.datagram_runtime_enabled());
        assert_eq!(cfg.rollout_stage_label(), "automatic");
        assert_eq!(
            cfg.advertised_datagram_mode(true),
            DatagramMode::AvailableAndEnabled
        );
        assert_eq!(
            cfg.advertised_datagram_mode(false),
            DatagramMode::Unavailable
        );

        cfg.datagram_rollout = H3DatagramRollout::Canary;
        assert!(cfg.datagram_runtime_enabled());
        assert_eq!(cfg.rollout_stage_label(), "canary");
        assert_eq!(
            cfg.advertised_datagram_mode(true),
            DatagramMode::AvailableAndEnabled
        );
        assert!(!cfg.datagram_runtime_enabled_for_flow(
            FlowFlags::new(0b0010).expect("fallback-only flags should be valid"),
            true,
        ));
        assert!(cfg.datagram_runtime_enabled_for_flow(
            FlowFlags::new(0b0011).expect("prefer-datagram flags should be valid"),
            true,
        ));

        cfg.datagram_rollout = H3DatagramRollout::Disabled;
        assert!(!cfg.datagram_runtime_enabled());
        assert_eq!(cfg.rollout_stage_label(), "disabled");
        assert_eq!(
            cfg.advertised_datagram_mode(true),
            DatagramMode::DisabledByPolicy
        );
        assert_eq!(
            cfg.advertised_datagram_mode(false),
            DatagramMode::DisabledByPolicy
        );
    }

    #[test]
    fn startup_contract_resolution_stays_fail_closed_when_rollout_widens_signed_intent() {
        assert!(matches!(
            resolve_h3_datagram_startup_contract(false, H3DatagramRollout::Automatic, true),
            Err(H3TransportError::InvalidConfig("datagram_rollout"))
        ));
    }

    #[test]
    fn startup_contract_resolution_reports_resolved_mode_and_stage() {
        let available = resolve_h3_datagram_startup_contract(true, H3DatagramRollout::Canary, true)
            .expect("available datagrams should resolve");
        assert_eq!(
            available.resolved_datagram_mode,
            DatagramMode::AvailableAndEnabled
        );
        assert_eq!(available.rollout_stage, "canary");

        let unavailable =
            resolve_h3_datagram_startup_contract(true, H3DatagramRollout::Automatic, false)
                .expect("carrier-unavailable datagrams should still resolve");
        assert_eq!(
            unavailable.resolved_datagram_mode,
            DatagramMode::Unavailable
        );
        assert_eq!(unavailable.rollout_stage, "automatic");

        let disabled =
            resolve_h3_datagram_startup_contract(true, H3DatagramRollout::Disabled, true)
                .expect("disabled rollout should resolve");
        assert_eq!(
            disabled.resolved_datagram_mode,
            DatagramMode::DisabledByPolicy
        );
        assert_eq!(disabled.rollout_stage, "disabled");
    }

    #[test]
    fn rejects_enabled_datagram_rollout_when_signed_profile_disables_datagrams() {
        let mut cfg = config();
        cfg.datagram_enabled = false;
        cfg.datagram_rollout = H3DatagramRollout::Automatic;
        assert!(matches!(
            cfg.validate(),
            Err(H3TransportError::InvalidConfig("datagram_rollout"))
        ));

        cfg.datagram_rollout = H3DatagramRollout::Canary;
        assert!(matches!(
            cfg.validate(),
            Err(H3TransportError::InvalidConfig("datagram_rollout"))
        ));
    }

    #[test]
    fn tunnel_frame_codec_enforces_size_bounds() {
        let oversized = vec![0_u8; MAX_TUNNEL_FRAME_BYTES + 1];
        assert!(matches!(
            decode_tunnel_frame(&oversized),
            Err(H3TransportError::TunnelFrameTooLarge {
                max_bytes: MAX_TUNNEL_FRAME_BYTES,
                actual_bytes,
            }) if actual_bytes == MAX_TUNNEL_FRAME_BYTES + 1
        ));
    }

    #[tokio::test]
    async fn in_memory_relay_supports_raw_receive_and_half_close() {
        let relay = H3RelayStream::default();
        let mut writer = relay.clone();
        let mut reader = relay;

        writer
            .send_raw(Bytes::from_static(b"verta"))
            .await
            .expect("raw bytes should buffer");
        assert_eq!(
            reader
                .recv_raw()
                .await
                .expect("buffered raw bytes should be readable"),
            Some(Bytes::from_static(b"verta"))
        );
        writer
            .finish_raw()
            .await
            .expect("finishing the writer side should succeed");
        assert_eq!(
            reader
                .recv_raw()
                .await
                .expect("reader should observe a clean EOF after finish"),
            None
        );
    }

    #[tokio::test]
    async fn pending_session_becomes_established() {
        let pending = H3ClientConnector::prepare(&config())
            .expect("valid h3 config should prepare a pending session");
        let established = pending
            .into_established()
            .await
            .expect("pending h3 session should become established");
        assert!(!established.info().datagrams_available);
    }

    #[tokio::test(flavor = "current_thread")]
    async fn datagram_socket_emits_success_guard_and_recovery_observability_events() {
        let socket = H3DatagramSocket::with_runtime_config(H3DatagramRuntimeConfig {
            max_payload_bytes: 4,
            max_buffered_bytes: 5,
            max_buffered_datagrams: 2,
            max_buffered_datagrams_per_flow: 2,
        })
        .expect("datagram runtime config should be valid");
        let (overflow_error, logs) = capture_logs_async(async {
            socket
                .push_inbound(UdpDatagram {
                    flow_id: 7,
                    flags: ns_wire::DatagramFlags::new(0)
                        .expect("zero datagram flags should be valid"),
                    payload: b"pong".to_vec(),
                })
                .expect("inbound datagram should fit");
            socket
                .send(UdpDatagram {
                    flow_id: 7,
                    flags: ns_wire::DatagramFlags::new(0)
                        .expect("zero datagram flags should be valid"),
                    payload: b"ping".to_vec(),
                })
                .await
                .expect("outbound datagram should fit");
            socket
                .send(UdpDatagram {
                    flow_id: 7,
                    flags: ns_wire::DatagramFlags::new(0)
                        .expect("zero datagram flags should be valid"),
                    payload: b"zz".to_vec(),
                })
                .await
                .expect_err("queue overflow should fail closed")
        })
        .await;

        assert_eq!(overflow_error.kind, TransportErrorKind::Backpressure);
        assert_eq!(socket.drain_outbound().len(), 1);
        socket
            .send(UdpDatagram {
                flow_id: 7,
                flags: ns_wire::DatagramFlags::new(0).expect("zero datagram flags should be valid"),
                payload: b"ok".to_vec(),
            })
            .await
            .expect("queue should recover after draining outbound datagrams");
        assert!(logs.contains("\"event_name\":\"verta.carrier.datagram.io\""));
        assert!(logs.contains("\"direction\":\"inbound\""));
        assert!(logs.contains("\"direction\":\"outbound\""));
        assert!(logs.contains("\"event_name\":\"verta.carrier.datagram.guard\""));
        assert!(logs.contains("\"reason\":\"udp_datagram_queue_full\""));
        assert!(logs.contains("\"limit_name\":\"max_buffered_datagram_bytes\""));
        assert!(logs.contains("\"limit_value\":5"));
        assert!(logs.contains("\"actual_value\":6"));
    }

    #[tokio::test(flavor = "current_thread")]
    async fn datagram_socket_emits_session_and_flow_burst_guards() {
        let socket = H3DatagramSocket::with_runtime_config(H3DatagramRuntimeConfig {
            max_payload_bytes: 8,
            max_buffered_bytes: 64,
            max_buffered_datagrams: 2,
            max_buffered_datagrams_per_flow: 1,
        })
        .expect("datagram runtime config should be valid");

        let (flow_error, flow_logs) = capture_logs_async(async {
            socket
                .send(UdpDatagram {
                    flow_id: 7,
                    flags: ns_wire::DatagramFlags::new(0)
                        .expect("zero datagram flags should be valid"),
                    payload: b"ping".to_vec(),
                })
                .await
                .expect("first datagram should fit");
            socket
                .send(UdpDatagram {
                    flow_id: 7,
                    flags: ns_wire::DatagramFlags::new(0)
                        .expect("zero datagram flags should be valid"),
                    payload: b"pong".to_vec(),
                })
                .await
                .expect_err("per-flow datagram burst should fail closed")
        })
        .await;
        assert_eq!(flow_error.kind, TransportErrorKind::Backpressure);
        assert!(flow_logs.contains("\"reason\":\"udp_datagram_flow_burst_exceeded\""));
        assert!(flow_logs.contains("\"limit_name\":\"max_buffered_datagrams_per_flow\""));
        assert!(flow_logs.contains("\"limit_value\":1"));
        assert!(flow_logs.contains("\"actual_value\":2"));

        let socket = H3DatagramSocket::with_runtime_config(H3DatagramRuntimeConfig {
            max_payload_bytes: 8,
            max_buffered_bytes: 64,
            max_buffered_datagrams: 1,
            max_buffered_datagrams_per_flow: 2,
        })
        .expect("datagram runtime config should be valid");
        let (session_error, session_logs) = capture_logs_async(async {
            socket
                .send(UdpDatagram {
                    flow_id: 7,
                    flags: ns_wire::DatagramFlags::new(0)
                        .expect("zero datagram flags should be valid"),
                    payload: b"ping".to_vec(),
                })
                .await
                .expect("first datagram should fit");
            socket
                .send(UdpDatagram {
                    flow_id: 8,
                    flags: ns_wire::DatagramFlags::new(0)
                        .expect("zero datagram flags should be valid"),
                    payload: b"pong".to_vec(),
                })
                .await
                .expect_err("per-session datagram burst should fail closed")
        })
        .await;
        assert_eq!(session_error.kind, TransportErrorKind::Backpressure);
        assert!(session_logs.contains("\"reason\":\"udp_datagram_session_burst_exceeded\""));
        assert!(session_logs.contains("\"limit_name\":\"max_buffered_datagrams\""));
        assert!(session_logs.contains("\"limit_value\":1"));
        assert!(session_logs.contains("\"actual_value\":2"));
    }

    #[tokio::test(flavor = "current_thread")]
    async fn repeated_queue_pressure_keeps_selected_datagram_transport_without_silent_fallback() {
        let mut cfg = config();
        cfg.datagram_enabled = true;
        cfg.datagram_rollout = H3DatagramRollout::Automatic;
        let mut controller = SessionController::new_gateway(
            ns_policy::EffectiveSessionPolicy::tcp_and_udp_defaults(1),
        );
        controller.accept_hello(ns_core::SessionId::random());
        let open = UdpFlowOpen {
            flow_id: 41,
            target: ns_wire::TargetAddress::Domain("resolver.example.net".to_owned()),
            target_port: 53,
            idle_timeout_ms: 5_000,
            flags: FlowFlags::new(0b0011).expect("prefer-datagram flags should be valid"),
            metadata: Vec::new(),
        };

        let (overflow_error, logs) = capture_logs_async(async move {
            let ok = select_h3_udp_flow_for_config(&mut controller, &open, &cfg, true)
                .expect("datagram selection should succeed before queue pressure");
            assert_eq!(ok.transport_mode, TransportMode::Datagram);

            let socket = H3DatagramSocket::with_runtime_config(H3DatagramRuntimeConfig {
                max_payload_bytes: 8,
                max_buffered_bytes: 8,
                max_buffered_datagrams: 8,
                max_buffered_datagrams_per_flow: 8,
            })
            .expect("queue-pressure runtime config should be valid");
            socket
                .send(UdpDatagram {
                    flow_id: open.flow_id,
                    flags: ns_wire::DatagramFlags::new(0)
                        .expect("zero datagram flags should be valid"),
                    payload: b"pressure".to_vec(),
                })
                .await
                .expect("first datagram should fit queue pressure budget");
            let first_error = socket
                .send(UdpDatagram {
                    flow_id: open.flow_id,
                    flags: ns_wire::DatagramFlags::new(0)
                        .expect("zero datagram flags should be valid"),
                    payload: b"x".to_vec(),
                })
                .await
                .expect_err("queue pressure should fail closed without changing selection");
            assert_eq!(first_error.kind, TransportErrorKind::Backpressure);
            let drained_once = socket.drain_outbound();
            assert_eq!(drained_once.len(), 1);
            assert_eq!(drained_once[0].payload, b"pressure");
            socket
                .send(UdpDatagram {
                    flow_id: open.flow_id,
                    flags: ns_wire::DatagramFlags::new(0)
                        .expect("zero datagram flags should be valid"),
                    payload: b"pressure".to_vec(),
                })
                .await
                .expect("queue should recover after the first drain");
            let second_error = socket
                .send(UdpDatagram {
                    flow_id: open.flow_id,
                    flags: ns_wire::DatagramFlags::new(0)
                        .expect("zero datagram flags should be valid"),
                    payload: b"x".to_vec(),
                })
                .await
                .expect_err("repeated queue pressure should stay fail closed");
            assert_eq!(second_error.kind, TransportErrorKind::Backpressure);
            let drained_twice = socket.drain_outbound();
            assert_eq!(drained_twice.len(), 1);
            assert_eq!(drained_twice[0].payload, b"pressure");
            socket
                .send(UdpDatagram {
                    flow_id: open.flow_id,
                    flags: ns_wire::DatagramFlags::new(0)
                        .expect("zero datagram flags should be valid"),
                    payload: b"again".to_vec(),
                })
                .await
                .expect("queue should remain recoverable after repeated pressure");
            let drained_thrice = socket.drain_outbound();
            assert_eq!(drained_thrice.len(), 1);
            assert_eq!(drained_thrice[0].payload, b"again");
            socket
                .send(UdpDatagram {
                    flow_id: open.flow_id,
                    flags: ns_wire::DatagramFlags::new(0)
                        .expect("zero datagram flags should be valid"),
                    payload: b"pressure".to_vec(),
                })
                .await
                .expect("queue should accept a third datagram cycle after recovery");
            let third_backpressure = socket
                .send(UdpDatagram {
                    flow_id: open.flow_id,
                    flags: ns_wire::DatagramFlags::new(0)
                        .expect("zero datagram flags should be valid"),
                    payload: b"x".to_vec(),
                })
                .await
                .expect_err("third queue pressure cycle should also stay fail closed");
            assert_eq!(third_backpressure.kind, TransportErrorKind::Backpressure);
            let drained_fourth = socket.drain_outbound();
            assert_eq!(drained_fourth.len(), 1);
            assert_eq!(drained_fourth[0].payload, b"pressure");
            third_backpressure
        })
        .await;

        assert_eq!(overflow_error.kind, TransportErrorKind::Backpressure);
        assert!(logs.contains("\"event_name\":\"verta.carrier.datagram.selection\""));
        assert!(logs.contains("\"selection\":\"datagram\""));
        assert!(!logs.contains("\"selection\":\"stream_fallback\""));
        assert!(logs.contains("\"limit_name\":\"max_buffered_datagram_bytes\""));
        assert!(logs.contains("\"limit_value\":8"));
        assert!(logs.contains("\"actual_value\":9"));
        assert_eq!(
            logs.matches("\"reason\":\"udp_datagram_queue_full\"")
                .count(),
            3
        );
    }

    #[tokio::test(flavor = "current_thread")]
    async fn canary_rollout_uses_stream_fallback_without_hiding_carrier_availability() {
        let mut cfg = config();
        cfg.datagram_enabled = true;
        cfg.datagram_rollout = H3DatagramRollout::Canary;
        let mut controller = SessionController::new_gateway(
            ns_policy::EffectiveSessionPolicy::tcp_and_udp_defaults(1),
        );
        controller.accept_hello(ns_core::SessionId::random());
        let open = UdpFlowOpen {
            flow_id: 9,
            target: ns_wire::TargetAddress::Domain("resolver.example.net".to_owned()),
            target_port: 53,
            idle_timeout_ms: 5_000,
            flags: FlowFlags::new(0b0010).expect("fallback-only flags should be valid"),
            metadata: Vec::new(),
        };

        let (ok, logs) = capture_logs_async(async {
            select_h3_udp_flow_for_config(&mut controller, &open, &cfg, true)
                .expect("canary rollout should fall back for non-prefer-datagram flows")
        })
        .await;

        assert_eq!(ok.transport_mode, TransportMode::StreamFallback);
        assert!(logs.contains("\"event_name\":\"verta.carrier.datagram.selection\""));
        assert!(logs.contains("\"selection\":\"stream_fallback\""));
        assert!(logs.contains("\"datagram_mode\":\"available_and_enabled\""));
        assert!(logs.contains("\"carrier_available\":true"));
        assert!(logs.contains("\"fallback_allowed\":true"));
        assert!(logs.contains("\"rollout_stage\":\"canary\""));
    }

    #[derive(Default)]
    struct ScriptedRelayState {
        inbound: VecDeque<Option<Bytes>>,
        outbound: Vec<Bytes>,
        carrier_finished: bool,
    }

    #[derive(Clone, Default)]
    struct ScriptedRelay {
        state: Arc<Mutex<ScriptedRelayState>>,
        notify: Arc<Notify>,
    }

    impl ScriptedRelay {
        fn push_inbound(&self, chunk: Bytes) {
            self.state
                .lock()
                .expect("scripted relay state poisoned")
                .inbound
                .push_back(Some(chunk));
            self.notify.notify_waiters();
        }

        fn finish_inbound(&self) {
            self.state
                .lock()
                .expect("scripted relay state poisoned")
                .inbound
                .push_back(None);
            self.notify.notify_waiters();
        }

        fn take_outbound(&self) -> Vec<Bytes> {
            self.state
                .lock()
                .expect("scripted relay state poisoned")
                .outbound
                .drain(..)
                .collect()
        }

        fn carrier_finished(&self) -> bool {
            self.state
                .lock()
                .expect("scripted relay state poisoned")
                .carrier_finished
        }
    }

    #[async_trait]
    impl RelayStreamIo for ScriptedRelay {
        async fn write_preamble(&mut self, _frame: &Frame) -> Result<(), TransportError> {
            Err(TransportError {
                kind: TransportErrorKind::Unsupported,
                message: "scripted relay does not support preambles".to_owned(),
            })
        }

        async fn read_preamble(&mut self) -> Result<Frame, TransportError> {
            Err(TransportError {
                kind: TransportErrorKind::Unsupported,
                message: "scripted relay does not support preambles".to_owned(),
            })
        }

        async fn send_raw(&mut self, chunk: Bytes) -> Result<(), TransportError> {
            self.state
                .lock()
                .expect("scripted relay state poisoned")
                .outbound
                .push(chunk);
            Ok(())
        }

        async fn recv_raw(&mut self) -> Result<Option<Bytes>, TransportError> {
            loop {
                if let Some(next) = self
                    .state
                    .lock()
                    .expect("scripted relay state poisoned")
                    .inbound
                    .pop_front()
                {
                    return Ok(next);
                }
                self.notify.notified().await;
            }
        }

        async fn finish_raw(&mut self) -> Result<(), TransportError> {
            self.state
                .lock()
                .expect("scripted relay state poisoned")
                .carrier_finished = true;
            Ok(())
        }
    }

    fn relay_runtime_config() -> H3RelayRuntimeConfig {
        H3RelayRuntimeConfig {
            max_raw_prebuffer_bytes: 64,
            idle_timeout_ms: 50,
            io_buffer_bytes: 32,
        }
    }

    #[tokio::test]
    async fn relay_runtime_keeps_the_first_clean_close_reason_when_client_finishes_first() {
        let scripted = ScriptedRelay::default();
        scripted.push_inbound(Bytes::from_static(b"verta"));
        scripted.finish_inbound();
        let observer = scripted.clone();
        let mut relay = scripted;
        let (upstream, mut peer) = duplex(128);

        let peer_task = tokio::spawn(async move {
            let mut observed = Vec::new();
            peer.read_to_end(&mut observed)
                .await
                .expect("peer should read the forwarded client payload");
            observed
        });

        let outcome = forward_raw_tcp_relay(7, &mut relay, upstream, &relay_runtime_config())
            .await
            .expect("relay runtime should complete after client EOF");

        assert_eq!(outcome.close_reason, H3RelayCloseReason::ClientFinished);
        assert!(outcome.client_half_closed);
        assert!(outcome.upstream_half_closed);
        assert_eq!(outcome.bytes_from_client, 5);
        assert_eq!(peer_task.await.expect("peer task should finish"), b"verta");
        assert!(observer.carrier_finished());
    }

    #[tokio::test]
    async fn relay_runtime_keeps_the_first_clean_close_reason_when_upstream_finishes_first() {
        let scripted = ScriptedRelay::default();
        let observer = scripted.clone();
        let finisher = scripted.clone();
        let mut relay = scripted;
        let (upstream, mut peer) = duplex(128);

        let peer_task = tokio::spawn(async move {
            peer.write_all(b"reply")
                .await
                .expect("peer should write an upstream payload");
            peer.shutdown()
                .await
                .expect("peer should half-close after writing");
        });
        let finish_task = tokio::spawn(async move {
            sleep(Duration::from_millis(10)).await;
            finisher.finish_inbound();
        });

        let outcome = forward_raw_tcp_relay(11, &mut relay, upstream, &relay_runtime_config())
            .await
            .expect("relay runtime should complete after upstream EOF");

        assert_eq!(outcome.close_reason, H3RelayCloseReason::UpstreamFinished);
        assert!(outcome.client_half_closed);
        assert!(outcome.upstream_half_closed);
        let outbound = observer
            .take_outbound()
            .into_iter()
            .flat_map(|chunk| chunk.to_vec())
            .collect::<Vec<_>>();
        assert_eq!(outbound, b"reply");
        assert!(observer.carrier_finished());
        peer_task.await.expect("peer task should finish");
        finish_task.await.expect("finish task should finish");
    }

    #[tokio::test]
    async fn relay_runtime_times_out_when_both_sides_go_idle() {
        let mut relay = ScriptedRelay::default();
        let (upstream, _peer) = duplex(128);

        let error = forward_raw_tcp_relay(13, &mut relay, upstream, &relay_runtime_config())
            .await
            .expect_err("relay runtime should time out when neither side makes progress");
        assert_eq!(error.kind, TransportErrorKind::TimedOut);
    }

    #[tokio::test]
    async fn relay_runtime_rejects_oversized_client_prebuffer_chunks() {
        let scripted = ScriptedRelay::default();
        scripted.push_inbound(Bytes::from(vec![0_u8; 65]));
        let mut relay = scripted;
        let (upstream, _peer) = duplex(128);

        let error = forward_raw_tcp_relay(17, &mut relay, upstream, &relay_runtime_config())
            .await
            .expect_err("relay runtime should reject oversized client prebuffer chunks");
        assert_eq!(error.kind, TransportErrorKind::Backpressure);
    }

    #[test]
    fn relay_close_reasons_keep_stable_observability_strings() {
        assert_eq!(
            H3RelayCloseReason::ClientFinished.as_str(),
            "client_finished"
        );
        assert_eq!(
            H3RelayCloseReason::UpstreamFinished.as_str(),
            "upstream_finished"
        );
        assert_eq!(H3RelayCloseReason::IdleTimeout.as_str(), "idle_timeout");
        assert_eq!(
            H3RelayCloseReason::PrebufferOverflow.as_str(),
            "prebuffer_overflow"
        );
    }
}
