//! TLS ClientHello parsing and JA4 fingerprinting.
//!
//! This is the measuring instrument for the "looks like a browser" checks: it
//! parses the first TLS record a client sends and computes the JA4 fingerprint
//! (FoxIO JA4: protocol/version/SNI/counts/ALPN, then truncated SHA-256 of the
//! sorted cipher suites, then of the sorted extensions plus the signature
//! algorithms). GREASE values are ignored everywhere, as the spec requires.

use sha2::{Digest, Sha256};

/// Errors from parsing a ClientHello record.
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum ParseError {
    /// The bytes do not start with a TLS handshake record.
    #[error("not a TLS handshake record")]
    NotHandshake,
    /// The handshake message is not a ClientHello.
    #[error("not a ClientHello")]
    NotClientHello,
    /// The record ends before the structure does.
    #[error("truncated ClientHello")]
    Truncated,
}

/// Whether `v` is a GREASE value (RFC 8701): `0x0a0a`, `0x1a1a`, ... `0xfafa`.
pub fn is_grease(v: u16) -> bool {
    (v & 0x0f0f) == 0x0a0a && (v >> 8) == (v & 0xff)
}

/// A parsed ClientHello.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClientHello {
    /// `legacy_version` field (0x0303 for TLS 1.2/1.3).
    pub legacy_version: u16,
    /// Cipher suites in wire order, GREASE included.
    pub ciphers: Vec<u16>,
    /// Extension types in wire order, GREASE included.
    pub extensions: Vec<u16>,
    /// Extension payloads in wire order.
    pub ext_data: Vec<(u16, Vec<u8>)>,
    /// Server name from the SNI extension.
    pub sni: Option<String>,
    /// ALPN tokens in wire order.
    pub alpn: Vec<String>,
    /// Signature algorithms in wire order.
    pub sigalgs: Vec<u16>,
    /// `supported_versions` in wire order.
    pub supported_versions: Vec<u16>,
    /// `supported_groups` in wire order.
    pub groups: Vec<u16>,
    /// `(group, key_exchange length)` per key share.
    pub key_shares: Vec<(u16, usize)>,
    /// Length of the TLS record that carried the hello.
    pub record_len: usize,
}

/// A JA4 fingerprint in hashed and raw form.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Ja4 {
    /// `a_b_c` with the two hashes truncated to 12 hex characters.
    pub fingerprint: String,
    /// The same with the unhashed cipher and extension lists.
    pub raw: String,
}

struct Reader<'a> {
    b: &'a [u8],
    o: usize,
}

impl<'a> Reader<'a> {
    fn take(&mut self, n: usize) -> Result<&'a [u8], ParseError> {
        let end = self.o.checked_add(n).ok_or(ParseError::Truncated)?;
        let s = self.b.get(self.o..end).ok_or(ParseError::Truncated)?;
        self.o = end;
        Ok(s)
    }
    fn u8(&mut self) -> Result<u8, ParseError> {
        Ok(self.take(1)?[0])
    }
    fn u16(&mut self) -> Result<u16, ParseError> {
        let s = self.take(2)?;
        Ok(u16::from_be_bytes([s[0], s[1]]))
    }
}

fn u16_list(b: &[u8]) -> Vec<u16> {
    b.chunks_exact(2)
        .map(|c| u16::from_be_bytes([c[0], c[1]]))
        .collect()
}

