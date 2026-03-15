use crate::ipc::models::ProxyNode;
use crate::engine::error::AppError;
use url::Url;

pub fn parse_vless(link: &str) -> Result<ProxyNode, AppError> {
    let parsed_url = Url::parse(link).map_err(|e| AppError::System(format!("Invalid URL: {}", e)))?;
    
    if parsed_url.scheme() != "vless" {
        return Err(AppError::System("Not a vless link".to_string()));
    }

    let uuid = parsed_url.username().to_string();
    if uuid.is_empty() {
        return Err(AppError::System("VLESS link missing UUID".to_string()));
    }

    let host = parsed_url.host_str().ok_or_else(|| AppError::System("VLESS link missing host".to_string()))?.to_string();
    let port = parsed_url.port().unwrap_or(443);

    let name = if let Some(fragment) = parsed_url.fragment() {
        // Simple URL decode for the name (fragment)
        urlencoding::decode(fragment)
            .unwrap_or(std::borrow::Cow::Borrowed("Imported VLESS"))
            .into_owned()
    } else {
        format!("VLESS {}", host)
    };

    // Parse query string parameters safely
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
        id: uuid::Uuid::new_v4().to_string(), // Generate unique ID for the store
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
    })
}

pub fn parse_link(link: &str) -> Result<ProxyNode, AppError> {
    let trimmed = link.trim();
    if trimmed.starts_with("vless://") {
        parse_vless(trimmed)
    } else {
        Err(AppError::System("Unsupported protocol/link format. Currently only vless:// is supported in this example.".to_string()))
    }
}
