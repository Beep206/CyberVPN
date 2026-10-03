//! Checkpoint 2's cover-site requirement: a probe set gets the same
//! responses from the Caddy instance fronting the node as it does from a
//! reference Caddy instance with no node behind it at all. See
//! `cover-site/README.md` for the full design and how to run this by hand.
//!
//! This spawns a real `caddy` binary (must be on `PATH`) twice from
//! `cover-site/Caddyfile.lab`, with ephemeral ports, reverse-proxying to an
//! in-process stand-in for the node: the same `WsGate`/`accept_ws` beep-node
//! itself uses, without the TUN device or Beep session handshake, since
//! these probes only exercise the HTTP layer Caddy and the gate operate at.

use beep_cover_wss::{accept_ws, WsGate};
use std::net::{Ipv4Addr, SocketAddr};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::time::Duration;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::{TcpListener, TcpStream};

fn workspace_root() -> PathBuf {
    std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("workspace root exists")
}

fn free_port() -> u16 {
    std::net::TcpListener::bind((Ipv4Addr::LOCALHOST, 0))
        .expect("bind an ephemeral port")
        .local_addr()
        .unwrap()
        .port()
}

/// Kills the child on drop, so a panicking assertion still cleans up caddy
/// rather than leaking it past the test.
struct CaddyGuard(Child);

impl Drop for CaddyGuard {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}

fn spawn_caddy(caddyfile: &std::path::Path, env: &[(&str, String)]) -> CaddyGuard {
    let mut cmd = Command::new("caddy");
    cmd.arg("run")
        .arg("--config")
        .arg(caddyfile)
        .arg("--adapter")
        .arg("caddyfile")
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null());
    for (k, v) in env {
        cmd.env(k, v);
    }
    let child = cmd.spawn().unwrap_or_else(|e| {
        panic!(
            "failed to start `caddy` ({e}); this test needs the caddy \
             binary on PATH (the project installs it for the stage-2 \
             cover-site checkpoint)"
        )
    });
    CaddyGuard(child)
}

async fn wait_until_listening(addr: SocketAddr, timeout: Duration) {
    let deadline = tokio::time::Instant::now() + timeout;
    loop {
        if TcpStream::connect(addr).await.is_ok() {
            return;
        }
        if tokio::time::Instant::now() >= deadline {
            panic!("nothing is listening on {addr} after {timeout:?}");
        }
        tokio::time::sleep(Duration::from_millis(50)).await;
    }
}

/// The node's own accept loop, minus the TUN device and the Beep session
/// handshake: enough to answer the WebSocket upgrade a reverse-proxied
/// probe would complete, which is all these probes look at.
async fn run_fake_node(listener: TcpListener, gate: WsGate) {
    loop {
        let (stream, _) = match listener.accept().await {
            Ok(x) => x,
            Err(_) => return,
        };
        let gate = gate.clone();
        tokio::spawn(async move {
            // A real binding would come from the proxy's leaf certificate;
            // these probes never look at it.
            let _ = accept_ws(stream, &gate, [0u8; 32]).await;
        });
    }
}

fn find_double_crlf(buf: &[u8]) -> Option<usize> {
    buf.windows(4).position(|w| w == b"\r\n\r\n")
}

fn content_length(header_block: &[u8]) -> Option<usize> {
    let text = String::from_utf8_lossy(header_block);
    text.lines().find_map(|line| {
        line.to_ascii_lowercase()
            .strip_prefix("content-length:")
            .and_then(|v| v.trim().parse().ok())
    })
}

/// One probe: a label for assertion messages, a method, a path, and the
/// extra headers to send.
type Probe = (
    &'static str,
    &'static str,
    &'static str,
    Vec<(&'static str, &'static str)>,
);

fn status_code(buf: &[u8]) -> u16 {
    String::from_utf8_lossy(buf)
        .lines()
        .next()
        .and_then(|line| line.split_whitespace().nth(1))
        .and_then(|code| code.parse().ok())
        .unwrap_or(0)
}

/// Send one HTTP/1.1 request and return `(status, body)`. Works for both an
/// ordinary closed-after-response reply and a `101` upgrade (which has no
/// `Content-Length` and never closes on its own): once the header block is
/// complete and either there is no `Content-Length` or the declared body
/// has fully arrived, the read loop stops rather than waiting out its
/// per-read timeout.
async fn http_probe(
    addr: SocketAddr,
    method: &str,
    path: &str,
    headers: &[(&str, &str)],
) -> (u16, Vec<u8>) {
    let mut stream = TcpStream::connect(addr).await.expect("connect to caddy");
    let mut req = format!("{method} {path} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n");
    for (name, value) in headers {
        req.push_str(&format!("{name}: {value}\r\n"));
    }
    req.push_str("\r\n");
    stream
        .write_all(req.as_bytes())
        .await
        .expect("write probe request");

    let mut buf = Vec::new();
    let mut chunk = [0u8; 4096];
    loop {
        match tokio::time::timeout(Duration::from_millis(800), stream.read(&mut chunk)).await {
            Ok(Ok(0)) | Err(_) => break,
            Ok(Err(_)) => break,
            Ok(Ok(n)) => buf.extend_from_slice(&chunk[..n]),
        }
        if let Some(end) = find_double_crlf(&buf) {
            match content_length(&buf[..end]) {
                Some(len) if buf.len() < end + 4 + len => continue,
                _ => break,
            }
        }
    }
    let body = find_double_crlf(&buf)
        .map(|end| buf[end + 4..].to_vec())
        .unwrap_or_default();
    (status_code(&buf), body)
}

