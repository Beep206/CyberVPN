use crate::engine::error::AppError;
use crate::engine::parser::{classify_vless_transport, validated_xhttp_mode, VlessTransportKind};
use crate::engine::store::AppDataStore;
use crate::ipc::models::{CreateSubscription, ProxyNode, Subscription};
use base64::prelude::*;
use futures::StreamExt;
use keyring::Entry;
use std::net::{IpAddr, Ipv4Addr, Ipv6Addr, SocketAddr};
use std::time::Duration;
use url::{Host, Url};

const MAX_SUBSCRIPTION_BODY_BYTES: usize = 4 * 1024 * 1024;
const MAX_SUBSCRIPTION_NODES: usize = 1024;
const MAX_SUBSCRIPTIONS: usize = 64;
const MAX_SUBSCRIPTION_NAME_CHARS: usize = 128;
const MAX_SUBSCRIPTION_URL_BYTES: usize = 2048;
const SUBSCRIPTION_KEYRING_SERVICE: &str = "CyberVPN_Subscriptions";

#[derive(Debug, Clone)]
enum SubscriptionHost {
    Domain(String),
    Ip,
}

fn is_public_ipv4(address: Ipv4Addr) -> bool {
    let [first, second, third, _fourth] = address.octets();

    !(first == 0
        || first == 10
        || first == 127
        || (first == 100 && (64..=127).contains(&second))
        || (first == 169 && second == 254)
        || (first == 172 && (16..=31).contains(&second))
        || (first == 192 && second == 0 && third == 0)
        || (first == 192 && second == 0 && third == 2)
        || (first == 192 && second == 88 && third == 99)
        || (first == 192 && second == 168)
        || (first == 198 && (second == 18 || second == 19))
        || (first == 198 && second == 51 && third == 100)
        || (first == 203 && second == 0 && third == 113)
        || first >= 224)
}

