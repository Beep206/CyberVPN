//! QUIC cover transport for the Beep protocol.
//!
//! Implements [`CoverConn`] over a QUIC connection via the `quinn` library.
//! A single bidirectional QUIC stream carries length-prefixed Beep frames,
//! while native QUIC datagrams are available for the datagram traffic class.
//!
//! # Wire format on the QUIC stream
//!
//! Each Beep frame is preceded by a 4-byte big-endian length prefix:
//! ```text
//! [len: u32 BE] [payload: len bytes]
//! ```
//!
//! This is necessary because QUIC streams are byte-oriented (no built-in
//! message boundaries like H2 DATA frames).

use std::net::SocketAddr;
use std::sync::Arc;

use beep_transport::{CoverConn, TransportCapabilities, TransportError};
use bytes::Bytes;
use sha2::{Digest, Sha256};

/// ALPN for Beep over QUIC.
pub const BEEP_ALPN: &[u8] = b"beep-quic";

/// QUIC cover transport connection.
pub struct H3CoverConn {
    /// The underlying QUIC connection (for datagrams + metadata).
    conn: quinn::Connection,
    /// Send half of the bidirectional stream.
    send: quinn::SendStream,
    /// Receive half of the bidirectional stream.
    recv: quinn::RecvStream,
    /// Transport binding digest.
    transport_binding: [u8; 32],
    /// Kept alive to prevent the I/O driver from shutting down.
    _endpoint: quinn::Endpoint,
}

impl CoverConn for H3CoverConn {
    async fn send(&mut self, data: Bytes) -> Result<(), TransportError> {
        let len = (data.len() as u32).to_be_bytes();
        self.send
            .write_all(&len)
            .await
            .map_err(|e| TransportError::Quic(e.to_string()))?;
        self.send
            .write_all(&data)
            .await
            .map_err(|e| TransportError::Quic(e.to_string()))?;
        Ok(())
    }

    async fn recv(&mut self) -> Result<Option<Bytes>, TransportError> {
        let mut len_buf = [0u8; 4];
        match self.recv.read_exact(&mut len_buf).await {
            Ok(()) => {}
            Err(quinn::ReadExactError::FinishedEarly(_)) => return Ok(None),
            Err(e) => return Err(TransportError::Quic(e.to_string())),
        }
        let len = u32::from_be_bytes(len_buf) as usize;

        let mut payload = vec![0u8; len];
        self.recv
            .read_exact(&mut payload)
            .await
            .map_err(|e| TransportError::Quic(e.to_string()))?;

        Ok(Some(Bytes::from(payload)))
    }

    fn transport_binding(&self) -> [u8; 32] {
        self.transport_binding
    }

    fn capabilities(&self) -> TransportCapabilities {
        TransportCapabilities {
            supports_streams: true,
            supports_datagrams: true,
            supports_migration: true,
        }
    }
}

impl H3CoverConn {
    /// Access the underlying QUIC connection for native datagram I/O.
    pub fn quic_connection(&self) -> &quinn::Connection {
        &self.conn
    }
}

// ── Client connect ──────────────────────────────────────────────────────

/// Connect to a Beep node over QUIC.
///
/// Establishes a QUIC connection, opens a bidirectional stream, and
/// returns an `H3CoverConn` ready for Beep handshake.
pub async fn connect_h3(
    bind_addr: SocketAddr,
    server_addr: SocketAddr,
    server_name: &str,
    client_crypto: rustls::ClientConfig,
) -> Result<H3CoverConn, TransportError> {
    let mut transport_config = quinn::TransportConfig::default();
    transport_config.datagram_receive_buffer_size(Some(2 * 1024 * 1024));
    transport_config.datagram_send_buffer_size(2 * 1024 * 1024);

    let mut client_config = quinn::ClientConfig::new(Arc::new(
        quinn::crypto::rustls::QuicClientConfig::try_from(client_crypto)
            .map_err(|e| TransportError::Tls(e.to_string()))?,
    ));
    client_config.transport_config(Arc::new(transport_config));

    let mut endpoint = quinn::Endpoint::client(bind_addr)
        .map_err(|e| TransportError::Io(e.to_string()))?;
    endpoint.set_default_client_config(client_config);

    let conn = endpoint
        .connect(server_addr, server_name)
        .map_err(|e| TransportError::Quic(e.to_string()))?
        .await
        .map_err(|e| TransportError::Quic(e.to_string()))?;

    let binding = compute_binding_from_conn(&conn);

    let (send, recv) = conn
        .open_bi()
        .await
        .map_err(|e| TransportError::Quic(e.to_string()))?;

    Ok(H3CoverConn {
        conn,
        send,
        recv,
        transport_binding: binding,
        _endpoint: endpoint,
    })
}

// ── Server accept ───────────────────────────────────────────────────────

/// Create a QUIC server endpoint bound to the given address.
pub fn server_endpoint(
    bind_addr: SocketAddr,
    server_crypto: rustls::ServerConfig,
) -> Result<quinn::Endpoint, TransportError> {
    let mut transport_config = quinn::TransportConfig::default();
    transport_config.datagram_receive_buffer_size(Some(2 * 1024 * 1024));
    transport_config.datagram_send_buffer_size(2 * 1024 * 1024);

    let quic_server_config = quinn::crypto::rustls::QuicServerConfig::try_from(server_crypto)
        .map_err(|e| TransportError::Tls(e.to_string()))?;

    let mut server_config = quinn::ServerConfig::with_crypto(Arc::new(quic_server_config));
    server_config.transport_config(Arc::new(transport_config));

    quinn::Endpoint::server(server_config, bind_addr)
        .map_err(|e| TransportError::Io(e.to_string()))
}

/// Accept one incoming QUIC connection and return an `H3CoverConn`.
///
/// `server_cert_der` is used to compute the transport binding on the
/// server side so it matches the client's view.
///
/// The `endpoint` is stored inside `H3CoverConn` to keep the I/O driver
/// alive for the lifetime of the connection.
pub async fn accept_h3(
    endpoint: quinn::Endpoint,
    incoming: quinn::Incoming,
    server_cert_der: &[u8],
) -> Result<H3CoverConn, TransportError> {
    let conn = incoming
        .await
        .map_err(|e| TransportError::Quic(e.to_string()))?;

    let binding = compute_binding(server_cert_der);

    let (send, recv) = conn
        .accept_bi()
        .await
        .map_err(|e| TransportError::Quic(e.to_string()))?;

    Ok(H3CoverConn {
        conn,
        send,
        recv,
        transport_binding: binding,
        _endpoint: endpoint,
    })
}

// ── TLS binding ─────────────────────────────────────────────────────────

fn compute_binding_from_conn(conn: &quinn::Connection) -> [u8; 32] {
    // Extract peer certificates from the QUIC connection
    let peer_certs = conn
        .peer_identity()
        .and_then(|id| {
            id.downcast::<Vec<rustls::pki_types::CertificateDer<'static>>>()
                .ok()
        });

    let cert_der = peer_certs
        .as_ref()
        .and_then(|certs| certs.first())
        .map(|c| c.as_ref());

    match cert_der {
        Some(der) => compute_binding(der),
        None => [0u8; 32],
    }
}

fn compute_binding(cert_der: &[u8]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(b"beep-transport-binding-h3-v1");
    hasher.update(cert_der);
    let hash = hasher.finalize();
    let mut binding = [0u8; 32];
    binding.copy_from_slice(&hash);
    binding
}
