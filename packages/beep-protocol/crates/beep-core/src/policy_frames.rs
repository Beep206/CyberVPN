//! Policy frame wire formats for node→client configuration pushes.
//!
//! Two frame types are defined:
//! - `ROUTE_SET` (0x60): Routing table entries the client should apply.
//! - `DNS_CONFIG` (0x62): DNS resolver configuration the client should use.

use crate::varint;

/// Action for a route entry.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum RouteAction {
    /// Route through the tunnel.
    Include = 0,
    /// Exclude from the tunnel (direct).
    Exclude = 1,
    /// Direct routing (bypass tunnel entirely).
    Direct = 2,
}

impl RouteAction {
    pub fn from_u8(v: u8) -> Option<Self> {
        match v {
            0 => Some(Self::Include),
            1 => Some(Self::Exclude),
            2 => Some(Self::Direct),
            _ => None,
        }
    }
}

/// A single route entry (prefix + action).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RouteEntry {
    /// Address family: 4 = IPv4, 6 = IPv6.
    pub family: u8,
    /// Prefix bytes (4 for IPv4, 16 for IPv6).
    pub prefix: Vec<u8>,
    /// Prefix length in bits.
    pub prefix_len: u8,
    /// Routing action.
    pub action: RouteAction,
}

/// `ROUTE_SET` frame payload.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RouteSetFrame {
    /// Replace existing routes (true) or append (false).
    pub replace: bool,
    /// Route entries.
    pub entries: Vec<RouteEntry>,
}

impl RouteSetFrame {
    pub fn encode(&self, buf: &mut Vec<u8>) {
        buf.push(if self.replace { 1 } else { 0 });
        let count = self.entries.len() as u16;
        buf.extend_from_slice(&count.to_be_bytes());
        for entry in &self.entries {
            buf.push(entry.family);
            buf.push(entry.prefix_len);
            buf.push(entry.action as u8);
            buf.extend_from_slice(&entry.prefix);
        }
    }

    pub fn decode(input: &[u8]) -> Result<Self, PolicyDecodeError> {
        if input.len() < 3 {
            return Err(PolicyDecodeError::Truncated);
        }
        let replace = input[0] != 0;
        let count = u16::from_be_bytes([input[1], input[2]]) as usize;
        let mut pos = 3;
        let mut entries = Vec::with_capacity(count);

        for _ in 0..count {
            if pos + 3 > input.len() {
                return Err(PolicyDecodeError::Truncated);
            }
            let family = input[pos];
            let prefix_len = input[pos + 1];
            let action_byte = input[pos + 2];
            pos += 3;

            let action = RouteAction::from_u8(action_byte)
                .ok_or(PolicyDecodeError::InvalidRouteAction(action_byte))?;

            let addr_len = match family {
                4 => 4,
                6 => 16,
                _ => return Err(PolicyDecodeError::InvalidAddressFamily(family)),
            };

            if pos + addr_len > input.len() {
                return Err(PolicyDecodeError::Truncated);
            }
            let prefix = input[pos..pos + addr_len].to_vec();
            pos += addr_len;

            entries.push(RouteEntry {
                family,
                prefix_len,
                action,
                prefix,
            });
        }

        Ok(RouteSetFrame { replace, entries })
    }
}

/// A DNS nameserver address.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum NameserverAddr {
    V4([u8; 4]),
    V6([u8; 16]),
}

/// `DNS_CONFIG` frame payload.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DnsConfigFrame {
    /// DNS nameservers.
    pub nameservers: Vec<NameserverAddr>,
    /// Search domains.
    pub search_domains: Vec<String>,
    /// TTL for this config in seconds.
    pub ttl_seconds: u32,
}

impl DnsConfigFrame {
    pub fn encode(&self, buf: &mut Vec<u8>) {
        // TTL
        buf.extend_from_slice(&self.ttl_seconds.to_be_bytes());

        // Nameservers
        let ns_count = self.nameservers.len() as u8;
        buf.push(ns_count);
        for ns in &self.nameservers {
            match ns {
                NameserverAddr::V4(addr) => {
                    buf.push(4);
                    buf.extend_from_slice(addr);
                }
                NameserverAddr::V6(addr) => {
                    buf.push(6);
                    buf.extend_from_slice(addr);
                }
            }
        }

        // Search domains
        let sd_count = self.search_domains.len() as u8;
        buf.push(sd_count);
        for domain in &self.search_domains {
            let _ = varint::encode(domain.len() as u64, buf);
            buf.extend_from_slice(domain.as_bytes());
        }
    }

