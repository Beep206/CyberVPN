//! Wire profile files.
//!
//! A client or node starts from one TOML file that says what the outer
//! connection looks like (TLS provider and browser preset, ALPN, server name,
//! request path, pacing) and how the transport behaves (timeouts, keepalive).
//! Changing the file changes behaviour on the wire without a rebuild.
//!
//! [`ProfileFile::validate`] is the single gate: it rejects anything that would
//! put a protocol-specific string on the wire, non-standard ALPN tokens, and
//! combinations that cannot work (for example HTTP/2 mode without `h2`).

use std::net::IpAddr;
use std::path::Path;

use serde::{Deserialize, Serialize};

use crate::artifact::{HttpMode, PresentationProfile, SniMode, TransportProfile};

/// ALPN tokens a profile may list. Anything else is a protocol-specific
/// identifier visible in the ClientHello.
pub const STANDARD_ALPN: [&str; 3] = ["h2", "http/1.1", "h3"];

/// Transport families the runtime knows.
pub const TRANSPORT_FAMILIES: [&str; 4] = ["cover_wss", "cover_h2", "cover_h3", "native_fast"];

/// Request headers a profile must not set: the HTTP stack owns them.
const RESERVED_HEADERS: [&str; 10] = [
    "host",
    "connection",
    "upgrade",
    "content-length",
    "transfer-encoding",
    "te",
    "trailer",
    "keep-alive",
    "proxy-authorization",
    "proxy-connection",
];

/// Substring no wire-visible field may contain (case-insensitive).
const FORBIDDEN_WIRE_SUBSTRING: &str = "beep";

/// Errors from loading or validating a profile file.
#[derive(Debug, thiserror::Error)]
pub enum ProfileError {
    /// The file could not be read.
    #[error("cannot read profile: {0}")]
    Io(String),
    /// The file is not valid TOML for this schema.
    #[error("cannot parse profile: {0}")]
    Parse(String),
    /// A field has a value the runtime cannot honour.
    #[error("invalid profile field `{field}`: {reason}")]
    Invalid {
        /// Offending field.
        field: &'static str,
        /// What is wrong with it.
        reason: String,
    },
}

fn invalid<T>(field: &'static str, reason: impl Into<String>) -> Result<T, ProfileError> {
    Err(ProfileError::Invalid {
        field,
        reason: reason.into(),
    })
}

/// What a profile is being validated for.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Role {
    /// A client dials out: it needs a server name and a path.
    Client,
    /// A node listens: it needs the path it will accept.
    Node,
}

/// The on-disk profile: presentation (what the connection looks like) plus
/// transport (how it behaves).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ProfileFile {
    /// Outer TLS/HTTP presentation.
    pub presentation: PresentationProfile,
    /// Transport timing and capabilities.
    pub transport: TransportProfile,
}

impl ProfileFile {
    /// Parse a profile from TOML text (no validation).
    pub fn from_toml_str(text: &str) -> Result<Self, ProfileError> {
        toml::from_str(text).map_err(|e| ProfileError::Parse(e.to_string()))
    }

    /// Read and parse a profile file (no validation).
    pub fn load(path: &Path) -> Result<Self, ProfileError> {
        let text = std::fs::read_to_string(path)
            .map_err(|e| ProfileError::Io(format!("{}: {e}", path.display())))?;
        Self::from_toml_str(&text)
    }

    /// Load and validate for `role` in one step.
    pub fn load_validated(path: &Path, role: Role) -> Result<Self, ProfileError> {
        let profile = Self::load(path)?;
        profile.validate(role)?;
        Ok(profile)
    }

    /// Check every field the runtime relies on.
    pub fn validate(&self, role: Role) -> Result<(), ProfileError> {
        validate_presentation(&self.presentation, role)?;
        validate_transport(&self.transport)
    }
}

fn neutral(field: &'static str, value: &str) -> Result<(), ProfileError> {
    if value
        .to_ascii_lowercase()
        .contains(FORBIDDEN_WIRE_SUBSTRING)
    {
        return invalid(
            field,
            format!("contains the protocol-specific string `{FORBIDDEN_WIRE_SUBSTRING}`"),
        );
    }
    Ok(())
}

fn is_dns_name(name: &str) -> bool {
    if name.is_empty() || name.len() > 253 {
        return false;
    }
    name.split('.').all(|label| {
        !label.is_empty()
            && label.len() <= 63
            && !label.starts_with('-')
            && !label.ends_with('-')
            && label
                .bytes()
                .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
    })
}

