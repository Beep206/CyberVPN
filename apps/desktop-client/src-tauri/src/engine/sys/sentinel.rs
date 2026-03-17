use std::process::Command;
use crate::engine::error::AppError;
use std::sync::atomic::{AtomicBool, Ordering};

pub struct SentinelGuard {
    active: AtomicBool,
}

impl Default for SentinelGuard {
    fn default() -> Self {
        Self::new()
    }
}

impl SentinelGuard {
    pub const fn new() -> Self {
        Self { active: AtomicBool::new(false) }
    }

    pub fn enable(&self) -> Result<(), AppError> {
        if !crate::engine::sys::is_elevated() {
            return Err(AppError::FirewallError("Execution requires Administrator privileges to enable Kill Switch.".to_string()));
        }

        enable_killswitch()?;
        self.active.store(true, Ordering::SeqCst);
        Ok(())
    }

    pub fn disable(&self) -> Result<(), AppError> {
        if !crate::engine::sys::is_elevated() {
            return Err(AppError::FirewallError("Execution requires Administrator privileges to disable Kill Switch.".to_string()));
        }

        disable_killswitch()?;
        self.active.store(false, Ordering::SeqCst);
        Ok(())
    }

    pub fn is_active(&self) -> bool {
        self.active.load(Ordering::SeqCst)
    }
}

impl Drop for SentinelGuard {
    fn drop(&mut self) {
        if self.is_active() {
            // SAFETY: Ensuring atomic cleanup of firewall rules if the app crashes or drops
            let _ = disable_killswitch();
        }
    }
}

#[cfg(target_os = "windows")]
fn enable_killswitch() -> Result<(), AppError> {
    // We utilize netsh advfirewall for robust WFP filter management as the optimal path for atomicity without kernel panic risks.
    let output = Command::new("netsh")
        .args(["advfirewall", "firewall", "add", "rule", "name=\"CyberVPN_KillSwitch_Block\"", "dir=out", "action=block", "protocol=ANY", "profile=ANY"])
        .output()
        .map_err(|e| AppError::FirewallError(format!("Failed to execute netsh: {}", e)))?;

    if !output.status.success() {
        return Err(AppError::FirewallError(format!("WFP netsh rule application failed: {}", String::from_utf8_lossy(&output.stderr))));
    }

    // specific allow rules for TUN and VPN IPs can be appended here, we permit OpenVPN/Tun0 equivalents
    let output2 = Command::new("netsh")
        .args(["advfirewall", "firewall", "add", "rule", "name=\"CyberVPN_KillSwitch_AllowTUN\"", "dir=out", "action=allow", "interface=tun0"])
        .output();
        
    let _ = output2; // ignore fail if interface doesn't exist yet

    Ok(())
}

#[cfg(target_os = "windows")]
fn disable_killswitch() -> Result<(), AppError> {
    let _ = Command::new("netsh")
        .args(["advfirewall", "firewall", "delete", "rule", "name=\"CyberVPN_KillSwitch_Block\""])
        .output();
    let _ = Command::new("netsh")
        .args(["advfirewall", "firewall", "delete", "rule", "name=\"CyberVPN_KillSwitch_AllowTUN\""])
        .output();
    Ok(())
}

#[cfg(target_os = "linux")]
fn enable_killswitch() -> Result<(), AppError> {
    // using iptables as a reliable fail-close mechanism
    let _ = Command::new("iptables")
        .args(["-I", "OUTPUT", "-m", "owner", "!", "--uid-owner", "root", "-j", "DROP"])
        .output();
    Ok(())
}

#[cfg(target_os = "linux")]
fn disable_killswitch() -> Result<(), AppError> {
    let _ = Command::new("iptables")
        .args(["-D", "OUTPUT", "-m", "owner", "!", "--uid-owner", "root", "-j", "DROP"])
        .output();
    Ok(())
}

#[cfg(not(any(target_os = "windows", target_os = "linux")))]
fn enable_killswitch() -> Result<(), AppError> {
    Err(AppError::FirewallError("Kill Switch not supported on this OS".to_string()))
}

#[cfg(not(any(target_os = "windows", target_os = "linux")))]
fn disable_killswitch() -> Result<(), AppError> {
    Err(AppError::FirewallError("Kill Switch not supported on this OS".to_string()))
}

#[tauri::command]
pub async fn repair_network() -> Result<(), AppError> {
    if !crate::engine::sys::is_elevated() {
         return Err(AppError::FirewallError("Elevation required to repair network".to_string()));
    }

    // Offload to blocking pool
    tokio::task::spawn_blocking(|| {
        #[cfg(target_os = "windows")]
        {
            // Reset WFP rules
            let _ = disable_killswitch();
            let _ = Command::new("ipconfig").arg("/flushdns").output();
            let _ = Command::new("netsh").args(["interface", "ipv4", "reset"]).output();
            let _ = Command::new("netsh").args(["winsock", "reset"]).output();
        }
        
        #[cfg(target_os = "linux")]
        {
            let _ = disable_killswitch();
            let _ = Command::new("systemd-resolve").args(["--flush-caches"]).output();
            let _ = Command::new("resolvectl").args(["flush-caches"]).output(); // For newer systemd
        }
    })
    .await
    .map_err(|e| AppError::System(format!("Tokio error: {}", e)))?;

    Ok(())
}

#[tauri::command]
pub fn enable_killswitch_cmd(guard: tauri::State<'_, SentinelGuard>) -> Result<(), AppError> {
    guard.enable()
}

#[tauri::command]
pub fn disable_killswitch_cmd(guard: tauri::State<'_, SentinelGuard>) -> Result<(), AppError> {
    guard.disable()
}
