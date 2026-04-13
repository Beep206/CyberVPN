use crate::{
    AccountSnapshot, AdapterError, AdapterWebhookEffect, BootstrapSubject, RemnawaveAdapter,
    VerifiedWebhookPayload,
};
use async_trait::async_trait;
use reqwest::StatusCode;
use serde::Serialize;
use serde_json::Value;
use std::time::Duration as StdDuration;

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
}

#[derive(Debug, Serialize)]
struct ResolveBootstrapRequest<'a> {
    bootstrap_subject_kind: &'static str,
    bootstrap_subject: &'a str,
}

#[async_trait]
impl RemnawaveAdapter for HttpRemnawaveAdapter {
    async fn resolve_bootstrap_subject(
        &self,
        subject: &BootstrapSubject,
    ) -> Result<AccountSnapshot, AdapterError> {
        subject.validate()?;
        let request = ResolveBootstrapRequest {
            bootstrap_subject_kind: bootstrap_subject_kind(subject),
            bootstrap_subject: subject.as_str(),
        };
        let response = self
            .request(
                self.client
                    .post(self.config.endpoint("/api/users/resolve")?)
                    .json(&request),
            )
            .send()
            .await
            .map_err(map_request_error)?;
        if !response.status().is_success() {
            return Err(map_status(response.status()));
        }
        self.decode_json(response).await
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
        self.decode_json(response).await
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
    use crate::{AccountLifecycle, NorthstarAccess};
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
    }

    fn sample_snapshot() -> AccountSnapshot {
        AccountSnapshot {
            account_id: "acct-1".to_owned(),
            bootstrap_subjects: vec![BootstrapSubject::ShortUuid("sub-1".to_owned())],
            lifecycle: AccountLifecycle::Active,
            northstar_access: NorthstarAccess {
                northstar_enabled: true,
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
            serde_json::json!({ "northstar": { "enabled": true } }),
        )
        .await
        .expect("metadata patch should store");
        let metadata = fetch_user_metadata_until_non_unavailable(&adapter, "acct-1")
            .await
            .expect("metadata should refetch");
        assert_eq!(
            metadata,
            Some(serde_json::json!({ "northstar": { "enabled": true } }))
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
}
