use crate::{
    AccountLifecycle, AccountSnapshot, AdapterError, AdapterWebhookEffect, BootstrapSubject,
    RemnawaveAdapter, VerifiedWebhookPayload, VertaAccess,
};
use async_trait::async_trait;
use reqwest::StatusCode;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::time::Duration as StdDuration;
use time::OffsetDateTime;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HttpRemnawaveAdapterConfig {
    pub base_url: String,
    pub api_token: String,
    pub request_timeout_ms: u64,
}

impl HttpRemnawaveAdapterConfig {
    pub fn new(
        base_url: impl Into<String>,
        api_token: impl Into<String>,
        request_timeout_ms: u64,
    ) -> Result<Self, AdapterError> {
        let base_url = base_url.into();
        let api_token = api_token.into();
        if base_url.trim().is_empty() {
            return Err(AdapterError::InvalidData("base_url"));
        }
        let url =
            reqwest::Url::parse(&base_url).map_err(|_| AdapterError::InvalidData("base_url"))?;
        if !matches!(url.scheme(), "http" | "https") {
            return Err(AdapterError::InvalidData("base_url"));
        }
        if api_token.trim().is_empty() {
            return Err(AdapterError::InvalidData("api_token"));
        }
        if request_timeout_ms == 0 {
            return Err(AdapterError::InvalidData("request_timeout_ms"));
        }
        Ok(Self {
            base_url,
            api_token,
            request_timeout_ms,
        })
    }

    fn request_timeout(&self) -> StdDuration {
        StdDuration::from_millis(self.request_timeout_ms)
    }

    fn endpoint(&self, path: &str) -> Result<reqwest::Url, AdapterError> {
        reqwest::Url::parse(&self.base_url)
            .map_err(|_| AdapterError::InvalidData("base_url"))?
            .join(path)
            .map_err(|_| AdapterError::InvalidData("base_url"))
    }
}

#[derive(Clone)]
pub struct HttpRemnawaveAdapter {
    config: HttpRemnawaveAdapterConfig,
    client: reqwest::Client,
}

impl HttpRemnawaveAdapter {
    pub fn new(config: HttpRemnawaveAdapterConfig) -> Self {
        Self::new_with_client(config, reqwest::Client::new())
    }

    pub fn new_with_client(config: HttpRemnawaveAdapterConfig, client: reqwest::Client) -> Self {
        Self { config, client }
    }

    fn request(&self, builder: reqwest::RequestBuilder) -> reqwest::RequestBuilder {
        builder
            .timeout(self.config.request_timeout())
            .bearer_auth(&self.config.api_token)
    }

    async fn decode_json<T: serde::de::DeserializeOwned>(
        &self,
        response: reqwest::Response,
    ) -> Result<T, AdapterError> {
        response
            .json::<T>()
            .await
            .map_err(|_| AdapterError::SchemaDrift)
    }

    async fn decode_bytes(&self, response: reqwest::Response) -> Result<Vec<u8>, AdapterError> {
        response
            .bytes()
            .await
            .map(|bytes| bytes.to_vec())
            .map_err(|_| AdapterError::SchemaDrift)
    }
}

#[derive(Debug, Serialize)]
struct LegacyResolveBootstrapRequest<'a> {
    bootstrap_subject_kind: &'static str,
    bootstrap_subject: &'a str,
}

#[derive(Debug, Serialize)]
struct CurrentResolveBootstrapRequest<'a> {
    #[serde(skip_serializing_if = "Option::is_none")]
    uuid: Option<&'a str>,
    #[serde(skip_serializing_if = "Option::is_none")]
    id: Option<&'a str>,
    #[serde(rename = "shortUuid", skip_serializing_if = "Option::is_none")]
    short_uuid: Option<&'a str>,
    #[serde(skip_serializing_if = "Option::is_none")]
    username: Option<&'a str>,
}

#[derive(Debug, Deserialize)]
struct CurrentResolveBootstrapResponse {
    uuid: String,
}

#[derive(Debug, Deserialize)]
struct CurrentUserPayload {
    uuid: String,
    #[serde(rename = "shortUuid", default)]
    short_uuid: Option<String>,
    status: String,
    #[serde(rename = "subRevokedAt", default)]
    sub_revoked_at: Option<String>,
    #[serde(rename = "hwidDeviceLimit", default)]
    hwid_device_limit: Option<u32>,
}

