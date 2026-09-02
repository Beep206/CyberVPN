use crate::engine::error::AppError;
use crate::engine::parser::{classify_vless_transport, VlessTransportKind};
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
            if matches!(
                classify_vless_transport(node.network.as_deref()),
                Ok(VlessTransportKind::Raw)
            ) {
                if let Some(ref flow) = node.flow {
                    if !flow.is_empty() {
                        ob_map.insert("flow".to_string(), json!(flow));
                    }
                }
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

    if let Some(ref m) = node.mux {
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

pub(crate) fn profile_requires_xray(proxy: &ProxyNode) -> Result<bool, AppError> {
    if proxy.protocol != "vless" {
        return Ok(false);
    }
    Ok(classify_vless_transport(proxy.network.as_deref())? == VlessTransportKind::Xhttp)
}

fn validate_managed_sing_box_transport(proxy: &ProxyNode) -> Result<(), AppError> {
    if proxy.protocol != "vless" {
        return Ok(());
    }
    match classify_vless_transport(proxy.network.as_deref())? {
        VlessTransportKind::Raw => Ok(()),
        VlessTransportKind::Xhttp => Err(AppError::Actionable {
            error: "XHTTP cannot be generated for the bundled sing-box runtime".to_string(),
            resolution: "Use the managed Xray path for this profile".to_string(),
        }),
    }
}

pub(crate) fn managed_xray_incompatible_features(
    proxy: &ProxyNode,
    user_rules: &[RoutingRule],
    split_apps: &[String],
    stealth_mode_enabled: bool,
    pqc_enforcement_mode: bool,
    privacy_shield_level: &str,
) -> Vec<&'static str> {
    let mut features = Vec::new();
    if proxy.next_hop_id.is_some() {
        features.push("multi-hop");
    }
    if user_rules.iter().any(|rule| rule.enabled) {
        features.push("custom routing rules");
    }
    if !split_apps.is_empty() {
        features.push("application split tunneling");
    }
    if stealth_mode_enabled {
        features.push("stealth mode");
    }
    if proxy.pqc_enabled.unwrap_or(false) || pqc_enforcement_mode {
        features.push("PQC enforcement");
    }
    if privacy_shield_level != "disabled" {
        features.push("Privacy Shield");
    }
    if proxy.tls_fragment == Some(true) || proxy.tls_record_fragment == Some(true) {
        features.push("TLS fragmentation");
    }
    if proxy.mux.as_deref().is_some_and(|mux| mux != "none") {
        features.push("multiplexing");
    }
    features
}

/// Generates an Xray configuration for the Remnawave VLESS transports that
/// cannot be represented by the bundled sing-box 1.13 transport API.
pub fn generate_xray_config(
    proxy: &ProxyNode,
    tun_enabled: bool,
    log_path: Option<&std::path::Path>,
    local_socks_port: Option<u16>,
    allow_lan: bool,
) -> Result<Value, AppError> {
    if proxy.protocol != "vless" {
        return Err(AppError::Actionable {
            error: format!(
                "Xray profile protocol '{}' is not supported",
                proxy.protocol
            ),
            resolution: "Select sing-box for this profile or import a VLESS profile".to_string(),
        });
    }
    if tun_enabled {
        return Err(AppError::Actionable {
            error: "The managed Xray profile path currently exposes a local SOCKS inbound only"
                .to_string(),
            resolution: "Disable TUN mode or select a compatible sing-box profile".to_string(),
        });
    }

    let transport_kind = classify_vless_transport(proxy.network.as_deref())?;
    let uuid = proxy
        .uuid
        .as_deref()
        .filter(|value| !value.trim().is_empty())
        .ok_or_else(|| AppError::System("VLESS profile missing UUID".to_string()))?;

    let security = proxy.tls.as_deref().unwrap_or("none");
    if !matches!(security, "none" | "tls" | "reality") {
        return Err(AppError::System(format!(
            "Unsupported VLESS security: {security}"
        )));
    }

    let mut user = serde_json::Map::new();
    user.insert("id".to_string(), json!(uuid));
    user.insert("encryption".to_string(), json!("none"));
    if transport_kind == VlessTransportKind::Raw {
        if let Some(flow) = proxy.flow.as_deref().filter(|value| !value.is_empty()) {
            if flow != "xtls-rprx-vision" {
                return Err(AppError::System(format!("Unsupported VLESS flow: {flow}")));
            }
            user.insert("flow".to_string(), json!(flow));
        }
    }

    let mut stream_settings = serde_json::Map::new();
    stream_settings.insert(
        "network".to_string(),
        json!(if transport_kind == VlessTransportKind::Xhttp {
            "xhttp"
        } else {
            "raw"
        }),
    );
    stream_settings.insert("security".to_string(), json!(security));

    match security {
        "reality" => {
            let server_name = proxy
                .sni
                .as_deref()
                .filter(|value| !value.trim().is_empty())
                .ok_or_else(|| AppError::System("Reality profile missing SNI".to_string()))?;
            let public_key = proxy
                .public_key
                .as_deref()
                .filter(|value| !value.trim().is_empty())
                .ok_or_else(|| {
                    AppError::System("Reality profile missing public key".to_string())
                })?;
            stream_settings.insert(
                "realitySettings".to_string(),
                json!({
                    "fingerprint": proxy.fingerprint.as_deref().unwrap_or("chrome"),
                    "serverName": server_name,
                    "publicKey": public_key,
                    "shortId": proxy.short_id.as_deref().unwrap_or(""),
                    "spiderX": ""
                }),
            );
        }
        "tls" => {
            stream_settings.insert(
                "tlsSettings".to_string(),
                json!({
                    "serverName": proxy.sni.as_deref().unwrap_or(&proxy.server),
                    "fingerprint": proxy.fingerprint.as_deref().unwrap_or("chrome")
                }),
            );
        }
        _ => {}
    }

    if transport_kind == VlessTransportKind::Raw {
        stream_settings.insert(
            "rawSettings".to_string(),
            json!({"header": {"type": "none"}}),
        );
    } else {
        let mut xhttp_settings = serde_json::Map::new();
        if let Some(path) = proxy.transport_path.as_deref() {
            xhttp_settings.insert("path".to_string(), json!(path));
        }
        if let Some(host) = proxy.transport_host.as_deref() {
            xhttp_settings.insert("host".to_string(), json!(host));
        }
        if let Some(mode) = proxy.xhttp_mode.as_deref() {
            match mode {
                "auto" | "packet-up" | "stream-up" | "stream-one" => {
                    xhttp_settings.insert("mode".to_string(), json!(mode));
                }
                _ => return Err(AppError::System(format!("Unsupported XHTTP mode: {mode}"))),
            }
        }
        stream_settings.insert("xhttpSettings".to_string(), Value::Object(xhttp_settings));
    }

    let mut log = serde_json::Map::new();
    log.insert("loglevel".to_string(), json!("warning"));
    if let Some(path) = log_path.and_then(std::path::Path::to_str) {
        log.insert("error".to_string(), json!(path));
    }

    Ok(json!({
        "log": log,
        "inbounds": [{
            "tag": "socks-in",
            "listen": if allow_lan { "0.0.0.0" } else { "127.0.0.1" },
            "port": local_socks_port.unwrap_or(2080),
            "protocol": "socks",
            "settings": {"udp": true}
        }],
        "outbounds": [
            {
                "tag": "proxy",
                "protocol": "vless",
                "settings": {
                    "vnext": [{
                        "address": proxy.server,
                        "port": proxy.port,
                        "users": [Value::Object(user)]
                    }]
                },
                "streamSettings": Value::Object(stream_settings)
            },
            {"tag": "direct", "protocol": "freedom"}
        ]
    }))
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
/// let config = generate_singbox_config(&node, &[], false, &[], None, None, false, &[], "disallow", false, false, "disabled", None)?;
/// assert_eq!(config["outbounds"][0]["tag"], "proxy");
/// # Ok::<(), desktop_client_lib::engine::error::AppError>(())
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
) -> Result<Value, AppError> {
    if stealth_mode_enabled {
        return Err(AppError::Actionable {
            error: "The bundled sing-box runtime cannot safely represent CyberVPN stealth mode"
                .to_string(),
            resolution:
                "Disable stealth mode before connecting with the managed sing-box configuration"
                    .to_string(),
        });
    }
    validate_managed_sing_box_transport(proxy)?;
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
                validate_managed_sing_box_transport(next_node)?;
                outbounds.push(create_outbound(
                    next_node,
                    next_tag,
                    None,
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

    Ok(json!({
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
    }))
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
        )
        .expect("sing-box config should generate");

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
        )
        .expect("sing-box config should generate");
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
        )
        .expect("sing-box config should generate");

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
        )
        .expect("sing-box config should generate");
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
        )
        .expect("sing-box config should generate");

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
        )
        .expect("sing-box config should generate");

        let endpoints = config["endpoints"].as_array().unwrap();
        let proxy_endpoint = endpoints
            .iter()
            .find(|endpoint| endpoint["tag"] == "proxy")
            .expect("Missing Tailscale endpoint");

        assert_eq!(proxy_endpoint["type"], "tailscale");
        assert_eq!(proxy_endpoint["state_directory"], "tailscale-state");
        assert_eq!(proxy_endpoint["accept_routes"], true);
    }

    fn reality_vless_node(network: &str) -> ProxyNode {
        ProxyNode {
            network: Some(network.to_string()),
            flow: Some("xtls-rprx-vision".to_string()),
            tls: Some("reality".to_string()),
            sni: Some("cover.example".to_string()),
            fingerprint: Some("chrome".to_string()),
            public_key: Some("ye-EGRj9KI06zeYwNZ0lZHnaRkMLtPif_66E6jJGbVo".to_string()),
            short_id: Some("abcd".to_string()),
            ..create_mock_node("reality", None)
        }
    }

    #[test]
    fn xray_raw_reality_keeps_vision_flow() {
        let node = reality_vless_node("raw");
        let config = generate_xray_config(&node, false, None, Some(2080), false)
            .expect("RAW Reality config should be generated");

        assert_eq!(
            config["outbounds"][0]["settings"]["vnext"][0]["users"][0]["flow"],
            "xtls-rprx-vision"
        );
        assert_eq!(config["outbounds"][0]["streamSettings"]["network"], "raw");
        assert_eq!(
            config["outbounds"][0]["streamSettings"]["realitySettings"]["publicKey"],
            "ye-EGRj9KI06zeYwNZ0lZHnaRkMLtPif_66E6jJGbVo"
        );
    }

    #[test]
    fn xray_xhttp_reality_omits_flow_and_preserves_options() {
        let mut node = reality_vless_node("xhttp");
        node.transport_path = Some("/api/v3".to_string());
        node.transport_host = Some("cdn.example".to_string());
        node.xhttp_mode = Some("packet-up".to_string());

        let config = generate_xray_config(&node, false, None, Some(2080), false)
            .expect("XHTTP Reality config should be generated");
        let user = &config["outbounds"][0]["settings"]["vnext"][0]["users"][0];
        let stream = &config["outbounds"][0]["streamSettings"];

        assert!(user.get("flow").is_none());
        assert_eq!(stream["network"], "xhttp");
        assert_eq!(stream["xhttpSettings"]["path"], "/api/v3");
        assert_eq!(stream["xhttpSettings"]["host"], "cdn.example");
        assert_eq!(stream["xhttpSettings"]["mode"], "packet-up");
        assert!(profile_requires_xray(&node).expect("transport should classify"));

        let error = generate_singbox_config(
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
        )
        .expect_err("XHTTP must never be passed to the bundled sing-box generator");
        assert!(error.to_string().contains("managed Xray"));
    }

    #[test]
    fn managed_sing_box_stealth_mode_fails_before_generating_xhttp() {
        let node = reality_vless_node("raw");
        let error = generate_singbox_config(
            &node,
            &[],
            false,
            &[],
            None,
            None,
            false,
            &[],
            "allow",
            true,
            false,
            "disabled",
            None,
        )
        .expect_err("stealth must fail closed for sing-box 1.13.8");

        assert!(error.to_string().contains("cannot safely represent"));
    }

    #[test]
    fn xray_unknown_transport_mode_and_managed_tun_fail_closed() {
        let mut node = reality_vless_node("magic");
        assert!(generate_xray_config(&node, false, None, None, false).is_err());

        node.network = Some("xhttp".to_string());
        node.xhttp_mode = Some("unsafe".to_string());
        assert!(generate_xray_config(&node, false, None, None, false).is_err());

        node.xhttp_mode = Some("auto".to_string());
        assert!(generate_xray_config(&node, true, None, None, false).is_err());
    }

    #[test]
    fn managed_xray_reports_features_it_cannot_preserve() {
        let mut node = reality_vless_node("xhttp");
        node.next_hop_id = Some("next".to_string());
        node.tls_fragment = Some(true);
        let rule = RoutingRule {
            id: "r1".into(),
            enabled: true,
            domains: vec!["example.com".into()],
            ips: vec![],
            outbound: "proxy".into(),
            process_name: vec![],
            port_range: vec![],
            network: None,
            domain_keyword: vec![],
            domain_regex: vec![],
        };

        let incompatible = managed_xray_incompatible_features(
            &node,
            &[rule],
            &["browser.exe".to_string()],
            false,
            false,
            "disabled",
        );
        assert_eq!(
            incompatible,
            vec![
                "multi-hop",
                "custom routing rules",
                "application split tunneling",
                "TLS fragmentation"
            ]
        );
    }

    #[test]
    fn exports_xray_protocol_matrix_fixtures_when_requested() {
        let raw = reality_vless_node("raw");
        let mut xhttp = reality_vless_node("xhttp");
        xhttp.transport_path = Some("/api/v3".to_string());
        xhttp.transport_host = Some("cdn.invalid".to_string());
        xhttp.xhttp_mode = Some("packet-up".to_string());

        let raw_config = generate_xray_config(&raw, false, None, Some(2080), false)
            .expect("RAW matrix fixture should generate");
        let xhttp_config = generate_xray_config(&xhttp, false, None, Some(2080), false)
            .expect("XHTTP matrix fixture should generate");
        assert_eq!(
            raw_config["outbounds"][0]["settings"]["vnext"][0]["users"][0]["flow"],
            "xtls-rprx-vision"
        );
        assert!(
            xhttp_config["outbounds"][0]["settings"]["vnext"][0]["users"][0]
                .get("flow")
                .is_none()
        );

        if let Some(output_dir) = std::env::var_os("CYBERVPN_PROTOCOL_MATRIX_OUTPUT") {
            let output_dir = std::path::PathBuf::from(output_dir);
            std::fs::create_dir_all(&output_dir).expect("matrix output directory should exist");
            std::fs::write(
                output_dir.join("xray-raw.json"),
                serde_json::to_vec_pretty(&raw_config).expect("RAW config should serialize"),
            )
            .expect("RAW matrix fixture should be written");
            std::fs::write(
                output_dir.join("xray-xhttp.json"),
                serde_json::to_vec_pretty(&xhttp_config).expect("XHTTP config should serialize"),
            )
            .expect("XHTTP matrix fixture should be written");
        }
    }
}
