use crate::engine::error::AppError;
use crate::engine::helix::config::{
    HelixPreparedRuntime, HelixRecoveryBenchmarkReport, HelixResolvedManifest,
    TransportBenchmarkComparisonReport, TransportBenchmarkMatrixReport, TransportBenchmarkReport,
};
use crate::engine::lifecycle::StartupRecoveryInfo;
use crate::engine::sys::net_monitor::NetworkProfile;
use crate::ipc::models::ProxyNode;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::Path;
use std::path::PathBuf;
use std::time::Duration;
use tauri::AppHandle;
use tauri::Manager;

const SUBSCRIPTION_MUTATION_LOCK_WAIT: Duration = Duration::from_secs(30);
const STORE_WRITE_LOCK_WAIT: Duration = Duration::from_secs(30);
const FILE_LOCK_RETRY: Duration = Duration::from_millis(50);
const STORE_MUTATION_MAX_ATTEMPTS: usize = 3;
static SUBSCRIPTION_MUTATION_LOCK: tokio::sync::Mutex<()> = tokio::sync::Mutex::const_new(());

pub(crate) struct SubscriptionMutationGuard {
    _process_guard: tokio::sync::MutexGuard<'static, ()>,
    _file_guard: fs::File,
}

fn acquire_file_lock_with_timeout(
    app_dir: &Path,
    lock_file_name: &str,
    lock_label: &str,
    wait: Duration,
) -> Result<fs::File, AppError> {
    use std::fs::TryLockError;
    use std::time::Instant;

    fs::create_dir_all(app_dir)?;
    let lock_file = fs::OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(false)
        .open(app_dir.join(lock_file_name))?;
    let deadline = Instant::now() + wait;
    loop {
        match lock_file.try_lock() {
            Ok(()) => return Ok(lock_file),
            Err(TryLockError::WouldBlock) if Instant::now() < deadline => {
                std::thread::sleep(
                    FILE_LOCK_RETRY.min(deadline.saturating_duration_since(Instant::now())),
                );
            }
            Err(TryLockError::WouldBlock) => {
                return Err(AppError::System(format!(
                    "Timed out waiting for the {lock_label} lock"
                )));
            }
            Err(TryLockError::Error(error)) => return Err(AppError::Io(error)),
        }
    }
}

fn acquire_subscription_file_lock_with_timeout(
    app_dir: &Path,
    wait: Duration,
) -> Result<fs::File, AppError> {
    acquire_file_lock_with_timeout(
        app_dir,
        ".subscription-mutation.lock",
        "subscription mutation",
        wait,
    )
}

fn acquire_store_write_lock_with_timeout(
    app_dir: &Path,
    wait: Duration,
) -> Result<fs::File, AppError> {
    acquire_file_lock_with_timeout(app_dir, ".store-write.lock", "store write", wait)
}

pub(crate) async fn acquire_subscription_mutation_guard(
    app_handle: &AppHandle,
) -> Result<SubscriptionMutationGuard, AppError> {
    let process_guard = SUBSCRIPTION_MUTATION_LOCK.lock().await;
    let app_dir = get_app_dir(app_handle)?;
    let file_guard = tokio::task::spawn_blocking(move || {
        acquire_subscription_file_lock_with_timeout(&app_dir, SUBSCRIPTION_MUTATION_LOCK_WAIT)
    })
    .await
    .map_err(|error| AppError::System(error.to_string()))??;
    Ok(SubscriptionMutationGuard {
        _process_guard: process_guard,
        _file_guard: file_guard,
    })
}

#[derive(Serialize, Deserialize)]
pub struct AppDataStore {
    #[serde(default)]
    pub(crate) store_revision: u64,
    pub profiles: Vec<ProxyNode>,
    pub active_profile_id: Option<String>,
    #[serde(default)]
    pub last_connection_options: crate::ipc::models::LastConnectionOptions,
    pub routing_rules: Vec<crate::ipc::models::RoutingRule>,
    pub subscriptions: Vec<crate::ipc::models::Subscription>,
    pub custom_config: Option<String>,
    #[serde(default = "default_active_core")]
    pub active_core: String,
    pub local_socks_port: Option<u16>,
    #[serde(default)]
    pub allow_lan: bool,
    #[serde(default)]
    pub groups: Vec<crate::ipc::models::ProfileGroup>,
    #[serde(default)]
    pub split_tunneling_apps: Vec<String>,
    #[serde(default = "default_split_tunneling_mode")]
    pub split_tunneling_mode: String,
    #[serde(default)]
    pub stealth_mode_enabled: bool,
    #[serde(default)]
    pub pqc_enforcement_mode: bool,
    #[serde(default = "default_privacy_shield_level")]
    pub privacy_shield_level: String,

