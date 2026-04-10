//! Full session lifecycle over QUIC transport.
//!
//! Handshake → encrypted stream (3 frames + FIN) → datagram → rekey →
//! resumption ticket → graceful close.

use std::net::{Ipv4Addr, SocketAddr};
use std::sync::Arc;

use beep_core::session::{ClientConfig, ClientHandshake, ServerConfig, ServerHandshake};
use beep_core::session_core::{IncomingAction, SessionCore};
use beep_core_types::{CapabilityId, CoreVersion};
use beep_cover_h3::{accept_h3, connect_h3, server_endpoint, BEEP_ALPN};
use beep_transport::CoverConn;
use bytes::Bytes;

// ── TLS helpers (same pattern as handshake test) ────────────────────────

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

// ── Test ────────────────────────────────────────────────────────────────

#[tokio::test]
async fn full_session_lifecycle_over_quic() {
    let _ = rustls::crypto::ring::default_provider().install_default();

    let (certs, key, raw_cert_der) = generate_test_certs();
    let server_tls = server_tls_config(certs, key);
    let client_tls = client_tls_config();

    let bind_addr: SocketAddr = (Ipv4Addr::LOCALHOST, 0).into();
    let endpoint = server_endpoint(bind_addr, server_tls).unwrap();
    let server_addr = endpoint.local_addr().unwrap();

    let cert_for_server = raw_cert_der;

    // ── Server side ─────────────────────────────────────────────────
    let server_handle = tokio::spawn(async move {
        let incoming = endpoint.accept().await.unwrap();
        let mut conn = accept_h3(endpoint, incoming, &cert_for_server).await.unwrap();
        let binding = conn.transport_binding();

        // Handshake
        let mut hs = ServerHandshake::new(ServerConfig {
            supported_versions: vec![CoreVersion::V1],
            transport_binding: binding,
            capabilities: vec![CapabilityId::Streams, CapabilityId::Rekey],
            node_identity: b"test-node-h3".to_vec(),
            policy_epoch: 1,
        });

        let data = conn.recv().await.unwrap().unwrap();
        hs.process_client_init(&data).unwrap();
        let server_init = hs.create_server_init().unwrap();
        conn.send(Bytes::from(server_init)).await.unwrap();
        let data = conn.recv().await.unwrap().unwrap();
        hs.process_client_finish(&data).unwrap();
        let (server_finish, server_keys) = hs.create_server_finish().unwrap();
        conn.send(Bytes::from(server_finish)).await.unwrap();

        let mut session = SessionCore::new(&server_keys, false);

        // Receive 3 stream frames
        for i in 0..3 {
            let data = conn.recv().await.unwrap().unwrap();
            let action = session.process_incoming(&data).unwrap();
            match action {
                IncomingAction::StreamData { frame, .. } => {
                    let expected = format!("frame-{i}");
                    assert_eq!(frame.data, expected.as_bytes());
                    assert_eq!(frame.fin, i == 2);
                }
                other => panic!("expected StreamData, got {other:?}"),
            }
        }

        // Receive datagram
        let data = conn.recv().await.unwrap().unwrap();
        let action = session.process_incoming(&data).unwrap();
        assert!(matches!(action, IncomingAction::Datagram(df) if df.data == b"dgram-quic"));

        // Receive rekey
        let data = conn.recv().await.unwrap().unwrap();
        let action = session.process_incoming(&data).unwrap();
        assert!(matches!(action, IncomingAction::Rekeyed { epoch: 1 }));

        // Send resumption ticket after rekey
        let sealed = session.seal_control_frame(
            beep_core_types::FrameType::TICKET_ISSUE,
            b"test-ticket-h3",
        ).unwrap();
        conn.send(Bytes::from(sealed.data)).await.unwrap();

        // Receive close
        let data = conn.recv().await.unwrap().unwrap();
        let action = session.process_incoming(&data).unwrap();
        assert!(matches!(action, IncomingAction::Closed { code: 0, .. }));

        // Wait to keep connection alive until client exits
        let _ = conn.recv().await;

        server_keys
    });

    // ── Client side ─────────────────────────────────────────────────
    let client_handle = tokio::spawn(async move {
        let client_bind: SocketAddr = (Ipv4Addr::LOCALHOST, 0).into();
        let mut conn =
            connect_h3(client_bind, server_addr, "localhost", client_tls)
                .await
                .unwrap();
        let binding = conn.transport_binding();

        // Handshake
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
        let client_keys = hs.process_server_finish(&data).unwrap();

        let mut session = SessionCore::new(&client_keys, true);

        // Send 3 stream frames (last has FIN)
        let sid = session.open_stream();
        for i in 0..3 {
            let payload = format!("frame-{i}");
            let fin = i == 2;
            let sealed = session.seal_stream(sid, payload.as_bytes(), fin).unwrap();
            conn.send(Bytes::from(sealed.data)).await.unwrap();
        }

        // Send datagram
        let sealed = session.seal_datagram(0, b"dgram-quic").unwrap();
        conn.send(Bytes::from(sealed.data)).await.unwrap();

        // Rekey
        let rekey_frame = session.initiate_rekey().unwrap();
        conn.send(Bytes::from(rekey_frame.data)).await.unwrap();
        let epoch = session.complete_initiated_rekey().unwrap();
        assert_eq!(epoch, 1);

        // Receive resumption ticket
        let data = conn.recv().await.unwrap().unwrap();
        let action = session.process_incoming(&data).unwrap();
        assert!(matches!(action, IncomingAction::TicketReceived(_)));

        // Close
        let close = session.close(0, "done-quic").unwrap();
        conn.send(Bytes::from(close.data)).await.unwrap();

        // Give the server time to process the close frame before dropping connection
        tokio::time::sleep(std::time::Duration::from_millis(50)).await;

        client_keys
    });

    let server_keys = server_handle.await.unwrap();
    let client_keys = client_handle.await.unwrap();

    // Verify key agreement
    assert_eq!(server_keys.control_key, client_keys.control_key);
    assert_eq!(server_keys.stream_key, client_keys.stream_key);
    assert_eq!(server_keys.datagram_key, client_keys.datagram_key);
}
