//! Stream and datagram multiplexing for the Beep session core.
//!
//! After handshake, a Beep session multiplexes two traffic classes:
//! - **Streams**: reliable, ordered byte flows identified by `StreamId`
//! - **Datagrams**: unreliable message carriage identified by `ClassId`
//!
//! Both are encrypted per-frame using the cipher module's `TrafficKey`.

use crate::varint;

/// Stream identifier (client-initiated: odd, server-initiated: even).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct StreamId(pub u32);

impl StreamId {
    pub fn is_client_initiated(&self) -> bool {
        self.0 % 2 == 1
    }
    pub fn is_server_initiated(&self) -> bool {
        self.0.is_multiple_of(2) && self.0 > 0
    }
}

/// Datagram class identifier.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct ClassId(pub u16);

/// Stream state.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StreamState {
    /// Stream has been opened.
    Open,
    /// Local side has sent FIN.
    HalfClosedLocal,
    /// Remote side has sent FIN.
    HalfClosedRemote,
    /// Both sides have closed.
    Closed,
}

/// Per-stream metadata tracked by the multiplexer.
#[derive(Debug)]
pub struct StreamInfo {
    pub id: StreamId,
    pub state: StreamState,
    /// Bytes we are allowed to send (peer's receive window).
    pub send_credit: u64,
    /// Bytes we are willing to receive (our receive window).
    pub recv_credit: u64,
    /// Total bytes sent on this stream.
    pub bytes_sent: u64,
    /// Total bytes received on this stream.
    pub bytes_received: u64,
}

/// Connection-level multiplexer state.
pub struct MuxState {
    /// Next client-initiated stream ID.
    next_client_id: u32,
    /// Next server-initiated stream ID.
    next_server_id: u32,
    /// Active streams.
    streams: std::collections::HashMap<StreamId, StreamInfo>,
    /// Connection-level send credit.
    pub conn_send_credit: u64,
    /// Connection-level recv credit.
    pub conn_recv_credit: u64,
    /// Default per-stream credit.
    default_stream_credit: u64,
    /// Whether this side is the initiator (client).
    is_initiator: bool,
}

/// Default connection-level credit (256 KiB).
const DEFAULT_CONN_CREDIT: u64 = 256 * 1024;
/// Default per-stream credit (64 KiB).
const DEFAULT_STREAM_CREDIT: u64 = 64 * 1024;

impl MuxState {
    /// Create a new multiplexer.
    pub fn new(is_initiator: bool) -> Self {
        Self {
            next_client_id: 1,
            next_server_id: 2,
            streams: std::collections::HashMap::new(),
            conn_send_credit: DEFAULT_CONN_CREDIT,
            conn_recv_credit: DEFAULT_CONN_CREDIT,
            default_stream_credit: DEFAULT_STREAM_CREDIT,
            is_initiator,
        }
    }

    /// Open a new locally-initiated stream.
    pub fn open_stream(&mut self) -> StreamId {
        let id = if self.is_initiator {
            let id = StreamId(self.next_client_id);
            self.next_client_id += 2;
            id
        } else {
            let id = StreamId(self.next_server_id);
            self.next_server_id += 2;
            id
        };

        self.streams.insert(id, StreamInfo {
            id,
            state: StreamState::Open,
            send_credit: self.default_stream_credit,
            recv_credit: self.default_stream_credit,
            bytes_sent: 0,
            bytes_received: 0,
        });

        id
    }

    /// Accept a remotely-opened stream.
    pub fn accept_stream(&mut self, id: StreamId) -> Result<(), MuxError> {
        if self.streams.contains_key(&id) {
            return Err(MuxError::StreamAlreadyExists(id));
        }
        self.streams.insert(id, StreamInfo {
            id,
            state: StreamState::Open,
            send_credit: self.default_stream_credit,
            recv_credit: self.default_stream_credit,
            bytes_sent: 0,
            bytes_received: 0,
        });
        Ok(())
    }

    /// Get a stream reference.
    pub fn stream(&self, id: StreamId) -> Option<&StreamInfo> {
        self.streams.get(&id)
    }

    /// Close the local half of a stream.
    pub fn close_local(&mut self, id: StreamId) -> Result<(), MuxError> {
        let info = self.streams.get_mut(&id)
            .ok_or(MuxError::UnknownStream(id))?;
        info.state = match info.state {
            StreamState::Open => StreamState::HalfClosedLocal,
            StreamState::HalfClosedRemote => StreamState::Closed,
            other => return Err(MuxError::InvalidStreamState(id, other)),
        };
        Ok(())
    }

    /// Close the remote half of a stream.
    pub fn close_remote(&mut self, id: StreamId) -> Result<(), MuxError> {
        let info = self.streams.get_mut(&id)
            .ok_or(MuxError::UnknownStream(id))?;
        info.state = match info.state {
            StreamState::Open => StreamState::HalfClosedRemote,
            StreamState::HalfClosedLocal => StreamState::Closed,
            other => return Err(MuxError::InvalidStreamState(id, other)),
        };
        Ok(())
    }

