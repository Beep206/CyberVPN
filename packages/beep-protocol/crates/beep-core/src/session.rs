//! Handshake drivers for client and server.
//!
//! These are **synchronous, transport-agnostic** state machines.
//! The async orchestration layer (runtime or integration test) calls
//! these methods and handles the actual I/O.
//!
//! # Client flow
//! ```text
//! create_client_init() → bytes to send
//! process_server_init(received_bytes) → ok
//! create_client_finish() → bytes to send
//! process_server_finish(received_bytes) → SessionKeys
//! ```
//!
//! # Server flow
//! ```text
//! process_client_init(received_bytes) → ok
//! create_server_init() → bytes to send
//! process_client_finish(received_bytes) → ok
//! create_server_finish() → (bytes to send, SessionKeys)
//! ```

use beep_core_types::{CapabilityId, CoreVersion, FrameType, SessionErrorCode};

use crate::codec::{self, RawFrame};
use crate::error::SessionError;
use crate::handshake::machine::{Event, StateMachine};
use crate::handshake::messages::*;
use crate::handshake::state::Role;
use crate::key_schedule::{self, HandshakeKeys, SessionKeys};

use x25519_dalek::{EphemeralSecret, PublicKey};

/// Client-side configuration.
pub struct ClientConfig {
    pub core_version: CoreVersion,
    pub transport_binding: [u8; 32],
    pub capabilities: Vec<CapabilityId>,
    pub auth_method: u16,
    pub auth_data: Vec<u8>,
}

/// Server-side configuration.
pub struct ServerConfig {
    pub supported_versions: Vec<CoreVersion>,
    pub transport_binding: [u8; 32],
    pub capabilities: Vec<CapabilityId>,
    pub node_identity: Vec<u8>,
    pub policy_epoch: u64,
}

/// Client handshake driver. Transport-agnostic, synchronous.
pub struct ClientHandshake {
    sm: StateMachine,
    config: ClientConfig,
    client_nonce: [u8; 32],
    ephemeral_secret: Option<EphemeralSecret>,
    client_public: Option<PublicKey>,
    transcript: Vec<u8>,
    handshake_keys: Option<HandshakeKeys>,
}

impl ClientHandshake {
    pub fn new(config: ClientConfig) -> Self {
        let mut nonce = [0u8; 32];
        rand::RngCore::fill_bytes(&mut rand::rngs::OsRng, &mut nonce);

        let (secret, public) = key_schedule::generate_x25519_keypair();

        let mut sm = StateMachine::new(Role::Initiator);
        sm.process(Event::OuterTransportReady).expect("idle → outer");

        Self {
            sm,
            config,
            client_nonce: nonce,
            ephemeral_secret: Some(secret),
            client_public: Some(public),
            transcript: Vec::new(),
            handshake_keys: None,
        }
    }

    /// Create ClientInit. Returns encoded frame bytes to send.
    pub fn create_client_init(&mut self) -> Result<Vec<u8>, SessionError> {
        let public = self.client_public.take().ok_or_else(|| {
            SessionError::InvalidTransition("ClientInit already created".into())
        })?;

        let msg = ClientInit {
            core_version: self.config.core_version.as_u32(),
            client_nonce: self.client_nonce,
            transport_binding: self.config.transport_binding,
            kem_id: beep_core_types::KemId::X25519.to_wire(),
            key_share: public.as_bytes().to_vec(),
            auth_method: self.config.auth_method,
            auth_data: self.config.auth_data.clone(),
            capabilities: self.config.capabilities.iter().map(|c| c.to_wire()).collect(),
            extensions: vec![],
        };

        let mut payload = Vec::new();
        msg.encode(&mut payload)
            .map_err(|e| SessionError::protocol(SessionErrorCode::InternalError, e.to_string()))?;
        self.transcript.extend_from_slice(&payload);

        let frame_bytes = encode_to_frame(FrameType::CLIENT_INIT, &payload)?;
        self.sm.process(Event::ClientInitProcessed)?;
        Ok(frame_bytes)
    }

