use async_trait::async_trait;
use beep_core::key_schedule::SessionKeys;
use beep_core::session::{ClientConfig, ClientHandshake};
use beep_core_types::{CapabilityId, CoreVersion, ProfileFile, Role};
use beep_cover_wss::{
    ChromeDialer, ChromePreset, ChromeWsConn, RootCerts, RustlsDialer, WssCoverConn,
};
use beep_runtime::{Event, EventLog, KeepaliveConfig, RuntimeMultiplexer, TunDevice};
use beep_session::SessionDriver;
use beep_transport::{CoverConn, CoverDialer, DialTarget, TransportCapabilities, TransportError};
use bytes::Bytes;
use clap::Parser;
use std::io;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::Duration;
use tokio::net::TcpStream;
use tokio_rustls::client::TlsStream;
use tokio_tun::TunBuilder;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Remote node address (e.g., 12.34.56.78:443)
    #[arg(short, long)]
    server: String,

    /// Wire profile (presentation + transport). Re-read on every connection
    /// attempt, so editing it changes behaviour without a rebuild or restart.
    #[arg(long)]
    profile: PathBuf,

    /// TUN interface name (defaults to beep0)
    #[arg(short, long, default_value = "beep0")]
    iface: String,

    /// IP address of the local TUN device in CIDR (e.g., 10.8.0.2)
    #[arg(long, default_value = "10.8.0.2")]
    address: String,

    /// Authentication token presented to the node. Required when the node
    /// enforces tokens; without the right one the tunnel is refused.
    #[arg(long, default_value = "")]
    token: String,

    /// Accept any certificate the node presents. Lab and test builds only.
    #[arg(long)]
    insecure: bool,

    /// Append a JSON event log (handshake timing, byte counts, stalls,
    /// disconnect reason) to this file, for the test bench.
    #[arg(long)]
    event_log: Option<PathBuf>,

    /// Control download: fetch this path from the cover site over the same TLS
    /// stack and profile, with no tunnel, then exit. The test-bench baseline
    /// for comparing against a Beep session.
    #[arg(long)]
    control_download: Option<String>,
}

// ── Physical Tun Adapter ────────────────────────────────────────────────

struct OsTun {
    iface: Arc<tokio_tun::Tun>,
}

// Shared so the same TUN interface survives across reconnect attempts.
impl Clone for OsTun {
    fn clone(&self) -> Self {
        Self {
            iface: Arc::clone(&self.iface),
        }
    }
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

// ── Presentation connection ─────────────────────────────────────────────

/// Either backend a profile can select, behind one [`CoverConn`].
///
/// `RuntimeMultiplexer`/`SessionDriver` are generic over a single concrete
/// `CoverConn` type; this enum is how one profile-driven client picks between
/// them at run time without a trait object (`CoverConn`'s methods return
/// `impl Future`, so it is not object-safe).
///
/// Both variants are boxed: a `WebSocketStream`'s internal buffers make the
/// rustls side over 1400 bytes on its own, and clippy's `large_enum_variant`
/// wants the variants kept close in size rather than just the largest one
/// shrunk, so the smaller (Chrome) side is boxed too.
enum PresentationConn {
    Rustls(Box<WssCoverConn<TlsStream<TcpStream>>>),
    Chrome(Box<ChromeWsConn>),
}

impl CoverConn for PresentationConn {
    async fn send(&mut self, data: Bytes) -> Result<(), TransportError> {
        match self {
            Self::Rustls(c) => c.send(data).await,
            Self::Chrome(c) => c.send(data).await,
        }
    }

    async fn recv(&mut self) -> Result<Option<Bytes>, TransportError> {
        match self {
            Self::Rustls(c) => c.recv().await,
            Self::Chrome(c) => c.recv().await,
        }
    }

    fn transport_binding(&self) -> [u8; 32] {
        match self {
            Self::Rustls(c) => c.transport_binding(),
            Self::Chrome(c) => c.transport_binding(),
        }
    }

