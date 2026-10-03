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

/// Rekey manager with independent send and receive directions.
///
/// Each direction has its own epoch counter and HKDF ratchet chain. Rotating
/// one direction never touches the other, so a `KEY_UPDATE` we send (which
/// advances only our send keys) cannot strand frames the peer already sent
/// under the previous epoch — those still decrypt under our unchanged receive
/// keys. Both chains start from the same session master secret and advance by
/// the same function, so our send-epoch-N keys match the peer's receive-epoch-N
/// keys. The per-direction nonce tag in the cipher keeps the two directions on
/// disjoint nonce streams even when they hold the same epoch.
pub struct RekeyState {
    send_epoch: u64,
    recv_epoch: u64,
    send_secret: [u8; 32],
    recv_secret: [u8; 32],
    /// Send-direction keys derived by `initiate` and installed by `complete`.
    pending_send: Option<EpochKeys>,
}

impl RekeyState {
    /// Create from initial session keys. Both directions start at epoch 0.
    pub fn new(session_keys: &SessionKeys) -> Self {
        Self {
            send_epoch: 0,
            recv_epoch: 0,
            send_secret: session_keys.session_master_secret,
            recv_secret: session_keys.session_master_secret,
            pending_send: None,
        }
    }

    /// Current send-direction epoch.
    pub fn send_epoch(&self) -> u64 {
        self.send_epoch
    }

    /// Current receive-direction epoch.
    pub fn recv_epoch(&self) -> u64 {
        self.recv_epoch
    }

    /// Highest epoch seen in either direction (for metrics/diagnostics).
    pub fn epoch(&self) -> u64 {
        self.send_epoch.max(self.recv_epoch)
    }

    /// Begin a send-direction rekey. Returns the new send epoch to advertise in
    /// the `KEY_UPDATE` frame. The caller seals `KEY_UPDATE` under the *current*
    /// send keys and then calls [`complete`](Self::complete) to install the new
    /// send keys.
    pub fn initiate(&mut self) -> Result<u64, RekeyError> {
        if self.pending_send.is_some() {
            return Err(RekeyError::RekeyAlreadyInProgress);
        }
        let new_epoch = self.send_epoch + 1;
        self.pending_send = Some(derive_epoch_keys(&self.send_secret, new_epoch));
        Ok(new_epoch)
    }

    /// Commit the send-direction rekey: advance the send ratchet and return the
    /// keys to install on the send ciphers.
    pub fn complete(&mut self) -> Result<EpochKeys, RekeyError> {
        let keys = self
            .pending_send
            .take()
            .ok_or(RekeyError::NoRekeyInProgress)?;
        self.send_secret = keys.epoch_secret;
        self.send_epoch += 1;
        Ok(keys)
    }

    /// Process a peer `KEY_UPDATE`: advance the receive ratchet and return the
    /// keys to install on the receive ciphers. Leaves the send direction
    /// untouched.
    pub fn process_peer_update(&mut self, new_epoch: u64) -> Result<EpochKeys, RekeyError> {
        let expected = self.recv_epoch + 1;
        if new_epoch != expected {
            return Err(RekeyError::EpochMismatch {
                expected,
                received: new_epoch,
            });
        }
        let keys = derive_epoch_keys(&self.recv_secret, new_epoch);
        self.recv_secret = keys.epoch_secret;
        self.recv_epoch += 1;
        Ok(keys)
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
    /// Create `TrafficKeyPair`s from these epoch keys for the given role.
    pub fn to_traffic_keys(
        &self,
        is_initiator: bool,
    ) -> (TrafficKeyPair, TrafficKeyPair, TrafficKeyPair) {
        (
            TrafficKeyPair::new(
                self.control_key,
                self.control_iv,
                TrafficClass::Control,
                is_initiator,
            ),
            TrafficKeyPair::new(
                self.stream_key,
                self.stream_iv,
                TrafficClass::Stream,
                is_initiator,
            ),
            TrafficKeyPair::new(
                self.datagram_key,
                self.datagram_iv,
                TrafficClass::Datagram,
                is_initiator,
            ),
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
    fn send_rekey_advances_only_send_epoch() {
        let sk = test_session_keys();
        let mut rs = RekeyState::new(&sk);
        assert_eq!(rs.send_epoch(), 0);
        assert_eq!(rs.recv_epoch(), 0);

        let new_epoch = rs.initiate().unwrap();
        assert_eq!(new_epoch, 1);

        let keys = rs.complete().unwrap();
        assert_eq!(rs.send_epoch(), 1);
        assert_eq!(rs.recv_epoch(), 0, "recv direction must not move");

        assert_ne!(keys.control_key, sk.control_key);
        assert_ne!(keys.stream_key, sk.stream_key);
    }

    #[test]
    fn recv_rekey_advances_only_recv_epoch() {
        let sk = test_session_keys();
        let mut rs = RekeyState::new(&sk);

        let keys = rs.process_peer_update(1).unwrap();
        assert_eq!(rs.recv_epoch(), 1);
        assert_eq!(rs.send_epoch(), 0, "send direction must not move");
        assert_ne!(keys.epoch_secret, sk.session_master_secret);
    }

    #[test]
    fn wrong_recv_epoch_rejected() {
        let sk = test_session_keys();
        let mut rs = RekeyState::new(&sk);

        let result = rs.process_peer_update(5);
        assert_eq!(
            result.err(),
            Some(RekeyError::EpochMismatch {
                expected: 1,
                received: 5
            })
        );
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
    fn sequential_send_rekeys_produce_different_keys() {
        let sk = test_session_keys();
        let mut rs = RekeyState::new(&sk);

        rs.initiate().unwrap();
        let keys1 = rs.complete().unwrap();

        rs.initiate().unwrap();
        let keys2 = rs.complete().unwrap();

        assert_ne!(keys1.control_key, keys2.control_key);
        assert_ne!(keys1.epoch_secret, keys2.epoch_secret);
        assert_eq!(rs.send_epoch(), 2);
    }

    #[test]
    fn send_and_recv_chains_agree_across_peers() {
        // One peer's send chain must match the other peer's recv chain so a
        // frame sealed under send-epoch N opens under recv-epoch N.
        let sk = test_session_keys();
        let mut initiator = RekeyState::new(&sk);
        let mut responder = RekeyState::new(&sk);

        let epoch = initiator.initiate().unwrap();
        let responder_recv = responder.process_peer_update(epoch).unwrap();
        let initiator_send = initiator.complete().unwrap();

        assert_eq!(initiator_send.control_key, responder_recv.control_key);
        assert_eq!(initiator_send.stream_key, responder_recv.stream_key);
        assert_eq!(initiator_send.datagram_key, responder_recv.datagram_key);
        assert_eq!(initiator_send.epoch_secret, responder_recv.epoch_secret);
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