    /// Process received ServerInit frame. Derives handshake keys.
    pub fn process_server_init(&mut self, data: &[u8]) -> Result<(), SessionError> {
        let frame = decode_expect_type(data, FrameType::SERVER_INIT)?;
        let (server_init, _) = ServerInit::decode(&frame.payload)
            .map_err(|e| SessionError::protocol(SessionErrorCode::ProtocolViolation, e.to_string()))?;

        self.transcript.extend_from_slice(&frame.payload);

        // X25519 DH
        let secret = self.ephemeral_secret.take().ok_or_else(|| {
            SessionError::InvalidTransition("ephemeral secret already consumed".into())
        })?;
        let peer_public = PublicKey::from(
            <[u8; 32]>::try_from(server_init.server_key_share.as_slice())
                .map_err(|_| SessionError::protocol(
                    SessionErrorCode::CapabilityMismatch,
                    "invalid server key share length",
                ))?,
        );

        let shared = key_schedule::x25519_dh(secret, &peer_public);
        let keys = key_schedule::derive_handshake_keys(
            shared.as_bytes(),
            &self.client_nonce,
            &server_init.server_nonce,
        );
        self.handshake_keys = Some(keys);

        self.sm.process(Event::ServerInitProcessed)?;
        Ok(())
    }

    /// Create ClientFinish with authenticator. Returns encoded frame bytes.
    pub fn create_client_finish(&mut self) -> Result<Vec<u8>, SessionError> {
        let keys = self.handshake_keys.as_ref().ok_or_else(|| {
            SessionError::InvalidTransition("handshake keys not derived".into())
        })?;

        let th = key_schedule::transcript_hash(&self.transcript);
        let authenticator = key_schedule::compute_authenticator(&keys.client_auth_key, &th);

        let msg = ClientFinish {
            authenticator: authenticator.to_vec(),
            limits_accepted: true,
            extensions: vec![],
        };

        let mut payload = Vec::new();
        msg.encode(&mut payload)
            .map_err(|e| SessionError::protocol(SessionErrorCode::InternalError, e.to_string()))?;
        self.transcript.extend_from_slice(&payload);

        let frame_bytes = encode_to_frame(FrameType::CLIENT_FINISH, &payload)?;
        self.sm.process(Event::ClientFinishProcessed)?;
        Ok(frame_bytes)
    }

    /// Process ServerFinish, verify authenticator, derive session keys.
    pub fn process_server_finish(&mut self, data: &[u8]) -> Result<SessionKeys, SessionError> {
        let frame = decode_expect_type(data, FrameType::SERVER_FINISH)?;
        let (server_finish, _) = ServerFinish::decode(&frame.payload)
            .map_err(|e| SessionError::protocol(SessionErrorCode::ProtocolViolation, e.to_string()))?;

        let keys = self.handshake_keys.as_ref().ok_or_else(|| {
            SessionError::InvalidTransition("handshake keys not available".into())
        })?;

        // Verify server authenticator (over transcript before ServerFinish)
        let th = key_schedule::transcript_hash(&self.transcript);
        if !key_schedule::verify_authenticator(&keys.server_auth_key, &th, &server_finish.authenticator) {
            return Err(SessionError::protocol(SessionErrorCode::AuthFailed, "server authenticator invalid"));
        }

        self.transcript.extend_from_slice(&frame.payload);
        let final_th = key_schedule::transcript_hash(&self.transcript);
        let session_keys = key_schedule::derive_session_keys(&keys.handshake_secret, &final_th);

        self.sm.process(Event::ServerFinishProcessed)?;
        Ok(session_keys)
    }
}

/// Server handshake driver. Transport-agnostic, synchronous.
pub struct ServerHandshake {
    sm: StateMachine,
    config: ServerConfig,
    server_nonce: [u8; 32],
    ephemeral_secret: Option<EphemeralSecret>,
    server_public: Option<PublicKey>,
    transcript: Vec<u8>,
    handshake_keys: Option<HandshakeKeys>,
}