    // Phase 28 features
    #[serde(default)]
    pub smart_connect_enabled: bool,
    #[serde(default = "default_stealth_auto_pilot_mode")]
    pub stealth_auto_pilot_mode: String,
    #[serde(default)]
    pub network_rules: HashMap<String, NetworkProfile>,
    #[serde(default)]
    pub last_stealth_rollback: Option<crate::engine::sys::diagnostics::StealthRollbackSnapshot>,
    #[serde(default)]
    pub helix_backend_url: Option<String>,
    #[serde(default)]
    pub helix_desktop_client_id: Option<String>,
    #[serde(default)]
    pub helix_last_manifest: Option<HelixResolvedManifest>,
    #[serde(default)]
    pub helix_last_prepared_runtime: Option<HelixPreparedRuntime>,
    #[serde(default)]
    pub helix_last_fallback_reason: Option<String>,
    #[serde(default)]
    pub helix_last_benchmark_report: Option<TransportBenchmarkReport>,
    #[serde(default)]
    pub helix_last_comparison_report: Option<TransportBenchmarkComparisonReport>,
    #[serde(default)]
    pub helix_last_matrix_report: Option<TransportBenchmarkMatrixReport>,
    #[serde(default)]
    pub helix_last_recovery_report: Option<HelixRecoveryBenchmarkReport>,
    #[serde(default)]
    pub last_startup_recovery: Option<StartupRecoveryInfo>,
}

fn default_privacy_shield_level() -> String {
    "standard".to_string()
}

fn default_split_tunneling_mode() -> String {
    "allow".to_string()
}

fn default_active_core() -> String {
    "sing-box".to_string()
}

fn default_stealth_auto_pilot_mode() -> String {
    "recommend-only".to_string()
}

impl Default for AppDataStore {
    fn default() -> Self {
        Self {
            store_revision: 0,
            profiles: Vec::new(),
            active_profile_id: None,
            last_connection_options: crate::ipc::models::LastConnectionOptions::default(),
            routing_rules: Vec::new(),
            subscriptions: Vec::new(),
            custom_config: None,
            active_core: default_active_core(),
            local_socks_port: None,
            allow_lan: false,
            groups: Vec::new(),
            split_tunneling_apps: Vec::new(),
            split_tunneling_mode: default_split_tunneling_mode(),
            stealth_mode_enabled: false,
            pqc_enforcement_mode: false,
            privacy_shield_level: default_privacy_shield_level(),
            smart_connect_enabled: false,
            stealth_auto_pilot_mode: default_stealth_auto_pilot_mode(),
            network_rules: HashMap::new(),
            last_stealth_rollback: None,
            helix_backend_url: None,
            helix_desktop_client_id: None,
            helix_last_manifest: None,
            helix_last_prepared_runtime: None,
            helix_last_fallback_reason: None,
            helix_last_benchmark_report: None,
            helix_last_comparison_report: None,
            helix_last_matrix_report: None,
            helix_last_recovery_report: None,
            last_startup_recovery: None,
        }
    }
}

pub fn get_app_dir(app_handle: &AppHandle) -> Result<PathBuf, AppError> {
    if let Ok(override_dir) = std::env::var("CYBERVPN_APP_DIR_OVERRIDE") {
        let app_dir = PathBuf::from(override_dir);
        if !app_dir.exists() {
            fs::create_dir_all(&app_dir)?;
        }
        return Ok(app_dir);
    }

    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(parent) = exe_path.parent() {
            let portable_flag = parent.join(".portable");
            if portable_flag.exists() {
                return Ok(parent.to_path_buf());
            }
        }
    }

    let app_dir = app_handle
        .path()
        .app_data_dir()
        .map_err(|e| AppError::System(format!("Failed to get app_data_dir: {}", e)))?;

    if !app_dir.exists() {
        fs::create_dir_all(&app_dir)?;
    }

    Ok(app_dir)
}

pub fn get_store_path(app_handle: &AppHandle) -> Result<PathBuf, AppError> {
    let app_dir = get_app_dir(app_handle)?;
    Ok(app_dir.join("store.json"))
}

fn load_store_path(store_path: &Path) -> Result<AppDataStore, AppError> {
    if !store_path.exists() {
        return Ok(AppDataStore::default());
    }

    let contents = fs::read_to_string(store_path)?;
    let store = serde_json::from_str(&contents)?;
    Ok(store)
}

