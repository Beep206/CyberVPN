//! Handshake message types.
//!
//! These correspond to the wire payloads of the handshake frame types:
//! `CLIENT_INIT`, `SERVER_INIT`, `CLIENT_FINISH`, `SERVER_FINISH`, `RETRY`.
//!
//! Each message has a binary encode/decode implementation. Fields are
//! written in a fixed order with QUIC-style varints for lengths and counts.

use crate::varint;

/// Nonce size in bytes (256-bit).
pub const NONCE_LEN: usize = 32;

/// Transport binding digest size (SHA-256).
pub const TRANSPORT_BINDING_LEN: usize = 32;

/// A TLV extension within a handshake message.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Extension {
    /// Extension type ID. Odd values are ignorable if unknown.
    pub ext_type: u64,
    /// Extension data.
    pub data: Vec<u8>,
}

// ── ClientInit ──────────────────────────────────────────────────────────

/// Flight 1: Sent by the initiator (client) after outer transport is ready.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClientInit {
    /// Requested session core version.
    pub core_version: u32,
    /// 256-bit client nonce for key derivation and replay protection.
    pub client_nonce: [u8; NONCE_LEN],
    /// SHA-256 digest binding this handshake to the outer transport.
    pub transport_binding: [u8; TRANSPORT_BINDING_LEN],
    /// Selected KEM for key exchange (wire ID).
    pub kem_id: u16,
    /// Client's public key share for key exchange.
    pub key_share: Vec<u8>,
    /// Authentication method (wire ID).
    pub auth_method: u16,
    /// Authentication credential data.
    pub auth_data: Vec<u8>,
    /// Capabilities the client supports (wire IDs).
    pub capabilities: Vec<u16>,
    /// Optional extensions (resumption ticket, path token, grease).
    pub extensions: Vec<Extension>,
}

// ── ServerInit ──────────────────────────────────────────────────────────

/// Flight 2: Sent by the responder (node) in response to ClientInit.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ServerInit {
    /// Selected session core version.
    pub selected_version: u32,
    /// 256-bit server nonce.
    pub server_nonce: [u8; NONCE_LEN],
    /// Server's public key share.
    pub server_key_share: Vec<u8>,
    /// Selected capabilities (intersection).
    pub selected_capabilities: Vec<u16>,
    /// Node identity data (e.g., node certificate or ID).
    pub node_identity: Vec<u8>,
    /// Policy epoch for this session.
    pub policy_epoch: u64,
    /// Optional extensions (retry_cookie, resumption_accept, session_limits).
    pub extensions: Vec<Extension>,
}

// ── ClientFinish ────────────────────────────────────────────────────────

/// Flight 3: Sent by the initiator to complete authentication.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClientFinish {
    /// Handshake authenticator (MAC or signature over transcript).
    pub authenticator: Vec<u8>,
    /// Acceptance of session limits imposed by the server.
    pub limits_accepted: bool,
    /// Optional extensions (path hints, stream/datagram class requests).
    pub extensions: Vec<Extension>,
}

// ── ServerFinish ────────────────────────────────────────────────────────

/// Flight 4: Sent by the responder to finalize the session.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ServerFinish {
    /// Final authenticator from the server.
    pub authenticator: Vec<u8>,
    /// Assigned session identifier.
    pub session_id: Vec<u8>,
    /// Route and DNS parameters serialized as extensions.
    pub extensions: Vec<Extension>,
}

// ── Retry ───────────────────────────────────────────────────────────────

/// Sent by the responder instead of ServerInit when DoS mitigation is active.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Retry {
    /// Opaque retry cookie the client must echo back.
    pub cookie: Vec<u8>,
}

// ── Well-known extension type IDs ───────────────────────────────────────

