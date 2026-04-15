#![recursion_limit = "256"]

use anyhow::Context;
use base64::Engine as _;
use clap::{ArgAction, Parser, Subcommand, ValueEnum};
use ed25519_dalek::SigningKey;
use ed25519_dalek::pkcs8::EncodePrivateKey;
use ns_auth::{MintedTokenRequest, SessionTokenSigner};
use ns_carrier_h3::{H3DatagramRollout, resolve_h3_datagram_startup_contract};
use ns_client_runtime::{
    ClientDatagramStartupContract, ClientLaunchPlan, ClientNegotiatedDatagramContractInput,
    ClientRuntimeConfig, build_launch_plan,
};
use ns_core::{
    Capability, CarrierKind, CarrierProfileId, DatagramMode, DeviceBindingId, ManifestId,
    UDP_VALIDATION_COMPARISON_FAMILY, UDP_VALIDATION_COMPARISON_PROFILE,
    UDP_VALIDATION_COMPARISON_SCHEMA, UDP_VALIDATION_COMPARISON_SCHEMA_VERSION,
    UDP_VALIDATION_COMPARISON_SCOPE,
};
use ns_observability::init_tracing;
use ns_wire::{ClientHello, Frame, FrameCodec};
use time::{Duration, OffsetDateTime};
use tracing::info;
use url::Url;

#[derive(Parser)]
#[command(name = "verta")]
struct Cli {
    #[arg(long, default_value_t = false)]
    json_logs: bool,
    #[arg(long, value_enum, default_value_t = OutputFormatArg::Text)]
    output: OutputFormatArg,
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    PlanClient {
        #[arg(long)]
        manifest: std::path::PathBuf,
        #[arg(long)]
        manifest_public_key_pem: std::path::PathBuf,
        #[arg(long)]
        manifest_key_id: String,
        #[arg(long, default_value = "https://bridge.example/v0/manifest")]
        manifest_url: String,
        #[arg(long, default_value = "device-1")]
        device_id: String,
        #[arg(long, default_value = "carrier-primary")]
        carrier_profile_id: String,
        #[arg(long, default_value = "0.1.0")]
        client_version: String,
        #[arg(long, value_enum, default_value_t = DatagramRolloutArg::Disabled)]
        datagram_rollout: DatagramRolloutArg,
        #[arg(long, action = ArgAction::Set, num_args = 0..=1, default_missing_value = "true", default_value_t = false)]
        carrier_datagrams_available: bool,
    },
    ValidateDatagramStartup {
        #[arg(long)]
        manifest: std::path::PathBuf,
        #[arg(long)]
        manifest_public_key_pem: std::path::PathBuf,
        #[arg(long)]
        manifest_key_id: String,
        #[arg(long, default_value = "https://bridge.example/v0/manifest")]
        manifest_url: String,
        #[arg(long, default_value = "device-1")]
        device_id: String,
        #[arg(long, default_value = "carrier-primary")]
        carrier_profile_id: String,
        #[arg(long, default_value = "0.1.0")]
        client_version: String,
        #[arg(long, value_enum, default_value_t = DatagramRolloutArg::Disabled)]
        datagram_rollout: DatagramRolloutArg,
        #[arg(long, action = ArgAction::Set, num_args = 0..=1, default_missing_value = "true", default_value_t = false)]
        carrier_datagrams_available: bool,
    },
    ValidateGatewayDatagramStartup {
        #[arg(long, action = ArgAction::Set, num_args = 0..=1, default_missing_value = "true", default_value_t = true)]
        signed_datagram_enabled: bool,
        #[arg(long, value_enum, default_value_t = DatagramRolloutArg::Disabled)]
        datagram_rollout: DatagramRolloutArg,
        #[arg(long, action = ArgAction::Set, num_args = 0..=1, default_missing_value = "true", default_value_t = false)]
        carrier_datagrams_available: bool,
    },
    ValidateDatagramContract {
        #[arg(long)]
        manifest: std::path::PathBuf,
        #[arg(long)]
        manifest_public_key_pem: std::path::PathBuf,
        #[arg(long)]
        manifest_key_id: String,
        #[arg(long, default_value = "https://bridge.example/v0/manifest")]
        manifest_url: String,
        #[arg(long, default_value = "device-1")]
        device_id: String,
        #[arg(long, default_value = "carrier-primary")]
        carrier_profile_id: String,
        #[arg(long, default_value = "0.1.0")]
        client_version: String,
        #[arg(long, value_enum, default_value_t = DatagramRolloutArg::Disabled)]
        datagram_rollout: DatagramRolloutArg,
        #[arg(long, action = ArgAction::Set, num_args = 0..=1, default_missing_value = "true", default_value_t = false)]
        carrier_datagrams_available: bool,
        #[arg(long, default_value_t = 7)]
        expected_policy_epoch: u64,
        #[arg(long, default_value_t = 4)]
        expected_max_udp_flows: u64,
        #[arg(long, default_value_t = 1200)]
        expected_max_udp_payload: u64,
        #[arg(long, default_value_t = 1200)]
        requested_max_udp_payload: u64,
        #[arg(long)]
        received_policy_epoch: u64,
        #[arg(long, value_enum)]
        received_datagram_mode: DatagramModeArg,
        #[arg(long)]
        received_max_udp_flows: u64,
        #[arg(long)]
        received_effective_max_udp_payload: u64,
    },
    EmitWireHelloFixture {
        #[arg(long, default_value = "fixture-token")]
        token: String,
    },
    PrintDemoTokenJwks,
    MintDemoSessionToken {
        #[arg(long, default_value = "man-2026-04-01-001")]
        manifest_id: String,
        #[arg(long, default_value = "device-1")]
        device_id: String,
        #[arg(long, default_value = "carrier-primary")]
        carrier_profile_id: String,
        #[arg(long, default_value_t = 7)]
        policy_epoch: u64,
        #[arg(long, default_value_t = 1_700_000_000)]
        now_unix: i64,
        #[arg(long, default_value_t = 300)]
        ttl_seconds: i64,
    },
}

#[derive(Clone, Copy, Debug, ValueEnum)]
enum DatagramRolloutArg {
    Disabled,
    Canary,
    Automatic,
}

impl From<DatagramRolloutArg> for H3DatagramRollout {
    fn from(value: DatagramRolloutArg) -> Self {
        match value {
            DatagramRolloutArg::Disabled => H3DatagramRollout::Disabled,
            DatagramRolloutArg::Canary => H3DatagramRollout::Canary,
            DatagramRolloutArg::Automatic => H3DatagramRollout::Automatic,
        }
    }
}

#[derive(Clone, Copy, Debug, ValueEnum)]
enum DatagramModeArg {
    Unavailable,
    AvailableAndEnabled,
    DisabledByPolicy,
}

#[derive(Clone, Copy, Debug, ValueEnum)]
enum OutputFormatArg {
    Text,
    Json,
}

const CLIENT_PLAN_COMPARISON_LABEL: &str = "client_plan";
const CLIENT_STARTUP_COMPARISON_LABEL: &str = "client_startup_contract";
const CLIENT_NEGOTIATED_COMPARISON_LABEL: &str = "client_negotiated_contract";
const GATEWAY_STARTUP_COMPARISON_LABEL: &str = "gateway_startup_contract";
const VALIDATION_EVIDENCE_STATE_COMPLETE: &str = "complete";
const VALIDATION_GATE_STATE_PASSED: &str = "passed";
const VALIDATION_GATE_STATE_BLOCKED: &str = "blocked";
const VALIDATION_GATE_STATE_REASON_READY: &str = "all_required_inputs_passed";
const VALIDATION_GATE_STATE_REASON_REQUIRED_INPUTS_UNREADY: &str = "required_inputs_unready";
const VALIDATION_GATE_STATE_REASON_FAMILY_READY: &str = "ready";
const VALIDATION_GATE_STATE_REASON_FAMILY_GATING: &str = "gating";
const VALIDATION_VERDICT_READY: &str = "ready";
const VALIDATION_VERDICT_HOLD: &str = "hold";
const VALIDATION_BLOCKING_REASON_NONE: &str = "none";
const VALIDATION_BLOCKING_REASON_FAMILY_NONE: &str = "none";
const VALIDATION_BLOCKING_REASON_FAMILY_VALIDATION: &str = "validation";

impl From<DatagramModeArg> for DatagramMode {
    fn from(value: DatagramModeArg) -> Self {
        match value {
            DatagramModeArg::Unavailable => DatagramMode::Unavailable,
            DatagramModeArg::AvailableAndEnabled => DatagramMode::AvailableAndEnabled,
            DatagramModeArg::DisabledByPolicy => DatagramMode::DisabledByPolicy,
        }
    }
}

async fn load_client_launch_plan(
    manifest: &std::path::Path,
    manifest_public_key_pem: &std::path::Path,
    manifest_key_id: String,
    manifest_url: String,
    device_id: String,
    carrier_profile_id: String,
    client_version: String,
    datagram_rollout: DatagramRolloutArg,
) -> anyhow::Result<ClientLaunchPlan> {
    let manifest_json = tokio::fs::read_to_string(manifest)
        .await
        .with_context(|| format!("failed to read {}", manifest.display()))?;
    let manifest_public_key = tokio::fs::read(manifest_public_key_pem)
        .await
        .with_context(|| format!("failed to read {}", manifest_public_key_pem.display()))?;
    let mut trust_store = ns_manifest::ManifestTrustStore::default();
    trust_store
        .insert_public_key_pem(manifest_key_id, &manifest_public_key)
        .context("failed to initialize manifest trust store from PEM")?;
    build_launch_plan(
        &ClientRuntimeConfig {
            manifest_url: Url::parse(&manifest_url)?,
            device_id: DeviceBindingId::new(device_id)?,
            client_version,
            selected_carrier_profile: CarrierProfileId::new(carrier_profile_id)?,
            datagram_rollout: datagram_rollout.into(),
        },
        &manifest_json,
        &trust_store,
        time::OffsetDateTime::now_utc(),
    )
    .context("failed to build the client launch plan")
}

