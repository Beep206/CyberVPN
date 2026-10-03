//! Two authenticated clients, one node, one physical device — end to end.
//!
//! This is the integrated form of the stage-3 checkpoint "two clients download
//! different files and the checksums match". Two real WSS client sessions each
//! run a full [`RuntimeMultiplexer`]; on the node both sessions share one
//! physical device through a [`TunHub`](beep_runtime::TunHub). The test drives
//! a distinct payload through each session in both directions and asserts every
//! packet reaches exactly the intended client — a packet for one client is
//! never delivered to the other. Both sessions authenticate with a token and a
//! pinned node key, so the stage-3 handshake runs concurrently for both.

use beep_core::key_schedule::{generate_node_keypair, SessionKeys};
use beep_core::session::{ClientConfig, ClientHandshake, ServerConfig, ServerHandshake};
use beep_core_types::{CapabilityId, CoreVersion};
use beep_cover_wss::{accept_wss, connect_wss, ALPN_HTTP11};
use beep_runtime::{tun_hub, RuntimeMultiplexer, TunDevice, TunHubHandle};
use beep_session::SessionDriver;
use beep_transport::CoverConn;
use bytes::Bytes;
use std::io;
use std::net::Ipv4Addr;
use std::sync::Arc;
use std::time::Duration;
use tokio::net::TcpListener;
use tokio::sync::mpsc;
use tokio_rustls::TlsAcceptor;

// ── Mock device ──────────────────────────────────────────────────────────

struct MockTun {
    rx: mpsc::Receiver<Bytes>,
    tx: mpsc::Sender<Bytes>,
}

#[async_trait::async_trait]
impl TunDevice for MockTun {
    async fn read_packet(&mut self) -> io::Result<Bytes> {
        self.rx
            .recv()
            .await
            .ok_or_else(|| io::Error::new(io::ErrorKind::BrokenPipe, "tun closed"))
    }
    async fn write_packet(&mut self, pkt: Bytes) -> io::Result<()> {
        self.tx
            .send(pkt)
            .await
            .map_err(|_| io::Error::new(io::ErrorKind::BrokenPipe, "tun closed"))
    }
}

/// A minimal IPv4 packet carrying a marker and a payload the test can checksum.
fn ipv4_packet(src: [u8; 4], dst: [u8; 4], marker: u8, payload: &[u8]) -> Bytes {
    let mut pkt = vec![0u8; 20];
    pkt[0] = 0x45;
    pkt[12..16].copy_from_slice(&src);
    pkt[16..20].copy_from_slice(&dst);
    pkt.push(marker);
    pkt.extend_from_slice(payload);
    Bytes::from(pkt)
}

fn checksum(pkt: &[u8]) -> u32 {
    pkt.iter().map(|&b| b as u32).sum()
}

// ── TLS helpers ──────────────────────────────────────────────────────────

fn generate_test_certs() -> (
    Vec<rustls::pki_types::CertificateDer<'static>>,
    rustls::pki_types::PrivateKeyDer<'static>,
    Vec<u8>,
) {
    let cert = rcgen::generate_simple_self_signed(vec!["localhost".to_string()]).unwrap();
    let raw_der = cert.cert.der().to_vec();
    let cert_der = rustls::pki_types::CertificateDer::from(raw_der.clone());
    let key_der =
        rustls::pki_types::PrivateKeyDer::try_from(cert.key_pair.serialize_der()).unwrap();
    (vec![cert_der], key_der, raw_der)
}

fn client_tls_config() -> rustls::ClientConfig {
    let mut config = rustls::ClientConfig::builder()
        .dangerous()
        .with_custom_certificate_verifier(Arc::new(InsecureVerifier))
        .with_no_client_auth();
    config.alpn_protocols = vec![ALPN_HTTP11.to_vec()];
    config
}

#[derive(Debug)]
struct InsecureVerifier;