/// Extension types used within handshake messages.
pub mod ext {
    /// Resumption ticket in ClientInit.
    pub const RESUMPTION_TICKET: u64 = 0x01;
    /// Path token in ClientInit.
    pub const PATH_TOKEN: u64 = 0x02;
    /// Retry cookie in ServerInit (echoed from Retry).
    pub const RETRY_COOKIE: u64 = 0x03;
    /// Resumption acceptance in ServerInit.
    pub const RESUMPTION_ACCEPT: u64 = 0x04;
    /// Session limits in ServerInit.
    pub const SESSION_LIMITS: u64 = 0x05;
    /// Route set in ServerFinish.
    pub const ROUTE_SET: u64 = 0x06;
    /// DNS config in ServerFinish.
    pub const DNS_CONFIG: u64 = 0x07;
    /// Rekey policy in ServerFinish.
    pub const REKEY_POLICY: u64 = 0x08;
    /// Telemetry budget in ServerFinish.
    pub const TELEMETRY_BUDGET: u64 = 0x09;
    /// Resumption ticket material in ServerFinish.
    pub const TICKET_MATERIAL: u64 = 0x0A;
}

// ── Encoding helpers ────────────────────────────────────────────────────

/// Encode a length-prefixed byte slice (varint length + data).
fn encode_bytes(data: &[u8], buf: &mut Vec<u8>) -> Result<(), varint::VarintError> {
    varint::encode(data.len() as u64, buf)?;
    buf.extend_from_slice(data);
    Ok(())
}

/// Decode a length-prefixed byte slice.
fn decode_bytes(input: &[u8]) -> Result<(Vec<u8>, usize), MessageDecodeError> {
    let (len, n) = varint::decode(input)?;
    let len = len as usize;
    let offset = n;
    if input.len() - offset < len {
        return Err(MessageDecodeError::Truncated);
    }
    Ok((input[offset..offset + len].to_vec(), offset + len))
}

/// Encode an extensions list.
fn encode_extensions(exts: &[Extension], buf: &mut Vec<u8>) -> Result<(), varint::VarintError> {
    varint::encode(exts.len() as u64, buf)?;
    for ext in exts {
        varint::encode(ext.ext_type, buf)?;
        encode_bytes(&ext.data, buf)?;
    }
    Ok(())
}

/// Decode an extensions list.
fn decode_extensions(input: &[u8]) -> Result<(Vec<Extension>, usize), MessageDecodeError> {
    let (count, mut offset) = varint::decode(input)?;
    let mut exts = Vec::with_capacity(count.min(64) as usize);
    for _ in 0..count {
        let (ext_type, n) = varint::decode(&input[offset..])?;
        offset += n;
        let (data, n) = decode_bytes(&input[offset..])?;
        offset += n;
        exts.push(Extension { ext_type, data });
    }
    Ok((exts, offset))
}

/// Errors from handshake message decoding.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum MessageDecodeError {
    #[error("varint error: {0}")]
    Varint(#[from] varint::VarintError),
    #[error("message truncated")]
    Truncated,
    #[error("invalid fixed-length field: expected {expected} bytes, got {actual}")]
    InvalidFixedLen { expected: usize, actual: usize },
}

// ── ClientInit encode/decode ────────────────────────────────────────────

impl ClientInit {
    pub fn encode(&self, buf: &mut Vec<u8>) -> Result<(), varint::VarintError> {
        // core_version: 4 bytes big-endian
        buf.extend_from_slice(&self.core_version.to_be_bytes());
        // client_nonce: 32 bytes
        buf.extend_from_slice(&self.client_nonce);
        // transport_binding: 32 bytes
        buf.extend_from_slice(&self.transport_binding);
        // kem_id: 2 bytes big-endian
        buf.extend_from_slice(&self.kem_id.to_be_bytes());
        // key_share: length-prefixed
        encode_bytes(&self.key_share, buf)?;
        // auth_method: 2 bytes big-endian
        buf.extend_from_slice(&self.auth_method.to_be_bytes());
        // auth_data: length-prefixed
        encode_bytes(&self.auth_data, buf)?;
        // capabilities: count + array of u16
        varint::encode(self.capabilities.len() as u64, buf)?;
        for cap in &self.capabilities {
            buf.extend_from_slice(&cap.to_be_bytes());
        }
        // extensions
        encode_extensions(&self.extensions, buf)?;
        Ok(())
    }

