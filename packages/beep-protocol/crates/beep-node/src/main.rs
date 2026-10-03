use async_trait::async_trait;
use beep_core::key_schedule::{generate_node_keypair, SessionKeys};
use beep_core::session::{ServerConfig, ServerHandshake};
use beep_core_types::artifact::decode_hex32;
use beep_core_types::{CapabilityId, CoreVersion, ProfileFile, Role};
use beep_cover_wss::{accept_ws, WsGate};
use beep_runtime::{tun_hub, Event, EventLog, RuntimeMultiplexer, TunDevice, TunHubHandle};
use beep_session::SessionDriver;
use beep_transport::{binding_from_leaf, CoverConn, WS_BINDING_LABEL};
use bytes::Bytes;
use clap::Parser;
use std::collections::HashMap;
use std::io;
use std::net::SocketAddr;
use std::path::{Path, PathBuf};
use std::process;
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tokio::net::TcpListener;
use tokio::sync::Semaphore;
use tokio_rustls::TlsAcceptor;
use tokio_tun::TunBuilder;

// Capacities and limits. Deliberately generous for a single-node lab; a
// production deployment would tune these to its traffic.
const OUTBOUND_QUEUE: usize = 1024;
const SESSION_INBOUND_QUEUE: usize = 256;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Port to listen on
    #[arg(short, long, default_value_t = 4443)]
    port: u16,

    /// Wire profile (presentation + transport): the path and header this
    /// node admits, and the ALPN it answers with. The same file a client
    /// dials with.
    #[arg(long)]
    profile: PathBuf,

    /// TUN interface name
    #[arg(short, long, default_value = "beep_server0")]
    iface: String,

    /// IP address of the node TUN device in CIDR (e.g., 10.8.0.1)
    #[arg(long, default_value = "10.8.0.1")]
    address: String,

    /// File of accepted client tokens, one per line (blank lines and `#`
    /// comments ignored). A client must present one of these in its handshake
    /// or the tunnel is refused. Omit to disable token checks (lab only).
    #[arg(long)]
    tokens: Option<PathBuf>,

    /// File holding the node's Ed25519 secret key as 64 hex characters. When
    /// set, the node signs each handshake transcript so a client that pins the
    /// matching public key can tell this node from an impostor. Omit to run
    /// without node authentication (lab only).
    #[arg(long)]
    node_key: Option<PathBuf>,

    /// Print a fresh Ed25519 node keypair (secret then public, hex) and exit.
    /// Put the secret in a file for `--node-key` and the public key in each
    /// client profile's `node_public_key`.
    #[arg(long)]
    generate_node_key: bool,

    /// Maximum handshakes allowed in flight at once. Excess connections are
    /// dropped immediately rather than queued, bounding handshake-flood cost.
    #[arg(long, default_value_t = 64)]
    max_handshakes: usize,

    /// Maximum simultaneous sessions per token.
    #[arg(long, default_value_t = 8)]
    max_sessions_per_token: usize,

    /// Seconds a single handshake may take before it is abandoned.
    #[arg(long, default_value_t = 10)]
    handshake_timeout_secs: u64,

    /// Append a JSON event log (handshake timing, byte counts, stalls,
    /// disconnect reason) to this file, for the test bench.
    #[arg(long)]
    event_log: Option<PathBuf>,

    /// Terminate TLS here with an auto-generated self-signed certificate,
    /// and listen on every interface. A lab convenience for running without
    /// a front proxy; use `--behind-proxy` for the real topology.
    #[arg(long, conflicts_with = "behind_proxy")]
    insecure: bool,

    /// Run with no TLS of its own, listening on 127.0.0.1 only: the
    /// topology a front proxy (Caddy) fronts in production. The proxy owns
    /// the public port and certificate and forwards only requests it has
    /// already gated by path and header; this process never sees anything
    /// else. The path given here is a PEM file holding the leaf certificate
    /// the proxy presents publicly — the same file on the same machine, not
    /// a copy — so the transport binding still ties the Beep session to the
    /// certificate the client actually saw (see `binding_from_leaf`).
    #[arg(long, conflicts_with = "insecure")]
    behind_proxy: Option<PathBuf>,
}

// ── Physical TUN adapter (the one real device, owned by the hub) ─────────

struct OsTun {
    iface: Arc<tokio_tun::Tun>,
}

