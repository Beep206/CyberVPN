use ns_testkit::repo_root;
use ns_wire::{Frame, FrameCodec, decode_udp_datagram};
use serde::Serialize;
use std::fs;
use std::path::{Path, PathBuf};

type SeedReplay = fn(&[u8]) -> Result<bool, Box<dyn std::error::Error>>;

#[derive(Debug, Serialize)]
struct SmokeGroupSummary {
    group: String,
    expect_error: bool,
    seed_count: usize,
}

#[derive(Debug, Serialize)]
struct UdpFuzzSmokeSummary {
    summary_version: u8,
    all_passed: bool,
    groups: Vec<SmokeGroupSummary>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let root = repo_root();
    let fuzz_root = root.join("fuzz").join("cargo-fuzz");
    let summary_path = std::env::var_os("NORTHSTAR_UDP_FUZZ_SMOKE_SUMMARY_PATH")
        .map(PathBuf::from)
        .unwrap_or_else(default_summary_path);
    let groups = vec![
        replay_group(
            &fuzz_root.join("corpus").join("control_frame_decoder"),
            "corpus/control_frame_decoder",
            replay_control_frame_seed,
            false,
        )?,
        replay_group(
            &fuzz_root.join("corpus").join("udp_datagram_decoder"),
            "corpus/udp_datagram_decoder",
            replay_udp_datagram_seed,
            false,
        )?,
        replay_group(
            &fuzz_root.join("corpus").join("udp_fallback_frame_decoder"),
            "corpus/udp_fallback_frame_decoder",
            replay_udp_fallback_seed,
            false,
        )?,
        replay_group(
            &fuzz_root
                .join("fuzz_regressions")
                .join("control_frame_decoder"),
            "fuzz_regressions/control_frame_decoder",
            replay_control_frame_seed,
            true,
        )?,
        replay_group(
            &fuzz_root
                .join("fuzz_regressions")
                .join("udp_datagram_decoder"),
            "fuzz_regressions/udp_datagram_decoder",
            replay_udp_datagram_seed,
            true,
        )?,
        replay_group(
            &fuzz_root
                .join("fuzz_regressions")
                .join("udp_fallback_frame_decoder"),
            "fuzz_regressions/udp_fallback_frame_decoder",
            replay_udp_fallback_seed,
            true,
        )?,
    ];

    if let Some(parent) = summary_path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(
        &summary_path,
        serde_json::to_vec_pretty(&UdpFuzzSmokeSummary {
            summary_version: 1,
            all_passed: true,
            groups,
        })?,
    )?;

    println!("UDP fuzz smoke replay completed successfully.");
    println!("machine_readable_summary={}", summary_path.display());
    Ok(())
}

fn replay_group(
    dir: &Path,
    group_name: &str,
    replay: SeedReplay,
    expect_error: bool,
) -> Result<SmokeGroupSummary, Box<dyn std::error::Error>> {
    if !dir.exists() {
        return Err(format!("missing fuzz seed directory {}", dir.display()).into());
    }

    let mut paths = fs::read_dir(dir)?
        .filter_map(|entry| entry.ok().map(|value| value.path()))
        .filter(|path| path.extension().and_then(|value| value.to_str()) == Some("bin"))
        .collect::<Vec<PathBuf>>();
    paths.sort();

    if paths.is_empty() {
        return Err(format!("no fuzz seeds found in {}", dir.display()).into());
    }

    let seed_count = paths.len();
    for path in paths {
        let bytes = fs::read(&path)?;
        let was_error = replay(&bytes)?;
        if expect_error && !was_error {
            return Err(format!(
                "expected regression seed {} to keep failing",
                path.display()
            )
            .into());
        }
    }

    Ok(SmokeGroupSummary {
        group: group_name.to_owned(),
        expect_error,
        seed_count,
    })
}

fn replay_control_frame_seed(bytes: &[u8]) -> Result<bool, Box<dyn std::error::Error>> {
    Ok(FrameCodec::decode(bytes).is_err())
}

fn replay_udp_datagram_seed(bytes: &[u8]) -> Result<bool, Box<dyn std::error::Error>> {
    Ok(decode_udp_datagram(bytes).is_err())
}

fn replay_udp_fallback_seed(bytes: &[u8]) -> Result<bool, Box<dyn std::error::Error>> {
    match FrameCodec::decode(bytes) {
        Ok(
            Frame::UdpStreamOpen(_)
            | Frame::UdpStreamAccept(_)
            | Frame::UdpStreamPacket(_)
            | Frame::UdpStreamClose(_),
        ) => Ok(false),
        Ok(other) => Err(format!(
            "unexpected fallback frame type {} in smoke replay",
            other.frame_type().id()
        )
        .into()),
        Err(_) => Ok(true),
    }
}

fn default_summary_path() -> PathBuf {
    repo_root()
        .join("target")
        .join("northstar")
        .join("udp-fuzz-smoke-summary.json")
}
