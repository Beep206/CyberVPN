//! Epoch-based rekey mechanism for the Beep session core.
//!
//! After session establishment, either side can initiate a key update
//! by sending a `KEY_UPDATE` frame. The new epoch's keys are derived
//! from the current epoch's keys using HKDF, ensuring forward secrecy.
//!
//! ```text
//! Epoch N keys + "beep v1 rekey epoch {N+1}"
//!   → HKDF-Extract → new_epoch_secret
//!   → HKDF-Expand  → new control_key, stream_key, datagram_key + IVs
//! ```

use hkdf::Hkdf;
use sha2::Sha256;

use crate::cipher::{TrafficClass, TrafficKeyPair};
use crate::key_schedule::SessionKeys;

/// Current rekey state.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RekeyPhase {
    /// Normal operation, no rekey in progress.
    Stable,
    /// We sent KEY_UPDATE, waiting for peer's acknowledgment.
    Initiated,
    /// We received KEY_UPDATE, will send ack.
    PeerInitiated,
}

/// Rekey manager.
pub struct RekeyState {
    /// Current key epoch (starts at 0 after handshake).
    epoch: u64,
    /// Current session master secret (used as input for next epoch derivation).
    current_secret: [u8; 32],
    /// Rekey phase.
    phase: RekeyPhase,
}

impl RekeyState {
    /// Create from initial session keys.
    pub fn new(session_keys: &SessionKeys) -> Self {
        Self {
            epoch: 0,
            current_secret: session_keys.session_master_secret,
            phase: RekeyPhase::Stable,
        }
    }

    /// Current epoch number.
    pub fn epoch(&self) -> u64 {
        self.epoch
    }

    /// Current phase.
    pub fn phase(&self) -> RekeyPhase {
        self.phase
    }

    /// Initiate a rekey. Returns the new epoch number for the KEY_UPDATE frame.
    pub fn initiate(&mut self) -> Result<u64, RekeyError> {
        if self.phase != RekeyPhase::Stable {
            return Err(RekeyError::RekeyAlreadyInProgress);
        }
        self.phase = RekeyPhase::Initiated;
        Ok(self.epoch + 1)
    }

    /// Process a received KEY_UPDATE from the peer.
    pub fn process_peer_update(&mut self, new_epoch: u64) -> Result<(), RekeyError> {
        if new_epoch != self.epoch + 1 {
            return Err(RekeyError::EpochMismatch {
                expected: self.epoch + 1,
                received: new_epoch,
            });
        }
        if self.phase == RekeyPhase::Initiated {
            // Both sides initiated simultaneously — our initiate wins
            // (just complete the transition)
        }
        self.phase = RekeyPhase::PeerInitiated;
        Ok(())
    }

    /// Complete the rekey: derive new epoch keys and return them.
    ///
    /// Both `initiate()` and `process_peer_update()` lead here.
    pub fn complete(&mut self) -> Result<EpochKeys, RekeyError> {
        if self.phase == RekeyPhase::Stable {
            return Err(RekeyError::NoRekeyInProgress);
        }

        let new_epoch = self.epoch + 1;
        let epoch_keys = derive_epoch_keys(&self.current_secret, new_epoch);

        // Update state
        self.current_secret = epoch_keys.epoch_secret;
        self.epoch = new_epoch;
        self.phase = RekeyPhase::Stable;

        Ok(epoch_keys)
    }
}

/// Keys for a new epoch.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EpochKeys {
    /// The new epoch secret (used as base for next rekey).
    pub epoch_secret: [u8; 32],
    /// New control channel key.
    pub control_key: [u8; 32],
    pub control_iv: [u8; 12],
    /// New stream traffic key.
    pub stream_key: [u8; 32],
    pub stream_iv: [u8; 12],
    /// New datagram traffic key.
    pub datagram_key: [u8; 32],
    pub datagram_iv: [u8; 12],
}

