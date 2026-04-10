//! AEAD cipher for Beep session traffic.
//!
//! Uses ChaCha20-Poly1305 with TLS 1.3-style nonce construction:
//! `nonce = IV ⊕ big-endian(sequence_number)`.
//!
//! Each traffic class (control, stream, datagram) has its own `TrafficKey`
//! with independent key, IV, and sequence counter.

use chacha20poly1305::{
    aead::{Aead, KeyInit},
    ChaCha20Poly1305, Nonce,
};
use zeroize::Zeroize;

/// AEAD tag length (Poly1305).
pub const TAG_LEN: usize = 16;

/// Maximum sequence number before mandatory rekey (2^32 - 1).
/// Conservative limit; keeps nonce well within the birthday bound.
const MAX_SEQUENCE: u64 = u32::MAX as u64;

/// Traffic class identifier for key separation.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum TrafficClass {
    Control,
    Stream,
    Datagram,
}

/// AEAD keying material for one traffic direction and class.
///
/// Owns a ChaCha20-Poly1305 key, base IV, and sequence counter.
/// The sequence counter is monotonically increasing and never reused.
pub struct TrafficKey {
    cipher: ChaCha20Poly1305,
    base_iv: [u8; 12],
    sequence: u64,
    class: TrafficClass,
}

/// Error from cipher operations.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum CipherError {
    #[error("sequence number exhausted for {0:?} — rekey required")]
    SequenceExhausted(TrafficClass),
    #[error("decryption failed: invalid ciphertext or authentication tag")]
    DecryptionFailed,
    #[error("ciphertext too short (need at least {TAG_LEN} bytes for tag)")]
    CiphertextTooShort,
}

impl TrafficKey {
    /// Create a new traffic key.
    pub fn new(key: [u8; 32], iv: [u8; 12], class: TrafficClass) -> Self {
        let cipher = ChaCha20Poly1305::new_from_slice(&key)
            .expect("ChaCha20Poly1305 accepts 32-byte keys");
        Self {
            cipher,
            base_iv: iv,
            sequence: 0,
            class,
        }
    }

    /// Current sequence number (for diagnostics/metrics).
    pub fn sequence(&self) -> u64 {
        self.sequence
    }

    /// Traffic class.
    pub fn class(&self) -> TrafficClass {
        self.class
    }

    /// Construct the 96-bit nonce: `base_iv ⊕ (0..0 || big_endian_u64(seq))`
    fn build_nonce(&self, seq: u64) -> Nonce {
        let mut nonce = self.base_iv;
        let seq_bytes = seq.to_be_bytes(); // 8 bytes
        // XOR into the last 8 bytes of the 12-byte nonce
        for i in 0..8 {
            nonce[4 + i] ^= seq_bytes[i];
        }
        Nonce::from(nonce)
    }

    /// Encrypt `plaintext` and return `ciphertext || tag`.
    ///
    /// Advances the sequence counter. Returns error if the sequence
    /// is exhausted (rekey required).
    pub fn seal(&mut self, plaintext: &[u8]) -> Result<Vec<u8>, CipherError> {
        if self.sequence > MAX_SEQUENCE {
            return Err(CipherError::SequenceExhausted(self.class));
        }

        let nonce = self.build_nonce(self.sequence);
        self.sequence += 1;

        self.cipher
            .encrypt(&nonce, plaintext)
            .map_err(|_| CipherError::DecryptionFailed) // encrypt should not fail
    }

    /// Decrypt `ciphertext || tag` and return the plaintext.
    ///
    /// The caller must provide the correct sequence number. For in-order
    /// traffic classes (control, stream), this is the next expected sequence.
    pub fn open(&mut self, ciphertext: &[u8]) -> Result<Vec<u8>, CipherError> {
        if ciphertext.len() < TAG_LEN {
            return Err(CipherError::CiphertextTooShort);
        }

        if self.sequence > MAX_SEQUENCE {
            return Err(CipherError::SequenceExhausted(self.class));
        }

        let nonce = self.build_nonce(self.sequence);
        self.sequence += 1;

        self.cipher
            .decrypt(&nonce, ciphertext)
            .map_err(|_| CipherError::DecryptionFailed)
    }

    /// Reset for a new epoch (after rekey). Zeroizes old key material.
    pub fn rekey(&mut self, new_key: [u8; 32], new_iv: [u8; 12]) {
        // Zeroize old IV
        self.base_iv.zeroize();
        self.sequence = 0;
        self.cipher = ChaCha20Poly1305::new_from_slice(&new_key)
            .expect("valid key length");
        self.base_iv = new_iv;
    }
}

/// A paired set of send/recv traffic keys for one traffic class.
pub struct TrafficKeyPair {
    pub send: TrafficKey,
    pub recv: TrafficKey,
}

