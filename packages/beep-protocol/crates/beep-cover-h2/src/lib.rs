//! HTTP/2 Extended CONNECT cover transport for Beep.
//!
//! Implements [`CoverConn`] over an HTTP/2 stream opened via Extended CONNECT.

use beep_transport::{CoverConn, TransportCapabilities, TransportError};
use bytes::Bytes;
use h2::{RecvStream, SendStream};
use sha2::{Digest, Sha256};

/// The Extended CONNECT :protocol value.
pub const BEEP_PROTOCOL: &str = "beep-tunnel";

/// HTTP/2 cover transport connection.
pub struct H2CoverConn {
    send: SendStream<Bytes>,
    recv: RecvStream,
    transport_binding: [u8; 32],
}

impl H2CoverConn {
    pub fn new(send: SendStream<Bytes>, recv: RecvStream, tls_binding: &[u8]) -> Self {
        let mut hasher = Sha256::new();
        hasher.update(b"beep-transport-binding-h2-v1");
        hasher.update(tls_binding);
        let hash = hasher.finalize();
        let mut binding = [0u8; 32];
        binding.copy_from_slice(&hash);
        Self { send, recv, transport_binding: binding }
    }
}

impl CoverConn for H2CoverConn {
    async fn send(&mut self, data: Bytes) -> Result<(), TransportError> {
        self.send.reserve_capacity(data.len());

        std::future::poll_fn(|cx| self.send.poll_capacity(cx))
            .await
            .ok_or(TransportError::ConnectionClosed)?
            .map_err(|e| TransportError::H2(e.to_string()))?;

        self.send
            .send_data(data, false)
            .map_err(|e| TransportError::H2(e.to_string()))
    }

    async fn recv(&mut self) -> Result<Option<Bytes>, TransportError> {
        match self.recv.data().await {
            Some(Ok(data)) => {
                let _ = self.recv.flow_control().release_capacity(data.len());
                Ok(Some(data))
            }
            Some(Err(e)) => Err(TransportError::H2(e.to_string())),
            None => Ok(None),
        }
    }

    fn transport_binding(&self) -> [u8; 32] {
        self.transport_binding
    }

    fn capabilities(&self) -> TransportCapabilities {
        TransportCapabilities {
            supports_streams: true,
            supports_datagrams: false,
            supports_migration: false,
        }
    }
}

// ── Client connect ──────────────────────────────────────────────────────

pub async fn connect_h2(
    tls_stream: tokio_rustls::client::TlsStream<tokio::net::TcpStream>,
    authority: &str,
) -> Result<H2CoverConn, TransportError> {
    let binding = client_tls_binding(&tls_stream);

    let (client, h2_conn) = h2::client::handshake(tls_stream)
        .await
        .map_err(|e| TransportError::H2(e.to_string()))?;

    tokio::spawn(async move {
        if let Err(e) = h2_conn.await {
            tracing::error!("H2 client conn error: {e}");
        }
    });

    let mut client = client
        .ready()
        .await
        .map_err(|e| TransportError::H2(e.to_string()))?;

    let uri = format!("https://{}/beep", authority);
    let req = http::Request::builder()
        .method("CONNECT")
        .uri(uri)
        .version(http::Version::HTTP_2)
        .extension(h2::ext::Protocol::from(BEEP_PROTOCOL))
        .body(())
        .map_err(|e| TransportError::H2(e.to_string()))?;

    let (response_fut, send_stream) = client
        .send_request(req, false)
        .map_err(|e| TransportError::H2(e.to_string()))?;

    let resp: http::Response<RecvStream> = response_fut
        .await
        .map_err(|e| TransportError::H2(e.to_string()))?;

    if resp.status() != http::StatusCode::OK {
        return Err(TransportError::H2(format!("status: {}", resp.status())));
    }

    let recv_stream = resp.into_body();
    Ok(H2CoverConn::new(send_stream, recv_stream, &binding))
}

// ── Server accept ───────────────────────────────────────────────────────

/// Accept one H2 Extended CONNECT and return a CoverConn.
///
/// `server_cert_der` is the DER-encoded server certificate, used to compute
/// transport binding that matches the client's view of the connection.
pub async fn accept_h2(
    tls_stream: tokio_rustls::server::TlsStream<tokio::net::TcpStream>,
    server_cert_der: &[u8],
) -> Result<H2CoverConn, TransportError> {
    let binding = sha256_hash(server_cert_der);

    let mut h2_conn = h2::server::Builder::new()
        .enable_connect_protocol()
        .handshake(tls_stream)
        .await
        .map_err(|e| TransportError::H2(e.to_string()))?;

    let (request, mut respond) = h2_conn
        .accept()
        .await
        .ok_or(TransportError::ConnectionClosed)?
        .map_err(|e| TransportError::H2(e.to_string()))?;

    let valid = request.method() == http::Method::CONNECT
        && request
            .extensions()
            .get::<h2::ext::Protocol>()
            .is_some_and(|p| p.as_str() == BEEP_PROTOCOL);

    if !valid {
        let r = http::Response::builder().status(400).body(()).unwrap();
        let _ = respond.send_response(r, true);
        return Err(TransportError::H2("invalid CONNECT".into()));
    }

    let recv_stream = request.into_body();
    let r = http::Response::builder().status(200).body(()).unwrap();
    let send_stream = respond
        .send_response(r, false)
        .map_err(|e| TransportError::H2(e.to_string()))?;

    tokio::spawn(async move {
        while let Some(Ok(_)) = h2_conn.accept().await {}
    });

    Ok(H2CoverConn::new(send_stream, recv_stream, &binding))
}

// ── TLS binding ─────────────────────────────────────────────────────────

fn client_tls_binding(
    s: &tokio_rustls::client::TlsStream<tokio::net::TcpStream>,
) -> Vec<u8> {
    let (_io, conn) = s.get_ref();
    conn.peer_certificates()
        .and_then(|c| c.first())
        .map(|c| sha256_hash(c.as_ref()))
        .unwrap_or_else(|| vec![0u8; 32])
}

fn sha256_hash(data: &[u8]) -> Vec<u8> {
    let mut h = Sha256::new();
    h.update(data);
    h.finalize().to_vec()
}
