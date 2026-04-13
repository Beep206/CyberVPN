use std::env;

use crate::error::AppError;

#[derive(Debug, Clone)]
pub struct AdapterConfig {
    pub bind_addr: String,
    pub remnawave_url: String,
    pub remnawave_token: String,
    pub database_url: String,
    pub database_max_connections: u32,
    pub database_acquire_timeout_seconds: u64,
    pub metrics_prefix: String,
    pub internal_auth_token: String,
    pub manifest_signing_key: String,
    pub manifest_signing_key_id: String,
    pub manifest_ttl_seconds: i64,
    pub default_rollout_channel: String,
    pub helix_canary_min_connect_success_rate: f64,
    pub helix_canary_max_fallback_rate: f64,
    pub helix_canary_min_continuity_observations: i32,
    pub helix_canary_require_throughput_evidence: bool,
    pub helix_canary_min_relative_throughput_ratio: f64,
    pub helix_canary_max_relative_open_to_first_byte_gap_ratio: f64,
    pub helix_rollout_min_continuity_success_rate: f64,
    pub helix_rollout_min_cross_route_recovery_rate: f64,
    pub log_level: String,
}

impl AdapterConfig {
    pub fn from_env() -> Result<Self, AppError> {
        Ok(Self {
            bind_addr: env_or_default("ADAPTER_BIND_ADDR", "127.0.0.1:8088"),
            remnawave_url: env_or_default("REMNAWAVE_URL", "http://localhost:3005"),
            remnawave_token: env_or_default("REMNAWAVE_TOKEN", "replace-me"),
            database_url: env_or_default(
                "DATABASE_URL",
                "postgresql://cybervpn:cybervpn@localhost:6767/cybervpn",
            ),
            database_max_connections: env_or_parse("DATABASE_MAX_CONNECTIONS", 10)?,
            database_acquire_timeout_seconds: env_or_parse("DATABASE_ACQUIRE_TIMEOUT_SECONDS", 5)?,
            metrics_prefix: env_or_default("METRICS_PREFIX", "helix"),
            internal_auth_token: env_or_default("INTERNAL_AUTH_TOKEN", "replace-me-too"),
            manifest_signing_key: env_or_default(
                "MANIFEST_SIGNING_KEY",
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            ),
            manifest_signing_key_id: env_or_default("MANIFEST_SIGNING_KEY_ID", "sig-key-local-dev"),
            manifest_ttl_seconds: env_or_parse("MANIFEST_TTL_SECONDS", 3600)?,
            default_rollout_channel: env_or_default("DEFAULT_ROLLOUT_CHANNEL", "lab"),
            helix_canary_min_connect_success_rate: env_or_parse(
                "HELIX_CANARY_MIN_CONNECT_SUCCESS_RATE",
                0.98,
            )?,
            helix_canary_max_fallback_rate: env_or_parse("HELIX_CANARY_MAX_FALLBACK_RATE", 0.03)?,
            helix_canary_min_continuity_observations: env_or_parse(
                "HELIX_CANARY_MIN_CONTINUITY_OBSERVATIONS",
                5,
            )?,
            helix_canary_require_throughput_evidence: env_or_parse(
                "HELIX_CANARY_REQUIRE_THROUGHPUT_EVIDENCE",
                true,
            )?,
            helix_canary_min_relative_throughput_ratio: env_or_parse(
                "HELIX_CANARY_MIN_RELATIVE_THROUGHPUT_RATIO",
                0.90,
            )?,
            helix_canary_max_relative_open_to_first_byte_gap_ratio: env_or_parse(
                "HELIX_CANARY_MAX_RELATIVE_OPEN_TO_FIRST_BYTE_GAP_RATIO",
                1.15,
            )?,
            helix_rollout_min_continuity_success_rate: env_or_parse(
                "HELIX_ROLLOUT_MIN_CONTINUITY_SUCCESS_RATE",
                0.80,
            )?,
            helix_rollout_min_cross_route_recovery_rate: env_or_parse(
                "HELIX_ROLLOUT_MIN_CROSS_ROUTE_RECOVERY_RATE",
                0.20,
            )?,
            log_level: env_or_default("LOG_LEVEL", "info"),
        })
    }

    pub fn test_default() -> Self {
        Self {
            bind_addr: "127.0.0.1:8088".to_string(),
            remnawave_url: "http://localhost:3005".to_string(),
            remnawave_token: "test-remnawave-token".to_string(),
            database_url: "postgresql://cybervpn:cybervpn@localhost:6767/cybervpn".to_string(),
            database_max_connections: 4,
            database_acquire_timeout_seconds: 1,
            metrics_prefix: "helix".to_string(),
            internal_auth_token: "test-internal-token".to_string(),
            manifest_signing_key: "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA".to_string(),
            manifest_signing_key_id: "sig-key-test".to_string(),
            manifest_ttl_seconds: 3600,
            default_rollout_channel: "lab".to_string(),
            helix_canary_min_connect_success_rate: 0.98,
            helix_canary_max_fallback_rate: 0.03,
            helix_canary_min_continuity_observations: 5,
            helix_canary_require_throughput_evidence: true,
            helix_canary_min_relative_throughput_ratio: 0.90,
            helix_canary_max_relative_open_to_first_byte_gap_ratio: 1.15,
            helix_rollout_min_continuity_success_rate: 0.80,
            helix_rollout_min_cross_route_recovery_rate: 0.20,
            log_level: "debug".to_string(),
        }
    }
}

fn env_or_default(key: &str, default: &str) -> String {
    env::var(key).unwrap_or_else(|_| default.to_string())
}

fn env_or_parse<T>(key: &str, default: T) -> Result<T, AppError>
where
    T: std::str::FromStr + Copy + ToString,
    T::Err: std::fmt::Display,
{
    env::var(key)
        .unwrap_or_else(|_| default.to_string())
        .parse::<T>()
        .map_err(|error| AppError::Config(format!("invalid value for {key}: {error}")))
}
