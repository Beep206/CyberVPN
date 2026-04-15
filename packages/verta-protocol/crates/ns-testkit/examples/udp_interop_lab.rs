use ns_testkit::{
    UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_COMPATIBLE_HOST, UdpWanLabCommandKind, repo_root,
    udp_wan_lab_profile_by_slug, udp_wan_lab_profiles, verta_output_path,
};
use serde::Serialize;
use std::env;
use std::fs;
use std::path::PathBuf;
use std::process::Command;
use std::time::Instant;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum OutputFormat {
    Text,
    Json,
}

#[derive(Debug, Default)]
struct InteropArgs {
    profiles: Vec<String>,
    run_all: bool,
    list_only: bool,
    format: Option<OutputFormat>,
    summary_path: Option<PathBuf>,
}

#[derive(Debug, Serialize)]
struct UdpInteropLabProfileSummary {
    slug: String,
    spec_suite_ids: Vec<String>,
    description: String,
    command_kind: String,
    command_selector: String,
    requires_no_silent_fallback: bool,
}

#[derive(Debug, Serialize)]
struct UdpInteropLabProfileCatalog {
    catalog_schema: &'static str,
    catalog_schema_version: u8,
    host_label: String,
    source_lane: String,
    profiles: Vec<UdpInteropLabProfileSummary>,
}

#[derive(Debug, Serialize)]
struct UdpInteropLabProfileResult {
    slug: String,
    spec_suite_ids: Vec<String>,
    command_kind: String,
    command_selector: String,
    requires_no_silent_fallback: bool,
    status: &'static str,
    exit_code: Option<i32>,
    duration_ms: u128,
    command: Vec<String>,
}

#[derive(Debug, Serialize)]
struct UdpInteropLabSummary {
    summary_version: u8,
    all_passed: bool,
    profile_count: usize,
    profile_slugs: Vec<String>,
    failed_profile_slugs: Vec<String>,
    required_no_silent_fallback_profile_count: usize,
    required_no_silent_fallback_passed_count: usize,
    required_no_silent_fallback_profile_slugs: Vec<String>,
    explicit_fallback_profile_count: usize,
    udp_blocked_fallback_surface_passed: bool,
    datagram_only_unavailable_rejection_surface_passed: bool,
    policy_disabled_fallback_surface_passed: bool,
    queue_pressure_surface_passed: bool,
    transport_fallback_integrity_surface_passed: bool,
    results: Vec<UdpInteropLabProfileResult>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = parse_args(env::args().skip(1))?;
    if !args.list_only && !args.run_all && args.profiles.is_empty() {
        args.run_all = true;
    }

    if args.list_only {
        let catalog = UdpInteropLabProfileCatalog {
            catalog_schema: "udp_interop_profile_catalog",
            catalog_schema_version: 1,
            host_label: catalog_host_label(),
            source_lane: catalog_source_lane(),
            profiles: udp_wan_lab_profiles()
                .iter()
                .map(|profile| UdpInteropLabProfileSummary {
                    slug: profile.slug.to_owned(),
                    spec_suite_ids: profile
                        .spec_suite_ids
                        .iter()
                        .map(|value| (*value).to_owned())
                        .collect(),
                    description: profile.description.to_owned(),
                    command_kind: command_kind_label(profile.command_kind).to_owned(),
                    command_selector: profile.command_selector.to_owned(),
                    requires_no_silent_fallback: profile.requires_no_silent_fallback,
                })
                .collect(),
        };
        emit_profile_catalog(&catalog, args.format.unwrap_or(OutputFormat::Text))?;
        return Ok(());
    }