impl rustls::client::danger::ServerCertVerifier for InsecureVerifier {
    fn verify_server_cert(
        &self,
        _e: &rustls::pki_types::CertificateDer<'_>,
        _i: &[rustls::pki_types::CertificateDer<'_>],
        _s: &rustls::pki_types::ServerName<'_>,
        _o: &[u8],
        _n: rustls::pki_types::UnixTime,
    ) -> Result<rustls::client::danger::ServerCertVerified, rustls::Error> {
        Ok(rustls::client::danger::ServerCertVerified::assertion())
    }
    fn verify_tls12_signature(
        &self,
        _m: &[u8],
        _c: &rustls::pki_types::CertificateDer<'_>,
        _d: &rustls::DigitallySignedStruct,
    ) -> Result<rustls::client::danger::HandshakeSignatureValid, rustls::Error> {
        Ok(rustls::client::danger::HandshakeSignatureValid::assertion())
    }
    fn verify_tls13_signature(
        &self,
        _m: &[u8],
        _c: &rustls::pki_types::CertificateDer<'_>,
        _d: &rustls::DigitallySignedStruct,
    ) -> Result<rustls::client::danger::HandshakeSignatureValid, rustls::Error> {
        Ok(rustls::client::danger::HandshakeSignatureValid::assertion())
    }
    fn supported_verify_schemes(&self) -> Vec<rustls::SignatureScheme> {
        rustls::crypto::ring::default_provider()
            .signature_verification_algorithms
            .supported_schemes()
    }
}

// ── Authenticated handshake helpers ──────────────────────────────────────

async fn server_handshake<C: CoverConn>(conn: &mut C, node_secret: [u8; 32]) -> SessionKeys {
    let binding = conn.transport_binding();
    let mut hs = ServerHandshake::new(ServerConfig {
        transport_binding: binding,
        capabilities: vec![CapabilityId::Streams, CapabilityId::Rekey],
        node_identity: b"beep-node".to_vec(),
        node_signing_key: Some(node_secret),
        ..Default::default()
    });
    let init = conn.recv().await.unwrap().unwrap();
    hs.process_client_init(&init).unwrap();
    let si = hs.create_server_init().unwrap();
    conn.send(Bytes::from(si)).await.unwrap();
    let cf = conn.recv().await.unwrap().unwrap();
    hs.process_client_finish(&cf).unwrap();
    let (sf, keys) = hs.create_server_finish().unwrap();
    conn.send(Bytes::from(sf)).await.unwrap();
    keys
}

async fn client_handshake<C: CoverConn>(
    conn: &mut C,
    expected_key: [u8; 32],
    token: &[u8],
) -> SessionKeys {
    let binding = conn.transport_binding();
    let mut hs = ClientHandshake::new(ClientConfig {
        core_version: CoreVersion::V1,
        transport_binding: binding,
        capabilities: vec![CapabilityId::Streams, CapabilityId::Rekey],
        auth_method: 0x01,
        auth_data: token.to_vec(),
        expected_node_key: Some(expected_key),
    });
    let ci = hs.create_client_init().unwrap();
    conn.send(Bytes::from(ci)).await.unwrap();
    let si = conn.recv().await.unwrap().unwrap();
    hs.process_server_init(&si).unwrap();
    let cf = hs.create_client_finish().unwrap();
    conn.send(Bytes::from(cf)).await.unwrap();
    let sf = conn.recv().await.unwrap().unwrap();
    hs.process_server_finish(&sf).unwrap()
}

// ── Test ──────────────────────────────────────────────────────────────────

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn two_clients_share_one_node_without_crossing_traffic() {
    let _ = rustls::crypto::ring::default_provider().install_default();
    let (node_secret, node_public) = generate_node_keypair();

    let (certs, key, raw_cert_der) = generate_test_certs();
    let mut server_tls = rustls::ServerConfig::builder()
        .with_no_client_auth()
        .with_single_cert(certs, key)
        .unwrap();
    server_tls.alpn_protocols = vec![ALPN_HTTP11.to_vec()];
    let acceptor = TlsAcceptor::from(Arc::new(server_tls));

    let listener = TcpListener::bind((Ipv4Addr::LOCALHOST, 0)).await.unwrap();
    let server_addr = listener.local_addr().unwrap();

    // The node's single physical device, owned by the hub. `phys_read_tx`
    // injects inbound replies (as if from the internet); `phys_write_rx`
    // captures what the sessions send out.
    let (phys_read_tx, phys_read_rx) = mpsc::channel::<Bytes>(64);
    let (phys_write_tx, mut phys_write_rx) = mpsc::channel::<Bytes>(64);
    let phys = MockTun {
        rx: phys_read_rx,
        tx: phys_write_tx,
    };
    let (hub, hub_handle) = tun_hub(phys, 256);
    tokio::spawn(hub.run());

    // Node accept loop: two sessions, both sharing the one hub.
    let accept_hub = hub_handle.clone();
    let accept_cert = raw_cert_der.clone();
    tokio::spawn(async move {
        for _ in 0..2 {
            let (tcp, _) = listener.accept().await.unwrap();
            let acceptor = acceptor.clone();
            let cert = accept_cert.clone();
            let hub: TunHubHandle = accept_hub.clone();
            tokio::spawn(async move {
                let tls = acceptor.accept(tcp).await.unwrap();
                let mut conn = accept_wss(tls, &cert).await.unwrap();
                let keys = server_handshake(&mut conn, node_secret).await;
                let session_tun = hub.register(256);
                let driver = SessionDriver::new(conn, &keys, false);
                let mut mux = RuntimeMultiplexer::new(driver, session_tun, false);
                let _ = mux.run().await;
            });
        }
    });

    // Bring up two client sessions, each with its own client-side device.
    let mut clients = Vec::new();
    for _ in 0..2 {
        let (os_tx, tun_rx) = mpsc::channel::<Bytes>(64); // test -> client (outbound)
        let (tun_tx, os_rx) = mpsc::channel::<Bytes>(64); // client -> test (delivered)
        let client_tun = MockTun {
            rx: tun_rx,
            tx: tun_tx,
        };
        let mut conn = connect_wss(server_addr, "localhost", "/ws", client_tls_config())
            .await
            .unwrap();
        let keys = client_handshake(&mut conn, node_public, b"shared-token").await;
        tokio::spawn(async move {
            let driver = SessionDriver::new(conn, &keys, true);
            let mut mux = RuntimeMultiplexer::new(driver, client_tun, false);
            let _ = mux.run().await;
        });
        clients.push((os_tx, os_rx));
    }

    let a_ip = [10, 8, 0, 2];
    let b_ip = [10, 8, 0, 3];
    let remote = [93, 184, 216, 34];

    // Each client sends an outbound packet; the hub learns its source address.
    let a_out = ipv4_packet(a_ip, remote, 0xA0, b"client-A-request");
    let b_out = ipv4_packet(b_ip, remote, 0xB0, b"client-B-request");
    clients[0].0.send(a_out.clone()).await.unwrap();
    clients[1].0.send(b_out.clone()).await.unwrap();

    // Both outbound packets reach the single physical device, intact.
    let mut seen = std::collections::HashMap::new();
    for _ in 0..2 {
        let pkt = tokio::time::timeout(Duration::from_secs(5), phys_write_rx.recv())
            .await
            .expect("node should forward both clients' packets")
            .unwrap();
        seen.insert(pkt[20], pkt);
    }
    assert_eq!(
        checksum(&seen[&0xA0]),
        checksum(&a_out),
        "A's packet garbled"
    );
    assert_eq!(
        checksum(&seen[&0xB0]),
        checksum(&b_out),
        "B's packet garbled"
    );

    // Wait until both inner addresses are bound before routing replies.
    for _ in 0..50 {
        if hub_handle.route_count() >= 2 {
            break;
        }
        tokio::time::sleep(Duration::from_millis(20)).await;
    }
    assert_eq!(
        hub_handle.route_count(),
        2,
        "both clients should be routable"
    );

    // Inject a reply for each client. The hub must route each to the session
    // owning that destination address — and to no other.
    let a_reply = ipv4_packet(remote, a_ip, 0xA1, b"reply-for-A-only");
    let b_reply = ipv4_packet(remote, b_ip, 0xB1, b"reply-for-B-only");
    phys_read_tx.send(a_reply.clone()).await.unwrap();
    phys_read_tx.send(b_reply.clone()).await.unwrap();

    let a_got = tokio::time::timeout(Duration::from_secs(5), clients[0].1.recv())
        .await
        .expect("client A should receive its reply")
        .unwrap();
    assert_eq!(a_got[20], 0xA1, "client A received the wrong packet");
    assert_eq!(checksum(&a_got), checksum(&a_reply));

    let b_got = tokio::time::timeout(Duration::from_secs(5), clients[1].1.recv())
        .await
        .expect("client B should receive its reply")
        .unwrap();
    assert_eq!(b_got[20], 0xB1, "client B received the wrong packet");
    assert_eq!(checksum(&b_got), checksum(&b_reply));

    // Neither client should have a second (crossed) packet waiting.
    assert!(
        tokio::time::timeout(Duration::from_millis(300), clients[0].1.recv())
            .await
            .is_err(),
        "client A should have no extra packet"
    );
    assert!(
        tokio::time::timeout(Duration::from_millis(300), clients[1].1.recv())
            .await
            .is_err(),
        "client B should have no extra packet"
    );
}
