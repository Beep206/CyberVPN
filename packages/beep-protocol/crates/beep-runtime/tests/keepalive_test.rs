//! The runtime declares a silent peer dead after the idle deadline, so the
//! client can reconnect.

use std::io;
use std::time::Duration;

use beep_core::key_schedule::derive_session_keys;
use beep_runtime::{KeepaliveConfig, MultiplexerError, RuntimeMultiplexer, TunDevice};
use beep_session::SessionDriver;
use beep_transport::{CoverConn, TransportCapabilities, TransportError};
use bytes::Bytes;

/// A transport that accepts sends but never delivers anything.
struct DeadConn;

impl CoverConn for DeadConn {
    async fn send(&mut self, _data: Bytes) -> Result<(), TransportError> {
        Ok(())
    }
    async fn recv(&mut self) -> Result<Option<Bytes>, TransportError> {
        std::future::pending().await
    }
    fn transport_binding(&self) -> [u8; 32] {
        [0u8; 32]
    }
    fn capabilities(&self) -> TransportCapabilities {
        TransportCapabilities {
            supports_streams: true,
            supports_datagrams: false,
            supports_migration: false,
        }
    }
}

/// A TUN that never produces a packet.
struct SilentTun;

#[async_trait::async_trait]
impl TunDevice for SilentTun {
    async fn read_packet(&mut self) -> io::Result<Bytes> {
        std::future::pending().await
    }
    async fn write_packet(&mut self, _pkt: Bytes) -> io::Result<()> {
        Ok(())
    }
}

#[tokio::test]
async fn keepalive_idle_timeout_fires() {
    let keys = derive_session_keys(&[1u8; 32], &[2u8; 32]);
    let driver = SessionDriver::new(DeadConn, &keys, true);
    let cfg = KeepaliveConfig {
        interval: Duration::from_millis(40),
        idle_timeout: Duration::from_millis(120),
    };
    let mut mux = RuntimeMultiplexer::new(driver, SilentTun, false).with_keepalive(cfg);

    let res = tokio::time::timeout(Duration::from_secs(2), mux.run()).await;
    match res {
        Ok(Err(MultiplexerError::IdleTimeout)) => {}
        Ok(other) => panic!("expected IdleTimeout, got {other:?}"),
        Err(_) => panic!("run did not return within 2s (idle timeout never fired)"),
    }
}
