use ns_testkit::{
    UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_NET_CHAOS, UdpWanLabCommandKind, repo_root,
    udp_wan_lab_profile_by_slug,
};
use serde::Serialize;
use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::Instant;

const UDP_NET_CHAOS_VERIFICATION_SCHEMA: &str = "udp_net_chaos_operator_verdict";
const UDP_NET_CHAOS_VERIFICATION_SCHEMA_VERSION: u8 = 1;
const UDP_NET_CHAOS_VERDICT_FAMILY: &str = "udp_net_chaos_campaign";
const UDP_NET_CHAOS_DECISION_SCOPE: &str = "udp_net_chaos";
const UDP_NET_CHAOS_DECISION_LABEL: &str = "udp_net_chaos_campaign";
const UDP_NET_CHAOS_PROFILE: &str = "net_chaos_campaign";
const UDP_NET_CHAOS_SUMMARY_VERSION: u8 = 1;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum OutputFormat {
    Text,
    Json,
}

#[derive(Debug, Default)]
struct NetChaosArgs {
    profiles: Vec<String>,
    run_all: bool,
    format: Option<OutputFormat>,
    summary_path: Option<PathBuf>,
    artifact_root: Option<PathBuf>,
    deployment_label: Option<String>,
    host_label: Option<String>,
}

#[derive(Debug)]
struct ResolvedConfig {
    selected_profiles: Vec<&'static NetChaosProfile>,
    format: OutputFormat,
    summary_path: PathBuf,
    artifact_root: Option<PathBuf>,
    deployment_label: Option<String>,
    host_label: Option<String>,
}

#[derive(Clone, Copy, Debug)]
struct NetChaosProfile {
    slug: &'static str,
    description: &'static str,
    impairment_label: &'static str,
    netem_args: &'static str,
    mtu: Option<u16>,
    underlying_profile_slug: &'static str,
}

const NET_CHAOS_PROFILES: &[NetChaosProfile] = &[
    NetChaosProfile {
        slug: "loss-1",
        description: "Loopback datagram transport under 1% packet loss.",
        impairment_label: "loss_1pct",
        netem_args: "loss 1%",
        mtu: None,
        underlying_profile_slug: "loss-burst",
    },
    NetChaosProfile {
        slug: "loss-5",
        description: "Loopback datagram transport under 5% packet loss.",
        impairment_label: "loss_5pct",
        netem_args: "loss 5%",
        mtu: None,
        underlying_profile_slug: "loss-burst",
    },
    NetChaosProfile {
        slug: "jitter-low",
        description: "Loopback datagram transport with low jitter and delay.",
        impairment_label: "jitter_low",
        netem_args: "delay 25ms 5ms",
        mtu: None,
        underlying_profile_slug: "delayed-black-hole",
    },
    NetChaosProfile {
        slug: "jitter-high",
        description: "Loopback datagram transport with higher jitter and delay.",
        impairment_label: "jitter_high",
        netem_args: "delay 120ms 30ms distribution normal",
        mtu: None,
        underlying_profile_slug: "delayed-black-hole",
    },
    NetChaosProfile {
        slug: "reorder-2",
        description: "Loopback datagram transport with 2% packet reordering.",
        impairment_label: "reorder_2pct",
        netem_args: "delay 20ms reorder 2% 50%",
        mtu: None,
        underlying_profile_slug: "reorder-window",
    },
    NetChaosProfile {
        slug: "reorder-10",
        description: "Loopback datagram transport with 10% packet reordering.",
        impairment_label: "reorder_10pct",
        netem_args: "delay 40ms reorder 10% 50%",
        mtu: None,
        underlying_profile_slug: "reorder-window",
    },
    NetChaosProfile {
        slug: "mtu-1200",
        description: "Datagram delivery at the maintained effective UDP payload ceiling of 1200 bytes.",
        impairment_label: "mtu_1200",
        netem_args: "",
        mtu: None,
        underlying_profile_slug: "mtu-pressure",
    },
    NetChaosProfile {
        slug: "udp-blocked",
        description: "Explicit stream fallback path when datagram carriage is unavailable.",
        impairment_label: "udp_blocked",
        netem_args: "",
        mtu: None,
        underlying_profile_slug: "udp-blocked-fallback",
    },
    NetChaosProfile {
        slug: "udp-flaky",
        description: "Loopback datagram transport under mixed delay and loss.",
        impairment_label: "udp_flaky",
        netem_args: "delay 90ms 20ms loss 12%",
        mtu: None,
        underlying_profile_slug: "mixed-delay-loss-recovery",
    },
];

