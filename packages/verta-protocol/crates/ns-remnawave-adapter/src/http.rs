use crate::{
    AccountLifecycle, AccountSnapshot, AdapterError, AdapterWebhookEffect, BootstrapSubject,
    RemnawaveAdapter, VerifiedWebhookPayload, VertaAccess,
};
use async_trait::async_trait;
use reqwest::StatusCode;
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use std::time::Duration as StdDuration;
use time::OffsetDateTime;
use uuid::Uuid;

/// The operator-facing `target-3.4.1` profile remains the stable numeric-ID
/// compatibility contract. Remnawave 3.4.3 retains the numeric-ID API profile
/// while fixing panel authorization and list rendering, so this is a
/// source-version advance rather than a new adapter profile.
pub const REMNAWAVE_TARGET_SOURCE_VERSION: &str = "3.4.3";
pub const REMNAWAVE_LEGACY_SOURCE_VERSION: &str = "2.8.0";

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum RemnawaveApiProfile {
    #[default]
    V3_4_1,
    LegacyV2_8,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HttpRemnawaveAdapterConfig {
    pub base_url: String,
    pub api_token: String,
    pub request_timeout_ms: u64,
    pub api_profile: RemnawaveApiProfile,
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
            api_profile: RemnawaveApiProfile::default(),
        })
    }

    pub fn with_api_profile(mut self, api_profile: RemnawaveApiProfile) -> Self {
        self.api_profile = api_profile;
        self
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

    async fn resolve_target_bootstrap(
        &self,
        subject: &BootstrapSubject,
    ) -> Result<AccountSnapshot, AdapterError> {
        let short_uuid = match subject {
            BootstrapSubject::ShortUuid(value) => value.as_str(),
            BootstrapSubject::BridgeAlias(_) | BootstrapSubject::SignedEnvelope(_) => {
                return Err(AdapterError::InvalidData("bootstrap_subject_kind"));
            }
        };
        let request = TargetResolveUserRequest {
            id: None,
            short_uuid: Some(short_uuid),
            username: None,
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
        let reference = self
            .decode_json::<ResponseEnvelope<TargetResolvedUser>>(response)
            .await?
            .response;
        reference.validate(Some(short_uuid))?;

        let snapshot = self.fetch_target_account_snapshot(reference.id).await?;
        if !snapshot.bootstrap_subjects.iter().any(
            |subject| matches!(subject, BootstrapSubject::ShortUuid(value) if value == &reference.short_uuid),
        ) {
            return Err(AdapterError::SchemaDrift);
        }
        Ok(snapshot)
    }

    async fn resolve_legacy_bootstrap(
        &self,
        subject: &BootstrapSubject,
    ) -> Result<AccountSnapshot, AdapterError> {
        let short_uuid = match subject {
            BootstrapSubject::ShortUuid(value) => value.as_str(),
            BootstrapSubject::BridgeAlias(_) | BootstrapSubject::SignedEnvelope(_) => {
                return Err(AdapterError::InvalidData("bootstrap_subject_kind"));
            }
        };
        let request = LegacyResolveUserRequest {
            uuid: None,
            id: None,
            short_uuid: Some(short_uuid),
            username: None,
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
        let reference = self
            .decode_json::<ResponseEnvelope<LegacyResolvedUser>>(response)
            .await?
            .response;
        reference.validate(Some(short_uuid))?;

        let snapshot = self.fetch_legacy_account_snapshot(reference.uuid).await?;
        if !snapshot.bootstrap_subjects.iter().any(
            |subject| matches!(subject, BootstrapSubject::ShortUuid(value) if value == &reference.short_uuid),
        ) {
            return Err(AdapterError::SchemaDrift);
        }
        Ok(snapshot)
    }

    async fn fetch_target_account_snapshot(
        &self,
        user_id: u64,
    ) -> Result<AccountSnapshot, AdapterError> {
        if user_id == 0 {
            return Err(AdapterError::InvalidData("account_id"));
        }
        let response = self
            .request(
                self.client
                    .get(self.config.endpoint(&format!("/api/users/{user_id}"))?),
            )
            .send()
            .await
            .map_err(map_request_error)?;
        if !response.status().is_success() {
            return Err(map_status(response.status()));
        }
        let payload = self
            .decode_json::<ResponseEnvelope<TargetUserPayload>>(response)
            .await?
            .response;
        if payload.id != user_id {
            return Err(AdapterError::SchemaDrift);
        }
        map_target_user_payload(payload)
    }

    async fn fetch_legacy_account_snapshot(
        &self,
        user_uuid: Uuid,
    ) -> Result<AccountSnapshot, AdapterError> {
        let response = self
            .request(
                self.client
                    .get(self.config.endpoint(&format!("/api/users/{user_uuid}"))?),
            )
            .send()
            .await
            .map_err(map_request_error)?;
        if !response.status().is_success() {
            return Err(map_status(response.status()));
        }
        let payload = self
            .decode_json::<ResponseEnvelope<LegacyUserPayload>>(response)
            .await?
            .response;
        if payload.uuid != user_uuid {
            return Err(AdapterError::SchemaDrift);
        }
        map_legacy_user_payload(payload)
    }

    fn normalized_account_reference(&self, account_id: &str) -> Result<String, AdapterError> {
        match self.config.api_profile {
            RemnawaveApiProfile::V3_4_1 => account_id
                .parse::<u64>()
                .ok()
                .filter(|id| *id > 0)
                .map(|id| id.to_string())
                .ok_or(AdapterError::InvalidData("account_id")),
            RemnawaveApiProfile::LegacyV2_8 => Uuid::parse_str(account_id)
                .map(|uuid| uuid.to_string())
                .map_err(|_| AdapterError::InvalidData("account_id")),
        }
    }
}

#[derive(Debug, Serialize)]
struct TargetResolveUserRequest<'a> {
    #[serde(skip_serializing_if = "Option::is_none")]
    id: Option<u64>,
    #[serde(rename = "shortUuid", skip_serializing_if = "Option::is_none")]
    short_uuid: Option<&'a str>,
    #[serde(skip_serializing_if = "Option::is_none")]
    username: Option<&'a str>,
}

#[derive(Debug, Serialize)]
struct LegacyResolveUserRequest<'a> {
    #[serde(skip_serializing_if = "Option::is_none")]
    uuid: Option<Uuid>,
    #[serde(skip_serializing_if = "Option::is_none")]
    id: Option<u64>,
    #[serde(rename = "shortUuid", skip_serializing_if = "Option::is_none")]
    short_uuid: Option<&'a str>,
    #[serde(skip_serializing_if = "Option::is_none")]
    username: Option<&'a str>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct TargetResolvedUser {
    id: u64,
    username: String,
    #[serde(rename = "shortUuid")]
    short_uuid: String,
}