#[async_trait]
impl TunDevice for OsTun {
    async fn read_packet(&mut self) -> io::Result<Bytes> {
        let mut buf = [0u8; 65536];
        let n = self.iface.recv(&mut buf).await?;
        Ok(Bytes::copy_from_slice(&buf[..n]))
    }

    async fn write_packet(&mut self, pkt: Bytes) -> io::Result<()> {
        self.iface.send_all(&pkt).await?;
        Ok(())
    }
}

// ── Token authentication ─────────────────────────────────────────────────

/// Accepted client tokens. When no tokens are configured, authentication is
/// disabled and every client is admitted (lab only).
struct TokenAuth {
    allowed: Vec<Vec<u8>>,
}

impl TokenAuth {
    fn load(path: Option<&Path>) -> io::Result<Self> {
        let allowed = match path {
            None => Vec::new(),
            Some(p) => std::fs::read_to_string(p)?
                .lines()
                .map(str::trim)
                .filter(|l| !l.is_empty() && !l.starts_with('#'))
                .map(|l| l.as_bytes().to_vec())
                .collect(),
        };
        Ok(Self { allowed })
    }

    fn enforced(&self) -> bool {
        !self.allowed.is_empty()
    }

    /// Whether `presented` is one of the accepted tokens. Disabled auth admits
    /// everyone. Every entry is compared in constant time and all are checked,
    /// so timing does not reveal which token (or prefix) matched.
    fn admits(&self, presented: &[u8]) -> bool {
        if !self.enforced() {
            return true;
        }
        let mut ok = false;
        for token in &self.allowed {
            ok |= constant_time_eq(token, presented);
        }
        ok
    }
}

fn constant_time_eq(a: &[u8], b: &[u8]) -> bool {
    if a.len() != b.len() {
        return false;
    }
    a.iter().zip(b).fold(0u8, |acc, (x, y)| acc | (x ^ y)) == 0
}

// ── Per-token session limiting ───────────────────────────────────────────

/// Caps simultaneous sessions per token. A reservation is released when its
/// [`SessionSlot`] is dropped (session ended).
#[derive(Clone)]
struct SessionLimiter {
    counts: Arc<Mutex<HashMap<Vec<u8>, usize>>>,
    max_per_token: usize,
}

impl SessionLimiter {
    fn new(max_per_token: usize) -> Self {
        Self {
            counts: Arc::new(Mutex::new(HashMap::new())),
            max_per_token: max_per_token.max(1),
        }
    }

    /// Reserve a slot for `token`, or `None` if it is already at its cap.
    fn try_acquire(&self, token: &[u8]) -> Option<SessionSlot> {
        let mut counts = self.counts.lock().expect("session-count mutex");
        let entry = counts.entry(token.to_vec()).or_insert(0);
        if *entry >= self.max_per_token {
            return None;
        }
        *entry += 1;
        Some(SessionSlot {
            counts: self.counts.clone(),
            token: token.to_vec(),
        })
    }
}

/// Releases one per-token session reservation on drop.
struct SessionSlot {
    counts: Arc<Mutex<HashMap<Vec<u8>, usize>>>,
    token: Vec<u8>,
}

impl Drop for SessionSlot {
    fn drop(&mut self) {
        let mut counts = self.counts.lock().expect("session-count mutex");
        if let Some(n) = counts.get_mut(&self.token) {
            *n = n.saturating_sub(1);
            if *n == 0 {
                counts.remove(&self.token);
            }
        }
    }
}

// ── Shared per-node context handed to every connection ───────────────────

struct NodeContext {
    capabilities: Vec<CapabilityId>,
    node_identity: Vec<u8>,
    node_signing_key: Option<[u8; 32]>,
    gate: WsGate,
    tokens: TokenAuth,
    sessions: SessionLimiter,
    handshake_permits: Arc<Semaphore>,
    handshake_timeout: Duration,
    hub: TunHubHandle,
    events: Option<EventLog>,
}

