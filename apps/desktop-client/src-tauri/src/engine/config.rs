use crate::ipc::models::ProxyNode;
use serde_json::{json, Value};

/// Generates a valid sing-box JSON configuration for a given ProxyNode
pub fn generate_singbox_config(proxy: &ProxyNode, tun_enabled: bool) -> Value {
    let outbounds = vec![
        json!({
            "type": proxy.protocol.clone(),
            "tag": "proxy",
            "server": proxy.server.clone(),
            "server_port": proxy.port,
            "uuid": proxy.uuid.clone().unwrap_or_default(),
            "flow": proxy.flow.clone().unwrap_or_default(),
            "tls": if proxy.tls.is_some() {
                Some(json!({
                    "enabled": true,
                    "server_name": proxy.sni.clone().unwrap_or_default(),
                    "utls": {
                        "enabled": true,
                        "fingerprint": proxy.fingerprint.clone().unwrap_or("chrome".to_string())
                    },
                    "reality": if proxy.tls.as_deref() == Some("reality") {
                        Some(json!({
                            "enabled": true,
                            "public_key": proxy.public_key.clone().unwrap_or_default(),
                            "short_id": proxy.short_id.clone().unwrap_or_default()
                        }))
                    } else {
                        None
                    }
                }))
            } else {
                None
            }
        }),
        json!({
            "type": "direct",
            "tag": "direct"
        }),
        json!({
            "type": "block",
            "tag": "block"
        }),
        json!({
            "type": "dns",
            "tag": "dns-out"
        })
    ];

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
            "stack": "system",
            "sniff": true,
            "sniff_override_destination": true
        }));
    }

    json!({
        "log": {
            "level": "info",
            "timestamp": true
        },
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
            "rules": [
                {
                    "protocol": "dns",
                    "outbound": "dns-out"
                },
                {
                    "ip_is_private": true,
                    "outbound": "direct"
                }
            ],
            "final": "proxy",
            "auto_detect_interface": true
        }
    })
}
