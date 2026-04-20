use crate::engine::error::AppError;
use lazy_static::lazy_static;
use regex::Regex;
use reqwest::Client;
use std::process::Stdio;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use tauri::{AppHandle, Emitter, Manager};
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::{Child, Command};
use tokio::sync::Mutex;

#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x08000000;
#[cfg(target_os = "windows")]
use windows::Win32::Foundation::{CloseHandle, HANDLE};
#[cfg(target_os = "windows")]
use windows::Win32::System::Threading::{GetExitCodeProcess, TerminateProcess};
#[cfg(target_os = "windows")]
const STILL_ACTIVE_EXIT_CODE: u32 = 259;

lazy_static! {
    static ref TRAFFIC_REGEX: Regex =
        Regex::new(r"(?i)(?:up|sent)\D*(\d+)\D*(?:down|recv)\D*(\d+)").unwrap();
    static ref TRAFFIC_REGEX_REV: Regex =
        Regex::new(r"(?i)(?:down|recv)\D*(\d+)\D*(?:up|sent)\D*(\d+)").unwrap();
    static ref FAILURE_REGEX: Regex =
        Regex::new(r"(?i)(connection reset|timeout|dns failure).*?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})")
            .unwrap();
}

#[derive(Clone, serde::Serialize)]
struct RoutingSuggestion {
    domain: String,
    reason: String,
}

async fn check_routing_failures(
    line: &str,
    domain_failures: Arc<Mutex<std::collections::HashMap<String, (u32, std::time::Instant)>>>,
    app_handle: AppHandle,
) {
    if let Some(caps) = FAILURE_REGEX.captures(line) {
        let reason = caps
            .get(1)
            .map(|m| m.as_str().to_string())
            .unwrap_or_default();
        let domain = caps
            .get(2)
            .map(|m| m.as_str().to_string())
            .unwrap_or_default();

        let mut failures = domain_failures.lock().await;
        let now = std::time::Instant::now();

        // Cleanup old entries
        failures.retain(|_, (_, time)| now.duration_since(*time).as_secs() < 120);

        let entry = failures.entry(domain.clone()).or_insert((0, now));
        entry.0 += 1;
        entry.1 = now;

        if entry.0 == 3 {
            let _ = app_handle.emit("routing-suggestion", RoutingSuggestion { domain, reason });
        }
    }
}

#[derive(Clone, serde::Serialize)]
struct TrafficUpdate {
    up: u64,
    down: u64,
}

#[derive(Debug, Clone)]
pub struct RuntimeMonitorConfig {
    pub health_url: String,
}

async fn check_privacy_threats(line: &str, threats_blocked: Arc<AtomicU64>, app_handle: AppHandle) {
    if line.contains("rejected by rule 'adblock-standard'")
        || line.contains("rejected by rule 'block'")
    {
        // Typical string: "[Route] [XX tcp] connection to tcp:metrics.icloud.com:443 rejected by rule 'adblock-standard'"
        let mut domain = "unknown".to_string();
        if let Some(idx) = line.find("connection to ") {
            let substr = &line[idx + 14..];
            let end_idx = substr.find(" rejected").unwrap_or(substr.len());
            let target = &substr[..end_idx];

            // Extract domain from tcp:domain:port if applicable
            let parts: Vec<&str> = target.split(':').collect();
            if parts.len() >= 2 {
                domain = parts[1].to_string();
            } else {
                domain = parts[0].to_string();
            }
        }

        threats_blocked.fetch_add(1, Ordering::Relaxed);
        let _ = app_handle.emit("tracker-blocked", domain);
    }
}

pub struct ProcessManager {
    child: Arc<Mutex<Option<Child>>>,
    #[cfg(target_os = "windows")]
    is_elevated_run: Arc<Mutex<bool>>,
    #[cfg(target_os = "windows")]
    elevated_process_handle: Arc<Mutex<Option<usize>>>,
    expected_exit: Arc<Mutex<bool>>,
    domain_failures: Arc<Mutex<std::collections::HashMap<String, (u32, std::time::Instant)>>>,
    pub threats_blocked: Arc<AtomicU64>,
}