impl EpochKeys {
    /// Create `TrafficKeyPair`s from these epoch keys.
    pub fn to_traffic_keys(&self) -> (TrafficKeyPair, TrafficKeyPair, TrafficKeyPair) {
        (
            TrafficKeyPair::new(self.control_key, self.control_iv, TrafficClass::Control),
            TrafficKeyPair::new(self.stream_key, self.stream_iv, TrafficClass::Stream),
            TrafficKeyPair::new(self.datagram_key, self.datagram_iv, TrafficClass::Datagram),
        )
    }
}

/// Rekey errors.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum RekeyError {
    #[error("rekey already in progress")]
    RekeyAlreadyInProgress,
    #[error("no rekey in progress")]
    NoRekeyInProgress,
    #[error("epoch mismatch: expected {expected}, received {received}")]
    EpochMismatch { expected: u64, received: u64 },
}

// ── Key derivation ──────────────────────────────────────────────────────

fn derive_epoch_keys(current_secret: &[u8; 32], new_epoch: u64) -> EpochKeys {
    let label = format!("beep v1 rekey epoch {new_epoch}");
    let hk = Hkdf::<Sha256>::new(Some(label.as_bytes()), current_secret);

    let expand = |info: &[u8], out: &mut [u8]| {
        hk.expand(info, out).expect("HKDF-Expand: valid length");
    };

    let mut epoch_secret = [0u8; 32];
    expand(b"beep v1 epoch secret", &mut epoch_secret);

    let mut control_key = [0u8; 32];
    expand(b"beep v1 control key", &mut control_key);
    let mut control_iv = [0u8; 12];
    expand(b"beep v1 control iv", &mut control_iv);

    let mut stream_key = [0u8; 32];
    expand(b"beep v1 stream key", &mut stream_key);
    let mut stream_iv = [0u8; 12];
    expand(b"beep v1 stream iv", &mut stream_iv);

    let mut datagram_key = [0u8; 32];
    expand(b"beep v1 datagram key", &mut datagram_key);
    let mut datagram_iv = [0u8; 12];
    expand(b"beep v1 datagram iv", &mut datagram_iv);

    EpochKeys {
        epoch_secret,
        control_key,
        control_iv,
        stream_key,
        stream_iv,
        datagram_key,
        datagram_iv,
    }
}

// ── Wire format for KEY_UPDATE and SESSION_CLOSE ────────────────────────

/// KEY_UPDATE frame payload.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct KeyUpdateFrame {
    /// The new epoch number.
    pub new_epoch: u64,
}

impl KeyUpdateFrame {
    pub fn encode(&self, buf: &mut Vec<u8>) {
        buf.extend_from_slice(&self.new_epoch.to_be_bytes());
    }

    pub fn decode(input: &[u8]) -> Result<Self, RekeyDecodeError> {
        if input.len() < 8 {
            return Err(RekeyDecodeError::Truncated);
        }
        let new_epoch = u64::from_be_bytes(input[..8].try_into().unwrap());
        Ok(KeyUpdateFrame { new_epoch })
    }
}

/// SESSION_CLOSE frame payload.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SessionCloseFrame {
    pub error_code: u32,
    pub reason: Vec<u8>,
}

impl SessionCloseFrame {
    pub fn encode(&self, buf: &mut Vec<u8>) {
        buf.extend_from_slice(&self.error_code.to_be_bytes());
        let reason_len = self.reason.len() as u16;
        buf.extend_from_slice(&reason_len.to_be_bytes());
        buf.extend_from_slice(&self.reason);
    }

    pub fn decode(input: &[u8]) -> Result<Self, RekeyDecodeError> {
        if input.len() < 6 {
            return Err(RekeyDecodeError::Truncated);
        }
        let error_code = u32::from_be_bytes(input[..4].try_into().unwrap());
        let reason_len = u16::from_be_bytes(input[4..6].try_into().unwrap()) as usize;
        if input.len() - 6 < reason_len {
            return Err(RekeyDecodeError::Truncated);
        }
        let reason = input[6..6 + reason_len].to_vec();
        Ok(SessionCloseFrame { error_code, reason })
    }
}

