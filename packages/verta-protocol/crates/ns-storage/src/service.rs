use crate::{
    BootstrapGrantConsumeOutcome, BootstrapGrantRecord, BridgeStore, BridgeStoreDeploymentScope,
    DeviceRegistrationStoreOutcome, DeviceRegistrationStoreRequest, RefreshCredentialRecord,
    ServiceBackedBridgeStoreAdapter, ServiceBackedBridgeStoreConfig, SharedBridgeStore,
    StorageError, StoredDeviceRecord,
};
use async_trait::async_trait;
use axum::extract::{DefaultBodyLimit, State};
use axum::http::HeaderMap;
use axum::http::StatusCode;
use axum::http::header::AUTHORIZATION;
use axum::response::{IntoResponse, Response};
use axum::routing::{get, post};
use axum::{Json, Router};
use ns_core::DeviceBindingId;
use ns_observability::record_bridge_store_service_failure;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::sync::Arc;

const STORE_SERVICE_HEALTH_PATH: &str = "/internal/store/v1/health";
const STORE_SERVICE_COMMAND_PATH: &str = "/internal/store/v1/command";
const STORE_SERVICE_BODY_LIMIT_BYTES: usize = 128 * 1024;
const INTERNAL_STORE_SERVICE_FAILURE_MESSAGE: &str = "internal store service failure";

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct BridgeStoreServiceHealthResponse {
    pub status: String,
    pub backend_name: String,
    pub deployment_scope: BridgeStoreDeploymentScope,
}

#[derive(Clone)]
struct BridgeStoreServiceState {
    store: SharedBridgeStore,
    auth_token: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "operation", rename_all = "snake_case")]
enum BridgeStoreServiceCommand {
    RememberBootstrapRedemption {
        subject: String,
    },
    StoreBootstrapGrant {
        credential: String,
        record: BootstrapGrantRecord,
    },
    ConsumeBootstrapGrant {
        credential: String,
        now_unix: i64,
    },
    RegisterDeviceWithRefresh {
        request: DeviceRegistrationStoreRequest,
    },
    UpsertDevice {
        record: StoredDeviceRecord,
    },
    LoadDevice {
        account_id: String,
        device_id: DeviceBindingId,
    },
    CountActiveDevices {
        account_id: String,
    },
    StoreRefreshCredential {
        credential: String,
        record: RefreshCredentialRecord,
    },
    LoadRefreshCredential {
        credential: String,
    },
    RememberWebhook {
        fingerprint: String,
    },
    PutMetadata {
        key: String,
        value: Value,
    },
}

impl BridgeStoreServiceCommand {
    fn operation_name(&self) -> &'static str {
        match self {
            Self::RememberBootstrapRedemption { .. } => "remember_bootstrap_redemption",
            Self::StoreBootstrapGrant { .. } => "store_bootstrap_grant",
            Self::ConsumeBootstrapGrant { .. } => "consume_bootstrap_grant",
            Self::RegisterDeviceWithRefresh { .. } => "register_device_with_refresh",
            Self::UpsertDevice { .. } => "upsert_device",
            Self::LoadDevice { .. } => "load_device",
            Self::CountActiveDevices { .. } => "count_active_devices",
            Self::StoreRefreshCredential { .. } => "store_refresh_credential",
            Self::LoadRefreshCredential { .. } => "load_refresh_credential",
            Self::RememberWebhook { .. } => "remember_webhook",
            Self::PutMetadata { .. } => "put_metadata",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "result", rename_all = "snake_case")]
enum BridgeStoreServiceResponse {
    RememberBootstrapRedemption {
        is_new: bool,
    },
    StoreBootstrapGrant,
    ConsumeBootstrapGrant {
        outcome: BootstrapGrantConsumeOutcome,
    },
    RegisterDeviceWithRefresh {
        outcome: DeviceRegistrationStoreOutcome,
    },
    UpsertDevice,
    LoadDevice {
        record: Option<StoredDeviceRecord>,
    },
    CountActiveDevices {
        count: usize,
    },
    StoreRefreshCredential,
    LoadRefreshCredential {
        record: RefreshCredentialRecord,
    },
    RememberWebhook {
        is_new: bool,
    },
    PutMetadata,
}

