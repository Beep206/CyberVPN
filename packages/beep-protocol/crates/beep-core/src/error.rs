//! Session-level error types for the Beep core.

use beep_core_types::SessionErrorCode;

/// A session error with context for diagnostics.
#[derive(Debug, thiserror::Error)]
pub enum SessionError {
    /// Protocol error with a wire error code.
    #[error("protocol error: {code}")]
    Protocol {
        code: SessionErrorCode,
        /// Optional human-readable detail (not sent on wire).
        detail: Option<String>,
    },

    /// Invalid state transition attempted.
    #[error("invalid state transition: {0}")]
    InvalidTransition(String),

    /// Frame codec error during session operation.
    #[error("codec error: {0}")]
    Codec(#[from] crate::codec::CodecError),
}

impl SessionError {
    /// Create a protocol error with a code and detail message.
    pub fn protocol(code: SessionErrorCode, detail: impl Into<String>) -> Self {
        Self::Protocol {
            code,
            detail: Some(detail.into()),
        }
    }

    /// Create a protocol error with only a code.
    pub fn protocol_code(code: SessionErrorCode) -> Self {
        Self::Protocol {
            code,
            detail: None,
        }
    }
}
