use crate::{
    engine::{diagnostics::DiagnosticLevel, shell},
    ipc::AppState,
};
use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Manager,
};

const FALLBACK_TRAY_ICON: tauri::image::Image<'_> = tauri::include_image!("./icons/32x32.png");

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum WindowMenuAction {
    Show,
    Hide,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum ConnectionMenuAction {
    Connect,
    Disconnect,
    None,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct TrayMenuPresentation {
    window_action: WindowMenuAction,
    window_enabled: bool,
    connection_action: ConnectionMenuAction,
    connection_enabled: bool,
    quit_enabled: bool,
}

fn derive_menu_presentation(
    connection_status: &str,
    window_visible: bool,
    shutdown_in_progress: bool,
) -> TrayMenuPresentation {
    if shutdown_in_progress {
        return TrayMenuPresentation {
            window_action: if window_visible {
                WindowMenuAction::Hide
            } else {
                WindowMenuAction::Show
            },
            window_enabled: false,
            connection_action: ConnectionMenuAction::None,
            connection_enabled: false,
            quit_enabled: false,
        };
    }

    let connection_action = match connection_status {
        "connected" | "degraded" => ConnectionMenuAction::Disconnect,
        "connecting" | "disconnecting" => ConnectionMenuAction::None,
        _ => ConnectionMenuAction::Connect,
    };

    TrayMenuPresentation {
        window_action: if window_visible {
            WindowMenuAction::Hide
        } else {
            WindowMenuAction::Show
        },
        window_enabled: true,
        connection_enabled: !matches!(connection_action, ConnectionMenuAction::None),
        connection_action,
        quit_enabled: true,
    }
}

fn localized_window_label(action: WindowMenuAction) -> String {
    match action {
        WindowMenuAction::Show => rust_i18n::t!("tray.show").to_string(),
        WindowMenuAction::Hide => rust_i18n::t!("tray.hide").to_string(),
    }
}

fn localized_connection_label(
    action: ConnectionMenuAction,
    connection_status: &str,
    shutdown_in_progress: bool,
) -> String {
    if shutdown_in_progress {
        return rust_i18n::t!("tray.quitting").to_string();
    }

    match action {
        ConnectionMenuAction::Connect => rust_i18n::t!("tray.connect").to_string(),
        ConnectionMenuAction::Disconnect => rust_i18n::t!("tray.disconnect").to_string(),
        ConnectionMenuAction::None => match connection_status {
            "connecting" => rust_i18n::t!("tray.connecting").to_string(),
            "disconnecting" => rust_i18n::t!("tray.disconnecting").to_string(),
            _ => rust_i18n::t!("tray.connect").to_string(),
        },
    }
}

fn localized_quit_label(shutdown_in_progress: bool) -> String {
    if shutdown_in_progress {
        rust_i18n::t!("tray.quitting").to_string()
    } else {
        rust_i18n::t!("tray.quit").to_string()
    }
}

fn current_connection_status(app: &AppHandle) -> String {
    app.try_state::<AppState>()
        .and_then(|state| {
            state
                .status
                .try_read()
                .ok()
                .map(|guard| guard.status.clone())
        })
        .unwrap_or_else(|| "disconnected".to_string())
}

fn current_window_visible(app: &AppHandle) -> bool {
    app.get_webview_window("main")
        .and_then(|window| window.is_visible().ok())
        .unwrap_or(true)
}

fn current_shutdown_in_progress(app: &AppHandle) -> bool {
    app.try_state::<crate::engine::shell::DesktopShellState>()
        .map(|state| state.is_shutdown_in_progress() && !state.is_exit_ready())
        .unwrap_or(false)
}

fn resolve_tray_icon(app: &AppHandle) -> Option<tauri::image::Image<'static>> {
    if let Some(icon) = app.default_window_icon().cloned() {
        return Some(icon.to_owned());
    }

    let fallback = Some(FALLBACK_TRAY_ICON.to_owned());
    if fallback.is_some() {
        let _ = crate::engine::diagnostics::record_event(
            app,
            DiagnosticLevel::Warn,
            "tray.icon",
            "Tray icon used bundled fallback image",
            serde_json::json!({}),
        );
    } else {
        let _ = crate::engine::diagnostics::record_event(
            app,
            DiagnosticLevel::Error,
            "tray.icon",
            "Tray icon is unavailable and fallback image could not be loaded",
            serde_json::json!({}),
        );
    }
    fallback
}

pub fn setup(app: &AppHandle) -> tauri::Result<()> {
    let connection_status = current_connection_status(app);
    let window_visible = current_window_visible(app);
    let shutdown_in_progress = current_shutdown_in_progress(app);
    let presentation =
        derive_menu_presentation(&connection_status, window_visible, shutdown_in_progress);
    let quit_text = localized_quit_label(shutdown_in_progress);
    let show_text = localized_window_label(presentation.window_action);
    let connect_text = localized_connection_label(
        presentation.connection_action,
        &connection_status,
        shutdown_in_progress,
    );

    let quit_i = MenuItem::with_id(
        app,
        "quit",
        &quit_text,
        presentation.quit_enabled,
        None::<&str>,
    )?;
    let show_i = MenuItem::with_id(
        app,
        "show",
        &show_text,
        presentation.window_enabled,
        None::<&str>,
    )?;
    let connect_i = MenuItem::with_id(
        app,
        "connect",
        &connect_text,
        presentation.connection_enabled,
        None::<&str>,
    )?;

    let menu = Menu::with_items(app, &[&show_i, &connect_i, &quit_i])?;

    if let Some(tray) = app.tray_by_id("main") {
        let _ = tray.set_menu(Some(menu));
        return Ok(());
    }

    let Some(icon) = resolve_tray_icon(app) else {
        return Ok(());
    };

    let _tray = TrayIconBuilder::with_id("main")
        .menu(&menu)
        .show_menu_on_left_click(false)
        .icon(icon)
        .tooltip("CyberVPN")
        .on_menu_event(|app, event| match event.id.as_ref() {
            "quit" => {
                let _ = crate::engine::diagnostics::record_event(
                    app,
                    DiagnosticLevel::Info,
                    "tray.menu",
                    "Tray quit selected",
                    serde_json::json!({}),
                );
                let _ = shell::request_app_shutdown(app.clone(), "tray-menu");
            }
            "show" => {
                let visible = current_window_visible(app);
                let _ = crate::engine::diagnostics::record_event(
                    app,
                    DiagnosticLevel::Info,
                    "tray.menu",
                    "Tray window toggle selected",
                    serde_json::json!({
                        "window_visible": visible,
                    }),
                );
                if visible {
                    shell::hide_main_window(app, "tray-menu");
                } else {
                    shell::show_main_window(app, "tray-menu");
                }
            }
            "connect" => {
                let app_handle = app.clone();

                tauri::async_runtime::spawn(async move {
                    if current_shutdown_in_progress(&app_handle) {
                        return;
                    }

                    let state = app_handle.state::<AppState>();
                    let status_str = {
                        let status_lock = state.status.read().await;
                        status_lock.status.clone()
                    };

                    if status_str == "disconnecting" || status_str == "connecting" {
                        return;
                    }

                    if status_str == "connected" || status_str == "degraded" {
                        let _ =
                            crate::ipc::disconnect_internal("tray-menu", app_handle.clone(), state)
                                .await;
                    } else {
                        let reconnect_state = app_handle.state::<AppState>();
                        let _ = crate::ipc::connect_with_last_options(
                            "tray-menu",
                            app_handle.clone(),
                            reconnect_state,
                        )
                        .await;
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
                let visible = current_window_visible(&app);
                let _ = crate::engine::diagnostics::record_event(
                    &app,
                    DiagnosticLevel::Info,
                    "tray.icon",
                    "Tray icon left-click received",
                    serde_json::json!({
                        "window_visible": visible,
                    }),
                );
                if visible {
                    if let Some(window) = app.get_webview_window("main") {
                        let _ = window.set_focus();
                    }
                } else {
                    shell::show_main_window(&app, "tray-left-click");
                }
            }
        })
        .build(app)?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{
        derive_menu_presentation, ConnectionMenuAction, TrayMenuPresentation, WindowMenuAction,
    };

    fn assert_presentation(
        actual: TrayMenuPresentation,
        window_action: WindowMenuAction,
        connection_action: ConnectionMenuAction,
        window_enabled: bool,
        connection_enabled: bool,
        quit_enabled: bool,
    ) {
        assert_eq!(actual.window_action, window_action);
        assert_eq!(actual.connection_action, connection_action);
        assert_eq!(actual.window_enabled, window_enabled);
        assert_eq!(actual.connection_enabled, connection_enabled);
        assert_eq!(actual.quit_enabled, quit_enabled);
    }

    #[test]
    fn connected_visible_menu_prefers_hide_and_disconnect() {
        let actual = derive_menu_presentation("connected", true, false);
        assert_presentation(
            actual,
            WindowMenuAction::Hide,
            ConnectionMenuAction::Disconnect,
            true,
            true,
            true,
        );
    }

    #[test]
    fn disconnected_hidden_menu_prefers_show_and_connect() {
        let actual = derive_menu_presentation("disconnected", false, false);
        assert_presentation(
            actual,
            WindowMenuAction::Show,
            ConnectionMenuAction::Connect,
            true,
            true,
            true,
        );
    }

    #[test]
    fn shutdown_in_progress_disables_everything() {
        let actual = derive_menu_presentation("connected", false, true);
        assert_presentation(
            actual,
            WindowMenuAction::Show,
            ConnectionMenuAction::None,
            false,
            false,
            false,
        );
    }
}
