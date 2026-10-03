//! Reference ClientHellos captured from a real browser.
//!
//! The raw TLS records live in `fixtures/*.json`, produced by
//! `tools/fingerprint/make_fixtures.py` against the Chromium that ships with
//! Playwright. They let CI check a client's ClientHello against a real browser
//! without a browser being installed.

use serde::Deserialize;

use crate::clienthello::{unhex, ClientHello};

#[derive(Deserialize)]
struct Raw {
    source: String,
    mode: String,
    ech_grease: bool,
    captured_on: String,
    ja4: String,
    record_hex: String,
}

/// One captured reference ClientHello.
#[derive(Debug, Clone)]
pub struct ReferenceHello {
    /// Browser build and platform it came from.
    pub source: String,
    /// What the browser was doing ("page load" or "WebSocket from a page").
    pub mode: String,
    /// Whether the hello carries the ECH GREASE extension.
    pub ech_grease: bool,
    /// Capture date.
    pub captured_on: String,
    /// JA4 as computed by the Python tool that captured it.
    pub ja4_from_capture_tool: String,
    /// The raw TLS record.
    pub record: Vec<u8>,
}

impl ReferenceHello {
    fn parse(json: &str) -> Self {
        let raw: Raw = serde_json::from_str(json).expect("fixture JSON");
        Self {
            source: raw.source,
            mode: raw.mode,
            ech_grease: raw.ech_grease,
            captured_on: raw.captured_on,
            ja4_from_capture_tool: raw.ja4,
            record: unhex(&raw.record_hex).expect("fixture hex"),
        }
    }

    /// Parse the stored record.
    pub fn hello(&self) -> ClientHello {
        ClientHello::parse(&self.record).expect("fixture parses")
    }
}

/// Chromium opening a WebSocket (ALPN `http/1.1`).
pub fn chromium_ws(ech_grease: bool) -> ReferenceHello {
    ReferenceHello::parse(if ech_grease {
        include_str!("../fixtures/chromium-ws-ech-on.json")
    } else {
        include_str!("../fixtures/chromium-ws-ech-off.json")
    })
}

/// Chromium loading a page over HTTPS (ALPN `h2, http/1.1`).
pub fn chromium_nav(ech_grease: bool) -> ReferenceHello {
    ReferenceHello::parse(if ech_grease {
        include_str!("../fixtures/chromium-nav-ech-on.json")
    } else {
        include_str!("../fixtures/chromium-nav-ech-off.json")
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rust_ja4_matches_the_python_capture_tool_on_every_fixture() {
        for r in [
            chromium_ws(true),
            chromium_ws(false),
            chromium_nav(true),
            chromium_nav(false),
        ] {
            let ja4 = r.hello().ja4().fingerprint;
            assert_eq!(
                ja4, r.ja4_from_capture_tool,
                "two independent JA4 implementations disagree on {} ({})",
                r.mode, r.source
            );
        }
    }

    #[test]
    fn fixtures_have_the_expected_browser_shape() {
        let ws = chromium_ws(true).hello();
        assert_eq!(ws.alpn, ["http/1.1"]);
        assert!(ws.has_ech());
        assert!(
            !ws.extensions.contains(&0x44cd),
            "WebSocket hello carries no ALPS"
        );

        let nav = chromium_nav(true).hello();
        assert_eq!(nav.alpn, ["h2", "http/1.1"]);
        assert!(nav.extensions.contains(&0x44cd));

        assert!(!chromium_ws(false).hello().has_ech());
        assert!(!chromium_nav(false).hello().has_ech());
        // X25519MLKEM768 key share (1184-byte ML-KEM key + 32-byte X25519).
        assert!(nav.key_shares.contains(&(0x11ec, 1216)));
    }

    #[test]
    fn ech_changes_the_fingerprint() {
        assert_ne!(
            chromium_nav(true).hello().ja4().fingerprint,
            chromium_nav(false).hello().ja4().fingerprint
        );
    }
}