    pub fn decode(input: &[u8]) -> Result<(Self, usize), MessageDecodeError> {
        let mut offset = 0;

        // core_version
        if input.len() < 4 {
            return Err(MessageDecodeError::Truncated);
        }
        let core_version = u32::from_be_bytes(input[0..4].try_into().unwrap());
        offset += 4;

        // client_nonce
        if input.len() - offset < NONCE_LEN {
            return Err(MessageDecodeError::Truncated);
        }
        let mut client_nonce = [0u8; NONCE_LEN];
        client_nonce.copy_from_slice(&input[offset..offset + NONCE_LEN]);
        offset += NONCE_LEN;

        // transport_binding
        if input.len() - offset < TRANSPORT_BINDING_LEN {
            return Err(MessageDecodeError::Truncated);
        }
        let mut transport_binding = [0u8; TRANSPORT_BINDING_LEN];
        transport_binding.copy_from_slice(&input[offset..offset + TRANSPORT_BINDING_LEN]);
        offset += TRANSPORT_BINDING_LEN;

        // kem_id
        if input.len() - offset < 2 {
            return Err(MessageDecodeError::Truncated);
        }
        let kem_id = u16::from_be_bytes(input[offset..offset + 2].try_into().unwrap());
        offset += 2;

        // key_share
        let (key_share, n) = decode_bytes(&input[offset..])?;
        offset += n;

        // auth_method
        if input.len() - offset < 2 {
            return Err(MessageDecodeError::Truncated);
        }
        let auth_method = u16::from_be_bytes(input[offset..offset + 2].try_into().unwrap());
        offset += 2;

        // auth_data
        let (auth_data, n) = decode_bytes(&input[offset..])?;
        offset += n;

        // capabilities
        let (cap_count, n) = varint::decode(&input[offset..])?;
        offset += n;
        let cap_count = cap_count as usize;
        if input.len() - offset < cap_count * 2 {
            return Err(MessageDecodeError::Truncated);
        }
        let mut capabilities = Vec::with_capacity(cap_count);
        for _ in 0..cap_count {
            let cap = u16::from_be_bytes(input[offset..offset + 2].try_into().unwrap());
            offset += 2;
            capabilities.push(cap);
        }

        // extensions
        let (extensions, n) = decode_extensions(&input[offset..])?;
        offset += n;

        Ok((
            ClientInit {
                core_version,
                client_nonce,
                transport_binding,
                kem_id,
                key_share,
                auth_method,
                auth_data,
                capabilities,
                extensions,
            },
            offset,
        ))
    }
}

// ── ServerInit encode/decode ────────────────────────────────────────────

impl ServerInit {
    pub fn encode(&self, buf: &mut Vec<u8>) -> Result<(), varint::VarintError> {
        buf.extend_from_slice(&self.selected_version.to_be_bytes());
        buf.extend_from_slice(&self.server_nonce);
        encode_bytes(&self.server_key_share, buf)?;
        varint::encode(self.selected_capabilities.len() as u64, buf)?;
        for cap in &self.selected_capabilities {
            buf.extend_from_slice(&cap.to_be_bytes());
        }
        encode_bytes(&self.node_identity, buf)?;
        buf.extend_from_slice(&self.policy_epoch.to_be_bytes());
        encode_extensions(&self.extensions, buf)?;
        Ok(())
    }

