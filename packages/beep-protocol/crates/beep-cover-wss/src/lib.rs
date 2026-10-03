mod dialer;

pub use dialer::{ChromeDialer, ChromePreset, ChromeWsConn, RootCerts, RustlsDialer};

use beep_transport::{CoverConn, TransportCapabilities, TransportError};
use bytes::Bytes;
use futures_util::{SinkExt, StreamExt};
use tokio::io::{AsyncRead, AsyncWrite};
use tokio_tungstenite::tungstenite::Message;
use tokio_tungstenite::WebSocketStream;

pub struct WssCoverConn<S> {
    stream: WebSocketStream<S>,
    transport_binding: [u8; 32],
}

impl<S> WssCoverConn<S> {
    pub fn new(stream: WebSocketStream<S>, transport_binding: [u8; 32]) -> Self {
        Self {
            stream,
            transport_binding,
        }
    }
}

impl<S> CoverConn for WssCoverConn<S>
where
    S: AsyncRead + AsyncWrite + Unpin + Send + Sync + 'static,
{
    async fn send(&mut self, data: Bytes) -> Result<(), TransportError> {
        self.stream
            .send(Message::Binary(data))
            .await
            .map_err(|e| TransportError::Io(e.to_string()))?;
        Ok(())
    }

    async fn recv(&mut self) -> Result<Option<Bytes>, TransportError> {
        loop {
            match self.stream.next().await {
                Some(Ok(Message::Binary(data))) => return Ok(Some(data)),
                Some(Ok(Message::Close(_))) | None => return Ok(None),
                Some(Ok(_)) => {
                    // Ignore Pings, Pongs, Text messages since Beep uses only Binary data over WSS.
                    // Tungstenite automatically responds to Pings with Pongs.
                    continue;
                }
                Some(Err(e)) => return Err(TransportError::Io(e.to_string())),
            }
        }
    }

    fn transport_binding(&self) -> [u8; 32] {
        self.transport_binding
    }

    fn capabilities(&self) -> TransportCapabilities {
        TransportCapabilities {
            supports_streams: true,
            supports_datagrams: false, // WebSockets are built on TCP streams
            supports_migration: false,
        }
    }
}

use beep_transport::{binding_from_leaf, WS_BINDING_LABEL};
use std::sync::Arc;
use tokio::net::TcpStream;
use tokio_rustls::TlsConnector;
use tokio_tungstenite::tungstenite::handshake::client::Request as ClientRequest;
use tokio_tungstenite::tungstenite::handshake::server::{
    ErrorResponse, Request as ServerRequest, Response as ServerResponse,
};
use tokio_tungstenite::tungstenite::http::{HeaderName, HeaderValue, StatusCode};

/// The only ALPN token the WebSocket-over-HTTP/1.1 transport offers.
pub const ALPN_HTTP11: &[u8] = b"http/1.1";

fn client_tls_leaf(s: &tokio_rustls::client::TlsStream<TcpStream>) -> Option<Vec<u8>> {
    let (_io, conn) = s.get_ref();
    conn.peer_certificates()
        .and_then(|c| c.first())
        .map(|c| c.as_ref().to_vec())
}

// ── Client side ─────────────────────────────────────────────────────────

/// Run the WebSocket upgrade over an already-established stream.
///
/// `host` goes into the `Host` header, `path` is the request path (a leading
/// `/` is optional) and `headers` are added verbatim (for example the secret
/// header a front proxy checks). `binding` is the transport binding the caller
/// derived from the TLS leaf certificate.
pub async fn client_ws_handshake<S>(
    stream: S,
    host: &str,
    path: &str,
    headers: &[(String, String)],
    binding: [u8; 32],
) -> Result<WssCoverConn<S>, TransportError>
where
    S: AsyncRead + AsyncWrite + Unpin + Send + Sync + 'static,
{
    let path = path.trim_start_matches('/');
    let url = format!("wss://{host}/{path}");
    let mut request: ClientRequest =
        tokio_tungstenite::tungstenite::client::IntoClientRequest::into_client_request(
            url.as_str(),
        )
        .map_err(|e| TransportError::Io(e.to_string()))?;
    for (name, value) in headers {
        let name = HeaderName::from_bytes(name.as_bytes())
            .map_err(|e| TransportError::Io(format!("bad header name: {e}")))?;
        let value = HeaderValue::from_str(value)
            .map_err(|e| TransportError::Io(format!("bad header value: {e}")))?;
        request.headers_mut().insert(name, value);
    }
    let (ws_stream, _response) = tokio_tungstenite::client_async(request, stream)
        .await
        .map_err(|e| TransportError::Io(e.to_string()))?;
    Ok(WssCoverConn::new(ws_stream, binding))
}

