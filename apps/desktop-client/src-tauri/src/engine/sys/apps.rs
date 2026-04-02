use crate::engine::error::AppError;
use crate::ipc::models::AppInfo;

#[cfg(target_os = "windows")]
pub fn get_installed_apps_impl() -> Result<Vec<AppInfo>, AppError> {
    use std::collections::HashSet;
    use windows::core::HSTRING;
    use windows::Win32::System::Registry::{
        RegEnumKeyExW, RegOpenKeyExW, RegQueryInfoKeyW, HKEY, HKEY_CURRENT_USER,
        HKEY_LOCAL_MACHINE, KEY_READ,
    };

    let mut apps = Vec::new();
    let mut seen_paths = HashSet::new();

    let paths_to_scan = [
        (
            HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        ),
        (
            HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        ),
        (
            HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Uninstall",
        ),
    ];

    for (base_key, sub_key_str) in paths_to_scan {
        unsafe {
            let sub_key = HSTRING::from(sub_key_str);
            let mut hkey_opt: HKEY = HKEY::default();

            if RegOpenKeyExW(base_key, &sub_key, 0, KEY_READ, &mut hkey_opt).is_err() {
                continue;
            }

            let mut subkeys_count = 0;
            let mut max_subkey_len = 0;

            if RegQueryInfoKeyW(
                hkey_opt,
                windows::core::PWSTR::null(),
                None,
                None,
                Some(&mut subkeys_count),
                Some(&mut max_subkey_len),
                None,
                None,
                None,
                None,
                None,
                None,
            )
            .is_err()
            {
                let _ = windows::Win32::System::Registry::RegCloseKey(hkey_opt);
                continue;
            }

            for i in 0..subkeys_count {
                let mut name_buf = vec![0u16; (max_subkey_len + 1) as usize];
                let mut name_len = name_buf.len() as u32;

                if RegEnumKeyExW(
                    hkey_opt,
                    i,
                    windows::core::PWSTR(name_buf.as_mut_ptr()),
                    &mut name_len,
                    None,
                    windows::core::PWSTR::null(),
                    None,
                    None,
                )
                .is_ok()
                {
                    let key_name = String::from_utf16_lossy(&name_buf[..name_len as usize]);

                    let mut app_key_opt: HKEY = HKEY::default();
                    let app_sub_key_path = format!("{}\\{}", sub_key_str, key_name);
                    let app_sub_key = HSTRING::from(&app_sub_key_path);

                    if RegOpenKeyExW(base_key, &app_sub_key, 0, KEY_READ, &mut app_key_opt).is_ok()
                    {
                        let display_name = get_reg_string(app_key_opt, "DisplayName");
                        let display_icon = get_reg_string(app_key_opt, "DisplayIcon");
                        let install_location = get_reg_string(app_key_opt, "_InstallLocation");

                        let exec_path = extract_exec_path(&display_icon, &install_location);

                        if let (Some(name), Some(path)) = (display_name, exec_path) {
                            let path_lower = path.to_lowercase();
                            if path_lower.ends_with(".exe") && !seen_paths.contains(&path_lower) {
                                seen_paths.insert(path_lower);
                                let icon_base64 = if apps.len() < 50 {
                                    extract_icon_base64(&path)
                                } else {
                                    None
                                };

                                apps.push(AppInfo {
                                    name,
                                    package_name: std::path::Path::new(&path)
                                        .file_name()
                                        .unwrap_or_default()
                                        .to_string_lossy()
                                        .to_string(),
                                    icon_base64,
                                    exec_path: path,
                                });
                            }
                        }
                        let _ = windows::Win32::System::Registry::RegCloseKey(app_key_opt);
                    }
                }
            }
            let _ = windows::Win32::System::Registry::RegCloseKey(hkey_opt);
        }
    }

    apps.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase()));
    Ok(apps)
}

