//! In-session metric counters for observability.
//!
//! `SessionMetrics` tracks session-level statistics and can produce
//! a `HealthSummaryFrame` for transmission to the peer.

use std::time::Instant;

use crate::telemetry::HealthSummaryFrame;

/// Session-level metric counters.
#[derive(Debug)]
pub struct SessionMetrics {
    /// Session start time.
    started_at: Instant,
    /// Current key epoch.
    pub epoch: u64,
    /// Total bytes encrypted and sent.
    pub bytes_sent: u64,
    /// Total bytes received and decrypted.
    pub bytes_recv: u64,
    /// Total frames sent.
    pub frames_sent: u64,
    /// Total frames received.
    pub frames_recv: u64,
    /// Streams opened (by us).
    pub streams_opened: u32,
    /// Streams closed (both sides).
    pub streams_closed: u32,
    /// Rekey operations completed.
    pub rekeys: u32,
    /// Estimated RTT in microseconds (0 = unknown).
    pub rtt_estimate_us: u32,
}

impl SessionMetrics {
    /// Create new metrics with the current time.
    pub fn new() -> Self {
        Self {
            started_at: Instant::now(),
            epoch: 0,
            bytes_sent: 0,
            bytes_recv: 0,
            frames_sent: 0,
            frames_recv: 0,
            streams_opened: 0,
            streams_closed: 0,
            rekeys: 0,
            rtt_estimate_us: 0,
        }
    }

    /// Session uptime in seconds.
    pub fn uptime_secs(&self) -> u64 {
        self.started_at.elapsed().as_secs()
    }

    /// Record bytes sent.
    pub fn record_send(&mut self, bytes: u64) {
        self.bytes_sent += bytes;
        self.frames_sent += 1;
    }

    /// Record bytes received.
    pub fn record_recv(&mut self, bytes: u64) {
        self.bytes_recv += bytes;
        self.frames_recv += 1;
    }

    /// Record a stream opened.
    pub fn record_stream_opened(&mut self) {
        self.streams_opened += 1;
    }

    /// Record a stream closed.
    pub fn record_stream_closed(&mut self) {
        self.streams_closed += 1;
    }

    /// Record a completed rekey.
    pub fn record_rekey(&mut self, new_epoch: u64) {
        self.rekeys += 1;
        self.epoch = new_epoch;
    }

    /// Generate a `HealthSummaryFrame` from current metrics.
    pub fn to_health_summary(&self) -> HealthSummaryFrame {
        HealthSummaryFrame {
            epoch: self.epoch,
            uptime_secs: self.uptime_secs(),
            bytes_sent: self.bytes_sent,
            bytes_recv: self.bytes_recv,
            streams_opened: self.streams_opened,
            streams_closed: self.streams_closed,
            rekeys: self.rekeys,
            rtt_estimate_us: self.rtt_estimate_us,
        }
    }
}

impl Default for SessionMetrics {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn initial_metrics() {
        let m = SessionMetrics::new();
        assert_eq!(m.bytes_sent, 0);
        assert_eq!(m.frames_sent, 0);
        assert_eq!(m.epoch, 0);
    }

    #[test]
    fn record_send_recv() {
        let mut m = SessionMetrics::new();
        m.record_send(1024);
        m.record_send(2048);
        m.record_recv(512);
        assert_eq!(m.bytes_sent, 3072);
        assert_eq!(m.frames_sent, 2);
        assert_eq!(m.bytes_recv, 512);
        assert_eq!(m.frames_recv, 1);
    }

    #[test]
    fn record_streams() {
        let mut m = SessionMetrics::new();
        m.record_stream_opened();
        m.record_stream_opened();
        m.record_stream_closed();
        assert_eq!(m.streams_opened, 2);
        assert_eq!(m.streams_closed, 1);
    }

    #[test]
    fn record_rekey() {
        let mut m = SessionMetrics::new();
        m.record_rekey(1);
        m.record_rekey(2);
        assert_eq!(m.rekeys, 2);
        assert_eq!(m.epoch, 2);
    }

    #[test]
    fn to_health_summary_captures_state() {
        let mut m = SessionMetrics::new();
        m.record_send(1000);
        m.record_recv(500);
        m.record_stream_opened();
        m.record_rekey(1);
        m.rtt_estimate_us = 15000;

        let hs = m.to_health_summary();
        assert_eq!(hs.epoch, 1);
        assert_eq!(hs.bytes_sent, 1000);
        assert_eq!(hs.bytes_recv, 500);
        assert_eq!(hs.streams_opened, 1);
        assert_eq!(hs.rekeys, 1);
        assert_eq!(hs.rtt_estimate_us, 15000);
    }
}
