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

#[derive(Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Subscription {
    pub id: String,
    pub name: String,
    /// One-time compatibility input for pre-keyring stores. This field is
    /// intentionally never serialized: callers must migrate it to the OS
    /// secure store before returning or persisting the containing store.
    #[serde(default, rename = "url", skip_serializing)]
    pub(crate) legacy_url: Option<String>,
    pub auto_update: bool,
    pub last_updated: Option<u64>, // Unix timestamp
}

/// Browser-safe read model. Subscription URLs are bearer credentials and must
/// remain in native storage instead of being round-tripped through React.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct SubscriptionSummary {
    pub id: String,
    pub name: String,
    pub auto_update: bool,
    pub last_updated: Option<u64>,
}

impl From<&Subscription> for SubscriptionSummary {
    fn from(subscription: &Subscription) -> Self {
        Self {
            id: subscription.id.clone(),
            name: subscription.name.clone(),
            auto_update: subscription.auto_update,
            last_updated: subscription.last_updated,
        }
    }
}

/// Transient IPC create payload. The URL is accepted once and persisted only
/// by the native layer; it is never part of the subscription read model.
#[derive(Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CreateSubscription {
    pub id: String,
    pub name: String,
    pub url: String,
    pub auto_update: bool,
}

impl CreateSubscription {
    pub(crate) fn into_metadata_and_url(self) -> (Subscription, String) {
        let metadata = Subscription {
            id: self.id,
            name: self.name,
            legacy_url: None,
            auto_update: self.auto_update,
            last_updated: None,
        };
        (metadata, self.url)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProfileGroup {
    pub id: String,
    pub name: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
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
    /// Transport path from VLESS/XHTTP subscription metadata.
    pub transport_path: Option<String>,
    /// HTTP Host override used by XHTTP and other HTTP-based transports.
    pub transport_host: Option<String>,
    /// XHTTP upload mode (`auto`, `packet-up`, `stream-up`, or `stream-one`).
    pub xhttp_mode: Option<String>,
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
    pub congestion_control: Option<String>,         // TUIC
    pub udp_relay_mode: Option<String>,             // TUIC
    pub local_address: Option<Vec<String>>,         // Wireguard
    pub private_key: Option<String>,                // Wireguard / SSH
    pub peer_public_key: Option<String>,            // Wireguard
    pub mtu: Option<u32>,                           // Wireguard
    pub pre_shared_key: Option<String>,             // Wireguard
    pub reserved: Option<Vec<u8>>,                  // Wireguard
    pub allowed_ips: Option<Vec<String>>,           // Wireguard
    pub persistent_keepalive_interval: Option<u16>, // Wireguard
    pub listen_port: Option<u16>,                   // Wireguard
    pub tailscale_auth_key: Option<String>,
    pub tailscale_control_url: Option<String>,
    pub tailscale_state_directory: Option<String>,
    pub tailscale_hostname: Option<String>,
    pub tailscale_ephemeral: Option<bool>,
    pub tailscale_accept_routes: Option<bool>,
    pub tailscale_exit_node: Option<String>,
    pub tailscale_exit_node_allow_lan_access: Option<bool>,
    pub tailscale_advertise_routes: Option<Vec<String>>,
    pub tailscale_advertise_exit_node: Option<bool>,
    pub tailscale_system_interface: Option<bool>,
    pub tailscale_system_interface_name: Option<String>,
    pub tailscale_system_interface_mtu: Option<u32>,
    pub tailscale_udp_timeout: Option<String>,
    pub tailscale_relay_server_port: Option<u16>,
    pub tailscale_relay_server_static_endpoints: Option<Vec<String>>,
    pub mux: Option<String>,      // Multiplexing
    pub group_id: Option<String>, // Profile Grouping
    // Phase 19 Additions
    pub plugin: Option<String>, // Shadowsocks obfs/v2ray-plugin
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
        if self.protocol != "tailscale" && self.server.trim().is_empty() {
            return Err("Server cannot be empty".to_string());
        }
        if !self.server.trim().is_empty()
            && self.server.contains(|c: char| {
                c.is_whitespace() || c == ';' || c == '&' || c == '|' || c == '`' || c == '$'
            })
        {
            return Err("Server contains invalid or dangerous characters".to_string());
        }
        if self.protocol != "tailscale" && self.port == 0 {
            return Err("Port must be greater than 0".to_string());
        }
        if self.protocol == "wireguard" {
            if self
                .local_address
                .as_ref()
                .is_none_or(|addresses| addresses.is_empty())
            {
                return Err("WireGuard profile missing local address".to_string());
            }
            if self
                .private_key
                .as_ref()
                .is_none_or(|private_key| private_key.trim().is_empty())
            {
                return Err("WireGuard profile missing private key".to_string());
            }
            if self
                .peer_public_key
                .as_ref()
                .is_none_or(|public_key| public_key.trim().is_empty())
            {
                return Err("WireGuard profile missing peer public key".to_string());
            }
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
    #[serde(default)]
    pub active_core: Option<String>,
    #[serde(default)]
    pub proxy_url: Option<String>,
    pub message: Option<String>,
    pub up_bytes: u64,
    pub down_bytes: u64,
}

fn default_connection_active_core() -> String {
    "sing-box".to_string()
}

fn default_connection_source_surface() -> String {
    "unknown".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct LastConnectionOptions {
    pub profile_id: Option<String>,
    #[serde(default)]
    pub tun_mode: bool,
    #[serde(default)]
    pub system_proxy: bool,
    #[serde(default = "default_connection_active_core")]
    pub active_core: String,
    #[serde(default = "default_connection_source_surface")]
    pub source_surface: String,
    #[serde(default)]
    pub favorite_profile_ids: Vec<String>,
    #[serde(default)]
    pub last_stable_profile_id: Option<String>,
    #[serde(default)]
    pub last_stable_connected_at: Option<u64>,
    #[serde(default)]
    pub last_action: Option<String>,
    #[serde(default)]
    pub last_requested_at: Option<u64>,
    #[serde(default)]
    pub last_connected_at: Option<u64>,
    #[serde(default)]
    pub last_disconnected_at: Option<u64>,
}

impl Default for LastConnectionOptions {
    fn default() -> Self {
        Self {
            profile_id: None,
            tun_mode: false,
            system_proxy: false,
            active_core: default_connection_active_core(),
            source_surface: default_connection_source_surface(),
            favorite_profile_ids: Vec::new(),
            last_stable_profile_id: None,
            last_stable_connected_at: None,
            last_action: None,
            last_requested_at: None,
            last_connected_at: None,
            last_disconnected_at: None,
        }
    }
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn subscription_summary_serialization_never_contains_the_url() {
        let stored = Subscription {
            id: "sub-1".to_string(),
            name: "Primary".to_string(),
            legacy_url: Some("https://subscription.example/bearer-token".to_string()),
            auto_update: true,
            last_updated: Some(42),
        };

        let summary = serde_json::to_value(SubscriptionSummary::from(&stored))
            .expect("summary must serialize");
        let persisted_metadata = serde_json::to_value(&stored).expect("metadata must serialize");

        assert_eq!(summary["id"], "sub-1");
        assert_eq!(summary["name"], "Primary");
        assert!(summary.get("url").is_none());
        assert!(persisted_metadata.get("url").is_none());
        assert!(!summary.to_string().contains("bearer-token"));
        assert!(!persisted_metadata.to_string().contains("bearer-token"));
    }
}