    let selected_profiles = select_profiles(&args)?;
    let mut results = Vec::with_capacity(selected_profiles.len());
    for profile in selected_profiles {
        results.push(run_profile(profile)?);
    }

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
    let explicit_fallback_profile_count = results
        .iter()
        .filter(|result| !result.requires_no_silent_fallback)
        .count();
    let mut required_no_silent_fallback_profile_slugs = results
        .iter()
        .filter(|result| result.requires_no_silent_fallback)
        .map(|result| result.slug.clone())
        .collect::<Vec<_>>();
    required_no_silent_fallback_profile_slugs.sort();
    let required_no_silent_fallback_profile_count = required_no_silent_fallback_profile_slugs.len();
    let required_no_silent_fallback_passed_count = results
        .iter()
        .filter(|result| result.requires_no_silent_fallback && result.status == "passed")
        .count();
    let udp_blocked_fallback_surface_passed = results
        .iter()
        .any(|result| result.slug == "udp-blocked-fallback" && result.status == "passed");
    let policy_disabled_fallback_surface_passed = results
        .iter()
        .any(|result| result.slug == "policy-disabled-fallback" && result.status == "passed");
    let datagram_only_unavailable_rejection_surface_passed = results.iter().any(|result| {
        result.slug == "datagram-only-unavailable-rejection" && result.status == "passed"
    });
    let queue_pressure_surface_passed = results
        .iter()
        .any(|result| result.slug == "queue-pressure-sticky" && result.status == "passed");
    let transport_fallback_integrity_surface_passed = required_no_silent_fallback_profile_count > 0
        && required_no_silent_fallback_passed_count == required_no_silent_fallback_profile_count
        && udp_blocked_fallback_surface_passed
        && policy_disabled_fallback_surface_passed
        && datagram_only_unavailable_rejection_surface_passed;
    let summary = UdpInteropLabSummary {
        summary_version: 5,
        all_passed: results.iter().all(|result| result.status == "passed"),
        profile_count: results.len(),
        profile_slugs,
        failed_profile_slugs,
        required_no_silent_fallback_profile_count,
        required_no_silent_fallback_passed_count,
        required_no_silent_fallback_profile_slugs,
        explicit_fallback_profile_count,
        udp_blocked_fallback_surface_passed,
        datagram_only_unavailable_rejection_surface_passed,
        policy_disabled_fallback_surface_passed,
        queue_pressure_surface_passed,
        transport_fallback_integrity_surface_passed,
        results,
    };

    let summary_path = args.summary_path.unwrap_or_else(default_summary_path);
    if let Some(parent) = summary_path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(&summary_path, serde_json::to_vec_pretty(&summary)?)?;

    match args.format.unwrap_or(OutputFormat::Text) {
        OutputFormat::Text => {
            println!("Verta UDP interoperability lab summary:");
            for result in &summary.results {
                let spec_ids = result.spec_suite_ids.join(", ");
                println!(
                    "- {slug} [{spec_ids}] {status} in {duration_ms}ms via {command_kind}:{command_selector}",
                    slug = result.slug,
                    spec_ids = spec_ids,
                    status = result.status,
                    duration_ms = result.duration_ms,
                    command_kind = result.command_kind,
                    command_selector = result.command_selector,
                );
            }
            println!("- profile_count: {}", summary.profile_count);
            println!("- profile_slugs: {}", summary.profile_slugs.join(", "));
            if summary.failed_profile_slugs.is_empty() {
                println!("- failed_profile_slugs: none");
            } else {
                println!(
                    "- failed_profile_slugs: {}",
                    summary.failed_profile_slugs.join(", ")
                );
            }
            println!(
                "- explicit_fallback_profile_count: {}",
                summary.explicit_fallback_profile_count
            );
            println!(
                "- udp_blocked_fallback_surface_passed: {}",
                summary.udp_blocked_fallback_surface_passed
            );
            println!(
                "- datagram_only_unavailable_rejection_surface_passed: {}",
                summary.datagram_only_unavailable_rejection_surface_passed
            );
            println!(
                "- policy_disabled_fallback_surface_passed: {}",
                summary.policy_disabled_fallback_surface_passed
            );
            println!(
                "- required_no_silent_fallback_profile_count: {}",
                summary.required_no_silent_fallback_profile_count
            );
            println!(
                "- required_no_silent_fallback_passed_count: {}",
                summary.required_no_silent_fallback_passed_count
            );
            if summary.required_no_silent_fallback_profile_slugs.is_empty() {
                println!("- required_no_silent_fallback_profile_slugs: none");
            } else {
                println!(
                    "- required_no_silent_fallback_profile_slugs: {}",
                    summary.required_no_silent_fallback_profile_slugs.join(", ")
                );
            }
            println!(
                "- queue_pressure_surface_passed: {}",
                summary.queue_pressure_surface_passed
            );
            println!(
                "- transport_fallback_integrity_surface_passed: {}",
                summary.transport_fallback_integrity_surface_passed
            );
            println!("machine_readable_summary={}", summary_path.display());
        }
        OutputFormat::Json => {
            println!("{}", serde_json::to_string_pretty(&summary)?);
        }
    }

    if !summary.all_passed {
        return Err("one or more UDP interoperability lab profiles failed".into());
    }

    Ok(())
}