    pub fn decode(input: &[u8]) -> Result<(Self, usize), MessageDecodeError> {
        let mut offset = 0;

        if input.len() < 4 {
            return Err(MessageDecodeError::Truncated);
        }
        let selected_version = u32::from_be_bytes(input[0..4].try_into().unwrap());
        offset += 4;

        if input.len() - offset < NONCE_LEN {
            return Err(MessageDecodeError::Truncated);
        }
        let mut server_nonce = [0u8; NONCE_LEN];
        server_nonce.copy_from_slice(&input[offset..offset + NONCE_LEN]);
        offset += NONCE_LEN;

        let (server_key_share, n) = decode_bytes(&input[offset..])?;
        offset += n;

        let (cap_count, n) = varint::decode(&input[offset..])?;
        offset += n;
        let cap_count = cap_count as usize;
        if input.len() - offset < cap_count * 2 {
            return Err(MessageDecodeError::Truncated);
        }
        let mut selected_capabilities = Vec::with_capacity(cap_count);
        for _ in 0..cap_count {
            let cap = u16::from_be_bytes(input[offset..offset + 2].try_into().unwrap());
            offset += 2;
            selected_capabilities.push(cap);
        }

        let (node_identity, n) = decode_bytes(&input[offset..])?;
        offset += n;

        if input.len() - offset < 8 {
            return Err(MessageDecodeError::Truncated);
        }
        let policy_epoch = u64::from_be_bytes(input[offset..offset + 8].try_into().unwrap());
        offset += 8;

        let (extensions, n) = decode_extensions(&input[offset..])?;
        offset += n;

        Ok((
            ServerInit {
                selected_version,
                server_nonce,
                server_key_share,
                selected_capabilities,
                node_identity,
                policy_epoch,
                extensions,
            },
            offset,
        ))
    }
}

// ── ClientFinish encode/decode ──────────────────────────────────────────

impl ClientFinish {
    pub fn encode(&self, buf: &mut Vec<u8>) -> Result<(), varint::VarintError> {
        encode_bytes(&self.authenticator, buf)?;
        buf.push(if self.limits_accepted { 1 } else { 0 });
        encode_extensions(&self.extensions, buf)?;
        Ok(())
    }

    pub fn decode(input: &[u8]) -> Result<(Self, usize), MessageDecodeError> {
        let mut offset = 0;
        let (authenticator, n) = decode_bytes(&input[offset..])?;
        offset += n;
        if input.len() - offset < 1 {
            return Err(MessageDecodeError::Truncated);
        }
        let limits_accepted = input[offset] != 0;
        offset += 1;
        let (extensions, n) = decode_extensions(&input[offset..])?;
        offset += n;
        Ok((
            ClientFinish {
                authenticator,
                limits_accepted,
                extensions,
            },
            offset,
        ))
    }
}

// ── ServerFinish encode/decode ──────────────────────────────────────────

impl ServerFinish {
    pub fn encode(&self, buf: &mut Vec<u8>) -> Result<(), varint::VarintError> {
        encode_bytes(&self.authenticator, buf)?;
        encode_bytes(&self.session_id, buf)?;
        encode_extensions(&self.extensions, buf)?;
        Ok(())
    }

    pub fn decode(input: &[u8]) -> Result<(Self, usize), MessageDecodeError> {
        let mut offset = 0;
        let (authenticator, n) = decode_bytes(&input[offset..])?;
        offset += n;
        let (session_id, n) = decode_bytes(&input[offset..])?;
        offset += n;
        let (extensions, n) = decode_extensions(&input[offset..])?;
        offset += n;
        Ok((
            ServerFinish {
                authenticator,
                session_id,
                extensions,
            },
            offset,
        ))
    }
}

// ── Retry encode/decode ─────────────────────────────────────────────────

impl Retry {
    pub fn encode(&self, buf: &mut Vec<u8>) -> Result<(), varint::VarintError> {
        encode_bytes(&self.cookie, buf)?;
        Ok(())
    }