// ── Main entrypoint ───────────────────────────────────────────────────────

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt::init();
    let args = Args::parse();

    if args.generate_node_key {
        let (secret, public) = generate_node_keypair();
        println!("secret {}", hex_encode(&secret));
        println!("public {}", hex_encode(&public));
        return Ok(());
    }

    let _ = rustls::crypto::ring::default_provider().install_default();

    let profile = ProfileFile::load_validated(&args.profile, Role::Node)
        .map_err(|e| format!("profile {}: {e}", args.profile.display()))?;
    let gate_headers: Vec<(String, String)> = profile
        .presentation
        .headers
        .iter()
        .map(|(k, v)| (k.clone(), v.clone()))
        .collect();
    let gate = WsGate::new(&profile.presentation.path, &gate_headers)?;

    let tokens =
        TokenAuth::load(args.tokens.as_deref()).map_err(|e| format!("reading tokens file: {e}"))?;
    if !tokens.enforced() {
        tracing::warn!("no --tokens file given: client token checks are DISABLED (lab only)");
    }

    let node_signing_key = match &args.node_key {
        Some(path) => Some(read_node_key(path).map_err(|e| format!("reading node key: {e}"))?),
        None => {
            tracing::warn!("no --node-key given: node identity signing is DISABLED (lab only)");
            None
        }
    };

    tracing::info!(
        profile = %profile.presentation.id,
        path = %profile.presentation.path,
        headers = gate_headers.len(),
        tokens = tokens.enforced(),
        node_signing = node_signing_key.is_some(),
        "Loaded wire profile"
    );

    // One physical TUN device, owned by the hub. Every session reads and
    // writes through its own hub endpoint, so an inbound packet is delivered
    // only to the session that owns its destination address.
    let tun = match TunBuilder::new()
        .name(&args.iface)
        .tap(false)
        .packet_info(false)
        .mtu(1420)
        .up()
        .address(args.address.parse().unwrap())
        .netmask(std::net::Ipv4Addr::new(255, 255, 255, 0))
        .try_build()
    {
        Ok(t) => OsTun { iface: Arc::new(t) },
        Err(e) => {
            tracing::error!(
                "Failed to open TUN interface '{}' (Did you run with sudo?): {}",
                args.iface,
                e
            );
            process::exit(1);
        }
    };
    tracing::info!("Allocated server TUN interface: {}", args.iface);

    let (hub, hub_handle) = tun_hub(tun, OUTBOUND_QUEUE);
    tokio::spawn(async move {
        if let Err(e) = hub.run().await {
            tracing::error!("TUN hub stopped: {e}");
        }
    });

    let events = match &args.event_log {
        Some(path) => Some(
            EventLog::to_file("node", &profile.presentation.id, path)
                .map_err(|e| format!("event log {}: {e}", path.display()))?,
        ),
        None => None,
    };

    let ctx = Arc::new(NodeContext {
        capabilities: vec![CapabilityId::Streams, CapabilityId::Rekey],
        node_identity: b"beep-node".to_vec(),
        node_signing_key,
        gate,
        tokens,
        sessions: SessionLimiter::new(args.max_sessions_per_token),
        handshake_permits: Arc::new(Semaphore::new(args.max_handshakes.max(1))),
        handshake_timeout: Duration::from_secs(args.handshake_timeout_secs.max(1)),
        hub: hub_handle,
        events,
    });

    // Prebuild the ALPN list the self-signed lab listener advertises.
    let alpn: Vec<Vec<u8>> = profile
        .presentation
        .alpn
        .iter()
        .map(|a| a.as_bytes().to_vec())
        .collect();

    if let Some(cert_path) = &args.behind_proxy {
        let leaf_der = read_leaf_cert_der(cert_path)
            .map_err(|e| format!("reading proxy certificate {}: {e}", cert_path.display()))?;
        let bind_addr = format!("127.0.0.1:{}", args.port);
        let listener = TcpListener::bind(&bind_addr).await?;
        tracing::info!(
            cert = %cert_path.display(),
            "Listening plain WebSocket on {bind_addr} (loopback only; a front proxy owns TLS)"
        );

        loop {
            let (tcp_stream, remote_addr) = listener.accept().await?;
            let ctx = ctx.clone();
            let binding = binding_from_leaf(WS_BINDING_LABEL, Some(&leaf_der));
            tokio::spawn(async move {
                let conn = match accept_ws(tcp_stream, &ctx.gate, binding).await {
                    Ok(c) => c,
                    Err(e) => {
                        tracing::debug!("Beep accept error (expected for scans): {}", e);
                        return;
                    }
                };
                serve_connection(ctx, conn, remote_addr).await;
            });
        }
    } else if args.insecure {
        let cert = rcgen::generate_simple_self_signed(vec!["localhost".to_string()]).unwrap();
        let raw_der = cert.cert.der().to_vec();
        let cert_der = rustls::pki_types::CertificateDer::from(raw_der.clone());
        let key_der =
            rustls::pki_types::PrivateKeyDer::try_from(cert.key_pair.serialize_der()).unwrap();

        let mut config = rustls::ServerConfig::builder()
            .with_no_client_auth()
            .with_single_cert(vec![cert_der], key_der)?;
        config.alpn_protocols = alpn;

        let bind_addr = format!("0.0.0.0:{}", args.port);
        let listener = TcpListener::bind(&bind_addr).await?;
        let acceptor = TlsAcceptor::from(Arc::new(config));
        tracing::info!("Listening WSS on {bind_addr} (self-signed, lab only)");

        loop {
            let (tcp_stream, remote_addr) = listener.accept().await?;
            let ctx = ctx.clone();
            let acceptor = acceptor.clone();
            let cert_der = raw_der.clone();
            tokio::spawn(async move {
                let tls_stream = match acceptor.accept(tcp_stream).await {
                    Ok(s) => s,
                    Err(e) => {
                        tracing::error!("TLS accept error: {}", e);
                        return;
                    }
                };
                let binding = binding_from_leaf(WS_BINDING_LABEL, Some(&cert_der));
                let conn = match accept_ws(tls_stream, &ctx.gate, binding).await {
                    Ok(c) => c,
                    Err(e) => {
                        tracing::debug!("Beep accept error (expected for scans): {}", e);
                        return;
                    }
                };
                serve_connection(ctx, conn, remote_addr).await;
            });
        }
    } else {
        tracing::error!(
            "Specify either --insecure (self-signed TLS, lab only) or \
             --behind-proxy <leaf-cert.pem> (plain WebSocket on 127.0.0.1, \
             for running behind a front proxy)."
        );
        process::exit(1);
    }
}

