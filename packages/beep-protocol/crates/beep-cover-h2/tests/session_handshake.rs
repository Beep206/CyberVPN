//! Integration tests: Beep session over HTTP/2 Extended CONNECT.
//!
//! Test 1: Full 4-flight handshake  
//! Test 2: Encrypted traffic + stream multiplexing + rekey

use std::sync::Arc;
use tokio::net::TcpListener;

use beep_core::cipher::{TrafficClass, TrafficKey};
use beep_core::key_schedule::SessionKeys;
use beep_core::mux::{DatagramFrame, StreamFrame};
use beep_core::rekey::{KeyUpdateFrame, RekeyState};
use beep_core::session::{ClientConfig, ClientHandshake, ServerConfig, ServerHandshake};
use beep_core_types::{CapabilityId, CoreVersion};
use beep_cover_h2::{accept_h2, connect_h2};
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

// ── Shared TLS+H2 setup helper ──────────────────────────────────────────

struct TestEndpoints {
    server_keys: SessionKeys,
    client_keys: SessionKeys,
}

async fn full_handshake_over_h2() -> TestEndpoints {
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

    TestEndpoints {
        server_keys,
        client_keys,
    }
}

// ── Test 1: Handshake & key agreement ───────────────────────────────────

#[tokio::test]
async fn full_session_handshake_over_h2() {
    let _ = rustls::crypto::ring::default_provider().install_default();

    let ep = full_handshake_over_h2().await;

    assert_eq!(ep.client_keys.session_master_secret, ep.server_keys.session_master_secret);
    assert_eq!(ep.client_keys.control_key, ep.server_keys.control_key);
    assert_eq!(ep.client_keys.stream_key, ep.server_keys.stream_key);
    assert_eq!(ep.client_keys.datagram_key, ep.server_keys.datagram_key);
    assert_eq!(ep.client_keys.resumption_secret, ep.server_keys.resumption_secret);
}

// ── Test 2: Encrypted stream data + rekey ───────────────────────────────

#[tokio::test]
async fn encrypted_stream_traffic_and_rekey() {
    let _ = rustls::crypto::ring::default_provider().install_default();

    let ep = full_handshake_over_h2().await;

    // Create traffic keys from session keys
    let mut client_stream_send =
        TrafficKey::new(ep.client_keys.stream_key, ep.client_keys.stream_iv, TrafficClass::Stream);
    let mut server_stream_recv =
        TrafficKey::new(ep.server_keys.stream_key, ep.server_keys.stream_iv, TrafficClass::Stream);

    // Encrypt a stream frame
    let frame = StreamFrame {
        stream_id: 1,
        offset: 0,
        fin: false,
        data: b"Hello from Beep tunnel!".to_vec(),
    };
    let mut payload = Vec::new();
    frame.encode(&mut payload).unwrap();

    let ciphertext = client_stream_send.seal(&payload).unwrap();
    let plaintext = server_stream_recv.open(&ciphertext).unwrap();
    let (decoded_frame, _) = StreamFrame::decode(&plaintext).unwrap();
    assert_eq!(decoded_frame.data, b"Hello from Beep tunnel!");
    assert_eq!(decoded_frame.stream_id, 1);

    // Encrypt a datagram frame
    let mut client_dg_send = TrafficKey::new(
        ep.client_keys.datagram_key,
        ep.client_keys.datagram_iv,
        TrafficClass::Datagram,
    );
    let mut server_dg_recv = TrafficKey::new(
        ep.server_keys.datagram_key,
        ep.server_keys.datagram_iv,
        TrafficClass::Datagram,
    );

    let dg = DatagramFrame {
        class_id: 0,
        data: vec![0xDE, 0xAD, 0xBE, 0xEF],
    };
    let mut dg_payload = Vec::new();
    dg.encode(&mut dg_payload).unwrap();

    let dg_ct = client_dg_send.seal(&dg_payload).unwrap();
    let dg_pt = server_dg_recv.open(&dg_ct).unwrap();
    let (decoded_dg, _) = DatagramFrame::decode(&dg_pt).unwrap();
    assert_eq!(decoded_dg.data, vec![0xDE, 0xAD, 0xBE, 0xEF]);

    // ── Rekey ───────────────────────────────────────────────────────

    // Both sides perform rekey from the same session keys
    let mut client_rekey = RekeyState::new(&ep.client_keys);
    let mut server_rekey = RekeyState::new(&ep.server_keys);

    // Client initiates KEY_UPDATE
    let new_epoch = client_rekey.initiate().unwrap();
    let ku_frame = KeyUpdateFrame { new_epoch };
    let mut ku_buf = Vec::new();
    ku_frame.encode(&mut ku_buf);

    // Server processes KEY_UPDATE
    let decoded_ku = KeyUpdateFrame::decode(&ku_buf).unwrap();
    server_rekey.process_peer_update(decoded_ku.new_epoch).unwrap();

    // Both complete rekey
    let client_epoch_keys = client_rekey.complete().unwrap();
    let server_epoch_keys = server_rekey.complete().unwrap();

    // New keys must match
    assert_eq!(client_epoch_keys, server_epoch_keys);
    assert_eq!(client_rekey.epoch(), 1);

    // Use new keys for traffic
    let mut new_send = TrafficKey::new(
        client_epoch_keys.stream_key,
        client_epoch_keys.stream_iv,
        TrafficClass::Stream,
    );
    let mut new_recv = TrafficKey::new(
        server_epoch_keys.stream_key,
        server_epoch_keys.stream_iv,
        TrafficClass::Stream,
    );

    let post_rekey_frame = StreamFrame {
        stream_id: 1,
        offset: 23,
        fin: true,
        data: b"after rekey!".to_vec(),
    };
    let mut post_payload = Vec::new();
    post_rekey_frame.encode(&mut post_payload).unwrap();

    let ct = new_send.seal(&post_payload).unwrap();
    let pt = new_recv.open(&ct).unwrap();
    let (decoded, _) = StreamFrame::decode(&pt).unwrap();
    assert_eq!(decoded.data, b"after rekey!");
    assert!(decoded.fin);

    // Old keys must NOT decrypt new-epoch traffic
    let ct2 = new_send.seal(b"new epoch only").unwrap();
    // Old receiver would have wrong nonce/key
    let mut old_recv = TrafficKey::new(
        ep.server_keys.stream_key,
        ep.server_keys.stream_iv,
        TrafficClass::Stream,
    );
    let result = old_recv.open(&ct2);
    assert!(result.is_err(), "old epoch key must not decrypt new epoch data");
}
