pub mod benchmark;
pub mod client;
pub mod config;
pub mod health;
pub mod process;
pub mod sidecar;

use tauri::AppHandle;

use crate::engine::{
    error::AppError,
    helix::{
        client::{
            fetch_capability_defaults, load_backend_access_token,
            report_runtime_event as send_runtime_event, resolve_manifest,
            save_backend_access_token,
        },
        config::{
            default_desktop_capabilities, ensure_manifest_compatible, HelixCapabilityDefaults,
            HelixPreparedRuntime, HelixResolveManifestRequest, HelixResolvedManifest,
            HelixRuntimeEventReport, HelixRuntimeEventRequest, HelixRuntimeState,
        },
        health::{fallback_core_for_manifest, manifest_expired},
        process::prepare_runtime_plan,
    },
    store,
};

pub fn get_or_create_desktop_client_id(app: &AppHandle) -> Result<String, AppError> {
    let mut store_data = store::load_store(app)?;
    if let Some(existing) = store_data.helix_desktop_client_id.clone() {
        return Ok(existing);
    }

    let client_id = format!("desktop-{}", uuid::Uuid::new_v4().simple());
    store_data.helix_desktop_client_id = Some(client_id.clone());
    store::save_store(app, &store_data)?;
    Ok(client_id)
}

pub fn get_stored_manifest(app: &AppHandle) -> Result<Option<HelixResolvedManifest>, AppError> {
    Ok(store::load_store(app)?.helix_last_manifest)
}

pub fn get_runtime_state(app: &AppHandle) -> Result<HelixRuntimeState, AppError> {
    let desktop_client_id = get_or_create_desktop_client_id(app)?;
    let store_data = store::load_store(app)?;

    Ok(HelixRuntimeState {
        backend_url: store_data.helix_backend_url,
        desktop_client_id,
        last_manifest: store_data.helix_last_manifest,
        last_prepared_runtime: store_data.helix_last_prepared_runtime,
        last_fallback_reason: store_data.helix_last_fallback_reason,
    })
}

pub async fn resolve_manifest_for_desktop(
    app: &AppHandle,
    base_url: &str,
    access_token: &str,
    preferred_fallback_core: Option<String>,
) -> Result<HelixResolvedManifest, AppError> {
    let desktop_client_id = get_or_create_desktop_client_id(app)?;
    let local_capabilities = default_desktop_capabilities();
    let backend_capabilities = fetch_capability_defaults(base_url, access_token).await?;

    let request = HelixResolveManifestRequest {
        desktop_client_id,
        trace_id: format!("trace-{}", uuid::Uuid::new_v4().simple()),
        channel: Some(backend_capabilities.default_channel.clone()),
        supported_protocol_versions: local_capabilities.supported_protocol_versions.clone(),
        supported_transport_profiles: local_capabilities.supported_transport_profiles.clone(),
        preferred_fallback_core,
    };

    let resolved_manifest = resolve_manifest(base_url, access_token, &request).await?;
    ensure_manifest_compatible(&resolved_manifest.manifest, &local_capabilities)?;

    if let Err(error) = save_backend_access_token(access_token) {
        eprintln!("Failed to store Helix backend access token: {error}");
    }

    let mut store_data = store::load_store(app)?;
    store_data.helix_backend_url = Some(base_url.trim_end_matches('/').to_string());
    store_data.helix_last_manifest = Some(resolved_manifest.clone());
    store_data.helix_last_prepared_runtime = None;
    store_data.helix_last_fallback_reason = None;
    store::save_store(app, &store_data)?;

    Ok(resolved_manifest)
}

pub fn local_capabilities() -> HelixCapabilityDefaults {
    default_desktop_capabilities()
}

pub async fn prepare_runtime_for_launch(app: &AppHandle) -> Result<HelixPreparedRuntime, AppError> {
    let mut store_data = store::load_store(app)?;
    let manifest = store_data
        .helix_last_manifest
        .clone()
        .ok_or(AppError::Actionable {
            error: "Helix manifest is missing".to_string(),
            resolution: "Resolve a compatible Helix manifest in Settings before connecting."
                .to_string(),
        })?;

    ensure_manifest_compatible(&manifest.manifest, &default_desktop_capabilities())?;

    if manifest_expired(&manifest.manifest)? {
        return Err(AppError::Actionable {
            error: "Helix manifest has expired".to_string(),
            resolution: "Resolve a fresh Helix manifest from the authenticated backend facade."
                .to_string(),
        });
    }

    let prepared_runtime = prepare_runtime_plan(app, &manifest).await?;
    store_data.helix_last_prepared_runtime = Some(prepared_runtime.clone());
    store_data.helix_last_fallback_reason = None;
    store::save_store(app, &store_data)?;

    Ok(prepared_runtime)
}

pub fn fallback_core_from_store(app: &AppHandle) -> Result<String, AppError> {
    let store_data = store::load_store(app)?;
    let fallback_core = store_data
        .helix_last_manifest
        .as_ref()
        .map(|manifest| {
            fallback_core_for_manifest(&manifest.manifest)
                .as_str()
                .to_string()
        })
        .unwrap_or_else(|| "sing-box".to_string());
    Ok(fallback_core)
}

pub fn record_runtime_fallback(
    app: &AppHandle,
    fallback_core: &str,
    reason: &str,
) -> Result<(), AppError> {
    let mut store_data = store::load_store(app)?;
    store_data.active_core = fallback_core.to_string();
    store_data.helix_last_fallback_reason = Some(reason.to_string());
    store::save_store(app, &store_data)
}

pub async fn report_runtime_event(
    app: &AppHandle,
    report: HelixRuntimeEventReport,
) -> Result<(), AppError> {
    let store_data = store::load_store(app)?;
    let backend_url = store_data.helix_backend_url.ok_or_else(|| {
        AppError::System("Helix backend URL is not available for telemetry".to_string())
    })?;
    let resolved_manifest = store_data.helix_last_manifest.ok_or_else(|| {
        AppError::System("Helix manifest is not available for telemetry".to_string())
    })?;
    let access_token = load_backend_access_token()?;

    let request = HelixRuntimeEventRequest {
        schema_version: "1.0".to_string(),
        desktop_client_id: get_or_create_desktop_client_id(app)?,
        manifest_version_id: resolved_manifest.manifest_version_id,
        rollout_id: resolved_manifest.manifest.rollout_id,
        transport_profile_id: resolved_manifest
            .manifest
            .transport_profile
            .transport_profile_id,
        event_kind: report.event_kind,
        active_core: report.active_core,
        fallback_core: report.fallback_core,
        latency_ms: report.latency_ms,
        route_count: report.route_count.map(saturating_i32_from_usize),
        reason: report.reason,
        payload: report.payload,
    };

    send_runtime_event(&backend_url, &access_token, &request).await
}

fn saturating_i32_from_usize(value: usize) -> i32 {
    i32::try_from(value).unwrap_or(i32::MAX)
}
