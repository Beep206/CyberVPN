//! Dialing: how a client reaches a node and what the outer connection looks like.
//!
//! A [`CoverDialer`] owns everything below the Beep session: TCP, TLS (with its
//! ClientHello), the HTTP layer and the WebSocket upgrade. The runtime asks it
//! for a ready [`CoverConn`] and never sees the TLS stack, so the TLS provider
//! (rustls or a browser-preset BoringSSL) is a profile choice, not a code path.

use std::future::Future;
use std::net::SocketAddr;
use std::time::Duration;

use beep_core_types::artifact::{HttpMode, SniMode};
use beep_core_types::profile::ProfileFile;
use sha2::{Digest, Sha256};

use crate::{CoverConn, TransportError};

/// Everything a dialer needs for one connection attempt.
///
/// Built once from the profile and reused for every attempt, so the SNI, ALPN
/// and fingerprint do not change between retries.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DialTarget {
    /// Where to connect (IP and port); DNS is never consulted.
    pub addr: SocketAddr,
    /// Host name for the SNI and the HTTP authority.
    pub server_name: String,
    /// Whether to send the SNI extension.
    pub sni: SniMode,
    /// How the outer HTTP layer carries the tunnel.
    pub http: HttpMode,
    /// Request path.
    pub path: String,
    /// Extra request headers (for example the secret header).
    pub headers: Vec<(String, String)>,
    /// ALPN tokens to offer, in order.
    pub alpn: Vec<String>,
    /// Upper bound for TCP connect plus TLS plus the upgrade.
    pub connect_timeout: Duration,
}

impl DialTarget {
    /// Build a target from a validated profile and the node address.
    pub fn from_profile(profile: &ProfileFile, addr: SocketAddr) -> Self {
        let p = &profile.presentation;
        Self {
            addr,
            server_name: p.server_name.clone(),
            sni: p.sni_mode,
            http: p.http_mode,
            path: p.path.clone(),
            headers: p
                .headers
                .iter()
                .map(|(k, v)| (k.clone(), v.clone()))
                .collect(),
            alpn: p.alpn.clone(),
            connect_timeout: Duration::from_millis(profile.transport.connect_timeout_ms),
        }
    }
}

/// Opens cover connections.
pub trait CoverDialer: Send + Sync {
    /// The connection type this dialer produces.
    type Conn: CoverConn + 'static;

    /// Connect, finish the TLS and HTTP handshakes, and return a ready conn.
    fn dial(
        &self,
        target: &DialTarget,
    ) -> impl Future<Output = Result<Self::Conn, TransportError>> + Send;
}

/// Domain-separation label of the WebSocket-based cover transports. It is hashed
/// into the transport binding and never appears on the wire.
pub const WS_BINDING_LABEL: &[u8] = b"beep-transport-binding-wss-v1";

/// Derive the 32-byte transport binding from the TLS leaf certificate.
///
/// Both ends hash the certificate the *client* sees on the public port, so a
/// middlebox that terminates TLS with a different certificate (even a valid
/// one) makes the two bindings differ and the session handshake fail. With no
/// certificate the digest input is 32 zero bytes, as before.
pub fn binding_from_leaf(label: &[u8], leaf_der: Option<&[u8]>) -> [u8; 32] {
    let tls_hash: Vec<u8> = match leaf_der {
        Some(der) => Sha256::digest(der).to_vec(),
        None => vec![0u8; 32],
    };
    let mut hasher = Sha256::new();
    hasher.update(label);
    hasher.update(&tls_hash);
    hasher.finalize().into()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn binding_depends_on_certificate_and_label() {
        let a = binding_from_leaf(WS_BINDING_LABEL, Some(b"cert-a"));
        let b = binding_from_leaf(WS_BINDING_LABEL, Some(b"cert-b"));
        let c = binding_from_leaf(b"other-label", Some(b"cert-a"));
        assert_ne!(a, b);
        assert_ne!(a, c);
        assert_eq!(a, binding_from_leaf(WS_BINDING_LABEL, Some(b"cert-a")));
    }

    #[test]
    fn missing_certificate_matches_the_old_zero_digest_rule() {
        let none = binding_from_leaf(WS_BINDING_LABEL, None);
        let mut h = Sha256::new();
        h.update(WS_BINDING_LABEL);
        h.update([0u8; 32]);
        assert_eq!(none, <[u8; 32]>::from(h.finalize()));
    }
}