fn parse_args(
    arguments: impl IntoIterator<Item = String>,
) -> Result<InteropArgs, Box<dyn std::error::Error>> {
    let mut parsed = InteropArgs::default();
    let mut iter = arguments.into_iter();
    while let Some(argument) = iter.next() {
        match argument.as_str() {
            "--all" => parsed.run_all = true,
            "--list" => parsed.list_only = true,
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
            "--help" | "-h" => {
                print_usage();
                std::process::exit(0);
            }
            other => return Err(format!("unrecognized argument {other}").into()),
        }
    }

    Ok(parsed)
}

fn print_usage() {
    eprintln!(
        "Usage: cargo run -p ns-testkit --example udp_interop_lab -- [--all | --profile <slug> ...] [--format text|json] [--summary-path <path>] [--list]"
    );
}

fn select_profiles(
    args: &InteropArgs,
) -> Result<Vec<&'static ns_testkit::UdpWanLabProfile>, Box<dyn std::error::Error>> {
    if args.run_all {
        return Ok(udp_wan_lab_profiles().iter().collect());
    }

    args.profiles
        .iter()
        .map(|slug| {
            udp_wan_lab_profile_by_slug(slug)
                .ok_or_else(|| format!("unknown UDP interoperability lab profile {slug}").into())
        })
        .collect()
}

fn run_profile(
    profile: &'static ns_testkit::UdpWanLabProfile,
) -> Result<UdpInteropLabProfileResult, Box<dyn std::error::Error>> {
    let repo_root = repo_root();
    let mut command = vec!["cargo".to_owned(), "test".to_owned()];
    command.extend(profile.cargo_args.iter().map(|value| (*value).to_owned()));

    let started_at = Instant::now();
    let status = Command::new(&command[0])
        .args(&command[1..])
        .current_dir(repo_root)
        .status()?;
    let duration_ms = started_at.elapsed().as_millis();

    Ok(UdpInteropLabProfileResult {
        slug: profile.slug.to_owned(),
        spec_suite_ids: profile
            .spec_suite_ids
            .iter()
            .map(|value| (*value).to_owned())
            .collect(),
        command_kind: command_kind_label(profile.command_kind).to_owned(),
        command_selector: profile.command_selector.to_owned(),
        requires_no_silent_fallback: profile.requires_no_silent_fallback,
        status: if status.success() { "passed" } else { "failed" },
        exit_code: status.code(),
        duration_ms,
        command,
    })
}

fn emit_profile_catalog(
    catalog: &UdpInteropLabProfileCatalog,
    format: OutputFormat,
) -> Result<(), Box<dyn std::error::Error>> {
    match format {
        OutputFormat::Text => {
            println!("Verta UDP interoperability lab profiles:");
            println!("- catalog_schema: {}", catalog.catalog_schema);
            println!(
                "- catalog_schema_version: {}",
                catalog.catalog_schema_version
            );
            println!("- host_label: {}", catalog.host_label);
            println!("- source_lane: {}", catalog.source_lane);
            for profile in &catalog.profiles {
                println!(
                    "- {slug} [{spec_ids}] -> {command_kind}:{command_selector}\n  {description}",
                    slug = profile.slug,
                    spec_ids = profile.spec_suite_ids.join(", "),
                    command_kind = profile.command_kind,
                    command_selector = profile.command_selector,
                    description = profile.description,
                );
            }
        }
        OutputFormat::Json => {
            println!("{}", serde_json::to_string_pretty(catalog)?);
        }
    }

    Ok(())
}

fn default_summary_path() -> PathBuf {
    verta_output_path("udp-interop-lab-summary.json")
}

fn command_kind_label(kind: UdpWanLabCommandKind) -> &'static str {
    match kind {
        UdpWanLabCommandKind::LiveUdp => "live_udp",
        UdpWanLabCommandKind::Lib => "lib",
    }
}

fn catalog_host_label() -> String {
    if let Ok(value) = env::var("VERTA_UDP_INTEROP_CATALOG_HOST_LABEL") {
        return value;
    }

    if let Ok(value) = env::var("VERTA_UDP_INTEROP_CATALOG_HOST_LABEL") {
        return value;
    }

    if cfg!(target_os = "windows") {
        "windows".to_owned()
    } else if cfg!(target_os = "macos") {
        "macos".to_owned()
    } else {
        "linux".to_owned()
    }
}

fn catalog_source_lane() -> String {
    env::var("VERTA_UDP_INTEROP_CATALOG_SOURCE_LANE")
        .or_else(|_| env::var("VERTA_UDP_INTEROP_CATALOG_SOURCE_LANE"))
        .unwrap_or_else(|_| UDP_INTEROP_PROFILE_CATALOG_SOURCE_LANE_COMPATIBLE_HOST.to_owned())
}
