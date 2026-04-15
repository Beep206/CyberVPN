use hex::decode;
use ns_wire::{Frame, FrameCodec, WireError, decode_udp_datagram, encode_udp_datagram};
use serde::Deserialize;
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Deserialize)]
struct ValidFixture {
    hex: String,
}

#[derive(Debug, Deserialize)]
struct InvalidFixture {
    expected_error: String,
    hex: String,
}

fn decode_hex_fixture(path: &str) -> Vec<u8> {
    let fixture: ValidFixture =
        serde_json::from_str(&load_fixture_text(path)).expect("wire fixture json should parse");
    decode(fixture.hex).expect("wire fixture hex should decode")
}

fn decode_invalid_fixture(path: &str) -> (Vec<u8>, String) {
    let fixture: InvalidFixture =
        serde_json::from_str(&load_fixture_text(path)).expect("wire fixture json should parse");
    (
        decode(fixture.hex).expect("wire fixture hex should decode"),
        fixture.expected_error,
    )
}

fn load_fixture_text(relative: &str) -> String {
    let mut root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    root.pop();
    root.pop();
    fs::read_to_string(root.join("fixtures").join(relative))
        .expect("wire fixture should be readable")
}

fn error_kind(error: &WireError) -> &'static str {
    match error {
        WireError::UnknownFrameType(_) => "UnknownFrameType",
        WireError::Truncated => "Truncated",
        WireError::LengthMismatch => "LengthMismatch",
        WireError::FrameTooLarge => "FrameTooLarge",
        WireError::NonCanonicalVarint(_) => "NonCanonicalVarint",
        WireError::VarintOverflow(_) => "VarintOverflow",
        WireError::InvalidUtf8 => "InvalidUtf8",
        WireError::Validation(_) => "Validation",
    }
}

#[test]
fn decodes_and_reencodes_valid_ping_fixture() {
    let bytes = decode_hex_fixture("wire/v1/valid/NS-FX-PING-001.json");
    let frame = FrameCodec::decode(&bytes).expect("valid ping fixture should decode");

    match &frame {
        Frame::Ping(ping) => {
            assert_eq!(ping.ping_id, 1);
            assert_eq!(ping.timestamp, 2);
        }
        other => panic!("expected ping frame, got {other:?}"),
    }

    let reencoded = FrameCodec::encode(&frame).expect("decoded ping should re-encode");
    assert_eq!(reencoded, bytes);
}

#[test]
fn decodes_and_reencodes_valid_client_hello_fixture() {
    let bytes = decode_hex_fixture("wire/v1/valid/NS-FX-HELLO-001.json");
    let frame = FrameCodec::decode(&bytes).expect("valid hello fixture should decode");

    match &frame {
        Frame::ClientHello(hello) => {
            assert_eq!(hello.manifest_id.as_str(), "man-2026-04-01-001");
            assert_eq!(hello.device_binding_id.as_str(), "device-1");
            assert_eq!(hello.carrier_profile_id.as_str(), "carrier-primary");
            assert_eq!(hello.requested_capabilities.len(), 2);
        }
        other => panic!("expected client hello frame, got {other:?}"),
    }

    let reencoded = FrameCodec::encode(&frame).expect("decoded hello should re-encode");
    assert_eq!(reencoded, bytes);
}

#[test]
fn rejects_truncated_client_hello_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-HELLO-TRUNCATED-001.json");
    let error = FrameCodec::decode(&bytes).expect_err("truncated hello fixture should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_invalid_minmax_client_hello_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-HELLO-MINMAX-002.json");
    let error = FrameCodec::decode(&bytes).expect_err("invalid min/max hello fixture should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_empty_token_client_hello_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-HELLO-EMPTYTOKEN-003.json");
    let error = FrameCodec::decode(&bytes).expect_err("empty-token hello fixture should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_non_canonical_varint_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-PING-NONCANONVARINT-004.json");
    let error = FrameCodec::decode(&bytes).expect_err("non-canonical varint fixture should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_unknown_carrier_kind_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-HELLO-BADCARRIER-005.json");
    let error = FrameCodec::decode(&bytes).expect_err("unknown carrier-kind fixture should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn decodes_and_reencodes_valid_udp_flow_open_fixture() {
    let bytes = decode_hex_fixture("wire/v1/valid/NS-FX-UDP-OPEN-001.json");
    let frame = FrameCodec::decode(&bytes).expect("valid udp-flow-open fixture should decode");

    match &frame {
        Frame::UdpFlowOpen(open) => {
            assert_eq!(open.flow_id, 7);
            assert_eq!(open.target_port, 53);
            assert!(open.flags.prefer_datagram());
            assert!(open.flags.allow_stream_fallback());
        }
        other => panic!("expected udp-flow-open frame, got {other:?}"),
    }

    let reencoded = FrameCodec::encode(&frame).expect("decoded udp-flow-open should re-encode");
    assert_eq!(reencoded, bytes);
}

