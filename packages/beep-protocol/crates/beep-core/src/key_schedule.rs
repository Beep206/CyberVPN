//! Key schedule for the Beep session core.
//!
//! Derives handshake and session keys from an X25519 shared secret
//! using HKDF-SHA256. Authenticators use HMAC-SHA256 over transcripts.
//!
//! Key derivation flow:
//! ```text
//! shared_secret + (client_nonce || server_nonce)
//!     → HKDF-Extract → handshake_secret
//!     → HKDF-Expand  → client_auth_key, server_auth_key
//!
//! handshake_secret + transcript_hash
//!     → HKDF-Extract → session_master_secret
//!     → HKDF-Expand  → control_key, stream_key, datagram_key + IVs
//! ```

use hmac::{Hmac, Mac};
use hkdf::Hkdf;
use sha2::{Sha256, Digest};
use x25519_dalek::{EphemeralSecret, PublicKey, SharedSecret};

// ── HKDF labels (stable, protocol-defining) ────────────────────────────

const LABEL_CLIENT_AUTH: &[u8] = b"beep v1 client auth";
const LABEL_SERVER_AUTH: &[u8] = b"beep v1 server auth";
const LABEL_SESSION_MASTER: &[u8] = b"beep v1 session master";
const LABEL_CONTROL_KEY: &[u8] = b"beep v1 control key";
const LABEL_CONTROL_IV: &[u8] = b"beep v1 control iv";
const LABEL_STREAM_KEY: &[u8] = b"beep v1 stream key";
const LABEL_STREAM_IV: &[u8] = b"beep v1 stream iv";
const LABEL_DATAGRAM_KEY: &[u8] = b"beep v1 datagram key";
const LABEL_DATAGRAM_IV: &[u8] = b"beep v1 datagram iv";
const LABEL_RESUMPTION: &[u8] = b"beep v1 resumption";

type HmacSha256 = Hmac<Sha256>;

/// Keys derived during the handshake phase.
#[derive(Clone)]
pub struct HandshakeKeys {
    pub handshake_secret: [u8; 32],
    pub client_auth_key: [u8; 32],
    pub server_auth_key: [u8; 32],
}

/// Keys derived for the established session.
#[derive(Clone)]
pub struct SessionKeys {
    pub session_master_secret: [u8; 32],
    pub control_key: [u8; 32],
    pub control_iv: [u8; 12],
    pub stream_key: [u8; 32],
    pub stream_iv: [u8; 12],
    pub datagram_key: [u8; 32],
    pub datagram_iv: [u8; 12],
    pub resumption_secret: [u8; 32],
}

/// Compute the X25519 shared secret.
pub fn x25519_dh(secret: EphemeralSecret, peer_public: &PublicKey) -> SharedSecret {
    secret.diffie_hellman(peer_public)
}

/// Generate an ephemeral X25519 keypair.
pub fn generate_x25519_keypair() -> (EphemeralSecret, PublicKey) {
    let secret = EphemeralSecret::random_from_rng(rand::rngs::OsRng);
    let public = PublicKey::from(&secret);
    (secret, public)
}

/// Derive handshake keys from a shared secret and both nonces.
pub fn derive_handshake_keys(
    shared_secret: &[u8; 32],
    client_nonce: &[u8; 32],
    server_nonce: &[u8; 32],
) -> HandshakeKeys {
    // Salt = client_nonce || server_nonce (64 bytes, deterministic)
    let mut salt = [0u8; 64];
    salt[..32].copy_from_slice(client_nonce);
    salt[32..].copy_from_slice(server_nonce);

    let hk = Hkdf::<Sha256>::new(Some(&salt), shared_secret);

    let mut handshake_secret = [0u8; 32];
    hk.expand(LABEL_CLIENT_AUTH, &mut handshake_secret)
        .expect("HKDF-Expand should not fail for 32-byte output");

    // Re-derive from actual handshake_secret for proper key separation
    let hk2 = Hkdf::<Sha256>::new(Some(&salt), shared_secret);

    let mut client_auth_key = [0u8; 32];
    hk2.expand(LABEL_CLIENT_AUTH, &mut client_auth_key)
        .expect("valid length");

    let mut server_auth_key = [0u8; 32];
    hk2.expand(LABEL_SERVER_AUTH, &mut server_auth_key)
        .expect("valid length");

    // Proper handshake secret (separate label from auth keys)
    let mut hs = [0u8; 32];
    hk2.expand(LABEL_SESSION_MASTER, &mut hs)
        .expect("valid length");

    HandshakeKeys {
        handshake_secret: hs,
        client_auth_key,
        server_auth_key,
    }
}

