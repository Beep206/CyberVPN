use chrono::{DateTime, Utc};
use reqwest::Client;
use std::time::Duration;

use crate::engine::{
    error::AppError,
    helix::config::{EngineCore, HelixManifestDocument, HelixPreparedRuntime, HelixSidecarHealth},
};

pub fn normalize_fallback_core(value: &str) -> EngineCore {
    match value {
        "xray" => EngineCore::Xray,
        _ => EngineCore::SingBox,
    }
}

pub fn fallback_core_for_manifest(manifest: &HelixManifestDocument) -> EngineCore {
    normalize_fallback_core(&manifest.capability_profile.fallback_core)
}

pub fn manifest_expired(manifest: &HelixManifestDocument) -> Result<bool, AppError> {
    let expires_at = DateTime::parse_from_rfc3339(&manifest.expires_at)
        .map_err(|error| AppError::System(format!("Invalid manifest expires_at value: {error}")))?;
    Ok(expires_at.with_timezone(&Utc) <= Utc::now())
}

pub async fn await_runtime_ready(
    runtime: &HelixPreparedRuntime,
) -> Result<HelixSidecarHealth, AppError> {
    let client = Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .map_err(AppError::Reqwest)?;
    let deadline = tokio::time::Instant::now()
        + Duration::from_secs(u64::try_from(runtime.startup_timeout_seconds.max(1)).unwrap_or(1));

    loop {
        if let Ok(response) = client.get(&runtime.health_url).send().await {
            let response = response.error_for_status().map_err(AppError::Reqwest)?;
            let health = response
                .json::<HelixSidecarHealth>()
                .await
                .map_err(AppError::Reqwest)?;
            if health.ready && health.status == "ready" {
                return Ok(health);
            }
        }

        if tokio::time::Instant::now() >= deadline {
            return Err(AppError::System(format!(
                "Helix sidecar did not become ready before {} seconds",
                runtime.startup_timeout_seconds
            )));
        }

        tokio::time::sleep(Duration::from_millis(250)).await;
    }
}
