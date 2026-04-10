//! Handshake state machine.
//!
//! Validates state transitions based on [`Role`] and incoming events.
//! The machine enforces the 4-flight handshake order and rejects
//! out-of-sequence or role-inappropriate events.

use crate::error::SessionError;

use super::state::{HandshakePhase, Role, SessionState};

/// Events that drive state machine transitions.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Event {
    /// Outer transport connection established.
    OuterTransportReady,

    // ── Handshake events ────────────────────────────────────────────
    /// ClientInit sent (Initiator) or received (Responder).
    ClientInitProcessed,
    /// ServerInit sent (Responder) or received (Initiator).
    ServerInitProcessed,
    /// ClientFinish sent (Initiator) or received (Responder).
    ClientFinishProcessed,
    /// ServerFinish sent (Responder) or received (Initiator).
    ServerFinishProcessed,
    /// Retry received by the Initiator — resets to OuterConnected.
    RetryReceived,

    // ── Session lifecycle events ────────────────────────────────────
    /// Rekey initiated.
    RekeyInitiated,
    /// Rekey completed successfully.
    RekeyCompleted,
    /// Resumption initiated.
    ResumeInitiated,
    /// Resumption completed successfully.
    ResumeCompleted,
    /// Graceful close initiated.
    CloseInitiated,
    /// Close completed (final frames exchanged).
    CloseCompleted,

    // ── Error events ────────────────────────────────────────────────
    /// A fatal error occurred.
    FatalError,
}

/// The handshake and session state machine.
///
/// Enforces valid state transitions for a given [`Role`].
/// All transition validation is explicit — no implicit state changes.
#[derive(Debug)]
pub struct StateMachine {
    role: Role,
    state: SessionState,
}

impl StateMachine {
    /// Create a new state machine in the Idle state.
    pub fn new(role: Role) -> Self {
        Self {
            role,
            state: SessionState::default(),
        }
    }

    /// Current state.
    pub fn state(&self) -> SessionState {
        self.state
    }

    /// Role of this endpoint.
    pub fn role(&self) -> Role {
        self.role
    }

    /// Process an event and transition to the next state.
    ///
    /// Returns the new state on success, or an error if the transition
    /// is invalid for the current state and role.
    pub fn process(&mut self, event: Event) -> Result<SessionState, SessionError> {
        let next = self.next_state(event)?;
        self.state = next;
        Ok(next)
    }

