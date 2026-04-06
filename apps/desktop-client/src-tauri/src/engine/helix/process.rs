use std::net::TcpListener;
use std::path::PathBuf;

use tauri::AppHandle;

use crate::engine::{
    error::AppError,
    helix::{
        config::{HelixPreparedRuntime, HelixResolvedManifest, HelixSidecarConfig},
        health::fallback_core_for_manifest,
    },
};

pub fn sidecar_binary_name() -> &'static str {
    env!("CARGO_PKG_NAME")
}

pub fn sidecar_binary_path(_app: &AppHandle) -> Result<PathBuf, AppError> {
    std::env::current_exe().map_err(AppError::Io)
}

fn reserve_health_addr() -> Result<(String, String), AppError> {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let addr = listener.local_addr()?;
    let bind_addr = addr.to_string();
    let health_url = format!("http://{bind_addr}/healthz");
    drop(listener);
    Ok((bind_addr, health_url))
}

fn reserve_proxy_addr() -> Result<(String, String), AppError> {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let addr = listener.local_addr()?;
    let bind_addr = addr.to_string();
    let proxy_url = format!("socks5://{bind_addr}");
    drop(listener);
    Ok((bind_addr, proxy_url))
}

pub fn build_sidecar_config(resolved_manifest: &HelixResolvedManifest) -> HelixSidecarConfig {
    let manifest = &resolved_manifest.manifest;
    let fallback_core = fallback_core_for_manifest(manifest).as_str().to_string();
    let (health_bind_addr, health_url) = reserve_health_addr().unwrap_or_else(|_| {
        (
            "127.0.0.1:38991".to_string(),
            "http://127.0.0.1:38991/healthz".to_string(),
        )
    });
    let (proxy_bind_addr, proxy_url) = reserve_proxy_addr().unwrap_or_else(|_| {
        (
            "127.0.0.1:38990".to_string(),
            "socks5://127.0.0.1:38990".to_string(),
        )
    });

    HelixSidecarConfig {
        schema_version: "1.0".to_string(),
        manifest_id: manifest.manifest_id.clone(),
        manifest_version_id: resolved_manifest.manifest_version_id.clone(),
        rollout_id: manifest.rollout_id.clone(),
        health_bind_addr,
        health_url,
        proxy_bind_addr,
        proxy_url,
        transport_family: manifest.transport.transport_family.clone(),
        session_mode: manifest.transport.session_mode.clone(),
        transport_profile_id: manifest.transport_profile.transport_profile_id.clone(),
        profile_family: manifest.transport_profile.profile_family.clone(),
        profile_version: manifest.transport_profile.profile_version,
        policy_version: manifest.transport_profile.policy_version,
        compatibility_window: manifest.compatibility_window.clone(),
        fallback_core,
        required_capabilities: manifest.capability_profile.required_capabilities.clone(),
        startup_timeout_seconds: manifest
            .capability_profile
            .health_policy
            .startup_timeout_seconds,
        runtime_unhealthy_threshold: manifest
            .capability_profile
            .health_policy
            .runtime_unhealthy_threshold,
        credentials: manifest.credentials.clone(),
        routes: manifest.routes.clone(),
        observability: manifest.observability.clone(),
        integrity: manifest.integrity.clone(),
    }
}

pub async fn prepare_runtime_plan(
    app: &AppHandle,
    resolved_manifest: &HelixResolvedManifest,
) -> Result<HelixPreparedRuntime, AppError> {
    let app_dir = crate::engine::store::get_app_dir(app)?;
    let runtime_dir = app_dir.join("helix");
    tokio::fs::create_dir_all(&runtime_dir).await?;

    let sidecar_config = build_sidecar_config(resolved_manifest);
    let config_path = runtime_dir.join("runtime.json");
    tokio::fs::write(&config_path, serde_json::to_vec_pretty(&sidecar_config)?).await?;

    let sidecar_path = sidecar_binary_path(app)?;

    Ok(HelixPreparedRuntime {
        manifest_id: resolved_manifest.manifest.manifest_id.clone(),
        manifest_version_id: resolved_manifest.manifest_version_id.clone(),
        rollout_id: resolved_manifest.manifest.rollout_id.clone(),
        transport_profile_id: resolved_manifest
            .manifest
            .transport_profile
            .transport_profile_id
            .clone(),
        config_path: config_path.display().to_string(),
        sidecar_path: sidecar_path.display().to_string(),
        binary_available: sidecar_path.exists(),
        health_url: sidecar_config.health_url.clone(),
        proxy_url: sidecar_config.proxy_url.clone(),
        fallback_core: sidecar_config.fallback_core,
        route_count: resolved_manifest.manifest.routes.len(),
        startup_timeout_seconds: resolved_manifest
            .manifest
            .capability_profile
            .health_policy
            .startup_timeout_seconds,
    })
}

