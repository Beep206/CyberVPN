use crate::engine::error::AppError;
use crate::ipc::models::ProxyNode;
use base64::prelude::*;
use std::time::Duration;

pub async fn fetch_and_parse_subscription(url: &str) -> Result<Vec<ProxyNode>, AppError> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .build()
        .map_err(|e| AppError::System(format!("Failed to build HTTP client: {}", e)))?;

    let response = client
        .get(url)
        .send()
        .await
        .map_err(|e| AppError::System(format!("Failed to fetch subscription: {}", e)))?;

    if !response.status().is_success() {
        return Err(AppError::System(format!(
            "Subscription fetch failed with status: {}",
            response.status()
        )));
    }

    let body = response
        .text()
        .await
        .map_err(|e| AppError::System(format!("Failed to read subscription body: {}", e)))?;

    // Attempt Clash YAML parsing first
    if let Ok(yaml_val) = serde_yaml::from_str::<serde_yaml::Value>(&body) {
        if let Some(proxies) = yaml_val.get("proxies").and_then(|p| p.as_sequence()) {
            let mut yaml_nodes = Vec::new();
            for proxy in proxies {
                let name = proxy
                    .get("name")
                    .and_then(|v| v.as_str())
                    .unwrap_or("Imported Clash Node")
                    .to_string();
                let server = proxy
                    .get("server")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string();
                let port = proxy.get("port").and_then(|v| v.as_u64()).unwrap_or(443) as u16;
                let protocol = proxy
                    .get("type")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string();

                if server.is_empty() || protocol.is_empty() {
                    continue;
                }

                // Map supported types safely
                match protocol.as_str() {
                    "vless" | "vmess" | "trojan" | "ss" | "shadowsocks" => {
                        let password = proxy
                            .get("password")
                            .and_then(|v| v.as_str())
                            .map(|s| s.to_string());
                        let uuid = proxy
                            .get("uuid")
                            .and_then(|v| v.as_str())
                            .map(|s| s.to_string());
                        let sni = proxy
                            .get("sni")
                            .and_then(|v| v.as_str())
                            .map(|s| s.to_string());
                        let tls = proxy.get("tls").and_then(|v| v.as_bool()).map(|b| {
                            if b {
                                "tls".to_string()
                            } else {
                                "none".to_string()
                            }
                        });
                        let method = proxy
                            .get("cipher")
                            .and_then(|v| v.as_str())
                            .map(|s| s.to_string());
                        let alter_id = proxy
                            .get("alterId")
                            .and_then(|v| v.as_u64())
                            .map(|u| u as u16);
                        let network = proxy
                            .get("network")
                            .and_then(|v| v.as_str())
                            .map(|s| s.to_string());

                        let proto_mapped = if protocol == "ss" {
                            "shadowsocks".to_string()
                        } else {
                            protocol.clone()
                        };

                        yaml_nodes.push(ProxyNode {
                            id: uuid::Uuid::new_v4().to_string(),
                            name,
                            server,
                            port,
                            protocol: proto_mapped,
                            uuid,
                            password,
                            network,
                            flow: None,
                            tls,
                            sni,
                            fingerprint: None,
                            public_key: None,
                            short_id: None,
                            ping: None,
                            next_hop_id: None,
                            alter_id,
                            security: None,
                            method,
                            obfs: None,
                            obfs_password: None,
                            up_mbps: None,
                            down_mbps: None,
                            alpn: None,
                            subscription_id: None,
                            congestion_control: None,
                            udp_relay_mode: None,
                            local_address: None,
                            private_key: None,
                            peer_public_key: None,
                            mtu: None,
                            mux: None,
                            group_id: None,
                            plugin: None,
                            plugin_opts: None,
                            tls_fragment: None,
                            tls_record_fragment: None,
                        });
                    }
                    _ => continue,
                }
            }
            if !yaml_nodes.is_empty() {
                return Ok(yaml_nodes);
            }
        }
    }

    // Try decoding as Base64, fallback to treating it as raw text if all decodes fail
    let decoded_body = match BASE64_URL_SAFE_NO_PAD
        .decode(body.trim())
        .or_else(|_| BASE64_URL_SAFE.decode(body.trim()))
        .or_else(|_| BASE64_STANDARD_NO_PAD.decode(body.trim()))
        .or_else(|_| BASE64_STANDARD.decode(body.trim()))
    {
        Ok(bytes) => String::from_utf8_lossy(&bytes).to_string(),
        Err(_) => body, // Fallback to raw plaintext if not base64
    };

    let nodes: Vec<ProxyNode> = decoded_body
        .lines()
        .map(|line| line.trim())
        .filter(|line| !line.is_empty())
        .filter_map(|line| crate::engine::parser::parse_link(line).ok())
        .collect();

    Ok(nodes)
}
