use std::{env, path::PathBuf};

use crate::error::AppError;

#[derive(Debug, Clone)]
pub struct NodeConfig {
    pub bind_addr: String,
    pub adapter_url: String,
    pub adapter_token: String,
    pub node_id: String,
    pub state_dir: PathBuf,
    pub instance_id: String,
    pub daemon_version: String,
    pub assignment_poll_interval_seconds: u64,
    pub health_gate_timeout_seconds: u64,
    pub metrics_prefix: String,
    pub log_level: String,
    pub allow_private_targets: bool,
}

impl NodeConfig {
    pub fn from_env() -> Result<Self, AppError> {
        let node_id = env_required("NODE_ID")?;

        Ok(Self {
            bind_addr: env_with_default("NODE_DAEMON_BIND_ADDR", "127.0.0.1:8091"),
            adapter_url: env_required("ADAPTER_URL")?,
            adapter_token: env_required("ADAPTER_TOKEN")?,
            node_id: node_id.clone(),
            state_dir: PathBuf::from(env_with_default("STATE_DIR", ".data/helix-node")),
            instance_id: env_optional("INSTANCE_ID")
                .filter(|value| !value.trim().is_empty())
                .unwrap_or_else(|| format!("node-daemon-{}", uuid::Uuid::new_v4().simple())),
            daemon_version: env_with_default("DAEMON_VERSION", "v0.1.0"),
            assignment_poll_interval_seconds: env_u64_with_default(
                "ASSIGNMENT_POLL_INTERVAL_SECONDS",
                15,
            )?,
            health_gate_timeout_seconds: env_u64_with_default("HEALTH_GATE_TIMEOUT_SECONDS", 15)?,
            metrics_prefix: env_with_default("METRICS_PREFIX", "helix_node"),
            log_level: env_with_default("LOG_LEVEL", "info"),
            allow_private_targets: env_bool_with_default("ALLOW_PRIVATE_TARGETS", false)?,
        })
    }
}

fn env_required(name: &str) -> Result<String, AppError> {
    env::var(name)
        .map_err(|_| AppError::Config(format!("missing required environment variable: {name}")))
}

fn env_optional(name: &str) -> Option<String> {
    env::var(name).ok()
}

fn env_with_default(name: &str, default: &str) -> String {
    env::var(name).unwrap_or_else(|_| default.to_string())
}

fn env_u64_with_default(name: &str, default: u64) -> Result<u64, AppError> {
    match env::var(name) {
        Ok(value) => value
            .parse::<u64>()
            .map_err(|_| AppError::Config(format!("invalid numeric value for {name}: {value}"))),
        Err(_) => Ok(default),
    }
}

fn env_bool_with_default(name: &str, default: bool) -> Result<bool, AppError> {
    match env::var(name) {
        Ok(value) => match value.trim().to_ascii_lowercase().as_str() {
            "1" | "true" | "yes" | "on" => Ok(true),
            "0" | "false" | "no" | "off" => Ok(false),
            _ => Err(AppError::Config(format!(
                "invalid boolean value for {name}: {value}"
            ))),
        },
        Err(_) => Ok(default),
    }
}
