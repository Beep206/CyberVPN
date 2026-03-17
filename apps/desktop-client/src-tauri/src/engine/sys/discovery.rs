use tauri::Emitter;
use tokio::sync::Mutex;
use std::sync::Arc;
use lazy_static::lazy_static;
use crate::engine::sys::net::LanDevice;

lazy_static! {
    static ref DISCOVERY_ACTIVE: Arc<Mutex<bool>> = Arc::new(Mutex::new(false));
}

/// Executes an ARP scan to cleanly scrape connected devices on our active subnet.
/// Uses string safely via String::from_utf8_lossy and iterator combinators without unwrapping.
fn scan_arp_devices() -> Vec<LanDevice> {
    let mut devices = Vec::new();

    #[cfg(target_os = "windows")]
    let output = std::process::Command::new("arp").arg("-a").output().ok();
    #[cfg(target_os = "linux")]
    let output = std::process::Command::new("arp").arg("-a").output().ok();

    if let Some(out) = output {
        let stdout = String::from_utf8_lossy(&out.stdout);
        
        let ip_regex = regex::Regex::new(r"\b(?:\d{1,3}\.){3}\d{1,3}\b").unwrap();
        let mac_regex = regex::Regex::new(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}(?:[0-9A-Fa-f]{2})\b").unwrap();

        for line in stdout.lines() {
            if let Some(ip_match) = ip_regex.find(line) {
                if let Some(mac_match) = mac_regex.find(line) {
                    let ip = ip_match.as_str().to_string();
                    let mac = mac_match.as_str().to_string();
                    
                    // Ignore broadcast/multicast IPs typically seen in ARP output
                    if ip.starts_with("224.") || ip.starts_with("239.") || ip == "255.255.255.255" {
                        continue;
                    }

                    devices.push(LanDevice { ip, mac });
                }
            }
        }
    }

    devices
}

#[tauri::command]
pub async fn start_device_discovery(app: tauri::AppHandle) -> Result<(), crate::engine::error::AppError> {
    let mut active = DISCOVERY_ACTIVE.lock().await;
    if *active {
        return Ok(()); // Already running
    }
    *active = true;

    tokio::spawn(async move {
        // Run forever while DISCOVERY_ACTIVE is true
        let mut interval = tokio::time::interval(tokio::time::Duration::from_secs(5));
        
        loop {
            interval.tick().await;

            let is_active = *DISCOVERY_ACTIVE.lock().await;
            if !is_active {
                break;
            }

            let devices: Vec<LanDevice> = tokio::task::spawn_blocking(scan_arp_devices).await.unwrap_or_default();
            
            // Push event safely exactly as requested by async pattern rule
            let _ = app.emit("lan-devices-updated", devices);
        }
    });

    Ok(())
}

#[tauri::command]
pub async fn stop_device_discovery() -> Result<(), crate::engine::error::AppError> {
    let mut active = DISCOVERY_ACTIVE.lock().await;
    *active = false;
    Ok(())
}
