use crate::engine::error::AppError;
use futures::StreamExt;
use sha2::{Digest, Sha256};
use std::fs;
use std::path::Path;
use std::path::PathBuf;
use std::time::Duration;
use tauri::path::BaseDirectory;
use tauri::AppHandle;
use tauri::Manager;

// Note: For production we would dynamically determine this or read from an API
const SING_BOX_VERSION: &str = "1.13.8";

fn sing_box_archive_sha256(target: &str) -> Option<&'static str> {
    match target {
        "windows-amd64" => Some("599b743e9618b38d16ae1af65b35ffa3afadcc531b5bd9fea616e644711be5b9"),
        "linux-amd64" => Some("aab8841979aba14ae4c4dc72c4a593be1a16da95e75d53b494ed718f0223370f"),
        "darwin-amd64" => Some("0db6aca503dcdd5a816e668669e79231f991cdbbd13fcbf6dd4f9bcb8a1c3b0e"),
        "darwin-arm64" => Some("e9e4c72a4a64c19d515b800b7191c50367522c8169654c569677b15873e08249"),
        _ => None,
    }
}

fn sing_box_archive_filename(target: &str) -> Option<String> {
    sing_box_archive_sha256(target)?;
    let extension = if target.starts_with("windows-") {
        "zip"
    } else {
        "tar.gz"
    };
    Some(format!("sing-box-{SING_BOX_VERSION}-{target}.{extension}"))
}

fn sing_box_runtime_file_sha256(target: &str, file_name: &str) -> Option<&'static str> {
    match (target, file_name) {
        ("windows-amd64", "sing-box.exe") => {
            Some("e4f0d76903dbec850121b20cd6cf917fa6c456a554c97fba53bd6cda7790fbd8")
        }
        ("windows-amd64", "libcronet.dll") => {
            Some("43e2e6c8bf0d29263fed11a7a11c108b671c741c54eb8ba9f5bc5370db8a2684")
        }
        ("linux-amd64", "sing-box") => {
            Some("83b7846dc85ffb1f64c1d14f63eba2fcf3d3b19ed4049c2fcd291ed6c29b5cc2")
        }
        ("linux-amd64", "libcronet.so") => {
            Some("55c35e93dff3ab2174b9a338adbc99f5bd1dc54347f8aa605f44f129db30dd80")
        }
        ("darwin-amd64", "sing-box") => {
            Some("21a31b26bbb9d9299380083aaab59c949006130720fdc44db940c32f6493f0b6")
        }
        ("darwin-arm64", "sing-box") => {
            Some("17e6a7f417a2bbff3693940c024856c3fc88fe5fc3acbc90146a7776d4211909")
        }
        _ => None,
    }
}

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

const XRAY_VERSION: &str = "26.7.28";

fn xray_archive_sha256(target: &str) -> Option<&'static str> {
    match target {
        "windows-64" => Some("c7172078fca4711bcd92a4774dcd1822544579c58816197575c47533317fd8d1"),
        "linux-64" => Some("8195d909f1109b8f3d99eefe401a3c451d7bf4af71f24d3815420f77e5dd2a40"),
        "macos-64" => Some("812f7d9de6d3506795eabda2f6928ba301c632c3fe6fa39c52ea8e0ed9e4e244"),
        "macos-arm64-v8a" => {
            Some("9b99a351febe31b7e0c7f22deeb1577a1da0b98aaa51aec7fd17832e68cf63d6")
        }
        _ => None,
    }
}

fn xray_archive_filename(target: &str) -> Option<String> {
    xray_archive_sha256(target).map(|_| format!("Xray-{target}.zip"))
}

fn xray_runtime_sha256(target: &str) -> Option<&'static str> {
    match target {
        "windows-64" => Some("1d9674327972a21afd4c906a7a72bb0856935aa9e0227c87f34f03d11a88bddf"),
        "linux-64" => Some("64d46afb80adea1bf97a0d467e83f4a9ac1ebd0995891e84bca3f1a1d1affb1d"),
        "macos-64" => Some("38571e7799c0f34b1151fc2dfc40cfe570bec55ea59dd93dcee19d52648cea03"),
        "macos-arm64-v8a" => {
            Some("bd4154efa640c5b8e21f10b68afcc9177c4f1f543be3ec0485b10c499b2a4b27")
        }
        _ => None,
    }
}

fn sing_box_support_files(target: &str) -> &'static [&'static str] {
    match target {
        "windows-amd64" => &["libcronet.dll"],
        "linux-amd64" => &["libcronet.so"],
        "darwin-amd64" | "darwin-arm64" => &[],
        _ => &[],
    }
}

const BUNDLED_RUNTIME_RESOURCE_ROOT: &str = "resources/runtime";

const MAX_RUNTIME_ARCHIVE_BYTES: usize = 64 * 1024 * 1024;
const MAX_GEO_ASSET_BYTES: usize = 8 * 1024 * 1024;
const GEO_ASSET_LOCK_WAIT: Duration = Duration::from_secs(30);
const GEO_ASSET_LOCK_RETRY: Duration = Duration::from_millis(50);

// A desktop process has one authoritative app-data/bin directory. Serializing
// the complete download and pair replacement prevents one failed rollback from
// clobbering another concurrent update.
static GEO_ASSET_UPDATE_LOCK: tokio::sync::Mutex<()> = tokio::sync::Mutex::const_new(());

