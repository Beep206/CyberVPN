//! Session state definitions.
//!
//! The state machine tracks both the handshake phase and the established
//! session lifecycle. States are separate from the messages that cause
//! transitions — the [`super::machine::StateMachine`] enforces valid
//! transitions based on [`Role`].

/// The role of a session endpoint.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Role {
    /// Client: initiates the session.
    Initiator,
    /// Node: accepts and terminates the session.
    Responder,
}

impl std::fmt::Display for Role {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Initiator => write!(f, "Initiator"),
            Self::Responder => write!(f, "Responder"),
        }
    }
}

/// Progress through the 4-flight handshake.
///
/// Flight semantics depend on [`Role`]:
/// - **Initiator**: Flight1 = sent ClientInit, Flight2 = received ServerInit,
///   Flight3 = sent ClientFinish, Complete = received ServerFinish.
/// - **Responder**: Flight1 = received ClientInit, Flight2 = sent ServerInit,
///   Flight3 = received ClientFinish, Complete = sent ServerFinish.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum HandshakePhase {
    /// Waiting for outer transport establishment.
    Idle,
    /// Outer transport is connected; ready to begin handshake.
    OuterConnected,
    /// Flight 1 complete (ClientInit).
    Flight1,
    /// Flight 2 complete (ServerInit).
    Flight2,
    /// Flight 3 complete (ClientFinish).
    Flight3,
    /// All flights complete; transitioning to Open.
    Complete,
}

/// The top-level session state.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum SessionState {
    /// Handshake in progress.
    Handshake(HandshakePhase),
    /// Session fully established and carrying traffic.
    Open,
    /// Key update in progress.
    Rekeying,
    /// Resumption in progress.
    Resuming,
    /// Graceful close initiated.
    Closing,
    /// Terminal: session ended normally.
    Closed,
    /// Terminal: session ended due to error.
    Failed,
}

impl SessionState {
    /// Returns `true` if the session is in a terminal state.
    pub const fn is_terminal(&self) -> bool {
        matches!(self, Self::Closed | Self::Failed)
    }

    /// Returns `true` if the session is fully established.
    pub const fn is_open(&self) -> bool {
        matches!(self, Self::Open)
    }

    /// Returns `true` if the session is still handshaking.
    pub const fn is_handshake(&self) -> bool {
        matches!(self, Self::Handshake(_))
    }
}

impl Default for SessionState {
    fn default() -> Self {
        Self::Handshake(HandshakePhase::Idle)
    }
}

impl std::fmt::Display for SessionState {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Handshake(phase) => write!(f, "Handshake({phase:?})"),
            Self::Open => write!(f, "Open"),
            Self::Rekeying => write!(f, "Rekeying"),
            Self::Resuming => write!(f, "Resuming"),
            Self::Closing => write!(f, "Closing"),
            Self::Closed => write!(f, "Closed"),
            Self::Failed => write!(f, "Failed"),
        }
    }
}
