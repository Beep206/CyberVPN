//! QUIC-style variable-length integer encoding (RFC 9000 §16).
//!
//! The first two bits of the first byte encode the length:
//!
//! | 2MSB | Wire bytes | Usable bits | Max value              |
//! |------|-----------|-------------|------------------------|
//! | 00   | 1         | 6           | 63                     |
//! | 01   | 2         | 14          | 16,383                 |
//! | 10   | 4         | 30          | 1,073,741,823          |
//! | 11   | 8         | 62          | 4,611,686,018,427,387,903 |

/// Maximum value representable by a QUIC-style varint (2^62 - 1).
pub const MAX_VARINT: u64 = (1 << 62) - 1;

/// Errors from varint operations.
#[derive(Debug, Clone, Copy, PartialEq, Eq, thiserror::Error)]
pub enum VarintError {
    /// Not enough bytes in the buffer to decode.
    #[error("buffer underflow: need at least {needed} bytes, have {available}")]
    BufferUnderflow { needed: usize, available: usize },

    /// Value exceeds 2^62 - 1.
    #[error("value {0} exceeds maximum varint value (2^62 - 1)")]
    ValueTooLarge(u64),
}

/// Returns the number of bytes needed to encode `value`, or an error if too large.
pub const fn encoded_len(value: u64) -> Result<usize, VarintError> {
    if value <= 63 {
        Ok(1)
    } else if value <= 16_383 {
        Ok(2)
    } else if value <= 1_073_741_823 {
        Ok(4)
    } else if value <= MAX_VARINT {
        Ok(8)
    } else {
        Err(VarintError::ValueTooLarge(value))
    }
}

/// Encode `value` as a QUIC-style varint, appending bytes to `buf`.
pub fn encode(value: u64, buf: &mut Vec<u8>) -> Result<usize, VarintError> {
    let len = encoded_len(value)?;
    match len {
        1 => {
            buf.push(value as u8);
        }
        2 => {
            let v = (value as u16) | 0x4000;
            buf.extend_from_slice(&v.to_be_bytes());
        }
        4 => {
            let v = (value as u32) | 0x8000_0000;
            buf.extend_from_slice(&v.to_be_bytes());
        }
        8 => {
            let v = value | 0xC000_0000_0000_0000;
            buf.extend_from_slice(&v.to_be_bytes());
        }
        _ => unreachable!(),
    }
    Ok(len)
}

