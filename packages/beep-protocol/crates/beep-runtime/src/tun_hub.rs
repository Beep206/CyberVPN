//! Sharing one physical TUN device across many sessions on the node.
//!
//! The per-session [`RuntimeMultiplexer`](crate::RuntimeMultiplexer) owns its
//! own [`TunDevice`]. On a node serving several clients that cannot be the one
//! physical device: if every session read the same device, an inbound packet
//! could be pulled by whichever session's reader happened to win, and so be
//! delivered to the wrong client. (That is the defect the stage-3 plan calls
//! out.)
//!
//! [`TunHub`] fixes it with a single reader. One task owns the physical device,
//! reads every inbound IP packet, and forwards it to the session that owns the
//! destination address. Each session gets a [`SessionTun`] endpoint that looks
//! like an ordinary `TunDevice` to the multiplexer: its reads come from the
//! hub's queue for that session, and its writes funnel back to the one physical
//! device through the hub's single writer.
//!
//! Addresses are learned, not pre-assigned: a session claims the source
//! address of the first inner packet its client sends, and inbound packets for
//! that address route back to it. A second session cannot claim an address
//! already held, so two clients can never cross traffic.

use crate::tun_device::TunDevice;
use bytes::Bytes;
use std::collections::HashMap;
use std::io;
use std::net::Ipv4Addr;
use std::sync::{Arc, Mutex};
use tokio::sync::mpsc;

/// Destination-address → session-inbound-queue table, shared between the hub
/// reader and every session (which self-registers on its learned address).
type Routes = Arc<Mutex<HashMap<Ipv4Addr, mpsc::Sender<Bytes>>>>;

/// Read the source IPv4 address of a raw IP packet (bytes 12..16).
fn ipv4_src(pkt: &[u8]) -> Option<Ipv4Addr> {
    ipv4_addr_at(pkt, 12)
}

/// Read the destination IPv4 address of a raw IP packet (bytes 16..20).
fn ipv4_dst(pkt: &[u8]) -> Option<Ipv4Addr> {
    ipv4_addr_at(pkt, 16)
}

fn ipv4_addr_at(pkt: &[u8], offset: usize) -> Option<Ipv4Addr> {
    // Need a full IPv4 header, and the version nibble must say IPv4. IPv6 is
    // not routed by this hub (the tunnel's inner network is IPv4).
    if pkt.len() < 20 || (pkt[0] >> 4) != 4 {
        return None;
    }
    Some(Ipv4Addr::new(
        pkt[offset],
        pkt[offset + 1],
        pkt[offset + 2],
        pkt[offset + 3],
    ))
}

/// Owns the physical TUN device and routes between it and the sessions.
pub struct TunHub<T: TunDevice> {
    tun: T,
    routes: Routes,
    outbound_rx: mpsc::Receiver<Bytes>,
}

/// Cheap handle used to register new sessions against a running [`TunHub`].
#[derive(Clone)]
pub struct TunHubHandle {
    routes: Routes,
    outbound_tx: mpsc::Sender<Bytes>,
}

/// Create a hub around `tun`. `outbound_capacity` bounds packets queued from
/// all sessions toward the device before back-pressure/drops kick in.
pub fn tun_hub<T: TunDevice>(tun: T, outbound_capacity: usize) -> (TunHub<T>, TunHubHandle) {
    let routes: Routes = Arc::new(Mutex::new(HashMap::new()));
    let (outbound_tx, outbound_rx) = mpsc::channel(outbound_capacity.max(1));
    (
        TunHub {
            tun,
            routes: routes.clone(),
            outbound_rx,
        },
        TunHubHandle {
            routes,
            outbound_tx,
        },
    )
}

impl TunHubHandle {
    /// Create a per-session TUN endpoint. `inbound_capacity` bounds packets
    /// queued toward this one session; when full, further inbound packets for
    /// it are dropped (as a real device drops under overload) rather than
    /// stalling the shared reader.
    pub fn register(&self, inbound_capacity: usize) -> SessionTun {
        let (inbound_tx, inbound_rx) = mpsc::channel(inbound_capacity.max(1));
        SessionTun {
            inbound_tx,
            inbound_rx,
            outbound_tx: self.outbound_tx.clone(),
            routes: self.routes.clone(),
            bound: None,
            learned: false,
        }
    }