fn is_public_ipv6(address: Ipv6Addr) -> bool {
    if let Some(mapped) = address.to_ipv4_mapped() {
        return is_public_ipv4(mapped);
    }

    let octets = address.octets();
    let transition_or_translation =
        // Deprecated IPv4-compatible and IPv4-translatable forms.
        octets[..12] == [0_u8; 12]
        || (octets[..8] == [0_u8; 8] && octets[8..12] == [0xff, 0xff, 0, 0])
        // RFC 6052 well-known and RFC 8215 local-use NAT64 prefixes.
        || octets[..12] == [0, 0x64, 0xff, 0x9b, 0, 0, 0, 0, 0, 0, 0, 0]
        || octets[..6] == [0, 0x64, 0xff, 0x9b, 0, 1]
        // 6to4 and the IANA special-purpose 2001::/23 block (including Teredo).
        || octets[..2] == [0x20, 0x02]
        || (octets[..2] == [0x20, 0x01] && octets[2] & 0xfe == 0)
        // ISATAP embeds IPv4 in the interface identifier under an arbitrary prefix.
        || octets[8..12] == [0, 0, 0x5e, 0xfe]
        || octets[8..12] == [0x02, 0, 0x5e, 0xfe];
    !(address.is_unspecified()
        || address.is_loopback()
        || address.is_multicast()
        || transition_or_translation
        || (octets[0] & 0xfe) == 0xfc
        || octets[0] == 0xfe
        || octets[..4] == [0x20, 0x01, 0x0d, 0xb8]
        || octets[..8] == [0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        || (octets[..3] == [0x20, 0x01, 0x00] && (octets[3] & 0xf0) == 0x20))
}

fn is_public_ip(address: IpAddr) -> bool {
    match address {
        IpAddr::V4(address) => is_public_ipv4(address),
        IpAddr::V6(address) => is_public_ipv6(address),
    }
}

fn parse_subscription_url(url: &str) -> Result<(Url, SubscriptionHost, u16), AppError> {
    let parsed =
        Url::parse(url).map_err(|_| AppError::System("Subscription URL is invalid".to_string()))?;
    if parsed.scheme() != "https" {
        return Err(AppError::System(
            "Subscription URL must use HTTPS".to_string(),
        ));
    }
    if !parsed.username().is_empty() || parsed.password().is_some() {
        return Err(AppError::System(
            "Subscription URL must not contain user information".to_string(),
        ));
    }

    let host = match parsed.host() {
        Some(Host::Domain(domain)) => {
            let normalized = domain.trim_end_matches('.').to_ascii_lowercase();
            if normalized == "localhost"
                || normalized.ends_with(".localhost")
                || normalized.ends_with(".local")
                || normalized.ends_with(".internal")
                || normalized == "home.arpa"
                || normalized.ends_with(".home.arpa")
            {
                return Err(AppError::System(
                    "Subscription destination is not public".to_string(),
                ));
            }
            SubscriptionHost::Domain(domain.to_string())
        }
        Some(Host::Ipv4(address)) => {
            if !is_public_ipv4(address) {
                return Err(AppError::System(
                    "Subscription destination is not public".to_string(),
                ));
            }
            SubscriptionHost::Ip
        }
        Some(Host::Ipv6(address)) => {
            if !is_public_ipv6(address) {
                return Err(AppError::System(
                    "Subscription destination is not public".to_string(),
                ));
            }
            SubscriptionHost::Ip
        }
        None => {
            return Err(AppError::System(
                "Subscription URL must contain a host".to_string(),
            ))
        }
    };
    let port = parsed
        .port_or_known_default()
        .ok_or_else(|| AppError::System("Subscription URL has no valid port".to_string()))?;

    Ok((parsed, host, port))
}

pub(crate) fn validate_subscription_id(id: &str) -> Result<uuid::Uuid, AppError> {
    let parsed_id = uuid::Uuid::parse_str(id)
        .map_err(|_| AppError::System("Subscription ID must be a UUID".to_string()))?;
    if id != parsed_id.hyphenated().to_string() {
        return Err(AppError::System(
            "Subscription ID must use canonical UUID format".to_string(),
        ));
    }
    Ok(parsed_id)
}

pub(crate) fn validate_subscription_url_for_storage(url: &str) -> Result<(), AppError> {
    if url.is_empty() || url.len() > MAX_SUBSCRIPTION_URL_BYTES {
        return Err(AppError::System(format!(
            "Subscription URL must contain at most {MAX_SUBSCRIPTION_URL_BYTES} bytes"
        )));
    }
    parse_subscription_url(url).map(|_| ())
}

fn subscription_url_entry(subscription_id: &str) -> Result<Entry, AppError> {
    validate_subscription_id(subscription_id)?;
    Entry::new(SUBSCRIPTION_KEYRING_SERVICE, subscription_id)
        .map_err(|_| AppError::System("Unable to access secure subscription storage".to_string()))
}

pub(crate) fn store_subscription_url(subscription_id: &str, url: &str) -> Result<(), AppError> {
    validate_subscription_url_for_storage(url)?;
    subscription_url_entry(subscription_id)?
        .set_secret(url.as_bytes())
        .map_err(|_| {
            AppError::System("Unable to save the subscription credential securely".to_string())
        })
}

pub(crate) fn load_subscription_url(subscription_id: &str) -> Result<String, AppError> {
    let secret = subscription_url_entry(subscription_id)?
        .get_secret()
        .map_err(|_| AppError::System("The subscription credential is unavailable".to_string()))?;
    let url = String::from_utf8(secret).map_err(|_| {
        AppError::System("The stored subscription credential is invalid".to_string())
    })?;
    validate_subscription_url_for_storage(&url).map_err(|_| {
        AppError::System("The stored subscription credential is invalid".to_string())
    })?;
    Ok(url)
}

pub(crate) fn delete_subscription_url(subscription_id: &str) -> Result<(), AppError> {
    match subscription_url_entry(subscription_id)?.delete_credential() {
        Ok(()) | Err(keyring::Error::NoEntry) => Ok(()),
        Err(_) => Err(AppError::System(
            "Unable to delete the subscription credential securely".to_string(),
        )),
    }
}

pub(crate) fn validate_new_subscription(
    subscription: &mut CreateSubscription,
    existing: &[Subscription],
) -> Result<(), AppError> {
    let parsed_id = validate_subscription_id(&subscription.id)?;
    let canonical_id = parsed_id.hyphenated().to_string();
    if existing.iter().any(|stored| {
        stored.id == canonical_id
            || uuid::Uuid::parse_str(&stored.id).is_ok_and(|stored_id| stored_id == parsed_id)
    }) {
        return Err(AppError::System(
            "A subscription with this ID already exists".to_string(),
        ));
    }
    if existing.len() >= MAX_SUBSCRIPTIONS {
        return Err(AppError::System(format!(
            "At most {MAX_SUBSCRIPTIONS} subscriptions may be stored"
        )));
    }

    let name = subscription.name.trim();
    if name.is_empty()
        || name.chars().count() > MAX_SUBSCRIPTION_NAME_CHARS
        || name.chars().any(char::is_control)
    {
        return Err(AppError::System(format!(
            "Subscription name must contain 1 to {MAX_SUBSCRIPTION_NAME_CHARS} printable characters"
        )));
    }
    subscription.name = name.to_string();

    validate_subscription_url_for_storage(&subscription.url)
}

fn validate_resolved_addresses(addresses: &[SocketAddr]) -> Result<SocketAddr, AppError> {
    if addresses.is_empty() || addresses.iter().any(|address| !is_public_ip(address.ip())) {
        return Err(AppError::System(
            "Subscription destination did not resolve exclusively to public addresses".to_string(),
        ));
    }

    addresses
        .iter()
        .copied()
        .min_by_key(|address| (address.is_ipv6(), address.ip().to_string(), address.port()))
        .ok_or_else(|| {
            AppError::System("Subscription destination could not be resolved".to_string())
        })
}

fn validate_response_status(status: reqwest::StatusCode) -> Result<(), AppError> {
    if status.is_redirection() {
        return Err(AppError::System(
            "Subscription redirects are not allowed".to_string(),
        ));
    }
    if !status.is_success() {
        return Err(AppError::System(format!(
            "Subscription fetch failed with status: {status}"
        )));
    }
    Ok(())
}

fn validate_content_length(content_length: Option<u64>) -> Result<(), AppError> {
    if content_length.is_some_and(|length| length > MAX_SUBSCRIPTION_BODY_BYTES as u64) {
        return Err(AppError::System(
            "Subscription response exceeds the 4 MiB limit".to_string(),
        ));
    }
    Ok(())
}

fn append_bounded_chunk(body: &mut Vec<u8>, chunk: &[u8]) -> Result<(), AppError> {
    if body.len().saturating_add(chunk.len()) > MAX_SUBSCRIPTION_BODY_BYTES {
        return Err(AppError::System(
            "Subscription response exceeds the 4 MiB limit".to_string(),
        ));
    }
    body.extend_from_slice(chunk);
    Ok(())
}

fn yaml_string(value: &serde_yaml::Value, key: &str) -> Option<String> {
    value
        .get(key)
        .and_then(serde_yaml::Value::as_str)
        .map(ToString::to_string)
}

fn parse_clash_proxy(proxy: &serde_yaml::Value) -> Option<ProxyNode> {
    let name = yaml_string(proxy, "name").unwrap_or_else(|| "Imported Clash Node".to_string());
    let server = yaml_string(proxy, "server")?;
    let port = proxy.get("port")?.as_u64()?;
    let port = u16::try_from(port).ok().filter(|port| *port > 0)?;
    let protocol = yaml_string(proxy, "type")?;

    if server.is_empty() {
        return None;
    }

    match protocol.as_str() {
        "vless" | "vmess" | "trojan" | "ss" | "shadowsocks" => {}
        _ => return None,
    }

    let proto_mapped = if protocol == "ss" {
        "shadowsocks".to_string()
    } else {
        protocol.clone()
    };
    let password = yaml_string(proxy, "password");
    let uuid = yaml_string(proxy, "uuid");
    let mut network = yaml_string(proxy, "network").map(|value| value.to_ascii_lowercase());
    let mut flow = yaml_string(proxy, "flow");
    let mut transport_path = None;
    let mut transport_host = None;
    let mut xhttp_mode = None;

    if protocol == "vless" {
        let transport_kind = classify_vless_transport(network.as_deref()).ok()?;
        if transport_kind == VlessTransportKind::Xhttp {
            let xhttp_options = proxy.get("xhttp-opts");
            transport_path = xhttp_options.and_then(|value| yaml_string(value, "path"));
            transport_host = xhttp_options.and_then(|value| yaml_string(value, "host"));
            xhttp_mode =
                validated_xhttp_mode(xhttp_options.and_then(|value| yaml_string(value, "mode")))
                    .ok()?;
            // Vision is a TCP/RAW flow. Mihomo and Xray XHTTP configs omit it.
            flow = None;
        } else {
            if proxy.get("xhttp-opts").is_some() {
                return None;
            }
            if transport_kind != VlessTransportKind::Raw {
                flow = None;
            } else if flow
                .as_deref()
                .is_some_and(|value| !value.is_empty() && value != "xtls-rprx-vision")
            {
                return None;
            }
        }
    } else {
        network = network.filter(|value| !value.is_empty());
    }

    let reality_options = proxy.get("reality-opts");
    let tls_enabled = proxy.get("tls").and_then(serde_yaml::Value::as_bool);
    if reality_options.is_some() && tls_enabled == Some(false) {
        return None;
    }
    let tls = if reality_options.is_some() {
        Some("reality".to_string())
    } else if tls_enabled == Some(true) {
        Some("tls".to_string())
    } else {
        None
    };

    let sni = yaml_string(proxy, "servername").or_else(|| yaml_string(proxy, "sni"));
    let fingerprint =
        yaml_string(proxy, "client-fingerprint").or_else(|| yaml_string(proxy, "fingerprint"));
    let public_key = reality_options.and_then(|value| yaml_string(value, "public-key"));
    let short_id = reality_options.and_then(|value| yaml_string(value, "short-id"));
    if tls.as_deref() == Some("reality")
        && (sni.as_deref().is_none_or(str::is_empty)
            || public_key.as_deref().is_none_or(str::is_empty))
    {
        return None;
    }

    Some(ProxyNode {
        id: uuid::Uuid::new_v4().to_string(),
        name,
        server,
        port,
        protocol: proto_mapped,
        uuid,
        password,
        network,
        transport_path,
        transport_host,
        xhttp_mode,
        flow,
        tls,
        sni,
        fingerprint,
        public_key,
        short_id,
        alter_id: proxy
            .get("alterId")
            .and_then(serde_yaml::Value::as_u64)
            .and_then(|value| u16::try_from(value).ok()),
        method: yaml_string(proxy, "cipher"),
        ..Default::default()
    })
}

pub(crate) fn parse_subscription_body(body: &str) -> Result<Vec<ProxyNode>, AppError> {
    if let Ok(yaml_value) = serde_yaml::from_str::<serde_yaml::Value>(body) {
        if let Some(proxies) = yaml_value
            .get("proxies")
            .and_then(serde_yaml::Value::as_sequence)
        {
            let nodes: Vec<_> = proxies
                .iter()
                .filter_map(parse_clash_proxy)
                .take(MAX_SUBSCRIPTION_NODES + 1)
                .collect();
            if nodes.len() > MAX_SUBSCRIPTION_NODES {
                return Err(AppError::System(format!(
                    "Subscription contains more than {MAX_SUBSCRIPTION_NODES} valid proxy nodes"
                )));
            }
            if !nodes.is_empty() {
                return Ok(nodes);
            }
        }
    }

    let decoded_body = match BASE64_URL_SAFE_NO_PAD
        .decode(body.trim())
        .or_else(|_| BASE64_URL_SAFE.decode(body.trim()))
        .or_else(|_| BASE64_STANDARD_NO_PAD.decode(body.trim()))
        .or_else(|_| BASE64_STANDARD.decode(body.trim()))
    {
        Ok(bytes) => String::from_utf8(bytes).map_err(|error| {
            AppError::System(format!("Subscription base64 payload is not UTF-8: {error}"))
        })?,
        Err(_) => body.to_string(),
    };

    let nodes: Vec<_> = decoded_body
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty())
        .filter_map(|line| crate::engine::parser::parse_link(line).ok())
        .take(MAX_SUBSCRIPTION_NODES + 1)
        .collect();
    if nodes.len() > MAX_SUBSCRIPTION_NODES {
        return Err(AppError::System(format!(
            "Subscription contains more than {MAX_SUBSCRIPTION_NODES} valid proxy nodes"
        )));
    }
    if nodes.is_empty() {
        return Err(AppError::System(
            "Subscription did not contain any valid proxy nodes".to_string(),
        ));
    }

    Ok(nodes)
}

