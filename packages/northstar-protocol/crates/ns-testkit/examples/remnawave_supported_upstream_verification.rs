use anyhow::Context;
use axum::Router;
use ed25519_dalek::pkcs8::EncodePrivateKey;
use ns_auth::SessionTokenSigner;
use ns_bridge_api::{
    BridgeHttpBudgets, BridgeHttpServiceState, DeviceRegisterResponse, TokenExchangeRequest,
    TokenExchangeResponse, build_bridge_router,
};
use ns_bridge_domain::{BridgeDomain, BridgeManifestContext, BridgeManifestTemplate};
use ns_manifest::{ManifestDocument, ManifestSigner};
use ns_remnawave_adapter::{
    AccountSnapshot, AdapterError, BootstrapSubject, HttpRemnawaveAdapter,
    HttpRemnawaveAdapterConfig, RemnawaveAdapter, VerifiedWebhookPayload, WebhookAuthenticator,
    WebhookVerificationConfig, WebhookVerificationError,
};
use ns_storage::{SharedBridgeStore, SqliteBridgeStore};
use ns_testkit::{
    FIXTURE_MANIFEST_KEY_ID, FIXTURE_TOKEN_KEY_ID, fixed_test_now, fixture_manifest_signing_key,
    fixture_token_jwks, fixture_token_signing_key, repo_root, sample_manifest_document,
    summarize_rollout_gate_state,
};
use serde::Serialize;
use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::io::ErrorKind;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use time::{Duration, OffsetDateTime};
use tokio::net::TcpListener;

const SUPPORTED_UPSTREAM_VERIFICATION_SCHEMA: &str = "supported_upstream_operator_verdict";
const SUPPORTED_UPSTREAM_VERIFICATION_SCHEMA_VERSION: u8 = 1;
const SUPPORTED_UPSTREAM_VERDICT_FAMILY: &str = "supported_upstream_verification";
const SUPPORTED_UPSTREAM_DECISION_SCOPE: &str = "supported_upstream";
const SUPPORTED_UPSTREAM_DECISION_LABEL: &str = "remnawave_supported_upstream_verification";
const SUPPORTED_UPSTREAM_PROFILE: &str = "supported_upstream_verification";
const SUPPORTED_UPSTREAM_SUMMARY_VERSION: u8 = 1;

const SUPPORTED_UPSTREAM_VERSION_FLOOR: SimpleVersion = SimpleVersion::new(2, 7, 0);
const SUPPORTED_UPSTREAM_VERSION_PREFERRED: SimpleVersion = SimpleVersion::new(2, 7, 4);

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum OutputFormat {
    Text,
    Json,
}

#[derive(Debug, Default)]
struct SupportedUpstreamArgs {
    format: Option<OutputFormat>,
    summary_path: Option<PathBuf>,
    base_url: Option<String>,
    api_token: Option<String>,
    bootstrap_subject: Option<String>,
    webhook_signature: Option<String>,
    source_version_override: Option<String>,
    request_timeout_ms: Option<u64>,
    max_snapshot_age_seconds: Option<i64>,
    expected_account_id: Option<String>,
    webhook_event_type: Option<String>,
}

#[derive(Debug)]
struct ResolvedConfig {
    format: OutputFormat,
    summary_path: PathBuf,
    base_url: Option<String>,
    api_token: Option<String>,
    bootstrap_subject: Option<String>,
    webhook_signature: Option<String>,
    source_version_override: Option<String>,
    request_timeout_ms: u64,
    max_snapshot_age_seconds: i64,
    expected_account_id: Option<String>,
    webhook_event_type: String,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd)]
struct SimpleVersion {
    major: u64,
    minor: u64,
    patch: u64,
}

impl SimpleVersion {
    const fn new(major: u64, minor: u64, patch: u64) -> Self {
        Self {
            major,
            minor,
            patch,
        }
    }

    fn parse(value: &str) -> Option<Self> {
        let trimmed = value.trim().trim_start_matches('v');
        let mut parts = trimmed.split(['.', '-', '+']);
        let major = parse_numeric_segment(parts.next()?)?;
        let minor = parse_numeric_segment(parts.next()?)?;
        let patch = parse_numeric_segment(parts.next().unwrap_or("0"))?;
        Some(Self::new(major, minor, patch))
    }

    fn render(self) -> String {
        format!("{}.{}.{}", self.major, self.minor, self.patch)
    }
}

#[derive(Debug, Default)]
struct SummaryState {
    missing_required_inputs: Vec<String>,
    blocking_reasons: Vec<String>,
    blocking_reason_key_counts: BTreeMap<String, usize>,
    blocking_reason_family_counts: BTreeMap<String, usize>,
    summary_contract_invalid_count: usize,
    required_input_unready_count: usize,
    degradation_hold_count: usize,
    supported_upstream_environment_present: bool,
    upstream_source_version: Option<String>,
    supported_upstream_version_passed: Option<bool>,
    supported_upstream_version_preferred_passed: Option<bool>,
    bootstrap_subject_resolved: Option<bool>,
    account_snapshot_fetched: Option<bool>,
    account_snapshot_fresh: Option<bool>,
    account_id_expected_match: Option<bool>,
    bridge_manifest_bootstrap_passed: Option<bool>,
    bridge_device_register_passed: Option<bool>,
    bridge_token_exchange_passed: Option<bool>,
    bridge_manifest_refresh_passed: Option<bool>,
    webhook_signature_negative_rejection_passed: Option<bool>,
    webhook_positive_delivery_passed: Option<bool>,
    response_shape_contract_passed: Option<bool>,
    supported_upstream_compatibility_passed: Option<bool>,
    partially_degraded_upstream: bool,
    unsupported_upstream_version_detected: bool,
    upstream_auth_failure_detected: bool,
    upstream_timeout_detected: bool,
    upstream_unavailable_detected: bool,
    upstream_stale_detected: bool,
    upstream_drift_detected: bool,
    webhook_signature_failure_detected: bool,
    incompatible_contract_detected: bool,
    successful_stage_count: usize,
}

#[derive(Debug, Serialize)]
struct SupportedUpstreamVerificationSummary {
    summary_version: u8,
    verification_schema: &'static str,
    verification_schema_version: u8,
    verdict_family: &'static str,
    decision_scope: &'static str,
    decision_label: &'static str,
    profile: &'static str,
    verdict: &'static str,
    evidence_state: &'static str,
    gate_state: &'static str,
    gate_state_reason: &'static str,
    gate_state_reason_family: &'static str,
    required_inputs: Vec<String>,
    considered_inputs: Vec<String>,
    missing_required_inputs: Vec<String>,
    missing_required_input_count: usize,
    required_input_count: usize,
    required_input_missing_count: usize,
    required_input_failed_count: usize,
    required_input_unready_count: usize,
    required_input_present_count: usize,
    required_input_passed_count: usize,
    all_required_inputs_present: bool,
    all_required_inputs_passed: bool,
    blocking_reason_count: usize,
    blocking_reason_key_count: usize,
    blocking_reason_family_count: usize,
    blocking_reason_key_counts: BTreeMap<String, usize>,
    blocking_reason_family_counts: BTreeMap<String, usize>,
    supported_upstream_environment_present: bool,
    supported_upstream_base_url: Option<String>,
    supported_upstream_version_floor: String,
    supported_upstream_version_preferred: String,
    upstream_source_version: Option<String>,
    upstream_state: &'static str,
    supported_upstream_version_passed: Option<bool>,
    supported_upstream_version_preferred_passed: Option<bool>,
    bootstrap_subject_resolved: Option<bool>,
    account_snapshot_fetched: Option<bool>,
    account_snapshot_fresh: Option<bool>,
    account_id_expected_match: Option<bool>,
    bridge_manifest_bootstrap_passed: Option<bool>,
    bridge_device_register_passed: Option<bool>,
    bridge_token_exchange_passed: Option<bool>,
    bridge_manifest_refresh_passed: Option<bool>,
    webhook_signature_negative_rejection_passed: Option<bool>,
    webhook_positive_delivery_passed: Option<bool>,
    response_shape_contract_passed: Option<bool>,
    supported_upstream_compatibility_passed: Option<bool>,
    partially_degraded_upstream: bool,
    unsupported_upstream_version_detected: bool,
    upstream_auth_failure_detected: bool,
    upstream_timeout_detected: bool,
    upstream_unavailable_detected: bool,
    upstream_stale_detected: bool,
    upstream_drift_detected: bool,
    webhook_signature_failure_detected: bool,
    incompatible_contract_detected: bool,
    blocking_reasons: Vec<String>,
    blocking_reason_keys: Vec<String>,
    blocking_reason_families: Vec<String>,
}