struct GeoAssetUpdateGuard {
    _process_guard: tokio::sync::MutexGuard<'static, ()>,
    _file_guard: fs::File,
}

fn acquire_geo_asset_file_lock_with_timeout(
    bin_dir: &Path,
    wait: Duration,
) -> Result<fs::File, AppError> {
    use std::fs::TryLockError;
    use std::time::Instant;

    fs::create_dir_all(bin_dir)?;
    let lock_path = bin_dir.join(".geo-assets-update.lock");
    let lock_file = fs::OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(false)
        .open(lock_path)?;
    let deadline = Instant::now() + wait;
    loop {
        match lock_file.try_lock() {
            Ok(()) => return Ok(lock_file),
            Err(TryLockError::WouldBlock) if Instant::now() < deadline => {
                std::thread::sleep(
                    GEO_ASSET_LOCK_RETRY.min(deadline.saturating_duration_since(Instant::now())),
                );
            }
            Err(TryLockError::WouldBlock) => {
                return Err(AppError::System(
                    "Timed out waiting for the Geo asset update lock".to_string(),
                ));
            }
            Err(TryLockError::Error(error)) => return Err(AppError::Io(error)),
        }
    }
}

async fn acquire_geo_asset_update_guard(bin_dir: &Path) -> Result<GeoAssetUpdateGuard, AppError> {
    let process_guard = GEO_ASSET_UPDATE_LOCK.lock().await;
    let lock_dir = bin_dir.to_path_buf();
    let file_guard = tokio::task::spawn_blocking(move || {
        acquire_geo_asset_file_lock_with_timeout(&lock_dir, GEO_ASSET_LOCK_WAIT)
    })
    .await
    .map_err(|error| AppError::System(error.to_string()))??;
    Ok(GeoAssetUpdateGuard {
        _process_guard: process_guard,
        _file_guard: file_guard,
    })
}

#[derive(Clone, Copy, Debug)]
struct GeoAssetSpec {
    filename: &'static str,
    release_tag: &'static str,
    sha256: &'static str,
    repository: &'static str,
}

impl GeoAssetSpec {
    fn download_url(self) -> String {
        format!(
            "https://github.com/{}/releases/download/{}/{}",
            self.repository, self.release_tag, self.filename
        )
    }
}

const GEO_ASSETS: [GeoAssetSpec; 2] = [
    GeoAssetSpec {
        filename: "geoip.db",
        release_tag: "20260812",
        sha256: "d8f4d22abee199b73c019df267e8dc649e868da3b130753640aa9b05d11040c0",
        repository: "SagerNet/sing-geoip",
    },
    GeoAssetSpec {
        filename: "geosite.db",
        release_tag: "20260831141734",
        sha256: "dfed5b0ca5a439bbb64561b5760434bd15ab10f9765f5e9cf7ba05d7d93205cb",
        repository: "SagerNet/sing-geosite",
    },
];

fn validate_download_content_length(
    label: &str,
    content_length: Option<u64>,
    maximum_bytes: usize,
) -> Result<(), AppError> {
    if content_length.is_some_and(|length| length > maximum_bytes as u64) {
        return Err(AppError::System(format!(
            "{label} exceeds the {maximum_bytes} byte download limit"
        )));
    }
    Ok(())
}

fn append_bounded_download_chunk(
    label: &str,
    body: &mut Vec<u8>,
    chunk: &[u8],
    maximum_bytes: usize,
) -> Result<(), AppError> {
    let next_length = body
        .len()
        .checked_add(chunk.len())
        .ok_or_else(|| AppError::System(format!("{label} is too large")))?;
    if next_length > maximum_bytes {
        return Err(AppError::System(format!(
            "{label} exceeds the {maximum_bytes} byte download limit"
        )));
    }
    body.extend_from_slice(chunk);
    Ok(())
}

async fn read_bounded_download(
    response: reqwest::Response,
    label: &str,
    maximum_bytes: usize,
) -> Result<Vec<u8>, AppError> {
    validate_download_content_length(label, response.content_length(), maximum_bytes)?;
    let mut body = Vec::with_capacity(
        response
            .content_length()
            .unwrap_or_default()
            .min(maximum_bytes as u64) as usize,
    );
    let mut stream = response.bytes_stream();
    while let Some(chunk) = stream.next().await {
        let chunk = chunk?;
        append_bounded_download_chunk(label, &mut body, &chunk, maximum_bytes)?;
    }
    Ok(body)
}

fn release_download_client(total_timeout: Duration) -> Result<reqwest::Client, AppError> {
    Ok(reqwest::Client::builder()
        .connect_timeout(Duration::from_secs(10))
        .timeout(total_timeout)
        .redirect(reqwest::redirect::Policy::limited(5))
        .user_agent("CyberVPN-desktop/0.1.5")
        .build()?)
}

fn verify_archive_sha256(
    runtime_name: &str,
    filename: &str,
    bytes: &[u8],
    expected_digest: Option<&str>,
) -> Result<(), AppError> {
    let Some(expected_digest) = expected_digest else {
        return Err(AppError::UnsupportedCoreVersion(format!(
            "No pinned archive digest is available for {runtime_name} ({filename}); refusing an unverified runtime download"
        )));
    };

    let actual_digest = format!("{:x}", Sha256::digest(bytes));
    if !actual_digest.eq_ignore_ascii_case(expected_digest) {
        return Err(AppError::System(format!(
            "{runtime_name} archive integrity check failed for {filename}"
        )));
    }

    Ok(())
}

