//! Full async session lifecycle test over HTTP/2 transport.
//!
//! Tests: handshake → SessionDriver → async stream → datagram → rekey →
//! policy push → health summary → close.

use std::sync::Arc;
use tokio::net::TcpListener;

use beep_core::key_schedule::SessionKeys;
use beep_core::policy_frames::{
    DnsConfigFrame, NameserverAddr, RouteAction, RouteEntry, RouteSetFrame,
};
use beep_core::session::{ClientConfig, ClientHandshake, ServerConfig, ServerHandshake};
use beep_core::telemetry::HealthSummaryFrame;
use beep_core_types::{CapabilityId, CoreVersion, FrameType};
use beep_cover_h2::{accept_h2, connect_h2};
use beep_session::driver::{RecvEvent, SessionDriver};
use beep_transport::CoverConn;
use bytes::Bytes;

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
) -> Arc<rustls::ServerConfig> {
    let mut config = rustls::ServerConfig::builder()
        .with_no_client_auth()
        .with_single_cert(certs, key)
        .unwrap();
    config.alpn_protocols = vec![b"h2".to_vec()];
    Arc::new(config)
}

fn client_tls_config() -> Arc<rustls::ClientConfig> {
    let mut config = rustls::ClientConfig::builder()
        .dangerous()
        .with_custom_certificate_verifier(Arc::new(InsecureVerifier))
        .with_no_client_auth();
    config.alpn_protocols = vec![b"h2".to_vec()];
    Arc::new(config)
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

// ── Handshake helper ────────────────────────────────────────────────────

struct HandshakeResult<C: CoverConn> {
    conn: C,
    keys: SessionKeys,
}

async fn run_handshake() -> (
    HandshakeResult<impl CoverConn>,
    HandshakeResult<impl CoverConn>,
) {
    let (certs, key, raw_cert_der) = generate_test_certs();
    let server_tls = server_tls_config(certs, key);
    let client_tls = client_tls_config();

    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();

    let cert_for_server = raw_cert_der;
    let server_handle = tokio::spawn(async move {
        let (tcp, _) = listener.accept().await.unwrap();
        let acceptor = tokio_rustls::TlsAcceptor::from(server_tls);
        let tls = acceptor.accept(tcp).await.unwrap();

        let mut conn = accept_h2(tls, &cert_for_server).await.unwrap();
        let binding = conn.transport_binding();

        let mut hs = ServerHandshake::new(ServerConfig {
            supported_versions: vec![CoreVersion::V1],
            transport_binding: binding,
            capabilities: vec![CapabilityId::Streams, CapabilityId::Rekey],
            node_identity: b"test-node".to_vec(),
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

        HandshakeResult { conn, keys }
    });

    let client_handle = tokio::spawn(async move {
        let tcp = tokio::net::TcpStream::connect(addr).await.unwrap();
        let connector = tokio_rustls::TlsConnector::from(client_tls);
        let server_name = rustls::pki_types::ServerName::try_from("localhost").unwrap();
        let tls = connector.connect(server_name, tcp).await.unwrap();

        let mut conn = connect_h2(tls, "localhost").await.unwrap();
        let binding = conn.transport_binding();

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
        let keys = hs.process_server_finish(&data).unwrap();

        HandshakeResult { conn, keys }
    });

    let server = server_handle.await.unwrap();
    let client = client_handle.await.unwrap();
    (client, server)
}

// ── Test ────────────────────────────────────────────────────────────────

#[tokio::test]
async fn async_driver_full_lifecycle() {
    let _ = rustls::crypto::ring::default_provider().install_default();

    let (client_hs, server_hs) = run_handshake().await;

    let mut client = SessionDriver::new(client_hs.conn, &client_hs.keys, true);
    let mut server = SessionDriver::new(server_hs.conn, &server_hs.keys, false);

    // ── Phase 1: Stream data ────────────────────────────────────────
    let sid = client.open_stream();
    client.send_stream(sid, b"hello async", false).await.unwrap();

    let event = server.recv().await.unwrap();
    match event {
        RecvEvent::StreamData { frame, .. } => {
            assert_eq!(frame.data, b"hello async");
            assert!(!frame.fin);
        }
        other => panic!("expected StreamData, got {other:?}"),
    }

    // ── Phase 2: Datagram ───────────────────────────────────────────
    client.send_datagram(0, b"dgram-1").await.unwrap();
    let event = server.recv().await.unwrap();
    assert!(matches!(event, RecvEvent::Datagram(df) if df.data == b"dgram-1"));

    // ── Phase 3: Rekey ──────────────────────────────────────────────
    let epoch = client.send_rekey().await.unwrap();
    assert_eq!(epoch, 1);

    let event = server.recv().await.unwrap();
    assert!(matches!(event, RecvEvent::Rekeyed { epoch: 1 }));

    // Post-rekey traffic
    client.send_stream(sid, b"post-rekey", false).await.unwrap();
    let event = server.recv().await.unwrap();
    assert!(matches!(event, RecvEvent::StreamData { frame, .. } if frame.data == b"post-rekey"));

    // ── Phase 4: Policy push (server → client) ──────────────────────
    let routes = RouteSetFrame {
        replace: true,
        entries: vec![RouteEntry {
            family: 4,
            prefix: vec![10, 0, 0, 0],
            prefix_len: 8,
            action: RouteAction::Include,
        }],
    };
    server.send_route_set(&routes).await.unwrap();
    let event = client.recv().await.unwrap();
    match event {
        RecvEvent::PolicyReceived { frame_type, payload } => {
            assert_eq!(frame_type, FrameType::ROUTE_SET);
            let decoded = RouteSetFrame::decode(&payload).unwrap();
            assert_eq!(decoded, routes);
        }
        other => panic!("expected PolicyReceived, got {other:?}"),
    }

    // DNS config push
    let dns = DnsConfigFrame {
        nameservers: vec![NameserverAddr::V4([8, 8, 8, 8])],
        search_domains: vec!["beep.internal".to_string()],
        ttl_seconds: 300,
    };
    server.send_dns_config(&dns).await.unwrap();
    let event = client.recv().await.unwrap();
    match event {
        RecvEvent::PolicyReceived { frame_type, payload } => {
            assert_eq!(frame_type, FrameType::DNS_CONFIG);
            let decoded = DnsConfigFrame::decode(&payload).unwrap();
            assert_eq!(decoded, dns);
        }
        other => panic!("expected PolicyReceived, got {other:?}"),
    }

    // ── Phase 5: Health summary (client → server) ───────────────────
    client.send_health_summary().await.unwrap();
    let event = server.recv().await.unwrap();
    match event {
        RecvEvent::Telemetry { frame_type, payload } => {
            assert_eq!(frame_type, FrameType::HEALTH_SUMMARY);
            let hs = HealthSummaryFrame::decode(&payload).unwrap();
            assert_eq!(hs.epoch, 1); // we rekeyed once
            assert!(hs.bytes_sent > 0);
        }
        other => panic!("expected Telemetry, got {other:?}"),
    }

    // ── Phase 6: Error report ───────────────────────────────────────
    client
        .send_error_report(42, 1_700_000_000, b"test error")
        .await
        .unwrap();
    let event = server.recv().await.unwrap();
    match event {
        RecvEvent::Telemetry { frame_type, payload } => {
            assert_eq!(frame_type, FrameType::ERROR_REPORT);
            let er = beep_core::telemetry::ErrorReportFrame::decode(&payload).unwrap();
            assert_eq!(er.error_code, 42);
            assert_eq!(er.context, b"test error");
        }
        other => panic!("expected Telemetry, got {other:?}"),
    }

    // ── Phase 7: Graceful close ─────────────────────────────────────
    client.send_close(0, "done").await.unwrap();
    let event = server.recv().await.unwrap();
    assert!(matches!(event, RecvEvent::Closed { code: 0, .. }));
    assert!(client.is_closed());
}
