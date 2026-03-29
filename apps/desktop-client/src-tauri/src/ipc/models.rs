use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub enum PqcAlgorithm {
    MlKem768x25519Plus,
    // Future algorithms can go here, e.g., MlKem1024x448Plus
}

// Fallback to serialization as a string for sing-box standard injection
impl PqcAlgorithm {
    pub fn as_str(&self) -> &'static str {
        match self {
            PqcAlgorithm::MlKem768x25519Plus => "mlkem768x25519plus",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Subscription {
    pub id: String,
    pub name: String,
    pub url: String,
    pub auto_update: bool,
    pub last_updated: Option<u64>, // Unix timestamp
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProfileGroup {
    pub id: String,
    pub name: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProxyNode {
    pub id: String,
    pub name: String,
    pub server: String,
    pub port: u16,
    pub protocol: String, // vless, trojan, ss, etc.
    pub uuid: Option<String>,
    pub password: Option<String>,
    pub flow: Option<String>,
    pub network: Option<String>,
    pub tls: Option<String>, // tls, reality
    pub sni: Option<String>,
    pub fingerprint: Option<String>,
    pub public_key: Option<String>,
    pub short_id: Option<String>,
    pub ping: Option<u32>,           // Latest ping in ms
    pub next_hop_id: Option<String>, // Multi-hop routing
    // Protocol-specific expanded fields
    pub alter_id: Option<u16>,           // VMess
    pub security: Option<String>,        // VMess / general TLS
    pub method: Option<String>,          // Shadowsocks
    pub obfs: Option<String>,            // Hysteria2 / Shadowsocks
    pub obfs_password: Option<String>,   // Hysteria2
    pub up_mbps: Option<u32>,            // Hysteria2
    pub down_mbps: Option<u32>,          // Hysteria2
    pub alpn: Option<Vec<String>>,       // Hysteria2 / TLS
    pub subscription_id: Option<String>, // Phase 11 Subscription sync
    // Phase 15 Additions
    pub congestion_control: Option<String>, // TUIC
    pub udp_relay_mode: Option<String>,     // TUIC
    pub local_address: Option<Vec<String>>, // Wireguard
    pub private_key: Option<String>,        // Wireguard / SSH
    pub peer_public_key: Option<String>,    // Wireguard
    pub mtu: Option<u32>,                   // Wireguard
    pub mux: Option<String>,                // Multiplexing
    pub group_id: Option<String>,           // Profile Grouping
    // Phase 19 Additions
    pub plugin: Option<String>,             // Shadowsocks obfs/v2ray-plugin
    pub plugin_opts: Option<String>,
    pub tls_fragment: Option<bool>,
    pub tls_record_fragment: Option<bool>,
    // Phase 26
    pub pqc_enabled: Option<bool>,
}

impl ProxyNode {
    pub fn validate(&self) -> Result<(), String> {
        if self.name.trim().is_empty() {
            return Err("Name cannot be empty".to_string());
        }
        if self.server.trim().is_empty() {
            return Err("Server cannot be empty".to_string());
        }
        if self.server.contains(|c: char| {
            c.is_whitespace() || c == ';' || c == '&' || c == '|' || c == '`' || c == '$'
        }) {
            return Err("Server contains invalid or dangerous characters".to_string());
        }
        if self.port == 0 {
            return Err("Port must be greater than 0".to_string());
        }
        if let Some(ref method) = self.method {
            if method.trim().is_empty() {
                return Err("Method (cipher) cannot be empty if provided".to_string());
            }
        }
        if let Some(ref sec) = self.security {
            if sec.trim().is_empty() {
                return Err("Security cannot be empty if provided".to_string());
            }
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RoutingRule {
    pub id: String,
    pub enabled: bool,
    pub domains: Vec<String>, // e.g., ["*.openai.com", "geosite:google"]
    pub ips: Vec<String>,     // e.g., ["geoip:telegram", "192.168.1.0/24"]
    pub outbound: String,     // e.g., "proxy", "direct", "block"
    // Phase 19 Advanced Routing
    #[serde(default)]
    pub process_name: Vec<String>,
    #[serde(default)]
    pub port_range: Vec<String>,
    #[serde(default)]
    pub network: Option<String>,
    #[serde(default)]
    pub domain_keyword: Vec<String>,
    #[serde(default)]
    pub domain_regex: Vec<String>,
}

impl RoutingRule {
    pub fn validate(&self) -> Result<(), String> {
        if self.outbound.trim().is_empty() {
            return Err("Outbound target cannot be empty".to_string());
        }
        if self.outbound.contains(|c: char| {
            c.is_whitespace() || c == ';' || c == '&' || c == '|' || c == '`' || c == '$'
        }) {
            return Err("Outbound target contains invalid or dangerous characters".to_string());
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProfileState {
    pub active_profile_id: Option<String>,
    pub profiles: Vec<ProxyNode>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ConnectionStatus {
    pub status: String, // "disconnected", "connecting", "connected", "error"
    pub active_id: Option<String>,
    pub message: Option<String>,
    pub up_bytes: u64,
    pub down_bytes: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AppInfo {
    pub name: String,
    pub package_name: String,
    pub icon_base64: Option<String>,
    pub exec_path: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AuditResult {
    pub id: String,
    pub name: String,
    pub protocol: String,
    pub status: String,
}