#[derive(Debug, Serialize)]
struct UdpNetChaosProfileResult {
    slug: String,
    description: String,
    impairment_label: String,
    underlying_profile_slug: String,
    command_kind: String,
    command_selector: String,
    requires_no_silent_fallback: bool,
    status: &'static str,
    exit_code: Option<i32>,
    duration_ms: u128,
    command: Vec<String>,
    pcap_path: String,
    pcap_present: bool,
    pcap_size_bytes: u64,
    error_detail: Option<String>,
}

#[derive(Debug, Serialize)]
struct UdpNetChaosCampaignSummary {
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
    source_lane: &'static str,
    deployment_label: Option<String>,
    host_label: Option<String>,
    artifact_root: Option<String>,
    artifact_root_present: Option<bool>,
    profile_count: usize,
    profile_slugs: Vec<String>,
    failed_profile_slugs: Vec<String>,
    pcap_artifact_count: usize,
    pcap_artifact_present_count: usize,
    degradation_path_visibility_passed: bool,
    transport_fallback_integrity_surface_passed: bool,
    blocking_reason_count: usize,
    blocking_reason_key_count: usize,
    blocking_reason_family_count: usize,
    blocking_reason_key_counts: BTreeMap<String, usize>,
    blocking_reason_family_counts: BTreeMap<String, usize>,
    blocking_reasons: Vec<String>,
    blocking_reason_keys: Vec<String>,
    blocking_reason_families: Vec<String>,
    results: Vec<UdpNetChaosProfileResult>,
}

#[derive(Debug, Default)]
struct EvaluationState {
    blocking_reasons: Vec<String>,
    blocking_reason_keys: Vec<String>,
    blocking_reason_families: Vec<String>,
    blocking_reason_key_counts: BTreeMap<String, usize>,
    blocking_reason_family_counts: BTreeMap<String, usize>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = parse_args(env::args().skip(1))?;
    if !args.run_all && args.profiles.is_empty() {
        args.run_all = true;
    }
    let config = resolve_config(args)?;
    let results = run_selected_profiles(&config)?;
    let summary = build_summary(&config, results);

    if let Some(parent) = config.summary_path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(&config.summary_path, serde_json::to_vec_pretty(&summary)?)?;

    match config.format {
        OutputFormat::Text => print_text_summary(&summary, &config.summary_path),
        OutputFormat::Json => println!("{}", serde_json::to_string_pretty(&summary)?),
    }

    if summary.verdict != "ready" {
        return Err("udp net chaos campaign is not ready".into());
    }

    Ok(())
}

fn parse_args(
    arguments: impl IntoIterator<Item = String>,
) -> Result<NetChaosArgs, Box<dyn std::error::Error>> {
    let mut parsed = NetChaosArgs::default();
    let mut iter = arguments.into_iter();
    while let Some(argument) = iter.next() {
        match argument.as_str() {
            "--all" => parsed.run_all = true,
            "--profile" => {
                let value = iter.next().ok_or("--profile requires a slug argument")?;
                parsed.profiles.push(value);
            }
            "--format" => {
                let value = iter.next().ok_or("--format requires either text or json")?;
                parsed.format = Some(match value.as_str() {
                    "text" => OutputFormat::Text,
                    "json" => OutputFormat::Json,
                    other => return Err(format!("unsupported --format value {other}").into()),
                });
            }
            "--summary-path" => {
                let value = iter
                    .next()
                    .ok_or("--summary-path requires a filesystem path")?;
                parsed.summary_path = Some(PathBuf::from(value));
            }
            "--artifact-root" => {
                let value = iter
                    .next()
                    .ok_or("--artifact-root requires a filesystem path")?;
                parsed.artifact_root = Some(PathBuf::from(value));
            }
            "--deployment-label" => {
                parsed.deployment_label =
                    Some(iter.next().ok_or("--deployment-label requires a value")?);
            }
            "--host-label" => {
                parsed.host_label = Some(iter.next().ok_or("--host-label requires a value")?);
            }
            "--help" | "-h" => {
                print_usage();
                std::process::exit(0);
            }
            other => return Err(format!("unrecognized argument {other}").into()),
        }
    }

    Ok(parsed)
}