impl ClientHello {
    /// Parse one TLS record that carries a ClientHello.
    pub fn parse(record: &[u8]) -> Result<Self, ParseError> {
        if record.len() < 9 || record[0] != 22 {
            return Err(ParseError::NotHandshake);
        }
        let rec_len = u16::from_be_bytes([record[3], record[4]]) as usize;
        let payload = record.get(5..5 + rec_len).ok_or(ParseError::Truncated)?;
        if payload.first() != Some(&1) {
            return Err(ParseError::NotClientHello);
        }
        let hs_len =
            ((payload[1] as usize) << 16) | ((payload[2] as usize) << 8) | payload[3] as usize;
        let body = payload.get(4..4 + hs_len).ok_or(ParseError::Truncated)?;

        let mut r = Reader { b: body, o: 0 };
        let legacy_version = r.u16()?;
        r.take(32)?; // random
        let sid = r.u8()? as usize;
        r.take(sid)?;
        let cs_len = r.u16()? as usize;
        let ciphers = u16_list(r.take(cs_len)?);
        let comp = r.u8()? as usize;
        r.take(comp)?;
        let ext_total = r.u16()? as usize;
        let ext_bytes = r.take(ext_total)?;

        let mut er = Reader { b: ext_bytes, o: 0 };
        let mut extensions = Vec::new();
        let mut ext_data = Vec::new();
        while er.o + 4 <= ext_bytes.len() {
            let t = er.u16()?;
            let l = er.u16()? as usize;
            let d = er.take(l)?.to_vec();
            extensions.push(t);
            ext_data.push((t, d));
        }

        let mut sni = None;
        let mut alpn = Vec::new();
        let mut sigalgs = Vec::new();
        let mut supported_versions = Vec::new();
        let mut groups = Vec::new();
        let mut key_shares = Vec::new();
        for (t, d) in &ext_data {
            match *t {
                0x0000 if d.len() >= 5 => {
                    let nl = u16::from_be_bytes([d[3], d[4]]) as usize;
                    if let Some(name) = d.get(5..5 + nl) {
                        sni = Some(String::from_utf8_lossy(name).into_owned());
                    }
                }
                0x0010 if d.len() >= 2 => {
                    let mut p = 2;
                    while p < d.len() {
                        let n = d[p] as usize;
                        if let Some(tok) = d.get(p + 1..p + 1 + n) {
                            alpn.push(String::from_utf8_lossy(tok).into_owned());
                        }
                        p += 1 + n;
                    }
                }
                0x000d if d.len() >= 2 => sigalgs = u16_list(&d[2..]),
                0x002b if !d.is_empty() => supported_versions = u16_list(&d[1..]),
                0x000a if d.len() >= 2 => groups = u16_list(&d[2..]),
                0x0033 if d.len() >= 2 => {
                    let end = 2 + u16::from_be_bytes([d[0], d[1]]) as usize;
                    let mut p = 2;
                    while p + 4 <= end.min(d.len()) {
                        let g = u16::from_be_bytes([d[p], d[p + 1]]);
                        let kl = u16::from_be_bytes([d[p + 2], d[p + 3]]) as usize;
                        key_shares.push((g, kl));
                        p += 4 + kl;
                    }
                }
                _ => {}
            }
        }

        Ok(Self {
            legacy_version,
            ciphers,
            extensions,
            ext_data,
            sni,
            alpn,
            sigalgs,
            supported_versions,
            groups,
            key_shares,
            record_len: 5 + rec_len,
        })
    }

    /// Whether the hello carries any GREASE cipher suite.
    pub fn has_grease_cipher(&self) -> bool {
        self.ciphers.iter().copied().any(is_grease)
    }

    /// Whether the encrypted_client_hello extension (0xfe0d) is present.
    pub fn has_ech(&self) -> bool {
        self.extensions.contains(&0xfe0d)
    }