fn is_token(name: &str) -> bool {
    !name.is_empty()
        && name.bytes().all(|b| {
            b.is_ascii_lowercase()
                || b.is_ascii_digit()
                || matches!(
                    b,
                    b'-' | b'_'
                        | b'.'
                        | b'!'
                        | b'#'
                        | b'$'
                        | b'%'
                        | b'&'
                        | b'\''
                        | b'*'
                        | b'+'
                        | b'^'
                        | b'`'
                        | b'|'
                        | b'~'
                )
        })
}

fn validate_presentation(p: &PresentationProfile, role: Role) -> Result<(), ProfileError> {
    // ALPN: only standard tokens, at least one.
    if p.alpn.is_empty() {
        return invalid("alpn", "must list at least one protocol");
    }
    for token in &p.alpn {
        if !STANDARD_ALPN.contains(&token.as_str()) {
            return invalid(
                "alpn",
                format!("`{token}` is not a standard ALPN token (allowed: h2, http/1.1, h3)"),
            );
        }
    }
    match p.http_mode {
        HttpMode::WsH1 => {
            if p.alpn != ["http/1.1"] {
                return invalid(
                    "alpn",
                    "ws_h1 must offer exactly [\"http/1.1\"], otherwise the server may pick h2 \
                     and the HTTP/1.1 Upgrade cannot happen",
                );
            }
        }
        HttpMode::WsH2 => {
            if p.alpn.first().map(String::as_str) != Some("h2") {
                return invalid("alpn", "ws_h2 requires `h2` as the first ALPN token");
            }
        }
    }

    // TLS provider and fingerprint.
    match p.tls_provider.as_str() {
        "rustls" | "default" => {
            if !p.fingerprint.is_empty() {
                return invalid(
                    "fingerprint",
                    "browser presets need tls_provider = \"boringssl\"; rustls has one fixed ClientHello",
                );
            }
        }
        "boringssl" => {
            if p.fingerprint.is_empty() {
                return invalid(
                    "fingerprint",
                    "tls_provider = \"boringssl\" needs a preset such as chrome_141",
                );
            }
            let ok = p
                .fingerprint
                .strip_prefix("chrome_")
                .is_some_and(|v| !v.is_empty() && v.bytes().all(|b| b.is_ascii_digit()));
            if !ok {
                return invalid("fingerprint", format!("unknown preset `{}`", p.fingerprint));
            }
        }
        other => return invalid("tls_provider", format!("unknown provider `{other}`")),
    }

    // ECH.
    match p.ech_mode.as_str() {
        "disabled" | "opportunistic" => {}
        "required" => return invalid("ech_mode", "`required` is not supported by any dialer yet"),
        other => return invalid("ech_mode", format!("unknown mode `{other}`")),
    }
    if !matches!(
        p.retry_mode.as_str(),
        "standard" | "aggressive" | "conservative"
    ) {
        return invalid("retry_mode", format!("unknown mode `{}`", p.retry_mode));
    }

    // Server name.
    if p.server_name.is_empty() {
        if role == Role::Client {
            return invalid(
                "server_name",
                "a client profile needs the host name to present",
            );
        }
    } else {
        let is_ip = p.server_name.parse::<IpAddr>().is_ok();
        if is_ip && p.sni_mode != SniMode::Omit {
            return invalid(
                "server_name",
                "an IP literal can only be used with sni_mode = \"omit\"",
            );
        }
        if !is_ip && !is_dns_name(&p.server_name) {
            return invalid("server_name", "must be a lowercase DNS name");
        }
        neutral("server_name", &p.server_name)?;
    }

    // Path.
    if p.path.is_empty() {
        return invalid(
            "path",
            "must be set (it is the only way in for a tunnel request)",
        );
    }
    if !p.path.starts_with('/') || p.path.len() > 512 {
        return invalid("path", "must start with `/` and be at most 512 bytes");
    }
    if !p.path.bytes().all(|b| (0x21..=0x7e).contains(&b)) {
        return invalid("path", "must be visible ASCII without spaces");
    }
    neutral("path", &p.path)?;

    // Extra headers.
    for (name, value) in &p.headers {
        if !is_token(name) {
            return invalid(
                "headers",
                format!("`{name}` is not a valid lowercase header name"),
            );
        }
        if RESERVED_HEADERS.contains(&name.as_str()) || name.starts_with("sec-websocket-") {
            return invalid("headers", format!("`{name}` is set by the HTTP stack"));
        }
        if value.is_empty()
            || value.len() > 1024
            || !value.bytes().all(|b| (0x20..=0x7e).contains(&b))
            || value.trim() != value
        {
            return invalid("headers", format!("value of `{name}` is not valid"));
        }
        neutral("headers", name)?;
        neutral("headers", value)?;
    }

    // Pacing.
    if p.handshake_gap_ms > 600_000 || p.handshake_gap_jitter_ms > 600_000 {
        return invalid("handshake_gap_ms", "pacing above ten minutes is a typo");
    }

    // Pinned node key: empty (off), or exactly a 32-byte hex Ed25519 key.
    if !p.node_public_key.is_empty() && p.node_public_key_bytes().is_none() {
        return invalid(
            "node_public_key",
            "must be 64 hex characters (a 32-byte Ed25519 public key)",
        );
    }

    Ok(())
}

