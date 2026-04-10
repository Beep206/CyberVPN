use async_trait::async_trait;
use beep_core::session::{ServerConfig, ServerHandshake};
use beep_core_types::{CapabilityId, CoreVersion};
use beep_cover_wss::accept_wss;
use beep_runtime::{RuntimeMultiplexer, TunDevice};
use beep_session::SessionDriver;
use bytes::Bytes;
use clap::Parser;
use std::io;
use std::process;
use std::sync::Arc;
use tokio::net::TcpListener;
use tokio_rustls::TlsAcceptor;
use tokio_tun::TunBuilder;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Port to listen on
    #[arg(short, long, default_value_t = 4443)]
    port: u16,

    /// TUN interface name 
    #[arg(short, long, default_value = "beep_server0")]
    iface: String,

    /// IP address of the node TUN device in CIDR (e.g., 10.8.0.1)
    #[arg(long, default_value = "10.8.0.1")]
    address: String,

    /// Run with auto-generated dev certificates
    #[arg(long)]
    insecure: bool,
}

// ── Physical Tun Adapter ────────────────────────────────────────────────

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

// ── Shared Helper to wrap OS Tun reference ─────────────────────────────

impl Clone for OsTun {
    fn clone(&self) -> Self {
        Self {
            iface: Arc::clone(&self.iface),
        }
    }
}

// ── Main Entrypoint ─────────────────────────────────────────────────────

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt::init();
    let args = Args::parse();
    
    let _ = rustls::crypto::ring::default_provider().install_default();

    tracing::info!("Initializing Beep Node Server...");

    // 1. Create Server TUN Interface (Requires root on Linux)
    let tun = match TunBuilder::new()
        .name(&args.iface)
        .tap(false) // Pure L3
        .packet_info(false)
        .mtu(1420)
        .up()
        .address(args.address.parse().unwrap())
        .netmask(std::net::Ipv4Addr::new(255, 255, 255, 0))
        .try_build()
    {
        Ok(t) => Arc::new(t),
        Err(e) => {
            tracing::error!("Failed to open TUN interface '{}' (Did you run with sudo?): {}", args.iface, e);
            process::exit(1);
        }
    };
    
    let tun_dev = OsTun { iface: tun };
    tracing::info!("Allocated Server TUN Interface: {}", args.iface);

    // 2. Setup TLS Server Config
    let (server_tls, cert_der_bytes) = if args.insecure {
        let cert = rcgen::generate_simple_self_signed(vec!["localhost".to_string()]).unwrap();
        let raw_der = cert.cert.der().to_vec();
        let cert_der = rustls::pki_types::CertificateDer::from(raw_der.clone());
        let key_der = rustls::pki_types::PrivateKeyDer::try_from(cert.key_pair.serialize_der()).unwrap();
        
        let mut config = rustls::ServerConfig::builder()
            .with_no_client_auth()
            .with_single_cert(vec![cert_der], key_der)?;
        config.alpn_protocols = vec![beep_cover_wss::BEEP_ALPN.to_vec()];
        (Arc::new(config), raw_der)
    } else {
        tracing::error!("Production cert loading not implemented in this version (use --insecure).");
        process::exit(1);
    };

    // 3. Bind TCP Listener
    let addr = format!("0.0.0.0:{}", args.port);
    let listener = TcpListener::bind(&addr).await?;
    let acceptor = TlsAcceptor::from(server_tls);
    
    tracing::info!("Listening WSS / TCP on {}", addr);

    loop {
        let (tcp_stream, remote_addr) = listener.accept().await?;
        tracing::info!("New TCP connection from {}", remote_addr);
        
        // Spawn each connection logic
        let acceptor_clone = acceptor.clone();
        let cert_der_clone = cert_der_bytes.clone();
        let client_tun = tun_dev.clone();

        tokio::spawn(async move {
            let tls_stream = match acceptor_clone.accept(tcp_stream).await {
                Ok(s) => s,
                Err(e) => {
                    tracing::error!("TLS Accept error: {}", e);
                    return;
                }
            };
            
            // Apply cover layer
            let mut conn = match accept_wss(tls_stream, &cert_der_clone).await {
                Ok(c) => c,
                Err(e) => {
                    tracing::error!("Beep Accept WSS error: {}", e);
                    return;
                }
            };

            use beep_transport::CoverConn;
            let binding = conn.transport_binding();

            // Handshake session
            let mut hs = ServerHandshake::new(ServerConfig {
                supported_versions: vec![CoreVersion::V1],
                transport_binding: binding,
                capabilities: vec![CapabilityId::Streams, CapabilityId::Rekey],
                node_identity: b"test-node-wss".to_vec(),
                policy_epoch: 1,
            });

            // Very simple sequential HS blocking setup
            let data = match conn.recv().await {
                Ok(Some(d)) => d,
                _ => return,
            };
            
            if let Err(e) = hs.process_client_init(&data) {
                tracing::error!("Handshake init err: {}", e);
                return;
            }
            
            let server_init = hs.create_server_init().unwrap();
            if conn.send(Bytes::from(server_init)).await.is_err() { return; }
            
            let data = match conn.recv().await {
                Ok(Some(d)) => d,
                _ => return,
            };
            
            if let Err(e) = hs.process_client_finish(&data) {
                tracing::error!("Handshake finalize err: {}", e);
                return;
            }
            
            let (server_finish, keys) = hs.create_server_finish().unwrap();
            let _ = conn.send(Bytes::from(server_finish)).await;

            tracing::info!("Session [{}] verified completely via {}", remote_addr, "WSS");

            let driver = SessionDriver::new(conn, &keys, false);
            let mut mux = RuntimeMultiplexer::new(driver, client_tun, false);
            
            tracing::info!("Multiplexer initialized for Client [{}]", remote_addr);
            if let Err(e) = mux.run().await {
                tracing::warn!("Multiplexer closed loop: {}", e);
            }
        });
    }
}