#[test]
fn decodes_and_reencodes_valid_udp_flow_ok_fixture() {
    let bytes = decode_hex_fixture("wire/v1/valid/NS-FX-UDP-OK-001.json");
    let frame = FrameCodec::decode(&bytes).expect("valid udp-flow-ok fixture should decode");

    match &frame {
        Frame::UdpFlowOk(ok) => {
            assert_eq!(ok.flow_id, 7);
            assert_eq!(ok.transport_mode.id(), 1);
            assert_eq!(ok.effective_idle_timeout_ms, 15_000);
            assert_eq!(ok.effective_max_payload, 1_200);
        }
        other => panic!("expected udp-flow-ok frame, got {other:?}"),
    }

    let reencoded = FrameCodec::encode(&frame).expect("decoded udp-flow-ok should re-encode");
    assert_eq!(reencoded, bytes);
}

#[test]
fn decodes_and_reencodes_valid_udp_flow_ok_stream_fallback_fixture() {
    let bytes = decode_hex_fixture("wire/v1/valid/NS-FX-UDP-OK-FALLBACK-002.json");
    let frame =
        FrameCodec::decode(&bytes).expect("valid fallback udp-flow-ok fixture should decode");

    match &frame {
        Frame::UdpFlowOk(ok) => {
            assert_eq!(ok.flow_id, 7);
            assert_eq!(ok.transport_mode.id(), 2);
            assert_eq!(ok.effective_idle_timeout_ms, 15_000);
            assert_eq!(ok.effective_max_payload, 1_200);
        }
        other => panic!("expected udp-flow-ok frame, got {other:?}"),
    }

    let reencoded = FrameCodec::encode(&frame).expect("decoded udp-flow-ok should re-encode");
    assert_eq!(reencoded, bytes);
}

#[test]
fn decodes_and_reencodes_valid_udp_datagram_fixture() {
    let bytes = decode_hex_fixture("wire/v1/valid/NS-FX-UDP-DGRAM-001.json");
    let datagram = decode_udp_datagram(&bytes).expect("valid udp datagram fixture should decode");

    assert_eq!(datagram.flow_id, 7);
    assert_eq!(datagram.flags.raw(), 0);
    assert_eq!(datagram.payload, b"dns-query");

    let reencoded = encode_udp_datagram(&datagram).expect("decoded udp datagram should re-encode");
    assert_eq!(reencoded, bytes);
}

#[test]
fn decodes_and_reencodes_valid_udp_datagram_at_mtu_fixture() {
    let bytes = decode_hex_fixture("wire/v1/valid/NS-FX-UDP-DGRAM-MTU-002.json");
    let datagram =
        decode_udp_datagram(&bytes).expect("valid MTU udp datagram fixture should decode");

    assert_eq!(datagram.flow_id, 7);
    assert_eq!(datagram.flags.raw(), 0);
    assert_eq!(datagram.payload.len(), 1_200);
    assert!(datagram.payload.iter().all(|byte| *byte == b'x'));

    let reencoded =
        encode_udp_datagram(&datagram).expect("decoded MTU udp datagram should re-encode");
    assert_eq!(reencoded, bytes);
}

#[test]
fn decodes_and_reencodes_valid_udp_flow_close_fixture() {
    let bytes = decode_hex_fixture("wire/v1/valid/NS-FX-UDP-FLOW-CLOSE-001.json");
    let frame = FrameCodec::decode(&bytes).expect("valid udp-flow-close fixture should decode");

    match &frame {
        Frame::UdpFlowClose(close) => {
            assert_eq!(close.flow_id, 7);
            assert_eq!(close.code.id(), 0);
            assert_eq!(close.message, "done");
        }
        other => panic!("expected udp-flow-close frame, got {other:?}"),
    }

    let reencoded = FrameCodec::encode(&frame).expect("decoded udp-flow-close should re-encode");
    assert_eq!(reencoded, bytes);
}

