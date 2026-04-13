use crate::types::{
    ClientHello, DatagramFlags, ErrorFrame, FlowFlags, Frame, FrameType, MetadataTlv, OpenFlags,
    Ping, Pong, ServerHello, SessionClose, StreamAccept, StreamOpen, StreamReject, TargetAddress,
    UdpDatagram, UdpFlowClose, UdpFlowOk, UdpFlowOpen, UdpStreamAccept, UdpStreamClose,
    UdpStreamOpen, UdpStreamPacket,
};
use ns_core::{
    CONTROL_FRAME_MAX_PAYLOAD, Capability, CarrierKind, CarrierProfileId, DatagramMode,
    DeviceBindingId, MAX_METADATA_TLVS, MAX_REQUESTED_CAPABILITIES, ManifestId, ProtocolErrorCode,
    SessionId, StatsMode, TargetType, TransportMode, ValidationError,
};
use std::net::{Ipv4Addr, Ipv6Addr};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum WireError {
    #[error("unsupported or invalid frame type {0:#x}")]
    UnknownFrameType(u64),
    #[error("payload ended unexpectedly")]
    Truncated,
    #[error("payload declared length exceeds available bytes")]
    LengthMismatch,
    #[error("frame payload exceeds v0.1 hard ceiling")]
    FrameTooLarge,
    #[error("value {0} used a non-canonical varint encoding")]
    NonCanonicalVarint(u64),
    #[error("value {0} does not fit the QUIC-style varint profile")]
    VarintOverflow(u64),
    #[error("UTF-8 field was not valid UTF-8")]
    InvalidUtf8,
    #[error("validation failed: {0}")]
    Validation(#[from] ValidationError),
}

pub struct FrameCodec;

impl FrameCodec {
    pub fn encode(frame: &Frame) -> Result<Vec<u8>, WireError> {
        let mut payload = Vec::new();
        match frame {
            Frame::ClientHello(value) => encode_client_hello(value, &mut payload)?,
            Frame::ServerHello(value) => encode_server_hello(value, &mut payload)?,
            Frame::Ping(value) => encode_ping(value, &mut payload)?,
            Frame::Pong(value) => encode_pong(value, &mut payload)?,
            Frame::Error(value) => encode_error(value, &mut payload)?,
            Frame::UdpFlowOpen(value) => encode_udp_flow_open(value, &mut payload)?,
            Frame::UdpFlowOk(value) => encode_udp_flow_ok(value, &mut payload)?,
            Frame::UdpFlowClose(value) => encode_udp_flow_close(value, &mut payload)?,
            Frame::SessionClose(value) => encode_session_close(value, &mut payload)?,
            Frame::StreamOpen(value) => encode_stream_open(value, &mut payload)?,
            Frame::StreamAccept(value) => encode_stream_accept(value, &mut payload)?,
            Frame::StreamReject(value) => encode_stream_reject(value, &mut payload)?,
            Frame::UdpStreamOpen(value) => encode_udp_stream_open(value, &mut payload)?,
            Frame::UdpStreamAccept(value) => encode_udp_stream_accept(value, &mut payload)?,
            Frame::UdpStreamPacket(value) => encode_udp_stream_packet(value, &mut payload)?,
            Frame::UdpStreamClose(value) => encode_udp_stream_close(value, &mut payload)?,
        }

        if payload.len() > CONTROL_FRAME_MAX_PAYLOAD {
            return Err(WireError::FrameTooLarge);
        }

        let mut encoded = Vec::new();
        encode_varint(frame.frame_type().id(), &mut encoded)?;
        encode_varint(payload.len() as u64, &mut encoded)?;
        encoded.extend(payload);
        Ok(encoded)
    }

    pub fn decode(input: &[u8]) -> Result<Frame, WireError> {
        let mut cursor = 0;
        let frame_type = decode_frame_type(input, &mut cursor)?;
        let payload_len = decode_varint(input, &mut cursor)? as usize;
        if payload_len > CONTROL_FRAME_MAX_PAYLOAD {
            return Err(WireError::FrameTooLarge);
        }
        let end = cursor
            .checked_add(payload_len)
            .ok_or(WireError::LengthMismatch)?;
        let payload = input.get(cursor..end).ok_or(WireError::LengthMismatch)?;
        let mut payload_cursor = 0;

        let frame = match frame_type {
            FrameType::ClientHello => {
                Frame::ClientHello(decode_client_hello(payload, &mut payload_cursor)?)
            }
            FrameType::ServerHello => {
                Frame::ServerHello(decode_server_hello(payload, &mut payload_cursor)?)
            }
            FrameType::Ping => Frame::Ping(decode_ping(payload, &mut payload_cursor)?),
            FrameType::Pong => Frame::Pong(decode_pong(payload, &mut payload_cursor)?),
            FrameType::Error => Frame::Error(decode_error(payload, &mut payload_cursor)?),
            FrameType::UdpFlowOpen => {
                Frame::UdpFlowOpen(decode_udp_flow_open(payload, &mut payload_cursor)?)
            }
            FrameType::UdpFlowOk => {
                Frame::UdpFlowOk(decode_udp_flow_ok(payload, &mut payload_cursor)?)
            }
            FrameType::UdpFlowClose => {
                Frame::UdpFlowClose(decode_udp_flow_close(payload, &mut payload_cursor)?)
            }
            FrameType::SessionClose => {
                Frame::SessionClose(decode_session_close(payload, &mut payload_cursor)?)
            }
            FrameType::StreamOpen => {
                Frame::StreamOpen(decode_stream_open(payload, &mut payload_cursor)?)
            }
            FrameType::StreamAccept => {
                Frame::StreamAccept(decode_stream_accept(payload, &mut payload_cursor)?)
            }
            FrameType::StreamReject => {
                Frame::StreamReject(decode_stream_reject(payload, &mut payload_cursor)?)
            }
            FrameType::UdpStreamOpen => {
                Frame::UdpStreamOpen(decode_udp_stream_open(payload, &mut payload_cursor)?)
            }
            FrameType::UdpStreamAccept => {
                Frame::UdpStreamAccept(decode_udp_stream_accept(payload, &mut payload_cursor)?)
            }
            FrameType::UdpStreamPacket => {
                Frame::UdpStreamPacket(decode_udp_stream_packet(payload, &mut payload_cursor)?)
            }
            FrameType::UdpStreamClose => {
                Frame::UdpStreamClose(decode_udp_stream_close(payload, &mut payload_cursor)?)
            }
        };

        if payload_cursor != payload.len() {
            return Err(WireError::LengthMismatch);
        }

        Ok(frame)
    }
}

pub fn encode_varint(value: u64, output: &mut Vec<u8>) -> Result<(), WireError> {
    match value {
        0..=63 => output.push(value as u8),
        64..=16_383 => {
            let encoded = (value as u16) | (0b01 << 14);
            output.extend_from_slice(&encoded.to_be_bytes());
        }
        16_384..=1_073_741_823 => {
            let encoded = (value as u32) | (0b10 << 30);
            output.extend_from_slice(&encoded.to_be_bytes());
        }
        1_073_741_824..=4_611_686_018_427_387_903 => {
            let encoded = value | (0b11_u64 << 62);
            output.extend_from_slice(&encoded.to_be_bytes());
        }
        _ => return Err(WireError::VarintOverflow(value)),
    }
    Ok(())
}

pub fn decode_varint(input: &[u8], cursor: &mut usize) -> Result<u64, WireError> {
    let first = *input.get(*cursor).ok_or(WireError::Truncated)?;
    let len = match first >> 6 {
        0 => 1,
        1 => 2,
        2 => 4,
        _ => 8,
    };
    let end = cursor.checked_add(len).ok_or(WireError::Truncated)?;
    let bytes = input.get(*cursor..end).ok_or(WireError::Truncated)?;
    *cursor = end;

    let value = match len {
        1 => u64::from(bytes[0] & 0b0011_1111),
        2 => u64::from(u16::from_be_bytes([bytes[0], bytes[1]]) & 0x3fff),
        4 => u64::from(u32::from_be_bytes([bytes[0], bytes[1], bytes[2], bytes[3]]) & 0x3fff_ffff),
        _ => {
            u64::from_be_bytes([
                bytes[0], bytes[1], bytes[2], bytes[3], bytes[4], bytes[5], bytes[6], bytes[7],
            ]) & 0x3fff_ffff_ffff_ffff
        }
    };

    let expected_len = match value {
        0..=63 => 1,
        64..=16_383 => 2,
        16_384..=1_073_741_823 => 4,
        _ => 8,
    };
    if expected_len != len {
        return Err(WireError::NonCanonicalVarint(value));
    }

    Ok(value)
}

fn decode_frame_type(input: &[u8], cursor: &mut usize) -> Result<FrameType, WireError> {
    match decode_varint(input, cursor)? {
        0x01 => Ok(FrameType::ClientHello),
        0x02 => Ok(FrameType::ServerHello),
        0x03 => Ok(FrameType::Ping),
        0x04 => Ok(FrameType::Pong),
        0x05 => Ok(FrameType::Error),
        0x08 => Ok(FrameType::UdpFlowOpen),
        0x09 => Ok(FrameType::UdpFlowOk),
        0x0A => Ok(FrameType::UdpFlowClose),
        0x0E => Ok(FrameType::SessionClose),
        0x40 => Ok(FrameType::StreamOpen),
        0x41 => Ok(FrameType::StreamAccept),
        0x42 => Ok(FrameType::StreamReject),
        0x43 => Ok(FrameType::UdpStreamOpen),
        0x44 => Ok(FrameType::UdpStreamAccept),
        0x45 => Ok(FrameType::UdpStreamPacket),
        0x46 => Ok(FrameType::UdpStreamClose),
        other => Err(WireError::UnknownFrameType(other)),
    }
}

fn encode_client_hello(frame: &ClientHello, out: &mut Vec<u8>) -> Result<(), WireError> {
    if frame.min_version > frame.max_version {
        return Err(WireError::Validation(ValidationError::Zero {
            field: "version_range",
        }));
    }
    encode_varint(frame.min_version, out)?;
    encode_varint(frame.max_version, out)?;
    out.extend_from_slice(&frame.client_nonce);
    encode_capabilities(&frame.requested_capabilities, out)?;
    encode_varint(frame.carrier_kind.id(), out)?;
    encode_string(frame.carrier_profile_id.as_str(), out)?;
    encode_string(frame.manifest_id.as_str(), out)?;
    encode_string(frame.device_binding_id.as_str(), out)?;
    encode_varint(frame.requested_idle_timeout_ms, out)?;
    encode_varint(frame.requested_max_udp_payload, out)?;
    encode_bytes(&frame.token, out)?;
    encode_metadata(&frame.client_metadata, out)?;
    Ok(())
}

fn decode_client_hello(input: &[u8], cursor: &mut usize) -> Result<ClientHello, WireError> {
    let min_version = decode_varint(input, cursor)?;
    let max_version = decode_varint(input, cursor)?;
    if min_version > max_version {
        return Err(WireError::Validation(ValidationError::Zero {
            field: "version_range",
        }));
    }
    let client_nonce = decode_fixed::<32>(input, cursor)?;
    let requested_capabilities = decode_capabilities(input, cursor)?;
    let carrier_kind = CarrierKind::from_id(decode_varint(input, cursor)?)?;
    let carrier_profile_id = CarrierProfileId::new(decode_string(input, cursor)?)?;
    let manifest_id = ManifestId::new(decode_string(input, cursor)?)?;
    let device_binding_id = DeviceBindingId::new(decode_string(input, cursor)?)?;
    let requested_idle_timeout_ms = decode_varint(input, cursor)?;
    let requested_max_udp_payload = decode_varint(input, cursor)?;
    let token = decode_bytes(input, cursor)?;
    let client_metadata = decode_metadata(input, cursor)?;
    if token.is_empty() {
        return Err(WireError::Validation(ValidationError::Empty {
            field: "token",
        }));
    }
    Ok(ClientHello {
        min_version,
        max_version,
        client_nonce,
        requested_capabilities,
        carrier_kind,
        carrier_profile_id,
        manifest_id,
        device_binding_id,
        requested_idle_timeout_ms,
        requested_max_udp_payload,
        token,
        client_metadata,
    })
}

fn encode_server_hello(frame: &ServerHello, out: &mut Vec<u8>) -> Result<(), WireError> {
    encode_varint(frame.selected_version, out)?;
    out.extend_from_slice(frame.session_id.as_bytes());
    out.extend_from_slice(&frame.server_nonce);
    encode_capabilities(&frame.selected_capabilities, out)?;
    for value in [
        frame.policy_epoch,
        frame.effective_idle_timeout_ms,
        frame.session_lifetime_ms,
        frame.max_concurrent_relay_streams,
        frame.max_udp_flows,
        frame.effective_max_udp_payload,
    ] {
        encode_varint(value, out)?;
    }
    encode_varint(frame.datagram_mode.id(), out)?;
    encode_varint(frame.stats_mode.id(), out)?;
    encode_metadata(&frame.server_metadata, out)?;
    Ok(())
}

fn decode_server_hello(input: &[u8], cursor: &mut usize) -> Result<ServerHello, WireError> {
    let selected_version = decode_varint(input, cursor)?;
    let session_id = SessionId::from_slice(&decode_fixed::<16>(input, cursor)?)?;
    let server_nonce = decode_fixed::<32>(input, cursor)?;
    let selected_capabilities = decode_capabilities(input, cursor)?;
    let policy_epoch = decode_varint(input, cursor)?;
    let effective_idle_timeout_ms = decode_varint(input, cursor)?;
    let session_lifetime_ms = decode_varint(input, cursor)?;
    let max_concurrent_relay_streams = decode_varint(input, cursor)?;
    let max_udp_flows = decode_varint(input, cursor)?;
    let effective_max_udp_payload = decode_varint(input, cursor)?;
    let datagram_mode = DatagramMode::from_id(decode_varint(input, cursor)?)?;
    let stats_mode = StatsMode::from_id(decode_varint(input, cursor)?)?;
    let server_metadata = decode_metadata(input, cursor)?;
    if [
        effective_idle_timeout_ms,
        session_lifetime_ms,
        max_concurrent_relay_streams,
        max_udp_flows,
        effective_max_udp_payload,
    ]
    .into_iter()
    .any(|value| value == 0)
    {
        return Err(WireError::Validation(ValidationError::Zero {
            field: "server_limits",
        }));
    }
    Ok(ServerHello {
        selected_version,
        session_id,
        server_nonce,
        selected_capabilities,
        policy_epoch,
        effective_idle_timeout_ms,
        session_lifetime_ms,
        max_concurrent_relay_streams,
        max_udp_flows,
        effective_max_udp_payload,
        datagram_mode,
        stats_mode,
        server_metadata,
    })
}

fn encode_ping(frame: &Ping, out: &mut Vec<u8>) -> Result<(), WireError> {
    encode_varint(frame.ping_id, out)?;
    encode_varint(frame.timestamp, out)?;
    Ok(())
}

fn decode_ping(input: &[u8], cursor: &mut usize) -> Result<Ping, WireError> {
    Ok(Ping {
        ping_id: decode_varint(input, cursor)?,
        timestamp: decode_varint(input, cursor)?,
    })
}

fn encode_pong(frame: &Pong, out: &mut Vec<u8>) -> Result<(), WireError> {
    encode_varint(frame.ping_id, out)?;
    encode_varint(frame.timestamp, out)?;
    Ok(())
}

fn decode_pong(input: &[u8], cursor: &mut usize) -> Result<Pong, WireError> {
    Ok(Pong {
        ping_id: decode_varint(input, cursor)?,
        timestamp: decode_varint(input, cursor)?,
    })
}

fn encode_error(frame: &ErrorFrame, out: &mut Vec<u8>) -> Result<(), WireError> {
    encode_varint(frame.code.id(), out)?;
    encode_string(&frame.message, out)?;
    encode_bool(frame.is_terminal, out);
    encode_metadata(&frame.details, out)?;
    Ok(())
}

fn decode_error(input: &[u8], cursor: &mut usize) -> Result<ErrorFrame, WireError> {
    Ok(ErrorFrame {
        code: ProtocolErrorCode::from_id(decode_varint(input, cursor)?)?,
        message: decode_string(input, cursor)?,
        is_terminal: decode_bool(input, cursor)?,
        details: decode_metadata(input, cursor)?,
    })
}

fn encode_session_close(frame: &SessionClose, out: &mut Vec<u8>) -> Result<(), WireError> {
    encode_varint(frame.code.id(), out)?;
    encode_string(&frame.message, out)?;
    Ok(())
}

fn decode_session_close(input: &[u8], cursor: &mut usize) -> Result<SessionClose, WireError> {
    Ok(SessionClose {
        code: ProtocolErrorCode::from_id(decode_varint(input, cursor)?)?,
        message: decode_string(input, cursor)?,
    })
}

fn encode_udp_flow_open(frame: &UdpFlowOpen, out: &mut Vec<u8>) -> Result<(), WireError> {
    encode_varint(frame.flow_id, out)?;
    encode_target_address(&frame.target, out)?;
    encode_varint(u64::from(frame.target_port), out)?;
    encode_varint(frame.idle_timeout_ms, out)?;
    encode_varint(frame.flags.raw(), out)?;
    encode_metadata(&frame.metadata, out)?;
    Ok(())
}

fn decode_udp_flow_open(input: &[u8], cursor: &mut usize) -> Result<UdpFlowOpen, WireError> {
    Ok(UdpFlowOpen {
        flow_id: decode_varint(input, cursor)?,
        target: decode_target_address(input, cursor)?,
        target_port: decode_port(input, cursor)?,
        idle_timeout_ms: decode_varint(input, cursor)?,
        flags: FlowFlags::new(decode_varint(input, cursor)?).map_err(|value| {
            WireError::Validation(ValidationError::ReservedRegistryValue { value })
        })?,
        metadata: decode_metadata(input, cursor)?,
    })
}

fn encode_udp_flow_ok(frame: &UdpFlowOk, out: &mut Vec<u8>) -> Result<(), WireError> {
    encode_varint(frame.flow_id, out)?;
    encode_varint(frame.transport_mode.id(), out)?;
    encode_varint(frame.effective_idle_timeout_ms, out)?;
    encode_varint(frame.effective_max_payload, out)?;
    encode_metadata(&frame.metadata, out)?;
    Ok(())
}

fn decode_udp_flow_ok(input: &[u8], cursor: &mut usize) -> Result<UdpFlowOk, WireError> {
    let flow_id = decode_varint(input, cursor)?;
    let transport_mode = TransportMode::from_id(decode_varint(input, cursor)?)?;
    let effective_idle_timeout_ms = decode_varint(input, cursor)?;
    let effective_max_payload = decode_varint(input, cursor)?;
    if effective_idle_timeout_ms == 0 || effective_max_payload == 0 {
        return Err(WireError::Validation(ValidationError::Zero {
            field: "udp_flow_ok_limits",
        }));
    }
    Ok(UdpFlowOk {
        flow_id,
        transport_mode,
        effective_idle_timeout_ms,
        effective_max_payload,
        metadata: decode_metadata(input, cursor)?,
    })
}

fn encode_udp_flow_close(frame: &UdpFlowClose, out: &mut Vec<u8>) -> Result<(), WireError> {
    encode_varint(frame.flow_id, out)?;
    encode_varint(frame.code.id(), out)?;
    encode_string(&frame.message, out)?;
    Ok(())
}

fn decode_udp_flow_close(input: &[u8], cursor: &mut usize) -> Result<UdpFlowClose, WireError> {
    Ok(UdpFlowClose {
        flow_id: decode_varint(input, cursor)?,
        code: ProtocolErrorCode::from_id(decode_varint(input, cursor)?)?,
        message: decode_string(input, cursor)?,
    })
}

fn encode_stream_open(frame: &StreamOpen, out: &mut Vec<u8>) -> Result<(), WireError> {
    encode_varint(frame.relay_id, out)?;
    encode_target_address(&frame.target, out)?;
    encode_varint(u64::from(frame.target_port), out)?;
    encode_varint(frame.flags.raw(), out)?;
    encode_metadata(&frame.metadata, out)?;
    Ok(())
}

fn decode_stream_open(input: &[u8], cursor: &mut usize) -> Result<StreamOpen, WireError> {
    Ok(StreamOpen {
        relay_id: decode_varint(input, cursor)?,
        target: decode_target_address(input, cursor)?,
        target_port: decode_port(input, cursor)?,
        flags: OpenFlags::new(decode_varint(input, cursor)?).map_err(|value| {
            WireError::Validation(ValidationError::ReservedRegistryValue { value })
        })?,
        metadata: decode_metadata(input, cursor)?,
    })
}

fn encode_stream_accept(frame: &StreamAccept, out: &mut Vec<u8>) -> Result<(), WireError> {
    encode_varint(frame.relay_id, out)?;
    encode_target_address(&frame.bind_address, out)?;
    encode_varint(u64::from(frame.bind_port), out)?;
    encode_metadata(&frame.metadata, out)?;
    Ok(())
}

fn decode_stream_accept(input: &[u8], cursor: &mut usize) -> Result<StreamAccept, WireError> {
    Ok(StreamAccept {
        relay_id: decode_varint(input, cursor)?,
        bind_address: decode_target_address(input, cursor)?,
        bind_port: decode_port(input, cursor)?,
        metadata: decode_metadata(input, cursor)?,
    })
}

fn encode_stream_reject(frame: &StreamReject, out: &mut Vec<u8>) -> Result<(), WireError> {
    encode_varint(frame.relay_id, out)?;
    encode_varint(frame.code.id(), out)?;
    encode_bool(frame.retryable, out);
    encode_string(&frame.message, out)?;
    encode_metadata(&frame.metadata, out)?;
    Ok(())
}

fn decode_stream_reject(input: &[u8], cursor: &mut usize) -> Result<StreamReject, WireError> {
    Ok(StreamReject {
        relay_id: decode_varint(input, cursor)?,
        code: ProtocolErrorCode::from_id(decode_varint(input, cursor)?)?,
        retryable: decode_bool(input, cursor)?,
        message: decode_string(input, cursor)?,
        metadata: decode_metadata(input, cursor)?,
    })
}

fn encode_udp_stream_open(frame: &UdpStreamOpen, out: &mut Vec<u8>) -> Result<(), WireError> {
    encode_varint(frame.flow_id, out)?;
    encode_metadata(&frame.metadata, out)?;
    Ok(())
}

fn decode_udp_stream_open(input: &[u8], cursor: &mut usize) -> Result<UdpStreamOpen, WireError> {
    Ok(UdpStreamOpen {
        flow_id: decode_varint(input, cursor)?,
        metadata: decode_metadata(input, cursor)?,
    })
}

fn encode_udp_stream_accept(frame: &UdpStreamAccept, out: &mut Vec<u8>) -> Result<(), WireError> {
    encode_varint(frame.flow_id, out)?;
    encode_metadata(&frame.metadata, out)?;
    Ok(())
}

fn decode_udp_stream_accept(
    input: &[u8],
    cursor: &mut usize,
) -> Result<UdpStreamAccept, WireError> {
    Ok(UdpStreamAccept {
        flow_id: decode_varint(input, cursor)?,
        metadata: decode_metadata(input, cursor)?,
    })
}

fn encode_udp_stream_packet(frame: &UdpStreamPacket, out: &mut Vec<u8>) -> Result<(), WireError> {
    encode_bytes(&frame.payload, out)
}

fn decode_udp_stream_packet(
    input: &[u8],
    cursor: &mut usize,
) -> Result<UdpStreamPacket, WireError> {
    Ok(UdpStreamPacket {
        payload: decode_bytes(input, cursor)?,
    })
}

fn encode_udp_stream_close(frame: &UdpStreamClose, out: &mut Vec<u8>) -> Result<(), WireError> {
    encode_varint(frame.flow_id, out)?;
    encode_varint(frame.code.id(), out)?;
    encode_string(&frame.message, out)?;
    Ok(())
}

fn decode_udp_stream_close(input: &[u8], cursor: &mut usize) -> Result<UdpStreamClose, WireError> {
    Ok(UdpStreamClose {
        flow_id: decode_varint(input, cursor)?,
        code: ProtocolErrorCode::from_id(decode_varint(input, cursor)?)?,
        message: decode_string(input, cursor)?,
    })
}

fn encode_target_address(address: &TargetAddress, out: &mut Vec<u8>) -> Result<(), WireError> {
    match address {
        TargetAddress::Domain(host) => {
            if host.is_empty() {
                return Err(WireError::Validation(ValidationError::Empty {
                    field: "target_domain",
                }));
            }
            encode_varint(TargetType::Domain.id(), out)?;
            encode_string(host, out)?;
        }
        TargetAddress::Ipv4(bytes) => {
            encode_varint(TargetType::Ipv4.id(), out)?;
            encode_bytes(bytes, out)?;
        }
        TargetAddress::Ipv6(bytes) => {
            encode_varint(TargetType::Ipv6.id(), out)?;
            encode_bytes(bytes, out)?;
        }
    }
    Ok(())
}

fn decode_target_address(input: &[u8], cursor: &mut usize) -> Result<TargetAddress, WireError> {
    match TargetType::from_id(decode_varint(input, cursor)?)? {
        TargetType::Domain => {
            let host = decode_string(input, cursor)?;
            if host.is_empty() {
                return Err(WireError::Validation(ValidationError::Empty {
                    field: "target_domain",
                }));
            }
            Ok(TargetAddress::Domain(host))
        }
        TargetType::Ipv4 => {
            let bytes = decode_bytes(input, cursor)?;
            let parsed = <[u8; 4]>::try_from(bytes.as_slice()).map_err(|_| {
                WireError::Validation(ValidationError::Length {
                    field: "ipv4_address",
                    min: 4,
                    max: 4,
                })
            })?;
            Ok(TargetAddress::Ipv4(parsed))
        }
        TargetType::Ipv6 => {
            let bytes = decode_bytes(input, cursor)?;
            let parsed = <[u8; 16]>::try_from(bytes.as_slice()).map_err(|_| {
                WireError::Validation(ValidationError::Length {
                    field: "ipv6_address",
                    min: 16,
                    max: 16,
                })
            })?;
            Ok(TargetAddress::Ipv6(parsed))
        }
    }
}

fn encode_capabilities(values: &[Capability], out: &mut Vec<u8>) -> Result<(), WireError> {
    if values.len() > MAX_REQUESTED_CAPABILITIES {
        return Err(WireError::Validation(ValidationError::Length {
            field: "requested_capabilities",
            min: 1,
            max: MAX_REQUESTED_CAPABILITIES,
        }));
    }
    encode_varint(values.len() as u64, out)?;
    for value in values {
        encode_varint(value.id(), out)?;
    }
    Ok(())
}

fn decode_capabilities(input: &[u8], cursor: &mut usize) -> Result<Vec<Capability>, WireError> {
    let count = decode_varint(input, cursor)? as usize;
    if count > MAX_REQUESTED_CAPABILITIES {
        return Err(WireError::Validation(ValidationError::Length {
            field: "requested_capabilities",
            min: 1,
            max: MAX_REQUESTED_CAPABILITIES,
        }));
    }
    let mut values = Vec::with_capacity(count);
    for _ in 0..count {
        values.push(Capability::from_id(decode_varint(input, cursor)?)?);
    }
    Ok(values)
}

fn encode_metadata(values: &[MetadataTlv], out: &mut Vec<u8>) -> Result<(), WireError> {
    if values.len() > MAX_METADATA_TLVS {
        return Err(WireError::Validation(ValidationError::Length {
            field: "metadata",
            min: 0,
            max: MAX_METADATA_TLVS,
        }));
    }
    encode_varint(values.len() as u64, out)?;
    for value in values {
        encode_varint(value.kind, out)?;
        encode_bytes(&value.value, out)?;
    }
    Ok(())
}

fn decode_metadata(input: &[u8], cursor: &mut usize) -> Result<Vec<MetadataTlv>, WireError> {
    let count = decode_varint(input, cursor)? as usize;
    if count > MAX_METADATA_TLVS {
        return Err(WireError::Validation(ValidationError::Length {
            field: "metadata",
            min: 0,
            max: MAX_METADATA_TLVS,
        }));
    }
    let mut values = Vec::with_capacity(count);
    for _ in 0..count {
        values.push(MetadataTlv {
            kind: decode_varint(input, cursor)?,
            value: decode_bytes(input, cursor)?,
        });
    }
    Ok(values)
}

fn encode_bool(value: bool, out: &mut Vec<u8>) {
    out.push(u8::from(value));
}

fn decode_bool(input: &[u8], cursor: &mut usize) -> Result<bool, WireError> {
    let value = *input.get(*cursor).ok_or(WireError::Truncated)?;
    *cursor += 1;
    match value {
        0 => Ok(false),
        1 => Ok(true),
        other => Err(WireError::Validation(
            ValidationError::UnknownRegistryValue {
                value: u64::from(other),
            },
        )),
    }
}

fn encode_string(value: &str, out: &mut Vec<u8>) -> Result<(), WireError> {
    encode_bytes(value.as_bytes(), out)
}

fn decode_string(input: &[u8], cursor: &mut usize) -> Result<String, WireError> {
    String::from_utf8(decode_bytes(input, cursor)?).map_err(|_| WireError::InvalidUtf8)
}

fn encode_bytes(value: &[u8], out: &mut Vec<u8>) -> Result<(), WireError> {
    encode_varint(value.len() as u64, out)?;
    out.extend_from_slice(value);
    Ok(())
}

fn decode_bytes(input: &[u8], cursor: &mut usize) -> Result<Vec<u8>, WireError> {
    let len = decode_varint(input, cursor)? as usize;
    let end = cursor.checked_add(len).ok_or(WireError::Truncated)?;
    let value = input.get(*cursor..end).ok_or(WireError::Truncated)?;
    *cursor = end;
    Ok(value.to_vec())
}

fn decode_fixed<const N: usize>(input: &[u8], cursor: &mut usize) -> Result<[u8; N], WireError> {
    let end = cursor.checked_add(N).ok_or(WireError::Truncated)?;
    let value = input.get(*cursor..end).ok_or(WireError::Truncated)?;
    *cursor = end;
    value.try_into().map_err(|_| WireError::Truncated)
}

fn decode_port(input: &[u8], cursor: &mut usize) -> Result<u16, WireError> {
    let value = decode_varint(input, cursor)?;
    let port = u16::try_from(value).map_err(|_| {
        WireError::Validation(ValidationError::Length {
            field: "port",
            min: 1,
            max: 65_535,
        })
    })?;
    if port == 0 {
        return Err(WireError::Validation(ValidationError::Zero {
            field: "port",
        }));
    }
    Ok(port)
}

pub fn encode_udp_datagram(datagram: &UdpDatagram) -> Result<Vec<u8>, WireError> {
    let mut encoded = Vec::new();
    encode_varint(datagram.flow_id, &mut encoded)?;
    encode_varint(datagram.flags.raw(), &mut encoded)?;
    encoded.extend_from_slice(&datagram.payload);
    Ok(encoded)
}

pub fn decode_udp_datagram(input: &[u8]) -> Result<UdpDatagram, WireError> {
    let mut cursor = 0;
    let flow_id = decode_varint(input, &mut cursor)?;
    let flags = DatagramFlags::new(decode_varint(input, &mut cursor)?)
        .map_err(|value| WireError::Validation(ValidationError::ReservedRegistryValue { value }))?;
    let payload = input
        .get(cursor..)
        .ok_or(WireError::LengthMismatch)?
        .to_vec();
    Ok(UdpDatagram {
        flow_id,
        flags,
        payload,
    })
}

impl TargetAddress {
    pub fn describe(&self) -> String {
        match self {
            Self::Domain(host) => host.clone(),
            Self::Ipv4(bytes) => Ipv4Addr::from(*bytes).to_string(),
            Self::Ipv6(bytes) => Ipv6Addr::from(*bytes).to_string(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_client_hello() -> ClientHello {
        ClientHello {
            min_version: 1,
            max_version: 1,
            client_nonce: [7_u8; 32],
            requested_capabilities: vec![
                Capability::TcpRelay,
                Capability::UdpRelay,
                Capability::QuicDatagram,
            ],
            carrier_kind: CarrierKind::H3,
            carrier_profile_id: CarrierProfileId::new("carrier-primary")
                .expect("fixture carrier profile id should be valid"),
            manifest_id: ManifestId::new("man-2026-04-01-001")
                .expect("fixture manifest id should be valid"),
            device_binding_id: DeviceBindingId::new("device-bind-001")
                .expect("fixture device binding id should be valid"),
            requested_idle_timeout_ms: 30_000,
            requested_max_udp_payload: 1_200,
            token: b"session-token".to_vec(),
            client_metadata: vec![MetadataTlv {
                kind: 1,
                value: b"client".to_vec(),
            }],
        }
    }

    #[test]
    fn varint_round_trips_boundary_values() {
        for value in [0_u64, 63, 64, 16_383, 16_384, 1_073_741_823] {
            let mut encoded = Vec::new();
            encode_varint(value, &mut encoded).expect("boundary varint should encode");
            let mut cursor = 0;
            assert_eq!(
                decode_varint(&encoded, &mut cursor).expect("boundary varint should decode"),
                value
            );
            assert_eq!(cursor, encoded.len());
        }
    }

    #[test]
    fn non_canonical_varints_are_rejected() {
        let encoded = [0x40_u8, 0x01];
        let mut cursor = 0;

        assert!(matches!(
            decode_varint(&encoded, &mut cursor),
            Err(WireError::NonCanonicalVarint(1))
        ));
    }

    #[test]
    fn client_hello_round_trips() {
        let frame = Frame::ClientHello(sample_client_hello());
        let encoded = FrameCodec::encode(&frame).expect("fixture frame should encode");
        let decoded = FrameCodec::decode(&encoded).expect("fixture frame should decode");
        assert_eq!(decoded, frame);
    }

    #[test]
    fn reserved_stream_flag_bits_are_rejected() {
        let mut payload = Vec::new();
        encode_varint(1, &mut payload).expect("relay id should encode");
        encode_varint(TargetType::Domain.id(), &mut payload).expect("target type should encode");
        encode_string("example.com", &mut payload).expect("hostname should encode");
        encode_varint(443, &mut payload).expect("port should encode");
        encode_varint(1 << 4, &mut payload).expect("flags should encode");
        encode_varint(0, &mut payload).expect("metadata count should encode");

        let mut encoded = Vec::new();
        encode_varint(FrameType::StreamOpen.id(), &mut encoded).expect("frame type should encode");
        encode_varint(payload.len() as u64, &mut encoded).expect("payload length should encode");
        encoded.extend(payload);

        assert!(matches!(
            FrameCodec::decode(&encoded),
            Err(WireError::Validation(
                ValidationError::ReservedRegistryValue { .. }
            ))
        ));
    }

    #[test]
    fn truncated_envelope_is_rejected() {
        let encoded = vec![FrameType::Ping.id() as u8, 0b0100_0001];
        assert!(matches!(
            FrameCodec::decode(&encoded),
            Err(WireError::Truncated)
        ));
    }
}
