use crate::ipc::models::{PqcAlgorithm, ProxyNode, RoutingRule};
use serde_json::{json, Value};

fn is_endpoint_protocol(protocol: &str) -> bool {
    matches!(protocol, "wireguard" | "tailscale")
}

fn apply_pqc_settings(
    tls_config: &mut serde_json::Map<String, Value>,
    node: &ProxyNode,
    pqc_enforcement_mode: bool,
) {
    let pqc_active = node.pqc_enabled.unwrap_or(false) || pqc_enforcement_mode;
    if pqc_active && node.protocol != "hysteria2" && node.protocol != "tuic" {
        // Apply hybrid post-quantum key exchange for TLS handshakes
        let algo = PqcAlgorithm::MlKem768x25519Plus;
        tls_config.insert("key_share".to_string(), json!(algo.as_str()));
    }
}

fn create_outbound(
    node: &ProxyNode,
    tag: &str,
    detour: Option<&str>,
    stealth_mode: bool,
    pqc_enforcement: bool,
) -> Value {
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

        let mut padding_map = serde_json::Map::new();
        padding_map.insert("enabled".to_string(), json!(true));
        padding_map.insert("size".to_string(), json!(format!("{}-{}", lower, upper)));
        ob_map.insert("padding".to_string(), Value::Object(padding_map));

        let mut multiplex_map = serde_json::Map::new();
        multiplex_map.insert("enabled".to_string(), json!(true));
        multiplex_map.insert("protocol".to_string(), json!("h2mux"));
        multiplex_map.insert("max_connections".to_string(), json!(4));
        multiplex_map.insert("min_streams".to_string(), json!(4));
        multiplex_map.insert("padding".to_string(), json!(true));
        ob_map.insert("multiplex".to_string(), Value::Object(multiplex_map));
        ob_map.insert("tcp_fast_open".to_string(), json!(true));

        let mut transport_map = serde_json::Map::new();
        transport_map.insert("type".to_string(), json!("xhttp"));
        transport_map.insert(
            "path".to_string(),
            json!(format!("/api/{}", rand::random::<u32>() % 9000 + 1000)),
        );
        ob_map.insert("transport".to_string(), Value::Object(transport_map));
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

fn create_endpoint(node: &ProxyNode, tag: &str, detour: Option<&str>) -> Value {
    let mut endpoint_map = serde_json::Map::new();
    endpoint_map.insert("type".to_string(), json!(node.protocol));
    endpoint_map.insert("tag".to_string(), json!(tag));

    match node.protocol.as_str() {
        "wireguard" => {
            if let Some(ref local_address) = node.local_address {
                endpoint_map.insert("address".to_string(), json!(local_address));
            }
            if let Some(ref private_key) = node.private_key {
                endpoint_map.insert("private_key".to_string(), json!(private_key));
            }
            if let Some(mtu) = node.mtu {
                endpoint_map.insert("mtu".to_string(), json!(mtu));
            }
            if let Some(listen_port) = node.listen_port {
                endpoint_map.insert("listen_port".to_string(), json!(listen_port));
            }
            if let Some(ref peer_public_key) = node.peer_public_key {
                let mut peer = serde_json::Map::new();
                peer.insert("address".to_string(), json!(node.server));
                peer.insert("port".to_string(), json!(node.port));
                peer.insert("public_key".to_string(), json!(peer_public_key));

                if let Some(ref pre_shared_key) = node.pre_shared_key {
                    peer.insert("pre_shared_key".to_string(), json!(pre_shared_key));
                }
                if let Some(ref allowed_ips) = node.allowed_ips {
                    peer.insert("allowed_ips".to_string(), json!(allowed_ips));
                } else {
                    peer.insert("allowed_ips".to_string(), json!(["0.0.0.0/0", "::/0"]));
                }
                if let Some(interval) = node.persistent_keepalive_interval {
                    peer.insert("persistent_keepalive_interval".to_string(), json!(interval));
                }
                if let Some(ref reserved) = node.reserved {
                    peer.insert("reserved".to_string(), json!(reserved));
                }

                endpoint_map.insert("peers".to_string(), json!([peer]));
            }
        }
        "tailscale" => {
            if let Some(ref auth_key) = node.tailscale_auth_key {
                endpoint_map.insert("auth_key".to_string(), json!(auth_key));
            }
            if let Some(ref control_url) = node.tailscale_control_url {
                endpoint_map.insert("control_url".to_string(), json!(control_url));
            }
            if let Some(ref state_directory) = node.tailscale_state_directory {
                endpoint_map.insert("state_directory".to_string(), json!(state_directory));
            }
            if let Some(ref hostname) = node.tailscale_hostname {
                endpoint_map.insert("hostname".to_string(), json!(hostname));
            }
            if let Some(ephemeral) = node.tailscale_ephemeral {
                endpoint_map.insert("ephemeral".to_string(), json!(ephemeral));
            }
            if let Some(accept_routes) = node.tailscale_accept_routes {
                endpoint_map.insert("accept_routes".to_string(), json!(accept_routes));
            }
            if let Some(ref exit_node) = node.tailscale_exit_node {
                endpoint_map.insert("exit_node".to_string(), json!(exit_node));
            }
            if let Some(allow_lan) = node.tailscale_exit_node_allow_lan_access {
                endpoint_map.insert("exit_node_allow_lan_access".to_string(), json!(allow_lan));
            }
            if let Some(ref advertise_routes) = node.tailscale_advertise_routes {
                endpoint_map.insert("advertise_routes".to_string(), json!(advertise_routes));
            }
            if let Some(advertise_exit_node) = node.tailscale_advertise_exit_node {
                endpoint_map.insert(
                    "advertise_exit_node".to_string(),
                    json!(advertise_exit_node),
                );
            }
            if let Some(system_interface) = node.tailscale_system_interface {
                endpoint_map.insert("system_interface".to_string(), json!(system_interface));
            }
            if let Some(ref interface_name) = node.tailscale_system_interface_name {
                endpoint_map.insert("system_interface_name".to_string(), json!(interface_name));
            }
            if let Some(interface_mtu) = node.tailscale_system_interface_mtu {
                endpoint_map.insert("system_interface_mtu".to_string(), json!(interface_mtu));
            }
            if let Some(ref udp_timeout) = node.tailscale_udp_timeout {
                endpoint_map.insert("udp_timeout".to_string(), json!(udp_timeout));
            }
            if let Some(relay_server_port) = node.tailscale_relay_server_port {
                endpoint_map.insert("relay_server_port".to_string(), json!(relay_server_port));
            }
            if let Some(ref static_endpoints) = node.tailscale_relay_server_static_endpoints {
                endpoint_map.insert(
                    "relay_server_static_endpoints".to_string(),
                    json!(static_endpoints),
                );
            }
        }
        _ => {}
    }

    if let Some(d) = detour {
        endpoint_map.insert("detour".to_string(), json!(d));
    }

    json!(endpoint_map)
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
///     id: "123".into(),
///     name: "Test".into(),
///     server: "1.1.1.1".into(),
///     port: 443,
///     protocol: "vless".into(),
///     uuid: Some("uuid".into()),
///     ..Default::default()
/// };
///
/// let config = generate_singbox_config(&node, &[], false, &[], None, None, false, &[], "disallow", false, false, "disabled", None);
/// assert_eq!(config["outbounds"][0]["tag"], "proxy");
/// ```
#[allow(clippy::too_many_arguments)]
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
    privacy_shield_level: &str,
    app_data_dir: Option<&std::path::Path>,
) -> Value {
    let mut outbounds = Vec::new();
    let mut endpoints = Vec::new();

    // 1. Determine multi-hop chain
    let mut detour_tag = None;
    if let Some(ref next_id) = proxy.next_hop_id {
        if let Some(next_node) = all_nodes.iter().find(|n| &n.id == next_id) {
            let next_tag = "proxy-next";
            detour_tag = Some(next_tag);
            if is_endpoint_protocol(next_node.protocol.as_str()) {
                endpoints.push(create_endpoint(next_node, next_tag, None));
            } else {
                outbounds.push(create_outbound(
                    next_node,
                    next_tag,
                    None,
                    stealth_mode_enabled,
                    pqc_enforcement_mode,
                ));
            }
        } else {
            eprintln!(
                "Warning: Next hop ID {} not found. Falling back to direct single-hop.",
                next_id
            );
        }
    }

    if is_endpoint_protocol(proxy.protocol.as_str()) {
        endpoints.push(create_endpoint(proxy, "proxy", detour_tag));
    } else {
        outbounds.push(create_outbound(
            proxy,
            "proxy",
            detour_tag,
            stealth_mode_enabled,
            pqc_enforcement_mode,
        ));
    }
    outbounds.push(json!({"type": "direct", "tag": "direct"}));

    // 2. Build Inbounds
    let port = local_socks_port.unwrap_or(2080);
    let listen_ip = if allow_lan { "0.0.0.0" } else { "127.0.0.1" };
    let mut inbounds = vec![json!({
        "type": "mixed",
        "tag": "mixed-in",
        "listen": listen_ip,
        "listen_port": port
    })];

    if tun_enabled {
        let mut tun_inbound = serde_json::Map::new();
        tun_inbound.insert("type".to_string(), json!("tun"));
        tun_inbound.insert("tag".to_string(), json!("tun-in"));
        tun_inbound.insert("address".to_string(), json!(["172.19.0.1/30"]));
        tun_inbound.insert("auto_route".to_string(), json!(true));
        tun_inbound.insert("strict_route".to_string(), json!(true));
        tun_inbound.insert("stack".to_string(), json!("system"));

        #[cfg(target_os = "linux")]
        {
            tun_inbound.insert("interface_name".to_string(), json!("tun0"));
            tun_inbound.insert("auto_redirect".to_string(), json!(true));
        }

        inbounds.push(Value::Object(tun_inbound));
    }

    // 3. Transform user RoutingRules into sing-box route rules using idiomatic Iterators
    let mut route_rules: Vec<Value> = Vec::new();

    route_rules.push(json!({
        "action": "sniff",
        "timeout": "300ms"
    }));
    route_rules.push(json!({
        "protocol": "dns",
        "action": "hijack-dns"
    }));

    // 3a. Inject Privacy Shield rule FIRST
    if privacy_shield_level != "disabled" && app_data_dir.is_some() {
        route_rules.push(json!({
            "rule_set": "adblock-standard",
            "action": "reject"
        }));
    }

    // 3b. Inject Split Tunneling rules
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
    let mut route_obj = serde_json::Map::new();
    route_obj.insert("rules".to_string(), Value::Array(route_rules));
    route_obj.insert(
        "final".to_string(),
        json!(if split_mode == "allow" && !split_apps.is_empty() {
            "direct"
        } else {
            "proxy"
        }),
    );
    route_obj.insert("default_domain_resolver".to_string(), json!("dns-local"));
    route_obj.insert("auto_detect_interface".to_string(), json!(true));

    if privacy_shield_level != "disabled" {
        if let Some(dir) = app_data_dir {
            let rs_path = dir.join("bin").join("adblock-standard.json");
            route_obj.insert(
                "rule_set".to_string(),
                json!([
                    {
                        "tag": "adblock-standard",
                        "type": "local",
                        "format": "source",
                        "path": rs_path.to_string_lossy()
                    }
                ]),
            );
        }
    }

    json!({
        "log": log_obj,
        "dns": {
            "servers": [
                {
                    "type": "https",
                    "tag": "dns-remote",
                    "server": "1.1.1.1",
                    "server_port": 443,
                    "path": "/dns-query",
                    "detour": "proxy"
                },
                {
                    "type": "udp",
                    "tag": "dns-local",
                    "server": "1.1.1.1",
                    "server_port": 53
                }
            ],
            "final": "dns-remote",
            "strategy": "ipv4_only"
        },
        "inbounds": inbounds,
        "endpoints": endpoints,
        "outbounds": outbounds,
        "route": route_obj
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
            ..Default::default()
        }
    }

    #[test]
    fn generate_config_should_append_tun_inbounds() {
        let node = create_mock_node("1", None);
        let config = generate_singbox_config(
            &node,
            &[],
            true,
            &[],
            None,
            None,
            false,
            &[],
            "allow",
            false,
            false,
            "disabled",
            None,
        );

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

        let config = generate_singbox_config(
            &node,
            &[],
            false,
            &[rule1, rule2],
            None,
            None,
            false,
            &[],
            "allow",
            false,
            false,
            "disabled",
            None,
        );
        let rules = config["route"]["rules"].as_array().unwrap();

        let custom_rule = rules
            .iter()
            .find(|rule| rule["domain_suffix"][0] == "*.openai.com")
            .expect("Custom routing rule was not included");
        assert_eq!(custom_rule["outbound"], "proxy");

        // Disabled rule should not be present
        let has_disabled = rules.iter().any(|r| {
            r.get("domain_suffix")
                .and_then(|v| v.as_array())
                .is_some_and(|arr| arr.iter().any(|s| s == "*.google.com"))
        });
        assert!(!has_disabled, "Disabled rule was included in config");
    }

    #[test]
    fn generate_config_should_use_non_legacy_direct_dns_resolver() {
        let node = create_mock_node("1", None);

        let config = generate_singbox_config(
            &node,
            &[],
            true,
            &[],
            None,
            None,
            false,
            &[],
            "allow",
            false,
            false,
            "disabled",
            None,
        );

        let dns_servers = config["dns"]["servers"]
            .as_array()
            .expect("dns.servers should be an array");
        let dns_local = dns_servers
            .iter()
            .find(|server| server["tag"] == "dns-local")
            .expect("dns-local server missing");

        assert_eq!(dns_local["type"], "udp");
        assert_eq!(dns_local["server"], "1.1.1.1");
        assert!(dns_local.get("detour").is_none());
        assert_eq!(config["route"]["default_domain_resolver"], "dns-local");
    }

    #[test]
    fn generate_config_with_next_hop_should_chain_detour_tag() {
        let node_a = create_mock_node("A", Some("B"));
        let node_b = create_mock_node("B", None);

        let config = generate_singbox_config(
            &node_a,
            &[node_a.clone(), node_b],
            false,
            &[],
            None,
            None,
            false,
            &[],
            "allow",
            false,
            false,
            "disabled",
            None,
        );
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

    #[test]
    fn generate_config_with_wireguard_profile_should_use_endpoint() {
        let node = ProxyNode {
            protocol: "wireguard".to_string(),
            server: "162.159.193.10".to_string(),
            port: 2408,
            private_key: Some("private".to_string()),
            peer_public_key: Some("peer".to_string()),
            local_address: Some(vec!["10.0.0.2/32".to_string()]),
            ..create_mock_node("wg", None)
        };

        let config = generate_singbox_config(
            &node,
            &[],
            false,
            &[],
            None,
            None,
            false,
            &[],
            "allow",
            false,
            false,
            "disabled",
            None,
        );

        let endpoints = config["endpoints"].as_array().unwrap();
        let proxy_endpoint = endpoints
            .iter()
            .find(|endpoint| endpoint["tag"] == "proxy")
            .expect("Missing WireGuard endpoint");

        assert_eq!(proxy_endpoint["type"], "wireguard");
        assert_eq!(proxy_endpoint["peers"][0]["allowed_ips"][0], "0.0.0.0/0");
        assert_eq!(config["route"]["final"], "proxy");
    }

    #[test]
    fn generate_config_with_tailscale_profile_should_use_endpoint() {
        let node = ProxyNode {
            protocol: "tailscale".to_string(),
            server: String::new(),
            port: 0,
            tailscale_state_directory: Some("tailscale-state".to_string()),
            tailscale_accept_routes: Some(true),
            ..create_mock_node("ts", None)
        };

        let config = generate_singbox_config(
            &node,
            &[],
            false,
            &[],
            None,
            None,
            false,
            &[],
            "allow",
            false,
            false,
            "disabled",
            None,
        );

        let endpoints = config["endpoints"].as_array().unwrap();
        let proxy_endpoint = endpoints
            .iter()
            .find(|endpoint| endpoint["tag"] == "proxy")
            .expect("Missing Tailscale endpoint");

        assert_eq!(proxy_endpoint["type"], "tailscale");
        assert_eq!(proxy_endpoint["state_directory"], "tailscale-state");
        assert_eq!(proxy_endpoint["accept_routes"], true);
    }
}
