//! Full session lifecycle test over HTTP/2 transport.
//!
//! Tests: handshake → SessionCore → encrypted stream → rekey → ticket → close.

use std::sync::Arc;
use tokio::net::TcpListener;

use beep_core::key_schedule::SessionKeys;
use beep_core::resumption::{seal_ticket, open_ticket, validate_ticket, ResumptionTicket};
use beep_core::session::{ClientConfig, ClientHandshake, ServerConfig, ServerHandshake};
use beep_core::session_core::{IncomingAction, SessionCore};
use beep_core_types::{CapabilityId, CoreVersion};
use beep_cover_h2::{accept_h2, connect_h2};
use beep_transport::CoverConn;
use bytes::Bytes;

// ── TLS helpers (same as session_handshake.rs) ──────────────────────────

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

// ── Helpers ─────────────────────────────────────────────────────────────

async fn handshake() -> (SessionKeys, SessionKeys) {
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
        let (server_finish, session_keys) = hs.create_server_finish().unwrap();
        conn.send(Bytes::from(server_finish)).await.unwrap();

        session_keys
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
        hs.process_server_finish(&data).unwrap()
    });

    let server_keys = server_handle.await.unwrap();
    let client_keys = client_handle.await.unwrap();
    (client_keys, server_keys)
}

// ── Test ────────────────────────────────────────────────────────────────

#[tokio::test]
async fn full_session_lifecycle() {
    let _ = rustls::crypto::ring::default_provider().install_default();

    let (client_keys, server_keys) = handshake().await;

    // ── Phase 1: Create sessions ────────────────────────────────────
    let mut client_session = SessionCore::new(&client_keys, true);
    let mut server_session = SessionCore::new(&server_keys, false);

    assert_eq!(client_session.epoch(), 0);
    assert_eq!(server_session.epoch(), 0);

    // ── Phase 2: Stream traffic ─────────────────────────────────────
    let sid = client_session.open_stream();

    // Send 3 frames of data
    for i in 0..3u8 {
        let data = format!("chunk {i}");
        let fin = i == 2;
        let sealed = client_session.seal_stream(sid, data.as_bytes(), fin).unwrap();
        let action = server_session.process_incoming(&sealed.data).unwrap();
        match action {
            IncomingAction::StreamData { frame, .. } => {
                assert_eq!(frame.data, data.as_bytes());
                assert_eq!(frame.fin, fin);
            }
            other => panic!("expected StreamData, got {other:?}"),
        }
    }

    // ── Phase 3: Datagram ───────────────────────────────────────────
    let sealed_dg = client_session.seal_datagram(0, b"ping").unwrap();
    let action = server_session.process_incoming(&sealed_dg.data).unwrap();
    assert!(matches!(action, IncomingAction::Datagram(df) if df.data == b"ping"));

    // ── Phase 4: Rekey ──────────────────────────────────────────────
    let ku = client_session.initiate_rekey().unwrap();
    // Complete client-side rekey
    client_session.complete_initiated_rekey().unwrap();

    let action = server_session.process_incoming(&ku.data).unwrap();
    assert!(matches!(action, IncomingAction::Rekeyed { epoch: 1 }));
    assert_eq!(client_session.epoch(), 1);
    assert_eq!(server_session.epoch(), 1);

    // Post-rekey traffic works
    let sid2 = client_session.open_stream();
    let sealed = client_session.seal_stream(sid2, b"epoch 1", false).unwrap();
    let action = server_session.process_incoming(&sealed.data).unwrap();
    assert!(matches!(action, IncomingAction::StreamData { frame, .. } if frame.data == b"epoch 1"));

    // ── Phase 5: Resumption ticket ──────────────────────────────────
    let ticket = ResumptionTicket {
        client_id: [0xAA; 16],
        node_scope: [0xBB; 16],
        policy_epoch: 1,
        capabilities: vec![0x01, 0x02],
        expiry_unix: 2_000_000_000,
        nonce: [0xCC; 12],
    };
    let sealed_ticket = seal_ticket(&server_keys.resumption_secret, &ticket).unwrap();

    // Server can verify
    let opened = open_ticket(&server_keys.resumption_secret, &sealed_ticket).unwrap();
    assert_eq!(opened, ticket);
    validate_ticket(&opened, 1, 1_600_000_000).unwrap();

    // Client can also open (same resumption_secret)
    let client_opened = open_ticket(&client_keys.resumption_secret, &sealed_ticket).unwrap();
    assert_eq!(client_opened, ticket);

    // ── Phase 6: Graceful close ─────────────────────────────────────
    let close = client_session.close(0, "done").unwrap();
    let action = server_session.process_incoming(&close.data).unwrap();
    assert!(matches!(action, IncomingAction::Closed { code: 0, .. }));
    assert!(client_session.is_closed());
    assert!(server_session.is_closed());
}
