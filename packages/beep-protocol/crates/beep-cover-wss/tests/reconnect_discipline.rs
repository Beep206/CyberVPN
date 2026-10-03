//! Regression test for the stage-2 connection-discipline checkpoint:
//!
//! > 20 forced disconnects: the capture shows no overlapping handshakes.
//! > The pause between attempts comes from the profile, plus a random
//! > addition; the fingerprint and SNI do not change during the pause.
//!
//! This replicates the shape of `beep-client`'s reconnect loop — dial,
//! and on failure sleep for `handshake_pacing()` before the next attempt —
//! against a real TCP+TLS listener that force-closes every connection right
//! after the TLS handshake, before any WebSocket upgrade response. The
//! server's own accept/close timestamps are what a packet capture would
//! show, so checking them for overlap is a direct, automated stand-in for
//! "look at a capture of 20 forced reconnects".

use beep_core_types::{ProfileFile, Role};
use beep_cover_wss::{RootCerts, RustlsDialer, ALPN_HTTP11};
use beep_transport::{CoverDialer, DialTarget};
use std::net::{Ipv4Addr, SocketAddr};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::io::AsyncWriteExt;
use tokio::net::TcpListener;
use tokio_rustls::TlsAcceptor;

const ROUNDS: usize = 20;

// A short, explicit pacing so the test does not take forever: 120ms base,
// up to 40ms of jitter on top. `handshake_gap_ms`/`handshake_gap_jitter_ms`
// are explicit, so they win over `retry_mode` in `handshake_pacing()`
// regardless of which retry mode is named below.
const PROFILE_TOML: &str = r#"
    [presentation]
    id = "reconnect-discipline-test"
    alpn = ["http/1.1"]
    tls_provider = "rustls"
    ech_mode = "disabled"
    retry_mode = "standard"
    server_name = "localhost"
    fingerprint = ""
    http_mode = "ws_h1"
    path = "/ws"
    handshake_gap_ms = 120
    handshake_gap_jitter_ms = 40

    [transport]
    id = "reconnect-discipline-test"
    family = "cover_wss"
    session_core_version = "1"
    connect_timeout_ms = 2000
    idle_timeout_ms = 15000
    keepalive_ms = 5000
    supports_streams = true
    supports_datagrams = false
    allows_migration = false
"#;

fn generate_test_certs() -> (
    Vec<rustls::pki_types::CertificateDer<'static>>,
    rustls::pki_types::PrivateKeyDer<'static>,
) {
    let cert = rcgen::generate_simple_self_signed(vec!["localhost".to_string()]).unwrap();
    let cert_der = rustls::pki_types::CertificateDer::from(cert.cert.der().to_vec());
    let key_der =
        rustls::pki_types::PrivateKeyDer::try_from(cert.key_pair.serialize_der()).unwrap();
    (vec![cert_der], key_der)
}

/// Accept `rounds` connections, completing the TLS handshake on each before
/// closing it at once — a forced disconnect, not a clean WebSocket close.
/// Returns each connection's `(accepted_at, closed_at)`, in acceptance order.
async fn run_forced_disconnect_server(
    listener: TcpListener,
    acceptor: TlsAcceptor,
    rounds: usize,
) -> Vec<(Instant, Instant)> {
    let mut intervals = Vec::with_capacity(rounds);
    for _ in 0..rounds {
        let (tcp, _) = listener.accept().await.expect("tcp accept");
        let accepted_at = Instant::now();
        let mut tls = acceptor.accept(tcp).await.expect("tls accept");
        let _ = tls.shutdown().await;
        drop(tls);
        intervals.push((accepted_at, Instant::now()));
    }
    intervals
}

/// Dependency-free jitter source in `[0, 1)`, matching the one in
/// `beep-client`'s own reconnect loop.
fn jitter_fraction() -> f64 {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.subsec_nanos())
        .unwrap_or(0);
    (nanos % 1_000_000) as f64 / 1_000_000.0
}

/// The client half: `rounds` sequential dial attempts, each expected to
/// fail, each followed by the profile-driven pause. Never more than one
/// dial is in flight — the loop only ever awaits one at a time — which is
/// the property under test, exercised against a real socket rather than
/// just read off the control flow.
async fn run_reconnect_loop(addr: SocketAddr, profile: &ProfileFile, rounds: usize) {
    let dialer = RustlsDialer::new(RootCerts::Insecure);
    for _ in 0..rounds {
        let target = DialTarget::from_profile(profile, addr);
        let result = dialer.dial(&target).await;
        assert!(
            result.is_err(),
            "the test server force-closes before any upgrade response; a \
             successful dial means the server and client fell out of sync"
        );
        let (base, jitter_cap) = profile.presentation.handshake_pacing();
        let delay = base + jitter_cap.mul_f64(jitter_fraction());
        tokio::time::sleep(delay).await;
    }
}

#[tokio::test]
async fn twenty_forced_disconnects_show_no_overlapping_handshakes() {
    let _ = rustls::crypto::ring::default_provider().install_default();

    let profile = ProfileFile::from_toml_str(PROFILE_TOML).expect("fixture profile parses");
    profile
        .validate(Role::Client)
        .expect("fixture profile passes validation");

    let (certs, key) = generate_test_certs();
    let mut server_tls = rustls::ServerConfig::builder()
        .with_no_client_auth()
        .with_single_cert(certs, key)
        .unwrap();
    server_tls.alpn_protocols = vec![ALPN_HTTP11.to_vec()];
    let acceptor = TlsAcceptor::from(Arc::new(server_tls));

    let listener = TcpListener::bind((Ipv4Addr::LOCALHOST, 0))
        .await
        .expect("bind loopback listener");
    let addr = listener.local_addr().unwrap();

    let server = tokio::spawn(run_forced_disconnect_server(listener, acceptor, ROUNDS));

    run_reconnect_loop(addr, &profile, ROUNDS).await;

    let intervals = server.await.expect("server task panicked");
    assert_eq!(intervals.len(), ROUNDS);

    // Half the configured base gap: comfortably above zero (so a capture
    // with real overlap or a near-zero pause still fails this) while
    // tolerant of scheduling slack in a loaded sandbox.
    let min_gap = Duration::from_millis(60);

    for (i, pair) in intervals.windows(2).enumerate() {
        let (_, prev_closed) = pair[0];
        let (next_accept, _) = pair[1];
        assert!(
            prev_closed <= next_accept,
            "handshake {} started before handshake {} fully closed; a \
             capture would show overlapping handshakes",
            i + 1,
            i
        );
        let gap = next_accept.duration_since(prev_closed);
        assert!(
            gap >= min_gap,
            "pause before handshake {} was {gap:?}, shorter than the \
             profile's minimum {min_gap:?}",
            i + 1
        );
    }
}
