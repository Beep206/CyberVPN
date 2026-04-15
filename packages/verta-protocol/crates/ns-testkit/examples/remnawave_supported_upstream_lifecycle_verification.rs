use anyhow::Context;
use axum::Router;
use ed25519_dalek::pkcs8::EncodePrivateKey;
use ns_auth::SessionTokenSigner;
use ns_bridge_api::{
    BridgeErrorCode, BridgeErrorEnvelope, BridgeHttpBudgets, BridgeHttpServiceState,
    DeviceRegisterResponse, TokenExchangeRequest, build_bridge_router,
};
use ns_bridge_domain::{BridgeDomain, BridgeManifestContext, BridgeManifestTemplate};
use ns_manifest::{ManifestDocument, ManifestSigner};
use ns_remnawave_adapter::{
    AccountLifecycle, AccountSnapshot, AdapterError, BootstrapSubject, HttpRemnawaveAdapter,
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
use std::time::Duration as StdDuration;
use time::{Duration, OffsetDateTime};
use tokio::net::TcpListener;

const LIFECYCLE_VERIFICATION_SCHEMA: &str = "supported_upstream_lifecycle_operator_verdict";
const LIFECYCLE_VERIFICATION_SCHEMA_VERSION: u8 = 1;
const LIFECYCLE_VERDICT_FAMILY: &str = "supported_upstream_lifecycle_verification";
const LIFECYCLE_DECISION_SCOPE: &str = "supported_upstream_lifecycle";
const LIFECYCLE_DECISION_LABEL: &str = "remnawave_supported_upstream_lifecycle_verification";
const LIFECYCLE_PROFILE: &str = "supported_upstream_lifecycle_verification";
const LIFECYCLE_SUMMARY_VERSION: u8 = 1;

const SUPPORTED_UPSTREAM_VERSION_FLOOR: SimpleVersion = SimpleVersion::new(2, 7, 0);
const SUPPORTED_UPSTREAM_VERSION_PREFERRED: SimpleVersion = SimpleVersion::new(2, 7, 4);

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum OutputFormat {
    Text,
    Json,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum LifecycleExpectation {
    Disabled,
    Revoked,
    Expired,
    Limited,
}

impl LifecycleExpectation {
    fn parse(value: &str) -> Option<Self> {
        match value.trim().to_ascii_lowercase().as_str() {
            "disabled" => Some(Self::Disabled),
            "revoked" => Some(Self::Revoked),
            "expired" => Some(Self::Expired),
            "limited" => Some(Self::Limited),
            _ => None,
        }
    }

    fn render(self) -> &'static str {
        match self {
            Self::Disabled => "disabled",
            Self::Revoked => "revoked",
            Self::Expired => "expired",
            Self::Limited => "limited",
        }
    }

    fn lifecycle(self) -> AccountLifecycle {
        match self {
            Self::Disabled => AccountLifecycle::Disabled,
            Self::Revoked => AccountLifecycle::Revoked,
            Self::Expired => AccountLifecycle::Expired,
            Self::Limited => AccountLifecycle::Limited,
        }
    }

    fn webhook_event_type(self) -> &'static str {
        match self {
            Self::Disabled => "user.disabled",
            Self::Revoked => "user.revoked",
            Self::Expired => "user.expired",
            Self::Limited => "user.limited",
        }
    }

    fn bridge_error_code(self) -> BridgeErrorCode {
        match self {
            Self::Disabled => BridgeErrorCode::AccountDisabled,
            Self::Revoked => BridgeErrorCode::AccountRevoked,
            Self::Expired => BridgeErrorCode::AccountExpired,
            Self::Limited => BridgeErrorCode::AccountLimited,
        }
    }
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
struct LifecycleArgs {
    format: Option<OutputFormat>,
    summary_path: Option<PathBuf>,
    base_url: Option<String>,
    api_token: Option<String>,
    bootstrap_subject: Option<String>,
    webhook_signature: Option<String>,
    source_version_override: Option<String>,
    expected_account_id: Option<String>,
    expected_lifecycle: Option<String>,
    webhook_event_type: Option<String>,
    request_timeout_ms: Option<u64>,
    max_snapshot_age_seconds: Option<i64>,
    max_reconcile_lag_seconds: Option<i64>,
    lifecycle_wait_timeout_seconds: Option<u64>,
    poll_interval_ms: Option<u64>,
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
    expected_account_id: Option<String>,
    expected_lifecycle: LifecycleExpectation,
    webhook_event_type: String,
    request_timeout_ms: u64,
    max_snapshot_age_seconds: i64,
    max_reconcile_lag_seconds: i64,
    lifecycle_wait_timeout_seconds: u64,
    poll_interval_ms: u64,
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
    bootstrap_subject_resolved: Option<bool>,
    initial_snapshot_fresh: Option<bool>,
    initial_account_id_expected_match: Option<bool>,
    initial_lifecycle_active_passed: Option<bool>,
    active_bridge_manifest_bootstrap_passed: Option<bool>,
    active_bridge_device_register_passed: Option<bool>,
    active_bridge_token_exchange_passed: Option<bool>,
    active_bridge_manifest_refresh_passed: Option<bool>,
    lifecycle_transition_observed: Option<bool>,
    lifecycle_expected_state_passed: Option<bool>,
    lifecycle_policy_epoch_advanced: Option<bool>,
    lifecycle_snapshot_fresh: Option<bool>,
    reconcile_lag_within_target: Option<bool>,
    lifecycle_bridge_manifest_bootstrap_denied: Option<bool>,
    lifecycle_bridge_manifest_refresh_denied: Option<bool>,
    lifecycle_bridge_token_exchange_denied: Option<bool>,
    lifecycle_denial_code_passed: Option<bool>,
    webhook_signature_negative_rejection_passed: Option<bool>,
    webhook_positive_delivery_passed: Option<bool>,
    webhook_duplicate_rejection_passed: Option<bool>,
    webhook_reconcile_hint_passed: Option<bool>,
    response_shape_contract_passed: Option<bool>,
    supported_upstream_lifecycle_passed: Option<bool>,
    partially_degraded_upstream: bool,
    unsupported_upstream_version_detected: bool,
    upstream_auth_failure_detected: bool,
    upstream_timeout_detected: bool,
    upstream_unavailable_detected: bool,
    upstream_stale_detected: bool,
    upstream_drift_detected: bool,
    lifecycle_drift_detected: bool,
    reconcile_lag_detected: bool,
    replay_sensitive_inconsistency_detected: bool,
    webhook_signature_failure_detected: bool,
    incompatible_contract_detected: bool,
}

#[derive(Debug, Serialize)]
struct SupportedUpstreamLifecycleSummary {
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
    supported_upstream_bootstrap_subject: Option<String>,
    supported_upstream_expected_account_id: Option<String>,
    supported_upstream_expected_lifecycle: &'static str,
    supported_upstream_version_floor: String,
    supported_upstream_version_preferred: String,
    upstream_source_version: Option<String>,
    upstream_state: &'static str,
    bootstrap_subject_resolved: Option<bool>,
    initial_snapshot_fresh: Option<bool>,
    initial_account_id_expected_match: Option<bool>,
    initial_lifecycle_active_passed: Option<bool>,
    active_bridge_manifest_bootstrap_passed: Option<bool>,
    active_bridge_device_register_passed: Option<bool>,
    active_bridge_token_exchange_passed: Option<bool>,
    active_bridge_manifest_refresh_passed: Option<bool>,
    lifecycle_transition_observed: Option<bool>,
    lifecycle_expected_state_passed: Option<bool>,
    lifecycle_policy_epoch_advanced: Option<bool>,
    lifecycle_snapshot_fresh: Option<bool>,
    reconcile_lag_within_target: Option<bool>,
    lifecycle_bridge_manifest_bootstrap_denied: Option<bool>,
    lifecycle_bridge_manifest_refresh_denied: Option<bool>,
    lifecycle_bridge_token_exchange_denied: Option<bool>,
    lifecycle_denial_code_passed: Option<bool>,
    webhook_signature_negative_rejection_passed: Option<bool>,
    webhook_positive_delivery_passed: Option<bool>,
    webhook_duplicate_rejection_passed: Option<bool>,
    webhook_reconcile_hint_passed: Option<bool>,
    response_shape_contract_passed: Option<bool>,
    supported_upstream_lifecycle_passed: Option<bool>,
    partially_degraded_upstream: bool,
    unsupported_upstream_version_detected: bool,
    upstream_auth_failure_detected: bool,
    upstream_timeout_detected: bool,
    upstream_unavailable_detected: bool,
    upstream_stale_detected: bool,
    upstream_drift_detected: bool,
    lifecycle_drift_detected: bool,
    reconcile_lag_detected: bool,
    replay_sensitive_inconsistency_detected: bool,
    webhook_signature_failure_detected: bool,
    incompatible_contract_detected: bool,
    blocking_reasons: Vec<String>,
    blocking_reason_keys: Vec<String>,
    blocking_reason_families: Vec<String>,
}

#[derive(Debug)]
struct ActiveBridgeFlowEvidence {
    refresh_credential: String,
    manifest_id: String,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum StageFailureKind {
    AuthFailure,
    Timeout,
    Unavailable,
    Drift,
    Lagged,
    ReplaySensitive,
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
    let config = resolve_config(args)?;
    let summary = build_supported_upstream_lifecycle_summary(&config).await;

    if let Some(parent) = config.summary_path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(
        &config.summary_path,
        serde_json::to_vec_pretty(&summary).context("failed to serialize lifecycle summary")?,
    )?;

    match config.format {
        OutputFormat::Text => print_text_summary(&summary, &config.summary_path),
        OutputFormat::Json => println!("{}", serde_json::to_string_pretty(&summary)?),
    }

    Ok(())
}

async fn build_supported_upstream_lifecycle_summary(
    config: &ResolvedConfig,
) -> SupportedUpstreamLifecycleSummary {
    let required_inputs = lifecycle_required_inputs();
    let considered_inputs = required_inputs.clone();
    let mut state = SummaryState::default();
    collect_missing_required_inputs(config, &mut state);
    if state.missing_required_inputs.is_empty() {
        state.supported_upstream_environment_present = true;
        execute_lifecycle_checks(config, &mut state).await;
    }
    finalize_summary(config, required_inputs, considered_inputs, state)
}

fn lifecycle_required_inputs() -> Vec<String> {
    vec![
        "supported_upstream_base_url".to_owned(),
        "supported_upstream_api_token".to_owned(),
        "supported_upstream_bootstrap_subject".to_owned(),
        "supported_upstream_webhook_signature".to_owned(),
        "supported_upstream_expected_account_id".to_owned(),
    ]
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
    if config.expected_account_id.is_none() {
        state
            .missing_required_inputs
            .push("supported_upstream_expected_account_id".to_owned());
    }
}

async fn execute_lifecycle_checks(config: &ResolvedConfig, state: &mut SummaryState) {
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
    let expected_account_id = config
        .expected_account_id
        .as_deref()
        .expect("checked required input");

    let adapter_config =
        match HttpRemnawaveAdapterConfig::new(base_url, api_token, config.request_timeout_ms) {
            Ok(value) => value,
            Err(error) => {
                state.response_shape_contract_passed = Some(false);
                state.supported_upstream_lifecycle_passed = Some(false);
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

    let initial_snapshot = match adapter.resolve_bootstrap_subject(&subject).await {
        Ok(snapshot) => {
            let snapshot =
                apply_source_version_override(snapshot, config.source_version_override.as_deref());
            state.bootstrap_subject_resolved = Some(true);
            state.response_shape_contract_passed = Some(true);
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

    state.upstream_source_version = initial_snapshot.source_version.clone();
    match validate_supported_version(&initial_snapshot) {
        Ok(_) => {}
        Err(reason) => {
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

    if initial_snapshot.account_id == expected_account_id {
        state.initial_account_id_expected_match = Some(true);
    } else {
        state.initial_account_id_expected_match = Some(false);
        state.incompatible_contract_detected = true;
        mark_contract_invalid(
            state,
            "supported_upstream_account_id_mismatch",
            "supported_upstream_account_id_mismatch",
            "supported_upstream_contract",
        );
    }

    if initial_snapshot.lifecycle == AccountLifecycle::Active {
        state.initial_lifecycle_active_passed = Some(true);
    } else {
        state.initial_lifecycle_active_passed = Some(false);
        state.lifecycle_drift_detected = true;
        mark_contract_invalid(
            state,
            &format!(
                "supported_upstream_lifecycle_not_active:{}",
                render_account_lifecycle(initial_snapshot.lifecycle)
            ),
            "supported_upstream_lifecycle_not_active",
            "supported_upstream_lifecycle",
        );
    }

    if snapshot_is_fresh(&initial_snapshot, config.max_snapshot_age_seconds) {
        state.initial_snapshot_fresh = Some(true);
    } else {
        state.initial_snapshot_fresh = Some(false);
        state.upstream_stale_detected = true;
        mark_degradation(
            state,
            "supported_upstream_initial_snapshot_stale",
            "supported_upstream_initial_snapshot_stale",
            "supported_upstream_freshness",
        );
    }

    let store_path = temporary_sqlite_store_path("supported-upstream-lifecycle");
    let router = match build_supported_upstream_router(
        adapter.clone(),
        store_path.as_path(),
        webhook_signature,
    ) {
        Ok(router) => router,
        Err(error) => {
            apply_stage_failure(
                state,
                StageFailure {
                    stage: "bridge_router_build",
                    kind: StageFailureKind::IncompatibleContract,
                    detail: error.to_string(),
                },
            );
            cleanup_sqlite_store_path(store_path.as_path());
            return;
        }
    };
    let (public_base_url, public_handle) = match spawn_router(router).await {
        Ok(value) => value,
        Err(error) => {
            apply_stage_failure(
                state,
                StageFailure {
                    stage: "bridge_router_spawn",
                    kind: StageFailureKind::Unavailable,
                    detail: error.to_string(),
                },
            );
            cleanup_sqlite_store_path(store_path.as_path());
            return;
        }
    };

    let active_flow =
        match exercise_active_bridge_flow(&public_base_url, bootstrap_subject, expected_account_id)
            .await
        {
            Ok(flow) => {
                state.active_bridge_manifest_bootstrap_passed = Some(true);
                state.active_bridge_device_register_passed = Some(true);
                state.active_bridge_token_exchange_passed = Some(true);
                state.active_bridge_manifest_refresh_passed = Some(true);
                flow
            }
            Err(failure) => {
                apply_stage_failure(state, failure);
                public_handle.abort();
                let _ = public_handle.await;
                cleanup_sqlite_store_path(store_path.as_path());
                return;
            }
        };

    eprintln!(
        "Verta lifecycle lane primed active flow for account {}; waiting up to {} seconds for upstream lifecycle to become {}.",
        expected_account_id,
        config.lifecycle_wait_timeout_seconds,
        config.expected_lifecycle.render()
    );

    let transitioned_snapshot =
        match wait_for_expected_lifecycle(&adapter, expected_account_id, &initial_snapshot, config)
            .await
        {
            Ok(snapshot) => snapshot,
            Err(failure) => {
                apply_stage_failure(state, failure);
                public_handle.abort();
                let _ = public_handle.await;
                cleanup_sqlite_store_path(store_path.as_path());
                return;
            }
        };

    state.lifecycle_transition_observed = Some(true);
    state.lifecycle_expected_state_passed = Some(true);
    state.lifecycle_policy_epoch_advanced = Some(
        transitioned_snapshot.verta_access.policy_epoch
            > initial_snapshot.verta_access.policy_epoch,
    );
    if !state.lifecycle_policy_epoch_advanced.unwrap_or(false) {
        state.partially_degraded_upstream = true;
        mark_degradation(
            state,
            "supported_upstream_policy_epoch_not_advanced",
            "supported_upstream_policy_epoch_not_advanced",
            "supported_upstream_lifecycle",
        );
    }

    if snapshot_is_fresh(&transitioned_snapshot, config.max_snapshot_age_seconds) {
        state.lifecycle_snapshot_fresh = Some(true);
    } else {
        state.lifecycle_snapshot_fresh = Some(false);
        state.upstream_stale_detected = true;
        mark_degradation(
            state,
            "supported_upstream_transition_snapshot_stale",
            "supported_upstream_transition_snapshot_stale",
            "supported_upstream_freshness",
        );
    }

    if snapshot_is_fresh(&transitioned_snapshot, config.max_reconcile_lag_seconds) {
        state.reconcile_lag_within_target = Some(true);
    } else {
        state.reconcile_lag_within_target = Some(false);
        state.reconcile_lag_detected = true;
        mark_degradation(
            state,
            "supported_upstream_reconcile_lag_exceeded",
            "supported_upstream_reconcile_lag_exceeded",
            "supported_upstream_reconciliation",
        );
    }

    match run_webhook_lifecycle_checks(
        &public_base_url,
        webhook_signature,
        expected_account_id,
        config,
    )
    .await
    {
        Ok(()) => {
            state.webhook_signature_negative_rejection_passed = Some(true);
            state.webhook_positive_delivery_passed = Some(true);
            state.webhook_duplicate_rejection_passed = Some(true);
            state.webhook_reconcile_hint_passed = Some(true);
        }
        Err(failure) => apply_stage_failure(state, failure),
    }

    match exercise_lifecycle_denial_flow(&public_base_url, bootstrap_subject, &active_flow, config)
        .await
    {
        Ok(()) => {
            state.lifecycle_bridge_manifest_bootstrap_denied = Some(true);
            state.lifecycle_bridge_manifest_refresh_denied = Some(true);
            state.lifecycle_bridge_token_exchange_denied = Some(true);
            state.lifecycle_denial_code_passed = Some(true);
        }
        Err(failure) => apply_stage_failure(state, failure),
    }

    public_handle.abort();
    let _ = public_handle.await;
    cleanup_sqlite_store_path(store_path.as_path());

    if state.supported_upstream_lifecycle_passed.is_none() {
        state.supported_upstream_lifecycle_passed = Some(
            state.bootstrap_subject_resolved == Some(true)
                && state.initial_snapshot_fresh == Some(true)
                && state.initial_account_id_expected_match == Some(true)
                && state.initial_lifecycle_active_passed == Some(true)
                && state.active_bridge_manifest_bootstrap_passed == Some(true)
                && state.active_bridge_device_register_passed == Some(true)
                && state.active_bridge_token_exchange_passed == Some(true)
                && state.active_bridge_manifest_refresh_passed == Some(true)
                && state.lifecycle_transition_observed == Some(true)
                && state.lifecycle_expected_state_passed == Some(true)
                && state.lifecycle_snapshot_fresh == Some(true)
                && state.reconcile_lag_within_target == Some(true)
                && state.lifecycle_bridge_manifest_bootstrap_denied == Some(true)
                && state.lifecycle_bridge_manifest_refresh_denied == Some(true)
                && state.lifecycle_bridge_token_exchange_denied == Some(true)
                && state.lifecycle_denial_code_passed == Some(true)
                && state.webhook_signature_negative_rejection_passed == Some(true)
                && state.webhook_positive_delivery_passed == Some(true)
                && state.webhook_duplicate_rejection_passed == Some(true)
                && state.webhook_reconcile_hint_passed == Some(true)
                && state.response_shape_contract_passed == Some(true)
                && state.summary_contract_invalid_count == 0
                && state.required_input_unready_count == 0
                && state.degradation_hold_count == 0,
        );
    }
}

async fn exercise_active_bridge_flow(
    base_url: &str,
    bootstrap_subject: &str,
    expected_account_id: &str,
) -> Result<ActiveBridgeFlowEvidence, StageFailure> {
    let client = reqwest::Client::new();
    let manifest_response = client
        .get(format!(
            "{base_url}/v0/manifest?subscription_token={bootstrap_subject}"
        ))
        .send()
        .await
        .map_err(|error| classify_request_error("bridge_manifest_bootstrap_active", error))?;
    if manifest_response.status() != reqwest::StatusCode::OK {
        return Err(StageFailure {
            stage: "bridge_manifest_bootstrap_active",
            kind: classify_status_failure(manifest_response.status()),
            detail: format!("expected 200, got {}", manifest_response.status()),
        });
    }
    let manifest: ManifestDocument =
        manifest_response
            .json()
            .await
            .map_err(|error| StageFailure {
                stage: "bridge_manifest_bootstrap_active",
                kind: StageFailureKind::Drift,
                detail: error.to_string(),
            })?;
    let bootstrap_credential = manifest
        .refresh
        .as_ref()
        .map(|refresh| refresh.credential.clone())
        .ok_or_else(|| StageFailure {
            stage: "bridge_manifest_bootstrap_active",
            kind: StageFailureKind::IncompatibleContract,
            detail: "bootstrap manifest did not include a refresh credential".to_owned(),
        })?;
    if manifest
        .user
        .as_ref()
        .and_then(|user| user.account_id.as_deref())
        != Some(expected_account_id)
    {
        return Err(StageFailure {
            stage: "bridge_manifest_bootstrap_active",
            kind: StageFailureKind::IncompatibleContract,
            detail: "active manifest returned an unexpected account id".to_owned(),
        });
    }

    let register_response = client
        .post(format!("{base_url}/v0/device/register"))
        .bearer_auth(&bootstrap_credential)
        .json(&serde_json::json!({
            "manifest_id": manifest.manifest_id,
            "device_id": "lifecycle-device-1",
            "device_name": "Lifecycle Verification Workstation",
            "platform": "windows",
            "client_version": "0.1.0",
            "install_channel": "stable",
            "requested_capabilities": [1, 2]
        }))
        .send()
        .await
        .map_err(|error| classify_request_error("bridge_device_register_active", error))?;
    if register_response.status() != reqwest::StatusCode::OK {
        return Err(StageFailure {
            stage: "bridge_device_register_active",
            kind: classify_status_failure(register_response.status()),
            detail: format!("expected 200, got {}", register_response.status()),
        });
    }
    let register: DeviceRegisterResponse =
        register_response
            .json()
            .await
            .map_err(|error| StageFailure {
                stage: "bridge_device_register_active",
                kind: StageFailureKind::Drift,
                detail: error.to_string(),
            })?;
    let refresh_credential = register.refresh_credential.ok_or_else(|| StageFailure {
        stage: "bridge_device_register_active",
        kind: StageFailureKind::IncompatibleContract,
        detail: "device register did not issue a refresh credential".to_owned(),
    })?;

    let exchange_response = client
        .post(format!("{base_url}/v0/token/exchange"))
        .json(&TokenExchangeRequest {
            manifest_id: manifest.manifest_id.clone(),
            device_id: "lifecycle-device-1".to_owned(),
            client_version: "0.1.0".to_owned(),
            core_version: 1,
            carrier_profile_id: "carrier-primary".to_owned(),
            requested_capabilities: vec![1, 2],
            refresh_credential: refresh_credential.clone(),
        })
        .send()
        .await
        .map_err(|error| classify_request_error("bridge_token_exchange_active", error))?;
    if exchange_response.status() != reqwest::StatusCode::OK {
        return Err(StageFailure {
            stage: "bridge_token_exchange_active",
            kind: classify_status_failure(exchange_response.status()),
            detail: format!("expected 200, got {}", exchange_response.status()),
        });
    }

    let refresh_manifest = client
        .get(format!("{base_url}/v0/manifest"))
        .bearer_auth(&refresh_credential)
        .send()
        .await
        .map_err(|error| classify_request_error("bridge_manifest_refresh_active", error))?;
    if !matches!(
        refresh_manifest.status(),
        reqwest::StatusCode::OK | reqwest::StatusCode::NOT_MODIFIED
    ) {
        return Err(StageFailure {
            stage: "bridge_manifest_refresh_active",
            kind: classify_status_failure(refresh_manifest.status()),
            detail: format!("expected 200 or 304, got {}", refresh_manifest.status()),
        });
    }

    Ok(ActiveBridgeFlowEvidence {
        refresh_credential,
        manifest_id: manifest.manifest_id,
    })
}

async fn wait_for_expected_lifecycle(
    adapter: &HttpRemnawaveAdapter,
    account_id: &str,
    initial_snapshot: &AccountSnapshot,
    config: &ResolvedConfig,
) -> Result<AccountSnapshot, StageFailure> {
    let deadline =
        std::time::Instant::now() + StdDuration::from_secs(config.lifecycle_wait_timeout_seconds);
    loop {
        let snapshot = adapter
            .fetch_account_snapshot(account_id)
            .await
            .map_err(|error| map_adapter_stage_error("lifecycle_transition_fetch", error))?;
        if snapshot.account_id != account_id {
            return Err(StageFailure {
                stage: "lifecycle_transition_fetch",
                kind: StageFailureKind::IncompatibleContract,
                detail: "transition fetch returned an unexpected account id".to_owned(),
            });
        }
        if snapshot.lifecycle == config.expected_lifecycle.lifecycle() {
            return Ok(snapshot);
        }
        if snapshot.lifecycle != initial_snapshot.lifecycle {
            return Err(StageFailure {
                stage: "lifecycle_transition_fetch",
                kind: StageFailureKind::IncompatibleContract,
                detail: format!(
                    "expected lifecycle {}, observed {}",
                    config.expected_lifecycle.render(),
                    render_account_lifecycle(snapshot.lifecycle)
                ),
            });
        }
        if std::time::Instant::now() >= deadline {
            return Err(StageFailure {
                stage: "lifecycle_transition_wait",
                kind: StageFailureKind::Lagged,
                detail: format!(
                    "timed out waiting for lifecycle {}",
                    config.expected_lifecycle.render()
                ),
            });
        }
        tokio::time::sleep(StdDuration::from_millis(config.poll_interval_ms)).await;
    }
}

async fn run_webhook_lifecycle_checks(
    base_url: &str,
    webhook_signature: &str,
    account_id: &str,
    config: &ResolvedConfig,
) -> Result<(), StageFailure> {
    let client = reqwest::Client::new();
    let now = OffsetDateTime::now_utc().unix_timestamp();
    let payload = VerifiedWebhookPayload {
        event_id: format!("evt-lifecycle-{now}"),
        event_type: config.webhook_event_type.clone(),
        account_id: Some(account_id.to_owned()),
        occurred_at_unix: now,
        payload: serde_json::json!({
            "expected_lifecycle": config.expected_lifecycle.render()
        }),
    };
    let negative = client
        .post(format!("{base_url}/internal/remnawave/webhook"))
        .header(
            "x-remnawave-signature",
            format!("{webhook_signature}-invalid"),
        )
        .header("x-remnawave-timestamp", now.to_string())
        .json(&payload)
        .send()
        .await
        .map_err(|error| classify_request_error("webhook_negative_rejection", error))?;
    if negative.status() != reqwest::StatusCode::UNAUTHORIZED {
        return Err(StageFailure {
            stage: "webhook_negative_rejection",
            kind: StageFailureKind::IncompatibleContract,
            detail: format!("expected 401, got {}", negative.status()),
        });
    }

    let positive = client
        .post(format!("{base_url}/internal/remnawave/webhook"))
        .header("x-remnawave-signature", webhook_signature)
        .header("x-remnawave-timestamp", now.to_string())
        .json(&payload)
        .send()
        .await
        .map_err(|error| classify_request_error("webhook_positive_acceptance", error))?;
    if positive.status() != reqwest::StatusCode::OK {
        return Err(StageFailure {
            stage: "webhook_positive_acceptance",
            kind: classify_status_failure(positive.status()),
            detail: format!("expected 200, got {}", positive.status()),
        });
    }
    let body: serde_json::Value = positive.json().await.map_err(|error| StageFailure {
        stage: "webhook_positive_acceptance",
        kind: StageFailureKind::Drift,
        detail: error.to_string(),
    })?;
    let expected_hint = format!(
        "reconcile-account:{account_id}:{}",
        config.webhook_event_type
    );
    if body.get("effect").and_then(|value| value.as_str()) != Some(expected_hint.as_str()) {
        return Err(StageFailure {
            stage: "webhook_reconcile_hint",
            kind: StageFailureKind::IncompatibleContract,
            detail: format!("expected effect hint {expected_hint}, got {body}"),
        });
    }

    let duplicate = client
        .post(format!("{base_url}/internal/remnawave/webhook"))
        .header("x-remnawave-signature", webhook_signature)
        .header("x-remnawave-timestamp", now.to_string())
        .json(&payload)
        .send()
        .await
        .map_err(|error| classify_request_error("webhook_duplicate_rejection", error))?;
    if duplicate.status() != reqwest::StatusCode::CONFLICT {
        return Err(StageFailure {
            stage: "webhook_duplicate_rejection",
            kind: StageFailureKind::ReplaySensitive,
            detail: format!("expected 409, got {}", duplicate.status()),
        });
    }

    Ok(())
}

async fn exercise_lifecycle_denial_flow(
    base_url: &str,
    bootstrap_subject: &str,
    active_flow: &ActiveBridgeFlowEvidence,
    config: &ResolvedConfig,
) -> Result<(), StageFailure> {
    let client = reqwest::Client::new();
    let expected_code = config.expected_lifecycle.bridge_error_code();

    let bootstrap = client
        .get(format!(
            "{base_url}/v0/manifest?subscription_token={bootstrap_subject}"
        ))
        .send()
        .await
        .map_err(|error| classify_request_error("lifecycle_manifest_bootstrap_denied", error))?;
    verify_denied_bridge_response(
        "lifecycle_manifest_bootstrap_denied",
        bootstrap,
        expected_code,
    )
    .await?;

    let refresh = client
        .get(format!("{base_url}/v0/manifest"))
        .bearer_auth(&active_flow.refresh_credential)
        .send()
        .await
        .map_err(|error| classify_request_error("lifecycle_manifest_refresh_denied", error))?;
    verify_denied_bridge_response("lifecycle_manifest_refresh_denied", refresh, expected_code)
        .await?;

    let token_exchange = client
        .post(format!("{base_url}/v0/token/exchange"))
        .json(&TokenExchangeRequest {
            manifest_id: active_flow.manifest_id.clone(),
            device_id: "lifecycle-device-1".to_owned(),
            client_version: "0.1.0".to_owned(),
            core_version: 1,
            carrier_profile_id: "carrier-primary".to_owned(),
            requested_capabilities: vec![1, 2],
            refresh_credential: active_flow.refresh_credential.clone(),
        })
        .send()
        .await
        .map_err(|error| classify_request_error("lifecycle_token_exchange_denied", error))?;
    verify_denied_bridge_response(
        "lifecycle_token_exchange_denied",
        token_exchange,
        expected_code,
    )
    .await?;

    Ok(())
}

async fn verify_denied_bridge_response(
    stage: &'static str,
    response: reqwest::Response,
    expected_code: BridgeErrorCode,
) -> Result<(), StageFailure> {
    if response.status() != reqwest::StatusCode::FORBIDDEN {
        return Err(StageFailure {
            stage,
            kind: classify_status_failure(response.status()),
            detail: format!("expected 403, got {}", response.status()),
        });
    }
    let envelope: BridgeErrorEnvelope = response.json().await.map_err(|error| StageFailure {
        stage,
        kind: StageFailureKind::Drift,
        detail: error.to_string(),
    })?;
    if envelope.error.code != expected_code {
        return Err(StageFailure {
            stage,
            kind: StageFailureKind::IncompatibleContract,
            detail: format!(
                "expected bridge error {:?}, got {:?}",
                expected_code, envelope.error.code
            ),
        });
    }
    Ok(())
}

fn finalize_summary(
    config: &ResolvedConfig,
    required_inputs: Vec<String>,
    considered_inputs: Vec<String>,
    mut state: SummaryState,
) -> SupportedUpstreamLifecycleSummary {
    let missing_required_input_count = state.missing_required_inputs.len();
    let blocking_reason_count = state.blocking_reasons.len();
    let required_input_count = required_inputs.len();
    let required_input_present_count =
        required_input_count.saturating_sub(missing_required_input_count);
    let required_input_failed_count = state.summary_contract_invalid_count
        + state.required_input_unready_count
        + state.degradation_hold_count;
    let required_input_passed_count =
        required_input_present_count.saturating_sub(required_input_failed_count);
    let compatibility_passed = state.supported_upstream_lifecycle_passed;
    let upstream_state = derive_upstream_state(&state, compatibility_passed);
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
    let evidence_state = if compatibility_passed == Some(true) {
        "verified"
    } else if missing_required_input_count > 0 {
        "incomplete"
    } else {
        "partial"
    };
    let mut blocking_reason_keys = state
        .blocking_reason_key_counts
        .keys()
        .cloned()
        .collect::<Vec<_>>();
    let mut blocking_reason_families = state
        .blocking_reason_family_counts
        .keys()
        .cloned()
        .collect::<Vec<_>>();
    blocking_reason_keys.sort();
    blocking_reason_families.sort();
    state.blocking_reasons.sort();

    SupportedUpstreamLifecycleSummary {
        summary_version: LIFECYCLE_SUMMARY_VERSION,
        verification_schema: LIFECYCLE_VERIFICATION_SCHEMA,
        verification_schema_version: LIFECYCLE_VERIFICATION_SCHEMA_VERSION,
        verdict_family: LIFECYCLE_VERDICT_FAMILY,
        decision_scope: LIFECYCLE_DECISION_SCOPE,
        decision_label: LIFECYCLE_DECISION_LABEL,
        profile: LIFECYCLE_PROFILE,
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
        supported_upstream_bootstrap_subject: config.bootstrap_subject.clone(),
        supported_upstream_expected_account_id: config.expected_account_id.clone(),
        supported_upstream_expected_lifecycle: config.expected_lifecycle.render(),
        supported_upstream_version_floor: SUPPORTED_UPSTREAM_VERSION_FLOOR.render(),
        supported_upstream_version_preferred: SUPPORTED_UPSTREAM_VERSION_PREFERRED.render(),
        upstream_source_version: state.upstream_source_version,
        upstream_state,
        bootstrap_subject_resolved: state.bootstrap_subject_resolved,
        initial_snapshot_fresh: state.initial_snapshot_fresh,
        initial_account_id_expected_match: state.initial_account_id_expected_match,
        initial_lifecycle_active_passed: state.initial_lifecycle_active_passed,
        active_bridge_manifest_bootstrap_passed: state.active_bridge_manifest_bootstrap_passed,
        active_bridge_device_register_passed: state.active_bridge_device_register_passed,
        active_bridge_token_exchange_passed: state.active_bridge_token_exchange_passed,
        active_bridge_manifest_refresh_passed: state.active_bridge_manifest_refresh_passed,
        lifecycle_transition_observed: state.lifecycle_transition_observed,
        lifecycle_expected_state_passed: state.lifecycle_expected_state_passed,
        lifecycle_policy_epoch_advanced: state.lifecycle_policy_epoch_advanced,
        lifecycle_snapshot_fresh: state.lifecycle_snapshot_fresh,
        reconcile_lag_within_target: state.reconcile_lag_within_target,
        lifecycle_bridge_manifest_bootstrap_denied: state
            .lifecycle_bridge_manifest_bootstrap_denied,
        lifecycle_bridge_manifest_refresh_denied: state.lifecycle_bridge_manifest_refresh_denied,
        lifecycle_bridge_token_exchange_denied: state.lifecycle_bridge_token_exchange_denied,
        lifecycle_denial_code_passed: state.lifecycle_denial_code_passed,
        webhook_signature_negative_rejection_passed: state
            .webhook_signature_negative_rejection_passed,
        webhook_positive_delivery_passed: state.webhook_positive_delivery_passed,
        webhook_duplicate_rejection_passed: state.webhook_duplicate_rejection_passed,
        webhook_reconcile_hint_passed: state.webhook_reconcile_hint_passed,
        response_shape_contract_passed: state.response_shape_contract_passed,
        supported_upstream_lifecycle_passed: compatibility_passed,
        partially_degraded_upstream: state.partially_degraded_upstream,
        unsupported_upstream_version_detected: state.unsupported_upstream_version_detected,
        upstream_auth_failure_detected: state.upstream_auth_failure_detected,
        upstream_timeout_detected: state.upstream_timeout_detected,
        upstream_unavailable_detected: state.upstream_unavailable_detected,
        upstream_stale_detected: state.upstream_stale_detected,
        upstream_drift_detected: state.upstream_drift_detected,
        lifecycle_drift_detected: state.lifecycle_drift_detected,
        reconcile_lag_detected: state.reconcile_lag_detected,
        replay_sensitive_inconsistency_detected: state.replay_sensitive_inconsistency_detected,
        webhook_signature_failure_detected: state.webhook_signature_failure_detected,
        incompatible_contract_detected: state.incompatible_contract_detected,
        blocking_reasons: state.blocking_reasons,
        blocking_reason_keys,
        blocking_reason_families,
    }
}

fn derive_upstream_state(state: &SummaryState, lifecycle_passed: Option<bool>) -> &'static str {
    if !state.supported_upstream_environment_present {
        "missing_environment"
    } else if state.unsupported_upstream_version_detected {
        "unsupported_version"
    } else if state.upstream_drift_detected {
        "response_shape_drift"
    } else if state.lifecycle_drift_detected {
        "lifecycle_drift"
    } else if state.replay_sensitive_inconsistency_detected {
        "replay_inconsistency"
    } else if state.webhook_signature_failure_detected {
        "webhook_signature_failure"
    } else if state.upstream_auth_failure_detected {
        "unauthorized"
    } else if state.upstream_timeout_detected {
        "timeout"
    } else if state.upstream_unavailable_detected {
        "unavailable"
    } else if state.reconcile_lag_detected {
        "reconcile_lag"
    } else if state.upstream_stale_detected {
        "stale"
    } else if state.partially_degraded_upstream {
        "partial_degradation"
    } else if lifecycle_passed == Some(true) {
        "lifecycle_verified"
    } else {
        "unverified"
    }
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

fn snapshot_is_fresh(snapshot: &AccountSnapshot, max_age_seconds: i64) -> bool {
    let now = OffsetDateTime::now_utc().unix_timestamp();
    let age = now.saturating_sub(snapshot.observed_at_unix);
    age <= max_age_seconds.max(0)
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

fn map_adapter_stage_error(stage: &'static str, error: AdapterError) -> StageFailure {
    match error {
        AdapterError::Unauthorized => StageFailure {
            stage,
            kind: StageFailureKind::AuthFailure,
            detail: "unauthorized".to_owned(),
        },
        AdapterError::Timeout => StageFailure {
            stage,
            kind: StageFailureKind::Timeout,
            detail: "timeout".to_owned(),
        },
        AdapterError::Unavailable | AdapterError::RateLimited | AdapterError::NotFound => {
            StageFailure {
                stage,
                kind: StageFailureKind::Unavailable,
                detail: error.to_string(),
            }
        }
        AdapterError::SchemaDrift => StageFailure {
            stage,
            kind: StageFailureKind::Drift,
            detail: "schema_drift".to_owned(),
        },
        AdapterError::InvalidData(_) | AdapterError::Conflict => StageFailure {
            stage,
            kind: StageFailureKind::IncompatibleContract,
            detail: error.to_string(),
        },
    }
}

fn apply_stage_failure(state: &mut SummaryState, failure: StageFailure) {
    match failure.stage {
        "bridge_router_build" | "bridge_router_spawn" => {
            state.active_bridge_manifest_bootstrap_passed = Some(false);
            state.active_bridge_device_register_passed = Some(false);
            state.active_bridge_token_exchange_passed = Some(false);
            state.active_bridge_manifest_refresh_passed = Some(false);
            state.lifecycle_bridge_manifest_bootstrap_denied = Some(false);
            state.lifecycle_bridge_manifest_refresh_denied = Some(false);
            state.lifecycle_bridge_token_exchange_denied = Some(false);
        }
        "bridge_manifest_bootstrap_active" => {
            state.active_bridge_manifest_bootstrap_passed = Some(false)
        }
        "bridge_device_register_active" => state.active_bridge_device_register_passed = Some(false),
        "bridge_token_exchange_active" => state.active_bridge_token_exchange_passed = Some(false),
        "bridge_manifest_refresh_active" => {
            state.active_bridge_manifest_refresh_passed = Some(false)
        }
        "lifecycle_transition_fetch" | "lifecycle_transition_wait" => {
            state.lifecycle_transition_observed = Some(false);
            state.lifecycle_expected_state_passed = Some(false);
        }
        "lifecycle_manifest_bootstrap_denied" => {
            state.lifecycle_bridge_manifest_bootstrap_denied = Some(false);
            state.lifecycle_denial_code_passed = Some(false);
        }
        "lifecycle_manifest_refresh_denied" => {
            state.lifecycle_bridge_manifest_refresh_denied = Some(false);
            state.lifecycle_denial_code_passed = Some(false);
        }
        "lifecycle_token_exchange_denied" => {
            state.lifecycle_bridge_token_exchange_denied = Some(false);
            state.lifecycle_denial_code_passed = Some(false);
        }
        "webhook_negative_rejection" => {
            state.webhook_signature_negative_rejection_passed = Some(false)
        }
        "webhook_positive_acceptance" => state.webhook_positive_delivery_passed = Some(false),
        "webhook_duplicate_rejection" => state.webhook_duplicate_rejection_passed = Some(false),
        "webhook_reconcile_hint" => state.webhook_reconcile_hint_passed = Some(false),
        _ => {}
    }

    match failure.kind {
        StageFailureKind::AuthFailure => {
            if failure.stage.starts_with("webhook_") {
                state.webhook_signature_failure_detected = true;
            } else {
                state.upstream_auth_failure_detected = true;
            }
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
                "required_input_unready",
                "supported_upstream_readiness",
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
        StageFailureKind::Lagged => {
            state.reconcile_lag_detected = true;
            mark_degradation(
                state,
                &format!("{}:{}", failure.stage, failure.detail),
                "reconcile_lag",
                "supported_upstream_reconciliation",
            );
        }
        StageFailureKind::ReplaySensitive => {
            state.replay_sensitive_inconsistency_detected = true;
            mark_contract_invalid(
                state,
                &format!("{}:{}", failure.stage, failure.detail),
                "replay_sensitive_inconsistency",
                "supported_upstream_reconciliation",
            );
        }
        StageFailureKind::IncompatibleContract => {
            if failure.stage.starts_with("lifecycle_") {
                state.lifecycle_drift_detected = true;
            } else if failure.stage.starts_with("webhook_") {
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
    let failure = map_adapter_stage_error(stage, error);
    apply_stage_failure(state, failure);
}

fn mark_unready(state: &mut SummaryState, code: &str, reason_key: &str, family: &'static str) {
    state.required_input_unready_count += 1;
    state.supported_upstream_lifecycle_passed = Some(false);
    push_reason(state, code, reason_key, family);
}

fn mark_contract_invalid(
    state: &mut SummaryState,
    code: &str,
    reason_key: &str,
    family: &'static str,
) {
    state.summary_contract_invalid_count += 1;
    state.supported_upstream_lifecycle_passed = Some(false);
    push_reason(state, code, reason_key, family);
}

fn mark_degradation(state: &mut SummaryState, code: &str, reason_key: &str, family: &'static str) {
    state.degradation_hold_count += 1;
    state.partially_degraded_upstream = true;
    state.supported_upstream_lifecycle_passed = Some(false);
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

fn render_account_lifecycle(lifecycle: AccountLifecycle) -> &'static str {
    match lifecycle {
        AccountLifecycle::Active => "active",
        AccountLifecycle::Disabled => "disabled",
        AccountLifecycle::Revoked => "revoked",
        AccountLifecycle::Expired => "expired",
        AccountLifecycle::Limited => "limited",
    }
}

fn parse_args<I>(args: I) -> Result<LifecycleArgs, Box<dyn std::error::Error>>
where
    I: IntoIterator<Item = String>,
{
    let mut parsed = LifecycleArgs::default();
    let mut iter = args.into_iter();
    while let Some(argument) = iter.next() {
        match argument.as_str() {
            "--json" => parsed.format = Some(OutputFormat::Json),
            "--text" => parsed.format = Some(OutputFormat::Text),
            "--summary-path" => {
                parsed.summary_path = Some(PathBuf::from(next_arg(&mut iter, "--summary-path")?))
            }
            "--base-url" => parsed.base_url = Some(next_arg(&mut iter, "--base-url")?),
            "--api-token" => parsed.api_token = Some(next_arg(&mut iter, "--api-token")?),
            "--bootstrap-subject" => {
                parsed.bootstrap_subject = Some(next_arg(&mut iter, "--bootstrap-subject")?)
            }
            "--webhook-signature" => {
                parsed.webhook_signature = Some(next_arg(&mut iter, "--webhook-signature")?)
            }
            "--expected-account-id" => {
                parsed.expected_account_id = Some(next_arg(&mut iter, "--expected-account-id")?)
            }
            "--expected-lifecycle" => {
                parsed.expected_lifecycle = Some(next_arg(&mut iter, "--expected-lifecycle")?)
            }
            "--webhook-event-type" => {
                parsed.webhook_event_type = Some(next_arg(&mut iter, "--webhook-event-type")?)
            }
            "--request-timeout-ms" => {
                parsed.request_timeout_ms = Some(
                    next_arg(&mut iter, "--request-timeout-ms")?
                        .parse()
                        .map_err(|_| "--request-timeout-ms must be an integer")?,
                )
            }
            "--max-snapshot-age-seconds" => {
                parsed.max_snapshot_age_seconds = Some(
                    next_arg(&mut iter, "--max-snapshot-age-seconds")?
                        .parse()
                        .map_err(|_| "--max-snapshot-age-seconds must be an integer")?,
                )
            }
            "--max-reconcile-lag-seconds" => {
                parsed.max_reconcile_lag_seconds = Some(
                    next_arg(&mut iter, "--max-reconcile-lag-seconds")?
                        .parse()
                        .map_err(|_| "--max-reconcile-lag-seconds must be an integer")?,
                )
            }
            "--lifecycle-wait-timeout-seconds" => {
                parsed.lifecycle_wait_timeout_seconds = Some(
                    next_arg(&mut iter, "--lifecycle-wait-timeout-seconds")?
                        .parse()
                        .map_err(|_| "--lifecycle-wait-timeout-seconds must be an integer")?,
                )
            }
            "--poll-interval-ms" => {
                parsed.poll_interval_ms = Some(
                    next_arg(&mut iter, "--poll-interval-ms")?
                        .parse()
                        .map_err(|_| "--poll-interval-ms must be an integer")?,
                )
            }
            other => return Err(format!("unsupported argument: {other}").into()),
        }
    }
    Ok(parsed)
}

fn resolve_config(args: LifecycleArgs) -> Result<ResolvedConfig, Box<dyn std::error::Error>> {
    let expected_lifecycle = args
        .expected_lifecycle
        .or_else(|| env::var("VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_LIFECYCLE").ok())
        .unwrap_or_else(|| "disabled".to_owned());
    let expected_lifecycle = LifecycleExpectation::parse(&expected_lifecycle)
        .ok_or("expected lifecycle must be one of disabled, revoked, expired, limited")?;

    Ok(ResolvedConfig {
        format: args.format.unwrap_or(OutputFormat::Text),
        summary_path: args
            .summary_path
            .or_else(|| {
                env::var("VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_LIFECYCLE_SUMMARY_PATH")
                    .ok()
                    .map(PathBuf::from)
            })
            .unwrap_or_else(default_summary_path),
        base_url: args
            .base_url
            .or_else(|| env::var("VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_BASE_URL").ok()),
        api_token: args
            .api_token
            .or_else(|| env::var("VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_API_TOKEN").ok()),
        bootstrap_subject: args
            .bootstrap_subject
            .or_else(|| env::var("VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_BOOTSTRAP_SUBJECT").ok()),
        webhook_signature: args
            .webhook_signature
            .or_else(|| env::var("VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_WEBHOOK_SIGNATURE").ok()),
        source_version_override: args
            .source_version_override
            .or_else(|| env::var("VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_SOURCE_VERSION").ok()),
        expected_account_id: args
            .expected_account_id
            .or_else(|| env::var("VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_ACCOUNT_ID").ok()),
        webhook_event_type: args
            .webhook_event_type
            .or_else(|| env::var("VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_WEBHOOK_EVENT_TYPE").ok())
            .unwrap_or_else(|| expected_lifecycle.webhook_event_type().to_owned()),
        expected_lifecycle,
        request_timeout_ms: args
            .request_timeout_ms
            .or_else(|| {
                env::var("VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_REQUEST_TIMEOUT_MS")
                    .ok()
                    .and_then(|value| value.parse().ok())
            })
            .unwrap_or(2_000),
        max_snapshot_age_seconds: args
            .max_snapshot_age_seconds
            .or_else(|| {
                env::var("VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_MAX_SNAPSHOT_AGE_SECONDS")
                    .ok()
                    .and_then(|value| value.parse().ok())
            })
            .unwrap_or(300),
        max_reconcile_lag_seconds: args
            .max_reconcile_lag_seconds
            .or_else(|| {
                env::var("VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_MAX_RECONCILE_LAG_SECONDS")
                    .ok()
                    .and_then(|value| value.parse().ok())
            })
            .unwrap_or(120),
        lifecycle_wait_timeout_seconds: args
            .lifecycle_wait_timeout_seconds
            .or_else(|| {
                env::var("VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_LIFECYCLE_WAIT_TIMEOUT_SECONDS")
                    .ok()
                    .and_then(|value| value.parse().ok())
            })
            .unwrap_or(180),
        poll_interval_ms: args
            .poll_interval_ms
            .or_else(|| {
                env::var("VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_POLL_INTERVAL_MS")
                    .ok()
                    .and_then(|value| value.parse().ok())
            })
            .unwrap_or(2_000),
    })
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

fn next_arg<I>(iter: &mut I, flag: &str) -> Result<String, Box<dyn std::error::Error>>
where
    I: Iterator<Item = String>,
{
    iter.next()
        .ok_or_else(|| format!("{flag} requires a value").into())
}

fn print_text_summary(summary: &SupportedUpstreamLifecycleSummary, summary_path: &Path) {
    println!("Verta Supported Upstream Lifecycle Verification");
    println!("- verdict: {}", summary.verdict);
    println!("- gate_state: {}", summary.gate_state);
    println!("- gate_state_reason: {}", summary.gate_state_reason);
    println!("- upstream_state: {}", summary.upstream_state);
    println!(
        "- expected_lifecycle: {}",
        summary.supported_upstream_expected_lifecycle
    );
    println!(
        "- required_input_counts: total={} present={} passed={} missing={} unready={}",
        summary.required_input_count,
        summary.required_input_present_count,
        summary.required_input_passed_count,
        summary.required_input_missing_count,
        summary.required_input_unready_count
    );
    println!(
        "- active_path: bootstrap={} register={} token={} refresh={}",
        render_optional_bool(summary.active_bridge_manifest_bootstrap_passed),
        render_optional_bool(summary.active_bridge_device_register_passed),
        render_optional_bool(summary.active_bridge_token_exchange_passed),
        render_optional_bool(summary.active_bridge_manifest_refresh_passed)
    );
    println!(
        "- lifecycle_path: observed={} expected_state={} snapshot_fresh={} reconcile_lag_ok={} denial_code={} bootstrap_denied={} refresh_denied={} token_denied={}",
        render_optional_bool(summary.lifecycle_transition_observed),
        render_optional_bool(summary.lifecycle_expected_state_passed),
        render_optional_bool(summary.lifecycle_snapshot_fresh),
        render_optional_bool(summary.reconcile_lag_within_target),
        render_optional_bool(summary.lifecycle_denial_code_passed),
        render_optional_bool(summary.lifecycle_bridge_manifest_bootstrap_denied),
        render_optional_bool(summary.lifecycle_bridge_manifest_refresh_denied),
        render_optional_bool(summary.lifecycle_bridge_token_exchange_denied)
    );
    println!(
        "- webhook_path: negative_sig={} positive={} duplicate={} reconcile_hint={}",
        render_optional_bool(summary.webhook_signature_negative_rejection_passed),
        render_optional_bool(summary.webhook_positive_delivery_passed),
        render_optional_bool(summary.webhook_duplicate_rejection_passed),
        render_optional_bool(summary.webhook_reconcile_hint_passed)
    );
    println!(
        "- detector_flags: unsupported_version={} auth_failure={} timeout={} unavailable={} stale={} drift={} lifecycle_drift={} reconcile_lag={} replay_inconsistency={} webhook_signature_failure={} incompatible_contract={}",
        summary.unsupported_upstream_version_detected,
        summary.upstream_auth_failure_detected,
        summary.upstream_timeout_detected,
        summary.upstream_unavailable_detected,
        summary.upstream_stale_detected,
        summary.upstream_drift_detected,
        summary.lifecycle_drift_detected,
        summary.reconcile_lag_detected,
        summary.replay_sensitive_inconsistency_detected,
        summary.webhook_signature_failure_detected,
        summary.incompatible_contract_detected
    );
    println!("- summary_path: {}", summary_path.display());
}

fn render_optional_bool(value: Option<bool>) -> &'static str {
    match value {
        Some(true) => "true",
        Some(false) => "false",
        None => "n/a",
    }
}

fn default_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("verta")
        .join("remnawave-supported-upstream-lifecycle-summary.json")
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
        .join("verta")
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
        .context("failed to encode supported-upstream lifecycle token signer")?;
    SessionTokenSigner::from_ed_pem(
        "bridge.example",
        "verta-gateway",
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
            "supported-upstream lifecycle verification server should serve while the harness is active",
        );
    });
    tokio::time::sleep(StdDuration::from_millis(10)).await;
    Ok((format!("http://{addr}"), handle))
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

    fn active_snapshot(version: &str) -> AccountSnapshot {
        AccountSnapshot {
            account_id: "acct-1".to_owned(),
            bootstrap_subjects: vec![BootstrapSubject::ShortUuid("sub-1".to_owned())],
            lifecycle: AccountLifecycle::Active,
            verta_access: ns_remnawave_adapter::VertaAccess {
                verta_enabled: true,
                policy_epoch: 7,
                device_limit: Some(4),
                allowed_core_versions: vec![1],
                allowed_carrier_profiles: vec!["carrier-primary".to_owned()],
                allowed_capabilities: vec![1, 2],
                rollout_cohort: Some("stable".to_owned()),
                preferred_regions: vec!["eu-central".to_owned()],
            },
            metadata: Some(serde_json::json!({ "plan": "pro" })),
            observed_at_unix: OffsetDateTime::now_utc().unix_timestamp(),
            source_version: Some(version.to_owned()),
        }
    }

    fn transitioned_snapshot(version: &str, lifecycle: AccountLifecycle) -> AccountSnapshot {
        let mut snapshot = active_snapshot(version);
        snapshot.lifecycle = lifecycle;
        snapshot.verta_access.policy_epoch += 1;
        snapshot.observed_at_unix = OffsetDateTime::now_utc().unix_timestamp();
        snapshot
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
    ) -> (String, Arc<TestUpstreamState>, tokio::task::JoinHandle<()>) {
        let state = Arc::new(TestUpstreamState {
            snapshot: Mutex::new(snapshot),
            expected_token: "rw-token".to_owned(),
        });
        let router = Router::new()
            .route("/api/users/resolve", post(resolve_user))
            .route("/api/users/{account_id}", get(get_user))
            .with_state(state.clone());
        let (base_url, handle) = spawn_router(router)
            .await
            .expect("test upstream router should spawn");
        (base_url, state, handle)
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
            expected_account_id: Some("acct-1".to_owned()),
            expected_lifecycle: LifecycleExpectation::Disabled,
            webhook_event_type: "user.disabled".to_owned(),
            request_timeout_ms: 500,
            max_snapshot_age_seconds: 300,
            max_reconcile_lag_seconds: 300,
            lifecycle_wait_timeout_seconds: 2,
            poll_interval_ms: 25,
        }
    }

    #[tokio::test]
    async fn lifecycle_summary_is_ready_when_transition_propagates() {
        let (base_url, state, handle) = spawn_test_upstream(active_snapshot("2.7.4")).await;
        let mutate_state = state.clone();
        tokio::spawn(async move {
            tokio::time::sleep(StdDuration::from_millis(500)).await;
            *mutate_state
                .snapshot
                .lock()
                .expect("test upstream state poisoned") =
                transitioned_snapshot("2.7.4", AccountLifecycle::Disabled);
        });

        let summary = build_supported_upstream_lifecycle_summary(&test_config(
            Some(base_url),
            Some("rw-token".to_owned()),
        ))
        .await;

        assert_eq!(summary.verdict, "ready");
        assert_eq!(summary.gate_state, "passed");
        assert_eq!(summary.gate_state_reason, "all_required_inputs_passed");
        assert_eq!(summary.upstream_state, "lifecycle_verified");
        assert_eq!(summary.lifecycle_transition_observed, Some(true));
        assert_eq!(summary.lifecycle_expected_state_passed, Some(true));
        assert_eq!(summary.lifecycle_policy_epoch_advanced, Some(true));
        assert_eq!(
            summary.lifecycle_bridge_manifest_bootstrap_denied,
            Some(true)
        );
        assert_eq!(summary.lifecycle_bridge_manifest_refresh_denied, Some(true));
        assert_eq!(summary.lifecycle_bridge_token_exchange_denied, Some(true));
        assert_eq!(summary.lifecycle_denial_code_passed, Some(true));
        assert_eq!(summary.webhook_duplicate_rejection_passed, Some(true));

        handle.abort();
        let _ = handle.await;
    }

    #[tokio::test]
    async fn lifecycle_summary_holds_when_environment_is_missing() {
        let summary = build_supported_upstream_lifecycle_summary(&ResolvedConfig {
            format: OutputFormat::Json,
            summary_path: default_summary_path(),
            base_url: None,
            api_token: None,
            bootstrap_subject: None,
            webhook_signature: None,
            source_version_override: None,
            expected_account_id: None,
            expected_lifecycle: LifecycleExpectation::Disabled,
            webhook_event_type: "user.disabled".to_owned(),
            request_timeout_ms: 500,
            max_snapshot_age_seconds: 300,
            max_reconcile_lag_seconds: 300,
            lifecycle_wait_timeout_seconds: 1,
            poll_interval_ms: 25,
        })
        .await;

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.evidence_state, "incomplete");
        assert_eq!(summary.gate_state_reason, "missing_required_inputs");
        assert_eq!(summary.supported_upstream_environment_present, false);
        assert_eq!(summary.missing_required_input_count, 5);
    }

    #[tokio::test]
    async fn lifecycle_summary_fails_closed_when_transition_does_not_arrive() {
        let (base_url, _state, handle) = spawn_test_upstream(active_snapshot("2.7.4")).await;
        let mut config = test_config(Some(base_url), Some("rw-token".to_owned()));
        config.lifecycle_wait_timeout_seconds = 1;

        let summary = build_supported_upstream_lifecycle_summary(&config).await;

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.gate_state_reason, "degradation_hold");
        assert_eq!(summary.lifecycle_transition_observed, Some(false));
        assert_eq!(summary.reconcile_lag_detected, true);
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|reason| reason.contains("lifecycle_transition_wait"))
        );

        handle.abort();
        let _ = handle.await;
    }
}