/// One connection that already passed the cover layer: bound a handshake
/// permit, run the authenticated handshake under a timeout, and on success
/// hand the session a TUN endpoint and run it.
async fn serve_connection<C: CoverConn + 'static>(
    ctx: Arc<NodeContext>,
    mut conn: C,
    remote: SocketAddr,
) {
    // Bound concurrent in-flight handshakes: beyond the limit, drop rather
    // than queue, so a flood of half-open handshakes cannot pile up.
    let permit = match ctx.handshake_permits.clone().try_acquire_owned() {
        Ok(p) => p,
        Err(_) => {
            tracing::warn!(%remote, "too many handshakes in flight; dropping connection");
            return;
        }
    };

    if let Some(ev) = &ctx.events {
        ev.emit(&Event::HandshakeStart);
    }
    let hs_start = std::time::Instant::now();
    let result = tokio::time::timeout(ctx.handshake_timeout, authenticate(&ctx, &mut conn)).await;
    let (keys, _slot) = match result {
        Ok(Ok(v)) => {
            if let Some(ev) = &ctx.events {
                ev.emit(&Event::HandshakeEnd {
                    ok: true,
                    duration_ms: hs_start.elapsed().as_millis() as u64,
                    detail: None,
                });
            }
            v
        }
        Ok(Err(e)) => {
            if let Some(ev) = &ctx.events {
                ev.emit(&Event::HandshakeEnd {
                    ok: false,
                    duration_ms: hs_start.elapsed().as_millis() as u64,
                    detail: Some(e.clone()),
                });
            }
            tracing::debug!(%remote, "handshake rejected: {e}");
            return;
        }
        Err(_) => {
            if let Some(ev) = &ctx.events {
                ev.emit(&Event::HandshakeEnd {
                    ok: false,
                    duration_ms: hs_start.elapsed().as_millis() as u64,
                    detail: Some("handshake timed out".into()),
                });
            }
            tracing::debug!(%remote, "handshake timed out");
            return;
        }
    };
    // Handshake done: free the permit so the next client can start. The
    // per-token session slot (`_slot`) is held for the session's lifetime.
    drop(permit);

    tracing::info!(%remote, "session established");
    let session_tun = ctx.hub.register(SESSION_INBOUND_QUEUE);
    let driver = SessionDriver::new(conn, &keys, false);
    let mut mux = RuntimeMultiplexer::new(driver, session_tun, false);
    if let Some(ev) = &ctx.events {
        mux = mux.with_events(ev.clone());
    }
    if let Err(e) = mux.run().await {
        tracing::warn!(%remote, "session ended: {e}");
    }
}