#[cfg(target_os = "windows")]
fn get_reg_string(
    hkey: windows::Win32::System::Registry::HKEY,
    value_name: &str,
) -> Option<String> {
    use windows::core::HSTRING;
    use windows::Win32::System::Registry::RegQueryValueExW;

    let mut data_len = 0;
    let val = HSTRING::from(value_name);

    unsafe {
        if RegQueryValueExW(hkey, &val, None, None, None, Some(&mut data_len)).is_err() {
            return None;
        }
    }

    if data_len == 0 {
        return None;
    }

    let mut buffer = vec![0u8; data_len as usize];
    unsafe {
        if RegQueryValueExW(
            hkey,
            &val,
            None,
            None,
            Some(buffer.as_mut_ptr()),
            Some(&mut data_len),
        )
        .is_err()
        {
            return None;
        }
    }

    let u16_slice: &[u16] = unsafe {
        std::slice::from_raw_parts(buffer.as_ptr() as *const u16, (data_len / 2) as usize)
    };
    let end = u16_slice
        .iter()
        .position(|&c| c == 0)
        .unwrap_or(u16_slice.len());
    let s = String::from_utf16_lossy(&u16_slice[..end])
        .trim_matches('"')
        .to_string();
    if s.is_empty() {
        None
    } else {
        Some(s)
    }
}

#[cfg(target_os = "windows")]
fn extract_exec_path(
    display_icon: &Option<String>,
    _install_location: &Option<String>,
) -> Option<String> {
    if let Some(mut icon_path) = display_icon.clone() {
        if let Some(idx) = icon_path.find(",0") {
            icon_path.truncate(idx);
        }
        let icon_path = icon_path.trim_matches('"').to_string();
        if icon_path.to_lowercase().ends_with(".exe") && std::path::Path::new(&icon_path).exists() {
            return Some(icon_path);
        }
    }
    None
}

#[cfg(target_os = "windows")]
fn extract_icon_base64(path: &str) -> Option<String> {
    use base64::{engine::general_purpose::STANDARD as BASE64, Engine as _};
    use image::{ImageFormat, RgbaImage};
    use std::io::Cursor;
    use windows::core::HSTRING;
    use windows::Win32::Graphics::Gdi::{
        DeleteObject, GetDC, GetDIBits, ReleaseDC, BITMAPINFO, BITMAPINFOHEADER, BI_RGB,
        DIB_RGB_COLORS,
    };
    use windows::Win32::UI::Shell::ExtractIconExW;
    use windows::Win32::UI::WindowsAndMessaging::{DestroyIcon, HICON};

    struct IconGuard(HICON);
    impl Drop for IconGuard {
        fn drop(&mut self) {
            unsafe {
                let _ = DestroyIcon(self.0);
            }
        }
    }

    struct GdiObjectGuard(windows::Win32::Graphics::Gdi::HGDIOBJ);
    impl Drop for GdiObjectGuard {
        fn drop(&mut self) {
            unsafe {
                if !self.0.is_invalid() {
                    let _ = DeleteObject(self.0);
                }
            }
        }
    }

    let path_h = HSTRING::from(path);
    let mut hicon_large: [HICON; 1] = [HICON::default()];

    unsafe {
        let result = ExtractIconExW(&path_h, 0, Some(hicon_large.as_mut_ptr()), None, 1);
        if result == 0 || hicon_large[0].is_invalid() {
            return None;
        }

        let hicon = hicon_large[0];
        let _icon_guard = IconGuard(hicon);

        let mut icon_info = windows::Win32::UI::WindowsAndMessaging::ICONINFO::default();
        if windows::Win32::UI::WindowsAndMessaging::GetIconInfo(hicon, &mut icon_info).is_err() {
            return None;
        }

        let _bmp_mask = GdiObjectGuard(icon_info.hbmMask.into());
        let _bmp_color = GdiObjectGuard(icon_info.hbmColor.into());

        let hbm = if !icon_info.hbmColor.is_invalid() {
            icon_info.hbmColor
        } else {
            icon_info.hbmMask
        };

        let mut bmp = windows::Win32::Graphics::Gdi::BITMAP::default();
        let query_res = windows::Win32::Graphics::Gdi::GetObjectW(
            hbm,
            std::mem::size_of::<windows::Win32::Graphics::Gdi::BITMAP>() as i32,
            Some(&mut bmp as *mut _ as *mut std::ffi::c_void),
        );

        if query_res == 0 || bmp.bmWidth <= 0 || bmp.bmHeight <= 0 {
            return None;
        }

        let width = bmp.bmWidth as u32;
        let height = bmp.bmHeight as u32;

        let hdc_screen = GetDC(None);
        struct DcGuard(windows::Win32::Graphics::Gdi::HDC);
        impl Drop for DcGuard {
            fn drop(&mut self) {
                unsafe {
                    let _ = ReleaseDC(None, self.0);
                }
            }
        }
        let _hdc_guard = DcGuard(hdc_screen);

        let mut bmi: BITMAPINFO = std::mem::zeroed();
        bmi.bmiHeader.biSize = std::mem::size_of::<BITMAPINFOHEADER>() as u32;
        bmi.bmiHeader.biWidth = width as i32;
        bmi.bmiHeader.biHeight = -(height as i32);
        bmi.bmiHeader.biPlanes = 1;
        bmi.bmiHeader.biBitCount = 32;
        bmi.bmiHeader.biCompression = BI_RGB.0;

        let mut pixels = vec![0u8; (width * height * 4) as usize];

        let get_dib_res = GetDIBits(
            hdc_screen,
            hbm,
            0,
            height,
            Some(pixels.as_mut_ptr() as *mut _),
            &mut bmi,
            DIB_RGB_COLORS,
        );

        if get_dib_res == 0 {
            return None;
        }

        for chunk in pixels.chunks_exact_mut(4) {
            let b = chunk[0];
            let r = chunk[2];
            chunk[0] = r;
            chunk[2] = b;

            if chunk[3] == 0 && (chunk[0] > 0 || chunk[1] > 0 || chunk[2] > 0) {
                chunk[3] = 255;
            }
        }

        let img = RgbaImage::from_raw(width, height, pixels)?;

        let mut buf = Cursor::new(Vec::new());
        if img.write_to(&mut buf, ImageFormat::Png).is_err() {
            return None;
        }

        Some(format!(
            "data:image/png;base64,{}",
            BASE64.encode(buf.into_inner())
        ))
    }
}