pub async fn fetch_and_parse_subscription(url: &str) -> Result<Vec<ProxyNode>, AppError> {
    let (parsed_url, host, port) = parse_subscription_url(url)?;
    let mut client_builder = reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .connect_timeout(Duration::from_secs(5))
        .redirect(reqwest::redirect::Policy::none())
        .no_proxy();

    if let SubscriptionHost::Domain(domain) = &host {
        let resolved: Vec<_> = tokio::net::lookup_host((domain.as_str(), port))
            .await
            .map_err(|_| {
                AppError::System("Subscription destination could not be resolved".to_string())
            })?
            .collect();
        let pinned_address = validate_resolved_addresses(&resolved)?;
        client_builder = client_builder.resolve(domain, pinned_address);
    }

    let client = client_builder
        .build()
        .map_err(|e| AppError::System(format!("Failed to build HTTP client: {e}")))?;

    let response = client
        .get(parsed_url)
        .send()
        .await
        .map_err(|_| AppError::System("Failed to fetch subscription".to_string()))?;

    validate_response_status(response.status())?;
    validate_content_length(response.content_length())?;
    let mut body = Vec::with_capacity(
        response
            .content_length()
            .unwrap_or_default()
            .min(MAX_SUBSCRIPTION_BODY_BYTES as u64) as usize,
    );
    let mut chunks = response.bytes_stream();
    while let Some(chunk) = chunks.next().await {
        let chunk =
            chunk.map_err(|_| AppError::System("Failed to read subscription body".to_string()))?;
        append_bounded_chunk(&mut body, &chunk)?;
    }
    let body = String::from_utf8(body).map_err(|_| {
        AppError::System("Subscription response body is not valid UTF-8".to_string())
    })?;

    parse_subscription_body(&body)
}