    pub fn decode(input: &[u8]) -> Result<(Self, usize), MessageDecodeError> {
        let (cookie, n) = decode_bytes(input)?;
        Ok((Retry { cookie }, n))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_client_init() -> ClientInit {
        ClientInit {
            core_version: 1,
            client_nonce: [0xAA; NONCE_LEN],
            transport_binding: [0xBB; TRANSPORT_BINDING_LEN],
            kem_id: 0x01,
            key_share: vec![0xCC; 32],
            auth_method: 0x01,
            auth_data: vec![0xDD; 16],
            capabilities: vec![0x01, 0x02, 0x03],
            extensions: vec![
                Extension {
                    ext_type: ext::RESUMPTION_TICKET,
                    data: vec![0xEE; 8],
                },
            ],
        }
    }

    #[test]
    fn client_init_roundtrip() {
        let msg = make_client_init();
        let mut buf = Vec::new();
        msg.encode(&mut buf).unwrap();
        let (decoded, consumed) = ClientInit::decode(&buf).unwrap();
        assert_eq!(consumed, buf.len());
        assert_eq!(decoded, msg);
    }

    #[test]
    fn server_init_roundtrip() {
        let msg = ServerInit {
            selected_version: 1,
            server_nonce: [0x11; NONCE_LEN],
            server_key_share: vec![0x22; 32],
            selected_capabilities: vec![0x01, 0x02],
            node_identity: vec![0x33; 64],
            policy_epoch: 42,
            extensions: vec![],
        };
        let mut buf = Vec::new();
        msg.encode(&mut buf).unwrap();
        let (decoded, consumed) = ServerInit::decode(&buf).unwrap();
        assert_eq!(consumed, buf.len());
        assert_eq!(decoded, msg);
    }

    #[test]
    fn client_finish_roundtrip() {
        let msg = ClientFinish {
            authenticator: vec![0x44; 32],
            limits_accepted: true,
            extensions: vec![],
        };
        let mut buf = Vec::new();
        msg.encode(&mut buf).unwrap();
        let (decoded, consumed) = ClientFinish::decode(&buf).unwrap();
        assert_eq!(consumed, buf.len());
        assert_eq!(decoded, msg);
    }

    #[test]
    fn server_finish_roundtrip() {
        let msg = ServerFinish {
            authenticator: vec![0x55; 32],
            session_id: vec![0x66; 16],
            extensions: vec![
                Extension {
                    ext_type: ext::ROUTE_SET,
                    data: vec![10, 0, 0, 0, 8],
                },
                Extension {
                    ext_type: ext::DNS_CONFIG,
                    data: vec![8, 8, 8, 8],
                },
            ],
        };
        let mut buf = Vec::new();
        msg.encode(&mut buf).unwrap();
        let (decoded, consumed) = ServerFinish::decode(&buf).unwrap();
        assert_eq!(consumed, buf.len());
        assert_eq!(decoded, msg);
    }

    #[test]
    fn retry_roundtrip() {
        let msg = Retry {
            cookie: vec![0x77; 48],
        };
        let mut buf = Vec::new();
        msg.encode(&mut buf).unwrap();
        let (decoded, consumed) = Retry::decode(&buf).unwrap();
        assert_eq!(consumed, buf.len());
        assert_eq!(decoded, msg);
    }

    #[test]
    fn empty_extensions() {
        let msg = ClientInit {
            core_version: 1,
            client_nonce: [0; NONCE_LEN],
            transport_binding: [0; TRANSPORT_BINDING_LEN],
            kem_id: 0x01,
            key_share: vec![0; 32],
            auth_method: 0x01,
            auth_data: vec![],
            capabilities: vec![],
            extensions: vec![],
        };
        let mut buf = Vec::new();
        msg.encode(&mut buf).unwrap();
        let (decoded, _) = ClientInit::decode(&buf).unwrap();
        assert_eq!(decoded.extensions.len(), 0);
        assert_eq!(decoded.capabilities.len(), 0);
    }

    #[test]
    fn truncated_client_init_fails() {
        let msg = make_client_init();
        let mut buf = Vec::new();
        msg.encode(&mut buf).unwrap();

        // Try decoding with progressively fewer bytes
        for truncated_len in [0, 1, 4, 35, 67] {
            let result = ClientInit::decode(&buf[..truncated_len.min(buf.len())]);
            assert!(result.is_err(), "expected error at len={truncated_len}");
        }
    }
}