#[cfg(target_os = "linux")]
pub fn get_installed_apps_impl() -> Result<Vec<AppInfo>, AppError> {
    use std::fs;
    use std::path::PathBuf;

    let mut apps = Vec::new();
    let mut seen_packages = std::collections::HashSet::new();

    let mut directories = vec![PathBuf::from("/usr/share/applications")];
    if let Ok(home) = std::env::var("HOME") {
        directories.push(PathBuf::from(home).join(".local/share/applications"));
    }

    for dir in directories {
        if let Ok(entries) = fs::read_dir(dir) {
            for entry in entries.filter_map(|e| e.ok()) {
                let path = entry.path();
                if path.is_file() && path.extension().and_then(|s| s.to_str()) == Some("desktop") {
                    if let Ok(content) = fs::read_to_string(&path) {
                        let mut name = None;
                        let mut exec = None;

                        for line in content.lines() {
                            if line.starts_with("Name=") && name.is_none() {
                                name = Some(line["Name=".len()..].to_string());
                            } else if line.starts_with("Exec=") && exec.is_none() {
                                let exec_cmd = line["Exec=".len()..].to_string();
                                let mut parts = exec_cmd.split_whitespace();
                                if let Some(cmd) = parts.next() {
                                    exec = Some(cmd.to_string());
                                }
                            }
                        }

                        if let (Some(app_name), Some(app_exec)) = (name, exec) {
                            let package_name = path
                                .file_stem()
                                .unwrap_or_default()
                                .to_string_lossy()
                                .to_string();
                            if !seen_packages.contains(&package_name) {
                                seen_packages.insert(package_name.clone());
                                apps.push(AppInfo {
                                    name: app_name,
                                    package_name,
                                    exec_path: app_exec,
                                    icon_base64: None,
                                });
                            }
                        }
                    }
                }
            }
        }
    }

    apps.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase()));
    Ok(apps)
}

#[cfg(target_os = "macos")]
pub fn get_installed_apps_impl() -> Result<Vec<AppInfo>, AppError> {
    Ok(vec![])
}

pub async fn get_installed_apps() -> Result<Vec<AppInfo>, AppError> {
    tokio::task::spawn_blocking(get_installed_apps_impl)
        .await
        .map_err(|e| AppError::System(format!("Tokio spawn blocking failed: {}", e)))?
}
