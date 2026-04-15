use base64::Engine as _;
use ed25519_dalek::Signer;
use ed25519_dalek::SigningKey;
use ed25519_dalek::pkcs8::EncodePrivateKey;
use jsonwebtoken::jwk::{
    AlgorithmParameters, CommonParameters, Jwk, JwkSet, OctetKeyPairParameters, OctetKeyPairType,
};
use ns_auth::{MintedTokenRequest, SessionTokenSigner};
use ns_core::TransportMode;
use ns_core::{
    Capability, CarrierKind, CarrierProfileId, DeviceBindingId, MAX_METADATA_TLVS, ManifestId,
};
use ns_manifest::ManifestDocument;
use ns_testkit::{repo_root, sample_client_hello, sample_manifest_document};
use ns_wire::{
    DatagramFlags, FlowFlags, Frame, FrameCodec, Ping, TargetAddress, UdpDatagram, UdpFlowClose,
    UdpFlowOk, UdpFlowOpen, UdpStreamAccept, UdpStreamClose, UdpStreamOpen, UdpStreamPacket,
    decode_udp_datagram, encode_udp_datagram, encode_varint,
};
use serde_json::json;
use std::fs;
use std::path::Path;
use time::{Duration, OffsetDateTime};

const MANIFEST_KID: &str = "fixture-manifest-key-1";
const TOKEN_KID: &str = "fixture-token-key-1";

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let root = repo_root();
    let now = OffsetDateTime::parse(
        "2026-04-01T00:10:00Z",
        &time::format_description::well_known::Rfc3339,
    )?;

    write_wire_fixtures(&root)?;
    write_manifest_fixtures(&root, now)?;
    write_token_fixtures(&root, now)?;
    write_bridge_and_webhook_fixtures(&root)?;

    Ok(())
}

