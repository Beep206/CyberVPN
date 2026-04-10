//! Async session driver that bridges `SessionCore` with `CoverConn`.
//!
//! Provides the primary consumer-facing API for the Beep protocol.

use beep_core::key_schedule::SessionKeys;
use beep_core::metrics::SessionMetrics;
use beep_core::mux::{DatagramFrame, StreamFrame, StreamId};
use beep_core::policy_frames::{DnsConfigFrame, RouteSetFrame};
use beep_core::session_core::{IncomingAction, SessionCore};
use beep_core_types::FrameType;
use beep_transport::CoverConn;
use bytes::Bytes;

/// Errors from the async session driver.
#[derive(Debug, thiserror::Error)]
pub enum DriverError {
    /// Session core error.
    #[error("session error: {0}")]
    Session(#[from] beep_core::session_core::SessionError),

    /// Transport I/O error.
    #[error("transport error: {0}")]
    Transport(#[from] beep_transport::TransportError),

    /// Connection closed by peer (EOF).
    #[error("connection closed by peer")]
    PeerClosed,

    /// Session is already closed.
    #[error("session is already closed")]
    AlreadyClosed,
}

/// Result of receiving a frame from the peer.
#[derive(Debug)]
pub enum RecvEvent {
    /// Stream data received.
    StreamData {
        stream_id: StreamId,
        frame: StreamFrame,
    },
    /// A remote stream was opened.
    StreamOpened { stream_id: StreamId },
    /// A remote stream was closed.
    StreamClosed { stream_id: StreamId },
    /// Datagram received.
    Datagram(DatagramFrame),
    /// Flow credit update.
    CreditUpdate { stream_id: u32, credit: u64 },
    /// Rekey completed.
    Rekeyed { epoch: u64 },
    /// Resumption ticket received.
    TicketReceived(Vec<u8>),
    /// Policy frame received (ROUTE_SET or DNS_CONFIG).
    PolicyReceived {
        frame_type: FrameType,
        payload: Vec<u8>,
    },
    /// Telemetry frame received.
    Telemetry {
        frame_type: FrameType,
        payload: Vec<u8>,
    },
    /// Session was closed by peer.
    Closed { code: u32, reason: String },
}

/// Async session driver wrapping `SessionCore` and a `CoverConn`.
///
/// All operations encrypt/decrypt through `SessionCore` and send/receive
/// through the underlying `CoverConn` transport.
pub struct SessionDriver<C: CoverConn> {
    core: SessionCore,
    conn: C,
}

impl<C: CoverConn> SessionDriver<C> {
    /// Create a new driver from handshake-derived keys and a CoverConn.
    pub fn new(conn: C, keys: &SessionKeys, is_initiator: bool) -> Self {
        Self {
            core: SessionCore::new(keys, is_initiator),
            conn,
        }
    }

    /// Current key epoch.
    pub fn epoch(&self) -> u64 {
        self.core.epoch()
    }

    /// Whether the session is closed.
    pub fn is_closed(&self) -> bool {
        self.core.is_closed()
    }

    /// Number of active streams.
    pub fn active_streams(&self) -> usize {
        self.core.active_streams()
    }

    /// Access session metrics.
    pub fn metrics(&self) -> &SessionMetrics {
        self.core.metrics()
    }

    // ── Send operations ─────────────────────────────────────────────────

    /// Open a new stream.
    pub fn open_stream(&mut self) -> StreamId {
        self.core.open_stream()
    }

    /// Send stream data to the peer.
    pub async fn send_stream(
        &mut self,
        stream_id: StreamId,
        data: &[u8],
        fin: bool,
    ) -> Result<(), DriverError> {
        self.check_open()?;
        let sealed = self.core.seal_stream(stream_id, data, fin)?;
        self.conn.send(Bytes::from(sealed.data)).await?;
        Ok(())
    }

    /// Send a datagram to the peer.
    pub async fn send_datagram(
        &mut self,
        class_id: u16,
        data: &[u8],
    ) -> Result<(), DriverError> {
        self.check_open()?;
        let sealed = self.core.seal_datagram(class_id, data)?;
        self.conn.send(Bytes::from(sealed.data)).await?;
        Ok(())
    }

    /// Initiate a rekey: sends KEY_UPDATE and completes local key rotation.
    pub async fn send_rekey(&mut self) -> Result<u64, DriverError> {
        self.check_open()?;
        let sealed = self.core.initiate_rekey()?;
        self.conn.send(Bytes::from(sealed.data)).await?;
        let epoch = self.core.complete_initiated_rekey()?;
        tracing::info!(epoch, "local rekey completed");
        Ok(epoch)
    }

    /// Send a session close and mark the session as closed.
    pub async fn send_close(
        &mut self,
        error_code: u32,
        reason: &str,
    ) -> Result<(), DriverError> {
        let sealed = self.core.close(error_code, reason)?;
        self.conn.send(Bytes::from(sealed.data)).await?;
        tracing::info!(error_code, reason, "session closed by us");
        Ok(())
    }

    /// Send a resumption ticket to the peer (via TICKET_ISSUE frame).
    pub async fn send_ticket(&mut self, sealed_ticket: &[u8]) -> Result<(), DriverError> {
        self.check_open()?;
        let ticket_frame = beep_core::resumption::TicketIssueFrame {
            sealed_ticket: sealed_ticket.to_vec(),
        };
        let mut payload = Vec::new();
        ticket_frame.encode(&mut payload);
        let sealed = self.core.seal_control_frame(
            FrameType::TICKET_ISSUE,
            &payload,
        )?;
        self.conn.send(Bytes::from(sealed.data)).await?;
        Ok(())
    }

    /// Send a HEALTH_SUMMARY telemetry frame.
    pub async fn send_health_summary(&mut self) -> Result<(), DriverError> {
        self.check_open()?;
        let sealed = self.core.seal_health_summary()?;
        self.conn.send(Bytes::from(sealed.data)).await?;
        Ok(())
    }

    /// Send an ERROR_REPORT telemetry frame.
    pub async fn send_error_report(
        &mut self,
        error_code: u32,
        timestamp_unix: u64,
        context: &[u8],
    ) -> Result<(), DriverError> {
        self.check_open()?;
        let sealed = self.core.seal_error_report(error_code, timestamp_unix, context)?;
        self.conn.send(Bytes::from(sealed.data)).await?;
        Ok(())
    }

    /// Send a ROUTE_SET policy frame.
    pub async fn send_route_set(&mut self, routes: &RouteSetFrame) -> Result<(), DriverError> {
        self.check_open()?;
        let sealed = self.core.seal_route_set(routes)?;
        self.conn.send(Bytes::from(sealed.data)).await?;
        Ok(())
    }

    /// Send a DNS_CONFIG policy frame.
    pub async fn send_dns_config(&mut self, dns: &DnsConfigFrame) -> Result<(), DriverError> {
        self.check_open()?;
        let sealed = self.core.seal_dns_config(dns)?;
        self.conn.send(Bytes::from(sealed.data)).await?;
        Ok(())
    }

    // ── Receive ─────────────────────────────────────────────────────────

    /// Receive the next event from the peer.
    ///
    /// Reads from the transport, decrypts, and dispatches the frame.
    /// Returns `None` at EOF (transport closed).
    pub async fn recv(&mut self) -> Result<RecvEvent, DriverError> {
        let chunk = self
            .conn
            .recv()
            .await?
            .ok_or(DriverError::PeerClosed)?;

        let action = self.core.process_incoming(&chunk)?;

        let event = match action {
            IncomingAction::StreamData { stream_id, frame } => {
                RecvEvent::StreamData { stream_id, frame }
            }
            IncomingAction::StreamOpened { stream_id } => {
                RecvEvent::StreamOpened { stream_id }
            }
            IncomingAction::StreamClosed { stream_id } => {
                RecvEvent::StreamClosed { stream_id }
            }
            IncomingAction::Datagram(df) => RecvEvent::Datagram(df),
            IncomingAction::CreditUpdate { stream_id, credit } => {
                RecvEvent::CreditUpdate { stream_id, credit }
            }
            IncomingAction::Rekeyed { epoch } => {
                tracing::info!(epoch, "peer rekey processed");
                RecvEvent::Rekeyed { epoch }
            }
            IncomingAction::TicketReceived(data) => RecvEvent::TicketReceived(data),
            IncomingAction::PolicyReceived { frame_type, payload } => {
                RecvEvent::PolicyReceived { frame_type, payload }
            }
            IncomingAction::Closed { code, reason } => {
                tracing::info!(code, %reason, "session closed by peer");
                RecvEvent::Closed { code, reason }
            }
            IncomingAction::Telemetry { frame_type, payload } => {
                RecvEvent::Telemetry { frame_type, payload }
            }
            IncomingAction::Ignored => {
                // Ignorable frame — recurse to get next meaningful event.
                // In production you'd use a loop; here recursion is bounded
                // by the protocol's frame pacing.
                return Box::pin(self.recv()).await;
            }
        };

        Ok(event)
    }

    // ── Internal ────────────────────────────────────────────────────────

    fn check_open(&self) -> Result<(), DriverError> {
        if self.core.is_closed() {
            Err(DriverError::AlreadyClosed)
        } else {
            Ok(())
        }
    }
}
