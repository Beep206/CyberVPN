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

use sha2::{Digest, Sha256};
use std::sync::Arc;
use tokio::net::TcpStream;
use tokio_rustls::TlsConnector;

pub const BEEP_ALPN: &[u8] = b"beep/wss";

fn sha256_hash(data: &[u8]) -> Vec<u8> {
    let mut h = Sha256::new();
    h.update(data);
    h.finalize().to_vec()
}

fn client_tls_binding(s: &tokio_rustls::client::TlsStream<TcpStream>) -> Vec<u8> {
    let (_io, conn) = s.get_ref();
    conn.peer_certificates()
        .and_then(|c| c.first())
        .map(|c| sha256_hash(c.as_ref()))
        .unwrap_or_else(|| vec![0u8; 32])
}

fn compute_binding(tls_hash: &[u8]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(b"beep-transport-binding-wss-v1");
    hasher.update(tls_hash);
    let hash = hasher.finalize();
    let mut binding = [0u8; 32];
    binding.copy_from_slice(&hash);
    binding
}

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

    let tls_cert_hash = client_tls_binding(&tls_stream);
    let binding = compute_binding(&tls_cert_hash);

    let url = format!("wss://{}/{}", server_name, path);
    // client_async returns (WebSocketStream, http::Response)
    let (ws_stream, _response) = tokio_tungstenite::client_async(&url, tls_stream)
        .await
        .map_err(|e| TransportError::Io(e.to_string()))?;

    Ok(WssCoverConn::new(ws_stream, binding))
}

pub async fn accept_wss(
    tls_stream: tokio_rustls::server::TlsStream<TcpStream>,
    server_cert_der: &[u8],
) -> Result<WssCoverConn<tokio_rustls::server::TlsStream<TcpStream>>, TransportError> {
    let tls_cert_hash = sha256_hash(server_cert_der);
    let binding = compute_binding(&tls_cert_hash);

    let ws_stream = tokio_tungstenite::accept_async(tls_stream)
        .await
        .map_err(|e| TransportError::Io(e.to_string()))?;

    Ok(WssCoverConn::new(ws_stream, binding))
}
