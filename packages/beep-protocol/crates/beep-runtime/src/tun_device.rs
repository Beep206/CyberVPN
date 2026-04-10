use bytes::Bytes;
use std::io;

/// An abstraction over the OS's TUN networking device.
/// 
/// `beep-runtime` uses this trait instead of reading directly from the platform TUN.
/// This allows it to decouple from OS-specific crates (like `tokio-tun` on Linux
/// or `wintun` on Windows). It also enables seamless cross-platform unit testing
/// through mock physical devices that implement this trait.
#[async_trait::async_trait]
pub trait TunDevice: Send + Sync {
    /// Read an entire IPv4 or IPv6 packet from the IP interface's TX queue.
    /// Returns the raw IP packet encapsulating the upper layers.
    async fn read_packet(&mut self) -> io::Result<Bytes>;

    /// Inject an entire IPv4 or IPv6 packet into the IP interface's RX queue.
    /// The OS will process this packet as if it arrived from a physical network.
    async fn write_packet(&mut self, pkt: Bytes) -> io::Result<()>;
}
