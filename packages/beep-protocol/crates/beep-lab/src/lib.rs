//! Lab instruments for Beep: the tools that turn "looks like a browser" and
//! "paces its handshakes" from claims into measurements.
//!
//! - [`clienthello`]: parse a ClientHello and compute its JA4.
//! - [`fixtures`]: reference ClientHellos captured from a real browser.
//! - [`recorder`]: a recording proxy for what a passive observer sees.

pub mod clienthello;
pub mod fixtures;
pub mod recorder;

pub use clienthello::{is_grease, ClientHello, Ja4, ParseError};
pub use recorder::{cleartext_prefix, contains_ci, Capture, RecordingProxy};
