//! Machine-readable session error codes for the Beep wire protocol.
//!
//! These codes are sent on the wire in SESSION_CLOSE and ERROR_REPORT frames.
//! They must remain stable across protocol versions.

/// Error codes sent on the Beep session wire.
///
/// Each variant maps to a fixed numeric code for wire encoding.
/// Codes are grouped by category for aggregation and alerting.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[repr(u32)]
pub enum SessionErrorCode {
    // ── Success ─────────────────────────────────────────────────────────
    /// No error; graceful close.
    NoError = 0x00,

    // ── Negotiation errors (0x01–0x0F) ──────────────────────────────────
    /// No mutually supported protocol version.
    VersionNegotiationFailed = 0x01,
    /// No mutually supported capability set.
    CapabilityMismatch = 0x02,

    // ── Authentication errors (0x10–0x1F) ───────────────────────────────
    /// Client authentication failed.
    AuthFailed = 0x10,
    /// Handshake replayed or anti-replay check failed.
    ReplayRejected = 0x11,

    // ── Policy errors (0x20–0x2F) ───────────────────────────────────────
    /// Policy does not allow this session.
    PolicyRejected = 0x20,

    // ── Resource errors (0x30–0x3F) ─────────────────────────────────────
    /// Node resource limits exceeded.
    ResourceLimit = 0x30,

    // ── Transport binding errors (0x40–0x4F) ────────────────────────────
    /// Transport binding verification failed.
    TransportBindingFailed = 0x40,

    // ── Session maintenance errors (0x50–0x5F) ──────────────────────────
    /// Rekey procedure failed.
    RekeyFailed = 0x50,

    // ── Internal errors (0xF0–0xFF) ─────────────────────────────────────
    /// Unspecified internal error.
    InternalError = 0xF0,
    /// Received a critical frame type that is not understood.
    UnknownCriticalFrame = 0xF1,
    /// Protocol state violation.
    ProtocolViolation = 0xF2,
    /// Frame payload exceeds maximum allowed size.
    FrameTooLarge = 0xF3,
}

impl SessionErrorCode {
    /// Decode from a wire value. Returns `None` for unknown codes.
    pub fn from_wire(value: u32) -> Option<Self> {
        match value {
            0x00 => Some(Self::NoError),
            0x01 => Some(Self::VersionNegotiationFailed),
            0x02 => Some(Self::CapabilityMismatch),
            0x10 => Some(Self::AuthFailed),
            0x11 => Some(Self::ReplayRejected),
            0x20 => Some(Self::PolicyRejected),
            0x30 => Some(Self::ResourceLimit),
            0x40 => Some(Self::TransportBindingFailed),
            0x50 => Some(Self::RekeyFailed),
            0xF0 => Some(Self::InternalError),
            0xF1 => Some(Self::UnknownCriticalFrame),
            0xF2 => Some(Self::ProtocolViolation),
            0xF3 => Some(Self::FrameTooLarge),
            _ => None,
        }
    }

    /// Encode to wire value.
    pub const fn to_wire(self) -> u32 {
        self as u32
    }

    /// Human-readable name for diagnostics.
    pub const fn name(self) -> &'static str {
        match self {
            Self::NoError => "NO_ERROR",
            Self::VersionNegotiationFailed => "VERSION_NEGOTIATION_FAILED",
            Self::CapabilityMismatch => "CAPABILITY_MISMATCH",
            Self::AuthFailed => "AUTH_FAILED",
            Self::ReplayRejected => "REPLAY_REJECTED",
            Self::PolicyRejected => "POLICY_REJECTED",
            Self::ResourceLimit => "RESOURCE_LIMIT",
            Self::TransportBindingFailed => "TRANSPORT_BINDING_FAILED",
            Self::RekeyFailed => "REKEY_FAILED",
            Self::InternalError => "INTERNAL_ERROR",
            Self::UnknownCriticalFrame => "UNKNOWN_CRITICAL_FRAME",
            Self::ProtocolViolation => "PROTOCOL_VIOLATION",
            Self::FrameTooLarge => "FRAME_TOO_LARGE",
        }
    }
}

impl std::fmt::Display for SessionErrorCode {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{} (0x{:02x})", self.name(), self.to_wire())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip_all_codes() {
        let codes = [
            SessionErrorCode::NoError,
            SessionErrorCode::VersionNegotiationFailed,
            SessionErrorCode::CapabilityMismatch,
            SessionErrorCode::AuthFailed,
            SessionErrorCode::ReplayRejected,
            SessionErrorCode::PolicyRejected,
            SessionErrorCode::ResourceLimit,
            SessionErrorCode::TransportBindingFailed,
            SessionErrorCode::RekeyFailed,
            SessionErrorCode::InternalError,
            SessionErrorCode::UnknownCriticalFrame,
            SessionErrorCode::ProtocolViolation,
            SessionErrorCode::FrameTooLarge,
        ];
        for code in codes {
            let wire = code.to_wire();
            let decoded = SessionErrorCode::from_wire(wire).unwrap();
            assert_eq!(decoded, code);
        }
    }

    #[test]
    fn unknown_wire_value_returns_none() {
        assert_eq!(SessionErrorCode::from_wire(0xDE), None);
    }
}