fn emit_client_startup_contract(command: &str, contract: &ClientDatagramStartupContract) {
    info!(
        event_name = "verta.client.datagram.startup_contract",
        command,
        simulated_inputs = true,
        signed_datagram_enabled = contract.signed_datagram_enabled,
        rollout_stage = contract.rollout_stage,
        carrier_datagrams_available = contract.carrier_datagrams_available,
        expected_server_datagram_mode = ?contract.expected_server_datagram_mode,
        "resolved client startup datagram contract"
    );
}

fn emit_gateway_startup_contract(
    command: &str,
    contract: &ns_carrier_h3::H3DatagramStartupContract,
) {
    info!(
        event_name = "verta.gateway.datagram.startup_contract",
        command,
        simulated_inputs = true,
        signed_datagram_enabled = contract.signed_datagram_enabled,
        rollout_stage = contract.rollout_stage,
        carrier_datagrams_available = contract.carrier_datagrams_available,
        resolved_datagram_mode = ?contract.resolved_datagram_mode,
        "resolved gateway startup datagram contract"
    );
}

fn render_plan_client_output(
    format: OutputFormatArg,
    command: &str,
    plan: &ClientLaunchPlan,
    contract: &ClientDatagramStartupContract,
) -> anyhow::Result<String> {
    match format {
        OutputFormatArg::Text => Ok(format!(
            "{}\nvalidation_result=valid surface=client_plan command={} simulated_inputs=true comparison_schema={} comparison_schema_version={} comparison_family={} comparison_label={} comparison_scope={} comparison_profile={} evidence_state={} gate_state={} gate_state_reason={} gate_state_reason_family={} verdict={} required_input_count=1 required_input_present_count=1 required_input_passed_count=1 required_input_missing_count=0 required_input_failed_count=0 required_input_unready_count=0 all_required_inputs_present=true all_required_inputs_passed=true missing_required_input_count=0 degradation_hold_count=0 blocking_reason_count=0 blocking_reason_key={} blocking_reason_family={}\n{:#?}",
            render_client_startup_output(OutputFormatArg::Text, command, plan, contract)?,
            command,
            UDP_VALIDATION_COMPARISON_SCHEMA,
            UDP_VALIDATION_COMPARISON_SCHEMA_VERSION,
            UDP_VALIDATION_COMPARISON_FAMILY,
            CLIENT_PLAN_COMPARISON_LABEL,
            UDP_VALIDATION_COMPARISON_SCOPE,
            UDP_VALIDATION_COMPARISON_PROFILE,
            VALIDATION_EVIDENCE_STATE_COMPLETE,
            VALIDATION_GATE_STATE_PASSED,
            VALIDATION_GATE_STATE_REASON_READY,
            VALIDATION_GATE_STATE_REASON_FAMILY_READY,
            VALIDATION_VERDICT_READY,
            VALIDATION_BLOCKING_REASON_NONE,
            VALIDATION_BLOCKING_REASON_FAMILY_NONE,
            plan
        )),
        OutputFormatArg::Json => Ok(serde_json::to_string_pretty(&serde_json::json!({
            "validation_result": "valid",
            "surface": "client_plan",
            "command": command,
            "simulated_inputs": true,
            "comparison_schema": UDP_VALIDATION_COMPARISON_SCHEMA,
            "comparison_schema_version": UDP_VALIDATION_COMPARISON_SCHEMA_VERSION,
            "comparison_family": UDP_VALIDATION_COMPARISON_FAMILY,
            "comparison_label": CLIENT_PLAN_COMPARISON_LABEL,
            "comparison_scope": UDP_VALIDATION_COMPARISON_SCOPE,
            "comparison_profile": UDP_VALIDATION_COMPARISON_PROFILE,
            "evidence_state": VALIDATION_EVIDENCE_STATE_COMPLETE,
            "gate_state": VALIDATION_GATE_STATE_PASSED,
            "gate_state_reason": VALIDATION_GATE_STATE_REASON_READY,
            "gate_state_reason_family": VALIDATION_GATE_STATE_REASON_FAMILY_READY,
            "verdict": VALIDATION_VERDICT_READY,
            "required_input_count": 1,
            "required_input_present_count": 1,
            "required_input_passed_count": 1,
            "required_input_missing_count": 0,
            "required_input_failed_count": 0,
            "required_input_unready_count": 0,
            "all_required_inputs_present": true,
            "all_required_inputs_passed": true,
            "missing_required_input_count": 0,
            "degradation_hold_count": 0,
            "blocking_reason_count": 0,
            "blocking_reason_key": VALIDATION_BLOCKING_REASON_NONE,
            "blocking_reason_family": VALIDATION_BLOCKING_REASON_FAMILY_NONE,
            "manifest_id": plan.manifest_id.as_str(),
            "carrier_profile_id": plan.carrier_profile_id.as_str(),
            "endpoint_id": plan.endpoint_id,
            "endpoint_host": plan.endpoint_host,
            "endpoint_port": plan.endpoint_port,
            "transport_origin_host": plan.transport_origin_host,
            "transport_origin_port": plan.transport_origin_port,
            "transport_sni": plan.transport_sni,
            "transport_alpn": plan.transport_alpn,
            "control_path": plan.control_path,
            "relay_path": plan.relay_path,
            "datagram_enabled": plan.datagram_enabled,
            "rollout_stage": contract.rollout_stage,
            "carrier_datagrams_available": contract.carrier_datagrams_available,
            "expected_server_datagram_mode": datagram_mode_label(contract.expected_server_datagram_mode),
        }))?),
    }
}

fn render_client_startup_output(
    format: OutputFormatArg,
    command: &str,
    plan: &ClientLaunchPlan,
    contract: &ClientDatagramStartupContract,
) -> anyhow::Result<String> {
    match format {
        OutputFormatArg::Text => Ok(format!(
            "manifest={} profile={} endpoint={}:{}\nvalidation_result=valid surface=startup_contract command={} simulated_inputs=true comparison_schema={} comparison_schema_version={} comparison_family={} comparison_label={} comparison_scope={} comparison_profile={} evidence_state={} gate_state={} gate_state_reason={} gate_state_reason_family={} verdict={} required_input_count=1 required_input_present_count=1 required_input_passed_count=1 required_input_missing_count=0 required_input_failed_count=0 required_input_unready_count=0 all_required_inputs_present=true all_required_inputs_passed=true missing_required_input_count=0 degradation_hold_count=0 blocking_reason_count=0 blocking_reason_key={} blocking_reason_family={} signed_datagram_enabled={} rollout_stage={} carrier_datagrams_available={} expected_server_datagram_mode={}",
            plan.manifest_id.as_str(),
            plan.carrier_profile_id.as_str(),
            plan.endpoint_host,
            plan.endpoint_port,
            command,
            UDP_VALIDATION_COMPARISON_SCHEMA,
            UDP_VALIDATION_COMPARISON_SCHEMA_VERSION,
            UDP_VALIDATION_COMPARISON_FAMILY,
            CLIENT_STARTUP_COMPARISON_LABEL,
            UDP_VALIDATION_COMPARISON_SCOPE,
            UDP_VALIDATION_COMPARISON_PROFILE,
            VALIDATION_EVIDENCE_STATE_COMPLETE,
            VALIDATION_GATE_STATE_PASSED,
            VALIDATION_GATE_STATE_REASON_READY,
            VALIDATION_GATE_STATE_REASON_FAMILY_READY,
            VALIDATION_VERDICT_READY,
            VALIDATION_BLOCKING_REASON_NONE,
            VALIDATION_BLOCKING_REASON_FAMILY_NONE,
            contract.signed_datagram_enabled,
            contract.rollout_stage,
            contract.carrier_datagrams_available,
            datagram_mode_label(contract.expected_server_datagram_mode),
        )),
        OutputFormatArg::Json => Ok(serde_json::to_string_pretty(&serde_json::json!({
            "validation_result": "valid",
            "surface": "startup_contract",
            "command": command,
            "simulated_inputs": true,
            "comparison_schema": UDP_VALIDATION_COMPARISON_SCHEMA,
            "comparison_schema_version": UDP_VALIDATION_COMPARISON_SCHEMA_VERSION,
            "comparison_family": UDP_VALIDATION_COMPARISON_FAMILY,
            "comparison_label": CLIENT_STARTUP_COMPARISON_LABEL,
            "comparison_scope": UDP_VALIDATION_COMPARISON_SCOPE,
            "comparison_profile": UDP_VALIDATION_COMPARISON_PROFILE,
            "evidence_state": VALIDATION_EVIDENCE_STATE_COMPLETE,
            "gate_state": VALIDATION_GATE_STATE_PASSED,
            "gate_state_reason": VALIDATION_GATE_STATE_REASON_READY,
            "gate_state_reason_family": VALIDATION_GATE_STATE_REASON_FAMILY_READY,
            "verdict": VALIDATION_VERDICT_READY,
            "required_input_count": 1,
            "required_input_present_count": 1,
            "required_input_passed_count": 1,
            "required_input_missing_count": 0,
            "required_input_failed_count": 0,
            "required_input_unready_count": 0,
            "all_required_inputs_present": true,
            "all_required_inputs_passed": true,
            "missing_required_input_count": 0,
            "degradation_hold_count": 0,
            "blocking_reason_count": 0,
            "blocking_reason_key": VALIDATION_BLOCKING_REASON_NONE,
            "blocking_reason_family": VALIDATION_BLOCKING_REASON_FAMILY_NONE,
            "manifest_id": plan.manifest_id.as_str(),
            "carrier_profile_id": plan.carrier_profile_id.as_str(),
            "endpoint_host": plan.endpoint_host,
            "endpoint_port": plan.endpoint_port,
            "signed_datagram_enabled": contract.signed_datagram_enabled,
            "rollout_stage": contract.rollout_stage,
            "carrier_datagrams_available": contract.carrier_datagrams_available,
            "expected_server_datagram_mode": datagram_mode_label(contract.expected_server_datagram_mode),
        }))?),
    }
}

