use crate::ipc::AppState;
use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Manager,
};

pub fn setup(app: &tauri::AppHandle) -> tauri::Result<()> {
    let quit_i = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
    let show_i = MenuItem::with_id(app, "show", "Show App", true, None::<&str>)?;
    let connect_i = MenuItem::with_id(app, "connect", "Disconnect / Connect", true, None::<&str>)?;

    let menu = Menu::with_items(app, &[&show_i, &connect_i, &quit_i])?;

    let icon = app.default_window_icon().cloned().unwrap_or_else(|| {
        // Fallback or empty if not found, but standard setup should have it
        unreachable!("Default icon is expected to be configured")
    });

    let _tray = TrayIconBuilder::new()
        .menu(&menu)
        .icon(icon)
        .tooltip("CyberVPN")
        .on_menu_event(|app, event| match event.id.as_ref() {
            "quit" => {
                let state = app.state::<AppState>();
                // Safely block and stop the sing-box process
                tokio::runtime::Handle::current().block_on(async {
                    if let Err(e) = state.process_manager.stop().await {
                        eprintln!("Failed to stop process manager on quit: {}", e);
                    }
                });
                app.exit(0);
            }
            "show" => {
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
            "connect" => {
                // To do: toggle connection using current active_id.
                // We will implement this safely using Rust async patterns.
                let app_handle = app.clone();

                tokio::spawn(async move {
                    let state = app_handle.state::<AppState>();
                    // Extract connection info without holding lock across awaits
                    let (status_str, active_id) = {
                        let status_lock = state.status.read().await;
                        (status_lock.status.clone(), status_lock.active_id.clone())
                    };

                    if status_str == "connected" || status_str == "connecting" {
                        println!("Tray: Disconnecting...");
                        if let Err(e) = crate::ipc::disconnect(app_handle.clone(), state).await {
                            eprintln!("Tray disconnect error: {}", e);
                        }
                    } else if let Some(id) = active_id {
                        println!("Tray: Connecting...");
                        // We strictly need tun_mode boolean here. For simplicity, we can fetch the latest tun_mode from somewhere or default to false, since the Tray doesn't know it.
                        // But wait! connect_profile needs `tun_mode`.
                        // For the tray toggle, we could just read the last used tun_mode or default to false.
                        // Let's modify the standard command to accept the previous state.
                        // For now we'll pass false, or look it up if persisted.
                        let _ =
                            crate::ipc::connect_profile(id, false, false, app_handle.clone(), state).await;
                    } else {
                        // Attempt to connect the first profile if no active_id
                        if let Ok(profiles) = crate::engine::store::load_store(&app_handle) {
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
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                let app = tray.app_handle();
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
        })
        .build(app)?;

    Ok(())
}