/// Run the four-flight server handshake, checking the client token before any
/// session state is allocated and reserving a per-token session slot. Returns
/// the session keys and the slot guard on success.
async fn authenticate<C: CoverConn>(
    ctx: &NodeContext,
    conn: &mut C,
) -> Result<(SessionKeys, SessionSlot), String> {
    let binding = conn.transport_binding();
    let mut hs = ServerHandshake::new(ServerConfig {
        supported_versions: vec![CoreVersion::V1],
        transport_binding: binding,
        capabilities: ctx.capabilities.clone(),
        node_identity: ctx.node_identity.clone(),
        policy_epoch: 1,
        node_signing_key: ctx.node_signing_key,
    });

    let init = conn
        .recv()
        .await
        .map_err(|e| e.to_string())?
        .ok_or("transport closed before ClientInit")?;
    let client_init = hs.process_client_init(&init).map_err(|e| e.to_string())?;

    // Token check comes before create_server_init, so an unauthenticated
    // client never causes the node to derive or hold session material.
    if !ctx.tokens.admits(&client_init.auth_data) {
        return Err("client token not recognised".into());
    }
    let slot = ctx
        .sessions
        .try_acquire(&client_init.auth_data)
        .ok_or("per-token session limit reached")?;

    let server_init = hs.create_server_init().map_err(|e| e.to_string())?;
    conn.send(Bytes::from(server_init))
        .await
        .map_err(|e| e.to_string())?;

    let finish = conn
        .recv()
        .await
        .map_err(|e| e.to_string())?
        .ok_or("transport closed before ClientFinish")?;
    hs.process_client_finish(&finish)
        .map_err(|e| e.to_string())?;

    let (server_finish, keys) = hs.create_server_finish().map_err(|e| e.to_string())?;
    conn.send(Bytes::from(server_finish))
        .await
        .map_err(|e| e.to_string())?;

    Ok((keys, slot))
}

// ── Key / cert file helpers ───────────────────────────────────────────────

/// Read a node Ed25519 secret key: a file of 64 hex characters (32 bytes).
fn read_node_key(path: &Path) -> io::Result<[u8; 32]> {
    let text = std::fs::read_to_string(path)?;
    decode_hex32(text.trim())
        .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "expected 64 hex characters"))
}

/// Read a PEM file's first certificate (the leaf) as DER, for computing the
/// same transport binding a TLS-terminating node would. This must be the exact
/// certificate the front proxy presents publicly — not a copy with the same
/// subject — since the binding is a hash of the DER bytes themselves.
fn read_leaf_cert_der(path: &Path) -> io::Result<Vec<u8>> {
    let mut reader = io::BufReader::new(std::fs::File::open(path)?);
    let mut certs = rustls_pemfile::certs(&mut reader);
    match certs.next() {
        Some(Ok(der)) => Ok(der.to_vec()),
        Some(Err(e)) => Err(e),
        None => Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "no certificate found in PEM file",
        )),
    }
}

fn hex_encode(bytes: &[u8]) -> String {
    let mut s = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        s.push_str(&format!("{b:02x}"));
    }
    s
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn disabled_token_auth_admits_everyone() {
        let auth = TokenAuth { allowed: vec![] };
        assert!(!auth.enforced());
        assert!(auth.admits(b""));
        assert!(auth.admits(b"anything"));
    }

    #[test]
    fn enforced_token_auth_admits_only_listed_tokens() {
        let auth = TokenAuth {
            allowed: vec![b"alpha-token".to_vec(), b"beta-token".to_vec()],
        };
        assert!(auth.enforced());
        assert!(auth.admits(b"alpha-token"));
        assert!(auth.admits(b"beta-token"));
        // Wrong value, a prefix, and empty are all refused — a foreign client
        // without a listed token cannot get in.
        assert!(!auth.admits(b"gamma-token"));
        assert!(!auth.admits(b"alpha"));
        assert!(!auth.admits(b""));
    }

    #[test]
    fn session_limiter_caps_per_token_and_releases_on_drop() {
        let limiter = SessionLimiter::new(2);
        let a = limiter.try_acquire(b"tok").expect("first slot");
        let _b = limiter.try_acquire(b"tok").expect("second slot");
        // Third exceeds the cap of 2.
        assert!(limiter.try_acquire(b"tok").is_none());
        // A different token has its own budget.
        assert!(limiter.try_acquire(b"other").is_some());
        // Releasing one frees a slot for the capped token.
        drop(a);
        assert!(limiter.try_acquire(b"tok").is_some());
    }

    #[test]
    fn constant_time_eq_matches_only_equal_slices() {
        assert!(constant_time_eq(b"abc", b"abc"));
        assert!(!constant_time_eq(b"abc", b"abd"));
        assert!(!constant_time_eq(b"abc", b"ab"));
    }
}