fn resolve_config(args: NetChaosArgs) -> Result<ResolvedConfig, Box<dyn std::error::Error>> {
    Ok(ResolvedConfig {
        selected_profiles: select_profiles(&args)?,
        format: args.format.unwrap_or(OutputFormat::Text),
        summary_path: args.summary_path.unwrap_or_else(default_summary_path),
        artifact_root: args.artifact_root.or_else(|| {
            env::var("NORTHSTAR_UDP_NET_CHAOS_ARTIFACT_ROOT")
                .ok()
                .map(PathBuf::from)
        }),
        deployment_label: args
            .deployment_label
            .or_else(|| env::var("NORTHSTAR_UDP_NET_CHAOS_DEPLOYMENT_LABEL").ok()),
        host_label: args
            .host_label
            .or_else(|| env::var("NORTHSTAR_UDP_NET_CHAOS_HOST_LABEL").ok()),
    })
}

fn select_profiles(
    args: &NetChaosArgs,
) -> Result<Vec<&'static NetChaosProfile>, Box<dyn std::error::Error>> {
    if args.run_all {
        return Ok(NET_CHAOS_PROFILES.iter().collect());
    }

    args.profiles
        .iter()
        .map(|slug| {
            NET_CHAOS_PROFILES
                .iter()
                .find(|profile| profile.slug == slug)
                .ok_or_else(|| format!("unknown UDP net chaos profile {slug}").into())
        })
        .collect()
}

fn run_selected_profiles(
    config: &ResolvedConfig,
) -> Result<Vec<UdpNetChaosProfileResult>, Box<dyn std::error::Error>> {
    let artifact_root = config
        .artifact_root
        .clone()
        .unwrap_or_else(default_artifact_root);
    fs::create_dir_all(&artifact_root)?;

    config
        .selected_profiles
        .iter()
        .map(|profile| run_profile(profile, &artifact_root))
        .collect()
}

fn run_profile(
    profile: &'static NetChaosProfile,
    artifact_root: &Path,
) -> Result<UdpNetChaosProfileResult, Box<dyn std::error::Error>> {
    let underlying =
        udp_wan_lab_profile_by_slug(profile.underlying_profile_slug).ok_or_else(|| {
            format!(
                "missing underlying UDP WAN profile {}",
                profile.underlying_profile_slug
            )
        })?;

    let repo_root = repo_root();
    let pcap_path = artifact_root.join(format!("{}.pcap", profile.slug));
    let script = build_unshare_script(&repo_root, &pcap_path, profile, underlying.cargo_args);

    let started_at = Instant::now();
    let status = Command::new("unshare")
        .args(["-Urn", "bash", "-lc", &script])
        .status();
    let duration_ms = started_at.elapsed().as_millis();

    let pcap_present = pcap_path.is_file();
    let pcap_size_bytes = fs::metadata(&pcap_path)
        .map(|metadata| metadata.len())
        .unwrap_or(0);

    let (status_label, exit_code, error_detail) = match status {
        Ok(value) => (
            if value.success() { "passed" } else { "failed" },
            value.code(),
            None,
        ),
        Err(error) => ("failed", None, Some(error.to_string())),
    };

    let mut command = vec![
        "unshare".to_owned(),
        "-Urn".to_owned(),
        "bash".to_owned(),
        "-lc".to_owned(),
        script,
    ];

    Ok(UdpNetChaosProfileResult {
        slug: profile.slug.to_owned(),
        description: profile.description.to_owned(),
        impairment_label: profile.impairment_label.to_owned(),
        underlying_profile_slug: profile.underlying_profile_slug.to_owned(),
        command_kind: command_kind_label(underlying.command_kind).to_owned(),
        command_selector: underlying.command_selector.to_owned(),
        requires_no_silent_fallback: underlying.requires_no_silent_fallback,
        status: status_label,
        exit_code,
        duration_ms,
        command: std::mem::take(&mut command),
        pcap_path: pcap_path.display().to_string(),
        pcap_present,
        pcap_size_bytes,
        error_detail,
    })
}