impl TargetResolvedUser {
    fn validate(&self, expected_short_uuid: Option<&str>) -> Result<(), AdapterError> {
        if self.id == 0
            || self.username.trim().is_empty()
            || self.short_uuid.trim().is_empty()
            || expected_short_uuid.is_some_and(|expected| expected != self.short_uuid)
        {
            return Err(AdapterError::SchemaDrift);
        }
        Ok(())
    }
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct LegacyResolvedUser {
    uuid: Uuid,
    id: u64,
    username: String,
    #[serde(rename = "shortUuid")]
    short_uuid: String,
}

impl LegacyResolvedUser {
    fn validate(&self, expected_short_uuid: Option<&str>) -> Result<(), AdapterError> {
        if self.id == 0
            || self.username.trim().is_empty()
            || self.short_uuid.trim().is_empty()
            || expected_short_uuid.is_some_and(|expected| expected != self.short_uuid)
        {
            return Err(AdapterError::SchemaDrift);
        }
        Ok(())
    }
}

#[derive(Debug, Deserialize)]
struct TargetUserPayload {
    id: u64,
    #[serde(rename = "shortUuid")]
    short_uuid: String,
    username: String,
    status: String,
    #[serde(rename = "subRevokedAt", default)]
    sub_revoked_at: Option<String>,
    #[serde(rename = "hwidDeviceLimit", default)]
    hwid_device_limit: Option<u32>,
}

#[derive(Debug, Deserialize)]
struct LegacyUserPayload {
    uuid: Uuid,
    id: u64,
    #[serde(rename = "shortUuid")]
    short_uuid: String,
    username: String,
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

#[derive(Debug, Deserialize)]
struct UserMetadataPayload {
    metadata: Map<String, Value>,
}

#[derive(Debug, Serialize)]
struct UpsertUserMetadataRequest<'a> {
    metadata: &'a Map<String, Value>,
}

#[async_trait]
impl RemnawaveAdapter for HttpRemnawaveAdapter {
    async fn resolve_bootstrap_subject(
        &self,
        subject: &BootstrapSubject,
    ) -> Result<AccountSnapshot, AdapterError> {
        subject.validate()?;
        match self.config.api_profile {
            RemnawaveApiProfile::V3_4_1 => self.resolve_target_bootstrap(subject).await,
            RemnawaveApiProfile::LegacyV2_8 => self.resolve_legacy_bootstrap(subject).await,
        }
    }