impl ServerHandshake {
    pub fn new(config: ServerConfig) -> Self {
        let mut nonce = [0u8; 32];
        rand::RngCore::fill_bytes(&mut rand::rngs::OsRng, &mut nonce);

        let (secret, public) = key_schedule::generate_x25519_keypair();

        let mut sm = StateMachine::new(Role::Responder);
        sm.process(Event::OuterTransportReady).expect("idle → outer");

        Self {
            sm,
            config,
            server_nonce: nonce,
            ephemeral_secret: Some(secret),
            server_public: Some(public),
            transcript: Vec::new(),
            handshake_keys: None,
        }
    }

    /// Process received ClientInit frame.
    pub fn process_client_init(&mut self, data: &[u8]) -> Result<ClientInit, SessionError> {
        let frame = decode_expect_type(data, FrameType::CLIENT_INIT)?;
        let (client_init, _) = ClientInit::decode(&frame.payload)
            .map_err(|e| SessionError::protocol(SessionErrorCode::ProtocolViolation, e.to_string()))?;

        // Verify transport binding
        if client_init.transport_binding != self.config.transport_binding {
            return Err(SessionError::protocol_code(SessionErrorCode::TransportBindingFailed));
        }

        self.transcript.extend_from_slice(&frame.payload);

        // X25519 DH
        let secret = self.ephemeral_secret.take().unwrap();
        let peer_public = PublicKey::from(
            <[u8; 32]>::try_from(client_init.key_share.as_slice())
                .map_err(|_| SessionError::protocol(
                    SessionErrorCode::CapabilityMismatch,
                    "invalid client key share length",
                ))?,
        );

        let shared = key_schedule::x25519_dh(secret, &peer_public);
        let keys = key_schedule::derive_handshake_keys(
            shared.as_bytes(),
            &client_init.client_nonce,
            &self.server_nonce,
        );
        self.handshake_keys = Some(keys);
        self.sm.process(Event::ClientInitProcessed)?;
        Ok(client_init)
    }

    /// Create ServerInit. Returns encoded frame bytes.
    pub fn create_server_init(&mut self) -> Result<Vec<u8>, SessionError> {
        let public = self.server_public.take().ok_or_else(|| {
            SessionError::InvalidTransition("ServerInit already created".into())
        })?;

        let selected_caps: Vec<u16> = self.config.capabilities.iter().map(|c| c.to_wire()).collect();

        let msg = ServerInit {
            selected_version: self.config.supported_versions.first()
                .map(|v| v.as_u32())
                .unwrap_or(1),
            server_nonce: self.server_nonce,
            server_key_share: public.as_bytes().to_vec(),
            selected_capabilities: selected_caps,
            node_identity: self.config.node_identity.clone(),
            policy_epoch: self.config.policy_epoch,
            extensions: vec![],
        };

        let mut payload = Vec::new();
        msg.encode(&mut payload)
            .map_err(|e| SessionError::protocol(SessionErrorCode::InternalError, e.to_string()))?;
        self.transcript.extend_from_slice(&payload);

        let frame_bytes = encode_to_frame(FrameType::SERVER_INIT, &payload)?;
        self.sm.process(Event::ServerInitProcessed)?;
        Ok(frame_bytes)
    }

    /// Process ClientFinish and verify authenticator.
    pub fn process_client_finish(&mut self, data: &[u8]) -> Result<(), SessionError> {
        let frame = decode_expect_type(data, FrameType::CLIENT_FINISH)?;
        let (client_finish, _) = ClientFinish::decode(&frame.payload)
            .map_err(|e| SessionError::protocol(SessionErrorCode::ProtocolViolation, e.to_string()))?;

        let keys = self.handshake_keys.as_ref().unwrap();
        let th = key_schedule::transcript_hash(&self.transcript);

        if !key_schedule::verify_authenticator(&keys.client_auth_key, &th, &client_finish.authenticator) {
            return Err(SessionError::protocol(SessionErrorCode::AuthFailed, "client authenticator invalid"));
        }

        self.transcript.extend_from_slice(&frame.payload);
        self.sm.process(Event::ClientFinishProcessed)?;
        Ok(())
    }

