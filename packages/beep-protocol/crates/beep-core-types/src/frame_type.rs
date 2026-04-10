//! Frame type identifiers for the Beep session core wire format.
//!
//! # Ignorable-bit convention
//!
//! Bit 0 (LSB) of the frame type value is the **ignorable flag**:
//! - Even values (bit 0 = 0): **critical** — unknown types terminate the session.
//! - Odd values (bit 0 = 1): **ignorable** — unknown types are silently skipped.
//!
//! This follows the QUIC extension frame convention and prevents protocol
//! ossification by allowing new optional frame types without breaking old peers.

/// A frame type identifier, encoded as a QUIC-style varint on the wire.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct FrameType(pub u64);

impl FrameType {
    // ── Handshake frames (critical) ─────────────────────────────────────
    pub const CLIENT_INIT: Self = Self(0x00);
    pub const SERVER_INIT: Self = Self(0x02);
    pub const CLIENT_FINISH: Self = Self(0x04);
    pub const SERVER_FINISH: Self = Self(0x06);
    pub const RETRY: Self = Self(0x08);

    // ── Session management frames ───────────────────────────────────────
    pub const SESSION_UPDATE: Self = Self(0x20);
    pub const SESSION_CLOSE: Self = Self(0x22);
    pub const KEY_UPDATE: Self = Self(0x24);
    pub const TICKET_ISSUE: Self = Self(0x26);
    pub const PATH_HINT: Self = Self(0x29); // ignorable: advisory

    // ── Stream and datagram frames ──────────────────────────────────────
    pub const STREAM_OPEN: Self = Self(0x40);
    pub const STREAM_CLOSE: Self = Self(0x42);
    pub const FLOW_CREDIT: Self = Self(0x44);
    pub const DATAGRAM_CLASS: Self = Self(0x46);
    pub const STREAM_DATA: Self = Self(0x48);
    pub const DATAGRAM_DROP_NOTICE: Self = Self(0x49); // ignorable: informational

    // ── Policy and routing frames ───────────────────────────────────────
    pub const ROUTE_SET: Self = Self(0x60);
    pub const DNS_CONFIG: Self = Self(0x62);
    pub const MTU_HINT: Self = Self(0x65); // ignorable: hint
    pub const QOS_HINT: Self = Self(0x67); // ignorable: hint

    // ── Telemetry frames (all ignorable) ────────────────────────────────
    pub const HEALTH_SUMMARY: Self = Self(0x81);
    pub const ERROR_REPORT: Self = Self(0x83);
    pub const TRACE_TOKEN: Self = Self(0x85);

    // ── GREASE values for forward-compatibility testing ──────────────────
    pub const GREASE_1: Self = Self(0xB3);
    pub const GREASE_2: Self = Self(0xB5);
    pub const GREASE_3: Self = Self(0xB7);

    /// Returns `true` if unknown instances of this frame type can be skipped.
    pub const fn is_ignorable(self) -> bool {
        self.0 & 1 == 1
    }

    /// Returns `true` if this frame type MUST be understood by the peer.
    pub const fn is_critical(self) -> bool {
        self.0 & 1 == 0
    }

    /// Raw value for wire encoding.
    pub const fn as_u64(self) -> u64 {
        self.0
    }

    /// Returns `true` if this is a handshake frame type (0x00–0x0F range).
    pub const fn is_handshake(self) -> bool {
        self.0 <= 0x0F
    }

    /// Returns the human-readable name, or `None` for unknown types.
    pub const fn name(self) -> Option<&'static str> {
        match self.0 {
            0x00 => Some("CLIENT_INIT"),
            0x02 => Some("SERVER_INIT"),
            0x04 => Some("CLIENT_FINISH"),
            0x06 => Some("SERVER_FINISH"),
            0x08 => Some("RETRY"),
            0x20 => Some("SESSION_UPDATE"),
            0x22 => Some("SESSION_CLOSE"),
            0x24 => Some("KEY_UPDATE"),
            0x26 => Some("TICKET_ISSUE"),
            0x29 => Some("PATH_HINT"),
            0x40 => Some("STREAM_OPEN"),
            0x42 => Some("STREAM_CLOSE"),
            0x44 => Some("FLOW_CREDIT"),
            0x46 => Some("DATAGRAM_CLASS"),
            0x48 => Some("STREAM_DATA"),
            0x49 => Some("DATAGRAM_DROP_NOTICE"),
            0x60 => Some("ROUTE_SET"),
            0x62 => Some("DNS_CONFIG"),
            0x65 => Some("MTU_HINT"),
            0x67 => Some("QOS_HINT"),
            0x81 => Some("HEALTH_SUMMARY"),
            0x83 => Some("ERROR_REPORT"),
            0x85 => Some("TRACE_TOKEN"),
            _ => None,
        }
    }
}

impl std::fmt::Display for FrameType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self.name() {
            Some(name) => write!(f, "{name}"),
            None => write!(f, "FrameType(0x{:02x})", self.0),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn critical_frames_are_even() {
        assert!(FrameType::CLIENT_INIT.is_critical());
        assert!(FrameType::SERVER_INIT.is_critical());
        assert!(FrameType::CLIENT_FINISH.is_critical());
        assert!(FrameType::SERVER_FINISH.is_critical());
        assert!(FrameType::RETRY.is_critical());
        assert!(FrameType::SESSION_CLOSE.is_critical());
        assert!(FrameType::KEY_UPDATE.is_critical());
    }

    #[test]
    fn ignorable_frames_are_odd() {
        assert!(FrameType::PATH_HINT.is_ignorable());
        assert!(FrameType::DATAGRAM_DROP_NOTICE.is_ignorable());
        assert!(FrameType::MTU_HINT.is_ignorable());
        assert!(FrameType::QOS_HINT.is_ignorable());
        assert!(FrameType::HEALTH_SUMMARY.is_ignorable());
        assert!(FrameType::ERROR_REPORT.is_ignorable());
        assert!(FrameType::TRACE_TOKEN.is_ignorable());
    }

    #[test]
    fn grease_values_are_ignorable() {
        assert!(FrameType::GREASE_1.is_ignorable());
        assert!(FrameType::GREASE_2.is_ignorable());
        assert!(FrameType::GREASE_3.is_ignorable());
    }

    #[test]
    fn handshake_range() {
        assert!(FrameType::CLIENT_INIT.is_handshake());
        assert!(FrameType::RETRY.is_handshake());
        assert!(!FrameType::SESSION_UPDATE.is_handshake());
        assert!(!FrameType::HEALTH_SUMMARY.is_handshake());
    }

    #[test]
    fn display_known() {
        assert_eq!(FrameType::CLIENT_INIT.to_string(), "CLIENT_INIT");
    }

    #[test]
    fn display_unknown() {
        assert_eq!(FrameType(0xFF).to_string(), "FrameType(0xff)");
    }
}
