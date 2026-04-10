//! Beep session core: frame codec, handshake state machine, protocol engine.
//!
//! This crate implements the transport-agnostic session core of the Beep protocol.
//! It must not depend on any specific HTTP version, TLS provider, or OS socket API.

pub mod cipher;
pub mod codec;
pub mod error;
pub mod frame_router;
pub mod handshake;
pub mod key_schedule;
pub mod metrics;
pub mod mux;
pub mod policy_frames;
pub mod rekey;
pub mod resumption;
pub mod session;
pub mod session_core;
pub mod telemetry;
pub mod varint;