    async fn fetch_account_snapshot(
        &self,
        account_id: &str,
    ) -> Result<AccountSnapshot, AdapterError> {
        match self.config.api_profile {
            RemnawaveApiProfile::V3_4_1 => {
                let user_id = account_id
                    .parse::<u64>()
                    .ok()
                    .filter(|id| *id > 0)
                    .ok_or(AdapterError::InvalidData("account_id"))?;
                self.fetch_target_account_snapshot(user_id).await
            }
            RemnawaveApiProfile::LegacyV2_8 => {
                let user_uuid = Uuid::parse_str(account_id)
                    .map_err(|_| AdapterError::InvalidData("account_id"))?;
                self.fetch_legacy_account_snapshot(user_uuid).await
            }
        }
    }

    async fn fetch_user_metadata(&self, account_id: &str) -> Result<Option<Value>, AdapterError> {
        let account_reference = self.normalized_account_reference(account_id)?;
        let response = self
            .request(
                self.client.get(
                    self.config
                        .endpoint(&format!("/api/metadata/user/{account_reference}"))?,
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
        let payload = self
            .decode_json::<ResponseEnvelope<UserMetadataPayload>>(response)
            .await?
            .response;
        Ok(Some(Value::Object(payload.metadata)))
    }

    async fn upsert_user_metadata(
        &self,
        account_id: &str,
        patch: Value,
    ) -> Result<(), AdapterError> {
        let account_reference = self.normalized_account_reference(account_id)?;
        let metadata = patch
            .as_object()
            .ok_or(AdapterError::InvalidData("metadata"))?;
        let request = UpsertUserMetadataRequest { metadata };
        let response = self
            .request(
                self.client
                    .put(
                        self.config
                            .endpoint(&format!("/api/metadata/user/{account_reference}"))?,
                    )
                    .json(&request),
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
        mut payload: VerifiedWebhookPayload,
    ) -> Result<AdapterWebhookEffect, AdapterError> {
        if webhook_event_has_account_scope(&payload.event_type) {
            payload.account_id = payload
                .account_id
                .as_deref()
                .map(|account_id| self.normalized_account_reference(account_id))
                .transpose()?;
        }
        Ok(map_verified_webhook(payload))
    }
}

fn map_target_user_payload(payload: TargetUserPayload) -> Result<AccountSnapshot, AdapterError> {
    if payload.id == 0 || payload.short_uuid.trim().is_empty() || payload.username.trim().is_empty()
    {
        return Err(AdapterError::SchemaDrift);
    }
    let lifecycle = parse_current_lifecycle(&payload.status, payload.sub_revoked_at.as_deref())?;

    Ok(AccountSnapshot {
        account_id: payload.id.to_string(),
        bootstrap_subjects: vec![BootstrapSubject::ShortUuid(payload.short_uuid)],
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
        source_version: Some(REMNAWAVE_TARGET_SOURCE_VERSION.to_owned()),
    })
}

fn map_legacy_user_payload(payload: LegacyUserPayload) -> Result<AccountSnapshot, AdapterError> {
    if payload.id == 0 || payload.short_uuid.trim().is_empty() || payload.username.trim().is_empty()
    {
        return Err(AdapterError::SchemaDrift);
    }
    let lifecycle = parse_current_lifecycle(&payload.status, payload.sub_revoked_at.as_deref())?;

    Ok(AccountSnapshot {
        account_id: payload.uuid.to_string(),
        bootstrap_subjects: vec![BootstrapSubject::ShortUuid(payload.short_uuid)],
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
        source_version: Some(REMNAWAVE_LEGACY_SOURCE_VERSION.to_owned()),
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
    if webhook_event_has_account_scope(&payload.event_type) {
        return payload
            .account_id
            .map(|account_id| AdapterWebhookEffect::ReconcileAccount {
                account_id,
                reason: payload.event_type,
            })
            .unwrap_or(AdapterWebhookEffect::ReconcileAll {
                reason: "missing_account_scope".to_owned(),
            });
    }

    match payload.event_type.as_str() {
        "service.subpage_config_changed" => AdapterWebhookEffect::ReconcileAll {
            reason: payload.event_type,
        },
        _ => AdapterWebhookEffect::Noop,
    }
}

fn webhook_event_has_account_scope(event_type: &str) -> bool {
    matches!(
        event_type,
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
            | "subscription.updated"
    )
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
            account_id: "42".to_owned(),
            bootstrap_subjects: vec![BootstrapSubject::ShortUuid("RWax9y-7fMyDprVZ".to_owned())],
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
            source_version: Some(REMNAWAVE_TARGET_SOURCE_VERSION.to_owned()),
        }
    }

    #[test]
    fn target_source_version_advances_without_replacing_the_numeric_profile() {
        assert_eq!(REMNAWAVE_TARGET_SOURCE_VERSION, "3.4.3");
        assert_eq!(RemnawaveApiProfile::default(), RemnawaveApiProfile::V3_4_1);
    }

    fn repo_root() -> PathBuf {
        let mut root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        root.pop();
        root.pop();
        root
    }

    fn load_schema_drift_fixture() -> String {
        fs::read_to_string(
            repo_root().join(
                "fixtures/remnawave/account/BG-UPSTREAM-RESOLVE-UUID-SCHEMADRIFT-3_4_1-015.json",
            ),
        )
        .expect("schema-drift fixture should be readable")
    }

    fn load_json_fixture(name: &str) -> Value {
        let bytes = fs::read(repo_root().join("fixtures/remnawave/account").join(name))
            .expect("Remnawave account fixture should be readable");
        serde_json::from_slice(&bytes).expect("Remnawave account fixture should be valid JSON")
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
        Json(request): Json<Value>,
    ) -> Result<Json<Value>, StatusCode> {
        if !authorized(&headers, &state.expected_token) {
            return Err(StatusCode::UNAUTHORIZED);
        }
        state
            .account
            .lock()
            .expect("test state poisoned")
            .clone()
            .ok_or(StatusCode::NOT_FOUND)?;
        if request != serde_json::json!({"shortUuid": "RWax9y-7fMyDprVZ"}) {
            return Err(StatusCode::BAD_REQUEST);
        }
        Ok(Json(load_json_fixture(
            "BG-UPSTREAM-RESOLVE-3_4_1-011.json",
        )))
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
    ) -> Result<Json<Value>, StatusCode> {
        if !authorized(&headers, &state.expected_token) {
            return Err(StatusCode::UNAUTHORIZED);
        }
        let snapshot = state
            .account
            .lock()
            .expect("test state poisoned")
            .clone()
            .ok_or(StatusCode::NOT_FOUND)?;
        if snapshot.account_id != account_id || account_id != "42" {
            return Err(StatusCode::NOT_FOUND);
        }
        Ok(Json(load_json_fixture("BG-UPSTREAM-USER-3_4_1-012.json")))
    }

    async fn get_user_schema_drift(
        State(state): State<Arc<TestState>>,
        headers: HeaderMap,
        Path(account_id): Path<String>,
    ) -> Result<Json<Value>, StatusCode> {
        if !authorized(&headers, &state.expected_token) {
            return Err(StatusCode::UNAUTHORIZED);
        }
        if account_id != "42" {
            return Err(StatusCode::NOT_FOUND);
        }
        Ok(Json(load_json_fixture(
            "BG-UPSTREAM-USER-ID-SCHEMADRIFT-3_4_1-014.json",
        )))
    }

    async fn get_user_with_mismatched_id(
        State(state): State<Arc<TestState>>,
        headers: HeaderMap,
        Path(account_id): Path<String>,
    ) -> Result<Json<Value>, StatusCode> {
        if !authorized(&headers, &state.expected_token) {
            return Err(StatusCode::UNAUTHORIZED);
        }
        if account_id != "42" {
            return Err(StatusCode::NOT_FOUND);
        }
        let mut fixture = load_json_fixture("BG-UPSTREAM-USER-3_4_1-012.json");
        fixture["response"]["id"] = serde_json::json!(43);
        Ok(Json(fixture))
    }

    async fn get_malformed_metadata(
        State(state): State<Arc<TestState>>,
        headers: HeaderMap,
        Path(account_id): Path<String>,
    ) -> Result<Json<Value>, StatusCode> {
        if !authorized(&headers, &state.expected_token) {
            return Err(StatusCode::UNAUTHORIZED);
        }
        if account_id != "42" {
            return Err(StatusCode::NOT_FOUND);
        }
        Ok(Json(serde_json::json!({"response": {"metadata": []}})))
    }

    async fn resolve_user_current_shape(
        State(state): State<Arc<TestState>>,
        headers: HeaderMap,
        Json(request): Json<Value>,
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
        if request != serde_json::json!({"shortUuid": "RWax9y-7fMyDprVZ"}) {
            return Err(StatusCode::BAD_REQUEST);
        }
        let response = payload
            .get("response")
            .ok_or(StatusCode::INTERNAL_SERVER_ERROR)?;
        Ok(Json(serde_json::json!({
            "response": {
                "uuid": response.get("uuid"),
                "id": response.get("id"),
                "username": response.get("username"),
                "shortUuid": response.get("shortUuid")
            }
        })))
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
            .map(|metadata| Json(serde_json::json!({"response": {"metadata": metadata}})))
            .ok_or(StatusCode::NOT_FOUND)
    }

    async fn put_metadata(
        State(state): State<Arc<TestState>>,
        headers: HeaderMap,
        Path(account_id): Path<String>,
        Json(body): Json<Value>,
    ) -> Result<StatusCode, StatusCode> {
        if !authorized(&headers, &state.expected_token) {
            return Err(StatusCode::UNAUTHORIZED);
        }
        let body = body.as_object().ok_or(StatusCode::BAD_REQUEST)?;
        if body.len() != 1 {
            return Err(StatusCode::BAD_REQUEST);
        }
        let patch = body
            .get("metadata")
            .filter(|value| value.is_object())
            .cloned()
            .ok_or(StatusCode::BAD_REQUEST)?;
        state
            .metadata
            .lock()
            .expect("test state poisoned")
            .insert(account_id, patch);
        Ok(StatusCode::ACCEPTED)
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
                "/api/metadata/user/{account_id}",
                get(get_metadata).put(put_metadata),
            )
            .with_state(state)
    }

    #[tokio::test]
    async fn http_adapter_round_trips_resolution_and_metadata_calls() {
        let metadata_fixture = load_json_fixture("BG-UPSTREAM-METADATA-3_4_1-013.json");
        let metadata = metadata_fixture["response"]["metadata"].clone();
        let state = Arc::new(TestState {
            account: Mutex::new(Some(sample_snapshot())),
            metadata: Mutex::new(HashMap::from([("42".to_owned(), metadata.clone())])),
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
            BootstrapSubject::ShortUuid("RWax9y-7fMyDprVZ".to_owned()),
        )
        .await
        .expect("bootstrap subject should resolve");
        assert_eq!(resolved.account_id, "42");
        assert_eq!(
            resolved.source_version.as_deref(),
            Some(REMNAWAVE_TARGET_SOURCE_VERSION)
        );

        let fetched = fetch_snapshot_until_non_unavailable(&adapter, "42")
            .await
            .expect("account snapshot should fetch");
        assert_eq!(fetched.account_id, "42");

        let metadata = fetch_user_metadata_until_non_unavailable(&adapter, "42")
            .await
            .expect("metadata should fetch");
        assert_eq!(
            metadata,
            Some(metadata_fixture["response"]["metadata"].clone())
        );

        upsert_user_metadata_until_non_unavailable(
            &adapter,
            "42",
            serde_json::json!({ "verta": { "enabled": true } }),
        )
        .await
        .expect("metadata patch should store");
        let metadata = fetch_user_metadata_until_non_unavailable(&adapter, "42")
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
        let error = fetch_snapshot_until_non_unavailable(&unauthorized, "42")
            .await
            .expect_err("wrong token should fail");
        assert_eq!(error, AdapterError::Unauthorized);

        let adapter = HttpRemnawaveAdapter::new(
            HttpRemnawaveAdapterConfig::new(base_url, "rw-token", 500)
                .expect("http adapter config should validate"),
        );
        let metadata = fetch_user_metadata_until_non_unavailable(&adapter, "404")
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
                account_id: Some("42".to_owned()),
                occurred_at_unix: 1_700_000_000,
                payload: serde_json::json!({ "plan": "pro" }),
            })
            .await
            .expect("webhook normalization should succeed");
        assert_eq!(
            effect,
            AdapterWebhookEffect::ReconcileAccount {
                account_id: "42".to_owned(),
                reason: "subscription.updated".to_owned(),
            }
        );

        let error = adapter
            .ingest_verified_webhook(VerifiedWebhookPayload {
                event_id: "evt-uuid".to_owned(),
                event_type: "user.modified".to_owned(),
                account_id: Some("167a749c-93e3-4428-ac20-a1f656ec9be5".to_owned()),
                occurred_at_unix: 1_700_000_001,
                payload: serde_json::json!({}),
            })
            .await
            .expect_err("target profile must reject UUID-scoped webhook reconciliation");
        assert_eq!(error, AdapterError::InvalidData("account_id"));
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
            BootstrapSubject::ShortUuid("RWax9y-7fMyDprVZ".to_owned()),
        )
        .await
        .expect_err("schema-drifted upstream account should fail closed");

        assert_eq!(error, AdapterError::SchemaDrift);

        handle.abort();
        let _ = handle.await;
    }

