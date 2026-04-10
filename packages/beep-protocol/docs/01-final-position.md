# Beep: Final Position After Source Validation

Date of review: 2026-04-08

## Scope

This document replaces the earlier `Helix` framing with a clean starting point for `Beep`. It does not treat the previous text as a protocol spec. Instead, it validates the main engineering conclusions, softens overstatements, and turns them into concrete decisions for a Rust implementation program.

## Short verdict

The strongest 2026 direction for `Beep` is:

`stable session core + H2/H3 dual-cover architecture + independent policy artifacts + lab-driven rollout`

In practice this means:

- do not bind the product to one eternal outer transport;
- do not make QUIC/UDP the only path;
- do not bury protocol evolution inside TLS tricks or one-off obfuscation;
- do keep the inner session semantics stable while the outer transport and policy can change independently.

## What remains correct from the original thesis

The following conclusions are sound and should stay:

| Claim | Status | Final wording |
| --- | --- | --- |
| One outer transport will accumulate operational signatures and policy exposure | Keep | `Beep` must support multiple transport profiles from day one. |
| MASQUE is a strong baseline, but QUIC cannot be the only transport | Keep | `Beep` should be MASQUE-compatible, not MASQUE-dependent. |
| HTTP/2 over TLS/TCP on 443 must stay first-class | Keep | `cover_h2` is a compatibility baseline, not merely a fallback. |
| Nested TLS handshakes are a detection risk | Keep | The session core must never require TLS-in-TLS as its standard mode. |
| ECH is useful but not a complete strategy | Keep | Support ECH-compatible deployments where available, but do not rely on ECH for viability. |
| Domain fronting is not a viable architectural pillar | Keep | Use only supported CDN patterns with matching authority and certificates. |
| PQ agility is necessary, but outer handshakes should not be destabilized by default | Keep | Default PQ posture belongs inside the inner session core and signed artifacts. |

## What needed correction

The original text had several good instincts, but some of its claims were too strong or too tightly coupled to stealth assumptions.

### 1. Exact browser mimicry should not be a v1 dependency

The source material was right that `rustls` is not built around byte-exact `ClientHello` impersonation. However, the correct architectural conclusion is narrower:

- keep the TLS provider behind an abstraction boundary;
- do not make exact browser impersonation part of the protocol core;
- treat advanced presentation control as an optional edge capability, not as the center of the product.

For `Beep v1`, the requirement is standards-compliant, mass-deployable outer behavior. Exact third-party client impersonation is an R&D branch, not the foundation.

### 2. `fingerprint_bundle` is too narrow a name for the real artifact

The original proposal correctly wanted independently rollable outer behavior, but the artifact is larger than TLS fingerprint data. In `Beep`, the better model is:

- `transport_profile` — transport family and capability envelope;
- `presentation_profile` — TLS/ALPN/HTTP settings that define outer presentation;
- `policy_bundle` — path selection, rollout rules, retry and timeout policy;
- `probe_recipe` — what the client tests before committing to a profile.

This is more maintainable than overloading everything into a single `fingerprint_bundle`.

### 3. Apple is a scale reference, not the protocol proof we depend on

Public Cloudflare material confirms that `tokio-quiche` powers Cloudflare's MASQUE client in WARP and also powers Cloudflare's Proxy B in Apple iCloud Private Relay. That is enough to treat it as a real scale reference for QUIC/H3 proxying. It is not, by itself, a reason to base the `Beep` argument on a public Apple-specific MASQUE specification. `Beep` should stand on RFCs and public transport behavior, not on assumptions about undocumented third-party internals.

## Final design position

### Decision 1. Beep owns the session semantics

`Beep` should define its own inner session/core with:

- authentication and authorization context;
- stream and datagram multiplexing;
- session resumption and key updates;
- replay protection;
- policy and capability negotiation;
- telemetry budgets and path hints.

This core is the long-lived part of the protocol.

### Decision 2. Outer transports stay standards-based