#[allow(clippy::too_many_arguments)]
fn render_client_negotiated_output(
    format: OutputFormatArg,
    command: &str,
    plan: &ClientLaunchPlan,
    startup: &ClientDatagramStartupContract,
    expected_policy_epoch: u64,
    received_policy_epoch: u64,
    expected_max_udp_flows: u64,
    received_max_udp_flows: u64,
    expected_max_udp_payload: u64,
    requested_max_udp_payload: u64,
    received_effective_max_udp_payload: u64,
    received_datagram_mode: DatagramMode,
) -> anyhow::Result<String> {
    match format {
        OutputFormatArg::Text => Ok(format!(
            "manifest={} profile={} endpoint={}:{}\nvalidation_result=valid surface=negotiated_contract command={} simulated_inputs=true comparison_schema={} comparison_schema_version={} comparison_family={} comparison_label={} comparison_scope={} comparison_profile={} evidence_state={} gate_state={} gate_state_reason={} gate_state_reason_family={} verdict={} required_input_count=1 required_input_present_count=1 required_input_passed_count=1 required_input_missing_count=0 required_input_failed_count=0 required_input_unready_count=0 all_required_inputs_present=true all_required_inputs_passed=true missing_required_input_count=0 degradation_hold_count=0 blocking_reason_count=0 blocking_reason_key={} blocking_reason_family={} signed_datagram_enabled={} rollout_stage={} carrier_datagrams_available={} expected_server_datagram_mode={} received_datagram_mode={} expected_policy_epoch={} received_policy_epoch={} expected_max_udp_flows={} received_max_udp_flows={} expected_max_udp_payload={} requested_max_udp_payload={} received_effective_max_udp_payload={}",
            plan.manifest_id.as_str(),
            plan.carrier_profile_id.as_str(),
            plan.endpoint_host,
            plan.endpoint_port,
            command,
            UDP_VALIDATION_COMPARISON_SCHEMA,
            UDP_VALIDATION_COMPARISON_SCHEMA_VERSION,
            UDP_VALIDATION_COMPARISON_FAMILY,
            CLIENT_NEGOTIATED_COMPARISON_LABEL,
            UDP_VALIDATION_COMPARISON_SCOPE,
            UDP_VALIDATION_COMPARISON_PROFILE,
            VALIDATION_EVIDENCE_STATE_COMPLETE,
            VALIDATION_GATE_STATE_PASSED,
            VALIDATION_GATE_STATE_REASON_READY,
            VALIDATION_GATE_STATE_REASON_FAMILY_READY,
            VALIDATION_VERDICT_READY,
            VALIDATION_BLOCKING_REASON_NONE,
            VALIDATION_BLOCKING_REASON_FAMILY_NONE,
            startup.signed_datagram_enabled,
            startup.rollout_stage,
            startup.carrier_datagrams_available,
            datagram_mode_label(startup.expected_server_datagram_mode),
            datagram_mode_label(received_datagram_mode),
            expected_policy_epoch,
            received_policy_epoch,
            expected_max_udp_flows,
            received_max_udp_flows,
            expected_max_udp_payload,
            requested_max_udp_payload,
            received_effective_max_udp_payload,
        )),
        OutputFormatArg::Json => Ok(serde_json::to_string_pretty(&serde_json::json!({
            "validation_result": "valid",
            "surface": "negotiated_contract",
            "command": command,
            "simulated_inputs": true,
            "comparison_schema": UDP_VALIDATION_COMPARISON_SCHEMA,
            "comparison_schema_version": UDP_VALIDATION_COMPARISON_SCHEMA_VERSION,
            "comparison_family": UDP_VALIDATION_COMPARISON_FAMILY,
            "comparison_label": CLIENT_NEGOTIATED_COMPARISON_LABEL,
            "comparison_scope": UDP_VALIDATION_COMPARISON_SCOPE,
            "comparison_profile": UDP_VALIDATION_COMPARISON_PROFILE,
            "evidence_state": VALIDATION_EVIDENCE_STATE_COMPLETE,
            "gate_state": VALIDATION_GATE_STATE_PASSED,
            "gate_state_reason": VALIDATION_GATE_STATE_REASON_READY,
            "gate_state_reason_family": VALIDATION_GATE_STATE_REASON_FAMILY_READY,
            "verdict": VALIDATION_VERDICT_READY,
            "required_input_count": 1,
            "required_input_present_count": 1,
            "required_input_passed_count": 1,
            "required_input_missing_count": 0,
            "required_input_failed_count": 0,
            "required_input_unready_count": 0,
            "all_required_inputs_present": true,
            "all_required_inputs_passed": true,
            "missing_required_input_count": 0,
            "degradation_hold_count": 0,
            "blocking_reason_count": 0,
            "blocking_reason_key": VALIDATION_BLOCKING_REASON_NONE,
            "blocking_reason_family": VALIDATION_BLOCKING_REASON_FAMILY_NONE,
            "manifest_id": plan.manifest_id.as_str(),
            "carrier_profile_id": plan.carrier_profile_id.as_str(),
            "endpoint_host": plan.endpoint_host,
            "endpoint_port": plan.endpoint_port,
            "signed_datagram_enabled": startup.signed_datagram_enabled,
            "rollout_stage": startup.rollout_stage,
            "carrier_datagrams_available": startup.carrier_datagrams_available,
            "expected_server_datagram_mode": datagram_mode_label(startup.expected_server_datagram_mode),
            "received_datagram_mode": datagram_mode_label(received_datagram_mode),
            "expected_policy_epoch": expected_policy_epoch,
            "received_policy_epoch": received_policy_epoch,
            "expected_max_udp_flows": expected_max_udp_flows,
            "received_max_udp_flows": received_max_udp_flows,
            "expected_max_udp_payload": expected_max_udp_payload,
            "requested_max_udp_payload": requested_max_udp_payload,
            "received_effective_max_udp_payload": received_effective_max_udp_payload,
        }))?),
    }
}

fn render_gateway_startup_output(
    format: OutputFormatArg,
    command: &str,
    contract: &ns_carrier_h3::H3DatagramStartupContract,
) -> anyhow::Result<String> {
    match format {
        OutputFormatArg::Text => Ok(format!(
            "validation_result=valid surface=startup_contract command={} simulated_inputs=true comparison_schema={} comparison_schema_version={} comparison_family={} comparison_label={} comparison_scope={} comparison_profile={} evidence_state={} gate_state={} gate_state_reason={} gate_state_reason_family={} verdict={} required_input_count=1 required_input_present_count=1 required_input_passed_count=1 required_input_missing_count=0 required_input_failed_count=0 required_input_unready_count=0 all_required_inputs_present=true all_required_inputs_passed=true missing_required_input_count=0 degradation_hold_count=0 blocking_reason_count=0 blocking_reason_key={} blocking_reason_family={} datagram_mode={} signed_datagram_enabled={} rollout_stage={} carrier_datagrams_available={}",
            command,
            UDP_VALIDATION_COMPARISON_SCHEMA,
            UDP_VALIDATION_COMPARISON_SCHEMA_VERSION,
            UDP_VALIDATION_COMPARISON_FAMILY,
            GATEWAY_STARTUP_COMPARISON_LABEL,
            UDP_VALIDATION_COMPARISON_SCOPE,
            UDP_VALIDATION_COMPARISON_PROFILE,
            VALIDATION_EVIDENCE_STATE_COMPLETE,
            VALIDATION_GATE_STATE_PASSED,
            VALIDATION_GATE_STATE_REASON_READY,
            VALIDATION_GATE_STATE_REASON_FAMILY_READY,
            VALIDATION_VERDICT_READY,
            VALIDATION_BLOCKING_REASON_NONE,
            VALIDATION_BLOCKING_REASON_FAMILY_NONE,
            datagram_mode_label(contract.resolved_datagram_mode),
            contract.signed_datagram_enabled,
            contract.rollout_stage,
            contract.carrier_datagrams_available,
        )),
        OutputFormatArg::Json => Ok(serde_json::to_string_pretty(&serde_json::json!({
            "validation_result": "valid",
            "surface": "startup_contract",
            "command": command,
            "simulated_inputs": true,
            "comparison_schema": UDP_VALIDATION_COMPARISON_SCHEMA,
            "comparison_schema_version": UDP_VALIDATION_COMPARISON_SCHEMA_VERSION,
            "comparison_family": UDP_VALIDATION_COMPARISON_FAMILY,
            "comparison_label": GATEWAY_STARTUP_COMPARISON_LABEL,
            "comparison_scope": UDP_VALIDATION_COMPARISON_SCOPE,
            "comparison_profile": UDP_VALIDATION_COMPARISON_PROFILE,
            "evidence_state": VALIDATION_EVIDENCE_STATE_COMPLETE,
            "gate_state": VALIDATION_GATE_STATE_PASSED,
            "gate_state_reason": VALIDATION_GATE_STATE_REASON_READY,
            "gate_state_reason_family": VALIDATION_GATE_STATE_REASON_FAMILY_READY,
            "verdict": VALIDATION_VERDICT_READY,
            "required_input_count": 1,
            "required_input_present_count": 1,
            "required_input_passed_count": 1,
            "required_input_missing_count": 0,
            "required_input_failed_count": 0,
            "required_input_unready_count": 0,
            "all_required_inputs_present": true,
            "all_required_inputs_passed": true,
            "missing_required_input_count": 0,
            "degradation_hold_count": 0,
            "blocking_reason_count": 0,
            "blocking_reason_key": VALIDATION_BLOCKING_REASON_NONE,
            "blocking_reason_family": VALIDATION_BLOCKING_REASON_FAMILY_NONE,
            "signed_datagram_enabled": contract.signed_datagram_enabled,
            "rollout_stage": contract.rollout_stage,
            "carrier_datagrams_available": contract.carrier_datagrams_available,
            "resolved_datagram_mode": datagram_mode_label(contract.resolved_datagram_mode),
        }))?),
    }
}