#[test]
fn decodes_and_reencodes_valid_udp_flow_close_rejection_fixture() {
    let bytes = decode_hex_fixture("wire/v1/valid/NS-FX-UDP-FLOW-CLOSE-DGRAMUNAVAIL-002.json");
    let frame =
        FrameCodec::decode(&bytes).expect("valid rejection udp-flow-close fixture should decode");

    match &frame {
        Frame::UdpFlowClose(close) => {
            assert_eq!(close.flow_id, 7);
            assert_eq!(close.code.id(), 20);
            assert_eq!(
                close.message,
                "udp datagram mode was unavailable and stream fallback was not allowed"
            );
        }
        other => panic!("expected udp-flow-close frame, got {other:?}"),
    }

    let reencoded = FrameCodec::encode(&frame).expect("decoded udp-flow-close should re-encode");
    assert_eq!(reencoded, bytes);
}

#[test]
fn decodes_and_reencodes_valid_udp_flow_close_protocol_violation_fixture() {
    let bytes = decode_hex_fixture("wire/v1/valid/NS-FX-UDP-FLOW-CLOSE-PROTOVIOL-003.json");
    let frame = FrameCodec::decode(&bytes)
        .expect("valid protocol-violation udp-flow-close fixture should decode");

    match &frame {
        Frame::UdpFlowClose(close) => {
            assert_eq!(close.flow_id, 7);
            assert_eq!(close.code.id(), 1);
            assert_eq!(close.message, "udp flow id 7 is not active");
        }
        other => panic!("expected udp-flow-close frame, got {other:?}"),
    }

    let reencoded = FrameCodec::encode(&frame).expect("decoded udp-flow-close should re-encode");
    assert_eq!(reencoded, bytes);
}

#[test]
fn decodes_and_reencodes_valid_udp_fallback_frames() {
    let open_bytes = decode_hex_fixture("wire/v1/valid/NS-FX-UDP-STREAM-OPEN-001.json");
    let open =
        FrameCodec::decode(&open_bytes).expect("valid udp-stream-open fixture should decode");
    match &open {
        Frame::UdpStreamOpen(frame) => assert_eq!(frame.flow_id, 7),
        other => panic!("expected udp-stream-open frame, got {other:?}"),
    }
    assert_eq!(
        FrameCodec::encode(&open).expect("decoded udp-stream-open should re-encode"),
        open_bytes
    );

    let accept_bytes = decode_hex_fixture("wire/v1/valid/NS-FX-UDP-STREAM-ACCEPT-001.json");
    let accept =
        FrameCodec::decode(&accept_bytes).expect("valid udp-stream-accept fixture should decode");
    match &accept {
        Frame::UdpStreamAccept(frame) => assert_eq!(frame.flow_id, 7),
        other => panic!("expected udp-stream-accept frame, got {other:?}"),
    }
    assert_eq!(
        FrameCodec::encode(&accept).expect("decoded udp-stream-accept should re-encode"),
        accept_bytes
    );

    let packet_bytes = decode_hex_fixture("wire/v1/valid/NS-FX-UDP-STREAM-PACKET-001.json");
    let packet =
        FrameCodec::decode(&packet_bytes).expect("valid udp-stream-packet fixture should decode");
    match &packet {
        Frame::UdpStreamPacket(frame) => assert_eq!(frame.payload, b"dns-fallback"),
        other => panic!("expected udp-stream-packet frame, got {other:?}"),
    }
    assert_eq!(
        FrameCodec::encode(&packet).expect("decoded udp-stream-packet should re-encode"),
        packet_bytes
    );

    let close_bytes = decode_hex_fixture("wire/v1/valid/NS-FX-UDP-STREAM-CLOSE-001.json");
    let close =
        FrameCodec::decode(&close_bytes).expect("valid udp-stream-close fixture should decode");
    match &close {
        Frame::UdpStreamClose(frame) => {
            assert_eq!(frame.flow_id, 7);
            assert_eq!(frame.code.id(), 0);
            assert_eq!(frame.message, "done");
        }
        other => panic!("expected udp-stream-close frame, got {other:?}"),
    }
    assert_eq!(
        FrameCodec::encode(&close).expect("decoded udp-stream-close should re-encode"),
        close_bytes
    );

    let idle_close_bytes = decode_hex_fixture("wire/v1/valid/NS-FX-UDP-STREAM-CLOSE-IDLE-002.json");
    let idle_close = FrameCodec::decode(&idle_close_bytes)
        .expect("valid idle udp-stream-close fixture should decode");
    match &idle_close {
        Frame::UdpStreamClose(frame) => {
            assert_eq!(frame.flow_id, 7);
            assert_eq!(frame.code.id(), 13);
            assert_eq!(frame.message, "idle timeout");
        }
        other => panic!("expected udp-stream-close frame, got {other:?}"),
    }
    assert_eq!(
        FrameCodec::encode(&idle_close).expect("decoded idle udp-stream-close should re-encode"),
        idle_close_bytes
    );
}

