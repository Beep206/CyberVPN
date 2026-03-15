use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProxyNode {
    pub id: String,
    pub name: String,
    pub server: String,
    pub port: u16,
    pub protocol: String,      // vless, trojan, ss, etc.
    pub uuid: Option<String>,
    pub password: Option<String>,
    pub flow: Option<String>,
    pub network: Option<String>,
    pub tls: Option<String>,   // tls, reality
    pub sni: Option<String>,
    pub fingerprint: Option<String>,
    pub public_key: Option<String>,
    pub short_id: Option<String>,
    pub ping: Option<u32>,     // Latest ping in ms
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
    pub status: String,    // "disconnected", "connecting", "connected", "error"
    pub active_id: Option<String>,
    pub message: Option<String>,
    pub up_bytes: u64,
    pub down_bytes: u64,
}
