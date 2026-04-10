//! Telemetry frame wire formats for in-session observability.
//!
//! Two frame types:
//! - `HEALTH_SUMMARY` (0x81, ignorable): Periodic session health snapshot.
//! - `ERROR_REPORT` (0x83, ignorable): Error diagnostic report.

/// `HEALTH_SUMMARY` frame payload.
///
/// A compact snapshot of session health sent periodically by either side.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HealthSummaryFrame {
    /// Current key epoch.
    pub epoch: u64,
    /// Session uptime in seconds.
    pub uptime_secs: u64,
    /// Total bytes sent.
    pub bytes_sent: u64,
    /// Total bytes received.
    pub bytes_recv: u64,
    /// Total streams opened.
    pub streams_opened: u32,
    /// Total streams closed.
    pub streams_closed: u32,
    /// Total rekey operations completed.
    pub rekeys: u32,
    /// Estimated RTT in microseconds (0 if unknown).
    pub rtt_estimate_us: u32,
}

impl HealthSummaryFrame {
    /// Fixed wire size: 8+8+8+8+4+4+4+4 = 48 bytes.
    pub const WIRE_SIZE: usize = 48;

    pub fn encode(&self, buf: &mut Vec<u8>) {
        buf.extend_from_slice(&self.epoch.to_be_bytes());
        buf.extend_from_slice(&self.uptime_secs.to_be_bytes());
        buf.extend_from_slice(&self.bytes_sent.to_be_bytes());
        buf.extend_from_slice(&self.bytes_recv.to_be_bytes());
        buf.extend_from_slice(&self.streams_opened.to_be_bytes());
        buf.extend_from_slice(&self.streams_closed.to_be_bytes());
        buf.extend_from_slice(&self.rekeys.to_be_bytes());
        buf.extend_from_slice(&self.rtt_estimate_us.to_be_bytes());
    }

    pub fn decode(input: &[u8]) -> Result<Self, TelemetryDecodeError> {
        if input.len() < Self::WIRE_SIZE {
            return Err(TelemetryDecodeError::Truncated);
        }
        Ok(Self {
            epoch: u64::from_be_bytes(input[0..8].try_into().unwrap()),
            uptime_secs: u64::from_be_bytes(input[8..16].try_into().unwrap()),
            bytes_sent: u64::from_be_bytes(input[16..24].try_into().unwrap()),
            bytes_recv: u64::from_be_bytes(input[24..32].try_into().unwrap()),
            streams_opened: u32::from_be_bytes(input[32..36].try_into().unwrap()),
            streams_closed: u32::from_be_bytes(input[36..40].try_into().unwrap()),
            rekeys: u32::from_be_bytes(input[40..44].try_into().unwrap()),
            rtt_estimate_us: u32::from_be_bytes(input[44..48].try_into().unwrap()),
        })
    }
}

/// `ERROR_REPORT` frame payload.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ErrorReportFrame {
    /// Error code from `SessionErrorCode`.
    pub error_code: u32,
    /// Unix timestamp (seconds) when the error occurred.
    pub timestamp_unix: u64,
    /// Opaque diagnostic context (up to 256 bytes).
    pub context: Vec<u8>,
}

impl ErrorReportFrame {
    pub fn encode(&self, buf: &mut Vec<u8>) {
        buf.extend_from_slice(&self.error_code.to_be_bytes());
        buf.extend_from_slice(&self.timestamp_unix.to_be_bytes());
        let ctx_len = self.context.len().min(256) as u16;
        buf.extend_from_slice(&ctx_len.to_be_bytes());
        buf.extend_from_slice(&self.context[..ctx_len as usize]);
    }

    pub fn decode(input: &[u8]) -> Result<Self, TelemetryDecodeError> {
        if input.len() < 14 {
            return Err(TelemetryDecodeError::Truncated);
        }
        let error_code = u32::from_be_bytes(input[0..4].try_into().unwrap());
        let timestamp_unix = u64::from_be_bytes(input[4..12].try_into().unwrap());
        let ctx_len = u16::from_be_bytes(input[12..14].try_into().unwrap()) as usize;
        if input.len() - 14 < ctx_len {
            return Err(TelemetryDecodeError::Truncated);
        }
        let context = input[14..14 + ctx_len].to_vec();
        Ok(Self {
            error_code,
            timestamp_unix,
            context,
        })
    }
}

/// Telemetry frame decode errors.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum TelemetryDecodeError {
    #[error("frame truncated")]
    Truncated,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn health_summary_roundtrip() {
        let frame = HealthSummaryFrame {
            epoch: 3,
            uptime_secs: 3600,
            bytes_sent: 1_000_000,
            bytes_recv: 2_000_000,
            streams_opened: 42,
            streams_closed: 40,
            rekeys: 3,
            rtt_estimate_us: 15_000,
        };
        let mut buf = Vec::new();
        frame.encode(&mut buf);
        assert_eq!(buf.len(), HealthSummaryFrame::WIRE_SIZE);
        let decoded = HealthSummaryFrame::decode(&buf).unwrap();
        assert_eq!(decoded, frame);
    }

    #[test]
    fn health_summary_truncated() {
        let result = HealthSummaryFrame::decode(&[0u8; 10]);
        assert_eq!(result, Err(TelemetryDecodeError::Truncated));
    }

    #[test]
    fn error_report_roundtrip() {
        let frame = ErrorReportFrame {
            error_code: 0x0042,
            timestamp_unix: 1_700_000_000,
            context: b"connection reset by peer".to_vec(),
        };
        let mut buf = Vec::new();
        frame.encode(&mut buf);
        let decoded = ErrorReportFrame::decode(&buf).unwrap();
        assert_eq!(decoded, frame);
    }

    #[test]
    fn error_report_empty_context() {
        let frame = ErrorReportFrame {
            error_code: 1,
            timestamp_unix: 0,
            context: vec![],
        };
        let mut buf = Vec::new();
        frame.encode(&mut buf);
        let decoded = ErrorReportFrame::decode(&buf).unwrap();
        assert_eq!(decoded, frame);
    }
}
