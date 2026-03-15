use crate::engine::error::AppError;
use crate::ipc::models::ProxyNode;
use base64::prelude::*;
use url::Url;

#[derive(serde::Deserialize, serde::Serialize, Debug)]
#[allow(dead_code)]
struct VmessFormat {
    v: String,
    add: String,
    port: serde_json::Value,
    id: String,
    ps: Option<String>,
    scy: Option<String>,
    net: Option<String>,
    tls: Option<String>,
    sni: Option<String>,
    host: Option<String>,
    path: Option<String>,
    aid: Option<serde_json::Value>,
    alpn: Option<String>,
}

pub fn parse_vmess(link: &str) -> Result<ProxyNode, AppError> {
    let b64 = link.trim_start_matches("vmess://");
    let decoded = BASE64_URL_SAFE_NO_PAD
        .decode(b64)
        .or_else(|_| BASE64_URL_SAFE.decode(b64))
        .or_else(|_| BASE64_STANDARD_NO_PAD.decode(b64))
        .or_else(|_| BASE64_STANDARD.decode(b64))
        .map_err(|e| AppError::System(format!("VMess base64 decode failed: {}", e)))?;

    let vmess: VmessFormat = serde_json::from_slice(&decoded)
        .map_err(|e| AppError::System(format!("VMess JSON parse failed: {}", e)))?;

    let port = match vmess.port {
        serde_json::Value::Number(ref n) => n.as_u64().unwrap_or(443) as u16,
        serde_json::Value::String(ref s) => s.parse().unwrap_or(443),
        _ => 443,
    };

    let alter_id = vmess.aid.and_then(|v| match v {
        serde_json::Value::Number(n) => n.as_u64().map(|n| n as u16),
        serde_json::Value::String(s) => s.parse().ok(),
        _ => None,
    });

    let alpn = vmess
        .alpn
        .filter(|s| !s.is_empty())
        .map(|s| s.split(',').map(|s| s.trim().to_string()).collect());

    // Fallback sni to host if sni is empty
    let mut final_sni = vmess.sni.filter(|s| !s.is_empty());
    if final_sni.is_none() {
        final_sni = vmess.host.filter(|s| !s.is_empty());
    }

    Ok(ProxyNode {
        id: uuid::Uuid::new_v4().to_string(),
        name: vmess.ps.unwrap_or_else(|| format!("VMess {}", vmess.add)),
        server: vmess.add,
        port,
        protocol: "vmess".to_string(),
        uuid: Some(vmess.id),
        password: None,
        network: vmess.net.filter(|s| !s.is_empty()),
        flow: None,
        tls: vmess.tls.filter(|s| !s.is_empty()),
        sni: final_sni,
        fingerprint: None,
        public_key: None,
        short_id: None,
        ping: None,
        next_hop_id: None,
        alter_id,
        security: vmess.scy.filter(|s| !s.is_empty()),
        method: None,
        obfs: None,
        obfs_password: None,
        up_mbps: None,
        down_mbps: None,
        alpn,
        subscription_id: None,
        congestion_control: None,
        udp_relay_mode: None,
        local_address: None,
        private_key: None,
        peer_public_key: None,
        mtu: None,
    })
}

pub fn parse_shadowsocks(link: &str) -> Result<ProxyNode, AppError> {
    let parsed_url =
        Url::parse(link).map_err(|e| AppError::System(format!("SS Invalid URL: {}", e)))?;
    if parsed_url.scheme() != "ss" {
        return Err(AppError::System("Not a shadowsocks link".to_string()));
    }

    let mut username = parsed_url.username().to_string();
    if let Some(pass) = parsed_url.password() {
        username = format!("{}:{}", username, pass);
    }

    let decoded_userinfo = BASE64_URL_SAFE_NO_PAD
        .decode(&username)
        .or_else(|_| BASE64_URL_SAFE.decode(&username))
        .or_else(|_| BASE64_STANDARD_NO_PAD.decode(&username))
        .or_else(|_| BASE64_STANDARD.decode(&username))
        .unwrap_or_else(|_| username.as_bytes().to_vec());

    let userinfo_str = String::from_utf8(decoded_userinfo)
        .map_err(|_| AppError::System("SS userinfo is not utf8".to_string()))?;

    let parts: Vec<&str> = userinfo_str.splitn(2, ':').collect();
    if parts.len() != 2 {
        return Err(AppError::System(
            "SS userinfo does not contain method:password".to_string(),
        ));
    }

    let method = parts[0].to_string();
    let password = parts[1].to_string();

    let host = parsed_url
        .host_str()
        .ok_or_else(|| AppError::System("SS link missing host".to_string()))?
        .to_string();
    let port = parsed_url.port().unwrap_or(8388);

    let name = if let Some(fragment) = parsed_url.fragment() {
        let decoded = urlencoding::decode(&fragment.replace('+', " "))
            .unwrap_or(std::borrow::Cow::Borrowed("Imported SS"))
            .into_owned();
        decoded
    } else {
        format!("SS {}", host)
    };

    Ok(ProxyNode {
        id: uuid::Uuid::new_v4().to_string(),
        name,
        server: host,
        port,
        protocol: "shadowsocks".to_string(),
        uuid: None,
        password: Some(password),
        network: None,
        flow: None,
        tls: None,
        sni: None,
        fingerprint: None,
        public_key: None,
        short_id: None,
        ping: None,
        next_hop_id: None,
        alter_id: None,
        security: None,
        method: Some(method),
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
    })
}

