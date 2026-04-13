#![forbid(unsafe_code)]

mod service;

use async_trait::async_trait;
use ns_core::{DeviceBindingId, ManifestId, ValidationError};
use parking_lot::RwLock;
use rusqlite::{Connection, OptionalExtension, TransactionBehavior, params};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::{HashMap, HashSet};
use std::fs;
use std::io;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Duration as StdDuration;
use thiserror::Error;

pub use service::{
    BridgeStoreServiceHealthResponse, HttpServiceBackedBridgeStoreAdapter,
    build_service_backed_bridge_store_router,
};

#[derive(Debug, Error)]
pub enum StorageError {
    #[error("bootstrap grant not found")]
    BootstrapGrantNotFound,
    #[error("refresh credential not found")]
    RefreshCredentialNotFound,
    #[error("validation failed: {0}")]
    Validation(#[from] ValidationError),
    #[error("failed to read bridge store state from {path}: {source}")]
    ReadState {
        path: String,
        #[source]
        source: io::Error,
    },
    #[error("failed to create bridge store directory {path}: {source}")]
    CreateDirectory {
        path: String,
        #[source]
        source: io::Error,
    },
    #[error("failed to parse bridge store state from {path}: {source}")]
    ParseState {
        path: String,
        #[source]
        source: serde_json::Error,
    },
    #[error("failed to serialize bridge store state for {path}: {source}")]
    SerializeState {
        path: String,
        #[source]
        source: serde_json::Error,
    },
    #[error("failed to persist bridge store state to {path}: {source}")]
    WriteState {
        path: String,
        #[source]
        source: io::Error,
    },
    #[error("failed to serialize bridge metadata for key {key}: {source}")]
    SerializeMetadata {
        key: String,
        #[source]
        source: serde_json::Error,
    },
    #[error("failed to open sqlite bridge store at {path}: {source}")]
    OpenDatabase {
        path: String,
        #[source]
        source: rusqlite::Error,
    },
    #[error("sqlite bridge store at {path} failed: {source}")]
    Database {
        path: String,
        #[source]
        source: rusqlite::Error,
    },
    #[error("invalid service-backed bridge store config field {0}")]
    InvalidServiceConfig(&'static str),
    #[error("service-backed bridge store backend is unavailable for {operation} via {endpoint}")]
    ServiceBackendUnavailable {
        endpoint: String,
        operation: &'static str,
    },
    #[error(
        "service-backed bridge store request to {endpoint} failed during {operation}: {source}"
    )]
    ServiceRequest {
        endpoint: String,
        operation: &'static str,
        #[source]
        source: reqwest::Error,
    },
    #[error(
        "service-backed bridge store at {endpoint} returned HTTP {status} during {operation}: {message}"
    )]
    ServiceResponseStatus {
        endpoint: String,
        operation: &'static str,
        status: u16,
        message: String,
    },
    #[error(
        "service-backed bridge store at {endpoint} returned an unexpected response during {operation}: {response}"
    )]
    UnexpectedServiceResponse {
        endpoint: String,
        operation: &'static str,
        response: String,
    },
    #[error("bridge store state file used unsupported schema version {0}")]
    UnsupportedSchemaVersion(u16),
    #[error("sqlite bridge store contained invalid state: {0}")]
    InvalidDatabaseState(String),
}