#[cfg(test)]
mod tests {
    use crate::engine::helix::config::{
        HelixManifestCapabilityProfile, HelixManifestCompatibilityWindow, HelixManifestCredentials,
        HelixManifestDocument, HelixManifestHealthPolicy, HelixManifestIntegrity,
        HelixManifestObservability, HelixManifestRoute, HelixManifestSubject,
        HelixManifestTransport, HelixManifestTransportProfile, HelixResolvedManifest,
        HelixSignature,
    };

    use super::build_sidecar_config;

    fn sample_resolved_manifest(fallback_core: &str) -> HelixResolvedManifest {
        HelixResolvedManifest {
            manifest_version_id: "manifest-version-1".to_string(),
            selected_profile_policy: None,
            manifest: HelixManifestDocument {
                schema_version: "1.1".to_string(),
                manifest_id: "manifest-1".to_string(),
                rollout_id: "rollout-1".to_string(),
                issued_at: "2026-03-31T12:00:00Z".to_string(),
                expires_at: "2026-03-31T13:00:00Z".to_string(),
                subject: HelixManifestSubject {
                    user_id: "user-1".to_string(),
                    desktop_client_id: "desktop-1".to_string(),
                    entitlement_id: "subscription:user-1".to_string(),
                    channel: "lab".to_string(),
                },
                transport: HelixManifestTransport {
                    transport_family: "helix".to_string(),
                    protocol_version: 1,
                    session_mode: "hybrid".to_string(),
                },
                transport_profile: HelixManifestTransportProfile {
                    transport_profile_id: "ptp-edge-hybrid-v4".to_string(),
                    profile_family: "edge-hybrid".to_string(),
                    profile_version: 4,
                    policy_version: 7,
                    deprecation_state: "active".to_string(),
                },
                compatibility_window: HelixManifestCompatibilityWindow {
                    profile_family: "edge-hybrid".to_string(),
                    min_transport_profile_version: 2,
                    max_transport_profile_version: 4,
                },
                capability_profile: HelixManifestCapabilityProfile {
                    required_capabilities: vec![
                        "protocol.v1".to_string(),
                        "runtime.rollback".to_string(),
                    ],
                    fallback_core: fallback_core.to_string(),
                    health_policy: HelixManifestHealthPolicy {
                        startup_timeout_seconds: 20,
                        runtime_unhealthy_threshold: 3,
                    },
                },
                routes: vec![HelixManifestRoute {
                    endpoint_ref: "edge-eu-west".to_string(),
                    dial_host: "127.0.0.1".to_string(),
                    dial_port: 9443,
                    server_name: Some("edge-eu-west.local".to_string()),
                    preference: 10,
                    policy_tag: "primary".to_string(),
                }],
                credentials: HelixManifestCredentials {
                    key_id: "sig-key-1".to_string(),
                    token: "pt_tok_123".to_string(),
                },
                integrity: HelixManifestIntegrity {
                    manifest_hash: "sha256:1234".to_string(),
                    signature: HelixSignature {
                        alg: "ed25519".to_string(),
                        key_id: "sig-key-1".to_string(),
                        sig: "signed".to_string(),
                    },
                },
                observability: HelixManifestObservability {
                    trace_id: "trace-1".to_string(),
                    metrics_namespace: "helix".to_string(),
                },
            },
        }
    }

    #[test]
    fn sidecar_config_normalizes_invalid_fallback_to_sing_box() {
        let config = build_sidecar_config(&sample_resolved_manifest("unexpected-core"));
        assert_eq!(config.fallback_core, "sing-box");
    }

    #[test]
    fn sidecar_config_preserves_xray_fallback() {
        let config = build_sidecar_config(&sample_resolved_manifest("xray"));
        assert_eq!(config.fallback_core, "xray");
    }
}
