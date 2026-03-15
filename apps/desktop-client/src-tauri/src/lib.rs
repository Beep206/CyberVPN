pub mod engine;
pub mod ipc;

// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

use ipc::AppState;
use ipc::models::ConnectionStatus;
use tokio::sync::RwLock;
use std::sync::Arc;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                if let Err(e) = engine::provision::ensure_sing_box_binary(&app_handle).await {
                    eprintln!("Failed to provision sing-box: {}", e);
                }
            });
            Ok(())
        })
        .manage(AppState {
            status: RwLock::new(ConnectionStatus {
                status: "disconnected".to_string(),
                active_id: None,
                message: None,
                up_bytes: 0,
                down_bytes: 0,
            }),
            process_manager: Arc::new(engine::manager::ProcessManager::new()),
        })
        .invoke_handler(tauri::generate_handler![
            greet,
            ipc::get_profiles,
            ipc::add_profile,
            ipc::connect_profile,
            ipc::disconnect,
            ipc::get_connection_status
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
