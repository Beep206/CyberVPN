use crate::engine::error::AppError;
use crate::ipc::models::ProxyNode;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use tauri::AppHandle;
use tauri::Manager;

#[derive(Serialize, Deserialize)]
pub struct AppDataStore {
    pub profiles: Vec<ProxyNode>,
    pub active_profile_id: Option<String>,
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
        }
    }
}

pub fn get_app_dir(app_handle: &AppHandle) -> Result<PathBuf, AppError> {
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
