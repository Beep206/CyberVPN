//! A recording TCP proxy: what a passive observer on the path would see.
//!
//! Put it between a client and a server (or give it no upstream to capture only
//! the ClientHello). It records both directions byte for byte, parses the
//! ClientHello, and timestamps the connection so tests can check handshake
//! pacing and scan the cleartext part of the exchange.

use std::net::SocketAddr;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::{TcpListener, TcpStream};
use tokio::task::JoinHandle;

use crate::clienthello::ClientHello;

/// Per-direction capture limit; the proxy keeps forwarding past it.
const CAPTURE_LIMIT: usize = 8 * 1024 * 1024;

/// What the proxy saw on one client connection.
#[derive(Debug, Clone)]
pub struct Capture {
    /// Client socket address.
    pub peer: SocketAddr,
    /// When the connection was accepted.
    pub accepted_at: Instant,
    /// When the client sent its first TLS application-data record (its
    /// `Finished` in TLS 1.3): the handshake is over from the client's side.
    pub client_handshake_done_at: Option<Instant>,
    /// When the connection closed.
    pub closed_at: Option<Instant>,
    /// Bytes client to server.
    pub client_bytes: Vec<u8>,
    /// Bytes server to client.
    pub server_bytes: Vec<u8>,
    /// Parsed ClientHello, if the connection started with one.
    pub hello: Option<ClientHello>,
}

/// Walk TLS records and return the prefix made of handshake, change-cipher-spec
/// and alert records, i.e. everything before the first application-data record.
/// With TLS 1.3 this is exactly the part an observer can read.
pub fn cleartext_prefix(bytes: &[u8]) -> &[u8] {
    let mut o = 0;
    while o + 5 <= bytes.len() {
        let kind = bytes[o];
        let len = u16::from_be_bytes([bytes[o + 3], bytes[o + 4]]) as usize;
        if !(20..=22).contains(&kind) || o + 5 + len > bytes.len() {
            break;
        }
        o += 5 + len;
    }
    &bytes[..o]
}

fn has_application_data(bytes: &[u8]) -> bool {
    let mut o = 0;
    while o + 5 <= bytes.len() {
        if bytes[o] == 23 {
            return true;
        }
        let len = u16::from_be_bytes([bytes[o + 3], bytes[o + 4]]) as usize;
        if o + 5 + len > bytes.len() {
            return false;
        }
        o += 5 + len;
    }
    false
}

/// Case-insensitive substring search.
pub fn contains_ci(haystack: &[u8], needle: &str) -> bool {
    let n = needle.as_bytes();
    !n.is_empty() && haystack.windows(n.len()).any(|w| w.eq_ignore_ascii_case(n))
}

impl Capture {
    /// The readable part of the client's side (handshake records only).
    pub fn client_cleartext(&self) -> &[u8] {
        cleartext_prefix(&self.client_bytes)
    }

    /// The readable part of the server's side (handshake records only).
    pub fn server_cleartext(&self) -> &[u8] {
        cleartext_prefix(&self.server_bytes)
    }
}

/// The recording proxy.
pub struct RecordingProxy {
    addr: SocketAddr,
    captures: Arc<Mutex<Vec<Capture>>>,
    task: JoinHandle<()>,
}

impl Drop for RecordingProxy {
    fn drop(&mut self) {
        self.task.abort();
    }
}

impl RecordingProxy {
    /// Listen on a loopback port. With `upstream` the proxy forwards traffic;
    /// without it the proxy reads the ClientHello and closes the connection.
    pub async fn start(upstream: Option<SocketAddr>) -> std::io::Result<Self> {
        let listener = TcpListener::bind("127.0.0.1:0").await?;
        let addr = listener.local_addr()?;
        let captures: Arc<Mutex<Vec<Capture>>> = Arc::default();
        let shared = captures.clone();
        let task = tokio::spawn(async move {
            loop {
                let Ok((client, peer)) = listener.accept().await else {
                    return;
                };
                let idx = {
                    let mut caps = shared.lock().unwrap();
                    caps.push(Capture {
                        peer,
                        accepted_at: Instant::now(),
                        client_handshake_done_at: None,
                        closed_at: None,
                        client_bytes: Vec::new(),
                        server_bytes: Vec::new(),
                        hello: None,
                    });
                    caps.len() - 1
                };
                let shared = shared.clone();
                tokio::spawn(async move {
                    handle(client, upstream, shared.clone(), idx).await;
                    shared.lock().unwrap()[idx].closed_at = Some(Instant::now());
                });
            }
        });
        Ok(Self {
            addr,
            captures,
            task,
        })
    }

    /// Address clients should connect to.
    pub fn addr(&self) -> SocketAddr {
        self.addr
    }

    /// Snapshot of everything captured so far, in connection order.
    pub fn captures(&self) -> Vec<Capture> {
        self.captures.lock().unwrap().clone()
    }

    /// Wait until at least `n` connections have been captured with a parsed
    /// ClientHello, or `timeout` passes; returns what there is.
    pub async fn wait_for_hellos(&self, n: usize, timeout: Duration) -> Vec<Capture> {
        let deadline = Instant::now() + timeout;
        loop {
            let caps = self.captures();
            if caps.iter().filter(|c| c.hello.is_some()).count() >= n || Instant::now() >= deadline
            {
                return caps;
            }
            tokio::time::sleep(Duration::from_millis(10)).await;
        }
    }
}