fn render_client_startup_error_output(
    format: OutputFormatArg,
    command: &str,
    plan: &ClientLaunchPlan,
    carrier_datagrams_available: bool,
    error_class: &str,
    error_message: &str,
) -> anyhow::Result<String> {
    match format {
        OutputFormatArg::Text => Ok(format!(
            "manifest={} profile={} endpoint={}:{}\nvalidation_result=invalid surface=startup_contract command={} simulated_inputs=true comparison_schema={} comparison_schema_version={} comparison_family={} comparison_label={} comparison_scope={} comparison_profile={} evidence_state={} gate_state={} gate_state_reason={} gate_state_reason_family={} verdict={} required_input_count=1 required_input_present_count=1 required_input_passed_count=0 required_input_missing_count=0 required_input_failed_count=1 required_input_unready_count=1 all_required_inputs_present=true all_required_inputs_passed=false missing_required_input_count=0 degradation_hold_count=0 blocking_reason_count=1 blocking_reason_key={} blocking_reason_family={} signed_datagram_enabled={} rollout_stage={} carrier_datagrams_available={} expected_server_datagram_mode=unresolved error_class={} error_message={}",
            plan.manifest_id.as_str(),
            plan.carrier_profile_id.as_str(),
            plan.endpoint_host,
            plan.endpoint_port,
            command,
            UDP_VALIDATION_COMPARISON_SCHEMA,
            UDP_VALIDATION_COMPARISON_SCHEMA_VERSION,
            UDP_VALIDATION_COMPARISON_FAMILY,
            CLIENT_STARTUP_COMPARISON_LABEL,
            UDP_VALIDATION_COMPARISON_SCOPE,
            UDP_VALIDATION_COMPARISON_PROFILE,
            VALIDATION_EVIDENCE_STATE_COMPLETE,
            VALIDATION_GATE_STATE_BLOCKED,
            VALIDATION_GATE_STATE_REASON_REQUIRED_INPUTS_UNREADY,
            VALIDATION_GATE_STATE_REASON_FAMILY_GATING,
            VALIDATION_VERDICT_HOLD,
            error_class,
            VALIDATION_BLOCKING_REASON_FAMILY_VALIDATION,
            plan.datagram_enabled,
            plan.datagram_rollout.stage_label(),
            carrier_datagrams_available,
            error_class,
            error_message,
        )),
        OutputFormatArg::Json => Ok(serde_json::to_string_pretty(&serde_json::json!({
            "validation_result": "invalid",
            "surface": "startup_contract",
            "command": command,
            "simulated_inputs": true,
            "comparison_schema": UDP_VALIDATION_COMPARISON_SCHEMA,
            "comparison_schema_version": UDP_VALIDATION_COMPARISON_SCHEMA_VERSION,
            "comparison_family": UDP_VALIDATION_COMPARISON_FAMILY,
            "comparison_label": CLIENT_STARTUP_COMPARISON_LABEL,
            "comparison_scope": UDP_VALIDATION_COMPARISON_SCOPE,
            "comparison_profile": UDP_VALIDATION_COMPARISON_PROFILE,
            "evidence_state": VALIDATION_EVIDENCE_STATE_COMPLETE,
            "gate_state": VALIDATION_GATE_STATE_BLOCKED,
            "gate_state_reason": VALIDATION_GATE_STATE_REASON_REQUIRED_INPUTS_UNREADY,
            "gate_state_reason_family": VALIDATION_GATE_STATE_REASON_FAMILY_GATING,
            "verdict": VALIDATION_VERDICT_HOLD,
            "required_input_count": 1,
            "required_input_present_count": 1,
            "required_input_passed_count": 0,
            "required_input_missing_count": 0,
            "required_input_failed_count": 1,
            "required_input_unready_count": 1,
            "all_required_inputs_present": true,
            "all_required_inputs_passed": false,
            "missing_required_input_count": 0,
            "degradation_hold_count": 0,
            "blocking_reason_count": 1,
            "blocking_reason_key": error_class,
            "blocking_reason_family": VALIDATION_BLOCKING_REASON_FAMILY_VALIDATION,
            "manifest_id": plan.manifest_id.as_str(),
            "carrier_profile_id": plan.carrier_profile_id.as_str(),
            "endpoint_host": plan.endpoint_host,
            "endpoint_port": plan.endpoint_port,
            "signed_datagram_enabled": plan.datagram_enabled,
            "rollout_stage": plan.datagram_rollout.stage_label(),
            "carrier_datagrams_available": carrier_datagrams_available,
            "expected_server_datagram_mode": "unresolved",
            "error_class": error_class,
            "error_message": error_message,
        }))?),
    }
}

#[allow(clippy::too_many_arguments)]
fn render_client_negotiated_error_output(
    format: OutputFormatArg,
    command: &str,
    plan: &ClientLaunchPlan,
    startup: &ClientDatagramStartupContract,
    expected_policy_epoch: u64,
    received_policy_epoch: u64,
    expected_max_udp_flows: u64,
    received_max_udp_flows: u64,
    expected_max_udp_payload: u64,
    requested_max_udp_payload: u64,
    received_effective_max_udp_payload: u64,
    received_datagram_mode: DatagramMode,
    error_class: &str,
    error_message: &str,
) -> anyhow::Result<String> {
    match format {
        OutputFormatArg::Text => Ok(format!(
            "manifest={} profile={} endpoint={}:{}\nvalidation_result=invalid surface=negotiated_contract command={} simulated_inputs=true comparison_schema={} comparison_schema_version={} comparison_family={} comparison_label={} comparison_scope={} comparison_profile={} evidence_state={} gate_state={} gate_state_reason={} gate_state_reason_family={} verdict={} required_input_count=1 required_input_present_count=1 required_input_passed_count=0 required_input_missing_count=0 required_input_failed_count=1 required_input_unready_count=1 all_required_inputs_present=true all_required_inputs_passed=false missing_required_input_count=0 degradation_hold_count=0 blocking_reason_count=1 blocking_reason_key={} blocking_reason_family={} signed_datagram_enabled={} rollout_stage={} carrier_datagrams_available={} expected_server_datagram_mode={} received_datagram_mode={} expected_policy_epoch={} received_policy_epoch={} expected_max_udp_flows={} received_max_udp_flows={} expected_max_udp_payload={} requested_max_udp_payload={} received_effective_max_udp_payload={} error_class={} error_message={}",
            plan.manifest_id.as_str(),
            plan.carrier_profile_id.as_str(),
            plan.endpoint_host,
            plan.endpoint_port,
            command,
            UDP_VALIDATION_COMPARISON_SCHEMA,
            UDP_VALIDATION_COMPARISON_SCHEMA_VERSION,
            UDP_VALIDATION_COMPARISON_FAMILY,
            CLIENT_NEGOTIATED_COMPARISON_LABEL,
            UDP_VALIDATION_COMPARISON_SCOPE,
            UDP_VALIDATION_COMPARISON_PROFILE,
            VALIDATION_EVIDENCE_STATE_COMPLETE,
            VALIDATION_GATE_STATE_BLOCKED,
            VALIDATION_GATE_STATE_REASON_REQUIRED_INPUTS_UNREADY,
            VALIDATION_GATE_STATE_REASON_FAMILY_GATING,
            VALIDATION_VERDICT_HOLD,
            error_class,
            VALIDATION_BLOCKING_REASON_FAMILY_VALIDATION,
            startup.signed_datagram_enabled,
            startup.rollout_stage,
            startup.carrier_datagrams_available,
            datagram_mode_label(startup.expected_server_datagram_mode),
            datagram_mode_label(received_datagram_mode),
            expected_policy_epoch,
            received_policy_epoch,
            expected_max_udp_flows,
            received_max_udp_flows,
            expected_max_udp_payload,
            requested_max_udp_payload,
            received_effective_max_udp_payload,
            error_class,
            error_message,
        )),
        OutputFormatArg::Json => Ok(serde_json::to_string_pretty(&serde_json::json!({
            "validation_result": "invalid",
            "surface": "negotiated_contract",
            "command": command,
            "simulated_inputs": true,
            "comparison_schema": UDP_VALIDATION_COMPARISON_SCHEMA,
            "comparison_schema_version": UDP_VALIDATION_COMPARISON_SCHEMA_VERSION,
            "comparison_family": UDP_VALIDATION_COMPARISON_FAMILY,
            "comparison_label": CLIENT_NEGOTIATED_COMPARISON_LABEL,
            "comparison_scope": UDP_VALIDATION_COMPARISON_SCOPE,
            "comparison_profile": UDP_VALIDATION_COMPARISON_PROFILE,
            "evidence_state": VALIDATION_EVIDENCE_STATE_COMPLETE,
            "gate_state": VALIDATION_GATE_STATE_BLOCKED,
            "gate_state_reason": VALIDATION_GATE_STATE_REASON_REQUIRED_INPUTS_UNREADY,
            "gate_state_reason_family": VALIDATION_GATE_STATE_REASON_FAMILY_GATING,
            "verdict": VALIDATION_VERDICT_HOLD,
            "required_input_count": 1,
            "required_input_present_count": 1,
            "required_input_passed_count": 0,
            "required_input_missing_count": 0,
            "required_input_failed_count": 1,
            "required_input_unready_count": 1,
            "all_required_inputs_present": true,
            "all_required_inputs_passed": false,
            "missing_required_input_count": 0,
            "degradation_hold_count": 0,
            "blocking_reason_count": 1,
            "blocking_reason_key": error_class,
            "blocking_reason_family": VALIDATION_BLOCKING_REASON_FAMILY_VALIDATION,
            "manifest_id": plan.manifest_id.as_str(),
            "carrier_profile_id": plan.carrier_profile_id.as_str(),
            "endpoint_host": plan.endpoint_host,
            "endpoint_port": plan.endpoint_port,
            "signed_datagram_enabled": startup.signed_datagram_enabled,
            "rollout_stage": startup.rollout_stage,
            "carrier_datagrams_available": startup.carrier_datagrams_available,
            "expected_server_datagram_mode": datagram_mode_label(startup.expected_server_datagram_mode),
            "received_datagram_mode": datagram_mode_label(received_datagram_mode),
            "expected_policy_epoch": expected_policy_epoch,
            "received_policy_epoch": received_policy_epoch,
            "expected_max_udp_flows": expected_max_udp_flows,
            "received_max_udp_flows": received_max_udp_flows,
            "expected_max_udp_payload": expected_max_udp_payload,
            "requested_max_udp_payload": requested_max_udp_payload,
            "received_effective_max_udp_payload": received_effective_max_udp_payload,
            "error_class": error_class,
            "error_message": error_message,
        }))?),
    }
}

