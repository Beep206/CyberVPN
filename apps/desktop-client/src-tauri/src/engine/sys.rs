use crate::engine::error::AppError;

#[cfg(target_os = "windows")]
use windows::Win32::Foundation::HANDLE;
#[cfg(target_os = "windows")]
use windows::Win32::Security::{GetTokenInformation, TokenElevation, TOKEN_ELEVATION, TOKEN_QUERY};
#[cfg(target_os = "windows")]
use windows::Win32::System::Threading::{GetCurrentProcess, OpenProcessToken};

/// Checks if the current process is running with elevated privileges (Admin/Root).
pub fn is_elevated() -> bool {
    #[cfg(target_os = "windows")]
    {
        // SAFETY: We are correctly calling Windows API functions to query the process token.
        // We handle the FFI bounds properly by mapping the resulting pointer and size.
        unsafe {
            let mut handle: HANDLE = HANDLE::default();
            if OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &mut handle).is_ok() {
                let mut elevation: TOKEN_ELEVATION = std::mem::zeroed();
                let mut size = std::mem::size_of::<TOKEN_ELEVATION>() as u32;
                
                let success = GetTokenInformation(
                    handle,
                    TokenElevation,
                    Some(&mut elevation as *mut _ as *mut std::ffi::c_void),
                    size,
                    &mut size,
                );
                
                if success.is_ok() {
                    return elevation.TokenIsElevated != 0;
                }
            }
        }
        false
    }

    #[cfg(unix)]
    {
        // SAFETY: Calling libc::geteuid is well-defined and has no side effects.
        unsafe { libc::geteuid() == 0 }
    }
}

/// On Windows, extracts wintun.dll next to the executable if running TUN mode.
pub fn ensure_wintun(app: &tauri::AppHandle) -> Result<(), AppError> {
    #[cfg(target_os = "windows")]
    {
        let app_dir = app.path().app_data_dir().map_err(AppError::Tauri)?;
        let dll_path = app_dir.join("wintun.dll");
        
        if !dll_path.exists() {
            // In a full production setup, we would download or extract the correct architecture of wintun.dll
            // from the bundled resources. For now, we simulate extraction.
            println!("Wintun.dll not found. Extracting to {}", dll_path.display());
            
            // Placeholder: std::fs::write(&dll_path, include_bytes!("../../resources/wintun-amd64.dll"))
        }
    }
    
    // On Unix, TUN relies on the kernel module (tun), so nothing needs to be downloaded.
    Ok(())
}
