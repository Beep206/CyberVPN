use criterion::{Criterion, black_box, criterion_group, criterion_main};
use ns_carrier_h3::{decode_received_udp_datagram, prepare_udp_datagram_for_send};
use ns_wire::{DatagramFlags, UdpDatagram, decode_udp_datagram};

fn sample_datagram(payload_len: usize) -> UdpDatagram {
    UdpDatagram {
        flow_id: 7,
        flags: DatagramFlags::new(0).expect("zero datagram flags should be valid"),
        payload: vec![0x5a; payload_len],
    }
}

fn bench_datagram_runtime(c: &mut Criterion) {
    for size in [64_usize, 512, 1200] {
        let datagram = sample_datagram(size);
        let encoded = ns_wire::encode_udp_datagram(&datagram)
            .expect("benchmark fixture datagram should encode");

        c.bench_function(
            &format!("ns_carrier_h3_prepare_udp_datagram_for_send_{size}"),
            |b| {
                b.iter(|| {
                    let _ = prepare_udp_datagram_for_send(black_box(&datagram), 1200)
                        .expect("fixture datagram should remain within the limit");
                });
            },
        );

        c.bench_function(
            &format!("ns_carrier_h3_decode_received_udp_datagram_{size}"),
            |b| {
                b.iter(|| {
                    let _ = decode_received_udp_datagram(black_box(encoded.as_slice()), 1200)
                        .expect("fixture datagram should decode successfully");
                });
            },
        );
    }

    let oversized = sample_datagram(1201);
    c.bench_function(
        "ns_carrier_h3_prepare_udp_datagram_reject_oversize_1201",
        |b| {
            b.iter(|| {
                let error = prepare_udp_datagram_for_send(black_box(&oversized), 1200)
                    .expect_err("oversized datagram should be rejected");
                black_box(error);
            });
        },
    );

    let encoded = ns_wire::encode_udp_datagram(&sample_datagram(1200))
        .expect("fixture datagram should encode");
    c.bench_function("ns_wire_decode_udp_datagram_1200_baseline", |b| {
        b.iter(|| {
            let _ = decode_udp_datagram(black_box(encoded.as_slice()))
                .expect("fixture datagram should decode");
        });
    });
}

criterion_group!(datagram_benches, bench_datagram_runtime);
criterion_main!(datagram_benches);