fn render_gateway_startup_error_output(
    format: OutputFormatArg,
    command: &str,
    signed_datagram_enabled: bool,
    datagram_rollout: H3DatagramRollout,
    carrier_datagrams_available: bool,
    error_class: &str,
    error_message: &str,
) -> anyhow::Result<String> {
    match format {
        OutputFormatArg::Text => Ok(format!(
            "validation_result=invalid surface=startup_contract command={} simulated_inputs=true comparison_schema={} comparison_schema_version={} comparison_family={} comparison_label={} comparison_scope={} comparison_profile={} evidence_state={} gate_state={} gate_state_reason={} gate_state_reason_family={} verdict={} required_input_count=1 required_input_present_count=1 required_input_passed_count=0 required_input_missing_count=0 required_input_failed_count=1 required_input_unready_count=1 all_required_inputs_present=true all_required_inputs_passed=false missing_required_input_count=0 degradation_hold_count=0 blocking_reason_count=1 blocking_reason_key={} blocking_reason_family={} datagram_mode=unresolved signed_datagram_enabled={} rollout_stage={} carrier_datagrams_available={} error_class={} error_message={}",
            command,
            UDP_VALIDATION_COMPARISON_SCHEMA,
            UDP_VALIDATION_COMPARISON_SCHEMA_VERSION,
            UDP_VALIDATION_COMPARISON_FAMILY,
            GATEWAY_STARTUP_COMPARISON_LABEL,
            UDP_VALIDATION_COMPARISON_SCOPE,
            UDP_VALIDATION_COMPARISON_PROFILE,
            VALIDATION_EVIDENCE_STATE_COMPLETE,
            VALIDATION_GATE_STATE_BLOCKED,
            VALIDATION_GATE_STATE_REASON_REQUIRED_INPUTS_UNREADY,
            VALIDATION_GATE_STATE_REASON_FAMILY_GATING,
            VALIDATION_VERDICT_HOLD,
            error_class,
            VALIDATION_BLOCKING_REASON_FAMILY_VALIDATION,
            signed_datagram_enabled,
            datagram_rollout.stage_label(),
            carrier_datagrams_available,
            error_class,
            error_message,
        )),
        OutputFormatArg::Json => Ok(serde_json::to_string_pretty(&serde_json::json!({
            "validation_result": "invalid",
            "surface": "startup_contract",
            "command": command,
            "simulated_inputs": true,
            "comparison_schema": UDP_VALIDATION_COMPARISON_SCHEMA,
            "comparison_schema_version": UDP_VALIDATION_COMPARISON_SCHEMA_VERSION,
            "comparison_family": UDP_VALIDATION_COMPARISON_FAMILY,
            "comparison_label": GATEWAY_STARTUP_COMPARISON_LABEL,
            "comparison_scope": UDP_VALIDATION_COMPARISON_SCOPE,
            "comparison_profile": UDP_VALIDATION_COMPARISON_PROFILE,
            "evidence_state": VALIDATION_EVIDENCE_STATE_COMPLETE,
            "gate_state": VALIDATION_GATE_STATE_BLOCKED,
            "gate_state_reason": VALIDATION_GATE_STATE_REASON_REQUIRED_INPUTS_UNREADY,
            "gate_state_reason_family": VALIDATION_GATE_STATE_REASON_FAMILY_GATING,
            "verdict": VALIDATION_VERDICT_HOLD,
            "required_input_count": 1,
            "required_input_present_count": 1,
            "required_input_passed_count": 0,
            "required_input_missing_count": 0,
            "required_input_failed_count": 1,
            "required_input_unready_count": 1,
            "all_required_inputs_present": true,
            "all_required_inputs_passed": false,
            "missing_required_input_count": 0,
            "degradation_hold_count": 0,
            "blocking_reason_count": 1,
            "blocking_reason_key": error_class,
            "blocking_reason_family": VALIDATION_BLOCKING_REASON_FAMILY_VALIDATION,
            "signed_datagram_enabled": signed_datagram_enabled,
            "rollout_stage": datagram_rollout.stage_label(),
            "carrier_datagrams_available": carrier_datagrams_available,
            "resolved_datagram_mode": "unresolved",
            "error_class": error_class,
            "error_message": error_message,
        }))?),
    }
}

