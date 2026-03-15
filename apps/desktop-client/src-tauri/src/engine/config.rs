use crate::ipc::models::{ProxyNode, RoutingRule};
use serde_json::{json, Value};

fn create_outbound(node: &ProxyNode, tag: &str, detour: Option<&str>) -> Value {
    let mut ob_map = serde_json::Map::new();
    ob_map.insert("type".to_string(), json!(node.protocol));
    ob_map.insert("tag".to_string(), json!(tag));
    ob_map.insert("server".to_string(), json!(node.server));
    ob_map.insert("server_port".to_string(), json!(node.port));

    match node.protocol.as_str() {
        "vless" => {
            if let Some(ref uuid) = node.uuid {
                ob_map.insert("uuid".to_string(), json!(uuid));
            }
            if let Some(ref flow) = node.flow {
                ob_map.insert("flow".to_string(), json!(flow));
            }
        }
        "vmess" => {
            if let Some(ref uuid) = node.uuid {
                ob_map.insert("uuid".to_string(), json!(uuid));
            }
            if let Some(alter_id) = node.alter_id {
                ob_map.insert("alter_id".to_string(), json!(alter_id));
            }
            if let Some(ref security) = node.security {
                ob_map.insert("security".to_string(), json!(security));
            }
        }
        "shadowsocks" => {
            if let Some(ref method) = node.method {
                ob_map.insert("method".to_string(), json!(method));
            }
            if let Some(ref password) = node.password {
                ob_map.insert("password".to_string(), json!(password));
            }
        }
        "trojan" => {
            if let Some(ref password) = node.password {
                ob_map.insert("password".to_string(), json!(password));
            }
        }
        "hysteria2" => {
            if let Some(ref password) = node.password {
                ob_map.insert("password".to_string(), json!(password));
            }
            if let Some(ref obfs) = node.obfs {
                let mut obfs_map = serde_json::Map::new();
                obfs_map.insert("type".to_string(), json!(obfs));
                if let Some(ref obfs_pw) = node.obfs_password {
                    obfs_map.insert("password".to_string(), json!(obfs_pw));
                }
                ob_map.insert("obfs".to_string(), json!(obfs_map));
            }
            if let Some(up) = node.up_mbps {
                ob_map.insert("up_mbps".to_string(), json!(up));
            }
            if let Some(down) = node.down_mbps {
                ob_map.insert("down_mbps".to_string(), json!(down));
            }
        }
        _ => {}
    }

    // Common TLS properties
    if node.tls.is_some() || node.protocol == "trojan" || node.protocol == "hysteria2" {
        let mut tls_map = serde_json::Map::new();
        tls_map.insert("enabled".to_string(), json!(true));
        
        if let Some(ref sni) = node.sni {
            tls_map.insert("server_name".to_string(), json!(sni));
        }

        if node.protocol == "hysteria2" {
            if let Some(ref alpn) = node.alpn {
                tls_map.insert("alpn".to_string(), json!(alpn));
            } 
        }

        // UTLS (Fingerprint)
        if node.protocol != "hysteria2" { 
            let mut utls_map = serde_json::Map::new();
            utls_map.insert("enabled".to_string(), json!(true));
            utls_map.insert("fingerprint".to_string(), json!(node.fingerprint.clone().unwrap_or("chrome".to_string())));
            tls_map.insert("utls".to_string(), json!(utls_map));
        }

        // Reality
        if node.tls.as_deref() == Some("reality") {
            let mut reality_map = serde_json::Map::new();
            reality_map.insert("enabled".to_string(), json!(true));
            if let Some(ref pk) = node.public_key {
                reality_map.insert("public_key".to_string(), json!(pk));
            }
            if let Some(ref sid) = node.short_id {
                reality_map.insert("short_id".to_string(), json!(sid));
            }
            tls_map.insert("reality".to_string(), json!(reality_map));
        }

        ob_map.insert("tls".to_string(), json!(tls_map));
    }

    if let Some(d) = detour {
        ob_map.insert("detour".to_string(), json!(d));
    }
    
    json!(ob_map)
}