fn build_summary(
    config: &ResolvedConfig,
    results: Vec<UdpNetChaosProfileResult>,
) -> UdpNetChaosCampaignSummary {
    let mut state = EvaluationState::default();
    let artifact_root_present = config.artifact_root.as_ref().map(|path| path.is_dir());
    let mut profile_slugs = results
        .iter()
        .map(|result| result.slug.clone())
        .collect::<Vec<_>>();
    profile_slugs.sort();
    let mut failed_profile_slugs = results
        .iter()
        .filter(|result| result.status != "passed")
        .map(|result| result.slug.clone())
        .collect::<Vec<_>>();
    failed_profile_slugs.sort();
    let pcap_artifact_present_count = results.iter().filter(|result| result.pcap_present).count();
    let pcap_artifact_count = results.len();
    let degradation_path_visibility_passed =
        results.iter().any(|result| result.slug == "udp-blocked")
            && results
                .iter()
                .filter(|result| result.slug == "udp-blocked")
                .all(|result| result.status == "passed");
    let transport_fallback_integrity_surface_passed = results
        .iter()
        .filter(|result| result.requires_no_silent_fallback)
        .all(|result| result.status == "passed");

    if artifact_root_present != Some(true) {
        record_blocking_reason(
            &mut state,
            "net_chaos_artifact_root_missing",
            "artifact_root_missing",
            "artifact_retention",
        );
    }
    if pcap_artifact_present_count < pcap_artifact_count {
        record_blocking_reason(
            &mut state,
            "net_chaos_packet_capture_missing",
            "packet_capture_missing",
            "artifact_retention",
        );
    }
    if !failed_profile_slugs.is_empty() {
        record_blocking_reason(
            &mut state,
            "net_chaos_profile_failures",
            "profiles_failed",
            "interop_execution",
        );
    }
    if !degradation_path_visibility_passed {
        record_blocking_reason(
            &mut state,
            "net_chaos_degradation_path_incomplete",
            "degradation_path_incomplete",
            "interop_execution",
        );
    }
    if !transport_fallback_integrity_surface_passed {
        record_blocking_reason(
            &mut state,
            "net_chaos_transport_fallback_integrity_failed",
            "transport_fallback_integrity_failed",
            "interop_execution",
        );
    }

    let verdict = if state.blocking_reasons.is_empty() {
        "ready"
    } else {
        "hold"
    };
    let evidence_state = if verdict == "ready" {
        "complete"
    } else {
        "degraded"
    };
    let gate_state = if verdict == "ready" { "pass" } else { "hold" };

    UdpNetChaosCampaignSummary {
        summary_version: UDP_NET_CHAOS_SUMMARY_VERSION,
        verification_schema: UDP_NET_CHAOS_VERIFICATION_SCHEMA,
        verification_schema_version: UDP_NET_CHAOS_VERIFICATION_SCHEMA_VERSION,
        verdict_family: UDP_NET_CHAOS_VERDICT_FAMILY,
        decision_scope: UDP_NET_CHAOS_DECISION_SCOPE,
        decision_label: UDP_NET_CHAOS_DECISION_LABEL,
        profile: UDP_NET_CHAOS_PROFILE,
        verdict,
        evidence_state,
        gate_state,
        gate_state_reason: if verdict == "ready" {
            "all_required_inputs_passed"
        } else {
            "blocking_reasons_present"
        },
        gate_state_reason_family: if verdict == "ready" {
            "ready"
        } else {
            "gating"
        },
        source_lane: UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_NET_CHAOS,
        deployment_label: config.deployment_label.clone(),
        host_label: config.host_label.clone(),
        artifact_root: config
            .artifact_root
            .as_ref()
            .map(|path| path.display().to_string()),
        artifact_root_present,
        profile_count: results.len(),
        profile_slugs,
        failed_profile_slugs,
        pcap_artifact_count,
        pcap_artifact_present_count,
        degradation_path_visibility_passed,
        transport_fallback_integrity_surface_passed,
        blocking_reason_count: state.blocking_reasons.len(),
        blocking_reason_key_count: state.blocking_reason_key_counts.len(),
        blocking_reason_family_count: state.blocking_reason_family_counts.len(),
        blocking_reason_key_counts: state.blocking_reason_key_counts,
        blocking_reason_family_counts: state.blocking_reason_family_counts,
        blocking_reasons: state.blocking_reasons,
        blocking_reason_keys: state.blocking_reason_keys,
        blocking_reason_families: state.blocking_reason_families,
        results,
    }
}

