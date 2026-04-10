//! Unified session object for the Beep protocol.
//!
//! Combines cipher, mux, rekey, and frame routing into a single
//! orchestrator that drives encrypted, multiplexed I/O.
//!
//! # Usage
//! ```text
//! // After handshake:
//! let session = SessionCore::new(session_keys, is_initiator);
//!
//! // Open a stream and send data:
//! let sid = session.open_stream();
//! let encrypted = session.seal_stream(sid, b"hello", false)?;
//!
//! // Receive and process:
//! let action = session.process_incoming(encrypted_frame)?;
//! ```

use beep_core_types::FrameType;

use crate::cipher::{CipherError, TrafficClass, TrafficKeyPair};
use crate::codec::{self, RawFrame};
use crate::frame_router::{self, FrameAction, FrameRouteError};
use crate::key_schedule::SessionKeys;
use crate::metrics::SessionMetrics;
use crate::mux::{
    DatagramFrame, FlowCreditFrame, MuxError, MuxState, StreamFrame, StreamId,
};
use crate::rekey::{
    EpochKeys, KeyUpdateFrame, RekeyError, RekeyState, SessionCloseFrame,
};

/// Errors from the session orchestrator.
#[derive(Debug, thiserror::Error)]
pub enum SessionError {
    #[error("cipher error: {0}")]
    Cipher(#[from] CipherError),
    #[error("mux error: {0}")]
    Mux(#[from] MuxError),
    #[error("rekey error: {0}")]
    Rekey(#[from] RekeyError),
    #[error("frame route error: {0}")]
    Route(#[from] FrameRouteError),
    #[error("codec error: {0}")]
    Codec(#[from] crate::codec::CodecError),
    #[error("session closed: code={code}, reason={reason}")]
    Closed { code: u32, reason: String },
    #[error("invalid frame payload")]
    InvalidPayload(String),
}

/// The unified session orchestrator.
///
/// Owns all per-session state after the handshake completes.
pub struct SessionCore {
    /// Control channel key pair (for KEY_UPDATE, SESSION_CLOSE, etc.)
    control: TrafficKeyPair,
    /// Stream traffic key pair
    stream: TrafficKeyPair,
    /// Datagram traffic key pair
    datagram: TrafficKeyPair,
    /// Multiplexer state
    mux: MuxState,
    /// Rekey state machine
    rekey: RekeyState,
    /// Session metrics
    metrics: SessionMetrics,
    /// Whether this session has been closed
    closed: bool,
}

/// Outgoing encrypted frame ready for transport.
#[derive(Debug)]
pub struct SealedFrame {
    pub data: Vec<u8>,
}

/// Result of processing an incoming frame.
#[derive(Debug)]
pub enum IncomingAction {
    /// Stream data received.
    StreamData { stream_id: StreamId, frame: StreamFrame },
    /// A new remote stream was opened.
    StreamOpened { stream_id: StreamId },
    /// A remote stream was closed.
    StreamClosed { stream_id: StreamId },
    /// A datagram was received.
    Datagram(DatagramFrame),
    /// Flow credit update.
    CreditUpdate { stream_id: u32, credit: u64 },
    /// Rekey completed — session is back to Stable on new epoch.
    Rekeyed { epoch: u64 },
    /// A resumption ticket was received (sealed blob).
    TicketReceived(Vec<u8>),
    /// Session was closed by peer.
    Closed { code: u32, reason: String },
    /// Policy frame received (route set or DNS config).
    PolicyReceived { frame_type: FrameType, payload: Vec<u8> },
    /// Telemetry data (informational).
    Telemetry { frame_type: FrameType, payload: Vec<u8> },
    /// Frame was silently ignored.
    Ignored,
}

impl SessionCore {
    /// Create a new session from handshake-derived keys.
    pub fn new(keys: &SessionKeys, is_initiator: bool) -> Self {
        Self {
            control: TrafficKeyPair::new(keys.control_key, keys.control_iv, TrafficClass::Control),
            stream: TrafficKeyPair::new(keys.stream_key, keys.stream_iv, TrafficClass::Stream),
            datagram: TrafficKeyPair::new(keys.datagram_key, keys.datagram_iv, TrafficClass::Datagram),
            mux: MuxState::new(is_initiator),
            rekey: RekeyState::new(keys),
            metrics: SessionMetrics::new(),
            closed: false,
        }
    }

    /// Current key epoch.
    pub fn epoch(&self) -> u64 {
        self.rekey.epoch()
    }

    /// Whether the session is closed.
    pub fn is_closed(&self) -> bool {
        self.closed
    }

    /// Number of active streams.
    pub fn active_streams(&self) -> usize {
        self.mux.active_stream_count()
    }

    /// Access session metrics.
    pub fn metrics(&self) -> &SessionMetrics {
        &self.metrics
    }

    // ── Stream operations ───────────────────────────────────────────────

    /// Open a new locally-initiated stream.
    pub fn open_stream(&mut self) -> StreamId {
        self.mux.open_stream()
    }

    /// Seal a stream data frame. Returns encrypted frame bytes for transport.
    pub fn seal_stream(
        &mut self,
        stream_id: StreamId,
        data: &[u8],
        fin: bool,
    ) -> Result<SealedFrame, SessionError> {
        let offset = self.mux.stream(stream_id)
            .map(|s| s.bytes_sent)
            .unwrap_or(0);

        self.mux.record_send(stream_id, data.len() as u64)?;

        let sf = StreamFrame {
            stream_id: stream_id.0,
            offset,
            fin,
            data: data.to_vec(),
        };
        let mut payload = Vec::new();
        sf.encode(&mut payload).map_err(|e| SessionError::InvalidPayload(e.to_string()))?;

        self.seal_frame(FrameType::STREAM_DATA, &payload, TrafficClass::Stream)
    }

    /// Seal a datagram frame.
    pub fn seal_datagram(
        &mut self,
        class_id: u16,
        data: &[u8],
    ) -> Result<SealedFrame, SessionError> {
        let df = DatagramFrame {
            class_id,
            data: data.to_vec(),
        };
        let mut payload = Vec::new();
        df.encode(&mut payload).map_err(|e| SessionError::InvalidPayload(e.to_string()))?;

        self.seal_frame(FrameType::DATAGRAM_CLASS, &payload, TrafficClass::Datagram)
    }

    /// Close local half of a stream and send STREAM_CLOSE.
    pub fn close_stream(&mut self, stream_id: StreamId) -> Result<SealedFrame, SessionError> {
        self.mux.close_local(stream_id)?;
        // Encode stream_id as payload
        let mut payload = Vec::new();
        crate::varint::encode(stream_id.0 as u64, &mut payload)
            .map_err(|e| SessionError::InvalidPayload(e.to_string()))?;
        self.seal_frame(FrameType::STREAM_CLOSE, &payload, TrafficClass::Control)
    }

    // ── Rekey ───────────────────────────────────────────────────────────

    /// Initiate a rekey. Returns the encrypted KEY_UPDATE frame.
    ///
    /// After sending this frame and before sending any more traffic,
    /// call [`complete_initiated_rekey`](Self::complete_initiated_rekey)
    /// to switch to the new epoch keys locally.
    pub fn initiate_rekey(&mut self) -> Result<SealedFrame, SessionError> {
        let new_epoch = self.rekey.initiate()?;
        let kuf = KeyUpdateFrame { new_epoch };
        let mut payload = Vec::new();
        kuf.encode(&mut payload);
        self.seal_frame(FrameType::KEY_UPDATE, &payload, TrafficClass::Control)
    }

    /// Complete our side of a locally-initiated rekey.
    ///
    /// Derives the new epoch keys and rotates all cipher state.
    /// Must be called after [`initiate_rekey`](Self::initiate_rekey)
    /// and before sending any more frames.
    pub fn complete_initiated_rekey(&mut self) -> Result<u64, SessionError> {
        let epoch_keys = self.rekey.complete()?;
        self.apply_new_epoch_keys(&epoch_keys);
        let epoch = self.rekey.epoch();
        self.metrics.record_rekey(epoch);
        Ok(epoch)
    }

    // ── Telemetry ───────────────────────────────────────────────────────

    /// Seal a `HEALTH_SUMMARY` telemetry frame from current metrics.
    pub fn seal_health_summary(&mut self) -> Result<SealedFrame, SessionError> {
        let hs = self.metrics.to_health_summary();
        let mut payload = Vec::new();
        hs.encode(&mut payload);
        self.seal_frame(FrameType::HEALTH_SUMMARY, &payload, TrafficClass::Control)
    }

    /// Seal an `ERROR_REPORT` telemetry frame.
    pub fn seal_error_report(
        &mut self,
        error_code: u32,
        timestamp_unix: u64,
        context: &[u8],
    ) -> Result<SealedFrame, SessionError> {
        let er = crate::telemetry::ErrorReportFrame {
            error_code,
            timestamp_unix,
            context: context.to_vec(),
        };
        let mut payload = Vec::new();
        er.encode(&mut payload);
        self.seal_frame(FrameType::ERROR_REPORT, &payload, TrafficClass::Control)
    }

    // ── Policy ──────────────────────────────────────────────────────────

    /// Seal a `ROUTE_SET` policy frame.
    pub fn seal_route_set(
        &mut self,
        route_set: &crate::policy_frames::RouteSetFrame,
    ) -> Result<SealedFrame, SessionError> {
        let mut payload = Vec::new();
        route_set.encode(&mut payload);
        self.seal_frame(FrameType::ROUTE_SET, &payload, TrafficClass::Control)
    }

    /// Seal a `DNS_CONFIG` policy frame.
    pub fn seal_dns_config(
        &mut self,
        dns_config: &crate::policy_frames::DnsConfigFrame,
    ) -> Result<SealedFrame, SessionError> {
        let mut payload = Vec::new();
        dns_config.encode(&mut payload);
        self.seal_frame(FrameType::DNS_CONFIG, &payload, TrafficClass::Control)
    }

    // ── Close ───────────────────────────────────────────────────────────

    /// Close the session. Returns the encrypted SESSION_CLOSE frame.
    pub fn close(
        &mut self,
        error_code: u32,
        reason: &str,
    ) -> Result<SealedFrame, SessionError> {
        let scf = SessionCloseFrame {
            error_code,
            reason: reason.as_bytes().to_vec(),
        };
        let mut payload = Vec::new();
        scf.encode(&mut payload);
        self.closed = true;
        self.seal_frame(FrameType::SESSION_CLOSE, &payload, TrafficClass::Control)
    }

    // ── Incoming frame processing ───────────────────────────────────────

    /// Process an incoming encrypted frame from the transport.
    ///
    /// Decrypts, routes, and applies the frame to session state.
    pub fn process_incoming(&mut self, data: &[u8]) -> Result<IncomingAction, SessionError> {
        // Decode the outer frame header (unencrypted: type + flags + length)
        let (frame, _) = codec::decode_frame(data)?;
        let frame_type = frame.frame_type;

        // Determine traffic class for decryption
        let tc = classify_frame_type(frame_type);
        let plaintext = self.open_frame(&frame.payload, tc)?;

        self.metrics.record_recv(data.len() as u64);

        // Route the decrypted payload
        let action = frame_router::route_frame(frame_type, plaintext)?;

        match action {
            FrameAction::StreamData(payload) => {
                let (sf, _) = StreamFrame::decode(&payload)
                    .map_err(|e| SessionError::InvalidPayload(e.to_string()))?;
                let sid = StreamId(sf.stream_id);
                // Accept remote stream if new
                if self.mux.stream(sid).is_none() {
                    self.mux.accept_stream(sid)
                        .map_err(SessionError::Mux)?;
                }
                self.mux.record_recv(sid, sf.data.len() as u64)?;
                if sf.fin {
                    self.mux.close_remote(sid)?;
                }
                Ok(IncomingAction::StreamData { stream_id: sid, frame: sf })
            }

            FrameAction::StreamOpen(payload) => {
                let (sid_val, _) = crate::varint::decode(&payload)
                    .map_err(|e| SessionError::InvalidPayload(e.to_string()))?;
                let sid = StreamId(sid_val as u32);
                self.mux.accept_stream(sid)?;
                Ok(IncomingAction::StreamOpened { stream_id: sid })
            }

            FrameAction::StreamClose(payload) => {
                let (sid_val, _) = crate::varint::decode(&payload)
                    .map_err(|e| SessionError::InvalidPayload(e.to_string()))?;
                let sid = StreamId(sid_val as u32);
                self.mux.close_remote(sid)?;
                Ok(IncomingAction::StreamClosed { stream_id: sid })
            }

            FrameAction::FlowCredit(payload) => {
                let (fc, _) = FlowCreditFrame::decode(&payload)
                    .map_err(|e| SessionError::InvalidPayload(e.to_string()))?;
                if fc.stream_id == 0 {
                    self.mux.add_conn_send_credit(fc.credit);
                } else {
                    self.mux.add_send_credit(StreamId(fc.stream_id), fc.credit)?;
                }
                Ok(IncomingAction::CreditUpdate {
                    stream_id: fc.stream_id,
                    credit: fc.credit,
                })
            }

            FrameAction::Datagram(payload) => {
                let (df, _) = DatagramFrame::decode(&payload)
                    .map_err(|e| SessionError::InvalidPayload(e.to_string()))?;
                Ok(IncomingAction::Datagram(df))
            }

            FrameAction::KeyUpdate(payload) => {
                let kuf = KeyUpdateFrame::decode(&payload)
                    .map_err(|e| SessionError::InvalidPayload(e.to_string()))?;
                self.rekey.process_peer_update(kuf.new_epoch)?;
                let epoch_keys = self.rekey.complete()?;
                self.apply_new_epoch_keys(&epoch_keys);
                let epoch = self.rekey.epoch();
                self.metrics.record_rekey(epoch);
                Ok(IncomingAction::Rekeyed { epoch })
            }

            FrameAction::SessionClose(payload) => {
                let scf = SessionCloseFrame::decode(&payload)
                    .map_err(|e| SessionError::InvalidPayload(e.to_string()))?;
                self.closed = true;
                Ok(IncomingAction::Closed {
                    code: scf.error_code,
                    reason: String::from_utf8_lossy(&scf.reason).to_string(),
                })
            }

            FrameAction::TicketIssue(payload) => {
                Ok(IncomingAction::TicketReceived(payload))
            }

            FrameAction::Policy { frame_type, payload } => {
                Ok(IncomingAction::PolicyReceived { frame_type, payload })
            }

            FrameAction::Telemetry { frame_type, payload } => {
                Ok(IncomingAction::Telemetry { frame_type, payload })
            }

            FrameAction::Ignored(_) => {
                Ok(IncomingAction::Ignored)
            }
        }
    }

    /// Seal an arbitrary control-class frame.
    ///
    /// Used by the driver to send frames that don't have dedicated methods
    /// (e.g. `TICKET_ISSUE`).
    pub fn seal_control_frame(
        &mut self,
        frame_type: FrameType,
        plaintext: &[u8],
    ) -> Result<SealedFrame, SessionError> {
        self.seal_frame(frame_type, plaintext, TrafficClass::Control)
    }

    // ── Internal ────────────────────────────────────────────────────────

    fn seal_frame(
        &mut self,
        frame_type: FrameType,
        plaintext: &[u8],
        class: TrafficClass,
    ) -> Result<SealedFrame, SessionError> {
        let sender = match class {
            TrafficClass::Control => &mut self.control.send,
            TrafficClass::Stream => &mut self.stream.send,
            TrafficClass::Datagram => &mut self.datagram.send,
        };
        let ciphertext = sender.seal(plaintext)?;

        let frame = RawFrame {
            frame_type,
            flags: 0,
            payload: ciphertext,
        };
        let mut buf = Vec::new();
        codec::encode_frame(&frame, &mut buf)?;

        self.metrics.record_send(buf.len() as u64);
        Ok(SealedFrame { data: buf })
    }

    fn open_frame(
        &mut self,
        ciphertext: &[u8],
        class: TrafficClass,
    ) -> Result<Vec<u8>, SessionError> {
        let receiver = match class {
            TrafficClass::Control => &mut self.control.recv,
            TrafficClass::Stream => &mut self.stream.recv,
            TrafficClass::Datagram => &mut self.datagram.recv,
        };
        Ok(receiver.open(ciphertext)?)
    }

    fn apply_new_epoch_keys(&mut self, keys: &EpochKeys) {
        self.control.send.rekey(keys.control_key, keys.control_iv);
        self.control.recv.rekey(keys.control_key, keys.control_iv);
        self.stream.send.rekey(keys.stream_key, keys.stream_iv);
        self.stream.recv.rekey(keys.stream_key, keys.stream_iv);
        self.datagram.send.rekey(keys.datagram_key, keys.datagram_iv);
        self.datagram.recv.rekey(keys.datagram_key, keys.datagram_iv);
    }
}

/// Classify a frame type into a traffic class for AEAD key selection.
fn classify_frame_type(ft: FrameType) -> TrafficClass {
    match ft {
        FrameType::STREAM_DATA | FrameType::STREAM_OPEN | FrameType::STREAM_CLOSE => {
            TrafficClass::Stream
        }
        FrameType::DATAGRAM_CLASS | FrameType::DATAGRAM_DROP_NOTICE => {
            TrafficClass::Datagram
        }
        // Everything else (session management, flow control, telemetry) uses control
        _ => TrafficClass::Control,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::key_schedule::SessionKeys;

    fn test_keys() -> SessionKeys {
        SessionKeys {
            session_master_secret: [0x10u8; 32],
            control_key: [0x20u8; 32],
            control_iv: [0x30u8; 12],
            stream_key: [0x40u8; 32],
            stream_iv: [0x50u8; 12],
            datagram_key: [0x60u8; 32],
            datagram_iv: [0x70u8; 12],
            resumption_secret: [0x80u8; 32],
        }
    }

    #[test]
    fn stream_data_roundtrip() {
        let keys = test_keys();
        let mut client = SessionCore::new(&keys, true);
        let mut server = SessionCore::new(&keys, false);

        let sid = client.open_stream();
        let sealed = client.seal_stream(sid, b"hello from client", false).unwrap();

        let action = server.process_incoming(&sealed.data).unwrap();
        match action {
            IncomingAction::StreamData { stream_id, frame } => {
                assert_eq!(frame.data, b"hello from client");
                assert!(!frame.fin);
                assert_eq!(stream_id.0, sid.0);
            }
            other => panic!("expected StreamData, got {other:?}"),
        }
    }

    #[test]
    fn datagram_roundtrip() {
        let keys = test_keys();
        let mut client = SessionCore::new(&keys, true);
        let mut server = SessionCore::new(&keys, false);

        let sealed = client.seal_datagram(7, b"udp-like data").unwrap();
        let action = server.process_incoming(&sealed.data).unwrap();
        match action {
            IncomingAction::Datagram(df) => {
                assert_eq!(df.class_id, 7);
                assert_eq!(df.data, b"udp-like data");
            }
            other => panic!("expected Datagram, got {other:?}"),
        }
    }

    #[test]
    fn rekey_via_session() {
        let keys = test_keys();
        let mut client = SessionCore::new(&keys, true);
        let mut server = SessionCore::new(&keys, false);

        assert_eq!(client.epoch(), 0);
        assert_eq!(server.epoch(), 0);

        // Client initiates rekey
        let ku_frame = client.initiate_rekey().unwrap();
        // Client completes its side
        client.complete_initiated_rekey().unwrap();

        // Server processes KEY_UPDATE
        let action = server.process_incoming(&ku_frame.data).unwrap();
        assert!(matches!(action, IncomingAction::Rekeyed { epoch: 1 }));

        assert_eq!(client.epoch(), 1);
        assert_eq!(server.epoch(), 1);

        // Post-rekey traffic works
        let sid = client.open_stream();
        let sealed = client.seal_stream(sid, b"post-rekey", false).unwrap();
        let action = server.process_incoming(&sealed.data).unwrap();
        match action {
            IncomingAction::StreamData { frame, .. } => {
                assert_eq!(frame.data, b"post-rekey");
            }
            other => panic!("expected StreamData, got {other:?}"),
        }
    }

    #[test]
    fn session_close() {
        let keys = test_keys();
        let mut client = SessionCore::new(&keys, true);
        let mut server = SessionCore::new(&keys, false);

        let close_frame = client.close(0, "goodbye").unwrap();
        assert!(client.is_closed());

        let action = server.process_incoming(&close_frame.data).unwrap();
        match action {
            IncomingAction::Closed { code, reason } => {
                assert_eq!(code, 0);
                assert_eq!(reason, "goodbye");
            }
            other => panic!("expected Closed, got {other:?}"),
        }
        assert!(server.is_closed());
    }

    #[test]
    fn stream_fin_closes_remote() {
        let keys = test_keys();
        let mut client = SessionCore::new(&keys, true);
        let mut server = SessionCore::new(&keys, false);

        let sid = client.open_stream();
        let sealed = client.seal_stream(sid, b"last", true).unwrap();

        let action = server.process_incoming(&sealed.data).unwrap();
        match action {
            IncomingAction::StreamData { stream_id, frame } => {
                assert!(frame.fin);
                // Stream should be half-closed on server side
                let info = server.mux.stream(stream_id).unwrap();
                assert_eq!(info.state, crate::mux::StreamState::HalfClosedRemote);
            }
            other => panic!("expected StreamData, got {other:?}"),
        }
    }

    #[test]
    fn multiple_streams_independent() {
        let keys = test_keys();
        let mut client = SessionCore::new(&keys, true);
        let mut server = SessionCore::new(&keys, false);

        let s1 = client.open_stream();
        let s2 = client.open_stream();

        let f1 = client.seal_stream(s1, b"stream1", false).unwrap();
        let f2 = client.seal_stream(s2, b"stream2", false).unwrap();

        let a1 = server.process_incoming(&f1.data).unwrap();
        let a2 = server.process_incoming(&f2.data).unwrap();

        match (a1, a2) {
            (IncomingAction::StreamData { frame: f1, .. }, IncomingAction::StreamData { frame: f2, .. }) => {
                assert_eq!(f1.data, b"stream1");
                assert_eq!(f2.data, b"stream2");
            }
            _ => panic!("expected two StreamData actions"),
        }

        assert_eq!(server.active_streams(), 2);
    }

    #[test]
    fn wrong_keys_cannot_decrypt() {
        let keys = test_keys();
        let other_keys = SessionKeys {
            control_key: [0xFF; 32],
            stream_key: [0xFE; 32],
            ..keys
        };
        let mut client = SessionCore::new(&keys, true);
        let mut wrong_server = SessionCore::new(&other_keys, false);

        let sid = client.open_stream();
        let sealed = client.seal_stream(sid, b"secret", false).unwrap();
        let result = wrong_server.process_incoming(&sealed.data);
        assert!(result.is_err());
    }
}