fn file_sha256_matches(path: &Path, expected_digest: &str) -> Result<bool, AppError> {
    use std::io::Read;

    let mut file = fs::File::open(path)?;
    let mut digest = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let read = file.read(&mut buffer)?;
        if read == 0 {
            break;
        }
        digest.update(&buffer[..read]);
    }
    Ok(format!("{:x}", digest.finalize()).eq_ignore_ascii_case(expected_digest))
}

async fn runtime_file_matches_pin(
    path: PathBuf,
    expected_digest: Option<&'static str>,
) -> Result<bool, AppError> {
    let Some(expected_digest) = expected_digest else {
        return Ok(false);
    };
    if !path.exists() {
        return Ok(false);
    }
    tokio::task::spawn_blocking(move || file_sha256_matches(&path, expected_digest))
        .await
        .map_err(|error| AppError::System(error.to_string()))?
}

async fn sing_box_runtime_matches_pins(
    bin_dir: &Path,
    target: &str,
    bin_name: &str,
) -> Result<bool, AppError> {
    if !runtime_file_matches_pin(
        bin_dir.join(bin_name),
        sing_box_runtime_file_sha256(target, bin_name),
    )
    .await?
    {
        return Ok(false);
    }

    for file_name in sing_box_support_files(target) {
        if !runtime_file_matches_pin(
            bin_dir.join(file_name),
            sing_box_runtime_file_sha256(target, file_name),
        )
        .await?
        {
            return Ok(false);
        }
    }
    Ok(true)
}

async fn xray_runtime_matches_pin(bin_path: &Path, target: &str) -> Result<bool, AppError> {
    runtime_file_matches_pin(bin_path.to_path_buf(), xray_runtime_sha256(target)).await
}

fn parse_binary_version(output: &str, binary_name: &str) -> Option<String> {
    let tokens: Vec<&str> = output.split_whitespace().collect();
    match binary_name {
        "xray" => tokens
            .windows(2)
            .find(|pair| pair[0].eq_ignore_ascii_case("xray"))
            .map(|pair| pair[1].trim_start_matches('v').to_string()),
        "sing-box" => tokens
            .windows(2)
            .find(|pair| pair[0].eq_ignore_ascii_case("version"))
            .map(|pair| pair[1].trim_start_matches('v').to_string()),
        _ => None,
    }
}