/// Generates a valid sing-box JSON configuration for a given ProxyNode
///
/// # Examples
///
/// ```
/// use desktop_client_lib::ipc::models::{ProxyNode, RoutingRule};
/// use desktop_client_lib::engine::config::generate_singbox_config;
/// 
/// let node = ProxyNode {
///     id: "123".into(), name: "Test".into(), server: "1.1.1.1".into(), port: 443,
///     protocol: "vless".into(), uuid: Some("uuid".into()), password: None, flow: None,
///     network: None, tls: None, sni: None, fingerprint: None, public_key: None,
///     short_id: None, ping: None, next_hop_id: None, alter_id: None, security: None,
///     method: None, obfs: None, obfs_password: None, up_mbps: None, down_mbps: None,
///     alpn: None, subscription_id: None,
/// };
/// 
/// let config = generate_singbox_config(&node, &[], false, &[], None);
/// assert_eq!(config["outbounds"][0]["tag"], "proxy");
/// ```
pub fn generate_singbox_config(
    proxy: &ProxyNode, 
    all_nodes: &[ProxyNode], 
    tun_enabled: bool,
    user_rules: &[RoutingRule],
    log_path: Option<&std::path::Path>,
) -> Value {
    let mut outbounds = Vec::new();

    // 1. Determine multi-hop chain
    let mut detour_tag = None;
    if let Some(ref next_id) = proxy.next_hop_id {
        if let Some(next_node) = all_nodes.iter().find(|n| &n.id == next_id) {
            let next_tag = "proxy-next";
            detour_tag = Some(next_tag);
            outbounds.push(create_outbound(next_node, next_tag, None));
        } else {
            eprintln!("Warning: Next hop ID {} not found. Falling back to direct single-hop.", next_id);
        }
    }

    outbounds.push(create_outbound(proxy, "proxy", detour_tag));
    outbounds.push(json!({"type": "direct", "tag": "direct"}));
    outbounds.push(json!({"type": "block", "tag": "block"}));
    outbounds.push(json!({"type": "dns", "tag": "dns-out"}));

    // 2. Build Inbounds
    let mut inbounds = vec![
        json!({
            "type": "mixed",
            "tag": "mixed-in",
            "listen": "127.0.0.1",
            "listen_port": 2080,
            "sniff": true,
            "sniff_override_destination": true
        })
    ];

    if tun_enabled {
        inbounds.push(json!({
            "type": "tun",
            "tag": "tun-in",
            "interface_name": "tun0",
            "inet4_address": "172.19.0.1/30",
            "auto_route": true,
            "strict_route": true,
            "auto_redirect": true,
            "stack": "system",
            "sniff": true,
            "sniff_override_destination": true
        }));
    }

    // 3. Transform user RoutingRules into sing-box route rules using idiomatic Iterators
    let mut route_rules: Vec<Value> = user_rules.iter()
        .filter(|r| r.enabled)
        .map(|r| {
            let mut rule_obj = serde_json::Map::new();
            if !r.domains.is_empty() {
                rule_obj.insert("domain_suffix".into(), json!(r.domains));
            }
            if !r.ips.is_empty() {
                rule_obj.insert("ip_cidr".into(), json!(r.ips));
            }
            rule_obj.insert("outbound".into(), json!(r.outbound));
            json!(rule_obj)
        })
        .collect();

    // Core default rules to prevent leaks and loops
    route_rules.push(json!({"protocol": "dns", "outbound": "dns-out"}));
    route_rules.push(json!({"ip_is_private": true, "outbound": "direct"}));

    let mut log_obj = serde_json::Map::new();
    log_obj.insert("level".into(), json!("info"));
    log_obj.insert("timestamp".into(), json!(true));
    if let Some(path) = log_path {
        if let Some(path_str) = path.to_str() {
            log_obj.insert("output".into(), json!(path_str));
        }
    }

    // 4. Final configuration assembly
    json!({
        "log": log_obj,
        "dns": {
            "servers": [
                {
                    "tag": "dns-remote",
                    "address": "https://1.1.1.1/dns-query",
                    "address_resolver": "dns-local",
                    "strategy": "ipv4_only",
                    "detour": "proxy"
                },
                {
                    "tag": "dns-local",
                    "address": "1.1.1.1",
                    "detour": "direct"
                }
            ],
            "rules": [
                {
                    "outbound": "any",
                    "server": "dns-local"
                }
            ],
            "final": "dns-remote",
            "strategy": "ipv4_only"
        },
        "inbounds": inbounds,
        "outbounds": outbounds,
        "route": {
            "rules": route_rules,
            "final": "proxy",
            "auto_detect_interface": true
        }
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ipc::models::RoutingRule;

    fn create_mock_node(id: &str, next_hop: Option<&str>) -> ProxyNode {
        ProxyNode {
            id: id.to_string(),
            name: format!("Node {}", id),
            server: "1.2.3.4".to_string(),
            port: 443,
            protocol: "vless".to_string(),
            uuid: Some("test-uuid".to_string()),
            password: None,
            flow: None,
            network: None,
            tls: None,
            sni: None,
            fingerprint: None,
            public_key: None,
            short_id: None,
            ping: None,
            next_hop_id: next_hop.map(|s| s.to_string()),
            alter_id: None,
            security: None,
            method: None,
            obfs: None,
            obfs_password: None,
            up_mbps: None,
            down_mbps: None,
            alpn: None,
            subscription_id: None,
        }
    }

    #[test]
    fn generate_config_should_append_tun_inbounds() {
        let node = create_mock_node("1", None);
        let config = generate_singbox_config(&node, &[], true, &[], None);
        
        let inbounds = config.get("inbounds").unwrap().as_array().unwrap();
        assert_eq!(inbounds.len(), 2, "Expected 2 inbounds (mixed + tun)");
        
        let has_tun = inbounds.iter().any(|i| i.get("type").and_then(|v| v.as_str()) == Some("tun"));
        assert!(has_tun, "TUN inbound was not appended");
    }

    #[test]
    fn generate_config_with_routing_rules_should_map_correctly() {
        let node = create_mock_node("1", None);
        let rule1 = RoutingRule {
            id: "r1".into(),
            enabled: true,
            domains: vec!["*.openai.com".into()],
            ips: vec![],
            outbound: "proxy".into(),
        };
        let rule2 = RoutingRule {
            id: "r2".into(),
            enabled: false, // Disabled, should not appear
            domains: vec!["*.google.com".into()],
            ips: vec![],
            outbound: "direct".into(),
        };

        let config = generate_singbox_config(&node, &[], false, &[rule1, rule2], None);
        let rules = config["route"]["rules"].as_array().unwrap();
        
        // Custom rule should be first
        let first_rule = &rules[0];
        assert_eq!(first_rule["outbound"], "proxy");
        assert_eq!(first_rule["domain_suffix"][0], "*.openai.com");
        
        // Disabled rule should not be present
        let has_disabled = rules.iter().any(|r| r.get("domain_suffix")
            .and_then(|v| v.as_array())
            .is_some_and(|arr| arr.iter().any(|s| s == "*.google.com")));
        assert!(!has_disabled, "Disabled rule was included in config");
    }

    #[test]
    fn generate_config_with_next_hop_should_chain_detour_tag() {
        let node_a = create_mock_node("A", Some("B"));
        let node_b = create_mock_node("B", None);
        
        let config = generate_singbox_config(&node_a, &[node_a.clone(), node_b], false, &[], None);
        let outbounds = config["outbounds"].as_array().unwrap();
        
        // We should have proxy and proxy-next.
        let proxy_next_outbound = outbounds.iter().find(|o| o["tag"] == "proxy-next").expect("Missing proxy-next outbound");
        let proxy_outbound = outbounds.iter().find(|o| o["tag"] == "proxy").expect("Missing proxy outbound");
        
        // `proxy` must detour to `proxy-next`
        assert_eq!(proxy_outbound["detour"], "proxy-next");
        // `proxy-next` must have no detour
        assert!(proxy_next_outbound.get("detour").is_none());
    }
}