async fn poll_helix_health(
    health_url: String,
    expected_exit: Arc<Mutex<bool>>,
    app_handle: AppHandle,
) {
    let client = match Client::builder()
        .timeout(tokio::time::Duration::from_millis(1200))
        .build()
    {
        Ok(client) => client,
        Err(error) => {
            eprintln!("Failed to build Helix health client: {error}");
            return;
        }
    };

    let mut interval = tokio::time::interval(tokio::time::Duration::from_millis(750));
    let mut degraded_emitted = false;

    loop {
        interval.tick().await;

        if *expected_exit.lock().await {
            break;
        }

        match client.get(&health_url).send().await {
            Ok(response) => match response.error_for_status() {
                Ok(response) => match response
                    .json::<crate::engine::helix::config::HelixSidecarHealth>()
                    .await
                {
                    Ok(health) => {
                        degraded_emitted = false;
                        let _ = app_handle.emit(
                            "traffic_update",
                            TrafficUpdate {
                                up: health.bytes_sent,
                                down: health.bytes_received,
                            },
                        );
                        crate::engine::sys::stats::update_absolute_bytes(
                            health.bytes_sent,
                            health.bytes_received,
                        );
                        let _ = app_handle.emit("helix-health", health);
                    }
                    Err(error) => {
                        eprintln!("Failed to parse Helix health payload: {error}");
                        let _ = crate::engine::diagnostics::record_event(
                            &app_handle,
                            crate::engine::diagnostics::DiagnosticLevel::Warn,
                            "helix.health",
                            "Failed to parse Helix health payload",
                            serde_json::json!({
                                "error": error.to_string(),
                            }),
                        );
                    }
                },
                Err(error) => {
                    if !degraded_emitted {
                        let error_message =
                            format!("Helix health endpoint returned error: {error}");
                        let _ = app_handle.emit("helix-runtime-degraded", error_message.clone());
                        let _ = crate::engine::diagnostics::record_event(
                            &app_handle,
                            crate::engine::diagnostics::DiagnosticLevel::Warn,
                            "helix.health",
                            "Helix health endpoint returned error",
                            serde_json::json!({
                                "error": error.to_string(),
                                "health_url": health_url,
                            }),
                        );
                        degraded_emitted = true;
                    }
                }
            },
            Err(error) => {
                if !degraded_emitted {
                    let error_message = format!("Helix health endpoint is unavailable: {error}");
                    let _ = app_handle.emit("helix-runtime-degraded", error_message.clone());
                    let _ = crate::engine::diagnostics::record_event(
                        &app_handle,
                        crate::engine::diagnostics::DiagnosticLevel::Warn,
                        "helix.health",
                        "Helix health endpoint is unavailable",
                        serde_json::json!({
                            "error": error.to_string(),
                            "health_url": health_url,
                        }),
                    );
                    degraded_emitted = true;
                }
            }
        }
    }
}

async fn handle_unexpected_runtime_exit(app_handle: &AppHandle, reason: &str) {
    let _ = crate::engine::sysproxy::clear_system_proxy();

    if let Some(state) = app_handle.try_state::<crate::ipc::AppState>() {
        let previous_status = state.status.read().await.clone();
        let mut status_lock = state.status.write().await;
        status_lock.status = "error".to_string();
        status_lock.proxy_url = None;
        status_lock.message = Some(reason.to_string());
        status_lock.active_core = None;
        status_lock.active_id = None;
        status_lock.up_bytes = 0;
        status_lock.down_bytes = 0;
        let status_snapshot = status_lock.clone();
        drop(status_lock);
        let _ = crate::ipc::emit_connection_status_event(app_handle, status_snapshot);

        let _ = crate::engine::diagnostics::record_event(
            app_handle,
            crate::engine::diagnostics::DiagnosticLevel::Error,
            "vpn.process",
            "VPN runtime exited unexpectedly",
            serde_json::json!({
                "reason": reason,
                "previous_status": previous_status.status,
                "previous_core": previous_status.active_core,
                "previous_proxy_url": previous_status.proxy_url,
            }),
        );
    }

    if let Ok(mut store_data) = crate::engine::store::load_store(app_handle) {
        if store_data.active_profile_id.is_some() {
            store_data.active_profile_id = None;
            let _ = crate::engine::store::save_store(app_handle, &store_data);
        }
    }
}