    fn capabilities(&self) -> TransportCapabilities {
        match self {
            Self::Rustls(c) => c.capabilities(),
            Self::Chrome(c) => c.capabilities(),
        }
    }
}

/// Dial using whichever backend `profile` names.
async fn dial(
    profile: &ProfileFile,
    target: &DialTarget,
    insecure: bool,
) -> Result<PresentationConn, TransportError> {
    match profile.presentation.tls_provider.as_str() {
        "boringssl" => {
            let preset =
                ChromePreset::parse(&profile.presentation.fingerprint).ok_or_else(|| {
                    TransportError::Tls(format!(
                        "unknown fingerprint `{}`",
                        profile.presentation.fingerprint
                    ))
                })?;
            let dialer = if insecure {
                ChromeDialer::insecure(preset)
            } else {
                ChromeDialer::new(preset)
            };
            dialer
                .dial(target)
                .await
                .map(|c| PresentationConn::Chrome(Box::new(c)))
        }
        _ => {
            let roots = if insecure {
                RootCerts::Insecure
            } else {
                RootCerts::System
            };
            RustlsDialer::new(roots)
                .dial(target)
                .await
                .map(|c| PresentationConn::Rustls(Box::new(c)))
        }
    }
}

// ── Main Entrypoint ─────────────────────────────────────────────────────

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt::init();
    let args = Args::parse();

    // Fix crypto provider once natively
    let _ = rustls::crypto::ring::default_provider().install_default();

    // Fail fast on a bad profile rather than after dialing.
    let profile = ProfileFile::load_validated(&args.profile, Role::Client)
        .map_err(|e| format!("profile {}: {e}", args.profile.display()))?;
    tracing::info!(
        profile = %profile.presentation.id,
        provider = %profile.presentation.tls_provider,
        "Loaded wire profile"
    );

    // Control-download mode: a plain HTTPS fetch over the same TLS stack and
    // profile, no tunnel, then exit. No TUN device is created.
    if let Some(dl_path) = &args.control_download {
        let addr: std::net::SocketAddr = args
            .server
            .parse()
            .map_err(|_| format!("invalid --server address: {}", args.server))?;
        let events = match &args.event_log {
            Some(path) => Some(
                EventLog::to_file("client", &profile.presentation.id, path)
                    .map_err(|e| format!("event log {}: {e}", path.display()))?,
            ),
            None => None,
        };
        tracing::info!(
            server = %args.server,
            host = %profile.presentation.server_name,
            path = %dl_path,
            "Control download (no tunnel)..."
        );
        match beep_cover_wss::control_download(&profile, addr, args.insecure, dl_path).await {
            Ok(r) => {
                tracing::info!(
                    status = r.status,
                    bytes = r.bytes,
                    ms = r.duration.as_millis() as u64,
                    "Control download complete"
                );
                if let Some(ev) = &events {
                    ev.emit(&Event::ControlDownload {
                        ok: (200..400).contains(&r.status),
                        status: r.status,
                        bytes: r.bytes,
                        duration_ms: r.duration.as_millis() as u64,
                    });
                }
            }
            Err(e) => {
                tracing::error!("Control download failed: {e}");
                if let Some(ev) = &events {
                    ev.emit(&Event::ControlDownload {
                        ok: false,
                        status: 0,
                        bytes: 0,
                        duration_ms: 0,
                    });
                }
                return Err(e.into());
            }
        }
        return Ok(());
    }

    tracing::info!("Initializing Beep Client...");

    // Create the TUN interface once and share it across reconnects, so the
    // interface, its address and routes survive transient connection drops.
    let tun = match TunBuilder::new()
        .name(&args.iface)
        .tap(false) // Pure IP L3
        .packet_info(false)
        .mtu(1420)
        .up()
        .address(args.address.parse().unwrap())
        .destination("10.8.0.1".parse().unwrap()) // Route default exit to node
        .netmask(std::net::Ipv4Addr::new(255, 255, 255, 0))
        .try_build()
    {
        Ok(t) => t,
        Err(e) => {
            tracing::error!(
                "Failed to open TUN interface '{}' (Did you run with sudo?): {}",
                args.iface,
                e
            );
            std::process::exit(1);
        }
    };
    let tun_dev = OsTun {
        iface: Arc::new(tun),
    };
    tracing::info!("Allocated OS TUN Interface: {}", args.iface);

    // Open the event log once (append-mode) and share it across reconnects.
    let events = match &args.event_log {
        Some(path) => Some(
            EventLog::to_file("client", &profile.presentation.id, path)
                .map_err(|e| format!("event log {}: {e}", path.display()))?,
        ),
        None => None,
    };

    loop {
        match run_session(&args, tun_dev.clone(), events.clone()).await {
            Ok(()) => {
                tracing::info!("Session closed cleanly; exiting.");
                break;
            }
            Err(e) => {
                // The pause between attempts, and its random addition, come
                // from the profile that is about to be re-read: a change to
                // handshake_gap_ms/retry_mode takes effect on the very next
                // attempt. Only one attempt is ever in flight (this loop is
                // sequential), so there is never more than one handshake at
                // a time, and the fingerprint/SNI a reconnect uses is fixed
                // by the same unchanged profile file.
                let (base, jitter_cap) =
                    match ProfileFile::load_validated(&args.profile, Role::Client) {
                        Ok(p) => p.presentation.handshake_pacing(),
                        Err(_) => profile.presentation.handshake_pacing(),
                    };
                let jitter = jitter_cap.mul_f64(jitter_fraction());
                let delay = base + jitter;
                tracing::warn!(
                    "Session ended ({e}); reconnecting in {:.1}s",
                    delay.as_secs_f64()
                );
                tokio::time::sleep(delay).await;
            }
        }
    }