async fn read_binary_version(
    bin_path: &Path,
    binary_name: &str,
) -> Result<Option<String>, AppError> {
    if !bin_path.exists() {
        return Ok(None);
    }

    let bin_path = bin_path.to_path_buf();
    let binary_name = binary_name.to_string();
    let command_binary_name = binary_name.clone();

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
                "Failed to execute {command_binary_name} version command: {error}"
            ))
        })
    })
    .await
    .map_err(|error| AppError::System(error.to_string()))??;

    if !output.status.success() {
        return Ok(None);
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    let version = parse_binary_version(
        if stdout.trim().is_empty() {
            stderr.as_ref()
        } else {
            stdout.as_ref()
        },
        &binary_name,
    );

    Ok(version)
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

    let target = get_target();
    if target == "unknown" {
        return Err(AppError::System(
            "Unsupported OS/Architecture combination for automatic Sing-box download.".to_string(),
        ));
    }
    let support_files = sing_box_support_files(target);

    if bin_path.exists() {
        let integrity_verified = sing_box_runtime_matches_pins(&bin_dir, target, bin_name).await?;
        let installed_version = if integrity_verified {
            read_binary_version(&bin_path, "sing-box").await?
        } else {
            None
        };
        if integrity_verified && installed_version.as_deref() == Some(SING_BOX_VERSION) {
            println!("Sing-box {} already provisioned.", SING_BOX_VERSION);
            return Ok(bin_path);
        }

        println!(
            "Refreshing Sing-box runtime. Integrity verified: {}, installed version: {:?}, expected: {}",
            integrity_verified,
            installed_version,
            SING_BOX_VERSION
        );

        let _ = tokio::fs::remove_file(&bin_path_sync).await;
        for file_name in support_files {
            let _ = tokio::fs::remove_file(bin_dir.join(file_name)).await;
        }
    }

    let mut bundled_files = Vec::with_capacity(1 + support_files.len());
    bundled_files.push(bin_name);
    bundled_files.extend(support_files.iter().copied());

    if provision_bundled_runtime_files(app_handle, target, &bundled_files, &bin_dir).await? {
        let integrity_verified = sing_box_runtime_matches_pins(&bin_dir, target, bin_name).await?;
        let installed_version = if integrity_verified {
            read_binary_version(&bin_path_sync, "sing-box").await?
        } else {
            None
        };
        if integrity_verified && installed_version.as_deref() == Some(SING_BOX_VERSION) {
            println!(
                "Sing-box {} provisioned from bundled resources.",
                SING_BOX_VERSION
            );
            return Ok(bin_path_sync);
        }

        let _ = tokio::fs::remove_file(&bin_path_sync).await;
        for file_name in support_files {
            let _ = tokio::fs::remove_file(bin_dir.join(file_name)).await;
        }
    }

    println!(
        "Downloading Sing-box {} for {}...",
        SING_BOX_VERSION, target
    );

    let release_folder = format!("sing-box-{}-{}", SING_BOX_VERSION, target);
    let filename = sing_box_archive_filename(target).ok_or_else(|| {
        AppError::UnsupportedCoreVersion(format!(
            "No pinned Sing-box release archive is available for target {target}"
        ))
    })?;
    let url = format!(
        "https://github.com/SagerNet/sing-box/releases/download/v{}/{}",
        SING_BOX_VERSION, filename
    );

    let archive_path = app_dir.join(&filename);

    let client = release_download_client(Duration::from_secs(180))?;
    let response = client.get(&url).send().await?;

    if !response.status().is_success() {
        return Err(AppError::System(format!(
            "Download failed with status: {}",
            response.status()
        )));
    }

    let bytes =
        read_bounded_download(response, "Sing-box archive", MAX_RUNTIME_ARCHIVE_BYTES).await?;
    verify_archive_sha256(
        "Sing-box",
        &filename,
        &bytes,
        sing_box_archive_sha256(target),
    )?;

    let extraction_bin_dir = bin_dir.clone();
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

                let destination = extraction_bin_dir.join(relative_path);
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

                let destination = extraction_bin_dir.join(relative_path);
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

    if !sing_box_runtime_matches_pins(&bin_dir, target, bin_name).await? {
        let _ = tokio::fs::remove_file(&bin_path_result).await;
        for file_name in support_files {
            let _ = tokio::fs::remove_file(bin_dir.join(file_name)).await;
        }
        return Err(AppError::System(
            "Extracted Sing-box runtime failed its pinned file integrity check".to_string(),
        ));
    }
    let installed_version = read_binary_version(&bin_path_result, "sing-box").await?;
    if installed_version.as_deref() != Some(SING_BOX_VERSION) {
        let _ = tokio::fs::remove_file(&bin_path_result).await;
        for file_name in support_files {
            let _ = tokio::fs::remove_file(bin_dir.join(file_name)).await;
        }
        return Err(AppError::UnsupportedCoreVersion(format!(
            "Downloaded Sing-box version {:?} does not match required {}",
            installed_version, SING_BOX_VERSION
        )));
    }

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

    let target = get_xray_target_name();
    if target == "unknown" {
        return Err(AppError::System(
            "Unsupported platform for Xray".to_string(),
        ));
    }

    if bin_path_sync.exists() {
        let integrity_verified = xray_runtime_matches_pin(&bin_path_sync, target).await?;
        let installed_version = if integrity_verified {
            read_binary_version(&bin_path_sync, "xray").await?
        } else {
            None
        };
        if integrity_verified && installed_version.as_deref() == Some(XRAY_VERSION) {
            println!("Xray {} already provisioned.", XRAY_VERSION);
            return Ok(bin_path_sync);
        }
        println!(
            "Refreshing Xray runtime. Integrity verified: {}, installed version: {:?}, expected: {}",
            integrity_verified, installed_version, XRAY_VERSION
        );
        tokio::fs::remove_file(&bin_path_sync)
            .await
            .map_err(|error| AppError::System(format!("Failed to replace Xray: {error}")))?;
    }

    if copy_bundled_runtime_file(app_handle, get_target(), bin_name, bin_path_sync.clone()).await? {
        let integrity_verified = xray_runtime_matches_pin(&bin_path_sync, target).await?;
        let installed_version = if integrity_verified {
            read_binary_version(&bin_path_sync, "xray").await?
        } else {
            None
        };
        if integrity_verified && installed_version.as_deref() == Some(XRAY_VERSION) {
            println!("Xray {} provisioned from bundled resources.", XRAY_VERSION);
            return Ok(bin_path_sync);
        }
        let _ = tokio::fs::remove_file(&bin_path_sync).await;
        println!(
            "Bundled Xray version {:?} did not match {}; downloading the pinned release.",
            installed_version, XRAY_VERSION
        );
    }

    let filename = xray_archive_filename(target).ok_or_else(|| {
        AppError::UnsupportedCoreVersion(format!(
            "No pinned Xray release archive is available for target {target}"
        ))
    })?;
    let url = format!(
        "https://github.com/XTLS/Xray-core/releases/download/v{}/{}",
        XRAY_VERSION, filename
    );

    let archive_path = app_dir.join(&filename);

    let client = release_download_client(Duration::from_secs(180))?;
    let response = client.get(&url).send().await?;

    if !response.status().is_success() {
        return Err(AppError::System(format!(
            "Download failed: {}",
            response.status()
        )));
    }

    let bytes = read_bounded_download(response, "Xray archive", MAX_RUNTIME_ARCHIVE_BYTES).await?;
    verify_archive_sha256("Xray", &filename, &bytes, xray_archive_sha256(target))?;

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

    if !xray_runtime_matches_pin(&bin_path_result, target).await? {
        let _ = tokio::fs::remove_file(&bin_path_result).await;
        return Err(AppError::System(
            "Extracted Xray runtime failed its pinned file integrity check".to_string(),
        ));
    }

    let installed_version = read_binary_version(&bin_path_result, "xray").await?;
    if installed_version.as_deref() != Some(XRAY_VERSION) {
        let _ = tokio::fs::remove_file(&bin_path_result).await;
        return Err(AppError::UnsupportedCoreVersion(format!(
            "Downloaded Xray version {:?} does not match required {}",
            installed_version, XRAY_VERSION
        )));
    }

    Ok(bin_path_result)
}

