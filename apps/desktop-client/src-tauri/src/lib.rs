pub mod engine;
pub mod ipc;
pub mod tray;

// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

use ipc::models::ConnectionStatus;
use ipc::AppState;
use std::sync::Arc;
use tauri::Manager;
use tokio::sync::RwLock;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    std::panic::set_hook(Box::new(|info| {
        let _ = crate::engine::sysproxy::clear_system_proxy();
        eprintln!("Panic occurred: {:?}", info);
    }));

    tauri::Builder::default()
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            Some(vec!["--hidden"]),
        ))
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_deep_link::init())
        .plugin(
            tauri_plugin_global_shortcut::Builder::new()
                .with_handler(|app, _shortcut, event| {
                    if event.state == tauri_plugin_global_shortcut::ShortcutState::Pressed {
                        let app_handle = app.clone();

                        tokio::spawn(async move {
                            let state = app_handle.state::<AppState>();
                            let (status_str, active_id) = {
                                let status_lock = state.status.read().await;
                                (status_lock.status.clone(), status_lock.active_id.clone())
                            };

                            if status_str == "connected" || status_str == "connecting" {
                                let _ = crate::ipc::disconnect(app_handle.clone(), state).await;
                            } else if let Some(id) = active_id {
                                let _ = crate::ipc::connect_profile(
                                    id,
                                    false,
                                    false,
                                    app_handle.clone(),
                                    state,
                                )
                                .await;
                            } else {
                                if let Ok(profiles) = crate::engine::store::load_store(&app_handle)
                                {
                                    if let Some(profile) = profiles.profiles.first() {
                                        let _ = crate::ipc::connect_profile(
                                            profile.id.clone(),
                                            false,
                                            false,
                                            app_handle.clone(),
                                            state,
                                        )
                                        .await;
                                    }
                                }
                            }
                        });
                    }
                })
                .build(),
        )
        .setup(|app| {
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                if let Err(e) = engine::provision::ensure_sing_box_binary(&app_handle).await {
                    eprintln!("Failed to provision sing-box: {}", e);
                }
                if let Err(e) = engine::provision::ensure_xray_binary(&app_handle).await {
                    eprintln!("Failed to provision xray-core: {}", e);
                }
            });

            #[cfg(any(target_os = "linux", target_os = "macos", target_os = "windows"))]
            {
                use tauri_plugin_deep_link::DeepLinkExt;
                let app_handle_cloned = app.handle().clone();
                // We wrap it in a catch to avoid panicking if we fail to register the scheme
                let _ = app.deep_link().on_open_url(move |urls| {
                    for url in urls.urls() {
                        let h = app_handle_cloned.clone();
                        let url_str = url.as_str().to_string();
                        tauri::async_runtime::spawn(async move {
                            if url_str.starts_with("throne://") {
                                // Extract the VLESS or Hysteria part after the throne://
                                // For now, pass the whole url_str, parser handles if it's prefixed
                                let parse_target = if url_str.starts_with("throne://vless")
                                    || url_str.starts_with("throne://hysteria")
                                {
                                    url_str.replace("throne://", "")
                                } else {
                                    url_str
                                };

                                if let Ok(node) = crate::engine::parser::parse_link(&parse_target) {
                                    if let Ok(mut store) = crate::engine::store::load_store(&h) {
                                        store.profiles.push(node);
                                        let _ = crate::engine::store::save_store(&h, &store);
                                        use tauri::Emitter;
                                        let _ = h.emit("profile-imported", ());
                                    }
                                }
                            }
                        });
                    }
                });
            }

            use std::str::FromStr;
            use tauri_plugin_global_shortcut::GlobalShortcutExt;
            if let Ok(shortcut) =
                tauri_plugin_global_shortcut::Shortcut::from_str("CommandOrControl+Shift+C")
            {
                if let Err(e) = app.global_shortcut().register(shortcut) {
                    eprintln!("Failed to register global hotkey: {}", e);
                }
            }

            crate::tray::setup(app.handle())?;

            // Start Network Monitor Phase 28
            crate::engine::sys::net_monitor::start_network_monitor(
                app.handle().clone(),
                std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false))
            );

            // Start Telemetry Histogram Flusher Phase 30
            crate::engine::sys::stats::spawn_flush_interval(app.handle().clone());

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                let _ = window.hide();
                api.prevent_close();
            }
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
        .manage(crate::engine::sys::sentinel::SentinelGuard::new())
        .invoke_handler(tauri::generate_handler![
            greet,
            ipc::get_profiles,
            ipc::add_profile,
            ipc::connect_profile,
            ipc::disconnect,
            ipc::get_connection_status,
            ipc::get_routing_rules,
            ipc::add_routing_rule,
            ipc::update_routing_rule,
            ipc::delete_routing_rule,
            ipc::apply_routing_fix,
            ipc::get_subscriptions,
            ipc::add_subscription,
            ipc::update_subscription,
            ipc::scan_screen_for_qr,
            ipc::generate_link,
            ipc::get_custom_config,
            ipc::save_custom_config,
            ipc::test_all_latencies,
            ipc::get_local_socks_port,
            ipc::save_local_socks_port,
            ipc::get_allow_lan,
            ipc::save_allow_lan,
            ipc::get_groups,
            ipc::add_group,
            ipc::delete_group,
            ipc::set_node_group,
            ipc::update_geo_assets,
            ipc::get_active_core,
            ipc::save_active_core,
            ipc::get_installed_apps,
            ipc::get_split_tunneling_apps,
            ipc::save_split_tunneling_apps,
            ipc::get_split_tunneling_mode,
            ipc::save_split_tunneling_mode,
            ipc::get_stealth_mode,
            ipc::save_stealth_mode,
            ipc::get_pqc_enforcement_mode,
            ipc::save_pqc_enforcement_mode,
            crate::engine::sys::net::get_lan_connection_info,
            crate::engine::sys::net::enable_lan_forwarding,
            crate::engine::sys::net::disable_lan_forwarding,
            crate::engine::sys::discovery::start_device_discovery,
            crate::engine::sys::discovery::stop_device_discovery,
            crate::engine::sys::sentinel::enable_killswitch_cmd,
            crate::engine::sys::sentinel::disable_killswitch_cmd,
            crate::engine::sys::sentinel::repair_network,
            crate::engine::sys::sync::cloud_push,
            crate::engine::sys::sync::cloud_pull,
            crate::engine::sys::sync::save_sync_password,
            crate::engine::sys::sync::get_sync_password,
            crate::engine::sys::sync::delete_sync_password,
            crate::engine::sys::sync::generate_pairing_qr,
            ipc::audit_quantum_readiness,
            ipc::get_smart_connect_status,
            ipc::set_smart_connect_status,
            ipc::get_network_rules,
            ipc::update_network_rule,
            ipc::run_stealth_diagnostics,
            ipc::apply_stealth_fix,
            crate::engine::sys::stats::get_usage_history, // Mapped natively on stats
            crate::engine::sys::stats::get_global_footprint,
            ipc::start_remote_server,
            ipc::stop_remote_server
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            if let tauri::RunEvent::Exit = event {
                let _ = crate::engine::sysproxy::clear_system_proxy();
                let guard = app_handle.state::<crate::engine::sys::sentinel::SentinelGuard>();
                let _ = guard.disable();
            }
        });
}