#[tokio::test]
async fn cover_site_hides_the_node_from_every_probe_but_the_real_one() {
    if Command::new("caddy").arg("version").output().is_err() {
        panic!(
            "this test needs the `caddy` binary on PATH (the project \
             installs it for the stage-2 cover-site checkpoint)"
        );
    }

    let secret_path = "/static/chunk-7f3a91c2.js";
    let header_name = "x-edge-token";
    let header_value = "probe-test-secret-9f2";

    let node_listener = TcpListener::bind((Ipv4Addr::LOCALHOST, 0)).await.unwrap();
    let node_port = node_listener.local_addr().unwrap().port();
    let gate = WsGate::new(
        secret_path,
        &[(header_name.to_string(), header_value.to_string())],
    )
    .expect("gate builds");
    tokio::spawn(run_fake_node(node_listener, gate));

    let tunnel_port = free_port();
    let reference_port = free_port();

    let caddyfile = workspace_root().join("cover-site/Caddyfile.lab");
    let site_root = workspace_root().join("cover-site/public");

    let env = [
        ("BEEP_LAB_PORT_TUNNEL", tunnel_port.to_string()),
        ("BEEP_LAB_PORT_REFERENCE", reference_port.to_string()),
        ("BEEP_NODE_PORT", node_port.to_string()),
        ("BEEP_COVER_PATH", secret_path.to_string()),
        ("BEEP_COVER_HEADER_NAME", header_name.to_string()),
        ("BEEP_COVER_HEADER_VALUE", header_value.to_string()),
        ("BEEP_COVER_SITE_ROOT", site_root.display().to_string()),
    ];
    let _caddy = spawn_caddy(&caddyfile, &env);

    let tunnel_addr: SocketAddr = ([127, 0, 0, 1], tunnel_port).into();
    let reference_addr: SocketAddr = ([127, 0, 0, 1], reference_port).into();
    wait_until_listening(tunnel_addr, Duration::from_secs(5)).await;
    wait_until_listening(reference_addr, Duration::from_secs(5)).await;

    // None of these is the real tunnel request, so each must come back
    // identical from the with-node and reference instances.
    let probes: Vec<Probe> = vec![
        ("plain page load", "GET", "/", vec![]),
        ("favicon scan", "GET", "/favicon.ico", vec![]),
        ("common scanner path", "GET", "/.git/config", vec![]),
        ("secret path, no header", "GET", secret_path, vec![]),
        (
            "secret path, wrong header value",
            "GET",
            secret_path,
            vec![(header_name, "wrong-value")],
        ),
        (
            "secret path and header, not an upgrade",
            "GET",
            secret_path,
            vec![(header_name, header_value)],
        ),
        (
            "secret path and header, POST instead of GET",
            "POST",
            secret_path,
            vec![(header_name, header_value)],
        ),
        (
            "wrong path with upgrade headers",
            "GET",
            "/nope",
            vec![("Connection", "Upgrade"), ("Upgrade", "websocket")],
        ),
    ];

    for (label, method, path, headers) in probes {
        let (tunnel_code, tunnel_body) = http_probe(tunnel_addr, method, path, &headers).await;
        let (reference_code, reference_body) =
            http_probe(reference_addr, method, path, &headers).await;
        assert_eq!(
            tunnel_code, reference_code,
            "probe `{label}`: status differed (with-node {tunnel_code}, reference {reference_code})"
        );
        assert_eq!(
            tunnel_body, reference_body,
            "probe `{label}`: body differed"
        );
    }

    // The one probe that must NOT match: a genuine tunnel request upgrades
    // against the with-node instance and still 404s against the reference,
    // because the reference has nothing to proxy it to.
    let ws_headers = [
        (header_name, header_value),
        ("Connection", "Upgrade"),
        ("Upgrade", "websocket"),
        ("Sec-WebSocket-Version", "13"),
        ("Sec-WebSocket-Key", "dGhlIHNhbXBsZSBub25jZQ=="),
    ];
    let (tunnel_code, _) = http_probe(tunnel_addr, "GET", secret_path, &ws_headers).await;
    let (reference_code, _) = http_probe(reference_addr, "GET", secret_path, &ws_headers).await;
    assert_eq!(tunnel_code, 101, "the real tunnel request should upgrade");
    assert_eq!(
        reference_code, 404,
        "the reference has no node to upgrade to"
    );
}
