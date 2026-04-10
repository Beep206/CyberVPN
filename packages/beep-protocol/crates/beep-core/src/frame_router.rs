//! Frame routing for post-handshake frame dispatch.
//!
//! Classifies incoming decrypted frames by their `FrameType` and returns
//! a structured action for the session orchestrator.

use beep_core_types::FrameType;

/// What the session should do with a received frame.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FrameAction {
    /// Stream data payload.
    StreamData(Vec<u8>),
    /// Stream open request.
    StreamOpen(Vec<u8>),
    /// Stream close notification.
    StreamClose(Vec<u8>),
    /// Datagram payload.
    Datagram(Vec<u8>),
    /// Flow credit update.
    FlowCredit(Vec<u8>),
    /// Key update request.
    KeyUpdate(Vec<u8>),
    /// Session close request.
    SessionClose(Vec<u8>),
    /// Resumption ticket issued by peer.
    TicketIssue(Vec<u8>),
    /// Policy frame (route set, DNS config).
    Policy { frame_type: FrameType, payload: Vec<u8> },
    /// Telemetry frame (informational, not required to process).
    Telemetry { frame_type: FrameType, payload: Vec<u8> },
    /// Unknown ignorable frame — skip silently.
    Ignored(FrameType),
}

/// Error from frame routing.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum FrameRouteError {
    #[error("unknown critical frame type: {0}")]
    UnknownCritical(FrameType),
    #[error("handshake frame received post-handshake: {0}")]
    UnexpectedHandshake(FrameType),
}

/// Route a decrypted frame to the appropriate handler.
///
/// Called after AEAD decryption to determine what action the session
/// orchestrator should take.
pub fn route_frame(
    frame_type: FrameType,
    payload: Vec<u8>,
) -> Result<FrameAction, FrameRouteError> {
    match frame_type {
        // Handshake frames should not appear after session is open
        ft if ft.is_handshake() => {
            Err(FrameRouteError::UnexpectedHandshake(ft))
        }

        // Session management
        FrameType::KEY_UPDATE => Ok(FrameAction::KeyUpdate(payload)),
        FrameType::SESSION_CLOSE => Ok(FrameAction::SessionClose(payload)),
        FrameType::TICKET_ISSUE => Ok(FrameAction::TicketIssue(payload)),
        FrameType::SESSION_UPDATE => Ok(FrameAction::Ignored(frame_type)), // future use

        // Stream and datagram
        FrameType::STREAM_OPEN => Ok(FrameAction::StreamOpen(payload)),
        FrameType::STREAM_CLOSE => Ok(FrameAction::StreamClose(payload)),
        FrameType::STREAM_DATA => Ok(FrameAction::StreamData(payload)),
        FrameType::FLOW_CREDIT => Ok(FrameAction::FlowCredit(payload)),
        FrameType::DATAGRAM_CLASS => Ok(FrameAction::Datagram(payload)),

        // Policy
        FrameType::ROUTE_SET | FrameType::DNS_CONFIG => {
            Ok(FrameAction::Policy { frame_type, payload })
        }

        // Telemetry (all ignorable by convention)
        FrameType::HEALTH_SUMMARY | FrameType::ERROR_REPORT | FrameType::TRACE_TOKEN => {
            Ok(FrameAction::Telemetry { frame_type, payload })
        }

        // Unknown frames
        ft if ft.is_ignorable() => Ok(FrameAction::Ignored(ft)),
        ft => Err(FrameRouteError::UnknownCritical(ft)),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stream_data_routes() {
        let action = route_frame(FrameType::STREAM_DATA, vec![1, 2, 3]).unwrap();
        assert_eq!(action, FrameAction::StreamData(vec![1, 2, 3]));
    }

    #[test]
    fn key_update_routes() {
        let action = route_frame(FrameType::KEY_UPDATE, vec![]).unwrap();
        assert_eq!(action, FrameAction::KeyUpdate(vec![]));
    }

    #[test]
    fn session_close_routes() {
        let action = route_frame(FrameType::SESSION_CLOSE, vec![0x01]).unwrap();
        assert_eq!(action, FrameAction::SessionClose(vec![0x01]));
    }

    #[test]
    fn telemetry_routes() {
        let action = route_frame(FrameType::HEALTH_SUMMARY, vec![0xAA]).unwrap();
        assert!(matches!(action, FrameAction::Telemetry { .. }));
    }

    #[test]
    fn unknown_ignorable_skipped() {
        let action = route_frame(FrameType(0xF1), vec![]).unwrap(); // odd = ignorable
        assert!(matches!(action, FrameAction::Ignored(_)));
    }

    #[test]
    fn unknown_critical_rejected() {
        let result = route_frame(FrameType(0xF0), vec![]); // even = critical
        assert!(matches!(result, Err(FrameRouteError::UnknownCritical(_))));
    }

    #[test]
    fn handshake_frame_post_open_rejected() {
        let result = route_frame(FrameType::CLIENT_INIT, vec![]);
        assert!(matches!(result, Err(FrameRouteError::UnexpectedHandshake(_))));
    }

    #[test]
    fn flow_credit_routes() {
        let action = route_frame(FrameType::FLOW_CREDIT, vec![0x03]).unwrap();
        assert_eq!(action, FrameAction::FlowCredit(vec![0x03]));
    }

    #[test]
    fn ticket_issue_routes() {
        let action = route_frame(FrameType::TICKET_ISSUE, vec![]).unwrap();
        assert_eq!(action, FrameAction::TicketIssue(vec![]));
    }

    #[test]
    fn datagram_routes() {
        let action = route_frame(FrameType::DATAGRAM_CLASS, vec![0xDE]).unwrap();
        assert_eq!(action, FrameAction::Datagram(vec![0xDE]));
    }

    #[test]
    fn route_set_routes() {
        let action = route_frame(FrameType::ROUTE_SET, vec![0x01]).unwrap();
        assert!(matches!(action, FrameAction::Policy { .. }));
    }

    #[test]
    fn dns_config_routes() {
        let action = route_frame(FrameType::DNS_CONFIG, vec![0x02]).unwrap();
        assert!(matches!(action, FrameAction::Policy { .. }));
    }
}
