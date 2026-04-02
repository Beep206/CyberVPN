use sysproxy::Sysproxy;

fn apply_system_proxy(host: String, port: u16) -> Result<(), String> {
    let proxy = Sysproxy {
        enable: true,
        host,
        port,
        bypass: "localhost;127.*;10.*;172.16.*;172.17.*;172.18.*;172.19.*;172.20.*;172.21.*;172.22.*;172.23.*;172.24.*;172.25.*;172.26.*;172.27.*;172.28.*;172.29.*;172.30.*;172.31.*;192.168.*".to_string(),
    };
    proxy.set_system_proxy().map_err(|e| e.to_string())
}

pub fn set_system_proxy(port: u16) -> Result<(), String> {
    apply_system_proxy("127.0.0.1".to_string(), port)
}

pub fn set_system_proxy_from_url(proxy_url: &str) -> Result<(), String> {
    let parsed = url::Url::parse(proxy_url).map_err(|error| error.to_string())?;
    let host = parsed
        .host_str()
        .ok_or_else(|| "Proxy URL does not include a host".to_string())?
        .to_string();
    let port = parsed
        .port_or_known_default()
        .ok_or_else(|| "Proxy URL does not include a port".to_string())?;
    apply_system_proxy(host, port)
}

pub fn clear_system_proxy() -> Result<(), String> {
    let proxy = Sysproxy {
        enable: false,
        host: "127.0.0.1".to_string(),
        port: 0,
        bypass: "".to_string(),
    };
    proxy.set_system_proxy().map_err(|e| e.to_string())
}
