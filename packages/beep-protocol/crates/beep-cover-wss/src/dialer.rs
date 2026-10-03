//! [`CoverDialer`] implementations for the WSS transport family.
//!
//! Two backends, selected by a [`PresentationProfile`]'s `tls_provider`:
//!
//! - [`RustlsDialer`]: a plain rustls connection. Its own ClientHello is
//!   whatever the installed rustls/ring version produces; nothing shapes it
//!   further. This is the fallback profile.
//! - [`ChromeDialer`]: a BoringSSL connection configured to produce the same
//!   ClientHello as a specific Chrome release (via `wreq`/`wreq-util`). Used
//!   when a profile asks for a `chrome_NNN` fingerprint.
//!
//! [`PresentationProfile`]: beep_core_types::artifact::PresentationProfile

use std::net::SocketAddr;
use std::sync::Arc;
use std::time::{Duration, Instant};

use beep_core_types::artifact::{HttpMode, SniMode};
use beep_core_types::profile::ProfileFile;
use beep_transport::{
    binding_from_leaf, CoverConn, CoverDialer, DialTarget, TransportCapabilities, TransportError,
    WS_BINDING_LABEL,
};
use bytes::Bytes;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpStream;
use tokio_rustls::TlsConnector;
use wreq::IntoEmulation;

use crate::{client_ws_handshake, WssCoverConn};

// ── rustls dialer ───────────────────────────────────────────────────────

/// Where a [`RustlsDialer`] gets its trust anchors.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RootCerts {
    /// The operating system's trust store.
    System,
    /// Accept any certificate. Lab and test builds only.
    Insecure,
}

/// Plain rustls dialer: standard TLS, no fingerprint shaping.
pub struct RustlsDialer {
    roots: RootCerts,
}

impl RustlsDialer {
    /// A dialer that verifies against the system trust store.
    pub fn new(roots: RootCerts) -> Self {
        Self { roots }
    }
}

#[derive(Debug)]
struct LabInsecureVerifier;

impl rustls::client::danger::ServerCertVerifier for LabInsecureVerifier {
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

fn system_roots() -> rustls::RootCertStore {
    let mut roots = rustls::RootCertStore::empty();
    let loaded = rustls_native_certs::load_native_certs();
    for err in &loaded.errors {
        tracing::warn!(%err, "skipped an unreadable system certificate");
    }
    let mut added = 0usize;
    for cert in loaded.certs {
        if roots.add(cert).is_ok() {
            added += 1;
        }
    }
    tracing::debug!(added, "loaded system root certificates");
    roots
}

fn client_tls_leaf(s: &tokio_rustls::client::TlsStream<TcpStream>) -> Option<Vec<u8>> {
    let (_io, conn) = s.get_ref();
    conn.peer_certificates()
        .and_then(|c| c.first())
        .map(|c| c.as_ref().to_vec())
}

impl CoverDialer for RustlsDialer {
    type Conn = WssCoverConn<tokio_rustls::client::TlsStream<TcpStream>>;

    async fn dial(&self, target: &DialTarget) -> Result<Self::Conn, TransportError> {
        let mut config = match self.roots {
            RootCerts::System => rustls::ClientConfig::builder()
                .with_root_certificates(system_roots())
                .with_no_client_auth(),
            RootCerts::Insecure => rustls::ClientConfig::builder()
                .dangerous()
                .with_custom_certificate_verifier(Arc::new(LabInsecureVerifier))
                .with_no_client_auth(),
        };
        config.alpn_protocols = target.alpn.iter().map(|s| s.as_bytes().to_vec()).collect();

        // rustls only emits the SNI extension for a DNS-name ServerName, so
        // routing an "omit" profile through the IP-literal variant is enough;
        // no separate switch is needed.
        let server_name = match target.sni {
            SniMode::Omit => rustls::pki_types::ServerName::IpAddress(target.addr.ip().into()),
            SniMode::ServerName => {
                rustls::pki_types::ServerName::try_from(target.server_name.clone())
                    .map_err(|e| TransportError::Tls(e.to_string()))?
            }
        };

        let connector = TlsConnector::from(Arc::new(config));
        let tcp = tokio::time::timeout(target.connect_timeout, TcpStream::connect(target.addr))
            .await
            .map_err(|_| TransportError::Timeout)?
            .map_err(|e| TransportError::Io(e.to_string()))?;
        let tls = tokio::time::timeout(target.connect_timeout, connector.connect(server_name, tcp))
            .await
            .map_err(|_| TransportError::Timeout)?
            .map_err(|e| TransportError::Tls(e.to_string()))?;

        let leaf = client_tls_leaf(&tls);
        let binding = binding_from_leaf(WS_BINDING_LABEL, leaf.as_deref());
        client_ws_handshake(
            tls,
            &target.server_name,
            &target.path,
            &target.headers,
            binding,
        )
        .await
    }
}

// ── Chrome-fingerprint dialer ───────────────────────────────────────────

/// A Chrome release this dialer can present as.
///
/// Add a variant here only once the matching version is in `wreq-util`'s
/// Chrome profile list; [`ChromePreset::parse`] is the single place that maps
/// a profile's `fingerprint` string to one.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[non_exhaustive]
pub enum ChromePreset {
    /// `chrome_140`
    Chrome140,
    /// `chrome_141` — matches the Chromium build validated in the lab.
    Chrome141,
    /// `chrome_142`
    Chrome142,
}

impl ChromePreset {
    /// Parse a `PresentationProfile.fingerprint` value such as `chrome_141`.
    pub fn parse(fingerprint: &str) -> Option<Self> {
        match fingerprint {
            "chrome_140" => Some(Self::Chrome140),
            "chrome_141" => Some(Self::Chrome141),
            "chrome_142" => Some(Self::Chrome142),
            _ => None,
        }
    }

