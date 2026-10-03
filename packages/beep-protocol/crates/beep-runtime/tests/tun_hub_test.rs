//! Routing test for the shared TUN hub: two sessions, two inner addresses,
//! and every inbound packet reaches exactly the session that owns its
//! destination. This is the protocol-level core of the stage-3 checkpoint
//! "two clients download different files and the checksums match" — it proves
//! a packet for one client can never be delivered to the other.

use beep_runtime::tun_hub;
use beep_runtime::TunDevice;
use bytes::Bytes;
use std::io;
use std::time::Duration;
use tokio::sync::mpsc;

/// A fake physical TUN: the test pushes inbound packets in through `inbound`,
/// and whatever the hub writes out is captured on `outbound`.
struct MockTun {
    inbound: mpsc::Receiver<Bytes>,
    outbound: mpsc::UnboundedSender<Bytes>,
}

#[async_trait::async_trait]
impl TunDevice for MockTun {
    async fn read_packet(&mut self) -> io::Result<Bytes> {
        self.inbound
            .recv()
            .await
            .ok_or_else(|| io::Error::new(io::ErrorKind::BrokenPipe, "mock closed"))
    }

    async fn write_packet(&mut self, pkt: Bytes) -> io::Result<()> {
        let _ = self.outbound.send(pkt);
        Ok(())
    }
}

/// Minimal IPv4 packet: a 20-byte header with the version nibble set and the
/// given source/destination addresses, plus one marker byte of payload. Only
/// the version nibble and the address fields matter to the hub.
fn ipv4_packet(src: [u8; 4], dst: [u8; 4], marker: u8) -> Bytes {
    let mut pkt = vec![0u8; 21];
    pkt[0] = 0x45; // version 4, IHL 5
    pkt[12..16].copy_from_slice(&src);
    pkt[16..20].copy_from_slice(&dst);
    pkt[20] = marker;
    Bytes::from(pkt)
}

#[tokio::test]
async fn inbound_packets_route_to_the_session_owning_the_destination() {
    let (inbound_tx, inbound_rx) = mpsc::channel::<Bytes>(16);
    let (outbound_tx, mut outbound_rx) = mpsc::unbounded_channel::<Bytes>();
    let mock = MockTun {
        inbound: inbound_rx,
        outbound: outbound_tx,
    };

    let (hub, handle) = tun_hub(mock, 64);
    let hub_task = tokio::spawn(hub.run());

    let mut client_a = handle.register(8);
    let mut client_b = handle.register(8);

    // Each client sends one packet outbound; the hub learns its source
    // address. A = 10.8.0.2, B = 10.8.0.3.
    client_a
        .write_packet(ipv4_packet([10, 8, 0, 2], [93, 184, 216, 34], 0xA1))
        .await
        .unwrap();
    client_b
        .write_packet(ipv4_packet([10, 8, 0, 3], [93, 184, 216, 34], 0xB1))
        .await
        .unwrap();

    // Both outbound packets reached the single physical device.
    let first = outbound_rx.recv().await.unwrap();
    let second = outbound_rx.recv().await.unwrap();
    let markers: Vec<u8> = [first, second].iter().map(|p| p[20]).collect();
    assert!(markers.contains(&0xA1) && markers.contains(&0xB1));

    assert_eq!(handle.route_count(), 2, "both addresses should be bound");
    assert_eq!(client_a.bound_address().unwrap().to_string(), "10.8.0.2");
    assert_eq!(client_b.bound_address().unwrap().to_string(), "10.8.0.3");

    // Inbound replies: one for each client's address, plus one for an address
    // nobody owns (must be dropped, delivered to neither).
    inbound_tx
        .send(ipv4_packet([93, 184, 216, 34], [10, 8, 0, 3], 0xB2))
        .await
        .unwrap();
    inbound_tx
        .send(ipv4_packet([93, 184, 216, 34], [10, 8, 0, 2], 0xA2))
        .await
        .unwrap();
    inbound_tx
        .send(ipv4_packet([93, 184, 216, 34], [10, 8, 0, 9], 0xFF))
        .await
        .unwrap();

    // A receives only its own packet; B receives only its own.
    let a_pkt = tokio::time::timeout(Duration::from_secs(2), client_a.read_packet())
        .await
        .expect("client A should receive its reply")
        .unwrap();
    assert_eq!(a_pkt[20], 0xA2, "A got the wrong packet");
    assert_eq!(&a_pkt[16..20], &[10, 8, 0, 2]);

    let b_pkt = tokio::time::timeout(Duration::from_secs(2), client_b.read_packet())
        .await
        .expect("client B should receive its reply")
        .unwrap();
    assert_eq!(b_pkt[20], 0xB2, "B got the wrong packet");
    assert_eq!(&b_pkt[16..20], &[10, 8, 0, 3]);

    // Neither client should have a second packet waiting (the unowned .9
    // packet was dropped, and no cross-delivery happened).
    assert!(
        tokio::time::timeout(Duration::from_millis(300), client_a.read_packet())
            .await
            .is_err(),
        "A should have no further packet"
    );
    assert!(
        tokio::time::timeout(Duration::from_millis(300), client_b.read_packet())
            .await
            .is_err(),
        "B should have no further packet"
    );

    // Dropping a session frees its address so the hub can reclaim it.
    drop(client_a);
    assert_eq!(handle.route_count(), 1, "A's address should be released");

    drop(client_b);
    drop(handle);
    drop(inbound_tx);
    // With every handle and session gone, the hub shuts down cleanly.
    let _ = tokio::time::timeout(Duration::from_secs(2), hub_task).await;
}