fn validate_transport(t: &TransportProfile) -> Result<(), ProfileError> {
    if !TRANSPORT_FAMILIES.contains(&t.family.as_str()) {
        return invalid("family", format!("unknown transport family `{}`", t.family));
    }
    if !(500..=120_000).contains(&t.connect_timeout_ms) {
        return invalid("connect_timeout_ms", "must be within 500..=120000");
    }
    if t.keepalive_ms < 1_000 {
        return invalid("keepalive_ms", "must be at least 1000");
    }
    if t.idle_timeout_ms < t.keepalive_ms.saturating_mul(2) {
        return invalid(
            "idle_timeout_ms",
            "must leave room for at least two keepalive beacons",
        );
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    const VALID: &str = r#"
        [presentation]
        id = "chrome141-ws"
        alpn = ["http/1.1"]
        tls_provider = "boringssl"
        ech_mode = "disabled"
        retry_mode = "conservative"
        server_name = "site.example"
        fingerprint = "chrome_141"
        http_mode = "ws_h1"
        path = "/static/chunk-7f3a91c2.js"
        handshake_gap_ms = 4000
        handshake_gap_jitter_ms = 2500

        [presentation.headers]
        x-edge-token = "k9Zq3vTt"

        [transport]
        id = "wss-ru"
        family = "cover_wss"
        session_core_version = "1"
        connect_timeout_ms = 8000
        idle_timeout_ms = 45000
        keepalive_ms = 15000
        supports_streams = true
        supports_datagrams = false
        allows_migration = false
    "#;

    fn valid() -> ProfileFile {
        ProfileFile::from_toml_str(VALID).unwrap()
    }

    #[test]
    fn valid_profile_passes_for_both_roles() {
        valid().validate(Role::Client).unwrap();
        valid().validate(Role::Node).unwrap();
    }

    #[test]
    fn roundtrips_through_toml() {
        let p = valid();
        let text = toml::to_string(&p).unwrap();
        assert_eq!(ProfileFile::from_toml_str(&text).unwrap(), p);
    }

    fn field_of(r: Result<(), ProfileError>) -> &'static str {
        match r {
            Err(ProfileError::Invalid { field, .. }) => field,
            other => panic!("expected an invalid-field error, got {other:?}"),
        }
    }

    #[test]
    fn rejects_non_standard_alpn() {
        let mut p = valid();
        p.presentation.alpn = vec!["http/1.1".into(), "x-private/1".into()];
        assert_eq!(field_of(p.validate(Role::Client)), "alpn");
    }

    #[test]
    fn rejects_protocol_string_in_wire_fields() {
        let mut p = valid();
        p.presentation.path = "/beep-tunnel".into();
        assert_eq!(field_of(p.validate(Role::Client)), "path");

        let mut p = valid();
        p.presentation.server_name = "node.beep.example".into();
        assert_eq!(field_of(p.validate(Role::Client)), "server_name");

        let mut p = valid();
        p.presentation.headers.insert("x-beep".into(), "1".into());
        assert_eq!(field_of(p.validate(Role::Client)), "headers");

        let mut p = valid();
        p.presentation
            .headers
            .insert("x-token".into(), "BeEp-abc".into());
        assert_eq!(field_of(p.validate(Role::Client)), "headers");
    }

    #[test]
    fn ws_h1_must_offer_only_http11() {
        let mut p = valid();
        p.presentation.alpn = vec!["h2".into(), "http/1.1".into()];
        assert_eq!(field_of(p.validate(Role::Client)), "alpn");
    }

    #[test]
    fn ws_h2_needs_h2_first() {
        let mut p = valid();
        p.presentation.http_mode = HttpMode::WsH2;
        assert_eq!(field_of(p.validate(Role::Client)), "alpn");
        p.presentation.alpn = vec!["h2".into(), "http/1.1".into()];
        p.validate(Role::Client).unwrap();
    }

    #[test]
    fn rustls_cannot_carry_a_browser_preset() {
        let mut p = valid();
        p.presentation.tls_provider = "rustls".into();
        assert_eq!(field_of(p.validate(Role::Client)), "fingerprint");
        p.presentation.fingerprint.clear();
        p.validate(Role::Client).unwrap();
    }

    #[test]
    fn boringssl_needs_a_known_preset() {
        let mut p = valid();
        p.presentation.fingerprint.clear();
        assert_eq!(field_of(p.validate(Role::Client)), "fingerprint");
        p.presentation.fingerprint = "firefox_150".into();
        assert_eq!(field_of(p.validate(Role::Client)), "fingerprint");
    }

    #[test]
    fn ech_required_is_rejected() {
        let mut p = valid();
        p.presentation.ech_mode = "required".into();
        assert_eq!(field_of(p.validate(Role::Client)), "ech_mode");
    }

    #[test]
    fn client_needs_server_name_but_node_does_not() {
        let mut p = valid();
        p.presentation.server_name.clear();
        assert_eq!(field_of(p.validate(Role::Client)), "server_name");
        p.validate(Role::Node).unwrap();
    }

    #[test]
    fn ip_literal_server_name_requires_omitted_sni() {
        let mut p = valid();
        p.presentation.server_name = "203.0.113.7".into();
        assert_eq!(field_of(p.validate(Role::Client)), "server_name");
        p.presentation.sni_mode = SniMode::Omit;
        p.validate(Role::Client).unwrap();
    }

    #[test]
    fn rejects_bad_paths() {
        for bad in ["", "no-slash", "/with space", "/caf\u{e9}"] {
            let mut p = valid();
            p.presentation.path = bad.into();
            assert_eq!(field_of(p.validate(Role::Node)), "path", "path {bad:?}");
        }
    }

    #[test]
    fn node_public_key_must_be_hex32_or_empty() {
        // Empty is fine (node auth off).
        let mut p = valid();
        p.presentation.node_public_key = String::new();
        p.validate(Role::Client).unwrap();

        // A well-formed 64-char hex key validates and decodes.
        let mut p = valid();
        p.presentation.node_public_key = "ab".repeat(32);
        p.validate(Role::Client).unwrap();
        assert!(p.presentation.node_public_key_bytes().is_some());

        // Wrong length and non-hex are rejected.
        for bad in ["abcd", &"zz".repeat(32), &"ab".repeat(31)] {
            let mut p = valid();
            p.presentation.node_public_key = bad.to_string();
            assert_eq!(
                field_of(p.validate(Role::Client)),
                "node_public_key",
                "key {bad:?}"
            );
        }
    }

    #[test]
    fn rejects_reserved_headers() {
        for name in ["host", "upgrade", "connection", "sec-websocket-key"] {
            let mut p = valid();
            p.presentation.headers.insert(name.into(), "x".into());
            assert_eq!(field_of(p.validate(Role::Client)), "headers", "{name}");
        }
    }

    #[test]
    fn transport_timings_must_leave_room_for_two_beacons() {
        let mut p = valid();
        p.transport.idle_timeout_ms = p.transport.keepalive_ms + 1;
        assert_eq!(field_of(p.validate(Role::Client)), "idle_timeout_ms");
    }

    #[test]
    fn unknown_family_is_rejected() {
        let mut p = valid();
        p.transport.family = "cover_smoke_signals".into();
        assert_eq!(field_of(p.validate(Role::Client)), "family");
    }

    #[test]
    fn older_presentation_file_without_new_fields_still_parses() {
        let old = r#"
            [presentation]
            id = "h3-standard-1"
            alpn = ["h3"]
            tls_provider = "default"
            ech_mode = "opportunistic"
            retry_mode = "standard"

            [transport]
            id = "t"
            family = "cover_h3"
            session_core_version = "1"
            connect_timeout_ms = 3500
            idle_timeout_ms = 45000
            keepalive_ms = 15000
            supports_streams = true
            supports_datagrams = true
            allows_migration = true
        "#;
        let p = ProfileFile::from_toml_str(old).unwrap();
        assert!(p.presentation.path.is_empty());
        // It parses (every added field has a default), but an h3-only profile
        // without a path is not a usable WebSocket wire profile.
        assert_eq!(field_of(p.validate(Role::Node)), "alpn");
    }
}
