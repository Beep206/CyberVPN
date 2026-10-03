//! Artifact schemas for signed runtime configuration.
//!
//! These schemas define the independently-deployable, signed artifacts that
//! control Beep runtime behavior without requiring binary upgrades.
//!
//! All artifacts use TOML serialization for human readability. Each artifact
//! is wrapped in [`SignedArtifact`] which carries metadata and a signature.

use serde::{Deserialize, Serialize};

// ── Signed artifact wrapper ────────────────────────────────────────────────

/// A signed artifact envelope.
///
/// The `signature` field covers `format_version` + serialized `payload`.
/// Actual signature verification is deferred to the control-plane integration
/// milestone; this type defines the schema contract.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SignedArtifact<T> {
    /// Envelope format version (currently 1).
    pub format_version: u32,
    /// The artifact payload.
    pub payload: T,
    /// Ed25519 (or future ML-DSA) signature bytes, hex-encoded.
    pub signature: String,
    /// Identifier of the signing key.
    pub signer_id: String,
    /// Unix timestamp when the artifact was issued.
    pub issued_at: u64,
    /// Optional expiration timestamp.
    pub expires_at: Option<u64>,
}

// ── Session core version artifact ──────────────────────────────────────────

/// Selects wire semantics and the capability set for a session core instance.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SessionCoreVersionArtifact {
    /// Unique artifact identifier.
    pub id: String,
    /// Protocol version number (e.g., 1).
    pub version: u32,
    /// Mandatory capabilities that both peers must support.
    pub mandatory_capabilities: Vec<u16>,
    /// Optional capabilities that may be negotiated.
    pub optional_capabilities: Vec<u16>,
    /// Mandatory-to-implement KEM.
    pub mandatory_kem: u16,
    /// Mandatory-to-implement AEAD.
    pub mandatory_aead: u16,
    /// Mandatory-to-implement KDF.
    pub mandatory_kdf: u16,
}

// ── Transport profile artifact ─────────────────────────────────────────────

/// Selects the outer transport family and transport-level parameters.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TransportProfile {
    /// Unique profile identifier (e.g., "h2-global-stable").
    pub id: String,
    /// Transport family: "cover_h2", "cover_h3", or "native_fast".
    pub family: String,
    /// Required session core version.
    pub session_core_version: String,
    /// Connection establishment timeout in milliseconds.
    pub connect_timeout_ms: u64,
    /// Idle timeout before the transport is closed, in milliseconds.
    pub idle_timeout_ms: u64,
    /// Keepalive interval in milliseconds.
    pub keepalive_ms: u64,
    /// Whether this transport supports reliable streams.
    pub supports_streams: bool,
    /// Whether this transport supports unreliable datagrams.
    pub supports_datagrams: bool,
    /// Whether this transport allows connection migration.
    pub allows_migration: bool,
}

// ── Presentation profile artifact ──────────────────────────────────────────

/// How the outer HTTP layer carries the tunnel.
#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum HttpMode {
    /// WebSocket over an HTTP/1.1 Upgrade (RFC 6455); ALPN `http/1.1`.
    #[default]
    WsH1,
    /// WebSocket over HTTP/2 Extended CONNECT (RFC 8441); ALPN starts with `h2`.
    WsH2,
}

/// What the TLS ClientHello says about the server name.
#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum SniMode {
    /// Send `server_name` as the SNI (what a browser does for a host name).
    #[default]
    ServerName,
    /// Send no SNI extension at all.
    Omit,
}

/// Controls TLS/ALPN/HTTP settings for the outer presentation layer.
///
/// The fields up to `retry_mode` are the original schema; the rest were added
/// in stage 2 so a client or node can start from one file and a change to that
/// file changes behaviour on the wire without a rebuild. Every added field has
/// a serde default, so older files keep parsing.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PresentationProfile {
    /// Unique profile identifier.
    pub id: String,
    /// ALPN protocol list (e.g., ["h2"], ["h3"]). Only standard tokens are allowed.
    pub alpn: Vec<String>,
    /// TLS provider family: "rustls" (alias "default") or "boringssl".
    pub tls_provider: String,
    /// ECH mode: "disabled" or "opportunistic" ("required" is rejected for now).
    pub ech_mode: String,
    /// Retry mode: "standard", "aggressive", "conservative". Picks the default
    /// handshake pacing when `handshake_gap_ms` is zero.
    pub retry_mode: String,

    /// Host name used for the SNI and the HTTP authority.
    #[serde(default)]
    pub server_name: String,
    /// Whether to send the SNI extension.
    #[serde(default)]
    pub sni_mode: SniMode,
    /// Browser preset for `tls_provider = "boringssl"` (for example
    /// `chrome_141`); empty for the rustls provider.
    #[serde(default)]
    pub fingerprint: String,
    /// How the outer HTTP layer carries the tunnel.
    #[serde(default)]
    pub http_mode: HttpMode,
    /// Request path, starting with `/`. On the node this is the path a request
    /// must carry to reach the tunnel.
    #[serde(default)]
    pub path: String,
    /// Minimum gap between connection attempts, in milliseconds. Zero means
    /// "take it from `retry_mode`".
    #[serde(default)]
    pub handshake_gap_ms: u64,
    /// Upper bound of the random addition to the gap, in milliseconds.
    #[serde(default)]
    pub handshake_gap_jitter_ms: u64,
    /// Pinned Ed25519 node public key, hex-encoded (64 hex chars = 32 bytes).
    /// When set, the client requires the node to sign the handshake transcript
    /// with the matching key and rejects it otherwise. Empty disables node
    /// authentication (lab only). A scalar, so it is kept before `headers`:
    /// TOML would otherwise fold a key after the `[...headers]` table into it.
    #[serde(default)]
    pub node_public_key: String,
    /// Extra request headers (for example the secret header the front proxy
    /// checks). Kept last so the TOML serializer can emit it as a table.
    #[serde(default)]
    pub headers: std::collections::BTreeMap<String, String>,
}