fn write_wire_fixtures(root: &Path) -> Result<(), Box<dyn std::error::Error>> {
    let ping = Frame::Ping(Ping {
        ping_id: 1,
        timestamp: 2,
    });
    let ping_bytes = FrameCodec::encode(&ping)?;
    write_json(
        &root.join("fixtures/wire/v1/valid/NS-FX-PING-001.json"),
        &json!({
            "case_id": "NS-FX-PING-001",
            "suite": "WC",
            "frame_type": "Ping",
            "hex": to_hex(&ping_bytes),
            "expected": {
                "ping_id": 1,
                "timestamp": 2
            }
        }),
    )?;

    let hello = Frame::ClientHello(sample_client_hello("fixture-session-token".to_owned()));
    let hello_bytes = FrameCodec::encode(&hello)?;
    write_json(
        &root.join("fixtures/wire/v1/valid/NS-FX-HELLO-001.json"),
        &json!({
            "case_id": "NS-FX-HELLO-001",
            "suite": "WC",
            "frame_type": "ClientHello",
            "hex": to_hex(&hello_bytes),
            "expected": {
                "manifest_id": "man-2026-04-01-001",
                "device_binding_id": "device-1",
                "carrier_profile_id": "carrier-primary",
                "requested_capabilities": ["TcpRelay", "UdpRelay"]
            }
        }),
    )?;

    let mut no_overlap_hello = sample_client_hello("fixture-session-token".to_owned());
    no_overlap_hello.min_version = 2;
    no_overlap_hello.max_version = 2;
    let no_overlap_bytes = FrameCodec::encode(&Frame::ClientHello(no_overlap_hello))?;
    write_json(
        &root.join("fixtures/wire/v1/valid/NS-FX-HELLO-NOOVERLAP-002.json"),
        &json!({
            "case_id": "NS-FX-HELLO-NOOVERLAP-002",
            "suite": "WC",
            "frame_type": "ClientHello",
            "hex": to_hex(&no_overlap_bytes),
            "expected": {
                "manifest_id": "man-2026-04-01-001",
                "device_binding_id": "device-1",
                "carrier_profile_id": "carrier-primary",
                "min_version": 2,
                "max_version": 2
            }
        }),
    )?;

    let mut truncated = hello_bytes.clone();
    truncated.pop();
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-HELLO-TRUNCATED-001.json"),
        &json!({
            "case_id": "WC-HELLO-TRUNCATED-001",
            "suite": "WC",
            "hex": to_hex(&truncated),
            "expected_error": "LengthMismatch"
        }),
    )?;

    let invalid_minmax = raw_client_hello_frame(2, 1, CarrierKind::H3.id())?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-HELLO-MINMAX-002.json"),
        &json!({
            "case_id": "WC-HELLO-MINMAX-002",
            "suite": "WC",
            "hex": to_hex(&invalid_minmax),
            "expected_error": "Validation"
        }),
    )?;

    let empty_token = Frame::ClientHello(sample_client_hello(String::new()));
    let empty_token_bytes = FrameCodec::encode(&empty_token)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-HELLO-EMPTYTOKEN-003.json"),
        &json!({
            "case_id": "WC-HELLO-EMPTYTOKEN-003",
            "suite": "WC",
            "hex": to_hex(&empty_token_bytes),
            "expected_error": "Validation"
        }),
    )?;

    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-PING-NONCANONVARINT-004.json"),
        &json!({
            "case_id": "WC-PING-NONCANONVARINT-004",
            "suite": "WC",
            "hex": "0303400102",
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let bad_carrier = raw_client_hello_frame(1, 1, 99)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-HELLO-BADCARRIER-005.json"),
        &json!({
            "case_id": "WC-HELLO-BADCARRIER-005",
            "suite": "WC",
            "hex": to_hex(&bad_carrier),
            "expected_error": "Validation"
        }),
    )?;

    let udp_open = Frame::UdpFlowOpen(UdpFlowOpen {
        flow_id: 7,
        target: TargetAddress::Domain("dns.example.net".to_owned()),
        target_port: 53,
        idle_timeout_ms: 15_000,
        flags: FlowFlags::new(0b0011).expect("fixture udp flow flags should be valid"),
        metadata: Vec::new(),
    });
    let udp_open_bytes = FrameCodec::encode(&udp_open)?;
    write_json(
        &root.join("fixtures/wire/v1/valid/NS-FX-UDP-OPEN-001.json"),
        &json!({
            "case_id": "NS-FX-UDP-OPEN-001",
            "suite": "WC",
            "frame_type": "UdpFlowOpen",
            "hex": to_hex(&udp_open_bytes),
            "expected": {
                "flow_id": 7,
                "target": "dns.example.net",
                "target_port": 53,
                "idle_timeout_ms": 15000,
                "flags": 3
            }
        }),
    )?;

    let udp_ok = Frame::UdpFlowOk(UdpFlowOk {
        flow_id: 7,
        transport_mode: TransportMode::Datagram,
        effective_idle_timeout_ms: 15_000,
        effective_max_payload: 1_200,
        metadata: Vec::new(),
    });
    let udp_ok_bytes = FrameCodec::encode(&udp_ok)?;
    write_json(
        &root.join("fixtures/wire/v1/valid/NS-FX-UDP-OK-001.json"),
        &json!({
            "case_id": "NS-FX-UDP-OK-001",
            "suite": "WC",
            "frame_type": "UdpFlowOk",
            "hex": to_hex(&udp_ok_bytes),
            "expected": {
                "flow_id": 7,
                "transport_mode": "datagram",
                "effective_idle_timeout_ms": 15000,
                "effective_max_payload": 1200
            }
        }),
    )?;

    let udp_ok_fallback = Frame::UdpFlowOk(UdpFlowOk {
        flow_id: 7,
        transport_mode: TransportMode::StreamFallback,
        effective_idle_timeout_ms: 15_000,
        effective_max_payload: 1_200,
        metadata: Vec::new(),
    });
    let udp_ok_fallback_bytes = FrameCodec::encode(&udp_ok_fallback)?;
    write_json(
        &root.join("fixtures/wire/v1/valid/NS-FX-UDP-OK-FALLBACK-002.json"),
        &json!({
            "case_id": "NS-FX-UDP-OK-FALLBACK-002",
            "suite": "WC",
            "frame_type": "UdpFlowOk",
            "hex": to_hex(&udp_ok_fallback_bytes),
            "expected": {
                "flow_id": 7,
                "transport_mode": "stream_fallback",
                "effective_idle_timeout_ms": 15000,
                "effective_max_payload": 1200
            }
        }),
    )?;

    let udp_flow_close = Frame::UdpFlowClose(UdpFlowClose {
        flow_id: 7,
        code: ns_core::ProtocolErrorCode::NoError,
        message: "done".to_owned(),
    });
    let udp_flow_close_bytes = FrameCodec::encode(&udp_flow_close)?;
    write_json(
        &root.join("fixtures/wire/v1/valid/NS-FX-UDP-FLOW-CLOSE-001.json"),
        &json!({
            "case_id": "NS-FX-UDP-FLOW-CLOSE-001",
            "suite": "WC",
            "frame_type": "UdpFlowClose",
            "hex": to_hex(&udp_flow_close_bytes),
            "expected": {
                "flow_id": 7,
                "code": "NoError",
                "message": "done"
            }
        }),
    )?;

    let udp_flow_close_datagram_unavailable = Frame::UdpFlowClose(UdpFlowClose {
        flow_id: 7,
        code: ns_core::ProtocolErrorCode::UdpDatagramUnavailable,
        message: "udp datagram mode was unavailable and stream fallback was not allowed".to_owned(),
    });
    let udp_flow_close_datagram_unavailable_bytes =
        FrameCodec::encode(&udp_flow_close_datagram_unavailable)?;
    write_json(
        &root.join("fixtures/wire/v1/valid/NS-FX-UDP-FLOW-CLOSE-DGRAMUNAVAIL-002.json"),
        &json!({
            "case_id": "NS-FX-UDP-FLOW-CLOSE-DGRAMUNAVAIL-002",
            "suite": "WC",
            "frame_type": "UdpFlowClose",
            "hex": to_hex(&udp_flow_close_datagram_unavailable_bytes),
            "expected": {
                "flow_id": 7,
                "code": "UdpDatagramUnavailable",
                "message": "udp datagram mode was unavailable and stream fallback was not allowed"
            }
        }),
    )?;

    let udp_flow_close_protocol_violation = Frame::UdpFlowClose(UdpFlowClose {
        flow_id: 7,
        code: ns_core::ProtocolErrorCode::ProtocolViolation,
        message: "udp flow id 7 is not active".to_owned(),
    });
    let udp_flow_close_protocol_violation_bytes =
        FrameCodec::encode(&udp_flow_close_protocol_violation)?;
    write_json(
        &root.join("fixtures/wire/v1/valid/NS-FX-UDP-FLOW-CLOSE-PROTOVIOL-003.json"),
        &json!({
            "case_id": "NS-FX-UDP-FLOW-CLOSE-PROTOVIOL-003",
            "suite": "WC",
            "frame_type": "UdpFlowClose",
            "hex": to_hex(&udp_flow_close_protocol_violation_bytes),
            "expected": {
                "flow_id": 7,
                "code": "ProtocolViolation",
                "message": "udp flow id 7 is not active"
            }
        }),
    )?;

    let udp_stream_open = Frame::UdpStreamOpen(UdpStreamOpen {
        flow_id: 7,
        metadata: Vec::new(),
    });
    let udp_stream_open_bytes = FrameCodec::encode(&udp_stream_open)?;
    write_json(
        &root.join("fixtures/wire/v1/valid/NS-FX-UDP-STREAM-OPEN-001.json"),
        &json!({
            "case_id": "NS-FX-UDP-STREAM-OPEN-001",
            "suite": "WC",
            "frame_type": "UdpStreamOpen",
            "hex": to_hex(&udp_stream_open_bytes),
            "expected": {
                "flow_id": 7
            }
        }),
    )?;

    let udp_stream_accept = Frame::UdpStreamAccept(UdpStreamAccept {
        flow_id: 7,
        metadata: Vec::new(),
    });
    let udp_stream_accept_bytes = FrameCodec::encode(&udp_stream_accept)?;
    write_json(
        &root.join("fixtures/wire/v1/valid/NS-FX-UDP-STREAM-ACCEPT-001.json"),
        &json!({
            "case_id": "NS-FX-UDP-STREAM-ACCEPT-001",
            "suite": "WC",
            "frame_type": "UdpStreamAccept",
            "hex": to_hex(&udp_stream_accept_bytes),
            "expected": {
                "flow_id": 7
            }
        }),
    )?;

    let udp_stream_packet = Frame::UdpStreamPacket(UdpStreamPacket {
        payload: b"dns-fallback".to_vec(),
    });
    let udp_stream_packet_bytes = FrameCodec::encode(&udp_stream_packet)?;
    write_json(
        &root.join("fixtures/wire/v1/valid/NS-FX-UDP-STREAM-PACKET-001.json"),
        &json!({
            "case_id": "NS-FX-UDP-STREAM-PACKET-001",
            "suite": "WC",
            "frame_type": "UdpStreamPacket",
            "hex": to_hex(&udp_stream_packet_bytes),
            "expected": {
                "payload_utf8": "dns-fallback"
            }
        }),
    )?;

    let udp_stream_close = Frame::UdpStreamClose(UdpStreamClose {
        flow_id: 7,
        code: ns_core::ProtocolErrorCode::NoError,
        message: "done".to_owned(),
    });
    let udp_stream_close_bytes = FrameCodec::encode(&udp_stream_close)?;
    write_json(
        &root.join("fixtures/wire/v1/valid/NS-FX-UDP-STREAM-CLOSE-001.json"),
        &json!({
            "case_id": "NS-FX-UDP-STREAM-CLOSE-001",
            "suite": "WC",
            "frame_type": "UdpStreamClose",
            "hex": to_hex(&udp_stream_close_bytes),
            "expected": {
                "flow_id": 7,
                "code": "NoError",
                "message": "done"
            }
        }),
    )?;

    let udp_stream_close_idle = Frame::UdpStreamClose(UdpStreamClose {
        flow_id: 7,
        code: ns_core::ProtocolErrorCode::IdleTimeout,
        message: "idle timeout".to_owned(),
    });
    let udp_stream_close_idle_bytes = FrameCodec::encode(&udp_stream_close_idle)?;
    write_json(
        &root.join("fixtures/wire/v1/valid/NS-FX-UDP-STREAM-CLOSE-IDLE-002.json"),
        &json!({
            "case_id": "NS-FX-UDP-STREAM-CLOSE-IDLE-002",
            "suite": "WC",
            "frame_type": "UdpStreamClose",
            "hex": to_hex(&udp_stream_close_idle_bytes),
            "expected": {
                "flow_id": 7,
                "code": "IdleTimeout",
                "message": "idle timeout"
            }
        }),
    )?;

    let udp_datagram = UdpDatagram {
        flow_id: 7,
        flags: DatagramFlags::new(0).expect("fixture datagram flags should be valid"),
        payload: b"dns-query".to_vec(),
    };
    let udp_datagram_bytes = encode_udp_datagram(&udp_datagram)?;
    let decoded_datagram = decode_udp_datagram(&udp_datagram_bytes)?;
    write_json(
        &root.join("fixtures/wire/v1/valid/NS-FX-UDP-DGRAM-001.json"),
        &json!({
            "case_id": "NS-FX-UDP-DGRAM-001",
            "suite": "WC",
            "frame_type": "UdpDatagram",
            "hex": to_hex(&udp_datagram_bytes),
            "expected": {
                "flow_id": decoded_datagram.flow_id,
                "flags": decoded_datagram.flags.raw(),
                "payload_utf8": String::from_utf8(decoded_datagram.payload)?,
            }
        }),
    )?;

    let mtu_payload = vec![b'x'; 1_200];
    let mtu_datagram = UdpDatagram {
        flow_id: 7,
        flags: DatagramFlags::new(0).expect("fixture datagram flags should be valid"),
        payload: mtu_payload.clone(),
    };
    let mtu_datagram_bytes = encode_udp_datagram(&mtu_datagram)?;
    write_json(
        &root.join("fixtures/wire/v1/valid/NS-FX-UDP-DGRAM-MTU-002.json"),
        &json!({
            "case_id": "NS-FX-UDP-DGRAM-MTU-002",
            "suite": "WC",
            "frame_type": "UdpDatagram",
            "hex": to_hex(&mtu_datagram_bytes),
            "expected": {
                "flow_id": 7,
                "flags": 0,
                "payload_len": mtu_payload.len(),
            }
        }),
    )?;

    let bad_udp_open = raw_udp_flow_open_frame(1 << 4)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OPEN-RESERVEDFLAGS-007.json"),
        &json!({
            "case_id": "WC-UDP-OPEN-RESERVEDFLAGS-007",
            "suite": "WC",
            "hex": to_hex(&bad_udp_open),
            "expected_error": "Validation"
        }),
    )?;

    let bad_udp_datagram = raw_udp_datagram(7, 1, b"oversized")?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-DGRAM-RESERVEDFLAGS-008.json"),
        &json!({
            "case_id": "WC-UDP-DGRAM-RESERVEDFLAGS-008",
            "suite": "WC",
            "hex": to_hex(&bad_udp_datagram),
            "expected_error": "Validation"
        }),
    )?;

    let truncated_udp_datagram = udp_datagram_bytes[..1].to_vec();
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-DGRAM-TRUNCATED-015.json"),
        &json!({
            "case_id": "WC-UDP-DGRAM-TRUNCATED-015",
            "suite": "WC",
            "hex": to_hex(&truncated_udp_datagram),
            "expected_error": "Truncated"
        }),
    )?;

    let bad_udp_ok = raw_udp_flow_ok_frame(7, 9, 15_000, 1_200)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OK-BADMODE-009.json"),
        &json!({
            "case_id": "WC-UDP-OK-BADMODE-009",
            "suite": "WC",
            "hex": to_hex(&bad_udp_ok),
            "expected_error": "Validation"
        }),
    )?;

    let truncated_udp_ok = udp_ok_bytes[..udp_ok_bytes.len() - 1].to_vec();
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OK-TRUNCATED-018.json"),
        &json!({
            "case_id": "WC-UDP-OK-TRUNCATED-018",
            "suite": "WC",
            "hex": to_hex(&truncated_udp_ok),
            "expected_error": "LengthMismatch"
        }),
    )?;

    let noncanonical_udp_ok_payload = raw_udp_flow_ok_noncanonical_payload_frame(7, 1, 15_000)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OK-NONCANONPAYLOAD-029.json"),
        &json!({
            "case_id": "WC-UDP-OK-NONCANONPAYLOAD-029",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_ok_payload),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let noncanonical_udp_ok_flow = raw_udp_flow_ok_noncanonical_flow_frame(1, 15_000, 1_200)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OK-NONCANONFLOW-030.json"),
        &json!({
            "case_id": "WC-UDP-OK-NONCANONFLOW-030",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_ok_flow),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let noncanonical_udp_ok_timeout = raw_udp_flow_ok_noncanonical_timeout_frame(7, 1, 1_200)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OK-NONCANONTIMEOUT-037.json"),
        &json!({
            "case_id": "WC-UDP-OK-NONCANONTIMEOUT-037",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_ok_timeout),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let noncanonical_udp_ok_mode = raw_udp_flow_ok_noncanonical_mode_frame(7, 15_000, 1_200)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OK-NONCANONMODE-042.json"),
        &json!({
            "case_id": "WC-UDP-OK-NONCANONMODE-042",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_ok_mode),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let invalid_udp_ok_zero_max_payload = raw_udp_flow_ok_frame(7, 1, 15_000, 0)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OK-ZEROMAXPAYLOAD-049.json"),
        &json!({
            "case_id": "WC-UDP-OK-ZEROMAXPAYLOAD-049",
            "suite": "WC",
            "hex": to_hex(&invalid_udp_ok_zero_max_payload),
            "expected_error": "Validation"
        }),
    )?;

    let invalid_udp_ok_zero_idle_timeout = raw_udp_flow_ok_frame(7, 1, 0, 1_200)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OK-ZEROIDLETIMEOUT-051.json"),
        &json!({
            "case_id": "WC-UDP-OK-ZEROIDLETIMEOUT-051",
            "suite": "WC",
            "hex": to_hex(&invalid_udp_ok_zero_idle_timeout),
            "expected_error": "Validation"
        }),
    )?;

    let invalid_udp_ok_bad_metadata_count =
        raw_udp_flow_ok_bad_metadata_count_frame(7, 1, 15_000, 1_200)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OK-BADMETACOUNT-055.json"),
        &json!({
            "case_id": "WC-UDP-OK-BADMETACOUNT-055",
            "suite": "WC",
            "hex": to_hex(&invalid_udp_ok_bad_metadata_count),
            "expected_error": "Validation"
        }),
    )?;

    let noncanonical_udp_ok_metadata_count =
        raw_udp_flow_ok_noncanonical_metadata_count_frame(7, 1, 15_000, 1_200)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OK-NONCANONMETACOUNT-058.json"),
        &json!({
            "case_id": "WC-UDP-OK-NONCANONMETACOUNT-058",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_ok_metadata_count),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let invalid_udp_ok_bad_metadata_len =
        raw_udp_flow_ok_bad_metadata_len_frame(7, 1, 15_000, 1_200)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OK-BADMETALEN-066.json"),
        &json!({
            "case_id": "WC-UDP-OK-BADMETALEN-066",
            "suite": "WC",
            "hex": to_hex(&invalid_udp_ok_bad_metadata_len),
            "expected_error": "Truncated"
        }),
    )?;

    let noncanonical_udp_ok_metadata_len =
        raw_udp_flow_ok_noncanonical_metadata_len_frame(7, 1, 15_000, 1_200)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OK-NONCANONMETALEN-062.json"),
        &json!({
            "case_id": "WC-UDP-OK-NONCANONMETALEN-062",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_ok_metadata_len),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let noncanonical_udp_ok_metadata_type =
        raw_udp_flow_ok_noncanonical_metadata_type_frame(7, 1, 15_000, 1_200)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OK-NONCANONMETATYPE-070.json"),
        &json!({
            "case_id": "WC-UDP-OK-NONCANONMETATYPE-070",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_ok_metadata_type),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let truncated_udp_open = udp_open_bytes[..udp_open_bytes.len() - 1].to_vec();
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OPEN-TRUNCATED-020.json"),
        &json!({
            "case_id": "WC-UDP-OPEN-TRUNCATED-020",
            "suite": "WC",
            "hex": to_hex(&truncated_udp_open),
            "expected_error": "LengthMismatch"
        }),
    )?;

    let noncanonical_udp_open_flow = raw_udp_flow_open_noncanonical_flow_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OPEN-NONCANONFLOW-034.json"),
        &json!({
            "case_id": "WC-UDP-OPEN-NONCANONFLOW-034",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_open_flow),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let noncanonical_udp_open_flags = raw_udp_flow_open_noncanonical_flags_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OPEN-NONCANONFLAGS-035.json"),
        &json!({
            "case_id": "WC-UDP-OPEN-NONCANONFLAGS-035",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_open_flags),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let noncanonical_udp_open_timeout = raw_udp_flow_open_noncanonical_timeout_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OPEN-NONCANONTIMEOUT-036.json"),
        &json!({
            "case_id": "WC-UDP-OPEN-NONCANONTIMEOUT-036",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_open_timeout),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let invalid_udp_open_ipv4_length = raw_udp_flow_open_ipv4_length_mismatch_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OPEN-IPV4LEN-038.json"),
        &json!({
            "case_id": "WC-UDP-OPEN-IPV4LEN-038",
            "suite": "WC",
            "hex": to_hex(&invalid_udp_open_ipv4_length),
            "expected_error": "Validation"
        }),
    )?;

    let invalid_udp_open_target_type = raw_udp_flow_open_bad_target_type_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OPEN-BADTARGETTYPE-039.json"),
        &json!({
            "case_id": "WC-UDP-OPEN-BADTARGETTYPE-039",
            "suite": "WC",
            "hex": to_hex(&invalid_udp_open_target_type),
            "expected_error": "Validation"
        }),
    )?;

    let noncanonical_udp_open_target_type = raw_udp_flow_open_noncanonical_target_type_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OPEN-NONCANONTARGETTYPE-043.json"),
        &json!({
            "case_id": "WC-UDP-OPEN-NONCANONTARGETTYPE-043",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_open_target_type),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let noncanonical_udp_open_port = raw_udp_flow_open_noncanonical_port_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OPEN-NONCANONPORT-044.json"),
        &json!({
            "case_id": "WC-UDP-OPEN-NONCANONPORT-044",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_open_port),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let invalid_udp_open_ipv6_length = raw_udp_flow_open_ipv6_length_mismatch_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OPEN-IPV6LEN-040.json"),
        &json!({
            "case_id": "WC-UDP-OPEN-IPV6LEN-040",
            "suite": "WC",
            "hex": to_hex(&invalid_udp_open_ipv6_length),
            "expected_error": "Validation"
        }),
    )?;

    let invalid_udp_open_empty_domain = raw_udp_flow_open_empty_domain_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OPEN-EMPTYDOMAIN-041.json"),
        &json!({
            "case_id": "WC-UDP-OPEN-EMPTYDOMAIN-041",
            "suite": "WC",
            "hex": to_hex(&invalid_udp_open_empty_domain),
            "expected_error": "Validation"
        }),
    )?;

    let invalid_udp_open_bad_metadata_count = raw_udp_flow_open_bad_metadata_count_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OPEN-BADMETACOUNT-056.json"),
        &json!({
            "case_id": "WC-UDP-OPEN-BADMETACOUNT-056",
            "suite": "WC",
            "hex": to_hex(&invalid_udp_open_bad_metadata_count),
            "expected_error": "Validation"
        }),
    )?;

    let noncanonical_udp_open_metadata_count =
        raw_udp_flow_open_noncanonical_metadata_count_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OPEN-NONCANONMETACOUNT-057.json"),
        &json!({
            "case_id": "WC-UDP-OPEN-NONCANONMETACOUNT-057",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_open_metadata_count),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let invalid_udp_open_bad_metadata_len = raw_udp_flow_open_bad_metadata_len_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OPEN-BADMETALEN-065.json"),
        &json!({
            "case_id": "WC-UDP-OPEN-BADMETALEN-065",
            "suite": "WC",
            "hex": to_hex(&invalid_udp_open_bad_metadata_len),
            "expected_error": "Truncated"
        }),
    )?;

    let noncanonical_udp_open_metadata_len = raw_udp_flow_open_noncanonical_metadata_len_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OPEN-NONCANONMETALEN-061.json"),
        &json!({
            "case_id": "WC-UDP-OPEN-NONCANONMETALEN-061",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_open_metadata_len),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let noncanonical_udp_open_metadata_type = raw_udp_flow_open_noncanonical_metadata_type_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OPEN-NONCANONMETATYPE-069.json"),
        &json!({
            "case_id": "WC-UDP-OPEN-NONCANONMETATYPE-069",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_open_metadata_type),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let noncanonical_udp_open_frame_len = raw_frame_with_noncanonical_length(&udp_open_bytes)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OPEN-NONCANONFRAMELEN-073.json"),
        &json!({
            "case_id": "WC-UDP-OPEN-NONCANONFRAMELEN-073",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_open_frame_len),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let bad_udp_open_frame_len = raw_frame_with_mismatched_length(&udp_open_bytes, 1)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OPEN-BADFRAMELEN-086.json"),
        &json!({
            "case_id": "WC-UDP-OPEN-BADFRAMELEN-086",
            "suite": "WC",
            "hex": to_hex(&bad_udp_open_frame_len),
            "expected_error": "LengthMismatch"
        }),
    )?;

    let bad_udp_flow_close_dgramunavail_frame_len =
        raw_frame_with_mismatched_length(&udp_flow_close_datagram_unavailable_bytes, 1)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-FLOW-CLOSE-DGRAMUNAVAIL-BADFRAMELEN-087.json"),
        &json!({
            "case_id": "WC-UDP-FLOW-CLOSE-DGRAMUNAVAIL-BADFRAMELEN-087",
            "suite": "WC",
            "hex": to_hex(&bad_udp_flow_close_dgramunavail_frame_len),
            "expected_error": "LengthMismatch"
        }),
    )?;

    let noncanonical_udp_ok_frame_len = raw_frame_with_noncanonical_length(&udp_ok_bytes)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OK-NONCANONFRAMELEN-074.json"),
        &json!({
            "case_id": "WC-UDP-OK-NONCANONFRAMELEN-074",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_ok_frame_len),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let bad_udp_ok_frame_len = raw_frame_with_mismatched_length(&udp_ok_fallback_bytes, 1)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OK-BADFRAMELEN-085.json"),
        &json!({
            "case_id": "WC-UDP-OK-BADFRAMELEN-085",
            "suite": "WC",
            "hex": to_hex(&bad_udp_ok_frame_len),
            "expected_error": "LengthMismatch"
        }),
    )?;

    let invalid_udp_open_zero_port = raw_udp_flow_open_zero_port_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OPEN-ZEROPORT-047.json"),
        &json!({
            "case_id": "WC-UDP-OPEN-ZEROPORT-047",
            "suite": "WC",
            "hex": to_hex(&invalid_udp_open_zero_port),
            "expected_error": "Validation"
        }),
    )?;

    let invalid_udp_open_bad_utf8_domain = raw_udp_flow_open_bad_utf8_domain_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-OPEN-BADUTF8DOMAIN-048.json"),
        &json!({
            "case_id": "WC-UDP-OPEN-BADUTF8DOMAIN-048",
            "suite": "WC",
            "hex": to_hex(&invalid_udp_open_bad_utf8_domain),
            "expected_error": "InvalidUtf8"
        }),
    )?;

    let noncanonical_udp_datagram = raw_udp_datagram_noncanonical_flow_id(b"dns-query");
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-DGRAM-NONCANONFLOW-021.json"),
        &json!({
            "case_id": "WC-UDP-DGRAM-NONCANONFLOW-021",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_datagram),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let noncanonical_udp_datagram_flags = raw_udp_datagram_noncanonical_flags(b"dns-query");
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-DGRAM-NONCANONFLAGS-027.json"),
        &json!({
            "case_id": "WC-UDP-DGRAM-NONCANONFLAGS-027",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_datagram_flags),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let bad_udp_stream_packet = raw_udp_stream_packet_frame(5, b"abcd")?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-PACKET-LEN-010.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-PACKET-LEN-010",
            "suite": "WC",
            "hex": to_hex(&bad_udp_stream_packet),
            "expected_error": "Truncated"
        }),
    )?;

    let noncanonical_udp_stream_packet =
        raw_udp_stream_packet_noncanonical_declared_len_frame(b"abcd")?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-PACKET-NONCANONLEN-031.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-PACKET-NONCANONLEN-031",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_stream_packet),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let noncanonical_udp_stream_packet_frame_len =
        raw_frame_with_noncanonical_length(&udp_stream_packet_bytes)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-PACKET-NONCANONFRAMELEN-079.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-PACKET-NONCANONFRAMELEN-079",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_stream_packet_frame_len),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let bad_udp_stream_packet_frame_len =
        raw_frame_with_mismatched_length(&udp_stream_packet_bytes, 1)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-PACKET-BADFRAMELEN-080.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-PACKET-BADFRAMELEN-080",
            "suite": "WC",
            "hex": to_hex(&bad_udp_stream_packet_frame_len),
            "expected_error": "LengthMismatch"
        }),
    )?;

    let bad_udp_stream_open_frame_len =
        raw_frame_with_mismatched_length(&udp_stream_open_bytes, 1)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-OPEN-BADFRAMELEN-081.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-OPEN-BADFRAMELEN-081",
            "suite": "WC",
            "hex": to_hex(&bad_udp_stream_open_frame_len),
            "expected_error": "LengthMismatch"
        }),
    )?;

    let bad_udp_stream_accept_frame_len =
        raw_frame_with_mismatched_length(&udp_stream_accept_bytes, 1)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-ACCEPT-BADFRAMELEN-082.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-ACCEPT-BADFRAMELEN-082",
            "suite": "WC",
            "hex": to_hex(&bad_udp_stream_accept_frame_len),
            "expected_error": "LengthMismatch"
        }),
    )?;

    let noncanonical_udp_flow_close_flow =
        raw_udp_flow_close_noncanonical_flow_frame(0, "noncanonical-close")?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-FLOW-CLOSE-NONCANONFLOW-032.json"),
        &json!({
            "case_id": "WC-UDP-FLOW-CLOSE-NONCANONFLOW-032",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_flow_close_flow),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let noncanonical_udp_flow_close_message_len =
        raw_udp_flow_close_noncanonical_message_len_frame(7, 0, "noncanonical-close")?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-FLOW-CLOSE-NONCANONMSGLEN-045.json"),
        &json!({
            "case_id": "WC-UDP-FLOW-CLOSE-NONCANONMSGLEN-045",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_flow_close_message_len),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let noncanonical_udp_flow_close_frame_len =
        raw_frame_with_noncanonical_length(&udp_flow_close_bytes)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-FLOW-CLOSE-NONCANONFRAMELEN-077.json"),
        &json!({
            "case_id": "WC-UDP-FLOW-CLOSE-NONCANONFRAMELEN-077",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_flow_close_frame_len),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let bad_udp_flow_close_frame_len = raw_frame_with_mismatched_length(&udp_flow_close_bytes, 1)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-FLOW-CLOSE-BADFRAMELEN-084.json"),
        &json!({
            "case_id": "WC-UDP-FLOW-CLOSE-BADFRAMELEN-084",
            "suite": "WC",
            "hex": to_hex(&bad_udp_flow_close_frame_len),
            "expected_error": "LengthMismatch"
        }),
    )?;

    let noncanonical_udp_stream_close_flow =
        raw_udp_stream_close_noncanonical_flow_frame(0, "noncanonical-close")?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-CLOSE-NONCANONFLOW-033.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-CLOSE-NONCANONFLOW-033",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_stream_close_flow),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let noncanonical_udp_stream_close_message_len =
        raw_udp_stream_close_noncanonical_message_len_frame(7, 0, "noncanonical-close")?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-CLOSE-NONCANONMSGLEN-046.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-CLOSE-NONCANONMSGLEN-046",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_stream_close_message_len),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let noncanonical_udp_stream_close_frame_len =
        raw_frame_with_noncanonical_length(&udp_stream_close_bytes)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-CLOSE-NONCANONFRAMELEN-078.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-CLOSE-NONCANONFRAMELEN-078",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_stream_close_frame_len),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let bad_udp_stream_close_frame_len =
        raw_frame_with_mismatched_length(&udp_stream_close_bytes, 1)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-CLOSE-BADFRAMELEN-083.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-CLOSE-BADFRAMELEN-083",
            "suite": "WC",
            "hex": to_hex(&bad_udp_stream_close_frame_len),
            "expected_error": "LengthMismatch"
        }),
    )?;

    let bad_udp_stream_close = raw_udp_stream_close_frame(7, 99, "bad-close")?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-CLOSE-BADCODE-011.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-CLOSE-BADCODE-011",
            "suite": "WC",
            "hex": to_hex(&bad_udp_stream_close),
            "expected_error": "Validation"
        }),
    )?;

    let bad_udp_stream_close_extended = raw_udp_stream_close_frame(9, 123, "unsupported-close")?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-CLOSE-BADCODE-022.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-CLOSE-BADCODE-022",
            "suite": "WC",
            "hex": to_hex(&bad_udp_stream_close_extended),
            "expected_error": "Validation"
        }),
    )?;

    let noncanonical_udp_stream_close =
        raw_udp_stream_close_noncanonical_code_frame(7, "noncanonical-close")?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-CLOSE-NONCANONCODE-028.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-CLOSE-NONCANONCODE-028",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_stream_close),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let invalid_udp_stream_close_bad_utf8 = raw_udp_stream_close_bad_utf8_message_frame(7, 0)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-CLOSE-BADUTF8-050.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-CLOSE-BADUTF8-050",
            "suite": "WC",
            "hex": to_hex(&invalid_udp_stream_close_bad_utf8),
            "expected_error": "InvalidUtf8"
        }),
    )?;

    let bad_udp_flow_close = raw_udp_flow_close_frame(7, 99, "bad-close")?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-FLOW-CLOSE-BADCODE-012.json"),
        &json!({
            "case_id": "WC-UDP-FLOW-CLOSE-BADCODE-012",
            "suite": "WC",
            "hex": to_hex(&bad_udp_flow_close),
            "expected_error": "Validation"
        }),
    )?;

    let invalid_udp_flow_close_bad_utf8 = raw_udp_flow_close_bad_utf8_message_frame(7, 0)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-FLOW-CLOSE-BADUTF8-052.json"),
        &json!({
            "case_id": "WC-UDP-FLOW-CLOSE-BADUTF8-052",
            "suite": "WC",
            "hex": to_hex(&invalid_udp_flow_close_bad_utf8),
            "expected_error": "InvalidUtf8"
        }),
    )?;

    let noncanonical_udp_flow_close =
        raw_udp_flow_close_noncanonical_code_frame(7, "noncanonical-close")?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-FLOW-CLOSE-NONCANONCODE-024.json"),
        &json!({
            "case_id": "WC-UDP-FLOW-CLOSE-NONCANONCODE-024",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_flow_close),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let truncated_udp_flow_close = udp_flow_close_bytes[..udp_flow_close_bytes.len() - 1].to_vec();
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-FLOW-CLOSE-TRUNCATED-016.json"),
        &json!({
            "case_id": "WC-UDP-FLOW-CLOSE-TRUNCATED-016",
            "suite": "WC",
            "hex": to_hex(&truncated_udp_flow_close),
            "expected_error": "LengthMismatch"
        }),
    )?;

    let truncated_udp_stream_open = raw_udp_stream_open_truncated_frame(7)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-OPEN-TRUNCATED-013.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-OPEN-TRUNCATED-013",
            "suite": "WC",
            "hex": to_hex(&truncated_udp_stream_open),
            "expected_error": "Truncated"
        }),
    )?;

    let noncanonical_udp_stream_open = raw_udp_stream_open_noncanonical_flow_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-OPEN-NONCANONFLOW-025.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-OPEN-NONCANONFLOW-025",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_stream_open),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let invalid_udp_stream_open_bad_metadata_count =
        raw_udp_stream_open_bad_metadata_count_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-OPEN-BADMETACOUNT-053.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-OPEN-BADMETACOUNT-053",
            "suite": "WC",
            "hex": to_hex(&invalid_udp_stream_open_bad_metadata_count),
            "expected_error": "Validation"
        }),
    )?;

    let noncanonical_udp_stream_open_metadata_count =
        raw_udp_stream_open_noncanonical_metadata_count_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-OPEN-NONCANONMETACOUNT-059.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-OPEN-NONCANONMETACOUNT-059",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_stream_open_metadata_count),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let invalid_udp_stream_open_bad_metadata_len = raw_udp_stream_open_bad_metadata_len_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-OPEN-BADMETALEN-067.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-OPEN-BADMETALEN-067",
            "suite": "WC",
            "hex": to_hex(&invalid_udp_stream_open_bad_metadata_len),
            "expected_error": "Truncated"
        }),
    )?;

    let noncanonical_udp_stream_open_metadata_len =
        raw_udp_stream_open_noncanonical_metadata_len_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-OPEN-NONCANONMETALEN-063.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-OPEN-NONCANONMETALEN-063",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_stream_open_metadata_len),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let noncanonical_udp_stream_open_metadata_type =
        raw_udp_stream_open_noncanonical_metadata_type_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-OPEN-NONCANONMETATYPE-071.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-OPEN-NONCANONMETATYPE-071",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_stream_open_metadata_type),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let noncanonical_udp_stream_open_frame_len =
        raw_frame_with_noncanonical_length(&udp_stream_open_bytes)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-OPEN-NONCANONFRAMELEN-075.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-OPEN-NONCANONFRAMELEN-075",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_stream_open_frame_len),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let truncated_udp_stream_accept =
        udp_stream_accept_bytes[..udp_stream_accept_bytes.len() - 1].to_vec();
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-ACCEPT-TRUNCATED-019.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-ACCEPT-TRUNCATED-019",
            "suite": "WC",
            "hex": to_hex(&truncated_udp_stream_accept),
            "expected_error": "LengthMismatch"
        }),
    )?;

    let noncanonical_udp_stream_accept = raw_udp_stream_accept_noncanonical_flow_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-ACCEPT-NONCANONFLOW-026.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-ACCEPT-NONCANONFLOW-026",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_stream_accept),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let invalid_udp_stream_accept_bad_metadata_count =
        raw_udp_stream_accept_bad_metadata_count_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-ACCEPT-BADMETACOUNT-054.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-ACCEPT-BADMETACOUNT-054",
            "suite": "WC",
            "hex": to_hex(&invalid_udp_stream_accept_bad_metadata_count),
            "expected_error": "Validation"
        }),
    )?;

    let noncanonical_udp_stream_accept_metadata_count =
        raw_udp_stream_accept_noncanonical_metadata_count_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-ACCEPT-NONCANONMETACOUNT-060.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-ACCEPT-NONCANONMETACOUNT-060",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_stream_accept_metadata_count),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let invalid_udp_stream_accept_bad_metadata_len =
        raw_udp_stream_accept_bad_metadata_len_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-ACCEPT-BADMETALEN-068.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-ACCEPT-BADMETALEN-068",
            "suite": "WC",
            "hex": to_hex(&invalid_udp_stream_accept_bad_metadata_len),
            "expected_error": "Truncated"
        }),
    )?;

    let noncanonical_udp_stream_accept_metadata_len =
        raw_udp_stream_accept_noncanonical_metadata_len_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-ACCEPT-NONCANONMETALEN-064.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-ACCEPT-NONCANONMETALEN-064",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_stream_accept_metadata_len),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let noncanonical_udp_stream_accept_metadata_type =
        raw_udp_stream_accept_noncanonical_metadata_type_frame()?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-ACCEPT-NONCANONMETATYPE-072.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-ACCEPT-NONCANONMETATYPE-072",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_stream_accept_metadata_type),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let noncanonical_udp_stream_accept_frame_len =
        raw_frame_with_noncanonical_length(&udp_stream_accept_bytes)?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-ACCEPT-NONCANONFRAMELEN-076.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-ACCEPT-NONCANONFRAMELEN-076",
            "suite": "WC",
            "hex": to_hex(&noncanonical_udp_stream_accept_frame_len),
            "expected_error": "NonCanonicalVarint"
        }),
    )?;

    let truncated_udp_stream_packet = raw_udp_stream_packet_frame(9, b"xy")?;
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-PACKET-TRUNCATED-014.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-PACKET-TRUNCATED-014",
            "suite": "WC",
            "hex": to_hex(&truncated_udp_stream_packet),
            "expected_error": "Truncated"
        }),
    )?;

    let truncated_udp_stream_close =
        udp_stream_close_bytes[..udp_stream_close_bytes.len() - 1].to_vec();
    write_json(
        &root.join("fixtures/wire/v1/invalid/WC-UDP-STREAM-CLOSE-TRUNCATED-017.json"),
        &json!({
            "case_id": "WC-UDP-STREAM-CLOSE-TRUNCATED-017",
            "suite": "WC",
            "hex": to_hex(&truncated_udp_stream_close),
            "expected_error": "LengthMismatch"
        }),
    )?;

    Ok(())
}