/// Decode a QUIC-style varint from `buf`.
///
/// Returns `(value, bytes_consumed)`. The caller must advance their own
/// read cursor by `bytes_consumed`. The input buffer is not modified.
pub fn decode(buf: &[u8]) -> Result<(u64, usize), VarintError> {
    if buf.is_empty() {
        return Err(VarintError::BufferUnderflow {
            needed: 1,
            available: 0,
        });
    }

    let first = buf[0];
    let length_class = first >> 6;

    match length_class {
        0b00 => Ok((u64::from(first), 1)),
        0b01 => {
            if buf.len() < 2 {
                return Err(VarintError::BufferUnderflow {
                    needed: 2,
                    available: buf.len(),
                });
            }
            let mut bytes = [0u8; 2];
            bytes.copy_from_slice(&buf[..2]);
            bytes[0] &= 0x3F; // Clear length class bits
            Ok((u64::from(u16::from_be_bytes(bytes)), 2))
        }
        0b10 => {
            if buf.len() < 4 {
                return Err(VarintError::BufferUnderflow {
                    needed: 4,
                    available: buf.len(),
                });
            }
            let mut bytes = [0u8; 4];
            bytes.copy_from_slice(&buf[..4]);
            bytes[0] &= 0x3F;
            Ok((u64::from(u32::from_be_bytes(bytes)), 4))
        }
        0b11 => {
            if buf.len() < 8 {
                return Err(VarintError::BufferUnderflow {
                    needed: 8,
                    available: buf.len(),
                });
            }
            let mut bytes = [0u8; 8];
            bytes.copy_from_slice(&buf[..8]);
            bytes[0] &= 0x3F;
            Ok((u64::from_be_bytes(bytes), 8))
        }
        _ => unreachable!(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Test vectors from RFC 9000 §A.1
    #[test]
    fn rfc_test_vectors() {
        // 1-byte encoding
        assert_roundtrip(0, &[0x00]);
        assert_roundtrip(37, &[0x25]);
        assert_roundtrip(63, &[0x3F]);

        // 2-byte encoding
        assert_roundtrip(15293, &[0x7B, 0xBD]);

        // 4-byte encoding
        assert_roundtrip(494878333, &[0x9D, 0x7F, 0x3E, 0x7D]);

        // 8-byte encoding
        assert_roundtrip(
            151288809941952652,
            &[0xC2, 0x19, 0x7C, 0x5E, 0xFF, 0x14, 0xE8, 0x8C],
        );
    }

    #[test]
    fn boundary_values() {
        // Max 1-byte
        assert_roundtrip(63, &[0x3F]);
        // Min 2-byte
        let mut buf = Vec::new();
        encode(64, &mut buf).unwrap();
        assert_eq!(buf.len(), 2);
        let (val, consumed) = decode(&buf).unwrap();
        assert_eq!(val, 64);
        assert_eq!(consumed, 2);

        // Max 2-byte
        let mut buf = Vec::new();
        encode(16383, &mut buf).unwrap();
        assert_eq!(buf.len(), 2);

        // Min 4-byte
        let mut buf = Vec::new();
        encode(16384, &mut buf).unwrap();
        assert_eq!(buf.len(), 4);

        // Max 4-byte
        let mut buf = Vec::new();
        encode(1_073_741_823, &mut buf).unwrap();
        assert_eq!(buf.len(), 4);

        // Min 8-byte
        let mut buf = Vec::new();
        encode(1_073_741_824, &mut buf).unwrap();
        assert_eq!(buf.len(), 8);

        // Max varint
        let mut buf = Vec::new();
        encode(MAX_VARINT, &mut buf).unwrap();
        assert_eq!(buf.len(), 8);
        let (val, _) = decode(&buf).unwrap();
        assert_eq!(val, MAX_VARINT);
    }

    #[test]
    fn zero() {
        assert_roundtrip(0, &[0x00]);
    }

    #[test]
    fn value_too_large() {
        let result = encode(MAX_VARINT + 1, &mut Vec::new());
        assert!(matches!(result, Err(VarintError::ValueTooLarge(_))));
    }

    #[test]
    fn buffer_underflow_empty() {
        let result = decode(&[]);
        assert!(matches!(
            result,
            Err(VarintError::BufferUnderflow {
                needed: 1,
                available: 0
            })
        ));
    }

    #[test]
    fn buffer_underflow_partial_2byte() {
        // First byte indicates 2-byte varint, but only 1 byte available
        let result = decode(&[0x40]);
        assert!(matches!(
            result,
            Err(VarintError::BufferUnderflow {
                needed: 2,
                available: 1
            })
        ));
    }

    #[test]
    fn buffer_underflow_partial_4byte() {
        let result = decode(&[0x80, 0x01]);
        assert!(matches!(
            result,
            Err(VarintError::BufferUnderflow {
                needed: 4,
                available: 2
            })
        ));
    }

    #[test]
    fn buffer_underflow_partial_8byte() {
        let result = decode(&[0xC0, 0x01, 0x02, 0x03]);
        assert!(matches!(
            result,
            Err(VarintError::BufferUnderflow {
                needed: 8,
                available: 4
            })
        ));
    }

    #[test]
    fn encoded_len_values() {
        assert_eq!(encoded_len(0), Ok(1));
        assert_eq!(encoded_len(63), Ok(1));
        assert_eq!(encoded_len(64), Ok(2));
        assert_eq!(encoded_len(16383), Ok(2));
        assert_eq!(encoded_len(16384), Ok(4));
        assert_eq!(encoded_len(1_073_741_823), Ok(4));
        assert_eq!(encoded_len(1_073_741_824), Ok(8));
        assert_eq!(encoded_len(MAX_VARINT), Ok(8));
        assert!(encoded_len(MAX_VARINT + 1).is_err());
    }

    #[test]
    fn decode_with_trailing_data() {
        // Varint followed by extra data — only varint bytes consumed
        let buf = [0x25, 0xFF, 0xFF];
        let (val, consumed) = decode(&buf).unwrap();
        assert_eq!(val, 37);
        assert_eq!(consumed, 1);
    }

    fn assert_roundtrip(value: u64, expected_bytes: &[u8]) {
        let mut buf = Vec::new();
        let written = encode(value, &mut buf).unwrap();
        assert_eq!(written, expected_bytes.len());
        assert_eq!(&buf, expected_bytes);

        let (decoded, consumed) = decode(&buf).unwrap();
        assert_eq!(decoded, value);
        assert_eq!(consumed, expected_bytes.len());
    }
}