fn validate_geo_asset(spec: GeoAssetSpec, bytes: &[u8]) -> Result<(), AppError> {
    if bytes.len() > MAX_GEO_ASSET_BYTES {
        return Err(AppError::System(format!(
            "{} exceeds the {} byte download limit",
            spec.filename, MAX_GEO_ASSET_BYTES
        )));
    }

    let actual_digest = format!("{:x}", Sha256::digest(bytes));
    if !actual_digest.eq_ignore_ascii_case(spec.sha256) {
        return Err(AppError::System(format!(
            "{} failed its pinned integrity check",
            spec.filename
        )));
    }
    Ok(())
}

async fn download_geo_asset(
    client: &reqwest::Client,
    spec: GeoAssetSpec,
) -> Result<Vec<u8>, AppError> {
    let response = client.get(spec.download_url()).send().await?;
    if !response.status().is_success() {
        return Err(AppError::System(format!(
            "Failed to download {}: {}",
            spec.filename,
            response.status()
        )));
    }
    let bytes = read_bounded_download(response, spec.filename, MAX_GEO_ASSET_BYTES).await?;
    validate_geo_asset(spec, &bytes)?;
    Ok(bytes)
}

#[derive(Debug)]
struct GeoAssetInstallState {
    destination: PathBuf,
    staged: PathBuf,
    backup: PathBuf,
    backed_up: bool,
    installed: bool,
}

fn clean_staged_geo_assets(states: &[GeoAssetInstallState]) {
    for state in states {
        if state.staged.exists() {
            let _ = fs::remove_file(&state.staged);
        }
    }
}

fn rollback_geo_asset_install(states: &[GeoAssetInstallState]) -> Result<(), AppError> {
    let mut failures = Vec::new();
    for state in states.iter().rev() {
        if state.installed && state.destination.exists() {
            if let Err(error) = fs::remove_file(&state.destination) {
                failures.push(format!(
                    "could not remove replacement {}: {error}",
                    state.destination.display()
                ));
            }
        }
        if state.backed_up && state.backup.exists() {
            if let Err(error) = fs::rename(&state.backup, &state.destination) {
                failures.push(format!(
                    "could not restore {}: {error}",
                    state.destination.display()
                ));
            }
        }
        if state.staged.exists() {
            if let Err(error) = fs::remove_file(&state.staged) {
                failures.push(format!(
                    "could not clean staged {}: {error}",
                    state.staged.display()
                ));
            }
        }
    }

    if failures.is_empty() {
        Ok(())
    } else {
        Err(AppError::System(format!(
            "Geo asset rollback was incomplete: {}",
            failures.join("; ")
        )))
    }
}

fn install_geo_assets_transactionally(
    bin_dir: &Path,
    assets: &[(GeoAssetSpec, Vec<u8>)],
) -> Result<(), AppError> {
    use std::io::Write;

    // Validate the complete pair before touching either known-good destination.
    for (spec, bytes) in assets {
        validate_geo_asset(*spec, bytes)?;
    }

    fs::create_dir_all(bin_dir)?;
    let transaction_id = uuid::Uuid::new_v4();
    let mut states = Vec::with_capacity(assets.len());
    for (spec, bytes) in assets {
        let staged = bin_dir.join(format!(".{}.update-{}.tmp", spec.filename, transaction_id));
        let backup = bin_dir.join(format!(".{}.update-{}.bak", spec.filename, transaction_id));
        let destination = bin_dir.join(spec.filename);

        let write_result = (|| -> Result<(), AppError> {
            let mut file = fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&staged)?;
            file.write_all(bytes)?;
            file.sync_all()?;
            Ok(())
        })();
        if let Err(error) = write_result {
            let _ = fs::remove_file(&staged);
            clean_staged_geo_assets(&states);
            return Err(error);
        }

        states.push(GeoAssetInstallState {
            destination,
            staged,
            backup,
            backed_up: false,
            installed: false,
        });
    }

    for index in 0..states.len() {
        if states[index].destination.exists() {
            if let Err(error) = fs::rename(&states[index].destination, &states[index].backup) {
                let rollback = rollback_geo_asset_install(&states);
                return Err(AppError::System(format!(
                    "Failed to stage the existing {} for replacement: {error}{}",
                    states[index].destination.display(),
                    rollback
                        .err()
                        .map(|failure| format!("; {failure}"))
                        .unwrap_or_default()
                )));
            }
            states[index].backed_up = true;
        }

        if let Err(error) = fs::rename(&states[index].staged, &states[index].destination) {
            let rollback = rollback_geo_asset_install(&states);
            return Err(AppError::System(format!(
                "Failed to activate {}: {error}{}",
                states[index].destination.display(),
                rollback
                    .err()
                    .map(|failure| format!("; {failure}"))
                    .unwrap_or_default()
            )));
        }
        states[index].installed = true;
    }

    // The new complete pair is active. A backup cleanup failure is recoverable and
    // must not turn a successful transaction into an error with mixed semantics.
    for state in &states {
        if state.backup.exists() {
            let _ = fs::remove_file(&state.backup);
        }
    }
    Ok(())
}

