//! Minimal quinn connectivity test to isolate QUIC issues.

use std::net::{Ipv4Addr, SocketAddr};
use std::sync::Arc;

use beep_cover_h3::BEEP_ALPN;

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

#[tokio::test]
async fn raw_quinn_bidi_roundtrip() {
    let _ = rustls::crypto::ring::default_provider().install_default();

    // Generate certs
    let cert = rcgen::generate_simple_self_signed(vec!["localhost".to_string()]).unwrap();
    let cert_der = rustls::pki_types::CertificateDer::from(cert.cert.der().to_vec());
    let key_der =
        rustls::pki_types::PrivateKeyDer::try_from(cert.key_pair.serialize_der()).unwrap();

    // Server TLS
    let mut server_tls = rustls::ServerConfig::builder()
        .with_no_client_auth()
        .with_single_cert(vec![cert_der], key_der)
        .unwrap();
    server_tls.alpn_protocols = vec![BEEP_ALPN.to_vec()];

    let quic_server_config = quinn::crypto::rustls::QuicServerConfig::try_from(server_tls)
        .expect("QuicServerConfig::try_from failed");
    let server_config = quinn::ServerConfig::with_crypto(Arc::new(quic_server_config));

    let bind_addr: SocketAddr = (Ipv4Addr::LOCALHOST, 0).into();
    let server_endpoint = quinn::Endpoint::server(server_config, bind_addr)
        .expect("server endpoint failed");
    let server_addr = server_endpoint.local_addr().unwrap();
    eprintln!("Server listening on {server_addr}");

    // Client TLS
    let mut client_tls = rustls::ClientConfig::builder()
        .dangerous()
        .with_custom_certificate_verifier(Arc::new(InsecureVerifier))
        .with_no_client_auth();
    client_tls.alpn_protocols = vec![BEEP_ALPN.to_vec()];

    let quic_client_config = quinn::crypto::rustls::QuicClientConfig::try_from(client_tls)
        .expect("QuicClientConfig::try_from failed");
    let client_config = quinn::ClientConfig::new(Arc::new(quic_client_config));

    let mut client_endpoint = quinn::Endpoint::client((Ipv4Addr::LOCALHOST, 0).into())
        .expect("client endpoint failed");
    client_endpoint.set_default_client_config(client_config);

    // Server task
    let server_handle = tokio::spawn(async move {
        eprintln!("[server] waiting for incoming...");
        let incoming = server_endpoint.accept().await.expect("accept failed");
        eprintln!("[server] got incoming, awaiting connection...");
        let conn = incoming.await.expect("incoming.await failed");
        eprintln!("[server] connection established, waiting for bidi...");
        let (mut send, mut recv) = conn.accept_bi().await.expect("accept_bi failed");
        eprintln!("[server] bidi accepted, reading...");

        let mut buf = vec![0u8; 5];
        recv.read_exact(&mut buf).await.expect("read_exact failed");
        eprintln!("[server] read: {:?}", std::str::from_utf8(&buf));

        send.write_all(b"world").await.expect("write_all failed");
        send.finish().expect("finish failed");
        eprintln!("[server] wrote response");

        // Wait for connection to become idle (all data acknowledged)
        conn.closed().await;
        eprintln!("[server] connection closed cleanly");
    });

    // Client task
    let client_handle = tokio::spawn(async move {
        eprintln!("[client] connecting to {server_addr}...");
        let conn = client_endpoint
            .connect(server_addr, "localhost")
            .expect("connect failed")
            .await
            .expect("connect.await failed");
        eprintln!("[client] connected, opening bidi...");

        let (mut send, mut recv) = conn.open_bi().await.expect("open_bi failed");
        eprintln!("[client] bidi opened, writing...");

        send.write_all(b"hello").await.expect("write_all failed");
        send.finish().expect("finish failed");
        eprintln!("[client] wrote data, reading response...");

        let mut buf = vec![0u8; 5];
        recv.read_exact(&mut buf).await.expect("read_exact failed");
        eprintln!("[client] read: {:?}", std::str::from_utf8(&buf));

        conn.close(0u32.into(), b"done");
    });

    let (s, c) = tokio::join!(server_handle, client_handle);
    s.expect("server panicked");
    c.expect("client panicked");
}