fn note_client_bytes(shared: &Arc<Mutex<Vec<Capture>>>, idx: usize, chunk: &[u8]) {
    let mut caps = shared.lock().unwrap();
    let c = &mut caps[idx];
    if c.client_bytes.len() < CAPTURE_LIMIT {
        c.client_bytes.extend_from_slice(chunk);
    }
    if c.hello.is_none() && c.client_bytes.len() >= 5 {
        let need = 5 + u16::from_be_bytes([c.client_bytes[3], c.client_bytes[4]]) as usize;
        if c.client_bytes.len() >= need {
            c.hello = ClientHello::parse(&c.client_bytes[..need]).ok();
        }
    }
    if c.client_handshake_done_at.is_none() && has_application_data(&c.client_bytes) {
        c.client_handshake_done_at = Some(Instant::now());
    }
}

fn note_server_bytes(shared: &Arc<Mutex<Vec<Capture>>>, idx: usize, chunk: &[u8]) {
    let mut caps = shared.lock().unwrap();
    let c = &mut caps[idx];
    if c.server_bytes.len() < CAPTURE_LIMIT {
        c.server_bytes.extend_from_slice(chunk);
    }
}

async fn handle(
    mut client: TcpStream,
    upstream: Option<SocketAddr>,
    shared: Arc<Mutex<Vec<Capture>>>,
    idx: usize,
) {
    let Some(upstream) = upstream else {
        // Hello-only mode: read until the first record is complete, then close.
        let mut buf = [0u8; 8192];
        let deadline = Instant::now() + Duration::from_secs(5);
        while Instant::now() < deadline {
            let Ok(Ok(n)) =
                tokio::time::timeout(Duration::from_secs(5), client.read(&mut buf)).await
            else {
                return;
            };
            if n == 0 {
                return;
            }
            note_client_bytes(&shared, idx, &buf[..n]);
            if shared.lock().unwrap()[idx].hello.is_some() {
                return;
            }
        }
        return;
    };

    let Ok(server) = TcpStream::connect(upstream).await else {
        return;
    };
    let (mut cr, mut cw) = client.into_split();
    let (mut sr, mut sw) = server.into_split();

    let up_shared = shared.clone();
    let up = tokio::spawn(async move {
        let mut buf = vec![0u8; 16 * 1024];
        loop {
            let n = match cr.read(&mut buf).await {
                Ok(0) | Err(_) => break,
                Ok(n) => n,
            };
            note_client_bytes(&up_shared, idx, &buf[..n]);
            if sw.write_all(&buf[..n]).await.is_err() {
                break;
            }
        }
        let _ = sw.shutdown().await;
    });
    let down_shared = shared.clone();
    let down = tokio::spawn(async move {
        let mut buf = vec![0u8; 16 * 1024];
        loop {
            let n = match sr.read(&mut buf).await {
                Ok(0) | Err(_) => break,
                Ok(n) => n,
            };
            note_server_bytes(&down_shared, idx, &buf[..n]);
            if cw.write_all(&buf[..n]).await.is_err() {
                break;
            }
        }
        let _ = cw.shutdown().await;
    });
    let _ = tokio::join!(up, down);
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::fixtures::chromium_nav;

    #[tokio::test]
    async fn hello_only_mode_parses_a_replayed_browser_hello() {
        let proxy = RecordingProxy::start(None).await.unwrap();
        let reference = chromium_nav(true);

        let mut s = TcpStream::connect(proxy.addr()).await.unwrap();
        // Send in two segments, as a 1.7 KB hello would travel.
        let (a, b) = reference.record.split_at(1200);
        s.write_all(a).await.unwrap();
        tokio::time::sleep(Duration::from_millis(20)).await;
        s.write_all(b).await.unwrap();

        let caps = proxy.wait_for_hellos(1, Duration::from_secs(3)).await;
        let hello = caps[0].hello.as_ref().expect("parsed across segments");
        assert_eq!(hello.ja4().fingerprint, reference.hello().ja4().fingerprint);
        assert_eq!(hello.sni.as_deref(), reference.hello().sni.as_deref());
    }

    #[tokio::test]
    async fn forwards_traffic_and_records_both_directions() {
        let echo = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let echo_addr = echo.local_addr().unwrap();
        tokio::spawn(async move {
            let (mut s, _) = echo.accept().await.unwrap();
            let mut buf = [0u8; 64];
            let n = s.read(&mut buf).await.unwrap();
            s.write_all(&buf[..n]).await.unwrap();
        });
        let proxy = RecordingProxy::start(Some(echo_addr)).await.unwrap();
        let mut s = TcpStream::connect(proxy.addr()).await.unwrap();
        s.write_all(b"ping-through-proxy").await.unwrap();
        let mut got = [0u8; 18];
        s.read_exact(&mut got).await.unwrap();
        assert_eq!(&got, b"ping-through-proxy");
        drop(s);
        tokio::time::sleep(Duration::from_millis(100)).await;
        let c = &proxy.captures()[0];
        assert_eq!(c.client_bytes, b"ping-through-proxy");
        assert_eq!(c.server_bytes, b"ping-through-proxy");
        assert!(c.closed_at.is_some());
    }

    #[test]
    fn cleartext_prefix_stops_at_application_data() {
        // handshake record (5-byte header, 3-byte body) + CCS + app data
        let mut b = vec![22, 3, 3, 0, 3, 1, 2, 3];
        b.extend_from_slice(&[20, 3, 3, 0, 1, 1]);
        let prefix_len = b.len();
        b.extend_from_slice(&[23, 3, 3, 0, 2, 9, 9]);
        assert_eq!(cleartext_prefix(&b).len(), prefix_len);
        assert!(has_application_data(&b));
        assert!(!has_application_data(&b[..prefix_len]));
    }

    #[test]
    fn case_insensitive_search() {
        assert!(contains_ci(b"xx BeEp yy", "beep"));
        assert!(!contains_ci(b"xx bee yy", "beep"));
        assert!(!contains_ci(b"anything", ""));
    }
}