    fn profile(self) -> wreq_util::Profile {
        match self {
            Self::Chrome140 => wreq_util::Profile::Chrome140,
            Self::Chrome141 => wreq_util::Profile::Chrome141,
            Self::Chrome142 => wreq_util::Profile::Chrome142,
        }
    }
}

/// Dials with a BoringSSL ClientHello shaped to match a real Chrome release.
pub struct ChromeDialer {
    preset: ChromePreset,
    insecure: bool,
}

impl ChromeDialer {
    /// Verify the peer certificate normally.
    pub fn new(preset: ChromePreset) -> Self {
        Self {
            preset,
            insecure: false,
        }
    }

    /// Skip certificate verification. Lab and test builds only.
    pub fn insecure(preset: ChromePreset) -> Self {
        Self {
            preset,
            insecure: true,
        }
    }
}

impl CoverDialer for ChromeDialer {
    type Conn = ChromeWsConn;

    async fn dial(&self, target: &DialTarget) -> Result<Self::Conn, TransportError> {
        if target.sni == SniMode::Omit {
            // A real browser always sends SNI; omitting it here would itself
            // be the detail that gives the connection away.
            return Err(TransportError::Tls(
                "sni_mode = omit is not compatible with a browser TLS fingerprint".into(),
            ));
        }

        let mut emulation = wreq_util::Emulation::builder()
            .profile(self.preset.profile())
            .platform(wreq_util::Platform::Linux)
            .build()
            .into_emulation();
        if target.http == HttpMode::WsH1 {
            // Chrome's own WebSocket-over-HTTP/1.1 upgrade carries no ALPS
            // extension; the profile's default is set for a normal page load
            // (ALPN h2, http/1.1) and is cleared here to match what a browser
            // actually sends for a cold WebSocket connection.
            if let Some(tls) = emulation.tls_options.as_mut() {
                tls.alps_protocols = None;
            }
        }

        let client = wreq::Client::builder()
            .emulation(emulation)
            .resolve(target.server_name.clone(), target.addr)
            .connect_timeout(target.connect_timeout)
            .tls_info(true)
            .tls_cert_verification(!self.insecure)
            .build()
            .map_err(|e| TransportError::Tls(e.to_string()))?;

        let path = target.path.trim_start_matches('/');
        let url = format!("wss://{}/{path}", target.server_name);
        let mut builder = client.websocket(&url).version(match target.http {
            HttpMode::WsH1 => http::Version::HTTP_11,
            HttpMode::WsH2 => http::Version::HTTP_2,
        });
        for (name, value) in &target.headers {
            builder = builder.header(name.as_str(), value.as_str());
        }

        let resp = builder
            .send()
            .await
            .map_err(|e| TransportError::Tls(e.to_string()))?;
        let leaf = resp
            .extensions()
            .get::<wreq::tls::TlsInfo>()
            .and_then(|info| info.peer_certificate().map(|c| c.to_vec()));
        let binding = binding_from_leaf(WS_BINDING_LABEL, leaf.as_deref());
        let ws = resp
            .into_websocket()
            .await
            .map_err(|e| TransportError::Tls(e.to_string()))?;
        Ok(ChromeWsConn {
            inner: ws,
            transport_binding: binding,
        })
    }
}

/// A [`CoverConn`] over a [`ChromeDialer`] connection.
#[derive(Debug)]
pub struct ChromeWsConn {
    inner: wreq::ws::WebSocket,
    transport_binding: [u8; 32],
}

impl CoverConn for ChromeWsConn {
    async fn send(&mut self, data: Bytes) -> Result<(), TransportError> {
        self.inner
            .send(wreq::ws::message::Message::binary(data))
            .await
            .map_err(|e| TransportError::Tls(e.to_string()))
    }

