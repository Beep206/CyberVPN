//! Capability identifiers for session negotiation.
//!
//! Capabilities are exchanged during the handshake to agree on
//! features both sides support. Each capability has a stable numeric ID.

/// A negotiable capability of the Beep session core.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[repr(u16)]
pub enum CapabilityId {
    /// Reliable stream multiplexing.
    Streams = 0x01,
    /// Unreliable datagram transport.
    Datagrams = 0x02,
    /// Session resumption via tickets.
    Resumption = 0x03,
    /// In-session key update (rekey).
    Rekey = 0x04,
    /// Path hint exchange.
    PathHints = 0x05,
    /// Route and DNS configuration push.
    RouteConfig = 0x06,
    /// Telemetry frame exchange.
    Telemetry = 0x07,
    /// Hybrid post-quantum key exchange (X25519 + ML-KEM-768).
    HybridPqKex = 0x10,
    /// AES-256-GCM AEAD (alternative to mandatory ChaCha20-Poly1305).
    AesGcm256 = 0x11,
}

impl CapabilityId {
    /// Decode from wire value.
    pub fn from_wire(value: u16) -> Option<Self> {
        match value {
            0x01 => Some(Self::Streams),
            0x02 => Some(Self::Datagrams),
            0x03 => Some(Self::Resumption),
            0x04 => Some(Self::Rekey),
            0x05 => Some(Self::PathHints),
            0x06 => Some(Self::RouteConfig),
            0x07 => Some(Self::Telemetry),
            0x10 => Some(Self::HybridPqKex),
            0x11 => Some(Self::AesGcm256),
            _ => None,
        }
    }

    /// Encode to wire value.
    pub const fn to_wire(self) -> u16 {
        self as u16
    }
}

impl std::fmt::Display for CapabilityId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let name = match self {
            Self::Streams => "STREAMS",
            Self::Datagrams => "DATAGRAMS",
            Self::Resumption => "RESUMPTION",
            Self::Rekey => "REKEY",
            Self::PathHints => "PATH_HINTS",
            Self::RouteConfig => "ROUTE_CONFIG",
            Self::Telemetry => "TELEMETRY",
            Self::HybridPqKex => "HYBRID_PQ_KEX",
            Self::AesGcm256 => "AES_GCM_256",
        };
        write!(f, "{name}")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip() {
        let caps = [
            CapabilityId::Streams,
            CapabilityId::Datagrams,
            CapabilityId::Resumption,
            CapabilityId::Rekey,
            CapabilityId::HybridPqKex,
        ];
        for cap in caps {
            assert_eq!(CapabilityId::from_wire(cap.to_wire()), Some(cap));
        }
    }

    #[test]
    fn unknown_returns_none() {
        assert_eq!(CapabilityId::from_wire(0xFF), None);
    }
}
