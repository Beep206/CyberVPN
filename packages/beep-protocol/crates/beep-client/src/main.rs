use async_trait::async_trait;
use beep_core::session::{ClientConfig, ClientHandshake};
use beep_core_types::{CapabilityId, CoreVersion};
use beep_cover_wss::{connect_wss, BEEP_ALPN};
use beep_runtime::{RuntimeMultiplexer, TunDevice};
use beep_session::SessionDriver;
use beep_transport::CoverConn;
use bytes::Bytes;
use clap::Parser;
use std::io;
use std::sync::Arc;
use tokio_tun::TunBuilder;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Remote node address (e.g., 12.34.56.78:443)
    #[arg(short, long)]
    server: String,

    /// Remote SNI domain name (e.g., node1.beep.vpn)
    #[arg(long, default_value = "localhost")]
    domain: String,

    /// TUN interface name (defaults to beep0)
    #[arg(short, long, default_value = "beep0")]
    iface: String,

    /// IP address of the local TUN device in CIDR (e.g., 10.8.0.2)
    #[arg(long, default_value = "10.8.0.2")]
    address: String,

    /// Use insecure TLS verification (only for dev/testing)
    #[arg(long)]
    insecure: bool,
}

// ── Physical Tun Adapter ────────────────────────────────────────────────

struct OsTun {
    iface: tokio_tun::Tun,
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

// ── Insecure Dev Verifier ───────────────────────────────────────────────

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
    
    // Additional boilerplate for signatures omitted, we assume standard TLS
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

// ── Main Entrypoint ─────────────────────────────────────────────────────

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt::init();
    let args = Args::parse();
    
    // Fix crypto provider once natively
    let _ = rustls::crypto::ring::default_provider().install_default();

    tracing::info!("Initializing Beep Client...");

    // 1. Create TUN Interface (Requires root on Linux)
    // We bind with 10.8.0.2 / 24 standard for clients
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
            tracing::error!("Failed to open TUN interface '{}' (Did you run with sudo?): {}", args.iface, e);
            std::process::exit(1);
        }
    };
    
    let tun_dev = OsTun { iface: tun };
    tracing::info!("Allocated OS TUN Interface: {}", args.iface);

    // 2. Setup TLS Config
    let mut tls_config = if args.insecure {
        rustls::ClientConfig::builder()
            .dangerous()
            .with_custom_certificate_verifier(Arc::new(InsecureVerifier))
            .with_no_client_auth()
    } else {
        let root_store = rustls::RootCertStore::empty();
        rustls::ClientConfig::builder()
            .with_root_certificates(root_store)
            .with_no_client_auth()
    };
    tls_config.alpn_protocols = vec![BEEP_ALPN.to_vec()];

    // 3. Connect Dial Cover Transport (WSS in this case)
    let server_addr_sock: std::net::SocketAddr = args.server.parse().expect("Invalid Server IP:Port");
    tracing::info!("Dialing server at {}...", args.server);
    let mut conn = connect_wss(server_addr_sock, &args.domain, "vpn", tls_config).await?;

    let binding = conn.transport_binding();
    
    // 4. Session Handshake
    tracing::info!("Transport established. Proceeding with Beep Session Check...");
    let mut hs = ClientHandshake::new(ClientConfig {
        core_version: CoreVersion::V1,
        transport_binding: binding,
        capabilities: vec![CapabilityId::Streams, CapabilityId::Rekey],
        auth_method: 0x01,
        auth_data: vec![0xAA; 16],
    });
    
    let client_init = hs.create_client_init()?;
    conn.send(Bytes::from(client_init)).await?;
    let data = conn.recv().await?.expect("EOF");
    hs.process_server_init(&data)?;
    let client_finish = hs.create_client_finish()?;
    conn.send(Bytes::from(client_finish)).await?;
    let data = conn.recv().await?.expect("EOF");
    let keys = hs.process_server_finish(&data)?;

    tracing::info!("Beep Session keys derived successfully!");
    
    // 5. Hand over to RuntimeMultiplexer
    let driver = SessionDriver::new(conn, &keys, true);
    // WSS does not natively support datagrams efficiently without overhead, segment over streams
    let mut mux = RuntimeMultiplexer::new(driver, tun_dev, false);
    
    tracing::info!("Runtime Multiplexer Operational. Traffic is now bridged.");
    let _ = mux.run().await;

    Ok(())
}