    async fn recv(&mut self) -> Result<Option<Bytes>, TransportError> {
        use wreq::ws::message::Message;
        loop {
            match self.inner.recv().await {
                Some(Ok(Message::Binary(data))) => return Ok(Some(data)),
                Some(Ok(Message::Close(_))) | None => return Ok(None),
                Some(Ok(_)) => continue,
                Some(Err(e)) => return Err(TransportError::Tls(e.to_string())),
            }
        }
    }

    fn transport_binding(&self) -> [u8; 32] {
        self.transport_binding
    }

    fn capabilities(&self) -> TransportCapabilities {
        TransportCapabilities {
            supports_streams: true,
            supports_datagrams: false,
            supports_migration: false,
        }
    }
}

// ── Control download (test-bench baseline) ──────────────────────────────
//
// A plain HTTPS GET of a file from the cover site, using the same TLS stack
// and profile a Beep session would, but with no tunnel. This is the control
// the stand compares Beep against: it shows whether an ordinary HTTPS fetch
// from the same server, with the same fingerprint, gets through.

/// Outcome of one control download.
#[derive(Debug, Clone)]
pub struct ControlResult {
    /// HTTP status code of the response.
    pub status: u16,
    /// Number of body bytes received.
    pub bytes: u64,
    /// Wall-clock time from connect start to the full body.
    pub duration: Duration,
}

/// Fetch `path` from the cover site named by `profile`, over the same TLS
/// provider and fingerprint a Beep session would use, without a tunnel.
pub async fn control_download(
    profile: &ProfileFile,
    addr: SocketAddr,
    insecure: bool,
    path: &str,
) -> Result<ControlResult, TransportError> {
    let target = DialTarget::from_profile(profile, addr);
    match profile.presentation.tls_provider.as_str() {
        "boringssl" => {
            let preset =
                ChromePreset::parse(&profile.presentation.fingerprint).ok_or_else(|| {
                    TransportError::Tls(format!(
                        "unknown fingerprint `{}`",
                        profile.presentation.fingerprint
                    ))
                })?;
            control_download_chrome(preset, &target, insecure, path).await
        }
        _ => {
            let roots = if insecure {
                RootCerts::Insecure
            } else {
                RootCerts::System
            };
            control_download_rustls(roots, &target, path).await
        }
    }
}

async fn control_download_chrome(
    preset: ChromePreset,
    target: &DialTarget,
    insecure: bool,
    path: &str,
) -> Result<ControlResult, TransportError> {
    // An ordinary page/file load keeps the browser's default ALPS, unlike the
    // cold WebSocket path, so the fingerprint matches a real navigation.
    let emulation = wreq_util::Emulation::builder()
        .profile(preset.profile())
        .platform(wreq_util::Platform::Linux)
        .build()
        .into_emulation();
    let client = wreq::Client::builder()
        .emulation(emulation)
        .resolve(target.server_name.clone(), target.addr)
        .connect_timeout(target.connect_timeout)
        .tls_cert_verification(!insecure)
        .build()
        .map_err(|e| TransportError::Tls(e.to_string()))?;

    let p = path.trim_start_matches('/');
    let url = format!("https://{}/{p}", target.server_name);
    let started = Instant::now();
    let resp = client
        .get(url)
        .send()
        .await
        .map_err(|e| TransportError::Tls(e.to_string()))?;
    let status = resp.status().as_u16();
    let body = resp
        .bytes()
        .await
        .map_err(|e| TransportError::Tls(e.to_string()))?;
    Ok(ControlResult {
        status,
        bytes: body.len() as u64,
        duration: started.elapsed(),
    })
}

async fn control_download_rustls(
    roots: RootCerts,
    target: &DialTarget,
    path: &str,
) -> Result<ControlResult, TransportError> {
    let mut config = match roots {
        RootCerts::System => rustls::ClientConfig::builder()
            .with_root_certificates(system_roots())
            .with_no_client_auth(),
        RootCerts::Insecure => rustls::ClientConfig::builder()
            .dangerous()
            .with_custom_certificate_verifier(Arc::new(LabInsecureVerifier))
            .with_no_client_auth(),
    };
    config.alpn_protocols = target.alpn.iter().map(|s| s.as_bytes().to_vec()).collect();

    let server_name = match target.sni {
        SniMode::Omit => rustls::pki_types::ServerName::IpAddress(target.addr.ip().into()),
        SniMode::ServerName => rustls::pki_types::ServerName::try_from(target.server_name.clone())
            .map_err(|e| TransportError::Tls(e.to_string()))?,
    };

    let connector = TlsConnector::from(Arc::new(config));
    let started = Instant::now();
    let tcp = tokio::time::timeout(target.connect_timeout, TcpStream::connect(target.addr))
        .await
        .map_err(|_| TransportError::Timeout)?
        .map_err(|e| TransportError::Io(e.to_string()))?;
    let mut tls = tokio::time::timeout(target.connect_timeout, connector.connect(server_name, tcp))
        .await
        .map_err(|_| TransportError::Timeout)?
        .map_err(|e| TransportError::Tls(e.to_string()))?;

    let p = if path.starts_with('/') {
        path.to_string()
    } else {
        format!("/{path}")
    };
    let request = format!(
        "GET {p} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: beep-control/1\r\n\
         Accept: */*\r\nConnection: close\r\n\r\n",
        host = target.server_name,
    );
    tls.write_all(request.as_bytes())
        .await
        .map_err(|e| TransportError::Io(e.to_string()))?;
    tls.flush()
        .await
        .map_err(|e| TransportError::Io(e.to_string()))?;

    // `Connection: close` means the server closes at the end of the body, so
    // reading to EOF yields the whole response.
    let mut raw = Vec::new();
    tls.read_to_end(&mut raw)
        .await
        .map_err(|e| TransportError::Io(e.to_string()))?;

    let (status, bytes) = parse_http_response(&raw)?;
    Ok(ControlResult {
        status,
        bytes,
        duration: started.elapsed(),
    })
}

/// Parse an HTTP/1.1 response buffer into `(status, body_len)`. Prefers the
/// `Content-Length` header when present, else counts the bytes after the
/// header terminator.
fn parse_http_response(raw: &[u8]) -> Result<(u16, u64), TransportError> {
    let header_end = raw
        .windows(4)
        .position(|w| w == b"\r\n\r\n")
        .ok_or_else(|| TransportError::Io("no HTTP header terminator in response".into()))?;
    let headers = &raw[..header_end];
    let head_text = String::from_utf8_lossy(headers);
    let mut lines = head_text.lines();

    let status_line = lines
        .next()
        .ok_or_else(|| TransportError::Io("empty HTTP response".into()))?;
    let status = status_line
        .split_whitespace()
        .nth(1)
        .and_then(|c| c.parse::<u16>().ok())
        .ok_or_else(|| TransportError::Io(format!("bad HTTP status line: {status_line}")))?;

    let content_length = lines.find_map(|line| {
        line.split_once(':').and_then(|(name, value)| {
            if name.trim().eq_ignore_ascii_case("content-length") {
                value.trim().parse::<u64>().ok()
            } else {
                None
            }
        })
    });

    let body_len = content_length.unwrap_or_else(|| (raw.len() - (header_end + 4)) as u64);
    Ok((status, body_len))
}

#[cfg(test)]
mod tests {
    use super::*;
    use beep_lab::RecordingProxy;
    use std::time::Duration;

