use crate::engine::error::AppError;
use lazy_static::lazy_static;
use regex::Regex;
use std::process::Stdio;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use tauri::{AppHandle, Emitter};
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::{Child, Command};
use tokio::sync::Mutex;

lazy_static! {
    static ref TRAFFIC_REGEX: Regex =
        Regex::new(r"(?i)(?:up|sent)\D*(\d+)\D*(?:down|recv)\D*(\d+)").unwrap();
    static ref TRAFFIC_REGEX_REV: Regex =
        Regex::new(r"(?i)(?:down|recv)\D*(\d+)\D*(?:up|sent)\D*(\d+)").unwrap();
    static ref FAILURE_REGEX: Regex =
        Regex::new(r"(?i)(connection reset|timeout|dns failure).*?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})").unwrap();
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
        let reason = caps.get(1).map(|m| m.as_str().to_string()).unwrap_or_default();
        let domain = caps.get(2).map(|m| m.as_str().to_string()).unwrap_or_default();
        
        let mut failures = domain_failures.lock().await;
        let now = std::time::Instant::now();
        
        // Cleanup old entries
        failures.retain(|_, (_, time)| now.duration_since(*time).as_secs() < 120);

        let entry = failures.entry(domain.clone()).or_insert((0, now));
        entry.0 += 1;
        entry.1 = now;

        if entry.0 == 3 {
             let _ = app_handle.emit("routing-suggestion", RoutingSuggestion {
                 domain,
                 reason,
             });
        }
    }
}

#[derive(Clone, serde::Serialize)]
struct TrafficUpdate {
    up: u64,
    down: u64,
}

async fn check_privacy_threats(
    line: &str,
    threats_blocked: Arc<AtomicU64>,
    app_handle: AppHandle,
) {
    if line.contains("rejected by rule 'adblock-standard'") || line.contains("rejected by rule 'block'") {
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
    expected_exit: Arc<Mutex<bool>>,
    domain_failures: Arc<Mutex<std::collections::HashMap<String, (u32, std::time::Instant)>>>,
    pub threats_blocked: Arc<AtomicU64>,
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
    ) -> Result<(), AppError> {
        let mut child_guard = self.child.lock().await;

        if child_guard.is_some() {
            return Err(AppError::System("Sing-box is already running".to_string()));
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

        let mut command = if tun_mode && !crate::engine::sys::is_elevated() {
            #[cfg(target_os = "windows")]
            {
                // Invoke UAC elevation
                println!("Requesting elevation via UAC...");
                crate::engine::sys::elevate_and_run(&bin_path, &config_path)?;

                let mut elevated_guard = self.is_elevated_run.lock().await;
                *elevated_guard = true;

                // We must tail the log file asynchronously
                let log_path = config_path.with_file_name("run.log");
                let app_clone = app_handle.clone();
                let failures_clone1 = self.domain_failures.clone();
                let threats_clone1 = self.threats_blocked.clone();
                tokio::spawn(async move {
                    // Give process a moment to create the log file array
                    tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
                    if let Ok(file) = tokio::fs::File::open(&log_path).await {
                        let mut reader = tokio::io::BufReader::new(file);
                        let mut line = String::new();
                        use tokio::io::AsyncBufReadExt;

                        loop {
                            line.clear();
                            match reader.read_line(&mut line).await {
                                Ok(0) => {
                                    // EOF reached, wait and try again
                                    tokio::time::sleep(tokio::time::Duration::from_millis(200))
                                        .await;
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
                                    
                                    check_routing_failures(
                                        trimmed,
                                        failures_clone1.clone(),
                                        app_clone.clone()
                                    ).await;

                                    check_privacy_threats(
                                        trimmed,
                                        threats_clone1.clone(),
                                        app_clone.clone()
                                    ).await;
                                }
                                Err(_) => {
                                    break;
                                }
                            }
                        }
                    }
                });

                let app_clone_watchdog = app_handle.clone();
                let expected_exit_arc = self.expected_exit.clone();
                let is_elevated_arc = self.is_elevated_run.clone();

                tokio::spawn(async move {
                    let mut interval = tokio::time::interval(tokio::time::Duration::from_millis(500));
                    let mut sys = sysinfo::System::new();

                    loop {
                        interval.tick().await;

                        if *expected_exit_arc.lock().await {
                            break;
                        }

                        let mut is_running = false;
                        if *is_elevated_arc.lock().await {
                            is_running = true;
                            sys.refresh_processes();
                            let mut found = false;
                            for _ in sys.processes_by_exact_name("sing-box.exe".as_ref()) {
                                found = true;
                                break;
                            }
                            if !found {
                                is_running = false;
                                *is_elevated_arc.lock().await = false;
                            }
                        }

                        if !is_running {
                            use tauri::Manager;
                            if let Some(guard) = app_clone_watchdog.try_state::<crate::engine::sys::sentinel::SentinelGuard>() {
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
                .stdout(Stdio::piped())
                .stderr(Stdio::piped());
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
                
                check_routing_failures(
                    &line,
                    failures_clone2.clone(),
                    app_clone1.clone()
                ).await;

                check_privacy_threats(
                    &line,
                    threats_clone2.clone(),
                    app_clone1.clone()
                ).await;
            }
        });

        let app_clone2 = app_handle.clone();
        let failures_clone3 = self.domain_failures.clone();
        let threats_clone3 = self.threats_blocked.clone();
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
                
                check_routing_failures(
                    &line,
                    failures_clone3.clone(),
                    app_clone2.clone()
                ).await;

                check_privacy_threats(
                    &line,
                    threats_clone3.clone(),
                    app_clone2.clone()
                ).await;
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
                    // Unexpected exit detected
                    use tauri::Manager;
                    if let Some(guard) = app_clone_watchdog.try_state::<crate::engine::sys::sentinel::SentinelGuard>() {
                        if guard.is_active() {
                            let _ = guard.enable();
                        }
                    }
                    let _ = app_clone_watchdog.emit("vpn-process-died", ());
                    break;
                }
            }
        });

        Ok(())
    }

    pub async fn stop(&self) -> Result<(), AppError> {
        *self.expected_exit.lock().await = true;

        #[cfg(target_os = "windows")]
        {
            let mut elevated_guard = self.is_elevated_run.lock().await;
            if *elevated_guard {
                println!("Stopping elevated sing-box process via taskkill...");
                let _ = tokio::process::Command::new("taskkill")
                    .args(&["/F", "/IM", "sing-box.exe"])
                    .output()
                    .await;
                *elevated_guard = false;
                return Ok(());
            }
        }

        let child_process = {
            let mut child_guard = self.child.lock().await;
            child_guard.take()
        };

        if let Some(mut child) = child_process {
            println!("Stopping sing-box process...");
            child.kill().await?;
            child.wait().await?;
            return Ok(());
        }

        Err(AppError::System("Sing-box is not running".to_string()))
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