fn write_manifest_fixtures(
    root: &Path,
    now: OffsetDateTime,
) -> Result<(), Box<dyn std::error::Error>> {
    let manifest_key = SigningKey::from_bytes(&[41_u8; 32]);

    let mut valid = manifest_template(now, now + Duration::hours(6));
    valid.signature.key_id = MANIFEST_KID.to_owned();
    let valid_signing_input = valid.canonical_signing_input()?;
    valid.signature.value = base64::engine::general_purpose::URL_SAFE_NO_PAD
        .encode(manifest_key.sign(&valid_signing_input).to_bytes());
    write_pretty_json(
        &root.join("fixtures/manifest/v1/valid/MF-MANIFEST-VALID-001.json"),
        &valid,
    )?;

    let mut badsig = valid.clone();
    badsig.endpoints[0].host = "tampered.example.net".to_owned();
    write_pretty_json(
        &root.join("fixtures/manifest/v1/invalid/MF-MANIFEST-BADSIG-002.json"),
        &badsig,
    )?;

    let mut expired = manifest_template(now - Duration::hours(12), now - Duration::hours(6));
    expired.signature.key_id = MANIFEST_KID.to_owned();
    let expired_signing_input = expired.canonical_signing_input()?;
    expired.signature.value = base64::engine::general_purpose::URL_SAFE_NO_PAD
        .encode(manifest_key.sign(&expired_signing_input).to_bytes());
    write_pretty_json(
        &root.join("fixtures/manifest/v1/invalid/MF-MANIFEST-EXPIRED-003.json"),
        &expired,
    )?;

    let mut wrong_schema = manifest_template(now, now + Duration::hours(6));
    wrong_schema.schema_version = 2;
    wrong_schema.signature.key_id = MANIFEST_KID.to_owned();
    let wrong_schema_signing_input = wrong_schema.canonical_signing_input()?;
    wrong_schema.signature.value = base64::engine::general_purpose::URL_SAFE_NO_PAD
        .encode(manifest_key.sign(&wrong_schema_signing_input).to_bytes());
    write_pretty_json(
        &root.join("fixtures/manifest/v1/invalid/MF-MANIFEST-SCHEMA-004.json"),
        &wrong_schema,
    )?;

    let mut disabled_profile = manifest_template(now, now + Duration::hours(6));
    let mut secondary_profile = disabled_profile.carrier_profiles[0].clone();
    secondary_profile.id = "carrier-secondary".to_owned();
    secondary_profile.origin_host = "backup.origin.edge.example.net".to_owned();
    secondary_profile.sni = Some("backup.origin.edge.example.net".to_owned());
    secondary_profile
        .headers
        .insert("x-verta-profile".to_owned(), "carrier-secondary".to_owned());
    disabled_profile.carrier_profiles.push(secondary_profile);
    disabled_profile.endpoints[0].carrier_profile_ids = vec!["carrier-secondary".to_owned()];
    disabled_profile.signature.key_id = MANIFEST_KID.to_owned();
    let disabled_profile_signing_input = disabled_profile.canonical_signing_input()?;
    disabled_profile.signature.value = base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(
        manifest_key
            .sign(&disabled_profile_signing_input)
            .to_bytes(),
    );
    write_pretty_json(
        &root.join("fixtures/manifest/v1/valid/MF-DISABLEDPROFILE-006.json"),
        &disabled_profile,
    )?;

    let mut empty_inventory = manifest_template(now, now + Duration::hours(6));
    empty_inventory.endpoints.clear();
    empty_inventory.signature.key_id = MANIFEST_KID.to_owned();
    let empty_inventory_signing_input = empty_inventory.canonical_signing_input()?;
    empty_inventory.signature.value = base64::engine::general_purpose::URL_SAFE_NO_PAD
        .encode(manifest_key.sign(&empty_inventory_signing_input).to_bytes());
    write_pretty_json(
        &root.join("fixtures/manifest/v1/invalid/MF-EMPTYINVENTORY-007.json"),
        &empty_inventory,
    )?;

    Ok(())
}

