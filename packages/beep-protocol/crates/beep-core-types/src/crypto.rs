//! Cryptographic algorithm identifiers for the Beep session core.
//!
//! These IDs are used during handshake negotiation and in artifact schemas.
//! The session core negotiates crypto independently from the outer TLS handshake.

/// Key Encapsulation Mechanism / Key Agreement identifier.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
#[repr(u16)]
pub enum KemId {
    /// X25519 Diffie-Hellman (mandatory in v1).
    X25519 = 0x01,
    /// Hybrid: X25519 + ML-KEM-768 (optional in v1).
    X25519MlKem768 = 0x02,
}

impl KemId {
    pub fn from_wire(v: u16) -> Option<Self> {
        match v {
            0x01 => Some(Self::X25519),
            0x02 => Some(Self::X25519MlKem768),
            _ => None,
        }
    }

    pub const fn to_wire(self) -> u16 {
        self as u16
    }

    /// Expected public key share length in bytes.
    pub const fn key_share_len(self) -> usize {
        match self {
            Self::X25519 => 32,
            // X25519 (32) + ML-KEM-768 encapsulation key (1184)
            Self::X25519MlKem768 => 32 + 1184,
        }
    }
}

/// Authenticated Encryption with Associated Data identifier.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
#[repr(u16)]
pub enum AeadId {
    /// ChaCha20-Poly1305 (mandatory in v1).
    ChaCha20Poly1305 = 0x01,
    /// AES-256-GCM (optional in v1).
    Aes256Gcm = 0x02,
}

impl AeadId {
    pub fn from_wire(v: u16) -> Option<Self> {
        match v {
            0x01 => Some(Self::ChaCha20Poly1305),
            0x02 => Some(Self::Aes256Gcm),
            _ => None,
        }
    }

    pub const fn to_wire(self) -> u16 {
        self as u16
    }

    /// AEAD key length in bytes.
    pub const fn key_len(self) -> usize {
        match self {
            Self::ChaCha20Poly1305 => 32,
            Self::Aes256Gcm => 32,
        }
    }

    /// AEAD nonce length in bytes.
    pub const fn nonce_len(self) -> usize {
        match self {
            Self::ChaCha20Poly1305 => 12,
            Self::Aes256Gcm => 12,
        }
    }

    /// AEAD authentication tag length in bytes.
    pub const fn tag_len(self) -> usize {
        16 // Both use 16-byte tags
    }
}

/// Key Derivation Function identifier.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
#[repr(u16)]
pub enum KdfId {
    /// HKDF-SHA256 (mandatory in v1).
    HkdfSha256 = 0x01,
    /// HKDF-SHA384 (optional in v1).
    HkdfSha384 = 0x02,
}

impl KdfId {
    pub fn from_wire(v: u16) -> Option<Self> {
        match v {
            0x01 => Some(Self::HkdfSha256),
            0x02 => Some(Self::HkdfSha384),
            _ => None,
        }
    }

    pub const fn to_wire(self) -> u16 {
        self as u16
    }
}

/// Signature algorithm identifier (for control-plane artifacts and node identity).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
#[repr(u16)]
pub enum SignatureId {
    /// Ed25519 (mandatory in v1).
    Ed25519 = 0x01,
    /// ML-DSA (reserved for future use).
    MlDsa = 0x02,
}

impl SignatureId {
    pub fn from_wire(v: u16) -> Option<Self> {
        match v {
            0x01 => Some(Self::Ed25519),
            0x02 => Some(Self::MlDsa),
            _ => None,
        }
    }

    pub const fn to_wire(self) -> u16 {
        self as u16
    }
}