pub(crate) fn apply_subscription_update(
    store_data: &mut AppDataStore,
    subscription_id: &str,
    mut new_nodes: Vec<ProxyNode>,
    updated_at: u64,
) -> Result<(), AppError> {
    if new_nodes.is_empty() {
        return Err(AppError::System(
            "Subscription update contained no valid proxy nodes".to_string(),
        ));
    }
    if !store_data
        .subscriptions
        .iter()
        .any(|subscription| subscription.id == subscription_id)
    {
        return Err(AppError::System("Subscription not found".to_string()));
    }

    for node in &mut new_nodes {
        node.subscription_id = Some(subscription_id.to_string());
    }
    store_data
        .profiles
        .retain(|profile| profile.subscription_id.as_deref() != Some(subscription_id));
    store_data.profiles.extend(new_nodes);
    if let Some(subscription) = store_data
        .subscriptions
        .iter_mut()
        .find(|subscription| subscription.id == subscription_id)
    {
        subscription.last_updated = Some(updated_at);
    }

    Ok(())
}

pub(crate) fn apply_fetched_subscription_update(
    store_data: &mut AppDataStore,
    subscription_id: &str,
    expected_url: &str,
    current_url: &str,
    new_nodes: Vec<ProxyNode>,
    updated_at: u64,
) -> Result<(), AppError> {
    store_data
        .subscriptions
        .iter()
        .find(|subscription| subscription.id == subscription_id)
        .ok_or_else(|| AppError::System("Subscription was removed during refresh".to_string()))?;
    if current_url != expected_url {
        return Err(AppError::System(
            "Subscription changed during refresh; retry with the current URL".to_string(),
        ));
    }
    apply_subscription_update(store_data, subscription_id, new_nodes, updated_at)
}