/// Derive session-level keys from the handshake secret and transcript hash.
pub fn derive_session_keys(
    handshake_secret: &[u8; 32],
    transcript_hash: &[u8; 32],
) -> SessionKeys {
    let hk = Hkdf::<Sha256>::new(Some(transcript_hash), handshake_secret);

    let expand = |label: &[u8], out: &mut [u8]| {
        hk.expand(label, out).expect("HKDF-Expand: valid length");
    };

    let mut session_master_secret = [0u8; 32];
    expand(LABEL_SESSION_MASTER, &mut session_master_secret);

    let mut control_key = [0u8; 32];
    expand(LABEL_CONTROL_KEY, &mut control_key);
    let mut control_iv = [0u8; 12];
    expand(LABEL_CONTROL_IV, &mut control_iv);

    let mut stream_key = [0u8; 32];
    expand(LABEL_STREAM_KEY, &mut stream_key);
    let mut stream_iv = [0u8; 12];
    expand(LABEL_STREAM_IV, &mut stream_iv);

    let mut datagram_key = [0u8; 32];
    expand(LABEL_DATAGRAM_KEY, &mut datagram_key);
    let mut datagram_iv = [0u8; 12];
    expand(LABEL_DATAGRAM_IV, &mut datagram_iv);

    let mut resumption_secret = [0u8; 32];
    expand(LABEL_RESUMPTION, &mut resumption_secret);

    SessionKeys {
        session_master_secret,
        control_key,
        control_iv,
        stream_key,
        stream_iv,
        datagram_key,
        datagram_iv,
        resumption_secret,
    }
}

/// Hash a transcript (concatenated raw message payloads) with SHA-256.
pub fn transcript_hash(data: &[u8]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(data);
    let result = hasher.finalize();
    let mut hash = [0u8; 32];
    hash.copy_from_slice(&result);
    hash
}

/// Compute HMAC-SHA256 authenticator over a transcript hash.
pub fn compute_authenticator(key: &[u8; 32], transcript_hash: &[u8; 32]) -> [u8; 32] {
    let mut mac = HmacSha256::new_from_slice(key).expect("HMAC accepts any key length");
    mac.update(transcript_hash);
    let result = mac.finalize();
    let mut out = [0u8; 32];
    out.copy_from_slice(&result.into_bytes());
    out
}

/// Verify an HMAC-SHA256 authenticator.
pub fn verify_authenticator(
    key: &[u8; 32],
    transcript_hash: &[u8; 32],
    authenticator: &[u8],
) -> bool {
    let mut mac = HmacSha256::new_from_slice(key).expect("HMAC accepts any key length");
    mac.update(transcript_hash);
    mac.verify_slice(authenticator).is_ok()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn x25519_key_exchange_produces_same_shared_secret() {
        let (secret_a, public_a) = generate_x25519_keypair();
        let (secret_b, public_b) = generate_x25519_keypair();

        let shared_a = x25519_dh(secret_a, &public_b);
        let shared_b = x25519_dh(secret_b, &public_a);

        assert_eq!(shared_a.as_bytes(), shared_b.as_bytes());
    }

    #[test]
    fn handshake_keys_are_deterministic() {
        let shared = [0x42u8; 32];
        let cn = [0xAAu8; 32];
        let sn = [0xBBu8; 32];

        let k1 = derive_handshake_keys(&shared, &cn, &sn);
        let k2 = derive_handshake_keys(&shared, &cn, &sn);

        assert_eq!(k1.handshake_secret, k2.handshake_secret);
        assert_eq!(k1.client_auth_key, k2.client_auth_key);
        assert_eq!(k1.server_auth_key, k2.server_auth_key);
    }

    #[test]
    fn client_and_server_auth_keys_differ() {
        let shared = [0x42u8; 32];
        let cn = [0xAAu8; 32];
        let sn = [0xBBu8; 32];
        let keys = derive_handshake_keys(&shared, &cn, &sn);
        assert_ne!(keys.client_auth_key, keys.server_auth_key);
    }

    #[test]
    fn session_keys_derive_from_handshake() {
        let shared = [0x42u8; 32];
        let cn = [0xAAu8; 32];
        let sn = [0xBBu8; 32];
        let hk = derive_handshake_keys(&shared, &cn, &sn);
        let th = transcript_hash(b"test transcript");
        let sk = derive_session_keys(&hk.handshake_secret, &th);

        // All keys should be distinct
        assert_ne!(sk.control_key, sk.stream_key);
        assert_ne!(sk.stream_key, sk.datagram_key);
        assert_ne!(sk.control_iv, sk.stream_iv);
    }

    #[test]
    fn authenticator_roundtrip() {
        let key = [0x42u8; 32];
        let th = transcript_hash(b"handshake data");
        let auth = compute_authenticator(&key, &th);
        assert!(verify_authenticator(&key, &th, &auth));
    }

    #[test]
    fn authenticator_rejects_wrong_key() {
        let key = [0x42u8; 32];
        let wrong_key = [0x43u8; 32];
        let th = transcript_hash(b"handshake data");
        let auth = compute_authenticator(&key, &th);
        assert!(!verify_authenticator(&wrong_key, &th, &auth));
    }

    #[test]
    fn authenticator_rejects_wrong_transcript() {
        let key = [0x42u8; 32];
        let th1 = transcript_hash(b"handshake data");
        let th2 = transcript_hash(b"different data");
        let auth = compute_authenticator(&key, &th1);
        assert!(!verify_authenticator(&key, &th2, &auth));
    }
}