/// Connect over TLS with a caller-supplied rustls config and upgrade to a
/// WebSocket. The config decides ALPN, roots and SNI.
pub async fn connect_wss(
    server_addr: std::net::SocketAddr,
    server_name: &str,
    path: &str,
    client_crypto: rustls::ClientConfig,
) -> Result<WssCoverConn<tokio_rustls::client::TlsStream<TcpStream>>, TransportError> {
    let domain = rustls::pki_types::ServerName::try_from(server_name.to_string())
        .map_err(|e| TransportError::Tls(e.to_string()))?;

    let connector = TlsConnector::from(Arc::new(client_crypto));
    let tcp_stream = TcpStream::connect(server_addr)
        .await
        .map_err(|e| TransportError::Io(e.to_string()))?;

    let tls_stream = connector
        .connect(domain, tcp_stream)
        .await
        .map_err(|e| TransportError::Tls(e.to_string()))?;

    let binding = binding_from_leaf(WS_BINDING_LABEL, client_tls_leaf(&tls_stream).as_deref());
    client_ws_handshake(tls_stream, server_name, path, &[], binding).await
}

// ── Server side ─────────────────────────────────────────────────────────

/// Which upgrade requests the node admits.
///
/// Behind a front proxy this is a second check (the proxy already filtered):
/// a request that does not carry the secret path and headers never becomes a
/// tunnel. An empty path admits any path (lab and tests).
#[derive(Debug, Clone, Default)]
pub struct WsGate {
    path: String,
    required: Vec<(HeaderName, Vec<u8>)>,
}

impl WsGate {
    /// Admit every request (lab and tests).
    pub fn open() -> Self {
        Self::default()
    }

    /// Admit only requests for `path` that carry every `(name, value)` header.
    pub fn new(path: &str, headers: &[(String, String)]) -> Result<Self, TransportError> {
        let mut required = Vec::with_capacity(headers.len());
        for (name, value) in headers {
            let name = HeaderName::from_bytes(name.as_bytes())
                .map_err(|e| TransportError::Io(format!("bad header name: {e}")))?;
            required.push((name, value.as_bytes().to_vec()));
        }
        Ok(Self {
            path: path.to_string(),
            required,
        })
    }

    fn admits(&self, req: &ServerRequest) -> bool {
        if !self.path.is_empty() && req.uri().path() != self.path {
            return false;
        }
        // Evaluate every header even after a mismatch so timing does not say
        // which one was wrong.
        let mut ok = true;
        for (name, expected) in &self.required {
            let matches = req
                .headers()
                .get(name)
                .map(|v| constant_time_eq(v.as_bytes(), expected))
                .unwrap_or(false);
            ok &= matches;
        }
        ok
    }
}

fn constant_time_eq(a: &[u8], b: &[u8]) -> bool {
    if a.len() != b.len() {
        return false;
    }
    a.iter().zip(b).fold(0u8, |acc, (x, y)| acc | (x ^ y)) == 0
}

fn not_found() -> ErrorResponse {
    let mut resp = ErrorResponse::new(None);
    *resp.status_mut() = StatusCode::NOT_FOUND;
    resp.headers_mut()
        .insert("content-length", HeaderValue::from_static("0"));
    resp
}

/// Accept a WebSocket upgrade on `stream` if it passes `gate`.
///
/// A request that fails the gate gets a bare 404 and the call returns an
/// error. `binding` is the transport binding the node derived from the public
/// certificate the client sees.
pub async fn accept_ws<S>(
    stream: S,
    gate: &WsGate,
    binding: [u8; 32],
) -> Result<WssCoverConn<S>, TransportError>
where
    S: AsyncRead + AsyncWrite + Unpin + Send + Sync + 'static,
{
    let gate = gate.clone();
    // The Err type and closure signature are tungstenite's `Callback` trait;
    // neither is ours to shrink.
    #[allow(clippy::result_large_err)]
    let callback =
        move |req: &ServerRequest, resp: ServerResponse| -> Result<ServerResponse, ErrorResponse> {
            if gate.admits(req) {
                Ok(resp)
            } else {
                Err(not_found())
            }
        };
    let ws_stream = tokio_tungstenite::accept_hdr_async(stream, callback)
        .await
        .map_err(|e| TransportError::Io(e.to_string()))?;
    Ok(WssCoverConn::new(ws_stream, binding))
}

/// Accept a WebSocket upgrade on a TLS stream the node terminated itself
/// (lab and tests). Any path is admitted.
pub async fn accept_wss(
    tls_stream: tokio_rustls::server::TlsStream<TcpStream>,
    server_cert_der: &[u8],
) -> Result<WssCoverConn<tokio_rustls::server::TlsStream<TcpStream>>, TransportError> {
    let binding = binding_from_leaf(WS_BINDING_LABEL, Some(server_cert_der));
    accept_ws(tls_stream, &WsGate::open(), binding).await
}
