use std::sync::{
    atomic::{AtomicBool, Ordering},
    RwLock,
};

use serde::Serialize;
use tauri::{AppHandle, Emitter, Manager};

use crate::{engine::diagnostics::DiagnosticLevel, ipc::AppState};

#[derive(Debug, Clone, Serialize)]
pub struct DesktopShellSnapshot {
    pub state: String,
    pub window_visible: bool,
    pub is_quitting: bool,
    pub last_source: Option<String>,
    pub last_action: Option<String>,
    pub updated_at: Option<String>,
}

impl Default for DesktopShellSnapshot {
    fn default() -> Self {
        Self {
            state: "visible".to_string(),
            window_visible: true,
            is_quitting: false,
            last_source: None,
            last_action: None,
            updated_at: None,
        }
    }
}

pub struct DesktopShellState {
    snapshot: RwLock<DesktopShellSnapshot>,
    shutdown_in_progress: AtomicBool,
    exit_ready: AtomicBool,
}

impl DesktopShellState {
    pub fn new(initial_hidden: bool) -> Self {
        let mut snapshot = DesktopShellSnapshot::default();
        snapshot.window_visible = !initial_hidden;
        snapshot.state = if initial_hidden {
            "hidden-to-tray".to_string()
        } else {
            "visible".to_string()
        };

        Self {
            snapshot: RwLock::new(snapshot),
            shutdown_in_progress: AtomicBool::new(false),
            exit_ready: AtomicBool::new(false),
        }
    }

    pub fn snapshot(&self) -> DesktopShellSnapshot {
        self.snapshot
            .read()
            .map(|guard| guard.clone())
            .unwrap_or_default()
    }

    pub fn is_shutdown_in_progress(&self) -> bool {
        self.shutdown_in_progress.load(Ordering::SeqCst)
    }

    pub fn is_exit_ready(&self) -> bool {
        self.exit_ready.load(Ordering::SeqCst)
    }

    pub fn begin_shutdown(&self) -> bool {
        !self.shutdown_in_progress.swap(true, Ordering::SeqCst)
    }

    pub fn mark_exit_ready(&self) {
        self.exit_ready.store(true, Ordering::SeqCst);
    }

    fn update_snapshot(
        &self,
        next_state: &str,
        window_visible: bool,
        source: &str,
        action: &str,
    ) -> DesktopShellSnapshot {
        let next_snapshot = DesktopShellSnapshot {
            state: next_state.to_string(),
            window_visible,
            is_quitting: next_state == "quitting" || next_state == "exited",
            last_source: Some(source.to_string()),
            last_action: Some(action.to_string()),
            updated_at: Some(chrono::Utc::now().to_rfc3339()),
        };

        if let Ok(mut guard) = self.snapshot.write() {
            *guard = next_snapshot.clone();
        }

        next_snapshot
    }
}

fn sanitize_source(source: &str, fallback: &str) -> String {
    let candidate = source.trim().to_lowercase();
    if candidate.is_empty() {
        return fallback.to_string();
    }

    let sanitized = candidate
        .chars()
        .filter(|character| {
            character.is_ascii_alphanumeric() || *character == '-' || *character == '_'
        })
        .take(32)
        .collect::<String>();

    if sanitized.is_empty() {
        fallback.to_string()
    } else {
        sanitized
    }
}

fn emit_shell_state(app: &AppHandle, snapshot: &DesktopShellSnapshot) {
    let _ = app.emit("desktop-shell-state", snapshot.clone());
}

fn record_shell_event(
    app: &AppHandle,
    level: DiagnosticLevel,
    message: &str,
    source: &str,
    snapshot: &DesktopShellSnapshot,
) {
    let _ = crate::engine::diagnostics::record_event(
        app,
        level,
        "app.shell",
        message,
        serde_json::json!({
            "source_surface": source,
            "state": snapshot.state,
            "window_visible": snapshot.window_visible,
            "is_quitting": snapshot.is_quitting,
            "last_action": snapshot.last_action,
            "updated_at": snapshot.updated_at,
        }),
    );
}

pub fn current_snapshot(app: &AppHandle) -> DesktopShellSnapshot {
    app.try_state::<DesktopShellState>()
        .map(|state| state.snapshot())
        .unwrap_or_default()
}

fn transition_shell_state(
    app: &AppHandle,
    next_state: &str,
    window_visible: bool,
    source: &str,
    action: &str,
) -> DesktopShellSnapshot {
    let sanitized_source = sanitize_source(source, "desktop-shell");
    let snapshot = app
        .try_state::<DesktopShellState>()
        .map(|state| state.update_snapshot(next_state, window_visible, &sanitized_source, action))
        .unwrap_or_else(|| DesktopShellSnapshot {
            state: next_state.to_string(),
            window_visible,
            is_quitting: next_state == "quitting" || next_state == "exited",
            last_source: Some(sanitized_source.clone()),
            last_action: Some(action.to_string()),
            updated_at: Some(chrono::Utc::now().to_rfc3339()),
        });

    emit_shell_state(app, &snapshot);
    let _ = crate::tray::setup(app);
    snapshot
}