impl PresentationProfile {
    /// The pause between connection attempts as `(base, max_extra)`.
    ///
    /// Explicit `handshake_gap_ms` wins; otherwise `retry_mode` supplies the
    /// default. A random value in `[0, max_extra]` is added to `base` by the
    /// caller, so two clients do not retry in lockstep.
    pub fn handshake_pacing(&self) -> (std::time::Duration, std::time::Duration) {
        use std::time::Duration;
        if self.handshake_gap_ms > 0 {
            return (
                Duration::from_millis(self.handshake_gap_ms),
                Duration::from_millis(self.handshake_gap_jitter_ms),
            );
        }
        match self.retry_mode.as_str() {
            "aggressive" => (Duration::from_millis(500), Duration::from_millis(500)),
            "conservative" => (Duration::from_millis(5000), Duration::from_millis(3000)),
            _ => (Duration::from_millis(2000), Duration::from_millis(1000)),
        }
    }

    /// The pinned node public key as 32 raw bytes.
    ///
    /// Returns `None` when `node_public_key` is empty (node authentication
    /// off) or malformed (not 64 hex characters). Validation rejects the
    /// malformed case up front, so after `ProfileFile::load_validated` a
    /// non-empty field always decodes.
    pub fn node_public_key_bytes(&self) -> Option<[u8; 32]> {
        decode_hex32(&self.node_public_key)
    }
}

/// Decode a 64-character hex string into 32 bytes, or `None` if the length is
/// wrong or a character is not a hex digit.
pub fn decode_hex32(s: &str) -> Option<[u8; 32]> {
    if s.len() != 64 {
        return None;
    }
    let mut out = [0u8; 32];
    let bytes = s.as_bytes();
    for (i, slot) in out.iter_mut().enumerate() {
        let hi = (bytes[2 * i] as char).to_digit(16)?;
        let lo = (bytes[2 * i + 1] as char).to_digit(16)?;
        *slot = ((hi << 4) | lo) as u8;
    }
    Some(out)
}

// ── Policy bundle artifact ─────────────────────────────────────────────────

/// Controls profile selection, retry behavior, and rollout rules.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PolicyBundle {
    /// Unique bundle identifier.
    pub id: String,
    /// Ordered list of candidate transport profile IDs.
    pub candidates: Vec<String>,
    /// Maximum consecutive failures before switching to next candidate.
    pub max_failures_before_switch: u32,
    /// How long a successful profile sticks, in seconds.
    pub sticky_ttl_seconds: u64,
    /// Telemetry budget level: "off", "minimal", "normal", "verbose".
    pub telemetry_budget: String,
}

// ── Probe recipe artifact ──────────────────────────────────────────────────

/// Defines path probes the client runs before selecting a transport profile.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ProbeRecipe {
    /// Unique recipe identifier.
    pub id: String,
    /// Individual probe steps.
    pub probes: Vec<Probe>,
    /// Overall timeout for all probes in milliseconds.
    pub timeout_ms: u64,
}

