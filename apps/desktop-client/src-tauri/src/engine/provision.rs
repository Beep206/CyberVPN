use crate::engine::error::AppError;
use std::fs;
use std::path::PathBuf;
use tauri::AppHandle;

// Note: For production we would dynamically determine this or read from an API
const SING_BOX_VERSION: &str = "1.11.4";

fn get_target() -> &'static str {
    #[cfg(all(target_os = "linux", target_arch = "x86_64"))]
    return "linux-amd64";
    #[cfg(all(target_os = "linux", target_arch = "aarch64"))]
    return "linux-arm64";
    #[cfg(all(target_os = "windows", target_arch = "x86_64"))]
    return "windows-amd64";
    #[cfg(all(target_os = "windows", target_arch = "aarch64"))]
    return "windows-arm64";
    #[cfg(all(target_os = "macos", target_arch = "x86_64"))]
    return "darwin-amd64";
    #[cfg(all(target_os = "macos", target_arch = "aarch64"))]
    return "darwin-arm64";

    #[allow(unreachable_code)]
    "unknown" // fallback
}

const XRAY_VERSION: &str = "1.8.24";

fn get_xray_target_name() -> &'static str {
    #[cfg(all(target_os = "linux", target_arch = "x86_64"))]
    return "linux-64";
    #[cfg(all(target_os = "linux", target_arch = "aarch64"))]
    return "linux-arm64-v8a";
    #[cfg(all(target_os = "windows", target_arch = "x86_64"))]
    return "windows-64";
    #[cfg(all(target_os = "windows", target_arch = "aarch64"))]
    return "windows-arm64-v8a";
    #[cfg(all(target_os = "macos", target_arch = "x86_64"))]
    return "macos-64";
    #[cfg(all(target_os = "macos", target_arch = "aarch64"))]
    return "macos-arm64-v8a";

    #[allow(unreachable_code)]
    "unknown"
}

pub async fn ensure_sing_box_binary(app_handle: &AppHandle) -> Result<PathBuf, AppError> {
    let app_dir = crate::engine::store::get_app_dir(app_handle)?;

    let bin_dir = app_dir.join("bin");

    if !bin_dir.exists() {
        tokio::task::spawn_blocking({
            let bin_dir = bin_dir.clone();
            move || fs::create_dir_all(&bin_dir)
        })
        .await
        .map_err(|e| AppError::System(e.to_string()))??;
    }

    #[cfg(target_os = "windows")]
    let bin_name = "sing-box.exe";
    #[cfg(not(target_os = "windows"))]
    let bin_name = "sing-box";

    let bin_path_sync = bin_dir.join(bin_name);
    let bin_path = bin_path_sync.clone();

    if bin_path.exists() {
        println!("Sing-box binary found at: {}", bin_path.display());
        // For production: verify binary hash or version string here
        return Ok(bin_path);
    }

    let target = get_target();
    if target == "unknown" {
        return Err(AppError::System(
            "Unsupported OS/Architecture combination for automatic Sing-box download.".to_string(),
        ));
    }

    println!(
        "Downloading Sing-box {} for {}...",
        SING_BOX_VERSION, target
    );

    let ext = if cfg!(target_os = "windows") {
        "zip"
    } else {
        "tar.gz"
    };
    let release_folder = format!("sing-box-{}-{}", SING_BOX_VERSION, target);
    let filename = format!("{}.{}", release_folder, ext);
    let url = format!(
        "https://github.com/SagerNet/sing-box/releases/download/v{}/{}",
        SING_BOX_VERSION, filename
    );

    let archive_path = app_dir.join(&filename);

    let client = reqwest::Client::new();
    let response = client.get(&url).send().await?;

    if !response.status().is_success() {
        return Err(AppError::System(format!(
            "Download failed with status: {}",
            response.status()
        )));
    }

    let bytes = response.bytes().await?;

    let bin_path_result = tokio::task::spawn_blocking(move || -> Result<PathBuf, AppError> {
        fs::write(&archive_path, bytes)?;

        println!("Extracting archive...");

        if cfg!(target_os = "windows") {
            let file = fs::File::open(&archive_path)?;
            let mut archive = zip::ZipArchive::new(file)?;

            for i in 0..archive.len() {
                let mut file = archive.by_index(i)?;
                let _outpath = match file.enclosed_name() {
                    Some(path) => path.to_owned(),
                    None => continue,
                };

                if file.name().ends_with('/') {
                    continue;
                }

                // check if the file is the main executable
                if file.name().ends_with(bin_name) {
                    let mut outfile = fs::File::create(&bin_path_sync)?;
                    std::io::copy(&mut file, &mut outfile)?;
                    break;
                }
            }
        } else {
            let tar_gz = fs::File::open(&archive_path)?;
            let tar = flate2::read::GzDecoder::new(tar_gz);
            let mut archive = tar::Archive::new(tar);

            for file in archive.entries()? {
                let mut file = file?;
                let path = file.path()?.into_owned();

                // Expected structure inside tar: sing-box-1.11.4-linux-amd64/sing-box
                if path.ends_with(bin_name) {
                    file.unpack(&bin_path_sync)?;

                    // Allow execute
                    #[cfg(unix)]
                    {
                        use std::os::unix::fs::PermissionsExt;
                        let mut perms = fs::metadata(&bin_path_sync)?.permissions();
                        perms.set_mode(0o755);
                        fs::set_permissions(&bin_path_sync, perms)?;
                    }
                    break;
                }
            }
        }

        // Cleanup archive
        let _ = fs::remove_file(&archive_path);

        if bin_path_sync.exists() {
            println!("Sing-box successfully provisioned.");
            Ok(bin_path_sync)
        } else {
            Err(AppError::System(
                "Failed to extract binary from archive".to_string(),
            ))
        }
    })
    .await
    .map_err(|e| AppError::System(e.to_string()))??;

    Ok(bin_path_result)
}