fn validate_legacy_subscription_migration(
    store: &AppDataStore,
) -> Result<Vec<(String, String)>, AppError> {
    let mut ids = HashSet::with_capacity(store.subscriptions.len());
    let mut credentials = Vec::new();
    for subscription in &store.subscriptions {
        let parsed_id = crate::engine::subscription::validate_subscription_id(&subscription.id)?;
        if !ids.insert(parsed_id) {
            return Err(AppError::System(
                "Duplicate subscription IDs prevent secure credential migration".to_string(),
            ));
        }
        if let Some(url) = subscription.legacy_url.as_deref() {
            crate::engine::subscription::validate_subscription_url_for_storage(url)?;
            credentials.push((subscription.id.clone(), url.to_string()));
        }
    }
    Ok(credentials)
}

fn migrate_legacy_subscription_urls_with<F>(
    store_path: &Path,
    store: &mut AppDataStore,
    mut store_credential: F,
) -> Result<bool, AppError>
where
    F: FnMut(&str, &str) -> Result<(), AppError>,
{
    // Complete every validation before the first keyring write. In
    // particular, duplicate IDs would otherwise alias the same keyring
    // account and could silently replace one bearer credential with another.
    let credentials = validate_legacy_subscription_migration(store)?;
    if credentials.is_empty() {
        return Ok(false);
    }

    for (subscription_id, url) in &credentials {
        store_credential(subscription_id, url)?;
    }

    // Subscription::legacy_url is skip_serializing. Only after every secure
    // write succeeds do we atomically replace the legacy plaintext store.
    // A failed replacement leaves the original file recoverable for retry.
    save_store_path_atomic(store_path, store)?;
    for subscription in &mut store.subscriptions {
        subscription.legacy_url = None;
    }
    Ok(true)
}

fn ensure_store_has_no_legacy_subscription_urls(store: &AppDataStore) -> Result<(), AppError> {
    if store
        .subscriptions
        .iter()
        .any(|subscription| subscription.legacy_url.is_some())
    {
        return Err(AppError::System(
            "Legacy subscription credentials must be migrated before saving".to_string(),
        ));
    }
    Ok(())
}

pub fn load_store(app_handle: &AppHandle) -> Result<AppDataStore, AppError> {
    let store_path = get_store_path(app_handle)?;
    let mut store = load_store_path(&store_path)?;
    if !store
        .subscriptions
        .iter()
        .any(|subscription| subscription.legacy_url.is_some())
    {
        return Ok(store);
    }

    let app_dir = store_path
        .parent()
        .ok_or_else(|| AppError::System("Store path has no parent directory".to_string()))?;
    let _migration_lock =
        acquire_subscription_file_lock_with_timeout(app_dir, SUBSCRIPTION_MUTATION_LOCK_WAIT)?;
    let _store_write_lock = acquire_store_write_lock_with_timeout(app_dir, STORE_WRITE_LOCK_WAIT)?;
    // Re-read after acquiring the cross-process lock: another process may
    // already have completed the one-time migration while this one waited.
    store = load_store_path(&store_path)?;
    migrate_legacy_subscription_urls_with(&store_path, &mut store, |subscription_id, url| {
        crate::engine::subscription::store_subscription_url(subscription_id, url)
    })?;
    Ok(store)
}

pub fn save_store(app_handle: &AppHandle, store: &AppDataStore) -> Result<(), AppError> {
    let store_path = get_store_path(app_handle)?;
    save_store_path_cas_atomic(&store_path, store)
}

#[cfg(target_os = "windows")]
fn replace_file_atomically(staged: &Path, destination: &Path) -> Result<(), AppError> {
    use std::iter::once;
    use std::os::windows::ffi::OsStrExt;
    use windows::core::PCWSTR;
    use windows::Win32::Storage::FileSystem::{
        MoveFileExW, MOVEFILE_REPLACE_EXISTING, MOVEFILE_WRITE_THROUGH,
    };

    let staged_wide: Vec<u16> = staged.as_os_str().encode_wide().chain(once(0)).collect();
    let destination_wide: Vec<u16> = destination
        .as_os_str()
        .encode_wide()
        .chain(once(0))
        .collect();
    // SAFETY: both PCWSTR arguments reference NUL-terminated buffers that stay
    // alive for the duration of the call, and both paths are on the same app-data volume.
    unsafe {
        MoveFileExW(
            PCWSTR(staged_wide.as_ptr()),
            PCWSTR(destination_wide.as_ptr()),
            MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH,
        )
    }
    .map_err(|error| AppError::System(format!("Atomic store replacement failed: {error}")))
}

