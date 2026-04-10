//! Binary frame codec for the Beep session core.
//!
//! Wire format:
//! ```text
//! Frame {
//!   frame_type: varint,     // QUIC-style variable-length integer
//!   flags:      u8,         // 8 flag bits (all reserved in v1)
//!   length:     varint,     // payload length in bytes
//!   payload:    [u8; length],
//! }
//! ```
//!
//! # Safety rules
//! - Unknown critical frame types (even `frame_type`) terminate the session.
//! - Unknown ignorable frame types (odd `frame_type`) are skipped.
//! - Payload length is validated against [`MAX_FRAME_PAYLOAD`].
//! - Decode never advances a buffer cursor on failure.

use beep_core_types::FrameType;

use crate::varint;

/// Maximum allowed frame payload size (16 MiB).
///
/// This prevents memory exhaustion from malformed or malicious frames.
/// Real session traffic should use much smaller frames; this is a safety cap.
pub const MAX_FRAME_PAYLOAD: usize = 16 * 1024 * 1024;

/// A raw, unparsed Beep frame.
///
/// The `payload` contains the frame-type-specific data that will be
/// interpreted by higher-level handlers (handshake, session, stream, etc.).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RawFrame {
    pub frame_type: FrameType,
    pub flags: u8,
    pub payload: Vec<u8>,
}

/// Errors from frame codec operations.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum CodecError {
    /// Not enough data to decode the frame. Try again with more bytes.
    #[error("incomplete frame: need more data")]
    Incomplete,

    /// Varint decoding failed.
    #[error("varint error: {0}")]
    Varint(#[from] varint::VarintError),

    /// Frame payload exceeds the maximum allowed size.
    #[error("payload too large: {len} bytes exceeds maximum {MAX_FRAME_PAYLOAD}")]
    PayloadTooLarge { len: u64 },

    /// Varint for frame type exceeds maximum varint value.
    #[error("frame type value too large for encoding")]
    FrameTypeTooLarge,
}

/// Encode a frame into `buf`.
///
/// Returns the total number of bytes written.
pub fn encode_frame(frame: &RawFrame, buf: &mut Vec<u8>) -> Result<usize, CodecError> {
    let start_len = buf.len();

    // frame_type as varint
    varint::encode(frame.frame_type.as_u64(), buf)?;

    // flags as u8
    buf.push(frame.flags);

    // length as varint
    let payload_len = frame.payload.len() as u64;
    varint::encode(payload_len, buf)?;

    // payload
    buf.extend_from_slice(&frame.payload);

    Ok(buf.len() - start_len)
}

/// Attempt to decode one frame from `input`.
///
/// On success, returns `(frame, bytes_consumed)`.
/// On `Err(CodecError::Incomplete)`, the caller should buffer more data and retry.
/// On other errors, the frame is malformed and the session should be terminated.
///
/// This function never modifies `input`; the caller advances their own cursor.
pub fn decode_frame(input: &[u8]) -> Result<(RawFrame, usize), CodecError> {
    let mut offset = 0;

    // frame_type
    let (frame_type_val, n) = varint::decode(&input[offset..]).map_err(underflow_to_incomplete)?;
    offset += n;

    // flags
    if offset >= input.len() {
        return Err(CodecError::Incomplete);
    }
    let flags = input[offset];
    offset += 1;

    // length
    let (payload_len, n) = varint::decode(&input[offset..]).map_err(underflow_to_incomplete)?;
    offset += n;

    // Validate payload length
    if payload_len > MAX_FRAME_PAYLOAD as u64 {
        return Err(CodecError::PayloadTooLarge { len: payload_len });
    }
    let payload_len = payload_len as usize;

    // payload
    if input.len() - offset < payload_len {
        return Err(CodecError::Incomplete);
    }
    let payload = input[offset..offset + payload_len].to_vec();
    offset += payload_len;

    let frame = RawFrame {
        frame_type: FrameType(frame_type_val),
        flags,
        payload,
    };

    Ok((frame, offset))
}

