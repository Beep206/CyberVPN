use beep_core::key_schedule::SessionKeys;
use beep_core::session::{ClientConfig, ClientHandshake, ServerConfig, ServerHandshake};
use beep_core_types::{CapabilityId, CoreVersion};
use beep_cover_wss::{accept_wss, connect_wss, BEEP_ALPN};
use beep_runtime::{RuntimeMultiplexer, TunDevice};
use beep_session::SessionDriver;
use beep_transport::CoverConn;
use bytes::Bytes;
use std::net::Ipv4Addr;
use std::sync::Arc;
use tokio::net::TcpListener;
use tokio::sync::mpsc;
use tokio_rustls::TlsAcceptor;
use std::io;

// ── Mock Tun ────────────────────────────────────────────────────────────

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

// ── TLS helpers ─────────────────────────────────────────────────────────

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

fn server_tls_config(
    certs: Vec<rustls::pki_types::CertificateDer<'static>>,
    key: rustls::pki_types::PrivateKeyDer<'static>,
) -> rustls::ServerConfig {
    let mut config = rustls::ServerConfig::builder()
        .with_no_client_auth()
        .with_single_cert(certs, key)
        .unwrap();
    config.alpn_protocols = vec![BEEP_ALPN.to_vec()];
    config
}

fn client_tls_config() -> rustls::ClientConfig {
    let mut config = rustls::ClientConfig::builder()
        .dangerous()
        .with_custom_certificate_verifier(Arc::new(InsecureVerifier))
        .with_no_client_auth();
    config.alpn_protocols = vec![BEEP_ALPN.to_vec()];
    config
}

#[derive(Debug)]
struct InsecureVerifier;