    Ok(())
}

/// Establish one Beep session and run it until it ends.
async fn run_session(
    args: &Args,
    tun_dev: OsTun,
    events: Option<EventLog>,
) -> Result<(), Box<dyn std::error::Error>> {
    let profile = ProfileFile::load_validated(&args.profile, Role::Client)
        .map_err(|e| format!("profile {}: {e}", args.profile.display()))?;

    let server_addr_sock: std::net::SocketAddr =
        args.server.parse().expect("Invalid Server IP:Port");
    let target = DialTarget::from_profile(&profile, server_addr_sock);

    tracing::info!(
        server = %args.server,
        sni = %profile.presentation.server_name,
        provider = %profile.presentation.tls_provider,
        "Dialing node..."
    );
    let mut conn = dial(&profile, &target, args.insecure).await?;
    let binding = conn.transport_binding();

    // The pinned node key, if the profile carries one. Validation guarantees a
    // non-empty value decodes, so an error here only means a malformed profile
    // slipped past (treated as fatal for this attempt).
    let expected_node_key = profile.presentation.node_public_key_bytes();
    if !profile.presentation.node_public_key.is_empty() && expected_node_key.is_none() {
        return Err("profile node_public_key is not valid hex".into());
    }

    // Session handshake, timed and logged as one unit so the event log records
    // both success and the reason for any failure.
    tracing::info!("Transport established. Proceeding with Beep Session Check...");
    if let Some(ev) = &events {
        ev.emit(&Event::HandshakeStart);
    }
    let hs_start = std::time::Instant::now();
    let hs_result: Result<SessionKeys, Box<dyn std::error::Error>> = async {
        let mut hs = ClientHandshake::new(ClientConfig {
            core_version: CoreVersion::V1,
            transport_binding: binding,
            capabilities: vec![CapabilityId::Streams, CapabilityId::Rekey],
            auth_method: 0x01,
            auth_data: args.token.as_bytes().to_vec(),
            expected_node_key,
        });
        let client_init = hs.create_client_init()?;
        conn.send(Bytes::from(client_init)).await?;
        let data = conn
            .recv()
            .await?
            .ok_or("transport closed during handshake")?;
        hs.process_server_init(&data)?;
        let client_finish = hs.create_client_finish()?;
        conn.send(Bytes::from(client_finish)).await?;
        let data = conn
            .recv()
            .await?
            .ok_or("transport closed during handshake")?;
        Ok(hs.process_server_finish(&data)?)
    }
    .await;

    let keys = match hs_result {
        Ok(keys) => {
            if let Some(ev) = &events {
                ev.emit(&Event::HandshakeEnd {
                    ok: true,
                    duration_ms: hs_start.elapsed().as_millis() as u64,
                    detail: None,
                });
            }
            keys
        }
        Err(e) => {
            if let Some(ev) = &events {
                ev.emit(&Event::HandshakeEnd {
                    ok: false,
                    duration_ms: hs_start.elapsed().as_millis() as u64,
                    detail: Some(e.to_string()),
                });
            }
            return Err(e);
        }
    };

    tracing::info!("Beep Session keys derived successfully!");

    // Hand over to the runtime multiplexer with keepalive timing from the
    // profile, so a dead peer is detected and this call returns, triggering
    // a reconnect.
    let keepalive = KeepaliveConfig {
        interval: Duration::from_millis(profile.transport.keepalive_ms),
        idle_timeout: Duration::from_millis(profile.transport.idle_timeout_ms),
    };
    let driver = SessionDriver::new(conn, &keys, true);
    let mut mux = RuntimeMultiplexer::new(driver, tun_dev, false).with_keepalive(keepalive);
    if let Some(ev) = &events {
        mux = mux.with_events(ev.clone());
    }

    tracing::info!("Runtime Multiplexer Operational. Traffic is now bridged.");
    mux.run().await?;
    Ok(())
}

/// Dependency-free jitter source in `[0, 1)` for the reconnect pause.
fn jitter_fraction() -> f64 {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.subsec_nanos())
        .unwrap_or(0);
    (nanos % 1_000_000) as f64 / 1_000_000.0
}