pub fn parse_trojan(link: &str) -> Result<ProxyNode, AppError> {
    let parsed_url =
        Url::parse(link).map_err(|e| AppError::System(format!("Trojan Invalid URL: {}", e)))?;
    if parsed_url.scheme() != "trojan" {
        return Err(AppError::System("Not a trojan link".to_string()));
    }

    let password = parsed_url.username().to_string();
    if password.is_empty() {
        return Err(AppError::System("Trojan link missing password".to_string()));
    }

    let host = parsed_url
        .host_str()
        .ok_or_else(|| AppError::System("Trojan link missing host".to_string()))?
        .to_string();
    let port = parsed_url.port().unwrap_or(443);

    let name = if let Some(fragment) = parsed_url.fragment() {
        let decoded = urlencoding::decode(&fragment.replace('+', " "))
            .unwrap_or(std::borrow::Cow::Borrowed("Imported Trojan"))
            .into_owned();
        decoded
    } else {
        format!("Trojan {}", host)
    };

    let mut sni = None;
    let mut security = Some("tls".to_string());
    let mut flow = None;

    for (k, v) in parsed_url.query_pairs() {
        match k.as_ref() {
            "sni" | "peer" => sni = Some(v.into_owned()),
            "security" => security = Some(v.into_owned()),
            "flow" => flow = Some(v.into_owned()),
            _ => {}
        }
    }

    Ok(ProxyNode {
        id: uuid::Uuid::new_v4().to_string(),
        name,
        server: host,
        port,
        protocol: "trojan".to_string(),
        uuid: None,
        password: Some(password),
        network: None,
        flow,
        tls: security.clone(),
        sni,
        fingerprint: None,
        public_key: None,
        short_id: None,
        ping: None,
        next_hop_id: None,
        alter_id: None,
        security,
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
    })
}

pub fn parse_hysteria2(link: &str) -> Result<ProxyNode, AppError> {
    let parsed_url =
        Url::parse(link).map_err(|e| AppError::System(format!("HY2 Invalid URL: {}", e)))?;
    if parsed_url.scheme() != "hy2" && parsed_url.scheme() != "hysteria2" {
        return Err(AppError::System("Not a hysteria2 link".to_string()));
    }

    let password = parsed_url.username().to_string();
    if password.is_empty() {
        return Err(AppError::System("HY2 link missing password".to_string()));
    }
    let host = parsed_url
        .host_str()
        .ok_or_else(|| AppError::System("HY2 link missing host".to_string()))?
        .to_string();
    let port = parsed_url.port().unwrap_or(443);

    let name = if let Some(fragment) = parsed_url.fragment() {
        let decoded = urlencoding::decode(&fragment.replace('+', " "))
            .unwrap_or(std::borrow::Cow::Borrowed("Imported Hysteria2"))
            .into_owned();
        decoded
    } else {
        format!("HY2 {}", host)
    };

    let mut obfs = None;
    let mut obfs_password = None;
    let mut up_mbps = None;
    let mut down_mbps = None;
    let mut sni = None;
    let mut alpn = None;

    for (k, v) in parsed_url.query_pairs() {
        match k.as_ref() {
            "obfs" => obfs = Some(v.into_owned()),
            "obfs-password" | "obfsParam" => obfs_password = Some(v.into_owned()),
            "up" | "upmbps" => up_mbps = v.parse().ok(),
            "down" | "downmbps" => down_mbps = v.parse().ok(),
            "sni" | "peer" => sni = Some(v.into_owned()),
            "alpn" => alpn = Some(v.split(',').map(|s| s.trim().to_string()).collect()),
            _ => {}
        }
    }

    Ok(ProxyNode {
        id: uuid::Uuid::new_v4().to_string(),
        name,
        server: host,
        port,
        protocol: "hysteria2".to_string(),
        uuid: None,
        password: Some(password),
        network: None,
        flow: None,
        tls: None,
        sni,
        fingerprint: None,
        public_key: None,
        short_id: None,
        ping: None,
        next_hop_id: None,
        alter_id: None,
        security: None,
        method: None,
        obfs,
        obfs_password,
        up_mbps,
        down_mbps,
        alpn,
        subscription_id: None,
        congestion_control: None,
        udp_relay_mode: None,
        local_address: None,
        private_key: None,
        peer_public_key: None,
        mtu: None,
    })
}