fn build_unshare_script(
    repo_root: &Path,
    pcap_path: &Path,
    profile: &NetChaosProfile,
    cargo_args: &[&str],
) -> String {
    let repo_root = shell_quote(repo_root);
    let pcap_path = shell_quote(pcap_path);
    let cargo_command = shell_join(
        std::iter::once("cargo".to_owned())
            .chain(std::iter::once("test".to_owned()))
            .chain(cargo_args.iter().map(|value| (*value).to_owned()))
            .collect::<Vec<_>>()
            .iter()
            .map(|value| value.as_str()),
    );
    let mtu_command = profile
        .mtu
        .map(|mtu| format!("ip link set lo mtu {mtu}; "))
        .unwrap_or_default();
    let netem_command = if profile.netem_args.is_empty() {
        String::new()
    } else {
        format!("tc qdisc add dev lo root netem {}; ", profile.netem_args)
    };
    format!(
        "set -euo pipefail; cd {repo_root}; ip link set lo up; {mtu_command}{netem_command}tcpdump -U -i lo -w {pcap_path} >/dev/null 2>&1 & TCPDUMP_PID=$!; cleanup() {{ kill $TCPDUMP_PID >/dev/null 2>&1 || true; wait $TCPDUMP_PID >/dev/null 2>&1 || true; tc qdisc del dev lo root >/dev/null 2>&1 || true; ip link set lo mtu 65536 >/dev/null 2>&1 || true; }}; trap cleanup EXIT; {cargo_command}"
    )
}

fn shell_join<'a>(values: impl IntoIterator<Item = &'a str>) -> String {
    values
        .into_iter()
        .map(shell_quote_str)
        .collect::<Vec<_>>()
        .join(" ")
}

fn shell_quote(path: &Path) -> String {
    shell_quote_str(&path.display().to_string())
}

fn shell_quote_str(value: &str) -> String {
    let escaped = value.replace('\'', "'\"'\"'");
    format!("'{escaped}'")
}

fn default_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-net-chaos-campaign-summary.json")
}

fn default_artifact_root() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("net-chaos")
}

fn print_text_summary(summary: &UdpNetChaosCampaignSummary, summary_path: &Path) {
    println!("Northstar UDP net-chaos campaign summary:");
    println!("- verdict: {}", summary.verdict);
    println!("- source_lane: {}", summary.source_lane);
    println!(
        "- artifact_root_present: {}",
        summary.artifact_root_present.unwrap_or(false)
    );
    println!("- pcap_artifact_count: {}", summary.pcap_artifact_count);
    println!(
        "- pcap_artifact_present_count: {}",
        summary.pcap_artifact_present_count
    );
    println!(
        "- degradation_path_visibility_passed: {}",
        summary.degradation_path_visibility_passed
    );
    println!(
        "- transport_fallback_integrity_surface_passed: {}",
        summary.transport_fallback_integrity_surface_passed
    );
    if summary.blocking_reasons.is_empty() {
        println!("- blocking_reasons: none");
    } else {
        println!(
            "- blocking_reasons: {}",
            summary.blocking_reasons.join(", ")
        );
    }
    for result in &summary.results {
        println!(
            "- {slug} {status} pcap={pcap}",
            slug = result.slug,
            status = result.status,
            pcap = result.pcap_path
        );
    }
    println!("machine_readable_summary={}", summary_path.display());
}

fn print_usage() {
    eprintln!(
        "Usage: cargo run -p ns-testkit --example udp_net_chaos_campaign -- [--all | --profile <slug> ...] [--format text|json] [--summary-path <path>] [--artifact-root <path>] [--deployment-label <label>] [--host-label <label>]"
    );
}

fn command_kind_label(kind: UdpWanLabCommandKind) -> &'static str {
    match kind {
        UdpWanLabCommandKind::LiveUdp => "live_udp",
        UdpWanLabCommandKind::Lib => "lib",
    }
}