#[test]
fn rejects_reserved_udp_flow_flags_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OPEN-RESERVEDFLAGS-007.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("reserved udp flow flags fixture should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_truncated_udp_flow_open_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OPEN-TRUNCATED-020.json");
    let error = FrameCodec::decode(&bytes).expect_err("truncated udp flow open should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_flow_open_flow_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OPEN-NONCANONFLOW-034.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("non-canonical udp flow open flow id should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_flow_open_flags_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OPEN-NONCANONFLAGS-035.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("non-canonical udp flow open flags should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_flow_open_timeout_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OPEN-NONCANONTIMEOUT-036.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("non-canonical udp flow open timeout should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_udp_flow_open_ipv4_length_mismatch_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OPEN-IPV4LEN-038.json");
    let error = FrameCodec::decode(&bytes).expect_err("udp flow open ipv4 length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_udp_flow_open_bad_target_type_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OPEN-BADTARGETTYPE-039.json");
    let error = FrameCodec::decode(&bytes).expect_err("udp flow open target type should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_flow_open_target_type_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OPEN-NONCANONTARGETTYPE-043.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("non-canonical udp flow open target type should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_flow_open_port_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OPEN-NONCANONPORT-044.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("non-canonical udp flow open port should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_udp_flow_open_ipv6_length_mismatch_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OPEN-IPV6LEN-040.json");
    let error = FrameCodec::decode(&bytes).expect_err("udp flow open ipv6 length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_udp_flow_open_empty_domain_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OPEN-EMPTYDOMAIN-041.json");
    let error = FrameCodec::decode(&bytes).expect_err("udp flow open empty domain should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_udp_flow_open_zero_port_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OPEN-ZEROPORT-047.json");
    let error = FrameCodec::decode(&bytes).expect_err("udp flow open zero port should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_udp_flow_open_bad_utf8_domain_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OPEN-BADUTF8DOMAIN-048.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("udp flow open invalid utf8 domain should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_udp_flow_open_bad_metadata_count_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OPEN-BADMETACOUNT-056.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("udp flow open bad metadata count should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_flow_open_metadata_count_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OPEN-NONCANONMETACOUNT-057.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("non-canonical udp flow open metadata count should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_udp_flow_open_bad_metadata_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OPEN-BADMETALEN-065.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("udp flow open bad metadata length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_flow_open_metadata_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OPEN-NONCANONMETALEN-061.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("non-canonical udp flow open metadata length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_flow_open_metadata_type_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OPEN-NONCANONMETATYPE-069.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("non-canonical udp flow open metadata type should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_flow_open_frame_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OPEN-NONCANONFRAMELEN-073.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("non-canonical udp flow open frame length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_reserved_udp_datagram_flags_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-DGRAM-RESERVEDFLAGS-008.json");
    let error =
        decode_udp_datagram(&bytes).expect_err("reserved udp datagram flags fixture should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_datagram_flow_id_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-DGRAM-NONCANONFLOW-021.json");
    let error =
        decode_udp_datagram(&bytes).expect_err("non-canonical udp datagram flow id should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_datagram_flags_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-DGRAM-NONCANONFLAGS-027.json");
    let error =
        decode_udp_datagram(&bytes).expect_err("non-canonical udp datagram flags should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_truncated_udp_datagram_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-DGRAM-TRUNCATED-015.json");
    let error =
        decode_udp_datagram(&bytes).expect_err("truncated udp datagram fixture should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_unknown_udp_transport_mode_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OK-BADMODE-009.json");
    let error = FrameCodec::decode(&bytes).expect_err("unknown udp transport mode should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_flow_ok_flow_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OK-NONCANONFLOW-030.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("non-canonical udp-flow-ok flow id should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_truncated_udp_flow_ok_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OK-TRUNCATED-018.json");
    let error = FrameCodec::decode(&bytes).expect_err("truncated udp-flow-ok should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_flow_ok_payload_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OK-NONCANONPAYLOAD-029.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("non-canonical udp-flow-ok payload should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_flow_ok_timeout_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OK-NONCANONTIMEOUT-037.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("non-canonical udp-flow-ok timeout should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_flow_ok_mode_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OK-NONCANONMODE-042.json");
    let error = FrameCodec::decode(&bytes).expect_err("non-canonical udp-flow-ok mode should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_udp_flow_ok_zero_max_payload_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OK-ZEROMAXPAYLOAD-049.json");
    let error = FrameCodec::decode(&bytes).expect_err("udp-flow-ok zero max payload should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_udp_flow_ok_zero_idle_timeout_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OK-ZEROIDLETIMEOUT-051.json");
    let error = FrameCodec::decode(&bytes).expect_err("udp-flow-ok zero idle timeout should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_udp_flow_ok_bad_metadata_count_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OK-BADMETACOUNT-055.json");
    let error = FrameCodec::decode(&bytes).expect_err("udp-flow-ok bad metadata count should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_flow_ok_metadata_count_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OK-NONCANONMETACOUNT-058.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("non-canonical udp-flow-ok metadata count should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_udp_flow_ok_bad_metadata_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OK-BADMETALEN-066.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("udp-flow-ok bad metadata length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_flow_ok_metadata_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OK-NONCANONMETALEN-062.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("non-canonical udp-flow-ok metadata length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_flow_ok_metadata_type_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OK-NONCANONMETATYPE-070.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("non-canonical udp-flow-ok metadata type should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_flow_ok_frame_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OK-NONCANONFRAMELEN-074.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("non-canonical udp-flow-ok frame length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_malformed_udp_stream_packet_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-PACKET-LEN-010.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("malformed udp-stream-packet fixture should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_stream_packet_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-PACKET-NONCANONLEN-031.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("non-canonical udp-stream-packet declared length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_stream_packet_frame_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-PACKET-NONCANONFRAMELEN-079.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("non-canonical udp-stream-packet frame length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_bad_udp_stream_packet_frame_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-PACKET-BADFRAMELEN-080.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("mismatched udp-stream-packet frame length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_bad_udp_stream_open_frame_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-OPEN-BADFRAMELEN-081.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("mismatched udp-stream-open frame length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_bad_udp_stream_accept_frame_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-ACCEPT-BADFRAMELEN-082.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("mismatched udp-stream-accept frame length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_bad_udp_ok_frame_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OK-BADFRAMELEN-085.json");
    let error = FrameCodec::decode(&bytes).expect_err("mismatched udp-ok frame length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_bad_udp_open_frame_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-OPEN-BADFRAMELEN-086.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("mismatched udp-open frame length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_bad_udp_flow_close_dgramunavail_frame_length_fixture() {
    let (bytes, expected_error) = decode_invalid_fixture(
        "wire/v1/invalid/WC-UDP-FLOW-CLOSE-DGRAMUNAVAIL-BADFRAMELEN-087.json",
    );
    let error = FrameCodec::decode(&bytes)
        .expect_err("mismatched udp-flow-close-dgramunavail frame length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_bad_udp_stream_close_frame_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-CLOSE-BADFRAMELEN-083.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("mismatched udp-stream-close frame length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_unknown_udp_stream_close_error_code_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-CLOSE-BADCODE-011.json");
    let error = FrameCodec::decode(&bytes).expect_err("unknown udp-stream-close code should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_extended_unknown_udp_stream_close_error_code_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-CLOSE-BADCODE-022.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("extended unknown udp-stream-close code should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_stream_close_error_code_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-CLOSE-NONCANONCODE-028.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("non-canonical udp-stream-close code should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_stream_close_flow_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-CLOSE-NONCANONFLOW-033.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("non-canonical udp-stream-close flow id should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_stream_close_message_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-CLOSE-NONCANONMSGLEN-046.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("non-canonical udp-stream-close message length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_stream_close_frame_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-CLOSE-NONCANONFRAMELEN-078.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("non-canonical udp-stream-close frame length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_udp_stream_close_bad_utf8_message_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-CLOSE-BADUTF8-050.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("udp-stream-close invalid utf8 message should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_unknown_udp_flow_close_error_code_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-FLOW-CLOSE-BADCODE-012.json");
    let error = FrameCodec::decode(&bytes).expect_err("unknown udp-flow-close code should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_flow_close_error_code_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-FLOW-CLOSE-NONCANONCODE-024.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("non-canonical udp-flow-close code should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_flow_close_flow_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-FLOW-CLOSE-NONCANONFLOW-032.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("non-canonical udp-flow-close flow id should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_flow_close_message_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-FLOW-CLOSE-NONCANONMSGLEN-045.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("non-canonical udp-flow-close message length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_flow_close_frame_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-FLOW-CLOSE-NONCANONFRAMELEN-077.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("non-canonical udp-flow-close frame length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_bad_udp_flow_close_frame_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-FLOW-CLOSE-BADFRAMELEN-084.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("mismatched udp-flow-close frame length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_truncated_udp_flow_close_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-FLOW-CLOSE-TRUNCATED-016.json");
    let error = FrameCodec::decode(&bytes).expect_err("truncated udp-flow-close should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_udp_flow_close_bad_utf8_message_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-FLOW-CLOSE-BADUTF8-052.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("udp-flow-close invalid utf8 message should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_truncated_udp_stream_open_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-OPEN-TRUNCATED-013.json");
    let error = FrameCodec::decode(&bytes).expect_err("truncated udp-stream-open should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_stream_open_flow_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-OPEN-NONCANONFLOW-025.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("non-canonical udp-stream-open flow id should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_udp_stream_open_bad_metadata_count_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-OPEN-BADMETACOUNT-053.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("udp-stream-open bad metadata count should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_stream_open_metadata_count_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-OPEN-NONCANONMETACOUNT-059.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("non-canonical udp-stream-open metadata count should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_udp_stream_open_bad_metadata_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-OPEN-BADMETALEN-067.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("udp-stream-open bad metadata length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_stream_open_metadata_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-OPEN-NONCANONMETALEN-063.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("non-canonical udp-stream-open metadata length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_stream_open_metadata_type_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-OPEN-NONCANONMETATYPE-071.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("non-canonical udp-stream-open metadata type should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_stream_open_frame_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-OPEN-NONCANONFRAMELEN-075.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("non-canonical udp-stream-open frame length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_truncated_udp_stream_accept_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-ACCEPT-TRUNCATED-019.json");
    let error = FrameCodec::decode(&bytes).expect_err("truncated udp-stream-accept should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_stream_accept_flow_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-ACCEPT-NONCANONFLOW-026.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("non-canonical udp-stream-accept flow id should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_udp_stream_accept_bad_metadata_count_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-ACCEPT-BADMETACOUNT-054.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("udp-stream-accept bad metadata count should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_stream_accept_metadata_count_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-ACCEPT-NONCANONMETACOUNT-060.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("non-canonical udp-stream-accept metadata count should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_udp_stream_accept_bad_metadata_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-ACCEPT-BADMETALEN-068.json");
    let error =
        FrameCodec::decode(&bytes).expect_err("udp-stream-accept bad metadata length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_stream_accept_metadata_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-ACCEPT-NONCANONMETALEN-064.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("non-canonical udp-stream-accept metadata length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_stream_accept_metadata_type_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-ACCEPT-NONCANONMETATYPE-072.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("non-canonical udp-stream-accept metadata type should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_noncanonical_udp_stream_accept_frame_length_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-ACCEPT-NONCANONFRAMELEN-076.json");
    let error = FrameCodec::decode(&bytes)
        .expect_err("non-canonical udp-stream-accept frame length should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_truncated_udp_stream_packet_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-PACKET-TRUNCATED-014.json");
    let error = FrameCodec::decode(&bytes).expect_err("truncated udp-stream-packet should fail");
    assert_eq!(error_kind(&error), expected_error);
}

#[test]
fn rejects_truncated_udp_stream_close_fixture() {
    let (bytes, expected_error) =
        decode_invalid_fixture("wire/v1/invalid/WC-UDP-STREAM-CLOSE-TRUNCATED-017.json");
    let error = FrameCodec::decode(&bytes).expect_err("truncated udp-stream-close should fail");
    assert_eq!(error_kind(&error), expected_error);
}