    /// Compute the JA4 fingerprint (TCP transport).
    pub fn ja4(&self) -> Ja4 {
        let ciphers: Vec<u16> = self
            .ciphers
            .iter()
            .copied()
            .filter(|c| !is_grease(*c))
            .collect();
        let exts: Vec<u16> = self
            .extensions
            .iter()
            .copied()
            .filter(|e| !is_grease(*e))
            .collect();
        let sig: Vec<u16> = self
            .sigalgs
            .iter()
            .copied()
            .filter(|s| !is_grease(*s))
            .collect();
        let top = self
            .supported_versions
            .iter()
            .copied()
            .filter(|v| !is_grease(*v))
            .max()
            .unwrap_or(self.legacy_version);
        let ver = match top {
            0x0304 => "13",
            0x0303 => "12",
            0x0302 => "11",
            0x0301 => "10",
            0x0300 => "s3",
            0x0002 => "s2",
            _ => "00",
        };
        let sni_flag = if self.sni.is_some() { 'd' } else { 'i' };
        let alpn = match self.alpn.first() {
            Some(first) if !first.is_empty() => {
                let b = first.as_bytes();
                format!("{}{}", b[0] as char, b[b.len() - 1] as char)
            }
            _ => "00".to_string(),
        };
        let a = format!(
            "t{ver}{sni_flag}{:02}{:02}{alpn}",
            ciphers.len().min(99),
            exts.len().min(99)
        );

        let mut sorted_ciphers = ciphers;
        sorted_ciphers.sort_unstable();
        let b_in = sorted_ciphers
            .iter()
            .map(|c| format!("{c:04x}"))
            .collect::<Vec<_>>()
            .join(",");

        let mut sorted_exts: Vec<u16> = exts
            .into_iter()
            .filter(|e| *e != 0x0000 && *e != 0x0010)
            .collect();
        sorted_exts.sort_unstable();
        let mut c_in = sorted_exts
            .iter()
            .map(|e| format!("{e:04x}"))
            .collect::<Vec<_>>()
            .join(",");
        if !sig.is_empty() {
            c_in.push('_');
            c_in.push_str(
                &sig.iter()
                    .map(|s| format!("{s:04x}"))
                    .collect::<Vec<_>>()
                    .join(","),
            );
        }

        let hash12 = |s: &str| -> String {
            Sha256::digest(s.as_bytes())
                .iter()
                .take(6)
                .map(|b| format!("{b:02x}"))
                .collect()
        };
        Ja4 {
            fingerprint: format!("{a}_{}_{}", hash12(&b_in), hash12(&c_in)),
            raw: format!("{a}_{b_in}_{c_in}"),
        }
    }

    /// Differences between `self` (the probe) and `reference` beyond JA4, after
    /// masking what is random by design: GREASE values, key-share material, the
    /// ECH payload, the session ticket and padding. An empty list means the two
    /// hellos are the same ClientHello as far as a passive observer can tell.
    pub fn differences_from(&self, reference: &ClientHello) -> Vec<String> {
        let mut diffs = Vec::new();
        let strip = |v: &[u16]| {
            v.iter()
                .copied()
                .filter(|x| !is_grease(*x))
                .collect::<Vec<_>>()
        };
        let mut check = |name: &str, same: bool, a: String, b: String| {
            if !same {
                diffs.push(format!("{name}: reference {a}, probe {b}"));
            }
        };
        check(
            "ja4",
            self.ja4().fingerprint == reference.ja4().fingerprint,
            reference.ja4().fingerprint,
            self.ja4().fingerprint,
        );
        check(
            "cipher suites",
            strip(&self.ciphers) == strip(&reference.ciphers),
            format!("{:04x?}", strip(&reference.ciphers)),
            format!("{:04x?}", strip(&self.ciphers)),
        );
        check(
            "GREASE cipher present",
            self.has_grease_cipher() == reference.has_grease_cipher(),
            reference.has_grease_cipher().to_string(),
            self.has_grease_cipher().to_string(),
        );
        let mut ea = strip(&self.extensions);
        let mut eb = strip(&reference.extensions);
        ea.sort_unstable();
        eb.sort_unstable();
        check(
            "extension set",
            ea == eb,
            format!("{eb:04x?}"),
            format!("{ea:04x?}"),
        );
        check(
            "GREASE extension count",
            self.extensions.iter().filter(|e| is_grease(**e)).count()
                == reference
                    .extensions
                    .iter()
                    .filter(|e| is_grease(**e))
                    .count(),
            reference
                .extensions
                .iter()
                .filter(|e| is_grease(**e))
                .count()
                .to_string(),
            self.extensions
                .iter()
                .filter(|e| is_grease(**e))
                .count()
                .to_string(),
        );
        check(
            "supported_groups",
            strip(&self.groups) == strip(&reference.groups),
            format!("{:04x?}", strip(&reference.groups)),
            format!("{:04x?}", strip(&self.groups)),
        );
        check(
            "signature_algorithms (order)",
            self.sigalgs == reference.sigalgs,
            format!("{:04x?}", reference.sigalgs),
            format!("{:04x?}", self.sigalgs),
        );
        check(
            "supported_versions",
            strip(&self.supported_versions) == strip(&reference.supported_versions),
            format!("{:04x?}", strip(&reference.supported_versions)),
            format!("{:04x?}", strip(&self.supported_versions)),
        );
        check(
            "ALPN list",
            self.alpn == reference.alpn,
            format!("{:?}", reference.alpn),
            format!("{:?}", self.alpn),
        );
        let ks = |h: &ClientHello| {
            h.key_shares
                .iter()
                .copied()
                .filter(|(g, _)| !is_grease(*g))
                .collect::<Vec<_>>()
        };
        check(
            "key share groups and sizes",
            ks(self) == ks(reference),
            format!("{:?}", ks(reference)),
            format!("{:?}", ks(self)),
        );
        // Per-extension payloads: everything not random by design must match.
        const VOLATILE: [u16; 6] = [0x0015, 0x0023, 0xfe0d, 0x0033, 0x000a, 0x002b];
        for (t, d) in &reference.ext_data {
            if VOLATILE.contains(t) || is_grease(*t) || *t == 0x0000 {
                continue;
            }
            if let Some((_, mine)) = self.ext_data.iter().find(|(tt, _)| tt == t) {
                if mine != d {
                    diffs.push(format!(
                        "extension {t:#06x} payload: reference {}, probe {}",
                        hex(d),
                        hex(mine)
                    ));
                }
            }
        }
        diffs
    }
}

