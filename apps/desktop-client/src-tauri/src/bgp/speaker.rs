use super::{BgpConfig, BgpStatus};
use std::time::Instant;
use tauri::AppHandle;
use tokio::task::JoinHandle;

pub struct BgpSessionState {
    pub config: Option<BgpConfig>,
    pub running: bool,
    pub status: String,
    pub routes: std::collections::HashSet<String>,
    pub start_time: Option<Instant>,
    task_handle: Option<JoinHandle<()>>,
}

impl BgpSessionState {
    pub fn new() -> Self {
        Self {
            config: None,
            running: false,
            status: "Idle".to_string(),
            routes: std::collections::HashSet::new(),
            start_time: None,
            task_handle: None,
        }
    }

    pub async fn start(&mut self, config: BgpConfig, _app_handle: AppHandle) -> Result<(), String> {
        if self.running {
            return Err("BGP session is already running".to_string());
        }
        self.config = Some(config.clone());
        self.running = true;
        self.status = "Connect".to_string();
        self.start_time = Some(Instant::now());

        // A mock implementation representing connection wait and established state
        self.task_handle = Some(tokio::spawn(async move {
            tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;

            loop {
                tokio::time::sleep(tokio::time::Duration::from_secs(10)).await;
            }
        }));

        self.status = "Established".to_string();

        Ok(())
    }

    pub async fn stop(&mut self) {
        if let Some(handle) = self.task_handle.take() {
            handle.abort();
        }
        self.running = false;
        self.status = "Idle".to_string();
        self.routes.clear();
        self.start_time = None;
    }

    pub fn get_status(&self) -> BgpStatus {
        let uptime = self.start_time.map(|t| t.elapsed().as_secs()).unwrap_or(0);
        BgpStatus {
            state: self.status.clone(),
            routes_count: self.routes.len(),
            uptime,
        }
    }

    pub fn get_routes(&self) -> Vec<String> {
        self.routes.iter().cloned().collect()
    }
}
