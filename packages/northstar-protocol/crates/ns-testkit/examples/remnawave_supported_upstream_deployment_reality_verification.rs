use anyhow::Context;
use axum::Router;
use axum::http::header::ETAG;
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
    HttpRemnawaveAdapterConfig, RemnawaveAdapter, WebhookAuthenticator, WebhookVerificationConfig,
    WebhookVerificationError,
};
use ns_storage::{
    BridgeStoreServiceHealthResponse, HttpServiceBackedBridgeStoreAdapter,
    ServiceBackedBridgeStore, ServiceBackedBridgeStoreConfig, SharedBridgeStore, SqliteBridgeStore,
    StorageError, build_service_backed_bridge_store_router,
};
use ns_testkit::{
    FIXTURE_MANIFEST_KEY_ID, FIXTURE_TOKEN_KEY_ID, fixed_test_now, fixture_manifest_signing_key,
    fixture_token_jwks, fixture_token_signing_key, repo_root, sample_manifest_document,
    summarize_rollout_gate_state,
};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::io::ErrorKind;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use time::{Duration, OffsetDateTime};
use tokio::net::TcpListener;
use tokio::sync::oneshot;

const DEPLOYMENT_REALITY_VERIFICATION_SCHEMA: &str =
    "supported_upstream_deployment_reality_operator_verdict";
const DEPLOYMENT_REALITY_VERIFICATION_SCHEMA_VERSION: u8 = 1;
const DEPLOYMENT_REALITY_VERDICT_FAMILY: &str = "supported_upstream_deployment_reality";
const DEPLOYMENT_REALITY_DECISION_SCOPE: &str = "supported_upstream_deployment_reality";
const DEPLOYMENT_REALITY_DECISION_LABEL: &str =
    "remnawave_supported_upstream_deployment_reality_verification";
const DEPLOYMENT_REALITY_PROFILE: &str = "supported_upstream_deployment_reality_verification";
const DEPLOYMENT_REALITY_SUMMARY_VERSION: u8 = 1;