impl BridgeStoreServiceResponse {
    fn response_name(&self) -> &'static str {
        match self {
            Self::RememberBootstrapRedemption { .. } => "remember_bootstrap_redemption",
            Self::StoreBootstrapGrant => "store_bootstrap_grant",
            Self::ConsumeBootstrapGrant { .. } => "consume_bootstrap_grant",
            Self::RegisterDeviceWithRefresh { .. } => "register_device_with_refresh",
            Self::UpsertDevice => "upsert_device",
            Self::LoadDevice { .. } => "load_device",
            Self::CountActiveDevices { .. } => "count_active_devices",
            Self::StoreRefreshCredential => "store_refresh_credential",
            Self::LoadRefreshCredential { .. } => "load_refresh_credential",
            Self::RememberWebhook { .. } => "remember_webhook",
            Self::PutMetadata => "put_metadata",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
enum BridgeStoreServiceErrorCode {
    Unauthorized,
    BootstrapGrantNotFound,
    RefreshCredentialNotFound,
    Internal,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct BridgeStoreServiceErrorEnvelope {
    code: BridgeStoreServiceErrorCode,
    message: String,
}

pub fn build_service_backed_bridge_store_router(
    store: SharedBridgeStore,
    auth_token: Option<String>,
) -> Router {
    Router::new()
        .route(STORE_SERVICE_HEALTH_PATH, get(get_health))
        .route(STORE_SERVICE_COMMAND_PATH, post(post_command))
        .layer(DefaultBodyLimit::max(STORE_SERVICE_BODY_LIMIT_BYTES))
        .with_state(Arc::new(BridgeStoreServiceState { store, auth_token }))
}

#[derive(Clone, Default)]
pub struct HttpServiceBackedBridgeStoreAdapter {
    client: reqwest::Client,
}

impl HttpServiceBackedBridgeStoreAdapter {
    pub fn new(client: reqwest::Client) -> Self {
        Self { client }
    }

    fn with_auth(
        &self,
        builder: reqwest::RequestBuilder,
        config: &ServiceBackedBridgeStoreConfig,
    ) -> reqwest::RequestBuilder {
        match config.auth_token() {
            Some(auth_token) => builder.bearer_auth(auth_token),
            None => builder,
        }
    }

    async fn send_command(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        command: BridgeStoreServiceCommand,
    ) -> Result<BridgeStoreServiceResponse, StorageError> {
        let operation = command.operation_name();
        let mut last_error = None;
        for endpoint_config in config.endpoint_configs() {
            match self
                .send_command_once(&endpoint_config, command.clone())
                .await
            {
                Ok(response) => return Ok(response),
                Err(error) if should_fail_over_for_command(&error) => last_error = Some(error),
                Err(error) => return Err(error),
            }
        }
        Err(
            last_error.unwrap_or(StorageError::ServiceBackendUnavailable {
                endpoint: config.endpoint.clone(),
                operation,
            }),
        )
    }

    async fn send_command_once(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        command: BridgeStoreServiceCommand,
    ) -> Result<BridgeStoreServiceResponse, StorageError> {
        let operation = command.operation_name();
        let response = self
            .with_auth(
                self.client
                    .post(endpoint_url(config, STORE_SERVICE_COMMAND_PATH)?),
                config,
            )
            .timeout(config.request_timeout())
            .json(&command)
            .send()
            .await
            .map_err(|source| service_request_error(config, operation, source))?;
        if !response.status().is_success() {
            let failure_kind = response_status_failure_kind(response.status());
            record_bridge_store_service_failure(
                "service",
                "shared_durable",
                &config.endpoint,
                operation,
                failure_kind,
                Some(response.status().as_u16()),
            );
            return Err(decode_error_response(config, operation, response).await);
        }
        response
            .json::<BridgeStoreServiceResponse>()
            .await
            .map_err(|source| {
                record_bridge_store_service_failure(
                    "service",
                    "shared_durable",
                    &config.endpoint,
                    operation,
                    "schema_drift",
                    None,
                );
                StorageError::ServiceRequest {
                    endpoint: config.endpoint.clone(),
                    operation,
                    source,
                }
            })
    }

    fn unexpected_response(
        config: &ServiceBackedBridgeStoreConfig,
        operation: &'static str,
        response: &BridgeStoreServiceResponse,
    ) -> StorageError {
        record_bridge_store_service_failure(
            "service",
            "shared_durable",
            &config.endpoint,
            operation,
            "unexpected_response",
            None,
        );
        StorageError::UnexpectedServiceResponse {
            endpoint: config.endpoint.clone(),
            operation,
            response: response.response_name().to_owned(),
        }
    }

    async fn check_health_once(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
    ) -> Result<(), StorageError> {
        let response = self
            .with_auth(
                self.client
                    .get(endpoint_url(config, STORE_SERVICE_HEALTH_PATH)?),
                config,
            )
            .timeout(config.request_timeout())
            .send()
            .await
            .map_err(|source| service_request_error(config, "check_health", source))?;
        if !response.status().is_success() {
            let failure_kind = response_status_failure_kind(response.status());
            record_bridge_store_service_failure(
                "service",
                "shared_durable",
                &config.endpoint,
                "check_health",
                failure_kind,
                Some(response.status().as_u16()),
            );
            return Err(decode_error_response(config, "check_health", response).await);
        }
        let health = response
            .json::<BridgeStoreServiceHealthResponse>()
            .await
            .map_err(|source| {
                record_bridge_store_service_failure(
                    "service",
                    "shared_durable",
                    &config.endpoint,
                    "check_health",
                    "schema_drift",
                    None,
                );
                StorageError::ServiceRequest {
                    endpoint: config.endpoint.clone(),
                    operation: "check_health",
                    source,
                }
            })?;
        if health.status != "ok" {
            record_bridge_store_service_failure(
                "service",
                "shared_durable",
                &config.endpoint,
                "check_health",
                "unhealthy_status",
                None,
            );
            return Err(StorageError::UnexpectedServiceResponse {
                endpoint: config.endpoint.clone(),
                operation: "check_health",
                response: health.status,
            });
        }
        if health.deployment_scope != BridgeStoreDeploymentScope::SharedDurable {
            record_bridge_store_service_failure(
                "service",
                "shared_durable",
                &config.endpoint,
                "check_health",
                "unexpected_scope",
                None,
            );
            return Err(StorageError::UnexpectedServiceResponse {
                endpoint: config.endpoint.clone(),
                operation: "check_health",
                response: format!("deployment_scope:{:?}", health.deployment_scope),
            });
        }
        Ok(())
    }
}

#[async_trait]
impl ServiceBackedBridgeStoreAdapter for HttpServiceBackedBridgeStoreAdapter {
    async fn check_health(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
    ) -> Result<(), StorageError> {
        let mut last_error = None;
        for endpoint_config in config.endpoint_configs() {
            match self.check_health_once(&endpoint_config).await {
                Ok(()) => return Ok(()),
                Err(error) if should_fail_over_for_health(&error) => last_error = Some(error),
                Err(error) => return Err(error),
            }
        }
        Err(
            last_error.unwrap_or(StorageError::ServiceBackendUnavailable {
                endpoint: config.endpoint.clone(),
                operation: "check_health",
            }),
        )
    }

    async fn remember_bootstrap_redemption(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        subject: &str,
    ) -> Result<bool, StorageError> {
        let response = self
            .send_command(
                config,
                BridgeStoreServiceCommand::RememberBootstrapRedemption {
                    subject: subject.to_owned(),
                },
            )
            .await?;
        match response {
            BridgeStoreServiceResponse::RememberBootstrapRedemption { is_new } => Ok(is_new),
            other => Err(Self::unexpected_response(
                config,
                "remember_bootstrap_redemption",
                &other,
            )),
        }
    }

    async fn store_bootstrap_grant(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        credential: &str,
        record: BootstrapGrantRecord,
    ) -> Result<(), StorageError> {
        let response = self
            .send_command(
                config,
                BridgeStoreServiceCommand::StoreBootstrapGrant {
                    credential: credential.to_owned(),
                    record,
                },
            )
            .await?;
        match response {
            BridgeStoreServiceResponse::StoreBootstrapGrant => Ok(()),
            other => Err(Self::unexpected_response(
                config,
                "store_bootstrap_grant",
                &other,
            )),
        }
    }

    async fn consume_bootstrap_grant(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        credential: &str,
        now_unix: i64,
    ) -> Result<BootstrapGrantConsumeOutcome, StorageError> {
        let response = self
            .send_command(
                config,
                BridgeStoreServiceCommand::ConsumeBootstrapGrant {
                    credential: credential.to_owned(),
                    now_unix,
                },
            )
            .await?;
        match response {
            BridgeStoreServiceResponse::ConsumeBootstrapGrant { outcome } => Ok(outcome),
            other => Err(Self::unexpected_response(
                config,
                "consume_bootstrap_grant",
                &other,
            )),
        }
    }

    async fn register_device_with_refresh(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        request: DeviceRegistrationStoreRequest,
    ) -> Result<DeviceRegistrationStoreOutcome, StorageError> {
        let response = self
            .send_command(
                config,
                BridgeStoreServiceCommand::RegisterDeviceWithRefresh { request },
            )
            .await?;
        match response {
            BridgeStoreServiceResponse::RegisterDeviceWithRefresh { outcome } => Ok(outcome),
            other => Err(Self::unexpected_response(
                config,
                "register_device_with_refresh",
                &other,
            )),
        }
    }

    async fn upsert_device(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        record: StoredDeviceRecord,
    ) -> Result<(), StorageError> {
        let response = self
            .send_command(config, BridgeStoreServiceCommand::UpsertDevice { record })
            .await?;
        match response {
            BridgeStoreServiceResponse::UpsertDevice => Ok(()),
            other => Err(Self::unexpected_response(config, "upsert_device", &other)),
        }
    }

    async fn load_device(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        account_id: &str,
        device_id: &DeviceBindingId,
    ) -> Result<Option<StoredDeviceRecord>, StorageError> {
        let response = self
            .send_command(
                config,
                BridgeStoreServiceCommand::LoadDevice {
                    account_id: account_id.to_owned(),
                    device_id: device_id.clone(),
                },
            )
            .await?;
        match response {
            BridgeStoreServiceResponse::LoadDevice { record } => Ok(record),
            other => Err(Self::unexpected_response(config, "load_device", &other)),
        }
    }

    async fn count_active_devices(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        account_id: &str,
    ) -> Result<usize, StorageError> {
        let response = self
            .send_command(
                config,
                BridgeStoreServiceCommand::CountActiveDevices {
                    account_id: account_id.to_owned(),
                },
            )
            .await?;
        match response {
            BridgeStoreServiceResponse::CountActiveDevices { count } => Ok(count),
            other => Err(Self::unexpected_response(
                config,
                "count_active_devices",
                &other,
            )),
        }
    }

    async fn store_refresh_credential(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        credential: &str,
        record: RefreshCredentialRecord,
    ) -> Result<(), StorageError> {
        let response = self
            .send_command(
                config,
                BridgeStoreServiceCommand::StoreRefreshCredential {
                    credential: credential.to_owned(),
                    record,
                },
            )
            .await?;
        match response {
            BridgeStoreServiceResponse::StoreRefreshCredential => Ok(()),
            other => Err(Self::unexpected_response(
                config,
                "store_refresh_credential",
                &other,
            )),
        }
    }

    async fn load_refresh_credential(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        credential: &str,
    ) -> Result<RefreshCredentialRecord, StorageError> {
        let response = self
            .send_command(
                config,
                BridgeStoreServiceCommand::LoadRefreshCredential {
                    credential: credential.to_owned(),
                },
            )
            .await?;
        match response {
            BridgeStoreServiceResponse::LoadRefreshCredential { record } => Ok(record),
            other => Err(Self::unexpected_response(
                config,
                "load_refresh_credential",
                &other,
            )),
        }
    }

    async fn remember_webhook(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        fingerprint: &str,
    ) -> Result<bool, StorageError> {
        let response = self
            .send_command(
                config,
                BridgeStoreServiceCommand::RememberWebhook {
                    fingerprint: fingerprint.to_owned(),
                },
            )
            .await?;
        match response {
            BridgeStoreServiceResponse::RememberWebhook { is_new } => Ok(is_new),
            other => Err(Self::unexpected_response(
                config,
                "remember_webhook",
                &other,
            )),
        }
    }

    async fn put_metadata(
        &self,
        config: &ServiceBackedBridgeStoreConfig,
        key: &str,
        value: Value,
    ) -> Result<(), StorageError> {
        let response = self
            .send_command(
                config,
                BridgeStoreServiceCommand::PutMetadata {
                    key: key.to_owned(),
                    value,
                },
            )
            .await?;
        match response {
            BridgeStoreServiceResponse::PutMetadata => Ok(()),
            other => Err(Self::unexpected_response(config, "put_metadata", &other)),
        }
    }
}

async fn get_health(
    State(state): State<Arc<BridgeStoreServiceState>>,
    headers: HeaderMap,
) -> Result<Json<BridgeStoreServiceHealthResponse>, ServiceCommandError> {
    authorize_request(&state, &headers)?;
    Ok(Json(BridgeStoreServiceHealthResponse {
        status: "ok".to_owned(),
        backend_name: state.store.backend_name().to_owned(),
        deployment_scope: state.store.deployment_scope(),
    }))
}

async fn post_command(
    State(state): State<Arc<BridgeStoreServiceState>>,
    headers: HeaderMap,
    Json(command): Json<BridgeStoreServiceCommand>,
) -> Result<Json<BridgeStoreServiceResponse>, ServiceCommandError> {
    authorize_request(&state, &headers)?;
    let response = match command {
        BridgeStoreServiceCommand::RememberBootstrapRedemption { subject } => {
            BridgeStoreServiceResponse::RememberBootstrapRedemption {
                is_new: state.store.remember_bootstrap_redemption(&subject).await?,
            }
        }
        BridgeStoreServiceCommand::StoreBootstrapGrant { credential, record } => {
            state
                .store
                .store_bootstrap_grant(&credential, record)
                .await?;
            BridgeStoreServiceResponse::StoreBootstrapGrant
        }
        BridgeStoreServiceCommand::ConsumeBootstrapGrant {
            credential,
            now_unix,
        } => BridgeStoreServiceResponse::ConsumeBootstrapGrant {
            outcome: state
                .store
                .consume_bootstrap_grant(&credential, now_unix)
                .await?,
        },
        BridgeStoreServiceCommand::RegisterDeviceWithRefresh { request } => {
            BridgeStoreServiceResponse::RegisterDeviceWithRefresh {
                outcome: state.store.register_device_with_refresh(request).await?,
            }
        }
        BridgeStoreServiceCommand::UpsertDevice { record } => {
            state.store.upsert_device(record).await?;
            BridgeStoreServiceResponse::UpsertDevice
        }
        BridgeStoreServiceCommand::LoadDevice {
            account_id,
            device_id,
        } => BridgeStoreServiceResponse::LoadDevice {
            record: state.store.load_device(&account_id, &device_id).await?,
        },
        BridgeStoreServiceCommand::CountActiveDevices { account_id } => {
            BridgeStoreServiceResponse::CountActiveDevices {
                count: state.store.count_active_devices(&account_id).await?,
            }
        }
        BridgeStoreServiceCommand::StoreRefreshCredential { credential, record } => {
            state
                .store
                .store_refresh_credential(&credential, record)
                .await?;
            BridgeStoreServiceResponse::StoreRefreshCredential
        }
        BridgeStoreServiceCommand::LoadRefreshCredential { credential } => {
            BridgeStoreServiceResponse::LoadRefreshCredential {
                record: state.store.load_refresh_credential(&credential).await?,
            }
        }
        BridgeStoreServiceCommand::RememberWebhook { fingerprint } => {
            BridgeStoreServiceResponse::RememberWebhook {
                is_new: state.store.remember_webhook(&fingerprint).await?,
            }
        }
        BridgeStoreServiceCommand::PutMetadata { key, value } => {
            state.store.put_metadata(&key, value).await?;
            BridgeStoreServiceResponse::PutMetadata
        }
    };
    Ok(Json(response))
}

fn authorize_request(
    state: &BridgeStoreServiceState,
    headers: &HeaderMap,
) -> Result<(), ServiceCommandError> {
    let Some(expected_token) = state.auth_token.as_deref() else {
        return Ok(());
    };
    let actual = headers
        .get(AUTHORIZATION)
        .and_then(|value| value.to_str().ok())
        .and_then(|value| value.strip_prefix("Bearer "));
    match actual {
        Some(token) if token == expected_token => Ok(()),
        _ => Err(ServiceCommandError(StorageError::ServiceResponseStatus {
            endpoint: "internal-store-service".to_owned(),
            operation: "authorize_request",
            status: StatusCode::UNAUTHORIZED.as_u16(),
            message: "store service authorization failed".to_owned(),
        })),
    }
}

#[derive(Debug)]
struct ServiceCommandError(StorageError);

impl From<StorageError> for ServiceCommandError {
    fn from(value: StorageError) -> Self {
        Self(value)
    }
}

impl IntoResponse for ServiceCommandError {
    fn into_response(self) -> Response {
        let (status, code, message) = match self.0 {
            StorageError::ServiceResponseStatus {
                operation: "authorize_request",
                status,
                message,
                ..
            } if status == StatusCode::UNAUTHORIZED.as_u16() => (
                StatusCode::UNAUTHORIZED,
                BridgeStoreServiceErrorCode::Unauthorized,
                message,
            ),
            StorageError::BootstrapGrantNotFound => (
                StatusCode::NOT_FOUND,
                BridgeStoreServiceErrorCode::BootstrapGrantNotFound,
                "bootstrap grant not found".to_owned(),
            ),
            StorageError::RefreshCredentialNotFound => (
                StatusCode::NOT_FOUND,
                BridgeStoreServiceErrorCode::RefreshCredentialNotFound,
                "refresh credential not found".to_owned(),
            ),
            _other => (
                StatusCode::INTERNAL_SERVER_ERROR,
                BridgeStoreServiceErrorCode::Internal,
                INTERNAL_STORE_SERVICE_FAILURE_MESSAGE.to_owned(),
            ),
        };
        (
            status,
            Json(BridgeStoreServiceErrorEnvelope { code, message }),
        )
            .into_response()
    }
}

fn endpoint_url(
    config: &ServiceBackedBridgeStoreConfig,
    path: &str,
) -> Result<reqwest::Url, StorageError> {
    reqwest::Url::parse(&config.endpoint)
        .map_err(|_| StorageError::InvalidServiceConfig("endpoint"))?
        .join(path)
        .map_err(|_| StorageError::InvalidServiceConfig("endpoint"))
}

fn service_request_error(
    config: &ServiceBackedBridgeStoreConfig,
    operation: &'static str,
    source: reqwest::Error,
) -> StorageError {
    record_bridge_store_service_failure(
        "service",
        "shared_durable",
        &config.endpoint,
        operation,
        if source.is_timeout() {
            "timeout"
        } else {
            "request_failed"
        },
        None,
    );
    StorageError::ServiceRequest {
        endpoint: config.endpoint.clone(),
        operation,
        source,
    }
}

fn response_status_failure_kind(status: StatusCode) -> &'static str {
    if matches!(status, StatusCode::UNAUTHORIZED | StatusCode::FORBIDDEN) {
        "unauthorized"
    } else {
        "http_status"
    }
}

fn should_fail_over_for_command(error: &StorageError) -> bool {
    match error {
        StorageError::ServiceRequest { .. } => true,
        StorageError::ServiceResponseStatus { status, .. } => *status >= 500,
        _ => false,
    }
}

fn should_fail_over_for_health(error: &StorageError) -> bool {
    match error {
        StorageError::ServiceRequest { .. } => true,
        StorageError::ServiceResponseStatus { status, .. } => *status >= 500,
        StorageError::UnexpectedServiceResponse {
            operation: "check_health",
            ..
        } => true,
        _ => false,
    }
}

async fn decode_error_response(
    config: &ServiceBackedBridgeStoreConfig,
    operation: &'static str,
    response: reqwest::Response,
) -> StorageError {
    let status = response.status();
    let body = response.text().await.unwrap_or_default();
    if let Ok(envelope) = serde_json::from_str::<BridgeStoreServiceErrorEnvelope>(&body) {
        return match envelope.code {
            BridgeStoreServiceErrorCode::Unauthorized => StorageError::ServiceResponseStatus {
                endpoint: config.endpoint.clone(),
                operation,
                status: status.as_u16(),
                message: envelope.message,
            },
            BridgeStoreServiceErrorCode::BootstrapGrantNotFound => {
                StorageError::BootstrapGrantNotFound
            }
            BridgeStoreServiceErrorCode::RefreshCredentialNotFound => {
                StorageError::RefreshCredentialNotFound
            }
            BridgeStoreServiceErrorCode::Internal => StorageError::ServiceResponseStatus {
                endpoint: config.endpoint.clone(),
                operation,
                status: status.as_u16(),
                message: INTERNAL_STORE_SERVICE_FAILURE_MESSAGE.to_owned(),
            },
        };
    }
    StorageError::ServiceResponseStatus {
        endpoint: config.endpoint.clone(),
        operation,
        status: status.as_u16(),
        message: if status.is_server_error() {
            INTERNAL_STORE_SERVICE_FAILURE_MESSAGE.to_owned()
        } else {
            body
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        InMemoryBridgeStore, ServiceBackedBridgeStore, SqliteBridgeStore, StoredDeviceStatus,
    };
    use axum::body::Body;
    use axum::http::Request;
    use ns_core::ManifestId;
    use std::fs;
    use std::io::ErrorKind;
    use std::path::{Path, PathBuf};
    use std::time::{SystemTime, UNIX_EPOCH};
    use tokio::net::TcpListener;
    use tokio::time::{Duration, sleep};
    use tower::util::ServiceExt;

    fn temporary_sqlite_store_path() -> PathBuf {
        let mut path = std::env::temp_dir();
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock should be after the unix epoch")
            .as_nanos();
        path.push(format!("verta-service-store-{nonce}.sqlite3"));
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

    async fn spawn_router(router: Router) -> (String, tokio::task::JoinHandle<()>) {
        let listener = TcpListener::bind("127.0.0.1:0")
            .await
            .expect("test listener should bind");
        let addr = listener
            .local_addr()
            .expect("test listener should expose a local address");
        let handle = tokio::spawn(async move {
            axum::serve(listener, router)
                .await
                .expect("test service should serve requests");
        });
        sleep(Duration::from_millis(10)).await;
        (format!("http://{addr}"), handle)
    }

    async fn check_health_until_ready(
        store: &ServiceBackedBridgeStore,
    ) -> Result<(), StorageError> {
        let mut last_request_error = None;
        for _ in 0..10 {
            match store.check_health().await {
                Ok(()) => return Ok(()),
                Err(
                    error @ StorageError::ServiceRequest {
                        operation: "check_health",
                        ..
                    },
                ) => {
                    last_request_error = Some(error);
                    sleep(Duration::from_millis(25)).await;
                }
                Err(error) => return Err(error),
            }
        }

        Err(
            last_request_error.unwrap_or(StorageError::ServiceBackendUnavailable {
                endpoint: "test-health-check".to_owned(),
                operation: "check_health",
            }),
        )
    }

    async fn check_health_until_unauthorized(store: &ServiceBackedBridgeStore) -> StorageError {
        let mut last_request_error = None;
        for _ in 0..10 {
            match store.check_health().await {
                Err(
                    error @ StorageError::ServiceResponseStatus {
                        operation: "check_health",
                        status: 401,
                        ..
                    },
                ) => return error,
                Err(
                    error @ StorageError::ServiceRequest {
                        operation: "check_health",
                        ..
                    },
                ) => {
                    last_request_error = Some(error);
                    sleep(Duration::from_millis(25)).await;
                }
                Err(error) => return error,
                Ok(()) => {
                    return StorageError::UnexpectedServiceResponse {
                        endpoint: "test-health-check".to_owned(),
                        operation: "check_health",
                        response: "unexpected_success".to_owned(),
                    };
                }
            }
        }

        last_request_error.unwrap_or(StorageError::ServiceBackendUnavailable {
            endpoint: "test-health-check".to_owned(),
            operation: "check_health",
        })
    }

    fn build_failing_store_service_router(status: StatusCode) -> Router {
        let health_status = status;
        let command_status = status;
        Router::new()
            .route(
                STORE_SERVICE_HEALTH_PATH,
                get(move || async move { health_status }),
            )
            .route(
                STORE_SERVICE_COMMAND_PATH,
                post(move || async move { command_status }),
            )
    }

    #[tokio::test]
    async fn http_service_backed_store_round_trips_against_shared_durable_remote_store() {
        let path = temporary_sqlite_store_path();
        let backend = SqliteBridgeStore::open(&path).expect("sqlite backend should initialize");
        let router =
            build_service_backed_bridge_store_router(SharedBridgeStore::new(backend), None);
        let (endpoint, handle) = spawn_router(router).await;
        let config = ServiceBackedBridgeStoreConfig::new(endpoint, 500)
            .expect("service-backed config should validate");
        let adapter = Arc::new(HttpServiceBackedBridgeStoreAdapter::default());
        let first = ServiceBackedBridgeStore::new(config.clone(), adapter.clone());
        let second = ServiceBackedBridgeStore::new(config.clone(), adapter);
        let manifest_id =
            ManifestId::new("man-2026-04-01-001").expect("fixture manifest id should be valid");

        check_health_until_ready(&first)
            .await
            .expect("shared durable remote store should pass health checks");
        assert!(
            first
                .remember_bootstrap_redemption("sub-1")
                .await
                .expect("first redemption should store")
        );
        assert!(
            !second
                .remember_bootstrap_redemption("sub-1")
                .await
                .expect("duplicate redemption should dedupe across clients")
        );

        first
            .store_bootstrap_grant(
                "btg_fixture",
                BootstrapGrantRecord {
                    account_id: "acct-1".to_owned(),
                    manifest_id: manifest_id.clone(),
                    expires_at_unix: 1_775_002_260,
                },
            )
            .await
            .expect("bootstrap grant should store remotely");
        assert!(matches!(
            second
                .consume_bootstrap_grant("btg_fixture", 1_775_002_200)
                .await
                .expect("bootstrap grant should consume remotely"),
            BootstrapGrantConsumeOutcome::Consumed(record)
                if record.manifest_id == manifest_id
        ));

        assert!(
            first
                .remember_webhook("evt-1:1775002200")
                .await
                .expect("webhook should store remotely")
        );
        assert!(
            !second
                .remember_webhook("evt-1:1775002200")
                .await
                .expect("duplicate webhook should dedupe remotely")
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
                .expect("first device registration should store remotely"),
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
                .expect("second device registration should evaluate remote limits"),
            DeviceRegistrationStoreOutcome::DeviceLimitReached { max_devices: 1 }
        );

        drop(first);
        drop(second);
        handle.abort();
        let _ = handle.await;
        cleanup_sqlite_store_path(path.as_path());
    }

    #[tokio::test]
    async fn http_service_backed_store_health_rejects_local_only_remote_backends() {
        let router = build_service_backed_bridge_store_router(
            SharedBridgeStore::new(InMemoryBridgeStore::default()),
            None,
        );
        let (endpoint, handle) = spawn_router(router).await;
        let config = ServiceBackedBridgeStoreConfig::new(endpoint, 500)
            .expect("service-backed config should validate");
        let store = ServiceBackedBridgeStore::new(
            config.clone(),
            Arc::new(HttpServiceBackedBridgeStoreAdapter::default()),
        );

        let error = store
            .check_health()
            .await
            .expect_err("local-only backends should fail the shared-durable health check");
        assert!(matches!(
            error,
            StorageError::UnexpectedServiceResponse {
                operation: "check_health",
                endpoint,
                ..
            } if endpoint == config.endpoint
        ));

        handle.abort();
        let _ = handle.await;
    }

    #[tokio::test]
    async fn http_service_backed_store_enforces_request_timeout() {
        async fn delayed_health() -> Json<BridgeStoreServiceHealthResponse> {
            sleep(Duration::from_millis(200)).await;
            Json(BridgeStoreServiceHealthResponse {
                status: "ok".to_owned(),
                backend_name: "sqlite".to_owned(),
                deployment_scope: BridgeStoreDeploymentScope::SharedDurable,
            })
        }

        let router = Router::new().route(STORE_SERVICE_HEALTH_PATH, get(delayed_health));
        let (endpoint, handle) = spawn_router(router).await;
        let config = ServiceBackedBridgeStoreConfig::new(endpoint, 20)
            .expect("service-backed config should validate");
        let store = ServiceBackedBridgeStore::new(
            config.clone(),
            Arc::new(HttpServiceBackedBridgeStoreAdapter::default()),
        );

        let error = store
            .check_health()
            .await
            .expect_err("health check should time out");
        assert!(matches!(
            error,
            StorageError::ServiceRequest {
                operation: "check_health",
                endpoint,
                ..
            } if endpoint == config.endpoint
        ));

        handle.abort();
        let _ = handle.await;
    }

    #[tokio::test]
    async fn http_service_backed_store_requires_the_configured_auth_token() {
        let path = temporary_sqlite_store_path();
        let backend = SqliteBridgeStore::open(&path).expect("sqlite backend should initialize");
        let router = build_service_backed_bridge_store_router(
            SharedBridgeStore::new(backend),
            Some("store-secret".to_owned()),
        );
        let (endpoint, handle) = spawn_router(router).await;
        let missing_auth = ServiceBackedBridgeStore::new(
            ServiceBackedBridgeStoreConfig::new(endpoint.clone(), 500)
                .expect("service-backed config should validate"),
            Arc::new(HttpServiceBackedBridgeStoreAdapter::default()),
        );
        let authorized = ServiceBackedBridgeStore::new(
            ServiceBackedBridgeStoreConfig::new(endpoint, 500)
                .expect("service-backed config should validate")
                .with_auth_token("store-secret")
                .expect("service-backed auth token should validate"),
            Arc::new(HttpServiceBackedBridgeStoreAdapter::default()),
        );

        let error = check_health_until_unauthorized(&missing_auth).await;
        assert!(matches!(
            error,
            StorageError::ServiceResponseStatus {
                operation: "check_health",
                status: 401,
                ..
            }
        ));
        check_health_until_ready(&authorized)
            .await
            .expect("authorized store should pass health checks");

        drop(missing_auth);
        drop(authorized);
        handle.abort();
        let _ = handle.await;
        cleanup_sqlite_store_path(path.as_path());
    }

    #[tokio::test]
    async fn http_service_backed_store_fails_over_to_secondary_endpoint_for_health_and_commands() {
        let path = temporary_sqlite_store_path();
        let healthy_router = build_service_backed_bridge_store_router(
            SharedBridgeStore::new(
                SqliteBridgeStore::open(&path).expect("sqlite backend should initialize"),
            ),
            Some("store-secret".to_owned()),
        );
        let (healthy_endpoint, healthy_handle) = spawn_router(healthy_router).await;
        let (failing_endpoint, failing_handle) = spawn_router(build_failing_store_service_router(
            StatusCode::SERVICE_UNAVAILABLE,
        ))
        .await;

        let config = ServiceBackedBridgeStoreConfig::new(failing_endpoint, 500)
            .expect("service-backed config should validate")
            .with_auth_token("store-secret")
            .expect("auth token should validate")
            .with_fallback_endpoint(healthy_endpoint)
            .expect("fallback endpoint should validate");
        let store = ServiceBackedBridgeStore::new(
            config,
            Arc::new(HttpServiceBackedBridgeStoreAdapter::default()),
        );

        store
            .check_health()
            .await
            .expect("the adapter should fail over to a healthy secondary endpoint");
        assert!(
            store
                .remember_webhook("evt-1:1775002200")
                .await
                .expect("commands should fail over to the healthy secondary endpoint")
        );

        drop(store);
        failing_handle.abort();
        let _ = failing_handle.await;
        healthy_handle.abort();
        let _ = healthy_handle.await;
        cleanup_sqlite_store_path(path.as_path());
    }

    #[tokio::test]
    async fn http_service_backed_store_does_not_fail_over_on_unauthorized_primary_endpoint() {
        let path = temporary_sqlite_store_path();
        let primary_router = build_service_backed_bridge_store_router(
            SharedBridgeStore::new(
                SqliteBridgeStore::open(&path).expect("sqlite backend should initialize"),
            ),
            Some("wrong-secret".to_owned()),
        );
        let secondary_router = build_service_backed_bridge_store_router(
            SharedBridgeStore::new(
                SqliteBridgeStore::open(&path).expect("sqlite backend should initialize"),
            ),
            Some("store-secret".to_owned()),
        );
        let (primary_endpoint, primary_handle) = spawn_router(primary_router).await;
        let (secondary_endpoint, secondary_handle) = spawn_router(secondary_router).await;

        let config = ServiceBackedBridgeStoreConfig::new(primary_endpoint, 500)
            .expect("service-backed config should validate")
            .with_auth_token("store-secret")
            .expect("auth token should validate")
            .with_fallback_endpoint(secondary_endpoint)
            .expect("fallback endpoint should validate");
        let store = ServiceBackedBridgeStore::new(
            config,
            Arc::new(HttpServiceBackedBridgeStoreAdapter::default()),
        );

        let error = store
            .check_health()
            .await
            .expect_err("unauthorized primary endpoint should fail closed");
        assert!(matches!(
            error,
            StorageError::ServiceResponseStatus {
                operation: "check_health",
                status: 401,
                ..
            }
        ));

        drop(store);
        primary_handle.abort();
        let _ = primary_handle.await;
        secondary_handle.abort();
        let _ = secondary_handle.await;
        cleanup_sqlite_store_path(path.as_path());
    }

    #[tokio::test]
    async fn store_service_rejects_unauthorized_health_requests() {
        let router = build_service_backed_bridge_store_router(
            SharedBridgeStore::new(InMemoryBridgeStore::default()),
            Some("store-secret".to_owned()),
        );

        let response = router
            .oneshot(
                Request::builder()
                    .uri(STORE_SERVICE_HEALTH_PATH)
                    .body(Body::empty())
                    .expect("health request should build"),
            )
            .await
            .expect("unauthorized health request should return a response");

        assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
    }

    #[tokio::test]
    async fn store_service_rejects_unauthorized_command_requests() {
        let router = build_service_backed_bridge_store_router(
            SharedBridgeStore::new(InMemoryBridgeStore::default()),
            Some("store-secret".to_owned()),
        );
        let body = serde_json::to_vec(&serde_json::json!({
            "operation": "remember_webhook",
            "fingerprint": "evt-1:1775002200",
        }))
        .expect("command request should serialize");

        let response = router
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri(STORE_SERVICE_COMMAND_PATH)
                    .header("content-type", "application/json")
                    .body(Body::from(body))
                    .expect("command request should build"),
            )
            .await
            .expect("unauthorized command request should return a response");

        assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
    }

    #[test]
    fn store_service_internal_failures_are_redacted_in_http_bodies() {
        let response = ServiceCommandError(StorageError::OpenDatabase {
            path: "C:\\secret\\bridge.sqlite3".to_owned(),
            source: rusqlite::Error::InvalidPath(PathBuf::from("C:\\secret\\bridge.sqlite3")),
        })
        .into_response();

        assert_eq!(response.status(), StatusCode::INTERNAL_SERVER_ERROR);
        let response_body = response.into_body();
        let runtime = tokio::runtime::Runtime::new().expect("test runtime should initialize");
        let bytes = runtime
            .block_on(axum::body::to_bytes(response_body, usize::MAX))
            .expect("response body should read");
        let envelope: BridgeStoreServiceErrorEnvelope =
            serde_json::from_slice(bytes.as_ref()).expect("redacted error envelope should parse");
        assert_eq!(envelope.code, BridgeStoreServiceErrorCode::Internal);
        assert_eq!(envelope.message, INTERNAL_STORE_SERVICE_FAILURE_MESSAGE);
        assert!(!envelope.message.contains("secret"));
    }
}