pub fn parse_vless(link: &str) -> Result<ProxyNode, AppError> {
    let parsed_url =
        Url::parse(link).map_err(|e| AppError::System(format!("Invalid URL: {}", e)))?;

    if parsed_url.scheme() != "vless" {
        return Err(AppError::System("Not a vless link".to_string()));
    }

    let uuid = parsed_url.username().to_string();
    if uuid.is_empty() {
        return Err(AppError::System("VLESS link missing UUID".to_string()));
    }

    let host = parsed_url
        .host_str()
        .ok_or_else(|| AppError::System("VLESS link missing host".to_string()))?
        .to_string();
    let port = parsed_url.port().unwrap_or(443);

    let name = if let Some(fragment) = parsed_url.fragment() {
        let decoded = urlencoding::decode(&fragment.replace('+', " "))
            .unwrap_or(std::borrow::Cow::Borrowed("Imported VLESS"))
            .into_owned();
        decoded
    } else {
        format!("VLESS {}", host)
    };

    let mut tls = None;
    let mut sni = None;
    let mut fingerprint = None;
    let mut flow = None;
    let mut short_id = None;
    let mut public_key = None;

    for (k, v) in parsed_url.query_pairs() {
        match k.as_ref() {
            "security" => tls = Some(v.into_owned()),
            "sni" => sni = Some(v.into_owned()),
            "fp" => fingerprint = Some(v.into_owned()),
            "flow" => flow = Some(v.into_owned()),
            "sid" => short_id = Some(v.into_owned()),
            "pbk" => public_key = Some(v.into_owned()),
            _ => {}
        }
    }

    Ok(ProxyNode {
        id: uuid::Uuid::new_v4().to_string(),
        name,
        server: host,
        port,
        protocol: "vless".to_string(),
        uuid: Some(uuid),
        password: None,
        network: None,
        flow,
        tls,
        sni,
        fingerprint,
        public_key,
        short_id,
        ping: None,
        next_hop_id: None,
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
    })
}

fn decode_userinfo(user: &str, pass: Option<&str>) -> (String, Option<String>) {
    let user_decoded = urlencoding::decode(user)
        .unwrap_or(std::borrow::Cow::Borrowed(user))
        .into_owned();
    let pass_decoded = pass.map(|p| {
        urlencoding::decode(p)
            .unwrap_or(std::borrow::Cow::Borrowed(p))
            .into_owned()
    });

    if pass_decoded.is_none() && !user_decoded.contains(':') && !user_decoded.is_empty() {
        if let Ok(decoded_bytes) = BASE64_STANDARD.decode(&user_decoded) {
            if let Ok(decoded_str) = String::from_utf8(decoded_bytes) {
                if let Some((u, p)) = decoded_str.split_once(':') {
                    return (u.to_string(), Some(p.to_string()));
                }
            }
        }
        if let Ok(decoded_bytes) = BASE64_URL_SAFE_NO_PAD.decode(&user_decoded) {
            if let Ok(decoded_str) = String::from_utf8(decoded_bytes) {
                if let Some((u, p)) = decoded_str.split_once(':') {
                    return (u.to_string(), Some(p.to_string()));
                }
            }
        }
    }

    (user_decoded, pass_decoded)
}