fn hex(b: &[u8]) -> String {
    b.iter().map(|x| format!("{x:02x}")).collect()
}

/// Decode a hex string (lowercase or uppercase, no separators).
pub fn unhex(s: &str) -> Option<Vec<u8>> {
    if !s.len().is_multiple_of(2) {
        return None;
    }
    (0..s.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&s[i..i + 2], 16).ok())
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn grease_values() {
        for v in [0x0a0au16, 0x1a1a, 0x2a2a, 0xdada, 0xfafa] {
            assert!(is_grease(v), "{v:#06x}");
        }
        for v in [0x1301u16, 0x0a1a, 0x0000, 0xff01, 0x44cd] {
            assert!(!is_grease(v), "{v:#06x}");
        }
    }

    #[test]
    fn rejects_non_client_hello() {
        assert_eq!(
            ClientHello::parse(b"GET / HTTP/1.1\r\n\r\n"),
            Err(ParseError::NotHandshake)
        );
        // handshake record carrying a ServerHello (type 2)
        let rec = [22u8, 3, 3, 0, 4, 2, 0, 0, 0];
        assert_eq!(ClientHello::parse(&rec), Err(ParseError::NotClientHello));
    }

    #[test]
    fn truncated_record_is_an_error_not_a_panic() {
        let rec = [22u8, 3, 1, 0x02, 0x00, 1, 0, 1, 0xfc];
        assert_eq!(ClientHello::parse(&rec), Err(ParseError::Truncated));
    }

    #[test]
    fn chrome_cipher_set_hash_is_the_well_known_value() {
        // The standard Chrome suite list hashes to 8daaf6152771 in every
        // published Chrome JA4; this pins our JA4_b implementation to them.
        let h = ClientHello {
            legacy_version: 0x0303,
            ciphers: vec![
                0x1301, 0x1302, 0x1303, 0xc02b, 0xc02f, 0xc02c, 0xc030, 0xcca9, 0xcca8, 0xc013,
                0xc014, 0x009c, 0x009d, 0x002f, 0x0035,
            ],
            extensions: vec![],
            ext_data: vec![],
            sni: Some("example.org".into()),
            alpn: vec!["h2".into(), "http/1.1".into()],
            sigalgs: vec![],
            supported_versions: vec![0x0304, 0x0303],
            groups: vec![],
            key_shares: vec![],
            record_len: 0,
        };
        assert!(h.ja4().fingerprint.starts_with("t13d1500h2_8daaf6152771_"));
    }
}
