//! Async session driver for the Beep VPN protocol.
//!
//! `SessionDriver` wraps the synchronous `SessionCore` and a `CoverConn` transport,
//! providing an ergonomic async API for encrypted session I/O.
//!
//! # Architecture
//!
//! ```text
//! ┌─────────────────────────────────────────┐
//! │           SessionDriver<C>              │
//! │  ┌─────────────┐   ┌──────────────────┐ │
//! │  │ SessionCore │   │ CoverConn (C)    │ │
//! │  │ (sync logic)│   │ (async transport)│ │
//! │  └─────────────┘   └──────────────────┘ │
//! └─────────────────────────────────────────┘
//! ```
//!
//! The driver keeps `beep-core` sync-only while providing a fully async
//! interface for consumers.

pub mod driver;

pub use driver::{DriverError, RecvEvent, SessionDriver};
