use ns_carrier_h3::{
    H3DatagramRuntimeConfig, H3DatagramSocket, decode_received_udp_datagram,
    prepare_udp_datagram_for_send,
};
use ns_session::DatagramIo;
use ns_testkit::{verta_env_path, verta_env_value};
use ns_wire::{DatagramFlags, UdpDatagram, decode_udp_datagram, encode_udp_datagram};
use serde::Serialize;
use std::hint::black_box;
use std::time::Instant;
use tokio::runtime::Builder;

const DEFAULT_ITERATIONS: usize = 25_000;
const MAX_WRAPPER_OVER_BASELINE_RATIO: u128 = 6;
const MAX_REJECT_OVER_SEND_RATIO: u128 = 3;
const MAX_QUEUE_REJECT_OVER_SEND_RATIO: u128 = 5;
const MAX_QUEUE_RECOVERY_OVER_SEND_RATIO: u128 = 6;
const MAX_REPEATED_QUEUE_RECOVERY_OVER_SEND_RATIO: u128 = 7;
const MAX_BURST_REJECT_OVER_QUEUE_RATIO: u128 = 5;
const RATIO_DENOMINATOR: u128 = 1;
const RATIO_GRACE_NS: u128 = 5_000_000;

#[derive(Debug, Serialize)]
struct PerfCaseSummary {
    label: String,
    candidate_ns: u128,
    baseline_ns: u128,
    allowed_ns: u128,
    passed: bool,
}

#[derive(Debug, Serialize)]
struct UdpPerfGateSummary {
    summary_version: u8,
    iterations: usize,
    all_passed: bool,
    results: Vec<PerfCaseSummary>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let iterations = verta_env_value(
        "VERTA_UDP_PERF_GATE_ITERATIONS",
        "VERTA_UDP_PERF_GATE_ITERATIONS",
    )
    .and_then(|value| value.parse::<usize>().ok())
    .filter(|value| *value > 0)
    .unwrap_or(DEFAULT_ITERATIONS);
    let summary_path = verta_env_path(
        "VERTA_UDP_PERF_SUMMARY_PATH",
        "VERTA_UDP_PERF_SUMMARY_PATH",
        "udp-perf-gate-summary.json",
    );

    println!("Running Verta UDP performance gate with {iterations} iterations per case.");

    let mut results = Vec::new();

    for payload_len in [64_usize, 512, 1_200] {
        let datagram = sample_datagram(payload_len);
        let encoded = encode_udp_datagram(&datagram)?;

        let baseline_send = measure(iterations, || {
            encode_udp_datagram(black_box(&datagram)).expect("baseline encode should succeed");
        });
        let wrapped_send = measure(iterations, || {
            prepare_udp_datagram_for_send(black_box(&datagram), 1_200)
                .expect("wrapped send should succeed");
        });
        results.push(assert_ratio(
            &format!("prepare_udp_datagram_for_send[{payload_len}]"),
            wrapped_send,
            baseline_send,
            MAX_WRAPPER_OVER_BASELINE_RATIO,
        )?);

        let baseline_recv = measure(iterations, || {
            decode_udp_datagram(black_box(encoded.as_slice()))
                .expect("baseline decode should succeed");
        });
        let wrapped_recv = measure(iterations, || {
            decode_received_udp_datagram(black_box(encoded.as_slice()), 1_200)
                .expect("wrapped decode should succeed");
        });
        results.push(assert_ratio(
            &format!("decode_received_udp_datagram[{payload_len}]"),
            wrapped_recv,
            baseline_recv,
            MAX_WRAPPER_OVER_BASELINE_RATIO,
        )?);
    }

    let baseline_send = measure(iterations, || {
        prepare_udp_datagram_for_send(black_box(&sample_datagram(1_200)), 1_200)
            .expect("wrapped send should succeed");
    });
    let oversized = sample_datagram(1_201);
    let reject_send = measure(iterations, || {
        prepare_udp_datagram_for_send(black_box(&oversized), 1_200)
            .expect_err("oversized datagram should stay rejected");
    });
    results.push(assert_ratio(
        "prepare_udp_datagram_for_send[1201-reject]",
        reject_send,
        baseline_send,
        MAX_REJECT_OVER_SEND_RATIO,
    )?);
    let baseline_recv = measure(iterations, || {
        decode_received_udp_datagram(
            black_box(
                encode_udp_datagram(&sample_datagram(1_200))
                    .expect("baseline datagram should encode")
                    .as_slice(),
            ),
            1_200,
        )
        .expect("baseline wrapped decode should succeed");
    });
    let oversized_recv = measure(iterations, || {
        decode_received_udp_datagram(
            black_box(
                encode_udp_datagram(&sample_datagram(1_201))
                    .expect("oversized datagram should still encode for reject-path benchmarking")
                    .as_slice(),
            ),
            1_200,
        )
        .expect_err("oversized receive path should stay rejected");
    });
    results.push(assert_ratio(
        "decode_received_udp_datagram[1201-reject]",
        oversized_recv,
        baseline_recv,
        MAX_REJECT_OVER_SEND_RATIO,
    )?);

