//! Resumption ticket issuance and validation.
//!
//! After a successful handshake, the server issues a **resumption ticket**
//! via the `TICKET_ISSUE` frame. The ticket is encrypted with ChaCha20-Poly1305
//! using a key derived from the `resumption_secret`.
//!
//! On reconnection, the client presents the opaque ticket in `ClientInit`.
//! The server decrypts, validates constraints (expiry, policy epoch),
//! and optionally skips full DH if the ticket is fresh.

use chacha20poly1305::{
    aead::{Aead, KeyInit},
    ChaCha20Poly1305, Nonce,
};

/// A resumption ticket (plaintext, before sealing).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResumptionTicket {
    /// Client identifier or cohort hash.
    pub client_id: [u8; 16],
    /// Node or cluster scope identifier.
    pub node_scope: [u8; 16],
    /// Policy epoch at issuance time.
    pub policy_epoch: u64,
    /// Negotiated capabilities (wire IDs).
    pub capabilities: Vec<u16>,
    /// Expiration timestamp (Unix seconds).
    pub expiry_unix: u64,
    /// Anti-replay nonce.
    pub nonce: [u8; 12],
}

impl ResumptionTicket {
    /// Serialize to bytes.
    pub fn encode(&self) -> Vec<u8> {
        let mut buf = Vec::with_capacity(64);
        buf.extend_from_slice(&self.client_id);
        buf.extend_from_slice(&self.node_scope);
        buf.extend_from_slice(&self.policy_epoch.to_be_bytes());
        let cap_count = self.capabilities.len() as u16;
        buf.extend_from_slice(&cap_count.to_be_bytes());
        for cap in &self.capabilities {
            buf.extend_from_slice(&cap.to_be_bytes());
        }
        buf.extend_from_slice(&self.expiry_unix.to_be_bytes());
        buf.extend_from_slice(&self.nonce);
        buf
    }

    /// Deserialize from bytes.
    pub fn decode(data: &[u8]) -> Result<Self, TicketError> {
        if data.len() < 16 + 16 + 8 + 2 + 8 + 12 {
            return Err(TicketError::Malformed);
        }

        let mut pos = 0;
        let mut client_id = [0u8; 16];
        client_id.copy_from_slice(&data[pos..pos + 16]);
        pos += 16;

        let mut node_scope = [0u8; 16];
        node_scope.copy_from_slice(&data[pos..pos + 16]);
        pos += 16;

        let policy_epoch = u64::from_be_bytes(data[pos..pos + 8].try_into().unwrap());
        pos += 8;

        let cap_count = u16::from_be_bytes(data[pos..pos + 2].try_into().unwrap()) as usize;
        pos += 2;

        if data.len() < pos + cap_count * 2 + 8 + 12 {
            return Err(TicketError::Malformed);
        }

        let mut capabilities = Vec::with_capacity(cap_count);
        for _ in 0..cap_count {
            let cap = u16::from_be_bytes(data[pos..pos + 2].try_into().unwrap());
            capabilities.push(cap);
            pos += 2;
        }

        let expiry_unix = u64::from_be_bytes(data[pos..pos + 8].try_into().unwrap());
        pos += 8;

        let mut nonce = [0u8; 12];
        nonce.copy_from_slice(&data[pos..pos + 12]);

        Ok(ResumptionTicket {
            client_id,
            node_scope,
            policy_epoch,
            capabilities,
            expiry_unix,
            nonce,
        })
    }
}

/// Seal a ticket into an opaque encrypted blob.
///
/// Uses the `resumption_secret` as the AEAD key and the ticket's
/// own nonce field as the AEAD nonce.
pub fn seal_ticket(
    resumption_secret: &[u8; 32],
    ticket: &ResumptionTicket,
) -> Result<Vec<u8>, TicketError> {
    let cipher = ChaCha20Poly1305::new_from_slice(resumption_secret)
        .map_err(|_| TicketError::CryptoError)?;
    let nonce = Nonce::from(ticket.nonce);
    let plaintext = ticket.encode();
    let ciphertext = cipher
        .encrypt(&nonce, plaintext.as_slice())
        .map_err(|_| TicketError::CryptoError)?;

    // Prepend the nonce so the server can decrypt without external state
    let mut sealed = Vec::with_capacity(12 + ciphertext.len());
    sealed.extend_from_slice(&ticket.nonce);
    sealed.extend_from_slice(&ciphertext);
    Ok(sealed)
}

/// Open a sealed ticket blob.
///
/// Returns the plaintext ticket and validates basic structure.
pub fn open_ticket(
    resumption_secret: &[u8; 32],
    sealed: &[u8],
) -> Result<ResumptionTicket, TicketError> {
    if sealed.len() < 12 + 16 {
        return Err(TicketError::Malformed);
    }
    let nonce = Nonce::from_slice(&sealed[..12]);
    let ciphertext = &sealed[12..];

    let cipher = ChaCha20Poly1305::new_from_slice(resumption_secret)
        .map_err(|_| TicketError::CryptoError)?;
    let plaintext = cipher
        .decrypt(nonce, ciphertext)
        .map_err(|_| TicketError::DecryptionFailed)?;

    ResumptionTicket::decode(&plaintext)
}

