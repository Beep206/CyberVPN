pub mod os_router;
pub mod speaker;

use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tauri::{AppHandle, State};
use tokio::sync::Mutex;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BgpConfig {
    pub remote_address: String,
    pub remote_port: u16,
    pub local_address: String,
    pub router_id: String,
    pub as_number: u32,
    pub remote_as: u32,
    pub hold_time: u16,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BgpStatus {
    pub state: String,
    pub routes_count: usize,
    pub uptime: u64,
}

pub struct BgpStateWrapper {
    pub inner: Arc<Mutex<speaker::BgpSessionState>>,
}

#[tauri::command]
pub async fn start_bgp_session(
    config: BgpConfig,
    state: State<'_, BgpStateWrapper>,
    app_handle: AppHandle,
) -> Result<(), String> {
    let mut session = state.inner.lock().await;
    session
        .start(config, app_handle)
        .await
        .map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub async fn stop_bgp_session(state: State<'_, BgpStateWrapper>) -> Result<(), String> {
    let mut session = state.inner.lock().await;
    session.stop().await;
    Ok(())
}

#[tauri::command]
pub async fn get_bgp_status(state: State<'_, BgpStateWrapper>) -> Result<BgpStatus, String> {
    let session = state.inner.lock().await;
    Ok(session.get_status())
}

#[tauri::command]
pub async fn get_bgp_routes(state: State<'_, BgpStateWrapper>) -> Result<Vec<String>, String> {
    let session = state.inner.lock().await;
    Ok(session.get_routes())
}

#[tauri::command]
pub async fn check_is_admin() -> Result<bool, String> {
    #[cfg(unix)]
    {
        // For macOS and Linux, if euid == 0, we have root privileges.
        let is_root = unsafe { libc::geteuid() == 0 };
        return Ok(is_root);
    }

    #[cfg(windows)]
    {
        // Basic check for Windows: try to open the system physical drive or a privileged key
        // A common poor man's elevated check without pulling in complex winapi calls.
        use std::process::Command;
        let mut command = Command::new("net");
        command.arg("session");

        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        command.creation_flags(CREATE_NO_WINDOW);

        let output = command.output();

        if let Ok(output) = output {
            return Ok(output.status.success());
        }
        return Ok(false);
    }

    #[cfg(not(any(unix, windows)))]
    {
        Ok(false)
    }
}

#[tauri::command]
pub async fn restart_as_admin(app_handle: AppHandle) -> Result<(), String> {
    let current_exe = std::env::current_exe().map_err(|e| e.to_string())?;
    let path_str = current_exe.to_string_lossy().to_string();

    #[cfg(target_os = "windows")]
    {
        use std::process::Command;
        let p_str = format!("'{}'", path_str.replace("'", "''"));
        Command::new("powershell")
            .args([
                "-NoProfile",
                "-WindowStyle",
                "Hidden",
                "-Command",
                "Start-Process",
                &p_str,
                "-Verb",
                "runAs",
            ])
            .spawn()
            .map_err(|e| e.to_string())?;
    }

    #[cfg(target_os = "linux")]
    {
        use std::process::Command;
        Command::new("pkexec")
            .arg(&path_str)
            .spawn()
            .map_err(|e| e.to_string())?;
    }

    #[cfg(target_os = "macos")]
    {
        use std::process::Command;
        let script = format!(
            "do shell script \"'{}'\" with administrator privileges",
            path_str
        );
        Command::new("osascript")
            .args(["-e", &script])
            .spawn()
            .map_err(|e| e.to_string())?;
    }

    // Give it a tiny bit of time to launch, then exit
    std::thread::spawn(move || {
        std::thread::sleep(std::time::Duration::from_millis(500));
        app_handle.exit(0);
    });

    Ok(())
}
