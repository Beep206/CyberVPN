use crate::engine::error::AppError;
pub mod adblock;
pub mod apps;
pub mod diagnostics;
pub mod discovery;
pub mod net;
pub mod net_monitor;
pub mod remote_control;
pub mod sentinel;
pub mod stats;
pub mod sync;

#[cfg(target_os = "windows")]
use std::fs;
#[cfg(target_os = "windows")]
use tauri::path::BaseDirectory;
#[cfg(target_os = "windows")]
use tauri::Manager;
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
        let bin_dir = app_dir.join("bin");
        if !bin_dir.exists() {
            fs::create_dir_all(&bin_dir)?;
        }
        let dll_path = bin_dir.join("wintun.dll");

        let needs_copy = fs::metadata(&dll_path)
            .map(|metadata| metadata.is_file() && metadata.len() > 0)
            .unwrap_or(false)
            == false;

        if needs_copy {
            let resource_path = app
                .path()
                .resolve(
                    "resources/runtime/windows-amd64/wintun.dll",
                    BaseDirectory::Resource,
                )
                .map_err(|error| {
                    AppError::System(format!(
                        "Failed to resolve bundled wintun.dll resource: {error}"
                    ))
                })?;

            if !resource_path.exists() {
                return Err(AppError::System(
                    "Bundled wintun.dll resource is missing".to_string(),
                ));
            }

            println!("Wintun.dll not found. Extracting to {}", dll_path.display());
            fs::copy(resource_path, &dll_path)?;
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
) -> Result<usize, AppError> {
    use std::os::windows::ffi::OsStrExt;
    use windows::Win32::UI::Shell::{
        ShellExecuteExW, SEE_MASK_NOASYNC, SEE_MASK_NOCLOSEPROCESS, SEE_MASK_NO_CONSOLE,
        SHELLEXECUTEINFOW,
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
    args_string.push('"');
    let args: Vec<u16> = std::ffi::OsStr::new(&args_string)
        .encode_wide()
        .chain(std::iter::once(0))
        .collect();
    let directory: Vec<u16> = bin_path
        .parent()
        .unwrap_or_else(|| std::path::Path::new("."))
        .as_os_str()
        .encode_wide()
        .chain(std::iter::once(0))
        .collect();

    let mut info = SHELLEXECUTEINFOW {
        cbSize: std::mem::size_of::<SHELLEXECUTEINFOW>() as u32,
        fMask: SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NOASYNC | SEE_MASK_NO_CONSOLE,
        lpVerb: windows::core::PCWSTR::from_raw(verb.as_ptr()),
        lpFile: windows::core::PCWSTR::from_raw(file.as_ptr()),
        lpParameters: windows::core::PCWSTR::from_raw(args.as_ptr()),
        lpDirectory: windows::core::PCWSTR::from_raw(directory.as_ptr()),
        nShow: SW_HIDE.0,
        ..Default::default()
    };

    // SAFETY: We initialize a valid SHELLEXECUTEINFOW structure.
    // Pointers are valid and point to null-terminated UTF-16 strings within the same scope.
    let res = unsafe { ShellExecuteExW(&mut info) };
    if res.is_err() {
        return Err(AppError::System(
            "Failed to elevate process via UAC".to_string(),
        ));
    }

    if info.hProcess.0.is_null() {
        return Err(AppError::System(
            "UAC elevation succeeded but returned no process handle".to_string(),
        ));
    }

    Ok(info.hProcess.0 as usize)
}