    #[tokio::test]
    async fn http_adapter_fails_closed_on_target_user_id_schema_drift() {
        let state = Arc::new(TestState {
            account: Mutex::new(Some(sample_snapshot())),
            metadata: Mutex::new(HashMap::new()),
            expected_token: "rw-token".to_owned(),
            current_payload: Mutex::new(None),
        });
        let router = Router::new()
            .route("/api/users/resolve", post(resolve_user))
            .route("/api/users/{account_id}", get(get_user_schema_drift))
            .with_state(state);
        let (base_url, handle) = spawn_router(router).await;
        let adapter = HttpRemnawaveAdapter::new(
            HttpRemnawaveAdapterConfig::new(base_url, "rw-token", 500)
                .expect("http adapter config should validate"),
        );

        let error = resolve_bootstrap_subject_until_non_unavailable(
            &adapter,
            BootstrapSubject::ShortUuid("RWax9y-7fMyDprVZ".to_owned()),
        )
        .await
        .expect_err("string target user id should fail closed");

        assert_eq!(error, AdapterError::SchemaDrift);
        handle.abort();
        let _ = handle.await;
    }

    #[tokio::test]
    async fn http_adapter_fails_closed_when_target_route_returns_another_user_id() {
        let state = Arc::new(TestState {
            account: Mutex::new(Some(sample_snapshot())),
            metadata: Mutex::new(HashMap::new()),
            expected_token: "rw-token".to_owned(),
            current_payload: Mutex::new(None),
        });
        let router = Router::new()
            .route("/api/users/resolve", post(resolve_user))
            .route("/api/users/{account_id}", get(get_user_with_mismatched_id))
            .with_state(state);
        let (base_url, handle) = spawn_router(router).await;
        let adapter = HttpRemnawaveAdapter::new(
            HttpRemnawaveAdapterConfig::new(base_url, "rw-token", 500)
                .expect("http adapter config should validate"),
        );

        let error = resolve_bootstrap_subject_until_non_unavailable(
            &adapter,
            BootstrapSubject::ShortUuid("RWax9y-7fMyDprVZ".to_owned()),
        )
        .await
        .expect_err("target route must not return a different numeric user ID");

        assert_eq!(error, AdapterError::SchemaDrift);
        handle.abort();
        let _ = handle.await;
    }

