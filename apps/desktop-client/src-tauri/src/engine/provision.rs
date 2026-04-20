use crate::engine::error::AppError;
use std::fs;
use std::path::Path;
use std::path::PathBuf;
use tauri::path::BaseDirectory;
use tauri::AppHandle;
use tauri::Manager;

// Note: For production we would dynamically determine this or read from an API
const SING_BOX_VERSION: &str = "1.13.8";

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

#[cfg(target_os = "windows")]
const SING_BOX_SUPPORT_FILES: &[&str] = &["libcronet.dll"];
#[cfg(target_os = "linux")]
const SING_BOX_SUPPORT_FILES: &[&str] = &["libcronet.so"];
#[cfg(target_os = "macos")]
const SING_BOX_SUPPORT_FILES: &[&str] = &["libcronet.dylib"];
#[cfg(not(any(target_os = "windows", target_os = "linux", target_os = "macos")))]
const SING_BOX_SUPPORT_FILES: &[&str] = &[];

const BUNDLED_RUNTIME_RESOURCE_ROOT: &str = "resources/runtime";

async fn read_binary_version(
    bin_path: &Path,
    binary_name: &str,
) -> Result<Option<String>, AppError> {
    if !bin_path.exists() {
        return Ok(None);
    }

    let bin_path = bin_path.to_path_buf();
    let binary_name = binary_name.to_string();

    let output = tokio::task::spawn_blocking(move || {
        let mut command = std::process::Command::new(&bin_path);
        command.arg("version");

        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;

            const CREATE_NO_WINDOW: u32 = 0x08000000;
            command.creation_flags(CREATE_NO_WINDOW);
        }

        command.output().map_err(|error| {
            AppError::System(format!(
                "Failed to execute {binary_name} version command: {error}"
            ))
        })
    })
    .await
    .map_err(|error| AppError::System(error.to_string()))??;

    if !output.status.success() {
        return Ok(None);
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let version = stdout
        .lines()
        .next()
        .and_then(|line| line.split_whitespace().last())
        .map(str::to_string);

    Ok(version)
}

fn sing_box_support_files_present(bin_dir: &Path) -> bool {
    SING_BOX_SUPPORT_FILES
        .iter()
        .all(|file_name| bin_dir.join(file_name).exists())
}

fn extract_release_archive_entry(
    out_path: &Path,
    reader: &mut dyn std::io::Read,
) -> Result<(), AppError> {
    let mut outfile = fs::File::create(out_path)?;
    std::io::copy(reader, &mut outfile)?;

    apply_runtime_permissions(out_path)?;

    Ok(())
}

fn apply_runtime_permissions(_out_path: &Path) -> Result<(), AppError> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mut perms = fs::metadata(_out_path)?.permissions();
        if _out_path
            .file_name()
            .and_then(|name| name.to_str())
            .is_some_and(|name| {
                name == "sing-box" || name.ends_with(".so") || name.ends_with(".dylib")
            })
        {
            perms.set_mode(0o755);
            fs::set_permissions(_out_path, perms)?;
        }
    }

    Ok(())
}

fn release_member_relative_path(path: &Path, release_folder: &str) -> Option<PathBuf> {
    let mut components = path.components();
    let folder_component = components.next()?.as_os_str().to_str()?;
    if folder_component != release_folder {
        return None;
    }

    let file_component = components.next()?.as_os_str().to_str()?;
    if file_component.is_empty() || components.next().is_some() {
        return None;
    }

    Some(PathBuf::from(file_component))
}

fn bundled_runtime_resource_path(target: &str, file_name: &str) -> PathBuf {
    PathBuf::from(BUNDLED_RUNTIME_RESOURCE_ROOT)
        .join(target)
        .join(file_name)
}

async fn copy_bundled_runtime_file(
    app_handle: &AppHandle,
    target: &str,
    file_name: &str,
    destination: PathBuf,
) -> Result<bool, AppError> {
    let resource_path = app_handle
        .path()
        .resolve(
            bundled_runtime_resource_path(target, file_name),
            BaseDirectory::Resource,
        )
        .map_err(|error| {
            AppError::System(format!(
                "Failed to resolve bundled runtime resource {file_name}: {error}"
            ))
        })?;

    if !resource_path.exists() {
        return Ok(false);
    }

    tokio::task::spawn_blocking(move || -> Result<(), AppError> {
        if let Some(parent) = destination.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::copy(&resource_path, &destination)?;
        apply_runtime_permissions(&destination)?;
        Ok(())
    })
    .await
    .map_err(|error| AppError::System(error.to_string()))??;

    Ok(true)
}