/// A single probe step.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Probe {
    /// Type of probe: "udp_reachability", "tcp_connect", "tls_handshake",
    /// "http_get", "dns_resolve", "mtu_discovery".
    pub probe_type: String,
    /// Target address or hostname.
    pub target: String,
    /// Probe-specific timeout in milliseconds.
    pub timeout_ms: u64,
    /// If true, failure of this probe eliminates dependent profiles.
    pub required: bool,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn transport_profile_roundtrip_toml() {
        let profile = TransportProfile {
            id: "h3-global-stable".into(),
            family: "cover_h3".into(),
            session_core_version: "1".into(),
            connect_timeout_ms: 3500,
            idle_timeout_ms: 45000,
            keepalive_ms: 15000,
            supports_streams: true,
            supports_datagrams: true,
            allows_migration: true,
        };
        let serialized = toml::to_string(&profile).unwrap();
        let deserialized: TransportProfile = toml::from_str(&serialized).unwrap();
        assert_eq!(profile, deserialized);
    }

    #[test]
    fn policy_bundle_roundtrip_toml() {
        let bundle = PolicyBundle {
            id: "default-eurasia".into(),
            candidates: vec!["h3-global-stable".into(), "h2-global-stable".into()],
            max_failures_before_switch: 2,
            sticky_ttl_seconds: 21600,
            telemetry_budget: "normal".into(),
        };
        let serialized = toml::to_string(&bundle).unwrap();
        let deserialized: PolicyBundle = toml::from_str(&serialized).unwrap();
        assert_eq!(bundle, deserialized);
    }

    #[test]
    fn presentation_profile_from_doc_example() {
        // Matches the example from docs/04-transport-profiles.md
        let toml_str = r#"
            id = "h3-standard-1"
            alpn = ["h3"]
            tls_provider = "default"
            ech_mode = "opportunistic"
            retry_mode = "standard"
        "#;
        let profile: PresentationProfile = toml::from_str(toml_str).unwrap();
        assert_eq!(profile.id, "h3-standard-1");
        assert_eq!(profile.alpn, vec!["h3"]);
        assert_eq!(profile.ech_mode, "opportunistic");
    }

    #[test]
    fn presentation_profile_extended_roundtrip_toml() {
        let mut headers = std::collections::BTreeMap::new();
        headers.insert("x-edge-token".to_string(), "abc123".to_string());
        let profile = PresentationProfile {
            id: "chrome141-ws".into(),
            alpn: vec!["http/1.1".into()],
            tls_provider: "boringssl".into(),
            ech_mode: "disabled".into(),
            retry_mode: "conservative".into(),
            server_name: "site.example".into(),
            sni_mode: SniMode::ServerName,
            fingerprint: "chrome_141".into(),
            http_mode: HttpMode::WsH1,
            path: "/assets/app.js".into(),
            handshake_gap_ms: 4000,
            handshake_gap_jitter_ms: 2500,
            node_public_key: String::new(),
            headers,
        };
        let serialized = toml::to_string(&profile).unwrap();
        let deserialized: PresentationProfile = toml::from_str(&serialized).unwrap();
        assert_eq!(profile, deserialized);
    }

    #[test]
    fn handshake_pacing_prefers_explicit_gap_then_retry_mode() {
        use std::time::Duration;
        let mut p: PresentationProfile = toml::from_str(
            r#"
            id = "x"
            alpn = ["http/1.1"]
            tls_provider = "rustls"
            ech_mode = "disabled"
            retry_mode = "conservative"
        "#,
        )
        .unwrap();
        assert_eq!(
            p.handshake_pacing(),
            (Duration::from_millis(5000), Duration::from_millis(3000))
        );
        p.handshake_gap_ms = 700;
        p.handshake_gap_jitter_ms = 300;
        assert_eq!(
            p.handshake_pacing(),
            (Duration::from_millis(700), Duration::from_millis(300))
        );
    }

    #[test]
    fn probe_recipe_roundtrip() {
        let recipe = ProbeRecipe {
            id: "default-probe".into(),
            probes: vec![
                Probe {
                    probe_type: "udp_reachability".into(),
                    target: "probe.example.com:443".into(),
                    timeout_ms: 2000,
                    required: false,
                },
                Probe {
                    probe_type: "tcp_connect".into(),
                    target: "node.example.com:443".into(),
                    timeout_ms: 3000,
                    required: true,
                },
            ],
            timeout_ms: 5000,
        };
        let serialized = toml::to_string(&recipe).unwrap();
        let deserialized: ProbeRecipe = toml::from_str(&serialized).unwrap();
        assert_eq!(recipe, deserialized);
    }

    #[test]
    fn signed_artifact_envelope() {
        let artifact = SignedArtifact {
            format_version: 1,
            payload: PolicyBundle {
                id: "test".into(),
                candidates: vec!["h2-stable".into()],
                max_failures_before_switch: 3,
                sticky_ttl_seconds: 3600,
                telemetry_budget: "minimal".into(),
            },
            signature: "deadbeef".into(),
            signer_id: "control-1".into(),
            issued_at: 1712577600,
            expires_at: Some(1712664000),
        };
        let serialized = toml::to_string(&artifact).unwrap();
        let deserialized: SignedArtifact<PolicyBundle> = toml::from_str(&serialized).unwrap();
        assert_eq!(deserialized.format_version, 1);
        assert_eq!(deserialized.payload.id, "test");
    }
}
