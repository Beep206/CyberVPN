use aes_gcm::{
    aead::{Aead, KeyInit},
    Aes256Gcm, Nonce,
};
use hmac::{Hmac, Mac};
use sha2::Sha256;
use uuid::Uuid;

use crate::{
    error::TransportError,
    model::{ControlFrame, HandshakeHello, HandshakeWelcome},
};

type HmacSha256 = Hmac<Sha256>;

#[derive(Debug, Clone, Copy)]
pub enum Direction {
    ClientToServer,
    ServerToClient,
}

pub fn random_nonce() -> [u8; 16] {
    *Uuid::new_v4().as_bytes()
}

pub fn unix_timestamp_ms() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|duration| u64::try_from(duration.as_millis()).unwrap_or(u64::MAX))
        .unwrap_or(0)
}

pub fn client_proof(token: &str, hello: &HandshakeHello) -> Result<[u8; 32], TransportError> {
    let mut mac = <HmacSha256 as Mac>::new_from_slice(token.as_bytes())
        .map_err(|error| TransportError::Crypto(error.to_string()))?;
    update_with_hello_fields(&mut mac, hello);
    Ok(mac.finalize().into_bytes().into())
}

pub fn server_proof(
    token: &str,
    welcome: &HandshakeWelcome,
    hello: &HandshakeHello,
) -> Result<[u8; 32], TransportError> {
    let mut mac = <HmacSha256 as Mac>::new_from_slice(token.as_bytes())
        .map_err(|error| TransportError::Crypto(error.to_string()))?;
    update_with_field(&mut mac, welcome.magic.as_bytes());
    update_with_field(&mut mac, &[u8::from(welcome.accepted)]);
    update_with_field(&mut mac, welcome.session_id.as_bytes());
    update_with_field(&mut mac, &[u8::from(welcome.resumed)]);
    update_with_field(&mut mac, welcome.transport_profile_id.as_bytes());
    update_with_field(&mut mac, &welcome.server_nonce);
    update_with_field(&mut mac, &welcome.heartbeat_interval_ms.to_be_bytes());
    update_with_optional_field(&mut mac, welcome.error.as_deref());
    update_with_field(&mut mac, &hello.client_nonce);
    Ok(mac.finalize().into_bytes().into())
}

pub fn derive_session_key(
    token: &str,
    session_id: &str,
    transport_profile_id: &str,
    client_nonce: &[u8; 16],
    server_nonce: &[u8; 16],
) -> Result<[u8; 32], TransportError> {
    let mut mac = <HmacSha256 as Mac>::new_from_slice(token.as_bytes())
        .map_err(|error| TransportError::Crypto(error.to_string()))?;
    update_with_field(&mut mac, b"helix-session-v1");
    update_with_field(&mut mac, session_id.as_bytes());
    update_with_field(&mut mac, transport_profile_id.as_bytes());
    update_with_field(&mut mac, client_nonce);
    update_with_field(&mut mac, server_nonce);
    Ok(mac.finalize().into_bytes().into())
}

pub fn encrypt_frame(
    session_key: &[u8; 32],
    direction: Direction,
    sequence: u64,
    frame: &ControlFrame,
) -> Result<Vec<u8>, TransportError> {
    let cipher = Aes256Gcm::new_from_slice(session_key)
        .map_err(|error| TransportError::Crypto(error.to_string()))?;
    let plaintext = postcard::to_allocvec(frame)?;
    let nonce_bytes = build_nonce(direction, sequence);
    cipher
        .encrypt(Nonce::from_slice(&nonce_bytes), plaintext.as_ref())
        .map_err(|error| TransportError::Crypto(error.to_string()))
}

pub fn decrypt_frame(
    session_key: &[u8; 32],
    direction: Direction,
    sequence: u64,
    ciphertext: &[u8],
) -> Result<ControlFrame, TransportError> {
    let cipher = Aes256Gcm::new_from_slice(session_key)
        .map_err(|error| TransportError::Crypto(error.to_string()))?;
    let nonce_bytes = build_nonce(direction, sequence);
    let plaintext = cipher
        .decrypt(Nonce::from_slice(&nonce_bytes), ciphertext)
        .map_err(|error| TransportError::Crypto(error.to_string()))?;
    postcard::from_bytes(&plaintext).map_err(TransportError::Codec)
}

fn build_nonce(direction: Direction, sequence: u64) -> [u8; 12] {
    let mut nonce = [0_u8; 12];
    nonce[0] = match direction {
        Direction::ClientToServer => 0xA1,
        Direction::ServerToClient => 0xB2,
    };
    nonce[4..].copy_from_slice(&sequence.to_be_bytes());
    nonce
}

fn update_with_hello_fields(mac: &mut HmacSha256, hello: &HandshakeHello) {
    update_with_field(mac, hello.magic.as_bytes());
    update_with_field(mac, &hello.protocol_version.to_be_bytes());
    update_with_field(mac, hello.manifest_id.as_bytes());
    update_with_field(mac, hello.transport_profile_id.as_bytes());
    update_with_field(mac, hello.profile_family.as_bytes());
    update_with_field(mac, &hello.profile_version.to_be_bytes());
    update_with_field(mac, &hello.policy_version.to_be_bytes());
    update_with_field(mac, hello.session_mode.as_bytes());
    update_with_field(mac, hello.route_ref.as_bytes());
    update_with_optional_field(mac, hello.resume_session_id.as_deref());
    update_with_field(mac, &hello.client_nonce);
    update_with_field(mac, &hello.timestamp_ms.to_be_bytes());
}

fn update_with_field(mac: &mut HmacSha256, bytes: &[u8]) {
    let len = u32::try_from(bytes.len()).unwrap_or(u32::MAX);
    mac.update(&len.to_be_bytes());
    mac.update(bytes);
}

fn update_with_optional_field(mac: &mut HmacSha256, bytes: Option<&str>) {
    match bytes {
        Some(bytes) => update_with_field(mac, bytes.as_bytes()),
        None => update_with_field(mac, &[]),
    }
}
