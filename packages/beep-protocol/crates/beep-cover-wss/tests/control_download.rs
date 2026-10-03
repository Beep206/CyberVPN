//! Control download (test-bench baseline): a plain HTTPS GET over the same
//! TLS stack and profile a Beep session uses, with no tunnel. This drives the
//! rustls path against a local self-signed HTTPS server and checks the parsed
//! status and body size. The BoringSSL/Chrome path reuses the same wreq stack
//! whose fingerprint is already covered by the stage-2 dialer test.

use beep_core_types::profile::ProfileFile;
use beep_cover_wss::{control_download, ALPN_HTTP11};
use std::net::Ipv4Addr;
use std::sync::Arc;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpListener;
use tokio_rustls::TlsAcceptor;

const PROFILE: &str = r#"
    [presentation]
    id = "control-test"
    alpn = ["http/1.1"]
    tls_provider = "rustls"
    ech_mode = "disabled"
    retry_mode = "standard"
    server_name = "localhost"
    fingerprint = ""
    http_mode = "ws_h1"
    path = "/ws"

    [transport]
    id = "t"
    family = "cover_wss"
    session_core_version = "1"
    connect_timeout_ms = 8000
    idle_timeout_ms = 45000
    keepalive_ms = 15000
    supports_streams = true
    supports_datagrams = false
    allows_migration = false
"#;

fn server_certs() -> (
    Vec<rustls::pki_types::CertificateDer<'static>>,
    rustls::pki_types::PrivateKeyDer<'static>,
) {
    let cert = rcgen::generate_simple_self_signed(vec!["localhost".to_string()]).unwrap();
    let cert_der = rustls::pki_types::CertificateDer::from(cert.cert.der().to_vec());
    let key_der =
        rustls::pki_types::PrivateKeyDer::try_from(cert.key_pair.serialize_der()).unwrap();
    (vec![cert_der], key_der)
}

#[tokio::test]
async fn control_download_fetches_a_file_over_rustls() {
    let _ = rustls::crypto::ring::default_provider().install_default();

    let (certs, key) = server_certs();
    let mut cfg = rustls::ServerConfig::builder()
        .with_no_client_auth()
        .with_single_cert(certs, key)
        .unwrap();
    cfg.alpn_protocols = vec![ALPN_HTTP11.to_vec()];
    let acceptor = TlsAcceptor::from(Arc::new(cfg));

    let listener = TcpListener::bind((Ipv4Addr::LOCALHOST, 0)).await.unwrap();
    let addr = listener.local_addr().unwrap();

    let body_len = 4096usize;
    tokio::spawn(async move {
        let (tcp, _) = listener.accept().await.unwrap();
        let mut tls = acceptor.accept(tcp).await.unwrap();
        // Read the request headers (enough to consume the GET line).
        let mut buf = [0u8; 2048];
        let _ = tls.read(&mut buf).await;
        let body = vec![b'A'; body_len];
        let head = format!(
            "HTTP/1.1 200 OK\r\nContent-Type: application/octet-stream\r\n\
             Content-Length: {body_len}\r\nConnection: close\r\n\r\n"
        );
        tls.write_all(head.as_bytes()).await.unwrap();
        tls.write_all(&body).await.unwrap();
        tls.flush().await.unwrap();
        let _ = tls.shutdown().await;
    });

    let profile = ProfileFile::from_toml_str(PROFILE).expect("profile parses");
    let result = control_download(&profile, addr, true, "/static/file.bin")
        .await
        .expect("control download succeeds");

    assert_eq!(result.status, 200, "unexpected HTTP status");
    assert_eq!(
        result.bytes, body_len as u64,
        "reported body size should match Content-Length"
    );
}
