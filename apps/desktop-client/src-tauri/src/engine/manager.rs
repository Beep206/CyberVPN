use tauri::{AppHandle, Emitter};
use tokio::process::{Child, Command};
use tokio::io::{AsyncBufReadExt, BufReader};
use std::sync::Arc;
use tokio::sync::Mutex;
use std::process::Stdio;
use crate::engine::error::AppError;
use regex::Regex;
use lazy_static::lazy_static;

lazy_static! {
    static ref TRAFFIC_REGEX: Regex = Regex::new(r"(?i)(?:up|sent)\D*(\d+)\D*(?:down|recv)\D*(\d+)").unwrap();
    static ref TRAFFIC_REGEX_REV: Regex = Regex::new(r"(?i)(?:down|recv)\D*(\d+)\D*(?:up|sent)\D*(\d+)").unwrap();
}

#[derive(Clone, serde::Serialize)]
struct TrafficUpdate {
    up: u64,
    down: u64,
}

pub struct ProcessManager {
    child: Arc<Mutex<Option<Child>>>,
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
        }
    }

    pub async fn start(&self, app_handle: AppHandle, bin_path: std::path::PathBuf, config_path: std::path::PathBuf) -> Result<(), AppError> {
        let mut child_guard = self.child.lock().await;

        if child_guard.is_some() {
            return Err(AppError::System("Sing-box is already running".to_string()));
        }

        println!("Starting sing-box with config: {}", config_path.display());

        let mut command = Command::new(bin_path);
        command.arg("run");
        command.arg("-c").arg(config_path);
        
        command.stdout(Stdio::piped());
        command.stderr(Stdio::piped());

        // Spawn child
        let mut spawn_child = command.spawn()?;

        let stdout = spawn_child.stdout.take()
            .ok_or_else(|| AppError::System("Failed to capture stdout".to_string()))?;
            
        let stderr = spawn_child.stderr.take()
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
        self.child.lock().await.is_some()
    }
}
