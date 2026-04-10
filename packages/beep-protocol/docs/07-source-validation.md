# Source Validation Matrix

This file records what the cited sources actually support and how those facts affect `Beep`.

## Standards and official protocol references

| Source | What it supports | Impact on Beep |
| --- | --- | --- |
| [RFC 9484](https://www.rfc-editor.org/rfc/rfc9484.html) | Standardizes IP proxying in HTTP, explicitly includes remote-access and site-to-site VPN use cases, uses HTTP Extended CONNECT for H2/H3 | Confirms that `cover_h3` can be standards-based for IP tunneling and that MASQUE-compatible design is not speculative |
| [RFC 9298](https://www.rfc-editor.org/rfc/rfc9298.html) | Standardizes UDP proxying in HTTP and ties it to HTTP Datagrams and Extended CONNECT | Confirms that UDP tunneling over H2/H3 is standardized |
| [RFC 9297](https://www.rfc-editor.org/rfc/rfc9297.html) | Defines HTTP Datagrams and Capsule Protocol | Validates datagram carriage model used by MASQUE-related transports |
| [RFC 9221](https://www.rfc-editor.org/rfc/rfc9221.html) | Defines unreliable datagrams over QUIC | Supports using datagrams as a first-class capability in QUIC-based profiles |
| [RFC 9849](https://www.rfc-editor.org/rfc/rfc9849.pdf) | Final RFC for Encrypted Client Hello, published March 2026 | Confirms ECH is now formally standardized, but does not justify relying on universal deployment |

## Vendor and platform documentation

| Source | What it supports | Impact on Beep |
| --- | --- | --- |
| [Cloudflare JA3/JA4 docs](https://developers.cloudflare.com/bots/additional-configurations/ja3-ja4-fingerprint/) | JA3/JA4 are used as operational signals; JA4 adds normalized extension handling | Confirms that outer presentation matters beyond encryption alone |
| [Cloudflare Signals Intelligence](https://developers.cloudflare.com/bots/additional-configurations/ja3-ja4-fingerprint/signals-intelligence/) | JA4 is correlated with HTTP/2/HTTP/3 ratios, browser ratio, networks, paths, and errors | Confirms that transport and application behavior are part of a broader operational identity |
| [Cloudflare ECH docs](https://developers.cloudflare.com/ssl/edge-certificates/ech/) | ECH splits ClientHello into outer and inner components | Supports treating ECH as a useful privacy feature, not a complete strategy |
| [Mozilla ECH help](https://support.mozilla.org/en-US/kb/understand-encrypted-client-hello) | ECH is enabled by default where available | Confirms real browser deployment, but not universal availability |
| [Cloudflare PQ to origin docs](https://developers.cloudflare.com/ssl/post-quantum-cryptography/pqc-to-origin/) | Adding ML-KEM commonly makes ClientHello span two packets | Strong evidence for keeping outer PQ usage profile-specific and conservative |
| [Cloudflare WARP MASQUE rollout](https://blog.cloudflare.com/masque-now-powers-1-1-1-1-and-warp-apps-dex-available-with-remote-captures/) | New WARP installs support MASQUE and it is rolled out as preferred over WireGuard | Confirms MASQUE is production-grade for VPN-like use |
| [Cloudflare tokio-quiche blog](https://blog.cloudflare.com/async-quic-and-http-3-made-easy-tokio-quiche-is-now-open-source/) | tokio-quiche powers Cloudflare's MASQUE client in WARP and Proxy B in Apple Private Relay | Confirms QUIC/H3 proxying at large scale and makes tokio-quiche a serious evaluation target |

## Cloud provider guidance on fronting and authority matching

| Source | What it supports | Impact on Beep |
| --- | --- | --- |
| [AWS CloudFront CNAME guidance](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/CNAMEs.html) | CloudFront states it has protection against domain fronting across AWS accounts and checks SNI against Host | Confirms classic domain fronting is not a safe architectural assumption |
| [Azure Front Door enforcement notice](https://learn.microsoft.com/en-us/answers/questions/1421101/take-action-to-stop-domain-fronting-on-your-applic) | Azure moved to block domain-fronting behavior unless both names belong to the same subscription setup | Reinforces that supported authority matching is required |

## Research and measurement papers

| Source | What it supports | Impact on Beep |
| --- | --- | --- |
| [IMC 2022 TSPU paper](https://censoredplanet.org/assets/tspu-imc22.pdf) | Shows SNI-, IP-, and QUIC-triggered interference; in-path and stateful behavior close to users | Strong argument for transport agility and against betting only on one outer transport |
| [USENIX Security 2024 nested TLS paper](https://www.usenix.org/system/files/usenixsecurity24-xue-fingerprinting.pdf) | Encapsulated TLS handshakes create detectable size/timing/direction patterns; padding alone is insufficient; multiplexing helps but is limited | Strong argument against TLS-in-TLS as the default Beep design |
| [NDSS 2023 probe-resistant proxies paper](https://www.ndss-symposium.org/ndss-paper/detecting-probe-resistant-proxies/) | Even probe-resistant proxies can be distinguishable via TCP behavior with minimal false positives | Supports the decision to keep v1 focused on robust standards-based transports rather than fragile covert tricks |
| [FOCI 2023 ShadowTLS paper](https://www.petsymposium.org/foci/2023/foci-2023-0002.php) | Handshake-forwarding can evade simple SNI blocking but remains attackable and detectable | Another reason not to design Beep around relay tricks or nested handshake semantics |
| [FOCI 2025 ECH in Circumvention](https://censorbib.nymity.ch/pdf/Niere2025b.pdf) | ECH support and advertisement are uneven; benefit is limited in current deployment reality | Confirms that ECH is helpful but not sufficient as a product pillar |
| [QUIC is not Quick Enough over Fast Internet](https://ahmadhassandebugs.github.io/assets/pdf/quic_www24.pdf) | Reports that QUIC/H3 can be up to 45.2% slower than TCP/TLS/H2 on fast Internet links | Supports keeping H2/TCP as a first-class path |

## Rust ecosystem references

| Source | What it supports | Impact on Beep |
| --- | --- | --- |
| [quinn-rs/quinn](https://github.com/quinn-rs/quinn) | Quinn is an async-friendly Rust QUIC implementation with pluggable cryptography | Validates Quinn as a clean pure-Rust baseline for QUIC experiments and client-side work |
| [rustls issue #1932](https://github.com/rustls/rustls/issues/1932) | Exposing arbitrary ClientHello customization is a requested but non-trivial use case | Supports keeping TLS provider details behind an abstraction boundary |
| [rustls issue #2498](https://github.com/rustls/rustls/issues/2498) | ClientHello fingerprinting remains an active topic rather than a standard product capability | Another reason not to make exact presentation control a v1 dependency |

## Performance and implementation references

| Source | What it supports | Impact on Beep |
| --- | --- | --- |
| [quic-go optimization docs](https://quic-go.net/docs/quic/optimizations/) | QUIC benefits from GSO/GRO and larger UDP buffers on high-bandwidth links | Confirms QUIC performance work is operational, not theoretical |
| [tokio-quiche socket capabilities docs](https://docs.quic.tech/tokio_quiche/socket/struct.SocketCapabilitiesBuilder.html) | Exposes socket features such as `UDP_SEGMENT`, `UDP_GRO`, pacing, and drop reporting | Supports a node-runtime design that treats socket capabilities as first-class data |

## NIST PQC references

| Source | What it supports | Impact on Beep |
| --- | --- | --- |
| [NIST first three PQ standards](https://www.nist.gov/news-events/news/2024/08/nist-releases-first-3-finalized-post-quantum-encryption-standards) | FIPS 203, 204, and 205 were finalized in August 2024 | Confirms that crypto agility and hybrid planning are no longer speculative |

## Corrections we deliberately made

The validated sources support the broad direction, but we intentionally corrected these earlier tendencies:

- We did not make exact browser impersonation central to `Beep v1`.
- We renamed the overly narrow `fingerprint_bundle` concept into `presentation_profile`.
- We did not treat undocumented Apple internals as a protocol argument; we used public Cloudflare statements only.
- We did not assume QUIC is always faster.
- We did not treat ECH deployment as universal or sufficient.

## Final interpretation

The source base is strong enough to support the `Beep` thesis, but only in this refined form:

- stable session core,
- standards-based H2/H3 dual baseline,
- optional native-fast profile,
- independently rollable artifacts,
- Rust-first implementation with provider boundaries,
- continuous validation in lab and canary environments.