#[cfg(not(target_os = "windows"))]
fn replace_file_atomically(staged: &Path, destination: &Path) -> Result<(), AppError> {
    fs::rename(staged, destination)?;
    Ok(())
}

fn save_bytes_path_atomic(store_path: &Path, contents: &[u8]) -> Result<(), AppError> {
    use std::io::Write;

    let parent = store_path
        .parent()
        .ok_or_else(|| AppError::System("Store path has no parent directory".to_string()))?;
    fs::create_dir_all(parent)?;
    let file_name = store_path
        .file_name()
        .and_then(|value| value.to_str())
        .unwrap_or("store.json");
    let staged_path = parent.join(format!(
        ".{file_name}.{}.tmp",
        uuid::Uuid::new_v4().hyphenated()
    ));
    let write_result = (|| -> Result<(), AppError> {
        let mut staged = fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&staged_path)?;
        staged.write_all(contents)?;
        staged.sync_all()?;
        Ok(())
    })();
    if let Err(error) = write_result {
        let _ = fs::remove_file(&staged_path);
        return Err(error);
    }

    if let Err(error) = replace_file_atomically(&staged_path, store_path) {
        let _ = fs::remove_file(&staged_path);
        return Err(error);
    }
    Ok(())
}

fn save_store_path_atomic(store_path: &Path, store: &AppDataStore) -> Result<(), AppError> {
    let contents = serde_json::to_vec_pretty(store)?;
    save_bytes_path_atomic(store_path, &contents)
}

fn save_store_path_cas_atomic(store_path: &Path, store: &AppDataStore) -> Result<(), AppError> {
    ensure_store_has_no_legacy_subscription_urls(store)?;
    let app_dir = store_path
        .parent()
        .ok_or_else(|| AppError::System("Store path has no parent directory".to_string()))?;
    let _write_lock = acquire_store_write_lock_with_timeout(app_dir, STORE_WRITE_LOCK_WAIT)?;
    let current = load_store_path(store_path)?;
    if current
        .subscriptions
        .iter()
        .any(|subscription| subscription.legacy_url.is_some())
    {
        return Err(AppError::SyncConflict(
            "Legacy subscription credentials must be migrated before saving".to_string(),
        ));
    }
    if current.store_revision != store.store_revision {
        return Err(AppError::SyncConflict(
            "The local store changed concurrently; reload and retry".to_string(),
        ));
    }

    let next_revision = store
        .store_revision
        .checked_add(1)
        .ok_or_else(|| AppError::System("Local store revision exhausted".to_string()))?;
    let mut serialized = serde_json::to_value(store)?;
    serialized["store_revision"] = serde_json::json!(next_revision);
    let contents = serde_json::to_vec_pretty(&serialized)?;
    save_bytes_path_atomic(store_path, &contents)
}

fn replace_store_path_if_revision_atomic(
    store_path: &Path,
    imported: &AppDataStore,
    expected_local_revision: u64,
) -> Result<(), AppError> {
    ensure_store_has_no_legacy_subscription_urls(imported)?;
    let app_dir = store_path
        .parent()
        .ok_or_else(|| AppError::System("Store path has no parent directory".to_string()))?;
    let _write_lock = acquire_store_write_lock_with_timeout(app_dir, STORE_WRITE_LOCK_WAIT)?;
    let current = load_store_path(store_path)?;
    if current
        .subscriptions
        .iter()
        .any(|subscription| subscription.legacy_url.is_some())
    {
        return Err(AppError::SyncConflict(
            "Legacy subscription credentials must be migrated before cloud restore".to_string(),
        ));
    }
    if current.store_revision != expected_local_revision {
        return Err(AppError::SyncConflict(
            "The local store changed during cloud pull; retry without overwriting local changes"
                .to_string(),
        ));
    }

    let next_revision = expected_local_revision
        .checked_add(1)
        .ok_or_else(|| AppError::System("Local store revision exhausted".to_string()))?;
    // The remote/source-device revision is not meaningful in this local CAS
    // domain. Serialize the imported payload with the next local revision.
    let mut serialized = serde_json::to_value(imported)?;
    serialized["store_revision"] = serde_json::json!(next_revision);
    let contents = serde_json::to_vec_pretty(&serialized)?;
    save_bytes_path_atomic(store_path, &contents)
}

