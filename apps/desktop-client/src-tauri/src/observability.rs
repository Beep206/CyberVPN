use std::borrow::Cow;

use sentry::{ClientInitGuard, ClientOptions, Level};

const DEFAULT_RELEASE: &str = concat!("desktop@", env!("CARGO_PKG_VERSION"), "+local");

#[derive(Debug, Clone, PartialEq)]
pub struct NativeSentryConfig {
    pub enabled: bool,
    pub dsn: Option<String>,
    pub environment: String,
    pub release: String,
    pub traces_sample_rate: f32,
}

impl NativeSentryConfig {
    pub fn resolve() -> Self {
        let dsn = first_non_empty(
            &["DESKTOP_SENTRY_DSN", "SENTRY_DSN"],
            &[option_env!("DESKTOP_SENTRY_DSN"), option_env!("SENTRY_DSN")],
        );
        let enabled = read_bool(
            &["DESKTOP_SENTRY_ENABLED", "SENTRY_ENABLED"],
            &[option_env!("DESKTOP_SENTRY_ENABLED"), option_env!("SENTRY_ENABLED")],
        )
        .unwrap_or_else(|| dsn.is_some());
        let environment = first_non_empty(
            &[
                "DESKTOP_SENTRY_ENVIRONMENT",
                "SENTRY_ENVIRONMENT",
                "APP_ENV",
                "ENVIRONMENT",
            ],
            &[
                option_env!("DESKTOP_SENTRY_ENVIRONMENT"),
                option_env!("SENTRY_ENVIRONMENT"),
                option_env!("APP_ENV"),
                option_env!("ENVIRONMENT"),
            ],
        )
        .unwrap_or_else(default_environment);
        let release = first_non_empty(
            &["DESKTOP_SENTRY_RELEASE", "SENTRY_RELEASE"],
            &[option_env!("DESKTOP_SENTRY_RELEASE"), option_env!("SENTRY_RELEASE")],
        )
        .unwrap_or_else(|| DEFAULT_RELEASE.to_string());
        let traces_sample_rate = first_non_empty(
            &["DESKTOP_SENTRY_TRACES_SAMPLE_RATE", "SENTRY_TRACES_SAMPLE_RATE"],
            &[
                option_env!("DESKTOP_SENTRY_TRACES_SAMPLE_RATE"),
                option_env!("SENTRY_TRACES_SAMPLE_RATE"),
            ],
        )
        .map(|value| parse_sample_rate(&value))
        .unwrap_or(0.0);

        Self {
            enabled,
            dsn,
            environment,
            release,
            traces_sample_rate,
        }
    }
}

pub fn init_native_sentry() -> Option<ClientInitGuard> {
    let config = NativeSentryConfig::resolve();
    if !config.enabled {
        return None;
    }

    let dsn = config.dsn.clone()?;
    let guard = sentry::init((
        dsn,
        ClientOptions {
            attach_stacktrace: true,
            send_default_pii: false,
            environment: Some(Cow::Owned(config.environment)),
            release: Some(Cow::Owned(config.release)),
            traces_sample_rate: config.traces_sample_rate,
            ..Default::default()
        },
    ));

    sentry::configure_scope(|scope| {
        scope.set_tag("runtime_surface", "desktop-client");
        scope.set_tag("runtime_layer", "native");
        scope.set_tag("service.name", "desktop-native");
    });

    Some(guard)
}

pub fn capture_bootstrap_message(message: &str, level: Level) {
    sentry::with_scope(
        |scope| {
            scope.set_tag("runtime_surface", "desktop-client");
            scope.set_tag("runtime_layer", "native");
            scope.set_tag("app.phase", "bootstrap");
        },
        || {
            sentry::capture_message(message, level);
        },
    );
}

fn default_environment() -> String {
    if cfg!(debug_assertions) {
        "development".to_string()
    } else {
        "production".to_string()
    }
}

fn first_non_empty(runtime_names: &[&str], compiled_values: &[Option<&str>]) -> Option<String> {
    for name in runtime_names {
        if let Ok(value) = std::env::var(name) {
            let trimmed = value.trim();
            if !trimmed.is_empty() {
                return Some(trimmed.to_string());
            }
        }
    }

    for value in compiled_values.iter().flatten() {
        let trimmed = value.trim();
        if !trimmed.is_empty() {
            return Some(trimmed.to_string());
        }
    }

    None
}

