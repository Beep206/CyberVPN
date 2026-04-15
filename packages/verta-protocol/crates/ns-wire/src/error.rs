use ns_core::ErrorCode;
use thiserror::Error;

#[derive(Debug, Error, Clone, PartialEq, Eq)]
pub enum WireError {
    #[error("truncated input")]
    Truncated,
    #[error("frame payload {actual} exceeds hard limit {limit}")]
    FrameTooLarge { actual: usize, limit: usize },
    #[error("non-canonical varint encoding")]
    NonCanonicalVarInt,
    #[error("varint value {0} exceeds the supported range")]
    VarIntOutOfRange(u64),
    #[error("invalid boolean encoding: {0}")]
    InvalidBoolean(u8),
    #[error("invalid UTF-8 for {field}")]
    InvalidUtf8 { field: &'static str },
    #[error("{field} length {length} exceeds limit {limit}")]
    LengthLimitExceeded {
        field: &'static str,
        length: usize,
        limit: usize,
    },
    #[error("{field} count {count} exceeds limit {limit}")]
    CountLimitExceeded {
        field: &'static str,
        count: u64,
        limit: u64,
    },
    #[error("{field} must not be empty")]
    EmptyField { field: &'static str },
    #[error("unknown value {value} for {field}")]
    UnknownValue {
        field: &'static str,
        value: u64,
    },
    #[error("reserved bits set in {field}: 0x{value:x}")]
    ReservedBits {
        field: &'static str,
        value: u64,
    },
    #[error("{field} must be in range 1..=65535, got {value}")]
    InvalidPort {
        field: &'static str,
        value: u64,
    },
    #[error("{field} length must be {expected}, got {actual}")]
    InvalidFixedLength {
        field: &'static str,
        expected: usize,
        actual: usize,
    },
    #[error("unsupported frame type 0x{0:02x}")]
    UnsupportedFrameType(u64),
}

impl WireError {
    pub fn error_code(&self) -> ErrorCode {
        match self {
            Self::FrameTooLarge { .. } => ErrorCode::FrameTooLarge,
            Self::UnsupportedFrameType(_)
            | Self::ReservedBits { .. }
            | Self::InvalidBoolean(_)
            | Self::InvalidUtf8 { .. }
            | Self::LengthLimitExceeded { .. }
            | Self::CountLimitExceeded { .. }
            | Self::EmptyField { .. }
            | Self::UnknownValue { .. }
            | Self::InvalidPort { .. }
            | Self::InvalidFixedLength { .. }
            | Self::Truncated
            | Self::NonCanonicalVarInt
            | Self::VarIntOutOfRange(_) => ErrorCode::ProtocolViolation,
        }
    }
}
