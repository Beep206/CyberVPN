use crate::engine::error::AppError;
use crate::engine::helix::config::{
    HelixPreparedRuntime, HelixRecoveryBenchmarkReport, HelixResolvedManifest,
    TransportBenchmarkComparisonReport, TransportBenchmarkMatrixReport, TransportBenchmarkReport,
};
use crate::engine::lifecycle::StartupRecoveryInfo;
use crate::engine::sys::net_monitor::NetworkProfile;
use crate::ipc::models::ProxyNode;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use tauri::AppHandle;
use tauri::Manager;

#[derive(Serialize, Deserialize)]
pub struct AppDataStore {
    pub profiles: Vec<ProxyNode>,
    pub active_profile_id: Option<String>,
    #[serde(default)]
    pub last_connection_options: crate::ipc::models::LastConnectionOptions,
    pub routing_rules: Vec<crate::ipc::models::RoutingRule>,
    pub subscriptions: Vec<crate::ipc::models::Subscription>,
    pub custom_config: Option<String>,
    #[serde(default = "default_active_core")]
    pub active_core: String,
    pub local_socks_port: Option<u16>,
    #[serde(default)]
    pub allow_lan: bool,
    #[serde(default)]
    pub groups: Vec<crate::ipc::models::ProfileGroup>,
    #[serde(default)]
    pub split_tunneling_apps: Vec<String>,
    #[serde(default = "default_split_tunneling_mode")]
    pub split_tunneling_mode: String,
    #[serde(default)]
    pub stealth_mode_enabled: bool,
    #[serde(default)]
    pub pqc_enforcement_mode: bool,
    #[serde(default = "default_privacy_shield_level")]
    pub privacy_shield_level: String,

    // Phase 28 features
    #[serde(default)]
    pub smart_connect_enabled: bool,
    #[serde(default)]
    pub network_rules: HashMap<String, NetworkProfile>,
    #[serde(default)]
    pub helix_backend_url: Option<String>,
    #[serde(default)]
    pub helix_desktop_client_id: Option<String>,
    #[serde(default)]
    pub helix_last_manifest: Option<HelixResolvedManifest>,
    #[serde(default)]
    pub helix_last_prepared_runtime: Option<HelixPreparedRuntime>,
    #[serde(default)]
    pub helix_last_fallback_reason: Option<String>,
    #[serde(default)]
    pub helix_last_benchmark_report: Option<TransportBenchmarkReport>,
    #[serde(default)]
    pub helix_last_comparison_report: Option<TransportBenchmarkComparisonReport>,
    #[serde(default)]
    pub helix_last_matrix_report: Option<TransportBenchmarkMatrixReport>,
    #[serde(default)]
    pub helix_last_recovery_report: Option<HelixRecoveryBenchmarkReport>,
    #[serde(default)]
    pub last_startup_recovery: Option<StartupRecoveryInfo>,
}

fn default_privacy_shield_level() -> String {
    "standard".to_string()
}

fn default_split_tunneling_mode() -> String {
    "allow".to_string()
}

fn default_active_core() -> String {
    "sing-box".to_string()
}

impl Default for AppDataStore {
    fn default() -> Self {
        Self {
            profiles: Vec::new(),
            active_profile_id: None,
            last_connection_options: crate::ipc::models::LastConnectionOptions::default(),
            routing_rules: Vec::new(),
            subscriptions: Vec::new(),
            custom_config: None,
            active_core: default_active_core(),
            local_socks_port: None,
            allow_lan: false,
            groups: Vec::new(),
            split_tunneling_apps: Vec::new(),
            split_tunneling_mode: default_split_tunneling_mode(),
            stealth_mode_enabled: false,
            pqc_enforcement_mode: false,
            privacy_shield_level: default_privacy_shield_level(),
            smart_connect_enabled: false,
            network_rules: HashMap::new(),
            helix_backend_url: None,
            helix_desktop_client_id: None,
            helix_last_manifest: None,
            helix_last_prepared_runtime: None,
            helix_last_fallback_reason: None,
            helix_last_benchmark_report: None,
            helix_last_comparison_report: None,
            helix_last_matrix_report: None,
            helix_last_recovery_report: None,
            last_startup_recovery: None,
        }
    }
}

pub fn get_app_dir(app_handle: &AppHandle) -> Result<PathBuf, AppError> {
    if let Ok(override_dir) = std::env::var("CYBERVPN_APP_DIR_OVERRIDE") {
        let app_dir = PathBuf::from(override_dir);
        if !app_dir.exists() {
            fs::create_dir_all(&app_dir)?;
        }
        return Ok(app_dir);
    }

    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(parent) = exe_path.parent() {
            let portable_flag = parent.join(".portable");
            if portable_flag.exists() {
                return Ok(parent.to_path_buf());
            }
        }
    }

    let app_dir = app_handle
        .path()
        .app_data_dir()
        .map_err(|e| AppError::System(format!("Failed to get app_data_dir: {}", e)))?;

    if !app_dir.exists() {
        fs::create_dir_all(&app_dir)?;
    }

    Ok(app_dir)
}

pub fn get_store_path(app_handle: &AppHandle) -> Result<PathBuf, AppError> {
    let app_dir = get_app_dir(app_handle)?;
    Ok(app_dir.join("store.json"))
}

pub fn load_store(app_handle: &AppHandle) -> Result<AppDataStore, AppError> {
    let store_path = get_store_path(app_handle)?;
    if !store_path.exists() {
        return Ok(AppDataStore::default());
    }

    let contents = fs::read_to_string(&store_path)?;
    let store = serde_json::from_str(&contents)?;
    Ok(store)
}

pub fn save_store(app_handle: &AppHandle, store: &AppDataStore) -> Result<(), AppError> {
    let store_path = get_store_path(app_handle)?;
    let contents = serde_json::to_string_pretty(store)?;
    fs::write(store_path, contents)?;
    Ok(())
}

#[derive(Debug, Default)]
pub struct ConnectionMetadataReconciliation {
    pub cleared_stale_active_profile: bool,
    pub cleared_missing_last_profile: bool,
    pub synced_last_active_core: bool,
}

pub fn reconcile_connection_metadata(
    app_handle: &AppHandle,
) -> Result<ConnectionMetadataReconciliation, AppError> {
    let mut store = load_store(app_handle)?;
    let mut report = ConnectionMetadataReconciliation::default();
    let mut changed = false;

    if store.active_profile_id.is_some() {
        store.active_profile_id = None;
        report.cleared_stale_active_profile = true;
        changed = true;
    }

    if store
        .last_connection_options
        .profile_id
        .as_ref()
        .is_some_and(|profile_id| {
            !store
                .profiles
                .iter()
                .any(|profile| &profile.id == profile_id)
        })
    {
        store.last_connection_options.profile_id = None;
        report.cleared_missing_last_profile = true;
        changed = true;
    }

    if store.last_connection_options.active_core.trim().is_empty()
        || store.last_connection_options.active_core != store.active_core
    {
        store.last_connection_options.active_core = store.active_core.clone();
        report.synced_last_active_core = true;
        changed = true;
    }

    if changed {
        save_store(app_handle, &store)?;
    }

    Ok(report)
}