    fn ws_target(addr: std::net::SocketAddr) -> DialTarget {
        DialTarget {
            addr,
            server_name: "localhost".into(),
            sni: SniMode::ServerName,
            http: HttpMode::WsH1,
            path: "/ws".into(),
            headers: Vec::new(),
            alpn: vec!["http/1.1".into()],
            connect_timeout: Duration::from_secs(3),
        }
    }

    /// The regression test for checkpoint 2's fingerprint requirement: the
    /// dialer's own ClientHello, captured off the wire by a passive listener
    /// that never completes the handshake, must be the same ClientHello a
    /// real Chromium 141 sends for the same request shape (`fixtures`), not
    /// just the same JA4.
    #[tokio::test]
    async fn chrome_dialer_hello_matches_real_chromium() {
        let proxy = RecordingProxy::start(None).await.unwrap();
        let dialer = ChromeDialer::insecure(ChromePreset::Chrome141);

        // The dialer will fail after this: the listener never speaks TLS
        // back. That is fine — the ClientHello is already on the wire.
        let _ = dialer.dial(&ws_target(proxy.addr())).await;

        let caps = proxy.wait_for_hellos(1, Duration::from_secs(3)).await;
        let hello = caps[0].hello.clone().expect("a ClientHello was captured");
        let reference = beep_lab::fixtures::chromium_ws(true).hello();
        let diffs = hello.differences_from(&reference);
        assert!(diffs.is_empty(), "{diffs:#?}");
    }

    #[tokio::test]
    async fn chrome_dialer_rejects_omitted_sni() {
        let dialer = ChromeDialer::new(ChromePreset::Chrome141);
        let mut target = ws_target("127.0.0.1:1".parse().unwrap());
        target.sni = SniMode::Omit;
        let err = dialer.dial(&target).await.unwrap_err();
        assert!(err.to_string().contains("sni_mode"), "{err}");
    }

    #[test]
    fn preset_parses_known_strings_only() {
        assert_eq!(
            ChromePreset::parse("chrome_141"),
            Some(ChromePreset::Chrome141)
        );
        assert_eq!(ChromePreset::parse("chrome_999"), None);
        assert_eq!(ChromePreset::parse("firefox_150"), None);
    }
}