#[cfg(test)]
mod tests {
    use super::*;

    const RAW_LINK: &str = "vless://b831381d-6324-4d53-ad4f-8cda48b30811@raw.example:443?security=reality&type=raw&flow=xtls-rprx-vision&sni=cover.example&fp=chrome&pbk=public-test&sid=abcd#RAW";

    fn create_subscription(id: &str) -> CreateSubscription {
        CreateSubscription {
            id: id.to_string(),
            name: " Primary ".to_string(),
            url: "https://203.0.114.1/sub".to_string(),
            auto_update: true,
        }
    }

    #[test]
    fn parses_raw_standard_and_url_safe_base64_subscriptions() {
        for body in [
            RAW_LINK.to_string(),
            BASE64_STANDARD.encode(RAW_LINK),
            BASE64_URL_SAFE_NO_PAD.encode(RAW_LINK),
        ] {
            let nodes = parse_subscription_body(&body).expect("subscription should parse");
            assert_eq!(nodes.len(), 1);
            assert_eq!(nodes[0].network.as_deref(), Some("raw"));
            assert_eq!(nodes[0].flow.as_deref(), Some("xtls-rprx-vision"));
        }
    }

    #[test]
    fn rejects_subscriptions_above_the_valid_node_limit() {
        let body = std::iter::repeat_n(RAW_LINK, MAX_SUBSCRIPTION_NODES + 1)
            .collect::<Vec<_>>()
            .join("\n");
        let error = parse_subscription_body(&body)
            .expect_err("oversized valid-node collections must fail closed");
        assert!(error
            .to_string()
            .contains(&MAX_SUBSCRIPTION_NODES.to_string()));
    }

