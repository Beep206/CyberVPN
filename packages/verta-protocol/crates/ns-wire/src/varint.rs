use crate::WireError;

pub fn encoded_varint_len(value: u64) -> Result<usize, WireError> {
    match value {
        0..=63 => Ok(1),
        64..=16_383 => Ok(2),
        16_384..=1_073_741_823 => Ok(4),
        1_073_741_824..=4_611_686_018_427_387_903 => Ok(8),
        _ => Err(WireError::VarIntOutOfRange(value)),
    }
}

pub fn encode_varint(value: u64, output: &mut Vec<u8>) -> Result<(), WireError> {
    match encoded_varint_len(value)? {
        1 => output.push(value as u8),
        2 => {
            output.push(0b01_000000 | ((value >> 8) as u8 & 0x3f));
            output.push(value as u8);
        }
        4 => {
            output.push(0b10_000000 | ((value >> 24) as u8 & 0x3f));
            output.push((value >> 16) as u8);
            output.push((value >> 8) as u8);
            output.push(value as u8);
        }
        8 => {
            output.push(0b11_000000 | ((value >> 56) as u8 & 0x3f));
            output.push((value >> 48) as u8);
            output.push((value >> 40) as u8);
            output.push((value >> 32) as u8);
            output.push((value >> 24) as u8);
            output.push((value >> 16) as u8);
            output.push((value >> 8) as u8);
            output.push(value as u8);
        }
        _ => unreachable!("encoded_varint_len only returns 1, 2, 4, or 8"),
    }
    Ok(())
}

pub fn decode_varint(input: &mut &[u8]) -> Result<u64, WireError> {
    if input.is_empty() {
        return Err(WireError::Truncated);
    }

    let first = input[0];
    let prefix = first >> 6;
    let length = match prefix {
        0 => 1,
        1 => 2,
        2 => 4,
        3 => 8,
        _ => unreachable!(),
    };

    if input.len() < length {
        return Err(WireError::Truncated);
    }

    let mut value = (first & 0x3f) as u64;
    for byte in &input[1..length] {
        value = (value << 8) | (*byte as u64);
    }

    let minimum = match length {
        1 => 0,
        2 => 64,
        4 => 16_384,
        8 => 1_073_741_824,
        _ => unreachable!(),
    };
    if value < minimum {
        return Err(WireError::NonCanonicalVarInt);
    }

    *input = &input[length..];
    Ok(value)
}

#[cfg(test)]
mod tests {
    use super::{decode_varint, encode_varint};

    #[test]
    fn round_trips_varints() {
        let values = [0, 1, 63, 64, 999, 16_383, 16_384, 1_073_741_823];
        for value in values {
            let mut output = Vec::new();
            encode_varint(value, &mut output).expect("fixture varint should encode");
            let mut slice = output.as_slice();
            let decoded = decode_varint(&mut slice).expect("fixture varint should decode");
            assert_eq!(decoded, value);
            assert!(slice.is_empty());
        }
    }

    #[test]
    fn rejects_non_canonical_varint() {
        let mut slice: &[u8] = &[0b01_000000, 0x01];
        assert!(decode_varint(&mut slice).is_err());
    }
}