impl rustls::client::danger::ServerCertVerifier for InsecureVerifier {
    fn verify_server_cert(
        &self,
        _end_entity: &rustls::pki_types::CertificateDer<'_>,
        _intermediates: &[rustls::pki_types::CertificateDer<'_>],
        _server_name: &rustls::pki_types::ServerName<'_>,
        _ocsp_response: &[u8],
        _now: rustls::pki_types::UnixTime,
    ) -> Result<rustls::client::danger::ServerCertVerified, rustls::Error> {
        Ok(rustls::client::danger::ServerCertVerified::assertion())
    }
    fn verify_tls12_signature(
        &self,
        _message: &[u8],
        _cert: &rustls::pki_types::CertificateDer<'_>,
        _dss: &rustls::DigitallySignedStruct,
    ) -> Result<rustls::client::danger::HandshakeSignatureValid, rustls::Error> {
        Ok(rustls::client::danger::HandshakeSignatureValid::assertion())
    }
    fn verify_tls13_signature(
        &self,
        _message: &[u8],
        _cert: &rustls::pki_types::CertificateDer<'_>,
        _dss: &rustls::DigitallySignedStruct,
    ) -> Result<rustls::client::danger::HandshakeSignatureValid, rustls::Error> {
        Ok(rustls::client::danger::HandshakeSignatureValid::assertion())
    }
    fn supported_verify_schemes(&self) -> Vec<rustls::SignatureScheme> {
        rustls::crypto::ring::default_provider()
            .signature_verification_algorithms
            .supported_schemes()
    }
}

// ── Generic beep handshake logic over CoverConn ─────────────────────────

async fn do_beep_handshake<C: CoverConn>(
    conn: &mut C,
    is_initiator: bool,
    binding: [u8; 32],
) -> SessionKeys {
    if is_initiator {
        let mut hs = ClientHandshake::new(ClientConfig {
            core_version: CoreVersion::V1,
            transport_binding: binding,
            capabilities: vec![CapabilityId::Streams, CapabilityId::Rekey],
            auth_method: 0x01,
            auth_data: vec![0xAA; 16],
        });
        let client_init = hs.create_client_init().unwrap();
        conn.send(Bytes::from(client_init)).await.unwrap();
        let data = conn.recv().await.unwrap().unwrap();
        hs.process_server_init(&data).unwrap();
        let client_finish = hs.create_client_finish().unwrap();
        conn.send(Bytes::from(client_finish)).await.unwrap();
        let data = conn.recv().await.unwrap().unwrap();
        hs.process_server_finish(&data).unwrap()
    } else {
        let mut hs = ServerHandshake::new(ServerConfig {
            supported_versions: vec![CoreVersion::V1],
            transport_binding: binding,
            capabilities: vec![CapabilityId::Streams, CapabilityId::Rekey],
            node_identity: b"test-node-wss".to_vec(),
            policy_epoch: 1,
        });
        let data = conn.recv().await.unwrap().unwrap();
        hs.process_client_init(&data).unwrap();
        let server_init = hs.create_server_init().unwrap();
        conn.send(Bytes::from(server_init)).await.unwrap();
        let data = conn.recv().await.unwrap().unwrap();
        hs.process_client_finish(&data).unwrap();
        let (server_finish, keys) = hs.create_server_finish().unwrap();
        conn.send(Bytes::from(server_finish)).await.unwrap();
        keys
    }
}

// ── Test ────────────────────────────────────────────────────────────────

#[tokio::test]
async fn runtime_multiplexer_end_to_end() {
    let _ = rustls::crypto::ring::default_provider().install_default();

    let (certs, key, raw_cert_der) = generate_test_certs();
    let server_tls = server_tls_config(certs, key);
    let client_tls = client_tls_config();
    let cert_for_server = raw_cert_der.clone();

    let listener = TcpListener::bind((Ipv4Addr::LOCALHOST, 0)).await.unwrap();
    let server_addr = listener.local_addr().unwrap();

    // Setup client mock interfaces
    let (client_os_tx, client_tun_rx) = mpsc::channel(100);
    let (client_tun_tx, mut client_os_rx) = mpsc::channel(100);
    let client_tun = MockTun { rx: client_tun_rx, tx: client_tun_tx };

    // Setup server mock interfaces
    let (server_os_tx, server_tun_rx) = mpsc::channel(100);
    let (server_tun_tx, mut server_os_rx) = mpsc::channel(100);
    let server_tun = MockTun { rx: server_tun_rx, tx: server_tun_tx };

    // Spawn server process
    let _server_handle = tokio::spawn(async move {
        let acceptor = TlsAcceptor::from(Arc::new(server_tls));
        let (tcp_stream, _) = listener.accept().await.unwrap();
        let tls_stream = acceptor.accept(tcp_stream).await.unwrap();

        let mut conn = accept_wss(tls_stream, &cert_for_server).await.unwrap();
        let binding = conn.transport_binding();
        let keys = do_beep_handshake(&mut conn, false, binding).await;
        
        let driver = SessionDriver::new(conn, &keys, false);
        // WSS doesn't native datagrams, multiplexer will segment over streams.
        let mut multiplexer = RuntimeMultiplexer::new(driver, server_tun, false);
        let _ = multiplexer.run().await;
    });

    // Spawn client process
    let _client_handle = tokio::spawn(async move {
        let mut conn = connect_wss(server_addr, "localhost", "vpn", client_tls)
            .await
            .unwrap();
        let binding = conn.transport_binding();
        let keys = do_beep_handshake(&mut conn, true, binding).await;

        let driver = SessionDriver::new(conn, &keys, true);
        let mut multiplexer = RuntimeMultiplexer::new(driver, client_tun, false);
        let _ = multiplexer.run().await;
    });

    // We act as the OS, let's inject a fake ICMP buffer
    let icmp_payload_1 = Bytes::from_static(b"PING-PAYLOAD-1-ICMP");
    let icmp_payload_2 = Bytes::from_static(b"PING-PAYLOAD-2-ICMP");
    
    // Send OS packets via Client
    client_os_tx.send(icmp_payload_1.clone()).await.unwrap();
    client_os_tx.send(icmp_payload_2.clone()).await.unwrap();

    // Verify Server OS receives exactly those packets 
    let rcv1 = server_os_rx.recv().await.unwrap();
    assert_eq!(rcv1, icmp_payload_1);
    
    let rcv2 = server_os_rx.recv().await.unwrap();
    assert_eq!(rcv2, icmp_payload_2);

    // Send OS response packets via Server
    let icmp_reply = Bytes::from_static(b"PONG-REPLY-ICMP");
    server_os_tx.send(icmp_reply.clone()).await.unwrap();

    // Verify Client OS receives it
    let rcv3 = client_os_rx.recv().await.unwrap();
    assert_eq!(rcv3, icmp_reply);

    // Drop OS channels to shut down
    drop(client_os_tx);
    drop(server_os_tx);
}