#[derive(Debug)]
struct BridgeFlowEvidence {
    manifest_bootstrap_passed: bool,
    device_register_passed: bool,
    token_exchange_passed: bool,
    manifest_refresh_passed: bool,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum StageFailureKind {
    AuthFailure,
    Timeout,
    Unavailable,
    Drift,
    IncompatibleContract,
}

#[derive(Debug)]
struct StageFailure {
    stage: &'static str,
    kind: StageFailureKind,
    detail: String,
}

#[derive(Clone)]
struct FixedWebhookSignatureAuthenticator {
    expected_signature: String,
}

impl WebhookAuthenticator for FixedWebhookSignatureAuthenticator {
    fn verify(
        &self,
        _timestamp_header: &str,
        signature_header: &str,
        _body: &[u8],
    ) -> Result<(), WebhookVerificationError> {
        if signature_header == self.expected_signature {
            Ok(())
        } else {
            Err(WebhookVerificationError::InvalidSignature)
        }
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = parse_args(env::args().skip(1))?;
    let config = resolve_config(args);
    let summary = build_supported_upstream_summary(&config).await;

    if let Some(parent) = config.summary_path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(&config.summary_path, serde_json::to_vec_pretty(&summary)?)?;

    match config.format {
        OutputFormat::Text => print_text_summary(&summary, &config.summary_path),
        OutputFormat::Json => println!("{}", serde_json::to_string_pretty(&summary)?),
    }

    if summary.verdict != "ready" {
        return Err("supported upstream verification did not pass".into());
    }

    Ok(())
}

async fn build_supported_upstream_summary(
    config: &ResolvedConfig,
) -> SupportedUpstreamVerificationSummary {
    let required_inputs = supported_upstream_required_inputs();
    let considered_inputs = required_inputs.clone();
    let mut state = SummaryState::default();

    collect_missing_required_inputs(config, &mut state);
    if state.missing_required_inputs.is_empty() {
        state.supported_upstream_environment_present = true;
        execute_supported_upstream_checks(config, &mut state).await;
    }

    finalize_summary(config, required_inputs, considered_inputs, state)
}

async fn execute_supported_upstream_checks(config: &ResolvedConfig, state: &mut SummaryState) {
    let base_url = config.base_url.as_deref().expect("checked required input");
    let api_token = config.api_token.as_deref().expect("checked required input");
    let bootstrap_subject = config
        .bootstrap_subject
        .as_deref()
        .expect("checked required input");
    let webhook_signature = config
        .webhook_signature
        .as_deref()
        .expect("checked required input");

    let adapter_config =
        match HttpRemnawaveAdapterConfig::new(base_url, api_token, config.request_timeout_ms) {
            Ok(value) => value,
            Err(error) => {
                state.response_shape_contract_passed = Some(false);
                state.supported_upstream_compatibility_passed = Some(false);
                state.incompatible_contract_detected = true;
                mark_contract_invalid(
                    state,
                    &format!("supported_upstream_adapter_config_invalid:{error}"),
                    "supported_upstream_adapter_config_invalid",
                    "supported_upstream_contract",
                );
                return;
            }
        };
    let adapter = HttpRemnawaveAdapter::new(adapter_config);
    let subject = BootstrapSubject::ShortUuid(bootstrap_subject.to_owned());

    let resolved = match adapter.resolve_bootstrap_subject(&subject).await {
        Ok(snapshot) => {
            let snapshot =
                apply_source_version_override(snapshot, config.source_version_override.as_deref());
            state.bootstrap_subject_resolved = Some(true);
            state.response_shape_contract_passed = Some(true);
            note_stage_success(state);
            snapshot
        }
        Err(error) => {
            state.bootstrap_subject_resolved = Some(false);
            state.response_shape_contract_passed = matches!(error, AdapterError::SchemaDrift)
                .then_some(false)
                .or(Some(true));
            apply_adapter_error(state, "bootstrap_resolution", error);
            return;
        }
    };

    state.upstream_source_version = resolved.source_version.clone();
    match validate_supported_version(&resolved) {
        Ok(preferred) => {
            state.supported_upstream_version_passed = Some(true);
            state.supported_upstream_version_preferred_passed = Some(preferred);
            note_stage_success(state);
        }
        Err(reason) => {
            state.supported_upstream_version_passed = Some(false);
            state.supported_upstream_version_preferred_passed = Some(false);
            state.unsupported_upstream_version_detected = true;
            state.incompatible_contract_detected = true;
            mark_contract_invalid(
                state,
                &reason,
                "unsupported_upstream_version",
                "supported_upstream_contract",
            );
        }
    }

    match validate_expected_account_id(&resolved, config.expected_account_id.as_deref()) {
        Ok(true) => {
            state.account_id_expected_match = Some(true);
            note_stage_success(state);
        }
        Ok(false) => {
            state.account_id_expected_match = Some(false);
            state.incompatible_contract_detected = true;
            mark_contract_invalid(
                state,
                "supported_upstream_account_id_mismatch",
                "supported_upstream_account_id_mismatch",
                "supported_upstream_contract",
            );
        }
        Err(reason) => {
            state.account_id_expected_match = Some(false);
            state.incompatible_contract_detected = true;
            mark_contract_invalid(
                state,
                &reason,
                "supported_upstream_account_id_mismatch",
                "supported_upstream_contract",
            );
        }
    }

    if snapshot_is_fresh(&resolved, config.max_snapshot_age_seconds) {
        state.account_snapshot_fresh = Some(true);
        note_stage_success(state);
    } else {
        state.account_snapshot_fresh = Some(false);
        state.upstream_stale_detected = true;
        mark_degradation(
            state,
            "supported_upstream_snapshot_stale",
            "supported_upstream_snapshot_stale",
            "supported_upstream_freshness",
        );
    }

    match adapter.fetch_account_snapshot(&resolved.account_id).await {
        Ok(snapshot) => {
            state.account_snapshot_fetched = Some(true);
            note_stage_success(state);
            if snapshot.account_id != resolved.account_id {
                state.incompatible_contract_detected = true;
                mark_contract_invalid(
                    state,
                    "supported_upstream_fetch_account_id_mismatch",
                    "supported_upstream_fetch_account_id_mismatch",
                    "supported_upstream_contract",
                );
            }
        }
        Err(error) => {
            state.account_snapshot_fetched = Some(false);
            apply_adapter_error(state, "account_fetch", error);
        }
    }

    match run_bridge_backed_checks(
        &adapter,
        bootstrap_subject,
        webhook_signature,
        &resolved,
        config,
    )
    .await
    {
        Ok(flow) => {
            state.bridge_manifest_bootstrap_passed = Some(flow.manifest_bootstrap_passed);
            state.bridge_device_register_passed = Some(flow.device_register_passed);
            state.bridge_token_exchange_passed = Some(flow.token_exchange_passed);
            state.bridge_manifest_refresh_passed = Some(flow.manifest_refresh_passed);
            note_stage_success(state);
            note_stage_success(state);
            note_stage_success(state);
            note_stage_success(state);
        }
        Err(failure) => apply_stage_failure(state, failure),
    }

    match run_webhook_checks(&adapter, webhook_signature, &resolved, config).await {
        Ok((negative_rejection, positive_acceptance)) => {
            state.webhook_signature_negative_rejection_passed = Some(negative_rejection);
            state.webhook_positive_delivery_passed = Some(positive_acceptance);
            if negative_rejection {
                note_stage_success(state);
            }
            if positive_acceptance {
                note_stage_success(state);
            }
        }
        Err(failure) => apply_stage_failure(state, failure),
    }

    if state.supported_upstream_compatibility_passed.is_none() {
        state.supported_upstream_compatibility_passed = Some(
            state.supported_upstream_version_passed == Some(true)
                && state.bootstrap_subject_resolved == Some(true)
                && state.account_snapshot_fetched == Some(true)
                && state.account_snapshot_fresh == Some(true)
                && state.account_id_expected_match != Some(false)
                && state.bridge_manifest_bootstrap_passed == Some(true)
                && state.bridge_device_register_passed == Some(true)
                && state.bridge_token_exchange_passed == Some(true)
                && state.bridge_manifest_refresh_passed == Some(true)
                && state.webhook_signature_negative_rejection_passed == Some(true)
                && state.webhook_positive_delivery_passed == Some(true)
                && state.response_shape_contract_passed == Some(true)
                && state.summary_contract_invalid_count == 0
                && state.required_input_unready_count == 0
                && state.degradation_hold_count == 0,
        );
    }
}

async fn run_bridge_backed_checks(
    adapter: &HttpRemnawaveAdapter,
    bootstrap_subject: &str,
    webhook_signature: &str,
    snapshot: &AccountSnapshot,
    config: &ResolvedConfig,
) -> Result<BridgeFlowEvidence, StageFailure> {
    let store_path = temporary_sqlite_store_path("supported-upstream");
    let router =
        build_supported_upstream_router(adapter.clone(), store_path.as_path(), webhook_signature)
            .map_err(|error| StageFailure {
            stage: "bridge_router_build",
            kind: StageFailureKind::IncompatibleContract,
            detail: error.to_string(),
        })?;
    let (public_base_url, public_handle) =
        spawn_router(router).await.map_err(|error| StageFailure {
            stage: "bridge_router_spawn",
            kind: StageFailureKind::Unavailable,
            detail: error.to_string(),
        })?;

    let result = exercise_bridge_public_flow(
        &public_base_url,
        bootstrap_subject,
        config
            .expected_account_id
            .as_deref()
            .unwrap_or(&snapshot.account_id),
    )
    .await;

    public_handle.abort();
    let _ = public_handle.await;
    cleanup_sqlite_store_path(store_path.as_path());
    result
}

async fn run_webhook_checks(
    adapter: &HttpRemnawaveAdapter,
    webhook_signature: &str,
    snapshot: &AccountSnapshot,
    config: &ResolvedConfig,
) -> Result<(bool, bool), StageFailure> {
    let store_path = temporary_sqlite_store_path("supported-upstream-webhook");
    let router =
        build_supported_upstream_router(adapter.clone(), store_path.as_path(), webhook_signature)
            .map_err(|error| StageFailure {
            stage: "bridge_webhook_router_build",
            kind: StageFailureKind::IncompatibleContract,
            detail: error.to_string(),
        })?;
    let (public_base_url, public_handle) =
        spawn_router(router).await.map_err(|error| StageFailure {
            stage: "bridge_webhook_router_spawn",
            kind: StageFailureKind::Unavailable,
            detail: error.to_string(),
        })?;
    let client = reqwest::Client::new();
    let now = OffsetDateTime::now_utc().unix_timestamp();
    let negative_payload = VerifiedWebhookPayload {
        event_id: format!("evt-negative-{now}"),
        event_type: config.webhook_event_type.clone(),
        account_id: Some(snapshot.account_id.clone()),
        occurred_at_unix: now,
        payload: serde_json::json!({ "phase": "negative" }),
    };
    let negative_response = client
        .post(format!("{public_base_url}/internal/remnawave/webhook"))
        .header(
            "x-remnawave-signature",
            format!("{webhook_signature}-invalid"),
        )
        .header("x-remnawave-timestamp", now.to_string())
        .json(&negative_payload)
        .send()
        .await
        .map_err(|error| classify_request_error("webhook_negative_rejection", error))?;
    if negative_response.status() != reqwest::StatusCode::UNAUTHORIZED {
        public_handle.abort();
        let _ = public_handle.await;
        cleanup_sqlite_store_path(store_path.as_path());
        return Err(StageFailure {
            stage: "webhook_negative_rejection",
            kind: StageFailureKind::IncompatibleContract,
            detail: format!("expected 401, got {}", negative_response.status()),
        });
    }

    let positive_payload = VerifiedWebhookPayload {
        event_id: format!("evt-positive-{now}"),
        event_type: config.webhook_event_type.clone(),
        account_id: Some(snapshot.account_id.clone()),
        occurred_at_unix: now,
        payload: serde_json::json!({ "phase": "positive" }),
    };
    let positive_response = client
        .post(format!("{public_base_url}/internal/remnawave/webhook"))
        .header("x-remnawave-signature", webhook_signature)
        .header("x-remnawave-timestamp", now.to_string())
        .json(&positive_payload)
        .send()
        .await
        .map_err(|error| classify_request_error("webhook_positive_acceptance", error))?;

    public_handle.abort();
    let _ = public_handle.await;
    cleanup_sqlite_store_path(store_path.as_path());

    if positive_response.status() != reqwest::StatusCode::OK {
        return Err(StageFailure {
            stage: "webhook_positive_acceptance",
            kind: classify_status_failure(positive_response.status()),
            detail: format!("expected 200, got {}", positive_response.status()),
        });
    }

    Ok((true, true))
}

async fn exercise_bridge_public_flow(
    base_url: &str,
    bootstrap_subject: &str,
    expected_account_id: &str,
) -> Result<BridgeFlowEvidence, StageFailure> {
    let client = reqwest::Client::new();
    let manifest_response = client
        .get(format!(
            "{base_url}/v0/manifest?subscription_token={bootstrap_subject}"
        ))
        .send()
        .await
        .map_err(|error| classify_request_error("bridge_manifest_bootstrap", error))?;
    if manifest_response.status() != reqwest::StatusCode::OK {
        return Err(StageFailure {
            stage: "bridge_manifest_bootstrap",
            kind: classify_status_failure(manifest_response.status()),
            detail: format!("expected 200, got {}", manifest_response.status()),
        });
    }
    let manifest: ManifestDocument =
        manifest_response
            .json()
            .await
            .map_err(|error| StageFailure {
                stage: "bridge_manifest_bootstrap",
                kind: StageFailureKind::Drift,
                detail: error.to_string(),
            })?;
    let bootstrap_credential = manifest
        .refresh
        .as_ref()
        .map(|refresh| refresh.credential.clone())
        .ok_or_else(|| StageFailure {
            stage: "bridge_manifest_bootstrap",
            kind: StageFailureKind::IncompatibleContract,
            detail: "bootstrap manifest did not include a refresh credential".to_owned(),
        })?;

    let register_response = client
        .post(format!("{base_url}/v0/device/register"))
        .bearer_auth(&bootstrap_credential)
        .json(&serde_json::json!({
            "manifest_id": manifest.manifest_id,
            "device_id": "device-1",
            "device_name": "Workstation",
            "platform": "windows",
            "client_version": "0.1.0",
            "install_channel": "stable",
            "requested_capabilities": [1, 2]
        }))
        .send()
        .await
        .map_err(|error| classify_request_error("bridge_device_register", error))?;
    if register_response.status() != reqwest::StatusCode::OK {
        return Err(StageFailure {
            stage: "bridge_device_register",
            kind: classify_status_failure(register_response.status()),
            detail: format!("expected 200, got {}", register_response.status()),
        });
    }
    let register: DeviceRegisterResponse =
        register_response
            .json()
            .await
            .map_err(|error| StageFailure {
                stage: "bridge_device_register",
                kind: StageFailureKind::Drift,
                detail: error.to_string(),
            })?;
    let refresh_credential = register.refresh_credential.ok_or_else(|| StageFailure {
        stage: "bridge_device_register",
        kind: StageFailureKind::IncompatibleContract,
        detail: "device register did not issue a refresh credential".to_owned(),
    })?;

    let exchange_response = client
        .post(format!("{base_url}/v0/token/exchange"))
        .json(&TokenExchangeRequest {
            manifest_id: manifest.manifest_id.clone(),
            device_id: "device-1".to_owned(),
            client_version: "0.1.0".to_owned(),
            core_version: 1,
            carrier_profile_id: "carrier-primary".to_owned(),
            requested_capabilities: vec![1, 2],
            refresh_credential: refresh_credential.clone(),
        })
        .send()
        .await
        .map_err(|error| classify_request_error("bridge_token_exchange", error))?;
    if exchange_response.status() != reqwest::StatusCode::OK {
        return Err(StageFailure {
            stage: "bridge_token_exchange",
            kind: classify_status_failure(exchange_response.status()),
            detail: format!("expected 200, got {}", exchange_response.status()),
        });
    }
    let exchange: TokenExchangeResponse =
        exchange_response
            .json()
            .await
            .map_err(|error| StageFailure {
                stage: "bridge_token_exchange",
                kind: StageFailureKind::Drift,
                detail: error.to_string(),
            })?;
    if exchange.policy_epoch == 0 || exchange.session_token.trim().is_empty() {
        return Err(StageFailure {
            stage: "bridge_token_exchange",
            kind: StageFailureKind::IncompatibleContract,
            detail: "token exchange returned an incomplete session token response".to_owned(),
        });
    }

    let refresh_manifest = client
        .get(format!("{base_url}/v0/manifest"))
        .bearer_auth(&refresh_credential)
        .send()
        .await
        .map_err(|error| classify_request_error("bridge_manifest_refresh", error))?;
    if !matches!(
        refresh_manifest.status(),
        reqwest::StatusCode::OK | reqwest::StatusCode::NOT_MODIFIED
    ) {
        return Err(StageFailure {
            stage: "bridge_manifest_refresh",
            kind: classify_status_failure(refresh_manifest.status()),
            detail: format!(
                "expected 200 or 304, got {} for account {}",
                refresh_manifest.status(),
                expected_account_id
            ),
        });
    }

    Ok(BridgeFlowEvidence {
        manifest_bootstrap_passed: true,
        device_register_passed: true,
        token_exchange_passed: true,
        manifest_refresh_passed: true,
    })
}

fn build_supported_upstream_router(
    adapter: HttpRemnawaveAdapter,
    store_path: &Path,
    webhook_signature: &str,
) -> anyhow::Result<Router> {
    let store = SharedBridgeStore::new(SqliteBridgeStore::open(store_path)?);
    let manifest_signer =
        ManifestSigner::new(FIXTURE_MANIFEST_KEY_ID, fixture_manifest_signing_key());
    let token_signer = build_token_signer()?;
    let domain = Arc::new(BridgeDomain::new(
        adapter,
        store,
        manifest_signer,
        token_signer,
        Duration::seconds(300),
    ));

    Ok(build_bridge_router(BridgeHttpServiceState::new(
        domain,
        supported_upstream_manifest_template(),
        Arc::new(FixedWebhookSignatureAuthenticator {
            expected_signature: webhook_signature.to_owned(),
        }),
        WebhookVerificationConfig::default(),
        serde_json::to_value(fixture_token_jwks())?,
        BridgeHttpBudgets::default(),
    )))
}

fn supported_upstream_manifest_template() -> BridgeManifestTemplate {
    let generated_at = fixed_test_now();
    let manifest = sample_manifest_document(generated_at, generated_at + Duration::hours(6));
    BridgeManifestTemplate {
        context: BridgeManifestContext {
            device_policy: manifest.device_policy,
            client_constraints: manifest.client_constraints,
            token_service: manifest.token_service,
            refresh: manifest.refresh,
            routing: manifest.routing,
            retry_policy: manifest.retry_policy,
            telemetry: manifest.telemetry,
        },
        carrier_profiles: manifest.carrier_profiles,
        endpoints: manifest.endpoints,
        manifest_ttl: Duration::hours(6),
        bootstrap_grant_ttl: Duration::minutes(10),
    }
}

fn build_token_signer() -> anyhow::Result<SessionTokenSigner> {
    let pem = fixture_token_signing_key()
        .to_pkcs8_pem(Default::default())
        .context("failed to encode supported-upstream token signer")?;
    SessionTokenSigner::from_ed_pem(
        "bridge.example",
        "northstar-gateway",
        FIXTURE_TOKEN_KEY_ID,
        pem.as_bytes(),
    )
    .map_err(anyhow::Error::from)
}

async fn spawn_router(router: Router) -> anyhow::Result<(String, tokio::task::JoinHandle<()>)> {
    let listener = TcpListener::bind("127.0.0.1:0").await?;
    let addr = listener.local_addr()?;
    let handle = tokio::spawn(async move {
        axum::serve(listener, router).await.expect(
            "supported-upstream verification server should serve while the harness is active",
        );
    });
    tokio::time::sleep(std::time::Duration::from_millis(10)).await;
    Ok((format!("http://{addr}"), handle))
}

fn validate_supported_version(snapshot: &AccountSnapshot) -> Result<bool, String> {
    let version = snapshot
        .source_version
        .as_deref()
        .ok_or_else(|| "supported_upstream_source_version_missing".to_owned())?;
    let parsed = SimpleVersion::parse(version)
        .ok_or_else(|| format!("supported_upstream_source_version_invalid:{version}"))?;
    if parsed < SUPPORTED_UPSTREAM_VERSION_FLOOR {
        return Err(format!(
            "supported_upstream_version_unsupported:{}<{}",
            parsed.render(),
            SUPPORTED_UPSTREAM_VERSION_FLOOR.render()
        ));
    }

    Ok(parsed >= SUPPORTED_UPSTREAM_VERSION_PREFERRED)
}

fn validate_expected_account_id(
    snapshot: &AccountSnapshot,
    expected_account_id: Option<&str>,
) -> Result<bool, String> {
    match expected_account_id {
        Some(expected) if expected.trim().is_empty() => {
            Err("supported_upstream_expected_account_id_invalid".to_owned())
        }
        Some(expected) => Ok(snapshot.account_id == expected),
        None => Ok(true),
    }
}

fn snapshot_is_fresh(snapshot: &AccountSnapshot, max_snapshot_age_seconds: i64) -> bool {
    let now = OffsetDateTime::now_utc().unix_timestamp();
    let age = now.saturating_sub(snapshot.observed_at_unix);
    age <= max_snapshot_age_seconds.max(0)
}

fn classify_request_error(stage: &'static str, error: reqwest::Error) -> StageFailure {
    let kind = if error.is_timeout() {
        StageFailureKind::Timeout
    } else if error.is_connect() || error.is_request() {
        StageFailureKind::Unavailable
    } else {
        StageFailureKind::IncompatibleContract
    };
    StageFailure {
        stage,
        kind,
        detail: error.to_string(),
    }
}

fn classify_status_failure(status: reqwest::StatusCode) -> StageFailureKind {
    if matches!(
        status,
        reqwest::StatusCode::UNAUTHORIZED | reqwest::StatusCode::FORBIDDEN
    ) {
        StageFailureKind::AuthFailure
    } else if matches!(
        status,
        reqwest::StatusCode::REQUEST_TIMEOUT | reqwest::StatusCode::GATEWAY_TIMEOUT
    ) {
        StageFailureKind::Timeout
    } else if status == reqwest::StatusCode::TOO_MANY_REQUESTS || status.is_server_error() {
        StageFailureKind::Unavailable
    } else {
        StageFailureKind::IncompatibleContract
    }
}

fn apply_stage_failure(state: &mut SummaryState, failure: StageFailure) {
    match failure.stage {
        "bridge_router_build" | "bridge_router_spawn" => {
            state.bridge_manifest_bootstrap_passed = Some(false);
            state.bridge_device_register_passed = Some(false);
            state.bridge_token_exchange_passed = Some(false);
            state.bridge_manifest_refresh_passed = Some(false);
        }
        "bridge_manifest_bootstrap" => state.bridge_manifest_bootstrap_passed = Some(false),
        "bridge_device_register" => state.bridge_device_register_passed = Some(false),
        "bridge_token_exchange" => state.bridge_token_exchange_passed = Some(false),
        "bridge_manifest_refresh" => state.bridge_manifest_refresh_passed = Some(false),
        "bridge_webhook_router_build" | "bridge_webhook_router_spawn" => {
            state.webhook_signature_negative_rejection_passed = Some(false);
            state.webhook_positive_delivery_passed = Some(false);
        }
        "webhook_negative_rejection" => {
            state.webhook_signature_negative_rejection_passed = Some(false)
        }
        "webhook_positive_acceptance" => state.webhook_positive_delivery_passed = Some(false),
        _ => {}
    }

    match failure.kind {
        StageFailureKind::AuthFailure => {
            if failure.stage.starts_with("webhook_") || failure.stage.starts_with("bridge_webhook")
            {
                state.webhook_signature_failure_detected = true;
            }
            state.upstream_auth_failure_detected = true;
            mark_unready(
                state,
                &format!("{}:{}", failure.stage, failure.detail),
                "upstream_auth_failure",
                "supported_upstream_auth",
            );
        }
        StageFailureKind::Timeout => {
            state.upstream_timeout_detected = true;
            state.partially_degraded_upstream = true;
            mark_degradation(
                state,
                &format!("{}:{}", failure.stage, failure.detail),
                "upstream_timeout",
                "supported_upstream_availability",
            );
        }
        StageFailureKind::Unavailable => {
            state.upstream_unavailable_detected = true;
            mark_unready(
                state,
                &format!("{}:{}", failure.stage, failure.detail),
                "upstream_unavailable",
                "supported_upstream_availability",
            );
        }
        StageFailureKind::Drift => {
            state.upstream_drift_detected = true;
            state.response_shape_contract_passed = Some(false);
            mark_contract_invalid(
                state,
                &format!("{}:{}", failure.stage, failure.detail),
                "response_shape_drift",
                "supported_upstream_contract",
            );
        }
        StageFailureKind::IncompatibleContract => {
            if failure.stage.starts_with("webhook_") || failure.stage.starts_with("bridge_webhook")
            {
                state.webhook_signature_failure_detected = true;
            }
            state.incompatible_contract_detected = true;
            mark_contract_invalid(
                state,
                &format!("{}:{}", failure.stage, failure.detail),
                "incompatible_contract",
                "supported_upstream_contract",
            );
        }
    }
}

fn apply_adapter_error(state: &mut SummaryState, stage: &'static str, error: AdapterError) {
    match error {
        AdapterError::Unauthorized => {
            state.upstream_auth_failure_detected = true;
            mark_unready(
                state,
                &format!("{stage}:unauthorized"),
                "upstream_auth_failure",
                "supported_upstream_auth",
            );
        }
        AdapterError::Timeout => {
            state.upstream_timeout_detected = true;
            state.partially_degraded_upstream = true;
            mark_degradation(
                state,
                &format!("{stage}:timeout"),
                "upstream_timeout",
                "supported_upstream_availability",
            );
        }
        AdapterError::Unavailable | AdapterError::RateLimited | AdapterError::NotFound => {
            if matches!(error, AdapterError::Unavailable | AdapterError::RateLimited) {
                state.upstream_unavailable_detected = true;
            }
            mark_unready(
                state,
                &format!("{stage}:{error}"),
                "required_input_unready",
                "supported_upstream_readiness",
            );
        }
        AdapterError::SchemaDrift => {
            state.upstream_drift_detected = true;
            state.response_shape_contract_passed = Some(false);
            mark_contract_invalid(
                state,
                &format!("{stage}:schema_drift"),
                "response_shape_drift",
                "supported_upstream_contract",
            );
        }
        AdapterError::InvalidData(_) | AdapterError::Conflict => {
            state.incompatible_contract_detected = true;
            mark_contract_invalid(
                state,
                &format!("{stage}:{error}"),
                "incompatible_contract",
                "supported_upstream_contract",
            );
        }
    }
}

fn note_stage_success(state: &mut SummaryState) {
    state.successful_stage_count += 1;
}

fn mark_unready(state: &mut SummaryState, code: &str, reason_key: &str, family: &'static str) {
    state.required_input_unready_count += 1;
    state.supported_upstream_compatibility_passed = Some(false);
    push_reason(state, code, reason_key, family);
}

fn mark_contract_invalid(
    state: &mut SummaryState,
    code: &str,
    reason_key: &str,
    family: &'static str,
) {
    state.summary_contract_invalid_count += 1;
    state.supported_upstream_compatibility_passed = Some(false);
    push_reason(state, code, reason_key, family);
}

fn mark_degradation(state: &mut SummaryState, code: &str, reason_key: &str, family: &'static str) {
    state.degradation_hold_count += 1;
    state.partially_degraded_upstream = true;
    state.supported_upstream_compatibility_passed = Some(false);
    push_reason(state, code, reason_key, family);
}

fn push_reason(state: &mut SummaryState, code: &str, reason_key: &str, family: &'static str) {
    state.blocking_reasons.push(code.to_owned());
    *state
        .blocking_reason_key_counts
        .entry(reason_key.to_owned())
        .or_insert(0) += 1;
    *state
        .blocking_reason_family_counts
        .entry(family.to_owned())
        .or_insert(0) += 1;
}

fn finalize_summary(
    config: &ResolvedConfig,
    required_inputs: Vec<String>,
    considered_inputs: Vec<String>,
    mut state: SummaryState,
) -> SupportedUpstreamVerificationSummary {
    let missing_required_input_count = state.missing_required_inputs.len();
    let blocking_reason_count = state.blocking_reasons.len();
    let (gate_state_reason, gate_state_reason_family) = summarize_rollout_gate_state(
        missing_required_input_count,
        state.summary_contract_invalid_count,
        state.required_input_unready_count,
        state.degradation_hold_count,
        blocking_reason_count,
    );
    let gate_state = if gate_state_reason == "all_required_inputs_passed" {
        "passed"
    } else {
        "blocked"
    };
    let verdict = if gate_state == "passed" {
        "ready"
    } else {
        "hold"
    };
    let evidence_state = if missing_required_input_count > 0 {
        "incomplete"
    } else if verdict == "ready" || state.successful_stage_count > 0 {
        "complete"
    } else {
        "partial"
    };
    let required_input_count = required_inputs.len();
    let required_input_present_count =
        required_input_count.saturating_sub(missing_required_input_count);
    let required_input_failed_count =
        usize::from(required_input_present_count > 0 && gate_state != "passed");
    let required_input_passed_count =
        required_input_present_count.saturating_sub(required_input_failed_count);
    let compatibility_passed = state.supported_upstream_compatibility_passed.or(
        if state.supported_upstream_environment_present {
            Some(verdict == "ready")
        } else {
            None
        },
    );
    let upstream_state = derive_upstream_state(&state, compatibility_passed);
    let blocking_reason_keys = state
        .blocking_reason_key_counts
        .keys()
        .cloned()
        .collect::<Vec<_>>();
    let blocking_reason_families = state
        .blocking_reason_family_counts
        .keys()
        .cloned()
        .collect::<Vec<_>>();

    if compatibility_passed == Some(true) {
        state.response_shape_contract_passed.get_or_insert(true);
    }

    SupportedUpstreamVerificationSummary {
        summary_version: SUPPORTED_UPSTREAM_SUMMARY_VERSION,
        verification_schema: SUPPORTED_UPSTREAM_VERIFICATION_SCHEMA,
        verification_schema_version: SUPPORTED_UPSTREAM_VERIFICATION_SCHEMA_VERSION,
        verdict_family: SUPPORTED_UPSTREAM_VERDICT_FAMILY,
        decision_scope: SUPPORTED_UPSTREAM_DECISION_SCOPE,
        decision_label: SUPPORTED_UPSTREAM_DECISION_LABEL,
        profile: SUPPORTED_UPSTREAM_PROFILE,
        verdict,
        evidence_state,
        gate_state,
        gate_state_reason,
        gate_state_reason_family,
        required_inputs,
        considered_inputs,
        missing_required_inputs: state.missing_required_inputs,
        missing_required_input_count,
        required_input_count,
        required_input_missing_count: missing_required_input_count,
        required_input_failed_count,
        required_input_unready_count: state.required_input_unready_count,
        required_input_present_count,
        required_input_passed_count,
        all_required_inputs_present: missing_required_input_count == 0,
        all_required_inputs_passed: gate_state == "passed",
        blocking_reason_count,
        blocking_reason_key_count: state.blocking_reason_key_counts.len(),
        blocking_reason_family_count: state.blocking_reason_family_counts.len(),
        blocking_reason_key_counts: state.blocking_reason_key_counts,
        blocking_reason_family_counts: state.blocking_reason_family_counts,
        supported_upstream_environment_present: state.supported_upstream_environment_present,
        supported_upstream_base_url: config.base_url.clone(),
        supported_upstream_version_floor: SUPPORTED_UPSTREAM_VERSION_FLOOR.render(),
        supported_upstream_version_preferred: SUPPORTED_UPSTREAM_VERSION_PREFERRED.render(),
        upstream_source_version: state.upstream_source_version,
        upstream_state,
        supported_upstream_version_passed: state.supported_upstream_version_passed,
        supported_upstream_version_preferred_passed: state
            .supported_upstream_version_preferred_passed,
        bootstrap_subject_resolved: state.bootstrap_subject_resolved,
        account_snapshot_fetched: state.account_snapshot_fetched,
        account_snapshot_fresh: state.account_snapshot_fresh,
        account_id_expected_match: state.account_id_expected_match,
        bridge_manifest_bootstrap_passed: state.bridge_manifest_bootstrap_passed,
        bridge_device_register_passed: state.bridge_device_register_passed,
        bridge_token_exchange_passed: state.bridge_token_exchange_passed,
        bridge_manifest_refresh_passed: state.bridge_manifest_refresh_passed,
        webhook_signature_negative_rejection_passed: state
            .webhook_signature_negative_rejection_passed,
        webhook_positive_delivery_passed: state.webhook_positive_delivery_passed,
        response_shape_contract_passed: state.response_shape_contract_passed,
        supported_upstream_compatibility_passed: compatibility_passed,
        partially_degraded_upstream: state.partially_degraded_upstream,
        unsupported_upstream_version_detected: state.unsupported_upstream_version_detected,
        upstream_auth_failure_detected: state.upstream_auth_failure_detected,
        upstream_timeout_detected: state.upstream_timeout_detected,
        upstream_unavailable_detected: state.upstream_unavailable_detected,
        upstream_stale_detected: state.upstream_stale_detected,
        upstream_drift_detected: state.upstream_drift_detected,
        webhook_signature_failure_detected: state.webhook_signature_failure_detected,
        incompatible_contract_detected: state.incompatible_contract_detected,
        blocking_reasons: state.blocking_reasons,
        blocking_reason_keys,
        blocking_reason_families,
    }
}

fn derive_upstream_state(state: &SummaryState, compatibility_passed: Option<bool>) -> &'static str {
    if !state.supported_upstream_environment_present {
        "missing_environment"
    } else if state.unsupported_upstream_version_detected {
        "unsupported_version"
    } else if state.upstream_drift_detected {
        "response_shape_drift"
    } else if state.webhook_signature_failure_detected {
        "webhook_signature_failure"
    } else if state.upstream_auth_failure_detected {
        "unauthorized"
    } else if state.upstream_timeout_detected {
        "timeout"
    } else if state.upstream_unavailable_detected {
        "unavailable"
    } else if state.upstream_stale_detected {
        "stale"
    } else if state.partially_degraded_upstream {
        "partial_degradation"
    } else if compatibility_passed == Some(true) {
        "verified"
    } else {
        "unverified"
    }
}

fn collect_missing_required_inputs(config: &ResolvedConfig, state: &mut SummaryState) {
    if config.base_url.is_none() {
        state
            .missing_required_inputs
            .push("supported_upstream_base_url".to_owned());
    }
    if config.api_token.is_none() {
        state
            .missing_required_inputs
            .push("supported_upstream_api_token".to_owned());
    }
    if config.bootstrap_subject.is_none() {
        state
            .missing_required_inputs
            .push("supported_upstream_bootstrap_subject".to_owned());
    }
    if config.webhook_signature.is_none() {
        state
            .missing_required_inputs
            .push("supported_upstream_webhook_signature".to_owned());
    }
}

fn supported_upstream_required_inputs() -> Vec<String> {
    vec![
        "supported_upstream_base_url".to_owned(),
        "supported_upstream_api_token".to_owned(),
        "supported_upstream_bootstrap_subject".to_owned(),
        "supported_upstream_webhook_signature".to_owned(),
    ]
}

fn resolve_config(args: SupportedUpstreamArgs) -> ResolvedConfig {
    let format = args.format.unwrap_or(OutputFormat::Text);
    let summary_path = args
        .summary_path
        .or_else(|| {
            env_override(None, "NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_SUMMARY_PATH")
                .map(PathBuf::from)
        })
        .unwrap_or_else(default_summary_path);
    let request_timeout_ms = args
        .request_timeout_ms
        .or_else(|| parse_env_u64("NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_REQUEST_TIMEOUT_MS"))
        .unwrap_or(5_000);
    let max_snapshot_age_seconds = args
        .max_snapshot_age_seconds
        .or_else(|| {
            parse_env_i64("NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_MAX_SNAPSHOT_AGE_SECONDS")
        })
        .unwrap_or(300);
    let webhook_event_type = args
        .webhook_event_type
        .or_else(|| {
            env_override(
                None,
                "NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_WEBHOOK_EVENT_TYPE",
            )
        })
        .unwrap_or_else(|| "subscription.updated".to_owned());

    ResolvedConfig {
        format,
        summary_path,
        base_url: env_override(
            args.base_url,
            "NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_BASE_URL",
        ),
        api_token: env_override(
            args.api_token,
            "NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_API_TOKEN",
        ),
        bootstrap_subject: env_override(
            args.bootstrap_subject,
            "NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_BOOTSTRAP_SUBJECT",
        ),
        webhook_signature: env_override(
            args.webhook_signature,
            "NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_WEBHOOK_SIGNATURE",
        ),
        source_version_override: env_override(
            args.source_version_override,
            "NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_SOURCE_VERSION",
        ),
        request_timeout_ms,
        max_snapshot_age_seconds,
        expected_account_id: env_override(
            args.expected_account_id,
            "NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_ACCOUNT_ID",
        ),
        webhook_event_type,
    }
}

fn env_override(current: Option<String>, key: &str) -> Option<String> {
    current.or_else(|| env::var(key).ok()).and_then(|value| {
        if value.trim().is_empty() {
            None
        } else {
            Some(value)
        }
    })
}

fn parse_env_u64(key: &str) -> Option<u64> {
    env::var(key).ok()?.parse().ok()
}

fn parse_env_i64(key: &str) -> Option<i64> {
    env::var(key).ok()?.parse().ok()
}

fn apply_source_version_override(
    mut snapshot: AccountSnapshot,
    source_version_override: Option<&str>,
) -> AccountSnapshot {
    if snapshot.source_version.is_none() {
        snapshot.source_version = source_version_override
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .map(ToOwned::to_owned);
    }
    snapshot
}

fn parse_args<I>(args: I) -> Result<SupportedUpstreamArgs, Box<dyn std::error::Error>>
where
    I: IntoIterator<Item = String>,
{
    let mut parsed = SupportedUpstreamArgs::default();
    let mut iter = args.into_iter();
    while let Some(argument) = iter.next() {
        match argument.as_str() {
            "--json" => parsed.format = Some(OutputFormat::Json),
            "--text" => parsed.format = Some(OutputFormat::Text),
            "--summary-path" => {
                parsed.summary_path = Some(PathBuf::from(next_arg(&mut iter, "--summary-path")?));
            }
            "--base-url" => parsed.base_url = Some(next_arg(&mut iter, "--base-url")?),
            "--api-token" => parsed.api_token = Some(next_arg(&mut iter, "--api-token")?),
            "--bootstrap-subject" => {
                parsed.bootstrap_subject = Some(next_arg(&mut iter, "--bootstrap-subject")?)
            }
            "--webhook-signature" => {
                parsed.webhook_signature = Some(next_arg(&mut iter, "--webhook-signature")?)
            }
            "--request-timeout-ms" => {
                parsed.request_timeout_ms = Some(
                    next_arg(&mut iter, "--request-timeout-ms")?
                        .parse()
                        .map_err(|_| "--request-timeout-ms must be an integer")?,
                );
            }
            "--max-snapshot-age-seconds" => {
                parsed.max_snapshot_age_seconds = Some(
                    next_arg(&mut iter, "--max-snapshot-age-seconds")?
                        .parse()
                        .map_err(|_| "--max-snapshot-age-seconds must be an integer")?,
                );
            }
            "--expected-account-id" => {
                parsed.expected_account_id = Some(next_arg(&mut iter, "--expected-account-id")?)
            }
            "--webhook-event-type" => {
                parsed.webhook_event_type = Some(next_arg(&mut iter, "--webhook-event-type")?)
            }
            other => return Err(format!("unsupported argument: {other}").into()),
        }
    }

    Ok(parsed)
}

fn next_arg<I>(iter: &mut I, flag: &str) -> Result<String, Box<dyn std::error::Error>>
where
    I: Iterator<Item = String>,
{
    iter.next()
        .ok_or_else(|| format!("{flag} requires a value").into())
}

fn print_text_summary(summary: &SupportedUpstreamVerificationSummary, summary_path: &Path) {
    println!("Northstar Supported Upstream Verification");
    println!("- summary_version: {}", summary.summary_version);
    println!("- verification_schema: {}", summary.verification_schema);
    println!("- decision_label: {}", summary.decision_label);
    println!("- verdict: {}", summary.verdict);
    println!("- evidence_state: {}", summary.evidence_state);
    println!("- gate_state: {}", summary.gate_state);
    println!("- gate_state_reason: {}", summary.gate_state_reason);
    println!(
        "- gate_state_reason_family: {}",
        summary.gate_state_reason_family
    );
    println!(
        "- supported_upstream_environment_present: {}",
        summary.supported_upstream_environment_present
    );
    println!(
        "- supported_upstream_base_url: {}",
        summary
            .supported_upstream_base_url
            .as_deref()
            .unwrap_or("missing")
    );
    println!(
        "- upstream_source_version: {}",
        summary
            .upstream_source_version
            .as_deref()
            .unwrap_or("missing")
    );
    println!("- upstream_state: {}", summary.upstream_state);
    println!(
        "- required_input_counts: total={} present={} passed={} missing={} unready={}",
        summary.required_input_count,
        summary.required_input_present_count,
        summary.required_input_passed_count,
        summary.required_input_missing_count,
        summary.required_input_unready_count
    );
    println!(
        "- supported_upstream_version_passed: {}",
        render_optional_bool(summary.supported_upstream_version_passed)
    );
    println!(
        "- supported_upstream_version_preferred_passed: {}",
        render_optional_bool(summary.supported_upstream_version_preferred_passed)
    );
    println!(
        "- bootstrap_subject_resolved: {}",
        render_optional_bool(summary.bootstrap_subject_resolved)
    );
    println!(
        "- account_snapshot_fetched: {}",
        render_optional_bool(summary.account_snapshot_fetched)
    );
    println!(
        "- account_snapshot_fresh: {}",
        render_optional_bool(summary.account_snapshot_fresh)
    );
    println!(
        "- account_id_expected_match: {}",
        render_optional_bool(summary.account_id_expected_match)
    );
    println!(
        "- bridge_manifest_bootstrap_passed: {}",
        render_optional_bool(summary.bridge_manifest_bootstrap_passed)
    );
    println!(
        "- bridge_device_register_passed: {}",
        render_optional_bool(summary.bridge_device_register_passed)
    );
    println!(
        "- bridge_token_exchange_passed: {}",
        render_optional_bool(summary.bridge_token_exchange_passed)
    );
    println!(
        "- bridge_manifest_refresh_passed: {}",
        render_optional_bool(summary.bridge_manifest_refresh_passed)
    );
    println!(
        "- webhook_signature_negative_rejection_passed: {}",
        render_optional_bool(summary.webhook_signature_negative_rejection_passed)
    );
    println!(
        "- webhook_positive_delivery_passed: {}",
        render_optional_bool(summary.webhook_positive_delivery_passed)
    );
    println!(
        "- response_shape_contract_passed: {}",
        render_optional_bool(summary.response_shape_contract_passed)
    );
    println!(
        "- supported_upstream_compatibility_passed: {}",
        render_optional_bool(summary.supported_upstream_compatibility_passed)
    );
    println!(
        "- detector_flags: unsupported_version={} auth_failure={} timeout={} unavailable={} stale={} drift={} webhook_signature_failure={} incompatible_contract={}",
        summary.unsupported_upstream_version_detected,
        summary.upstream_auth_failure_detected,
        summary.upstream_timeout_detected,
        summary.upstream_unavailable_detected,
        summary.upstream_stale_detected,
        summary.upstream_drift_detected,
        summary.webhook_signature_failure_detected,
        summary.incompatible_contract_detected
    );
    if summary.blocking_reasons.is_empty() {
        println!("- blocking_reasons: none");
    } else {
        println!(
            "- blocking_reasons: {}",
            summary.blocking_reasons.join(", ")
        );
    }
    println!("- summary_path: {}", summary_path.display());
}

fn render_optional_bool(value: Option<bool>) -> &'static str {
    match value {
        Some(true) => "true",
        Some(false) => "false",
        None => "missing",
    }
}

