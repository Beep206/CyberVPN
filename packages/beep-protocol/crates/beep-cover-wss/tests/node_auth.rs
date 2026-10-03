//! Node authentication over a real WSS transport.
//!
//! The in-memory handshake tests in `beep-core` prove the Ed25519 signature
//! logic; this drives the same four flights across an actual `WssCoverConn`
//! loopback, so the signed handshake is exercised end to end on the wire. It
//! covers the stage-3 checkpoint "node spoofing is detected": a client that
//! pins the wrong node key must refuse the session even though the X25519 DH
//! and the symmetric authenticators all succeed.

use beep_core::key_schedule::generate_node_keypair;
use beep_core::session::{ClientConfig, ClientHandshake, ServerConfig, ServerHandshake};
use beep_core_types::{CapabilityId, CoreVersion};
use beep_cover_wss::{accept_wss, connect_wss, ALPN_HTTP11};
use beep_transport::CoverConn;
use bytes::Bytes;
use std::net::Ipv4Addr;
use std::sync::Arc;
use tokio::net::TcpListener;
use tokio_rustls::TlsAcceptor;

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

/// Spawn a node that always signs with `node_secret`, and run a client that
/// pins `client_expected_key`. Returns whether the client accepted the node.
async fn handshake_with_pins(node_secret: [u8; 32], client_expected_key: [u8; 32]) -> bool {
    let _ = rustls::crypto::ring::default_provider().install_default();

    let (certs, key, raw_cert_der) = generate_test_certs();
    let mut server_tls = rustls::ServerConfig::builder()
        .with_no_client_auth()
        .with_single_cert(certs, key)
        .unwrap();
    server_tls.alpn_protocols = vec![ALPN_HTTP11.to_vec()];

    let listener = TcpListener::bind((Ipv4Addr::LOCALHOST, 0)).await.unwrap();
    let server_addr = listener.local_addr().unwrap();
    let cert_for_server = raw_cert_der.clone();

    let server = tokio::spawn(async move {
        let acceptor = TlsAcceptor::from(Arc::new(server_tls));
        let (tcp, _) = listener.accept().await.unwrap();
        let tls = acceptor.accept(tcp).await.unwrap();
        let mut conn = accept_wss(tls, &cert_for_server).await.unwrap();
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
        let (sf, _keys) = hs.create_server_finish().unwrap();
        // The client decides accept/reject from this flight.
        let _ = conn.send(Bytes::from(sf)).await;
    });

    let client = tokio::spawn(async move {
        let mut conn = connect_wss(server_addr, "localhost", "/ws", client_tls_config())
            .await
            .unwrap();
        let binding = conn.transport_binding();

        let mut hs = ClientHandshake::new(ClientConfig {
            core_version: CoreVersion::V1,
            transport_binding: binding,
            capabilities: vec![CapabilityId::Streams, CapabilityId::Rekey],
            auth_method: 0x01,
            auth_data: b"test-token".to_vec(),
            expected_node_key: Some(client_expected_key),
        });

        let ci = hs.create_client_init().unwrap();
        conn.send(Bytes::from(ci)).await.unwrap();
        let si = conn.recv().await.unwrap().unwrap();
        hs.process_server_init(&si).unwrap();
        let cf = hs.create_client_finish().unwrap();
        conn.send(Bytes::from(cf)).await.unwrap();
        let sf = conn.recv().await.unwrap().unwrap();
        hs.process_server_finish(&sf).is_ok()
    });

    let accepted = client.await.unwrap();
    let _ = server.await;
    accepted
}

#[tokio::test]
async fn client_accepts_node_with_the_pinned_key() {
    let (secret, public) = generate_node_keypair();
    assert!(
        handshake_with_pins(secret, public).await,
        "client should accept the node whose key it pinned"
    );
}

#[tokio::test]
async fn client_rejects_node_with_a_different_key() {
    let (secret, _public) = generate_node_keypair();
    let (_other_secret, other_public) = generate_node_keypair();
    assert!(
        !handshake_with_pins(secret, other_public).await,
        "client must reject a node signing with a key it did not pin"
    );
}