pub fn parse_tuic(link: &str) -> Result<ProxyNode, AppError> {
    let parsed_url =
        Url::parse(link).map_err(|e| AppError::System(format!("TUIC Invalid URL: {}", e)))?;
    if parsed_url.scheme() != "tuic" {
        return Err(AppError::System("Not a tuic link".to_string()));
    }

    let uuid = parsed_url.username().to_string();
    if uuid.is_empty() {
        return Err(AppError::System("TUIC link missing UUID".to_string()));
    }

    let password = parsed_url.password().map(|p| p.to_string());
    let host = parsed_url
        .host_str()
        .ok_or_else(|| AppError::System("TUIC link missing host".to_string()))?
        .to_string();
    let port = parsed_url.port().unwrap_or(443);

    let name = if let Some(fragment) = parsed_url.fragment() {
        urlencoding::decode(&fragment.replace('+', " "))
            .unwrap_or(std::borrow::Cow::Borrowed("Imported TUIC"))
            .into_owned()
    } else {
        format!("TUIC {}", host)
    };

    let mut congestion_control = None;
    let mut udp_relay_mode = None;
    let mut sni = None;
    let mut alpn = None;

    for (k, v) in parsed_url.query_pairs() {
        match k.as_ref() {
            "congestion_control" => congestion_control = Some(v.into_owned()),
            "udp_relay_mode" => udp_relay_mode = Some(v.into_owned()),
            "sni" => sni = Some(v.into_owned()),
            "alpn" => alpn = Some(v.split(',').map(|s| s.trim().to_string()).collect()),
            _ => {}
        }
    }

    Ok(ProxyNode {
        id: uuid::Uuid::new_v4().to_string(),
        name,
        server: host,
        port,
        protocol: "tuic".to_string(),
        uuid: Some(uuid),
        password,
        network: None,
        flow: None,
        tls: None,
        sni,
        fingerprint: None,
        public_key: None,
        short_id: None,
        ping: None,
        next_hop_id: None,
        alter_id: None,
        security: None,
        method: None,
        obfs: None,
        obfs_password: None,
        up_mbps: None,
        down_mbps: None,
        alpn,
        subscription_id: None,
        congestion_control,
        udp_relay_mode,
        local_address: None,
        private_key: None,
        peer_public_key: None,
        mtu: None,
    })
}

pub fn parse_wireguard(link: &str) -> Result<ProxyNode, AppError> {
    let parsed_url =
        Url::parse(link).map_err(|e| AppError::System(format!("WG Invalid URL: {}", e)))?;
    if parsed_url.scheme() != "wg" && parsed_url.scheme() != "wireguard" {
        return Err(AppError::System("Not a wireguard link".to_string()));
    }

    let peer_public_key = parsed_url.username().to_string();
    if peer_public_key.is_empty() {
        return Err(AppError::System(
            "Wireguard link missing peer pubkey".to_string(),
        ));
    }

    let peer_public_key = urlencoding::decode(&peer_public_key)
        .unwrap_or(std::borrow::Cow::Borrowed(&peer_public_key))
        .into_owned();

    let host = parsed_url
        .host_str()
        .ok_or_else(|| AppError::System("Wireguard missing endpoint".to_string()))?
        .to_string();
    let port = parsed_url.port().unwrap_or(51820);

    let name = if let Some(fragment) = parsed_url.fragment() {
        urlencoding::decode(&fragment.replace('+', " "))
            .unwrap_or(std::borrow::Cow::Borrowed("Imported WG"))
            .into_owned()
    } else {
        format!("WG {}", host)
    };

    let mut private_key = None;
    let mut local_address = None;
    let mut mtu = None;

    for (k, v) in parsed_url.query_pairs() {
        match k.as_ref() {
            "private_key" | "privateKey" => private_key = Some(v.into_owned()),
            "address" | "local_address" => {
                local_address = Some(v.split(',').map(|s| s.trim().to_string()).collect());
            }
            "mtu" => mtu = v.parse::<u32>().ok(),
            _ => {}
        }
    }

    Ok(ProxyNode {
        id: uuid::Uuid::new_v4().to_string(),
        name,
        server: host,
        port,
        protocol: "wireguard".to_string(),
        uuid: None,
        password: None,
        network: None,
        flow: None,
        tls: None,
        sni: None,
        fingerprint: None,
        public_key: None,
        short_id: None,
        ping: None,
        next_hop_id: None,
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
        local_address,
        private_key,
        peer_public_key: Some(peer_public_key),
        mtu,
    })
}

