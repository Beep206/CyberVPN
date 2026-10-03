use crate::events::{Event, EventLog, STALL_THRESHOLD_MS};
use crate::keepalive::KeepaliveConfig;
use crate::tun_device::TunDevice;
use beep_core::mux::StreamId;
use beep_session::{DriverError, RecvEvent, SessionDriver};
use beep_transport::CoverConn;
use bytes::{Buf, BufMut, Bytes, BytesMut};
use std::io;
use std::time::{Duration, Instant};

/// How often the event log takes a byte-count snapshot and checks for stalls,
/// when an [`EventLog`] is attached. Independent of keepalive timing.
const EVENT_TICK: Duration = Duration::from_secs(5);

#[derive(Debug, thiserror::Error)]
pub enum MultiplexerError {
    #[error("Session driver error: {0}")]
    Driver(#[from] DriverError),
    #[error("TUN device error: {0}")]
    Tun(#[from] io::Error),
    #[error("peer idle timeout: no frame received within the keepalive deadline")]
    IdleTimeout,
    #[error("Multiplexer misconfigured or unexpected failure: {0}")]
    Internal(String),
}

/// Orchestrates traffic between the physical/virtual network (TUN) and the Beep VPN tunnel.
pub struct RuntimeMultiplexer<C: CoverConn, T: TunDevice> {
    driver: SessionDriver<C>,
    tun: T,
    use_datagrams: bool,
    stream_id: StreamId,

    // Buffers for parsing length-prefixed IP packets from the continuous stream.
    recv_buffer: BytesMut,

    // A single outbound packet held while waiting for send credit. Bounds
    // in-flight data to the send window and paces the TUN read side.
    pending_out: Option<Bytes>,

    // Optional liveness beacon + idle deadline. When set, the loop sends a
    // periodic HEALTH_SUMMARY and fails with `IdleTimeout` if the peer goes
    // silent for longer than `idle_timeout`, so the client can reconnect.
    keepalive: Option<KeepaliveConfig>,
    last_activity: Instant,

    // Optional structured event log for the test bench, plus the counters it
    // reports. `stall_reported` keeps one stall episode to a single event.
    events: Option<EventLog>,
    in_bytes: u64,
    out_bytes: u64,
    session_start: Instant,
    stall_reported: bool,
}

impl<C: CoverConn, T: TunDevice> RuntimeMultiplexer<C, T> {
    pub fn new(mut driver: SessionDriver<C>, tun: T, use_datagrams: bool) -> Self {
        // We open a primary stream immediately if we are forced to use streams
        // (the server will dynamically discover this stream ID when it receives data).
        let stream_id = if !use_datagrams {
            driver.open_stream()
        } else {
            StreamId(0)
        };

        Self {
            driver,
            tun,
            use_datagrams,
            stream_id,
            recv_buffer: BytesMut::new(),
            pending_out: None,
            keepalive: None,
            last_activity: Instant::now(),
            events: None,
            in_bytes: 0,
            out_bytes: 0,
            session_start: Instant::now(),
            stall_reported: false,
        }
    }

    /// Enable periodic liveness beacons and an idle deadline on this session.
    pub fn with_keepalive(mut self, config: KeepaliveConfig) -> Self {
        self.keepalive = Some(config);
        self.last_activity = Instant::now();
        self
    }

    /// Attach a structured event log. Byte counters, stalls and the final
    /// `SessionClosed` are then emitted for this session.
    pub fn with_events(mut self, events: EventLog) -> Self {
        self.events = Some(events);
        self
    }

    /// Run the session until it closes or errors, emitting a final
    /// `SessionClosed` event (with byte totals and the reason) when a log is
    /// attached. The actual loop is [`Self::drive`]; this wrapper guarantees the
    /// close event is recorded on every exit path.
    pub async fn run(&mut self) -> Result<(), MultiplexerError> {
        let result = self.drive().await;
        if let Some(ev) = self.events.clone() {
            let reason = match &result {
                Ok(()) => "closed".to_string(),
                Err(e) => e.to_string(),
            };
            ev.emit(&Event::SessionClosed {
                reason,
                in_bytes: self.in_bytes,
                out_bytes: self.out_bytes,
                duration_ms: self.session_start.elapsed().as_millis() as u64,
            });
        }
        result
    }

    /// The multiplexer loop.
    ///
    /// Outbound packets are paced by stream flow control: at most one packet is
    /// held (`pending_out`) while we wait for the peer's `FLOW_CREDIT` grants,
    /// which arrive on the receive arm. This keeps in-flight data bounded by the
    /// send window, so a stream never dies at the window edge and the outer
    /// transport socket never fills enough to block both directions at once.
    async fn drive(&mut self) -> Result<(), MultiplexerError> {
        // The beacon ticks at the keepalive interval, or idles far in the
        // future when keepalive is disabled (the arm then does nothing).
        let tick_period = self
            .keepalive
            .map(|k| k.interval)
            .unwrap_or_else(|| Duration::from_secs(3600));
        let mut beacon = tokio::time::interval(tick_period);
        beacon.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Delay);

        // A separate, faster beacon drives event snapshots and stall detection,
        // so they work even without keepalive. Its arm is a no-op when no log
        // is attached.
        let mut event_beacon = tokio::time::interval(EVENT_TICK);
        event_beacon.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Delay);

        self.last_activity = Instant::now();
        self.session_start = Instant::now();

        loop {
            // Flush the held packet as soon as we have credit for it.
            if let Some(pkt) = self.pending_out.take() {
                if self.can_send_now(&pkt) {
                    self.send_out(pkt).await?;
                } else {
                    self.pending_out = Some(pkt);
                }
            }

            tokio::select! {
                // VPN ➔ TUN (read from session -> inject to local OS). Also
                // delivers FLOW_CREDIT grants that free up send credit.
                event_res = self.driver.recv() => {
                    self.last_activity = Instant::now();
                    self.stall_reported = false;
                    let event = event_res?;
                    self.handle_vpn_event(event).await?;
                }

                // TUN ➔ VPN. Only read a new packet when none is held, so we
                // never buffer more than one packet ahead of available credit.
                pkt_res = self.tun.read_packet(), if self.pending_out.is_none() => {
                    self.pending_out = Some(pkt_res?);
                }

                // Keepalive: declare the peer dead after the idle deadline,
                // otherwise send a liveness beacon.
                _ = beacon.tick() => {
                    if let Some(cfg) = self.keepalive {
                        if self.last_activity.elapsed() > cfg.idle_timeout {
                            return Err(MultiplexerError::IdleTimeout);
                        }
                        self.driver.send_health_summary().await?;
                    }
                }

                // Event log: periodic byte snapshot + stall detection.
                _ = event_beacon.tick(), if self.events.is_some() => {
                    self.on_event_tick();
                }
            }
        }
    }