    #[test]
    fn clash_xhttp_preserves_transport_and_reality_but_drops_vision_flow() {
        let yaml = r#"
proxies:
  - name: XHTTP
    type: vless
    server: xhttp.example
    port: 8443
    uuid: b831381d-6324-4d53-ad4f-8cda48b30811
    network: xhttp
    flow: xtls-rprx-vision
    tls: true
    servername: cover.example
    client-fingerprint: chrome
    reality-opts:
      public-key: public-test
      short-id: abcd
    xhttp-opts:
      path: /api/v3
      host: cdn.example
      mode: packet-up
"#;

        let nodes = parse_subscription_body(yaml).expect("Clash subscription should parse");
        assert_eq!(nodes.len(), 1);
        let node = &nodes[0];
        assert_eq!(node.network.as_deref(), Some("xhttp"));
        assert_eq!(node.transport_path.as_deref(), Some("/api/v3"));
        assert_eq!(node.transport_host.as_deref(), Some("cdn.example"));
        assert_eq!(node.xhttp_mode.as_deref(), Some("packet-up"));
        assert_eq!(node.flow, None);
        assert_eq!(node.tls.as_deref(), Some("reality"));
        assert_eq!(node.sni.as_deref(), Some("cover.example"));
        assert_eq!(node.public_key.as_deref(), Some("public-test"));
        assert_eq!(node.short_id.as_deref(), Some("abcd"));
    }

    #[test]
    fn clash_unknown_transport_and_xhttp_mode_fail_closed() {
        for yaml in [
            "proxies:\n  - {name: Bad, type: vless, server: bad.example, port: 443, uuid: id, network: magic}\n",
            "proxies:\n  - name: Bad\n    type: vless\n    server: bad.example\n    port: 443\n    uuid: id\n    network: xhttp\n    xhttp-opts: {mode: unsafe}\n",
        ] {
            let error = parse_subscription_body(yaml)
                .expect_err("a subscription with zero valid entries must fail closed");
            assert!(error.to_string().contains("did not contain any valid proxy nodes"));
        }
    }

    #[test]
    fn rejects_local_private_and_credentialed_subscription_urls() {
        for url in [
            "http://localhost/sub",
            "http://127.0.0.1/sub",
            "http://10.0.0.1/sub",
            "http://169.254.169.254/latest/meta-data",
            "http://[::1]/sub",
            "http://203.0.114.1/sub",
            "https://user:password@203.0.114.1/sub",
            "file:///etc/passwd",
        ] {
            assert!(
                parse_subscription_url(url).is_err(),
                "{url} must be rejected"
            );
        }
        assert!(parse_subscription_url("https://203.0.114.1/sub").is_ok());
    }

    #[test]
    fn rejects_dns_results_when_any_destination_is_not_public() {
        let mixed = [
            SocketAddr::from(([203, 0, 114, 1], 443)),
            SocketAddr::from(([10, 0, 0, 1], 443)),
        ];
        assert!(validate_resolved_addresses(&mixed).is_err());
        assert!(validate_resolved_addresses(&[SocketAddr::from(([203, 0, 114, 1], 443,))]).is_ok());
    }

    #[test]
    fn ipv6_transition_and_translation_destinations_fail_closed() {
        for address in [
            "::a00:1",
            "::ffff:0:a00:1",
            "64:ff9b::a00:1",
            "64:ff9b:1::a00:1",
            "2002:a00:1::",
            "2001:0:4136:e378:8000:63bf:f5ff:fffe",
            "2001:2::1",
            "2606:4700:4700:0:0:5efe:a00:1",
        ] {
            let address = address.parse::<Ipv6Addr>().expect("fixture must parse");
            assert!(!is_public_ipv6(address), "{address} must fail closed");
        }

        assert!(is_public_ipv6(
            "2606:4700:4700::1111"
                .parse()
                .expect("public IPv6 fixture must parse")
        ));
        assert!(is_public_ipv6(
            "::ffff:203.0.114.1"
                .parse()
                .expect("public mapped IPv4 fixture must parse")
        ));
        assert!(!is_public_ipv6(
            "::ffff:10.0.0.1"
                .parse()
                .expect("private mapped IPv4 fixture must parse")
        ));
    }