/// Convert varint BufferUnderflow into codec Incomplete.
fn underflow_to_incomplete(err: varint::VarintError) -> CodecError {
    match err {
        varint::VarintError::BufferUnderflow { .. } => CodecError::Incomplete,
        other => CodecError::Varint(other),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip_empty_payload() {
        let frame = RawFrame {
            frame_type: FrameType::CLIENT_INIT,
            flags: 0,
            payload: vec![],
        };
        let mut buf = Vec::new();
        let written = encode_frame(&frame, &mut buf).unwrap();
        assert!(written > 0);

        let (decoded, consumed) = decode_frame(&buf).unwrap();
        assert_eq!(consumed, written);
        assert_eq!(decoded, frame);
    }

    #[test]
    fn roundtrip_with_payload() {
        let payload = vec![0xDE, 0xAD, 0xBE, 0xEF, 0x01, 0x02, 0x03];
        let frame = RawFrame {
            frame_type: FrameType::SERVER_INIT,
            flags: 0x00,
            payload: payload.clone(),
        };
        let mut buf = Vec::new();
        encode_frame(&frame, &mut buf).unwrap();

        let (decoded, _) = decode_frame(&buf).unwrap();
        assert_eq!(decoded.frame_type, FrameType::SERVER_INIT);
        assert_eq!(decoded.flags, 0x00);
        assert_eq!(decoded.payload, payload);
    }

    #[test]
    fn roundtrip_with_flags() {
        let frame = RawFrame {
            frame_type: FrameType::STREAM_OPEN,
            flags: 0b1010_0101,
            payload: vec![0x42],
        };
        let mut buf = Vec::new();
        encode_frame(&frame, &mut buf).unwrap();

        let (decoded, _) = decode_frame(&buf).unwrap();
        assert_eq!(decoded.flags, 0b1010_0101);
    }

    #[test]
    fn roundtrip_ignorable_frame() {
        let frame = RawFrame {
            frame_type: FrameType::GREASE_1,
            flags: 0,
            payload: vec![0; 8],
        };
        assert!(frame.frame_type.is_ignorable());

        let mut buf = Vec::new();
        encode_frame(&frame, &mut buf).unwrap();
        let (decoded, _) = decode_frame(&buf).unwrap();
        assert_eq!(decoded, frame);
    }

    #[test]
    fn decode_incomplete_no_data() {
        assert!(matches!(decode_frame(&[]), Err(CodecError::Incomplete)));
    }

    #[test]
    fn decode_incomplete_header_only() {
        // frame_type=0x00, flags=0x00, length=10, but no payload
        let mut buf = Vec::new();
        varint::encode(0x00, &mut buf).unwrap(); // frame_type
        buf.push(0x00); // flags
        varint::encode(10, &mut buf).unwrap(); // length = 10 bytes
        // No payload bytes

        assert!(matches!(decode_frame(&buf), Err(CodecError::Incomplete)));
    }

    #[test]
    fn decode_incomplete_partial_payload() {
        let mut buf = Vec::new();
        varint::encode(0x00, &mut buf).unwrap();
        buf.push(0x00);
        varint::encode(10, &mut buf).unwrap();
        buf.extend_from_slice(&[0u8; 5]); // Only 5 of 10 bytes

        assert!(matches!(decode_frame(&buf), Err(CodecError::Incomplete)));
    }

    #[test]
    fn decode_payload_too_large() {
        let mut buf = Vec::new();
        varint::encode(0x00, &mut buf).unwrap();
        buf.push(0x00);
        let oversized = MAX_FRAME_PAYLOAD as u64 + 1;
        varint::encode(oversized, &mut buf).unwrap();

        assert!(matches!(
            decode_frame(&buf),
            Err(CodecError::PayloadTooLarge { .. })
        ));
    }

    #[test]
    fn multiple_frames_in_buffer() {
        let f1 = RawFrame {
            frame_type: FrameType::CLIENT_INIT,
            flags: 0,
            payload: vec![1, 2, 3],
        };
        let f2 = RawFrame {
            frame_type: FrameType::SERVER_INIT,
            flags: 0,
            payload: vec![4, 5],
        };
        let mut buf = Vec::new();
        encode_frame(&f1, &mut buf).unwrap();
        encode_frame(&f2, &mut buf).unwrap();

        let (d1, consumed1) = decode_frame(&buf).unwrap();
        assert_eq!(d1, f1);

        let (d2, consumed2) = decode_frame(&buf[consumed1..]).unwrap();
        assert_eq!(d2, f2);

        assert_eq!(consumed1 + consumed2, buf.len());
    }

    #[test]
    fn unknown_frame_type_decodes() {
        // Unknown frame types should still decode — it's the caller's
        // job to decide whether to ignore or error based on is_ignorable().
        let frame = RawFrame {
            frame_type: FrameType(0xFFFE), // unknown, critical (even)
            flags: 0,
            payload: vec![0xAB],
        };
        let mut buf = Vec::new();
        encode_frame(&frame, &mut buf).unwrap();

        let (decoded, _) = decode_frame(&buf).unwrap();
        assert_eq!(decoded.frame_type, FrameType(0xFFFE));
        assert!(decoded.frame_type.is_critical());
    }
}
