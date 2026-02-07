/// Supported VPN protocols.
///
/// Extracted to `core/domain/` to break the circular dependency between
/// the `vpn` and `servers` features — both need to reference this enum
/// without importing each other.
enum VpnProtocol { vless, vmess, trojan, shadowsocks }