    /// Emit a byte snapshot and, once per stall episode, a stall event.
    fn on_event_tick(&mut self) {
        let Some(ev) = self.events.clone() else {
            return;
        };
        ev.emit(&Event::Bytes {
            in_bytes: self.in_bytes,
            out_bytes: self.out_bytes,
        });
        let idle = self.last_activity.elapsed().as_millis() as u64;
        if idle >= STALL_THRESHOLD_MS && !self.stall_reported {
            ev.emit(&Event::Stall { idle_ms: idle });
            self.stall_reported = true;
        }
    }

    /// Whether the held packet can be sent now. Datagrams are unmetered;
    /// stream packets need credit for their 2-byte length prefix plus payload.
    fn can_send_now(&self, pkt: &Bytes) -> bool {
        if self.use_datagrams {
            return true;
        }
        let framed = pkt.len().saturating_add(2);
        self.driver.can_send_stream(self.stream_id, framed)
    }

    async fn handle_vpn_event(&mut self, event: RecvEvent) -> Result<(), MultiplexerError> {
        match event {
            RecvEvent::Datagram(df) => {
                // Datagram framing perfectly aligns with IP packtes.
                self.in_bytes += df.data.len() as u64;
                self.tun.write_packet(Bytes::from(df.data)).await?;
            }
            RecvEvent::StreamData { frame, .. } => {
                // Packets might be fragmented across stream frames.
                self.recv_buffer.extend_from_slice(&frame.data);
                self.flush_stream_buffer().await?;
            }
            RecvEvent::Closed { .. } => {
                return Err(MultiplexerError::Internal(
                    "Peer closed session".to_string(),
                ));
            }
            // Other control events are ignored or handled internally by SessionDriver.
            _ => {}
        }
        Ok(())
    }

    async fn flush_stream_buffer(&mut self) -> Result<(), MultiplexerError> {
        loop {
            if self.recv_buffer.len() < 2 {
                break;
            }
            let mut len_bytes = [0u8; 2];
            len_bytes.copy_from_slice(&self.recv_buffer[..2]);
            let packet_len = u16::from_be_bytes(len_bytes) as usize;

            if self.recv_buffer.len() < 2 + packet_len {
                // Wait for more data
                break;
            }

            self.recv_buffer.advance(2); // Consume length
            let pkt = self.recv_buffer.split_to(packet_len);

            // Inject into TUN
            self.in_bytes += pkt.len() as u64;
            self.tun.write_packet(pkt.freeze()).await?;
        }
        Ok(())
    }

    /// Send one outbound packet. Callers gate stream sends on [`can_send_now`]
    /// so the stream path never exceeds its send credit here.
    async fn send_out(&mut self, pkt: Bytes) -> Result<(), MultiplexerError> {
        if self.use_datagrams {
            // Unreliable direct injection; class ID 0 for default IP traffic.
            self.out_bytes += pkt.len() as u64;
            self.driver.send_datagram(0, &pkt).await?;
        } else {
            // Reliable continuous stream: length-prefix wrapper.
            if pkt.len() > u16::MAX as usize {
                return Err(MultiplexerError::Internal(
                    "Packet exceeds 64KB".to_string(),
                ));
            }
            let mut out = BytesMut::with_capacity(2 + pkt.len());
            out.put_u16(pkt.len() as u16);
            out.put_slice(&pkt);

            self.out_bytes += pkt.len() as u64;
            self.driver.send_stream(self.stream_id, &out, false).await?;
        }
        Ok(())
    }
}
