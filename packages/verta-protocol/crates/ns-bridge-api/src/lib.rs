#![forbid(unsafe_code)]

use axum::body::Bytes;
use axum::extract::{DefaultBodyLimit, Query, State};
use axum::http::header::{AUTHORIZATION, ETAG, IF_NONE_MATCH};
use axum::http::{HeaderMap, StatusCode};
use axum::response::{IntoResponse, Response};
use axum::routing::{get, post};
use axum::{Json, Router};
use ns_bridge_domain::{
    BridgeDomain, BridgeDomainError, BridgeManifestTemplate,
    DeviceRegistrationRequest as DomainDeviceRegistrationRequest, TokenExchangeInput,
};
use ns_core::{DeviceBindingId, ManifestId};
use ns_observability::record_bridge_http_body_rejected;
use ns_remnawave_adapter::{
    BootstrapSubject, RemnawaveAdapter, VerifiedWebhookPayload, WebhookAuthenticator,
    WebhookVerificationConfig, WebhookVerificationInput,
};
use ns_storage::{BridgeStore, StorageError};
use serde::de::DeserializeOwned;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::sync::Arc;
use thiserror::Error;
use time::OffsetDateTime;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum BridgeErrorCode {
    InvalidBootstrapSubject,
    BootstrapExpired,
    AccountNotFound,
    AccountDisabled,
    AccountRevoked,
    AccountExpired,
    AccountLimited,
    ManifestNotAvailable,
    DeviceBindingRequired,
    DeviceLimitReached,
    DeviceRevoked,
    InvalidRefreshCredential,
    RefreshCredentialExpired,
    ProfileNotAllowed,
    CoreVersionNotAllowed,
    ClientVersionTooOld,
    RateLimited,
    UpstreamControlPlaneUnavailable,
    TemporaryReconciliationInProgress,
}

impl BridgeErrorCode {
    pub fn recommended_status(self) -> StatusCode {
        match self {
            Self::InvalidBootstrapSubject => StatusCode::NOT_FOUND,
            Self::BootstrapExpired => StatusCode::GONE,
            Self::AccountNotFound => StatusCode::NOT_FOUND,
            Self::AccountDisabled
            | Self::AccountRevoked
            | Self::AccountExpired
            | Self::AccountLimited
            | Self::ManifestNotAvailable
            | Self::DeviceRevoked
            | Self::ProfileNotAllowed
            | Self::CoreVersionNotAllowed
            | Self::ClientVersionTooOld => StatusCode::FORBIDDEN,
            Self::DeviceBindingRequired
            | Self::InvalidRefreshCredential
            | Self::RefreshCredentialExpired => StatusCode::UNAUTHORIZED,
            Self::DeviceLimitReached => StatusCode::CONFLICT,
            Self::RateLimited => StatusCode::TOO_MANY_REQUESTS,
            Self::UpstreamControlPlaneUnavailable | Self::TemporaryReconciliationInProgress => {
                StatusCode::SERVICE_UNAVAILABLE
            }
        }
    }