pub fn parse_socks(link: &str) -> Result<ProxyNode, AppError> {
    let parsed_url =
        Url::parse(link).map_err(|e| AppError::System(format!("SOCKS Invalid URL: {}", e)))?;
    if parsed_url.scheme() != "socks5" && parsed_url.scheme() != "socks" {
        return Err(AppError::System("Not a socks link".to_string()));
    }

    let (user, pass) = decode_userinfo(parsed_url.username(), parsed_url.password());
    let host = parsed_url
        .host_str()
        .ok_or_else(|| AppError::System("SOCKS link missing host".to_string()))?
        .to_string();
    let port = parsed_url.port().unwrap_or(1080);

    let name = if let Some(fragment) = parsed_url.fragment() {
        urlencoding::decode(&fragment.replace('+', " "))
            .unwrap_or(std::borrow::Cow::Borrowed("Imported SOCKS"))
            .into_owned()
    } else {
        format!("SOCKS {}", host)
    };

    Ok(ProxyNode {
        id: uuid::Uuid::new_v4().to_string(),
        name,
        server: host,
        port,
        protocol: "socks".to_string(),
        uuid: if user.is_empty() { None } else { Some(user) },
        password: pass,
        network: None,
        flow: None,
        tls: None,
        sni: None,
        fingerprint: None,
        public_key: None,
        short_id: None,
        ping: None,
        next_hop_id: None,
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
    })
}

pub fn parse_http(link: &str) -> Result<ProxyNode, AppError> {
    let parsed_url =
        Url::parse(link).map_err(|e| AppError::System(format!("HTTP Invalid URL: {}", e)))?;
    if parsed_url.scheme() != "http" && parsed_url.scheme() != "https" {
        return Err(AppError::System("Not a http link".to_string()));
    }

    let (user, pass) = decode_userinfo(parsed_url.username(), parsed_url.password());
    let host = parsed_url
        .host_str()
        .ok_or_else(|| AppError::System("HTTP link missing host".to_string()))?
        .to_string();
    let port = parsed_url
        .port()
        .unwrap_or(if parsed_url.scheme() == "https" {
            443
        } else {
            80
        });
    let tls = if parsed_url.scheme() == "https" {
        Some("tls".to_string())
    } else {
        None
    };

    let name = if let Some(fragment) = parsed_url.fragment() {
        urlencoding::decode(&fragment.replace('+', " "))
            .unwrap_or(std::borrow::Cow::Borrowed("Imported HTTP"))
            .into_owned()
    } else {
        format!("HTTP {}", host)
    };

    Ok(ProxyNode {
        id: uuid::Uuid::new_v4().to_string(),
        name,
        server: host,
        port,
        protocol: "http".to_string(),
        uuid: if user.is_empty() { None } else { Some(user) },
        password: pass,
        network: None,
        flow: None,
        tls,
        sni: None,
        fingerprint: None,
        public_key: None,
        short_id: None,
        ping: None,
        next_hop_id: None,
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
    })
}

pub fn parse_ssh(link: &str) -> Result<ProxyNode, AppError> {
    let parsed_url =
        Url::parse(link).map_err(|e| AppError::System(format!("SSH Invalid URL: {}", e)))?;
    if parsed_url.scheme() != "ssh" {
        return Err(AppError::System("Not a ssh link".to_string()));
    }

    let (user, pass) = decode_userinfo(parsed_url.username(), parsed_url.password());
    let host = parsed_url
        .host_str()
        .ok_or_else(|| AppError::System("SSH link missing host".to_string()))?
        .to_string();
    let port = parsed_url.port().unwrap_or(22);

    let name = if let Some(fragment) = parsed_url.fragment() {
        urlencoding::decode(&fragment.replace('+', " "))
            .unwrap_or(std::borrow::Cow::Borrowed("Imported SSH"))
            .into_owned()
    } else {
        format!("SSH {}", host)
    };

    let mut private_key = None;
    for (k, v) in parsed_url.query_pairs() {
        if k == "private_key" || k == "privateKey" {
            private_key = Some(v.into_owned());
        }
    }

    Ok(ProxyNode {
        id: uuid::Uuid::new_v4().to_string(),
        name,
        server: host,
        port,
        protocol: "ssh".to_string(),
        uuid: if user.is_empty() { None } else { Some(user) },
        password: pass,
        network: None,
        flow: None,
        tls: None,
        sni: None,
        fingerprint: None,
        public_key: None,
        short_id: None,
        ping: None,
        next_hop_id: None,
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
        private_key,
        peer_public_key: None,
        mtu: None,
    })
}