    /// Compute the next state without mutating. Used for validation.
    fn next_state(&self, event: Event) -> Result<SessionState, SessionError> {
        use Event::*;
        use HandshakePhase::*;
        use SessionState::*;

        // Fatal error from any non-terminal state
        if event == FatalError && !self.state.is_terminal() {
            return Ok(Failed);
        }

        match (self.state, event, self.role) {
            // ── Handshake flow ──────────────────────────────────────

            // Idle → OuterConnected (both roles)
            (Handshake(Idle), OuterTransportReady, _) => {
                Ok(Handshake(OuterConnected))
            }

            // OuterConnected → Flight1 (ClientInit)
            // Initiator sends, Responder receives
            (Handshake(OuterConnected), ClientInitProcessed, _) => {
                Ok(Handshake(Flight1))
            }

            // Flight1 → Flight2 (ServerInit)
            // Responder sends, Initiator receives
            (Handshake(Flight1), ServerInitProcessed, _) => {
                Ok(Handshake(Flight2))
            }

            // Flight2 → Flight3 (ClientFinish)
            // Initiator sends, Responder receives
            (Handshake(Flight2), ClientFinishProcessed, _) => {
                Ok(Handshake(Flight3))
            }

            // Flight3 → Open (ServerFinish)
            // Responder sends, Initiator receives
            (Handshake(Flight3), ServerFinishProcessed, _) => {
                Ok(Open)
            }

            // Retry: resets initiator back to OuterConnected for re-handshake
            (Handshake(Flight1), RetryReceived, Role::Initiator) => {
                Ok(Handshake(OuterConnected))
            }

            // ── Session lifecycle ───────────────────────────────────

            (Open, RekeyInitiated, _) => Ok(Rekeying),
            (Rekeying, RekeyCompleted, _) => Ok(Open),

            (Open, ResumeInitiated, _) => Ok(Resuming),
            (Resuming, ResumeCompleted, _) => Ok(Open),

            (Open, CloseInitiated, _) => Ok(Closing),
            (Closing, CloseCompleted, _) => Ok(Closed),

            // ── Invalid transitions ─────────────────────────────────
            _ => Err(SessionError::InvalidTransition(format!(
                "cannot process {:?} in state {} as {}",
                event, self.state, self.role,
            ))),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use Event::*;

    // ── Normal handshake flow ───────────────────────────────────────────

    #[test]
    fn initiator_full_handshake() {
        let mut sm = StateMachine::new(Role::Initiator);

        assert_eq!(sm.state(), SessionState::Handshake(HandshakePhase::Idle));
        sm.process(OuterTransportReady).unwrap();
        assert_eq!(sm.state(), SessionState::Handshake(HandshakePhase::OuterConnected));
        sm.process(ClientInitProcessed).unwrap();
        assert_eq!(sm.state(), SessionState::Handshake(HandshakePhase::Flight1));
        sm.process(ServerInitProcessed).unwrap();
        assert_eq!(sm.state(), SessionState::Handshake(HandshakePhase::Flight2));
        sm.process(ClientFinishProcessed).unwrap();
        assert_eq!(sm.state(), SessionState::Handshake(HandshakePhase::Flight3));
        sm.process(ServerFinishProcessed).unwrap();
        assert_eq!(sm.state(), SessionState::Open);
    }

    #[test]
    fn responder_full_handshake() {
        let mut sm = StateMachine::new(Role::Responder);

        sm.process(OuterTransportReady).unwrap();
        sm.process(ClientInitProcessed).unwrap();
        sm.process(ServerInitProcessed).unwrap();
        sm.process(ClientFinishProcessed).unwrap();
        sm.process(ServerFinishProcessed).unwrap();
        assert_eq!(sm.state(), SessionState::Open);
    }

    // ── Retry flow ──────────────────────────────────────────────────────

    #[test]
    fn initiator_retry_resets_to_outer_connected() {
        let mut sm = StateMachine::new(Role::Initiator);
        sm.process(OuterTransportReady).unwrap();
        sm.process(ClientInitProcessed).unwrap();
        assert_eq!(sm.state(), SessionState::Handshake(HandshakePhase::Flight1));

        // Server sends retry instead of ServerInit
        sm.process(RetryReceived).unwrap();
        assert_eq!(sm.state(), SessionState::Handshake(HandshakePhase::OuterConnected));

        // Can retry the handshake
        sm.process(ClientInitProcessed).unwrap();
        sm.process(ServerInitProcessed).unwrap();
        sm.process(ClientFinishProcessed).unwrap();
        sm.process(ServerFinishProcessed).unwrap();
        assert_eq!(sm.state(), SessionState::Open);
    }

    #[test]
    fn responder_cannot_receive_retry() {
        let mut sm = StateMachine::new(Role::Responder);
        sm.process(OuterTransportReady).unwrap();
        sm.process(ClientInitProcessed).unwrap();

        let result = sm.process(RetryReceived);
        assert!(result.is_err());
    }

    // ── Session lifecycle ───────────────────────────────────────────────

    #[test]
    fn rekey_cycle() {
        let mut sm = open_session(Role::Initiator);
        sm.process(RekeyInitiated).unwrap();
        assert_eq!(sm.state(), SessionState::Rekeying);
        sm.process(RekeyCompleted).unwrap();
        assert_eq!(sm.state(), SessionState::Open);
    }

    #[test]
    fn resume_cycle() {
        let mut sm = open_session(Role::Responder);
        sm.process(ResumeInitiated).unwrap();
        assert_eq!(sm.state(), SessionState::Resuming);
        sm.process(ResumeCompleted).unwrap();
        assert_eq!(sm.state(), SessionState::Open);
    }

    #[test]
    fn graceful_close() {
        let mut sm = open_session(Role::Initiator);
        sm.process(CloseInitiated).unwrap();
        assert_eq!(sm.state(), SessionState::Closing);
        sm.process(CloseCompleted).unwrap();
        assert_eq!(sm.state(), SessionState::Closed);
        assert!(sm.state().is_terminal());
    }

    // ── Error handling ──────────────────────────────────────────────────

    #[test]
    fn fatal_error_from_handshake() {
        let mut sm = StateMachine::new(Role::Initiator);
        sm.process(OuterTransportReady).unwrap();
        sm.process(FatalError).unwrap();
        assert_eq!(sm.state(), SessionState::Failed);
        assert!(sm.state().is_terminal());
    }

    #[test]
    fn fatal_error_from_open() {
        let mut sm = open_session(Role::Initiator);
        sm.process(FatalError).unwrap();
        assert_eq!(sm.state(), SessionState::Failed);
    }

    #[test]
    fn no_transitions_from_terminal() {
        let mut sm = open_session(Role::Initiator);
        sm.process(FatalError).unwrap();

        // All events should fail from terminal state
        assert!(sm.process(OuterTransportReady).is_err());
        assert!(sm.process(CloseInitiated).is_err());
        assert!(sm.process(RekeyInitiated).is_err());
    }

    // ── Out-of-order transitions ────────────────────────────────────────

    #[test]
    fn cannot_skip_handshake_flights() {
        let mut sm = StateMachine::new(Role::Initiator);
        sm.process(OuterTransportReady).unwrap();

        // Cannot jump to ServerInit without ClientInit
        assert!(sm.process(ServerInitProcessed).is_err());
    }

    #[test]
    fn cannot_rekey_during_handshake() {
        let mut sm = StateMachine::new(Role::Initiator);
        sm.process(OuterTransportReady).unwrap();
        assert!(sm.process(RekeyInitiated).is_err());
    }

    #[test]
    fn cannot_initiate_handshake_when_open() {
        let mut sm = open_session(Role::Initiator);
        assert!(sm.process(ClientInitProcessed).is_err());
    }

    // ── Helper ──────────────────────────────────────────────────────────

    fn open_session(role: Role) -> StateMachine {
        let mut sm = StateMachine::new(role);
        sm.process(OuterTransportReady).unwrap();
        sm.process(ClientInitProcessed).unwrap();
        sm.process(ServerInitProcessed).unwrap();
        sm.process(ClientFinishProcessed).unwrap();
        sm.process(ServerFinishProcessed).unwrap();
        assert_eq!(sm.state(), SessionState::Open);
        sm
    }
}
