use crate::engine::error::AppError;
use std::fs;
use std::path::PathBuf;
use tauri::{AppHandle, Manager};

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

pub async fn ensure_sing_box_binary(app_handle: &AppHandle) -> Result<PathBuf, AppError> {
    let app_dir = app_handle
        .path()
        .app_data_dir()
        .map_err(|e| AppError::System(format!("Failed to get app_data_dir: {}", e)))?;

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