impl Default for ProcessManager {
    fn default() -> Self {
        Self::new()
    }
}

impl ProcessManager {
    pub fn new() -> Self {
        Self {
            child: Arc::new(Mutex::new(None)),
            #[cfg(target_os = "windows")]
            is_elevated_run: Arc::new(Mutex::new(false)),
            #[cfg(target_os = "windows")]
            elevated_process_handle: Arc::new(Mutex::new(None)),
            expected_exit: Arc::new(Mutex::new(false)),
            domain_failures: Arc::new(Mutex::new(std::collections::HashMap::new())),
            threats_blocked: Arc::new(AtomicU64::new(0)),
        }
    }

    pub async fn start(
        &self,
        app_handle: AppHandle,
        bin_path: std::path::PathBuf,
        config_path: std::path::PathBuf,
        tun_mode: bool,
        core_name: &str,
        runtime_monitor: Option<RuntimeMonitorConfig>,
    ) -> Result<(), AppError> {
        let mut child_guard = self.child.lock().await;

        if child_guard.is_some() {
            return Err(AppError::System("VPN core is already running".to_string()));
        }

        *self.expected_exit.lock().await = false;

        if core_name == "xray" {
            println!("Warning: connecting with Xray-core, limited config generation rules apply.");
        }

        println!(
            "Starting {} with config: {}",
            core_name,
            config_path.display()
        );
        println!("TUN Mode Enabled: {}", tun_mode);
        let _ = crate::engine::diagnostics::record_event(
            &app_handle,
            crate::engine::diagnostics::DiagnosticLevel::Info,
            "vpn.connect",
            format!("Starting {core_name} runtime"),
            serde_json::json!({
                "core": core_name,
                "tun_mode": tun_mode,
                "config_path": config_path.display().to_string(),
            }),
        );

        let mut command = if tun_mode && !crate::engine::sys::is_elevated() {
            #[cfg(target_os = "windows")]
            {
                // Invoke UAC elevation
                println!("Requesting elevation via UAC...");
                let elevated_process_handle =
                    crate::engine::sys::elevate_and_run(&bin_path, &config_path)?;

                let mut elevated_guard = self.is_elevated_run.lock().await;
                *elevated_guard = true;
                *self.elevated_process_handle.lock().await = Some(elevated_process_handle);

                // We must tail the log file asynchronously
                let log_path = config_path.with_file_name("run.log");
                let app_clone = app_handle.clone();
                let failures_clone1 = self.domain_failures.clone();
                let threats_clone1 = self.threats_blocked.clone();
                tokio::spawn(async move {
                    let deadline =
                        tokio::time::Instant::now() + tokio::time::Duration::from_secs(15);
                    let file = loop {
                        match tokio::fs::File::open(&log_path).await {
                            Ok(file) => break Some(file),
                            Err(_) if tokio::time::Instant::now() < deadline => {
                                tokio::time::sleep(tokio::time::Duration::from_millis(250)).await;
                            }
                            Err(error) => {
                                let _ = crate::engine::diagnostics::record_event(
                                    &app_clone,
                                    crate::engine::diagnostics::DiagnosticLevel::Warn,
                                    "runtime.sing-box",
                                    "Elevated sing-box log file did not appear in time",
                                    serde_json::json!({
                                        "log_path": log_path.display().to_string(),
                                        "error": error.to_string(),
                                    }),
                                );
                                break None;
                            }
                        }
                    };

                    let Some(file) = file else {
                        return;
                    };

                    let mut reader = tokio::io::BufReader::new(file);
                    let mut line = String::new();
                    use tokio::io::AsyncBufReadExt;

                    loop {
                        line.clear();
                        match reader.read_line(&mut line).await {
                            Ok(0) => {
                                // EOF reached, wait and try again
                                tokio::time::sleep(tokio::time::Duration::from_millis(200)).await;
                            }
                            Ok(_) => {
                                let trimmed = line.trim();
                                if trimmed.is_empty() {
                                    continue;
                                }

                                // Check for traffic stats
                                if let Some(caps) = TRAFFIC_REGEX.captures(trimmed) {
                                    if let (Ok(up), Ok(down)) =
                                        (caps[1].parse::<u64>(), caps[2].parse::<u64>())
                                    {
                                        let _ = app_clone
                                            .emit("traffic_update", TrafficUpdate { up, down });
                                        crate::engine::sys::stats::update_absolute_bytes(up, down);
                                    }
                                } else if let Some(caps) = TRAFFIC_REGEX_REV.captures(trimmed) {
                                    if let (Ok(down), Ok(up)) =
                                        (caps[1].parse::<u64>(), caps[2].parse::<u64>())
                                    {
                                        let _ = app_clone
                                            .emit("traffic_update", TrafficUpdate { up, down });
                                        crate::engine::sys::stats::update_absolute_bytes(up, down);
                                    }
                                }
                                let _ = app_clone.emit("singbox-log", trimmed);
                                let _ = crate::engine::diagnostics::append_core_runtime_log(
                                    &app_clone, "sing-box", "stdout", trimmed,
                                );

                                check_routing_failures(
                                    trimmed,
                                    failures_clone1.clone(),
                                    app_clone.clone(),
                                )
                                .await;

                                check_privacy_threats(
                                    trimmed,
                                    threats_clone1.clone(),
                                    app_clone.clone(),
                                )
                                .await;
                            }
                            Err(_) => {
                                break;
                            }
                        }
                    }
                });

                let app_clone_watchdog = app_handle.clone();
                let expected_exit_arc = self.expected_exit.clone();
                let is_elevated_arc = self.is_elevated_run.clone();
                let elevated_process_handle_arc = self.elevated_process_handle.clone();

                tokio::spawn(async move {
                    let mut interval =
                        tokio::time::interval(tokio::time::Duration::from_millis(500));

                    loop {
                        interval.tick().await;

                        if *expected_exit_arc.lock().await {
                            break;
                        }

                        let mut is_running = false;
                        if *is_elevated_arc.lock().await {
                            if let Some(raw_handle) = *elevated_process_handle_arc.lock().await {
                                let handle = HANDLE(raw_handle as *mut std::ffi::c_void);
                                let mut exit_code = 0u32;
                                let still_active = unsafe {
                                    GetExitCodeProcess(handle, &mut exit_code).is_ok()
                                        && exit_code == STILL_ACTIVE_EXIT_CODE
                                };
                                if still_active {
                                    is_running = true;
                                } else {
                                    unsafe {
                                        let _ = CloseHandle(handle);
                                    }
                                    *elevated_process_handle_arc.lock().await = None;
                                    *is_elevated_arc.lock().await = false;
                                }
                            } else {
                                *is_elevated_arc.lock().await = false;
                            }
                        }

                        if !is_running {
                            handle_unexpected_runtime_exit(
                                &app_clone_watchdog,
                                "Elevated VPN runtime exited unexpectedly",
                            )
                            .await;
                            use tauri::Manager;
                            if let Some(guard) = app_clone_watchdog
                                .try_state::<crate::engine::sys::sentinel::SentinelGuard>(
                            ) {
                                if guard.is_active() {
                                    let _ = guard.enable();
                                }
                            }
                            let _ = app_clone_watchdog.emit("vpn-process-died", ());
                            break;
                        }
                    }
                });

                return Ok(());
            }

            #[cfg(unix)]
            {
                // Linux/macOS: wrap the command in pkexec to seamlessly prompt for user password
                // Note: pkexec must be installed on the system map the GUI prompt appropriately.
                // Alternative is `sudo -A` with a custom askpass script.
                println!("Requesting elevation via pkexec...");
                let mut cmd = Command::new("pkexec");
                cmd.arg(bin_path);
                cmd.arg("run");
                cmd.arg("-c").arg(config_path);
                cmd
            }
        } else {
            // Normal execution (or already elevated)
            let mut c = Command::new(&bin_path);
            c.arg("run")
                .arg("-c")
                .arg(&config_path)
                .stdin(Stdio::null())
                .stdout(Stdio::piped())
                .stderr(Stdio::piped());
            #[cfg(target_os = "windows")]
            c.creation_flags(CREATE_NO_WINDOW);
            c
        };

        // Spawn child
        let mut spawn_child = command.spawn()?;

        let stdout = spawn_child
            .stdout
            .take()
            .ok_or_else(|| AppError::System("Failed to capture stdout".to_string()))?;

        let stderr = spawn_child
            .stderr
            .take()
            .ok_or_else(|| AppError::System("Failed to capture stderr".to_string()))?;

        let app_clone1 = app_handle.clone();
        let failures_clone2 = self.domain_failures.clone();
        let threats_clone2 = self.threats_blocked.clone();
        let core_name_stdout = core_name.to_string();
        tokio::spawn(async move {
            let mut reader = BufReader::new(stdout).lines();
            while let Ok(Some(line)) = reader.next_line().await {
                // Check for traffic stats
                if let Some(caps) = TRAFFIC_REGEX.captures(&line) {
                    if let (Ok(up), Ok(down)) = (caps[1].parse::<u64>(), caps[2].parse::<u64>()) {
                        let _ = app_clone1.emit("traffic_update", TrafficUpdate { up, down });
                        crate::engine::sys::stats::update_absolute_bytes(up, down);
                    }
                } else if let Some(caps) = TRAFFIC_REGEX_REV.captures(&line) {
                    if let (Ok(down), Ok(up)) = (caps[1].parse::<u64>(), caps[2].parse::<u64>()) {
                        let _ = app_clone1.emit("traffic_update", TrafficUpdate { up, down });
                        crate::engine::sys::stats::update_absolute_bytes(up, down);
                    }
                }

                // Forward Sing-box stdout to React frontend
                let _ = app_clone1.emit("singbox-log", &line);
                let _ = crate::engine::diagnostics::append_core_runtime_log(
                    &app_clone1,
                    &core_name_stdout,
                    "stdout",
                    &line,
                );

                check_routing_failures(&line, failures_clone2.clone(), app_clone1.clone()).await;

                check_privacy_threats(&line, threats_clone2.clone(), app_clone1.clone()).await;
            }
        });

        let app_clone2 = app_handle.clone();
        let failures_clone3 = self.domain_failures.clone();
        let threats_clone3 = self.threats_blocked.clone();
        let core_name_stderr = core_name.to_string();
        tokio::spawn(async move {
            let mut reader = BufReader::new(stderr).lines();
            while let Ok(Some(line)) = reader.next_line().await {
                // Check for traffic stats
                if let Some(caps) = TRAFFIC_REGEX.captures(&line) {
                    if let (Ok(up), Ok(down)) = (caps[1].parse::<u64>(), caps[2].parse::<u64>()) {
                        let _ = app_clone2.emit("traffic_update", TrafficUpdate { up, down });
                        crate::engine::sys::stats::update_absolute_bytes(up, down);
                    }
                } else if let Some(caps) = TRAFFIC_REGEX_REV.captures(&line) {
                    if let (Ok(down), Ok(up)) = (caps[1].parse::<u64>(), caps[2].parse::<u64>()) {
                        let _ = app_clone2.emit("traffic_update", TrafficUpdate { up, down });
                        crate::engine::sys::stats::update_absolute_bytes(up, down);
                    }
                }

                // Forward Sing-box stderr to React frontend
                let _ = app_clone2.emit("singbox-log", &line);
                let _ = crate::engine::diagnostics::append_core_runtime_log(
                    &app_clone2,
                    &core_name_stderr,
                    "stderr",
                    &line,
                );

                check_routing_failures(&line, failures_clone3.clone(), app_clone2.clone()).await;

                check_privacy_threats(&line, threats_clone3.clone(), app_clone2.clone()).await;
            }
        });

        *child_guard = Some(spawn_child);
        drop(child_guard); // explicit unlock before spinning watchdog

        let app_clone_watchdog = app_handle.clone();
        let child_arc = self.child.clone();
        let expected_exit_arc = self.expected_exit.clone();

        tokio::spawn(async move {
            let mut interval = tokio::time::interval(tokio::time::Duration::from_millis(500));

            loop {
                interval.tick().await;

                if *expected_exit_arc.lock().await {
                    break;
                }

                let mut is_running = false;

                {
                    let mut cg = child_arc.lock().await;
                    if let Some(child) = cg.as_mut() {
                        is_running = true;
                        if let Ok(Some(_status)) = child.try_wait() {
                            let _ = cg.take();
                            is_running = false;
                        }
                    }
                }

                if !is_running {
                    handle_unexpected_runtime_exit(
                        &app_clone_watchdog,
                        "VPN runtime exited unexpectedly",
                    )
                    .await;
                    use tauri::Manager;
                    if let Some(guard) = app_clone_watchdog
                        .try_state::<crate::engine::sys::sentinel::SentinelGuard>()
                    {
                        if guard.is_active() {
                            let _ = guard.enable();
                        }
                    }
                    let _ = app_clone_watchdog.emit("vpn-process-died", ());
                    break;
                }
            }
        });

        if let Some(runtime_monitor) = runtime_monitor {
            let _ = crate::engine::diagnostics::record_event(
                &app_handle,
                crate::engine::diagnostics::DiagnosticLevel::Info,
                "vpn.connect",
                format!("{core_name} runtime started"),
                serde_json::json!({
                    "core": core_name,
                    "health_url": runtime_monitor.health_url,
                }),
            );
            tokio::spawn(poll_helix_health(
                runtime_monitor.health_url,
                self.expected_exit.clone(),
                app_handle.clone(),
            ));
        } else {
            let _ = crate::engine::diagnostics::record_event(
                &app_handle,
                crate::engine::diagnostics::DiagnosticLevel::Info,
                "vpn.connect",
                format!("{core_name} runtime started"),
                serde_json::json!({
                    "core": core_name,
                }),
            );
        }

        Ok(())
    }

    pub async fn stop(&self) -> Result<(), AppError> {
        *self.expected_exit.lock().await = true;

        #[cfg(target_os = "windows")]
        {
            let mut elevated_guard = self.is_elevated_run.lock().await;
            if *elevated_guard {
                if let Some(raw_handle) = self.elevated_process_handle.lock().await.take() {
                    let handle = HANDLE(raw_handle as *mut std::ffi::c_void);
                    println!("Stopping elevated VPN core via process handle...");
                    unsafe {
                        let _ = TerminateProcess(handle, 1);
                        let _ = CloseHandle(handle);
                    }
                }
                *elevated_guard = false;
                return Ok(());
            }
        }

        let child_process = {
            let mut child_guard = self.child.lock().await;
            child_guard.take()
        };

        if let Some(mut child) = child_process {
            println!("Stopping VPN core process...");
            child.kill().await?;
            child.wait().await?;
            return Ok(());
        }

        Err(AppError::System("VPN core is not running".to_string()))
    }

    pub async fn is_running(&self) -> bool {
        #[cfg(target_os = "windows")]
        {
            if *self.is_elevated_run.lock().await {
                return true;
            }
        }
        self.child.lock().await.is_some()
    }
}
