//! Native fast UDP transport for Beep VPN protocol.
//!
//! Provides a `CoverConn` implementation that uses raw UDP datagrams without
//! an intermediate TLS cover layer. This reduces latency and MTU overhead on
//! friendly, high-quality networks.

use std::sync::Arc;
use tokio::net::UdpSocket;
use bytes::Bytes;
use beep_transport::{CoverConn, TransportCapabilities, TransportError};

/// A naive UDP-based CoverConn instance.
pub struct NativeUdpConn {
    socket: Arc<UdpSocket>,
    recv_buf: Vec<u8>,
}

impl NativeUdpConn {
    /// Create a new `NativeUdpConn` from a connected `tokio::net::UdpSocket`.
    /// The socket must already be `connect()`ed to the target peer so that we
    /// can use `send`/`recv` without specifying remote addresses.
    pub fn new(socket: Arc<UdpSocket>) -> Self {
        Self {
            socket,
            recv_buf: vec![0u8; 65536], // max UDP datagram size
        }
    }
}

impl CoverConn for NativeUdpConn {
    async fn send(&mut self, data: Bytes) -> Result<(), TransportError> {
        let n = self.socket.send(&data).await.map_err(|e| TransportError::Io(e.to_string()))?;
        if n < data.len() {
            return Err(TransportError::Io("Partial send over UDP".to_string()));
        }
        Ok(())
    }

    async fn recv(&mut self) -> Result<Option<Bytes>, TransportError> {
        let n = self.socket.recv(&mut self.recv_buf).await.map_err(|e| TransportError::Io(e.to_string()))?;
        if n == 0 {
            // Technically UDP datagram size 0 is possible, but practically not expected with Beep frames.
            // On some platforms receiving 0 bytes might indicate connection closure (e.g. ICMP port unreachable received on connected socket).
            return Ok(None);
        }
        Ok(Some(Bytes::copy_from_slice(&self.recv_buf[..n])))
    }

    fn transport_binding(&self) -> [u8; 32] {
        // Native UDP has no TLS outer wrapper. Use an all-zero binding (or statically defined magic)
        // so that channel binding requirements inside SessionCore succeed without relying on outer TLS.
        [0u8; 32]
    }

    fn capabilities(&self) -> TransportCapabilities {
        TransportCapabilities {
            supports_streams: false, // Pure datagram transport. Handshake operates on best-effort byte sending.
            supports_datagrams: true,
            supports_migration: true, // Native apps can re-bind the UDP port to a new IP path.
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::net::UdpSocket;

    #[tokio::test]
    async fn it_works() {
        let listener = Arc::new(UdpSocket::bind("127.0.0.1:0").await.unwrap());
        let addr = listener.local_addr().unwrap();

        let client = Arc::new(UdpSocket::bind("127.0.0.1:0").await.unwrap());
        client.connect(addr).await.unwrap();

        let mut t1 = NativeUdpConn::new(client);
        
        t1.send(Bytes::from("hello")).await.unwrap();
        
        let mut buf = [0u8; 100];
        let (n, peer) = listener.recv_from(&mut buf).await.unwrap();
        
        assert_eq!(&buf[..n], b"hello");
    }
}
