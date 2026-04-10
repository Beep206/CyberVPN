use crate::tun_device::TunDevice;
use beep_core::mux::StreamId;
use beep_session::{DriverError, RecvEvent, SessionDriver};
use beep_transport::CoverConn;
use bytes::{Buf, BufMut, Bytes, BytesMut};
use std::io;

#[derive(Debug, thiserror::Error)]
pub enum MultiplexerError {
    #[error("Session driver error: {0}")]
    Driver(#[from] DriverError),
    #[error("TUN device error: {0}")]
    Tun(#[from] io::Error),
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
        }
    }

    /// Run the multiplexer loop until closure or error.
    pub async fn run(&mut self) -> Result<(), MultiplexerError> {
        loop {
            tokio::select! {
                // VPN ➔ TUN (read from session -> inject to local OS)
                event_res = self.driver.recv() => {
                    let event = event_res?;
                    self.handle_vpn_event(event).await?;
                }
                
                // TUN ➔ VPN (intercept from local OS -> encrypt to peer)
                pkt_res = self.tun.read_packet() => {
                    let pkt = pkt_res?;
                    self.handle_tun_packet(pkt).await?;
                }
            }
        }
    }

    async fn handle_vpn_event(&mut self, event: RecvEvent) -> Result<(), MultiplexerError> {
        match event {
            RecvEvent::Datagram(df) => {
                // Datagram framing perfectly aligns with IP packtes.
                self.tun.write_packet(Bytes::from(df.data)).await?;
            }
            RecvEvent::StreamData { frame, .. } => {
                // Packets might be fragmented across stream frames.
                self.recv_buffer.extend_from_slice(&frame.data);
                self.flush_stream_buffer().await?;
            }
            RecvEvent::Closed { .. } => {
                return Err(MultiplexerError::Internal("Peer closed session".to_string()));
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
            self.tun.write_packet(pkt.freeze()).await?;
        }
        Ok(())
    }

    async fn handle_tun_packet(&mut self, pkt: Bytes) -> Result<(), MultiplexerError> {
        if self.use_datagrams {
            // Unreliable direct injection
            // Class ID 0 assumed for default IP traffic
            self.driver.send_datagram(0, &pkt).await?;
        } else {
            // Reliable continuous stream: length-prefix wrapper
            if pkt.len() > u16::MAX as usize {
                return Err(MultiplexerError::Internal("Packet exceeds 64KB".to_string()));
            }
            let mut out = BytesMut::with_capacity(2 + pkt.len());
            out.put_u16(pkt.len() as u16);
            out.put_slice(&pkt);

            self.driver.send_stream(self.stream_id, &out, false).await?;
        }
        Ok(())
    }
}