    #[tokio::test]
    async fn http_adapter_rejects_non_numeric_target_ids_and_non_object_metadata() {
        let adapter = HttpRemnawaveAdapter::new(
            HttpRemnawaveAdapterConfig::new("https://panel.example.net", "rw-token", 500)
                .expect("http adapter config should validate"),
        );
        assert_eq!(
            adapter
                .fetch_account_snapshot("167a749c-93e3-4428-ac20-a1f656ec9be5")
                .await,
            Err(AdapterError::InvalidData("account_id"))
        );
        assert_eq!(
            adapter
                .fetch_user_metadata("167a749c-93e3-4428-ac20-a1f656ec9be5")
                .await,
            Err(AdapterError::InvalidData("account_id"))
        );
        assert_eq!(
            adapter
                .resolve_bootstrap_subject(&BootstrapSubject::BridgeAlias("alias-1".to_owned()))
                .await,
            Err(AdapterError::InvalidData("bootstrap_subject_kind"))
        );
        assert_eq!(
            adapter
                .upsert_user_metadata("42", serde_json::json!(["not-an-object"]))
                .await,
            Err(AdapterError::InvalidData("metadata"))
        );

        let state = Arc::new(TestState {
            account: Mutex::new(Some(sample_snapshot())),
            metadata: Mutex::new(HashMap::new()),
            expected_token: "rw-token".to_owned(),
            current_payload: Mutex::new(None),
        });
        let router = Router::new()
            .route(
                "/api/metadata/user/{account_id}",
                get(get_malformed_metadata),
            )
            .with_state(state);
        let (base_url, handle) = spawn_router(router).await;
        let adapter = HttpRemnawaveAdapter::new(
            HttpRemnawaveAdapterConfig::new(base_url, "rw-token", 500)
                .expect("http adapter config should validate"),
        );
        assert_eq!(
            adapter.fetch_user_metadata("42").await,
            Err(AdapterError::SchemaDrift)
        );
        handle.abort();
        let _ = handle.await;
    }