/// Generates a shareable URL link for a given `ProxyNode`.
pub fn generate_link(node: &ProxyNode) -> String {
    let mut url_str = match node.protocol.as_str() {
        "vless" => {
            let mut u = Url::parse("vless://").unwrap();
            let _ = u.set_username(node.uuid.as_deref().unwrap_or(""));
            let _ = u.set_host(Some(&node.server));
            let _ = u.set_port(Some(node.port));

            let mut q = u.query_pairs_mut();
            if let Some(ref flow) = node.flow {
                q.append_pair("flow", flow);
            }
            if let Some(ref tls) = node.tls {
                q.append_pair("security", tls);
            }
            if let Some(ref sni) = node.sni {
                q.append_pair("sni", sni);
            }
            if let Some(ref fp) = node.fingerprint {
                q.append_pair("fp", fp);
            }
            if let Some(ref pbk) = node.public_key {
                q.append_pair("pbk", pbk);
            }
            if let Some(ref sid) = node.short_id {
                q.append_pair("sid", sid);
            }
            drop(q);

            u.set_fragment(Some(&node.name));
            u.to_string()
        }
        "trojan" => {
            let mut u = Url::parse("trojan://").unwrap();
            let _ = u.set_username(node.password.as_deref().unwrap_or(""));
            let _ = u.set_host(Some(&node.server));
            let _ = u.set_port(Some(node.port));

            let mut q = u.query_pairs_mut();
            if let Some(ref sni) = node.sni {
                q.append_pair("sni", sni);
            }
            if let Some(ref sec) = node.security {
                q.append_pair("security", sec);
            }
            if let Some(ref flow) = node.flow {
                q.append_pair("flow", flow);
            }
            drop(q);

            u.set_fragment(Some(&node.name));
            u.to_string()
        }
        "hysteria2" | "hy2" => {
            let mut u = Url::parse("hy2://").unwrap();
            let _ = u.set_username(node.password.as_deref().unwrap_or(""));
            let _ = u.set_host(Some(&node.server));
            let _ = u.set_port(Some(node.port));

            let mut q = u.query_pairs_mut();
            if let Some(ref obfs) = node.obfs {
                q.append_pair("obfs", obfs);
            }
            if let Some(ref obfs_pw) = node.obfs_password {
                q.append_pair("obfs-password", obfs_pw);
            }
            if let Some(up) = node.up_mbps {
                q.append_pair("up", &up.to_string());
            }
            if let Some(down) = node.down_mbps {
                q.append_pair("down", &down.to_string());
            }
            if let Some(ref sni) = node.sni {
                q.append_pair("sni", sni);
            }
            if let Some(ref alpn) = node.alpn {
                q.append_pair("alpn", &alpn.join(","));
            }
            drop(q);

            u.set_fragment(Some(&node.name));
            u.to_string()
        }
        "shadowsocks" => {
            let userpass = format!(
                "{}:{}",
                node.method.as_deref().unwrap_or("chacha20-ietf-poly1305"),
                node.password.as_deref().unwrap_or("")
            );
            let b64 = BASE64_STANDARD.encode(userpass);
            let mut u = Url::parse("ss://").unwrap();
            let _ = u.set_username(&b64);
            let _ = u.set_host(Some(&node.server));
            let _ = u.set_port(Some(node.port));
            u.set_fragment(Some(&node.name));
            u.to_string()
        }
        "vmess" => {
            let vmess = VmessFormat {
                v: "2".to_string(),
                ps: Some(node.name.clone()),
                add: node.server.clone(),
                port: serde_json::json!(node.port),
                id: node.uuid.clone().unwrap_or_default(),
                scy: node.security.clone(),
                net: node.network.clone(),
                tls: node.tls.clone(),
                sni: node.sni.clone(),
                host: node.sni.clone(), // Often duplicated
                path: None,
                aid: node.alter_id.map(|a| serde_json::json!(a)),
                alpn: node.alpn.as_ref().map(|a| a.join(",")),
            };
            let json_str = serde_json::to_string(&vmess).unwrap_or_default();
            format!("vmess://{}", BASE64_STANDARD.encode(json_str))
        }
        _ => "".to_string(),
    };

    // Some urls might encode the fragment with too many escapes, let's keep it simple
    url_str = url_str.trim().to_string();
    url_str
}