fn write_token_fixtures(
    root: &Path,
    now: OffsetDateTime,
) -> Result<(), Box<dyn std::error::Error>> {
    let token_key = SigningKey::from_bytes(&[42_u8; 32]);
    let private_pem = token_key.to_pkcs8_pem(Default::default())?.to_string();

    let signer = SessionTokenSigner::from_ed_pem(
        "bridge.example",
        "verta-gateway",
        TOKEN_KID,
        private_pem.as_bytes(),
    )?;

    write_json(
        &root.join("fixtures/token/jws/valid/AU-TOKEN-VALID-001.json"),
        &json!({
            "issuer": "bridge.example",
            "subject": "acct-1",
            "device_id": "device-1",
            "manifest_id": "man-2026-04-01-001",
            "policy_epoch": 7,
            "core_versions": [1],
            "carrier_profiles": ["carrier-primary"],
            "capabilities": [1, 2],
            "session_modes": ["tcp"],
            "region_scope": "eu-central",
            "ttl_seconds": 300
        }),
    )?;

    let valid = signer.mint(token_request(), now, Duration::seconds(300))?;
    write_text(
        &root.join("fixtures/token/jws/valid/AU-TOKEN-VALID-001.jwt"),
        &valid.token,
    )?;

    let expired = signer.mint(
        token_request(),
        now - Duration::minutes(10),
        Duration::seconds(300),
    )?;
    write_text(
        &root.join("fixtures/token/jws/invalid/AU-TOKEN-EXPIRED-002.jwt"),
        &expired.token,
    )?;

    let future = signer.mint(
        token_request(),
        now + Duration::minutes(2),
        Duration::seconds(300),
    )?;
    write_text(
        &root.join("fixtures/token/jws/invalid/AU-TOKEN-NBF-FUTURE-003.jwt"),
        &future.token,
    )?;

    let wrong_issuer = SessionTokenSigner::from_ed_pem(
        "other-bridge.example",
        "verta-gateway",
        TOKEN_KID,
        private_pem.as_bytes(),
    )?
    .mint(token_request(), now, Duration::seconds(300))?;
    write_text(
        &root.join("fixtures/token/jws/invalid/AU-TOKEN-WRONGISS-004.jwt"),
        &wrong_issuer.token,
    )?;

    let wrong_audience = SessionTokenSigner::from_ed_pem(
        "bridge.example",
        "verta-client",
        TOKEN_KID,
        private_pem.as_bytes(),
    )?
    .mint(token_request(), now, Duration::seconds(300))?;
    write_text(
        &root.join("fixtures/token/jws/invalid/AU-TOKEN-WRONGAUD-005.jwt"),
        &wrong_audience.token,
    )?;

    let unknown_kid = SessionTokenSigner::from_ed_pem(
        "bridge.example",
        "verta-gateway",
        "fixture-token-key-2",
        private_pem.as_bytes(),
    )?
    .mint(token_request(), now, Duration::seconds(300))?;
    write_text(
        &root.join("fixtures/token/jws/invalid/AU-TOKEN-UNKNOWNKID-007.jwt"),
        &unknown_kid.token,
    )?;

    let wrong_alg = rewrite_token_alg(&valid.token, "HS256")?;
    write_text(
        &root.join("fixtures/token/jws/invalid/AU-TOKEN-WRONGALG-006.jwt"),
        &wrong_alg,
    )?;

    let wrong_typ = rewrite_token_typ(&valid.token, "verta+jwt")?;
    write_text(
        &root.join("fixtures/token/jws/invalid/AU-TOKEN-WRONGTYP-008.jwt"),
        &wrong_typ,
    )?;

    write_text(
        &root.join("fixtures/token/jws/invalid/AU-TOKEN-MALFORMED-009.jwt"),
        "not-a-jwt",
    )?;

    let no_typ = rewrite_token_without_typ(&valid.token)?;
    write_text(
        &root.join("fixtures/token/jws/invalid/AU-TOKEN-NOTYP-010.jwt"),
        &no_typ,
    )?;

    let stale_jwks = JwkSet {
        keys: vec![jwk_for_signing_key(
            TOKEN_KID,
            &SigningKey::from_bytes(&[43_u8; 32]),
        )],
    };
    write_json(
        &root.join("fixtures/token/jws/invalid/AU-TOKEN-STALEJWKS-011.json"),
        &json!({
            "token": valid.token,
            "jwks": stale_jwks
        }),
    )?;

    let revoked_subject = signer.mint(token_request(), now, Duration::seconds(300))?;
    write_json(
        &root.join("fixtures/token/jws/invalid/AU-TOKEN-REVOKEDSUB-012.json"),
        &json!({
            "token": revoked_subject.token,
            "revoked_subjects": ["acct-1"]
        }),
    )?;

    let stale_policy = signer.mint(token_request(), now, Duration::seconds(300))?;
    write_json(
        &root.join("fixtures/token/jws/invalid/AU-TOKEN-STALEPOLICY-013.json"),
        &json!({
            "token": stale_policy.token,
            "minimum_policy_epoch": 8
        }),
    )?;

    Ok(())
}

