use crate::engine::error::AppError;
use lazy_static::lazy_static;
use regex::Regex;
use std::process::Stdio;
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
}

#[derive(Clone, serde::Serialize)]
struct TrafficUpdate {
    up: u64,
    down: u64,
}

pub struct ProcessManager {
    child: Arc<Mutex<Option<Child>>>,
    #[cfg(target_os = "windows")]
    is_elevated_run: Arc<Mutex<bool>>,
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
                                        }
                                    } else if let Some(caps) = TRAFFIC_REGEX_REV.captures(trimmed) {
                                        if let (Ok(down), Ok(up)) =
                                            (caps[1].parse::<u64>(), caps[2].parse::<u64>())
                                        {
                                            let _ = app_clone
                                                .emit("traffic_update", TrafficUpdate { up, down });
                                        }
                                    }
                                    let _ = app_clone.emit("singbox-log", trimmed);
                                }
                                Err(_) => {
                                    break;
                                }
                            }
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
        tokio::spawn(async move {
            let mut reader = BufReader::new(stdout).lines();
            while let Ok(Some(line)) = reader.next_line().await {
                // Check for traffic stats
                if let Some(caps) = TRAFFIC_REGEX.captures(&line) {
                    if let (Ok(up), Ok(down)) = (caps[1].parse::<u64>(), caps[2].parse::<u64>()) {
                        let _ = app_clone1.emit("traffic_update", TrafficUpdate { up, down });
                    }
                } else if let Some(caps) = TRAFFIC_REGEX_REV.captures(&line) {
                    if let (Ok(down), Ok(up)) = (caps[1].parse::<u64>(), caps[2].parse::<u64>()) {
                        let _ = app_clone1.emit("traffic_update", TrafficUpdate { up, down });
                    }
                }

                // Forward Sing-box stdout to React frontend
                let _ = app_clone1.emit("singbox-log", &line);
            }
        });

        let app_clone2 = app_handle.clone();
        tokio::spawn(async move {
            let mut reader = BufReader::new(stderr).lines();
            while let Ok(Some(line)) = reader.next_line().await {
                // Check for traffic stats
                if let Some(caps) = TRAFFIC_REGEX.captures(&line) {
                    if let (Ok(up), Ok(down)) = (caps[1].parse::<u64>(), caps[2].parse::<u64>()) {
                        let _ = app_clone2.emit("traffic_update", TrafficUpdate { up, down });
                    }
                } else if let Some(caps) = TRAFFIC_REGEX_REV.captures(&line) {
                    if let (Ok(down), Ok(up)) = (caps[1].parse::<u64>(), caps[2].parse::<u64>()) {
                        let _ = app_clone2.emit("traffic_update", TrafficUpdate { up, down });
                    }
                }

                // Forward Sing-box stderr to React frontend
                let _ = app_clone2.emit("singbox-log", &line);
            }
        });

        *child_guard = Some(spawn_child);
        Ok(())
    }

    pub async fn stop(&self) -> Result<(), AppError> {
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