`Beep` should ship three transport families:

- `cover_h2` — HTTP/2 Extended CONNECT over TLS/TCP 443;
- `cover_h3` — HTTP/3 with MASQUE building blocks such as CONNECT-IP and CONNECT-UDP;
- `native_fast` — a low-overhead mode for networks where compatibility pressure is low.

These profiles share one session core and one policy engine.

### Decision 3. H2 is not optional

QUIC is powerful, but not universally faster or more deployable. Public RFC guidance and performance work both show that UDP-based stacks benefit from kernel and NIC offloads, tuned buffers, and favorable path behavior. Therefore:

- H3/MASQUE is the performance baseline;
- H2/TCP is the compatibility baseline;
- profile choice must be based on measured path quality, not ideology.

### Decision 4. PQ belongs inside the stable core first

`Beep` should be crypto-agile from day one, but the default production posture is:

- outer H2/H3 presentation remains conservative and interoperable;
- hybrid KEM support is negotiated inside the session core;
- control-plane signatures and manifest integrity are PQ-ready on a roadmap, without forcing a brittle outer wire image.

### Decision 5. Beep must be a platform, not a one-shot protocol

`Beep` needs signed and independently rollable artifacts:

- `session_core_version`
- `transport_profile`
- `presentation_profile`
- `policy_bundle`
- `probe_recipe`

This is the difference between "we shipped a protocol" and "we can keep operating it under changing real networks."

## Final formula

The best starting point for `Beep` is not a monolithic "anti-DPI protocol".

It is:

`a Rust session core with transport agility, H2/H3 dual baseline, optional native-fast mode, signed policy artifacts, and continuous path validation`

That is the position the rest of the documentation set assumes.

## References

- [RFC 9484: Proxying IP in HTTP](https://www.rfc-editor.org/rfc/rfc9484.html)
- [RFC 9298: Proxying UDP in HTTP](https://www.rfc-editor.org/rfc/rfc9298.html)
- [RFC 9297: HTTP Datagrams and the Capsule Protocol](https://www.rfc-editor.org/rfc/rfc9297.html)
- [RFC 9221: QUIC Datagrams](https://www.rfc-editor.org/rfc/rfc9221.html)
- [RFC 9849: TLS Encrypted Client Hello](https://www.rfc-editor.org/rfc/rfc9849.pdf)
- [Cloudflare: MASQUE now powers WARP apps](https://blog.cloudflare.com/masque-now-powers-1-1-1-1-and-warp-apps-dex-available-with-remote-captures/)
- [Cloudflare: tokio-quiche is now open source](https://blog.cloudflare.com/async-quic-and-http-3-made-easy-tokio-quiche-is-now-open-source/)
- [Cloudflare: JA3/JA4 fingerprint docs](https://developers.cloudflare.com/bots/additional-configurations/ja3-ja4-fingerprint/)
- [Cloudflare: ECH docs](https://developers.cloudflare.com/ssl/edge-certificates/ech/)
- [Mozilla: Understand ECH](https://support.mozilla.org/en-US/kb/understand-encrypted-client-hello)
- [Cloudflare: Post-quantum to origin](https://developers.cloudflare.com/ssl/post-quantum-cryptography/pqc-to-origin/)
- [AWS CloudFront CNAME/domain fronting guidance](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/CNAMEs.html)
- [Azure Front Door domain fronting enforcement notice](https://learn.microsoft.com/en-us/answers/questions/1421101/take-action-to-stop-domain-fronting-on-your-applic)
- [USENIX Security 2024: Encapsulated TLS handshake fingerprinting](https://www.usenix.org/system/files/usenixsecurity24-xue-fingerprinting.pdf)
- [IMC 2022: TSPU in-path, stateful blocking](https://censoredplanet.org/assets/tspu-imc22.pdf)
- [NIST: first three finalized PQ standards](https://www.nist.gov/news-events/news/2024/08/nist-releases-first-3-finalized-post-quantum-encryption-standards)