    #[test]
    fn rejects_redirects_and_oversized_response_bodies() {
        assert!(validate_response_status(reqwest::StatusCode::FOUND).is_err());
        assert!(validate_response_status(reqwest::StatusCode::OK).is_ok());
        assert!(validate_content_length(Some((MAX_SUBSCRIPTION_BODY_BYTES + 1) as u64)).is_err());

        let mut body = vec![0; MAX_SUBSCRIPTION_BODY_BYTES];
        assert!(append_bounded_chunk(&mut body, &[1]).is_err());
        assert_eq!(body.len(), MAX_SUBSCRIPTION_BODY_BYTES);
    }

    #[test]
    fn new_subscription_validation_enforces_canonical_bounded_unique_input() {
        let canonical_id = "b831381d-6324-4d53-ad4f-8cda48b30811";
        let mut valid = create_subscription(canonical_id);
        validate_new_subscription(&mut valid, &[]).expect("valid input must pass");
        assert_eq!(valid.name, "Primary");

        for mut invalid in [
            create_subscription("not-a-uuid"),
            create_subscription("B831381D-6324-4D53-AD4F-8CDA48B30811"),
        ] {
            assert!(validate_new_subscription(&mut invalid, &[]).is_err());
        }

        let mut empty_name = create_subscription(canonical_id);
        empty_name.name = "   ".to_string();
        assert!(validate_new_subscription(&mut empty_name, &[]).is_err());
        let mut long_name = create_subscription(canonical_id);
        long_name.name = "n".repeat(MAX_SUBSCRIPTION_NAME_CHARS + 1);
        assert!(validate_new_subscription(&mut long_name, &[]).is_err());
        let mut control_name = create_subscription(canonical_id);
        control_name.name = "unsafe\nname".to_string();
        assert!(validate_new_subscription(&mut control_name, &[]).is_err());

        let mut long_url = create_subscription(canonical_id);
        long_url.url = format!(
            "https://203.0.114.1/{}",
            "a".repeat(MAX_SUBSCRIPTION_URL_BYTES)
        );
        assert!(validate_new_subscription(&mut long_url, &[]).is_err());
        let mut private_url = create_subscription(canonical_id);
        private_url.url = "http://127.0.0.1/sub".to_string();
        assert!(validate_new_subscription(&mut private_url, &[]).is_err());

        let existing = vec![Subscription {
            id: canonical_id.to_string(),
            name: "Existing".to_string(),
            legacy_url: None,
            auto_update: true,
            last_updated: None,
        }];
        let mut duplicate = create_subscription(canonical_id);
        assert!(validate_new_subscription(&mut duplicate, &existing).is_err());

        let full: Vec<_> = (1..=MAX_SUBSCRIPTIONS)
            .map(|index| Subscription {
                id: uuid::Uuid::from_u128(index as u128)
                    .hyphenated()
                    .to_string(),
                name: format!("Subscription {index}"),
                legacy_url: None,
                auto_update: true,
                last_updated: None,
            })
            .collect();
        let mut over_limit = create_subscription(canonical_id);
        assert!(validate_new_subscription(&mut over_limit, &full).is_err());
    }

    #[test]
    fn empty_update_preserves_known_good_profiles_and_timestamp() {
        let mut store_data = AppDataStore::default();
        store_data
            .subscriptions
            .push(crate::ipc::models::Subscription {
                id: "sub-1".to_string(),
                name: "Primary".to_string(),
                legacy_url: None,
                auto_update: true,
                last_updated: Some(42),
            });
        store_data.profiles.push(ProxyNode {
            id: "known-good".to_string(),
            name: "Known good".to_string(),
            server: "vpn.example".to_string(),
            port: 443,
            protocol: "vless".to_string(),
            subscription_id: Some("sub-1".to_string()),
            ..Default::default()
        });

        let error = apply_subscription_update(&mut store_data, "sub-1", Vec::new(), 100)
            .expect_err("empty updates must fail before mutating stored state");

        assert!(error.to_string().contains("no valid proxy nodes"));
        assert_eq!(store_data.profiles.len(), 1);
        assert_eq!(store_data.profiles[0].id, "known-good");
        assert_eq!(store_data.subscriptions[0].last_updated, Some(42));
    }