fn datagram_mode_label(mode: DatagramMode) -> &'static str {
    match mode {
        DatagramMode::Unavailable => "unavailable",
        DatagramMode::AvailableAndEnabled => "available_and_enabled",
        DatagramMode::DisabledByPolicy => "disabled_by_policy",
    }
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();
    init_tracing("verta", cli.json_logs);

    match cli.command {
        Command::PlanClient {
            manifest,
            manifest_public_key_pem,
            manifest_key_id,
            manifest_url,
            device_id,
            carrier_profile_id,
            client_version,
            datagram_rollout,
            carrier_datagrams_available,
        } => {
            let plan = load_client_launch_plan(
                &manifest,
                &manifest_public_key_pem,
                manifest_key_id,
                manifest_url,
                device_id,
                carrier_profile_id,
                client_version,
                datagram_rollout,
            )
            .await?;
            let contract =
                match plan.validate_startup_datagram_contract(carrier_datagrams_available) {
                    Ok(contract) => contract,
                    Err(error) => {
                        println!(
                            "{}",
                            render_client_startup_error_output(
                                cli.output,
                                "plan-client",
                                &plan,
                                carrier_datagrams_available,
                                "startup_contract_invalid",
                                &error.to_string(),
                            )?
                        );
                        std::process::exit(2);
                    }
                };

            emit_client_startup_contract("plan-client", &contract);
            println!(
                "{}",
                render_plan_client_output(cli.output, "plan-client", &plan, &contract)?
            );
        }
        Command::ValidateDatagramStartup {
            manifest,
            manifest_public_key_pem,
            manifest_key_id,
            manifest_url,
            device_id,
            carrier_profile_id,
            client_version,
            datagram_rollout,
            carrier_datagrams_available,
        } => {
            let plan = load_client_launch_plan(
                &manifest,
                &manifest_public_key_pem,
                manifest_key_id,
                manifest_url,
                device_id,
                carrier_profile_id,
                client_version,
                datagram_rollout,
            )
            .await?;
            let contract =
                match plan.validate_startup_datagram_contract(carrier_datagrams_available) {
                    Ok(contract) => contract,
                    Err(error) => {
                        println!(
                            "{}",
                            render_client_startup_error_output(
                                cli.output,
                                "validate-datagram-startup",
                                &plan,
                                carrier_datagrams_available,
                                "startup_contract_invalid",
                                &error.to_string(),
                            )?
                        );
                        std::process::exit(2);
                    }
                };
            emit_client_startup_contract("validate-datagram-startup", &contract);
            println!(
                "{}",
                render_client_startup_output(
                    cli.output,
                    "validate-datagram-startup",
                    &plan,
                    &contract,
                )?
            );
        }
        Command::ValidateGatewayDatagramStartup {
            signed_datagram_enabled,
            datagram_rollout,
            carrier_datagrams_available,
        } => {
            let contract = match resolve_h3_datagram_startup_contract(
                signed_datagram_enabled,
                datagram_rollout.into(),
                carrier_datagrams_available,
            ) {
                Ok(contract) => contract,
                Err(error) => {
                    println!(
                        "{}",
                        render_gateway_startup_error_output(
                            cli.output,
                            "validate-gateway-datagram-startup",
                            signed_datagram_enabled,
                            datagram_rollout.into(),
                            carrier_datagrams_available,
                            "startup_contract_invalid",
                            &error.to_string(),
                        )?
                    );
                    std::process::exit(2);
                }
            };
            emit_gateway_startup_contract("validate-gateway-datagram-startup", &contract);
            println!(
                "{}",
                render_gateway_startup_output(
                    cli.output,
                    "validate-gateway-datagram-startup",
                    &contract,
                )?
            );
        }
        Command::ValidateDatagramContract {
            manifest,
            manifest_public_key_pem,
            manifest_key_id,
            manifest_url,
            device_id,
            carrier_profile_id,
            client_version,
            datagram_rollout,
            carrier_datagrams_available,
            expected_policy_epoch,
            expected_max_udp_flows,
            expected_max_udp_payload,
            requested_max_udp_payload,
            received_policy_epoch,
            received_datagram_mode,
            received_max_udp_flows,
            received_effective_max_udp_payload,
        } => {
            let plan = load_client_launch_plan(
                &manifest,
                &manifest_public_key_pem,
                manifest_key_id,
                manifest_url,
                device_id,
                carrier_profile_id,
                client_version,
                datagram_rollout,
            )
            .await?;
            let startup = match plan.validate_startup_datagram_contract(carrier_datagrams_available)
            {
                Ok(contract) => contract,
                Err(error) => {
                    println!(
                        "{}",
                        render_client_startup_error_output(
                            cli.output,
                            "validate-datagram-contract",
                            &plan,
                            carrier_datagrams_available,
                            "startup_contract_invalid",
                            &error.to_string(),
                        )?
                    );
                    std::process::exit(2);
                }
            };
            let negotiated_input = ClientNegotiatedDatagramContractInput {
                expected_policy_epoch,
                expected_max_udp_flows,
                expected_max_udp_payload,
                requested_max_udp_payload,
                carrier_datagrams_available,
                received_policy_epoch,
                received_datagram_mode: received_datagram_mode.into(),
                received_max_udp_flows,
                received_effective_max_udp_payload,
            };
            if let Err(error) = plan.validate_negotiated_datagram_contract(&negotiated_input) {
                println!(
                    "{}",
                    render_client_negotiated_error_output(
                        cli.output,
                        "validate-datagram-contract",
                        &plan,
                        &startup,
                        expected_policy_epoch,
                        received_policy_epoch,
                        expected_max_udp_flows,
                        received_max_udp_flows,
                        expected_max_udp_payload,
                        requested_max_udp_payload,
                        received_effective_max_udp_payload,
                        received_datagram_mode.into(),
                        "negotiated_contract_invalid",
                        &error.to_string(),
                    )?
                );
                std::process::exit(2);
            }

            info!(
                event_name = "verta.client.datagram.contract",
                command = "validate-datagram-contract",
                simulated_inputs = true,
                expected_mode = ?startup.expected_server_datagram_mode,
                received_mode = ?DatagramMode::from(received_datagram_mode),
                expected_policy_epoch,
                received_policy_epoch,
                expected_max_udp_flows,
                received_max_udp_flows,
                expected_max_udp_payload,
                requested_max_udp_payload,
                received_effective_max_udp_payload,
                "validated client negotiated datagram contract"
            );
            emit_client_startup_contract("validate-datagram-contract", &startup);
            println!(
                "{}",
                render_client_negotiated_output(
                    cli.output,
                    "validate-datagram-contract",
                    &plan,
                    &startup,
                    expected_policy_epoch,
                    received_policy_epoch,
                    expected_max_udp_flows,
                    received_max_udp_flows,
                    expected_max_udp_payload,
                    requested_max_udp_payload,
                    received_effective_max_udp_payload,
                    received_datagram_mode.into(),
                )?
            );
        }
        Command::EmitWireHelloFixture { token } => {
            let frame = Frame::ClientHello(ClientHello {
                min_version: 1,
                max_version: 1,
                client_nonce: [1_u8; 32],
                requested_capabilities: vec![Capability::TcpRelay, Capability::UdpRelay],
                carrier_kind: CarrierKind::H3,
                carrier_profile_id: CarrierProfileId::new("carrier-primary")?,
                manifest_id: ManifestId::new("sha256:fixture-manifest-id")?,
                device_binding_id: DeviceBindingId::new("device-1")?,
                requested_idle_timeout_ms: 30_000,
                requested_max_udp_payload: 1_200,
                token: token.into_bytes(),
                client_metadata: Vec::new(),
            });
            let encoded = FrameCodec::encode(&frame)?;

            println!("{}", hex::encode(encoded));
        }
        Command::PrintDemoTokenJwks => {
            println!("{}", serde_json::to_string_pretty(&demo_token_jwks())?);
        }
        Command::MintDemoSessionToken {
            manifest_id,
            device_id,
            carrier_profile_id,
            policy_epoch,
            now_unix,
            ttl_seconds,
        } => {
            let signer = demo_token_signer()?;
            let now = OffsetDateTime::from_unix_timestamp(now_unix)
                .context("now_unix was not a valid unix timestamp")?;
            let minted = signer.mint(
                MintedTokenRequest {
                    subject: "acct-1".to_owned(),
                    device_id: DeviceBindingId::new(device_id)?,
                    manifest_id: ManifestId::new(manifest_id)?,
                    policy_epoch,
                    core_versions: vec![1],
                    carrier_profiles: vec![carrier_profile_id],
                    capabilities: vec![Capability::TcpRelay.id(), Capability::UdpRelay.id()],
                    session_modes: vec!["tcp".to_owned(), "udp".to_owned()],
                    region_scope: Some("eu-central".to_owned()),
                    token_max_relay_streams: Some(8),
                    token_max_udp_flows: Some(4),
                    token_max_udp_payload: Some(1_200),
                },
                now,
                Duration::seconds(ttl_seconds),
            )?;

            println!("{}", minted.token);
        }
    }

    Ok(())
}

fn demo_token_signer() -> anyhow::Result<SessionTokenSigner> {
    let signing_key = SigningKey::from_bytes(&[21_u8; 32]);
    let pem = signing_key
        .to_pkcs8_pem(Default::default())
        .context("failed to encode demo token signing key")?;
    SessionTokenSigner::from_ed_pem(
        "bridge.example",
        "verta-gateway",
        "bridge-token-2026-01",
        pem.as_bytes(),
    )
    .context("failed to initialize demo token signer")
}

fn demo_token_jwks() -> serde_json::Value {
    let signing_key = SigningKey::from_bytes(&[21_u8; 32]);
    let x = base64::engine::general_purpose::URL_SAFE_NO_PAD
        .encode(signing_key.verifying_key().to_bytes());

    serde_json::json!({
        "keys": [
            {
                "kty": "OKP",
                "crv": "Ed25519",
                "kid": "bridge-token-2026-01",
                "alg": "EdDSA",
                "use": "sig",
                "x": x
            }
        ]
    })
}

#[cfg(test)]
mod tests {
    use super::{
        Cli, Command, DatagramModeArg, DatagramRolloutArg, OutputFormatArg,
        render_client_negotiated_error_output, render_client_negotiated_output,
        render_client_startup_error_output, render_client_startup_output,
        render_gateway_startup_error_output, render_gateway_startup_output,
        render_plan_client_output,
    };
    use clap::Parser;
    use ns_carrier_h3::{
        H3DatagramRollout, H3TransportError, resolve_h3_datagram_startup_contract,
    };
    use ns_client_runtime::{
        ClientLaunchPlan, ClientNegotiatedDatagramContractInput, ClientRuntimeConfig,
        ClientRuntimeError, build_launch_plan,
    };
    use ns_core::{CarrierProfileId, DatagramMode, DeviceBindingId};
    use ns_session::SessionError;
    use ns_testkit::{fixed_test_now, fixture_manifest_trust_store, load_fixture_text};
    use url::Url;

    fn fixture_plan(datagram_rollout: H3DatagramRollout) -> ClientLaunchPlan {
        build_launch_plan(
            &ClientRuntimeConfig {
                manifest_url: Url::parse("https://bridge.example/v0/manifest")
                    .expect("fixture manifest url should parse"),
                device_id: DeviceBindingId::new("device-1")
                    .expect("fixture device id should be valid"),
                client_version: "0.1.0".to_owned(),
                selected_carrier_profile: CarrierProfileId::new("carrier-primary")
                    .expect("fixture carrier profile should be valid"),
                datagram_rollout,
            },
            &load_fixture_text("manifest/v1/valid/MF-MANIFEST-VALID-001.json"),
            &fixture_manifest_trust_store(),
            fixed_test_now(),
        )
        .expect("fixture launch plan should build")
    }

    #[test]
    fn cli_parses_gateway_startup_validation_subcommand() {
        let cli = Cli::try_parse_from([
            "verta",
            "validate-gateway-datagram-startup",
            "--signed-datagram-enabled=false",
            "--datagram-rollout",
            "automatic",
            "--carrier-datagrams-available",
        ])
        .expect("gateway startup validation CLI should parse");

        assert!(matches!(
            cli.command,
            Command::ValidateGatewayDatagramStartup {
                signed_datagram_enabled: false,
                datagram_rollout: DatagramRolloutArg::Automatic,
                carrier_datagrams_available: true,
            }
        ));
    }

    #[test]
    fn gateway_startup_validation_fails_closed_for_signed_intent_mismatch() {
        let error = resolve_h3_datagram_startup_contract(false, H3DatagramRollout::Automatic, true)
            .expect_err("gateway startup validation should fail closed");

        assert!(matches!(
            error,
            H3TransportError::InvalidConfig("datagram_rollout")
        ));
    }

    #[test]
    fn negotiated_contract_validation_rejects_udp_flow_limit_drift() {
        let plan = fixture_plan(H3DatagramRollout::Automatic);

        let error = plan
            .validate_negotiated_datagram_contract(&ClientNegotiatedDatagramContractInput {
                expected_policy_epoch: 7,
                expected_max_udp_flows: 4,
                expected_max_udp_payload: 1_200,
                requested_max_udp_payload: 1_100,
                carrier_datagrams_available: true,
                received_policy_epoch: 7,
                received_datagram_mode: DatagramModeArg::AvailableAndEnabled.into(),
                received_max_udp_flows: 5,
                received_effective_max_udp_payload: 1_100,
            })
            .expect_err("negotiated contract limit drift should be rejected");

        assert!(matches!(
            error,
            ClientRuntimeError::Session(SessionError::InvalidServerUdpFlowLimit {
                max_udp_flows: 4,
                received_max_udp_flows: 5,
            })
        ));
    }

