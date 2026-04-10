//! Transport abstraction for the Beep protocol.
//!
//! This crate defines the [`CoverConn`] trait that all transport implementations
//! must satisfy. The session core communicates through this trait without knowing
//! whether the underlying transport is HTTP/2, HTTP/3, or native-fast.

use bytes::Bytes;

/// Capabilities of a transport connection.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct TransportCapabilities {
    /// Whether this transport supports reliable streams.
    pub supports_streams: bool,
    /// Whether this transport supports unreliable datagrams.
    pub supports_datagrams: bool,
    /// Whether this transport supports connection migration.
    pub supports_migration: bool,
}

/// Transport-level errors.
#[derive(Debug, thiserror::Error)]
pub enum TransportError {
    #[error("connection closed")]
    ConnectionClosed,
    #[error("I/O error: {0}")]
    Io(String),
    #[error("H2 error: {0}")]
    H2(String),
    #[error("QUIC error: {0}")]
    Quic(String),
    #[error("TLS error: {0}")]
    Tls(String),
    #[error("transport timeout")]
    Timeout,
}

/// A cover transport connection that provides byte-chunk I/O.
///
/// The session core sends and receives Beep frames as serialized byte chunks
/// through this interface. The transport handles the outer protocol framing
/// (H2 DATA frames, QUIC streams, etc.) transparently.
///
/// # Contract
/// - `send()` must deliver the entire chunk or fail.
/// - `recv()` returns `None` on clean connection close.
/// - `transport_binding()` must return a stable digest derived from
///   the outer TLS channel binding material.
pub trait CoverConn: Send {
    /// Send a chunk of bytes over the transport.
    fn send(
        &mut self,
        data: Bytes,
    ) -> impl std::future::Future<Output = Result<(), TransportError>> + Send;

    /// Receive the next chunk of bytes. Returns `None` on clean close.
    fn recv(
        &mut self,
    ) -> impl std::future::Future<Output = Result<Option<Bytes>, TransportError>> + Send;

    /// Transport binding material (32-byte SHA-256 digest of TLS channel binding).
    fn transport_binding(&self) -> [u8; 32];

    /// Transport capabilities.
    fn capabilities(&self) -> TransportCapabilities;
}