    /// Record bytes sent on a stream. Decrements both stream and connection credit.
    pub fn record_send(&mut self, id: StreamId, len: u64) -> Result<(), MuxError> {
        if len > self.conn_send_credit {
            return Err(MuxError::ConnectionCreditExhausted);
        }
        let info = self.streams.get_mut(&id)
            .ok_or(MuxError::UnknownStream(id))?;
        if len > info.send_credit {
            return Err(MuxError::StreamCreditExhausted(id));
        }
        info.send_credit -= len;
        info.bytes_sent += len;
        self.conn_send_credit -= len;
        Ok(())
    }

    /// Record bytes received on a stream. Decrements recv credit.
    pub fn record_recv(&mut self, id: StreamId, len: u64) -> Result<(), MuxError> {
        if len > self.conn_recv_credit {
            return Err(MuxError::ConnectionCreditExhausted);
        }
        let info = self.streams.get_mut(&id)
            .ok_or(MuxError::UnknownStream(id))?;
        if len > info.recv_credit {
            return Err(MuxError::StreamCreditExhausted(id));
        }
        info.recv_credit -= len;
        info.bytes_received += len;
        self.conn_recv_credit -= len;
        Ok(())
    }

    /// Issue additional send credit to a stream (from a received FLOW_CREDIT).
    pub fn add_send_credit(&mut self, id: StreamId, amount: u64) -> Result<(), MuxError> {
        let info = self.streams.get_mut(&id)
            .ok_or(MuxError::UnknownStream(id))?;
        info.send_credit = info.send_credit.saturating_add(amount);
        Ok(())
    }

    /// Issue additional connection-level send credit.
    pub fn add_conn_send_credit(&mut self, amount: u64) {
        self.conn_send_credit = self.conn_send_credit.saturating_add(amount);
    }

    /// Count of active (non-closed) streams.
    pub fn active_stream_count(&self) -> usize {
        self.streams.values().filter(|s| s.state != StreamState::Closed).count()
    }

    /// Remove closed streams from tracking.
    pub fn gc_closed_streams(&mut self) {
        self.streams.retain(|_, s| s.state != StreamState::Closed);
    }
}

/// Mux-level errors.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum MuxError {
    #[error("unknown stream {0:?}")]
    UnknownStream(StreamId),
    #[error("stream {0:?} already exists")]
    StreamAlreadyExists(StreamId),
    #[error("invalid stream state {1:?} for stream {0:?}")]
    InvalidStreamState(StreamId, StreamState),
    #[error("stream credit exhausted for {0:?}")]
    StreamCreditExhausted(StreamId),
    #[error("connection-level credit exhausted")]
    ConnectionCreditExhausted,
}

// ── Wire format for stream/datagram frames ──────────────────────────────

/// A stream data frame (STREAM_DATA on the wire).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StreamFrame {
    pub stream_id: u32,
    pub offset: u64,
    pub fin: bool,
    pub data: Vec<u8>,
}

impl StreamFrame {
    pub fn encode(&self, buf: &mut Vec<u8>) -> Result<(), varint::VarintError> {
        varint::encode(self.stream_id as u64, buf)?;
        varint::encode(self.offset, buf)?;
        buf.push(if self.fin { 1 } else { 0 });
        varint::encode(self.data.len() as u64, buf)?;
        buf.extend_from_slice(&self.data);
        Ok(())
    }

    pub fn decode(input: &[u8]) -> Result<(Self, usize), StreamFrameDecodeError> {
        let mut offset = 0;

        let (stream_id, n) = varint::decode(input)?;
        offset += n;
        let (file_offset, n) = varint::decode(&input[offset..])?;
        offset += n;

        if offset >= input.len() {
            return Err(StreamFrameDecodeError::Truncated);
        }
        let fin = input[offset] != 0;
        offset += 1;

        let (data_len, n) = varint::decode(&input[offset..])?;
        offset += n;
        let data_len = data_len as usize;

        if input.len() - offset < data_len {
            return Err(StreamFrameDecodeError::Truncated);
        }
        let data = input[offset..offset + data_len].to_vec();
        offset += data_len;

        Ok((StreamFrame {
            stream_id: stream_id as u32,
            offset: file_offset,
            fin,
            data,
        }, offset))
    }
}

/// A datagram frame.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DatagramFrame {
    pub class_id: u16,
    pub data: Vec<u8>,
}

impl DatagramFrame {
    pub fn encode(&self, buf: &mut Vec<u8>) -> Result<(), varint::VarintError> {
        buf.extend_from_slice(&self.class_id.to_be_bytes());
        varint::encode(self.data.len() as u64, buf)?;
        buf.extend_from_slice(&self.data);
        Ok(())
    }

    pub fn decode(input: &[u8]) -> Result<(Self, usize), StreamFrameDecodeError> {
        if input.len() < 2 {
            return Err(StreamFrameDecodeError::Truncated);
        }
        let class_id = u16::from_be_bytes([input[0], input[1]]);
        let mut offset = 2;
        let (data_len, n) = varint::decode(&input[offset..])?;
        offset += n;
        let data_len = data_len as usize;
        if input.len() - offset < data_len {
            return Err(StreamFrameDecodeError::Truncated);
        }
        let data = input[offset..offset + data_len].to_vec();
        offset += data_len;
        Ok((DatagramFrame { class_id, data }, offset))
    }
}