fn write_bridge_and_webhook_fixtures(root: &Path) -> Result<(), Box<dyn std::error::Error>> {
    write_json(
        &root.join("fixtures/bridge/bootstrap/BG-MANIFEST-FETCH-BOOTSTRAP-001.json"),
        &json!({
            "case_id": "BG-MANIFEST-FETCH-BOOTSTRAP-001",
            "subscription_token": "sub-1",
            "authorization_header": null,
            "expected_mode": "bootstrap"
        }),
    )?;

    write_json(
        &root.join("fixtures/bridge/bootstrap/BG-MANIFEST-FETCH-REFRESH-002.json"),
        &json!({
            "case_id": "BG-MANIFEST-FETCH-REFRESH-002",
            "subscription_token": null,
            "authorization_header": "Bearer rfr_fixture_123",
            "expected_mode": "refresh"
        }),
    )?;

    write_json(
        &root.join("fixtures/bridge/bootstrap/BG-MANIFEST-FETCH-CONFLICT-003.json"),
        &json!({
            "case_id": "BG-MANIFEST-FETCH-CONFLICT-003",
            "subscription_token": "sub-1",
            "authorization_header": "Bearer rfr_fixture_123",
            "expected_error": "ConflictingManifestAuthModes"
        }),
    )?;

    write_json(
        &root.join("fixtures/bridge/device/BG-DEVICE-REGISTER-VALID-004.json"),
        &json!({
            "manifest_id": "man-2026-04-01-001",
            "device_id": "device-1",
            "device_name": "Workstation",
            "platform": "windows",
            "client_version": "0.1.0",
            "install_channel": "stable",
            "requested_capabilities": [1, 2]
        }),
    )?;

    write_json(
        &root.join("fixtures/bridge/device/BG-DEVICE-REGISTER-UNKNOWNFIELD-005.json"),
        &json!({
            "manifest_id": "man-2026-04-01-001",
            "device_id": "device-1",
            "platform": "windows",
            "client_version": "0.1.0",
            "requested_capabilities": [1],
            "unexpected_field": true
        }),
    )?;

    write_json(
        &root.join("fixtures/bridge/device/BG-DEVICE-REGISTER-LIMIT-008.json"),
        &json!({
            "manifest_id": "man-2026-04-01-001",
            "device_id": "device-3",
            "device_name": "Tablet",
            "platform": "windows",
            "client_version": "0.1.0",
            "install_channel": "stable",
            "requested_capabilities": [1, 2],
            "expected_error": "DeviceLimitReached"
        }),
    )?;

    write_json(
        &root.join("fixtures/bridge/token/BG-TOKEN-EXCHANGE-VALID-006.json"),
        &json!({
            "manifest_id": "man-2026-04-01-001",
            "device_id": "device-1",
            "client_version": "0.1.0",
            "core_version": 1,
            "carrier_profile_id": "carrier-primary",
            "requested_capabilities": [1, 2],
            "refresh_credential": "rfr_fixture_123"
        }),
    )?;

    write_json(
        &root.join("fixtures/bridge/token/BG-TOKEN-EXCHANGE-MISSINGREFRESH-007.json"),
        &json!({
            "manifest_id": "man-2026-04-01-001",
            "device_id": "device-1",
            "client_version": "0.1.0",
            "core_version": 1,
            "carrier_profile_id": "carrier-primary",
            "requested_capabilities": [1, 2]
        }),
    )?;

    write_json(
        &root.join("fixtures/bridge/token/BG-TOKEN-EXCHANGE-REVOKEDDEVICE-009.json"),
        &json!({
            "manifest_id": "man-2026-04-01-001",
            "device_id": "device-2",
            "client_version": "0.1.0",
            "core_version": 1,
            "carrier_profile_id": "carrier-primary",
            "requested_capabilities": [1, 2],
            "refresh_credential": "rfr_revoked_fixture",
            "expected_error": "DeviceRevoked"
        }),
    )?;

    write_json(
        &root.join("fixtures/remnawave/webhook/BG-WEBHOOK-VALID-001.json"),
        &json!({
            "case_id": "BG-WEBHOOK-VALID-001",
            "signature_header": "sig-ok",
            "timestamp_header": "1775002200",
            "body": "{\"event\":\"account.updated\"}",
            "expected": "ok"
        }),
    )?;

    write_json(
        &root.join("fixtures/remnawave/webhook/BG-WEBHOOK-STALE-002.json"),
        &json!({
            "case_id": "BG-WEBHOOK-STALE-002",
            "signature_header": "sig-ok",
            "timestamp_header": "1775000000",
            "body": "{\"event\":\"account.updated\"}",
            "expected_error": "StaleTimestamp"
        }),
    )?;

    write_json(
        &root.join("fixtures/remnawave/webhook/BG-WEBHOOK-BADSIG-003.json"),
        &json!({
            "case_id": "BG-WEBHOOK-BADSIG-003",
            "signature_header": "sig-bad",
            "timestamp_header": "1775002200",
            "body": "{\"event\":\"account.updated\"}",
            "expected_error": "InvalidSignature"
        }),
    )?;

    write_json(
        &root.join("fixtures/remnawave/webhook/BG-WEBHOOK-MISSINGSIG-004.json"),
        &json!({
            "case_id": "BG-WEBHOOK-MISSINGSIG-004",
            "signature_header": "",
            "timestamp_header": "1775002200",
            "body": "{\"event\":\"account.updated\"}",
            "expected_error": "MissingSignature"
        }),
    )?;

    write_json(
        &root.join("fixtures/remnawave/webhook/BG-WEBHOOK-BADTIMESTAMP-005.json"),
        &json!({
            "case_id": "BG-WEBHOOK-BADTIMESTAMP-005",
            "signature_header": "sig-ok",
            "timestamp_header": "not-a-timestamp",
            "body": "{\"event\":\"account.updated\"}",
            "expected_error": "InvalidTimestamp"
        }),
    )?;

    write_json(
        &root.join("fixtures/remnawave/webhook/BG-WEBHOOK-DUPLICATE-006.json"),
        &json!({
            "case_id": "BG-WEBHOOK-DUPLICATE-006",
            "signature_header": "sig-ok",
            "timestamp_header": "1775002200",
            "body": "{\"event\":\"account.updated\",\"event_id\":\"evt-dup-1\"}",
            "payload": {
                "event_id": "evt-dup-1",
                "event_type": "account.updated",
                "account_id": "acct-1",
                "occurred_at_unix": 1775002200,
                "payload": {
                    "lifecycle": "active"
                }
            }
        }),
    )?;

    Ok(())
}

