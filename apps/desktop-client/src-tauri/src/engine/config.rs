use crate::ipc::models::{ProxyNode, RoutingRule, PqcAlgorithm};
use serde::Serialize;
use serde_json::{json, Value};

#[derive(Serialize)]
struct StealthPaddingConfig {
    enabled: bool,
    size: String,
}

#[derive(Serialize)]
struct StealthMultiplexConfig {
    enabled: bool,
    protocol: String,
    max_connections: u32,
    min_streams: u32,
    padding: bool,
}

#[derive(Serialize)]
struct StealthXhttpConfig {
    #[serde(rename = "type")]
    transport_type: String,
    path: String,
}

fn apply_pqc_settings(tls_config: &mut serde_json::Map<String, Value>, node: &ProxyNode, pqc_enforcement_mode: bool) {
    let pqc_active = node.pqc_enabled.unwrap_or(false) || pqc_enforcement_mode;
    if pqc_active && node.protocol != "hysteria2" && node.protocol != "tuic" {
        // Apply hybrid post-quantum key exchange for TLS handshakes
        let algo = PqcAlgorithm::MlKem768x25519Plus;
        tls_config.insert("key_share".to_string(), json!(algo.as_str()));
    }
}

fn create_outbound(node: &ProxyNode, tag: &str, detour: Option<&str>, stealth_mode: bool, pqc_enforcement: bool) -> Value {
    let mut ob_map = serde_json::Map::new();
    ob_map.insert("type".to_string(), json!(node.protocol));
    ob_map.insert("tag".to_string(), json!(tag));
    ob_map.insert("server".to_string(), json!(node.server));
    ob_map.insert("server_port".to_string(), json!(node.port));

    match node.protocol.as_str() {
        "tailscale" => {
            // Tailscale outbounds do not use server/server_port in standard sing-box config
            ob_map.remove("server");
            ob_map.remove("server_port");
        }
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
            if let Some(ref plugin) = node.plugin {
                ob_map.insert("plugin".to_string(), json!(plugin));
                if let Some(ref plugin_opts) = node.plugin_opts {
                    ob_map.insert("plugin_opts".to_string(), json!(plugin_opts));
                }
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
        "tuic" => {
            if let Some(ref uuid) = node.uuid {
                ob_map.insert("uuid".to_string(), json!(uuid));
            }
            if let Some(ref password) = node.password {
                ob_map.insert("password".to_string(), json!(password));
            }
            if let Some(ref cc) = node.congestion_control {
                ob_map.insert("congestion_control".to_string(), json!(cc));
            }
            if let Some(ref udp) = node.udp_relay_mode {
                ob_map.insert("udp_relay_mode".to_string(), json!(udp));
            }
        }
        "wireguard" => {
            // Sing-box wireguard expects endpoint fields within peers, so remove them from the top level
            ob_map.remove("server");
            ob_map.remove("server_port");

            if let Some(ref local_address) = node.local_address {
                ob_map.insert("local_address".to_string(), json!(local_address));
            }
            if let Some(ref private_key) = node.private_key {
                ob_map.insert("private_key".to_string(), json!(private_key));
            }
            if let Some(mtu) = node.mtu {
                ob_map.insert("mtu".to_string(), json!(mtu));
            }
            if let Some(ref peer_pk) = node.peer_public_key {
                ob_map.insert(
                    "peers".to_string(),
                    json!([{
                        "server": node.server,
                        "server_port": node.port,
                        "public_key": peer_pk
                    }]),
                );
            }
        }
        "socks" | "http" | "ssh" => {
            if let Some(ref username) = node.uuid {
                // Username is stored in uuid
                ob_map.insert("username".to_string(), json!(username));
            }
            if let Some(ref password) = node.password {
                ob_map.insert("password".to_string(), json!(password));
            }
            if node.protocol == "ssh" {
                if let Some(ref pk) = node.private_key {
                    ob_map.insert("private_key".to_string(), json!(pk));
                }
            }
        }
        _ => {}
    }

    // Common TLS properties
    if node.tls.is_some()
        || node.protocol == "trojan"
        || node.protocol == "hysteria2"
        || node.protocol == "tuic"
    {
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
        if node.protocol != "hysteria2" && node.protocol != "tuic" {
            let mut utls_map = serde_json::Map::new();
            utls_map.insert("enabled".to_string(), json!(true));
            utls_map.insert(
                "fingerprint".to_string(),
                json!(node.fingerprint.clone().unwrap_or("chrome".to_string())),
            );
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

        // Fragment
        if node.tls_fragment == Some(true) {
            let mut fragment_map = serde_json::Map::new();
            fragment_map.insert("enabled".to_string(), json!(true));
            fragment_map.insert("size".to_string(), json!("10-50"));
            fragment_map.insert("sleep".to_string(), json!("10-20"));
            tls_map.insert("fragment".to_string(), json!(fragment_map));
        }

        apply_pqc_settings(&mut tls_map, node, pqc_enforcement);

        ob_map.insert("tls".to_string(), json!(tls_map));
    }

    if let Some(d) = detour {
        ob_map.insert("detour".to_string(), json!(d));
    }

    if stealth_mode && (node.protocol == "vless" || node.tls.as_deref() == Some("reality")) {
        let lower: u32 = rand::random::<u32>() % 100 + 50; // 50-149
        let upper: u32 = rand::random::<u32>() % 300 + 300; // 300-599
        
        ob_map.insert("packet_encoding".to_string(), json!("xudp"));

        let padding = StealthPaddingConfig {
            enabled: true,
            size: format!("{}-{}", lower, upper),
        };
        ob_map.insert("padding".to_string(), serde_json::to_value(&padding).unwrap());

        let mx = StealthMultiplexConfig {
            enabled: true,
            protocol: "h2mux".to_string(),
            max_connections: 4,
            min_streams: 4,
            padding: true,
        };
        ob_map.insert("multiplex".to_string(), serde_json::to_value(&mx).unwrap());
        ob_map.insert("tcp_fast_open".to_string(), json!(true));

        let xhttp = StealthXhttpConfig {
            transport_type: "xhttp".to_string(),
            path: format!("/api/{}", rand::random::<u32>() % 9000 + 1000),
        };
        ob_map.insert("transport".to_string(), serde_json::to_value(&xhttp).unwrap());
    } else if let Some(ref m) = node.mux {
        if m != "none" {
            let mut mux_map = serde_json::Map::new();
            mux_map.insert("enabled".to_string(), json!(true));
            mux_map.insert("protocol".to_string(), json!(m));
            ob_map.insert("multiplex".to_string(), json!(mux_map));
        }
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
///     alpn: None, subscription_id: None, congestion_control: None,
///     udp_relay_mode: None, local_address: None, private_key: None,
///     peer_public_key: None, mtu: None, mux: None, group_id: None,
///     plugin: None, plugin_opts: None, tls_fragment: None, tls_record_fragment: None,
/// };
///
/// let config = generate_singbox_config(&node, &[], false, &[], None, None, false, &[], "disallow", false, false);
/// assert_eq!(config["outbounds"][0]["tag"], "proxy");
/// ```
pub fn generate_singbox_config(
    proxy: &ProxyNode,
    all_nodes: &[ProxyNode],
    tun_enabled: bool,
    user_rules: &[RoutingRule],
    log_path: Option<&std::path::Path>,
    local_socks_port: Option<u16>,
    allow_lan: bool,
    split_apps: &[String],
    split_mode: &str,
    stealth_mode_enabled: bool,
    pqc_enforcement_mode: bool,
) -> Value {
    let mut outbounds = Vec::new();

    // 1. Determine multi-hop chain
    let mut detour_tag = None;
    if let Some(ref next_id) = proxy.next_hop_id {
        if let Some(next_node) = all_nodes.iter().find(|n| &n.id == next_id) {
            let next_tag = "proxy-next";
            detour_tag = Some(next_tag);
            outbounds.push(create_outbound(next_node, next_tag, None, stealth_mode_enabled, pqc_enforcement_mode));
        } else {
            eprintln!(
                "Warning: Next hop ID {} not found. Falling back to direct single-hop.",
                next_id
            );
        }
    }

    outbounds.push(create_outbound(proxy, "proxy", detour_tag, stealth_mode_enabled, pqc_enforcement_mode));
    outbounds.push(json!({"type": "direct", "tag": "direct"}));
    outbounds.push(json!({"type": "block", "tag": "block"}));
    outbounds.push(json!({"type": "dns", "tag": "dns-out"}));

    // 2. Build Inbounds
    let port = local_socks_port.unwrap_or(2080);
    let listen_ip = if allow_lan { "0.0.0.0" } else { "127.0.0.1" };
    let mut inbounds = vec![json!({
        "type": "mixed",
        "tag": "mixed-in",
        "listen": listen_ip,
        "listen_port": port,
        "sniff": true,
        "sniff_override_destination": true
    })];

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
    let mut route_rules: Vec<Value> = Vec::new();

    // 3a. Inject Split Tunneling rules FIRST
    if !split_apps.is_empty() {
        if split_mode == "allow" {
            route_rules.push(json!({
                "process_name": split_apps,
                "outbound": "proxy"
            }));
        } else if split_mode == "disallow" {
            route_rules.push(json!({
                "process_name": split_apps,
                "outbound": "direct"
            }));
        }
    }

    let mut user_mapped_rules: Vec<Value> = user_rules
        .iter()
        .filter(|r| r.enabled)
        .map(|r| {
            let mut rule_obj = serde_json::Map::new();
            if !r.domains.is_empty() {
                rule_obj.insert("domain_suffix".into(), json!(r.domains));
            }
            if !r.ips.is_empty() {
                rule_obj.insert("ip_cidr".into(), json!(r.ips));
            }
            if !r.process_name.is_empty() {
                rule_obj.insert("process_name".into(), json!(r.process_name));
            }
            if !r.port_range.is_empty() {
                rule_obj.insert("port".into(), json!(r.port_range));
            }
            if let Some(ref network) = r.network {
                if !network.trim().is_empty() {
                    rule_obj.insert("network".into(), json!(network));
                }
            }
            if !r.domain_keyword.is_empty() {
                rule_obj.insert("domain_keyword".into(), json!(r.domain_keyword));
            }
            if !r.domain_regex.is_empty() {
                rule_obj.insert("domain_regex".into(), json!(r.domain_regex));
            }
            rule_obj.insert("outbound".into(), json!(r.outbound));
            json!(rule_obj)
        })
        .collect();

    route_rules.append(&mut user_mapped_rules);

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
            "final": if split_mode == "allow" && !split_apps.is_empty() { "direct" } else { "proxy" },
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
            pqc_enabled: None,
        }
    }

    #[test]
    fn generate_config_should_append_tun_inbounds() {
        let node = create_mock_node("1", None);
        let config = generate_singbox_config(&node, &[], true, &[], None, None, false, &[], "allow", false, false);

        let inbounds = config.get("inbounds").unwrap().as_array().unwrap();
        assert_eq!(inbounds.len(), 2, "Expected 2 inbounds (mixed + tun)");

        let has_tun = inbounds
            .iter()
            .any(|i| i.get("type").and_then(|v| v.as_str()) == Some("tun"));
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
            process_name: vec![],
            port_range: vec![],
            network: None,
            domain_keyword: vec![],
            domain_regex: vec![],
        };
        let rule2 = RoutingRule {
            id: "r2".into(),
            enabled: false, // Disabled, should not appear
            domains: vec!["*.google.com".into()],
            ips: vec![],
            outbound: "direct".into(),
            process_name: vec![],
            port_range: vec![],
            network: None,
            domain_keyword: vec![],
            domain_regex: vec![],
        };

        let config = generate_singbox_config(&node, &[], false, &[rule1, rule2], None, None, false, &[], "allow", false, false);
        let rules = config["route"]["rules"].as_array().unwrap();

        // Custom rule should be first
        let first_rule = &rules[0];
        assert_eq!(first_rule["outbound"], "proxy");
        assert_eq!(first_rule["domain_suffix"][0], "*.openai.com");

        // Disabled rule should not be present
        let has_disabled = rules.iter().any(|r| {
            r.get("domain_suffix")
                .and_then(|v| v.as_array())
                .is_some_and(|arr| arr.iter().any(|s| s == "*.google.com"))
        });
        assert!(!has_disabled, "Disabled rule was included in config");
    }

    #[test]
    fn generate_config_with_next_hop_should_chain_detour_tag() {
        let node_a = create_mock_node("A", Some("B"));
        let node_b = create_mock_node("B", None);

        let config = generate_singbox_config(&node_a, &[node_a.clone(), node_b], false, &[], None, None, false, &[], "allow", false, false);
        let outbounds = config["outbounds"].as_array().unwrap();

        // We should have proxy and proxy-next.
        let proxy_next_outbound = outbounds
            .iter()
            .find(|o| o["tag"] == "proxy-next")
            .expect("Missing proxy-next outbound");
        let proxy_outbound = outbounds
            .iter()
            .find(|o| o["tag"] == "proxy")
            .expect("Missing proxy outbound");

        // `proxy` must detour to `proxy-next`
        assert_eq!(proxy_outbound["detour"], "proxy-next");
        // `proxy-next` must have no detour
        assert!(proxy_next_outbound.get("detour").is_none());
    }
}