pub(crate) fn save_store_atomic(
    app_handle: &AppHandle,
    store: &AppDataStore,
) -> Result<(), AppError> {
    let store_path = get_store_path(app_handle)?;
    save_store_path_cas_atomic(&store_path, store)
}

pub(crate) fn replace_store_if_revision_atomic(
    app_handle: &AppHandle,
    imported: &AppDataStore,
    expected_local_revision: u64,
) -> Result<(), AppError> {
    let store_path = get_store_path(app_handle)?;
    replace_store_path_if_revision_atomic(&store_path, imported, expected_local_revision)
}

enum StoreMutation<T> {
    NoChange(T),
    Save(T),
}

fn mutate_store_with_retry_using<T, L, S, M>(
    max_attempts: usize,
    mut load: L,
    mut save: S,
    mut mutation: M,
) -> Result<T, AppError>
where
    L: FnMut() -> Result<AppDataStore, AppError>,
    S: FnMut(&AppDataStore) -> Result<(), AppError>,
    M: FnMut(&mut AppDataStore) -> StoreMutation<T>,
{
    if max_attempts == 0 {
        return Err(AppError::System(
            "Store mutation retry budget must be positive".to_string(),
        ));
    }

    for attempt in 0..max_attempts {
        let mut store = load()?;
        match mutation(&mut store) {
            StoreMutation::NoChange(result) => return Ok(result),
            StoreMutation::Save(result) => match save(&store) {
                Ok(()) => return Ok(result),
                Err(AppError::SyncConflict(_)) if attempt + 1 < max_attempts => continue,
                Err(error) => return Err(error),
            },
        }
    }

    Err(AppError::SyncConflict(
        "The local store remained busy after bounded retries".to_string(),
    ))
}

pub(crate) fn import_profile_with_retry(
    app_handle: &AppHandle,
    profile: ProxyNode,
) -> Result<bool, AppError> {
    mutate_store_with_retry_using(
        STORE_MUTATION_MAX_ATTEMPTS,
        || load_store(app_handle),
        |store| save_store(app_handle, store),
        |store| apply_profile_import(store, &profile),
    )
}

fn apply_profile_import(store: &mut AppDataStore, profile: &ProxyNode) -> StoreMutation<bool> {
    if store.profiles.iter().any(|stored| stored.id == profile.id) {
        StoreMutation::NoChange(false)
    } else {
        store.profiles.push(profile.clone());
        StoreMutation::Save(true)
    }
}

pub(crate) fn clear_active_profile_with_retry(app_handle: &AppHandle) -> Result<bool, AppError> {
    mutate_store_with_retry_using(
        STORE_MUTATION_MAX_ATTEMPTS,
        || load_store(app_handle),
        |store| save_store(app_handle, store),
        |store| {
            if store.active_profile_id.is_none() {
                StoreMutation::NoChange(false)
            } else {
                store.active_profile_id = None;
                StoreMutation::Save(true)
            }
        },
    )
}

#[derive(Debug, Default)]
pub struct ConnectionMetadataReconciliation {
    pub cleared_stale_active_profile: bool,
    pub cleared_missing_last_profile: bool,
    pub synced_last_active_core: bool,
}

