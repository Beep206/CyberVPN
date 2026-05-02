use std::borrow::Cow;

use sentry::{ClientInitGuard, ClientOptions};
use subtle::ConstantTimeEq;

use crate::{config::NodeConfig, error::AppError};

pub const RUNTIME_SURFACE: &str = "helix-node";
pub const SERVICE_NAME: &str = "helix-node";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SentryContractSnapshot {
    pub runtime_surface: &'static str,
    pub service: &'static str,
    pub environment: String,
    pub release: String,
    pub dsn_configured: bool,
    pub node_id: String,
    pub daemon_version: String,
}

pub fn init_sentry(config: &NodeConfig) -> Result<Option<ClientInitGuard>, AppError> {
    let dsn = config.sentry_dsn.trim();
    if dsn.is_empty() {
        return Ok(None);
    }

    let parsed_dsn: sentry::types::Dsn = dsn
        .parse()
        .map_err(|error| AppError::Config(format!("invalid SENTRY_DSN: {error}")))?;

    let guard = sentry::init((
        parsed_dsn,
        ClientOptions {
            attach_stacktrace: true,
            send_default_pii: false,
            environment: Some(Cow::Owned(config.environment.clone())),
            release: Some(Cow::Owned(config.sentry_release.clone())),
            traces_sample_rate: config.sentry_traces_sample_rate,
            in_app_include: vec!["helix_node"],
            ..Default::default()
        },
    ));

    sentry::configure_scope(|scope| {
        scope.set_tag("runtime_surface", RUNTIME_SURFACE);
        scope.set_tag("service.name", SERVICE_NAME);
        scope.set_tag("node_id", config.node_id.clone());
        scope.set_tag("daemon_version", config.daemon_version.clone());
        scope.set_tag("instance_id", config.instance_id.clone());
    });

    Ok(Some(guard))
}

pub fn sentry_contract(config: &NodeConfig) -> SentryContractSnapshot {
    SentryContractSnapshot {
        runtime_surface: RUNTIME_SURFACE,
        service: SERVICE_NAME,
        environment: config.environment.clone(),
        release: config.sentry_release.clone(),
        dsn_configured: !config.sentry_dsn.trim().is_empty(),
        node_id: config.node_id.clone(),
        daemon_version: config.daemon_version.clone(),
    }
}

pub fn is_observability_authorized(configured_secret: &str, provided_secret: Option<&str>) -> bool {
    let configured = configured_secret.trim();
    let provided = provided_secret.unwrap_or_default().trim();

    if configured.is_empty() || provided.is_empty() || configured.len() != provided.len() {
        return false;
    }

    configured.as_bytes().ct_eq(provided.as_bytes()).into()
}

#[cfg(test)]
mod tests {
    use std::env;

    use crate::config::NodeConfig;

    use super::{is_observability_authorized, sentry_contract, RUNTIME_SURFACE, SERVICE_NAME};

    #[test]
    fn sentry_contract_snapshot_reflects_runtime_config() {
        let mut config = NodeConfig::test_default(env::temp_dir());
        config.environment = "staging".to_string();
        config.sentry_release = "helix-node@abc123".to_string();

        let snapshot = sentry_contract(&config);

        assert_eq!(snapshot.runtime_surface, RUNTIME_SURFACE);
        assert_eq!(snapshot.service, SERVICE_NAME);
        assert_eq!(snapshot.environment, "staging");
        assert_eq!(snapshot.release, "helix-node@abc123");
        assert_eq!(snapshot.node_id, "node-test-01");
        assert_eq!(snapshot.daemon_version, "v0.1.0");
        assert!(snapshot.dsn_configured);
    }

    #[test]
    fn observability_authorization_requires_matching_secret() {
        assert!(is_observability_authorized(
            "helix-secret",
            Some("helix-secret")
        ));
        assert!(!is_observability_authorized(
            "helix-secret",
            Some("wrong-secret")
        ));
        assert!(!is_observability_authorized("helix-secret", None));
        assert!(!is_observability_authorized("", Some("helix-secret")));
    }
}