fn manifest_template(generated_at: OffsetDateTime, expires_at: OffsetDateTime) -> ManifestDocument {
    sample_manifest_document(generated_at, expires_at)
}

fn token_request() -> MintedTokenRequest {
    MintedTokenRequest {
        subject: "acct-1".to_owned(),
        device_id: DeviceBindingId::new("device-1")
            .expect("fixture device binding id should be valid"),
        manifest_id: ManifestId::new("man-2026-04-01-001")
            .expect("fixture manifest id should be valid"),
        policy_epoch: 7,
        core_versions: vec![1],
        carrier_profiles: vec![
            CarrierProfileId::new("carrier-primary")
                .expect("fixture carrier profile should be valid")
                .as_str()
                .to_owned(),
        ],
        capabilities: vec![Capability::TcpRelay.id(), Capability::UdpRelay.id()],
        session_modes: vec!["tcp".to_owned()],
        region_scope: Some("eu-central".to_owned()),
        token_max_relay_streams: Some(8),
        token_max_udp_flows: Some(4),
        token_max_udp_payload: Some(1200),
    }
}

fn rewrite_token_alg(token: &str, alg: &str) -> Result<String, Box<dyn std::error::Error>> {
    rewrite_token_header(token, |header| {
        header["alg"] = serde_json::Value::String(alg.to_owned());
    })
}

fn rewrite_token_typ(token: &str, typ: &str) -> Result<String, Box<dyn std::error::Error>> {
    rewrite_token_header(token, |header| {
        header["typ"] = serde_json::Value::String(typ.to_owned());
    })
}

fn rewrite_token_without_typ(token: &str) -> Result<String, Box<dyn std::error::Error>> {
    rewrite_token_header(token, |header| {
        if let Some(object) = header.as_object_mut() {
            object.remove("typ");
        }
    })
}

fn rewrite_token_header(
    token: &str,
    mutator: impl FnOnce(&mut serde_json::Value),
) -> Result<String, Box<dyn std::error::Error>> {
    let mut segments = token.split('.').collect::<Vec<_>>();
    if segments.len() != 3 {
        return Err("token must have three JWT segments".into());
    }
    let header_bytes = base64::engine::general_purpose::URL_SAFE_NO_PAD.decode(segments[0])?;
    let mut header_value: serde_json::Value = serde_json::from_slice(&header_bytes)?;
    mutator(&mut header_value);
    let header = serde_json::to_vec(&header_value)?;
    segments[0] = Box::leak(
        base64::engine::general_purpose::URL_SAFE_NO_PAD
            .encode(header)
            .into_boxed_str(),
    );
    Ok(segments.join("."))
}

fn raw_client_hello_frame(
    min_version: u64,
    max_version: u64,
    carrier_kind: u64,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let hello = sample_client_hello("fixture-session-token".to_owned());
    let mut payload = Vec::new();
    encode_varint(min_version, &mut payload)?;
    encode_varint(max_version, &mut payload)?;
    payload.extend_from_slice(&hello.client_nonce);
    encode_varint(hello.requested_capabilities.len() as u64, &mut payload)?;
    for capability in &hello.requested_capabilities {
        encode_varint(capability.id(), &mut payload)?;
    }
    encode_varint(carrier_kind, &mut payload)?;
    encode_string(hello.carrier_profile_id.as_str(), &mut payload)?;
    encode_string(hello.manifest_id.as_str(), &mut payload)?;
    encode_string(hello.device_binding_id.as_str(), &mut payload)?;
    encode_varint(hello.requested_idle_timeout_ms, &mut payload)?;
    encode_varint(hello.requested_max_udp_payload, &mut payload)?;
    encode_bytes(&hello.token, &mut payload)?;
    encode_varint(0, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x01, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_frame_with_noncanonical_length(frame: &[u8]) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let (_, frame_type_len) = decode_varint_prefix(frame)?;
    let (payload_len, declared_len_len) = decode_varint_prefix(&frame[frame_type_len..])?;
    let payload = &frame[frame_type_len + declared_len_len..];
    if payload.len() != payload_len as usize {
        return Err("frame payload length did not match declared frame length".into());
    }

    let mut mutated = frame[..frame_type_len].to_vec();
    mutated.extend(encode_noncanonical_varint(payload_len)?);
    mutated.extend_from_slice(payload);
    Ok(mutated)
}

fn raw_frame_with_mismatched_length(
    frame: &[u8],
    extra_len: u64,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let (_, frame_type_len) = decode_varint_prefix(frame)?;
    let (payload_len, declared_len_len) = decode_varint_prefix(&frame[frame_type_len..])?;
    let payload = &frame[frame_type_len + declared_len_len..];
    if payload.len() != payload_len as usize {
        return Err("frame payload length did not match declared frame length".into());
    }

    let mut mutated = frame[..frame_type_len].to_vec();
    encode_varint(payload_len + extra_len, &mut mutated)?;
    mutated.extend_from_slice(payload);
    Ok(mutated)
}

fn decode_varint_prefix(bytes: &[u8]) -> Result<(u64, usize), Box<dyn std::error::Error>> {
    let first = *bytes.first().ok_or("varint prefix was truncated")?;
    let width = match first >> 6 {
        0 => 1,
        1 => 2,
        2 => 4,
        _ => 8,
    };
    if bytes.len() < width {
        return Err("varint prefix did not have enough bytes".into());
    }

    let mut value = u64::from(first & 0x3f);
    for byte in &bytes[1..width] {
        value = (value << 8) | u64::from(*byte);
    }

    Ok((value, width))
}

fn encode_noncanonical_varint(value: u64) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    if value < 64 {
        Ok(vec![0x40 | ((value >> 8) as u8), value as u8])
    } else if value < 16_384 {
        Ok(vec![
            0x80 | (((value >> 24) & 0x3f) as u8),
            ((value >> 16) & 0xff) as u8,
            ((value >> 8) & 0xff) as u8,
            (value & 0xff) as u8,
        ])
    } else if value < 1_073_741_824 {
        Ok(vec![
            0xc0 | (((value >> 56) & 0x3f) as u8),
            ((value >> 48) & 0xff) as u8,
            ((value >> 40) & 0xff) as u8,
            ((value >> 32) & 0xff) as u8,
            ((value >> 24) & 0xff) as u8,
            ((value >> 16) & 0xff) as u8,
            ((value >> 8) & 0xff) as u8,
            (value & 0xff) as u8,
        ])
    } else {
        Err("value too large for the reviewed noncanonical varint helper".into())
    }
}

