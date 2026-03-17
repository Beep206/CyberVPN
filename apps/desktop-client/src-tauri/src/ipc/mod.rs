pub mod models;

use crate::engine::error::AppError;
use crate::engine::manager::ProcessManager;
use crate::engine::parser;
use crate::engine::store;
use models::{ConnectionStatus, ProfileGroup, ProxyNode};
use std::sync::Arc;
use tauri::{AppHandle, Emitter, State};
use tokio::sync::RwLock;

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
pub async fn update_routing_rule(
    rule: models::RoutingRule,
    app: AppHandle,
) -> Result<(), AppError> {
    rule.validate().map_err(AppError::System)?;
    let mut store_data = store::load_store(&app)?;
    if let Some(existing) = store_data
        .routing_rules
        .iter_mut()
        .find(|r| r.id == rule.id)
    {
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
pub async fn apply_routing_fix(
    domain: String,
    app: AppHandle,
    state: State<'_, AppState>,
) -> Result<(), AppError> {
    let mut store_data = store::load_store(&app)?;
    
    // Quick deduplication
    let already_exists = store_data.routing_rules.iter().any(|r| {
        r.domains.contains(&domain) || r.domain_keyword.contains(&domain)
    });

    if !already_exists {
        let rule = models::RoutingRule {
            id: uuid::Uuid::new_v4().to_string(),
            enabled: true,
            domains: vec![format!("domain:{}", domain)],
            ips: vec![],
            outbound: "proxy".to_string(),
            process_name: vec![],
            port_range: vec![],
            network: None,
            domain_keyword: vec![],
            domain_regex: vec![],
        };
        store_data.routing_rules.push(rule);
        store::save_store(&app, &store_data)?;
    }

    // Checking state gracefully
    let (status, active_id) = {
        let lock = state.status.read().await;
        (lock.status.clone(), lock.active_id.clone())
    };

    if status == "connecting" {
         // Do not interrupt an active connection attempt to prevent race conditions
         return Ok(());
    } else if status == "connected" {
        if let Some(profile_id) = active_id {
            // Signal the frontend to perform a graceful restart using the existing UI toggles
            // This safely preserves the user's tun_mode and system_proxy states without needing
            // to persist them permanently on the backend tracking thread.
            let _ = app.emit("request-reconnect", profile_id);
        }
    }

    Ok(())
}

#[tauri::command]
pub async fn test_all_latencies(app: AppHandle) -> Result<(), AppError> {
    use futures::stream::StreamExt;
    
    let mut store_data = store::load_store(&app)?;
    
    // We clone the profiles so we can borrow them across async tasks
    let profiles_clone = store_data.profiles.clone();
    
    let results = futures::stream::iter(profiles_clone.into_iter().enumerate().map(|(index, node)| {
        async move {
            let ping = crate::engine::ping::test_latency(&node).await.unwrap_or(0);
            (index, ping)
        }
    }))
    .buffer_unordered(15) // Max 15 concurrent tests
    .collect::<Vec<(usize, u32)>>()
    .await;

    for (index, ping) in results {
        if ping > 0 {
            store_data.profiles[index].ping = Some(ping);
        } else {
            // Either failed or timeout. Set to 0 or leave as is. We set to 0 to indicate error.
            store_data.profiles[index].ping = Some(0);
        }
    }

    store::save_store(&app, &store_data)?;
    app.emit("profiles-updated", ())?;
    
    Ok(())
}

#[tauri::command]
pub async fn parse_clipboard_link(link: String) -> Result<ProxyNode, AppError> {
    parser::parse_link(&link)
}

#[tauri::command]
pub async fn connect_profile(
    id: String,
    tun_mode: bool,
    system_proxy: bool,
    app: AppHandle,
    state: State<'_, AppState>,
) -> Result<(), AppError> {
    // 1. Fetch profile
    let store_data = store::load_store(&app)?;
    let profile = store_data
        .profiles
        .iter()
        .find(|p| p.id == id)
        .ok_or_else(|| AppError::System("Profile not found".to_string()))?;

    let app_dir = crate::engine::store::get_app_dir(&app)?;
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
            log_path_opt,
            store_data.local_socks_port,
            store_data.allow_lan,
            &store_data.split_tunneling_apps,
            &store_data.split_tunneling_mode,
        )
    };

    // 3. Save to run.json
    let config_path = app_dir.join("run.json");
    let active_core = store_data.active_core.clone();

    #[cfg(target_os = "windows")]
    let bin_name = if active_core == "xray" {
        "xray.exe"
    } else {
        "sing-box.exe"
    };
    #[cfg(not(target_os = "windows"))]
    let bin_name = if active_core == "xray" {
        "xray"
    } else {
        "sing-box"
    };

    let bin_path = app_dir.join("bin").join(bin_name);

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
    if let Err(e) = state
        .process_manager
        .start(app.clone(), bin_path, config_path, tun_mode, &active_core)
        .await
    {
        let mut status_lock = state.status.write().await;
        status_lock.status = "error".to_string();
        status_lock.message = Some(e.to_string());
        app.emit("connection-status", status_lock.clone())?;
        return Err(e);
    }

    if system_proxy && !tun_mode {
        let port = store_data.local_socks_port.unwrap_or(2080);
        if let Err(e) = crate::engine::sysproxy::set_system_proxy(port) {
            eprintln!("Failed to set system proxy: {}", e);
        }
    } else {
        crate::engine::sysproxy::clear_system_proxy().ok();
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
    crate::engine::sysproxy::clear_system_proxy().ok();

    let mut status_lock = state.status.write().await;
    status_lock.status = "disconnected".to_string();
    status_lock.active_id = None;
    status_lock.up_bytes = 0;
    status_lock.down_bytes = 0;

    app.emit("connection-status", status_lock.clone())?;

    Ok(())
}

#[tauri::command]
pub async fn get_connection_status(
    state: State<'_, AppState>,
) -> Result<ConnectionStatus, AppError> {
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
        let sub = store_data
            .subscriptions
            .iter()
            .find(|s| s.id == sub_id)
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
    store_data
        .profiles
        .retain(|p| p.subscription_id.as_deref() != Some(sub_id.as_str()));

    // Append new nodes
    store_data.profiles.extend(new_nodes);

    // Update timestamp
    if let Some(sub) = store_data.subscriptions.iter_mut().find(|s| s.id == sub_id) {
        sub.last_updated = Some(
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        );
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

#[tauri::command]
pub async fn get_local_socks_port(app: AppHandle) -> Result<Option<u16>, AppError> {
    let store_data = store::load_store(&app)?;
    Ok(store_data.local_socks_port)
}

#[tauri::command]
pub async fn save_local_socks_port(port: Option<u16>, app: AppHandle) -> Result<(), AppError> {
    let mut store_data = store::load_store(&app)?;
    store_data.local_socks_port = port;
    store::save_store(&app, &store_data)?;
    Ok(())
}

#[tauri::command]
pub async fn get_allow_lan(app: AppHandle) -> Result<bool, AppError> {
    let store_data = store::load_store(&app)?;
    Ok(store_data.allow_lan)
}

#[tauri::command]
pub async fn save_allow_lan(allow: bool, app: AppHandle) -> Result<(), AppError> {
    let mut store_data = store::load_store(&app)?;
    store_data.allow_lan = allow;
    store::save_store(&app, &store_data)?;
    Ok(())
}

#[tauri::command]
pub async fn get_groups(app: AppHandle) -> Result<Vec<ProfileGroup>, AppError> {
    let store_data = store::load_store(&app)?;
    Ok(store_data.groups)
}

#[tauri::command]
pub async fn add_group(group: ProfileGroup, app: AppHandle) -> Result<(), AppError> {
    let mut store_data = store::load_store(&app)?;
    store_data.groups.push(group);
    store::save_store(&app, &store_data)?;
    Ok(())
}

#[tauri::command]
pub async fn delete_group(id: String, app: AppHandle) -> Result<(), AppError> {
    let mut store_data = store::load_store(&app)?;
    store_data.groups.retain(|g| g.id != id);
    for p in store_data.profiles.iter_mut() {
        if let Some(ref gid) = p.group_id {
            if gid == &id {
                p.group_id = None;
            }
        }
    }
    store::save_store(&app, &store_data)?;
    Ok(())
}

#[tauri::command]
pub async fn set_node_group(node_id: String, group_id: Option<String>, app: AppHandle) -> Result<(), AppError> {
    let mut store_data = store::load_store(&app)?;
    if let Some(node) = store_data.profiles.iter_mut().find(|n| n.id == node_id) {
        node.group_id = group_id;
        store::save_store(&app, &store_data)?;
    }
    Ok(())
}

#[tauri::command]
pub async fn update_geo_assets(app: AppHandle) -> Result<(), AppError> {
    crate::engine::provision::update_geo_assets(&app).await
}

#[tauri::command]
pub async fn get_active_core(app: AppHandle) -> Result<String, AppError> {
    let store_data = tokio::task::spawn_blocking(move || store::load_store(&app))
        .await
        .map_err(|e| AppError::System(format!("Tokio spawn blocking failed: {}", e)))??;
    Ok(store_data.active_core)
}

#[tauri::command]
pub async fn save_active_core(core: String, app: AppHandle) -> Result<(), AppError> {
    if core != "sing-box" && core != "xray" {
        return Err(AppError::System(format!("Invalid proxy engine core selected: {}", core)));
    }
    
    tokio::task::spawn_blocking(move || {
        let mut store_data = store::load_store(&app)?;
        store_data.active_core = core;
        store::save_store(&app, &store_data)?;
        Ok::<(), AppError>(())
    })
    .await
    .map_err(|e| AppError::System(format!("Tokio spawn blocking failed: {}", e)))??;

    Ok(())
}

#[tauri::command]
pub async fn get_installed_apps() -> Result<Vec<models::AppInfo>, AppError> {
    crate::engine::sys::apps::get_installed_apps().await
}

#[tauri::command]
pub async fn get_split_tunneling_apps(app: tauri::AppHandle) -> Result<Vec<String>, AppError> {
    let store = tokio::task::spawn_blocking(move || crate::engine::store::load_store(&app))
        .await
        .map_err(|e| AppError::System(format!("Tokio error: {}", e)))??;
    Ok(store.split_tunneling_apps)
}

#[tauri::command]
pub async fn save_split_tunneling_apps(apps: Vec<String>, app: tauri::AppHandle) -> Result<(), AppError> {
    tokio::task::spawn_blocking(move || {
        let mut store = crate::engine::store::load_store(&app)?;
        store.split_tunneling_apps = apps;
        crate::engine::store::save_store(&app, &store)
    })
    .await
    .map_err(|e| AppError::System(format!("Tokio error: {}", e)))??;
    Ok(())
}

#[tauri::command]
pub async fn get_split_tunneling_mode(app: tauri::AppHandle) -> Result<String, AppError> {
    let store = tokio::task::spawn_blocking(move || crate::engine::store::load_store(&app))
        .await
        .map_err(|e| AppError::System(format!("Tokio error: {}", e)))??;
    Ok(store.split_tunneling_mode)
}

#[tauri::command]
pub async fn save_split_tunneling_mode(mode: String, app: tauri::AppHandle) -> Result<(), AppError> {
    if mode != "allow" && mode != "disallow" {
        return Err(AppError::System("Invalid mode".to_string()));
    }
    tokio::task::spawn_blocking(move || {
        let mut store = crate::engine::store::load_store(&app)?;
        store.split_tunneling_mode = mode;
        crate::engine::store::save_store(&app, &store)
    })
    .await
    .map_err(|e| AppError::System(format!("Tokio error: {}", e)))??;
    Ok(())
}
// Removed redundant wrappers, these are exposed natively by `crate::engine::sys::net` and `discovery`