pub async fn ensure_xray_binary(app_handle: &AppHandle) -> Result<PathBuf, AppError> {
    let app_dir = crate::engine::store::get_app_dir(app_handle)?;
    let bin_dir = app_dir.join("bin");

    if !bin_dir.exists() {
        tokio::fs::create_dir_all(&bin_dir)
            .await
            .map_err(|e| AppError::System(e.to_string()))?;
    }

    #[cfg(target_os = "windows")]
    let bin_name = "xray.exe";
    #[cfg(not(target_os = "windows"))]
    let bin_name = "xray";

    let bin_path_sync = bin_dir.join(bin_name);

    if bin_path_sync.exists() {
        return Ok(bin_path_sync);
    }

    let target = get_xray_target_name();
    if target == "unknown" {
        return Err(AppError::System(
            "Unsupported platform for Xray".to_string(),
        ));
    }

    let filename = format!("Xray-{}.zip", target);
    let url = format!(
        "https://github.com/XTLS/Xray-core/releases/download/v{}/{}",
        XRAY_VERSION, filename
    );

    let archive_path = app_dir.join(&filename);

    let client = reqwest::Client::new();
    let response = client.get(&url).send().await?;

    if !response.status().is_success() {
        return Err(AppError::System(format!(
            "Download failed: {}",
            response.status()
        )));
    }

    let bytes = response.bytes().await?;

    let bin_path_result = tokio::task::spawn_blocking(move || -> Result<PathBuf, AppError> {
        std::fs::write(&archive_path, bytes)?;

        let file = std::fs::File::open(&archive_path)?;
        let mut archive = zip::ZipArchive::new(file)?;

        for i in 0..archive.len() {
            let mut file = archive.by_index(i)?;
            if file.name().ends_with("/") {
                continue;
            }

            if file.name() == bin_name || file.name().ends_with(&format!("/{}", bin_name)) {
                let mut outfile = std::fs::File::create(&bin_path_sync)?;
                std::io::copy(&mut file, &mut outfile)?;

                #[cfg(unix)]
                {
                    use std::os::unix::fs::PermissionsExt;
                    let mut perms = std::fs::metadata(&bin_path_sync)?.permissions();
                    perms.set_mode(0o755);
                    std::fs::set_permissions(&bin_path_sync, perms)?;
                }
                break;
            }
        }

        let _ = std::fs::remove_file(&archive_path);

        if bin_path_sync.exists() {
            Ok(bin_path_sync)
        } else {
            Err(AppError::System("Failed to extract Xray".to_string()))
        }
    })
    .await
    .map_err(|e| AppError::System(e.to_string()))??;

    Ok(bin_path_result)
}

pub async fn update_geo_assets(app_handle: &AppHandle) -> Result<(), AppError> {
    let app_dir = crate::engine::store::get_app_dir(app_handle)?;
    let bin_dir = app_dir.join("bin");
    
    if !bin_dir.exists() {
        tokio::fs::create_dir_all(&bin_dir)
            .await
            .map_err(|e| AppError::System(e.to_string()))?;
    }

    let geoip_url = "https://github.com/SagerNet/sing-geoip/releases/latest/download/geoip.db";
    let geosite_url = "https://github.com/SagerNet/sing-geosite/releases/latest/download/geosite.db";

    let client = reqwest::Client::new();
    
    for (url, filename) in [(geoip_url, "geoip.db"), (geosite_url, "geosite.db")] {
        let dest = bin_dir.join(filename);
        let tmp_dest = bin_dir.join(format!("{}.tmp", filename));
        
        let response = client.get(url).send().await.map_err(|e| AppError::System(e.to_string()))?;
        if response.status().is_success() {
            let bytes = response.bytes().await.map_err(|e| AppError::System(e.to_string()))?;
            tokio::fs::write(&tmp_dest, bytes).await.map_err(|e| AppError::System(e.to_string()))?;
            tokio::fs::rename(&tmp_dest, &dest).await.map_err(|e| AppError::System(e.to_string()))?;
        } else {
            return Err(AppError::System(format!("Failed to download {}: {}", filename, response.status())));
        }
    }

    Ok(())
}

pub async fn check_pqc_support(app_handle: &AppHandle) -> Result<(), AppError> {
    let bin_path = ensure_sing_box_binary(app_handle).await?;

    // Check version
    let output = tokio::process::Command::new(&bin_path)
        .arg("version")
        .output()
        .await
        .map_err(|e| AppError::System(format!("Failed to execute sing-box version: {}", e)))?;

    let version_str = String::from_utf8_lossy(&output.stdout);
    
    // sing-box version output typically starts with "sing-box version 1.11.4"
    if let Some(ver_line) = version_str.lines().next() {
        if ver_line.contains("version") {
            let parts: Vec<&str> = ver_line.split_whitespace().collect();
            if let Some(v_str) = parts.last() {
                // Parse version, e.g., "1.11.4"
                let semver_parts: Vec<&str> = v_str.split('.').collect();
                if semver_parts.len() >= 2 {
                    if let (Ok(major), Ok(minor)) = (semver_parts[0].parse::<u32>(), semver_parts[1].parse::<u32>()) {
                        if major == 1 && minor < 9 {
                            return Err(AppError::UnsupportedCoreVersion(
                                "Sing-box core is older than 1.9.0 and does not support ML-KEM/Kyber Post-Quantum Cryptography. Please update your core.".to_string()
                            ));
                        }
                    }
                }
            }
        }
    }

    Ok(())
}