    let runtime = Builder::new_current_thread().enable_all().build()?;
    let queue_baseline = measure(iterations, || {
        runtime.block_on(async {
            let socket = H3DatagramSocket::with_runtime_config(H3DatagramRuntimeConfig {
                max_payload_bytes: 1_200,
                max_buffered_bytes: 32,
                max_buffered_datagrams: 8,
                max_buffered_datagrams_per_flow: 8,
            })
            .expect("queue baseline runtime config should be valid");
            socket
                .send(sample_datagram(8))
                .await
                .expect("baseline datagram should fit");
            let drained = socket.drain_outbound();
            assert_eq!(drained.len(), 1);
        });
    });
    let queue_reject = measure(iterations, || {
        runtime.block_on(async {
            let socket = H3DatagramSocket::with_runtime_config(H3DatagramRuntimeConfig {
                max_payload_bytes: 1_200,
                max_buffered_bytes: 8,
                max_buffered_datagrams: 8,
                max_buffered_datagrams_per_flow: 8,
            })
            .expect("queue reject runtime config should be valid");
            socket
                .send(sample_datagram(8))
                .await
                .expect("first datagram should fill the queue budget");
            socket
                .send(sample_datagram(1))
                .await
                .expect_err("queue-full datagram should stay rejected");
        });
    });
    results.push(assert_ratio(
        "H3DatagramSocket.queue_full_reject",
        queue_reject,
        queue_baseline,
        MAX_QUEUE_REJECT_OVER_SEND_RATIO,
    )?);
    let queue_recovery = measure(iterations, || {
        runtime.block_on(async {
            let socket = H3DatagramSocket::with_runtime_config(H3DatagramRuntimeConfig {
                max_payload_bytes: 1_200,
                max_buffered_bytes: 8,
                max_buffered_datagrams: 8,
                max_buffered_datagrams_per_flow: 8,
            })
            .expect("queue recovery runtime config should be valid");
            socket
                .send(sample_datagram(8))
                .await
                .expect("first datagram should fill the queue budget");
            socket
                .send(sample_datagram(1))
                .await
                .expect_err("queue-full datagram should stay rejected before recovery");
            let drained = socket.drain_outbound();
            assert_eq!(drained.len(), 1);
            socket
                .send(sample_datagram(8))
                .await
                .expect("the first post-drain datagram should recover cleanly");
            let drained = socket.drain_outbound();
            assert_eq!(drained.len(), 1);
        });
    });
    results.push(assert_ratio(
        "H3DatagramSocket.queue_recovery_send",
        queue_recovery,
        queue_baseline,
        MAX_QUEUE_RECOVERY_OVER_SEND_RATIO,
    )?);
    let repeated_queue_recovery = measure(iterations, || {
        runtime.block_on(async {
            let socket = H3DatagramSocket::with_runtime_config(H3DatagramRuntimeConfig {
                max_payload_bytes: 1_200,
                max_buffered_bytes: 8,
                max_buffered_datagrams: 8,
                max_buffered_datagrams_per_flow: 8,
            })
            .expect("repeated queue recovery runtime config should be valid");
            socket
                .send(sample_datagram(8))
                .await
                .expect("first datagram should fill the queue budget");
            socket
                .send(sample_datagram(1))
                .await
                .expect_err("queue-full datagram should stay rejected before first recovery");
            let drained = socket.drain_outbound();
            assert_eq!(drained.len(), 1);
            socket
                .send(sample_datagram(8))
                .await
                .expect("first post-drain datagram should recover cleanly");
            let drained = socket.drain_outbound();
            assert_eq!(drained.len(), 1);
            socket
                .send(sample_datagram(8))
                .await
                .expect("second datagram should fill the queue budget again");
            socket
                .send(sample_datagram(1))
                .await
                .expect_err("queue-full datagram should stay rejected before second recovery");
            let drained = socket.drain_outbound();
            assert_eq!(drained.len(), 1);
            socket
                .send(sample_datagram(8))
                .await
                .expect("second post-drain datagram should recover cleanly");
            let drained = socket.drain_outbound();
            assert_eq!(drained.len(), 1);
        });
    });
    results.push(assert_ratio(
        "H3DatagramSocket.repeated_queue_recovery_send",
        repeated_queue_recovery,
        queue_baseline,
        MAX_REPEATED_QUEUE_RECOVERY_OVER_SEND_RATIO,
    )?);
    let flow_burst_reject = measure(iterations, || {
        runtime.block_on(async {
            let socket = H3DatagramSocket::with_runtime_config(H3DatagramRuntimeConfig {
                max_payload_bytes: 8,
                max_buffered_bytes: 64,
                max_buffered_datagrams: 8,
                max_buffered_datagrams_per_flow: 1,
            })
            .expect("flow-burst runtime config should be valid");
            socket
                .send(sample_datagram(8))
                .await
                .expect("first datagram should fit per-flow budget");
            socket
                .send(sample_datagram(1))
                .await
                .expect_err("second per-flow datagram should stay rejected");
        });
    });
    results.push(assert_ratio(
        "H3DatagramSocket.flow_burst_reject",
        flow_burst_reject,
        queue_baseline,
        MAX_BURST_REJECT_OVER_QUEUE_RATIO,
    )?);
    let session_burst_reject = measure(iterations, || {
        runtime.block_on(async {
            let socket = H3DatagramSocket::with_runtime_config(H3DatagramRuntimeConfig {
                max_payload_bytes: 8,
                max_buffered_bytes: 64,
                max_buffered_datagrams: 1,
                max_buffered_datagrams_per_flow: 8,
            })
            .expect("session-burst runtime config should be valid");
            socket
                .send(sample_datagram(8))
                .await
                .expect("first datagram should fit session budget");
            socket
                .send(UdpDatagram {
                    flow_id: 99,
                    ..sample_datagram(1)
                })
                .await
                .expect_err("second session datagram should stay rejected");
        });
    });
    results.push(assert_ratio(
        "H3DatagramSocket.session_burst_reject",
        session_burst_reject,
        queue_baseline,
        MAX_BURST_REJECT_OVER_QUEUE_RATIO,
    )?);