const BRIDGE_STORE_SCHEMA_VERSION: u16 = 1;
const SQLITE_BUSY_TIMEOUT_MS: u64 = 5_000;
const SQLITE_STATUS_ACTIVE: i64 = 1;
const SQLITE_STATUS_REVOKED: i64 = 2;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum StoredDeviceStatus {
    Active,
    Revoked,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct StoredDeviceRecord {
    pub account_id: String,
    pub device_id: DeviceBindingId,
    pub status: StoredDeviceStatus,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RefreshCredentialRecord {
    pub account_id: String,
    pub device_id: DeviceBindingId,
    pub manifest_id: ManifestId,
    pub revoked: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct BootstrapGrantRecord {
    pub account_id: String,
    pub manifest_id: ManifestId,
    pub expires_at_unix: i64,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum BootstrapGrantConsumeOutcome {
    Consumed(BootstrapGrantRecord),
    Expired(BootstrapGrantRecord),
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct DeviceRegistrationStoreRequest {
    pub device: StoredDeviceRecord,
    pub refresh_credential: String,
    pub refresh_record: RefreshCredentialRecord,
    pub max_devices: Option<u32>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum DeviceRegistrationStoreOutcome {
    Stored,
    DeviceRevoked,
    DeviceLimitReached { max_devices: u32 },
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum BridgeStoreDeploymentScope {
    LocalOnly,
    SharedDurable,
}

#[async_trait]
pub trait BridgeStore: Send + Sync {
    async fn remember_bootstrap_redemption(&self, subject: &str) -> Result<bool, StorageError>;
    async fn store_bootstrap_grant(
        &self,
        credential: &str,
        record: BootstrapGrantRecord,
    ) -> Result<(), StorageError>;
    async fn consume_bootstrap_grant(
        &self,
        credential: &str,
        now_unix: i64,
    ) -> Result<BootstrapGrantConsumeOutcome, StorageError>;
    async fn register_device_with_refresh(
        &self,
        request: DeviceRegistrationStoreRequest,
    ) -> Result<DeviceRegistrationStoreOutcome, StorageError>;
    async fn upsert_device(&self, record: StoredDeviceRecord) -> Result<(), StorageError>;
    async fn load_device(
        &self,
        account_id: &str,
        device_id: &DeviceBindingId,
    ) -> Result<Option<StoredDeviceRecord>, StorageError>;
    async fn count_active_devices(&self, account_id: &str) -> Result<usize, StorageError>;
    async fn store_refresh_credential(
        &self,
        credential: &str,
        record: RefreshCredentialRecord,
    ) -> Result<(), StorageError>;
    async fn load_refresh_credential(
        &self,
        credential: &str,
    ) -> Result<RefreshCredentialRecord, StorageError>;
    async fn remember_webhook(&self, fingerprint: &str) -> Result<bool, StorageError>;
    async fn put_metadata(&self, key: &str, value: Value) -> Result<(), StorageError>;
}

pub trait BridgeStoreBackend: BridgeStore + Send + Sync {
    fn backend_name(&self) -> &'static str;
    fn deployment_scope(&self) -> BridgeStoreDeploymentScope;
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ServiceBackedBridgeStoreConfig {
    pub endpoint: String,
    pub request_timeout_ms: u64,
    pub auth_token: Option<String>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub fallback_endpoints: Vec<String>,
}

impl ServiceBackedBridgeStoreConfig {
    pub fn new(endpoint: impl Into<String>, request_timeout_ms: u64) -> Result<Self, StorageError> {
        let endpoint = endpoint.into();
        validate_service_endpoint("endpoint", &endpoint)?;
        if request_timeout_ms == 0 {
            return Err(StorageError::InvalidServiceConfig("request_timeout_ms"));
        }
        Ok(Self {
            endpoint,
            request_timeout_ms,
            auth_token: None,
            fallback_endpoints: Vec::new(),
        })
    }

    pub fn request_timeout(&self) -> StdDuration {
        StdDuration::from_millis(self.request_timeout_ms)
    }

    pub fn with_auth_token(mut self, auth_token: impl Into<String>) -> Result<Self, StorageError> {
        let auth_token = auth_token.into();
        if auth_token.trim().is_empty() {
            return Err(StorageError::InvalidServiceConfig("auth_token"));
        }
        self.auth_token = Some(auth_token);
        Ok(self)
    }

    pub fn auth_token(&self) -> Option<&str> {
        self.auth_token.as_deref()
    }

    pub fn with_fallback_endpoint(
        mut self,
        endpoint: impl Into<String>,
    ) -> Result<Self, StorageError> {
        let endpoint = endpoint.into();
        validate_service_endpoint("fallback_endpoint", &endpoint)?;
        if endpoint != self.endpoint
            && !self
                .fallback_endpoints
                .iter()
                .any(|value| value == &endpoint)
        {
            self.fallback_endpoints.push(endpoint);
        }
        Ok(self)
    }

    pub(crate) fn endpoint_configs(&self) -> Vec<Self> {
        let mut configs = Vec::with_capacity(1 + self.fallback_endpoints.len());
        configs.push(self.clone_for_endpoint(self.endpoint.clone()));
        configs.extend(
            self.fallback_endpoints
                .iter()
                .cloned()
                .map(|endpoint| self.clone_for_endpoint(endpoint)),
        );
        configs
    }

    fn clone_for_endpoint(&self, endpoint: String) -> Self {
        Self {
            endpoint,
            request_timeout_ms: self.request_timeout_ms,
            auth_token: self.auth_token.clone(),
            fallback_endpoints: Vec::new(),
        }
    }
}

#[async_trait]
pub trait ServiceBackedBridgeStoreAdapter: Send + Sync {
    async fn check_health(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
    ) -> Result<(), StorageError>;
    async fn remember_bootstrap_redemption(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        subject: &str,
    ) -> Result<bool, StorageError>;
    async fn store_bootstrap_grant(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        credential: &str,
        record: BootstrapGrantRecord,
    ) -> Result<(), StorageError>;
    async fn consume_bootstrap_grant(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        credential: &str,
        now_unix: i64,
    ) -> Result<BootstrapGrantConsumeOutcome, StorageError>;
    async fn register_device_with_refresh(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        request: DeviceRegistrationStoreRequest,
    ) -> Result<DeviceRegistrationStoreOutcome, StorageError>;
    async fn upsert_device(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        record: StoredDeviceRecord,
    ) -> Result<(), StorageError>;
    async fn load_device(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        account_id: &str,
        device_id: &DeviceBindingId,
    ) -> Result<Option<StoredDeviceRecord>, StorageError>;
    async fn count_active_devices(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        account_id: &str,
    ) -> Result<usize, StorageError>;
    async fn store_refresh_credential(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        credential: &str,
        record: RefreshCredentialRecord,
    ) -> Result<(), StorageError>;
    async fn load_refresh_credential(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        credential: &str,
    ) -> Result<RefreshCredentialRecord, StorageError>;
    async fn remember_webhook(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        fingerprint: &str,
    ) -> Result<bool, StorageError>;
    async fn put_metadata(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        key: &str,
        value: Value,
    ) -> Result<(), StorageError>;
}

#[derive(Clone)]
pub struct SharedBridgeStore {
    backend: Arc<dyn BridgeStoreBackend>,
}

impl SharedBridgeStore {
    pub fn new<B>(backend: B) -> Self
    where
        B: BridgeStoreBackend + 'static,
    {
        Self {
            backend: Arc::new(backend),
        }
    }

    pub fn backend_name(&self) -> &'static str {
        self.backend.backend_name()
    }

    pub fn deployment_scope(&self) -> BridgeStoreDeploymentScope {
        self.backend.deployment_scope()
    }
}

#[derive(Clone)]
pub struct ServiceBackedBridgeStore {
    config: ServiceBackedBridgeStoreConfig,
    adapter: Arc<dyn ServiceBackedBridgeStoreAdapter>,
}

impl ServiceBackedBridgeStore {
    pub fn new(
        config: ServiceBackedBridgeStoreConfig,
        adapter: Arc<dyn ServiceBackedBridgeStoreAdapter>,
    ) -> Self {
        Self { config, adapter }
    }

    pub fn unavailable(config: ServiceBackedBridgeStoreConfig) -> Self {
        Self::new(config, Arc::new(UnavailableServiceBackedBridgeStoreAdapter))
    }

    pub fn config(&self) -> &ServiceBackedBridgeStoreConfig {
        &self.config
    }

    pub async fn check_health(&self) -> Result<(), StorageError> {
        self.adapter.check_health(&self.config).await
    }
}

#[derive(Clone, Default)]
pub struct UnavailableServiceBackedBridgeStoreAdapter;

impl UnavailableServiceBackedBridgeStoreAdapter {
    fn unavailable(
        config: &ServiceBackedBridgeStoreConfig,
        operation: &'static str,
    ) -> StorageError {
        StorageError::ServiceBackendUnavailable {
            endpoint: config.endpoint.clone(),
            operation,
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
struct PersistedBridgeStoreState {
    schema_version: u16,
    redeemed_bootstrap_subjects: HashSet<String>,
    bootstrap_grants: HashMap<String, BootstrapGrantRecord>,
    devices: HashMap<String, StoredDeviceRecord>,
    refresh_credentials: HashMap<String, RefreshCredentialRecord>,
    seen_webhooks: HashSet<String>,
    metadata: HashMap<String, Value>,
}

impl Default for PersistedBridgeStoreState {
    fn default() -> Self {
        Self {
            schema_version: BRIDGE_STORE_SCHEMA_VERSION,
            redeemed_bootstrap_subjects: HashSet::new(),
            bootstrap_grants: HashMap::new(),
            devices: HashMap::new(),
            refresh_credentials: HashMap::new(),
            seen_webhooks: HashSet::new(),
            metadata: HashMap::new(),
        }
    }
}

#[derive(Clone, Default)]
pub struct InMemoryBridgeStore {
    redeemed_bootstrap_subjects: Arc<RwLock<HashSet<String>>>,
    bootstrap_grants: Arc<RwLock<HashMap<String, BootstrapGrantRecord>>>,
    devices: Arc<RwLock<HashMap<String, StoredDeviceRecord>>>,
    refresh_credentials: Arc<RwLock<HashMap<String, RefreshCredentialRecord>>>,
    seen_webhooks: Arc<RwLock<HashSet<String>>>,
    metadata: Arc<RwLock<HashMap<String, Value>>>,
}

impl InMemoryBridgeStore {
    fn digest(input: &str) -> String {
        let mut hasher = Sha256::new();
        hasher.update(input.as_bytes());
        let digest = hasher.finalize();
        format!("{digest:x}")
    }
}

#[derive(Clone)]
pub struct FileBackedBridgeStore {
    path: Arc<PathBuf>,
    state: Arc<RwLock<PersistedBridgeStoreState>>,
}

#[derive(Clone)]
pub struct SqliteBridgeStore {
    path: Arc<PathBuf>,
}

impl FileBackedBridgeStore {
    pub fn open(path: impl Into<PathBuf>) -> Result<Self, StorageError> {
        let path = path.into();
        let state = Self::load_state(&path)?;
        let store = Self {
            path: Arc::new(path),
            state: Arc::new(RwLock::new(state)),
        };
        store.persist()?;
        Ok(store)
    }

    pub fn path(&self) -> &Path {
        self.path.as_ref().as_path()
    }

    fn digest(input: &str) -> String {
        InMemoryBridgeStore::digest(input)
    }

    fn load_state(path: &Path) -> Result<PersistedBridgeStoreState, StorageError> {
        if !path.exists() {
            return Ok(PersistedBridgeStoreState::default());
        }

        let raw = fs::read(path).map_err(|source| StorageError::ReadState {
            path: path.display().to_string(),
            source,
        })?;
        let state: PersistedBridgeStoreState =
            serde_json::from_slice(&raw).map_err(|source| StorageError::ParseState {
                path: path.display().to_string(),
                source,
            })?;
        if state.schema_version != BRIDGE_STORE_SCHEMA_VERSION {
            return Err(StorageError::UnsupportedSchemaVersion(state.schema_version));
        }
        Ok(state)
    }

    fn persist(&self) -> Result<(), StorageError> {
        let snapshot = self.state.read().clone();
        let path = self.path.as_ref();
        if let Some(parent) = path.parent()
            && !parent.as_os_str().is_empty()
        {
            fs::create_dir_all(parent).map_err(|source| StorageError::CreateDirectory {
                path: parent.display().to_string(),
                source,
            })?;
        }

        let encoded = serde_json::to_vec_pretty(&snapshot).map_err(|source| {
            StorageError::SerializeState {
                path: path.display().to_string(),
                source,
            }
        })?;
        let temp_path = temporary_state_path(path);
        fs::write(&temp_path, encoded).map_err(|source| StorageError::WriteState {
            path: temp_path.display().to_string(),
            source,
        })?;
        if path.exists() {
            fs::remove_file(path).map_err(|source| StorageError::WriteState {
                path: path.display().to_string(),
                source,
            })?;
        }
        fs::rename(&temp_path, path).map_err(|source| StorageError::WriteState {
            path: path.display().to_string(),
            source,
        })?;
        Ok(())
    }
}

#[async_trait]
impl BridgeStore for InMemoryBridgeStore {
    async fn remember_bootstrap_redemption(&self, subject: &str) -> Result<bool, StorageError> {
        let mut guard = self.redeemed_bootstrap_subjects.write();
        Ok(guard.insert(Self::digest(subject)))
    }

    async fn store_bootstrap_grant(
        &self,
        credential: &str,
        record: BootstrapGrantRecord,
    ) -> Result<(), StorageError> {
        self.bootstrap_grants
            .write()
            .insert(Self::digest(credential), record);
        Ok(())
    }

    async fn consume_bootstrap_grant(
        &self,
        credential: &str,
        now_unix: i64,
    ) -> Result<BootstrapGrantConsumeOutcome, StorageError> {
        let record = self
            .bootstrap_grants
            .write()
            .remove(&Self::digest(credential))
            .ok_or(StorageError::BootstrapGrantNotFound)?;
        if record.expires_at_unix <= now_unix {
            return Ok(BootstrapGrantConsumeOutcome::Expired(record));
        }
        Ok(BootstrapGrantConsumeOutcome::Consumed(record))
    }

    async fn register_device_with_refresh(
        &self,
        request: DeviceRegistrationStoreRequest,
    ) -> Result<DeviceRegistrationStoreOutcome, StorageError> {
        let device_key = Self::digest(&device_lookup_key(
            &request.device.account_id,
            &request.device.device_id,
        ));
        {
            let mut devices = self.devices.write();
            match devices.get(&device_key) {
                Some(existing) if existing.status == StoredDeviceStatus::Revoked => {
                    return Ok(DeviceRegistrationStoreOutcome::DeviceRevoked);
                }
                Some(_) => {}
                None => {
                    if let Some(limit) = request.max_devices {
                        let active_device_count = devices
                            .values()
                            .filter(|record| {
                                record.account_id == request.device.account_id
                                    && record.status == StoredDeviceStatus::Active
                            })
                            .count();
                        if active_device_count >= limit as usize {
                            return Ok(DeviceRegistrationStoreOutcome::DeviceLimitReached {
                                max_devices: limit,
                            });
                        }
                    }
                }
            }
            devices.insert(device_key, request.device.clone());
        }
        self.refresh_credentials.write().insert(
            Self::digest(&request.refresh_credential),
            request.refresh_record,
        );
        Ok(DeviceRegistrationStoreOutcome::Stored)
    }

    async fn upsert_device(&self, record: StoredDeviceRecord) -> Result<(), StorageError> {
        self.devices.write().insert(
            Self::digest(&device_lookup_key(&record.account_id, &record.device_id)),
            record,
        );
        Ok(())
    }

    async fn load_device(
        &self,
        account_id: &str,
        device_id: &DeviceBindingId,
    ) -> Result<Option<StoredDeviceRecord>, StorageError> {
        Ok(self
            .devices
            .read()
            .get(&Self::digest(&device_lookup_key(account_id, device_id)))
            .cloned())
    }

    async fn count_active_devices(&self, account_id: &str) -> Result<usize, StorageError> {
        Ok(self
            .devices
            .read()
            .values()
            .filter(|record| {
                record.account_id == account_id && record.status == StoredDeviceStatus::Active
            })
            .count())
    }

    async fn store_refresh_credential(
        &self,
        credential: &str,
        record: RefreshCredentialRecord,
    ) -> Result<(), StorageError> {
        self.refresh_credentials
            .write()
            .insert(Self::digest(credential), record);
        Ok(())
    }

    async fn load_refresh_credential(
        &self,
        credential: &str,
    ) -> Result<RefreshCredentialRecord, StorageError> {
        self.refresh_credentials
            .read()
            .get(&Self::digest(credential))
            .cloned()
            .ok_or(StorageError::RefreshCredentialNotFound)
    }

    async fn remember_webhook(&self, fingerprint: &str) -> Result<bool, StorageError> {
        Ok(self.seen_webhooks.write().insert(Self::digest(fingerprint)))
    }

    async fn put_metadata(&self, key: &str, value: Value) -> Result<(), StorageError> {
        self.metadata.write().insert(key.to_owned(), value);
        Ok(())
    }
}

#[async_trait]
impl BridgeStore for FileBackedBridgeStore {
    async fn remember_bootstrap_redemption(&self, subject: &str) -> Result<bool, StorageError> {
        let inserted = {
            let mut guard = self.state.write();
            guard
                .redeemed_bootstrap_subjects
                .insert(Self::digest(subject))
        };
        self.persist()?;
        Ok(inserted)
    }

    async fn store_bootstrap_grant(
        &self,
        credential: &str,
        record: BootstrapGrantRecord,
    ) -> Result<(), StorageError> {
        {
            let mut guard = self.state.write();
            guard
                .bootstrap_grants
                .insert(Self::digest(credential), record);
        }
        self.persist()
    }

    async fn consume_bootstrap_grant(
        &self,
        credential: &str,
        now_unix: i64,
    ) -> Result<BootstrapGrantConsumeOutcome, StorageError> {
        let record = {
            let mut guard = self.state.write();
            guard
                .bootstrap_grants
                .remove(&Self::digest(credential))
                .ok_or(StorageError::BootstrapGrantNotFound)?
        };
        self.persist()?;
        if record.expires_at_unix <= now_unix {
            return Ok(BootstrapGrantConsumeOutcome::Expired(record));
        }
        Ok(BootstrapGrantConsumeOutcome::Consumed(record))
    }

    async fn register_device_with_refresh(
        &self,
        request: DeviceRegistrationStoreRequest,
    ) -> Result<DeviceRegistrationStoreOutcome, StorageError> {
        let device_key = Self::digest(&device_lookup_key(
            &request.device.account_id,
            &request.device.device_id,
        ));
        let outcome = {
            let mut guard = self.state.write();
            match guard.devices.get(&device_key) {
                Some(existing) if existing.status == StoredDeviceStatus::Revoked => {
                    DeviceRegistrationStoreOutcome::DeviceRevoked
                }
                Some(_) => {
                    guard.devices.insert(device_key, request.device.clone());
                    guard.refresh_credentials.insert(
                        Self::digest(&request.refresh_credential),
                        request.refresh_record,
                    );
                    DeviceRegistrationStoreOutcome::Stored
                }
                None => {
                    if let Some(limit) = request.max_devices {
                        let active_device_count = guard
                            .devices
                            .values()
                            .filter(|record| {
                                record.account_id == request.device.account_id
                                    && record.status == StoredDeviceStatus::Active
                            })
                            .count();
                        if active_device_count >= limit as usize {
                            DeviceRegistrationStoreOutcome::DeviceLimitReached {
                                max_devices: limit,
                            }
                        } else {
                            guard.devices.insert(device_key, request.device.clone());
                            guard.refresh_credentials.insert(
                                Self::digest(&request.refresh_credential),
                                request.refresh_record,
                            );
                            DeviceRegistrationStoreOutcome::Stored
                        }
                    } else {
                        guard.devices.insert(device_key, request.device.clone());
                        guard.refresh_credentials.insert(
                            Self::digest(&request.refresh_credential),
                            request.refresh_record,
                        );
                        DeviceRegistrationStoreOutcome::Stored
                    }
                }
            }
        };
        if matches!(outcome, DeviceRegistrationStoreOutcome::Stored) {
            self.persist()?;
        }
        Ok(outcome)
    }

    async fn upsert_device(&self, record: StoredDeviceRecord) -> Result<(), StorageError> {
        let key = device_lookup_key(&record.account_id, &record.device_id);
        {
            let mut guard = self.state.write();
            guard.devices.insert(Self::digest(&key), record);
        }
        self.persist()
    }

    async fn load_device(
        &self,
        account_id: &str,
        device_id: &DeviceBindingId,
    ) -> Result<Option<StoredDeviceRecord>, StorageError> {
        let key = device_lookup_key(account_id, device_id);
        Ok(self.state.read().devices.get(&Self::digest(&key)).cloned())
    }

    async fn count_active_devices(&self, account_id: &str) -> Result<usize, StorageError> {
        Ok(self
            .state
            .read()
            .devices
            .values()
            .filter(|record| {
                record.account_id == account_id && record.status == StoredDeviceStatus::Active
            })
            .count())
    }

    async fn store_refresh_credential(
        &self,
        credential: &str,
        record: RefreshCredentialRecord,
    ) -> Result<(), StorageError> {
        {
            let mut guard = self.state.write();
            guard
                .refresh_credentials
                .insert(Self::digest(credential), record);
        }
        self.persist()
    }

    async fn load_refresh_credential(
        &self,
        credential: &str,
    ) -> Result<RefreshCredentialRecord, StorageError> {
        self.state
            .read()
            .refresh_credentials
            .get(&Self::digest(credential))
            .cloned()
            .ok_or(StorageError::RefreshCredentialNotFound)
    }

    async fn remember_webhook(&self, fingerprint: &str) -> Result<bool, StorageError> {
        let inserted = {
            let mut guard = self.state.write();
            guard.seen_webhooks.insert(Self::digest(fingerprint))
        };
        self.persist()?;
        Ok(inserted)
    }

    async fn put_metadata(&self, key: &str, value: Value) -> Result<(), StorageError> {
        {
            let mut guard = self.state.write();
            guard.metadata.insert(key.to_owned(), value);
        }
        self.persist()
    }
}

impl SqliteBridgeStore {
    pub fn open(path: impl Into<PathBuf>) -> Result<Self, StorageError> {
        let path = path.into();
        if let Some(parent) = path.parent()
            && !parent.as_os_str().is_empty()
        {
            fs::create_dir_all(parent).map_err(|source| StorageError::CreateDirectory {
                path: parent.display().to_string(),
                source,
            })?;
        }

        open_initialized_sqlite_connection(&path)?;

        Ok(Self {
            path: Arc::new(path),
        })
    }

    pub fn path(&self) -> &Path {
        self.path.as_ref().as_path()
    }

    fn database_error(&self, source: rusqlite::Error) -> StorageError {
        StorageError::Database {
            path: self.path.display().to_string(),
            source,
        }
    }

    fn with_connection<T>(
        &self,
        operation: impl FnOnce(&Connection) -> Result<T, StorageError>,
    ) -> Result<T, StorageError> {
        let connection = open_initialized_sqlite_connection(&self.path)?;
        operation(&connection)
    }

    fn with_transaction<T>(
        &self,
        operation: impl FnOnce(&rusqlite::Transaction<'_>) -> Result<T, StorageError>,
    ) -> Result<T, StorageError> {
        let mut connection = open_initialized_sqlite_connection(&self.path)?;
        let transaction = connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(|source| self.database_error(source))?;
        let result = operation(&transaction)?;
        transaction
            .commit()
            .map_err(|source| self.database_error(source))?;
        Ok(result)
    }
}

#[async_trait]
impl BridgeStore for SqliteBridgeStore {
    async fn remember_bootstrap_redemption(&self, subject: &str) -> Result<bool, StorageError> {
        self.with_connection(|connection| {
            let rows_affected = connection
                .execute(
                    "INSERT INTO bootstrap_redemptions (subject_digest) VALUES (?1)
                     ON CONFLICT(subject_digest) DO NOTHING",
                    params![digest(subject)],
                )
                .map_err(|source| self.database_error(source))?;
            Ok(rows_affected > 0)
        })
    }

    async fn store_bootstrap_grant(
        &self,
        credential: &str,
        record: BootstrapGrantRecord,
    ) -> Result<(), StorageError> {
        self.with_connection(|connection| {
            connection
                .execute(
                    "INSERT INTO bootstrap_grants (
                         credential_digest,
                         account_id,
                         manifest_id,
                         expires_at_unix
                     ) VALUES (?1, ?2, ?3, ?4)
                     ON CONFLICT(credential_digest) DO UPDATE SET
                         account_id = excluded.account_id,
                         manifest_id = excluded.manifest_id,
                         expires_at_unix = excluded.expires_at_unix",
                    params![
                        digest(credential),
                        record.account_id,
                        record.manifest_id.as_str(),
                        record.expires_at_unix,
                    ],
                )
                .map_err(|source| self.database_error(source))?;
            Ok(())
        })
    }

    async fn consume_bootstrap_grant(
        &self,
        credential: &str,
        now_unix: i64,
    ) -> Result<BootstrapGrantConsumeOutcome, StorageError> {
        self.with_transaction(|transaction| {
            let record = transaction
                .query_row(
                    "SELECT account_id, manifest_id, expires_at_unix
                     FROM bootstrap_grants
                     WHERE credential_digest = ?1",
                    params![digest(credential)],
                    |row| {
                        Ok((
                            row.get::<_, String>(0)?,
                            row.get::<_, String>(1)?,
                            row.get::<_, i64>(2)?,
                        ))
                    },
                )
                .optional()
                .map_err(|source| self.database_error(source))?
                .ok_or(StorageError::BootstrapGrantNotFound)?;
            transaction
                .execute(
                    "DELETE FROM bootstrap_grants WHERE credential_digest = ?1",
                    params![digest(credential)],
                )
                .map_err(|source| self.database_error(source))?;

            let record = BootstrapGrantRecord {
                account_id: record.0,
                manifest_id: ManifestId::new(record.1)?,
                expires_at_unix: record.2,
            };
            if record.expires_at_unix <= now_unix {
                return Ok(BootstrapGrantConsumeOutcome::Expired(record));
            }
            Ok(BootstrapGrantConsumeOutcome::Consumed(record))
        })
    }

    async fn register_device_with_refresh(
        &self,
        request: DeviceRegistrationStoreRequest,
    ) -> Result<DeviceRegistrationStoreOutcome, StorageError> {
        self.with_transaction(|transaction| {
            let account_id = request.device.account_id.as_str();
            let device_id = request.device.device_id.as_str();
            let existing_status = transaction
                .query_row(
                    "SELECT status FROM devices WHERE account_id = ?1 AND device_id = ?2",
                    params![account_id, device_id],
                    |row| row.get::<_, i64>(0),
                )
                .optional()
                .map_err(|source| self.database_error(source))?;

            if let Some(status) = existing_status {
                if stored_device_status_from_sql(status)? == StoredDeviceStatus::Revoked {
                    return Ok(DeviceRegistrationStoreOutcome::DeviceRevoked);
                }
            } else if let Some(limit) = request.max_devices {
                let active_device_count = transaction
                    .query_row(
                        "SELECT COUNT(*) FROM devices WHERE account_id = ?1 AND status = ?2",
                        params![account_id, SQLITE_STATUS_ACTIVE],
                        |row| row.get::<_, i64>(0),
                    )
                    .map_err(|source| self.database_error(source))?;
                if active_device_count >= i64::from(limit) {
                    return Ok(DeviceRegistrationStoreOutcome::DeviceLimitReached {
                        max_devices: limit,
                    });
                }
            }

            transaction
                .execute(
                    "INSERT INTO devices (account_id, device_id, status) VALUES (?1, ?2, ?3)
                     ON CONFLICT(account_id, device_id) DO UPDATE SET status = excluded.status",
                    params![
                        account_id,
                        device_id,
                        stored_device_status_to_sql(request.device.status),
                    ],
                )
                .map_err(|source| self.database_error(source))?;
            transaction
                .execute(
                    "INSERT INTO refresh_credentials (
                         credential_digest,
                         account_id,
                         device_id,
                         manifest_id,
                         revoked
                     ) VALUES (?1, ?2, ?3, ?4, ?5)
                     ON CONFLICT(credential_digest) DO UPDATE SET
                         account_id = excluded.account_id,
                         device_id = excluded.device_id,
                         manifest_id = excluded.manifest_id,
                         revoked = excluded.revoked",
                    params![
                        digest(&request.refresh_credential),
                        request.refresh_record.account_id.as_str(),
                        request.refresh_record.device_id.as_str(),
                        request.refresh_record.manifest_id.as_str(),
                        if request.refresh_record.revoked {
                            1_i64
                        } else {
                            0_i64
                        },
                    ],
                )
                .map_err(|source| self.database_error(source))?;

            Ok(DeviceRegistrationStoreOutcome::Stored)
        })
    }

    async fn upsert_device(&self, record: StoredDeviceRecord) -> Result<(), StorageError> {
        self.with_connection(|connection| {
            connection
                .execute(
                    "INSERT INTO devices (account_id, device_id, status) VALUES (?1, ?2, ?3)
                     ON CONFLICT(account_id, device_id) DO UPDATE SET status = excluded.status",
                    params![
                        record.account_id,
                        record.device_id.as_str(),
                        stored_device_status_to_sql(record.status),
                    ],
                )
                .map_err(|source| self.database_error(source))?;
            Ok(())
        })
    }

    async fn load_device(
        &self,
        account_id: &str,
        device_id: &DeviceBindingId,
    ) -> Result<Option<StoredDeviceRecord>, StorageError> {
        self.with_connection(|connection| {
            let status = connection
                .query_row(
                    "SELECT status FROM devices WHERE account_id = ?1 AND device_id = ?2",
                    params![account_id, device_id.as_str()],
                    |row| row.get::<_, i64>(0),
                )
                .optional()
                .map_err(|source| self.database_error(source))?;

            status
                .map(stored_device_status_from_sql)
                .transpose()
                .map(|status| {
                    status.map(|status| StoredDeviceRecord {
                        account_id: account_id.to_owned(),
                        device_id: device_id.clone(),
                        status,
                    })
                })
        })
    }

    async fn count_active_devices(&self, account_id: &str) -> Result<usize, StorageError> {
        self.with_connection(|connection| {
            let active_device_count = connection
                .query_row(
                    "SELECT COUNT(*) FROM devices WHERE account_id = ?1 AND status = ?2",
                    params![account_id, SQLITE_STATUS_ACTIVE],
                    |row| row.get::<_, i64>(0),
                )
                .map_err(|source| self.database_error(source))?;
            usize::try_from(active_device_count)
                .map_err(|_| StorageError::InvalidDatabaseState("negative device count".to_owned()))
        })
    }

    async fn store_refresh_credential(
        &self,
        credential: &str,
        record: RefreshCredentialRecord,
    ) -> Result<(), StorageError> {
        self.with_connection(|connection| {
            connection
                .execute(
                    "INSERT INTO refresh_credentials (
                         credential_digest,
                         account_id,
                         device_id,
                         manifest_id,
                         revoked
                     ) VALUES (?1, ?2, ?3, ?4, ?5)
                     ON CONFLICT(credential_digest) DO UPDATE SET
                         account_id = excluded.account_id,
                         device_id = excluded.device_id,
                         manifest_id = excluded.manifest_id,
                         revoked = excluded.revoked",
                    params![
                        digest(credential),
                        record.account_id,
                        record.device_id.as_str(),
                        record.manifest_id.as_str(),
                        if record.revoked { 1_i64 } else { 0_i64 },
                    ],
                )
                .map_err(|source| self.database_error(source))?;
            Ok(())
        })
    }

    async fn load_refresh_credential(
        &self,
        credential: &str,
    ) -> Result<RefreshCredentialRecord, StorageError> {
        self.with_connection(|connection| {
            let row = connection
                .query_row(
                    "SELECT account_id, device_id, manifest_id, revoked
                     FROM refresh_credentials WHERE credential_digest = ?1",
                    params![digest(credential)],
                    |row| {
                        Ok((
                            row.get::<_, String>(0)?,
                            row.get::<_, String>(1)?,
                            row.get::<_, String>(2)?,
                            row.get::<_, i64>(3)?,
                        ))
                    },
                )
                .optional()
                .map_err(|source| self.database_error(source))?
                .ok_or(StorageError::RefreshCredentialNotFound)?;

            Ok(RefreshCredentialRecord {
                account_id: row.0,
                device_id: DeviceBindingId::new(row.1)?,
                manifest_id: ManifestId::new(row.2)?,
                revoked: row.3 != 0,
            })
        })
    }

    async fn remember_webhook(&self, fingerprint: &str) -> Result<bool, StorageError> {
        self.with_connection(|connection| {
            let rows_affected = connection
                .execute(
                    "INSERT INTO webhooks (fingerprint_digest) VALUES (?1)
                     ON CONFLICT(fingerprint_digest) DO NOTHING",
                    params![digest(fingerprint)],
                )
                .map_err(|source| self.database_error(source))?;
            Ok(rows_affected > 0)
        })
    }

    async fn put_metadata(&self, key: &str, value: Value) -> Result<(), StorageError> {
        let encoded =
            serde_json::to_string(&value).map_err(|source| StorageError::SerializeMetadata {
                key: key.to_owned(),
                source,
            })?;
        self.with_connection(|connection| {
            connection
                .execute(
                    "INSERT INTO metadata (key, value_json) VALUES (?1, ?2)
                     ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json",
                    params![key, encoded],
                )
                .map_err(|source| self.database_error(source))?;
            Ok(())
        })
    }
}

fn open_sqlite_connection(path: &Path) -> Result<Connection, StorageError> {
    let connection = Connection::open(path).map_err(|source| StorageError::OpenDatabase {
        path: path.display().to_string(),
        source,
    })?;
    connection
        .busy_timeout(StdDuration::from_millis(SQLITE_BUSY_TIMEOUT_MS))
        .map_err(|source| StorageError::Database {
            path: path.display().to_string(),
            source,
        })?;
    connection
        .pragma_update(None, "journal_mode", "WAL")
        .map_err(|source| StorageError::Database {
            path: path.display().to_string(),
            source,
        })?;
    connection
        .pragma_update(None, "synchronous", "NORMAL")
        .map_err(|source| StorageError::Database {
            path: path.display().to_string(),
            source,
        })?;
    connection
        .pragma_update(None, "foreign_keys", 1_i64)
        .map_err(|source| StorageError::Database {
            path: path.display().to_string(),
            source,
        })?;
    Ok(connection)
}

fn open_initialized_sqlite_connection(path: &Path) -> Result<Connection, StorageError> {
    let connection = open_sqlite_connection(path)?;
    initialize_sqlite_schema(&connection, path)?;
    Ok(connection)
}

fn initialize_sqlite_schema(connection: &Connection, path: &Path) -> Result<(), StorageError> {
    let version = connection
        .pragma_query_value(None, "user_version", |row| row.get::<_, u16>(0))
        .map_err(|source| StorageError::Database {
            path: path.display().to_string(),
            source,
        })?;
    if version != 0 && version != BRIDGE_STORE_SCHEMA_VERSION {
        return Err(StorageError::UnsupportedSchemaVersion(version));
    }

    connection
        .execute_batch(
            "
            CREATE TABLE IF NOT EXISTS bootstrap_redemptions (
                subject_digest TEXT PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS bootstrap_grants (
                credential_digest TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                manifest_id TEXT NOT NULL,
                expires_at_unix INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS devices (
                account_id TEXT NOT NULL,
                device_id TEXT NOT NULL,
                status INTEGER NOT NULL,
                PRIMARY KEY (account_id, device_id)
            );
            CREATE TABLE IF NOT EXISTS refresh_credentials (
                credential_digest TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                device_id TEXT NOT NULL,
                manifest_id TEXT NOT NULL,
                revoked INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS webhooks (
                fingerprint_digest TEXT PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL
            );
            ",
        )
        .map_err(|source| StorageError::Database {
            path: path.display().to_string(),
            source,
        })?;

    if version == 0 {
        connection
            .pragma_update(None, "user_version", BRIDGE_STORE_SCHEMA_VERSION)
            .map_err(|source| StorageError::Database {
                path: path.display().to_string(),
                source,
            })?;
    }
    Ok(())
}

#[async_trait]
impl BridgeStore for SharedBridgeStore {
    async fn remember_bootstrap_redemption(&self, subject: &str) -> Result<bool, StorageError> {
        BridgeStore::remember_bootstrap_redemption(self.backend.as_ref(), subject).await
    }

    async fn store_bootstrap_grant(
        &self,
        credential: &str,
        record: BootstrapGrantRecord,
    ) -> Result<(), StorageError> {
        BridgeStore::store_bootstrap_grant(self.backend.as_ref(), credential, record).await
    }

    async fn consume_bootstrap_grant(
        &self,
        credential: &str,
        now_unix: i64,
    ) -> Result<BootstrapGrantConsumeOutcome, StorageError> {
        BridgeStore::consume_bootstrap_grant(self.backend.as_ref(), credential, now_unix).await
    }

    async fn register_device_with_refresh(
        &self,
        request: DeviceRegistrationStoreRequest,
    ) -> Result<DeviceRegistrationStoreOutcome, StorageError> {
        BridgeStore::register_device_with_refresh(self.backend.as_ref(), request).await
    }

    async fn upsert_device(&self, record: StoredDeviceRecord) -> Result<(), StorageError> {
        BridgeStore::upsert_device(self.backend.as_ref(), record).await
    }

    async fn load_device(
        &self,
        account_id: &str,
        device_id: &DeviceBindingId,
    ) -> Result<Option<StoredDeviceRecord>, StorageError> {
        BridgeStore::load_device(self.backend.as_ref(), account_id, device_id).await
    }

    async fn count_active_devices(&self, account_id: &str) -> Result<usize, StorageError> {
        BridgeStore::count_active_devices(self.backend.as_ref(), account_id).await
    }

    async fn store_refresh_credential(
        &self,
        credential: &str,
        record: RefreshCredentialRecord,
    ) -> Result<(), StorageError> {
        BridgeStore::store_refresh_credential(self.backend.as_ref(), credential, record).await
    }

    async fn load_refresh_credential(
        &self,
        credential: &str,
    ) -> Result<RefreshCredentialRecord, StorageError> {
        BridgeStore::load_refresh_credential(self.backend.as_ref(), credential).await
    }

    async fn remember_webhook(&self, fingerprint: &str) -> Result<bool, StorageError> {
        BridgeStore::remember_webhook(self.backend.as_ref(), fingerprint).await
    }

    async fn put_metadata(&self, key: &str, value: Value) -> Result<(), StorageError> {
        BridgeStore::put_metadata(self.backend.as_ref(), key, value).await
    }
}

#[async_trait]
impl BridgeStore for ServiceBackedBridgeStore {
    async fn remember_bootstrap_redemption(&self, subject: &str) -> Result<bool, StorageError> {
        self.adapter
            .remember_bootstrap_redemption(&self.config, subject)
            .await
    }

    async fn store_bootstrap_grant(
        &self,
        credential: &str,
        record: BootstrapGrantRecord,
    ) -> Result<(), StorageError> {
        self.adapter
            .store_bootstrap_grant(&self.config, credential, record)
            .await
    }

    async fn consume_bootstrap_grant(
        &self,
        credential: &str,
        now_unix: i64,
    ) -> Result<BootstrapGrantConsumeOutcome, StorageError> {
        self.adapter
            .consume_bootstrap_grant(&self.config, credential, now_unix)
            .await
    }

    async fn register_device_with_refresh(
        &self,
        request: DeviceRegistrationStoreRequest,
    ) -> Result<DeviceRegistrationStoreOutcome, StorageError> {
        self.adapter
            .register_device_with_refresh(&self.config, request)
            .await
    }

    async fn upsert_device(&self, record: StoredDeviceRecord) -> Result<(), StorageError> {
        self.adapter.upsert_device(&self.config, record).await
    }

    async fn load_device(
        &self,
        account_id: &str,
        device_id: &DeviceBindingId,
    ) -> Result<Option<StoredDeviceRecord>, StorageError> {
        self.adapter
            .load_device(&self.config, account_id, device_id)
            .await
    }

    async fn count_active_devices(&self, account_id: &str) -> Result<usize, StorageError> {
        self.adapter
            .count_active_devices(&self.config, account_id)
            .await
    }

    async fn store_refresh_credential(
        &self,
        credential: &str,
        record: RefreshCredentialRecord,
    ) -> Result<(), StorageError> {
        self.adapter
            .store_refresh_credential(&self.config, credential, record)
            .await
    }

    async fn load_refresh_credential(
        &self,
        credential: &str,
    ) -> Result<RefreshCredentialRecord, StorageError> {
        self.adapter
            .load_refresh_credential(&self.config, credential)
            .await
    }

    async fn remember_webhook(&self, fingerprint: &str) -> Result<bool, StorageError> {
        self.adapter
            .remember_webhook(&self.config, fingerprint)
            .await
    }

    async fn put_metadata(&self, key: &str, value: Value) -> Result<(), StorageError> {
        self.adapter.put_metadata(&self.config, key, value).await
    }
}

#[async_trait]
impl ServiceBackedBridgeStoreAdapter for UnavailableServiceBackedBridgeStoreAdapter {
    async fn check_health(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
    ) -> Result<(), StorageError> {
        Err(Self::unavailable(config, "check_health"))
    }

    async fn remember_bootstrap_redemption(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        _subject: &str,
    ) -> Result<bool, StorageError> {
        Err(Self::unavailable(config, "remember_bootstrap_redemption"))
    }

    async fn store_bootstrap_grant(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        _credential: &str,
        _record: BootstrapGrantRecord,
    ) -> Result<(), StorageError> {
        Err(Self::unavailable(config, "store_bootstrap_grant"))
    }

    async fn consume_bootstrap_grant(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        _credential: &str,
        _now_unix: i64,
    ) -> Result<BootstrapGrantConsumeOutcome, StorageError> {
        Err(Self::unavailable(config, "consume_bootstrap_grant"))
    }

    async fn register_device_with_refresh(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        _request: DeviceRegistrationStoreRequest,
    ) -> Result<DeviceRegistrationStoreOutcome, StorageError> {
        Err(Self::unavailable(config, "register_device_with_refresh"))
    }

    async fn upsert_device(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        _record: StoredDeviceRecord,
    ) -> Result<(), StorageError> {
        Err(Self::unavailable(config, "upsert_device"))
    }

    async fn load_device(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        _account_id: &str,
        _device_id: &DeviceBindingId,
    ) -> Result<Option<StoredDeviceRecord>, StorageError> {
        Err(Self::unavailable(config, "load_device"))
    }

    async fn count_active_devices(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        _account_id: &str,
    ) -> Result<usize, StorageError> {
        Err(Self::unavailable(config, "count_active_devices"))
    }

    async fn store_refresh_credential(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        _credential: &str,
        _record: RefreshCredentialRecord,
    ) -> Result<(), StorageError> {
        Err(Self::unavailable(config, "store_refresh_credential"))
    }

    async fn load_refresh_credential(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        _credential: &str,
    ) -> Result<RefreshCredentialRecord, StorageError> {
        Err(Self::unavailable(config, "load_refresh_credential"))
    }

    async fn remember_webhook(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        _fingerprint: &str,
    ) -> Result<bool, StorageError> {
        Err(Self::unavailable(config, "remember_webhook"))
    }

    async fn put_metadata(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        _key: &str,
        _value: Value,
    ) -> Result<(), StorageError> {
        Err(Self::unavailable(config, "put_metadata"))
    }
}

impl BridgeStoreBackend for InMemoryBridgeStore {
    fn backend_name(&self) -> &'static str {
        "in_memory"
    }

    fn deployment_scope(&self) -> BridgeStoreDeploymentScope {
        BridgeStoreDeploymentScope::LocalOnly
    }
}

impl BridgeStoreBackend for FileBackedBridgeStore {
    fn backend_name(&self) -> &'static str {
        "file"
    }

    fn deployment_scope(&self) -> BridgeStoreDeploymentScope {
        BridgeStoreDeploymentScope::LocalOnly
    }
}

impl BridgeStoreBackend for SqliteBridgeStore {
    fn backend_name(&self) -> &'static str {
        "sqlite"
    }

    fn deployment_scope(&self) -> BridgeStoreDeploymentScope {
        BridgeStoreDeploymentScope::SharedDurable
    }
}

impl BridgeStoreBackend for ServiceBackedBridgeStore {
    fn backend_name(&self) -> &'static str {
        "service"
    }

    fn deployment_scope(&self) -> BridgeStoreDeploymentScope {
        BridgeStoreDeploymentScope::SharedDurable
    }
}

fn device_lookup_key(account_id: &str, device_id: &DeviceBindingId) -> String {
    format!("{account_id}:{}", device_id.as_str())
}

fn digest(input: &str) -> String {
    InMemoryBridgeStore::digest(input)
}

fn stored_device_status_to_sql(status: StoredDeviceStatus) -> i64 {
    match status {
        StoredDeviceStatus::Active => SQLITE_STATUS_ACTIVE,
        StoredDeviceStatus::Revoked => SQLITE_STATUS_REVOKED,
    }
}

fn stored_device_status_from_sql(status: i64) -> Result<StoredDeviceStatus, StorageError> {
    match status {
        SQLITE_STATUS_ACTIVE => Ok(StoredDeviceStatus::Active),
        SQLITE_STATUS_REVOKED => Ok(StoredDeviceStatus::Revoked),
        other => Err(StorageError::InvalidDatabaseState(format!(
            "unknown device status {other}"
        ))),
    }
}

fn temporary_state_path(path: &Path) -> PathBuf {
    let file_name = path
        .file_name()
        .and_then(|name| name.to_str())
        .map(|name| format!("{name}.tmp"))
        .unwrap_or_else(|| "bridge-store.tmp".to_owned());
    path.with_file_name(file_name)
}

fn validate_service_endpoint(
    field: &'static str,
    endpoint: &str,
) -> Result<reqwest::Url, StorageError> {
    if endpoint.trim().is_empty() {
        return Err(StorageError::InvalidServiceConfig(field));
    }
    let url =
        reqwest::Url::parse(endpoint).map_err(|_| StorageError::InvalidServiceConfig(field))?;
    if !matches!(url.scheme(), "http" | "https") {
        return Err(StorageError::InvalidServiceConfig(field));
    }
    Ok(url)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::ErrorKind;
    use std::sync::atomic::{AtomicU64, Ordering};

    fn unique_test_path_nonce() -> u64 {
        static NEXT_NONCE: AtomicU64 = AtomicU64::new(0);
        NEXT_NONCE.fetch_add(1, Ordering::Relaxed)
    }

    fn temporary_store_path() -> PathBuf {
        let mut path = std::env::temp_dir();
        let nonce = unique_test_path_nonce();
        path.push(format!(
            "northstar-bridge-store-{}-{nonce}.json",
            std::process::id()
        ));
        path
    }

    fn temporary_sqlite_store_path() -> PathBuf {
        let mut path = std::env::temp_dir();
        let nonce = unique_test_path_nonce();
        path.push(format!(
            "northstar-bridge-store-{}-{nonce}.sqlite3",
            std::process::id()
        ));
        path
    }

    fn cleanup_sqlite_store_path(path: &Path) {
        let candidates = [
            path.to_path_buf(),
            PathBuf::from(format!("{}-wal", path.display())),
            PathBuf::from(format!("{}-shm", path.display())),
        ];

        for _ in 0..10 {
            let mut busy = false;
            let mut remaining = false;

            for candidate in &candidates {
                if !candidate.exists() {
                    continue;
                }
                remaining = true;
                match fs::remove_file(candidate) {
                    Ok(()) => {}
                    Err(error)
                        if error.kind() == ErrorKind::NotFound
                            || error.raw_os_error() == Some(2) => {}
                    Err(error)
                        if error.kind() == ErrorKind::PermissionDenied
                            || error.raw_os_error() == Some(32) =>
                    {
                        busy = true;
                        break;
                    }
                    Err(error) => panic!(
                        "sqlite test store artifact should be removable ({}): {error}",
                        candidate.display()
                    ),
                }
            }

            if !busy && (!remaining || candidates.iter().all(|candidate| !candidate.exists())) {
                return;
            }

            std::thread::sleep(std::time::Duration::from_millis(25));
        }

        let remaining: Vec<String> = candidates
            .iter()
            .filter(|candidate| candidate.exists())
            .map(|candidate| candidate.display().to_string())
            .collect();
        panic!(
            "sqlite test store artifacts should be removable after retries: {}",
            remaining.join(", ")
        );
    }

    fn registration_request(
        account_id: &str,
        device_id: &str,
        refresh_credential: &str,
        manifest_id: &ManifestId,
        max_devices: Option<u32>,
    ) -> DeviceRegistrationStoreRequest {
        let device_id = DeviceBindingId::new(device_id).expect("fixture device id should be valid");
        DeviceRegistrationStoreRequest {
            device: StoredDeviceRecord {
                account_id: account_id.to_owned(),
                device_id: device_id.clone(),
                status: StoredDeviceStatus::Active,
            },
            refresh_credential: refresh_credential.to_owned(),
            refresh_record: RefreshCredentialRecord {
                account_id: account_id.to_owned(),
                device_id,
                manifest_id: manifest_id.clone(),
                revoked: false,
            },
            max_devices,
        }
    }

    #[tokio::test]
    async fn bootstrap_redemption_is_single_use() {
        let store = InMemoryBridgeStore::default();

        assert!(
            store
                .remember_bootstrap_redemption("sub-1")
                .await
                .expect("first bootstrap redemption should be stored")
        );
        assert!(
            !store
                .remember_bootstrap_redemption("sub-1")
                .await
                .expect("second bootstrap redemption should be recognized as duplicate")
        );
    }

    #[tokio::test]
    async fn bootstrap_grant_is_single_use_and_expires() {
        let store = InMemoryBridgeStore::default();
        let record = BootstrapGrantRecord {
            account_id: "acct-1".to_owned(),
            manifest_id: ManifestId::new("man-2026-04-01-001")
                .expect("fixture manifest id should be valid"),
            expires_at_unix: 1_775_002_260,
        };
        store
            .store_bootstrap_grant("btg_fixture", record.clone())
            .await
            .expect("bootstrap grant should store");

        assert!(matches!(
            store
                .consume_bootstrap_grant("btg_fixture", 1_775_002_200)
                .await
                .expect("bootstrap grant should consume"),
            BootstrapGrantConsumeOutcome::Consumed(consumed)
                if consumed.manifest_id == record.manifest_id
        ));
        assert!(matches!(
            store
                .consume_bootstrap_grant("btg_fixture", 1_775_002_200)
                .await,
            Err(StorageError::BootstrapGrantNotFound)
        ));

        store
            .store_bootstrap_grant(
                "btg_expired",
                BootstrapGrantRecord {
                    expires_at_unix: 1_775_002_199,
                    ..record
                },
            )
            .await
            .expect("expired bootstrap grant should store");
        assert!(matches!(
            store
                .consume_bootstrap_grant("btg_expired", 1_775_002_200)
                .await
                .expect("expired bootstrap grant should resolve"),
            BootstrapGrantConsumeOutcome::Expired(_)
        ));
    }

    #[tokio::test]
    async fn webhook_fingerprint_is_only_accepted_once() {
        let store = InMemoryBridgeStore::default();

        assert!(
            store
                .remember_webhook("evt-1:1775002200")
                .await
                .expect("first webhook fingerprint should be stored")
        );
        assert!(
            !store
                .remember_webhook("evt-1:1775002200")
                .await
                .expect("duplicate webhook fingerprint should be rejected")
        );
    }

    #[tokio::test]
    async fn device_records_can_be_upserted_loaded_and_counted() {
        let store = InMemoryBridgeStore::default();
        let active = StoredDeviceRecord {
            account_id: "acct-1".to_owned(),
            device_id: DeviceBindingId::new("device-1").expect("fixture device id should be valid"),
            status: StoredDeviceStatus::Active,
        };
        let revoked = StoredDeviceRecord {
            account_id: "acct-1".to_owned(),
            device_id: DeviceBindingId::new("device-2").expect("fixture device id should be valid"),
            status: StoredDeviceStatus::Revoked,
        };
        store
            .upsert_device(active.clone())
            .await
            .expect("active device should upsert");
        store
            .upsert_device(revoked.clone())
            .await
            .expect("revoked device should upsert");

        let loaded = store
            .load_device(
                "acct-1",
                &DeviceBindingId::new("device-1").expect("fixture device id should be valid"),
            )
            .await
            .expect("device lookup should succeed");
        assert!(matches!(loaded, Some(record) if record.status == StoredDeviceStatus::Active));
        assert_eq!(
            store
                .count_active_devices("acct-1")
                .await
                .expect("active-device count should succeed"),
            1
        );
    }

    #[tokio::test]
    async fn file_backed_store_persists_bridge_state_across_reopen() {
        let path = temporary_store_path();
        let device_id =
            DeviceBindingId::new("device-1").expect("fixture device id should be valid");
        let manifest_id =
            ManifestId::new("man-2026-04-01-001").expect("fixture manifest id should be valid");

        {
            let store = FileBackedBridgeStore::open(&path)
                .expect("file-backed bridge store should initialize");
            assert!(
                store
                    .remember_bootstrap_redemption("sub-1")
                    .await
                    .expect("bootstrap redemption should store")
            );
            store
                .upsert_device(StoredDeviceRecord {
                    account_id: "acct-1".to_owned(),
                    device_id: device_id.clone(),
                    status: StoredDeviceStatus::Active,
                })
                .await
                .expect("device should store");
            store
                .store_refresh_credential(
                    "rfr_fixture",
                    RefreshCredentialRecord {
                        account_id: "acct-1".to_owned(),
                        device_id: device_id.clone(),
                        manifest_id: manifest_id.clone(),
                        revoked: false,
                    },
                )
                .await
                .expect("refresh credential should store");
            assert!(
                store
                    .remember_webhook("evt-1:1775002200")
                    .await
                    .expect("webhook fingerprint should store")
            );
            store
                .put_metadata("policy_epoch", serde_json::json!({ "epoch": 7_u64 }))
                .await
                .expect("metadata should store");
        }

        let reopened =
            FileBackedBridgeStore::open(&path).expect("persisted bridge store should reopen");
        assert!(
            !reopened
                .remember_bootstrap_redemption("sub-1")
                .await
                .expect("bootstrap redemption should be single-use across reopen")
        );
        assert!(
            !reopened
                .remember_webhook("evt-1:1775002200")
                .await
                .expect("webhook fingerprint should remain single-use across reopen")
        );
        let loaded_device = reopened
            .load_device("acct-1", &device_id)
            .await
            .expect("device load should succeed after reopen");
        assert!(matches!(
            loaded_device,
            Some(StoredDeviceRecord {
                status: StoredDeviceStatus::Active,
                ..
            })
        ));
        assert_eq!(
            reopened
                .count_active_devices("acct-1")
                .await
                .expect("active-device count should persist"),
            1
        );
        let loaded_credential = reopened
            .load_refresh_credential("rfr_fixture")
            .await
            .expect("refresh credential should load after reopen");
        assert_eq!(loaded_credential.manifest_id, manifest_id);

        if path.exists() {
            fs::remove_file(&path).expect("test store should be removable");
        }
    }

    #[tokio::test]
    async fn sqlite_store_persists_bridge_state_across_reopen() {
        let path = temporary_sqlite_store_path();
        let device_id =
            DeviceBindingId::new("device-1").expect("fixture device id should be valid");
        let manifest_id =
            ManifestId::new("man-2026-04-01-001").expect("fixture manifest id should be valid");

        {
            let store =
                SqliteBridgeStore::open(&path).expect("sqlite bridge store should initialize");
            assert!(
                store
                    .remember_bootstrap_redemption("sub-1")
                    .await
                    .expect("bootstrap redemption should store")
            );
            assert_eq!(
                store
                    .register_device_with_refresh(DeviceRegistrationStoreRequest {
                        device: StoredDeviceRecord {
                            account_id: "acct-1".to_owned(),
                            device_id: device_id.clone(),
                            status: StoredDeviceStatus::Active,
                        },
                        refresh_credential: "rfr_fixture".to_owned(),
                        refresh_record: RefreshCredentialRecord {
                            account_id: "acct-1".to_owned(),
                            device_id: device_id.clone(),
                            manifest_id: manifest_id.clone(),
                            revoked: false,
                        },
                        max_devices: Some(2),
                    })
                    .await
                    .expect("device registration should store"),
                DeviceRegistrationStoreOutcome::Stored
            );
            assert!(
                store
                    .remember_webhook("evt-1:1775002200")
                    .await
                    .expect("webhook fingerprint should store")
            );
            store
                .put_metadata("policy_epoch", serde_json::json!({ "epoch": 7_u64 }))
                .await
                .expect("metadata should store");
        }

        let reopened = SqliteBridgeStore::open(&path).expect("sqlite bridge store should reopen");
        assert!(
            !reopened
                .remember_bootstrap_redemption("sub-1")
                .await
                .expect("bootstrap redemption should be single-use across reopen")
        );
        assert!(
            !reopened
                .remember_webhook("evt-1:1775002200")
                .await
                .expect("webhook fingerprint should remain single-use across reopen")
        );
        let loaded_device = reopened
            .load_device("acct-1", &device_id)
            .await
            .expect("device load should succeed after reopen");
        assert!(matches!(
            loaded_device,
            Some(StoredDeviceRecord {
                status: StoredDeviceStatus::Active,
                ..
            })
        ));
        assert_eq!(
            reopened
                .count_active_devices("acct-1")
                .await
                .expect("active-device count should persist"),
            1
        );
        let loaded_credential = reopened
            .load_refresh_credential("rfr_fixture")
            .await
            .expect("refresh credential should load after reopen");
        assert_eq!(loaded_credential.manifest_id, manifest_id);

        drop(reopened);
        cleanup_sqlite_store_path(path.as_path());
    }

    #[test]
    fn shared_bridge_store_reports_backend_scope() {
        let local = SharedBridgeStore::new(InMemoryBridgeStore::default());
        assert_eq!(local.backend_name(), "in_memory");
        assert_eq!(
            local.deployment_scope(),
            BridgeStoreDeploymentScope::LocalOnly
        );

        let path = temporary_sqlite_store_path();
        let durable = SharedBridgeStore::new(
            SqliteBridgeStore::open(&path).expect("sqlite bridge store should initialize"),
        );
        assert_eq!(durable.backend_name(), "sqlite");
        assert_eq!(
            durable.deployment_scope(),
            BridgeStoreDeploymentScope::SharedDurable
        );
        drop(durable);
        cleanup_sqlite_store_path(path.as_path());
    }

    #[tokio::test]
    async fn sqlite_store_coordinates_single_use_and_device_limits_across_instances() {
        let path = temporary_sqlite_store_path();
        let manifest_id =
            ManifestId::new("man-2026-04-01-001").expect("fixture manifest id should be valid");
        let first = SqliteBridgeStore::open(&path).expect("first sqlite store should initialize");
        let second = SqliteBridgeStore::open(&path).expect("second sqlite store should initialize");

        assert!(
            first
                .remember_bootstrap_redemption("sub-1")
                .await
                .expect("bootstrap redemption should store")
        );
        assert!(
            !second
                .remember_bootstrap_redemption("sub-1")
                .await
                .expect("bootstrap redemption should dedupe across instances")
        );
        assert!(
            first
                .remember_webhook("evt-1:1775002200")
                .await
                .expect("webhook should store")
        );
        assert!(
            !second
                .remember_webhook("evt-1:1775002200")
                .await
                .expect("webhook should dedupe across instances")
        );
        assert_eq!(
            first
                .register_device_with_refresh(registration_request(
                    "acct-1",
                    "device-1",
                    "rfr-1",
                    &manifest_id,
                    Some(1),
                ))
                .await
                .expect("first device registration should succeed"),
            DeviceRegistrationStoreOutcome::Stored
        );
        assert_eq!(
            second
                .register_device_with_refresh(registration_request(
                    "acct-1",
                    "device-2",
                    "rfr-2",
                    &manifest_id,
                    Some(1),
                ))
                .await
                .expect("second device registration should evaluate limits"),
            DeviceRegistrationStoreOutcome::DeviceLimitReached { max_devices: 1 }
        );

        drop(first);
        drop(second);
        cleanup_sqlite_store_path(path.as_path());
    }

    #[test]
    fn service_backed_store_reports_shared_durable_scope() {
        let config = ServiceBackedBridgeStoreConfig::new("http://bridge-store.internal", 3_000)
            .expect("service-backed store config should validate");
        let store = ServiceBackedBridgeStore::unavailable(config.clone());

        assert_eq!(store.backend_name(), "service");
        assert_eq!(
            store.deployment_scope(),
            BridgeStoreDeploymentScope::SharedDurable
        );
        assert_eq!(store.config(), &config);
    }

    #[tokio::test]
    async fn unavailable_service_backed_store_fails_closed() {
        let config = ServiceBackedBridgeStoreConfig::new("http://bridge-store.internal", 3_000)
            .expect("service-backed store config should validate");
        let store = ServiceBackedBridgeStore::unavailable(config.clone());

        let error = store
            .remember_webhook("evt-1:1775002200")
            .await
            .expect_err("the unavailable service store should fail closed");
        assert!(matches!(
            error,
            StorageError::ServiceBackendUnavailable {
                operation: "remember_webhook",
                endpoint,
            } if endpoint == config.endpoint
        ));
    }
}