/// A flow credit update frame.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FlowCreditFrame {
    /// 0 = connection-level, >0 = stream-level.
    pub stream_id: u32,
    pub credit: u64,
}

impl FlowCreditFrame {
    pub fn encode(&self, buf: &mut Vec<u8>) -> Result<(), varint::VarintError> {
        varint::encode(self.stream_id as u64, buf)?;
        varint::encode(self.credit, buf)?;
        Ok(())
    }

    pub fn decode(input: &[u8]) -> Result<(Self, usize), StreamFrameDecodeError> {
        let (stream_id, n) = varint::decode(input)?;
        let (credit, n2) = varint::decode(&input[n..])?;
        Ok((FlowCreditFrame {
            stream_id: stream_id as u32,
            credit,
        }, n + n2))
    }
}

/// Decode errors for multiplexed frames.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum StreamFrameDecodeError {
    #[error("varint error: {0}")]
    Varint(#[from] varint::VarintError),
    #[error("frame truncated")]
    Truncated,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stream_frame_roundtrip() {
        let frame = StreamFrame {
            stream_id: 3,
            offset: 0,
            fin: false,
            data: b"hello stream".to_vec(),
        };
        let mut buf = Vec::new();
        frame.encode(&mut buf).unwrap();
        let (decoded, consumed) = StreamFrame::decode(&buf).unwrap();
        assert_eq!(consumed, buf.len());
        assert_eq!(decoded, frame);
    }

    #[test]
    fn stream_frame_with_fin() {
        let frame = StreamFrame {
            stream_id: 5,
            offset: 1024,
            fin: true,
            data: b"last chunk".to_vec(),
        };
        let mut buf = Vec::new();
        frame.encode(&mut buf).unwrap();
        let (decoded, _) = StreamFrame::decode(&buf).unwrap();
        assert!(decoded.fin);
        assert_eq!(decoded.offset, 1024);
    }

    #[test]
    fn datagram_frame_roundtrip() {
        let frame = DatagramFrame {
            class_id: 42,
            data: vec![0xDE, 0xAD, 0xBE, 0xEF],
        };
        let mut buf = Vec::new();
        frame.encode(&mut buf).unwrap();
        let (decoded, consumed) = DatagramFrame::decode(&buf).unwrap();
        assert_eq!(consumed, buf.len());
        assert_eq!(decoded, frame);
    }

    #[test]
    fn flow_credit_roundtrip() {
        let frame = FlowCreditFrame { stream_id: 3, credit: 65536 };
        let mut buf = Vec::new();
        frame.encode(&mut buf).unwrap();
        let (decoded, consumed) = FlowCreditFrame::decode(&buf).unwrap();
        assert_eq!(consumed, buf.len());
        assert_eq!(decoded, frame);
    }

    #[test]
    fn mux_open_and_close_stream() {
        let mut mux = MuxState::new(true); // client
        let id = mux.open_stream();
        assert!(id.is_client_initiated());
        assert_eq!(mux.active_stream_count(), 1);

        mux.close_local(id).unwrap();
        assert_eq!(mux.stream(id).unwrap().state, StreamState::HalfClosedLocal);

        mux.close_remote(id).unwrap();
        assert_eq!(mux.stream(id).unwrap().state, StreamState::Closed);

        mux.gc_closed_streams();
        assert_eq!(mux.active_stream_count(), 0);
    }

    #[test]
    fn mux_server_streams_are_even() {
        let mut mux = MuxState::new(false); // server
        let id1 = mux.open_stream();
        let id2 = mux.open_stream();
        assert!(id1.is_server_initiated());
        assert!(id2.is_server_initiated());
        assert_ne!(id1, id2);
    }

    #[test]
    fn flow_credit_enforcement() {
        let mut mux = MuxState::new(true);
        let id = mux.open_stream();

        // Default credit is 64 KiB
        let result = mux.record_send(id, 64 * 1024);
        assert!(result.is_ok());

        // Exceeding credit fails
        let result = mux.record_send(id, 1);
        assert!(result.is_err());

        // Adding credit allows more
        mux.add_send_credit(id, 1024).unwrap();
        let result = mux.record_send(id, 1024);
        assert!(result.is_ok());
    }

    #[test]
    fn connection_level_credit() {
        let mut mux = MuxState::new(true);
        let id = mux.open_stream();

        // Exhaust connection credit
        mux.conn_send_credit = 100;
        let result = mux.record_send(id, 101);
        assert_eq!(result, Err(MuxError::ConnectionCreditExhausted));

        let result = mux.record_send(id, 100);
        assert!(result.is_ok());
    }

    #[test]
    fn accept_duplicate_stream_fails() {
        let mut mux = MuxState::new(true);
        mux.accept_stream(StreamId(5)).unwrap();
        let result = mux.accept_stream(StreamId(5));
        assert_eq!(result, Err(MuxError::StreamAlreadyExists(StreamId(5))));
    }
}