    /// Create ServerFinish with authenticator. Returns (frame bytes, session keys).
    pub fn create_server_finish(&mut self) -> Result<(Vec<u8>, SessionKeys), SessionError> {
        let keys = self.handshake_keys.as_ref().unwrap();

        let th = key_schedule::transcript_hash(&self.transcript);
        let authenticator = key_schedule::compute_authenticator(&keys.server_auth_key, &th);

        let msg = ServerFinish {
            authenticator: authenticator.to_vec(),
            session_id: vec![0x01; 16], // placeholder session ID
            extensions: vec![],
        };

        let mut payload = Vec::new();
        msg.encode(&mut payload)
            .map_err(|e| SessionError::protocol(SessionErrorCode::InternalError, e.to_string()))?;
        self.transcript.extend_from_slice(&payload);

        let final_th = key_schedule::transcript_hash(&self.transcript);
        let session_keys = key_schedule::derive_session_keys(&keys.handshake_secret, &final_th);

        let frame_bytes = encode_to_frame(FrameType::SERVER_FINISH, &payload)?;
        self.sm.process(Event::ServerFinishProcessed)?;
        Ok((frame_bytes, session_keys))
    }
}

// ── Helpers ─────────────────────────────────────────────────────────────

fn encode_to_frame(frame_type: FrameType, payload: &[u8]) -> Result<Vec<u8>, SessionError> {
    let frame = RawFrame {
        frame_type,
        flags: 0,
        payload: payload.to_vec(),
    };
    let mut buf = Vec::new();
    codec::encode_frame(&frame, &mut buf)?;
    Ok(buf)
}

fn decode_expect_type(data: &[u8], expected: FrameType) -> Result<RawFrame, SessionError> {
    let (frame, _) = codec::decode_frame(data)?;
    if frame.frame_type != expected {
        return Err(SessionError::protocol(
            SessionErrorCode::ProtocolViolation,
            format!("expected {expected}, got {}", frame.frame_type),
        ));
    }
    Ok(frame)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn client_config(binding: [u8; 32]) -> ClientConfig {
        ClientConfig {
            core_version: CoreVersion::V1,
            transport_binding: binding,
            capabilities: vec![CapabilityId::Streams, CapabilityId::Rekey],
            auth_method: 0x01,
            auth_data: vec![0xAA; 16],
        }
    }

    fn server_config(binding: [u8; 32]) -> ServerConfig {
        ServerConfig {
            supported_versions: vec![CoreVersion::V1],
            transport_binding: binding,
            capabilities: vec![CapabilityId::Streams, CapabilityId::Rekey],
            node_identity: b"test-node-1".to_vec(),
            policy_epoch: 1,
        }
    }

    #[test]
    fn full_handshake_in_memory() {
        let binding = [0x55u8; 32];
        let mut client = ClientHandshake::new(client_config(binding));
        let mut server = ServerHandshake::new(server_config(binding));

        // Flight 1: Client → Server
        let client_init_bytes = client.create_client_init().unwrap();
        server.process_client_init(&client_init_bytes).unwrap();

        // Flight 2: Server → Client
        let server_init_bytes = server.create_server_init().unwrap();
        client.process_server_init(&server_init_bytes).unwrap();

        // Flight 3: Client → Server
        let client_finish_bytes = client.create_client_finish().unwrap();
        server.process_client_finish(&client_finish_bytes).unwrap();

        // Flight 4: Server → Client
        let (server_finish_bytes, server_keys) = server.create_server_finish().unwrap();
        let client_keys = client.process_server_finish(&server_finish_bytes).unwrap();

        // Both sides derive the same session master secret
        assert_eq!(client_keys.session_master_secret, server_keys.session_master_secret);
        assert_eq!(client_keys.control_key, server_keys.control_key);
        assert_eq!(client_keys.stream_key, server_keys.stream_key);
    }

    #[test]
    fn transport_binding_mismatch_rejected() {
        let mut client = ClientHandshake::new(client_config([0xAA; 32]));
        let mut server = ServerHandshake::new(server_config([0xBB; 32])); // different!

        let client_init_bytes = client.create_client_init().unwrap();
        let result = server.process_client_init(&client_init_bytes);
        assert!(result.is_err());
    }
}