    #[tokio::test]
    async fn http_adapter_legacy_2_8_profile_is_explicit_and_uuid_scoped() {
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
                .expect("http adapter config should validate")
                .with_api_profile(RemnawaveApiProfile::LegacyV2_8),
        );

        let resolved = resolve_bootstrap_subject_until_non_unavailable(
            &adapter,
            BootstrapSubject::ShortUuid("RWax9y-7fMyDprVZ".to_owned()),
        )
        .await
        .expect("explicit legacy Remnawave resolve payload should map");

        assert_eq!(resolved.account_id, "167a749c-93e3-4428-ac20-a1f656ec9be5");
        assert_eq!(
            resolved.bootstrap_subjects,
            vec![BootstrapSubject::ShortUuid("RWax9y-7fMyDprVZ".to_owned())]
        );
        assert_eq!(resolved.lifecycle, AccountLifecycle::Active);
        assert_eq!(
            resolved.source_version.as_deref(),
            Some(REMNAWAVE_LEGACY_SOURCE_VERSION)
        );
        assert_eq!(resolved.verta_access.policy_epoch, 7);
        assert_eq!(resolved.verta_access.device_limit, Some(3));
        assert_eq!(
            resolved.verta_access.allowed_carrier_profiles,
            vec!["carrier-primary".to_owned()]
        );

        let effect = adapter
            .ingest_verified_webhook(VerifiedWebhookPayload {
                event_id: "evt-legacy".to_owned(),
                event_type: "user.modified".to_owned(),
                account_id: Some("167a749c-93e3-4428-ac20-a1f656ec9be5".to_owned()),
                occurred_at_unix: 1_700_000_000,
                payload: serde_json::json!({}),
            })
            .await
            .expect("explicit legacy profile should retain UUID webhook scope");
        assert_eq!(
            effect,
            AdapterWebhookEffect::ReconcileAccount {
                account_id: "167a749c-93e3-4428-ac20-a1f656ec9be5".to_owned(),
                reason: "user.modified".to_owned(),
            }
        );

        handle.abort();
        let _ = handle.await;
    }
}