async fn provision_bundled_runtime_files(
    app_handle: &AppHandle,
    target: &str,
    files: &[&str],
    bin_dir: &Path,
) -> Result<bool, AppError> {
    let mut copied_any = false;

    for file_name in files {
        let copied =
            copy_bundled_runtime_file(app_handle, target, file_name, bin_dir.join(file_name))
                .await?;

        if !copied {
            return Ok(false);
        }

        copied_any = true;
    }

    Ok(copied_any)
}

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
        let installed_version = read_binary_version(&bin_path, "sing-box").await?;
        let support_files_ready = sing_box_support_files_present(&bin_dir);
        if installed_version.as_deref() == Some(SING_BOX_VERSION) && support_files_ready {
            println!("Sing-box {} already provisioned.", SING_BOX_VERSION);
            return Ok(bin_path);
        }

        println!(
            "Refreshing Sing-box runtime. Installed version: {:?}, expected: {}, support files ready: {}",
            installed_version,
            SING_BOX_VERSION,
            support_files_ready
        );

        let _ = tokio::fs::remove_file(&bin_path_sync).await;
        for file_name in SING_BOX_SUPPORT_FILES {
            let _ = tokio::fs::remove_file(bin_dir.join(file_name)).await;
        }
    }

    let target = get_target();
    if target == "unknown" {
        return Err(AppError::System(
            "Unsupported OS/Architecture combination for automatic Sing-box download.".to_string(),
        ));
    }

    let mut bundled_files = Vec::with_capacity(1 + SING_BOX_SUPPORT_FILES.len());
    bundled_files.push(bin_name);
    bundled_files.extend(SING_BOX_SUPPORT_FILES.iter().copied());

    if provision_bundled_runtime_files(app_handle, target, &bundled_files, &bin_dir).await? {
        let installed_version = read_binary_version(&bin_path_sync, "sing-box").await?;
        let support_files_ready = sing_box_support_files_present(&bin_dir);
        if installed_version.as_deref() == Some(SING_BOX_VERSION) && support_files_ready {
            println!(
                "Sing-box {} provisioned from bundled resources.",
                SING_BOX_VERSION
            );
            return Ok(bin_path_sync);
        }

        let _ = tokio::fs::remove_file(&bin_path_sync).await;
        for file_name in SING_BOX_SUPPORT_FILES {
            let _ = tokio::fs::remove_file(bin_dir.join(file_name)).await;
        }
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
            let mut extracted_entries = 0usize;

            for i in 0..archive.len() {
                let mut file = archive.by_index(i)?;
                let outpath = match file.enclosed_name() {
                    Some(path) => path.to_owned(),
                    None => continue,
                };

                if file.name().ends_with('/') {
                    continue;
                }

                let relative_path = match release_member_relative_path(&outpath, &release_folder) {
                    Some(path) => path,
                    None => continue,
                };

                let destination = bin_dir.join(relative_path);
                extract_release_archive_entry(&destination, &mut file)?;
                extracted_entries += 1;
                if destination == bin_path_sync {
                    println!("Extracted Sing-box binary to {}", destination.display());
                }
            }

            if extracted_entries == 0 {
                return Err(AppError::System(format!(
                    "Failed to extract Sing-box archive contents from {}",
                    archive_path.display()
                )));
            }
        } else {
            let tar_gz = fs::File::open(&archive_path)?;
            let tar = flate2::read::GzDecoder::new(tar_gz);
            let mut archive = tar::Archive::new(tar);
            let mut extracted_entries = 0usize;

            for file in archive.entries()? {
                let mut file = file?;
                let path = file.path()?.into_owned();
                let relative_path = match release_member_relative_path(&path, &release_folder) {
                    Some(path) => path,
                    None => continue,
                };

                let destination = bin_dir.join(relative_path);
                extract_release_archive_entry(&destination, &mut file)?;
                extracted_entries += 1;
            }

            if extracted_entries == 0 {
                return Err(AppError::System(format!(
                    "Failed to extract Sing-box archive contents from {}",
                    archive_path.display()
                )));
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

    if copy_bundled_runtime_file(app_handle, get_target(), bin_name, bin_path_sync.clone()).await? {
        println!("Xray {} provisioned from bundled resources.", XRAY_VERSION);
        return Ok(bin_path_sync);
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
    let geosite_url =
        "https://github.com/SagerNet/sing-geosite/releases/latest/download/geosite.db";

    let client = reqwest::Client::new();

    for (url, filename) in [(geoip_url, "geoip.db"), (geosite_url, "geosite.db")] {
        let dest = bin_dir.join(filename);
        let tmp_dest = bin_dir.join(format!("{}.tmp", filename));

        let response = client
            .get(url)
            .send()
            .await
            .map_err(|e| AppError::System(e.to_string()))?;
        if response.status().is_success() {
            let bytes = response
                .bytes()
                .await
                .map_err(|e| AppError::System(e.to_string()))?;
            tokio::fs::write(&tmp_dest, bytes)
                .await
                .map_err(|e| AppError::System(e.to_string()))?;
            tokio::fs::rename(&tmp_dest, &dest)
                .await
                .map_err(|e| AppError::System(e.to_string()))?;
        } else {
            return Err(AppError::System(format!(
                "Failed to download {}: {}",
                filename,
                response.status()
            )));
        }
    }

    Ok(())
}

pub async fn check_pqc_support(app_handle: &AppHandle) -> Result<(), AppError> {
    let bin_path = ensure_sing_box_binary(app_handle).await?;

    // Check version
    let version_str = read_binary_version(&bin_path, "sing-box")
        .await?
        .unwrap_or_default();

    // sing-box version output typically starts with "sing-box version 1.11.4"
    let semver_parts: Vec<&str> = version_str.split('.').collect();
    if semver_parts.len() >= 2 {
        if let (Ok(major), Ok(minor)) = (
            semver_parts[0].parse::<u32>(),
            semver_parts[1].parse::<u32>(),
        ) {
            if major == 1 && minor < 9 {
                return Err(AppError::UnsupportedCoreVersion(
                    "Sing-box core is older than 1.9.0 and does not support ML-KEM/Kyber Post-Quantum Cryptography. Please update your core.".to_string()
                ));
            }
        }
    }

    Ok(())
}
