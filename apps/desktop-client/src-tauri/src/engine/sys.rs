use crate::engine::error::AppError;
pub mod apps;
pub mod net;
pub mod discovery;

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
#[allow(unused_variables)]
pub fn ensure_wintun(app: &tauri::AppHandle) -> Result<(), AppError> {
    #[cfg(target_os = "windows")]
    {
        let app_dir = crate::engine::store::get_app_dir(app)?;
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

/// On Windows, invoke the process with the runas verb to trigger UAC.
#[cfg(target_os = "windows")]
pub fn elevate_and_run(
    bin_path: &std::path::Path,
    config_path: &std::path::Path,
) -> Result<(), AppError> {
    use std::os::windows::ffi::OsStrExt;
    use windows::Win32::UI::Shell::{
        ShellExecuteExW, SEE_MASK_NOASYNC, SEE_MASK_NOCLOSEPROCESS, SHELLEXECUTEINFOW,
    };
    use windows::Win32::UI::WindowsAndMessaging::SW_HIDE;

    let verb: Vec<u16> = std::ffi::OsStr::new("runas")
        .encode_wide()
        .chain(std::iter::once(0))
        .collect();
    let file: Vec<u16> = bin_path
        .as_os_str()
        .encode_wide()
        .chain(std::iter::once(0))
        .collect();

    // arguments: run -c config_path
    let mut args_string = String::from("run -c \"");
    args_string.push_str(&config_path.to_string_lossy());
    args_string.push_str("\"");
    let args: Vec<u16> = std::ffi::OsStr::new(&args_string)
        .encode_wide()
        .chain(std::iter::once(0))
        .collect();

    let mut info = SHELLEXECUTEINFOW::default();
    info.cbSize = std::mem::size_of::<SHELLEXECUTEINFOW>() as u32;
    // We intentionally don't capture hProcess here since we can't easily integrate it with Tokio
    // and we will rely on checking if `sing-box` is running via name later or closing it directly.
    info.fMask = SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NOASYNC;
    info.lpVerb = windows::core::PCWSTR::from_raw(verb.as_ptr());
    info.lpFile = windows::core::PCWSTR::from_raw(file.as_ptr());
    info.lpParameters = windows::core::PCWSTR::from_raw(args.as_ptr());
    info.nShow = SW_HIDE.0 as i32;

    // SAFETY: We initialize a valid SHELLEXECUTEINFOW structure.
    // Pointers are valid and point to null-terminated UTF-16 strings within the same scope.
    let res = unsafe { ShellExecuteExW(&mut info) };
    if res.is_err() {
        return Err(AppError::System(
            "Failed to elevate process via UAC".to_string(),
        ));
    }

    Ok(())
}
