use crate::engine::error::AppError;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use tauri::{AppHandle, Emitter};
use tokio::time::{sleep, Duration};

#[derive(Clone, serde::Serialize, serde::Deserialize)]
pub struct NetworkProfile {
    pub auto_connect: bool,
    pub stealth_required: bool,
    pub kill_switch_required: bool,
    pub icon_type: String, // "home", "work", "coffee", "public"
}

// Emulate simple struct for the network change
#[derive(Clone, serde::Serialize)]
pub struct NetworkChangeEvent {
    pub ssid: String,
    pub is_trusted: bool, // Checked by frontend later or sent directly
}

pub fn get_current_ssid() -> Result<String, AppError> {
    #[cfg(target_os = "windows")]
    {
        use windows::Win32::Foundation::HANDLE;
        use windows::Win32::NetworkManagement::WiFi::{
            WlanCloseHandle, WlanEnumInterfaces, WlanFreeMemory, WlanOpenHandle,
            WlanQueryInterface, wlan_intf_opcode_current_connection, WLAN_API_VERSION_2_0,
            WLAN_CONNECTION_ATTRIBUTES, WLAN_INTERFACE_INFO_LIST,
        };

        // SAFETY: Direct memory-interaction bounded encapsulation via windows-rs.
        // Pointers evaluated for null. Memory is consistently freed via WlanFreeMemory.
        unsafe {
            let mut negotiated_version = 0u32;
            let mut handle = HANDLE::default();

            let status = WlanOpenHandle(
                WLAN_API_VERSION_2_0,
                None, // reserved
                &mut negotiated_version,
                &mut handle,
            );

            if status != 0 {
                return Err(AppError::System(
                    "Wi-Fi monitoring disabled. Please ensure the 'WLAN AutoConfig' service is running in Windows Services.".to_string(),
                ));
            }

            let mut p_interface_list: *mut WLAN_INTERFACE_INFO_LIST = std::ptr::null_mut();
            if WlanEnumInterfaces(handle, None, &mut p_interface_list) != 0 {
                let _ = WlanCloseHandle(handle, None);
                return Err(AppError::System("Failed to enumerate WLAN interfaces.".to_string()));
            }

            if p_interface_list.is_null() || (*p_interface_list).dwNumberOfItems == 0 {
                if !p_interface_list.is_null() {
                    WlanFreeMemory(p_interface_list as *mut core::ffi::c_void);
                }
                let _ = WlanCloseHandle(handle, None);
                return Ok("Wired Connection".to_string());
            }

            // We examine the first active Wi-Fi interface
            let interface_info = (*p_interface_list).InterfaceInfo[0];
            let guid = &interface_info.InterfaceGuid;

            let mut p_data: *mut core::ffi::c_void = std::ptr::null_mut();
            let mut data_size = 0u32;
            let mut opcode_value_type = 0u32;

            if WlanQueryInterface(
                handle,
                guid,
                wlan_intf_opcode_current_connection,
                None,
                &mut data_size,
                &mut p_data,
                Some(&mut opcode_value_type),
            ) == 0
            {
                if !p_data.is_null() {
                    let conn_attr = &*(p_data as *const WLAN_CONNECTION_ATTRIBUTES);
                    let len = conn_attr.wlanAssociationAttributes.dot11Ssid.uSSIDLength as usize;
                    if len > 0 && len <= 32 {
                        let ssid_bytes =
                            &conn_attr.wlanAssociationAttributes.dot11Ssid.ucSSID[0..len];
                        if let Ok(ssid) = String::from_utf8(ssid_bytes.to_vec()) {
                            WlanFreeMemory(p_data);
                            WlanFreeMemory(p_interface_list as *mut core::ffi::c_void);
                            let _ = WlanCloseHandle(handle, None);
                            return Ok(ssid);
                        }
                    }
                    WlanFreeMemory(p_data);
                }
            }

            WlanFreeMemory(p_interface_list as *mut core::ffi::c_void);
            let _ = WlanCloseHandle(handle, None);

            // Default fallback
            Ok("Wired Connection".to_string())
        }
    }

    #[cfg(unix)]
    {
        if cfg!(target_os = "macos") {
            if let Ok(output) = std::process::Command::new("/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport")
                .arg("-I")
                .output()
            {
                let stdout = String::from_utf8_lossy(&output.stdout);
                for line in stdout.lines() {
                    let trimmed = line.trim();
                    if trimmed.starts_with("SSID:") {
                        let ssid = trimmed["SSID:".len()..].trim();
                        if !ssid.is_empty() {
                            return Ok(ssid.to_string());
                        }
                    }
                }
            }
        } else {
            // Assume Linux
            if let Ok(output) = std::process::Command::new("nmcli")
                .args(&["-t", "-f", "active,ssid", "dev", "wifi"])
                .output()
            {
                let stdout = String::from_utf8_lossy(&output.stdout);
                for line in stdout.lines() {
                    if line.starts_with("yes:") {
                        let ssid = line["yes:".len()..].trim();
                        if !ssid.is_empty() {
                            return Ok(ssid.to_string());
                        }
                    }
                }
            }
            if let Ok(output) = std::process::Command::new("iwgetid").arg("-r").output() {
                let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
                if !stdout.is_empty() {
                    return Ok(stdout);
                }
            }
        }

        Ok("Wired Connection".to_string())
    }
}

pub fn start_network_monitor(app: AppHandle, cancellation_token: Arc<AtomicBool>) {
    tokio::spawn(async move {
        let mut last_stable_ssid = get_current_ssid().unwrap_or_else(|_| "Unknown".to_string());
        let mut transient_ssid = last_stable_ssid.clone();
        let mut transient_ticks = 0;

        loop {
            if cancellation_token.load(Ordering::Relaxed) {
                break;
            }

            // Polling every 10 seconds under stable conditions,
            // but if we detect a change, we poll faster to debounce.
            sleep(Duration::from_secs(if transient_ticks > 0 { 1 } else { 10 })).await;

            let current = get_current_ssid().unwrap_or_else(|_| "Unknown".to_string());

            if current != last_stable_ssid {
                if current != transient_ssid {
                    // Start of a change
                    transient_ssid = current.clone();
                    transient_ticks = 1;
                } else {
                    // Stability confirmation
                    transient_ticks += 1;
                    if transient_ticks >= 3 {
                        // Consistently new for 3 ticks (3 seconds) -> DEBOUNCED
                        last_stable_ssid = current.clone();
                        transient_ticks = 0;

                        // Emit the change
                        let _ = app.emit(
                            "network-changed",
                            NetworkChangeEvent {
                                ssid: last_stable_ssid.clone(),
                                is_trusted: false, // Calculated on front-end config
                            },
                        );
                    }
                }
            } else {
                transient_ticks = 0;
            }
        }
    });
}