fn record_blocking_reason(state: &mut EvaluationState, reason: &str, key: &str, family: &str) {
    state.blocking_reasons.push(reason.to_owned());
    state.blocking_reason_keys.push(key.to_owned());
    state.blocking_reason_families.push(family.to_owned());
    *state
        .blocking_reason_key_counts
        .entry(key.to_owned())
        .or_insert(0) += 1;
    *state
        .blocking_reason_family_counts
        .entry(family.to_owned())
        .or_insert(0) += 1;
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn unique_temp_path(label: &str) -> PathBuf {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock should be after epoch")
            .as_nanos();
        env::temp_dir().join(format!(
            "northstar-udp-net-chaos-{label}-{}-{nanos}",
            std::process::id()
        ))
    }

    fn sample_result(
        slug: &str,
        requires_no_silent_fallback: bool,
        status: &'static str,
    ) -> UdpNetChaosProfileResult {
        UdpNetChaosProfileResult {
            slug: slug.to_owned(),
            description: slug.to_owned(),
            impairment_label: slug.to_owned(),
            underlying_profile_slug: slug.to_owned(),
            command_kind: "live_udp".to_owned(),
            command_selector: slug.to_owned(),
            requires_no_silent_fallback,
            status,
            exit_code: Some(if status == "passed" { 0 } else { 1 }),
            duration_ms: 1,
            command: vec!["cargo".to_owned()],
            pcap_path: "/tmp/test.pcap".to_owned(),
            pcap_present: true,
            pcap_size_bytes: 128,
            error_detail: None,
        }
    }

    fn sample_config() -> ResolvedConfig {
        let artifact_root = unique_temp_path("artifact-root");
        fs::create_dir_all(&artifact_root).expect("artifact root should be creatable");
        ResolvedConfig {
            selected_profiles: Vec::new(),
            format: OutputFormat::Json,
            summary_path: unique_temp_path("summary"),
            artifact_root: Some(artifact_root),
            deployment_label: Some("chaos-local".to_owned()),
            host_label: Some("lab-linux".to_owned()),
        }
    }

    #[test]
    fn net_chaos_profile_inventory_contains_expected_named_profiles() {
        let slugs = NET_CHAOS_PROFILES
            .iter()
            .map(|profile| profile.slug)
            .collect::<Vec<_>>();
        assert!(slugs.contains(&"loss-1"));
        assert!(slugs.contains(&"loss-5"));
        assert!(slugs.contains(&"jitter-low"));
        assert!(slugs.contains(&"jitter-high"));
        assert!(slugs.contains(&"reorder-2"));
        assert!(slugs.contains(&"reorder-10"));
        assert!(slugs.contains(&"mtu-1200"));
        assert!(slugs.contains(&"udp-blocked"));
        assert!(slugs.contains(&"udp-flaky"));
    }

    #[test]
    fn net_chaos_summary_blocks_when_profiles_fail() {
        let config = sample_config();
        let summary = build_summary(
            &config,
            vec![
                sample_result("loss-1", true, "passed"),
                sample_result("udp-blocked", false, "failed"),
            ],
        );

        assert_eq!(summary.verdict, "hold");
        assert_eq!(
            summary.source_lane,
            UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_NET_CHAOS
        );
        assert!(
            summary
                .blocking_reasons
                .iter()
                .any(|value| value == "net_chaos_profile_failures")
        );
    }

    #[test]
    fn net_chaos_summary_is_ready_when_all_profiles_and_pcaps_exist() {
        let config = sample_config();
        let summary = build_summary(
            &config,
            vec![
                sample_result("loss-1", true, "passed"),
                sample_result("reorder-2", true, "passed"),
                sample_result("udp-blocked", false, "passed"),
            ],
        );

        assert_eq!(summary.verdict, "ready");
        assert_eq!(summary.pcap_artifact_present_count, 3);
        assert!(summary.degradation_path_visibility_passed);
        assert!(summary.transport_fallback_integrity_surface_passed);
    }

    #[test]
    fn net_chaos_unshare_script_includes_netem_and_capture() {
        let repo = PathBuf::from("/tmp/repo");
        let pcap = PathBuf::from("/tmp/capture.pcap");
        let profile = NET_CHAOS_PROFILES
            .iter()
            .find(|profile| profile.slug == "loss-5")
            .expect("loss-5 profile should exist");
        let script = build_unshare_script(&repo, &pcap, profile, &["-p", "ns-carrier-h3"]);

        assert!(script.contains("tc qdisc add dev lo root netem loss 5%"));
        assert!(script.contains("tcpdump -U -i lo -w"));
        assert!(script.contains("cargo"));
    }
}
