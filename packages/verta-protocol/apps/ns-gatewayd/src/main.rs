use anyhow::Context;
use clap::{ArgAction, Parser, Subcommand, ValueEnum};
use jsonwebtoken::jwk::JwkSet;
use ns_auth::{SessionTokenVerifier, TrustedKeySet, VerifierConfig};
use ns_carrier_h3::{H3DatagramRollout, resolve_h3_datagram_startup_contract};
use ns_core::{
    Capability, CarrierProfileId, DeviceBindingId, ManifestId, SessionMode,
    UDP_VALIDATION_COMPARISON_FAMILY, UDP_VALIDATION_COMPARISON_PROFILE,
    UDP_VALIDATION_COMPARISON_SCHEMA, UDP_VALIDATION_COMPARISON_SCHEMA_VERSION,
    UDP_VALIDATION_COMPARISON_SCOPE,
};
use ns_gateway_runtime::admit_client_hello;
use ns_observability::init_tracing;
use ns_wire::ClientHello;
use time::Duration;
use tracing::info;

#[derive(Parser)]
#[command(name = "verta-gatewayd")]
struct Cli {
    #[arg(long, default_value_t = false)]
    json_logs: bool,
    #[arg(long, value_enum, default_value_t = OutputFormatArg::Text)]
    output: OutputFormatArg,
    #[command(subcommand)]
    command: Command,
}

#[allow(clippy::enum_variant_names)]
#[derive(Subcommand)]
enum Command {
    ValidateDatagramStartup {
        #[arg(long, action = ArgAction::Set, num_args = 0..=1, default_missing_value = "true", default_value_t = true)]
        signed_datagram_enabled: bool,
        #[arg(long, value_enum, default_value_t = DatagramRolloutArg::Disabled)]
        datagram_rollout: DatagramRolloutArg,
        #[arg(long, action = ArgAction::Set, num_args = 0..=1, default_missing_value = "true", default_value_t = false)]
        carrier_datagrams_available: bool,
    },
    ValidateHello {
        #[arg(long)]
        token: std::path::PathBuf,
        #[arg(long)]
        jwks: std::path::PathBuf,
        #[arg(long, default_value = "bridge.example")]
        issuer: String,
        #[arg(long, default_value = "man-2026-04-01-001")]
        manifest_id: String,
        #[arg(long, default_value = "device-1")]
        device_id: String,
        #[arg(long, default_value = "carrier-primary")]
        carrier_profile_id: String,
        #[arg(long, value_enum, default_value_t = SessionModeArg::Udp)]
        session_mode: SessionModeArg,
        #[arg(long, default_value_t = 1200)]
        requested_max_udp_payload: u64,
        #[arg(long, action = ArgAction::Set, num_args = 0..=1, default_missing_value = "true", default_value_t = true)]
        signed_datagram_enabled: bool,
        #[arg(long, value_enum, default_value_t = DatagramRolloutArg::Disabled)]
        datagram_rollout: DatagramRolloutArg,
        #[arg(long, action = ArgAction::Set, num_args = 0..=1, default_missing_value = "true", default_value_t = false)]
        carrier_datagrams_available: bool,
    },
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, ValueEnum)]
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

#[derive(Clone, Copy, Debug, PartialEq, Eq, ValueEnum)]
enum SessionModeArg {
    Tcp,
    Udp,
}

#[derive(Clone, Copy, Debug, ValueEnum)]
enum OutputFormatArg {
    Text,
    Json,
}

const GATEWAY_STARTUP_COMPARISON_LABEL: &str = "gateway_startup_contract";
const GATEWAY_HELLO_COMPARISON_LABEL: &str = "gateway_hello_validation";
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

impl From<SessionModeArg> for SessionMode {
    fn from(value: SessionModeArg) -> Self {
        match value {
            SessionModeArg::Tcp => SessionMode::Tcp,
            SessionModeArg::Udp => SessionMode::Udp,
        }
    }
}

impl SessionModeArg {
    fn requested_capabilities(self) -> Vec<Capability> {
        match self {
            Self::Tcp => vec![Capability::TcpRelay],
            Self::Udp => vec![Capability::UdpRelay],
        }
    }
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();
    init_tracing("verta_gatewayd", cli.json_logs);