fn read_bool(runtime_names: &[&str], compiled_values: &[Option<&str>]) -> Option<bool> {
    let raw = first_non_empty(runtime_names, compiled_values)?;
    match raw.to_ascii_lowercase().as_str() {
        "1" | "true" | "yes" | "on" => Some(true),
        "0" | "false" | "no" | "off" => Some(false),
        _ => None,
    }
}

fn parse_sample_rate(value: &str) -> f32 {
    value
        .parse::<f32>()
        .map(|rate| rate.clamp(0.0, 1.0))
        .unwrap_or(0.0)
}

#[cfg(test)]
mod tests {
    use super::NativeSentryConfig;
    use std::sync::Mutex;

    static ENV_MUTEX: Mutex<()> = Mutex::new(());

    #[test]
    fn resolves_explicit_native_contract() {
        let _guard = ENV_MUTEX.lock().unwrap();
        let keys = [
            "DESKTOP_SENTRY_DSN",
            "SENTRY_DSN",
            "DESKTOP_SENTRY_ENABLED",
            "DESKTOP_SENTRY_ENVIRONMENT",
            "SENTRY_ENVIRONMENT",
            "APP_ENV",
            "ENVIRONMENT",
            "DESKTOP_SENTRY_RELEASE",
            "SENTRY_RELEASE",
            "DESKTOP_SENTRY_TRACES_SAMPLE_RATE",
            "SENTRY_TRACES_SAMPLE_RATE",
            "SENTRY_ENABLED",
        ];
        let previous = snapshot_env(&keys);

        std::env::set_var("DESKTOP_SENTRY_DSN", "https://native@example.com/7");
        std::env::set_var("DESKTOP_SENTRY_ENABLED", "true");
        std::env::set_var("DESKTOP_SENTRY_ENVIRONMENT", "staging");
        std::env::set_var("DESKTOP_SENTRY_RELEASE", "desktop@0.1.5+build.7");
        std::env::set_var("DESKTOP_SENTRY_TRACES_SAMPLE_RATE", "0.2");

        let resolved = NativeSentryConfig::resolve();

        restore_env(previous);

        assert_eq!(
            resolved,
            NativeSentryConfig {
                enabled: true,
                dsn: Some("https://native@example.com/7".to_string()),
                environment: "staging".to_string(),
                release: "desktop@0.1.5+build.7".to_string(),
                traces_sample_rate: 0.2,
            }
        );
    }

    #[test]
    fn disables_native_sentry_without_dsn_by_default() {
        let _guard = ENV_MUTEX.lock().unwrap();
        let keys = [
            "DESKTOP_SENTRY_DSN",
            "SENTRY_DSN",
            "DESKTOP_SENTRY_ENABLED",
            "DESKTOP_SENTRY_ENVIRONMENT",
            "SENTRY_ENVIRONMENT",
            "APP_ENV",
            "ENVIRONMENT",
            "DESKTOP_SENTRY_RELEASE",
            "SENTRY_RELEASE",
            "DESKTOP_SENTRY_TRACES_SAMPLE_RATE",
            "SENTRY_TRACES_SAMPLE_RATE",
            "SENTRY_ENABLED",
        ];
        let previous = snapshot_env(&keys);

        for key in keys {
            std::env::remove_var(key);
        }

        let resolved = NativeSentryConfig::resolve();

        restore_env(previous);

        assert!(!resolved.enabled);
        assert_eq!(resolved.environment, "development");
        assert_eq!(resolved.release, "desktop@0.1.5+local");
        assert_eq!(resolved.traces_sample_rate, 0.0);
    }

    fn snapshot_env(keys: &[&str]) -> Vec<(String, Option<String>)> {
        keys.iter()
            .map(|key| ((*key).to_string(), std::env::var(key).ok()))
            .collect()
    }

    fn restore_env(values: Vec<(String, Option<String>)>) {
        for (key, value) in values {
            match value {
                Some(value) => std::env::set_var(&key, value),
                None => std::env::remove_var(&key),
            }
        }
    }
}