#[derive(Debug, Deserialize)]
struct ResponseEnvelope<T> {
    response: T,
}

#[async_trait]
impl RemnawaveAdapter for HttpRemnawaveAdapter {
    async fn resolve_bootstrap_subject(
        &self,
        subject: &BootstrapSubject,
    ) -> Result<AccountSnapshot, AdapterError> {
        subject.validate()?;
        let legacy_request = LegacyResolveBootstrapRequest {
            bootstrap_subject_kind: bootstrap_subject_kind(subject),
            bootstrap_subject: subject.as_str(),
        };
        let response = self
            .request(
                self.client
                    .post(self.config.endpoint("/api/users/resolve")?)
                    .json(&legacy_request),
            )
            .send()
            .await
            .map_err(map_request_error)?;
        if response.status().is_success() {
            let body = self.decode_bytes(response).await?;
            if let Ok(snapshot) = parse_account_snapshot_payload(&body) {
                return Ok(snapshot);
            }
            if let Ok(reference) = parse_current_resolve_response(&body) {
                return self.fetch_account_snapshot(&reference.uuid).await;
            }
            return Err(AdapterError::SchemaDrift);
        }

        if response.status() != StatusCode::BAD_REQUEST {
            return Err(map_status(response.status()));
        }

        let current_request = match current_resolve_request(subject) {
            Some(request) => request,
            None => return Err(map_status(StatusCode::BAD_REQUEST)),
        };
        let current_response = self
            .request(
                self.client
                    .post(self.config.endpoint("/api/users/resolve")?)
                    .json(&current_request),
            )
            .send()
            .await
            .map_err(map_request_error)?;
        if !current_response.status().is_success() {
            return Err(map_status(current_response.status()));
        }
        let body = self.decode_bytes(current_response).await?;
        if let Ok(snapshot) = parse_account_snapshot_payload(&body) {
            return Ok(snapshot);
        }
        let reference = parse_current_resolve_response(&body)?;
        self.fetch_account_snapshot(&reference.uuid).await
    }

    async fn fetch_account_snapshot(
        &self,
        account_id: &str,
    ) -> Result<AccountSnapshot, AdapterError> {
        if account_id.trim().is_empty() {
            return Err(AdapterError::InvalidData("account_id"));
        }
        let response = self
            .request(
                self.client
                    .get(self.config.endpoint(&format!("/api/users/{account_id}"))?),
            )
            .send()
            .await
            .map_err(map_request_error)?;
        if !response.status().is_success() {
            return Err(map_status(response.status()));
        }
        let body = self.decode_bytes(response).await?;
        parse_account_snapshot_payload(&body)
    }

    async fn fetch_user_metadata(&self, account_id: &str) -> Result<Option<Value>, AdapterError> {
        if account_id.trim().is_empty() {
            return Err(AdapterError::InvalidData("account_id"));
        }
        let response = self
            .request(
                self.client.get(
                    self.config
                        .endpoint(&format!("/api/users/{account_id}/metadata"))?,
                ),
            )
            .send()
            .await
            .map_err(map_request_error)?;
        if response.status() == StatusCode::NOT_FOUND {
            return Ok(None);
        }
        if !response.status().is_success() {
            return Err(map_status(response.status()));
        }
        self.decode_json(response).await.map(Some)
    }

    async fn upsert_user_metadata(
        &self,
        account_id: &str,
        patch: Value,
    ) -> Result<(), AdapterError> {
        if account_id.trim().is_empty() {
            return Err(AdapterError::InvalidData("account_id"));
        }
        let response = self
            .request(
                self.client
                    .put(
                        self.config
                            .endpoint(&format!("/api/users/{account_id}/metadata"))?,
                    )
                    .json(&patch),
            )
            .send()
            .await
            .map_err(map_request_error)?;
        if !response.status().is_success() {
            return Err(map_status(response.status()));
        }
        Ok(())
    }

    async fn ingest_verified_webhook(
        &self,
        payload: VerifiedWebhookPayload,
    ) -> Result<AdapterWebhookEffect, AdapterError> {
        Ok(map_verified_webhook(payload))
    }
}