fn default_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("remnawave-supported-upstream-summary.json")
}

fn parse_numeric_segment(value: &str) -> Option<u64> {
    let digits = value
        .chars()
        .take_while(|character| character.is_ascii_digit())
        .collect::<String>();
    if digits.is_empty() {
        None
    } else {
        digits.parse().ok()
    }
}

fn temporary_sqlite_store_path(prefix: &str) -> PathBuf {
    let unique = format!(
        "{}-{}-{}",
        prefix,
        std::process::id(),
        OffsetDateTime::now_utc().unix_timestamp_nanos()
    );
    repo_root()
        .join("target")
        .join("northstar")
        .join(format!("{unique}.sqlite"))
}

fn cleanup_sqlite_store_path(path: &Path) {
    for candidate in [
        path.to_path_buf(),
        PathBuf::from(format!("{}-wal", path.display())),
        PathBuf::from(format!("{}-shm", path.display())),
    ] {
        match fs::remove_file(&candidate) {
            Ok(()) => {}
            Err(error) if error.kind() == ErrorKind::NotFound => {}
            Err(_) => {}
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::Json;
    use axum::extract::{Path as AxumPath, State};
    use axum::http::HeaderMap;
    use axum::http::header::AUTHORIZATION;
    use axum::routing::{get, post};
    use serde::Deserialize;
    use std::sync::Mutex;

    #[derive(Debug, Deserialize)]
    struct ResolveBootstrapRequest {
        bootstrap_subject_kind: String,
        bootstrap_subject: String,
    }

    struct TestUpstreamState {
        snapshot: Mutex<AccountSnapshot>,
        expected_token: String,
    }

    fn authorized(headers: &HeaderMap, expected_token: &str) -> bool {
        headers
            .get(AUTHORIZATION)
            .and_then(|value| value.to_str().ok())
            .and_then(|value| value.strip_prefix("Bearer "))
            == Some(expected_token)
    }

    fn supported_snapshot(version: &str) -> AccountSnapshot {
        AccountSnapshot {
            account_id: "acct-1".to_owned(),
            bootstrap_subjects: vec![BootstrapSubject::ShortUuid("sub-1".to_owned())],
            lifecycle: ns_remnawave_adapter::AccountLifecycle::Active,
            northstar_access: ns_remnawave_adapter::NorthstarAccess {
                northstar_enabled: true,
                policy_epoch: 7,
                device_limit: Some(4),
                allowed_core_versions: vec![1],
                allowed_carrier_profiles: vec!["carrier-primary".to_owned()],
                allowed_capabilities: vec![1, 2],
                rollout_cohort: Some("stable".to_owned()),
                preferred_regions: vec!["eu-central".to_owned()],
            },
            metadata: Some(serde_json::json!({ "plan": "pro" })),
            observed_at_unix: OffsetDateTime::now_utc().unix_timestamp() - 30,
            source_version: Some(version.to_owned()),
        }
    }

    async fn resolve_user(
        State(state): State<Arc<TestUpstreamState>>,
        headers: HeaderMap,
        Json(request): Json<ResolveBootstrapRequest>,
    ) -> Result<Json<AccountSnapshot>, reqwest::StatusCode> {
        if !authorized(&headers, &state.expected_token) {
            return Err(reqwest::StatusCode::UNAUTHORIZED);
        }
        if request.bootstrap_subject_kind != "short_uuid" || request.bootstrap_subject != "sub-1" {
            return Err(reqwest::StatusCode::NOT_FOUND);
        }
        Ok(Json(
            state
                .snapshot
                .lock()
                .expect("test upstream state poisoned")
                .clone(),
        ))
    }

    async fn get_user(
        State(state): State<Arc<TestUpstreamState>>,
        headers: HeaderMap,
        AxumPath(account_id): AxumPath<String>,
    ) -> Result<Json<AccountSnapshot>, reqwest::StatusCode> {
        if !authorized(&headers, &state.expected_token) {
            return Err(reqwest::StatusCode::UNAUTHORIZED);
        }
        let snapshot = state
            .snapshot
            .lock()
            .expect("test upstream state poisoned")
            .clone();
        if snapshot.account_id != account_id {
            return Err(reqwest::StatusCode::NOT_FOUND);
        }
        Ok(Json(snapshot))
    }

    async fn spawn_test_upstream(
        snapshot: AccountSnapshot,
    ) -> (String, tokio::task::JoinHandle<()>) {
        let state = Arc::new(TestUpstreamState {
            snapshot: Mutex::new(snapshot),
            expected_token: "rw-token".to_owned(),
        });
        let router = Router::new()
            .route("/api/users/resolve", post(resolve_user))
            .route("/api/users/{account_id}", get(get_user))
            .with_state(state);
        let (base_url, handle) = spawn_router(router)
            .await
            .expect("test upstream router should spawn");
        (base_url, handle)
    }

    fn test_config(base_url: Option<String>, api_token: Option<String>) -> ResolvedConfig {
        ResolvedConfig {
            format: OutputFormat::Json,
            summary_path: default_summary_path(),
            base_url,
            api_token,
            bootstrap_subject: Some("sub-1".to_owned()),
            webhook_signature: Some("sig-ok".to_owned()),
            source_version_override: None,
            request_timeout_ms: 500,
            max_snapshot_age_seconds: 300,
            expected_account_id: Some("acct-1".to_owned()),
            webhook_event_type: "subscription.updated".to_owned(),
        }
    }

    #[tokio::test]
    async fn supported_upstream_summary_is_ready_for_supported_fixture_server() {
        let (base_url, handle) = spawn_test_upstream(supported_snapshot("2.7.4")).await;
        let summary = build_supported_upstream_summary(&test_config(
            Some(base_url),
            Some("rw-token".to_owned()),
        ))
        .await;

        assert_eq!(summary.verdict, "ready");
        assert_eq!(summary.gate_state, "passed");
        assert_eq!(summary.gate_state_reason, "all_required_inputs_passed");
        assert_eq!(summary.upstream_state, "verified");
        assert_eq!(summary.supported_upstream_compatibility_passed, Some(true));
        assert_eq!(summary.bridge_manifest_bootstrap_passed, Some(true));
        assert_eq!(summary.bridge_device_register_passed, Some(true));
        assert_eq!(summary.bridge_token_exchange_passed, Some(true));
        assert_eq!(summary.bridge_manifest_refresh_passed, Some(true));
        assert_eq!(
            summary.webhook_signature_negative_rejection_passed,
            Some(true)
        );
        assert_eq!(summary.webhook_positive_delivery_passed, Some(true));

        handle.abort();
        let _ = handle.await;
    }

    #[tokio::test]
    async fn supported_upstream_summary_holds_when_environment_is_missing() {
        let summary = build_supported_upstream_summary(&ResolvedConfig {
            format: OutputFormat::Json,
            summary_path: default_summary_path(),
            base_url: None,
            api_token: None,
            bootstrap_subject: None,
            webhook_signature: None,
            source_version_override: None,
            request_timeout_ms: 500,
            max_snapshot_age_seconds: 300,
            expected_account_id: None,
            webhook_event_type: "subscription.updated".to_owned(),
        })
        .await;

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.evidence_state, "incomplete");
        assert_eq!(summary.gate_state_reason, "missing_required_inputs");
        assert_eq!(summary.supported_upstream_environment_present, false);
        assert_eq!(summary.supported_upstream_compatibility_passed, None);
        assert_eq!(summary.missing_required_input_count, 4);
    }

    #[tokio::test]
    async fn supported_upstream_summary_fails_closed_on_unsupported_version() {
        let (base_url, handle) = spawn_test_upstream(supported_snapshot("2.6.9")).await;
        let summary = build_supported_upstream_summary(&test_config(
            Some(base_url),
            Some("rw-token".to_owned()),
        ))
        .await;

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state_reason, "summary_contract_invalid");
        assert_eq!(summary.upstream_state, "unsupported_version");
        assert_eq!(summary.unsupported_upstream_version_detected, true);
        assert_eq!(summary.supported_upstream_version_passed, Some(false));
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|reason| reason.contains("supported_upstream_version_unsupported"))
        );

        handle.abort();
        let _ = handle.await;
    }

    #[tokio::test]
    async fn supported_upstream_summary_marks_auth_failures_unready() {
        let (base_url, handle) = spawn_test_upstream(supported_snapshot("2.7.4")).await;
        let summary = build_supported_upstream_summary(&test_config(
            Some(base_url),
            Some("wrong-token".to_owned()),
        ))
        .await;

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state_reason, "required_inputs_unready");
        assert_eq!(summary.upstream_state, "unauthorized");
        assert!(summary.upstream_auth_failure_detected);
        assert_eq!(summary.bootstrap_subject_resolved, Some(false));

        handle.abort();
        let _ = handle.await;
    }
}
