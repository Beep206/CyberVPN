use criterion::{Criterion, black_box, criterion_group, criterion_main};
use ns_core::{Capability, CarrierKind, CarrierProfileId, DeviceBindingId, ManifestId};
use ns_wire::{ClientHello, Frame, FrameCodec};

fn sample_client_hello() -> Frame {
    Frame::ClientHello(ClientHello {
        min_version: 1,
        max_version: 1,
        client_nonce: [7_u8; 32],
        requested_capabilities: vec![Capability::TcpRelay, Capability::UdpRelay],
        carrier_kind: CarrierKind::H3,
        carrier_profile_id: CarrierProfileId::new("carrier-primary")
            .expect("bench fixture carrier profile should be valid"),
        manifest_id: ManifestId::new("man-2026-04-01-001")
            .expect("bench fixture manifest id should be valid"),
        device_binding_id: DeviceBindingId::new("device-1")
            .expect("bench fixture device binding id should be valid"),
        requested_idle_timeout_ms: 30_000,
        requested_max_udp_payload: 1_200,
        token: b"bench-token".to_vec(),
        client_metadata: Vec::new(),
    })
}

fn bench_wire_codec(c: &mut Criterion) {
    let frame = sample_client_hello();
    let encoded = FrameCodec::encode(&frame).expect("bench fixture should encode successfully");

    c.bench_function("ns_wire_encode_client_hello", |b| {
        b.iter(|| {
            let _ = FrameCodec::encode(black_box(&frame))
                .expect("bench fixture should encode successfully");
        });
    });

    c.bench_function("ns_wire_decode_client_hello", |b| {
        b.iter(|| {
            let _ = FrameCodec::decode(black_box(encoded.as_slice()))
                .expect("bench fixture should decode successfully");
        });
    });
}

criterion_group!(wire_benches, bench_wire_codec);
criterion_main!(wire_benches);
