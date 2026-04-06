use std::{
    fs,
    path::{Path, PathBuf},
};

use chrono::Utc;
use serde::{Deserialize, Serialize};
use tauri::AppHandle;

use crate::engine::{error::AppError, store};

const LIFECYCLE_STATE_FILE_NAME: &str = "lifecycle-state.json";

#[derive(Debug, Clone, Default)]
pub struct LaunchOptions {
    pub hidden: bool,
    pub smoke_exit_after_ms: Option<u64>,
    pub smoke_crash_after_ms: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct StartupRecoveryInfo {
    pub current_run_id: String,
    pub started_at: String,
    pub launch_mode: String,
    pub hidden_launch_requested: bool,
    pub previous_unclean_shutdown_detected: bool,
    pub previous_run_id: Option<String>,
    pub previous_started_at: Option<String>,
    pub previous_exit_kind: Option<String>,
    pub previous_exit_at: Option<String>,
    pub previous_exit_message: Option<String>,
    pub startup_cleanup_performed: bool,
    pub system_proxy_cleanup_succeeded: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct LifecycleState {
    schema_version: String,
    app_version: String,
    run_id: String,
    started_at: String,
    launch_mode: String,
    clean_shutdown: bool,
    exit_kind: Option<String>,
    exit_message: Option<String>,
    exit_at: Option<String>,
}

pub fn parse_launch_options_from_args<I, S>(args: I) -> LaunchOptions
where
    I: IntoIterator<Item = S>,
    S: Into<String>,
{
    let values = args.into_iter().map(Into::into).collect::<Vec<_>>();
    let mut options = LaunchOptions::default();
    let mut index = 0;

    while index < values.len() {
        let argument = &values[index];
        if argument == "--hidden" {
            options.hidden = true;
        } else if let Some(value) = argument.strip_prefix("--smoke-exit-after-ms=") {
            options.smoke_exit_after_ms = value.parse::<u64>().ok();
        } else if argument == "--smoke-exit-after-ms" {
            options.smoke_exit_after_ms = values
                .get(index + 1)
                .and_then(|value| value.parse::<u64>().ok());
            index += 1;
        } else if let Some(value) = argument.strip_prefix("--smoke-crash-after-ms=") {
            options.smoke_crash_after_ms = value.parse::<u64>().ok();
        } else if argument == "--smoke-crash-after-ms" {
            options.smoke_crash_after_ms = values
                .get(index + 1)
                .and_then(|value| value.parse::<u64>().ok());
            index += 1;
        }

        index += 1;
    }

    options
}

pub fn initialize(
    app: &AppHandle,
    launch_options: &LaunchOptions,
) -> Result<StartupRecoveryInfo, AppError> {
    let app_dir = store::get_app_dir(app)?;
    let recovery = initialize_in_dir(&app_dir, launch_options, env!("CARGO_PKG_VERSION"))?;

    let mut store_data = store::load_store(app)?;
    store_data.last_startup_recovery = Some(recovery.clone());
    store::save_store(app, &store_data)?;

    Ok(recovery)
}

pub fn mark_clean_exit(app: &AppHandle, message: impl Into<String>) -> Result<(), AppError> {
    let app_dir = store::get_app_dir(app)?;
    mark_exit_in_dir(&app_dir, "clean", Some(message.into()))
}

pub fn mark_panic(message: impl Into<String>) -> Result<(), AppError> {
    let app_dir = resolve_app_dir_without_handle().ok_or_else(|| {
        AppError::System("Unable to resolve app dir for panic marker".to_string())
    })?;
    mark_exit_in_dir(&app_dir, "panic", Some(message.into()))
}

fn resolve_app_dir_without_handle() -> Option<PathBuf> {
    if let Ok(override_dir) = std::env::var("CYBERVPN_APP_DIR_OVERRIDE") {
        return Some(PathBuf::from(override_dir));
    }

    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(parent) = exe_path.parent() {
            let portable_flag = parent.join(".portable");
            if portable_flag.exists() {
                return Some(parent.to_path_buf());
            }
        }
    }

    std::env::var("APPDATA")
        .ok()
        .map(|dir| PathBuf::from(dir).join("com.beep.desktop-client"))
}

fn lifecycle_state_path(app_dir: &Path) -> PathBuf {
    app_dir.join(LIFECYCLE_STATE_FILE_NAME)
}

fn load_lifecycle_state(app_dir: &Path) -> Result<Option<LifecycleState>, AppError> {
    let path = lifecycle_state_path(app_dir);
    if !path.exists() {
        return Ok(None);
    }

    let contents = fs::read_to_string(path)?;
    let state = serde_json::from_str::<LifecycleState>(&contents)?;
    Ok(Some(state))
}

fn save_lifecycle_state(app_dir: &Path, state: &LifecycleState) -> Result<(), AppError> {
    fs::create_dir_all(app_dir)?;
    let path = lifecycle_state_path(app_dir);
    let contents = serde_json::to_string_pretty(state)?;
    fs::write(path, contents)?;
    Ok(())
}

fn initialize_in_dir(
    app_dir: &Path,
    launch_options: &LaunchOptions,
    app_version: &str,
) -> Result<StartupRecoveryInfo, AppError> {
    let previous_state = load_lifecycle_state(app_dir)?;
    let previous_unclean_shutdown_detected = previous_state
        .as_ref()
        .is_some_and(|state| !state.clean_shutdown);

    let startup_cleanup_performed = previous_unclean_shutdown_detected;
    let system_proxy_cleanup_succeeded = if startup_cleanup_performed {
        crate::engine::sysproxy::clear_system_proxy().is_ok()
    } else {
        false
    };

    let recovery = StartupRecoveryInfo {
        current_run_id: format!("desktop-run-{}", uuid::Uuid::new_v4().simple()),
        started_at: Utc::now().to_rfc3339(),
        launch_mode: if launch_options.hidden {
            "hidden".to_string()
        } else {
            "visible".to_string()
        },
        hidden_launch_requested: launch_options.hidden,
        previous_unclean_shutdown_detected,
        previous_run_id: previous_state.as_ref().map(|state| state.run_id.clone()),
        previous_started_at: previous_state
            .as_ref()
            .map(|state| state.started_at.clone()),
        previous_exit_kind: previous_state
            .as_ref()
            .and_then(|state| state.exit_kind.clone()),
        previous_exit_at: previous_state
            .as_ref()
            .and_then(|state| state.exit_at.clone()),
        previous_exit_message: previous_state
            .as_ref()
            .and_then(|state| state.exit_message.clone()),
        startup_cleanup_performed,
        system_proxy_cleanup_succeeded,
    };

    let next_state = LifecycleState {
        schema_version: "1.0".to_string(),
        app_version: app_version.to_string(),
        run_id: recovery.current_run_id.clone(),
        started_at: recovery.started_at.clone(),
        launch_mode: recovery.launch_mode.clone(),
        clean_shutdown: false,
        exit_kind: None,
        exit_message: None,
        exit_at: None,
    };
    save_lifecycle_state(app_dir, &next_state)?;

    Ok(recovery)
}

fn mark_exit_in_dir(
    app_dir: &Path,
    exit_kind: &str,
    exit_message: Option<String>,
) -> Result<(), AppError> {
    let Some(mut state) = load_lifecycle_state(app_dir)? else {
        return Ok(());
    };

    state.clean_shutdown = exit_kind == "clean";
    state.exit_kind = Some(exit_kind.to_string());
    state.exit_message = exit_message;
    state.exit_at = Some(Utc::now().to_rfc3339());
    save_lifecycle_state(app_dir, &state)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn unique_temp_dir(name: &str) -> PathBuf {
        let dir =
            std::env::temp_dir().join(format!("cybervpn-{name}-{}", uuid::Uuid::new_v4().simple()));
        fs::create_dir_all(&dir).expect("create temp dir");
        dir
    }

    #[test]
    fn parses_hidden_and_smoke_flags() {
        let options = parse_launch_options_from_args([
            "--hidden",
            "--smoke-exit-after-ms",
            "250",
            "--smoke-crash-after-ms=900",
        ]);
        assert!(options.hidden);
        assert_eq!(options.smoke_exit_after_ms, Some(250));
        assert_eq!(options.smoke_crash_after_ms, Some(900));
    }

    #[test]
    fn initialize_detects_unclean_previous_shutdown() {
        let temp_dir = unique_temp_dir("lifecycle-unclean");
        let first = initialize_in_dir(&temp_dir, &LaunchOptions::default(), "0.1.5")
            .expect("first init should succeed");
        assert!(!first.previous_unclean_shutdown_detected);

        let second = initialize_in_dir(
            &temp_dir,
            &LaunchOptions {
                hidden: true,
                ..LaunchOptions::default()
            },
            "0.1.5",
        )
        .expect("second init should succeed");
        assert!(second.previous_unclean_shutdown_detected);
        assert_eq!(
            second.previous_run_id.as_deref(),
            Some(first.current_run_id.as_str())
        );
        assert!(second.startup_cleanup_performed);
    }

    #[test]
    fn clean_exit_prevents_recovery_signal() {
        let temp_dir = unique_temp_dir("lifecycle-clean");
        let first = initialize_in_dir(&temp_dir, &LaunchOptions::default(), "0.1.5")
            .expect("first init should succeed");
        assert!(!first.previous_unclean_shutdown_detected);

        mark_exit_in_dir(&temp_dir, "clean", Some("normal exit".to_string()))
            .expect("clean exit should persist");

        let second = initialize_in_dir(&temp_dir, &LaunchOptions::default(), "0.1.5")
            .expect("second init should succeed");
        assert!(!second.previous_unclean_shutdown_detected);
        assert_eq!(second.previous_exit_kind.as_deref(), Some("clean"));
    }
}
