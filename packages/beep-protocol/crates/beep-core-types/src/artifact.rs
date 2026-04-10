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

/// Controls TLS/ALPN/HTTP settings for the outer presentation layer.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PresentationProfile {
    /// Unique profile identifier.
    pub id: String,
    /// ALPN protocol list (e.g., ["h2"], ["h3"]).
    pub alpn: Vec<String>,
    /// TLS provider family (e.g., "default", "boringssl").
    pub tls_provider: String,
    /// ECH mode: "disabled", "opportunistic", or "required".
    pub ech_mode: String,
    /// Retry mode: "standard", "aggressive", "conservative".
    pub retry_mode: String,
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