fn bootstrap_subject_kind(subject: &BootstrapSubject) -> &'static str {
    match subject {
        BootstrapSubject::ShortUuid(_) => "short_uuid",
        BootstrapSubject::BridgeAlias(_) => "bridge_alias",
        BootstrapSubject::SignedEnvelope(_) => "signed_envelope",
    }
}

fn current_resolve_request(
    subject: &BootstrapSubject,
) -> Option<CurrentResolveBootstrapRequest<'_>> {
    match subject {
        BootstrapSubject::ShortUuid(value) => Some(CurrentResolveBootstrapRequest {
            uuid: None,
            id: None,
            short_uuid: Some(value),
            username: None,
        }),
        _ => None,
    }
}

fn parse_account_snapshot_payload(payload: &[u8]) -> Result<AccountSnapshot, AdapterError> {
    if let Ok(snapshot) = serde_json::from_slice::<AccountSnapshot>(payload) {
        return Ok(snapshot);
    }
    if let Ok(envelope) = serde_json::from_slice::<ResponseEnvelope<CurrentUserPayload>>(payload) {
        return map_current_user_payload(envelope.response);
    }
    if let Ok(current) = serde_json::from_slice::<CurrentUserPayload>(payload) {
        return map_current_user_payload(current);
    }
    Err(AdapterError::SchemaDrift)
}

fn parse_current_resolve_response(
    payload: &[u8],
) -> Result<CurrentResolveBootstrapResponse, AdapterError> {
    if let Ok(envelope) =
        serde_json::from_slice::<ResponseEnvelope<CurrentResolveBootstrapResponse>>(payload)
    {
        return Ok(envelope.response);
    }
    serde_json::from_slice::<CurrentResolveBootstrapResponse>(payload)
        .map_err(|_| AdapterError::SchemaDrift)
}

fn map_current_user_payload(payload: CurrentUserPayload) -> Result<AccountSnapshot, AdapterError> {
    let account_id = payload.uuid.trim();
    if account_id.is_empty() {
        return Err(AdapterError::SchemaDrift);
    }
    let short_uuid = payload
        .short_uuid
        .as_deref()
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .ok_or(AdapterError::SchemaDrift)?;
    let lifecycle = parse_current_lifecycle(&payload.status, payload.sub_revoked_at.as_deref())?;

    Ok(AccountSnapshot {
        account_id: account_id.to_owned(),
        bootstrap_subjects: vec![BootstrapSubject::ShortUuid(short_uuid.to_owned())],
        lifecycle,
        verta_access: VertaAccess {
            verta_enabled: true,
            policy_epoch: default_policy_epoch(lifecycle),
            device_limit: payload.hwid_device_limit,
            allowed_core_versions: vec![1],
            allowed_carrier_profiles: vec!["carrier-primary".to_owned()],
            allowed_capabilities: vec![1, 2],
            rollout_cohort: None,
            preferred_regions: vec!["eu-central".to_owned()],
        },
        metadata: None,
        observed_at_unix: OffsetDateTime::now_utc().unix_timestamp(),
        source_version: None,
    })
}

fn parse_current_lifecycle(
    status: &str,
    sub_revoked_at: Option<&str>,
) -> Result<AccountLifecycle, AdapterError> {
    if sub_revoked_at.is_some_and(|value| !value.trim().is_empty()) {
        return Ok(AccountLifecycle::Revoked);
    }

    match status.trim().to_ascii_uppercase().as_str() {
        "ACTIVE" => Ok(AccountLifecycle::Active),
        "DISABLED" => Ok(AccountLifecycle::Disabled),
        "REVOKED" => Ok(AccountLifecycle::Revoked),
        "EXPIRED" => Ok(AccountLifecycle::Expired),
        "LIMITED" => Ok(AccountLifecycle::Limited),
        _ => Err(AdapterError::SchemaDrift),
    }
}

fn default_policy_epoch(lifecycle: AccountLifecycle) -> u64 {
    match lifecycle {
        AccountLifecycle::Active => 7,
        AccountLifecycle::Disabled => 8,
        AccountLifecycle::Revoked => 9,
        AccountLifecycle::Expired => 10,
        AccountLifecycle::Limited => 11,
    }
}