    /// Number of addresses currently bound to a session. Test/metrics aid.
    pub fn route_count(&self) -> usize {
        self.routes.lock().expect("routes mutex not poisoned").len()
    }
}

impl<T: TunDevice> TunHub<T> {
    /// Run the hub until the device errors or all sessions have gone away.
    ///
    /// One select loop owns both directions, so the physical device is never
    /// touched concurrently: inbound reads route by destination address;
    /// outbound packets drain to the device. The read future and the outbound
    /// handler borrow disjoint fields, so neither direction blocks the other
    /// from being polled.
    pub async fn run(mut self) -> io::Result<()> {
        loop {
            tokio::select! {
                read = self.tun.read_packet() => {
                    let pkt = read?;
                    if let Some(dst) = ipv4_dst(&pkt) {
                        let sender = self
                            .routes
                            .lock()
                            .expect("routes mutex not poisoned")
                            .get(&dst)
                            .cloned();
                        if let Some(tx) = sender {
                            // Drop on a full or closed per-session queue rather
                            // than stalling every other session.
                            let _ = tx.try_send(pkt);
                        }
                        // No route for this destination: drop silently, as a
                        // host would for an address it does not own.
                    }
                }
                outbound = self.outbound_rx.recv() => {
                    match outbound {
                        Some(pkt) => self.tun.write_packet(pkt).await?,
                        // Every session (and handle) is gone; nothing more can
                        // arrive. Shut the hub down cleanly.
                        None => return Ok(()),
                    }
                }
            }
        }
    }
}

/// A per-session virtual TUN endpoint handed to a [`RuntimeMultiplexer`].
///
/// Reads come from the hub (packets whose destination is this session's
/// learned address); writes go to the hub's single device writer. On its first
/// write it learns its client's source address and registers it so inbound
/// packets route back.
pub struct SessionTun {
    inbound_tx: mpsc::Sender<Bytes>,
    inbound_rx: mpsc::Receiver<Bytes>,
    outbound_tx: mpsc::Sender<Bytes>,
    routes: Routes,
    bound: Option<Ipv4Addr>,
    learned: bool,
}

impl SessionTun {
    /// The inner address this session claimed, once learned.
    pub fn bound_address(&self) -> Option<Ipv4Addr> {
        self.bound
    }

    /// On the first outbound packet, claim the client's source address so
    /// replies route back here. If another session already holds it, this one
    /// gets no inbound route (it cannot steal the other's traffic); with
    /// distinct client addresses that never happens.
    fn learn_from_outbound(&mut self, pkt: &[u8]) {
        if self.learned {
            return;
        }
        if let Some(src) = ipv4_src(pkt) {
            self.learned = true;
            let mut table = self.routes.lock().expect("routes mutex not poisoned");
            if let std::collections::hash_map::Entry::Vacant(slot) = table.entry(src) {
                slot.insert(self.inbound_tx.clone());
                self.bound = Some(src);
            } else {
                tracing::warn!(
                    address = %src,
                    "inner address already owned by another session; not routing replies here"
                );
            }
        }
    }
}

impl Drop for SessionTun {
    fn drop(&mut self) {
        if let Some(addr) = self.bound {
            self.routes
                .lock()
                .expect("routes mutex not poisoned")
                .remove(&addr);
        }
    }
}

#[async_trait::async_trait]
impl TunDevice for SessionTun {
    async fn read_packet(&mut self) -> io::Result<Bytes> {
        self.inbound_rx
            .recv()
            .await
            .ok_or_else(|| io::Error::new(io::ErrorKind::BrokenPipe, "TUN hub closed this session"))
    }

    async fn write_packet(&mut self, pkt: Bytes) -> io::Result<()> {
        self.learn_from_outbound(&pkt);
        self.outbound_tx
            .send(pkt)
            .await
            .map_err(|_| io::Error::new(io::ErrorKind::BrokenPipe, "TUN hub writer gone"))
    }
}