pub async fn update_geo_assets(app_handle: &AppHandle) -> Result<(), AppError> {
    let app_dir = crate::engine::store::get_app_dir(app_handle)?;
    let bin_dir = app_dir.join("bin");
    let _update_guard = acquire_geo_asset_update_guard(&bin_dir).await?;
    let client = release_download_client(Duration::from_secs(30))?;

    let mut downloaded = Vec::with_capacity(GEO_ASSETS.len());
    for spec in GEO_ASSETS {
        downloaded.push((spec, download_geo_asset(&client, spec).await?));
    }

    tokio::task::spawn_blocking(move || install_geo_assets_transactionally(&bin_dir, &downloaded))
        .await
        .map_err(|error| AppError::System(error.to_string()))?
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_xray_and_sing_box_versions_without_platform_suffixes() {
        assert_eq!(
            parse_binary_version(
                "Xray 26.7.28 (Xray, Penetrates Everything.) Custom (go1.26.5 windows/amd64)",
                "xray"
            )
            .as_deref(),
            Some("26.7.28")
        );
        assert_eq!(
            parse_binary_version("sing-box version 1.13.8\nEnvironment: go1.26", "sing-box")
                .as_deref(),
            Some("1.13.8")
        );
        assert_eq!(parse_binary_version("unexpected", "xray"), None);
    }

    #[test]
    fn rejects_an_archive_when_its_pinned_digest_does_not_match() {
        let error = verify_archive_sha256(
            "Xray",
            "Xray-windows-64.zip",
            b"tampered archive",
            Some("c7172078fca4711bcd92a4774dcd1822544579c58816197575c47533317fd8d1"),
        )
        .expect_err("tampered Xray archive must fail closed");

        assert_eq!(
            error.to_string(),
            "System error: Xray archive integrity check failed for Xray-windows-64.zip"
        );
    }

    #[test]
    fn accepts_an_archive_only_when_its_digest_matches() {
        verify_archive_sha256(
            "test-runtime",
            "fixture.zip",
            b"hello",
            Some("2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"),
        )
        .expect("known fixture digest must match");
    }

    #[test]
    fn rejects_an_archive_when_no_target_pin_exists() {
        let error = verify_archive_sha256("Xray", "Xray-unsupported.zip", b"archive", None)
            .expect_err("an unpinned runtime download must fail closed");

        assert_eq!(
            error.to_string(),
            "Unsupported Core Version: No pinned archive digest is available for Xray (Xray-unsupported.zip); refusing an unverified runtime download"
        );
    }

    #[test]
    fn desktop_release_targets_have_exact_runtime_archive_pins() {
        let sing_box_cases = [
            (
                "windows-amd64",
                "sing-box-1.13.8-windows-amd64.zip",
                "599b743e9618b38d16ae1af65b35ffa3afadcc531b5bd9fea616e644711be5b9",
            ),
            (
                "linux-amd64",
                "sing-box-1.13.8-linux-amd64.tar.gz",
                "aab8841979aba14ae4c4dc72c4a593be1a16da95e75d53b494ed718f0223370f",
            ),
            (
                "darwin-amd64",
                "sing-box-1.13.8-darwin-amd64.tar.gz",
                "0db6aca503dcdd5a816e668669e79231f991cdbbd13fcbf6dd4f9bcb8a1c3b0e",
            ),
            (
                "darwin-arm64",
                "sing-box-1.13.8-darwin-arm64.tar.gz",
                "e9e4c72a4a64c19d515b800b7191c50367522c8169654c569677b15873e08249",
            ),
        ];
        for (target, filename, digest) in sing_box_cases {
            assert_eq!(sing_box_archive_filename(target).as_deref(), Some(filename));
            assert_eq!(sing_box_archive_sha256(target), Some(digest), "{target}");
        }

        let xray_cases = [
            (
                "windows-64",
                "Xray-windows-64.zip",
                "c7172078fca4711bcd92a4774dcd1822544579c58816197575c47533317fd8d1",
            ),
            (
                "linux-64",
                "Xray-linux-64.zip",
                "8195d909f1109b8f3d99eefe401a3c451d7bf4af71f24d3815420f77e5dd2a40",
            ),
            (
                "macos-64",
                "Xray-macos-64.zip",
                "812f7d9de6d3506795eabda2f6928ba301c632c3fe6fa39c52ea8e0ed9e4e244",
            ),
            (
                "macos-arm64-v8a",
                "Xray-macos-arm64-v8a.zip",
                "9b99a351febe31b7e0c7f22deeb1577a1da0b98aaa51aec7fd17832e68cf63d6",
            ),
        ];
        for (target, filename, digest) in xray_cases {
            assert_eq!(xray_archive_filename(target).as_deref(), Some(filename));
            assert_eq!(xray_archive_sha256(target), Some(digest), "{target}");
        }

        let sing_box_runtime_cases = [
            (
                "windows-amd64",
                "sing-box.exe",
                "e4f0d76903dbec850121b20cd6cf917fa6c456a554c97fba53bd6cda7790fbd8",
            ),
            (
                "windows-amd64",
                "libcronet.dll",
                "43e2e6c8bf0d29263fed11a7a11c108b671c741c54eb8ba9f5bc5370db8a2684",
            ),
            (
                "linux-amd64",
                "sing-box",
                "83b7846dc85ffb1f64c1d14f63eba2fcf3d3b19ed4049c2fcd291ed6c29b5cc2",
            ),
            (
                "linux-amd64",
                "libcronet.so",
                "55c35e93dff3ab2174b9a338adbc99f5bd1dc54347f8aa605f44f129db30dd80",
            ),
            (
                "darwin-amd64",
                "sing-box",
                "21a31b26bbb9d9299380083aaab59c949006130720fdc44db940c32f6493f0b6",
            ),
            (
                "darwin-arm64",
                "sing-box",
                "17e6a7f417a2bbff3693940c024856c3fc88fe5fc3acbc90146a7776d4211909",
            ),
        ];
        for (target, file_name, digest) in sing_box_runtime_cases {
            assert_eq!(
                sing_box_runtime_file_sha256(target, file_name),
                Some(digest),
                "{target}/{file_name}"
            );
        }
        assert_eq!(sing_box_support_files("windows-amd64"), &["libcronet.dll"]);
        assert_eq!(sing_box_support_files("linux-amd64"), &["libcronet.so"]);
        assert!(sing_box_support_files("darwin-amd64").is_empty());
        assert!(sing_box_support_files("darwin-arm64").is_empty());

        let xray_runtime_cases = [
            (
                "windows-64",
                "1d9674327972a21afd4c906a7a72bb0856935aa9e0227c87f34f03d11a88bddf",
            ),
            (
                "linux-64",
                "64d46afb80adea1bf97a0d467e83f4a9ac1ebd0995891e84bca3f1a1d1affb1d",
            ),
            (
                "macos-64",
                "38571e7799c0f34b1151fc2dfc40cfe570bec55ea59dd93dcee19d52648cea03",
            ),
            (
                "macos-arm64-v8a",
                "bd4154efa640c5b8e21f10b68afcc9177c4f1f543be3ec0485b10c499b2a4b27",
            ),
        ];
        for (target, digest) in xray_runtime_cases {
            assert_eq!(xray_runtime_sha256(target), Some(digest), "{target}");
        }
    }

    #[test]
    fn non_release_or_unknown_targets_remain_fail_closed() {
        for target in ["linux-arm64", "windows-arm64", "unknown"] {
            assert_eq!(sing_box_archive_sha256(target), None);
            assert_eq!(sing_box_archive_filename(target), None);
            assert_eq!(sing_box_runtime_file_sha256(target, "sing-box"), None);
        }
        for target in ["linux-arm64-v8a", "windows-arm64-v8a", "unknown"] {
            assert_eq!(xray_archive_sha256(target), None);
            assert_eq!(xray_archive_filename(target), None);
            assert_eq!(xray_runtime_sha256(target), None);
        }
    }

    #[test]
    fn tampered_cached_runtime_fails_identity_check_before_execution() {
        let path = std::env::temp_dir().join(format!(
            "cybervpn-runtime-integrity-{}",
            uuid::Uuid::new_v4()
        ));
        fs::write(&path, b"hello").expect("fixture should be written");
        assert!(file_sha256_matches(
            &path,
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        )
        .expect("fixture should hash"));

        fs::write(&path, b"tampered executable").expect("fixture should be replaced");
        assert!(!file_sha256_matches(
            &path,
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        )
        .expect("tampered fixture should hash"));
        fs::remove_file(path).expect("fixture should be removed");
    }

    #[test]
    fn geo_asset_pins_use_immutable_release_urls() {
        let expected = [
            (
                "geoip.db",
                "20260812",
                "d8f4d22abee199b73c019df267e8dc649e868da3b130753640aa9b05d11040c0",
            ),
            (
                "geosite.db",
                "20260831141734",
                "dfed5b0ca5a439bbb64561b5760434bd15ab10f9765f5e9cf7ba05d7d93205cb",
            ),
        ];

        for (spec, (filename, release_tag, digest)) in GEO_ASSETS.iter().zip(expected) {
            assert_eq!(spec.filename, filename);
            assert_eq!(spec.release_tag, release_tag);
            assert_eq!(spec.sha256, digest);
            let url = spec.download_url();
            assert!(url.contains(&format!("/releases/download/{release_tag}/")));
            assert!(!url.contains("/latest/"));
        }
    }

    #[test]
    fn invalid_or_oversized_geo_assets_preserve_known_good_files() {
        let directory = std::env::temp_dir().join(format!(
            "cybervpn-geo-assets-preserve-{}",
            uuid::Uuid::new_v4()
        ));
        fs::create_dir_all(&directory).expect("fixture directory should be created");
        let geoip_path = directory.join("geoip.db");
        let geosite_path = directory.join("geosite.db");
        fs::write(&geoip_path, b"known-good-geoip").expect("geoip fixture should be written");
        fs::write(&geosite_path, b"known-good-geosite").expect("geosite fixture should be written");

        let wrong_hash = vec![(GEO_ASSETS[0], b"wrong geoip".to_vec())];
        install_geo_assets_transactionally(&directory, &wrong_hash)
            .expect_err("wrong digest must fail closed");
        assert_eq!(fs::read(&geoip_path).unwrap(), b"known-good-geoip");
        assert_eq!(fs::read(&geosite_path).unwrap(), b"known-good-geosite");

        let oversized = vec![(GEO_ASSETS[1], vec![0_u8; MAX_GEO_ASSET_BYTES + 1])];
        install_geo_assets_transactionally(&directory, &oversized)
            .expect_err("oversized asset must fail closed");
        assert_eq!(fs::read(&geoip_path).unwrap(), b"known-good-geoip");
        assert_eq!(fs::read(&geosite_path).unwrap(), b"known-good-geosite");

        fs::remove_dir_all(directory).expect("fixture directory should be removed");
    }

    #[test]
    fn validated_geo_asset_pair_replaces_both_files() {
        let directory = std::env::temp_dir().join(format!(
            "cybervpn-geo-assets-commit-{}",
            uuid::Uuid::new_v4()
        ));
        fs::create_dir_all(&directory).expect("fixture directory should be created");
        fs::write(directory.join("geoip.db"), b"old geoip").unwrap();
        fs::write(directory.join("geosite.db"), b"old geosite").unwrap();

        let fixture_assets = vec![
            (
                GeoAssetSpec {
                    filename: "geoip.db",
                    release_tag: "fixture",
                    sha256: "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
                    repository: "fixture/geoip",
                },
                b"hello".to_vec(),
            ),
            (
                GeoAssetSpec {
                    filename: "geosite.db",
                    release_tag: "fixture",
                    sha256: "486ea46224d1bb4fb680f34f7c9ad96a8f24ec88be73ea8e5a6c65260e9cb8a7",
                    repository: "fixture/geosite",
                },
                b"world".to_vec(),
            ),
        ];
        install_geo_assets_transactionally(&directory, &fixture_assets)
            .expect("validated pair should commit");
        assert_eq!(fs::read(directory.join("geoip.db")).unwrap(), b"hello");
        assert_eq!(fs::read(directory.join("geosite.db")).unwrap(), b"world");

        fs::remove_dir_all(directory).expect("fixture directory should be removed");
    }

    #[test]
    fn runtime_archive_length_and_stream_limits_fail_closed() {
        let error = validate_download_content_length("Xray archive", Some(9), 8)
            .expect_err("oversized Content-Length must be rejected");
        assert!(error.to_string().contains("8 byte download limit"));

        let mut body = vec![1_u8; 8];
        let error = append_bounded_download_chunk("Sing-box archive", &mut body, &[2], 8)
            .expect_err("oversized streamed response must be rejected");
        assert!(error.to_string().contains("8 byte download limit"));
        assert_eq!(body, vec![1_u8; 8]);
    }

    #[tokio::test]
    async fn concurrent_geo_success_and_failure_cannot_mix_or_clobber_the_pair() {
        use std::sync::Arc;
        use tokio::sync::Notify;

        let directory = std::env::temp_dir().join(format!(
            "cybervpn-geo-assets-concurrent-{}",
            uuid::Uuid::new_v4()
        ));
        fs::create_dir_all(&directory).expect("fixture directory should be created");
        fs::write(directory.join("geoip.db"), b"old geoip").unwrap();
        fs::write(directory.join("geosite.db"), b"old geosite").unwrap();

        let successful_assets = vec![
            (
                GeoAssetSpec {
                    filename: "geoip.db",
                    release_tag: "fixture",
                    sha256: "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
                    repository: "fixture/geoip",
                },
                b"hello".to_vec(),
            ),
            (
                GeoAssetSpec {
                    filename: "geosite.db",
                    release_tag: "fixture",
                    sha256: "486ea46224d1bb4fb680f34f7c9ad96a8f24ec88be73ea8e5a6c65260e9cb8a7",
                    repository: "fixture/geosite",
                },
                b"world".to_vec(),
            ),
        ];
        let failing_assets = vec![(GEO_ASSETS[0], b"wrong digest".to_vec())];
        let first_started = Arc::new(Notify::new());
        let release_first = Arc::new(Notify::new());
        let second_started = Arc::new(Notify::new());

        let first_directory = directory.clone();
        let first_started_task = Arc::clone(&first_started);
        let release_first_task = Arc::clone(&release_first);
        let first = tokio::spawn(async move {
            let _guard = acquire_geo_asset_update_guard(&first_directory).await?;
            first_started_task.notify_one();
            release_first_task.notified().await;
            install_geo_assets_transactionally(&first_directory, &successful_assets)
        });
        first_started.notified().await;

        let second_directory = directory.clone();
        let second_started_task = Arc::clone(&second_started);
        let second = tokio::spawn(async move {
            let _guard = acquire_geo_asset_update_guard(&second_directory).await?;
            second_started_task.notify_one();
            install_geo_assets_transactionally(&second_directory, &failing_assets)
        });

        assert!(
            tokio::time::timeout(Duration::from_millis(50), second_started.notified())
                .await
                .is_err(),
            "the second update must remain queued while the first owns the single-flight lock"
        );
        release_first.notify_one();
        first
            .await
            .expect("first task must join")
            .expect("first update must commit");
        second
            .await
            .expect("second task must join")
            .expect_err("queued invalid update must fail without rollback clobber");

        assert_eq!(fs::read(directory.join("geoip.db")).unwrap(), b"hello");
        assert_eq!(fs::read(directory.join("geosite.db")).unwrap(), b"world");
        fs::remove_dir_all(directory).expect("fixture directory should be removed");
    }

    #[test]
    fn geo_asset_file_lock_rejects_a_second_handle_until_release() {
        let directory = std::env::temp_dir().join(format!(
            "cybervpn-geo-assets-file-lock-{}",
            uuid::Uuid::new_v4()
        ));
        fs::create_dir_all(&directory).expect("fixture directory should be created");

        let first = acquire_geo_asset_file_lock_with_timeout(&directory, Duration::ZERO)
            .expect("first process handle must acquire the OS lock");
        let error = acquire_geo_asset_file_lock_with_timeout(&directory, Duration::from_millis(10))
            .expect_err("second process handle must time out while the lock is held");
        assert!(error.to_string().contains("Geo asset update lock"));
        drop(first);

        let second = acquire_geo_asset_file_lock_with_timeout(&directory, Duration::ZERO)
            .expect("the lock must become available after RAII release");
        drop(second);
        fs::remove_dir_all(directory).expect("fixture directory should be removed");
    }
}