    match cli.command {
        Command::ValidateDatagramStartup {
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
                            "validate-datagram-startup",
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

            info!(
                event_name = "verta.gateway.datagram.startup_contract",
                command = "validate-datagram-startup",
                simulated_inputs = true,
                signed_datagram_enabled = contract.signed_datagram_enabled,
                rollout_stage = contract.rollout_stage,
                carrier_datagrams_available = contract.carrier_datagrams_available,
                resolved_datagram_mode = ?contract.resolved_datagram_mode,
                "resolved gateway startup datagram contract"
            );
            println!(
                "{}",
                render_gateway_startup_output(cli.output, "validate-datagram-startup", &contract,)?
            );
        }
        Command::ValidateHello {
            token,
            jwks,
            issuer,
            manifest_id,
            device_id,
            carrier_profile_id,
            session_mode,
            requested_max_udp_payload,
            signed_datagram_enabled,
            datagram_rollout,
            carrier_datagrams_available,
        } => {
            let token_value = tokio::fs::read_to_string(&token)
                .await
                .with_context(|| format!("failed to read {}", token.display()))?;
            let jwks_json = tokio::fs::read_to_string(&jwks)
                .await
                .with_context(|| format!("failed to read {}", jwks.display()))?;
            let jwks: JwkSet = serde_json::from_str(&jwks_json)
                .with_context(|| format!("failed to parse {}", jwks.display()))?;
            let verifier = SessionTokenVerifier::new(
                VerifierConfig {
                    trusted_issuers: vec![issuer],
                    audience: "verta-gateway".to_owned(),
                    clock_skew: Duration::seconds(120),
                    revoked_subjects: Vec::new(),
                    minimum_policy_epoch: None,
                },
                TrustedKeySet::from_jwks(&jwks)?,
            );
            let hello = ClientHello {
                min_version: 1,
                max_version: 1,
                client_nonce: [1_u8; 32],
                requested_capabilities: session_mode.requested_capabilities(),
                carrier_kind: ns_core::CarrierKind::H3,
                carrier_profile_id: CarrierProfileId::new(carrier_profile_id)?,
                manifest_id: ManifestId::new(manifest_id)?,
                device_binding_id: DeviceBindingId::new(device_id)?,
                requested_idle_timeout_ms: 30_000,
                requested_max_udp_payload,
                token: token_value.trim().as_bytes().to_vec(),
                client_metadata: Vec::new(),
            };
            let resolved_session_mode = SessionMode::from(session_mode);
            let contract = match resolve_h3_datagram_startup_contract(
                signed_datagram_enabled,
                datagram_rollout.into(),
                carrier_datagrams_available,
            ) {
                Ok(contract) => contract,
                Err(error) => {
                    println!(
                        "{}",
                        render_gateway_hello_error_output(
                            cli.output,
                            "validate-hello",
                            signed_datagram_enabled,
                            datagram_rollout.into(),
                            carrier_datagrams_available,
                            resolved_session_mode,
                            requested_max_udp_payload,
                            None,
                            None,
                            "startup_contract_invalid",
                            &error.to_string(),
                        )?
                    );
                    std::process::exit(2);
                }
            };
            let outcome = match admit_client_hello(
                &verifier,
                &hello,
                resolved_session_mode,
                contract.resolved_datagram_mode,
            ) {
                Ok(outcome) => outcome,
                Err(error) => {
                    println!(
                        "{}",
                        render_gateway_hello_error_output(
                            cli.output,
                            "validate-hello",
                            contract.signed_datagram_enabled,
                            datagram_rollout.into(),
                            contract.carrier_datagrams_available,
                            resolved_session_mode,
                            requested_max_udp_payload,
                            None,
                            Some(datagram_mode_label(contract.resolved_datagram_mode)),
                            "hello_validation_invalid",
                            &error.to_string(),
                        )?
                    );
                    std::process::exit(2);
                }
            };

            info!(
                event_name = "verta.gateway.datagram.hello_contract",
                command = "validate-hello",
                simulated_inputs = true,
                requested_session_mode = ?resolved_session_mode,
                requested_capabilities = ?hello.requested_capabilities,
                signed_datagram_enabled = contract.signed_datagram_enabled,
                rollout_stage = contract.rollout_stage,
                carrier_datagrams_available = contract.carrier_datagrams_available,
                resolved_datagram_mode = ?contract.resolved_datagram_mode,
                requested_max_udp_payload,
                policy_epoch = outcome.response.policy_epoch,
                "validated gateway hello against startup datagram posture"
            );
            println!(
                "{}",
                render_gateway_hello_output(
                    cli.output,
                    "validate-hello",
                    &contract,
                    resolved_session_mode,
                    requested_max_udp_payload,
                    outcome.response.policy_epoch,
                    &format!("{:?}", outcome.response.session_id),
                )?
            );
        }
    }