/// Validate a ticket against current server state.
pub fn validate_ticket(
    ticket: &ResumptionTicket,
    current_policy_epoch: u64,
    now_unix: u64,
) -> Result<(), TicketError> {
    if now_unix > ticket.expiry_unix {
        return Err(TicketError::Expired);
    }
    if ticket.policy_epoch != current_policy_epoch {
        return Err(TicketError::PolicyEpochMismatch {
            ticket_epoch: ticket.policy_epoch,
            current_epoch: current_policy_epoch,
        });
    }
    Ok(())
}

/// `TICKET_ISSUE` frame payload (wraps the sealed ticket blob).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TicketIssueFrame {
    pub sealed_ticket: Vec<u8>,
}

impl TicketIssueFrame {
    pub fn encode(&self, buf: &mut Vec<u8>) {
        let len = self.sealed_ticket.len() as u32;
        buf.extend_from_slice(&len.to_be_bytes());
        buf.extend_from_slice(&self.sealed_ticket);
    }

    pub fn decode(input: &[u8]) -> Result<Self, TicketError> {
        if input.len() < 4 {
            return Err(TicketError::Malformed);
        }
        let len = u32::from_be_bytes(input[..4].try_into().unwrap()) as usize;
        if input.len() - 4 < len {
            return Err(TicketError::Malformed);
        }
        let sealed_ticket = input[4..4 + len].to_vec();
        Ok(TicketIssueFrame { sealed_ticket })
    }
}

/// Ticket errors.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum TicketError {
    #[error("ticket is malformed")]
    Malformed,
    #[error("ticket has expired")]
    Expired,
    #[error("policy epoch mismatch: ticket={ticket_epoch}, current={current_epoch}")]
    PolicyEpochMismatch { ticket_epoch: u64, current_epoch: u64 },
    #[error("ticket decryption failed (tampered or wrong key)")]
    DecryptionFailed,
    #[error("cryptographic error")]
    CryptoError,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_ticket() -> ResumptionTicket {
        ResumptionTicket {
            client_id: [0xAA; 16],
            node_scope: [0xBB; 16],
            policy_epoch: 42,
            capabilities: vec![0x01, 0x02, 0x03],
            expiry_unix: 1_700_000_000,
            nonce: [0xCC; 12],
        }
    }

    #[test]
    fn ticket_encode_decode_roundtrip() {
        let ticket = test_ticket();
        let encoded = ticket.encode();
        let decoded = ResumptionTicket::decode(&encoded).unwrap();
        assert_eq!(decoded, ticket);
    }

    #[test]
    fn seal_open_roundtrip() {
        let secret = [0x42u8; 32];
        let ticket = test_ticket();
        let sealed = seal_ticket(&secret, &ticket).unwrap();
        let opened = open_ticket(&secret, &sealed).unwrap();
        assert_eq!(opened, ticket);
    }

    #[test]
    fn wrong_secret_rejected() {
        let ticket = test_ticket();
        let sealed = seal_ticket(&[0x42u8; 32], &ticket).unwrap();
        let result = open_ticket(&[0x43u8; 32], &sealed);
        assert_eq!(result, Err(TicketError::DecryptionFailed));
    }

    #[test]
    fn tampered_ticket_rejected() {
        let secret = [0x42u8; 32];
        let ticket = test_ticket();
        let mut sealed = seal_ticket(&secret, &ticket).unwrap();
        sealed[20] ^= 0xFF;
        let result = open_ticket(&secret, &sealed);
        assert_eq!(result, Err(TicketError::DecryptionFailed));
    }

    #[test]
    fn expired_ticket_rejected() {
        let ticket = test_ticket();
        let result = validate_ticket(&ticket, 42, 2_000_000_000); // way past expiry
        assert_eq!(result, Err(TicketError::Expired));
    }

    #[test]
    fn policy_epoch_mismatch_rejected() {
        let ticket = test_ticket();
        let result = validate_ticket(&ticket, 99, 1_600_000_000);
        assert_eq!(result, Err(TicketError::PolicyEpochMismatch {
            ticket_epoch: 42,
            current_epoch: 99,
        }));
    }

    #[test]
    fn valid_ticket_accepted() {
        let ticket = test_ticket();
        let result = validate_ticket(&ticket, 42, 1_600_000_000);
        assert!(result.is_ok());
    }

    #[test]
    fn ticket_issue_frame_roundtrip() {
        let frame = TicketIssueFrame {
            sealed_ticket: vec![0x01, 0x02, 0x03, 0x04],
        };
        let mut buf = Vec::new();
        frame.encode(&mut buf);
        let decoded = TicketIssueFrame::decode(&buf).unwrap();
        assert_eq!(decoded, frame);
    }
}