    #[test]
    fn nsctl_client_startup_output_renders_consistent_text_and_json_fields() {
        let plan = fixture_plan(H3DatagramRollout::Automatic);
        let contract = plan
            .validate_startup_datagram_contract(true)
            .expect("startup contract should validate");

        let text = render_client_startup_output(
            OutputFormatArg::Text,
            "validate-datagram-startup",
            &plan,
            &contract,
        )
        .expect("text output should render");
        assert!(text.contains("manifest="));
        assert!(text.contains("validation_result=valid"));
        assert!(text.contains("comparison_schema=udp_rollout_validation_surface"));
        assert!(text.contains("comparison_schema_version=1"));
        assert!(text.contains("comparison_label=client_startup_contract"));
        assert!(text.contains("comparison_scope=surface"));
        assert!(text.contains("comparison_profile=validation_surface"));
        assert!(text.contains("gate_state=passed"));
        assert!(text.contains("gate_state_reason=all_required_inputs_passed"));
        assert!(text.contains("gate_state_reason_family=ready"));
        assert!(text.contains("verdict=ready"));
        assert!(text.contains("required_input_count=1"));
        assert!(text.contains("required_input_passed_count=1"));
        assert!(text.contains("all_required_inputs_passed=true"));
        assert!(text.contains("blocking_reason_key=none"));
        assert!(text.contains("expected_server_datagram_mode=available_and_enabled"));

        let json = render_client_startup_output(
            OutputFormatArg::Json,
            "validate-datagram-startup",
            &plan,
            &contract,
        )
        .expect("json output should render");
        let value: serde_json::Value =
            serde_json::from_str(&json).expect("json output should parse");
        assert_eq!(value["validation_result"], "valid");
        assert_eq!(value["surface"], "startup_contract");
        assert_eq!(value["command"], "validate-datagram-startup");
        assert_eq!(value["comparison_schema"], "udp_rollout_validation_surface");
        assert_eq!(value["comparison_schema_version"], 1);
        assert_eq!(value["comparison_family"], "udp_rollout_validation");
        assert_eq!(value["comparison_label"], "client_startup_contract");
        assert_eq!(value["comparison_scope"], "surface");
        assert_eq!(value["comparison_profile"], "validation_surface");
        assert_eq!(value["gate_state"], "passed");
        assert_eq!(value["gate_state_reason"], "all_required_inputs_passed");
        assert_eq!(value["gate_state_reason_family"], "ready");
        assert_eq!(value["verdict"], "ready");
        assert_eq!(value["required_input_count"], 1);
        assert_eq!(value["required_input_present_count"], 1);
        assert_eq!(value["required_input_passed_count"], 1);
        assert_eq!(value["required_input_missing_count"], 0);
        assert_eq!(value["required_input_failed_count"], 0);
        assert_eq!(value["required_input_unready_count"], 0);
        assert_eq!(value["all_required_inputs_present"], true);
        assert_eq!(value["all_required_inputs_passed"], true);
        assert_eq!(value["blocking_reason_key"], "none");
        assert_eq!(
            value["expected_server_datagram_mode"],
            "available_and_enabled"
        );
    }

    #[test]
    fn nsctl_gateway_startup_output_renders_consistent_text_and_json_fields() {
        let contract =
            resolve_h3_datagram_startup_contract(true, H3DatagramRollout::Automatic, true)
                .expect("gateway startup contract should resolve");

        let text = render_gateway_startup_output(
            OutputFormatArg::Text,
            "validate-gateway-datagram-startup",
            &contract,
        )
        .expect("text output should render");
        assert!(text.contains("surface=startup_contract"));
        assert!(text.contains("validation_result=valid"));
        assert!(text.contains("comparison_schema=udp_rollout_validation_surface"));
        assert!(text.contains("comparison_schema_version=1"));
        assert!(text.contains("comparison_label=gateway_startup_contract"));
        assert!(text.contains("comparison_scope=surface"));
        assert!(text.contains("comparison_profile=validation_surface"));
        assert!(text.contains("evidence_state=complete"));
        assert!(text.contains("gate_state=passed"));
        assert!(text.contains("verdict=ready"));
        assert!(text.contains("required_input_count=1"));
        assert!(text.contains("required_input_passed_count=1"));
        assert!(text.contains("all_required_inputs_passed=true"));
        assert!(text.contains("datagram_mode=available_and_enabled"));

        let json = render_gateway_startup_output(
            OutputFormatArg::Json,
            "validate-gateway-datagram-startup",
            &contract,
        )
        .expect("json output should render");
        let value: serde_json::Value =
            serde_json::from_str(&json).expect("json output should parse");
        assert_eq!(value["validation_result"], "valid");
        assert_eq!(value["surface"], "startup_contract");
        assert_eq!(value["comparison_schema"], "udp_rollout_validation_surface");
        assert_eq!(value["comparison_schema_version"], 1);
        assert_eq!(value["comparison_family"], "udp_rollout_validation");
        assert_eq!(value["comparison_label"], "gateway_startup_contract");
        assert_eq!(value["comparison_scope"], "surface");
        assert_eq!(value["comparison_profile"], "validation_surface");
        assert_eq!(value["evidence_state"], "complete");
        assert_eq!(value["gate_state"], "passed");
        assert_eq!(value["verdict"], "ready");
        assert_eq!(value["required_input_count"], 1);
        assert_eq!(value["required_input_present_count"], 1);
        assert_eq!(value["required_input_passed_count"], 1);
        assert_eq!(value["required_input_missing_count"], 0);
        assert_eq!(value["required_input_failed_count"], 0);
        assert_eq!(value["all_required_inputs_present"], true);
        assert_eq!(value["all_required_inputs_passed"], true);
        assert_eq!(value["resolved_datagram_mode"], "available_and_enabled");
    }

    #[test]
    fn nsctl_negotiated_output_renders_consistent_text_and_json_fields() {
        let plan = fixture_plan(H3DatagramRollout::Automatic);
        let contract = plan
            .validate_startup_datagram_contract(true)
            .expect("startup contract should validate");

        let text = render_client_negotiated_output(
            OutputFormatArg::Text,
            "validate-datagram-contract",
            &plan,
            &contract,
            7,
            7,
            4,
            4,
            1_200,
            1_100,
            1_100,
            DatagramMode::AvailableAndEnabled,
        )
        .expect("text output should render");
        assert!(text.contains("validation_result=valid"));
        assert!(text.contains("comparison_schema=udp_rollout_validation_surface"));
        assert!(text.contains("comparison_schema_version=1"));
        assert!(text.contains("comparison_label=client_negotiated_contract"));
        assert!(text.contains("comparison_scope=surface"));
        assert!(text.contains("comparison_profile=validation_surface"));
        assert!(text.contains("required_input_count=1"));
        assert!(text.contains("required_input_passed_count=1"));
        assert!(text.contains("all_required_inputs_passed=true"));
        assert!(text.contains("received_datagram_mode=available_and_enabled"));

        let json = render_client_negotiated_output(
            OutputFormatArg::Json,
            "validate-datagram-contract",
            &plan,
            &contract,
            7,
            7,
            4,
            4,
            1_200,
            1_100,
            1_100,
            DatagramMode::AvailableAndEnabled,
        )
        .expect("json output should render");
        let value: serde_json::Value =
            serde_json::from_str(&json).expect("json output should parse");
        assert_eq!(value["validation_result"], "valid");
        assert_eq!(value["surface"], "negotiated_contract");
        assert_eq!(value["comparison_schema"], "udp_rollout_validation_surface");
        assert_eq!(value["comparison_schema_version"], 1);
        assert_eq!(value["comparison_family"], "udp_rollout_validation");
        assert_eq!(value["comparison_label"], "client_negotiated_contract");
        assert_eq!(value["comparison_scope"], "surface");
        assert_eq!(value["comparison_profile"], "validation_surface");
        assert_eq!(value["required_input_count"], 1);
        assert_eq!(value["required_input_present_count"], 1);
        assert_eq!(value["required_input_passed_count"], 1);
        assert_eq!(value["required_input_missing_count"], 0);
        assert_eq!(value["required_input_failed_count"], 0);
        assert_eq!(value["all_required_inputs_present"], true);
        assert_eq!(value["all_required_inputs_passed"], true);
        assert_eq!(value["expected_policy_epoch"], 7);
        assert_eq!(value["received_max_udp_flows"], 4);
        assert_eq!(value["received_datagram_mode"], "available_and_enabled");
    }