    #[test]
    fn post_fetch_reload_preserves_concurrent_store_changes_and_checks_url_identity() {
        let expected_url = "https://203.0.114.1/sub";
        let mut latest = AppDataStore {
            smart_connect_enabled: true,
            ..Default::default()
        };
        latest.subscriptions.push(Subscription {
            id: "refresh-target".to_string(),
            name: "Target".to_string(),
            legacy_url: None,
            auto_update: true,
            last_updated: Some(10),
        });
        latest.subscriptions.push(Subscription {
            id: "concurrent-add".to_string(),
            name: "Added while fetching".to_string(),
            legacy_url: None,
            auto_update: true,
            last_updated: None,
        });
        latest.profiles.push(ProxyNode {
            id: "concurrent-profile".to_string(),
            name: "Concurrent profile".to_string(),
            server: "vpn.example".to_string(),
            port: 443,
            protocol: "vless".to_string(),
            ..Default::default()
        });
        let refreshed = ProxyNode {
            id: "refreshed".to_string(),
            name: "Refreshed".to_string(),
            server: "vpn-2.example".to_string(),
            port: 443,
            protocol: "vless".to_string(),
            ..Default::default()
        };

        apply_fetched_subscription_update(
            &mut latest,
            "refresh-target",
            expected_url,
            expected_url,
            vec![refreshed],
            99,
        )
        .expect("refresh should apply to the latest store snapshot");
        assert!(latest.smart_connect_enabled);
        assert_eq!(latest.subscriptions.len(), 2);
        assert!(latest
            .profiles
            .iter()
            .any(|profile| profile.id == "concurrent-profile"));
        assert!(latest.profiles.iter().any(|profile| {
            profile.id == "refreshed"
                && profile.subscription_id.as_deref() == Some("refresh-target")
        }));
        assert_eq!(latest.subscriptions[0].last_updated, Some(99));

        let profile_count = latest.profiles.len();
        let error = apply_fetched_subscription_update(
            &mut latest,
            "refresh-target",
            expected_url,
            "https://203.0.114.1/replaced",
            vec![ProxyNode::default()],
            100,
        )
        .expect_err("a URL change during fetch must require a retry");
        assert!(error.to_string().contains("changed during refresh"));
        assert_eq!(latest.profiles.len(), profile_count);
        assert_eq!(latest.subscriptions[0].last_updated, Some(99));
    }

    #[cfg(target_os = "windows")]
    #[test]
    fn native_windows_keyring_process_helper() {
        let Ok(action) = std::env::var("CYBERVPN_KEYRING_PROBE_ACTION") else {
            return;
        };
        let subscription_id = std::env::var("CYBERVPN_KEYRING_PROBE_ID")
            .expect("probe subscription ID must be supplied");
        let expected_url = "https://203.0.114.1/synthetic-keyring-probe";

        match action.as_str() {
            "write" => store_subscription_url(&subscription_id, expected_url)
                .expect("native keyring write must succeed"),
            "read" => assert_eq!(
                load_subscription_url(&subscription_id)
                    .expect("credential written by another process must persist"),
                expected_url
            ),
            "delete" => delete_subscription_url(&subscription_id)
                .expect("native keyring delete must succeed"),
            "verify-missing" => assert!(
                load_subscription_url(&subscription_id).is_err(),
                "deleted credential must not remain readable"
            ),
            _ => panic!("unsupported keyring probe action"),
        }
    }

    #[cfg(target_os = "windows")]
    #[test]
    fn native_windows_keyring_persists_across_processes_and_deletes() {
        struct CredentialCleanup(String);
        impl Drop for CredentialCleanup {
            fn drop(&mut self) {
                let _ = delete_subscription_url(&self.0);
            }
        }

        let subscription_id = uuid::Uuid::new_v4().hyphenated().to_string();
        let _cleanup = CredentialCleanup(subscription_id.clone());
        let current_test_executable =
            std::env::current_exe().expect("current test executable must be available");

        for action in ["write", "read", "delete", "verify-missing"] {
            let status = std::process::Command::new(&current_test_executable)
                .arg("--exact")
                .arg("engine::subscription::tests::native_windows_keyring_process_helper")
                .arg("--nocapture")
                .env("CYBERVPN_KEYRING_PROBE_ACTION", action)
                .env("CYBERVPN_KEYRING_PROBE_ID", &subscription_id)
                .status()
                .expect("native keyring probe child process must launch");
            assert!(status.success(), "native keyring {action} probe failed");
        }
    }
}
