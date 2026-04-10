use criterion::{criterion_group, criterion_main, BenchmarkId, Criterion};
use tokio::runtime::Runtime;
use tokio::net::TcpListener;
use std::sync::Arc;
use std::net::{SocketAddr, Ipv4Addr};
use bytes::Bytes;
use beep_transport::CoverConn;
use beep_cover_h2::{accept_h2, connect_h2};
use beep_cover_h3::{accept_h3, connect_h3, server_endpoint, BEEP_ALPN};
use beep_benchmarks::common::{generate_test_certs, InsecureVerifier};

fn server_tls_config_h2(certs: Vec<rustls::pki_types::CertificateDer<'static>>, key: rustls::pki_types::PrivateKeyDer<'static>) -> Arc<rustls::ServerConfig> {
    let mut config = rustls::ServerConfig::builder().with_no_client_auth().with_single_cert(certs, key).unwrap();
    config.alpn_protocols = vec![b"h2".to_vec()];
    Arc::new(config)
}

fn client_tls_config_h2() -> Arc<rustls::ClientConfig> {
    let mut config = rustls::ClientConfig::builder().dangerous().with_custom_certificate_verifier(Arc::new(InsecureVerifier)).with_no_client_auth();
    config.alpn_protocols = vec![b"h2".to_vec()];
    Arc::new(config)
}

fn server_tls_config_h3(certs: Vec<rustls::pki_types::CertificateDer<'static>>, key: rustls::pki_types::PrivateKeyDer<'static>) -> rustls::ServerConfig {
    let mut config = rustls::ServerConfig::builder().with_no_client_auth().with_single_cert(certs, key).unwrap();
    config.alpn_protocols = vec![BEEP_ALPN.to_vec()];
    config
}

fn client_tls_config_h3() -> rustls::ClientConfig {
    let mut config = rustls::ClientConfig::builder().dangerous().with_custom_certificate_verifier(Arc::new(InsecureVerifier)).with_no_client_auth();
    config.alpn_protocols = vec![BEEP_ALPN.to_vec()];
    config
}

fn bench_transports(c: &mut Criterion) {
    let _ = rustls::crypto::ring::default_provider().install_default();
    let rt = Runtime::new().unwrap();
    
    // Set up H2 client/server
    let mut h2_conn = rt.block_on(async {
        let (certs, key, raw_cert_der) = generate_test_certs();
        let h2_server_tls = server_tls_config_h2(certs.clone(), key.clone_key());
        let h2_client_tls = client_tls_config_h2();
        
        let h2_listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let h2_addr = h2_listener.local_addr().unwrap();
        let cert_for_server = raw_cert_der.clone();
        
        tokio::spawn(async move {
            let (tcp, _) = h2_listener.accept().await.unwrap();
            let acceptor = tokio_rustls::TlsAcceptor::from(h2_server_tls);
            let tls = acceptor.accept(tcp).await.unwrap();
            let mut conn = accept_h2(tls, &cert_for_server).await.unwrap();
            loop {
                if let Ok(Some(data)) = conn.recv().await {
                    let _ = conn.send(data).await;
                } else {
                    break;
                }
            }
        });
        
        let h2_tcp = tokio::net::TcpStream::connect(h2_addr).await.unwrap();
        let h2_connector = tokio_rustls::TlsConnector::from(h2_client_tls);
        let h2_servername = rustls::pki_types::ServerName::try_from("localhost").unwrap();
        let h2_tls = h2_connector.connect(h2_servername, h2_tcp).await.unwrap();
        connect_h2(h2_tls, "localhost").await.unwrap()
    });

    // Set up H3 client/server
    let mut h3_conn = rt.block_on(async {
        let (certs, key, raw_cert_der) = generate_test_certs();
        let h3_server_tls = server_tls_config_h3(certs, key);
        let h3_client_tls = client_tls_config_h3();
        let bind_addr: SocketAddr = (Ipv4Addr::LOCALHOST, 0).into();
        let h3_endpoint = server_endpoint(bind_addr, h3_server_tls).unwrap();
        let h3_addr = h3_endpoint.local_addr().unwrap();
        
        let cert_for_server_h3 = raw_cert_der;
        tokio::spawn(async move {
            let incoming = h3_endpoint.accept().await.unwrap();
            let mut conn = accept_h3(h3_endpoint, incoming, &cert_for_server_h3).await.unwrap();
            loop {
                if let Ok(Some(data)) = conn.recv().await {
                    let _ = conn.send(data).await;
                } else {
                    break;
                }
            }
        });
        
        let client_bind: SocketAddr = (Ipv4Addr::LOCALHOST, 0).into();
        connect_h3(client_bind, h3_addr, "localhost", h3_client_tls).await.unwrap()
    });

    let payload = Bytes::from(vec![0u8; 1024]);
    let mut group = c.benchmark_group("transport_overhead");
    
    group.bench_function(BenchmarkId::new("h2_echo", "1KB"), |b| {
        b.iter(|| {
            rt.block_on(async {
                h2_conn.send(payload.clone()).await.unwrap();
                let _ = h2_conn.recv().await.unwrap().unwrap();
            });
        });
    });

    group.bench_function(BenchmarkId::new("h3_echo", "1KB"), |b| {
        b.iter(|| {
            rt.block_on(async {
                h3_conn.send(payload.clone()).await.unwrap();
                let _ = h3_conn.recv().await.unwrap().unwrap();
            });
        });
    });
    
    group.finish();
}

criterion_group!(benches, bench_transports);
criterion_main!(benches);