fn raw_udp_flow_open_frame(flags: u64) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    encode_varint(ns_core::TargetType::Domain.id(), &mut payload)?;
    encode_string("dns.example.net", &mut payload)?;
    encode_varint(53, &mut payload)?;
    encode_varint(15_000, &mut payload)?;
    encode_varint(flags, &mut payload)?;
    encode_varint(0, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x08, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_open_bad_metadata_count_frame() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    encode_varint(ns_core::TargetType::Domain.id(), &mut payload)?;
    encode_string("dns.example.net", &mut payload)?;
    encode_varint(53, &mut payload)?;
    encode_varint(15_000, &mut payload)?;
    encode_varint(3, &mut payload)?;
    encode_varint((MAX_METADATA_TLVS as u64) + 1, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x08, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_open_noncanonical_metadata_count_frame()
-> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    encode_varint(ns_core::TargetType::Domain.id(), &mut payload)?;
    encode_string("dns.example.net", &mut payload)?;
    encode_varint(53, &mut payload)?;
    encode_varint(15_000, &mut payload)?;
    encode_varint(3, &mut payload)?;
    payload.extend_from_slice(&[0x40, 0x00]);

    let mut frame = Vec::new();
    encode_varint(0x08, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_open_bad_metadata_len_frame() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    encode_varint(ns_core::TargetType::Domain.id(), &mut payload)?;
    encode_string("dns.example.net", &mut payload)?;
    encode_varint(53, &mut payload)?;
    encode_varint(15_000, &mut payload)?;
    encode_varint(3, &mut payload)?;
    append_single_metadata_tlv_bad_len(&mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x08, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_open_noncanonical_metadata_len_frame() -> Result<Vec<u8>, Box<dyn std::error::Error>>
{
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    encode_varint(ns_core::TargetType::Domain.id(), &mut payload)?;
    encode_string("dns.example.net", &mut payload)?;
    encode_varint(53, &mut payload)?;
    encode_varint(15_000, &mut payload)?;
    encode_varint(3, &mut payload)?;
    append_single_metadata_tlv_noncanonical_len(&mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x08, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_open_noncanonical_metadata_type_frame()
-> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    encode_varint(ns_core::TargetType::Domain.id(), &mut payload)?;
    encode_string("dns.example.net", &mut payload)?;
    encode_varint(53, &mut payload)?;
    encode_varint(15_000, &mut payload)?;
    encode_varint(3, &mut payload)?;
    append_single_metadata_tlv_noncanonical_type(&mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x08, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_open_noncanonical_flow_frame() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = vec![0x40, 0x07];
    encode_varint(ns_core::TargetType::Domain.id(), &mut payload)?;
    encode_string("dns.example.net", &mut payload)?;
    encode_varint(53, &mut payload)?;
    encode_varint(15_000, &mut payload)?;
    encode_varint(3, &mut payload)?;
    encode_varint(0, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x08, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_open_noncanonical_flags_frame() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    encode_varint(ns_core::TargetType::Domain.id(), &mut payload)?;
    encode_string("dns.example.net", &mut payload)?;
    encode_varint(53, &mut payload)?;
    encode_varint(15_000, &mut payload)?;
    payload.extend_from_slice(&[0x40, 0x03]);
    encode_varint(0, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x08, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_open_noncanonical_timeout_frame() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    encode_varint(ns_core::TargetType::Domain.id(), &mut payload)?;
    encode_string("dns.example.net", &mut payload)?;
    encode_varint(53, &mut payload)?;
    payload.extend_from_slice(&[0x80, 0x00, 0x3a, 0x98]);
    encode_varint(3, &mut payload)?;
    encode_varint(0, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x08, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_open_ipv4_length_mismatch_frame() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    encode_varint(ns_core::TargetType::Ipv4.id(), &mut payload)?;
    encode_bytes(&[127, 0, 0], &mut payload)?;
    encode_varint(53, &mut payload)?;
    encode_varint(15_000, &mut payload)?;
    encode_varint(3, &mut payload)?;
    encode_varint(0, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x08, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_open_ipv6_length_mismatch_frame() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    encode_varint(ns_core::TargetType::Ipv6.id(), &mut payload)?;
    encode_bytes(
        &[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
        &mut payload,
    )?;
    encode_varint(53, &mut payload)?;
    encode_varint(15_000, &mut payload)?;
    encode_varint(3, &mut payload)?;
    encode_varint(0, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x08, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_open_empty_domain_frame() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    encode_varint(ns_core::TargetType::Domain.id(), &mut payload)?;
    encode_string("", &mut payload)?;
    encode_varint(53, &mut payload)?;
    encode_varint(15_000, &mut payload)?;
    encode_varint(3, &mut payload)?;
    encode_varint(0, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x08, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_open_zero_port_frame() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    encode_varint(ns_core::TargetType::Domain.id(), &mut payload)?;
    encode_string("dns.example.net", &mut payload)?;
    encode_varint(0, &mut payload)?;
    encode_varint(15_000, &mut payload)?;
    encode_varint(3, &mut payload)?;
    encode_varint(0, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x08, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_open_bad_utf8_domain_frame() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    encode_varint(ns_core::TargetType::Domain.id(), &mut payload)?;
    encode_bytes(&[0xff], &mut payload)?;
    encode_varint(53, &mut payload)?;
    encode_varint(15_000, &mut payload)?;
    encode_varint(3, &mut payload)?;
    encode_varint(0, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x08, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_open_bad_target_type_frame() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    encode_varint(9, &mut payload)?;
    encode_bytes(&[127, 0, 0, 1], &mut payload)?;
    encode_varint(53, &mut payload)?;
    encode_varint(15_000, &mut payload)?;
    encode_varint(3, &mut payload)?;
    encode_varint(0, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x08, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_open_noncanonical_target_type_frame() -> Result<Vec<u8>, Box<dyn std::error::Error>>
{
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    payload.extend_from_slice(&[0x40, ns_core::TargetType::Domain.id() as u8]);
    encode_string("dns.example.net", &mut payload)?;
    encode_varint(53, &mut payload)?;
    encode_varint(15_000, &mut payload)?;
    encode_varint(3, &mut payload)?;
    encode_varint(0, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x08, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_open_noncanonical_port_frame() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    encode_varint(ns_core::TargetType::Domain.id(), &mut payload)?;
    encode_string("dns.example.net", &mut payload)?;
    payload.extend_from_slice(&[0x40, 0x35]);
    encode_varint(15_000, &mut payload)?;
    encode_varint(3, &mut payload)?;
    encode_varint(0, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x08, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_ok_frame(
    flow_id: u64,
    transport_mode: u64,
    idle_timeout_ms: u64,
    max_payload: u64,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(flow_id, &mut payload)?;
    encode_varint(transport_mode, &mut payload)?;
    encode_varint(idle_timeout_ms, &mut payload)?;
    encode_varint(max_payload, &mut payload)?;
    encode_varint(0, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x09, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_datagram(
    flow_id: u64,
    flags: u64,
    payload: &[u8],
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut datagram = Vec::new();
    encode_varint(flow_id, &mut datagram)?;
    encode_varint(flags, &mut datagram)?;
    datagram.extend_from_slice(payload);
    Ok(datagram)
}

fn raw_udp_datagram_noncanonical_flow_id(payload: &[u8]) -> Vec<u8> {
    let mut datagram = vec![0x40, 0x07, 0x00];
    datagram.extend_from_slice(payload);
    datagram
}

fn raw_udp_datagram_noncanonical_flags(payload: &[u8]) -> Vec<u8> {
    let mut datagram = vec![0x07, 0x40, 0x00];
    datagram.extend_from_slice(payload);
    datagram
}

fn raw_udp_stream_packet_frame(
    declared_len: u64,
    payload: &[u8],
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut frame = Vec::new();
    encode_varint(0x45, &mut frame)?;
    encode_varint((payload.len() as u64) + 1, &mut frame)?;

    let mut body = Vec::new();
    encode_varint(declared_len, &mut body)?;
    body.extend_from_slice(payload);
    frame.extend(body);
    Ok(frame)
}

fn raw_udp_stream_packet_noncanonical_declared_len_frame(
    payload: &[u8],
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut frame = Vec::new();
    encode_varint(0x45, &mut frame)?;
    encode_varint((payload.len() as u64) + 2, &mut frame)?;
    frame.push(0x40);
    frame.push(
        u8::try_from(payload.len()).expect("non-canonical packet fixture payload should fit in u8"),
    );
    frame.extend_from_slice(payload);
    Ok(frame)
}

fn raw_udp_stream_close_frame(
    flow_id: u64,
    code: u64,
    message: &str,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(flow_id, &mut payload)?;
    encode_varint(code, &mut payload)?;
    encode_string(message, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x46, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_stream_close_noncanonical_code_frame(
    flow_id: u64,
    message: &str,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(flow_id, &mut payload)?;
    payload.extend_from_slice(&[0x40, 0x00]);
    encode_string(message, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x46, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_stream_close_noncanonical_flow_frame(
    code: u64,
    message: &str,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = vec![0x40, 0x07];
    encode_varint(code, &mut payload)?;
    encode_string(message, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x46, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_stream_close_noncanonical_message_len_frame(
    flow_id: u64,
    code: u64,
    message: &str,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(flow_id, &mut payload)?;
    encode_varint(code, &mut payload)?;
    payload.extend_from_slice(&[0x40, message.len() as u8]);
    payload.extend_from_slice(message.as_bytes());

    let mut frame = Vec::new();
    encode_varint(0x46, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_stream_close_bad_utf8_message_frame(
    flow_id: u64,
    code: u64,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(flow_id, &mut payload)?;
    encode_varint(code, &mut payload)?;
    encode_bytes(&[0xff], &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x46, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_close_frame(
    flow_id: u64,
    code: u64,
    message: &str,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(flow_id, &mut payload)?;
    encode_varint(code, &mut payload)?;
    encode_string(message, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x0A, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_close_noncanonical_code_frame(
    flow_id: u64,
    message: &str,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(flow_id, &mut payload)?;
    payload.extend_from_slice(&[0x40, 0x00]);
    encode_string(message, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x0A, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_close_noncanonical_flow_frame(
    code: u64,
    message: &str,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = vec![0x40, 0x07];
    encode_varint(code, &mut payload)?;
    encode_string(message, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x0A, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_close_noncanonical_message_len_frame(
    flow_id: u64,
    code: u64,
    message: &str,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(flow_id, &mut payload)?;
    encode_varint(code, &mut payload)?;
    payload.extend_from_slice(&[0x40, message.len() as u8]);
    payload.extend_from_slice(message.as_bytes());

    let mut frame = Vec::new();
    encode_varint(0x0A, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_ok_noncanonical_payload_frame(
    flow_id: u64,
    transport_mode: u64,
    idle_timeout_ms: u64,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(flow_id, &mut payload)?;
    encode_varint(transport_mode, &mut payload)?;
    encode_varint(idle_timeout_ms, &mut payload)?;
    payload.extend_from_slice(&[0x40, 0x00]);
    encode_varint(0, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x09, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_ok_noncanonical_flow_frame(
    transport_mode: u64,
    idle_timeout_ms: u64,
    max_payload: u64,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = vec![0x40, 0x07];
    encode_varint(transport_mode, &mut payload)?;
    encode_varint(idle_timeout_ms, &mut payload)?;
    encode_varint(max_payload, &mut payload)?;
    encode_varint(0, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x09, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_ok_noncanonical_timeout_frame(
    flow_id: u64,
    transport_mode: u64,
    max_payload: u64,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(flow_id, &mut payload)?;
    encode_varint(transport_mode, &mut payload)?;
    payload.extend_from_slice(&[0x80, 0x00, 0x3a, 0x98]);
    encode_varint(max_payload, &mut payload)?;
    encode_varint(0, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x09, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_ok_noncanonical_mode_frame(
    flow_id: u64,
    idle_timeout_ms: u64,
    max_payload: u64,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(flow_id, &mut payload)?;
    payload.extend_from_slice(&[0x40, 0x01]);
    encode_varint(idle_timeout_ms, &mut payload)?;
    encode_varint(max_payload, &mut payload)?;
    encode_varint(0, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x09, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_ok_bad_metadata_count_frame(
    flow_id: u64,
    transport_mode: u64,
    idle_timeout_ms: u64,
    max_payload: u64,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(flow_id, &mut payload)?;
    encode_varint(transport_mode, &mut payload)?;
    encode_varint(idle_timeout_ms, &mut payload)?;
    encode_varint(max_payload, &mut payload)?;
    encode_varint((MAX_METADATA_TLVS as u64) + 1, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x09, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_ok_noncanonical_metadata_count_frame(
    flow_id: u64,
    transport_mode: u64,
    idle_timeout_ms: u64,
    max_payload: u64,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(flow_id, &mut payload)?;
    encode_varint(transport_mode, &mut payload)?;
    encode_varint(idle_timeout_ms, &mut payload)?;
    encode_varint(max_payload, &mut payload)?;
    payload.extend_from_slice(&[0x40, 0x00]);

    let mut frame = Vec::new();
    encode_varint(0x09, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_ok_bad_metadata_len_frame(
    flow_id: u64,
    transport_mode: u64,
    idle_timeout_ms: u64,
    max_payload: u64,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(flow_id, &mut payload)?;
    encode_varint(transport_mode, &mut payload)?;
    encode_varint(idle_timeout_ms, &mut payload)?;
    encode_varint(max_payload, &mut payload)?;
    append_single_metadata_tlv_bad_len(&mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x09, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_ok_noncanonical_metadata_len_frame(
    flow_id: u64,
    transport_mode: u64,
    idle_timeout_ms: u64,
    max_payload: u64,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(flow_id, &mut payload)?;
    encode_varint(transport_mode, &mut payload)?;
    encode_varint(idle_timeout_ms, &mut payload)?;
    encode_varint(max_payload, &mut payload)?;
    append_single_metadata_tlv_noncanonical_len(&mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x09, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_ok_noncanonical_metadata_type_frame(
    flow_id: u64,
    transport_mode: u64,
    idle_timeout_ms: u64,
    max_payload: u64,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(flow_id, &mut payload)?;
    encode_varint(transport_mode, &mut payload)?;
    encode_varint(idle_timeout_ms, &mut payload)?;
    encode_varint(max_payload, &mut payload)?;
    append_single_metadata_tlv_noncanonical_type(&mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x09, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_flow_close_bad_utf8_message_frame(
    flow_id: u64,
    code: u64,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(flow_id, &mut payload)?;
    encode_varint(code, &mut payload)?;
    encode_bytes(&[0xff], &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x0A, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_stream_open_truncated_frame(
    flow_id: u64,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(flow_id, &mut payload)?;
    encode_varint(1, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x43, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_stream_open_bad_metadata_count_frame() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    encode_varint((MAX_METADATA_TLVS as u64) + 1, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x43, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_stream_open_noncanonical_metadata_count_frame()
-> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    payload.extend_from_slice(&[0x40, 0x00]);

    let mut frame = Vec::new();
    encode_varint(0x43, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_stream_open_bad_metadata_len_frame() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    append_single_metadata_tlv_bad_len(&mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x43, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_stream_open_noncanonical_metadata_len_frame()
-> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    append_single_metadata_tlv_noncanonical_len(&mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x43, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_stream_open_noncanonical_metadata_type_frame()
-> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    append_single_metadata_tlv_noncanonical_type(&mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x43, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_stream_open_noncanonical_flow_frame() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let payload = vec![0x40, 0x07, 0x00];
    let mut frame = Vec::new();
    encode_varint(0x43, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_stream_accept_bad_metadata_count_frame() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    encode_varint((MAX_METADATA_TLVS as u64) + 1, &mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x44, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_stream_accept_noncanonical_metadata_count_frame()
-> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    payload.extend_from_slice(&[0x40, 0x00]);

    let mut frame = Vec::new();
    encode_varint(0x44, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_stream_accept_bad_metadata_len_frame() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    append_single_metadata_tlv_bad_len(&mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x44, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_stream_accept_noncanonical_metadata_len_frame()
-> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    append_single_metadata_tlv_noncanonical_len(&mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x44, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_stream_accept_noncanonical_metadata_type_frame()
-> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut payload = Vec::new();
    encode_varint(7, &mut payload)?;
    append_single_metadata_tlv_noncanonical_type(&mut payload)?;

    let mut frame = Vec::new();
    encode_varint(0x44, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn raw_udp_stream_accept_noncanonical_flow_frame() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let payload = vec![0x40, 0x07, 0x00];
    let mut frame = Vec::new();
    encode_varint(0x44, &mut frame)?;
    encode_varint(payload.len() as u64, &mut frame)?;
    frame.extend(payload);
    Ok(frame)
}

fn encode_string(value: &str, out: &mut Vec<u8>) -> Result<(), Box<dyn std::error::Error>> {
    encode_varint(value.len() as u64, out)?;
    out.extend_from_slice(value.as_bytes());
    Ok(())
}

fn encode_bytes(value: &[u8], out: &mut Vec<u8>) -> Result<(), Box<dyn std::error::Error>> {
    encode_varint(value.len() as u64, out)?;
    out.extend_from_slice(value);
    Ok(())
}

fn append_single_metadata_tlv_bad_len(
    payload: &mut Vec<u8>,
) -> Result<(), Box<dyn std::error::Error>> {
    encode_varint(1, payload)?;
    encode_varint(1, payload)?;
    encode_varint(4, payload)?;
    payload.push(b'x');
    Ok(())
}

fn append_single_metadata_tlv_noncanonical_len(
    payload: &mut Vec<u8>,
) -> Result<(), Box<dyn std::error::Error>> {
    encode_varint(1, payload)?;
    encode_varint(1, payload)?;
    payload.extend_from_slice(&[0x40, 0x01]);
    payload.push(b'x');
    Ok(())
}

fn append_single_metadata_tlv_noncanonical_type(
    payload: &mut Vec<u8>,
) -> Result<(), Box<dyn std::error::Error>> {
    encode_varint(1, payload)?;
    payload.extend_from_slice(&[0x40, 0x01]);
    encode_varint(1, payload)?;
    payload.push(b'x');
    Ok(())
}

fn jwk_for_signing_key(kid: &str, signing_key: &SigningKey) -> Jwk {
    let x = base64::engine::general_purpose::URL_SAFE_NO_PAD
        .encode(signing_key.verifying_key().to_bytes());

    Jwk {
        common: CommonParameters {
            key_id: Some(kid.to_owned()),
            key_algorithm: Some(jsonwebtoken::jwk::KeyAlgorithm::EdDSA),
            ..Default::default()
        },
        algorithm: AlgorithmParameters::OctetKeyPair(OctetKeyPairParameters {
            key_type: OctetKeyPairType::OctetKeyPair,
            curve: jsonwebtoken::jwk::EllipticCurve::Ed25519,
            x,
        }),
    }
}

fn write_json(path: &Path, value: &serde_json::Value) -> Result<(), Box<dyn std::error::Error>> {
    write_text(path, &serde_json::to_string_pretty(value)?)
}

fn write_pretty_json<T: serde::Serialize>(
    path: &Path,
    value: &T,
) -> Result<(), Box<dyn std::error::Error>> {
    write_text(path, &serde_json::to_string_pretty(value)?)
}

fn write_text(path: &Path, contents: &str) -> Result<(), Box<dyn std::error::Error>> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(path, contents)?;
    Ok(())
}

fn to_hex(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        out.push_str(&format!("{byte:02x}"));
    }
    out
}