    pub fn decode(input: &[u8]) -> Result<Self, PolicyDecodeError> {
        if input.len() < 6 {
            return Err(PolicyDecodeError::Truncated);
        }
        let ttl_seconds = u32::from_be_bytes(input[..4].try_into().unwrap());
        let mut pos = 4;

        let ns_count = input[pos] as usize;
        pos += 1;
        let mut nameservers = Vec::with_capacity(ns_count);
        for _ in 0..ns_count {
            if pos >= input.len() {
                return Err(PolicyDecodeError::Truncated);
            }
            let family = input[pos];
            pos += 1;
            match family {
                4 => {
                    if pos + 4 > input.len() {
                        return Err(PolicyDecodeError::Truncated);
                    }
                    let mut addr = [0u8; 4];
                    addr.copy_from_slice(&input[pos..pos + 4]);
                    nameservers.push(NameserverAddr::V4(addr));
                    pos += 4;
                }
                6 => {
                    if pos + 16 > input.len() {
                        return Err(PolicyDecodeError::Truncated);
                    }
                    let mut addr = [0u8; 16];
                    addr.copy_from_slice(&input[pos..pos + 16]);
                    nameservers.push(NameserverAddr::V6(addr));
                    pos += 16;
                }
                _ => return Err(PolicyDecodeError::InvalidAddressFamily(family)),
            }
        }

        if pos >= input.len() {
            return Err(PolicyDecodeError::Truncated);
        }
        let sd_count = input[pos] as usize;
        pos += 1;
        let mut search_domains = Vec::with_capacity(sd_count);
        for _ in 0..sd_count {
            let (len, n) = varint::decode(&input[pos..])
                .map_err(|_| PolicyDecodeError::Truncated)?;
            pos += n;
            let len = len as usize;
            if pos + len > input.len() {
                return Err(PolicyDecodeError::Truncated);
            }
            let domain = String::from_utf8(input[pos..pos + len].to_vec())
                .map_err(|_| PolicyDecodeError::InvalidUtf8)?;
            search_domains.push(domain);
            pos += len;
        }

        Ok(DnsConfigFrame {
            nameservers,
            search_domains,
            ttl_seconds,
        })
    }
}

/// Policy frame decode errors.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum PolicyDecodeError {
    #[error("frame truncated")]
    Truncated,
    #[error("invalid route action: {0}")]
    InvalidRouteAction(u8),
    #[error("invalid address family: {0}")]
    InvalidAddressFamily(u8),
    #[error("invalid UTF-8 in domain name")]
    InvalidUtf8,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn route_set_roundtrip_ipv4() {
        let frame = RouteSetFrame {
            replace: true,
            entries: vec![
                RouteEntry {
                    family: 4,
                    prefix: vec![10, 0, 0, 0],
                    prefix_len: 8,
                    action: RouteAction::Include,
                },
                RouteEntry {
                    family: 4,
                    prefix: vec![192, 168, 1, 0],
                    prefix_len: 24,
                    action: RouteAction::Exclude,
                },
            ],
        };
        let mut buf = Vec::new();
        frame.encode(&mut buf);
        let decoded = RouteSetFrame::decode(&buf).unwrap();
        assert_eq!(decoded, frame);
    }

    #[test]
    fn route_set_roundtrip_ipv6() {
        let mut prefix = vec![0x20, 0x01, 0x0d, 0xb8];
        prefix.extend_from_slice(&[0u8; 12]);
        let frame = RouteSetFrame {
            replace: false,
            entries: vec![RouteEntry {
                family: 6,
                prefix,
                prefix_len: 32,
                action: RouteAction::Direct,
            }],
        };
        let mut buf = Vec::new();
        frame.encode(&mut buf);
        let decoded = RouteSetFrame::decode(&buf).unwrap();
        assert_eq!(decoded, frame);
    }

    #[test]
    fn route_set_empty() {
        let frame = RouteSetFrame {
            replace: true,
            entries: vec![],
        };
        let mut buf = Vec::new();
        frame.encode(&mut buf);
        let decoded = RouteSetFrame::decode(&buf).unwrap();
        assert_eq!(decoded, frame);
    }

    #[test]
    fn dns_config_roundtrip() {
        let frame = DnsConfigFrame {
            nameservers: vec![
                NameserverAddr::V4([8, 8, 8, 8]),
                NameserverAddr::V4([8, 8, 4, 4]),
            ],
            search_domains: vec!["example.com".to_string(), "internal.corp".to_string()],
            ttl_seconds: 3600,
        };
        let mut buf = Vec::new();
        frame.encode(&mut buf);
        let decoded = DnsConfigFrame::decode(&buf).unwrap();
        assert_eq!(decoded, frame);
    }

    #[test]
    fn dns_config_ipv6() {
        let mut addr = [0u8; 16];
        addr[0] = 0x20;
        addr[1] = 0x01;
        let frame = DnsConfigFrame {
            nameservers: vec![NameserverAddr::V6(addr)],
            search_domains: vec![],
            ttl_seconds: 60,
        };
        let mut buf = Vec::new();
        frame.encode(&mut buf);
        let decoded = DnsConfigFrame::decode(&buf).unwrap();
        assert_eq!(decoded, frame);
    }

    #[test]
    fn invalid_route_action_rejected() {
        let frame = RouteSetFrame {
            replace: false,
            entries: vec![RouteEntry {
                family: 4,
                prefix: vec![10, 0, 0, 0],
                prefix_len: 8,
                action: RouteAction::Include,
            }],
        };
        let mut buf = Vec::new();
        frame.encode(&mut buf);
        // Corrupt the action byte
        buf[5] = 0xFF;
        let result = RouteSetFrame::decode(&buf);
        assert!(matches!(result, Err(PolicyDecodeError::InvalidRouteAction(0xFF))));
    }
}