    #[test]
    fn nsctl_client_startup_error_output_renders_consistent_text_and_json_fields() {
        let plan = fixture_plan(H3DatagramRollout::Disabled);
        let text = render_client_startup_error_output(
            OutputFormatArg::Text,
            "validate-datagram-startup",
            &plan,
            true,
            "startup_contract_invalid",
            "rollout widened signed intent",
        )
        .expect("text error output should render");
        assert!(text.contains("validation_result=invalid"));
        assert!(text.contains("comparison_schema=udp_rollout_validation_surface"));
        assert!(text.contains("comparison_schema_version=1"));
        assert!(text.contains("comparison_label=client_startup_contract"));
        assert!(text.contains("comparison_scope=surface"));
        assert!(text.contains("comparison_profile=validation_surface"));
        assert!(text.contains("gate_state=blocked"));
        assert!(text.contains("gate_state_reason=required_inputs_unready"));
        assert!(text.contains("gate_state_reason_family=gating"));
        assert!(text.contains("verdict=hold"));
        assert!(text.contains("required_input_count=1"));
        assert!(text.contains("required_input_failed_count=1"));
        assert!(text.contains("all_required_inputs_passed=false"));
        assert!(text.contains("blocking_reason_key=startup_contract_invalid"));
        assert!(text.contains("expected_server_datagram_mode=unresolved"));

        let json = render_client_startup_error_output(
            OutputFormatArg::Json,
            "validate-datagram-startup",
            &plan,
            true,
            "startup_contract_invalid",
            "rollout widened signed intent",
        )
        .expect("json error output should render");
        let value: serde_json::Value =
            serde_json::from_str(&json).expect("json error output should parse");
        assert_eq!(value["validation_result"], "invalid");
        assert_eq!(value["comparison_schema"], "udp_rollout_validation_surface");
        assert_eq!(value["comparison_schema_version"], 1);
        assert_eq!(value["comparison_family"], "udp_rollout_validation");
        assert_eq!(value["comparison_label"], "client_startup_contract");
        assert_eq!(value["comparison_scope"], "surface");
        assert_eq!(value["comparison_profile"], "validation_surface");
        assert_eq!(value["gate_state"], "blocked");
        assert_eq!(value["gate_state_reason"], "required_inputs_unready");
        assert_eq!(value["gate_state_reason_family"], "gating");
        assert_eq!(value["verdict"], "hold");
        assert_eq!(value["required_input_count"], 1);
        assert_eq!(value["required_input_present_count"], 1);
        assert_eq!(value["required_input_passed_count"], 0);
        assert_eq!(value["required_input_missing_count"], 0);
        assert_eq!(value["required_input_failed_count"], 1);
        assert_eq!(value["required_input_unready_count"], 1);
        assert_eq!(value["all_required_inputs_present"], true);
        assert_eq!(value["all_required_inputs_passed"], false);
        assert_eq!(value["blocking_reason_key"], "startup_contract_invalid");
        assert_eq!(value["error_class"], "startup_contract_invalid");
    }

    #[test]
    fn nsctl_gateway_startup_error_output_renders_consistent_text_and_json_fields() {
        let text = render_gateway_startup_error_output(
            OutputFormatArg::Text,
            "validate-gateway-datagram-startup",
            false,
            H3DatagramRollout::Automatic,
            true,
            "startup_contract_invalid",
            "rollout widened signed intent",
        )
        .expect("text error output should render");
        assert!(text.contains("validation_result=invalid"));
        assert!(text.contains("comparison_schema=udp_rollout_validation_surface"));
        assert!(text.contains("comparison_schema_version=1"));
        assert!(text.contains("comparison_label=gateway_startup_contract"));
        assert!(text.contains("comparison_scope=surface"));
        assert!(text.contains("comparison_profile=validation_surface"));
        assert!(text.contains("gate_state=blocked"));
        assert!(text.contains("verdict=hold"));
        assert!(text.contains("required_input_count=1"));
        assert!(text.contains("required_input_failed_count=1"));
        assert!(text.contains("all_required_inputs_passed=false"));
        assert!(text.contains("blocking_reason_family=validation"));
        assert!(text.contains("datagram_mode=unresolved"));

        let json = render_gateway_startup_error_output(
            OutputFormatArg::Json,
            "validate-gateway-datagram-startup",
            false,
            H3DatagramRollout::Automatic,
            true,
            "startup_contract_invalid",
            "rollout widened signed intent",
        )
        .expect("json error output should render");
        let value: serde_json::Value =
            serde_json::from_str(&json).expect("json error output should parse");
        assert_eq!(value["validation_result"], "invalid");
        assert_eq!(value["comparison_schema"], "udp_rollout_validation_surface");
        assert_eq!(value["comparison_schema_version"], 1);
        assert_eq!(value["comparison_family"], "udp_rollout_validation");
        assert_eq!(value["comparison_label"], "gateway_startup_contract");
        assert_eq!(value["comparison_scope"], "surface");
        assert_eq!(value["comparison_profile"], "validation_surface");
        assert_eq!(value["gate_state"], "blocked");
        assert_eq!(value["verdict"], "hold");
        assert_eq!(value["required_input_count"], 1);
        assert_eq!(value["required_input_present_count"], 1);
        assert_eq!(value["required_input_passed_count"], 0);
        assert_eq!(value["required_input_missing_count"], 0);
        assert_eq!(value["required_input_failed_count"], 1);
        assert_eq!(value["all_required_inputs_present"], true);
        assert_eq!(value["all_required_inputs_passed"], false);
        assert_eq!(value["blocking_reason_family"], "validation");
        assert_eq!(value["resolved_datagram_mode"], "unresolved");
    }

    #[test]
    fn nsctl_negotiated_error_output_renders_consistent_text_and_json_fields() {
        let plan = fixture_plan(H3DatagramRollout::Automatic);
        let contract = plan
            .validate_startup_datagram_contract(true)
            .expect("startup contract should validate");

        let text = render_client_negotiated_error_output(
            OutputFormatArg::Text,
            "validate-datagram-contract",
            &plan,
            &contract,
            7,
            8,
            4,
            5,
            1_200,
            1_100,
            1_050,
            DatagramMode::DisabledByPolicy,
            "negotiated_contract_invalid",
            "received udp limits drifted",
        )
        .expect("text error output should render");
        assert!(text.contains("validation_result=invalid"));
        assert!(text.contains("comparison_schema=udp_rollout_validation_surface"));
        assert!(text.contains("comparison_schema_version=1"));
        assert!(text.contains("comparison_label=client_negotiated_contract"));
        assert!(text.contains("comparison_scope=surface"));
        assert!(text.contains("comparison_profile=validation_surface"));
        assert!(text.contains("required_input_count=1"));
        assert!(text.contains("required_input_failed_count=1"));
        assert!(text.contains("all_required_inputs_passed=false"));
        assert!(text.contains("error_class=negotiated_contract_invalid"));

        let json = render_client_negotiated_error_output(
            OutputFormatArg::Json,
            "validate-datagram-contract",
            &plan,
            &contract,
            7,
            8,
            4,
            5,
            1_200,
            1_100,
            1_050,
            DatagramMode::DisabledByPolicy,
            "negotiated_contract_invalid",
            "received udp limits drifted",
        )
        .expect("json error output should render");
        let value: serde_json::Value =
            serde_json::from_str(&json).expect("json error output should parse");
        assert_eq!(value["validation_result"], "invalid");
        assert_eq!(value["comparison_schema"], "udp_rollout_validation_surface");
        assert_eq!(value["comparison_schema_version"], 1);
        assert_eq!(value["comparison_family"], "udp_rollout_validation");
        assert_eq!(value["comparison_label"], "client_negotiated_contract");
        assert_eq!(value["comparison_scope"], "surface");
        assert_eq!(value["comparison_profile"], "validation_surface");
        assert_eq!(value["required_input_count"], 1);
        assert_eq!(value["required_input_present_count"], 1);
        assert_eq!(value["required_input_passed_count"], 0);
        assert_eq!(value["required_input_missing_count"], 0);
        assert_eq!(value["required_input_failed_count"], 1);
        assert_eq!(value["all_required_inputs_present"], true);
        assert_eq!(value["all_required_inputs_passed"], false);
        assert_eq!(value["received_datagram_mode"], "disabled_by_policy");
    }

    #[test]
    fn nsctl_plan_output_renders_consistent_text_and_json_fields() {
        let plan = fixture_plan(H3DatagramRollout::Automatic);
        let contract = plan
            .validate_startup_datagram_contract(true)
            .expect("startup contract should validate");

        let text =
            render_plan_client_output(OutputFormatArg::Text, "plan-client", &plan, &contract)
                .expect("text plan output should render");
        assert!(text.contains("surface=client_plan"));
        assert!(text.contains("comparison_schema=udp_rollout_validation_surface"));
        assert!(text.contains("comparison_schema_version=1"));
        assert!(text.contains("comparison_label=client_plan"));
        assert!(text.contains("comparison_scope=surface"));
        assert!(text.contains("comparison_profile=validation_surface"));
        assert!(text.contains("gate_state=passed"));
        assert!(text.contains("verdict=ready"));
        assert!(text.contains("required_input_count=1"));
        assert!(text.contains("required_input_passed_count=1"));
        assert!(text.contains("all_required_inputs_passed=true"));
        assert!(text.contains("blocking_reason_count=0"));

        let json =
            render_plan_client_output(OutputFormatArg::Json, "plan-client", &plan, &contract)
                .expect("json plan output should render");
        let value: serde_json::Value =
            serde_json::from_str(&json).expect("json plan output should parse");
        assert_eq!(value["validation_result"], "valid");
        assert_eq!(value["surface"], "client_plan");
        assert_eq!(value["comparison_schema"], "udp_rollout_validation_surface");
        assert_eq!(value["comparison_schema_version"], 1);
        assert_eq!(value["comparison_family"], "udp_rollout_validation");
        assert_eq!(value["comparison_label"], "client_plan");
        assert_eq!(value["comparison_scope"], "surface");
        assert_eq!(value["comparison_profile"], "validation_surface");
        assert_eq!(value["gate_state"], "passed");
        assert_eq!(value["verdict"], "ready");
        assert_eq!(value["required_input_count"], 1);
        assert_eq!(value["required_input_present_count"], 1);
        assert_eq!(value["required_input_passed_count"], 1);
        assert_eq!(value["required_input_missing_count"], 0);
        assert_eq!(value["required_input_failed_count"], 0);
        assert_eq!(value["all_required_inputs_present"], true);
        assert_eq!(value["all_required_inputs_passed"], true);
        assert_eq!(value["blocking_reason_count"], 0);
    }
}