const SUPPORTED_UPSTREAM_VERSION_FLOOR: SimpleVersion = SimpleVersion::new(2, 7, 0);
const SUPPORTED_UPSTREAM_VERSION_PREFERRED: SimpleVersion = SimpleVersion::new(2, 7, 4);

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum OutputFormat {
    Text,
    Json,
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
struct DeploymentRealityArgs {
    format: Option<OutputFormat>,
    summary_path: Option<PathBuf>,
    base_url: Option<String>,
    api_token: Option<String>,
    bootstrap_subject: Option<String>,
    webhook_signature: Option<String>,
    source_version_override: Option<String>,
    expected_account_id: Option<String>,
    store_auth_token: Option<String>,
    upstream_summary_path: Option<PathBuf>,
    lifecycle_summary_path: Option<PathBuf>,
    request_timeout_ms: Option<u64>,
    max_snapshot_age_seconds: Option<i64>,
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
    store_auth_token: Option<String>,
    upstream_summary_path: PathBuf,
    lifecycle_summary_path: PathBuf,
    request_timeout_ms: u64,
    max_snapshot_age_seconds: i64,
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
    successful_stage_count: usize,
    supported_upstream_environment_present: bool,
    prior_supported_upstream_summary_loaded: Option<bool>,
    prior_lifecycle_summary_loaded: Option<bool>,
    prior_supported_upstream_summary_passed: Option<bool>,
    prior_lifecycle_summary_passed: Option<bool>,
    upstream_source_version: Option<String>,
    supported_upstream_version_passed: Option<bool>,
    supported_upstream_version_preferred_passed: Option<bool>,
    account_snapshot_fetched: Option<bool>,
    account_snapshot_fresh: Option<bool>,
    account_id_expected_match: Option<bool>,
    deployment_store_scope_shared_durable_passed: Option<bool>,
    deployment_store_health_check_passed: Option<bool>,
    deployment_startup_ordering_passed: Option<bool>,
    deployment_public_manifest_bootstrap_passed: Option<bool>,
    deployment_public_device_register_passed: Option<bool>,
    deployment_public_token_exchange_passed: Option<bool>,
    deployment_public_manifest_refresh_passed: Option<bool>,
    deployment_shutdown_passed: Option<bool>,
    deployment_remote_store_auth_mismatch_rejected: Option<bool>,
    deployment_unauthorized_primary_no_failover_passed: Option<bool>,
    supported_upstream_deployment_reality_passed: Option<bool>,
    control_plane_issuance_only: bool,
    unsupported_upstream_version_detected: bool,
    upstream_auth_failure_detected: bool,
    upstream_timeout_detected: bool,
    response_shape_drift_detected: bool,
    webhook_signature_failure_detected: bool,
    lifecycle_drift_detected: bool,
    reconcile_lag_detected: bool,
    stale_snapshot_state_detected: bool,
    replay_sensitive_inconsistency_detected: bool,
    remote_store_auth_mismatch_detected: bool,
    remote_backend_unavailable_detected: bool,
    health_check_drift_detected: bool,
    startup_ordering_failure_detected: bool,
    partial_failover_detected: bool,
    incompatible_contract_detected: bool,
}

#[derive(Debug, Serialize)]
struct SupportedUpstreamDeploymentRealitySummary {
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
    supported_upstream_version_floor: String,
    supported_upstream_version_preferred: String,
    upstream_source_version: Option<String>,
    deployment_state: &'static str,
    control_plane_issuance_only: bool,
    prior_supported_upstream_summary_path: String,
    prior_lifecycle_summary_path: String,
    prior_supported_upstream_summary_loaded: Option<bool>,
    prior_lifecycle_summary_loaded: Option<bool>,
    prior_supported_upstream_summary_passed: Option<bool>,
    prior_lifecycle_summary_passed: Option<bool>,
    supported_upstream_version_passed: Option<bool>,
    supported_upstream_version_preferred_passed: Option<bool>,
    account_snapshot_fetched: Option<bool>,
    account_snapshot_fresh: Option<bool>,
    account_id_expected_match: Option<bool>,
    deployment_store_scope_shared_durable_passed: Option<bool>,
    deployment_store_health_check_passed: Option<bool>,
    deployment_startup_ordering_passed: Option<bool>,
    deployment_public_manifest_bootstrap_passed: Option<bool>,
    deployment_public_device_register_passed: Option<bool>,
    deployment_public_token_exchange_passed: Option<bool>,
    deployment_public_manifest_refresh_passed: Option<bool>,
    deployment_shutdown_passed: Option<bool>,
    deployment_remote_store_auth_mismatch_rejected: Option<bool>,
    deployment_unauthorized_primary_no_failover_passed: Option<bool>,
    supported_upstream_deployment_reality_passed: Option<bool>,
    unsupported_upstream_version_detected: bool,
    upstream_auth_failure_detected: bool,
    upstream_timeout_detected: bool,
    response_shape_drift_detected: bool,
    webhook_signature_failure_detected: bool,
    lifecycle_drift_detected: bool,
    reconcile_lag_detected: bool,
    stale_snapshot_state_detected: bool,
    replay_sensitive_inconsistency_detected: bool,
    remote_store_auth_mismatch_detected: bool,
    remote_backend_unavailable_detected: bool,
    health_check_drift_detected: bool,
    startup_ordering_failure_detected: bool,
    partial_failover_detected: bool,
    incompatible_contract_detected: bool,
    blocking_reasons: Vec<String>,
    blocking_reason_keys: Vec<String>,
    blocking_reason_families: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct PriorSummaryInput {
    gate_state: String,
    gate_state_reason: String,
    #[serde(default)]
    all_required_inputs_passed: bool,
    #[serde(default)]
    blocking_reason_keys: Vec<String>,
    #[serde(default)]
    supported_upstream_compatibility_passed: Option<bool>,
    #[serde(default)]
    supported_upstream_lifecycle_passed: Option<bool>,
}

#[derive(Debug)]
struct BridgeFlowEvidence {
    manifest_bootstrap_passed: bool,
    device_register_passed: bool,
    token_exchange_passed: bool,
    manifest_refresh_passed: bool,
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

struct ManagedRouter {
    base_url: String,
    shutdown: Option<oneshot::Sender<()>>,
    task: tokio::task::JoinHandle<()>,
}

impl ManagedRouter {
    async fn shutdown(mut self) {
        if let Some(sender) = self.shutdown.take() {
            let _ = sender.send(());
        }
        let _ = self.task.await;
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = parse_args(env::args().skip(1))?;
    let config = resolve_config(args);
    let summary = build_supported_upstream_deployment_reality_summary(&config).await;

    if let Some(parent) = config.summary_path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(
        &config.summary_path,
        serde_json::to_vec_pretty(&summary).context("failed to serialize deployment summary")?,
    )?;

    match config.format {
        OutputFormat::Text => print_text_summary(&summary, &config.summary_path),
        OutputFormat::Json => println!("{}", serde_json::to_string_pretty(&summary)?),
    }

    Ok(())
}

async fn build_supported_upstream_deployment_reality_summary(
    config: &ResolvedConfig,
) -> SupportedUpstreamDeploymentRealitySummary {
    let required_inputs = vec![
        "supported_upstream_base_url".to_owned(),
        "supported_upstream_api_token".to_owned(),
        "supported_upstream_bootstrap_subject".to_owned(),
        "supported_upstream_webhook_signature".to_owned(),
        "supported_upstream_expected_account_id".to_owned(),
        "supported_upstream_store_auth_token".to_owned(),
        "supported_upstream_summary_input".to_owned(),
        "supported_upstream_lifecycle_summary_input".to_owned(),
    ];
    let considered_inputs = required_inputs.clone();
    let mut state = SummaryState {
        control_plane_issuance_only: true,
        ..SummaryState::default()
    };

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
    if config.store_auth_token.is_none() {
        state
            .missing_required_inputs
            .push("supported_upstream_store_auth_token".to_owned());
    }
    if !config.upstream_summary_path.exists() {
        state
            .missing_required_inputs
            .push("supported_upstream_summary_input".to_owned());
    }
    if !config.lifecycle_summary_path.exists() {
        state
            .missing_required_inputs
            .push("supported_upstream_lifecycle_summary_input".to_owned());
    }

    if !state.missing_required_inputs.is_empty() {
        return finalize_summary(config, required_inputs, considered_inputs, state);
    }

    state.supported_upstream_environment_present = true;

    if !load_prior_summary_input(
        &config.upstream_summary_path,
        "supported_upstream_summary_input",
        "supported_upstream_compatibility_passed",
        &mut state,
    ) {
        return finalize_summary(config, required_inputs, considered_inputs, state);
    }

    if !load_prior_summary_input(
        &config.lifecycle_summary_path,
        "supported_upstream_lifecycle_summary_input",
        "supported_upstream_lifecycle_passed",
        &mut state,
    ) {
        return finalize_summary(config, required_inputs, considered_inputs, state);
    }

    let base_url = config.base_url.clone().expect("checked above");
    let api_token = config.api_token.clone().expect("checked above");
    let adapter = match HttpRemnawaveAdapterConfig::new(
        base_url.clone(),
        api_token,
        config.request_timeout_ms,
    )
    .map(HttpRemnawaveAdapter::new)
    {
        Ok(adapter) => adapter,
        Err(error) => {
            mark_incompatible_contract(
                &mut state,
                "supported_upstream_adapter_config_invalid",
                error.to_string(),
            );
            return finalize_summary(config, required_inputs, considered_inputs, state);
        }
    };

    let bootstrap_subject = BootstrapSubject::ShortUuid(
        config
            .bootstrap_subject
            .clone()
            .expect("checked above for missing inputs"),
    );

    let snapshot = match adapter.resolve_bootstrap_subject(&bootstrap_subject).await {
        Ok(snapshot) => {
            let snapshot =
                apply_source_version_override(snapshot, config.source_version_override.as_deref());
            state.account_snapshot_fetched = Some(true);
            state.successful_stage_count += 1;
            snapshot
        }
        Err(error) => {
            apply_upstream_error(&mut state, "resolve_bootstrap_subject", &error);
            return finalize_summary(config, required_inputs, considered_inputs, state);
        }
    };

    state.upstream_source_version = snapshot.source_version.clone();
    if let Some(version) = snapshot
        .source_version
        .as_deref()
        .and_then(|value| SimpleVersion::parse(value))
    {
        let version_passed = version >= SUPPORTED_UPSTREAM_VERSION_FLOOR;
        let preferred_passed = version >= SUPPORTED_UPSTREAM_VERSION_PREFERRED;
        state.supported_upstream_version_passed = Some(version_passed);
        state.supported_upstream_version_preferred_passed = Some(preferred_passed);
        if !version_passed {
            state.unsupported_upstream_version_detected = true;
            state.summary_contract_invalid_count += 1;
            record_blocking_reason(
                &mut state,
                "unsupported_upstream_version",
                "compatibility",
                format!(
                    "source_version={} below {}",
                    version.render(),
                    SUPPORTED_UPSTREAM_VERSION_FLOOR.render()
                ),
            );
            return finalize_summary(config, required_inputs, considered_inputs, state);
        }
    } else {
        state.response_shape_drift_detected = true;
        state.summary_contract_invalid_count += 1;
        record_blocking_reason(
            &mut state,
            "response_shape_drift",
            "summary_contract",
            "supported upstream snapshot missing parseable source_version",
        );
        return finalize_summary(config, required_inputs, considered_inputs, state);
    }

    let snapshot_age = OffsetDateTime::now_utc().unix_timestamp() - snapshot.observed_at_unix;
    state.account_snapshot_fresh = Some(snapshot_age <= config.max_snapshot_age_seconds);
    if state.account_snapshot_fresh != Some(true) {
        state.stale_snapshot_state_detected = true;
        state.required_input_unready_count += 1;
        record_blocking_reason(
            &mut state,
            "stale_snapshot_state",
            "upstream",
            format!(
                "snapshot_age_seconds={} exceeded {}",
                snapshot_age, config.max_snapshot_age_seconds
            ),
        );
        return finalize_summary(config, required_inputs, considered_inputs, state);
    }

    state.account_id_expected_match =
        Some(snapshot.account_id == config.expected_account_id.clone().expect("checked above"));
    if state.account_id_expected_match != Some(true) {
        state.incompatible_contract_detected = true;
        state.summary_contract_invalid_count += 1;
        record_blocking_reason(
            &mut state,
            "incompatible_contract",
            "bridge_contract",
            format!(
                "expected account_id {}, got {}",
                config.expected_account_id.as_deref().unwrap_or_default(),
                snapshot.account_id
            ),
        );
        return finalize_summary(config, required_inputs, considered_inputs, state);
    }
    state.successful_stage_count += 1;

    match run_positive_deployment_reality_check(&adapter, config).await {
        Ok(evidence) => {
            state.deployment_store_scope_shared_durable_passed =
                Some(evidence.store_scope_shared_durable_passed);
            state.deployment_store_health_check_passed = Some(evidence.store_health_check_passed);
            state.deployment_startup_ordering_passed = Some(evidence.startup_ordering_passed);
            state.deployment_public_manifest_bootstrap_passed =
                Some(evidence.public_flow.manifest_bootstrap_passed);
            state.deployment_public_device_register_passed =
                Some(evidence.public_flow.device_register_passed);
            state.deployment_public_token_exchange_passed =
                Some(evidence.public_flow.token_exchange_passed);
            state.deployment_public_manifest_refresh_passed =
                Some(evidence.public_flow.manifest_refresh_passed);
            state.deployment_shutdown_passed = Some(evidence.shutdown_passed);
            if evidence.store_scope_shared_durable_passed
                && evidence.store_health_check_passed
                && evidence.startup_ordering_passed
                && evidence.public_flow.manifest_bootstrap_passed
                && evidence.public_flow.device_register_passed
                && evidence.public_flow.token_exchange_passed
                && evidence.public_flow.manifest_refresh_passed
                && evidence.shutdown_passed
            {
                state.successful_stage_count += 1;
            }
        }
        Err(error) => apply_deployment_error(&mut state, "deployment_runtime", &error),
    }

    match run_remote_store_auth_mismatch_check(config).await {
        Ok(()) => {
            state.deployment_remote_store_auth_mismatch_rejected = Some(true);
            state.successful_stage_count += 1;
        }
        Err(error) => {
            state.deployment_remote_store_auth_mismatch_rejected = Some(false);
            state.remote_store_auth_mismatch_detected = true;
            state.required_input_unready_count += 1;
            record_blocking_reason(
                &mut state,
                "remote_store_auth_mismatch",
                "deployment",
                error,
            );
        }
    }

    match run_unauthorized_primary_no_failover_check(config).await {
        Ok(()) => {
            state.deployment_unauthorized_primary_no_failover_passed = Some(true);
            state.successful_stage_count += 1;
        }
        Err(UnauthorizedPrimaryFailure::UnexpectedFailover) => {
            state.deployment_unauthorized_primary_no_failover_passed = Some(false);
            state.partial_failover_detected = true;
            state.degradation_hold_count += 1;
            record_blocking_reason(
                &mut state,
                "partial_failover",
                "deployment",
                "unauthorized primary store endpoint unexpectedly failed over to the secondary endpoint",
            );
        }
        Err(UnauthorizedPrimaryFailure::BackendUnavailable(detail)) => {
            state.deployment_unauthorized_primary_no_failover_passed = Some(false);
            state.remote_backend_unavailable_detected = true;
            state.required_input_unready_count += 1;
            record_blocking_reason(
                &mut state,
                "remote_backend_unavailable",
                "deployment",
                detail,
            );
        }
        Err(UnauthorizedPrimaryFailure::Unexpected(detail)) => {
            state.deployment_unauthorized_primary_no_failover_passed = Some(false);
            state.health_check_drift_detected = true;
            state.summary_contract_invalid_count += 1;
            record_blocking_reason(&mut state, "health_check_drift", "summary_contract", detail);
        }
    }

    state.supported_upstream_deployment_reality_passed = Some(
        state.deployment_store_scope_shared_durable_passed == Some(true)
            && state.deployment_store_health_check_passed == Some(true)
            && state.deployment_startup_ordering_passed == Some(true)
            && state.deployment_public_manifest_bootstrap_passed == Some(true)
            && state.deployment_public_device_register_passed == Some(true)
            && state.deployment_public_token_exchange_passed == Some(true)
            && state.deployment_public_manifest_refresh_passed == Some(true)
            && state.deployment_shutdown_passed == Some(true)
            && state.deployment_remote_store_auth_mismatch_rejected == Some(true)
            && state.deployment_unauthorized_primary_no_failover_passed == Some(true)
            && state.prior_supported_upstream_summary_passed == Some(true)
            && state.prior_lifecycle_summary_passed == Some(true),
    );

    finalize_summary(config, required_inputs, considered_inputs, state)
}

fn finalize_summary(
    config: &ResolvedConfig,
    required_inputs: Vec<String>,
    considered_inputs: Vec<String>,
    state: SummaryState,
) -> SupportedUpstreamDeploymentRealitySummary {
    let deployment_state = derive_deployment_state(
        &state,
        if state.missing_required_inputs.is_empty()
            && state.summary_contract_invalid_count == 0
            && state.required_input_unready_count == 0
            && state.degradation_hold_count == 0
            && state.blocking_reasons.is_empty()
        {
            "ready"
        } else {
            "hold"
        },
    );
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

    SupportedUpstreamDeploymentRealitySummary {
        summary_version: DEPLOYMENT_REALITY_SUMMARY_VERSION,
        verification_schema: DEPLOYMENT_REALITY_VERIFICATION_SCHEMA,
        verification_schema_version: DEPLOYMENT_REALITY_VERIFICATION_SCHEMA_VERSION,
        verdict_family: DEPLOYMENT_REALITY_VERDICT_FAMILY,
        decision_scope: DEPLOYMENT_REALITY_DECISION_SCOPE,
        decision_label: DEPLOYMENT_REALITY_DECISION_LABEL,
        profile: DEPLOYMENT_REALITY_PROFILE,
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
        blocking_reason_key_count: blocking_reason_keys.len(),
        blocking_reason_family_count: blocking_reason_families.len(),
        blocking_reason_key_counts: state.blocking_reason_key_counts,
        blocking_reason_family_counts: state.blocking_reason_family_counts,
        supported_upstream_environment_present: state.supported_upstream_environment_present,
        supported_upstream_base_url: config.base_url.clone(),
        supported_upstream_bootstrap_subject: config.bootstrap_subject.clone(),
        supported_upstream_expected_account_id: config.expected_account_id.clone(),
        supported_upstream_version_floor: SUPPORTED_UPSTREAM_VERSION_FLOOR.render(),
        supported_upstream_version_preferred: SUPPORTED_UPSTREAM_VERSION_PREFERRED.render(),
        upstream_source_version: state.upstream_source_version,
        deployment_state,
        control_plane_issuance_only: state.control_plane_issuance_only,
        prior_supported_upstream_summary_path: config.upstream_summary_path.display().to_string(),
        prior_lifecycle_summary_path: config.lifecycle_summary_path.display().to_string(),
        prior_supported_upstream_summary_loaded: state.prior_supported_upstream_summary_loaded,
        prior_lifecycle_summary_loaded: state.prior_lifecycle_summary_loaded,
        prior_supported_upstream_summary_passed: state.prior_supported_upstream_summary_passed,
        prior_lifecycle_summary_passed: state.prior_lifecycle_summary_passed,
        supported_upstream_version_passed: state.supported_upstream_version_passed,
        supported_upstream_version_preferred_passed: state
            .supported_upstream_version_preferred_passed,
        account_snapshot_fetched: state.account_snapshot_fetched,
        account_snapshot_fresh: state.account_snapshot_fresh,
        account_id_expected_match: state.account_id_expected_match,
        deployment_store_scope_shared_durable_passed: state
            .deployment_store_scope_shared_durable_passed,
        deployment_store_health_check_passed: state.deployment_store_health_check_passed,
        deployment_startup_ordering_passed: state.deployment_startup_ordering_passed,
        deployment_public_manifest_bootstrap_passed: state
            .deployment_public_manifest_bootstrap_passed,
        deployment_public_device_register_passed: state.deployment_public_device_register_passed,
        deployment_public_token_exchange_passed: state.deployment_public_token_exchange_passed,
        deployment_public_manifest_refresh_passed: state.deployment_public_manifest_refresh_passed,
        deployment_shutdown_passed: state.deployment_shutdown_passed,
        deployment_remote_store_auth_mismatch_rejected: state
            .deployment_remote_store_auth_mismatch_rejected,
        deployment_unauthorized_primary_no_failover_passed: state
            .deployment_unauthorized_primary_no_failover_passed,
        supported_upstream_deployment_reality_passed: state
            .supported_upstream_deployment_reality_passed,
        unsupported_upstream_version_detected: state.unsupported_upstream_version_detected,
        upstream_auth_failure_detected: state.upstream_auth_failure_detected,
        upstream_timeout_detected: state.upstream_timeout_detected,
        response_shape_drift_detected: state.response_shape_drift_detected,
        webhook_signature_failure_detected: state.webhook_signature_failure_detected,
        lifecycle_drift_detected: state.lifecycle_drift_detected,
        reconcile_lag_detected: state.reconcile_lag_detected,
        stale_snapshot_state_detected: state.stale_snapshot_state_detected,
        replay_sensitive_inconsistency_detected: state.replay_sensitive_inconsistency_detected,
        remote_store_auth_mismatch_detected: state.remote_store_auth_mismatch_detected,
        remote_backend_unavailable_detected: state.remote_backend_unavailable_detected,
        health_check_drift_detected: state.health_check_drift_detected,
        startup_ordering_failure_detected: state.startup_ordering_failure_detected,
        partial_failover_detected: state.partial_failover_detected,
        incompatible_contract_detected: state.incompatible_contract_detected,
        blocking_reasons: state.blocking_reasons,
        blocking_reason_keys,
        blocking_reason_families,
    }
}

fn derive_deployment_state(state: &SummaryState, verdict: &str) -> &'static str {
    if !state.supported_upstream_environment_present {
        "missing_environment"
    } else if state.summary_contract_invalid_count > 0 {
        "contract_invalid"
    } else if state.required_input_unready_count > 0 {
        "required_input_unready"
    } else if state.degradation_hold_count > 0 {
        "degraded"
    } else if verdict == "ready" {
        "verified"
    } else {
        "partial"
    }
}

fn load_prior_summary_input(
    path: &Path,
    input_label: &str,
    required_flag: &str,
    state: &mut SummaryState,
) -> bool {
    let contents = match fs::read_to_string(path) {
        Ok(contents) => contents,
        Err(error) => {
            if error.kind() == ErrorKind::NotFound {
                state.missing_required_inputs.push(input_label.to_owned());
            } else {
                state.summary_contract_invalid_count += 1;
                record_blocking_reason(
                    state,
                    "summary_contract_invalid",
                    "summary_contract",
                    format!("failed to read {input_label}: {error}"),
                );
            }
            return false;
        }
    };

    let summary: PriorSummaryInput = match serde_json::from_str(&contents) {
        Ok(summary) => summary,
        Err(error) => {
            state.summary_contract_invalid_count += 1;
            record_blocking_reason(
                state,
                "summary_contract_invalid",
                "summary_contract",
                format!("failed to parse {input_label}: {error}"),
            );
            return false;
        }
    };

    match input_label {
        "supported_upstream_summary_input" => {
            state.prior_supported_upstream_summary_loaded = Some(true)
        }
        "supported_upstream_lifecycle_summary_input" => {
            state.prior_lifecycle_summary_loaded = Some(true)
        }
        _ => {}
    }

    for key in &summary.blocking_reason_keys {
        project_prior_reason_key(state, key);
    }

    let specific_passed = match required_flag {
        "supported_upstream_compatibility_passed" => {
            summary.supported_upstream_compatibility_passed == Some(true)
        }
        "supported_upstream_lifecycle_passed" => {
            summary.supported_upstream_lifecycle_passed == Some(true)
        }
        _ => false,
    };
    let input_passed =
        summary.gate_state == "passed" && summary.all_required_inputs_passed && specific_passed;

    match input_label {
        "supported_upstream_summary_input" => {
            state.prior_supported_upstream_summary_passed = Some(input_passed)
        }
        "supported_upstream_lifecycle_summary_input" => {
            state.prior_lifecycle_summary_passed = Some(input_passed)
        }
        _ => {}
    }

    if input_passed {
        state.successful_stage_count += 1;
        true
    } else {
        state.required_input_unready_count += 1;
        record_blocking_reason(
            state,
            "required_inputs_unready",
            "gating",
            format!(
                "{input_label} gate_state={} reason={}",
                summary.gate_state, summary.gate_state_reason
            ),
        );
        false
    }
}

fn project_prior_reason_key(state: &mut SummaryState, key: &str) {
    match key {
        "unsupported_upstream_version" => state.unsupported_upstream_version_detected = true,
        "upstream_auth_failure" => state.upstream_auth_failure_detected = true,
        "upstream_timeout" => state.upstream_timeout_detected = true,
        "response_shape_drift" => state.response_shape_drift_detected = true,
        "webhook_signature_failure" => state.webhook_signature_failure_detected = true,
        "lifecycle_drift" => state.lifecycle_drift_detected = true,
        "reconcile_lag_exceeded" => state.reconcile_lag_detected = true,
        "stale_snapshot_state" => state.stale_snapshot_state_detected = true,
        "replay_sensitive_inconsistency" => state.replay_sensitive_inconsistency_detected = true,
        "incompatible_contract" => state.incompatible_contract_detected = true,
        _ => {}
    }
}

fn apply_upstream_error(state: &mut SummaryState, stage: &str, error: &AdapterError) {
    match error {
        AdapterError::Unauthorized => {
            state.upstream_auth_failure_detected = true;
            state.required_input_unready_count += 1;
            record_blocking_reason(
                state,
                "upstream_auth_failure",
                "upstream",
                format!("{stage} returned unauthorized"),
            );
        }
        AdapterError::Timeout => {
            state.upstream_timeout_detected = true;
            state.required_input_unready_count += 1;
            record_blocking_reason(
                state,
                "upstream_timeout",
                "upstream",
                format!("{stage} timed out"),
            );
        }
        AdapterError::SchemaDrift | AdapterError::InvalidData(_) => {
            state.response_shape_drift_detected = true;
            state.summary_contract_invalid_count += 1;
            record_blocking_reason(
                state,
                "response_shape_drift",
                "summary_contract",
                format!("{stage} drifted: {error}"),
            );
        }
        AdapterError::Unavailable | AdapterError::RateLimited | AdapterError::NotFound => {
            state.required_input_unready_count += 1;
            record_blocking_reason(
                state,
                "required_inputs_unready",
                "gating",
                format!("{stage} failed: {error}"),
            );
        }
        AdapterError::Conflict => {
            state.replay_sensitive_inconsistency_detected = true;
            state.summary_contract_invalid_count += 1;
            record_blocking_reason(
                state,
                "replay_sensitive_inconsistency",
                "security",
                format!("{stage} reported conflict"),
            );
        }
    }
}

fn apply_deployment_error(state: &mut SummaryState, stage: &str, error: &DeploymentError) {
    match error {
        DeploymentError::RemoteBackendUnavailable(detail) => {
            state.remote_backend_unavailable_detected = true;
            state.required_input_unready_count += 1;
            record_blocking_reason(
                state,
                "remote_backend_unavailable",
                "deployment",
                format!("{stage}: {detail}"),
            );
        }
        DeploymentError::RemoteStoreAuthMismatch(detail) => {
            state.remote_store_auth_mismatch_detected = true;
            state.required_input_unready_count += 1;
            record_blocking_reason(
                state,
                "remote_store_auth_mismatch",
                "deployment",
                format!("{stage}: {detail}"),
            );
        }
        DeploymentError::HealthCheckDrift(detail) => {
            state.health_check_drift_detected = true;
            state.summary_contract_invalid_count += 1;
            record_blocking_reason(
                state,
                "health_check_drift",
                "summary_contract",
                format!("{stage}: {detail}"),
            );
        }
        DeploymentError::StartupOrderingFailure(detail) => {
            state.startup_ordering_failure_detected = true;
            state.required_input_unready_count += 1;
            record_blocking_reason(
                state,
                "startup_ordering_failure",
                "deployment",
                format!("{stage}: {detail}"),
            );
        }
        DeploymentError::IncompatibleContract(detail) => {
            state.incompatible_contract_detected = true;
            state.summary_contract_invalid_count += 1;
            record_blocking_reason(
                state,
                "incompatible_contract",
                "bridge_contract",
                format!("{stage}: {detail}"),
            );
        }
    }
}

fn mark_incompatible_contract(state: &mut SummaryState, key: &str, detail: String) {
    state.incompatible_contract_detected = true;
    state.summary_contract_invalid_count += 1;
    record_blocking_reason(state, key, "bridge_contract", detail);
}

fn record_blocking_reason(
    state: &mut SummaryState,
    key: &str,
    family: &str,
    detail: impl Into<String>,
) {
    *state
        .blocking_reason_key_counts
        .entry(key.to_owned())
        .or_insert(0) += 1;
    *state
        .blocking_reason_family_counts
        .entry(family.to_owned())
        .or_insert(0) += 1;
    state
        .blocking_reasons
        .push(format!("{key}: {}", detail.into()));
}

#[derive(Debug)]
struct DeploymentRealityEvidence {
    store_scope_shared_durable_passed: bool,
    store_health_check_passed: bool,
    startup_ordering_passed: bool,
    public_flow: BridgeFlowEvidence,
    shutdown_passed: bool,
}

#[derive(Debug)]
enum DeploymentError {
    RemoteBackendUnavailable(String),
    RemoteStoreAuthMismatch(String),
    HealthCheckDrift(String),
    StartupOrderingFailure(String),
    IncompatibleContract(String),
}

#[derive(Debug)]
enum UnauthorizedPrimaryFailure {
    UnexpectedFailover,
    BackendUnavailable(String),
    Unexpected(String),
}

async fn run_positive_deployment_reality_check(
    adapter: &HttpRemnawaveAdapter,
    config: &ResolvedConfig,
) -> Result<DeploymentRealityEvidence, DeploymentError> {
    let bootstrap_subject = config
        .bootstrap_subject
        .as_deref()
        .expect("checked above for missing inputs");
    let webhook_signature = config
        .webhook_signature
        .as_deref()
        .expect("checked above for missing inputs");
    let store_auth_token = config
        .store_auth_token
        .as_deref()
        .expect("checked above for missing inputs");
    let store_path = temporary_sqlite_store_path("supported-upstream-deployment-reality");

    let result = async {
        let store_router = build_store_service_router(store_path.as_path(), store_auth_token)
            .map_err(|error| {
                DeploymentError::StartupOrderingFailure(format!(
                    "failed to build store service router: {error:#}"
                ))
            })?;
        let store_runtime =
            spawn_managed_router("supported-upstream deployment store service", store_router)
                .await
                .map_err(|error| {
                    DeploymentError::StartupOrderingFailure(format!(
                        "failed to spawn store service router: {error:#}"
                    ))
                })?;

        let health = request_store_health_until_ready(&store_runtime.base_url, store_auth_token)
            .await
            .map_err(|error| {
                DeploymentError::RemoteBackendUnavailable(format!(
                    "store health did not become ready: {error}"
                ))
            })?;
        let health_body: BridgeStoreServiceHealthResponse =
            health.json().await.map_err(|error| {
                DeploymentError::HealthCheckDrift(format!(
                    "store health response failed to parse: {error}"
                ))
            })?;
        if health_body.deployment_scope != ns_storage::BridgeStoreDeploymentScope::SharedDurable {
            return Err(DeploymentError::HealthCheckDrift(format!(
                "expected shared_durable deployment scope, got {:?}",
                health_body.deployment_scope
            )));
        }
        if health_body.status != "ok" {
            return Err(DeploymentError::HealthCheckDrift(format!(
                "expected status ok, got {}",
                health_body.status
            )));
        }

        let remote_store = open_service_backed_shared_store(
            store_runtime.base_url.clone(),
            store_auth_token,
            config.request_timeout_ms,
            &[],
        )
        .await?;
        let public_router =
            build_bridge_router_over_store(adapter.clone(), remote_store, webhook_signature)
                .map_err(|error| {
                    DeploymentError::IncompatibleContract(format!(
                        "failed to build public bridge router: {error:#}"
                    ))
                })?;
        let public_runtime =
            spawn_managed_router("supported-upstream deployment public bridge", public_router)
                .await
                .map_err(|error| {
                    DeploymentError::StartupOrderingFailure(format!(
                        "failed to spawn public bridge router: {error:#}"
                    ))
                })?;

        let public_flow = exercise_public_bridge_flow_over_http(
            public_runtime.base_url.as_str(),
            bootstrap_subject,
        )
        .await
        .map_err(|error| {
            DeploymentError::IncompatibleContract(format!("public bridge flow failed: {error:#}"))
        })?;

        let public_base_url = public_runtime.base_url.clone();
        public_runtime.shutdown().await;
        let shutdown_error = reqwest::Client::new()
            .get(format!(
                "{public_base_url}/v0/manifest?subscription_token={bootstrap_subject}"
            ))
            .send()
            .await;
        let shutdown_passed = shutdown_error.is_err();

        store_runtime.shutdown().await;

        Ok(DeploymentRealityEvidence {
            store_scope_shared_durable_passed: true,
            store_health_check_passed: true,
            startup_ordering_passed: true,
            public_flow,
            shutdown_passed,
        })
    }
    .await;

    cleanup_sqlite_store_path(store_path.as_path());
    result
}

async fn run_remote_store_auth_mismatch_check(config: &ResolvedConfig) -> Result<(), String> {
    let store_auth_token = config
        .store_auth_token
        .as_deref()
        .expect("checked above for missing inputs");
    let store_path = temporary_sqlite_store_path("supported-upstream-deployment-auth-mismatch");
    let result = async {
        let store_router = build_store_service_router(store_path.as_path(), store_auth_token)
            .map_err(|error| format!("failed to build store service router: {error:#}"))?;
        let store_runtime = spawn_managed_router(
            "supported-upstream deployment auth mismatch store",
            store_router,
        )
        .await
        .map_err(|error| format!("failed to spawn store service router: {error:#}"))?;

        let result = match open_service_backed_shared_store(
            store_runtime.base_url.clone(),
            "wrong-secret",
            config.request_timeout_ms,
            &[],
        )
        .await
        {
            Ok(_) => Err(
                "remote store health unexpectedly succeeded with the wrong auth token".to_owned(),
            ),
            Err(DeploymentError::RemoteStoreAuthMismatch(_)) => Ok(()),
            Err(other) => Err(format!("unexpected auth mismatch outcome: {other:?}")),
        };

        store_runtime.shutdown().await;
        result
    }
    .await;

    cleanup_sqlite_store_path(store_path.as_path());
    result
}

async fn run_unauthorized_primary_no_failover_check(
    config: &ResolvedConfig,
) -> Result<(), UnauthorizedPrimaryFailure> {
    let store_auth_token = config
        .store_auth_token
        .as_deref()
        .expect("checked above for missing inputs");
    let primary_path = temporary_sqlite_store_path("supported-upstream-primary-unauthorized");
    let secondary_path = temporary_sqlite_store_path("supported-upstream-secondary-healthy");
    let result = async {
        let primary_router = build_store_service_router(primary_path.as_path(), "wrong-secret")
            .map_err(|error| UnauthorizedPrimaryFailure::Unexpected(error.to_string()))?;
        let secondary_router = build_store_service_router(secondary_path.as_path(), store_auth_token)
            .map_err(|error| UnauthorizedPrimaryFailure::Unexpected(error.to_string()))?;
        let primary_runtime = spawn_managed_router(
            "supported-upstream deployment unauthorized primary",
            primary_router,
        )
        .await
        .map_err(|error| UnauthorizedPrimaryFailure::BackendUnavailable(error.to_string()))?;
        let secondary_runtime = spawn_managed_router(
            "supported-upstream deployment healthy secondary",
            secondary_router,
        )
        .await
        .map_err(|error| UnauthorizedPrimaryFailure::BackendUnavailable(error.to_string()))?;

        let mut service_config = ServiceBackedBridgeStoreConfig::new(
            primary_runtime.base_url.clone(),
            config.request_timeout_ms,
        )
        .map_err(|error| UnauthorizedPrimaryFailure::Unexpected(error.to_string()))?
        .with_auth_token(store_auth_token)
        .map_err(|error| UnauthorizedPrimaryFailure::Unexpected(error.to_string()))?
        .with_fallback_endpoint(secondary_runtime.base_url.clone())
        .map_err(|error| UnauthorizedPrimaryFailure::Unexpected(error.to_string()))?;
        service_config = service_config.clone();
        let store = ServiceBackedBridgeStore::new(
            service_config,
            Arc::new(HttpServiceBackedBridgeStoreAdapter::default()),
        );

        let result = match store.check_health().await {
            Ok(()) => Err(UnauthorizedPrimaryFailure::UnexpectedFailover),
            Err(StorageError::ServiceResponseStatus {
                operation: "check_health",
                status: 401,
                ..
            }) => Ok(()),
            Err(StorageError::ServiceBackendUnavailable {
                operation: "check_health",
                ..
            }) => {
                Err(UnauthorizedPrimaryFailure::BackendUnavailable(
                    "health check backend was unavailable before the unauthorized primary response was observed"
                        .to_owned(),
                ))
            }
            Err(error) => Err(UnauthorizedPrimaryFailure::Unexpected(format!(
                "expected HTTP 401 from unauthorized primary endpoint, got {error}"
            ))),
        };

        secondary_runtime.shutdown().await;
        primary_runtime.shutdown().await;
        result
    }
    .await;

    cleanup_sqlite_store_path(primary_path.as_path());
    cleanup_sqlite_store_path(secondary_path.as_path());
    result
}

fn build_store_service_router(path: &Path, auth_token: &str) -> anyhow::Result<Router> {
    let store = SharedBridgeStore::new(SqliteBridgeStore::open(path)?);
    Ok(build_service_backed_bridge_store_router(
        store,
        Some(auth_token.to_owned()),
    ))
}

async fn open_service_backed_shared_store(
    endpoint: String,
    auth_token: &str,
    timeout_ms: u64,
    fallback_endpoints: &[String],
) -> Result<SharedBridgeStore, DeploymentError> {
    let mut config = ServiceBackedBridgeStoreConfig::new(endpoint, timeout_ms)
        .map_err(|error| DeploymentError::IncompatibleContract(error.to_string()))?
        .with_auth_token(auth_token)
        .map_err(|error| DeploymentError::IncompatibleContract(error.to_string()))?;
    for fallback_endpoint in fallback_endpoints {
        config = config
            .with_fallback_endpoint(fallback_endpoint.clone())
            .map_err(|error| DeploymentError::IncompatibleContract(error.to_string()))?;
    }
    let backend = ServiceBackedBridgeStore::new(
        config.clone(),
        Arc::new(HttpServiceBackedBridgeStoreAdapter::default()),
    );
    backend.check_health().await.map_err(|error| match error {
        StorageError::ServiceResponseStatus { status: 401, .. }
        | StorageError::ServiceResponseStatus { status: 403, .. } => {
            DeploymentError::RemoteStoreAuthMismatch(error.to_string())
        }
        StorageError::ServiceBackendUnavailable { .. } | StorageError::ServiceRequest { .. } => {
            DeploymentError::RemoteBackendUnavailable(error.to_string())
        }
        StorageError::UnexpectedServiceResponse { .. } => {
            DeploymentError::HealthCheckDrift(error.to_string())
        }
        _ => DeploymentError::IncompatibleContract(error.to_string()),
    })?;
    Ok(SharedBridgeStore::new(backend))
}

fn build_bridge_router_over_store(
    adapter: HttpRemnawaveAdapter,
    store: SharedBridgeStore,
    webhook_signature: &str,
) -> anyhow::Result<Router> {
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

async fn request_store_health_until_ready(
    store_endpoint: &str,
    auth_token: &str,
) -> Result<reqwest::Response, String> {
    let client = reqwest::Client::new();
    let url = format!("{store_endpoint}/internal/store/v1/health");
    let mut last_outcome = None;

    for _ in 0..12 {
        match client.get(&url).bearer_auth(auth_token).send().await {
            Ok(response) if response.status() == reqwest::StatusCode::OK => return Ok(response),
            Ok(response) => {
                last_outcome = Some(format!("unexpected status {}", response.status()));
            }
            Err(error) => {
                last_outcome = Some(error.to_string());
            }
        }
        tokio::time::sleep(std::time::Duration::from_millis(25)).await;
    }

    Err(last_outcome.unwrap_or_else(|| "unknown readiness failure".to_owned()))
}

async fn exercise_public_bridge_flow_over_http(
    base_url: &str,
    bootstrap_subject: &str,
) -> anyhow::Result<BridgeFlowEvidence> {
    let client = reqwest::Client::new();
    let manifest_response = client
        .get(format!(
            "{base_url}/v0/manifest?subscription_token={bootstrap_subject}"
        ))
        .send()
        .await
        .context("bootstrap manifest request failed")?;
    anyhow::ensure!(
        manifest_response.status() == reqwest::StatusCode::OK,
        "bootstrap manifest returned {}",
        manifest_response.status()
    );
    let manifest: ManifestDocument = manifest_response
        .json()
        .await
        .context("bootstrap manifest response should parse")?;
    let bootstrap_credential = manifest
        .refresh
        .as_ref()
        .map(|refresh| refresh.credential.clone())
        .context("bootstrap manifest did not include a refresh credential")?;

    let register_response = client
        .post(format!("{base_url}/v0/device/register"))
        .bearer_auth(&bootstrap_credential)
        .json(&json!({
            "manifest_id": manifest.manifest_id,
            "device_id": "device-1",
            "device_name": "Workstation",
            "platform": "windows",
            "client_version": "0.1.0",
            "install_channel": "stable",
            "requested_capabilities": [1, 2],
        }))
        .send()
        .await
        .context("device register request failed")?;
    anyhow::ensure!(
        register_response.status() == reqwest::StatusCode::OK,
        "device register returned {}",
        register_response.status()
    );
    let register: DeviceRegisterResponse = register_response
        .json()
        .await
        .context("device register response should parse")?;
    let refresh_credential = register
        .refresh_credential
        .clone()
        .context("device register did not issue a refresh credential")?;

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
        .context("token exchange request failed")?;
    anyhow::ensure!(
        exchange_response.status() == reqwest::StatusCode::OK,
        "token exchange returned {}",
        exchange_response.status()
    );
    let exchange: TokenExchangeResponse = exchange_response
        .json()
        .await
        .context("token exchange response should parse")?;
    anyhow::ensure!(
        !exchange.session_token.is_empty(),
        "token exchange returned an empty session token"
    );

    let refresh_manifest = client
        .get(format!("{base_url}/v0/manifest"))
        .bearer_auth(&refresh_credential)
        .send()
        .await
        .context("refresh manifest request failed")?;
    anyhow::ensure!(
        refresh_manifest.status() == reqwest::StatusCode::OK,
        "refresh manifest returned {}",
        refresh_manifest.status()
    );
    let refresh_etag = refresh_manifest
        .headers()
        .get(ETAG)
        .and_then(|value| value.to_str().ok())
        .context("refresh manifest did not expose an etag")?;

    let conditional = client
        .get(format!("{base_url}/v0/manifest"))
        .bearer_auth(&refresh_credential)
        .header("if-none-match", refresh_etag)
        .send()
        .await
        .context("conditional refresh manifest request failed")?;
    anyhow::ensure!(
        matches!(
            conditional.status(),
            reqwest::StatusCode::OK | reqwest::StatusCode::NOT_MODIFIED
        ),
        "conditional refresh returned {}",
        conditional.status()
    );

    Ok(BridgeFlowEvidence {
        manifest_bootstrap_passed: true,
        device_register_passed: true,
        token_exchange_passed: true,
        manifest_refresh_passed: true,
    })
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
        .context("failed to encode deployment-reality token signer")?;
    SessionTokenSigner::from_ed_pem(
        "bridge.example",
        "northstar-gateway",
        FIXTURE_TOKEN_KEY_ID,
        pem.as_bytes(),
    )
    .map_err(anyhow::Error::from)
}

async fn spawn_managed_router(service_name: &str, router: Router) -> anyhow::Result<ManagedRouter> {
    let listener = TcpListener::bind("127.0.0.1:0").await?;
    let addr = listener.local_addr()?;
    let (shutdown_tx, shutdown_rx) = oneshot::channel::<()>();
    let name = service_name.to_owned();
    let task = tokio::spawn(async move {
        axum::serve(listener, router)
            .with_graceful_shutdown(async move {
                let _ = shutdown_rx.await;
            })
            .await
            .unwrap_or_else(|error| {
                panic!("{name} should serve while the harness is active: {error}")
            });
    });
    tokio::time::sleep(std::time::Duration::from_millis(10)).await;
    Ok(ManagedRouter {
        base_url: format!("http://{addr}"),
        shutdown: Some(shutdown_tx),
        task,
    })
}

fn parse_args<I>(args: I) -> Result<DeploymentRealityArgs, Box<dyn std::error::Error>>
where
    I: IntoIterator<Item = String>,
{
    let mut parsed = DeploymentRealityArgs::default();
    let mut iter = args.into_iter();

    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--json" => parsed.format = Some(OutputFormat::Json),
            "--text" => parsed.format = Some(OutputFormat::Text),
            "--summary-path" => {
                parsed.summary_path = Some(PathBuf::from(next_value(&mut iter, &arg)?))
            }
            "--base-url" => parsed.base_url = Some(next_value(&mut iter, &arg)?),
            "--api-token" => parsed.api_token = Some(next_value(&mut iter, &arg)?),
            "--bootstrap-subject" => parsed.bootstrap_subject = Some(next_value(&mut iter, &arg)?),
            "--webhook-signature" => parsed.webhook_signature = Some(next_value(&mut iter, &arg)?),
            "--expected-account-id" => {
                parsed.expected_account_id = Some(next_value(&mut iter, &arg)?)
            }
            "--store-auth-token" => parsed.store_auth_token = Some(next_value(&mut iter, &arg)?),
            "--supported-upstream-summary" => {
                parsed.upstream_summary_path = Some(PathBuf::from(next_value(&mut iter, &arg)?))
            }
            "--supported-upstream-lifecycle-summary" => {
                parsed.lifecycle_summary_path = Some(PathBuf::from(next_value(&mut iter, &arg)?))
            }
            "--request-timeout-ms" => {
                parsed.request_timeout_ms = Some(next_value(&mut iter, &arg)?.parse()?)
            }
            "--max-snapshot-age-seconds" => {
                parsed.max_snapshot_age_seconds = Some(next_value(&mut iter, &arg)?.parse()?)
            }
            other => return Err(format!("unrecognized argument: {other}").into()),
        }
    }

    Ok(parsed)
}

fn next_value<I>(iter: &mut I, flag: &str) -> Result<String, Box<dyn std::error::Error>>
where
    I: Iterator<Item = String>,
{
    iter.next()
        .ok_or_else(|| format!("expected a value after {flag}").into())
}

fn resolve_config(args: DeploymentRealityArgs) -> ResolvedConfig {
    ResolvedConfig {
        format: args.format.unwrap_or(OutputFormat::Text),
        summary_path: args
            .summary_path
            .or_else(|| {
                env::var("NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_REALITY_SUMMARY_PATH")
                    .ok()
                    .map(PathBuf::from)
            })
            .unwrap_or_else(default_summary_path),
        base_url: args
            .base_url
            .or_else(|| env::var("NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_BASE_URL").ok()),
        api_token: args
            .api_token
            .or_else(|| env::var("NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_API_TOKEN").ok()),
        bootstrap_subject: args
            .bootstrap_subject
            .or_else(|| env::var("NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_BOOTSTRAP_SUBJECT").ok()),
        webhook_signature: args
            .webhook_signature
            .or_else(|| env::var("NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_WEBHOOK_SIGNATURE").ok()),
        source_version_override: args
            .source_version_override
            .or_else(|| env::var("NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_SOURCE_VERSION").ok()),
        expected_account_id: args.expected_account_id.or_else(|| {
            env::var("NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_ACCOUNT_ID").ok()
        }),
        store_auth_token: args
            .store_auth_token
            .or_else(|| env::var("NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_STORE_AUTH_TOKEN").ok()),
        upstream_summary_path: args
            .upstream_summary_path
            .or_else(|| {
                env::var("NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_SUMMARY_INPUT_PATH")
                    .ok()
                    .map(PathBuf::from)
            })
            .unwrap_or_else(default_supported_upstream_summary_path),
        lifecycle_summary_path: args
            .lifecycle_summary_path
            .or_else(|| {
                env::var("NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_LIFECYCLE_SUMMARY_INPUT_PATH")
                    .ok()
                    .map(PathBuf::from)
            })
            .unwrap_or_else(default_lifecycle_summary_path),
        request_timeout_ms: args.request_timeout_ms.unwrap_or(1_500),
        max_snapshot_age_seconds: args.max_snapshot_age_seconds.unwrap_or(300),
    }
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

fn print_text_summary(summary: &SupportedUpstreamDeploymentRealitySummary, summary_path: &Path) {
    println!("Northstar Supported Upstream Deployment Reality Verification");
    println!("- verdict: {}", summary.verdict);
    println!("- gate_state: {}", summary.gate_state);
    println!("- gate_state_reason: {}", summary.gate_state_reason);
    println!("- deployment_state: {}", summary.deployment_state);
    println!(
        "- control_plane_issuance_only: {}",
        summary.control_plane_issuance_only
    );
    println!(
        "- supported_upstream_deployment_reality_passed: {:?}",
        summary.supported_upstream_deployment_reality_passed
    );
    println!(
        "- deployment_store_scope_shared_durable_passed: {:?}",
        summary.deployment_store_scope_shared_durable_passed
    );
    println!(
        "- deployment_store_health_check_passed: {:?}",
        summary.deployment_store_health_check_passed
    );
    println!(
        "- deployment_remote_store_auth_mismatch_rejected: {:?}",
        summary.deployment_remote_store_auth_mismatch_rejected
    );
    println!(
        "- deployment_unauthorized_primary_no_failover_passed: {:?}",
        summary.deployment_unauthorized_primary_no_failover_passed
    );
    println!(
        "- prior_supported_upstream_summary_passed: {:?}",
        summary.prior_supported_upstream_summary_passed
    );
    println!(
        "- prior_lifecycle_summary_passed: {:?}",
        summary.prior_lifecycle_summary_passed
    );
    println!("- summary_path: {}", summary_path.display());
}

fn default_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("remnawave-supported-upstream-deployment-reality-summary.json")
}

fn default_supported_upstream_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("remnawave-supported-upstream-summary.json")
}

fn default_lifecycle_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("remnawave-supported-upstream-lifecycle-summary.json")
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
        .join(format!("{unique}.sqlite3"))
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
            Err(error) => panic!("failed to remove {}: {error}", candidate.display()),
        }
    }
}