    let summary = UdpPerfGateSummary {
        summary_version: 1,
        iterations,
        all_passed: results.iter().all(|result| result.passed),
        results,
    };
    if let Some(parent) = summary_path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    std::fs::write(&summary_path, serde_json::to_vec_pretty(&summary)?)?;

    println!("Verta UDP performance gate completed successfully.");
    println!("machine_readable_summary={}", summary_path.display());
    Ok(())
}

fn sample_datagram(payload_len: usize) -> UdpDatagram {
    UdpDatagram {
        flow_id: 7,
        flags: DatagramFlags::new(0).expect("zero datagram flags should be valid"),
        payload: vec![0x5a; payload_len],
    }
}

fn measure(iterations: usize, mut run: impl FnMut()) -> u128 {
    let start = Instant::now();
    for _ in 0..iterations {
        run();
    }
    start.elapsed().as_nanos()
}

fn assert_ratio(
    label: &str,
    candidate_ns: u128,
    baseline_ns: u128,
    max_ratio: u128,
) -> Result<PerfCaseSummary, Box<dyn std::error::Error>> {
    println!(
        "{label}: candidate={}ns baseline={}ns ratio_limit={}x",
        candidate_ns, baseline_ns, max_ratio
    );

    let allowed_ns = baseline_ns
        .saturating_mul(max_ratio)
        .saturating_div(RATIO_DENOMINATOR)
        .saturating_add(RATIO_GRACE_NS);
    let summary = PerfCaseSummary {
        label: label.to_owned(),
        candidate_ns,
        baseline_ns,
        allowed_ns,
        passed: candidate_ns <= allowed_ns,
    };
    if !summary.passed {
        return Err(format!(
            "{label} exceeded its regression threshold: candidate {candidate_ns}ns > allowed {allowed_ns}ns"
        )
        .into());
    }

    Ok(summary)
}
