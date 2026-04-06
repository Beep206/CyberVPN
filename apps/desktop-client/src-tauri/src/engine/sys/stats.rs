use crate::engine::error::AppError;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use std::sync::Mutex;
use tauri::{AppHandle, Manager};

lazy_static::lazy_static! {
    pub static ref ACTIVE_SESSION: Mutex<Option<SessionMetadata>> = Mutex::new(None);
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct UsageRecord {
    pub date: String,
    pub bytes_up: u64,
    pub bytes_down: u64,
    pub protocol: String,
    pub country_code: String,
}

#[derive(Debug, Clone)]
pub struct SessionMetadata {
    pub protocol: String,
    pub country_code: String,
    pub session_up: u64,
    pub session_down: u64,
    pub last_synced_up: u64,
    pub last_synced_down: u64,
}

pub fn start_session(protocol: String, country_code: String) {
    if let Ok(mut session) = ACTIVE_SESSION.lock() {
        // Attempt to flush previous session if it existed
        if let Some(_old_sess) = session.take() {
            // We can't safely grab AppHandle here, but we can do a background queue.
            // Better to rely on manual flush before starting a new one.
        }
        *session = Some(SessionMetadata {
            protocol,
            country_code,
            session_up: 0,
            session_down: 0,
            last_synced_up: 0,
            last_synced_down: 0,
        });
    }
}

pub fn update_absolute_bytes(up: u64, down: u64) {
    if let Ok(mut session_opt) = ACTIVE_SESSION.lock() {
        if let Some(session) = session_opt.as_mut() {
            session.session_up = up;
            session.session_down = down;
        }
    }
}

pub fn get_stats_path(app: &AppHandle) -> PathBuf {
    app.path()
        .app_data_dir()
        .unwrap()
        .join("usage_history.json")
}

pub fn load_history(app: &AppHandle) -> Result<Vec<UsageRecord>, AppError> {
    let path = get_stats_path(app);
    if !path.exists() {
        return Ok(Vec::new());
    }

    let data = fs::read_to_string(&path)?;
    match serde_json::from_str::<Vec<UsageRecord>>(&data) {
        Ok(history) => Ok(history),
        Err(e) => {
            // Corruption detected!
            let corrupted_path = path.with_extension("corrupted");
            let _ = fs::rename(&path, corrupted_path);
            Err(AppError::UsageCorrupted(e.to_string()))
        }
    }
}

pub fn flush_session(app: &AppHandle) -> Result<(), AppError> {
    let (delta_up, delta_down, protocol, country_code) = {
        let mut session_opt = ACTIVE_SESSION.lock().unwrap();
        if let Some(session) = session_opt.as_mut() {
            let add_up = session.session_up.saturating_sub(session.last_synced_up);
            let add_down = session
                .session_down
                .saturating_sub(session.last_synced_down);

            if add_up == 0 && add_down == 0 {
                return Ok(()); // Nothing to flush
            }

            session.last_synced_up = session.session_up;
            session.last_synced_down = session.session_down;

            (
                add_up,
                add_down,
                session.protocol.clone(),
                session.country_code.clone(),
            )
        } else {
            return Ok(());
        }
    };

    let today = chrono::Local::now().format("%Y-%m-%d").to_string();
    let mut history = load_history(app).unwrap_or_default();

    // Look for an existing record for today, protocol, and country
    let mut found = false;
    for record in history.iter_mut() {
        if record.date == today
            && record.protocol == protocol
            && record.country_code == country_code
        {
            record.bytes_up = record.bytes_up.saturating_add(delta_up);
            record.bytes_down = record.bytes_down.saturating_add(delta_down);
            found = true;
            break;
        }
    }

    if !found {
        history.push(UsageRecord {
            date: today,
            bytes_up: delta_up,
            bytes_down: delta_down,
            protocol,
            country_code,
        });
    }

    let json = serde_json::to_string_pretty(&history)?;
    fs::write(get_stats_path(app), json)?;

    Ok(())
}

pub fn spawn_flush_interval(app: AppHandle) {
    tauri::async_runtime::spawn(async move {
        let mut interval = tokio::time::interval(std::time::Duration::from_secs(300)); // 5 mins
        loop {
            interval.tick().await;
            let _ = flush_session(&app);
        }
    });
}

#[tauri::command]
pub async fn get_usage_history(
    _period: String,
    app: tauri::AppHandle,
) -> Result<Vec<UsageRecord>, AppError> {
    tokio::task::spawn_blocking(move || {
        let _ = flush_session(&app);
        let history = load_history(&app)?;
        Ok(history)
    })
    .await
    .map_err(|e| AppError::System(format!("Tokio error: {}", e)))?
}

pub fn resolve_ip_country(ip: &str) -> String {
    // Dummy deterministic GeoIP resolution mapping arbitrary IPs to global servers
    let countries = [
        "US", "DE", "GB", "NL", "SG", "JP", "FR", "CA", "AU", "BR", "CH", "FI", "KR",
    ];
    let sum: usize = ip.bytes().map(|b| b as usize).sum();
    countries[sum % countries.len()].to_string()
}

#[tauri::command]
pub async fn get_global_footprint(app: tauri::AppHandle) -> Result<HashMap<String, u64>, AppError> {
    tokio::task::spawn_blocking(move || {
        let history = load_history(&app)?;
        let mut footprint = HashMap::new();
        for record in history {
            // Include both upstream and downstream to footprint graph
            *footprint.entry(record.country_code).or_insert(0) +=
                record.bytes_up + record.bytes_down;
        }
        Ok(footprint)
    })
    .await
    .map_err(|e| AppError::System(format!("Tokio error: {}", e)))?
}
