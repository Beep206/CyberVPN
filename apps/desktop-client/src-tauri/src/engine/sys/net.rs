use std::process::Command;
use crate::engine::error::AppError;

pub trait GatewayManager {
    fn enable_forwarding() -> Result<(), AppError>;
    fn disable_forwarding() -> Result<(), AppError>;
}

pub struct SystemGateway;

#[cfg(target_os = "windows")]
impl GatewayManager for SystemGateway {
    fn enable_forwarding() -> Result<(), AppError> {
        if !crate::engine::sys::is_elevated() {
            return Err(AppError::System("ELEVATION_REQUIRED".to_string()));
        }

        // Simplistic approach: Just enable routing for the whole TCP/IP stack (Routing and Remote Access)
        // More specific is `netsh interface ipv4 set interface "Wi-Fi" forwarding=enabled` but
        // enabling it globally via registry is often more robust for hotspot architectures.
        
        let output = Command::new("netsh")
            .args(["interface", "ipv4", "set", "interface", "\"Wi-Fi\"", "forwarding=enabled"])
            .output()
            .map_err(|e| AppError::System(format!("Failed to execute netsh: {}", e)))?;

        // Fallback for Ethernet if Wi-Fi isn't the primary adapter
        let _ = Command::new("netsh")
            .args(["interface", "ipv4", "set", "interface", "\"Ethernet\"", "forwarding=enabled"])
            .output();

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(AppError::System(format!("netsh error: {}", stderr)));
        }

        Ok(())
    }

    fn disable_forwarding() -> Result<(), AppError> {
        if !crate::engine::sys::is_elevated() {
            return Err(AppError::System("ELEVATION_REQUIRED".to_string()));
        }

        let _ = Command::new("netsh")
            .args(["interface", "ipv4", "set", "interface", "\"Wi-Fi\"", "forwarding=disabled"])
            .output();
            
        let _ = Command::new("netsh")
            .args(["interface", "ipv4", "set", "interface", "\"Ethernet\"", "forwarding=disabled"])
            .output();

        Ok(())
    }
}

#[cfg(target_os = "linux")]
impl GatewayManager for SystemGateway {
    fn enable_forwarding() -> Result<(), AppError> {
        if !crate::engine::sys::is_elevated() {
            return Err(AppError::System("ELEVATION_REQUIRED".to_string()));
        }

        let output = Command::new("sysctl")
            .args(["-w", "net.ipv4.ip_forward=1"])
            .output()
            .map_err(|e| AppError::System(format!("Failed to execute sysctl: {}", e)))?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(AppError::System(format!("sysctl error: {}", stderr)));
        }

        Ok(())
    }

    fn disable_forwarding() -> Result<(), AppError> {
        if !crate::engine::sys::is_elevated() {
            return Err(AppError::System("ELEVATION_REQUIRED".to_string()));
        }

        let output = Command::new("sysctl")
            .args(["-w", "net.ipv4.ip_forward=0"])
            .output()
            .map_err(|e| AppError::System(format!("Failed to execute sysctl: {}", e)))?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(AppError::System(format!("sysctl error: {}", stderr)));
        }

        Ok(())
    }
}

// Ensure the platform is covered
#[cfg(not(any(target_os = "windows", target_os = "linux")))]
impl GatewayManager for SystemGateway {
    fn enable_forwarding() -> Result<(), AppError> {
        Err(AppError::System("Hotspot routing not supported on this OS".to_string()))
    }
    
    fn disable_forwarding() -> Result<(), AppError> {
        Err(AppError::System("Hotspot routing not supported on this OS".to_string()))
    }
}

// --- LAN Discovery & IP Fetching ---

#[derive(serde::Serialize, Clone)]
pub struct LanInfo {
    pub ip: String,
    pub port: u16,
}

#[derive(serde::Serialize, Clone, Debug)]
pub struct LanDevice {
    pub ip: String,
    pub mac: String,
}

pub fn get_local_ip() -> Option<String> {
    let socket = std::net::UdpSocket::bind("0.0.0.0:0").ok()?;
    socket.connect("8.8.8.8:80").ok()?;
    socket.local_addr().ok().map(|addr| addr.ip().to_string())
}

#[tauri::command]
pub async fn get_lan_connection_info(app: tauri::AppHandle) -> Result<LanInfo, AppError> {
    // 1. Get the local IP
    let ip = get_local_ip().unwrap_or_else(|| "127.0.0.1".to_string());
    
    // 2. Get the current proxy port from store
    let port = tokio::task::spawn_blocking(move || {
        let store = crate::engine::store::load_store(&app)?;
        Ok::<u16, AppError>(store.local_socks_port.unwrap_or(2080))
    })
    .await
    .map_err(|e| AppError::System(format!("Tokio error: {}", e)))??;

    Ok(LanInfo { ip, port })
}

#[tauri::command]
pub async fn enable_lan_forwarding() -> Result<(), AppError> {
    tokio::task::spawn_blocking(SystemGateway::enable_forwarding)
        .await
        .map_err(|e| AppError::System(format!("Failed to spawn blocking netsh task: {}", e)))??;
    Ok(())
}

#[tauri::command]
pub async fn disable_lan_forwarding() -> Result<(), AppError> {
    tokio::task::spawn_blocking(SystemGateway::disable_forwarding)
        .await
        .map_err(|e| AppError::System(format!("Failed to spawn blocking netsh task: {}", e)))??;
    Ok(())
}

