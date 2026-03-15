pub mod models;

use models::{ConnectionStatus, ProxyNode};
use tauri::{AppHandle, State, Emitter};
use crate::engine::manager::ProcessManager;
use tokio::sync::RwLock;
use std::sync::Arc;
use tauri::Manager;
use crate::engine::store;
use crate::engine::error::AppError;
use crate::engine::parser;

pub struct AppState {
    pub status: RwLock<ConnectionStatus>,
    pub process_manager: Arc<ProcessManager>,
}

#[tauri::command]
pub async fn get_profiles(app: AppHandle) -> Result<Vec<ProxyNode>, AppError> {
    let store_data = store::load_store(&app)?;
    Ok(store_data.profiles)
}

#[tauri::command]
pub async fn add_profile(profile: ProxyNode, app: AppHandle) -> Result<(), AppError> {
    let mut store_data = store::load_store(&app)?;
    store_data.profiles.push(profile);
    store::save_store(&app, &store_data)?;
    Ok(())
}

#[tauri::command]
pub async fn parse_clipboard_link(link: String) -> Result<ProxyNode, AppError> {
    parser::parse_link(&link)
}

#[tauri::command]
pub async fn connect_profile(id: String, app: AppHandle, state: State<'_, AppState>) -> Result<(), AppError> {
    // 1. Fetch profile
    let store_data = store::load_store(&app)?;
    let profile = store_data.profiles.iter()
        .find(|p| p.id == id)
        .ok_or_else(|| AppError::System("Profile not found".to_string()))?;

    // 2. Generate config
    let config_json = crate::engine::config::generate_singbox_config(profile, true);
    
    // 3. Save to run.json
    let app_dir = app.path().app_data_dir().map_err(AppError::Tauri)?;
    let config_path = app_dir.join("run.json");
    let bin_path = app_dir.join("sing-box");

    tokio::fs::write(&config_path, serde_json::to_string_pretty(&config_json)?).await?;

    // 4. Update status to connecting
    {
        let mut status_lock = state.status.write().await;
        status_lock.status = "connecting".to_string();
        status_lock.active_id = Some(id.clone());
        app.emit("connection-status", status_lock.clone())?;
    }

    // 5. Start process
    if let Err(e) = state.process_manager.start(app.clone(), bin_path, config_path).await {
        let mut status_lock = state.status.write().await;
        status_lock.status = "error".to_string();
        status_lock.message = Some(e.to_string());
        app.emit("connection-status", status_lock.clone())?;
        return Err(e);
    }

    // 6. Update status to connected
    {
        let mut status_lock = state.status.write().await;
        status_lock.status = "connected".to_string();
        status_lock.message = None;
        app.emit("connection-status", status_lock.clone())?;
    }

    Ok(())
}

#[tauri::command]
pub async fn disconnect(app: AppHandle, state: State<'_, AppState>) -> Result<(), AppError> {
    state.process_manager.stop().await?;

    let mut status_lock = state.status.write().await;
    status_lock.status = "disconnected".to_string();
    status_lock.active_id = None;
    status_lock.up_bytes = 0;
    status_lock.down_bytes = 0;
    
    app.emit("connection-status", status_lock.clone())?;

    Ok(())
}

#[tauri::command]
pub async fn get_connection_status(state: State<'_, AppState>) -> Result<ConnectionStatus, AppError> {
    let status_lock = state.status.read().await;
    Ok(status_lock.clone())
}