    fn default_message(self) -> &'static str {
        match self {
            Self::InvalidBootstrapSubject => "bootstrap subject was not valid",
            Self::BootstrapExpired => "bootstrap credential is no longer valid",
            Self::AccountNotFound => "account state could not be resolved",
            Self::AccountDisabled => "account is disabled",
            Self::AccountRevoked => "account is revoked",
            Self::AccountExpired => "account is expired",
            Self::AccountLimited => "account is limited",
            Self::ManifestNotAvailable => "manifest is not available",
            Self::DeviceBindingRequired => "device binding is required",
            Self::DeviceLimitReached => "device limit has been reached",
            Self::DeviceRevoked => "device is revoked",
            Self::InvalidRefreshCredential => "refresh credential is invalid",
            Self::RefreshCredentialExpired => "refresh credential is expired",
            Self::ProfileNotAllowed => "carrier profile is not allowed",
            Self::CoreVersionNotAllowed => "core version is not allowed",
            Self::ClientVersionTooOld => "client version is too old",
            Self::RateLimited => "request was rate limited",
            Self::UpstreamControlPlaneUnavailable => "control-plane state is unavailable",
            Self::TemporaryReconciliationInProgress => "reconciliation is still in progress",
        }
    }

    fn retryable(self) -> bool {
        matches!(
            self,
            Self::RateLimited
                | Self::UpstreamControlPlaneUnavailable
                | Self::TemporaryReconciliationInProgress
        )
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct BridgeErrorEnvelope {
    pub error: BridgeErrorBody,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct BridgeErrorBody {
    pub code: BridgeErrorCode,
    pub message: String,
    pub retryable: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub policy_epoch: Option<u64>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DeviceRegisterRequest {
    pub manifest_id: String,
    pub device_id: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub device_name: Option<String>,
    pub platform: String,
    pub client_version: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub install_channel: Option<String>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub requested_capabilities: Vec<u16>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DeviceRegisterResponse {
    pub device_id: String,
    pub binding_required: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub refresh_credential: Option<String>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TokenExchangeRequest {
    pub manifest_id: String,
    pub device_id: String,
    pub client_version: String,
    pub core_version: u16,
    pub carrier_profile_id: String,
    pub requested_capabilities: Vec<u16>,
    pub refresh_credential: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TokenExchangeResponse {
    pub session_token: String,
    pub expires_at: String,
    pub policy_epoch: u64,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub recommended_endpoints: Vec<String>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ManifestRequestMode {
    Bootstrap { subscription_token: String },
    Refresh { refresh_credential: String },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct BridgeHttpBudgets {
    pub max_json_body_bytes: usize,
    pub max_webhook_body_bytes: usize,
}

impl Default for BridgeHttpBudgets {
    fn default() -> Self {
        Self {
            max_json_body_bytes: 16 * 1024,
            max_webhook_body_bytes: 64 * 1024,
        }
    }
}

#[derive(Debug, Clone, Deserialize)]
pub struct ManifestQuery {
    #[serde(default)]
    pub subscription_token: Option<String>,
}

#[derive(Clone)]
pub struct BridgeHttpServiceState<A, S, W> {
    domain: Arc<BridgeDomain<A, S>>,
    manifest_template: BridgeManifestTemplate,
    webhook_authenticator: Arc<W>,
    webhook_verification: WebhookVerificationConfig,
    token_jwks: Value,
    budgets: BridgeHttpBudgets,
    now: Arc<dyn Fn() -> OffsetDateTime + Send + Sync>,
}

impl<A, S, W> BridgeHttpServiceState<A, S, W> {
    pub fn new(
        domain: Arc<BridgeDomain<A, S>>,
        manifest_template: BridgeManifestTemplate,
        webhook_authenticator: Arc<W>,
        webhook_verification: WebhookVerificationConfig,
        token_jwks: Value,
        budgets: BridgeHttpBudgets,
    ) -> Self {
        Self::new_with_clock(
            domain,
            manifest_template,
            webhook_authenticator,
            webhook_verification,
            token_jwks,
            budgets,
            Arc::new(OffsetDateTime::now_utc),
        )
    }

    pub fn new_with_clock(
        domain: Arc<BridgeDomain<A, S>>,
        manifest_template: BridgeManifestTemplate,
        webhook_authenticator: Arc<W>,
        webhook_verification: WebhookVerificationConfig,
        token_jwks: Value,
        budgets: BridgeHttpBudgets,
        now: Arc<dyn Fn() -> OffsetDateTime + Send + Sync>,
    ) -> Self {
        Self {
            domain,
            manifest_template,
            webhook_authenticator,
            webhook_verification,
            token_jwks,
            budgets,
            now,
        }
    }

    fn now(&self) -> OffsetDateTime {
        (self.now)()
    }
}

pub fn parse_manifest_request(
    subscription_token: Option<&str>,
    authorization_header: Option<&str>,
) -> Result<ManifestRequestMode, BridgeApiError> {
    match (
        subscription_token,
        authorization_header.and_then(parse_bearer_token),
    ) {
        (Some(token), None) if !token.trim().is_empty() => Ok(ManifestRequestMode::Bootstrap {
            subscription_token: token.to_owned(),
        }),
        (None, Some(refresh)) => Ok(ManifestRequestMode::Refresh {
            refresh_credential: refresh,
        }),
        (Some(_), Some(_)) => Err(BridgeApiError::ConflictingManifestAuthModes),
        _ => Err(BridgeApiError::MissingManifestAuth),
    }
}

pub fn parse_bearer_token(header_value: &str) -> Option<String> {
    let stripped = header_value.strip_prefix("Bearer ")?;
    if stripped.trim().is_empty() {
        return None;
    }
    Some(stripped.to_owned())
}

impl BridgeErrorEnvelope {
    pub fn new(
        code: BridgeErrorCode,
        message: impl Into<String>,
        retryable: bool,
        policy_epoch: Option<u64>,
    ) -> Self {
        Self {
            error: BridgeErrorBody {
                code,
                message: message.into(),
                retryable,
                policy_epoch,
            },
        }
    }
}

pub fn build_bridge_router<A, S, W>(state: BridgeHttpServiceState<A, S, W>) -> Router
where
    A: RemnawaveAdapter + Send + Sync + 'static,
    S: BridgeStore + Send + Sync + 'static,
    W: WebhookAuthenticator + Send + Sync + 'static,
{
    let json_limit = state.budgets.max_json_body_bytes;
    let webhook_limit = state.budgets.max_webhook_body_bytes;

    Router::new()
        .merge(
            Router::new()
                .route("/v0/manifest", get(get_manifest::<A, S, W>))
                .route("/v0/device/register", post(post_device_register::<A, S, W>))
                .route("/v0/token/exchange", post(post_token_exchange::<A, S, W>))
                .route("/.well-known/jwks.json", get(get_jwks::<A, S, W>))
                .layer(DefaultBodyLimit::max(json_limit)),
        )
        .merge(
            Router::new()
                .route(
                    "/internal/remnawave/webhook",
                    post(post_remnawave_webhook::<A, S, W>),
                )
                .layer(DefaultBodyLimit::max(webhook_limit)),
        )
        .with_state(Arc::new(state))
}

#[derive(Debug, Clone, Copy)]
enum BridgeOperation {
    ManifestBootstrap,
    ManifestRefresh,
    DeviceRegister,
    TokenExchange,
}

struct BridgeHttpError {
    response: Box<Response>,
}

async fn get_manifest<A, S, W>(
    State(state): State<Arc<BridgeHttpServiceState<A, S, W>>>,
    headers: HeaderMap,
    Query(query): Query<ManifestQuery>,
) -> Result<Response, BridgeHttpError>
where
    A: RemnawaveAdapter + Send + Sync + 'static,
    S: BridgeStore + Send + Sync + 'static,
    W: WebhookAuthenticator + Send + Sync + 'static,
{
    let auth_header = header_text(&headers, AUTHORIZATION);
    let mode = parse_manifest_request(query.subscription_token.as_deref(), auth_header)
        .map_err(|error| BridgeHttpError::plain(StatusCode::BAD_REQUEST, error.to_string()))?;
    let now = state.now();
    let manifest = match mode {
        ManifestRequestMode::Bootstrap { subscription_token } => state
            .domain
            .compile_manifest_for_bootstrap(
                &BootstrapSubject::ShortUuid(subscription_token),
                &state.manifest_template,
                now,
            )
            .await
            .map_err(|error| {
                BridgeHttpError::from_domain(BridgeOperation::ManifestBootstrap, error)
            })?,
        ManifestRequestMode::Refresh { refresh_credential } => state
            .domain
            .compile_manifest_for_refresh(&refresh_credential, &state.manifest_template, now)
            .await
            .map_err(|error| {
                BridgeHttpError::from_domain(BridgeOperation::ManifestRefresh, error)
            })?,
    };

    let etag = manifest_etag(&manifest);
    if header_text(&headers, IF_NONE_MATCH) == Some(etag.as_str()) {
        return Ok((StatusCode::NOT_MODIFIED, [(ETAG, etag)]).into_response());
    }

    Ok((StatusCode::OK, [(ETAG, etag)], Json(manifest)).into_response())
}

async fn post_device_register<A, S, W>(
    State(state): State<Arc<BridgeHttpServiceState<A, S, W>>>,
    headers: HeaderMap,
    body: Bytes,
) -> Result<Response, BridgeHttpError>
where
    A: RemnawaveAdapter + Send + Sync + 'static,
    S: BridgeStore + Send + Sync + 'static,
    W: WebhookAuthenticator + Send + Sync + 'static,
{
    let credential = header_text(&headers, AUTHORIZATION)
        .and_then(parse_bearer_token)
        .ok_or_else(|| {
            BridgeHttpError::envelope(BridgeErrorCode::InvalidRefreshCredential, None)
        })?;
    let request: DeviceRegisterRequest = decode_json_body(
        body,
        state.budgets.max_json_body_bytes,
        "/v0/device/register",
    )?;
    let now = state.now();
    let auth = state
        .domain
        .resolve_device_registration_auth(&credential, now)
        .await
        .map_err(|error| BridgeHttpError::from_domain(BridgeOperation::DeviceRegister, error))?;
    let manifest_id = ManifestId::new(request.manifest_id).map_err(|error| {
        BridgeHttpError::from_domain(
            BridgeOperation::DeviceRegister,
            BridgeDomainError::Validation(error),
        )
    })?;
    let device_id = DeviceBindingId::new(request.device_id).map_err(|error| {
        BridgeHttpError::from_domain(
            BridgeOperation::DeviceRegister,
            BridgeDomainError::Validation(error),
        )
    })?;

    let result = state
        .domain
        .register_device_with_auth(
            auth,
            DomainDeviceRegistrationRequest {
                manifest_id,
                device_id,
                device_name: request.device_name,
                platform: request.platform,
                client_version: request.client_version,
                install_channel: request.install_channel,
            },
            now,
        )
        .await
        .map_err(|error| BridgeHttpError::from_domain(BridgeOperation::DeviceRegister, error))?;

    Ok(Json(DeviceRegisterResponse {
        device_id: result.device.device_id,
        binding_required: true,
        refresh_credential: Some(result.refresh_credential),
        warnings: Vec::new(),
    })
    .into_response())
}

async fn post_token_exchange<A, S, W>(
    State(state): State<Arc<BridgeHttpServiceState<A, S, W>>>,
    body: Bytes,
) -> Result<Response, BridgeHttpError>
where
    A: RemnawaveAdapter + Send + Sync + 'static,
    S: BridgeStore + Send + Sync + 'static,
    W: WebhookAuthenticator + Send + Sync + 'static,
{
    let request: TokenExchangeRequest = decode_json_body(
        body,
        state.budgets.max_json_body_bytes,
        "/v0/token/exchange",
    )?;
    let now = state.now();
    let result = state
        .domain
        .exchange_token_for_refresh(
            TokenExchangeInput {
                manifest_id: ManifestId::new(request.manifest_id).map_err(|error| {
                    BridgeHttpError::from_domain(
                        BridgeOperation::TokenExchange,
                        BridgeDomainError::Validation(error),
                    )
                })?,
                device_id: DeviceBindingId::new(request.device_id).map_err(|error| {
                    BridgeHttpError::from_domain(
                        BridgeOperation::TokenExchange,
                        BridgeDomainError::Validation(error),
                    )
                })?,
                client_version: request.client_version,
                core_version: u64::from(request.core_version),
                carrier_profile_id: request.carrier_profile_id,
                requested_capabilities: request
                    .requested_capabilities
                    .into_iter()
                    .map(u64::from)
                    .collect(),
                refresh_credential: request.refresh_credential,
            },
            now,
        )
        .await
        .map_err(|error| BridgeHttpError::from_domain(BridgeOperation::TokenExchange, error))?;

    let expires_at = result
        .expires_at
        .format(&time::format_description::well_known::Rfc3339)
        .map_err(|error| {
            BridgeHttpError::plain(StatusCode::INTERNAL_SERVER_ERROR, error.to_string())
        })?;

    Ok(Json(TokenExchangeResponse {
        session_token: result.session_token,
        expires_at,
        policy_epoch: result.policy_epoch,
        recommended_endpoints: Vec::new(),
        warnings: Vec::new(),
    })
    .into_response())
}

async fn get_jwks<A, S, W>(State(state): State<Arc<BridgeHttpServiceState<A, S, W>>>) -> Response
where
    A: RemnawaveAdapter + Send + Sync + 'static,
    S: BridgeStore + Send + Sync + 'static,
    W: WebhookAuthenticator + Send + Sync + 'static,
{
    Json(state.token_jwks.clone()).into_response()
}

async fn post_remnawave_webhook<A, S, W>(
    State(state): State<Arc<BridgeHttpServiceState<A, S, W>>>,
    headers: HeaderMap,
    body: Bytes,
) -> Result<Response, BridgeHttpError>
where
    A: RemnawaveAdapter + Send + Sync + 'static,
    S: BridgeStore + Send + Sync + 'static,
    W: WebhookAuthenticator + Send + Sync + 'static,
{
    if body.len() > state.budgets.max_webhook_body_bytes {
        record_bridge_http_body_rejected(
            "/internal/remnawave/webhook",
            "max_webhook_body_bytes",
            state.budgets.max_webhook_body_bytes,
            body.len(),
        );
        return Err(BridgeHttpError::plain(
            StatusCode::PAYLOAD_TOO_LARGE,
            "webhook body exceeded the configured limit",
        ));
    }

    let payload: VerifiedWebhookPayload = serde_json::from_slice(body.as_ref())
        .map_err(|error| BridgeHttpError::plain(StatusCode::BAD_REQUEST, error.to_string()))?;
    let signature_header = header_text(&headers, "x-remnawave-signature").ok_or_else(|| {
        BridgeHttpError::plain(StatusCode::UNAUTHORIZED, "missing webhook signature")
    })?;
    let timestamp_header = header_text(&headers, "x-remnawave-timestamp").ok_or_else(|| {
        BridgeHttpError::plain(StatusCode::BAD_REQUEST, "missing webhook timestamp")
    })?;

    let effect = state
        .domain
        .ingest_verified_webhook(
            WebhookVerificationInput {
                signature_header,
                timestamp_header,
                body: body.as_ref(),
            },
            state.webhook_authenticator.as_ref(),
            payload,
            state.now(),
            state.webhook_verification,
        )
        .await
        .map_err(BridgeHttpError::from_webhook)?;

    Ok(Json(json!({
        "effect": BridgeDomain::<A, S>::webhook_reconcile_hint(effect),
    }))
    .into_response())
}

fn manifest_etag(manifest: &ns_manifest::ManifestDocument) -> String {
    format!("\"{}\"", manifest.signature.value)
}

fn header_text(headers: &HeaderMap, name: impl axum::http::header::AsHeaderName) -> Option<&str> {
    headers.get(name).and_then(|value| value.to_str().ok())
}

fn decode_json_body<T>(
    body: Bytes,
    max_bytes: usize,
    route: &'static str,
) -> Result<T, BridgeHttpError>
where
    T: DeserializeOwned,
{
    if body.len() > max_bytes {
        record_bridge_http_body_rejected(route, "max_json_body_bytes", max_bytes, body.len());
        return Err(BridgeHttpError::plain(
            StatusCode::PAYLOAD_TOO_LARGE,
            "request body exceeded the configured limit",
        ));
    }
    serde_json::from_slice(body.as_ref())
        .map_err(|error| BridgeHttpError::plain(StatusCode::BAD_REQUEST, error.to_string()))
}

impl BridgeHttpError {
    fn plain(status: StatusCode, message: impl Into<String>) -> Self {
        Self {
            response: Box::new((status, message.into()).into_response()),
        }
    }

    fn envelope(code: BridgeErrorCode, policy_epoch: Option<u64>) -> Self {
        Self {
            response: Box::new(
                (
                    code.recommended_status(),
                    Json(BridgeErrorEnvelope::new(
                        code,
                        code.default_message(),
                        code.retryable(),
                        policy_epoch,
                    )),
                )
                    .into_response(),
            ),
        }
    }

    fn from_domain(operation: BridgeOperation, error: BridgeDomainError) -> Self {
        let code = match error {
            BridgeDomainError::VertaDisabled => BridgeErrorCode::AccountLimited,
            BridgeDomainError::AccountDisabled => BridgeErrorCode::AccountDisabled,
            BridgeDomainError::AccountRevoked => BridgeErrorCode::AccountRevoked,
            BridgeDomainError::AccountExpired => BridgeErrorCode::AccountExpired,
            BridgeDomainError::AccountLimited => BridgeErrorCode::AccountLimited,
            BridgeDomainError::CoreVersionNotAllowed(_) => BridgeErrorCode::CoreVersionNotAllowed,
            BridgeDomainError::CarrierProfileNotAllowed(_) => BridgeErrorCode::ProfileNotAllowed,
            BridgeDomainError::DeviceBindingRequired => BridgeErrorCode::DeviceBindingRequired,
            BridgeDomainError::DeviceRevoked => BridgeErrorCode::DeviceRevoked,
            BridgeDomainError::DeviceLimitReached { .. } => BridgeErrorCode::DeviceLimitReached,
            BridgeDomainError::RefreshCredentialRevoked
            | BridgeDomainError::RefreshCredentialAccountMismatch
            | BridgeDomainError::RefreshCredentialManifestMismatch
            | BridgeDomainError::DeviceIdMismatch
            | BridgeDomainError::CapabilityNotAllowed
            | BridgeDomainError::Storage(StorageError::RefreshCredentialNotFound)
            | BridgeDomainError::BootstrapCredentialManifestMismatch => {
                BridgeErrorCode::InvalidRefreshCredential
            }
            BridgeDomainError::BootstrapCredentialExpired
            | BridgeDomainError::Storage(StorageError::BootstrapGrantNotFound) => {
                BridgeErrorCode::BootstrapExpired
            }
            BridgeDomainError::Adapter(ns_remnawave_adapter::AdapterError::NotFound) => {
                match operation {
                    BridgeOperation::ManifestBootstrap => BridgeErrorCode::InvalidBootstrapSubject,
                    _ => BridgeErrorCode::AccountNotFound,
                }
            }
            BridgeDomainError::Adapter(ns_remnawave_adapter::AdapterError::RateLimited) => {
                BridgeErrorCode::RateLimited
            }
            BridgeDomainError::Adapter(_) => BridgeErrorCode::UpstreamControlPlaneUnavailable,
            BridgeDomainError::Manifest(_) => BridgeErrorCode::ManifestNotAvailable,
            BridgeDomainError::Validation(_) | BridgeDomainError::Auth(_) => {
                BridgeErrorCode::TemporaryReconciliationInProgress
            }
            BridgeDomainError::Storage(_) => BridgeErrorCode::TemporaryReconciliationInProgress,
            BridgeDomainError::WebhookVerification(_) => {
                BridgeErrorCode::UpstreamControlPlaneUnavailable
            }
            BridgeDomainError::DuplicateWebhookDelivery => BridgeErrorCode::RateLimited,
            BridgeDomainError::InvalidBootstrapGrantTtl => {
                BridgeErrorCode::TemporaryReconciliationInProgress
            }
        };
        Self::envelope(code, None)
    }

    fn from_webhook(error: BridgeDomainError) -> Self {
        match error {
            BridgeDomainError::DuplicateWebhookDelivery => {
                Self::plain(StatusCode::CONFLICT, "duplicate webhook delivery")
            }
            BridgeDomainError::WebhookVerification(_) => {
                Self::plain(StatusCode::UNAUTHORIZED, "webhook verification failed")
            }
            other => Self::from_domain(BridgeOperation::ManifestRefresh, other),
        }
    }
}

impl IntoResponse for BridgeHttpError {
    fn into_response(self) -> Response {
        *self.response
    }
}

#[derive(Debug, Error, Clone, PartialEq, Eq)]
pub enum BridgeApiError {
    #[error("manifest fetch must use exactly one auth mode")]
    ConflictingManifestAuthModes,
    #[error("manifest fetch requires bootstrap or refresh auth")]
    MissingManifestAuth,
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::{Body, to_bytes};
    use ed25519_dalek::SigningKey;
    use ed25519_dalek::pkcs8::EncodePrivateKey;
    use ns_auth::SessionTokenSigner;
    use ns_bridge_domain::{BridgeCarrierProfile, BridgeGatewayEndpoint, BridgeManifestContext};
    use ns_manifest::{
        ClientConstraints, ConnectBackoff, DevicePolicy, HttpTemplate, HttpTemplateMethod,
        ManifestCarrierKind, ManifestDocument, ManifestSigner, RefreshMode, RefreshPolicy,
        RetryPolicy, RoutingFailoverMode, RoutingPolicy, RoutingSelectionMode, TelemetryPolicy,
        TokenService, ZeroRttPolicy,
    };
    use ns_remnawave_adapter::{
        AccountLifecycle, AccountSnapshot, AdapterWebhookEffect, FakeRemnawaveAdapter, VertaAccess,
        WebhookAuthenticator, WebhookVerificationError,
    };
    use ns_storage::{InMemoryBridgeStore, SharedBridgeStore};
    use std::collections::BTreeMap;
    use tower::ServiceExt;
    use url::Url;

    struct AcceptAllWebhookAuthenticator;

    impl WebhookAuthenticator for AcceptAllWebhookAuthenticator {
        fn verify(
            &self,
            _timestamp_header: &str,
            signature_header: &str,
            _body: &[u8],
        ) -> Result<(), WebhookVerificationError> {
            match signature_header {
                "sig-ok" => Ok(()),
                _ => Err(WebhookVerificationError::InvalidSignature),
            }
        }
    }

    fn fixed_now() -> OffsetDateTime {
        OffsetDateTime::from_unix_timestamp(1_775_002_200)
            .expect("fixture timestamp should be valid")
    }

    fn sample_snapshot() -> AccountSnapshot {
        AccountSnapshot {
            account_id: "acct-1".to_owned(),
            bootstrap_subjects: vec![BootstrapSubject::ShortUuid("sub-1".to_owned())],
            lifecycle: AccountLifecycle::Active,
            verta_access: VertaAccess {
                verta_enabled: true,
                policy_epoch: 7,
                device_limit: Some(2),
                allowed_core_versions: vec![1],
                allowed_carrier_profiles: vec!["carrier-primary".to_owned()],
                allowed_capabilities: vec![1, 2],
                rollout_cohort: Some("alpha".to_owned()),
                preferred_regions: vec!["eu-central".to_owned()],
            },
            metadata: None,
            observed_at_unix: 1_700_000_000,
            source_version: Some("2.7.4".to_owned()),
        }
    }

    fn sample_manifest_template() -> BridgeManifestTemplate {
        BridgeManifestTemplate {
            context: BridgeManifestContext {
                device_policy: Some(DevicePolicy {
                    max_devices: 2,
                    require_device_binding: true,
                }),
                client_constraints: ClientConstraints {
                    min_client_version: "0.1.0".to_owned(),
                    recommended_client_version: "0.1.0".to_owned(),
                    allowed_core_versions: vec![1],
                },
                token_service: TokenService {
                    url: Url::parse("https://bridge.example/v0/token/exchange")
                        .expect("fixture token url should parse"),
                    issuer: "bridge.example".to_owned(),
                    jwks_url: Url::parse("https://bridge.example/.well-known/jwks.json")
                        .expect("fixture jwks url should parse"),
                    session_token_ttl_seconds: 300,
                },
                refresh: Some(RefreshPolicy {
                    mode: RefreshMode::OpaqueSecret,
                    credential: "placeholder".to_owned(),
                    rotation_hint_seconds: Some(86_400),
                }),
                routing: RoutingPolicy {
                    selection_mode: RoutingSelectionMode::LatencyWeighted,
                    failover_mode: RoutingFailoverMode::SameRegionThenGlobal,
                },
                retry_policy: RetryPolicy {
                    connect_attempts: 3,
                    initial_backoff_ms: 500,
                    max_backoff_ms: 10_000,
                },
                telemetry: TelemetryPolicy {
                    allow_client_reports: true,
                    sample_rate: 0.05,
                },
            },
            carrier_profiles: vec![BridgeCarrierProfile {
                id: "carrier-primary".to_owned(),
                carrier_kind: ManifestCarrierKind::H3,
                origin_host: "origin.edge.example.net".to_owned(),
                origin_port: 8443,
                sni: Some("origin.edge.example.net".to_owned()),
                alpn: vec!["h3".to_owned()],
                control_template: HttpTemplate {
                    method: HttpTemplateMethod::Connect,
                    path: "/ns/control".to_owned(),
                },
                relay_template: HttpTemplate {
                    method: HttpTemplateMethod::Connect,
                    path: "/ns/relay".to_owned(),
                },
                headers: BTreeMap::from([(
                    "x-verta-profile".to_owned(),
                    "carrier-primary".to_owned(),
                )]),
                datagram_enabled: false,
                heartbeat_interval_ms: 20_000,
                idle_timeout_ms: 90_000,
                zero_rtt_policy: Some(ZeroRttPolicy::Disabled),
                connect_backoff: ConnectBackoff {
                    initial_ms: 500,
                    max_ms: 10_000,
                    jitter: 0.2,
                },
            }],
            endpoints: vec![BridgeGatewayEndpoint {
                id: "edge-1".to_owned(),
                host: "edge.example.net".to_owned(),
                port: 443,
                region: "eu-central".to_owned(),
                routing_group: Some("primary".to_owned()),
                carrier_profile_ids: vec!["carrier-primary".to_owned()],
                priority: 10,
                weight: 100,
                tags: vec!["stable".to_owned()],
            }],
            manifest_ttl: time::Duration::hours(6),
            bootstrap_grant_ttl: time::Duration::minutes(5),
        }
    }

    fn build_router() -> Router {
        build_router_with_budgets(BridgeHttpBudgets::default())
    }

    fn build_router_with_budgets(budgets: BridgeHttpBudgets) -> Router {
        let adapter = FakeRemnawaveAdapter::with_account(
            BootstrapSubject::ShortUuid("sub-1".to_owned()),
            sample_snapshot(),
        );
        adapter.push_webhook_effect(AdapterWebhookEffect::ReconcileAccount {
            account_id: "acct-1".to_owned(),
            reason: "fixture".to_owned(),
        });

        let token_signing_key = SigningKey::from_bytes(&[12_u8; 32]);
        let token_pem = token_signing_key
            .to_pkcs8_pem(Default::default())
            .expect("fixture token key should encode");
        let token_signer = SessionTokenSigner::from_ed_pem(
            "bridge.example",
            "verta-gateway",
            "bridge-token-2026-01",
            token_pem.as_bytes(),
        )
        .expect("fixture token signer should initialize");
        let token_jwks =
            serde_json::to_value(token_signer.jwks()).expect("fixture jwks should serialize");
        let manifest_signer = ManifestSigner::new(
            "bridge-manifest-2026-01",
            SigningKey::from_bytes(&[13_u8; 32]),
        );
        let domain = Arc::new(BridgeDomain::new(
            adapter,
            SharedBridgeStore::new(InMemoryBridgeStore::default()),
            manifest_signer,
            token_signer,
            time::Duration::seconds(300),
        ));

        build_bridge_router(BridgeHttpServiceState::new_with_clock(
            domain,
            sample_manifest_template(),
            Arc::new(AcceptAllWebhookAuthenticator),
            WebhookVerificationConfig::default(),
            token_jwks,
            budgets,
            Arc::new(fixed_now),
        ))
    }

    #[test]
    fn parses_bootstrap_manifest_request() {
        let mode = parse_manifest_request(Some("sub-1"), None)
            .expect("bootstrap manifest request should parse");
        assert!(matches!(mode, ManifestRequestMode::Bootstrap { .. }));
    }

    #[test]
    fn rejects_conflicting_manifest_auth() {
        let error = parse_manifest_request(Some("sub-1"), Some("Bearer rfr_123")).unwrap_err();
        assert!(matches!(
            error,
            BridgeApiError::ConflictingManifestAuthModes
        ));
    }

    #[tokio::test]
    async fn bootstrap_manifest_register_and_token_exchange_flow_compose_over_http() {
        let router = build_router();

        let manifest_response = router
            .clone()
            .oneshot(
                axum::http::Request::builder()
                    .uri("/v0/manifest?subscription_token=sub-1")
                    .body(Body::empty())
                    .expect("manifest request should build"),
            )
            .await
            .expect("manifest request should succeed");
        assert_eq!(manifest_response.status(), StatusCode::OK);
        let manifest_body = to_bytes(manifest_response.into_body(), usize::MAX)
            .await
            .expect("manifest body should read");
        let manifest: ManifestDocument =
            serde_json::from_slice(manifest_body.as_ref()).expect("manifest response should parse");
        assert_eq!(
            manifest
                .refresh
                .as_ref()
                .map(|refresh| refresh.mode.clone()),
            Some(RefreshMode::BootstrapOnly)
        );
        let bootstrap_credential = manifest
            .refresh
            .as_ref()
            .map(|refresh| refresh.credential.clone())
            .expect("bootstrap manifest should carry a bootstrap credential");

        let register_response = router
            .clone()
            .oneshot(
                axum::http::Request::builder()
                    .method("POST")
                    .uri("/v0/device/register")
                    .header(AUTHORIZATION, format!("Bearer {bootstrap_credential}"))
                    .header("content-type", "application/json")
                    .body(Body::from(
                        serde_json::to_vec(&json!({
                            "manifest_id": manifest.manifest_id,
                            "device_id": "device-1",
                            "device_name": "Workstation",
                            "platform": "windows",
                            "client_version": "0.1.0",
                            "install_channel": "stable",
                            "requested_capabilities": [1, 2],
                        }))
                        .expect("device-register payload should serialize"),
                    ))
                    .expect("device-register request should build"),
            )
            .await
            .expect("device-register request should succeed");
        assert_eq!(register_response.status(), StatusCode::OK);
        let register_body = to_bytes(register_response.into_body(), usize::MAX)
            .await
            .expect("device-register body should read");
        let register: DeviceRegisterResponse = serde_json::from_slice(register_body.as_ref())
            .expect("device-register response should parse");
        let refresh_credential = register
            .refresh_credential
            .clone()
            .expect("device register should issue a refresh credential");

        let token_exchange_response = router
            .clone()
            .oneshot(
                axum::http::Request::builder()
                    .method("POST")
                    .uri("/v0/token/exchange")
                    .header("content-type", "application/json")
                    .body(Body::from(
                        serde_json::to_vec(&TokenExchangeRequest {
                            manifest_id: manifest.manifest_id,
                            device_id: "device-1".to_owned(),
                            client_version: "0.1.0".to_owned(),
                            core_version: 1,
                            carrier_profile_id: "carrier-primary".to_owned(),
                            requested_capabilities: vec![1, 2],
                            refresh_credential,
                        })
                        .expect("token-exchange payload should serialize"),
                    ))
                    .expect("token-exchange request should build"),
            )
            .await
            .expect("token-exchange request should succeed");
        assert_eq!(token_exchange_response.status(), StatusCode::OK);
        let exchange_body = to_bytes(token_exchange_response.into_body(), usize::MAX)
            .await
            .expect("token-exchange body should read");
        let exchange: TokenExchangeResponse = serde_json::from_slice(exchange_body.as_ref())
            .expect("token-exchange response should parse");
        assert!(!exchange.session_token.is_empty());
    }

    #[tokio::test]
    async fn remnawave_webhook_is_deduplicated_over_http() {
        let router = build_router();
        let payload = json!({
            "event_id": "evt-1",
            "event_type": "subscription.updated",
            "account_id": "acct-1",
            "occurred_at_unix": fixed_now().unix_timestamp(),
            "payload": { "plan": "pro" }
        });

        let request = || {
            axum::http::Request::builder()
                .method("POST")
                .uri("/internal/remnawave/webhook")
                .header("x-remnawave-signature", "sig-ok")
                .header(
                    "x-remnawave-timestamp",
                    fixed_now().unix_timestamp().to_string(),
                )
                .header("content-type", "application/json")
                .body(Body::from(
                    serde_json::to_vec(&payload).expect("webhook payload should serialize"),
                ))
                .expect("webhook request should build")
        };

        let first = router
            .clone()
            .oneshot(request())
            .await
            .expect("first webhook delivery should succeed");
        assert_eq!(first.status(), StatusCode::OK);

        let duplicate = router
            .clone()
            .oneshot(request())
            .await
            .expect("duplicate webhook delivery should return a response");
        assert_eq!(duplicate.status(), StatusCode::CONFLICT);
    }

    #[tokio::test]
    async fn manifest_etag_supports_not_modified_responses() {
        let router = build_router();
        let manifest_response = router
            .clone()
            .oneshot(
                axum::http::Request::builder()
                    .uri("/v0/manifest?subscription_token=sub-1")
                    .body(Body::empty())
                    .expect("manifest request should build"),
            )
            .await
            .expect("bootstrap manifest request should succeed");
        assert_eq!(manifest_response.status(), StatusCode::OK);
        let manifest_body = to_bytes(manifest_response.into_body(), usize::MAX)
            .await
            .expect("bootstrap manifest body should read");
        let manifest: ManifestDocument = serde_json::from_slice(manifest_body.as_ref())
            .expect("bootstrap manifest should parse");
        let bootstrap_credential = manifest
            .refresh
            .as_ref()
            .map(|refresh| refresh.credential.clone())
            .expect("bootstrap manifest should carry a bootstrap credential");

        let register_response = router
            .clone()
            .oneshot(
                axum::http::Request::builder()
                    .method("POST")
                    .uri("/v0/device/register")
                    .header(AUTHORIZATION, format!("Bearer {bootstrap_credential}"))
                    .header("content-type", "application/json")
                    .body(Body::from(
                        serde_json::to_vec(&json!({
                            "manifest_id": manifest.manifest_id,
                            "device_id": "device-1",
                            "device_name": "Workstation",
                            "platform": "windows",
                            "client_version": "0.1.0",
                            "install_channel": "stable",
                            "requested_capabilities": [1, 2],
                        }))
                        .expect("device-register payload should serialize"),
                    ))
                    .expect("device-register request should build"),
            )
            .await
            .expect("device-register request should succeed");
        assert_eq!(register_response.status(), StatusCode::OK);
        let register_body = to_bytes(register_response.into_body(), usize::MAX)
            .await
            .expect("device-register body should read");
        let register: DeviceRegisterResponse = serde_json::from_slice(register_body.as_ref())
            .expect("device-register response should parse");
        let refresh_credential = register
            .refresh_credential
            .expect("device-register should issue a refresh credential");

        let refresh_request = |etag: Option<&str>| {
            let mut builder = axum::http::Request::builder().uri("/v0/manifest");
            builder = builder.header(AUTHORIZATION, format!("Bearer {refresh_credential}"));
            if let Some(value) = etag {
                builder = builder.header(IF_NONE_MATCH, value);
            }
            builder
                .body(Body::empty())
                .expect("refresh manifest request should build")
        };

        let initial = router
            .clone()
            .oneshot(refresh_request(None))
            .await
            .expect("initial refresh manifest request should succeed");
        assert_eq!(initial.status(), StatusCode::OK);
        let etag = initial
            .headers()
            .get(ETAG)
            .and_then(|value| value.to_str().ok())
            .map(str::to_owned)
            .expect("refresh manifest responses should carry an ETag");

        let not_modified = router
            .clone()
            .oneshot(refresh_request(Some(&etag)))
            .await
            .expect("conditional refresh manifest request should succeed");
        assert_eq!(not_modified.status(), StatusCode::NOT_MODIFIED);
    }

    #[tokio::test]
    async fn json_routes_enforce_their_own_body_limit_before_webhook_budget() {
        let router = build_router_with_budgets(BridgeHttpBudgets {
            max_json_body_bytes: 96,
            max_webhook_body_bytes: 8 * 1024,
        });
        let oversized = serde_json::json!({
            "manifest_id": "man-2026-04-01-001",
            "device_id": "device-1",
            "client_version": "0.1.0",
            "core_version": 1,
            "carrier_profile_id": "carrier-primary",
            "requested_capabilities": [1, 2],
            "refresh_credential": "rfr_fixture",
            "padding": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        });

        let response = router
            .clone()
            .oneshot(
                axum::http::Request::builder()
                    .method("POST")
                    .uri("/v0/token/exchange")
                    .header("content-type", "application/json")
                    .body(Body::from(
                        serde_json::to_vec(&oversized)
                            .expect("oversized token-exchange payload should serialize"),
                    ))
                    .expect("oversized token-exchange request should build"),
            )
            .await
            .expect("oversized token-exchange request should return a response");
        assert_eq!(response.status(), StatusCode::PAYLOAD_TOO_LARGE);
    }
}