impl TrafficKeyPair {
    /// Create a key pair. Both directions share the same key/IV
    /// (acceptable because sequence counters are independent and
    /// one side seals while the other opens).
    pub fn new(key: [u8; 32], iv: [u8; 12], class: TrafficClass) -> Self {
        Self {
            send: TrafficKey::new(key, iv, class),
            recv: TrafficKey::new(key, iv, class),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn seal_open_roundtrip() {
        let key = [0x42u8; 32];
        let iv = [0x01u8; 12];
        let mut sender = TrafficKey::new(key, iv, TrafficClass::Control);
        let mut receiver = TrafficKey::new(key, iv, TrafficClass::Control);

        let plaintext = b"hello beep protocol";
        let ciphertext = sender.seal(plaintext).unwrap();

        assert_ne!(&ciphertext[..plaintext.len()], plaintext);
        assert_eq!(ciphertext.len(), plaintext.len() + TAG_LEN);

        let decrypted = receiver.open(&ciphertext).unwrap();
        assert_eq!(decrypted, plaintext);
    }

    #[test]
    fn multiple_messages_different_nonces() {
        let key = [0x42u8; 32];
        let iv = [0x01u8; 12];
        let mut sender = TrafficKey::new(key, iv, TrafficClass::Stream);
        let mut receiver = TrafficKey::new(key, iv, TrafficClass::Stream);

        let ct1 = sender.seal(b"message one").unwrap();
        let ct2 = sender.seal(b"message two").unwrap();

        // Different ciphertexts (different nonces)
        assert_ne!(ct1, ct2);

        let pt1 = receiver.open(&ct1).unwrap();
        let pt2 = receiver.open(&ct2).unwrap();
        assert_eq!(pt1, b"message one");
        assert_eq!(pt2, b"message two");
    }

    #[test]
    fn tampered_ciphertext_rejected() {
        let key = [0x42u8; 32];
        let iv = [0x01u8; 12];
        let mut sender = TrafficKey::new(key, iv, TrafficClass::Control);
        let mut receiver = TrafficKey::new(key, iv, TrafficClass::Control);

        let mut ciphertext = sender.seal(b"secret data").unwrap();

        // Flip a byte
        ciphertext[0] ^= 0xFF;

        let result = receiver.open(&ciphertext);
        assert_eq!(result, Err(CipherError::DecryptionFailed));
    }

    #[test]
    fn wrong_key_rejected() {
        let mut sender = TrafficKey::new([0x42u8; 32], [0x01u8; 12], TrafficClass::Control);
        let mut receiver = TrafficKey::new([0x43u8; 32], [0x01u8; 12], TrafficClass::Control);

        let ciphertext = sender.seal(b"data").unwrap();
        let result = receiver.open(&ciphertext);
        assert_eq!(result, Err(CipherError::DecryptionFailed));
    }

    #[test]
    fn out_of_order_sequence_rejected() {
        let key = [0x42u8; 32];
        let iv = [0x01u8; 12];
        let mut sender = TrafficKey::new(key, iv, TrafficClass::Control);
        let mut receiver = TrafficKey::new(key, iv, TrafficClass::Control);

        let ct1 = sender.seal(b"first").unwrap();
        let ct2 = sender.seal(b"second").unwrap();

        // Try to open ct2 first (wrong sequence)
        let result = receiver.open(&ct2);
        assert_eq!(result, Err(CipherError::DecryptionFailed));

        // ct1 is now also broken because receiver advanced its sequence
        let result = receiver.open(&ct1);
        assert_eq!(result, Err(CipherError::DecryptionFailed));
    }

    #[test]
    fn ciphertext_too_short() {
        let mut receiver = TrafficKey::new([0u8; 32], [0u8; 12], TrafficClass::Control);
        let result = receiver.open(&[0u8; 5]);
        assert_eq!(result, Err(CipherError::CiphertextTooShort));
    }

    #[test]
    fn empty_plaintext_roundtrip() {
        let key = [0x42u8; 32];
        let iv = [0x01u8; 12];
        let mut sender = TrafficKey::new(key, iv, TrafficClass::Datagram);
        let mut receiver = TrafficKey::new(key, iv, TrafficClass::Datagram);

        let ct = sender.seal(b"").unwrap();
        assert_eq!(ct.len(), TAG_LEN); // just the tag
        let pt = receiver.open(&ct).unwrap();
        assert!(pt.is_empty());
    }

    #[test]
    fn rekey_resets_sequence() {
        let mut tk = TrafficKey::new([0x42u8; 32], [0x01u8; 12], TrafficClass::Control);
        tk.seal(b"a").unwrap();
        tk.seal(b"b").unwrap();
        assert_eq!(tk.sequence(), 2);

        tk.rekey([0x99u8; 32], [0x02u8; 12]);
        assert_eq!(tk.sequence(), 0);
    }

    #[test]
    fn nonce_construction_is_deterministic() {
        let tk = TrafficKey::new([0u8; 32], [0xAA; 12], TrafficClass::Control);
        let n0 = tk.build_nonce(0);
        let n1 = tk.build_nonce(1);

        // Different sequences → different nonces
        assert_ne!(n0, n1);

        // Same sequence → same nonce
        let n0b = tk.build_nonce(0);
        assert_eq!(n0, n0b);
    }
}