pub fn hide_main_window(app: &AppHandle, source: &str) {
    let Some(window) = app.get_webview_window("main") else {
        return;
    };

    let _ = window.hide();
    if app
        .try_state::<DesktopShellState>()
        .map(|state| state.is_shutdown_in_progress() && !state.is_exit_ready())
        .unwrap_or(false)
    {
        return;
    }

    let snapshot = transition_shell_state(app, "hidden-to-tray", false, source, "hide");
    record_shell_event(
        app,
        DiagnosticLevel::Info,
        "Desktop window hidden to tray",
        source,
        &snapshot,
    );
}

pub fn show_main_window(app: &AppHandle, source: &str) {
    let Some(window) = app.get_webview_window("main") else {
        return;
    };

    if app
        .try_state::<DesktopShellState>()
        .map(|state| state.is_shutdown_in_progress() && !state.is_exit_ready())
        .unwrap_or(false)
    {
        return;
    }

    let _ = window.unminimize();
    let _ = window.show();
    let _ = window.set_focus();

    let snapshot = transition_shell_state(app, "visible", true, source, "show");
    record_shell_event(
        app,
        DiagnosticLevel::Info,
        "Desktop window shown from tray shell",
        source,
        &snapshot,
    );
}

pub fn sync_main_window_visibility(app: &AppHandle, source: &str) {
    let window_visible = app
        .get_webview_window("main")
        .and_then(|window| window.is_visible().ok())
        .unwrap_or(true);

    let next_state = if app
        .try_state::<DesktopShellState>()
        .map(|state| state.is_shutdown_in_progress() && !state.is_exit_ready())
        .unwrap_or(false)
    {
        "quitting"
    } else if window_visible {
        "visible"
    } else {
        "hidden-to-tray"
    };

    let _ = transition_shell_state(app, next_state, window_visible, source, "sync");
}

pub fn request_app_shutdown(app: AppHandle, source: &str) -> bool {
    let sanitized_source = sanitize_source(source, "desktop-shutdown");
    let Some(shell_state) = app.try_state::<DesktopShellState>() else {
        app.exit(0);
        return true;
    };

    if !shell_state.begin_shutdown() {
        let snapshot = shell_state.snapshot();
        record_shell_event(
            &app,
            DiagnosticLevel::Info,
            "Desktop shutdown request ignored because shutdown is already in progress",
            &sanitized_source,
            &snapshot,
        );
        return false;
    }

    let snapshot = transition_shell_state(&app, "quitting", false, &sanitized_source, "quit");
    record_shell_event(
        &app,
        DiagnosticLevel::Info,
        "Desktop shutdown requested",
        &sanitized_source,
        &snapshot,
    );

    tauri::async_runtime::spawn({
        let app = app.clone();
        let sanitized_source = sanitized_source.clone();
        async move {
            let process_manager = {
                let state = app.state::<AppState>();
                state.process_manager.clone()
            };

            if let Err(error) = process_manager.stop().await {
                let _ = crate::engine::diagnostics::record_event(
                    &app,
                    DiagnosticLevel::Warn,
                    "app.shutdown",
                    "Failed to stop VPN runtime during desktop shutdown",
                    serde_json::json!({
                        "source_surface": sanitized_source,
                        "error": error.to_string(),
                    }),
                );
            } else {
                let _ = crate::engine::diagnostics::record_event(
                    &app,
                    DiagnosticLevel::Info,
                    "app.shutdown",
                    "VPN runtime stopped during desktop shutdown",
                    serde_json::json!({
                        "source_surface": sanitized_source,
                    }),
                );
            }

            let _ = crate::engine::sysproxy::clear_system_proxy();
            let guard = app.state::<crate::engine::sys::sentinel::SentinelGuard>();
            let _ = guard.disable();

            if let Some(shell_state) = app.try_state::<DesktopShellState>() {
                shell_state.mark_exit_ready();
            }

            let _ = crate::engine::diagnostics::record_event(
                &app,
                DiagnosticLevel::Info,
                "app.shutdown",
                "Desktop shutdown cleanup completed",
                serde_json::json!({
                    "source_surface": sanitized_source,
                }),
            );

            std::thread::spawn(|| {
                std::thread::sleep(std::time::Duration::from_secs(2));
                std::process::exit(0);
            });
            app.exit(0);
        }
    });

    true
}

pub fn mark_exit_completed(app: &AppHandle, source: &str) {
    let snapshot = transition_shell_state(app, "exited", false, source, "exit-completed");
    record_shell_event(
        app,
        DiagnosticLevel::Info,
        "Desktop client exited cleanly",
        source,
        &snapshot,
    );
}