fn map_request_error(error: reqwest::Error) -> AdapterError {
    if error.is_timeout() {
        AdapterError::Timeout
    } else {
        AdapterError::Unavailable
    }
}

fn map_status(status: StatusCode) -> AdapterError {
    match status {
        StatusCode::UNAUTHORIZED | StatusCode::FORBIDDEN => AdapterError::Unauthorized,
        StatusCode::NOT_FOUND => AdapterError::NotFound,
        StatusCode::CONFLICT => AdapterError::Conflict,
        StatusCode::TOO_MANY_REQUESTS => AdapterError::RateLimited,
        StatusCode::REQUEST_TIMEOUT => AdapterError::Timeout,
        status if status.is_server_error() => AdapterError::Unavailable,
        _ => AdapterError::SchemaDrift,
    }
}

fn map_verified_webhook(payload: VerifiedWebhookPayload) -> AdapterWebhookEffect {
    match payload.event_type.as_str() {
        "user.created"
        | "user.modified"
        | "user.deleted"
        | "user.revoked"
        | "user.disabled"
        | "user.enabled"
        | "user.limited"
        | "user.expired"
        | "user.traffic_reset"
        | "user_hwid_devices.added"
        | "user_hwid_devices.deleted"
        | "subscription.updated" => payload
            .account_id
            .map(|account_id| AdapterWebhookEffect::ReconcileAccount {
                account_id,
                reason: payload.event_type,
            })
            .unwrap_or(AdapterWebhookEffect::ReconcileAll {
                reason: "missing_account_scope".to_owned(),
            }),
        "service.subpage_config_changed" => AdapterWebhookEffect::ReconcileAll {
            reason: payload.event_type,
        },
        _ => AdapterWebhookEffect::Noop,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{AccountLifecycle, VertaAccess};
    use axum::extract::{Path, State};
    use axum::http::HeaderMap;
    use axum::http::header::AUTHORIZATION;
    use axum::routing::{get, post};
    use axum::{Json, Router};
    use std::collections::HashMap;
    use std::fs;
    use std::path::PathBuf;
    use std::sync::{Arc, Mutex};
    use tokio::net::TcpListener;

    #[derive(Default)]
    struct TestState {
        account: Mutex<Option<AccountSnapshot>>,
        metadata: Mutex<HashMap<String, Value>>,
        expected_token: String,
        current_payload: Mutex<Option<Value>>,
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

    fn repo_root() -> PathBuf {
        let mut root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        root.pop();
        root.pop();
        root
    }

    fn load_schema_drift_fixture() -> String {
        fs::read_to_string(
            repo_root().join("fixtures/remnawave/account/BG-UPSTREAM-ACCOUNT-SCHEMADRIFT-010.json"),
        )
        .expect("schema-drift fixture should be readable")
    }

    fn authorized(headers: &HeaderMap, expected_token: &str) -> bool {
        headers
            .get(AUTHORIZATION)
            .and_then(|value| value.to_str().ok())
            .and_then(|value| value.strip_prefix("Bearer "))
            == Some(expected_token)
    }

    async fn resolve_user(
        State(state): State<Arc<TestState>>,
        headers: HeaderMap,
    ) -> Result<Json<AccountSnapshot>, StatusCode> {
        if !authorized(&headers, &state.expected_token) {
            return Err(StatusCode::UNAUTHORIZED);
        }
        let snapshot = state
            .account
            .lock()
            .expect("test state poisoned")
            .clone()
            .ok_or(StatusCode::NOT_FOUND)?;
        Ok(Json(snapshot))
    }

    async fn resolve_user_schema_drift(
        State(state): State<Arc<TestState>>,
        headers: HeaderMap,
    ) -> Result<(StatusCode, [(&'static str, &'static str); 1], String), StatusCode> {
        if !authorized(&headers, &state.expected_token) {
            return Err(StatusCode::UNAUTHORIZED);
        }

        Ok((
            StatusCode::OK,
            [("content-type", "application/json")],
            load_schema_drift_fixture(),
        ))
    }

    async fn get_user(
        State(state): State<Arc<TestState>>,
        headers: HeaderMap,
        Path(account_id): Path<String>,
    ) -> Result<Json<AccountSnapshot>, StatusCode> {
        if !authorized(&headers, &state.expected_token) {
            return Err(StatusCode::UNAUTHORIZED);
        }
        let snapshot = state
            .account
            .lock()
            .expect("test state poisoned")
            .clone()
            .ok_or(StatusCode::NOT_FOUND)?;
        if snapshot.account_id != account_id {
            return Err(StatusCode::NOT_FOUND);
        }
        Ok(Json(snapshot))
    }

    async fn resolve_user_current_shape(
        State(state): State<Arc<TestState>>,
        headers: HeaderMap,
    ) -> Result<Json<Value>, StatusCode> {
        if !authorized(&headers, &state.expected_token) {
            return Err(StatusCode::UNAUTHORIZED);
        }
        let payload = state
            .current_payload
            .lock()
            .expect("test state poisoned")
            .clone()
            .ok_or(StatusCode::NOT_FOUND)?;
        Ok(Json(payload))
    }

    async fn get_user_current_shape(
        State(state): State<Arc<TestState>>,
        headers: HeaderMap,
        Path(account_id): Path<String>,
    ) -> Result<Json<Value>, StatusCode> {
        if !authorized(&headers, &state.expected_token) {
            return Err(StatusCode::UNAUTHORIZED);
        }
        let payload = state
            .current_payload
            .lock()
            .expect("test state poisoned")
            .clone()
            .ok_or(StatusCode::NOT_FOUND)?;
        if payload
            .get("response")
            .and_then(|value| value.get("uuid"))
            .and_then(|value| value.as_str())
            != Some(account_id.as_str())
        {
            return Err(StatusCode::NOT_FOUND);
        }
        Ok(Json(payload))
    }

    async fn get_metadata(
        State(state): State<Arc<TestState>>,
        headers: HeaderMap,
        Path(account_id): Path<String>,
    ) -> Result<Json<Value>, StatusCode> {
        if !authorized(&headers, &state.expected_token) {
            return Err(StatusCode::UNAUTHORIZED);
        }
        state
            .metadata
            .lock()
            .expect("test state poisoned")
            .get(&account_id)
            .cloned()
            .map(Json)
            .ok_or(StatusCode::NOT_FOUND)
    }

    async fn put_metadata(
        State(state): State<Arc<TestState>>,
        headers: HeaderMap,
        Path(account_id): Path<String>,
        Json(patch): Json<Value>,
    ) -> Result<StatusCode, StatusCode> {
        if !authorized(&headers, &state.expected_token) {
            return Err(StatusCode::UNAUTHORIZED);
        }
        state
            .metadata
            .lock()
            .expect("test state poisoned")
            .insert(account_id, patch);
        Ok(StatusCode::NO_CONTENT)
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
        tokio::time::sleep(StdDuration::from_millis(10)).await;
        (format!("http://{addr}"), handle)
    }

    async fn fetch_snapshot_until_non_unavailable(
        adapter: &HttpRemnawaveAdapter,
        account_id: &str,
    ) -> Result<AccountSnapshot, AdapterError> {
        for _ in 0..10 {
            match adapter.fetch_account_snapshot(account_id).await {
                Err(AdapterError::Unavailable) => {
                    tokio::time::sleep(StdDuration::from_millis(25)).await;
                }
                other => return other,
            }
        }

        Err(AdapterError::Unavailable)
    }

    async fn resolve_bootstrap_subject_until_non_unavailable(
        adapter: &HttpRemnawaveAdapter,
        subject: BootstrapSubject,
    ) -> Result<AccountSnapshot, AdapterError> {
        for _ in 0..10 {
            match adapter.resolve_bootstrap_subject(&subject).await {
                Err(AdapterError::Unavailable) => {
                    tokio::time::sleep(StdDuration::from_millis(25)).await;
                }
                other => return other,
            }
        }

        Err(AdapterError::Unavailable)
    }

    async fn fetch_user_metadata_until_non_unavailable(
        adapter: &HttpRemnawaveAdapter,
        account_id: &str,
    ) -> Result<Option<Value>, AdapterError> {
        for _ in 0..10 {
            match adapter.fetch_user_metadata(account_id).await {
                Err(AdapterError::Unavailable) => {
                    tokio::time::sleep(StdDuration::from_millis(25)).await;
                }
                other => return other,
            }
        }

        Err(AdapterError::Unavailable)
    }

    async fn upsert_user_metadata_until_non_unavailable(
        adapter: &HttpRemnawaveAdapter,
        account_id: &str,
        patch: Value,
    ) -> Result<(), AdapterError> {
        for _ in 0..10 {
            match adapter
                .upsert_user_metadata(account_id, patch.clone())
                .await
            {
                Err(AdapterError::Unavailable) => {
                    tokio::time::sleep(StdDuration::from_millis(25)).await;
                }
                other => return other,
            }
        }

        Err(AdapterError::Unavailable)
    }

    fn build_test_router(state: Arc<TestState>) -> Router {
        Router::new()
            .route("/api/users/resolve", post(resolve_user))
            .route("/api/users/{account_id}", get(get_user))
            .route(
                "/api/users/{account_id}/metadata",
                get(get_metadata).put(put_metadata),
            )
            .with_state(state)
    }

    #[tokio::test]
    async fn http_adapter_round_trips_resolution_and_metadata_calls() {
        let state = Arc::new(TestState {
            account: Mutex::new(Some(sample_snapshot())),
            metadata: Mutex::new(HashMap::from([(
                "acct-1".to_owned(),
                serde_json::json!({ "plan": "pro" }),
            )])),
            expected_token: "rw-token".to_owned(),
            current_payload: Mutex::new(None),
        });
        let (base_url, handle) = spawn_router(build_test_router(state)).await;
        let adapter = HttpRemnawaveAdapter::new(
            HttpRemnawaveAdapterConfig::new(base_url, "rw-token", 500)
                .expect("http adapter config should validate"),
        );

        let resolved = resolve_bootstrap_subject_until_non_unavailable(
            &adapter,
            BootstrapSubject::ShortUuid("sub-1".to_owned()),
        )
        .await
        .expect("bootstrap subject should resolve");
        assert_eq!(resolved.account_id, "acct-1");

        let fetched = fetch_snapshot_until_non_unavailable(&adapter, "acct-1")
            .await
            .expect("account snapshot should fetch");
        assert_eq!(fetched.account_id, "acct-1");

        let metadata = fetch_user_metadata_until_non_unavailable(&adapter, "acct-1")
            .await
            .expect("metadata should fetch");
        assert_eq!(metadata, Some(serde_json::json!({ "plan": "pro" })));

        upsert_user_metadata_until_non_unavailable(
            &adapter,
            "acct-1",
            serde_json::json!({ "verta": { "enabled": true } }),
        )
        .await
        .expect("metadata patch should store");
        let metadata = fetch_user_metadata_until_non_unavailable(&adapter, "acct-1")
            .await
            .expect("metadata should refetch");
        assert_eq!(
            metadata,
            Some(serde_json::json!({ "verta": { "enabled": true } }))
        );

        handle.abort();
        let _ = handle.await;
    }

    #[tokio::test]
    async fn http_adapter_maps_unauthorized_and_not_found_responses() {
        let state = Arc::new(TestState {
            account: Mutex::new(Some(sample_snapshot())),
            metadata: Mutex::new(HashMap::new()),
            expected_token: "rw-token".to_owned(),
            current_payload: Mutex::new(None),
        });
        let (base_url, handle) = spawn_router(build_test_router(state)).await;
        let unauthorized = HttpRemnawaveAdapter::new(
            HttpRemnawaveAdapterConfig::new(base_url.clone(), "wrong-token", 500)
                .expect("http adapter config should validate"),
        );
        let error = fetch_snapshot_until_non_unavailable(&unauthorized, "acct-1")
            .await
            .expect_err("wrong token should fail");
        assert_eq!(error, AdapterError::Unauthorized);

        let adapter = HttpRemnawaveAdapter::new(
            HttpRemnawaveAdapterConfig::new(base_url, "rw-token", 500)
                .expect("http adapter config should validate"),
        );
        let metadata = fetch_user_metadata_until_non_unavailable(&adapter, "missing")
            .await
            .expect("missing metadata should map to none");
        assert_eq!(metadata, None);

        handle.abort();
        let _ = handle.await;
    }

    #[tokio::test]
    async fn http_adapter_normalizes_verified_webhooks_locally() {
        let adapter = HttpRemnawaveAdapter::new(
            HttpRemnawaveAdapterConfig::new("https://panel.example.net", "rw-token", 500)
                .expect("http adapter config should validate"),
        );

        let effect = adapter
            .ingest_verified_webhook(VerifiedWebhookPayload {
                event_id: "evt-1".to_owned(),
                event_type: "subscription.updated".to_owned(),
                account_id: Some("acct-1".to_owned()),
                occurred_at_unix: 1_700_000_000,
                payload: serde_json::json!({ "plan": "pro" }),
            })
            .await
            .expect("webhook normalization should succeed");
        assert_eq!(
            effect,
            AdapterWebhookEffect::ReconcileAccount {
                account_id: "acct-1".to_owned(),
                reason: "subscription.updated".to_owned(),
            }
        );
    }

    #[tokio::test]
    async fn http_adapter_fails_closed_on_upstream_schema_drift() {
        let state = Arc::new(TestState {
            account: Mutex::new(None),
            metadata: Mutex::new(HashMap::new()),
            expected_token: "rw-token".to_owned(),
            current_payload: Mutex::new(None),
        });
        let router = Router::new()
            .route("/api/users/resolve", post(resolve_user_schema_drift))
            .with_state(state);
        let (base_url, handle) = spawn_router(router).await;
        let adapter = HttpRemnawaveAdapter::new(
            HttpRemnawaveAdapterConfig::new(base_url, "rw-token", 500)
                .expect("http adapter config should validate"),
        );

        let error = resolve_bootstrap_subject_until_non_unavailable(
            &adapter,
            BootstrapSubject::ShortUuid("sub-1".to_owned()),
        )
        .await
        .expect_err("schema-drifted upstream account should fail closed");

        assert_eq!(error, AdapterError::SchemaDrift);

        handle.abort();
        let _ = handle.await;
    }

    #[tokio::test]
    async fn http_adapter_accepts_current_remnawave_2_7_x_user_shapes() {
        let state = Arc::new(TestState {
            account: Mutex::new(None),
            metadata: Mutex::new(HashMap::new()),
            expected_token: "rw-token".to_owned(),
            current_payload: Mutex::new(Some(serde_json::json!({
                "response": {
                    "uuid": "167a749c-93e3-4428-ac20-a1f656ec9be5",
                    "id": 1,
                    "shortUuid": "RWax9y-7fMyDprVZ",
                    "username": "Sasha_Beep",
                    "status": "ACTIVE",
                    "hwidDeviceLimit": 3,
                    "subRevokedAt": null
                }
            }))),
        });
        let router = Router::new()
            .route("/api/users/resolve", post(resolve_user_current_shape))
            .route("/api/users/{account_id}", get(get_user_current_shape))
            .with_state(state);
        let (base_url, handle) = spawn_router(router).await;
        let adapter = HttpRemnawaveAdapter::new(
            HttpRemnawaveAdapterConfig::new(base_url, "rw-token", 500)
                .expect("http adapter config should validate"),
        );

        let resolved = resolve_bootstrap_subject_until_non_unavailable(
            &adapter,
            BootstrapSubject::ShortUuid("RWax9y-7fMyDprVZ".to_owned()),
        )
        .await
        .expect("current Remnawave resolve payload should map");

        assert_eq!(resolved.account_id, "167a749c-93e3-4428-ac20-a1f656ec9be5");
        assert_eq!(
            resolved.bootstrap_subjects,
            vec![BootstrapSubject::ShortUuid("RWax9y-7fMyDprVZ".to_owned())]
        );
        assert_eq!(resolved.lifecycle, AccountLifecycle::Active);
        assert_eq!(resolved.verta_access.policy_epoch, 7);
        assert_eq!(resolved.verta_access.device_limit, Some(3));
        assert_eq!(
            resolved.verta_access.allowed_carrier_profiles,
            vec!["carrier-primary".to_owned()]
        );

        handle.abort();
        let _ = handle.await;
    }
}
