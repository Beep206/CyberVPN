//! Shared protocol types and artifact schemas for the Beep session core.
//!
//! This crate defines the foundational types used across all Beep crates:
//! - Protocol versioning
//! - Frame type identifiers with ignorable-bit semantics
//! - Session error codes
//! - Capability identifiers for negotiation
//! - Cryptographic algorithm identifiers
//! - Artifact schemas for signed runtime configuration

pub mod artifact;
pub mod capability;
pub mod crypto;
pub mod error_code;
pub mod frame_type;
pub mod version;

pub use capability::CapabilityId;
pub use crypto::{AeadId, KdfId, KemId, SignatureId};
pub use error_code::SessionErrorCode;
pub use frame_type::FrameType;
pub use version::CoreVersion;