    Ok(())
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

fn render_gateway_hello_output(
    format: OutputFormatArg,
    command: &str,
    contract: &ns_carrier_h3::H3DatagramStartupContract,
    session_mode: SessionMode,
    requested_max_udp_payload: u64,
    policy_epoch: u64,
    session_id: &str,
) -> anyhow::Result<String> {
    match format {
        OutputFormatArg::Text => Ok(format!(
            "validation_result=valid surface=hello_validation command={} simulated_inputs=true comparison_schema={} comparison_schema_version={} comparison_family={} comparison_label={} comparison_scope={} comparison_profile={} evidence_state={} gate_state={} gate_state_reason={} gate_state_reason_family={} verdict={} required_input_count=1 required_input_present_count=1 required_input_passed_count=1 required_input_missing_count=0 required_input_failed_count=0 required_input_unready_count=0 all_required_inputs_present=true all_required_inputs_passed=true missing_required_input_count=0 degradation_hold_count=0 blocking_reason_count=0 blocking_reason_key={} blocking_reason_family={} policy_epoch={} session_id={} datagram_mode={} session_mode={} signed_datagram_enabled={} rollout_stage={} carrier_datagrams_available={} requested_max_udp_payload={}",
            command,
            UDP_VALIDATION_COMPARISON_SCHEMA,
            UDP_VALIDATION_COMPARISON_SCHEMA_VERSION,
            UDP_VALIDATION_COMPARISON_FAMILY,
            GATEWAY_HELLO_COMPARISON_LABEL,
            UDP_VALIDATION_COMPARISON_SCOPE,
            UDP_VALIDATION_COMPARISON_PROFILE,
            VALIDATION_EVIDENCE_STATE_COMPLETE,
            VALIDATION_GATE_STATE_PASSED,
            VALIDATION_GATE_STATE_REASON_READY,
            VALIDATION_GATE_STATE_REASON_FAMILY_READY,
            VALIDATION_VERDICT_READY,
            VALIDATION_BLOCKING_REASON_NONE,
            VALIDATION_BLOCKING_REASON_FAMILY_NONE,
            policy_epoch,
            session_id,
            datagram_mode_label(contract.resolved_datagram_mode),
            session_mode_label(session_mode),
            contract.signed_datagram_enabled,
            contract.rollout_stage,
            contract.carrier_datagrams_available,
            requested_max_udp_payload,
        )),
        OutputFormatArg::Json => Ok(serde_json::to_string_pretty(&serde_json::json!({
            "validation_result": "valid",
            "surface": "hello_validation",
            "command": command,
            "simulated_inputs": true,
            "comparison_schema": UDP_VALIDATION_COMPARISON_SCHEMA,
            "comparison_schema_version": UDP_VALIDATION_COMPARISON_SCHEMA_VERSION,
            "comparison_family": UDP_VALIDATION_COMPARISON_FAMILY,
            "comparison_label": GATEWAY_HELLO_COMPARISON_LABEL,
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
            "policy_epoch": policy_epoch,
            "session_id": session_id,
            "resolved_datagram_mode": datagram_mode_label(contract.resolved_datagram_mode),
            "session_mode": session_mode_label(session_mode),
            "signed_datagram_enabled": contract.signed_datagram_enabled,
            "rollout_stage": contract.rollout_stage,
            "carrier_datagrams_available": contract.carrier_datagrams_available,
            "requested_max_udp_payload": requested_max_udp_payload,
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

#[allow(clippy::too_many_arguments)]
fn render_gateway_hello_error_output(
    format: OutputFormatArg,
    command: &str,
    signed_datagram_enabled: bool,
    datagram_rollout: H3DatagramRollout,
    carrier_datagrams_available: bool,
    session_mode: SessionMode,
    requested_max_udp_payload: u64,
    policy_epoch: Option<u64>,
    resolved_datagram_mode: Option<&str>,
    error_class: &str,
    error_message: &str,
) -> anyhow::Result<String> {
    let resolved_datagram_mode = resolved_datagram_mode.unwrap_or("unresolved");
    match format {
        OutputFormatArg::Text => Ok(format!(
            "validation_result=invalid surface=hello_validation command={} simulated_inputs=true comparison_schema={} comparison_schema_version={} comparison_family={} comparison_label={} comparison_scope={} comparison_profile={} evidence_state={} gate_state={} gate_state_reason={} gate_state_reason_family={} verdict={} required_input_count=1 required_input_present_count=1 required_input_passed_count=0 required_input_missing_count=0 required_input_failed_count=1 required_input_unready_count=1 all_required_inputs_present=true all_required_inputs_passed=false missing_required_input_count=0 degradation_hold_count=0 blocking_reason_count=1 blocking_reason_key={} blocking_reason_family={} policy_epoch={} datagram_mode={} session_mode={} signed_datagram_enabled={} rollout_stage={} carrier_datagrams_available={} requested_max_udp_payload={} error_class={} error_message={}",
            command,
            UDP_VALIDATION_COMPARISON_SCHEMA,
            UDP_VALIDATION_COMPARISON_SCHEMA_VERSION,
            UDP_VALIDATION_COMPARISON_FAMILY,
            GATEWAY_HELLO_COMPARISON_LABEL,
            UDP_VALIDATION_COMPARISON_SCOPE,
            UDP_VALIDATION_COMPARISON_PROFILE,
            VALIDATION_EVIDENCE_STATE_COMPLETE,
            VALIDATION_GATE_STATE_BLOCKED,
            VALIDATION_GATE_STATE_REASON_REQUIRED_INPUTS_UNREADY,
            VALIDATION_GATE_STATE_REASON_FAMILY_GATING,
            VALIDATION_VERDICT_HOLD,
            error_class,
            VALIDATION_BLOCKING_REASON_FAMILY_VALIDATION,
            policy_epoch.map_or_else(|| "unresolved".to_owned(), |epoch| epoch.to_string()),
            resolved_datagram_mode,
            session_mode_label(session_mode),
            signed_datagram_enabled,
            datagram_rollout.stage_label(),
            carrier_datagrams_available,
            requested_max_udp_payload,
            error_class,
            error_message,
        )),
        OutputFormatArg::Json => Ok(serde_json::to_string_pretty(&serde_json::json!({
            "validation_result": "invalid",
            "surface": "hello_validation",
            "command": command,
            "simulated_inputs": true,
            "comparison_schema": UDP_VALIDATION_COMPARISON_SCHEMA,
            "comparison_schema_version": UDP_VALIDATION_COMPARISON_SCHEMA_VERSION,
            "comparison_family": UDP_VALIDATION_COMPARISON_FAMILY,
            "comparison_label": GATEWAY_HELLO_COMPARISON_LABEL,
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
            "policy_epoch": policy_epoch,
            "resolved_datagram_mode": resolved_datagram_mode,
            "session_mode": session_mode_label(session_mode),
            "signed_datagram_enabled": signed_datagram_enabled,
            "rollout_stage": datagram_rollout.stage_label(),
            "carrier_datagrams_available": carrier_datagrams_available,
            "requested_max_udp_payload": requested_max_udp_payload,
            "error_class": error_class,
            "error_message": error_message,
        }))?),
    }
}

fn datagram_mode_label(mode: ns_core::DatagramMode) -> &'static str {
    match mode {
        ns_core::DatagramMode::Unavailable => "unavailable",
        ns_core::DatagramMode::AvailableAndEnabled => "available_and_enabled",
        ns_core::DatagramMode::DisabledByPolicy => "disabled_by_policy",
    }
}

fn session_mode_label(mode: SessionMode) -> &'static str {
    match mode {
        SessionMode::Tcp => "tcp",
        SessionMode::Udp => "udp",
    }
}

#[cfg(test)]
mod tests {
    use super::{
        Cli, Command, DatagramRolloutArg, OutputFormatArg, SessionModeArg,
        render_gateway_hello_error_output, render_gateway_hello_output,
        render_gateway_startup_error_output, render_gateway_startup_output,
    };
    use clap::Parser;
    use ns_carrier_h3::{
        H3DatagramRollout, H3TransportError, resolve_h3_datagram_startup_contract,
    };
    use ns_core::{Capability, SessionMode};

    #[test]
    fn udp_session_mode_requests_udp_capability_only() {
        assert_eq!(
            SessionModeArg::Udp.requested_capabilities(),
            vec![Capability::UdpRelay]
        );
    }

    #[test]
    fn tcp_session_mode_requests_tcp_capability_only() {
        assert_eq!(
            SessionModeArg::Tcp.requested_capabilities(),
            vec![Capability::TcpRelay]
        );
    }

    #[test]
    fn cli_parses_validate_hello_with_udp_session_mode() {
        let cli = Cli::try_parse_from([
            "verta-gatewayd",
            "validate-hello",
            "--token",
            "target/test-token.jwt",
            "--jwks",
            "target/test-jwks.json",
            "--session-mode",
            "udp",
            "--carrier-datagrams-available",
        ])
        .expect("gateway hello CLI should parse");

        assert!(matches!(
            cli.command,
            Command::ValidateHello {
                session_mode: SessionModeArg::Udp,
                carrier_datagrams_available: true,
                ..
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
    fn gateway_cli_parses_startup_validation_surface() {
        let cli = Cli::try_parse_from([
            "verta-gatewayd",
            "validate-datagram-startup",
            "--signed-datagram-enabled=false",
            "--datagram-rollout",
            "automatic",
            "--carrier-datagrams-available",
        ])
        .expect("gateway startup CLI should parse");

        assert!(matches!(
            cli.command,
            Command::ValidateDatagramStartup {
                signed_datagram_enabled: false,
                datagram_rollout: DatagramRolloutArg::Automatic,
                carrier_datagrams_available: true,
            }
        ));
    }

    #[test]
    fn gateway_startup_output_renders_consistent_text_and_json_fields() {
        let contract =
            resolve_h3_datagram_startup_contract(true, H3DatagramRollout::Automatic, true)
                .expect("gateway startup contract should resolve");

        let text = render_gateway_startup_output(
            OutputFormatArg::Text,
            "validate-datagram-startup",
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
        assert!(text.contains("gate_state_reason=all_required_inputs_passed"));
        assert!(text.contains("gate_state_reason_family=ready"));
        assert!(text.contains("verdict=ready"));
        assert!(text.contains("required_input_count=1"));
        assert!(text.contains("required_input_passed_count=1"));
        assert!(text.contains("all_required_inputs_passed=true"));
        assert!(text.contains("datagram_mode=available_and_enabled"));

        let json = render_gateway_startup_output(
            OutputFormatArg::Json,
            "validate-datagram-startup",
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
        assert_eq!(value["resolved_datagram_mode"], "available_and_enabled");
    }

    #[test]
    fn gateway_hello_output_renders_consistent_text_and_json_fields() {
        let contract =
            resolve_h3_datagram_startup_contract(true, H3DatagramRollout::Automatic, true)
                .expect("gateway startup contract should resolve");

        let text = render_gateway_hello_output(
            OutputFormatArg::Text,
            "validate-hello",
            &contract,
            SessionMode::Udp,
            1_200,
            7,
            "SessionId([1, 1, 1, 1])",
        )
        .expect("text output should render");
        assert!(text.contains("validation_result=valid"));
        assert!(text.contains("comparison_schema=udp_rollout_validation_surface"));
        assert!(text.contains("comparison_schema_version=1"));
        assert!(text.contains("comparison_label=gateway_hello_validation"));
        assert!(text.contains("comparison_scope=surface"));
        assert!(text.contains("comparison_profile=validation_surface"));
        assert!(text.contains("gate_state=passed"));
        assert!(text.contains("verdict=ready"));
        assert!(text.contains("required_input_count=1"));
        assert!(text.contains("required_input_passed_count=1"));
        assert!(text.contains("all_required_inputs_passed=true"));
        assert!(text.contains("blocking_reason_key=none"));
        assert!(text.contains("session_mode=udp"));
        assert!(text.contains("datagram_mode=available_and_enabled"));

        let json = render_gateway_hello_output(
            OutputFormatArg::Json,
            "validate-hello",
            &contract,
            SessionMode::Udp,
            1_200,
            7,
            "SessionId([1, 1, 1, 1])",
        )
        .expect("json output should render");
        let value: serde_json::Value =
            serde_json::from_str(&json).expect("json output should parse");
        assert_eq!(value["validation_result"], "valid");
        assert_eq!(value["surface"], "hello_validation");
        assert_eq!(value["comparison_schema"], "udp_rollout_validation_surface");
        assert_eq!(value["comparison_schema_version"], 1);
        assert_eq!(value["comparison_family"], "udp_rollout_validation");
        assert_eq!(value["comparison_label"], "gateway_hello_validation");
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
        assert_eq!(value["blocking_reason_key"], "none");
        assert_eq!(value["session_mode"], "udp");
        assert_eq!(value["resolved_datagram_mode"], "available_and_enabled");
    }

    #[test]
    fn gateway_startup_error_output_renders_consistent_text_and_json_fields() {
        let text = render_gateway_startup_error_output(
            OutputFormatArg::Text,
            "validate-datagram-startup",
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
        assert!(text.contains("gate_state_reason=required_inputs_unready"));
        assert!(text.contains("gate_state_reason_family=gating"));
        assert!(text.contains("verdict=hold"));
        assert!(text.contains("required_input_count=1"));
        assert!(text.contains("required_input_failed_count=1"));
        assert!(text.contains("all_required_inputs_passed=false"));
        assert!(text.contains("blocking_reason_key=startup_contract_invalid"));
        assert!(text.contains("datagram_mode=unresolved"));

        let json = render_gateway_startup_error_output(
            OutputFormatArg::Json,
            "validate-datagram-startup",
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
        assert_eq!(value["resolved_datagram_mode"], "unresolved");
    }

    #[test]
    fn gateway_hello_error_output_renders_consistent_text_and_json_fields() {
        let text = render_gateway_hello_error_output(
            OutputFormatArg::Text,
            "validate-hello",
            true,
            H3DatagramRollout::Automatic,
            true,
            SessionMode::Udp,
            1_200,
            None,
            Some("available_and_enabled"),
            "hello_validation_invalid",
            "received hello violated negotiated datagram policy",
        )
        .expect("text error output should render");
        assert!(text.contains("validation_result=invalid"));
        assert!(text.contains("comparison_schema=udp_rollout_validation_surface"));
        assert!(text.contains("comparison_schema_version=1"));
        assert!(text.contains("comparison_label=gateway_hello_validation"));
        assert!(text.contains("comparison_scope=surface"));
        assert!(text.contains("comparison_profile=validation_surface"));
        assert!(text.contains("gate_state=blocked"));
        assert!(text.contains("verdict=hold"));
        assert!(text.contains("required_input_count=1"));
        assert!(text.contains("required_input_failed_count=1"));
        assert!(text.contains("all_required_inputs_passed=false"));
        assert!(text.contains("blocking_reason_family=validation"));
        assert!(text.contains("error_class=hello_validation_invalid"));

        let json = render_gateway_hello_error_output(
            OutputFormatArg::Json,
            "validate-hello",
            true,
            H3DatagramRollout::Automatic,
            true,
            SessionMode::Udp,
            1_200,
            None,
            Some("available_and_enabled"),
            "hello_validation_invalid",
            "received hello violated negotiated datagram policy",
        )
        .expect("json error output should render");
        let value: serde_json::Value =
            serde_json::from_str(&json).expect("json error output should parse");
        assert_eq!(value["validation_result"], "invalid");
        assert_eq!(value["comparison_schema"], "udp_rollout_validation_surface");
        assert_eq!(value["comparison_schema_version"], 1);
        assert_eq!(value["comparison_family"], "udp_rollout_validation");
        assert_eq!(value["comparison_label"], "gateway_hello_validation");
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
        assert_eq!(value["error_class"], "hello_validation_invalid");
        assert_eq!(value["resolved_datagram_mode"], "available_and_enabled");
    }
}
