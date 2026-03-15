use crate::engine::error::AppError;
use crate::ipc::models::ProxyNode;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use tauri::AppHandle;
use tauri::Manager;

#[derive(Serialize, Deserialize, Default)]
pub struct AppDataStore {
    pub profiles: Vec<ProxyNode>,
    pub active_profile_id: Option<String>,
    pub routing_rules: Vec<crate::ipc::models::RoutingRule>,
    pub subscriptions: Vec<crate::ipc::models::Subscription>,
    pub custom_config: Option<String>,
}

pub fn get_store_path(app_handle: &AppHandle) -> Result<PathBuf, AppError> {
    let app_dir = app_handle
        .path()
        .app_data_dir()
        .map_err(|e| AppError::System(format!("Failed to get app_data_dir: {}", e)))?;

    if !app_dir.exists() {
        fs::create_dir_all(&app_dir)?;
    }

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
