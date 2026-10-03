//! Structured JSON event log for the test bench.
//!
//! Client and node write one JSON object per line, each tagged with the
//! profile id, so a later aggregator can read both sides of a run uniformly.
//! The events are the ones the stand needs to judge a series: when a handshake
//! started and finished (and how long it took), how many bytes moved, any stall
//! longer than [`STALL_THRESHOLD_MS`], and why a session ended.
//!
//! The log is optional: with no sink configured, the emit calls are cheap
//! no-ops, so normal (non-stand) runs stay quiet.

use serde::Serialize;
use std::io::{self, Write};
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};

/// A gap with no data longer than this (milliseconds) is reported as a stall.
pub const STALL_THRESHOLD_MS: u64 = 10_000;

/// One stand event. Serialized with a `event` tag plus the common fields that
/// [`EventLog::emit`] adds (timestamp, role, profile).
#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(tag = "event", rename_all = "snake_case")]
pub enum Event {
    /// A session handshake has begun.
    HandshakeStart,
    /// A handshake finished. `ok` is whether it succeeded; `detail` carries the
    /// rejection reason when it did not.
    HandshakeEnd {
        ok: bool,
        duration_ms: u64,
        #[serde(skip_serializing_if = "Option::is_none")]
        detail: Option<String>,
    },
    /// Cumulative bytes carried since the session started (periodic snapshot).
    Bytes { in_bytes: u64, out_bytes: u64 },
    /// No data moved for longer than [`STALL_THRESHOLD_MS`].
    Stall { idle_ms: u64 },
    /// The session ended, with totals and the reason.
    SessionClosed {
        reason: String,
        in_bytes: u64,
        out_bytes: u64,
        duration_ms: u64,
    },
}

/// The record actually written: common fields plus the flattened event.
#[derive(Serialize)]
struct Record<'a> {
    ts_ms: u128,
    role: &'a str,
    profile: &'a str,
    #[serde(flatten)]
    event: &'a Event,
}

/// A shared, line-delimited JSON event sink. Clones share one writer, so the
/// multiplexer and the binary can log to the same place.
#[derive(Clone)]
pub struct EventLog {
    role: Arc<str>,
    profile: Arc<str>,
    writer: Arc<Mutex<Box<dyn Write + Send>>>,
}

impl EventLog {
    /// Build a log over an arbitrary writer (a file, stderr, or a test buffer).
    pub fn new(role: &str, profile: &str, writer: Box<dyn Write + Send>) -> Self {
        Self {
            role: Arc::from(role),
            profile: Arc::from(profile),
            writer: Arc::new(Mutex::new(writer)),
        }
    }

    /// Append events to a file (created if absent).
    pub fn to_file(role: &str, profile: &str, path: &std::path::Path) -> io::Result<Self> {
        let file = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(path)?;
        Ok(Self::new(role, profile, Box::new(file)))
    }

    /// Write one event as a JSON line. Best-effort: a serialization or I/O
    /// error is swallowed so logging never breaks the data path.
    pub fn emit(&self, event: &Event) {
        let record = Record {
            ts_ms: now_ms(),
            role: &self.role,
            profile: &self.profile,
            event,
        };
        if let Ok(line) = serde_json::to_string(&record) {
            if let Ok(mut w) = self.writer.lock() {
                let _ = writeln!(w, "{line}");
                let _ = w.flush();
            }
        }
    }
}

fn now_ms() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis())
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Collect emitted lines into a shared buffer for assertions.
    #[derive(Clone, Default)]
    struct SharedBuf(Arc<Mutex<Vec<u8>>>);
    impl Write for SharedBuf {
        fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
            self.0.lock().unwrap().extend_from_slice(buf);
            Ok(buf.len())
        }
        fn flush(&mut self) -> io::Result<()> {
            Ok(())
        }
    }

    #[test]
    fn emits_one_json_line_per_event_with_common_fields() {
        let buf = SharedBuf::default();
        let log = EventLog::new("client", "chrome141-ws", Box::new(buf.clone()));

        log.emit(&Event::HandshakeStart);
        log.emit(&Event::HandshakeEnd {
            ok: true,
            duration_ms: 42,
            detail: None,
        });
        log.emit(&Event::SessionClosed {
            reason: "peer closed".into(),
            in_bytes: 100,
            out_bytes: 200,
            duration_ms: 1234,
        });

        let raw = String::from_utf8(buf.0.lock().unwrap().clone()).unwrap();
        let lines: Vec<&str> = raw.lines().collect();
        assert_eq!(lines.len(), 3, "one line per event");

        let first: serde_json::Value = serde_json::from_str(lines[0]).unwrap();
        assert_eq!(first["event"], "handshake_start");
        assert_eq!(first["role"], "client");
        assert_eq!(first["profile"], "chrome141-ws");
        assert!(first["ts_ms"].is_number());

        let second: serde_json::Value = serde_json::from_str(lines[1]).unwrap();
        assert_eq!(second["event"], "handshake_end");
        assert_eq!(second["ok"], true);
        assert_eq!(second["duration_ms"], 42);
        assert!(second.get("detail").is_none(), "None detail is omitted");

        let third: serde_json::Value = serde_json::from_str(lines[2]).unwrap();
        assert_eq!(third["event"], "session_closed");
        assert_eq!(third["reason"], "peer closed");
        assert_eq!(third["in_bytes"], 100);
        assert_eq!(third["out_bytes"], 200);
    }

    #[test]
    fn handshake_end_includes_detail_on_failure() {
        let buf = SharedBuf::default();
        let log = EventLog::new("node", "p", Box::new(buf.clone()));
        log.emit(&Event::HandshakeEnd {
            ok: false,
            duration_ms: 5,
            detail: Some("client token not recognised".into()),
        });
        let raw = String::from_utf8(buf.0.lock().unwrap().clone()).unwrap();
        let v: serde_json::Value = serde_json::from_str(raw.trim()).unwrap();
        assert_eq!(v["ok"], false);
        assert_eq!(v["detail"], "client token not recognised");
    }

    #[test]
    fn clones_share_one_writer() {
        let buf = SharedBuf::default();
        let a = EventLog::new("client", "p", Box::new(buf.clone()));
        let b = a.clone();
        a.emit(&Event::Stall { idle_ms: 11_000 });
        b.emit(&Event::Bytes {
            in_bytes: 1,
            out_bytes: 2,
        });
        let raw = String::from_utf8(buf.0.lock().unwrap().clone()).unwrap();
        assert_eq!(raw.lines().count(), 2, "both clones wrote to one buffer");
    }
}