pub fn reconcile_connection_metadata(
    app_handle: &AppHandle,
) -> Result<ConnectionMetadataReconciliation, AppError> {
    let mut store = load_store(app_handle)?;
    let mut report = ConnectionMetadataReconciliation::default();
    let mut changed = false;

    if store.active_profile_id.is_some() {
        store.active_profile_id = None;
        report.cleared_stale_active_profile = true;
        changed = true;
    }

    if store
        .last_connection_options
        .profile_id
        .as_ref()
        .is_some_and(|profile_id| {
            !store
                .profiles
                .iter()
                .any(|profile| &profile.id == profile_id)
        })
    {
        store.last_connection_options.profile_id = None;
        report.cleared_missing_last_profile = true;
        changed = true;
    }

    if store.last_connection_options.active_core.trim().is_empty()
        || store.last_connection_options.active_core != store.active_core
    {
        store.last_connection_options.active_core = store.active_core.clone();
        report.synced_last_active_core = true;
        changed = true;
    }

    if changed {
        save_store(app_handle, &store)?;
    }

    Ok(report)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn write_legacy_store(store_path: &Path, subscriptions: serde_json::Value) -> Vec<u8> {
        let mut value =
            serde_json::to_value(AppDataStore::default()).expect("default store must serialize");
        value["subscriptions"] = subscriptions;
        let bytes = serde_json::to_vec_pretty(&value).expect("legacy fixture must serialize");
        fs::create_dir_all(
            store_path
                .parent()
                .expect("fixture path must have a parent"),
        )
        .expect("fixture directory must be created");
        fs::write(store_path, &bytes).expect("legacy fixture must be written");
        bytes
    }

    #[test]
    fn subscription_file_lock_is_cross_handle_and_released_by_raii() {
        let directory = std::env::temp_dir().join(format!(
            "cybervpn-subscription-lock-{}",
            uuid::Uuid::new_v4()
        ));
        fs::create_dir_all(&directory).expect("fixture directory should be created");

        let first = acquire_subscription_file_lock_with_timeout(&directory, Duration::ZERO)
            .expect("first handle must acquire the lock");
        let error =
            acquire_subscription_file_lock_with_timeout(&directory, Duration::from_millis(10))
                .expect_err("second handle must time out while the lock is held");
        assert!(error.to_string().contains("subscription mutation lock"));
        drop(first);

        let second = acquire_subscription_file_lock_with_timeout(&directory, Duration::ZERO)
            .expect("RAII drop must release the lock");
        drop(second);
        fs::remove_dir_all(directory).expect("fixture directory should be removed");
    }

    #[test]
    fn atomic_store_replacement_leaves_one_complete_json_document() {
        let directory =
            std::env::temp_dir().join(format!("cybervpn-store-atomic-{}", uuid::Uuid::new_v4()));
        let store_path = directory.join("store.json");
        let first = AppDataStore {
            smart_connect_enabled: false,
            ..Default::default()
        };
        save_store_path_atomic(&store_path, &first).expect("initial atomic save must pass");

        let second = AppDataStore {
            smart_connect_enabled: true,
            local_socks_port: Some(2080),
            ..Default::default()
        };
        save_store_path_atomic(&store_path, &second).expect("replacement must pass");

        let persisted: AppDataStore = serde_json::from_slice(
            &fs::read(&store_path).expect("persisted store must be readable"),
        )
        .expect("persisted store must be one complete JSON document");
        assert!(persisted.smart_connect_enabled);
        assert_eq!(persisted.local_socks_port, Some(2080));
        assert_eq!(
            fs::read_dir(&directory)
                .unwrap()
                .filter_map(Result::ok)
                .filter(|entry| entry.file_name().to_string_lossy().ends_with(".tmp"))
                .count(),
            0
        );
        fs::remove_dir_all(directory).expect("fixture directory should be removed");
    }

    #[test]
    fn store_revision_cas_rejects_stale_whole_store_writer_without_erasing_refresh() {
        let directory =
            std::env::temp_dir().join(format!("cybervpn-store-cas-{}", uuid::Uuid::new_v4()));
        let store_path = directory.join("store.json");
        save_store_path_cas_atomic(&store_path, &AppDataStore::default())
            .expect("initial store commit must pass");

        // Both snapshots represent separate commands that loaded before
        // either one committed its whole-store mutation.
        let mut subscription_refresh =
            load_store_path(&store_path).expect("refresh snapshot must load");
        let mut stale_setting_writer =
            load_store_path(&store_path).expect("setting snapshot must load");
        subscription_refresh
            .subscriptions
            .push(crate::ipc::models::Subscription {
                id: "b831381d-6324-4d53-ad4f-8cda48b30811".to_string(),
                name: "Primary".to_string(),
                legacy_url: None,
                auto_update: true,
                last_updated: Some(99),
            });
        subscription_refresh.profiles.push(ProxyNode {
            id: "refreshed-node".to_string(),
            name: "Refreshed node".to_string(),
            server: "vpn.example".to_string(),
            port: 443,
            protocol: "vless".to_string(),
            subscription_id: Some("b831381d-6324-4d53-ad4f-8cda48b30811".to_string()),
            ..Default::default()
        });
        stale_setting_writer.local_socks_port = Some(2080);

        save_store_path_cas_atomic(&store_path, &subscription_refresh)
            .expect("subscription refresh must commit");
        let stale_error = save_store_path_cas_atomic(&store_path, &stale_setting_writer)
            .expect_err("stale whole-store writer must fail closed");

        assert!(stale_error.to_string().contains("changed concurrently"));
        let persisted = load_store_path(&store_path).expect("committed store must remain readable");
        assert_eq!(persisted.store_revision, 2);
        assert_eq!(persisted.local_socks_port, None);
        assert_eq!(persisted.subscriptions[0].last_updated, Some(99));
        assert_eq!(persisted.profiles[0].id, "refreshed-node");
        fs::remove_dir_all(directory).expect("fixture directory should be removed");
    }

    #[test]
    fn cloud_replace_uses_local_revision_and_rejects_intervening_local_commit() {
        let directory =
            std::env::temp_dir().join(format!("cybervpn-store-cloud-cas-{}", uuid::Uuid::new_v4()));
        let store_path = directory.join("store.json");
        save_store_path_cas_atomic(&store_path, &AppDataStore::default())
            .expect("initial local store commit must pass");
        let expected_revision = load_store_path(&store_path).unwrap().store_revision;

        let imported = AppDataStore {
            // A source-device revision must never participate in local CAS.
            store_revision: 9_999,
            local_socks_port: Some(3090),
            ..Default::default()
        };
        replace_store_path_if_revision_atomic(&store_path, &imported, expected_revision)
            .expect("unchanged local store must accept secret-free import");
        let replaced = load_store_path(&store_path).expect("replacement must be readable");
        assert_eq!(replaced.store_revision, expected_revision + 1);
        assert_eq!(replaced.local_socks_port, Some(3090));

        let pull_started_at_revision = replaced.store_revision;
        let mut concurrent_local = load_store_path(&store_path).unwrap();
        concurrent_local.smart_connect_enabled = true;
        save_store_path_cas_atomic(&store_path, &concurrent_local)
            .expect("intervening local commit must pass");
        let stale_import = AppDataStore {
            store_revision: 1,
            local_socks_port: Some(4080),
            ..Default::default()
        };
        let error = replace_store_path_if_revision_atomic(
            &store_path,
            &stale_import,
            pull_started_at_revision,
        )
        .expect_err("pull must not overwrite an intervening local commit");

        assert!(error.to_string().contains("changed during cloud pull"));
        let preserved = load_store_path(&store_path).expect("local commit must remain readable");
        assert!(preserved.smart_connect_enabled);
        assert_eq!(preserved.local_socks_port, Some(3090));
        assert_eq!(preserved.store_revision, pull_started_at_revision + 1);
        fs::remove_dir_all(directory).expect("fixture directory should be removed");
    }

    #[test]
    fn profile_import_reloads_after_cas_conflict_and_deduplicates_before_success_signal() {
        let directory = std::env::temp_dir().join(format!(
            "cybervpn-profile-import-cas-{}",
            uuid::Uuid::new_v4()
        ));
        let store_path = directory.join("store.json");
        save_store_path_cas_atomic(&store_path, &AppDataStore::default())
            .expect("initial store commit must pass");
        let profile = ProxyNode {
            id: "deep-link-profile".to_string(),
            name: "Deep link".to_string(),
            server: "vpn.example".to_string(),
            port: 443,
            protocol: "vless".to_string(),
            ..Default::default()
        };
        let inject_concurrent_commit = std::cell::Cell::new(true);

        let imported = mutate_store_with_retry_using(
            STORE_MUTATION_MAX_ATTEMPTS,
            || load_store_path(&store_path),
            |candidate| {
                if inject_concurrent_commit.replace(false) {
                    let mut concurrent = load_store_path(&store_path)?;
                    concurrent.smart_connect_enabled = true;
                    save_store_path_cas_atomic(&store_path, &concurrent)?;
                }
                save_store_path_cas_atomic(&store_path, candidate)
            },
            |store| apply_profile_import(store, &profile),
        )
        .expect("bounded reload/reapply must commit after one conflict");

        assert!(imported);
        let persisted = load_store_path(&store_path).expect("committed store must load");
        assert!(persisted.smart_connect_enabled);
        assert_eq!(persisted.profiles.len(), 1);
        assert_eq!(persisted.profiles[0].id, profile.id);
        let revision_after_import = persisted.store_revision;

        let duplicate_imported = mutate_store_with_retry_using(
            STORE_MUTATION_MAX_ATTEMPTS,
            || load_store_path(&store_path),
            |candidate| save_store_path_cas_atomic(&store_path, candidate),
            |store| apply_profile_import(store, &profile),
        )
        .expect("duplicate check must be stable");
        assert!(!duplicate_imported);
        assert_eq!(
            load_store_path(&store_path).unwrap().store_revision,
            revision_after_import,
            "dedupe must not emit a new store commit"
        );
        fs::remove_dir_all(directory).expect("fixture directory should be removed");
    }

    #[test]
    fn legacy_subscription_url_migration_sanitizes_store_only_after_secure_writes() {
        let directory = std::env::temp_dir().join(format!(
            "cybervpn-subscription-migrate-{}",
            uuid::Uuid::new_v4()
        ));
        let store_path = directory.join("store.json");
        let subscription_id = "b831381d-6324-4d53-ad4f-8cda48b30811";
        let secret_url = "https://203.0.114.1/bearer-token";
        write_legacy_store(
            &store_path,
            serde_json::json!([{
                "id": subscription_id,
                "name": "Primary",
                "url": secret_url,
                "autoUpdate": true,
                "lastUpdated": 42
            }]),
        );
        let mut store = load_store_path(&store_path).expect("legacy store must parse");
        let written = std::cell::RefCell::new(Vec::new());

        let migrated = migrate_legacy_subscription_urls_with(&store_path, &mut store, |id, url| {
            written.borrow_mut().push((id.to_string(), url.to_string()));
            Ok(())
        })
        .expect("migration must succeed");

        assert!(migrated);
        assert_eq!(
            written.into_inner(),
            vec![(subscription_id.to_string(), secret_url.to_string())]
        );
        assert!(store.subscriptions[0].legacy_url.is_none());
        let persisted = fs::read_to_string(&store_path).expect("sanitized store must be readable");
        assert!(!persisted.contains("bearer-token"));
        assert!(
            serde_json::from_str::<serde_json::Value>(&persisted).unwrap()["subscriptions"][0]
                .get("url")
                .is_none()
        );
        fs::remove_dir_all(directory).expect("fixture directory should be removed");
    }

    #[test]
    fn failed_legacy_subscription_migration_preserves_recoverable_source_without_ui_exposure() {
        let directory = std::env::temp_dir().join(format!(
            "cybervpn-subscription-migrate-failure-{}",
            uuid::Uuid::new_v4()
        ));
        let store_path = directory.join("store.json");
        let secret_url = "https://203.0.114.1/recoverable-bearer-token";
        let original = write_legacy_store(
            &store_path,
            serde_json::json!([{
                "id": "b831381d-6324-4d53-ad4f-8cda48b30811",
                "name": "Primary",
                "url": secret_url,
                "autoUpdate": true,
                "lastUpdated": null
            }]),
        );
        let mut store = load_store_path(&store_path).expect("legacy store must parse");

        let error = migrate_legacy_subscription_urls_with(&store_path, &mut store, |_id, _url| {
            Err(AppError::System(
                "Synthetic secure storage failure".to_string(),
            ))
        })
        .expect_err("failed secure storage must abort migration");

        assert!(!error.to_string().contains("recoverable-bearer-token"));
        assert_eq!(fs::read(&store_path).unwrap(), original);
        assert_eq!(
            store.subscriptions[0].legacy_url.as_deref(),
            Some(secret_url)
        );
        let summary = serde_json::to_string(&crate::ipc::models::SubscriptionSummary::from(
            &store.subscriptions[0],
        ))
        .expect("summary must serialize");
        assert!(!summary.contains("url"));
        assert!(!summary.contains("recoverable-bearer-token"));
        fs::remove_dir_all(directory).expect("fixture directory should be removed");
    }

    #[test]
    fn duplicate_legacy_subscription_ids_fail_before_any_secure_write() {
        let directory = std::env::temp_dir().join(format!(
            "cybervpn-subscription-migrate-duplicate-{}",
            uuid::Uuid::new_v4()
        ));
        let store_path = directory.join("store.json");
        let duplicate_id = "b831381d-6324-4d53-ad4f-8cda48b30811";
        let original = write_legacy_store(
            &store_path,
            serde_json::json!([
                {
                    "id": duplicate_id,
                    "name": "One",
                    "url": "https://203.0.114.1/one",
                    "autoUpdate": true,
                    "lastUpdated": null
                },
                {
                    "id": duplicate_id,
                    "name": "Two",
                    "url": "https://203.0.114.1/two",
                    "autoUpdate": false,
                    "lastUpdated": null
                }
            ]),
        );
        let mut store = load_store_path(&store_path).expect("legacy store must parse");
        let writes = std::cell::Cell::new(0_u32);

        let error = migrate_legacy_subscription_urls_with(&store_path, &mut store, |_id, _url| {
            writes.set(writes.get() + 1);
            Ok(())
        })
        .expect_err("duplicate IDs must fail closed");

        assert!(error.to_string().contains("Duplicate subscription IDs"));
        assert_eq!(writes.get(), 0);
        assert_eq!(fs::read(&store_path).unwrap(), original);
        fs::remove_dir_all(directory).expect("fixture directory should be removed");
    }
}
