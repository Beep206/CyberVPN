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
    profile.validate().map_err(AppError::System)?;
    let mut store_data = store::load_store(&app)?;
    store_data.profiles.push(profile);
    store::save_store(&app, &store_data)?;
    Ok(())
}

#[tauri::command]
pub async fn get_routing_rules(app: AppHandle) -> Result<Vec<models::RoutingRule>, AppError> {
    let store_data = store::load_store(&app)?;
    Ok(store_data.routing_rules)
}

#[tauri::command]
pub async fn add_routing_rule(rule: models::RoutingRule, app: AppHandle) -> Result<(), AppError> {
    rule.validate().map_err(AppError::System)?;
    let mut store_data = store::load_store(&app)?;
    store_data.routing_rules.push(rule);
    store::save_store(&app, &store_data)?;
    Ok(())
}

#[tauri::command]
pub async fn update_routing_rule(rule: models::RoutingRule, app: AppHandle) -> Result<(), AppError> {
    rule.validate().map_err(AppError::System)?;
    let mut store_data = store::load_store(&app)?;
    if let Some(existing) = store_data.routing_rules.iter_mut().find(|r| r.id == rule.id) {
        *existing = rule;
        store::save_store(&app, &store_data)?;
    }
    Ok(())
}

#[tauri::command]
pub async fn delete_routing_rule(id: String, app: AppHandle) -> Result<(), AppError> {
    let mut store_data = store::load_store(&app)?;
    store_data.routing_rules.retain(|r| r.id != id);
    store::save_store(&app, &store_data)?;
    Ok(())
}

#[tauri::command]
pub async fn parse_clipboard_link(link: String) -> Result<ProxyNode, AppError> {
    parser::parse_link(&link)
}

#[tauri::command]
pub async fn connect_profile(id: String, tun_mode: bool, app: AppHandle, state: State<'_, AppState>) -> Result<(), AppError> {
    // 1. Fetch profile
    let store_data = store::load_store(&app)?;
    let profile = store_data.profiles.iter()
        .find(|p| p.id == id)
        .ok_or_else(|| AppError::System("Profile not found".to_string()))?;

    let app_dir = app.path().app_data_dir().map_err(AppError::Tauri)?;
    #[allow(unused_variables)]
    let log_path = app_dir.join("run.log");

    #[allow(unused_mut, unused_assignments)]
    let mut log_path_opt = None;
    
    #[cfg(target_os = "windows")]
    {
        if tun_mode && !crate::engine::sys::is_elevated() {
            log_path_opt = Some(log_path.as_path());
        }
    }

    // 2. Generate config or apply Custom Config Override
    let config_json = if let Some(custom_json_str) = &store_data.custom_config {
        println!("Using Custom JSON Override for sing-box configuration.");
        serde_json::from_str::<serde_json::Value>(custom_json_str)
            .map_err(|e| AppError::System(format!("Custom JSON config parse error: {}", e)))?
    } else {
        crate::engine::config::generate_singbox_config(
            profile, 
            &store_data.profiles, 
            tun_mode, 
            &store_data.routing_rules,
            log_path_opt
        )
    };
    
    // 3. Save to run.json
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

    if tun_mode {
        crate::engine::sys::ensure_wintun(&app)?;
    }

    // 5. Start process
    if let Err(e) = state.process_manager.start(app.clone(), bin_path, config_path, tun_mode).await {
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

#[tauri::command]
pub async fn get_subscriptions(app: AppHandle) -> Result<Vec<models::Subscription>, AppError> {
    let store_data = store::load_store(&app)?;
    Ok(store_data.subscriptions)
}

#[tauri::command]
pub async fn add_subscription(sub: models::Subscription, app: AppHandle) -> Result<(), AppError> {
    let mut store_data = store::load_store(&app)?;
    store_data.subscriptions.push(sub);
    store::save_store(&app, &store_data)?;
    Ok(())
}

#[tauri::command]
pub async fn update_subscription(sub_id: String, app: AppHandle) -> Result<(), AppError> {
    let mut store_data = store::load_store(&app)?;
    
    // Find the subscription URL
    let url = {
        let sub = store_data.subscriptions.iter().find(|s| s.id == sub_id)
            .ok_or_else(|| AppError::System("Subscription not found".to_string()))?;
        sub.url.clone()
    };

    // Fetch new nodes
    let mut new_nodes = crate::engine::subscription::fetch_and_parse_subscription(&url).await?;
    
    // Assign sub_id
    for node in &mut new_nodes {
        node.subscription_id = Some(sub_id.clone());
    }

    // Sweep old nodes
    store_data.profiles.retain(|p| p.subscription_id.as_deref() != Some(sub_id.as_str()));
    
    // Append new nodes
    store_data.profiles.extend(new_nodes);
    
    // Update timestamp
    if let Some(sub) = store_data.subscriptions.iter_mut().find(|s| s.id == sub_id) {
        sub.last_updated = Some(std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs());
    }

    store::save_store(&app, &store_data)?;
    Ok(())
}

#[tauri::command]
pub async fn scan_screen_for_qr() -> Result<ProxyNode, AppError> {
    crate::engine::qr::scan_screen_for_qr().await
}

#[tauri::command]
pub async fn generate_link(node: ProxyNode) -> Result<String, AppError> {
    Ok(crate::engine::parser::generate_link(&node))
}

#[tauri::command]
pub async fn get_custom_config(app: AppHandle) -> Result<Option<String>, AppError> {
    let store_data = store::load_store(&app)?;
    Ok(store_data.custom_config)
}

#[tauri::command]
pub async fn save_custom_config(config: Option<String>, app: AppHandle) -> Result<(), AppError> {
    if let Some(ref json_str) = config {
        // Zero-cost validation
        serde_json::from_str::<serde::de::IgnoredAny>(json_str)
            .map_err(|e| AppError::System(format!("Invalid JSON configuration: {}", e)))?;
    }
    let mut store_data = store::load_store(&app)?;
    store_data.custom_config = config;
    store::save_store(&app, &store_data)?;
    Ok(())
}