#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum RekeyDecodeError {
    #[error("frame truncated")]
    Truncated,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_session_keys() -> SessionKeys {
        SessionKeys {
            session_master_secret: [0x42u8; 32],
            control_key: [0x01u8; 32],
            control_iv: [0x02u8; 12],
            stream_key: [0x03u8; 32],
            stream_iv: [0x04u8; 12],
            datagram_key: [0x05u8; 32],
            datagram_iv: [0x06u8; 12],
            resumption_secret: [0x07u8; 32],
        }
    }

    #[test]
    fn rekey_epoch_advances() {
        let sk = test_session_keys();
        let mut rs = RekeyState::new(&sk);
        assert_eq!(rs.epoch(), 0);

        let new_epoch = rs.initiate().unwrap();
        assert_eq!(new_epoch, 1);

        let keys = rs.complete().unwrap();
        assert_eq!(rs.epoch(), 1);
        assert_eq!(rs.phase(), RekeyPhase::Stable);

        // Keys should differ from original
        assert_ne!(keys.control_key, sk.control_key);
        assert_ne!(keys.stream_key, sk.stream_key);
    }

    #[test]
    fn peer_initiated_rekey() {
        let sk = test_session_keys();
        let mut rs = RekeyState::new(&sk);

        rs.process_peer_update(1).unwrap();
        assert_eq!(rs.phase(), RekeyPhase::PeerInitiated);

        let keys = rs.complete().unwrap();
        assert_eq!(rs.epoch(), 1);
        assert_ne!(keys.epoch_secret, sk.session_master_secret);
    }

    #[test]
    fn wrong_epoch_rejected() {
        let sk = test_session_keys();
        let mut rs = RekeyState::new(&sk);

        let result = rs.process_peer_update(5);
        assert_eq!(result, Err(RekeyError::EpochMismatch { expected: 1, received: 5 }));
    }

    #[test]
    fn double_initiate_rejected() {
        let sk = test_session_keys();
        let mut rs = RekeyState::new(&sk);

        rs.initiate().unwrap();
        let result = rs.initiate();
        assert_eq!(result, Err(RekeyError::RekeyAlreadyInProgress));
    }

    #[test]
    fn complete_without_initiate_rejected() {
        let sk = test_session_keys();
        let mut rs = RekeyState::new(&sk);

        let result = rs.complete();
        assert_eq!(result, Err(RekeyError::NoRekeyInProgress));
    }

    #[test]
    fn sequential_rekeys_produce_different_keys() {
        let sk = test_session_keys();
        let mut rs = RekeyState::new(&sk);

        rs.initiate().unwrap();
        let keys1 = rs.complete().unwrap();

        rs.initiate().unwrap();
        let keys2 = rs.complete().unwrap();

        assert_ne!(keys1.control_key, keys2.control_key);
        assert_ne!(keys1.epoch_secret, keys2.epoch_secret);
        assert_eq!(rs.epoch(), 2);
    }

    #[test]
    fn both_sides_derive_same_epoch_keys() {
        let sk = test_session_keys();
        let mut rs_a = RekeyState::new(&sk);
        let mut rs_b = RekeyState::new(&sk);

        // A initiates, B accepts
        let epoch = rs_a.initiate().unwrap();
        rs_b.process_peer_update(epoch).unwrap();

        let keys_a = rs_a.complete().unwrap();
        let keys_b = rs_b.complete().unwrap();

        assert_eq!(keys_a.control_key, keys_b.control_key);
        assert_eq!(keys_a.stream_key, keys_b.stream_key);
        assert_eq!(keys_a.datagram_key, keys_b.datagram_key);
        assert_eq!(keys_a.epoch_secret, keys_b.epoch_secret);
    }

    #[test]
    fn key_update_frame_roundtrip() {
        let frame = KeyUpdateFrame { new_epoch: 42 };
        let mut buf = Vec::new();
        frame.encode(&mut buf);
        let decoded = KeyUpdateFrame::decode(&buf).unwrap();
        assert_eq!(decoded, frame);
    }

    #[test]
    fn session_close_frame_roundtrip() {
        let frame = SessionCloseFrame {
            error_code: 0x0001,
            reason: b"graceful shutdown".to_vec(),
        };
        let mut buf = Vec::new();
        frame.encode(&mut buf);
        let decoded = SessionCloseFrame::decode(&buf).unwrap();
        assert_eq!(decoded, frame);
    }
}