/// Parses a given proxy link (e.g., vless://, vmess://) and returns a `ProxyNode`.
pub fn parse_link(link: &str) -> Result<ProxyNode, AppError> {
    let trimmed = link.trim();
    if trimmed.starts_with("vless://") {
        parse_vless(trimmed)
    } else if trimmed.starts_with("vmess://") {
        parse_vmess(trimmed)
    } else if trimmed.starts_with("ss://") {
        parse_shadowsocks(trimmed)
    } else if trimmed.starts_with("trojan://") {
        parse_trojan(trimmed)
    } else if trimmed.starts_with("hy2://") || trimmed.starts_with("hysteria2://") {
        parse_hysteria2(trimmed)
    } else if trimmed.starts_with("tuic://") {
        parse_tuic(trimmed)
    } else if trimmed.starts_with("wg://") || trimmed.starts_with("wireguard://") {
        parse_wireguard(trimmed)
    } else if trimmed.starts_with("socks://") || trimmed.starts_with("socks5://") {
        parse_socks(trimmed)
    } else if trimmed.starts_with("http://") || trimmed.starts_with("https://") {
        parse_http(trimmed)
    } else if trimmed.starts_with("ssh://") {
        parse_ssh(trimmed)
    } else {
        Err(AppError::System(
            "Unsupported protocol/link format.".to_string(),
        ))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_vmess_should_extract_valid_fields() {
        // vmess payload: {"v":"2","ps":"My VMess","add":"1.2.3.4","port":10086,"id":"deadd0d0-0000-0000-0000-000000000000","net":"ws","type":"none","tls":"tls","sni":"example.com"}
        let b64 = BASE64_STANDARD.encode(r#"{"v":"2","ps":"My VMess","add":"1.2.3.4","port":10086,"id":"deadd0d0-0000-0000-0000-000000000000","net":"ws","type":"none","tls":"tls","sni":"example.com"}"#);
        let link = format!("vmess://{}", b64);

        let node = parse_link(&link).expect("Failed to parse VMess");
        assert_eq!(node.protocol, "vmess");
        assert_eq!(node.name, "My VMess");
        assert_eq!(node.server, "1.2.3.4");
        assert_eq!(node.port, 10086);
        assert_eq!(node.network.as_deref(), Some("ws"));
        assert_eq!(node.tls.as_deref(), Some("tls"));
        assert_eq!(node.sni.as_deref(), Some("example.com"));
        assert_eq!(
            node.uuid.as_deref(),
            Some("deadd0d0-0000-0000-0000-000000000000")
        );
    }

    #[test]
    fn parse_vmess_should_fail_gracefully_on_invalid_base64() {
        let result = parse_link("vmess://!!!invalid_base_64!!!");
        assert!(result.is_err());
    }

    #[test]
    fn parse_shadowsocks_should_extract_sip002_parameters_correctly() {
        // chacha20-ietf-poly1305:mypassword
        let b64_userinfo = BASE64_STANDARD.encode("chacha20-ietf-poly1305:mypassword");
        let link = format!("ss://{}@1.1.1.1:8388#SS%20Node", b64_userinfo);

        let node = parse_link(&link).expect("Failed to parse SS");
        assert_eq!(node.protocol, "shadowsocks");
        assert_eq!(node.name, "SS Node");
        assert_eq!(node.server, "1.1.1.1");
        assert_eq!(node.port, 8388);
        assert_eq!(node.method.as_deref(), Some("chacha20-ietf-poly1305"));
        assert_eq!(node.password.as_deref(), Some("mypassword"));
    }

    #[test]
    fn parse_trojan_should_extract_password_and_sni() {
        let link = "trojan://mypass@trojan.example.com:443?sni=spoofed.com#Trojan%20Node";
        let node = parse_link(link).expect("Failed to parse Trojan");
        assert_eq!(node.protocol, "trojan");
        assert_eq!(node.password.as_deref(), Some("mypass"));
        assert_eq!(node.server, "trojan.example.com");
        assert_eq!(node.tls.as_deref(), Some("tls"));
        assert_eq!(node.sni.as_deref(), Some("spoofed.com"));
    }

    #[test]
    fn parse_hysteria2_should_extract_obfs_and_bandwidth() {
        let link = "hy2://mypass@1.1.1.1:443?obfs=salamander&obfs-password=secret&up=100&down=500&sni=test.com#hy2";
        let node = parse_link(link).expect("Failed to parse HY2");
        assert_eq!(node.protocol, "hysteria2");
        assert_eq!(node.password.as_deref(), Some("mypass"));
        assert_eq!(node.obfs.as_deref(), Some("salamander"));
        assert_eq!(node.obfs_password.as_deref(), Some("secret"));
        assert_eq!(node.up_mbps, Some(100));
        assert_eq!(node.down_mbps, Some(500));
        assert_eq!(node.sni.as_deref(), Some("test.com"));
    }

    #[test]
    fn parse_vless_with_valid_link_should_extract_all_fields() {
        let link = "vless://b831381d-6324-4d53-ad4f-8cda48b30811@api.example.com:8443?security=tls&sni=api.example.com&fp=chrome&pbk=pubkey123&sid=short123#My%20Custom%20Node";
        let node = parse_link(link).expect("Failed to parse valid VLESS link");

        assert_eq!(node.protocol, "vless");
        assert_eq!(node.server, "api.example.com");
        assert_eq!(node.port, 8443);
        assert_eq!(
            node.uuid.as_deref(),
            Some("b831381d-6324-4d53-ad4f-8cda48b30811")
        );
        assert_eq!(node.tls.as_deref(), Some("tls"));
        assert_eq!(node.sni.as_deref(), Some("api.example.com"));
        assert_eq!(node.fingerprint.as_deref(), Some("chrome"));
        assert_eq!(node.public_key.as_deref(), Some("pubkey123"));
        assert_eq!(node.short_id.as_deref(), Some("short123"));
        assert_eq!(node.name, "My Custom Node");
    }

    #[test]
    fn parse_vless_should_return_error_when_uuid_is_missing() {
        let link = "vless://@api.example.com:8443";
        let result = parse_link(link);
        assert!(
            result.is_err(),
            "Expected parsing to fail due to missing UUID"
        );

        if let Err(AppError::System(msg)) = result {
            assert_eq!(msg, "VLESS link missing UUID");
        } else {
            panic!("Expected AppError::System");
        }
    }
    #[test]
    fn parse_tuic_should_extract_parameters() {
        let link = "tuic://my-uuid@tuic.example.com:8443?congestion_control=bbr&udp_relay_mode=native&sni=test.com&alpn=h3,spdy/3.1#tuic_node";
        let node = parse_link(link).expect("Failed to parse TUIC");
        assert_eq!(node.protocol, "tuic");
        assert_eq!(node.uuid.as_deref(), Some("my-uuid"));
        assert_eq!(node.server, "tuic.example.com");
        assert_eq!(node.port, 8443);
        assert_eq!(node.congestion_control.as_deref(), Some("bbr"));
        assert_eq!(node.udp_relay_mode.as_deref(), Some("native"));
        assert_eq!(node.sni.as_deref(), Some("test.com"));
        assert_eq!(
            node.alpn.unwrap(),
            vec!["h3".to_string(), "spdy/3.1".to_string()]
        );
        assert_eq!(node.name, "tuic_node");
    }

    #[test]
    fn parse_wireguard_should_extract_parameters() {
        let link = "wg://peer_pubkey@1.1.1.1:51820?private_key=priv_key&address=10.0.0.1/24,fd00::1/64&mtu=1420#wg_node";
        let node = parse_link(link).expect("Failed to parse WG");
        assert_eq!(node.protocol, "wireguard");
        assert_eq!(node.peer_public_key.as_deref(), Some("peer_pubkey"));
        assert_eq!(node.server, "1.1.1.1");
        assert_eq!(node.port, 51820);
        assert_eq!(node.private_key.as_deref(), Some("priv_key"));
        assert_eq!(
            node.local_address.unwrap(),
            vec!["10.0.0.1/24".to_string(), "fd00::1/64".to_string()]
        );
        assert_eq!(node.mtu, Some(1420));
        assert_eq!(node.name, "wg_node");
    }

    #[test]
    fn parse_socks_should_handle_base64_encode() {
        use base64::prelude::*;
        let b64 = BASE64_STANDARD.encode("user:pass");
        let link = format!("socks5://{}@1.1.1.1:1080#socks_node", b64);
        let node = parse_link(&link).expect("Failed to parse SOCKS");
        assert_eq!(node.protocol, "socks");
        assert_eq!(node.uuid.as_deref(), Some("user"));
        assert_eq!(node.password.as_deref(), Some("pass"));
        assert_eq!(node.server, "1.1.1.1");
        assert_eq!(node.port, 1080);
    }

    #[test]
    fn parse_http_should_handle_url_encode() {
        let link = "https://user%40name:pass%23word@1.1.1.1:443#http_node";
        let node = parse_link(link).expect("Failed to parse HTTP");
        assert_eq!(node.protocol, "http");
        assert_eq!(node.uuid.as_deref(), Some("user@name"));
        assert_eq!(node.password.as_deref(), Some("pass#word"));
        assert_eq!(node.server, "1.1.1.1");
        assert_eq!(node.port, 443);
        assert_eq!(node.tls.as_deref(), Some("tls"));
    }

    #[test]
    fn parse_ssh_should_extract_private_key() {
        let link = "ssh://root:password@1.1.1.1:22?private_key=secret_key#ssh_node";
        let node = parse_link(link).expect("Failed to parse SSH");
        assert_eq!(node.protocol, "ssh");
        assert_eq!(node.uuid.as_deref(), Some("root"));
        assert_eq!(node.password.as_deref(), Some("password"));
        assert_eq!(node.server, "1.1.1.1");
        assert_eq!(node.port, 22);
        assert_eq!(node.private_key.as_deref(), Some("secret_key"));
    }
}