fn parse_numeric_segment(value: &str) -> Option<u64> {
    if value.is_empty() {
        return None;
    }
    value
        .chars()
        .take_while(|ch| ch.is_ascii_digit())
        .collect::<String>()
        .parse()
        .ok()
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::Json;
    use axum::extract::Path as AxumPath;
    use axum::extract::State;
    use axum::http::HeaderMap;
    use axum::http::StatusCode;
    use axum::http::header::AUTHORIZATION;
    use axum::routing::{get, post};
    use ns_remnawave_adapter::{AccountLifecycle, AccountSnapshot, NorthstarAccess};
    use std::fs;
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
            lifecycle: AccountLifecycle::Active,
            northstar_access: NorthstarAccess {
                northstar_enabled: true,
                policy_epoch: 7,
                device_limit: Some(4),
                allowed_core_versions: vec![1],
                allowed_carrier_profiles: vec!["carrier-primary".to_owned()],
                allowed_capabilities: vec![1, 2],
                rollout_cohort: Some("stable".to_owned()),
                preferred_regions: vec!["eu-central".to_owned()],
            },
            metadata: Some(json!({ "plan": "pro" })),
            observed_at_unix: OffsetDateTime::now_utc().unix_timestamp() - 30,
            source_version: Some(version.to_owned()),
        }
    }

    async fn resolve_user(
        State(state): State<Arc<TestUpstreamState>>,
        headers: HeaderMap,
        Json(request): Json<ResolveBootstrapRequest>,
    ) -> Result<Json<AccountSnapshot>, StatusCode> {
        if !authorized(&headers, &state.expected_token) {
            return Err(StatusCode::UNAUTHORIZED);
        }
        if request.bootstrap_subject_kind != "short_uuid" || request.bootstrap_subject != "sub-1" {
            return Err(StatusCode::NOT_FOUND);
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
    ) -> Result<Json<AccountSnapshot>, StatusCode> {
        if !authorized(&headers, &state.expected_token) {
            return Err(StatusCode::UNAUTHORIZED);
        }
        let snapshot = state
            .snapshot
            .lock()
            .expect("test upstream state poisoned")
            .clone();
        if snapshot.account_id != account_id {
            return Err(StatusCode::NOT_FOUND);
        }
        Ok(Json(snapshot))
    }

    async fn spawn_test_upstream(snapshot: AccountSnapshot) -> ManagedRouter {
        let state = Arc::new(TestUpstreamState {
            snapshot: Mutex::new(snapshot),
            expected_token: "rw-token".to_owned(),
        });
        let router = Router::new()
            .route("/api/users/resolve", post(resolve_user))
            .route("/api/users/{account_id}", get(get_user))
            .with_state(state);
        spawn_managed_router("test supported upstream", router)
            .await
            .expect("test upstream router should spawn")
    }

    fn write_prior_summary(path: &Path, key: &str) {
        let json = match key {
            "supported_upstream_compatibility_passed" => json!({
                "gate_state": "passed",
                "gate_state_reason": "all_required_inputs_passed",
                "all_required_inputs_passed": true,
                "blocking_reason_keys": [],
                "supported_upstream_compatibility_passed": true
            }),
            "supported_upstream_lifecycle_passed" => json!({
                "gate_state": "passed",
                "gate_state_reason": "all_required_inputs_passed",
                "all_required_inputs_passed": true,
                "blocking_reason_keys": [],
                "supported_upstream_lifecycle_passed": true
            }),
            _ => unreachable!("unsupported prior summary key"),
        };
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).expect("summary parent should exist");
        }
        fs::write(
            path,
            serde_json::to_vec_pretty(&json).expect("summary should serialize"),
        )
        .expect("summary should write");
    }

    fn test_config(
        base_url: Option<String>,
        api_token: Option<String>,
        upstream_summary_path: PathBuf,
        lifecycle_summary_path: PathBuf,
    ) -> ResolvedConfig {
        ResolvedConfig {
            format: OutputFormat::Json,
            summary_path: default_summary_path(),
            base_url,
            api_token,
            bootstrap_subject: Some("sub-1".to_owned()),
            webhook_signature: Some("sig-ok".to_owned()),
            source_version_override: None,
            expected_account_id: Some("acct-1".to_owned()),
            store_auth_token: Some("store-secret".to_owned()),
            upstream_summary_path,
            lifecycle_summary_path,
            request_timeout_ms: 500,
            max_snapshot_age_seconds: 300,
        }
    }

    #[tokio::test]
    async fn deployment_reality_summary_is_ready_for_supported_fixture_server() {
        let upstream_summary_path =
            temporary_sqlite_store_path("supported-upstream-summary-input").with_extension("json");
        let lifecycle_summary_path =
            temporary_sqlite_store_path("supported-upstream-lifecycle-input")
                .with_extension("json");
        write_prior_summary(
            upstream_summary_path.as_path(),
            "supported_upstream_compatibility_passed",
        );
        write_prior_summary(
            lifecycle_summary_path.as_path(),
            "supported_upstream_lifecycle_passed",
        );

        let runtime = spawn_test_upstream(supported_snapshot("2.7.4")).await;
        let summary = build_supported_upstream_deployment_reality_summary(&test_config(
            Some(runtime.base_url.clone()),
            Some("rw-token".to_owned()),
            upstream_summary_path.clone(),
            lifecycle_summary_path.clone(),
        ))
        .await;

        assert_eq!(summary.verdict, "ready");
        assert_eq!(summary.gate_state, "passed");
        assert_eq!(summary.gate_state_reason, "all_required_inputs_passed");
        assert_eq!(summary.control_plane_issuance_only, true);
        assert_eq!(
            summary.supported_upstream_deployment_reality_passed,
            Some(true)
        );
        assert_eq!(
            summary.deployment_store_scope_shared_durable_passed,
            Some(true)
        );
        assert_eq!(summary.deployment_store_health_check_passed, Some(true));
        assert_eq!(
            summary.deployment_remote_store_auth_mismatch_rejected,
            Some(true)
        );
        assert_eq!(
            summary.deployment_unauthorized_primary_no_failover_passed,
            Some(true)
        );

        runtime.shutdown().await;
        let _ = fs::remove_file(upstream_summary_path);
        let _ = fs::remove_file(lifecycle_summary_path);
    }

    #[tokio::test]
    async fn deployment_reality_summary_holds_when_environment_is_missing() {
        let summary = build_supported_upstream_deployment_reality_summary(&ResolvedConfig {
            format: OutputFormat::Json,
            summary_path: default_summary_path(),
            base_url: None,
            api_token: None,
            bootstrap_subject: None,
            webhook_signature: None,
            source_version_override: None,
            expected_account_id: None,
            store_auth_token: None,
            upstream_summary_path: default_supported_upstream_summary_path(),
            lifecycle_summary_path: default_lifecycle_summary_path(),
            request_timeout_ms: 500,
            max_snapshot_age_seconds: 300,
        })
        .await;

        assert_eq!(summary.verdict, "hold");
        assert_eq!(summary.evidence_state, "incomplete");
        assert_eq!(summary.gate_state_reason, "missing_required_inputs");
        assert_eq!(summary.supported_upstream_environment_present, false);
        assert!(summary.missing_required_input_count >= 6);
    }
}
